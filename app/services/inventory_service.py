from typing import List, Dict, Any, Optional, Tuple
from ..database.db import get_connection
from ..utils.helpers import now_iso, parse_float


class InventoryService:
    @staticmethod
    def list_products(search_term: str = "", active_only: bool = True) -> List[Dict[str, Any]]:
        """Lista productos filtrados por búsqueda (código o nombre)"""
        conn = get_connection()
        cursor = conn.cursor()

        query = "SELECT * FROM products WHERE 1=1"
        params = []

        if active_only:
            query += " AND is_active = 1"

        if search_term and search_term.strip():
            clean = f"%{search_term.strip()}%"
            query += " AND (code LIKE ? OR name LIKE ? OR category LIKE ?)"
            params.extend([clean, clean, clean])

        query += " ORDER BY name ASC"
        cursor.execute(query, params)
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return rows

    @staticmethod
    def get_by_code(code: str) -> Optional[Dict[str, Any]]:
        """Busca un producto por código exacto o código de barras"""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM products WHERE code = ? AND is_active = 1", (code.strip(),))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    @staticmethod
    def get_by_id(product_id: int) -> Optional[Dict[str, Any]]:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM products WHERE id = ?", (product_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    @staticmethod
    def save_product(product_id: Optional[int], code: str, name: str, category: str,
                     cost_usd: float, price_usd: float, stock: float, min_stock: float) -> Tuple[bool, str]:
        """Crea o actualiza un producto validando unicidad de código"""
        code = str(code).strip()
        name = str(name).strip()
        category = str(category).strip() or "General"
        cost_usd = parse_float(cost_usd, 0.0)
        price_usd = parse_float(price_usd, 0.0)
        stock = parse_float(stock, 0.0)
        min_stock = parse_float(min_stock, 5.0)

        if not code:
            return False, "El código o código de barra es obligatorio."
        if not name:
            return False, "El nombre del producto es obligatorio."
        if price_usd <= 0:
            return False, "El precio en USD debe ser mayor a 0."

        conn = get_connection()
        cursor = conn.cursor()
        ts = now_iso()

        try:
            if product_id:
                # Verificar duplicado de código en otros productos
                cursor.execute("SELECT id FROM products WHERE code = ? AND id != ?", (code, product_id))
                if cursor.fetchone():
                    conn.close()
                    return False, f"Ya existe otro producto con el código '{code}'."

                cursor.execute("""
                    UPDATE products
                    SET code = ?, name = ?, category = ?, cost_usd = ?, price_usd = ?,
                        stock = ?, min_stock = ?, updated_at = ?
                    WHERE id = ?
                """, (code, name, category, cost_usd, price_usd, stock, min_stock, ts, product_id))
                conn.commit()
                conn.close()
                return True, "Producto actualizado exitosamente."
            else:
                # Verificar código existente
                cursor.execute("SELECT id FROM products WHERE code = ?", (code,))
                if cursor.fetchone():
                    conn.close()
                    return False, f"Ya existe un producto con el código '{code}'."

                cursor.execute("""
                    INSERT INTO products (code, name, category, cost_usd, price_usd, stock, min_stock, is_active, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
                """, (code, name, category, cost_usd, price_usd, stock, min_stock, ts, ts))
                conn.commit()
                conn.close()
                return True, "Producto registrado exitosamente."
        except Exception as e:
            conn.close()
            return False, f"Error al guardar producto: {str(e)}"

    @staticmethod
    def delete_product(product_id: int) -> Tuple[bool, str]:
        """Elimina un producto (o lo desactiva si tiene ventas registradas)"""
        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT COUNT(*) FROM sale_items WHERE product_id = ?", (product_id,))
            has_sales = cursor.fetchone()[0] > 0
            if has_sales:
                cursor.execute("UPDATE products SET is_active = 0, updated_at = ? WHERE id = ?", (now_iso(), product_id))
                conn.commit()
                conn.close()
                return True, "El producto tiene ventas históricas asociadas; fue desactivado del catálogo."
            else:
                cursor.execute("DELETE FROM products WHERE id = ?", (product_id,))
                conn.commit()
                conn.close()
                return True, "Producto eliminado permanentemente."
        except Exception as e:
            conn.close()
            return False, f"Error al eliminar producto: {str(e)}"

    @staticmethod
    def get_inventory_summary() -> Dict[str, Any]:
        """Estadísticas globales del inventario para tarjetas informativas y reportes"""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                COUNT(*) as total_items,
                SUM(stock) as total_units,
                SUM(stock * cost_usd) as total_cost_usd,
                SUM(stock * price_usd) as total_retail_usd,
                SUM(CASE WHEN stock <= min_stock THEN 1 ELSE 0 END) as low_stock_count
            FROM products 
            WHERE is_active = 1
        """)
        row = cursor.fetchone()
        conn.close()

        return {
            "total_items": row["total_items"] or 0,
            "total_units": row["total_units"] or 0.0,
            "total_cost_usd": row["total_cost_usd"] or 0.0,
            "total_retail_usd": row["total_retail_usd"] or 0.0,
            "low_stock_count": row["low_stock_count"] or 0,
        }
