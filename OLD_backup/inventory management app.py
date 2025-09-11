import streamlit as st
import pandas as pd
import psycopg2
import io
import os
import psycopg2.extras
import numpy as np
from datetime import datetime

# ReportLab imports for PDF generation (with error handling)
REPORTLAB_AVAILABLE = False
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    REPORTLAB_AVAILABLE = True
except ImportError:
    pass

# ---------------- DATABASE CONNECTION ----------------
def get_connection():
    try:
        db_cfg = st.secrets["db"]
    except Exception:
        db_cfg = {}

    host = db_cfg.get("host") or os.getenv("PGHOST", "127.0.0.1")
    database = db_cfg.get("database") or os.getenv("PGDATABASE", "inventory")
    user = db_cfg.get("user") or os.getenv("PGUSER", "admin")
    password = db_cfg.get("password") or os.getenv("PGPASSWORD", "admin")
    port = int(db_cfg.get("port") or os.getenv("PGPORT", "5432"))

    try:
        conn = psycopg2.connect(
            host=host,
            database=database,
            user=user,
            password=password,
            port=port,
        )
        return conn
    except psycopg2.OperationalError as e:
        st.error(f"Could not connect to PostgreSQL: {e}")
        st.stop()

@st.cache_resource(show_spinner=False)
def get_cached_connection():
    return get_connection()

conn = get_cached_connection()
c = conn.cursor()

