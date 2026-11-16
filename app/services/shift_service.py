from typing import Optional, Dict, Any, List, Tuple
from ..database.db import get_connection
from ..utils.helpers import now_iso, parse_float


class ShiftService:
    @staticmethod
    def get_active_shift() -> Optional[Dict[str, Any]]:
        """Devuelve el turno actualmente abierto, o None si no hay turno activo."""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM shifts WHERE status = 'OPEN' ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    @staticmethod
    def open_shift(initial_usd: float = 0.0, initial_bs: float = 0.0, cashier_name: str = "Cajero Principal") -> Tuple[bool, str, Optional[int]]:
        """Abre un nuevo turno de caja con montos base."""
        active = ShiftService.get_active_shift()
        if active:
            return False, f"Ya existe un turno abierto (Turno #{active['id']}). Debe cerrarlo primero.", active['id']

        initial_usd = max(0.0, parse_float(initial_usd, 0.0))
        initial_bs = max(0.0, parse_float(initial_bs, 0.0))
        cashier_name = cashier_name.strip() or "Cajero Principal"
        ts = now_iso()

        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO shifts (opened_at, status, cashier_name, initial_cash_usd, initial_cash_bs)
                VALUES (?, 'OPEN', ?, ?, ?)
            """, (ts, cashier_name, initial_usd, initial_bs))
            shift_id = cursor.lastrowid

            # Registrar movimiento de apertura
            cursor.execute("""
                INSERT INTO cash_movements (shift_id, type, description, amount_usd, amount_bs, payment_method, created_at)
                VALUES (?, 'APERTURA', ?, ?, ?, 'MIXTO', ?)
            """, (shift_id, f"Apertura de turno #{shift_id}", initial_usd, initial_bs, ts))

            conn.commit()
            conn.close()
            return True, f"Turno #{shift_id} abierto correctamente.", shift_id
        except Exception as e:
            conn.close()
            return False, f"Error al abrir turno: {str(e)}", None

    @staticmethod
    def get_shift_metrics(shift_id: int) -> Dict[str, Any]:
        """Calcula el arqueo detallado y balance del turno."""
        conn = get_connection()
        cursor = conn.cursor()

        # Obtener turno
        cursor.execute("SELECT * FROM shifts WHERE id = ?", (shift_id,))
        shift_row = cursor.fetchone()
        if not shift_row:
            conn.close()
            return {}

        shift = dict(shift_row)
        initial_usd = float(shift.get("initial_cash_usd", 0.0) or 0.0)
        initial_bs = float(shift.get("initial_cash_bs", 0.0) or 0.0)

        # 1. Ventas por método de pago asociadas a este turno
        cursor.execute("""
            SELECT 
                p.method,
                SUM(p.amount) as total_amount,
                SUM(p.amount_usd_equiv) as total_usd,
                SUM(p.amount_bs_equiv) as total_bs
            FROM sale_payments p
            JOIN sales s ON p.sale_id = s.id
            WHERE s.shift_id = ? AND s.status = 'COMPLETED'
            GROUP BY p.method
        """, (shift_id,))

        payment_sums = {
            "USD_EFECTIVO": 0.0,
            "BS_EFECTIVO": 0.0,
            "BS_TARJETA": 0.0,
            "BS_PAGO_MOVIL": 0.0
        }
        for r in cursor.fetchall():
            payment_sums[r["method"]] = float(r["total_amount"] or 0.0)

        # 2. Avances de efectivo
        # Por avance: sale BS_EFECTIVO de caja, y entra BS_TARJETA o BS_PAGO_MOVIL
        cursor.execute("""
            SELECT 
                payment_method,
                SUM(amount_bs) as total_dispensed,
                COUNT(*) as count
            FROM cash_movements
            WHERE shift_id = ? AND type = 'AVANCE_EFECTIVO'
            GROUP BY payment_method
        """, (shift_id,))

        advances_card_bs = 0.0
        advances_pm_bs = 0.0
        total_advances_dispensed_bs = 0.0

        for r in cursor.fetchall():
            method = r["payment_method"]
            amt = float(r["total_dispensed"] or 0.0)
            total_advances_dispensed_bs += amt
            if method == "BS_TARJETA":
                advances_card_bs += amt
            elif method == "BS_PAGO_MOVIL":
                advances_pm_bs += amt

        # 3. Ingresos y egresos manuales de caja
        cursor.execute("""
            SELECT 
                type,
                SUM(amount_usd) as usd_sum,
                SUM(amount_bs) as bs_sum
            FROM cash_movements
            WHERE shift_id = ? AND type IN ('INGRESO_MANUAL', 'EGRESO_MANUAL')
            GROUP BY type
        """, (shift_id,))

        manual_in_usd, manual_in_bs = 0.0, 0.0
        manual_out_usd, manual_out_bs = 0.0, 0.0
        for r in cursor.fetchall():
            if r["type"] == "INGRESO_MANUAL":
                manual_in_usd += float(r["usd_sum"] or 0.0)
                manual_in_bs += float(r["bs_sum"] or 0.0)
            elif r["type"] == "EGRESO_MANUAL":
                manual_out_usd += float(r["usd_sum"] or 0.0)
                manual_out_bs += float(r["bs_sum"] or 0.0)

        # 4. Vueltos entregados en efectivo durante el turno
        cursor.execute("""
            SELECT 
                COALESCE(SUM(change_usd), 0.0) as total_change_usd,
                COALESCE(SUM(change_bs), 0.0) as total_change_bs
            FROM sales
            WHERE shift_id = ? AND status = 'COMPLETED'
        """, (shift_id,))
        change_row = cursor.fetchone()
        total_change_usd = float(change_row["total_change_usd"] or 0.0) if change_row else 0.0
        total_change_bs = float(change_row["total_change_bs"] or 0.0) if change_row else 0.0

        conn.close()

        # Fórmulas de efectivo esperado en gaveta física
        expected_usd = initial_usd + payment_sums["USD_EFECTIVO"] - total_change_usd + manual_in_usd - manual_out_usd
        expected_bs = initial_bs + payment_sums["BS_EFECTIVO"] - total_change_bs - total_advances_dispensed_bs + manual_in_bs - manual_out_bs

        # Totales electrónicos acumulados
        total_card_bs = payment_sums["BS_TARJETA"] + advances_card_bs
        total_pm_bs = payment_sums["BS_PAGO_MOVIL"] + advances_pm_bs

        return {
            "shift_id": shift_id,
            "status": shift["status"],
            "opened_at": shift["opened_at"],
            "cashier_name": shift["cashier_name"],
            "initial_cash_usd": initial_usd,
            "initial_cash_bs": initial_bs,
            # Ventas directas
            "sales_usd_cash": payment_sums["USD_EFECTIVO"],
            "sales_bs_cash": payment_sums["BS_EFECTIVO"],
            "sales_bs_card": payment_sums["BS_TARJETA"],
            "sales_bs_pm": payment_sums["BS_PAGO_MOVIL"],
            # Vueltos entregados
            "total_change_usd": total_change_usd,
            "total_change_bs": total_change_bs,
            # Avances
            "advances_dispensed_bs": total_advances_dispensed_bs,
            "advances_card_bs": advances_card_bs,
            "advances_pm_bs": advances_pm_bs,
            # Movimientos manuales
            "manual_in_usd": manual_in_usd,
            "manual_in_bs": manual_in_bs,
            "manual_out_usd": manual_out_usd,
            "manual_out_bs": manual_out_bs,
            # Totales esperados en gaveta
            "expected_cash_usd": expected_usd,
            "expected_cash_bs": expected_bs,
            # Totales electrónicos a conciliar
            "total_card_bs": total_card_bs,
            "total_pago_movil_bs": total_pm_bs,
        }

    @staticmethod
    def close_shift(shift_id: int, real_cash_usd: float, real_cash_bs: float, notes: str = "") -> Tuple[bool, str, Dict[str, Any]]:
        """Cierra el turno registrando arqueo físico y calculando faltantes/sobrantes."""
        metrics = ShiftService.get_shift_metrics(shift_id)
        if not metrics:
            return False, "No se encontró el turno especificado.", {}

        real_usd = parse_float(real_cash_usd, 0.0)
        real_bs = parse_float(real_cash_bs, 0.0)
        expected_usd = metrics["expected_cash_usd"]
        expected_bs = metrics["expected_cash_bs"]

        diff_usd = round(real_usd - expected_usd, 2)
        diff_bs = round(real_bs - expected_bs, 2)
        ts = now_iso()

        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                UPDATE shifts
                SET closed_at = ?,
                    status = 'CLOSED',
                    expected_cash_usd = ?,
                    expected_cash_bs = ?,
                    real_cash_usd = ?,
                    real_cash_bs = ?,
                    diff_usd = ?,
                    diff_bs = ?,
                    total_card_bs = ?,
                    total_pago_movil_bs = ?,
                    notes = ?
                WHERE id = ?
            """, (ts, expected_usd, expected_bs, real_usd, real_bs, diff_usd, diff_bs,
                  metrics["total_card_bs"], metrics["total_pago_movil_bs"], notes, shift_id))

            # Registrar movimiento de cierre
            diff_desc = f"Dif USD: {diff_usd:+,.2f}, Dif BS: {diff_bs:+,.2f}" if (abs(diff_usd) > 0.001 or abs(diff_bs) > 0.001) else "Cuadrado (Sin diferencias)"
            desc = f"Cierre Turno #{shift_id}. {diff_desc}"
            cursor.execute("""
                INSERT INTO cash_movements (shift_id, type, description, amount_usd, amount_bs, payment_method, created_at)
                VALUES (?, 'CIERRE', ?, ?, ?, 'MIXTO', ?)
            """, (shift_id, desc, real_usd, real_bs, ts))

            conn.commit()
            conn.close()

            result_summary = {
                "shift_id": shift_id,
                "closed_at": ts,
                "expected_usd": expected_usd,
                "real_usd": real_usd,
                "diff_usd": diff_usd,
                "expected_bs": expected_bs,
                "real_bs": real_bs,
                "diff_bs": diff_bs,
                "total_card_bs": metrics["total_card_bs"],
                "total_pago_movil_bs": metrics["total_pago_movil_bs"],
            }
            return True, f"Turno #{shift_id} cerrado exitosamente.", result_summary
        except Exception as e:
            conn.close()
            return False, f"Error al cerrar turno: {str(e)}", {}
