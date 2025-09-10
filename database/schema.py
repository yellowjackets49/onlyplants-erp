def create_tables(conn):
    """Create all database tables"""
    c = conn.cursor()

    c.execute("""
              CREATE TABLE IF NOT EXISTS suppliers
              (
                  id
                  SERIAL
                  PRIMARY
                  KEY,
                  name
                  TEXT
                  UNIQUE,
                  contact
                  TEXT,
                  phone
                  TEXT,
                  email
                  TEXT,
                  raw_materials
                  TEXT,
                  category_codes
                  TEXT
              )
              """)

    c.execute("""
              CREATE TABLE IF NOT EXISTS products
              (
                  id
                  SERIAL
                  PRIMARY
                  KEY,
                  name
                  TEXT,
                  sku
                  TEXT
                  UNIQUE,
                  product_type
                  TEXT
                  CHECK (
                  product_type
                  IN
              (
                  'raw',
                  'finished'
              )),
                  category TEXT,
                  category_code TEXT,
                  quantity_in_stock BIGINT DEFAULT 0,
                  price_paid NUMERIC DEFAULT 0,
                  price_selling NUMERIC DEFAULT 0,
                  supplier_id INTEGER REFERENCES suppliers
              (
                  id
              )
                  )
              """)

    c.execute("""
              CREATE TABLE IF NOT EXISTS bill_of_materials
              (
                  id
                  SERIAL
                  PRIMARY
                  KEY,
                  finished_product_id
                  INTEGER
                  REFERENCES
                  products
              (
                  id
              ),
                  raw_material_id INTEGER REFERENCES products
              (
                  id
              ),
                  quantity_required NUMERIC,
                  product_name TEXT,
                  product_volume NUMERIC
                  )
              """)

    c.execute("""
              CREATE TABLE IF NOT EXISTS transactions
              (
                  id
                  SERIAL
                  PRIMARY
                  KEY,
                  product_id
                  INTEGER
                  NOT
                  NULL
                  REFERENCES
                  products
              (
                  id
              ),
                  tx_type TEXT CHECK
              (
                  tx_type
                  IN
              (
                  'in',
                  'out'
              )) NOT NULL,
                  quantity NUMERIC NOT NULL,
                  date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  price NUMERIC,
                  notes TEXT
                  )
              """)

    c.execute("""
              CREATE TABLE IF NOT EXISTS sales
              (
                  id
                  SERIAL
                  PRIMARY
                  KEY,
                  invoice_number
                  TEXT
                  UNIQUE,
                  customer_name
                  TEXT
                  NOT
                  NULL,
                  customer_email
                  TEXT,
                  customer_phone
                  TEXT,
                  customer_address
                  TEXT,
                  sale_date
                  TIMESTAMP
                  DEFAULT
                  CURRENT_TIMESTAMP,
                  total_amount
                  NUMERIC
                  NOT
                  NULL,
                  notes
                  TEXT
              )
              """)

    c.execute("""
              CREATE TABLE IF NOT EXISTS sales_items
              (
                  id
                  SERIAL
                  PRIMARY
                  KEY,
                  sale_id
                  INTEGER
                  NOT
                  NULL
                  REFERENCES
                  sales
              (
                  id
              ),
                  product_id INTEGER NOT NULL REFERENCES products
              (
                  id
              ),
                  quantity NUMERIC NOT NULL,
                  unit_price NUMERIC NOT NULL,
                  total_price NUMERIC NOT NULL
                  )
              """)

    c.execute("""
              CREATE TABLE IF NOT EXISTS raw_material_batches
              (
                  id
                  SERIAL
                  PRIMARY
                  KEY,
                  product_id
                  INTEGER
                  NOT
                  NULL
                  REFERENCES
                  products
              (
                  id
              ),
                  batch_number TEXT NOT NULL,
                  quantity_received NUMERIC NOT NULL,
                  quantity_remaining NUMERIC NOT NULL,
                  date_received DATE NOT NULL,
                  expiration_date DATE,
                  barcode TEXT,
                  coa_provided BOOLEAN DEFAULT FALSE,
                  kebs_smark_number TEXT,
                  receiver_name TEXT NOT NULL,
                  supplier_id INTEGER REFERENCES suppliers
              (
                  id
              ),
                  price_per_unit NUMERIC DEFAULT 0,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                  )
              """)

    c.execute("""
              CREATE TABLE IF NOT EXISTS receiving_quality_checks
              (
                  id
                  SERIAL
                  PRIMARY
                  KEY,
                  batch_id
                  INTEGER
                  NOT
                  NULL
                  REFERENCES
                  raw_material_batches
              (
                  id
              ),
                  color TEXT CHECK
              (
                  color
                  IN
              (
                  'acceptable',
                  'not_acceptable',
                  'na'
              )) DEFAULT 'na',
                  packaging TEXT CHECK
              (
                  packaging
                  IN
              (
                  'acceptable',
                  'not_acceptable',
                  'na'
              )) DEFAULT 'na',
                  shelf_life TEXT CHECK
              (
                  shelf_life
                  IN
              (
                  'acceptable',
                  'not_acceptable',
                  'na'
              )) DEFAULT 'na',
                  weight TEXT CHECK
              (
                  weight
                  IN
              (
                  'acceptable',
                  'not_acceptable',
                  'na'
              )) DEFAULT 'na',
                  coa TEXT CHECK
              (
                  coa
                  IN
              (
                  'acceptable',
                  'not_acceptable',
                  'na'
              )) DEFAULT 'na',
                  seal_integrity TEXT CHECK
              (
                  seal_integrity
                  IN
              (
                  'acceptable',
                  'not_acceptable',
                  'na'
              )) DEFAULT 'na',
                  labelling TEXT CHECK
              (
                  labelling
                  IN
              (
                  'acceptable',
                  'not_acceptable',
                  'na'
              )) DEFAULT 'na',
                  storage_conditions TEXT CHECK
              (
                  storage_conditions
                  IN
              (
                  'acceptable',
                  'not_acceptable',
                  'na'
              )) DEFAULT 'na',
                  overall_status TEXT CHECK
              (
                  overall_status
                  IN
              (
                  'accepted',
                  'rejected'
              )) DEFAULT 'accepted',
                  notes TEXT
                  )
              """)

    c.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS bom_unique_pair ON bill_of_materials(finished_product_id, raw_material_id)")
    c.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS batch_product_unique ON raw_material_batches(product_id, batch_number)")
    conn.commit()