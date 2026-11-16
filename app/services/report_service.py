import os
from pathlib import Path
from typing import Optional, Dict, Any, List
from fpdf import FPDF
from fpdf.enums import XPos, YPos
from ..database.db import get_connection, DB_PATH
from ..utils.helpers import now_iso, format_dt_display, format_usd, format_bs, format_qty
from .exchange_rate import ExchangeRateService

REPORTS_DIR = DB_PATH.parent / "reports"
IMG_DIR = DB_PATH.parent.parent / "img"


class AtlasPDF(FPDF):
    def __init__(self, title_text: str, subtitle_text: str = ""):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.title_text = title_text
        self.subtitle_text = subtitle_text
        self.set_auto_page_break(auto=True, margin=15)
        self.alias_nb_pages()

    def header(self):
        # Fondo sutil superior con color de marca #222A2A
        self.set_fill_color(34, 42, 42)
        self.rect(0, 0, 210, 24, "F")

        # Línea de acento inferior en Turquesa #4FBBBC
        self.set_fill_color(79, 187, 188)
        self.rect(0, 23.5, 210, 1.5, "F")

        # Buscar logo en carpeta img
        logo_file = None
        for cand in ["logo.png", "logo.jpg", "atlaserp-icon-sin-fondo.svg", "atlaserp-icon.svg"]:
            p = IMG_DIR / cand
            if p.exists():
                logo_file = str(p)
                break

        x_text_start = 12
        if logo_file:
            try:
                self.image(logo_file, x=10, y=4, w=15)
                x_text_start = 28
            except Exception:
                pass

        # Logo / Marca
        self.set_font("helvetica", "B", 14)
        self.set_text_color(255, 255, 255)
        self.set_xy(x_text_start, 5)
        self.cell(70, 7, "AtlasERP", align="L")

        self.set_font("helvetica", "", 8)
        self.set_text_color(226, 218, 194)  # #E2DAC2
        self.set_xy(x_text_start, 13)
        self.cell(70, 5, "Sistema de Gestion y Punto de Venta Offline", align="L")

        # Título del reporte en header
        self.set_font("helvetica", "B", 10.5)
        self.set_text_color(255, 255, 255)
        self.set_xy(90, 5)
        self.cell(110, 7, self.title_text, align="R")

        self.set_font("helvetica", "I", 8)
        self.set_text_color(79, 187, 188)  # #4FBBBC
        self.set_xy(90, 13)
        self.cell(110, 5, self.subtitle_text, align="R")

        self.ln(16)
        self.set_text_color(34, 42, 42)

    def footer(self):
        self.set_y(-12)
        self.set_font("helvetica", "I", 8)
        self.set_text_color(100, 116, 139)
        self.cell(100, 8, f"Generado: {now_iso()} | AtlasERP Offline", align="L")
        self.cell(90, 8, f"Pagina {self.page_no()} de {{nb}}", align="R")


