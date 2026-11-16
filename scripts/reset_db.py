"""
Script de Limpieza y Preparación de Base de Datos para Entrega de AtlasERP.

Uso:
  python scripts/reset_db.py --clean          (Vacía ventas, turnos, movimientos y productos para producción limpia)
  python scripts/reset_db.py --keep-products (Vacía ventas, turnos y movimientos, conservando productos)
  python scripts/reset_db.py                  (Modo interactivo en consola)
"""

import sys
import os
import argparse
from pathlib import Path

# Añadir raíz del proyecto al path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from app.database.db import get_connection, init_db
from app.utils.helpers import now_iso


def clean_database(include_products: bool = False, clean_reports: bool = True):
    print("\n" + "=" * 60)
    print(" PREPARACIÓN DE BASE DE DATOS - ATLAS ERP")
    print("=" * 60)

    # 1. Asegurar esquema inicial
    init_db()

    conn = get_connection()
    cursor = conn.cursor()

    try:
        # Desactivar temporalmente foreign keys para limpieza
        cursor.execute("PRAGMA foreign_keys = OFF;")

        # Borrar tablas operativas
        print("[+] Vaciando historial de pagos de ventas (sale_payments)...")
        cursor.execute("DELETE FROM sale_payments;")

        print("[+] Vaciando detalle de items de venta (sale_items)...")
        cursor.execute("DELETE FROM sale_items;")

        print("[+] Vaciando facturas y ventas (sales)...")
        cursor.execute("DELETE FROM sales;")

        print("[+] Vaciando movimientos de caja y vueltos (cash_movements)...")
        cursor.execute("DELETE FROM cash_movements;")

        print("[+] Vaciando aperturas y cierres de turno (shifts)...")
        cursor.execute("DELETE FROM shifts;")

        if include_products:
            print("[+] Vaciando catálogo de productos e inventario (products)...")
            cursor.execute("DELETE FROM products;")
            cursor.execute("DELETE FROM sqlite_sequence WHERE name = 'products';")
        else:
            print("[*] Conservando catálogo de productos existente.")

        # Reiniciar secuencias autoincrementales
        cursor.execute("DELETE FROM sqlite_sequence WHERE name IN ('sales', 'sale_items', 'sale_payments', 'cash_movements', 'shifts');")

        # Reiniciar número de factura a 1000
        print("[+] Reiniciando secuencia de facturación a FAC-001000...")
        cursor.execute("""
            INSERT OR REPLACE INTO settings (key, value, description, updated_at)
            VALUES ('invoice_sequence', '1000', 'Secuencia de facturación', ?)
        """, (now_iso(),))

        # Marcar modo producción (evita regenerar productos demo)
        cursor.execute("""
            INSERT OR REPLACE INTO settings (key, value, description, updated_at)
            VALUES ('demo_seeded', '1', 'Base de datos preparada para cliente', ?)
        """, (now_iso(),))

        cursor.execute("PRAGMA foreign_keys = ON;")
        conn.commit()

        # Optimizar y compactar archivo SQLite
        print("[+] Compactando base de datos (VACUUM)...")
        cursor.execute("VACUUM;")
        conn.close()

        # Limpiar reportes PDF de prueba
        if clean_reports:
            reports_dir = ROOT_DIR / "data" / "reports"
            if reports_dir.exists():
                count_rep = 0
                for f in reports_dir.glob("*.pdf"):
                    try:
                        f.unlink()
                        count_rep += 1
                    except Exception:
                        pass
                print(f"[+] Eliminados {count_rep} reportes PDF de prueba en data/reports/")

        print("\n" + "=" * 60)
        print(" [OK] Base de datos limpia y lista para entregar al cliente!")
        if include_products:
            print(" Estado: En blanco TOTAL (0 productos, 0 ventas, 0 turnos).")
        else:
            print(" Estado: Operación limpia (Productos conservados, 0 ventas, 0 turnos).")
        print(" Próxima factura: FAC-001000")
        print("=" * 60 + "\n")

    except Exception as e:
        conn.rollback()
        conn.close()
        print(f"\n[ERROR] Error al limpiar base de datos: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Limpiar base de datos para entrega de AtlasERP.")
    parser.add_argument("--clean", "--all", action="store_true", help="Limpieza total: borra ventas, turnos Y productos.")
    parser.add_argument("--keep-products", action="store_true", help="Limpieza operativa: borra ventas y turnos pero conserva productos.")
    parser.add_argument("--no-clean-reports", action="store_true", help="No borrar los PDFs de reportes generados.")

    args = parser.parse_args()

    clean_reports = not args.no_clean_reports

    if args.clean:
        clean_database(include_products=True, clean_reports=clean_reports)
    elif args.keep_products:
        clean_database(include_products=False, clean_reports=clean_reports)
    else:
        print("\n" + "=" * 60)
        print(" ATLAS ERP - ASISTENTE DE ENTREGA AL CLIENTE")
        print("=" * 60)
        print("Seleccione el tipo de limpieza que desea realizar:\n")
        print("  [1] Limpieza Total (Recomendado para entregar en blanco)")
        print("      - Borra todas las ventas, turnos y movimientos de caja.")
        print("      - Borra todos los productos para que el cliente cargue su propio inventario.")
        print("      - Reinicia facturas a FAC-001000 y limpia reportes de prueba.")
        print()
        print("  [2] Limpieza Operativa (Mantener Productos)")
        print("      - Borra todas las ventas, turnos y movimientos de caja.")
        print("      - CONSERVA los productos que ya están registrados en inventario.")
        print("      - Reinicia facturas a FAC-001000 y limpia reportes de prueba.")
        print()
        print("  [3] Cancelar y salir")
        print("=" * 60)

        choice = input("\nIngrese una opción (1, 2 o 3): ").strip()
        if choice == "1":
            clean_database(include_products=True, clean_reports=clean_reports)
        elif choice == "2":
            clean_database(include_products=False, clean_reports=clean_reports)
        else:
            print("[*] Operación cancelada. No se modificó la base de datos.")


if __name__ == "__main__":
    main()