# ---------------- CREATE TABLES ----------------
def create_tables():
    c.execute("""
    CREATE TABLE IF NOT EXISTS suppliers (
        id SERIAL PRIMARY KEY,
        name TEXT UNIQUE,
        contact TEXT,
        phone TEXT,
        email TEXT,
        raw_materials TEXT,
        category_codes TEXT
    )
    """)
    c.execute("""
    CREATE TABLE IF NOT EXISTS products (
        id SERIAL PRIMARY KEY,
        name TEXT,
        sku TEXT UNIQUE,
        product_type TEXT CHECK(product_type IN ('raw','finished')),
        category TEXT,
        category_code TEXT,
        quantity_in_stock BIGINT DEFAULT 0,
        price_paid NUMERIC DEFAULT 0,
        price_selling NUMERIC DEFAULT 0,
        supplier_id INTEGER REFERENCES suppliers(id)
    )
    """)
    c.execute("""
    CREATE TABLE IF NOT EXISTS bill_of_materials (
        id SERIAL PRIMARY KEY,
        finished_product_id INTEGER REFERENCES products(id),
        raw_material_id INTEGER REFERENCES products(id),
        quantity_required NUMERIC,
        product_name TEXT,
        product_volume NUMERIC
    )
    """)
    c.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
        id SERIAL PRIMARY KEY,
        product_id INTEGER NOT NULL REFERENCES products(id),
        tx_type TEXT CHECK(tx_type IN ('in','out')) NOT NULL,
        quantity NUMERIC NOT NULL,
        date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        price NUMERIC,
        notes TEXT
    )
    """)
    c.execute("""
    CREATE TABLE IF NOT EXISTS sales (
        id SERIAL PRIMARY KEY,
        invoice_number TEXT UNIQUE,
        customer_name TEXT NOT NULL,
        customer_email TEXT,
        customer_phone TEXT,
        customer_address TEXT,
        sale_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        total_amount NUMERIC NOT NULL,
        notes TEXT
    )
    """)
    c.execute("""
    CREATE TABLE IF NOT EXISTS sales_items (
        id SERIAL PRIMARY KEY,
        sale_id INTEGER NOT NULL REFERENCES sales(id),
        product_id INTEGER NOT NULL REFERENCES products(id),
        quantity NUMERIC NOT NULL,
        unit_price NUMERIC NOT NULL,
        total_price NUMERIC NOT NULL
    )
    """)
    c.execute("""
    CREATE TABLE IF NOT EXISTS raw_material_batches (
        id SERIAL PRIMARY KEY,
        product_id INTEGER NOT NULL REFERENCES products(id),
        batch_number TEXT NOT NULL,
        quantity_received NUMERIC NOT NULL,
        quantity_remaining NUMERIC NOT NULL,
        date_received DATE NOT NULL,
        expiration_date DATE,
        barcode TEXT,
        coa_provided BOOLEAN DEFAULT FALSE,
        kebs_smark_number TEXT,
        receiver_name TEXT NOT NULL,
        supplier_id INTEGER REFERENCES suppliers(id),
        price_per_unit NUMERIC DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    c.execute("""
    CREATE TABLE IF NOT EXISTS receiving_quality_checks (
        id SERIAL PRIMARY KEY,
        batch_id INTEGER NOT NULL REFERENCES raw_material_batches(id),
        color TEXT CHECK(color IN ('acceptable','not_acceptable','na')) DEFAULT 'na',
        packaging TEXT CHECK(packaging IN ('acceptable','not_acceptable','na')) DEFAULT 'na',
        shelf_life TEXT CHECK(shelf_life IN ('acceptable','not_acceptable','na')) DEFAULT 'na',
        weight TEXT CHECK(weight IN ('acceptable','not_acceptable','na')) DEFAULT 'na',
        coa TEXT CHECK(coa IN ('acceptable','not_acceptable','na')) DEFAULT 'na',
        seal_integrity TEXT CHECK(seal_integrity IN ('acceptable','not_acceptable','na')) DEFAULT 'na',
        labelling TEXT CHECK(labelling IN ('acceptable','not_acceptable','na')) DEFAULT 'na',
        storage_conditions TEXT CHECK(storage_conditions IN ('acceptable','not_acceptable','na')) DEFAULT 'na',
        overall_status TEXT CHECK(overall_status IN ('accepted','rejected')) DEFAULT 'accepted',
        notes TEXT
    )
    """)
    
    c.execute("CREATE UNIQUE INDEX IF NOT EXISTS bom_unique_pair ON bill_of_materials(finished_product_id, raw_material_id)")
    c.execute("CREATE UNIQUE INDEX IF NOT EXISTS batch_product_unique ON raw_material_batches(product_id, batch_number)")
    conn.commit()

# Call create_tables() right after establishing connection
create_tables()

# ---------------- HELPER FUNCTIONS ----------------
def calculate_product_cost(product_id):
    try:
        df = pd.read_sql("""
            SELECT b.quantity_required, r.price_paid
            FROM bill_of_materials b
            JOIN products r ON b.raw_material_id = r.id
            WHERE b.finished_product_id=%s
        """, conn, params=(product_id,))
        return float((df["quantity_required"] * df["price_paid"]).sum()) if not df.empty else 0
    except Exception:
        return 0

def generate_invoice_number():
    now = datetime.now()
    return f"INV-{now.strftime('%Y%m%d')}-{now.strftime('%H%M%S')}"

def create_pdf_invoice(sale_data, items_data, buffer):
    if not REPORTLAB_AVAILABLE:
        raise ImportError("ReportLab is required for PDF generation")
    
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []
    
    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30,
        textColor=colors.darkblue
    )
    story.append(Paragraph("INVOICE", title_style))
    story.append(Spacer(1, 12))
    
    # Company Info
    company_style = ParagraphStyle(
        'Company',
        parent=styles['Normal'],
        fontSize=12,
        textColor=colors.darkblue
    )
    story.append(Paragraph("<b>Your Company Name</b><br/>123 Business Street<br/>City, State 12345<br/>Phone: (555) 123-4567", company_style))
    story.append(Spacer(1, 20))
    
    # Invoice details
    invoice_data = [
        ['Invoice Number:', sale_data['invoice_number']],
        ['Date:', sale_data['sale_date'].strftime('%Y-%m-%d %H:%M')],
        ['Customer:', sale_data['customer_name']],
        ['Email:', sale_data.get('customer_email', 'N/A')],
        ['Phone:', sale_data.get('customer_phone', 'N/A')],
    ]
    
    invoice_table = Table(invoice_data, colWidths=[1.5*inch, 3*inch])
    invoice_table.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
        ('FONTNAME', (1,0), (1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 10),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(invoice_table)
    story.append(Spacer(1, 20))
    
    # Items table
    items_table_data = [['Product', 'SKU', 'Quantity', 'Unit Price', 'Total']]
    
    for item in items_data:
        items_table_data.append([
            item['product_name'],
            item['product_sku'],
            str(int(item['quantity'])),
            f"${item['unit_price']:.2f}",
            f"${item['total_price']:.2f}"
        ])
    
    # Add total row
    items_table_data.append(['', '', '', 'TOTAL:', f"${sale_data['total_amount']:.2f}"])
    
    items_table = Table(items_table_data, colWidths=[2.5*inch, 1*inch, 1*inch, 1*inch, 1*inch])
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.grey),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 10),
        ('BOTTOMPADDING', (0,0), (-1,0), 12),
        ('BACKGROUND', (0,1), (-1,-2), colors.beige),
        ('BACKGROUND', (0,-1), (-1,-1), colors.lightgrey),
        ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
        ('GRID', (0,0), (-1,-1), 1, colors.black)
    ]))
    story.append(items_table)
    
    if sale_data.get('notes'):
        story.append(Spacer(1, 20))
        story.append(Paragraph(f"<b>Notes:</b> {sale_data['notes']}", styles['Normal']))
    
    doc.build(story)
    return buffer

