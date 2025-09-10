import streamlit as st
import pandas as pd
from datetime import datetime
from database.connection import get_connection

def show_manufacturing():
    """Display manufacturing page"""
    st.subheader("🏭 Manufacturing")
    supabase = get_connection()

    # Initialize session state
    if 'production_status' not in st.session_state:
        st.session_state.production_status = 'ready'

    try:
        # Get products that have BOMs (can be manufactured)
        bom_response = supabase.table('bill_of_materials').select(
            'finished_product_id, finished_product:finished_product_id(id, name, sku)'
        ).execute()

        if bom_response.data:
            # Get unique products that can be manufactured
            manufacturable_products = []
            product_ids = set()
            
            for item in bom_response.data:
                product = item.get('finished_product', {})
                if product and product.get('id') not in product_ids:
                    manufacturable_products.append({
                        'id': product.get('id'),
                        'name': product.get('name'),
                        'sku': product.get('sku')
                    })
                    product_ids.add(product.get('id'))
            
            manufactureable_products = pd.DataFrame(manufacturable_products)

            if not manufactureable_products.empty:
                # Show current production status
                show_current_production_status()

                st.markdown("### 🎯 Start New Production")
                
                with st.form("manufacturing_form"):
                    # Product selection
                    product_options = [f"{row['name']} ({row['sku']})" for _, row in manufactureable_products.iterrows()]
                    selected_product = st.selectbox("Select Product to Manufacture", product_options)
                    
                    quantity_to_produce = st.number_input("Quantity to Produce", min_value=1, value=1)
                    production_notes = st.text_area("Production Notes")
                    
                    check_materials_btn = st.form_submit_button("🔍 Check Materials")

                if check_materials_btn:
                    handle_check_materials(selected_product, quantity_to_produce, production_notes, 
                                         manufactureable_products, product_options, supabase)

                # Handle production flow based on status
                if st.session_state.production_status == 'materials_checked':
                    handle_start_production(supabase)
                elif st.session_state.production_status == 'in_progress':
                    handle_finish_production(supabase)

            else:
                st.warning("No products found with BOMs. Please create BOMs first.")
        else:
            st.warning("No BOMs found. Please create some BOMs to enable manufacturing.")

        # Show production summary and recent activity
        st.markdown("---")
        show_production_summary(supabase)
        show_recent_manufacturing_activity(supabase)

    except Exception as e:
        st.error(f"Manufacturing error: {e}")


def handle_check_materials(selected_product, quantity_to_produce, production_notes, 
                         manufactureable_products, product_options, supabase):
    """Handle material availability checking"""
    # Get product details
    product_idx = product_options.index(selected_product)
    selected_product_row = manufactureable_products.iloc[product_idx]
    product_id = int(selected_product_row['id'])
    product_name = selected_product_row['name']

    st.markdown(f"### 📊 Material Requirements for {product_name} (Qty: {quantity_to_produce})")

    try:
        # Get BOM requirements
        bom_response = supabase.table('bill_of_materials').select(
            'raw_material_id, quantity_required, '
            'raw_material:raw_material_id(id, name, sku, quantity_in_stock)'
        ).eq('finished_product_id', product_id).execute()

        if bom_response.data:
            # Process BOM data
            bom_requirements = []
            for item in bom_response.data:
                raw_material = item.get('raw_material', {})
                bom_requirements.append({
                    'raw_material_id': item.get('raw_material_id'),
                    'raw_material_name': raw_material.get('name', 'Unknown'),
                    'raw_material_sku': raw_material.get('sku', 'Unknown'),
                    'available_stock': raw_material.get('quantity_in_stock', 0),
                    'quantity_required': item.get('quantity_required', 0),
                    'total_needed': item.get('quantity_required', 0) * quantity_to_produce
                })

            # Display material requirements
            materials_ok = True
            st.markdown("**📋 Material Availability Check:**")

            for req in bom_requirements:
                available = req['available_stock']
                needed = req['total_needed']
                material_name = req['raw_material_name']
                sku = req['raw_material_sku']

                col_mat1, col_mat2, col_mat3, col_mat4 = st.columns([3, 1, 1, 2])

                with col_mat1:
                    st.write(f"**{material_name}** ({sku})")
                with col_mat2:
                    st.write(f"Available: {available:.0f}")
                with col_mat3:
                    st.write(f"Needed: {needed:.0f}")
                with col_mat4:
                    if available >= needed:
                        st.success("✅ OK")
                    else:
                        shortage = needed - available
                        st.error(f"❌ Short: {shortage:.0f}")
                        materials_ok = False

            # Store results in session state
            if materials_ok:
                st.success("🎉 All materials available! Ready to start production.")

                # Store production plan in session state
                st.session_state.production_status = 'materials_checked'
                st.session_state.production_plan = {
                    'product_id': product_id,
                    'product_name': product_name,
                    'quantity': quantity_to_produce,
                    'notes': production_notes,
                    'bom_requirements': bom_requirements
                }
                st.rerun()
            else:
                st.error("❌ Insufficient materials for production.")
                st.session_state.production_status = 'ready'

                # Show shortages
                st.write("**Materials needed:**")
                for req in bom_requirements:
                    if req['available_stock'] < req['total_needed']:
                        shortage = req['total_needed'] - req['available_stock']
                        st.write(f"• {req['raw_material_name']}: Need {shortage:.0f} more units")
        else:
            st.error("No BOM found for this product!")
            st.session_state.production_status = 'ready'

    except Exception as e:
        st.error(f"Error checking BOM: {e}")
        st.session_state.production_status = 'ready'


