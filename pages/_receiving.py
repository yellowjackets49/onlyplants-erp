import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from database.connection import get_connection

def show_receiving():
    """Display receiving/inventory page"""
    st.subheader("📦 Receiving & Inventory Management")
    supabase = get_connection()

    # Navigation tabs
    tab1, tab2, tab3 = st.tabs(["📥 Receive Inventory", "📊 Current Stock", "📋 Recent Receipts"])

    with tab1:
        show_receive_inventory_form(supabase)

    with tab2:
        show_current_stock(supabase)

    with tab3:
        show_recent_receipts(supabase)


def show_receive_inventory_form(supabase):
    """Show form for receiving inventory"""
    st.markdown("### 📥 Receive New Inventory")

    try:
        # Get raw materials and products
        products_response = supabase.table('products').select('*').execute()
        products_df = pd.DataFrame(products_response.data) if products_response.data else pd.DataFrame()

        if products_df.empty:
            st.warning("No products found. Please add products first.")
            return

        # Get suppliers
        suppliers_response = supabase.table('suppliers').select('*').execute()
        suppliers_df = pd.DataFrame(suppliers_response.data) if suppliers_response.data else pd.DataFrame()

        with st.form("receive_inventory"):
            col1, col2 = st.columns(2)

            with col1:
                # Product selection
                product_options = [f"{row['name']} ({row['sku']}) - {row['product_type']}" 
                                 for _, row in products_df.iterrows()]
                selected_product = st.selectbox("Select Product", product_options)

                quantity_received = st.number_input("Quantity Received", min_value=0.0, format="%.2f")
                unit_cost = st.number_input("Unit Cost", min_value=0.0, format="%.2f")

            with col2:
                # Supplier selection
                if not suppliers_df.empty:
                    supplier_options = ["None"] + suppliers_df["name"].tolist()
                    selected_supplier = st.selectbox("Supplier", supplier_options)
                else:
                    selected_supplier = "None"

                # Receipt details
                receipt_date = st.date_input("Receipt Date", value=datetime.now().date())
                reference_number = st.text_input("Reference/PO Number")

            # Batch information (for raw materials)
            st.markdown("#### 📦 Batch Information (Optional)")
            col3, col4 = st.columns(2)
            
            with col3:
                batch_number = st.text_input("Batch Number")
                expiry_date = st.date_input("Expiry Date", value=None)
                
            with col4:
                location = st.text_input("Storage Location")
                notes = st.text_area("Notes")

            submitted = st.form_submit_button("📥 Receive Inventory", type="primary")

            if submitted and quantity_received > 0:
                try:
                    # Get selected product details
                    product_idx = product_options.index(selected_product)
                    product = products_df.iloc[product_idx]

                    # Get supplier ID
                    supplier_id = None
                    if selected_supplier != "None" and not suppliers_df.empty:
                        supplier_row = suppliers_df[suppliers_df["name"] == selected_supplier]
                        if not supplier_row.empty:
                            supplier_id = supplier_row.iloc[0]["id"]

                    # Create receipt record
                    receipt_data = {
                        "product_id": product["id"],
                        "product_name": product["name"],
                        "supplier_id": supplier_id,
                        "quantity_received": quantity_received,
                        "unit_cost": unit_cost,
                        "total_cost": quantity_received * unit_cost,
                        "receipt_date": receipt_date.isoformat(),
                        "reference_number": reference_number,
                        "notes": notes
                    }

                    receipt_result = supabase.table('inventory_receipts').insert(receipt_data).execute()

                    if receipt_result.data:
                        receipt_id = receipt_result.data[0]['id']

                        # Update product inventory
                        current_stock = product.get('quantity_in_stock', 0)
                        current_cost = product.get('price_paid', 0)
                        
                        # Calculate weighted average cost
                        if current_stock > 0:
                            total_value = (current_stock * current_cost) + (quantity_received * unit_cost)
                            new_average_cost = total_value / (current_stock + quantity_received)
                        else:
                            new_average_cost = unit_cost

                        new_stock = current_stock + quantity_received

                        # Update product
                        update_data = {
                            'quantity_in_stock': new_stock,
                            'price_paid': new_average_cost
                        }
                        
                        if supplier_id:
                            update_data['supplier_id'] = supplier_id

                        supabase.table('products').update(update_data).eq('id', product['id']).execute()

                        # Create batch record if batch information provided
                        if batch_number or expiry_date:
                            batch_data = {
                                "product_id": product["id"],
                                "batch_number": batch_number or f"BATCH-{receipt_id}",
                                "quantity": quantity_received,
                                "receipt_id": receipt_id,
                                "location": location,
                                "notes": notes
                            }
                            
                            if expiry_date:
                                batch_data["expiry_date"] = expiry_date.isoformat()

                            supabase.table('batches').insert(batch_data).execute()

                        st.success(f"✅ Successfully received {quantity_received} units of {product['name']}")
                        st.success(f"📦 New stock level: {new_stock} units")
                        if batch_number:
                            st.success(f"🏷️ Batch {batch_number} created")

                        st.rerun()

                except Exception as e:
                    st.error(f"Error processing receipt: {e}")

    except Exception as e:
        st.error(f"Error loading receiving form: {e}")


