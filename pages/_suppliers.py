import streamlit as st
import pandas as pd
from database.connection import get_connection

def show_suppliers():
    """Display suppliers page - UPDATED VERSION"""
    st.subheader("🏭 Suppliers")
    
    # Debug info to confirm we're using the right version
    st.write("DEBUG: Using Supabase version of suppliers page")
    
    try:
        supabase = get_connection()
        st.write(f"DEBUG: Connection type: {type(supabase)}")
        
        # Get all suppliers
        response = supabase.table('suppliers').select('*').execute()
        suppliers = pd.DataFrame(response.data) if response.data else pd.DataFrame()

        if not suppliers.empty:
            st.dataframe(suppliers)
        else:
            st.info("No suppliers found. Add some suppliers below.")

        st.markdown("### ➕ Add Supplier")
        with st.form("add_supplier"):
            name = st.text_input("Supplier Name")
            contact = st.text_input("Contact Person")
            phone = st.text_input("Phone")
            email = st.text_input("Email")
            raw_materials = st.text_area("Raw Materials Supplied")
            category_codes = st.text_input("Category Codes")

            submitted = st.form_submit_button("Add Supplier")

            if submitted and name:
                try:
                    data = {
                        "name": name,
                        "contact": contact,
                        "phone": phone,
                        "email": email,
                        "raw_materials": raw_materials,
                        "category_codes": category_codes
                    }
                    result = supabase.table('suppliers').insert(data).execute()
                    st.success(f"✅ Supplier '{name}' added")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error adding supplier: {e}")

    except Exception as e:
        st.error(f"❌ Error in suppliers: {e}")
        import traceback
        st.code(traceback.format_exc())