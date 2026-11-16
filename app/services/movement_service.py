from typing import List, Dict, Any, Optional, Tuple
from ..database.db import get_connection
from ..utils.helpers import now_iso, parse_float
from .shift_service import ShiftService


class MovementService:
    @staticmethod
    def list_movements(
        shift_id: Optional[int] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        movement_type: Optional[str] = None,
        limit: int = 200
    ) -> List[Dict[str, Any]]:
        """Lista movimientos de caja con filtros opcionales de turno, fecha o tipo"""
        conn = get_connection()
        cursor = conn.cursor()

        query = """
            SELECT m.*, s.cashier_name, s.status as shift_status
            FROM cash_movements m
            LEFT JOIN shifts s ON m.shift_id = s.id
            WHERE 1=1
        """
        params = []

        if shift_id:
            query += " AND m.shift_id = ?"
            params.append(shift_id)

        if start_date:
            query += " AND date(m.created_at) >= date(?)"
            params.append(start_date)

        if end_date:
            query += " AND date(m.created_at) <= date(?)"
            params.append(end_date)

        if movement_type and movement_type != "TODOS":
            query += " AND m.type = ?"
            params.append(movement_type)

        query += " ORDER BY m.id DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows

    @staticmethod
    def add_manual_movement(
        movement_type: str,
        amount_usd: float,
        amount_bs: float,
        description: str,
        reference: str = ""
    ) -> Tuple[bool, str]:
        """Registra un ingreso o egreso manual a la caja"""
        active_shift = ShiftService.get_active_shift()
        if not active_shift:
            return False, "No hay un turno de caja abierto para registrar el movimiento."

        amt_usd = parse_float(amount_usd, 0.0)
        amt_bs = parse_float(amount_bs, 0.0)
        desc = str(description).strip()

        if amt_usd <= 0 and amt_bs <= 0:
            return False, "Debe ingresar un monto mayor a 0 en USD o en Bolívares."

        if not desc:
            return False, "Debe indicar el motivo o descripción del movimiento."

        if movement_type not in ("INGRESO_MANUAL", "EGRESO_MANUAL"):
            return False, "Tipo de movimiento inválido."

        ts = now_iso()
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO cash_movements (shift_id, type, description, amount_usd, amount_bs,
                                           payment_method, reference, created_at)
                VALUES (?, ?, ?, ?, ?, 'MANUAL', ?, ?)
            """, (active_shift["id"], movement_type, desc, amt_usd, amt_bs, reference, ts))
            conn.commit()
            conn.close()
            return True, f"Movimiento de {movement_type.replace('_', ' ')} registrado con éxito."
        except Exception as e:
            conn.close()
            return False, f"Error al registrar movimiento manual: {str(e)}"
