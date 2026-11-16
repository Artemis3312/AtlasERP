import os
from pathlib import Path
from typing import Optional, Dict, Any, List
from fpdf import FPDF
from fpdf.enums import XPos, YPos
from ..database.db import get_connection, DB_PATH
from ..utils.helpers import now_iso, format_dt_display, format_usd, format_bs, format_qty
from .exchange_rate import ExchangeRateService

REPORTS_DIR = DB_PATH.parent / "reports"


class AtlasPDF(FPDF):
    def __init__(self, title_text: str, subtitle_text: str = ""):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.title_text = title_text
        self.subtitle_text = subtitle_text
        self.set_auto_page_break(auto=True, margin=15)
        self.alias_nb_pages()

    def header(self):
        # Fondo sutil superior
        self.set_fill_color(15, 23, 42)  # Slate 900
        self.rect(0, 0, 210, 22, "F")

        # Logo / Marca
        self.set_font("helvetica", "B", 14)
        self.set_text_color(255, 255, 255)
        self.set_xy(10, 5)
        self.cell(70, 7, "AtlasERP", align="L")

        self.set_font("helvetica", "", 8)
        self.set_text_color(203, 213, 225)
        self.set_xy(10, 12)
        self.cell(70, 5, "Sistema de Gestión y Punto de Venta Offline", align="L")

        # Título del reporte en header
        self.set_font("helvetica", "B", 11)
        self.set_text_color(255, 255, 255)
        self.set_xy(90, 5)
        self.cell(110, 7, self.title_text, align="R")

        self.set_font("helvetica", "I", 8)
        self.set_text_color(203, 213, 225)
        self.set_xy(90, 12)
        self.cell(110, 5, self.subtitle_text, align="R")

        self.ln(12)
        self.set_text_color(0, 0, 0)

    def footer(self):
        self.set_y(-12)
        self.set_font("helvetica", "I", 8)
        self.set_text_color(100, 116, 139)
        self.cell(100, 8, f"Generado: {now_iso()} | AtlasERP Offline", align="L")
        self.cell(90, 8, f"Página {self.page_no()} de {{nb}}", align="R")