class ReportService:
    @staticmethod
    def generate_operations_report(start_date: str, end_date: str, output_path: Optional[str] = None) -> str:
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

        total_sales_usd = sum(s["total_usd"] for s in sales if s["status"] == "COMPLETED")
        total_sales_bs = sum(s["total_bs"] for s in sales if s["status"] == "COMPLETED")

        # Construir PDF
        pdf = AtlasPDF(
            title_text="HISTORICO DE OPERACIONES Y VENTAS",
            subtitle_text=f"Periodo: {start_date} al {end_date}"
        )
        pdf.add_page()

        pdf.set_font("helvetica", "B", 12)
        pdf.set_text_color(34, 42, 42)
        pdf.cell(0, 8, "Resumen Global del Periodo", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        # Cajas de resumen (KPIs) con colores de marca
        # Caja 1: Total Ventas USD
        pdf.set_fill_color(245, 242, 235)  # #F5F2EB
        pdf.set_draw_color(226, 218, 194)  # #E2DAC2
        pdf.rect(10, 38, 45, 18, "FD")
        pdf.set_xy(12, 40)
        pdf.set_font("helvetica", "", 7)
        pdf.set_text_color(100, 116, 139)
        pdf.cell(41, 4, "TOTAL VENTAS USD", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_x(12)
        pdf.set_font("helvetica", "B", 11)
        pdf.set_text_color(34, 42, 42)
        pdf.cell(41, 7, format_usd(total_sales_usd), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        # Caja 2: Total Ventas BS
        pdf.rect(58, 38, 45, 18, "FD")
        pdf.set_xy(60, 40)
        pdf.set_font("helvetica", "", 7)
        pdf.set_text_color(100, 116, 139)
        pdf.cell(41, 4, "TOTAL VENTAS BS", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_x(60)
        pdf.set_font("helvetica", "B", 9)
        pdf.set_text_color(79, 187, 188)  # #4FBBBC
        pdf.cell(41, 7, format_bs(total_sales_bs), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        # Caja 3: Cantidad de Ventas
        pdf.rect(106, 38, 45, 18, "FD")
        pdf.set_xy(108, 40)
        pdf.set_font("helvetica", "", 7)
        pdf.set_text_color(100, 116, 139)
        pdf.cell(41, 4, "TOTAL FACTURAS", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_x(108)
        pdf.set_font("helvetica", "B", 11)
        pdf.set_text_color(34, 42, 42)
        pdf.cell(41, 7, f"{len(sales)} facturas", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        # Caja 4: Avances de Efectivo BS
        pdf.rect(154, 38, 46, 18, "FD")
        pdf.set_xy(156, 40)
        pdf.set_font("helvetica", "", 7)
        pdf.set_text_color(100, 116, 139)
        pdf.cell(42, 4, "AVANCES EFECTIVO BS", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_x(156)
        pdf.set_font("helvetica", "B", 9)
        pdf.set_text_color(243, 145, 32)  # #F39120
        pdf.cell(42, 7, format_bs(total_advances_bs), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        pdf.set_y(60)

        # Desglose por método de pago
        pdf.set_font("helvetica", "B", 10)
        pdf.set_text_color(34, 42, 42)
        pdf.cell(0, 6, "Desglose por Metodo de Pago en Ventas:", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        pdf.set_font("helvetica", "B", 8)
        pdf.set_fill_color(226, 218, 194)  # #E2DAC2
        pdf.cell(50, 6, "Metodo", 1, align="L", fill=True)
        pdf.cell(45, 6, "Monto Original", 1, align="R", fill=True)
        pdf.cell(45, 6, "Equivalente USD", 1, align="R", fill=True)
        pdf.cell(50, 6, "Equivalente BS", 1, align="R", fill=True)
        pdf.ln()

        method_labels = {
            "USD_EFECTIVO": "USD Efectivo",
            "BS_EFECTIVO": "Bolivares Efectivo",
            "BS_TARJETA": "Bolivares Tarjeta (P.O.S.)",
            "BS_PAGO_MOVIL": "Bolivares Pago Movil"
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
        pdf.set_text_color(34, 42, 42)
        pdf.cell(0, 6, "Detalle Cronologico de Movimientos de Caja:", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        # Anchos de columnas balanceados para evitar cualquier desborde (Total: 190 mm)
        col_w_date = 25
        col_w_type = 18
        col_w_desc = 81
        col_w_method = 22
        col_w_usd = 20
        col_w_bs = 24

        pdf.set_font("helvetica", "B", 7.5)
        pdf.set_fill_color(34, 42, 42)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(col_w_date, 6, "Fecha/Hora", 1, align="C", fill=True)
        pdf.cell(col_w_type, 6, "Tipo", 1, align="C", fill=True)
        pdf.cell(col_w_desc, 6, "Descripcion", 1, align="L", fill=True)
        pdf.cell(col_w_method, 6, "Metodo", 1, align="C", fill=True)
        pdf.cell(col_w_usd, 6, "Monto USD", 1, align="R", fill=True)
        pdf.cell(col_w_bs, 6, "Monto BS", 1, align="R", fill=True)
        pdf.ln()

        pdf.set_font("helvetica", "", 6.8)
        pdf.set_text_color(34, 42, 42)
        fill = False

        type_display_map = {
            "AVANCE_EFECTIVO": "AVANCE",
            "INGRESO_MANUAL": "INGRESO",
            "EGRESO_MANUAL": "EGRESO",
            "VENTA": "VENTA",
            "CIERRE": "CIERRE",
            "APERTURA": "APERTURA",
            "VUELTO": "VUELTO"
        }

        def fit_cell_text(text: str, max_w: float) -> str:
            val = str(text or "").strip()
            if not val:
                return ""
            target_w = max_w - 2.0
            if pdf.get_string_width(val) <= target_w:
                return val
            while pdf.get_string_width(val) > target_w and len(val) > 3:
                val = val[:-4] + "..."
            return val

        for m in movements:
            pdf.set_fill_color(248, 246, 240) if fill else pdf.set_fill_color(255, 255, 255)

            # 1. Fecha / Hora
            created = fit_cell_text(format_dt_display(m["created_at"]), col_w_date)

            # 2. Tipo formateado (evita que AVANCE_EFECTIVO se desborde)
            raw_type = str(m.get("type") or "").strip()
            type_show = type_display_map.get(raw_type, raw_type.replace("_", " "))
            type_show = fit_cell_text(type_show, col_w_type)

            # 3. Descripción ajustada al ancho disponible
            desc = fit_cell_text(str(m.get("description") or ""), col_w_desc)

            # 4. Método formateado (múltiples métodos se muestran como MIXTO para no salirse de casilla)
            raw_method = str(m.get("payment_method") or "").strip()
            if "," in raw_method:
                method_show = "MIXTO"
            else:
                clean_m = raw_method.replace("BS_", "").replace("USD_", "").replace("_", " ").strip()
                method_show = clean_m if clean_m else "N/A"
            method_show = fit_cell_text(method_show, col_w_method)

            # 5. Montos numéricos
            usd_str = format_usd(m.get("amount_usd", 0.0))
            bs_str = format_bs(m.get("amount_bs", 0.0))

            pdf.cell(col_w_date, 5, created, 1, align="C", fill=fill)
            pdf.cell(col_w_type, 5, type_show, 1, align="C", fill=fill)
            pdf.cell(col_w_desc, 5, desc, 1, align="L", fill=fill)
            pdf.cell(col_w_method, 5, method_show, 1, align="C", fill=fill)
            pdf.cell(col_w_usd, 5, usd_str, 1, align="R", fill=fill)
            pdf.cell(col_w_bs, 5, bs_str, 1, align="R", fill=fill)
            pdf.ln()
            fill = not fill

        pdf.output(output_path)
        return output_path

    @staticmethod
    def generate_inventory_report(output_path: Optional[str] = None) -> str:
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

        total_items = len(products)
        total_units = sum(float(p["stock"] or 0) for p in products)
        total_cost_usd = sum(float(p["stock"] or 0) * float(p["cost_usd"] or 0) for p in products)
        total_retail_usd = sum(float(p["stock"] or 0) * float(p["price_usd"] or 0) for p in products)
        low_stock_products = [p for p in products if float(p["stock"] or 0) <= float(p["min_stock"] or 0)]

        pdf = AtlasPDF(
            title_text="REPORTE DE INVENTARIO Y EXISTENCIAS",
            subtitle_text=f"Tasa Activa: Bs. {rate:,.2f} / USD"
        )
        pdf.add_page()

        pdf.set_font("helvetica", "B", 11)
        pdf.set_text_color(34, 42, 42)
        pdf.cell(0, 7, "Valorizacion Global del Inventario", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        pdf.set_fill_color(245, 242, 235)
        pdf.set_draw_color(226, 218, 194)

        # Caja 1: Total Unidades
        pdf.rect(10, 38, 45, 18, "FD")
        pdf.set_xy(12, 40)
        pdf.set_font("helvetica", "", 7)
        pdf.set_text_color(100, 116, 139)
        pdf.cell(41, 4, "PRODUCTOS EN CATALOGO", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_x(12)
        pdf.set_font("helvetica", "B", 10)
        pdf.set_text_color(34, 42, 42)
        pdf.cell(41, 7, f"{total_items} articulos", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        # Caja 2: Valor al Costo
        pdf.rect(58, 38, 45, 18, "FD")
        pdf.set_xy(60, 40)
        pdf.set_font("helvetica", "", 7)
        pdf.set_text_color(100, 116, 139)
        pdf.cell(41, 4, "VALOR AL COSTO (USD)", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_x(60)
        pdf.set_font("helvetica", "B", 10)
        pdf.set_text_color(79, 187, 188)
        pdf.cell(41, 7, format_usd(total_cost_usd), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        # Caja 3: Valor de Venta
        pdf.rect(106, 38, 45, 18, "FD")
        pdf.set_xy(108, 40)
        pdf.set_font("helvetica", "", 7)
        pdf.set_text_color(100, 116, 139)
        pdf.cell(41, 4, "VALOR DE VENTA (USD)", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_x(108)
        pdf.set_font("helvetica", "B", 10)
        pdf.set_text_color(243, 145, 32)
        pdf.cell(41, 7, format_usd(total_retail_usd), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        # Caja 4: Alertas de Stock Mínimo
        pdf.rect(154, 38, 46, 18, "FD")
        pdf.set_xy(156, 40)
        pdf.set_font("helvetica", "", 7)
        pdf.set_text_color(100, 116, 139)
        pdf.cell(42, 4, "ALERTAS STOCK BAJO", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_x(156)
        pdf.set_font("helvetica", "B", 10)
        pdf.set_text_color(236, 70, 36)
        pdf.cell(42, 7, f"{len(low_stock_products)} en alerta", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        pdf.set_y(60)

        pdf.set_font("helvetica", "B", 10)
        pdf.set_text_color(34, 42, 42)
        pdf.cell(0, 6, "Listado Detallado de Productos:", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        # Cabecera de tabla
        pdf.set_font("helvetica", "B", 7.5)
        pdf.set_fill_color(34, 42, 42)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(24, 6, "Codigo", 1, align="C", fill=True)
        pdf.cell(52, 6, "Descripcion del Producto", 1, align="L", fill=True)
        pdf.cell(22, 6, "Categoria", 1, align="L", fill=True)
        pdf.cell(14, 6, "Unidad", 1, align="C", fill=True)
        pdf.cell(19, 6, "Costo USD", 1, align="R", fill=True)
        pdf.cell(19, 6, "Precio USD", 1, align="R", fill=True)
        pdf.cell(22, 6, "Precio BS", 1, align="R", fill=True)
        pdf.cell(18, 6, "Stock", 1, align="C", fill=True)
        pdf.ln()

        pdf.set_font("helvetica", "", 7.5)
        fill = False

        for p in products:
            stock_val = float(p["stock"] or 0)
            min_val = float(p["min_stock"] or 0)
            unit = p.get("unit", "UND") or "UND"
            p_usd = float(p["price_usd"] or 0)
            p_bs = p_usd * rate
            c_usd = float(p.get("cost_usd", 0.0) or 0)

            is_low = stock_val <= min_val
            if is_low:
                pdf.set_fill_color(254, 226, 226)
                pdf.set_text_color(236, 70, 36)
            else:
                pdf.set_fill_color(248, 246, 240) if fill else pdf.set_fill_color(255, 255, 255)
                pdf.set_text_color(34, 42, 42)

            name = p["name"][:30] + "..." if len(p["name"]) > 32 else p["name"]
            cat = p["category"][:12]

            pdf.cell(24, 5, str(p["code"]), 1, align="C", fill=True)
            pdf.cell(52, 5, name, 1, align="L", fill=True)
            pdf.cell(22, 5, cat, 1, align="L", fill=True)
            pdf.cell(14, 5, unit, 1, align="C", fill=True)
            pdf.cell(19, 5, format_usd(c_usd), 1, align="R", fill=True)
            pdf.cell(19, 5, format_usd(p_usd), 1, align="R", fill=True)
            pdf.cell(22, 5, format_bs(p_bs), 1, align="R", fill=True)
            pdf.cell(18, 5, format_qty(stock_val, unit), 1, align="C", fill=True)
            pdf.ln()
            fill = not fill

        pdf.output(output_path)
        return output_path
