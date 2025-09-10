import streamlit as st
import pandas as pd
from database.connection import get_connection


def show_products():
    """Display products page"""
    st.subheader("🏭 Finished Products")
    supabase = get_connection()

    try:
        # Get finished products
        response = supabase.table('products').select('*').eq('product_type', 'finished').execute()
        df = pd.DataFrame(response.data) if response.data else pd.DataFrame()

        # Try to calculate costs
        try:
            from utils.helpers import calculate_product_cost
            if not df.empty:
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
            category_code = st.text_input("Category Code")
            price_selling = st.number_input("Selling Price", min_value=0.0, format="%.2f")

            # Get suppliers
            try:
                suppliers_response = supabase.table('suppliers').select('id, name').execute()
                suppliers_df = pd.DataFrame(suppliers_response.data) if suppliers_response.data else pd.DataFrame()
                supplier_options = ["None"] + suppliers_df["name"].tolist()
            except:
                supplier_options = ["None"]

            supplier = st.selectbox("Supplier", supplier_options)

            submitted = st.form_submit_button("Add Product")

            if submitted and name and sku:
                supplier_id = None
                if supplier != "None":
                    supplier_row = suppliers_df[suppliers_df["name"] == supplier]
                    if not supplier_row.empty:
                        supplier_id = supplier_row.iloc[0]["id"]

                try:
                    data = {
                        "name": name,
                        "sku": sku,
                        "product_type": "finished",
                        "category": category,
                        "category_code": category_code,
                        "price_selling": price_selling,
                        "supplier_id": supplier_id,
                        "quantity_in_stock": 0,
                        "price_paid": 0
                    }
                    result = supabase.table('products').insert(data).execute()
                    st.success(f"✅ Product '{name}' added")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error adding product: {e}")
                    
    except Exception as e:
        st.error(f"Products error: {e}")