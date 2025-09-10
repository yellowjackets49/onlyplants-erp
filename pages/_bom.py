import streamlit as st
import pandas as pd
from database.connection import get_connection

def show_bom():
    """Display BOM page"""
    st.subheader("🔧 Bill of Materials")
    supabase = get_connection()

    try:
        # Get BOM data with product information
        bom_response = supabase.table('bill_of_materials').select(
            'id, quantity_required, product_volume, '
            'finished_product:finished_product_id(name, sku), '
            'raw_material:raw_material_id(name, sku)'
        ).execute()

        if bom_response.data:
            # Process the data to flatten it
            bom_data = []
            for item in bom_response.data:
                finished_product = item.get('finished_product', {})
                raw_material = item.get('raw_material', {})
                
                bom_data.append({
                    'id': item.get('id'),
                    'product_name': finished_product.get('name', 'Unknown') if finished_product else 'Unknown',
                    'product_sku': finished_product.get('sku', 'Unknown') if finished_product else 'Unknown',
                    'raw_material_name': raw_material.get('name', 'Unknown') if raw_material else 'Unknown',
                    'raw_material_sku': raw_material.get('sku', 'Unknown') if raw_material else 'Unknown',
                    'quantity_required': item.get('quantity_required', 0),
                    'product_volume': item.get('product_volume', 0)
                })
            
            bom_df = pd.DataFrame(bom_data)
            st.write(f"Found {len(bom_df)} BOM entries")
            st.dataframe(bom_df)
        else:
            st.info("No BOMs found. Add BOM entries below.")

        # Add new BOM entry
        st.markdown("### ➕ Add BOM Entry")
        with st.form("add_bom"):
            # Get finished products
            finished_response = supabase.table('products').select('id, name, sku').eq('product_type', 'finished').execute()
            finished_products = pd.DataFrame(finished_response.data) if finished_response.data else pd.DataFrame()
            
            # Get raw materials
            raw_response = supabase.table('products').select('id, name, sku').eq('product_type', 'raw').execute()
            raw_materials = pd.DataFrame(raw_response.data) if raw_response.data else pd.DataFrame()

            if not finished_products.empty and not raw_materials.empty:
                finished_options = [f"{row['name']} ({row['sku']})" for _, row in finished_products.iterrows()]
                raw_options = [f"{row['name']} ({row['sku']})" for _, row in raw_materials.iterrows()]

                selected_finished = st.selectbox("Finished Product", finished_options)
                selected_raw = st.selectbox("Raw Material", raw_options)
                quantity_required = st.number_input("Quantity Required", min_value=0.0, format="%.4f")
                product_volume = st.number_input("Product Volume", min_value=0.0, format="%.4f")

                submitted = st.form_submit_button("Add BOM Entry")

                if submitted:
                    try:
                        # Get IDs from selected options
                        finished_id = finished_products.iloc[finished_options.index(selected_finished)]['id']
                        raw_id = raw_materials.iloc[raw_options.index(selected_raw)]['id']

                        data = {
                            "finished_product_id": finished_id,
                            "raw_material_id": raw_id,
                            "quantity_required": quantity_required,
                            "product_volume": product_volume,
                            "product_name": selected_finished.split(' (')[0]
                        }
                        
                        result = supabase.table('bill_of_materials').insert(data).execute()
                        st.success("✅ BOM entry added")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error adding BOM entry: {e}")
            else:
                st.warning("Please add finished products and raw materials before creating BOMs.")

    except Exception as e:
        st.error(f"Error loading BOMs: {e}")