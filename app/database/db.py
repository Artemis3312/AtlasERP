import sqlite3
import os
from pathlib import Path
from ..utils.helpers import now_iso

DB_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "atlas_erp.db"


def get_connection() -> sqlite3.Connection:
    """Obtiene una conexión a la base de datos SQLite con row_factory activado."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), timeout=15.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    return conn


def init_db():
    """Inicializa las tablas e inserta valores por defecto si no existen."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.executescript("""
    -- Tabla de configuración del sistema
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL,
        description TEXT,
        updated_at TEXT
    );

    -- Tabla de productos e inventario
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        category TEXT DEFAULT 'General',
        unit TEXT DEFAULT 'UND', -- 'UND' (Unidad), 'KG' (Kilogramo)
        cost_usd REAL DEFAULT 0.0,
        price_usd REAL NOT NULL,
        stock REAL DEFAULT 0.0,
        min_stock REAL DEFAULT 5.0,
        is_active INTEGER DEFAULT 1,
        created_at TEXT,
        updated_at TEXT
    );

    -- Tabla de turnos / aperturas y cierres de caja
    CREATE TABLE IF NOT EXISTS shifts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        opened_at TEXT NOT NULL,
        closed_at TEXT,
        status TEXT DEFAULT 'OPEN', -- 'OPEN', 'CLOSED'
        cashier_name TEXT DEFAULT 'Cajero Principal',
        initial_cash_usd REAL DEFAULT 0.0,
        initial_cash_bs REAL DEFAULT 0.0,
        expected_cash_usd REAL DEFAULT 0.0,
        expected_cash_bs REAL DEFAULT 0.0,
        real_cash_usd REAL DEFAULT 0.0,
        real_cash_bs REAL DEFAULT 0.0,
        diff_usd REAL DEFAULT 0.0,
        diff_bs REAL DEFAULT 0.0,
        total_card_bs REAL DEFAULT 0.0,
        total_pago_movil_bs REAL DEFAULT 0.0,
        notes TEXT
    );

    -- Tabla de ventas / facturación
    CREATE TABLE IF NOT EXISTS sales (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        invoice_number TEXT UNIQUE NOT NULL,
        shift_id INTEGER,
        created_at TEXT NOT NULL,
        client_name TEXT DEFAULT 'Consumidor Final',
        client_id_doc TEXT DEFAULT 'V-00000000',
        total_usd REAL NOT NULL,
        total_bs REAL NOT NULL,
        exchange_rate REAL NOT NULL,
        status TEXT DEFAULT 'COMPLETED', -- 'COMPLETED', 'CANCELLED'
        notes TEXT,
        change_usd REAL DEFAULT 0.0,
        change_bs REAL DEFAULT 0.0,
        FOREIGN KEY (shift_id) REFERENCES shifts(id)
    );

    -- Detalle de productos por venta
    CREATE TABLE IF NOT EXISTS sale_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sale_id INTEGER NOT NULL,
        product_id INTEGER,
        product_code TEXT,
        product_name TEXT NOT NULL,
        quantity REAL NOT NULL,
        price_usd REAL NOT NULL,
        price_bs REAL NOT NULL,
        subtotal_usd REAL NOT NULL,
        subtotal_bs REAL NOT NULL,
        FOREIGN KEY (sale_id) REFERENCES sales(id) ON DELETE CASCADE,
        FOREIGN KEY (product_id) REFERENCES products(id)
    );

    -- Pagos recibidos por venta (múltiples formas de pago)
    CREATE TABLE IF NOT EXISTS sale_payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sale_id INTEGER NOT NULL,
        method TEXT NOT NULL, -- 'USD_EFECTIVO', 'BS_EFECTIVO', 'BS_TARJETA', 'BS_PAGO_MOVIL'
        amount REAL NOT NULL,
        currency TEXT NOT NULL, -- 'USD', 'BS'
        amount_usd_equiv REAL NOT NULL,
        amount_bs_equiv REAL NOT NULL,
        reference TEXT, -- Obligatorio para pago móvil, opcional para tarjeta
        created_at TEXT NOT NULL,
        FOREIGN KEY (sale_id) REFERENCES sales(id) ON DELETE CASCADE
    );

    -- Historial de movimientos de caja (ventas, avances de efectivo, ingresos/egresos)
    CREATE TABLE IF NOT EXISTS cash_movements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        shift_id INTEGER,
        sale_id INTEGER,
        type TEXT NOT NULL, -- 'VENTA', 'AVANCE_EFECTIVO', 'INGRESO_MANUAL', 'EGRESO_MANUAL', 'APERTURA', 'CIERRE'
        description TEXT NOT NULL,
        amount_usd REAL DEFAULT 0.0,
        amount_bs REAL DEFAULT 0.0,
        payment_method TEXT, -- 'USD_EFECTIVO', 'BS_EFECTIVO', 'BS_TARJETA', 'BS_PAGO_MOVIL', 'MIXTO'
        reference TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY (shift_id) REFERENCES shifts(id),
        FOREIGN KEY (sale_id) REFERENCES sales(id)
    );
    """)

    # Migración de esquemas existentes si falta la columna unit o vueltos
    try:
        cursor.execute("ALTER TABLE products ADD COLUMN unit TEXT DEFAULT 'UND'")
    except Exception:
        pass  # La columna ya existe

    try:
        cursor.execute("ALTER TABLE sales ADD COLUMN change_usd REAL DEFAULT 0.0")
    except Exception:
        pass

    try:
        cursor.execute("ALTER TABLE sales ADD COLUMN change_bs REAL DEFAULT 0.0")
    except Exception:
        pass
    defaults = [
        ("system_name", "AtlasERP", "Nombre del sistema"),
        ("business_name", "Inversiones Atlas C.A.", "Nombre comercial del negocio"),
        ("business_rif", "J-40912345-6", "RIF del negocio"),
        ("exchange_rate", "911.62", "Tasa activa USD a Bolívares"),
        ("rate_source", "MANUAL", "Fuente de la tasa: MANUAL, OFICIAL, PARALELO"),
        ("rate_updated_at", now_iso(), "Última actualización de la tasa"),
        ("invoice_sequence", "1000", "Secuencia de facturación"),
    ]

    for key, val, desc in defaults:
        cursor.execute("""
            INSERT OR IGNORE INTO settings (key, value, description, updated_at)
            VALUES (?, ?, ?, ?)
        """, (key, val, desc, now_iso()))

    # Comprobar si ya se completó el ciclo inicial de semillas o si está en modo producción
    cursor.execute("SELECT value FROM settings WHERE key = 'demo_seeded'")
    row_demo = cursor.fetchone()
    demo_seeded = (row_demo["value"] == "1") if row_demo else False

    if not demo_seeded:
        # Insertar productos de demostración si la tabla está vacía
        cursor.execute("SELECT COUNT(*) FROM products")
        if cursor.fetchone()[0] == 0:
            seed_products = [
                ("7591001001", "Harina Pan 1kg", "Víveres", 0.95, 1.25, 65.0, 10.0),
                ("7591001002", "Arroz Blanco Mary 1kg", "Víveres", 0.85, 1.15, 50.0, 10.0),
                ("7591001003", "Pasta Primor Espagueti 1kg", "Víveres", 1.10, 1.45, 40.0, 8.0),
                ("7591001004", "Aceite Vegetal Vatel 1L", "Víveres", 2.10, 2.75, 30.0, 5.0),
                ("7591001005", "Azúcar Montalbán 1kg", "Víveres", 0.90, 1.20, 45.0, 10.0),
                ("7591001006", "Café Fama de América 250g", "Bebidas", 1.80, 2.40, 25.0, 5.0),
                ("7591001007", "Leche en Polvo Campestre 900g", "Lácteos", 5.50, 7.20, 18.0, 4.0),
                ("7591001008", "Refresco Coca-Cola 2L", "Bebidas", 1.70, 2.25, 35.0, 6.0),
                ("7591001009", "Margarina Mavesa 500g", "Lácteos", 1.40, 1.85, 28.0, 6.0),
                ("7591001010", "Atún Margarita en Aceite 140g", "Enlatados", 1.20, 1.65, 40.0, 8.0),
            ]
            created = now_iso()
            for code, name, cat, cost, price, stock, min_s in seed_products:
                cursor.execute("""
                    INSERT INTO products (code, name, category, cost_usd, price_usd, stock, min_stock, is_active, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
                """, (code, name, cat, cost, price, stock, min_s, created, created))

        # Asegurar productos de demostración que incluyan venta por kilogramo
        cursor.execute("SELECT COUNT(*) FROM products WHERE unit = 'KG'")
        if cursor.fetchone()[0] == 0:
            kg_products = [
                ("7592002001", "Papas Blancas Lavadas", "Vegetales", "KG", 0.90, 1.40, 45.5, 10.0),
                ("7592002002", "Tomate Perita Maduro", "Vegetales", "KG", 1.10, 1.65, 30.0, 8.0),
                ("7592002003", "Cebolla Morada Nacional", "Vegetales", "KG", 0.95, 1.35, 25.0, 5.0),
                ("7592002004", "Queso Blanco Llanero Duro", "Charcutería", "KG", 3.80, 5.20, 20.0, 4.0),
            ]
            created = now_iso()
            for code, name, cat, unit, cost, price, stock, min_s in kg_products:
                cursor.execute("""
                    INSERT OR IGNORE INTO products (code, name, category, unit, cost_usd, price_usd, stock, min_stock, is_active, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
                """, (code, name, cat, unit, cost, price, stock, min_s, created, created))

        # Registrar que las semillas iniciales ya fueron gestionadas
        cursor.execute("""
            INSERT OR REPLACE INTO settings (key, value, description, updated_at)
            VALUES ('demo_seeded', '1', 'Estado de semillas iniciales cargadas', ?)
        """, (now_iso(),))

    conn.commit()
    conn.close()