def show_current_stock(supabase):
    """Show current stock levels"""
    st.markdown("### 📊 Current Stock Levels")

    try:
        # Get all products with stock information
        response = supabase.table('products').select('*').execute()
        df = pd.DataFrame(response.data) if response.data else pd.DataFrame()

        if not df.empty:
            # Add stock status
            df['stock_status'] = df.apply(lambda row: 
                '🔴 Out of Stock' if row.get('quantity_in_stock', 0) == 0
                else '🟡 Low Stock' if row.get('quantity_in_stock', 0) <= 10
                else '🟢 In Stock', axis=1
            )

            # Summary metrics
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                total_products = len(df)
                st.metric("Total Products", total_products)
                
            with col2:
                out_of_stock = len(df[df['quantity_in_stock'] == 0])
                st.metric("Out of Stock", out_of_stock)
                
            with col3:
                low_stock = len(df[(df['quantity_in_stock'] > 0) & (df['quantity_in_stock'] <= 10)])
                st.metric("Low Stock", low_stock)
                
            with col4:
                total_value = (df['quantity_in_stock'] * df.get('price_paid', 0)).sum()
                st.metric("Total Inventory Value", f"${total_value:.2f}")

            # Filter options
            col_filter1, col_filter2, col_filter3 = st.columns(3)
            
            with col_filter1:
                product_type_filter = st.selectbox("Product Type", 
                                                 ["All"] + list(df['product_type'].unique()))
            
            with col_filter2:
                stock_status_filter = st.selectbox("Stock Status", 
                                                 ["All", "In Stock", "Low Stock", "Out of Stock"])
                                                 
            with col_filter3:
                category_filter = st.selectbox("Category", 
                                             ["All"] + list(df['category'].dropna().unique()))

            # Apply filters
            filtered_df = df.copy()
            
            if product_type_filter != "All":
                filtered_df = filtered_df[filtered_df['product_type'] == product_type_filter]
                
            if stock_status_filter != "All":
                if stock_status_filter == "Out of Stock":
                    filtered_df = filtered_df[filtered_df['quantity_in_stock'] == 0]
                elif stock_status_filter == "Low Stock":
                    filtered_df = filtered_df[(filtered_df['quantity_in_stock'] > 0) & 
                                            (filtered_df['quantity_in_stock'] <= 10)]
                elif stock_status_filter == "In Stock":
                    filtered_df = filtered_df[filtered_df['quantity_in_stock'] > 10]
                    
            if category_filter != "All":
                filtered_df = filtered_df[filtered_df['category'] == category_filter]

            # Display filtered results
            if not filtered_df.empty:
                # Select columns to display
                display_columns = ['name', 'sku', 'product_type', 'category', 'quantity_in_stock', 
                                 'price_paid', 'stock_status']
                display_df = filtered_df[display_columns]
                
                st.dataframe(display_df, use_container_width=True)
                
                # Export option
                csv = display_df.to_csv(index=False)
                st.download_button(
                    label="📥 Export to CSV",
                    data=csv,
                    file_name=f"inventory_report_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv"
                )
            else:
                st.info("No products match the selected filters.")
        else:
            st.info("No products found.")

    except Exception as e:
        st.error(f"Error loading stock information: {e}")


def show_recent_receipts(supabase):
    """Show recent inventory receipts"""
    st.markdown("### 📋 Recent Receipts")

    try:
        # Get recent receipts
        response = supabase.table('inventory_receipts').select('*').order('receipt_date', desc=True).limit(20).execute()
        
        if response.data:
            df = pd.DataFrame(response.data)
            
            # Format dates and currency
            df['receipt_date'] = pd.to_datetime(df['receipt_date']).dt.strftime('%Y-%m-%d')
            df['total_cost'] = df['total_cost'].apply(lambda x: f"${x:.2f}")
            df['unit_cost'] = df['unit_cost'].apply(lambda x: f"${x:.2f}")
            
            # Select and rename columns for display
            display_columns = {
                'receipt_date': 'Date',
                'product_name': 'Product',
                'quantity_received': 'Quantity',
                'unit_cost': 'Unit Cost',
                'total_cost': 'Total Cost',
                'reference_number': 'Reference'
            }
            
            display_df = df.rename(columns=display_columns)[list(display_columns.values())]
            st.dataframe(display_df, use_container_width=True)
            
            # Summary for recent receipts
            total_receipts = len(df)
            total_value = df['quantity_received'].sum() if 'quantity_received' in df.columns else 0
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Recent Receipts", total_receipts)
            with col2:
                st.metric("Total Quantity Received", f"{total_value:.0f}")
                
        else:
            st.info("No receipts recorded yet")

    except Exception as e:
        st.error(f"Error loading recent receipts: {e}")