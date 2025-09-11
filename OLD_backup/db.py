import sqlite3

DB_FILE = "inventory.db"

def get_connection():
    return sqlite3.connect(DB_FILE, check_same_thread=False)

def init_db():
    conn = get_connection()
    cur = conn.cursor()

    # suppliers
    cur.execute("""
    CREATE TABLE IF NOT EXISTS suppliers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        contact_name TEXT,
        phone TEXT,
        email TEXT,
        address TEXT
    )
    """)

    # products (using product_type instead of type)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        sku TEXT UNIQUE,
        category TEXT,
        supplier_id INTEGER,
        product_type TEXT CHECK(product_type IN ('raw','finished')) DEFAULT 'raw',
        quantity_in_stock INTEGER DEFAULT 0,
        reorder_level INTEGER DEFAULT 0,
        price_paid REAL,
        price_selling REAL,
        FOREIGN KEY (supplier_id) REFERENCES suppliers (id)
    )
    """)

    # transactions
    cur.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER NOT NULL,
        tx_type TEXT CHECK(tx_type IN ('in','out')) NOT NULL,
        quantity INTEGER NOT NULL,
        date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        price REAL,
        notes TEXT,
        FOREIGN KEY (product_id) REFERENCES products (id)
    )
    """)

    # bills of materials (BOM)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS bill_of_materials (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        finished_product_id INTEGER NOT NULL,
        raw_material_id INTEGER NOT NULL,
        quantity_required REAL NOT NULL,
        FOREIGN KEY (finished_product_id) REFERENCES products (id),
        FOREIGN KEY (raw_material_id) REFERENCES products (id)
    )
    """)

    # work orders
    cur.execute("""
    CREATE TABLE IF NOT EXISTS work_orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        finished_product_id INTEGER NOT NULL,
        quantity_to_produce INTEGER NOT NULL,
        status TEXT CHECK(status IN ('planned','in_progress','completed')) DEFAULT 'planned',
        start_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        end_date TIMESTAMP,
        FOREIGN KEY (finished_product_id) REFERENCES products (id)
    )
    """)

    # work order consumption
    cur.execute("""
    CREATE TABLE IF NOT EXISTS work_order_consumption (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        work_order_id INTEGER NOT NULL,
        raw_material_id INTEGER NOT NULL,
        quantity_consumed REAL NOT NULL,
        FOREIGN KEY (work_order_id) REFERENCES work_orders (id),
        FOREIGN KEY (raw_material_id) REFERENCES products (id)
    )
    """)

    conn.commit()
    conn.close()
