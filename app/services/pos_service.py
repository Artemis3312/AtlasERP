from typing import List, Dict, Any, Tuple, Optional
from ..database.db import get_connection
from ..utils.helpers import now_iso, parse_float
from .shift_service import ShiftService
from .exchange_rate import ExchangeRateService


class PosService:
    @staticmethod
    def get_next_invoice_number(cursor=None) -> str:
        """Genera el siguiente número consecutivo de factura"""
        should_close = False
        if cursor is None:
            conn = get_connection()
            cursor = conn.cursor()
            should_close = True
        else:
            conn = None

        cursor.execute("SELECT value FROM settings WHERE key = 'invoice_sequence'")
        row = cursor.fetchone()
        seq = int(row["value"]) if row else 1000
        new_seq = seq + 1
        cursor.execute("UPDATE settings SET value = ? WHERE key = 'invoice_sequence'", (str(new_seq),))
        if should_close and conn:
            conn.commit()
            conn.close()
        return f"FAC-{seq:06d}"

    @staticmethod
    def process_sale(
        items: List[Dict[str, Any]],
        payments: List[Dict[str, Any]],
        client_name: str = "Consumidor Final",
        client_id_doc: str = "V-00000000",
        notes: str = ""
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Procesa una venta completa con múltiples métodos de pago y descuento de inventario.
        items: [{'product_id': int, 'code': str, 'name': str, 'qty': float, 'price_usd': float}]
        payments: [{'method': str, 'amount': float, 'currency': 'USD'|'BS', 'reference': str}]
        """
        if not items:
            return False, "El carrito de compras está vacío.", None

        active_shift = ShiftService.get_active_shift()
        if not active_shift:
            return False, "No hay un turno de caja abierto. Debe abrir turno antes de facturar.", None

        rate = ExchangeRateService.get_active_rate()
        if rate <= 0:
            return False, "La tasa de cambio actual es inválida.", None

        # Calcular totales de la venta
        total_usd = 0.0
        for item in items:
            qty = parse_float(item.get("qty", 1.0))
            price_usd = parse_float(item.get("price_usd", 0.0))
            if qty <= 0:
                return False, f"La cantidad para '{item.get('name')}' debe ser mayor a 0.", None
            total_usd += qty * price_usd

        total_usd = round(total_usd, 2)
        total_bs = round(total_usd * rate, 2)

        # Validar pagos
        total_paid_usd = 0.0
        processed_payments = []

        for p in payments:
            method = p.get("method")
            amount = parse_float(p.get("amount", 0.0))
            currency = p.get("currency", "USD")
            ref = str(p.get("reference", "")).strip()

            if amount <= 0:
                continue

            if method == "BS_PAGO_MOVIL" and not ref:
                return False, "El método Pago Móvil requiere obligatoriamente un número de referencia.", None

            if currency == "USD":
                amount_usd_equiv = amount
                amount_bs_equiv = round(amount * rate, 2)
            else:
                amount_usd_equiv = round(amount / rate, 2)
                amount_bs_equiv = amount

            total_paid_usd += amount_usd_equiv
            processed_payments.append({
                "method": method,
                "amount": amount,
                "currency": currency,
                "amount_usd_equiv": amount_usd_equiv,
                "amount_bs_equiv": amount_bs_equiv,
                "reference": ref
            })

        total_paid_usd = round(total_paid_usd, 2)
        # Tolerancia pequeña por redondeos en centavos de dólar/bolívares
        if total_paid_usd < (total_usd - 0.02):
            falta_usd = round(total_usd - total_paid_usd, 2)
            falta_bs = round(falta_usd * rate, 2)
            return False, f"Monto incompleto. Faltan ${falta_usd:,.2f} (Bs. {falta_bs:,.2f}).", None

        # Procesar en base de datos
        conn = get_connection()
        cursor = conn.cursor()
        ts = now_iso()

        try:
            # 1. Verificar y descontar stock
            for item in items:
                prod_id = item["product_id"]
                qty = parse_float(item["qty"])
                cursor.execute("SELECT stock, name FROM products WHERE id = ?", (prod_id,))
                prod_row = cursor.fetchone()
                if not prod_row:
                    conn.rollback()
                    conn.close()
                    return False, f"El producto ID {prod_id} no existe en inventario.", None

                current_stock = float(prod_row["stock"])
                if current_stock < qty:
                    conn.rollback()
                    conn.close()
                    return False, f"Stock insuficiente para '{prod_row['name']}'. Disponible: {current_stock}, Solicitado: {qty}.", None

                cursor.execute("UPDATE products SET stock = stock - ?, updated_at = ? WHERE id = ?", (qty, ts, prod_id))

            # 2. Insertar venta
            invoice_num = PosService.get_next_invoice_number(cursor=cursor)
            cursor.execute("""
                INSERT INTO sales (invoice_number, shift_id, created_at, client_name, client_id_doc,
                                   total_usd, total_bs, exchange_rate, status, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'COMPLETED', ?)
            """, (invoice_num, active_shift["id"], ts, client_name or "Consumidor Final",
                  client_id_doc or "V-00000000", total_usd, total_bs, rate, notes))
            sale_id = cursor.lastrowid

            # 3. Insertar items
            for item in items:
                qty = parse_float(item["qty"])
                p_usd = parse_float(item["price_usd"])
                p_bs = round(p_usd * rate, 2)
                sub_usd = round(qty * p_usd, 2)
                sub_bs = round(sub_usd * rate, 2)

                cursor.execute("""
                    INSERT INTO sale_items (sale_id, product_id, product_code, product_name,
                                           quantity, price_usd, price_bs, subtotal_usd, subtotal_bs)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (sale_id, item["product_id"], item.get("code", ""), item.get("name", ""),
                      qty, p_usd, p_bs, sub_usd, sub_bs))

            # 4. Insertar pagos
            for p in processed_payments:
                cursor.execute("""
                    INSERT INTO sale_payments (sale_id, method, amount, currency, amount_usd_equiv,
                                              amount_bs_equiv, reference, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (sale_id, p["method"], p["amount"], p["currency"],
                      p["amount_usd_equiv"], p["amount_bs_equiv"], p["reference"], ts))

            # 5. Registrar en movimientos de caja
            methods_used = ", ".join(sorted(list(set(p["method"] for p in processed_payments))))
            cursor.execute("""
                INSERT INTO cash_movements (shift_id, sale_id, type, description, amount_usd,
                                           amount_bs, payment_method, created_at)
                VALUES (?, ?, 'VENTA', ?, ?, ?, ?, ?)
            """, (active_shift["id"], sale_id, f"Venta {invoice_num} ({client_name})",
                  total_usd, total_bs, methods_used, ts))

            conn.commit()
            conn.close()

            sale_result = {
                "sale_id": sale_id,
                "invoice_number": invoice_num,
                "created_at": ts,
                "client_name": client_name,
                "client_id_doc": client_id_doc,
                "total_usd": total_usd,
                "total_bs": total_bs,
                "rate": rate,
                "items_count": len(items),
                "payments": processed_payments
            }
            return True, f"Venta {invoice_num} procesada exitosamente.", sale_result

        except Exception as e:
            conn.rollback()
            conn.close()
            return False, f"Error al procesar la venta: {str(e)}", None

    @staticmethod
    def process_cash_advance(
        amount_cash_dispensed_bs: float,
        payment_method: str,
        reference: str,
        commission_pct: float = 0.0,
        client_name: str = "Cliente Avance"
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Realiza un 'Avance de Efectivo':
        El negocio entrega BS en efectivo al cliente y cobra ese monto (más comisión si aplica)
        mediante Tarjeta (punto) o Pago Móvil.
        """
        active_shift = ShiftService.get_active_shift()
        if not active_shift:
            return False, "No hay un turno de caja abierto para registrar el avance de efectivo.", None

        dispensed_bs = parse_float(amount_cash_dispensed_bs, 0.0)
        commission_pct = parse_float(commission_pct, 0.0)
        reference = str(reference).strip()
        payment_method = payment_method.strip()

        if dispensed_bs <= 0:
            return False, "El monto de efectivo en BS a entregar debe ser mayor a 0.", None

        if payment_method not in ("BS_TARJETA", "BS_PAGO_MOVIL"):
            return False, "El método de recepción debe ser 'BS_TARJETA' o 'BS_PAGO_MOVIL'.", None

        if payment_method == "BS_PAGO_MOVIL" and not reference:
            return False, "El Pago Móvil requiere obligatoriamente el número de referencia bancaria.", None

        # Validar disponibilidad de efectivo en bolívares en caja
        metrics = ShiftService.get_shift_metrics(active_shift["id"])
        available_bs_cash = metrics.get("expected_cash_bs", 0.0)
        if dispensed_bs > available_bs_cash:
            return False, (
                f"Efectivo en bolívares insuficiente en caja para realizar este avance.\n"
                f"Disponible en gaveta: Bs. {available_bs_cash:,.2f}\n"
                f"Solicitado para avance: Bs. {dispensed_bs:,.2f}"
            ), None

        charged_bs = round(dispensed_bs * (1 + (commission_pct / 100.0)), 2)
        commission_bs = round(charged_bs - dispensed_bs, 2)
        ts = now_iso()

        conn = get_connection()
        cursor = conn.cursor()
        try:
            # Registrar movimiento de caja
            desc = (
                f"Avance de Efectivo: Entregado Bs. {dispensed_bs:,.2f} efectivo | "
                f"Recibido Bs. {charged_bs:,.2f} vía {payment_method.replace('BS_', '')} "
                f"(Comisión: {commission_pct}% - Ref: {reference or 'N/A'})"
            )
            cursor.execute("""
                INSERT INTO cash_movements (shift_id, type, description, amount_usd, amount_bs,
                                           payment_method, reference, created_at)
                VALUES (?, 'AVANCE_EFECTIVO', ?, 0.0, ?, ?, ?, ?)
            """, (active_shift["id"], desc, dispensed_bs, payment_method, reference, ts))

            conn.commit()
            conn.close()

            data = {
                "dispensed_bs": dispensed_bs,
                "charged_bs": charged_bs,
                "commission_bs": commission_bs,
                "payment_method": payment_method,
                "reference": reference,
                "created_at": ts
            }
            return True, f"Avance de efectivo por Bs. {dispensed_bs:,.2f} procesado exitosamente.", data
        except Exception as e:
            conn.close()
            return False, f"Error al registrar avance de efectivo: {str(e)}", None

    @staticmethod
    def get_recent_sales(limit: int = 50) -> List[Dict[str, Any]]:
        """Obtiene las ventas recientes con sus detalles de pago"""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT s.*, 
                   COALESCE(GROUP_CONCAT(DISTINCT p.method), 'N/A') as payment_methods
            FROM sales s
            LEFT JOIN sale_payments p ON s.id = p.sale_id
            GROUP BY s.id
            ORDER BY s.id DESC
            LIMIT ?
        """, (limit,))
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows
