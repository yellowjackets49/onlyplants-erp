import streamlit as st
import pandas as pd
from database.connection import get_connection


def show_products():
    """Display products page"""
    st.subheader("🏭 Finished Products")
    conn = get_connection()
    c = conn.cursor()

    try:
        df = pd.read_sql("SELECT * FROM products WHERE product_type='finished'", conn)

        # Try to calculate costs, but don't fail if utils.helpers isn't available
        try:
            from utils.helpers import calculate_product_cost
            df["Cost"] = df["id"].apply(calculate_product_cost)
        except ImportError:
            st.info("Cost calculation not available - utils.helpers module not found")

        if not df.empty:
            st.dataframe(df)
        else:
            st.info("No finished products found. Add some products below.")

        st.markdown("### ➕ Add Finished Product")
        with st.form("add_product"):
            name = st.text_input("Product Name")
            sku = st.text_input("SKU")
            category = st.text_input("Category")
            price_selling = st.number_input("Selling Price", min_value=0.0, format="%.2f")

            # Get suppliers
            try:
                suppliers_df = pd.read_sql("SELECT id, name FROM suppliers", conn)
                supplier_options = ["None"] + suppliers_df["name"].tolist()
            except:
                supplier_options = ["None"]

            supplier = st.selectbox("Supplier", supplier_options)

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
                              VALUES (%s, %s, 'finished', %s, %s, %s) ON CONFLICT (sku) DO NOTHING
                              """, (name, sku, category, price_selling, supplier_id))
                    conn.commit()
                    st.success(f"✅ Product '{name}' added")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
    except Exception as e:
        st.error(f"Products error: {e}")