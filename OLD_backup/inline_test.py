import streamlit as st
import pandas as pd
import psycopg2
import os


def get_test_connection():
    host = os.getenv("PGHOST", "127.0.0.1")
    database = os.getenv("PGDATABASE", "inventory")
    user = os.getenv("PGUSER", "admin")
    password = os.getenv("PGPASSWORD", "admin")
    port = int(os.getenv("PGPORT", "5432"))
    return psycopg2.connect(host=host, database=database, user=user, password=password, port=port)


def test_dashboard():
    st.write("🔍 Dashboard function called")
    st.subheader("📊 Test Dashboard")
    st.write("✅ Dashboard content")


def test_suppliers():
    st.write("🔍 Suppliers function called")
    st.subheader("🏭 Test Suppliers")
    st.write("✅ Suppliers content")

    try:
        conn = get_test_connection()
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM suppliers")
        count = c.fetchone()[0]
        st.write(f"Found {count} suppliers")

        suppliers = pd.read_sql("SELECT * FROM suppliers LIMIT 5", conn)
        if not suppliers.empty:
            st.dataframe(suppliers)
        else:
            st.info("No suppliers")
    except Exception as e:
        st.error(f"Error: {e}")


def main():
    st.set_page_config(page_title="Test App", layout="wide")
    st.title("🧪 Inline Test App")

    menu = ["Dashboard", "Suppliers"]
    choice = st.sidebar.selectbox("Menu", menu)

    st.write(f"Selected: {choice}")

    # Force output with st.empty()
    placeholder = st.empty()

    with placeholder.container():
        if choice == "Dashboard":
            test_dashboard()
        elif choice == "Suppliers":
            test_suppliers()


if __name__ == "__main__":
    main()