def handle_start_production(supabase):
    """Handle starting production"""
    if st.button("🚀 Start Production", type="primary"):
        try:
            plan = st.session_state.production_plan

            # Create production order
            production_data = {
                "product_id": plan['product_id'],
                "product_name": plan['product_name'],
                "quantity_planned": plan['quantity'],
                "start_date": datetime.now().isoformat(),
                "status": "in_progress",
                "notes": plan['notes']
            }
            
            result = supabase.table('production_orders').insert(production_data).execute()
            
            if result.data:
                production_order_id = result.data[0]['id']
                
                # Deduct raw materials from inventory
                for req in plan['bom_requirements']:
                    # Update raw material stock
                    new_stock = req['available_stock'] - req['total_needed']
                    supabase.table('products').update({
                        'quantity_in_stock': new_stock
                    }).eq('id', req['raw_material_id']).execute()

                st.session_state.production_status = 'in_progress'
                st.session_state.current_production_order = production_order_id
                st.success("✅ Production started! Materials deducted from inventory.")
                st.rerun()
            
        except Exception as e:
            st.error(f"Error starting production: {e}")


def handle_finish_production(supabase):
    """Handle finishing production"""
    st.info("🔄 Production in progress...")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("✅ Finish Production", type="primary"):
            try:
                plan = st.session_state.production_plan
                production_order_id = st.session_state.current_production_order

                # Update production order
                supabase.table('production_orders').update({
                    "status": "completed",
                    "end_date": datetime.now().isoformat(),
                    "quantity_produced": plan['quantity']
                }).eq('id', production_order_id).execute()

                # Add finished products to inventory
                # First get current stock
                product_response = supabase.table('products').select('quantity_in_stock').eq('id', plan['product_id']).execute()
                current_stock = product_response.data[0]['quantity_in_stock'] if product_response.data else 0
                
                # Update stock
                new_stock = current_stock + plan['quantity']
                supabase.table('products').update({
                    'quantity_in_stock': new_stock
                }).eq('id', plan['product_id']).execute()

                # Clear session state
                st.session_state.production_status = 'ready'
                if 'production_plan' in st.session_state:
                    del st.session_state.production_plan
                if 'current_production_order' in st.session_state:
                    del st.session_state.current_production_order

                st.success(f"🎉 Production completed! {plan['quantity']} units of {plan['product_name']} added to inventory.")
                st.rerun()
                
            except Exception as e:
                st.error(f"Error finishing production: {e}")

    with col2:
        if st.button("❌ Cancel Production"):
            # Reset session state
            st.session_state.production_status = 'ready'
            if 'production_plan' in st.session_state:
                del st.session_state.production_plan
            if 'current_production_order' in st.session_state:
                del st.session_state.current_production_order
            st.rerun()


def show_current_production_status():
    """Show current production status"""
    if st.session_state.production_status != 'ready':
        if st.session_state.production_status == 'materials_checked':
            plan = st.session_state.production_plan
            st.info(f"🎯 Ready to produce {plan['quantity']} units of {plan['product_name']}")
        elif st.session_state.production_status == 'in_progress':
            plan = st.session_state.production_plan
            st.warning(f"🔄 Currently producing {plan['quantity']} units of {plan['product_name']}")


def show_production_summary(supabase):
    """Show production summary"""
    st.markdown("### 📊 Production Summary")
    
    try:
        # Get production orders
        response = supabase.table('production_orders').select('*').execute()
        
        if response.data:
            df = pd.DataFrame(response.data)
            
            col1, col2, col3 = st.columns(3)
            with col1:
                total_orders = len(df)
                st.metric("Total Orders", total_orders)
            with col2:
                completed = len(df[df['status'] == 'completed'])
                st.metric("Completed", completed)
            with col3:
                in_progress = len(df[df['status'] == 'in_progress'])
                st.metric("In Progress", in_progress)
        else:
            st.info("No production orders yet")
            
    except Exception as e:
        st.error(f"Error loading production summary: {e}")


def show_recent_manufacturing_activity(supabase):
    """Show recent manufacturing activity"""
    st.markdown("### 📋 Recent Manufacturing Activity")
    
    try:
        response = supabase.table('production_orders').select('*').order('start_date', desc=True).limit(10).execute()
        
        if response.data:
            df = pd.DataFrame(response.data)
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No manufacturing activity yet")
            
    except Exception as e:
        st.error(f"Error loading manufacturing activity: {e}")