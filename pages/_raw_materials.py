import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from database.connection import get_connection


def show_raw_materials():
    """Display raw materials page"""
    st.subheader("📦 Raw Materials")
    supabase = get_connection()

    try:
        # Get raw materials
        response = supabase.table('products').select('*').eq('product_type', 'raw').execute()
        df = pd.DataFrame(response.data) if response.data else pd.DataFrame()

        if not df.empty:
            # Display summary stats
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Items", len(df))
            with col2:
                total_stock = df['quantity_in_stock'].sum() if 'quantity_in_stock' in df.columns else 0
                st.metric("Total Stock", f"{total_stock:.0f}")
            with col3:
                low_stock = len(df[df['quantity_in_stock'] <= 10]) if 'quantity_in_stock' in df.columns else 0
                st.metric("Low Stock Items", low_stock)

            # Display data
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No raw materials found. Add some raw materials below.")

        # Add new raw material
        st.markdown("### ➕ Add Raw Material")
        with st.form("add_raw_material"):
            col1, col2 = st.columns(2)
            
            with col1:
                name = st.text_input("Material Name")
                sku = st.text_input("SKU")
                category = st.text_input("Category")
                
            with col2:
                category_code = st.text_input("Category Code")
                price_paid = st.number_input("Cost per Unit", min_value=0.0, format="%.2f")
                quantity = st.number_input("Initial Quantity", min_value=0, value=0)

            # Get suppliers
            try:
                suppliers_response = supabase.table('suppliers').select('id, name').execute()
                suppliers_df = pd.DataFrame(suppliers_response.data) if suppliers_response.data else pd.DataFrame()
                supplier_options = ["None"] + suppliers_df["name"].tolist()
            except:
                supplier_options = ["None"]

            supplier = st.selectbox("Supplier", supplier_options)
            notes = st.text_area("Notes")

            submitted = st.form_submit_button("Add Raw Material")

            if submitted and name and sku:
                supplier_id = None
                if supplier != "None" and not suppliers_df.empty:
                    supplier_row = suppliers_df[suppliers_df["name"] == supplier]
                    if not supplier_row.empty:
                        supplier_id = supplier_row.iloc[0]["id"]

                try:
                    data = {
                        "name": name,
                        "sku": sku,
                        "product_type": "raw",
                        "category": category,
                        "category_code": category_code,
                        "price_paid": price_paid,
                        "quantity_in_stock": quantity,
                        "supplier_id": supplier_id,
                        "price_selling": 0,  # Raw materials don't have selling price
                        "notes": notes
                    }
                    result = supabase.table('products').insert(data).execute()
                    st.success(f"✅ Raw material '{name}' added")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error adding raw material: {e}")

        # Show expiring batches section
        show_expiring_batches()

    except Exception as e:
        st.error(f"Raw materials error: {e}")


def get_batch_details(product_id):
    """Get batch details for a product"""
    supabase = get_connection()
    
    try:
        response = supabase.table('batches').select('*').eq('product_id', product_id).execute()
        return pd.DataFrame(response.data) if response.data else pd.DataFrame()
    except Exception as e:
        st.error(f"Error getting batch details: {e}")
        return pd.DataFrame()


def get_all_batch_details():
    """Get all batch details with product information"""
    supabase = get_connection()
    
    try:
        response = supabase.table('batches').select(
            'id, batch_number, quantity, expiry_date, notes, '
            'product:product_id(name, sku)'
        ).execute()
        
        if response.data:
            # Process the data to flatten it
            batch_data = []
            for item in response.data:
                product = item.get('product', {})
                
                batch_data.append({
                    'id': item.get('id'),
                    'batch_number': item.get('batch_number'),
                    'product_name': product.get('name', 'Unknown') if product else 'Unknown',
                    'product_sku': product.get('sku', 'Unknown') if product else 'Unknown',
                    'quantity': item.get('quantity', 0),
                    'expiry_date': item.get('expiry_date'),
                    'notes': item.get('notes', '')
                })
            
            return pd.DataFrame(batch_data)
        else:
            return pd.DataFrame()
            
    except Exception as e:
        st.error(f"Error getting all batch details: {e}")
        return pd.DataFrame()


def show_expiring_batches():
    """Show batches expiring soon"""
    st.markdown("### ⏰ Expiring Batches")
    
    try:
        batches_df = get_all_batch_details()
        
        if not batches_df.empty and 'expiry_date' in batches_df.columns:
            # Convert expiry_date to datetime
            batches_df['expiry_date'] = pd.to_datetime(batches_df['expiry_date'], errors='coerce')
            
            # Filter for batches expiring in next 30 days
            today = datetime.now()
            next_month = today + timedelta(days=30)
            
            expiring_batches = batches_df[
                (batches_df['expiry_date'] >= today) & 
                (batches_df['expiry_date'] <= next_month)
            ]
            
            if not expiring_batches.empty:
                st.warning(f"⚠️ {len(expiring_batches)} batches expiring within 30 days!")
                
                # Add days until expiry
                expiring_batches['days_until_expiry'] = (
                    expiring_batches['expiry_date'] - today
                ).dt.days
                
                # Sort by expiry date
                expiring_batches = expiring_batches.sort_values('expiry_date')
                
                # Display expiring batches
                for _, batch in expiring_batches.iterrows():
                    days_left = batch['days_until_expiry']
                    
                    if days_left <= 7:
                        alert_type = "🔴"
                        color = "red"
                    elif days_left <= 14:
                        alert_type = "🟡"
                        color = "orange"
                    else:
                        alert_type = "🟠"
                        color = "blue"
                    
                    st.markdown(
                        f"{alert_type} **{batch['product_name']}** "
                        f"(Batch: {batch['batch_number']}) - "
                        f"Expires in {days_left} days "
                        f"({batch['expiry_date'].strftime('%Y-%m-%d')})"
                    )
            else:
                st.success("✅ No batches expiring in the next 30 days")
        else:
            st.info("No batch data available")
            
    except Exception as e:
        st.error(f"Error checking expiring batches: {e}")