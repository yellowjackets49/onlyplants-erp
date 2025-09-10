import streamlit as st
import pandas as pd
from database.connection import get_connection

def show_dashboard():
    """Display dashboard page"""
    st.subheader("📊 Dashboard")
    
    try:
        supabase = get_connection()
        st.write(f"Connection type: {type(supabase)}")
        
        # Simple test query first
        st.write("Testing connection...")
        response = supabase.table('suppliers').select('*').limit(1).execute()
        st.write(f"Suppliers query successful: {len(response.data) if response.data else 0} records")

        # Test products query  
        response = supabase.table('products').select('*').limit(1).execute()
        st.write(f"Products query successful: {len(response.data) if response.data else 0} records")

        # Get raw materials
        st.write("Getting raw materials...")
        raw_response = supabase.table('products').select('*').eq('product_type', 'raw').execute()
        raw_df = pd.DataFrame(raw_response.data) if raw_response.data else pd.DataFrame()
        st.write(f"Raw materials found: {len(raw_df)}")
        
        # Get finished products
        st.write("Getting finished products...")
        fin_response = supabase.table('products').select('*').eq('product_type', 'finished').execute()
        fin_df = pd.DataFrame(fin_response.data) if fin_response.data else pd.DataFrame()
        st.write(f"Finished products found: {len(fin_df)}")

        # Display inventory sections
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 🧺 Raw Materials Inventory")
            if not raw_df.empty:
                total_raw_items = len(raw_df)
                st.metric("Raw Materials", total_raw_items)
                st.dataframe(raw_df[['name', 'sku']].head(), use_container_width=True)
            else:
                st.info("No raw materials found")
            
        with col2:
            st.markdown("### 🎯 Finished Products Inventory") 
            if not fin_df.empty:
                total_finished_items = len(fin_df)
                st.metric("Finished Products", total_finished_items)
                st.dataframe(fin_df[['name', 'sku']].head(), use_container_width=True)
            else:
                st.info("No finished products found")

        st.success("✅ Dashboard loaded successfully!")
            
    except Exception as e:
        st.error(f"Dashboard error: {str(e)}")
        st.error(f"Error type: {type(e)}")
        import traceback
        st.code(traceback.format_exc())