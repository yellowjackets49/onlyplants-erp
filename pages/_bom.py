import streamlit as st
import pandas as pd
from database.connection import get_connection
from database.schema import create_tables


def show_bom():
    """Display BOM page"""
    st.subheader("🔧 Bill of Materials")
    conn = get_connection()
    c = conn.cursor()

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
            create_tables(conn)
            st.success("Created missing tables. Please refresh the page.")
        except Exception as e2:
            st.error(f"Failed to create tables: {e2}")

    bom_query = """
                SELECT b.id, \
                       fp.name as product_name, \
                       fp.sku  as product_sku, \
                       rm.name as raw_material_name, \
                       rm.sku  as raw_material_sku, \
                       b.quantity_required, \
                       b.product_volume
                FROM bill_of_materials b
                         LEFT JOIN products fp ON b.finished_product_id = fp.id
                         LEFT JOIN products rm ON b.raw_material_id = rm.id
                ORDER BY fp.name, rm.name \
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