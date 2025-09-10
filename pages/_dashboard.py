import streamlit as st
import pandas as pd
from database.connection import get_connection
from utils.helpers import calculate_product_cost

def show_dashboard():
    """Display dashboard page"""
    st.subheader("📊 Dashboard")
    conn = get_connection()

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
            raw_value = (raw_df['quantity_in_stock'] * raw_df['price_paid']).sum()
            st.metric("Total Raw Material Value", f"${raw_value:,.2f}")
        with col2:
            st.metric("Total Finished Goods Cost", f"${fin_df['Cost'].sum():,.2f}")
    except Exception as e:
        st.error(f"Dashboard error: {e}")