class ReportService:
    @staticmethod
    def generate_operations_report(start_date: str, end_date: str, output_path: Optional[str] = None) -> str:
        """
        Genera un reporte PDF con el histórico de operaciones y ventas entre dos fechas.
        start_date y end_date en formato 'YYYY-MM-DD'.
        """
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        if not output_path:
            filename = f"reporte_operaciones_{start_date}_a_{end_date}.pdf"
            output_path = str(REPORTS_DIR / filename)

        conn = get_connection()
        cursor = conn.cursor()

        # 1. Ventas en el rango
        cursor.execute("""
            SELECT s.*, 
                   COALESCE(GROUP_CONCAT(DISTINCT p.method), 'N/A') as methods
            FROM sales s
            LEFT JOIN sale_payments p ON s.id = p.sale_id
            WHERE date(s.created_at) >= date(?) AND date(s.created_at) <= date(?)
            GROUP BY s.id
            ORDER BY s.created_at DESC
        """, (start_date, end_date))
        sales = [dict(r) for r in cursor.fetchall()]

        # 2. Resumen financiero de pagos
        cursor.execute("""
            SELECT 
                p.method,
                SUM(p.amount) as total_amount,
                SUM(p.amount_usd_equiv) as total_usd,
                SUM(p.amount_bs_equiv) as total_bs
            FROM sale_payments p
            JOIN sales s ON p.sale_id = s.id
            WHERE date(s.created_at) >= date(?) AND date(s.created_at) <= date(?) AND s.status = 'COMPLETED'
            GROUP BY p.method
        """, (start_date, end_date))
        payment_breakdown = {r["method"]: dict(r) for r in cursor.fetchall()}

        # 3. Avances de efectivo en el rango
        cursor.execute("""
            SELECT 
                payment_method,
                SUM(amount_bs) as total_dispensed_bs,
                COUNT(*) as count
            FROM cash_movements
            WHERE type = 'AVANCE_EFECTIVO' 
              AND date(created_at) >= date(?) AND date(created_at) <= date(?)
            GROUP BY payment_method
        """, (start_date, end_date))
        advances = [dict(r) for r in cursor.fetchall()]
        total_advances_bs = sum(a["total_dispensed_bs"] or 0.0 for a in advances)

        # 4. Todos los movimientos para la tabla cronológica
        cursor.execute("""
            SELECT * FROM cash_movements
            WHERE date(created_at) >= date(?) AND date(created_at) <= date(?)
            ORDER BY created_at DESC
        """, (start_date, end_date))
        movements = [dict(r) for r in cursor.fetchall()]

        conn.close()

        # Totales generales de ventas
        total_sales_usd = sum(s["total_usd"] for s in sales if s["status"] == "COMPLETED")
        total_sales_bs = sum(s["total_bs"] for s in sales if s["status"] == "COMPLETED")

        # Construir PDF
        pdf = AtlasPDF(
            title_text="HISTÓRICO DE OPERACIONES Y VENTAS",
            subtitle_text=f"Período: {start_date} al {end_date}"
        )
        pdf.add_page()

        # Resumen superior
        pdf.set_font("helvetica", "B", 12)
        pdf.set_text_color(15, 23, 42)
        pdf.cell(0, 8, "Resumen Global del Período", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        # Cajas de resumen (KPIs)
        # Caja 1: Total Ventas USD
        pdf.set_fill_color(241, 245, 249)
        pdf.set_draw_color(203, 213, 225)
        pdf.rect(10, 36, 45, 18, "FD")
        pdf.set_xy(12, 38)
        pdf.set_font("helvetica", "", 7)
        pdf.set_text_color(71, 85, 105)
        pdf.cell(41, 4, "TOTAL VENTAS USD", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_x(12)
        pdf.set_font("helvetica", "B", 11)
        pdf.set_text_color(16, 185, 129)
        pdf.cell(41, 7, format_usd(total_sales_usd), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        # Caja 2: Total Ventas BS
        pdf.rect(58, 36, 45, 18, "FD")
        pdf.set_xy(60, 38)
        pdf.set_font("helvetica", "", 7)
        pdf.set_text_color(71, 85, 105)
        pdf.cell(41, 4, "TOTAL VENTAS BS", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_x(60)
        pdf.set_font("helvetica", "B", 9)
        pdf.set_text_color(37, 99, 235)
        pdf.cell(41, 7, format_bs(total_sales_bs), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        # Caja 3: Cantidad de Ventas
        pdf.rect(106, 36, 45, 18, "FD")
        pdf.set_xy(108, 38)
        pdf.set_font("helvetica", "", 7)
        pdf.set_text_color(71, 85, 105)
        pdf.cell(41, 4, "TOTAL FACTURAS", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_x(108)
        pdf.set_font("helvetica", "B", 11)
        pdf.set_text_color(15, 23, 42)
        pdf.cell(41, 7, f"{len(sales)} ops", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        # Caja 4: Avances de Efectivo BS
        pdf.rect(154, 36, 46, 18, "FD")
        pdf.set_xy(156, 38)
        pdf.set_font("helvetica", "", 7)
        pdf.set_text_color(71, 85, 105)
        pdf.cell(42, 4, "AVANCES EFECTIVO BS", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_x(156)
        pdf.set_font("helvetica", "B", 9)
        pdf.set_text_color(217, 119, 6)
        pdf.cell(42, 7, format_bs(total_advances_bs), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        pdf.set_y(58)

        # Desglose de recaudación por método de pago
        pdf.set_font("helvetica", "B", 10)
        pdf.set_text_color(15, 23, 42)
        pdf.cell(0, 6, "Desglose por Método de Pago en Ventas:", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        pdf.set_font("helvetica", "B", 8)
        pdf.set_fill_color(226, 232, 240)
        pdf.cell(50, 6, "Método", 1, align="L", fill=True)
        pdf.cell(45, 6, "Monto Original", 1, align="R", fill=True)
        pdf.cell(45, 6, "Equivalente USD", 1, align="R", fill=True)
        pdf.cell(50, 6, "Equivalente BS", 1, align="R", fill=True)
        pdf.ln()

        method_labels = {
            "USD_EFECTIVO": "USD Efectivo",
            "BS_EFECTIVO": "Bolívares Efectivo",
            "BS_TARJETA": "Bolívares Tarjeta (P.O.S.)",
            "BS_PAGO_MOVIL": "Bolívares Pago Móvil"
        }

        pdf.set_font("helvetica", "", 8)
        for m_key, m_name in method_labels.items():
            row_data = payment_breakdown.get(m_key, {"total_amount": 0.0, "total_usd": 0.0, "total_bs": 0.0})
            orig_str = format_usd(row_data["total_amount"]) if "USD" in m_key else format_bs(row_data["total_amount"])
            pdf.cell(50, 5, m_name, 1, align="L")
            pdf.cell(45, 5, orig_str, 1, align="R")
            pdf.cell(45, 5, format_usd(row_data["total_usd"]), 1, align="R")
            pdf.cell(50, 5, format_bs(row_data["total_bs"]), 1, align="R")
            pdf.ln()

        pdf.ln(5)

        # Tabla detallada de movimientos y ventas
        pdf.set_font("helvetica", "B", 10)
        pdf.set_text_color(15, 23, 42)
        pdf.cell(0, 6, "Detalle Cronológico de Movimientos de Caja:", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        pdf.set_font("helvetica", "B", 7.5)
        pdf.set_fill_color(15, 23, 42)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(28, 6, "Fecha/Hora", 1, align="C", fill=True)
        pdf.cell(24, 6, "Tipo", 1, align="C", fill=True)
        pdf.cell(62, 6, "Descripción", 1, align="L", fill=True)
        pdf.cell(26, 6, "Método", 1, align="C", fill=True)
        pdf.cell(24, 6, "Monto USD", 1, align="R", fill=True)
        pdf.cell(26, 6, "Monto BS", 1, align="R", fill=True)
        pdf.ln()

        pdf.set_font("helvetica", "", 7)
        pdf.set_text_color(0, 0, 0)
        fill = False

        for m in movements:
            pdf.set_fill_color(248, 250, 252) if fill else pdf.set_fill_color(255, 255, 255)
            # Truncar descripción si es muy larga
            desc = m["description"][:38] + "..." if len(m["description"]) > 40 else m["description"]
            created = format_dt_display(m["created_at"])
            m_type = m["type"]
            method_show = (m["payment_method"] or "").replace("BS_", "").replace("USD_", "")

            pdf.cell(28, 5, created, 1, align="C", fill=fill)
            pdf.cell(24, 5, m_type, 1, align="C", fill=fill)
            pdf.cell(62, 5, desc, 1, align="L", fill=fill)
            pdf.cell(26, 5, method_show, 1, align="C", fill=fill)
            pdf.cell(24, 5, format_usd(m["amount_usd"]), 1, align="R", fill=fill)
            pdf.cell(26, 5, format_bs(m["amount_bs"]), 1, align="R", fill=fill)
            pdf.ln()
            fill = not fill

        pdf.output(output_path)
        return output_path

    @staticmethod
    def generate_inventory_report(output_path: Optional[str] = None) -> str:
        """
        Genera un reporte PDF con el estado actual del inventario, valorizaciones
        y alertas de reposición (stock mínimo).
        """
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        if not output_path:
            filename = f"reporte_inventario_{now_iso().replace(':', '-').replace(' ', '_')}.pdf"
            output_path = str(REPORTS_DIR / filename)

        rate = ExchangeRateService.get_active_rate()
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM products WHERE is_active = 1 ORDER BY category ASC, name ASC")
        products = [dict(r) for r in cursor.fetchall()]
        conn.close()

        # Cálculos de valorización
        total_items = len(products)
        total_units = sum(float(p["stock"] or 0) for p in products)
        total_cost_usd = sum(float(p["stock"] or 0) * float(p["cost_usd"] or 0) for p in products)
        total_retail_usd = sum(float(p["stock"] or 0) * float(p["price_usd"] or 0) for p in products)
        total_cost_bs = total_cost_usd * rate
        total_retail_bs = total_retail_usd * rate
        low_stock_products = [p for p in products if float(p["stock"] or 0) <= float(p["min_stock"] or 0)]

        pdf = AtlasPDF(
            title_text="REPORTE DE INVENTARIO Y EXISTENCIAS",
            subtitle_text=f"Tasa Activa: Bs. {rate:,.2f} / USD"
        )
        pdf.add_page()

        # Resumen general de inventario
        pdf.set_font("helvetica", "B", 11)
        pdf.set_text_color(15, 23, 42)
        pdf.cell(0, 7, "Valorización Global del Inventario", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        # Cajas KPI
        pdf.set_fill_color(241, 245, 249)
        pdf.set_draw_color(203, 213, 225)

        # Caja 1: Total Unidades
        pdf.rect(10, 36, 45, 18, "FD")
        pdf.set_xy(12, 38)
        pdf.set_font("helvetica", "", 7)
        pdf.set_text_color(71, 85, 105)
        pdf.cell(41, 4, "PRODUCTOS / UNIDADES", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_x(12)
        pdf.set_font("helvetica", "B", 10)
        pdf.set_text_color(15, 23, 42)
        pdf.cell(41, 7, f"{total_items} arts / {format_qty(total_units)} und", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        # Caja 2: Valor al Costo
        pdf.rect(58, 36, 45, 18, "FD")
        pdf.set_xy(60, 38)
        pdf.set_font("helvetica", "", 7)
        pdf.set_text_color(71, 85, 105)
        pdf.cell(41, 4, "VALOR AL COSTO (USD)", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_x(60)
        pdf.set_font("helvetica", "B", 10)
        pdf.set_text_color(37, 99, 235)
        pdf.cell(41, 7, format_usd(total_cost_usd), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        # Caja 3: Valor de Venta
        pdf.rect(106, 36, 45, 18, "FD")
        pdf.set_xy(108, 38)
        pdf.set_font("helvetica", "", 7)
        pdf.set_text_color(71, 85, 105)
        pdf.cell(41, 4, "VALOR DE VENTA (USD)", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_x(108)
        pdf.set_font("helvetica", "B", 10)
        pdf.set_text_color(16, 185, 129)
        pdf.cell(41, 7, format_usd(total_retail_usd), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        # Caja 4: Alertas de Stock Mínimo
        pdf.rect(154, 36, 46, 18, "FD")
        pdf.set_xy(156, 38)
        pdf.set_font("helvetica", "", 7)
        pdf.set_text_color(71, 85, 105)
        pdf.cell(42, 4, "STOCK BAJO / AGOTADO", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_x(156)
        pdf.set_font("helvetica", "B", 10)
        pdf.set_text_color(225, 29, 72)
        pdf.cell(42, 7, f"{len(low_stock_products)} en alerta", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        pdf.set_y(58)

        # Tabla detallada de catálogo
        pdf.set_font("helvetica", "B", 10)
        pdf.set_text_color(15, 23, 42)
        pdf.cell(0, 6, "Listado Detallado de Productos:", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        # Cabecera de tabla
        pdf.set_font("helvetica", "B", 7.5)
        pdf.set_fill_color(15, 23, 42)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(25, 6, "Código", 1, align="C", fill=True)
        pdf.cell(56, 6, "Descripción del Producto", 1, align="L", fill=True)
        pdf.cell(24, 6, "Categoría", 1, align="L", fill=True)
        pdf.cell(20, 6, "Costo USD", 1, align="R", fill=True)
        pdf.cell(20, 6, "Precio USD", 1, align="R", fill=True)
        pdf.cell(24, 6, "Precio BS", 1, align="R", fill=True)
        pdf.cell(21, 6, "Stock (Mín)", 1, align="C", fill=True)
        pdf.ln()

        pdf.set_font("helvetica", "", 7.5)
        fill = False

        for p in products:
            stock_val = float(p["stock"] or 0)
            min_val = float(p["min_stock"] or 0)
            p_usd = float(p["price_usd"] or 0)
            p_bs = p_usd * rate
            c_usd = float(p["cost_usd"] or 0)

            is_low = stock_val <= min_val
            if is_low:
                pdf.set_fill_color(254, 226, 226)  # Red light highlight
                pdf.set_text_color(185, 28, 28)
            else:
                pdf.set_fill_color(248, 250, 252) if fill else pdf.set_fill_color(255, 255, 255)
                pdf.set_text_color(15, 23, 42)

            name = p["name"][:32] + "..." if len(p["name"]) > 34 else p["name"]
            cat = p["category"][:14]

            pdf.cell(25, 5, str(p["code"]), 1, align="C", fill=True)
            pdf.cell(56, 5, name, 1, align="L", fill=True)
            pdf.cell(24, 5, cat, 1, align="L", fill=True)
            pdf.cell(20, 5, format_usd(c_usd), 1, align="R", fill=True)
            pdf.cell(20, 5, format_usd(p_usd), 1, align="R", fill=True)
            pdf.cell(24, 5, format_bs(p_bs), 1, align="R", fill=True)
            pdf.cell(21, 5, f"{format_qty(stock_val)} ({format_qty(min_val)})", 1, align="C", fill=True)
            pdf.ln()
            fill = not fill

        pdf.output(output_path)
        return output_path