def download_template(template_type):
    buffer = io.BytesIO()
    if template_type == "Suppliers":
        df = pd.DataFrame([{"Name": "", "Contact": "", "Phone": "", "Email": "", "RawMaterials": "", "CategoryCodes": ""}])
    elif template_type == "RawMaterials":
        df = pd.DataFrame([{"Name": "", "SKU": "", "Category": "", "CategoryCode": "", "Quantity": 0, "PricePaid": 0.0, "Supplier": ""}])
    elif template_type == "Products":
        df = pd.DataFrame([{"Name": "", "SKU": "", "Category": "", "PriceSelling": 0.0, "Supplier": ""}])
    elif template_type == "BOM":
        df = pd.DataFrame([{
            "ProductID": "",
            "ProductName": "",
            "RawMaterialID": "",
            "QuantityRequired": 0,
            "Volume": 0
        }])
    df.to_excel(buffer, index=False, engine="openpyxl")
    buffer.seek(0)
    return buffer

# ---------------- STREAMLIT APP ----------------
st.set_page_config(page_title="Inventory & BOM Management", layout="wide")
st.title("📦 Inventory & BOM Management")

menu = ["Dashboard", "Suppliers", "Raw Materials", "Products", "BOM", "Manufacturing", "Sales", "Receiving", "Uploads"]
choice = st.sidebar.selectbox("Menu", menu)

# ---------- DASHBOARD ----------
if choice == "Dashboard":
    st.subheader("📊 Dashboard")
    try:
        raw_df = pd.read_sql("SELECT * FROM products WHERE product_type='raw'", conn)
        fin_df = pd.read_sql("SELECT * FROM products WHERE product_type='finished'", conn)
        fin_df["Cost"] = fin_df["id"].apply(calculate_product_cost)

        st.markdown("### 🧺 Raw Materials Inventory")
        st.dataframe(raw_df)
        st.markdown("### 🎯 Finished Products Inventory")
        st.dataframe(fin_df)

        col1, col2 = st.columns(2)
        with col1:
            raw_value = (raw_df['quantity_in_stock']*raw_df['price_paid']).sum()
            st.metric("Total Raw Material Value", f"${raw_value:,.2f}")
        with col2:
            st.metric("Total Finished Goods Cost", f"${fin_df['Cost'].sum():,.2f}")
    except Exception as e:
        st.error(f"Dashboard error: {e}")

# ---------- SUPPLIERS ----------
elif choice == "Suppliers":
    st.subheader("🏭 Suppliers")
    try:
        suppliers = pd.read_sql("SELECT * FROM suppliers", conn)
        st.dataframe(suppliers)

        st.markdown("### ➕ Add Supplier")
        with st.form("add_supplier"):
            name = st.text_input("Supplier Name")
            contact = st.text_input("Contact")
            phone = st.text_input("Phone")
            email = st.text_input("Email")
            raw_materials = st.text_area("Raw Materials Supplied")
            category_codes = st.text_input("Category Codes")
            submitted = st.form_submit_button("Add Supplier")
            
            if submitted and name:
                try:
                    c.execute("""
                        INSERT INTO suppliers (name, contact, phone, email, raw_materials, category_codes)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ON CONFLICT (name) DO NOTHING
                    """, (name, contact, phone, email, raw_materials, category_codes))
                    conn.commit()
                    st.success(f"✅ Supplier '{name}' added")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error adding supplier: {e}")
    except Exception as e:
        st.error(f"Suppliers error: {e}")

# ---------- RAW MATERIALS ----------
elif choice == "Raw Materials":
    st.subheader("🧺 Raw Materials Inventory")
    try:
        df = pd.read_sql("SELECT * FROM products WHERE product_type='raw'", conn)
        st.dataframe(df)

        st.markdown("### ➕ Add Raw Material")
        with st.form("add_raw_material"):
            name = st.text_input("Raw Material Name")
            sku = st.text_input("SKU")
            category = st.text_input("Category")
            category_code = st.text_input("Category Code")
            qty = st.number_input("Initial Quantity", min_value=0)
            price_paid = st.number_input("Price Paid", min_value=0.0, format="%.2f")
            
            suppliers_df = pd.read_sql("SELECT id, name FROM suppliers", conn)
            supplier = st.selectbox("Supplier", suppliers_df["name"].tolist() if not suppliers_df.empty else ["None"])
            
            submitted = st.form_submit_button("Add Raw Material")
            
            if submitted and name and sku:
                supplier_id = None
                if supplier != "None":
                    c.execute("SELECT id FROM suppliers WHERE name=%s", (supplier,))
                    result = c.fetchone()
                    if result:
                        supplier_id = result[0]
                        
                try:
                    c.execute("""
                        INSERT INTO products (name, sku, product_type, category, category_code, quantity_in_stock, price_paid, supplier_id)
                        VALUES (%s, %s, 'raw', %s, %s, %s, %s, %s)
                        ON CONFLICT (sku) DO NOTHING
                    """, (name, sku, category, category_code, qty, price_paid, supplier_id))
                    conn.commit()
                    st.success(f"✅ Raw Material '{name}' added")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
    except Exception as e:
        st.error(f"Raw Materials error: {e}")

# ---------- PRODUCTS ----------
elif choice == "Products":
    st.subheader("🏭 Finished Products")
    try:
        df = pd.read_sql("SELECT * FROM products WHERE product_type='finished'", conn)
        df["Cost"] = df["id"].apply(calculate_product_cost)
        st.dataframe(df)

        st.markdown("### ➕ Add Finished Product")
        with st.form("add_product"):
            name = st.text_input("Product Name")
            sku = st.text_input("SKU")
            category = st.text_input("Category")
            price_selling = st.number_input("Selling Price", min_value=0.0, format="%.2f")
            
            suppliers_df = pd.read_sql("SELECT id, name FROM suppliers", conn)
            supplier = st.selectbox("Supplier", suppliers_df["name"].tolist() if not suppliers_df.empty else ["None"])
            
            submitted = st.form_submit_button("Add Product")
            
            if submitted and name and sku:
                supplier_id = None
                if supplier != "None":
                    c.execute("SELECT id FROM suppliers WHERE name=%s", (supplier,))
                    result = c.fetchone()
                    if result:
                        supplier_id = result[0]
                        
                try:
                    c.execute("""
                        INSERT INTO products (name, sku, product_type, category, price_selling, supplier_id)
                        VALUES (%s, %s, 'finished', %s, %s, %s)
                        ON CONFLICT (sku) DO NOTHING
                    """, (name, sku, category, price_selling, supplier_id))
                    conn.commit()
                    st.success(f"✅ Product '{name}' added")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
    except Exception as e:
        st.error(f"Products error: {e}")

# ---------- BOM ----------
elif choice == "BOM":
    st.subheader("🔧 Bill of Materials")
    
    try:
        conn.rollback()
    except Exception:
        pass
    
    st.write("DEBUG: Checking bill_of_materials table...")
    try:
        c.execute("SELECT COUNT(*) FROM bill_of_materials")
        count = c.fetchone()[0]
        st.write(f"Total BOM entries: {count}")
        
        if count > 0:
            c.execute("SELECT * FROM bill_of_materials LIMIT 5")
            raw_boms = c.fetchall()
            st.write("First 5 raw BOM entries:", raw_boms)
    except Exception as e:
        st.error(f"Error checking bill_of_materials table: {e}")
        try:
            conn.rollback()
            create_tables()
            st.success("Created missing tables. Please refresh the page.")
        except Exception as e2:
            st.error(f"Failed to create tables: {e2}")
    
    bom_query = """
    SELECT 
        b.id,
        fp.name as product_name,
        fp.sku as product_sku,
        rm.name as raw_material_name,
        rm.sku as raw_material_sku,
        b.quantity_required,
        b.product_volume
    FROM bill_of_materials b
    LEFT JOIN products fp ON b.finished_product_id = fp.id
    LEFT JOIN products rm ON b.raw_material_id = rm.id
    ORDER BY fp.name, rm.name
    """
    
    try:
        bom_df = pd.read_sql(bom_query, conn)
        st.write(f"Query returned {len(bom_df)} rows")
        if not bom_df.empty:
            st.write("BOM Data:")
            st.dataframe(bom_df)
        else:
            st.info("No BOMs found. Use the Uploads section to import BOM data.")
    except Exception as e:
        st.error(f"Error loading BOMs: {e}")

