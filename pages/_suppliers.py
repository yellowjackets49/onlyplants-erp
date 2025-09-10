import streamlit as st

def show_suppliers():
    """Display suppliers page"""
    st.write("🔍 Suppliers function started")
    st.subheader("🏭 Suppliers")
    st.write("✅ Basic content displayed")

    try:
        import pandas as pd
        st.write("✅ Pandas import successful")

        from database.connection import get_connection
        st.write("✅ Database connection import successful")

        conn = get_connection()
        st.write("✅ Database connection established")

        c = conn.cursor()
        st.write("✅ Database cursor created")

        # Test simple query
        c.execute("SELECT COUNT(*) FROM suppliers")
        count = c.fetchone()[0]
        st.write(f"✅ Query successful - {count} suppliers found")

        # Test pandas query
        suppliers = pd.read_sql("SELECT * FROM suppliers", conn)
        st.write(f"✅ Pandas query successful - {len(suppliers)} rows")

        if not suppliers.empty:
            st.dataframe(suppliers)
        else:
            st.info("No suppliers found")

        st.write("✅ Suppliers function completed successfully")

    except Exception as e:
        st.error(f"❌ Error in suppliers: {e}")
        import traceback
        st.code(traceback.format_exc())