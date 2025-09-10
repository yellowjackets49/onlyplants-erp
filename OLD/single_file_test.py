import streamlit as st
import pandas as pd
import psycopg2
import os


# Database connection (inline)
@st.cache_resource
def get_db_connection():
    try:
        db_cfg = st.secrets.get("db", {})
    except:
        db_cfg = {}

    host = db_cfg.get("host", os.getenv("PGHOST", "127.0.0.1"))
    database = db_cfg.get("database", os.getenv("PGDATABASE", "inventory"))
    user = db_cfg.get("user", os.getenv("PGUSER", "admin"))
    password = db_cfg.get("password", os.getenv("PGPASSWORD", "admin"))
    port = int(db_cfg.get("port", os.getenv("PGPORT", "5432")))

    return psycopg2.connect(host=host, database=database, user=user, password=password, port=port)


# Dashboard function (inline)
def show_dashboard_inline():
    st.subheader("📊 Dashboard (Inline)")
    try:
        conn = get_db_connection()
        raw_df = pd.read_sql("SELECT * FROM products WHERE product_type='raw' LIMIT 10", conn)
        st.success("✅ Dashboard loaded successfully!")
        st.write(f"Found {len(raw_df)} raw materials")
        if not raw_df.empty:
            st.dataframe(raw_df.head())
    except Exception as e:
        st.error(f"Dashboard error: {e}")


# Suppliers function (inline)
def show_suppliers_inline():
    st.subheader("🏭 Suppliers (Inline)")
    st.success("✅ Suppliers loaded successfully!")

    try:
        conn = get_db_connection()
        suppliers_df = pd.read_sql("SELECT * FROM suppliers LIMIT 10", conn)
        st.write(f"Found {len(suppliers_df)} suppliers")
        if not suppliers_df.empty:
            st.dataframe(suppliers_df)
        else:
            st.info("No suppliers found")

        # Simple form
        with st.form("add_supplier_inline"):
            name = st.text_input("Supplier Name")
            if st.form_submit_button("Add"):
                if name:
                    st.success(f"Would add supplier: {name}")

    except Exception as e:
        st.error(f"Suppliers error: {e}")


def main():
    st.set_page_config(page_title="Single File Test", layout="wide")
    st.title("📦 Single File Test")

    menu = ["Dashboard", "Suppliers", "Test"]
    choice = st.sidebar.selectbox("Menu", menu)

    st.write(f"Selected: {choice}")

    if choice == "Dashboard":
        show_dashboard_inline()
    elif choice == "Suppliers":
        show_suppliers_inline()
    elif choice == "Test":
        st.subheader("🧪 Test Page")
        st.write("This is a test page")
        st.success("Test page working!")


if __name__ == "__main__":
    main()