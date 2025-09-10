import streamlit as st
import pandas as pd
from database.connection import get_connection
from utils.helpers import calculate_product_cost

def show_dashboard():
    """Display dashboard page"""
    st.subheader("📊 Dashboard")
    supabase = get_connection()

    try:
        # Get raw materials
        raw_response = supabase.table('products').select('*').eq('product_type', 'raw').execute()
        raw_df = pd.DataFrame(raw_response.data) if raw_response.data else pd.DataFrame()
        
        # Get finished products
        fin_response = supabase.table('products').select('*').eq('product_type', 'finished').execute()
        fin_df = pd.DataFrame(fin_response.data) if fin_response.data else pd.DataFrame()
        
        if not fin_df.empty:
            fin_df["Cost"] = fin_df["id"].apply(calculate_product_cost)

        st.markdown("### 🧺 Raw Materials Inventory")
        if not raw_df.empty:
            st.dataframe(raw_df)
        else:
            st.info("No raw materials found")
            
        st.markdown("### 🎯 Finished Products Inventory")
        if not fin_df.empty:
            st.dataframe(fin_df)
        else:
            st.info("No finished products found")

        col1, col2 = st.columns(2)
        with col1:
            if not raw_df.empty and 'quantity_in_stock' in raw_df.columns and 'price_paid' in raw_df.columns:
                raw_value = (raw_df['quantity_in_stock'] * raw_df['price_paid']).sum()
                st.metric("Total Raw Material Value", f"${raw_value:,.2f}")
            else:
                st.metric("Total Raw Material Value", "$0.00")
                
        with col2:
            if not fin_df.empty and 'Cost' in fin_df.columns:
                st.metric("Total Finished Goods Cost", f"${fin_df['Cost'].sum():,.2f}")
            else:
                st.metric("Total Finished Goods Cost", "$0.00")
                
    except Exception as e:
        st.error(f"Dashboard error: {e}")