# ---------- MANUFACTURING ----------
elif choice == "Manufacturing":
    st.subheader("🏭 Manufacturing")
    
    manufacturing_query = """
    SELECT DISTINCT 
        p.id,
        p.name,
        p.sku,
        p.quantity_in_stock as current_stock
    FROM products p
    INNER JOIN bill_of_materials b ON p.id = b.finished_product_id
    WHERE p.product_type = 'finished'
    ORDER BY p.name
    """
    
    try:
        manufactureable_products = pd.read_sql(manufacturing_query, conn)
        
        if manufactureable_products.empty:
            st.warning("No finished products with BOMs found. Upload Products and BOMs first.")
        else:
            st.markdown("### 📋 Available Products for Manufacturing")
            st.dataframe(manufactureable_products)
            
            st.markdown("### 🚀 Production Control")
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                product_options = [f"{row.name} (SKU: {row.sku})" for _, row in manufactureable_products.iterrows()]
                selected_product = st.selectbox("Select Product to Manufacture", product_options)
                
                quantity_to_produce = st.number_input("Quantity to Produce", min_value=1, value=1)
                
                notes = st.text_area("Production Notes (optional)")
            
            with col2:
                st.markdown("### 🎯 Actions")
                
                if st.button("🔍 Check Materials", type="secondary", use_container_width=True):
                    st.session_state.materials_checked = True
                    st.session_state.production_started = False
                    st.session_state.production_ready = False
                
                start_disabled = not st.session_state.get('materials_ok', False)
                if st.button("🚀 Start Production", type="primary", use_container_width=True, disabled=start_disabled):
                    if st.session_state.get('materials_ok', False):
                        st.session_state.production_started = True
                        st.session_state.production_ready = False
                
                finish_disabled = not st.session_state.get('production_started', False)
                if st.button("🏁 Finish Production", type="primary", use_container_width=True, disabled=finish_disabled):
                    if st.session_state.get('production_started', False):
                        st.session_state.finish_production = True
            
            if st.session_state.get('materials_checked', False) and selected_product:
                product_idx = product_options.index(selected_product)
                selected_product_row = manufactureable_products.iloc[product_idx]
                product_id = int(selected_product_row.id)
                product_name = selected_product_row.name
                
                st.markdown(f"### 📊 Material Requirements for {product_name} (Qty: {quantity_to_produce})")
                
                bom_query = """
                SELECT 
                    b.raw_material_id,
                    r.name as raw_material_name,
                    r.sku as raw_material_sku,
                    r.quantity_in_stock as available_stock,
                    b.quantity_required,
                    (b.quantity_required * %s) as total_needed
                FROM bill_of_materials b
                JOIN products r ON b.raw_material_id = r.id
                WHERE b.finished_product_id = %s
                ORDER BY r.name
                """
                
                bom_requirements = pd.read_sql(bom_query, conn, params=(int(quantity_to_produce), int(product_id)))
                
                if not bom_requirements.empty:
                    bom_requirements['sufficient'] = bom_requirements['available_stock'] >= bom_requirements['total_needed']
                    bom_requirements['shortage'] = bom_requirements['total_needed'] - bom_requirements['available_stock']
                    bom_requirements['shortage'] = bom_requirements['shortage'].clip(lower=0)
                    
                    display_cols = ['raw_material_name', 'raw_material_sku', 'available_stock', 'total_needed', 'sufficient', 'shortage']
                    st.dataframe(bom_requirements[display_cols].style.apply(
                        lambda row: ['background-color: lightcoral' if not row['sufficient'] else 'background-color: lightgreen' 
                                    for _ in row], axis=1))
                    
                    can_produce = bom_requirements['sufficient'].all()
                    
                    if can_produce:
                        st.success("✅ All materials available! Ready to start production.")
                        st.session_state.materials_ok = True
                        st.session_state.bom_data = bom_requirements
                        st.session_state.current_product_id = product_id
                        st.session_state.current_product_name = product_name
                        st.session_state.current_quantity = quantity_to_produce
                        st.session_state.current_notes = notes
                    else:
                        st.error("❌ Insufficient materials for production!")
                        st.session_state.materials_ok = False
                        shortages = bom_requirements[~bom_requirements['sufficient']]
                        st.write("**Materials needed:**")
                        for _, row in shortages.iterrows():
                            st.write(f"• {row.raw_material_name}: Need {row.shortage:.2f} more units")
                else:
                    st.error("No BOM found for this product!")
                    st.session_state.materials_ok = False
            
            if st.session_state.get('production_started', False):
                st.info("🔄 Production in progress...")
                st.markdown(f"**Product:** {st.session_state.get('current_product_name', 'N/A')}")
                st.markdown(f"**Quantity:** {st.session_state.get('current_quantity', 0)}")
                st.markdown("**Status:** Raw materials have been reserved. Click 'Finish Production' when ready to complete.")
                
                if 'bom_data' in st.session_state:
                    st.markdown("**Materials to be consumed:**")
                    bom_data = st.session_state.bom_data
                    consumption_display = bom_data[['raw_material_name', 'raw_material_sku', 'total_needed']].copy()
                    consumption_display.columns = ['Material', 'SKU', 'Quantity to Consume']
                    st.dataframe(consumption_display)
            
            if st.session_state.get('finish_production', False):
                st.markdown("### 🏁 Finishing Production")
                
                try:
                    product_id = st.session_state.get('current_product_id')
                    product_name = st.session_state.get('current_product_name')
                    quantity_to_produce = st.session_state.get('current_quantity')
                    notes = st.session_state.get('current_notes', '')
                    bom_requirements = st.session_state.get('bom_data')
                    
                    c.execute("BEGIN")
                    
                    st.info("🔧 Consuming raw materials...")
                    for _, row in bom_requirements.iterrows():
                        new_stock = row.available_stock - row.total_needed
                        c.execute("""
                            UPDATE products 
                            SET quantity_in_stock = %s 
                            WHERE id = %s
                        """, (int(new_stock), int(row.raw_material_id)))
                        
                        try:
                            c.execute("""
                                INSERT INTO transactions (product_id, tx_type, quantity, notes)
                                VALUES (%s, 'out', %s, %s)
                            """, (int(row.raw_material_id), int(row.total_needed), 
                                 f"Manufacturing: {product_name} (Qty: {quantity_to_produce})"))
                        except Exception:
                            pass
                    
                    st.info("📦 Adding finished products to stock...")
                    c.execute("""
                        UPDATE products 
                        SET quantity_in_stock = quantity_in_stock + %s 
                        WHERE id = %s
                    """, (int(quantity_to_produce), int(product_id)))
                    
                    try:
                        c.execute("""
                            INSERT INTO transactions (product_id, tx_type, quantity, notes)
                            VALUES (%s, 'in', %s, %s)
                        """, (int(product_id), int(quantity_to_produce), 
                             f"Manufacturing completed. Notes: {notes}"))
                    except Exception:
                        pass
                    
                    conn.commit()
                    
                    st.success(f"🎉 Successfully produced {quantity_to_produce} units of {product_name}!")
                    st.balloons()
                    
                    st.markdown("### 📦 Updated Inventory")
                    updated_finished = pd.read_sql(
                        "SELECT name, sku, quantity_in_stock FROM products WHERE id = %s", 
                        conn, params=(int(product_id),))
                    st.write("**Finished Product:**")
                    st.dataframe(updated_finished)
                    
                    updated_raw = pd.read_sql("""
                        SELECT name, sku, quantity_in_stock 
                        FROM products 
                        WHERE id IN %s
                    """, conn, params=(tuple(int(x) for x in bom_requirements['raw_material_id'].tolist()),))
                    st.write("**Raw Materials:**")
                    st.dataframe(updated_raw)
                    
                    for key in ['materials_checked', 'materials_ok', 'production_started', 'finish_production', 
                               'bom_data', 'current_product_id', 'current_product_name', 'current_quantity', 'current_notes']:
                        if key in st.session_state:
                            del st.session_state[key]
                    
                except Exception as e:
                    conn.rollback()
                    st.error(f"Production failed: {e}")
                    st.session_state.production_started = False
                    st.session_state.finish_production = False
            
            st.markdown("### 📊 Recent Manufacturing Activity")
            try:
                recent_manufacturing = pd.read_sql("""
                    SELECT 
                        t.date,
                        p.name as product_name,
                        p.sku,
                        t.tx_type,
                        t.quantity,
                        t.notes
                    FROM transactions t
                    JOIN products p ON t.product_id = p.id
                    WHERE t.notes LIKE 'Manufacturing%'
                    ORDER BY t.date DESC
                    LIMIT 20
                """, conn)
                
                if not recent_manufacturing.empty:
                    st.dataframe(recent_manufacturing)
                else:
                    st.info("No manufacturing activity yet.")
            except Exception as e:
                if "does not exist" in str(e):
                    st.info("Transaction logging not yet available. Start a production run to initialize.")
                else:
                    st.error(f"Error loading transactions: {e}")
                    
    except Exception as e:
        st.error(f"Error loading manufactureable products: {e}")
# ---------- SALES ----------
elif choice == "Sales":
    st.subheader("💰 Sales")

    try:
        create_tables()

        finished_products_query = """
                                  SELECT id, name, sku, quantity_in_stock, price_selling
                                  FROM products
                                  WHERE product_type = 'finished' \
                                    AND quantity_in_stock > 0
                                  ORDER BY name \
                                  """

        available_products = pd.read_sql(finished_products_query, conn)

        if available_products.empty:
            st.warning("No finished products available for sale.")
        else:
            st.dataframe(available_products)

            with st.form("sales_form"):
                st.markdown("### Customer & Sale Details")

                col1, col2 = st.columns(2)
                with col1:
                    customer_name = st.text_input("Customer Name")
                    customer_phone = st.text_input("Phone")
                with col2:
                    customer_email = st.text_input("Email")
                    customer_address = st.text_area("Address")

                product_options = [f"{row.name} (SKU: {row.sku})" for _, row in available_products.iterrows()]
                selected_product = st.selectbox("Product", product_options)

                col3, col4 = st.columns(2)
                with col3:
                    quantity = st.number_input("Quantity", min_value=1, value=1)
                with col4:
                    if selected_product:
                        product_idx = product_options.index(selected_product)
                        default_price = float(available_products.iloc[product_idx].price_selling)
                    else:
                        default_price = 0.0
                    unit_price = st.number_input("Unit Price", min_value=0.0, value
