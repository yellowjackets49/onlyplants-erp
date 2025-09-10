import streamlit as st
import pandas as pd
from database.connection import get_connection

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
        
        # Calculate costs for finished products
        if not fin_df.empty:
            fin_df["Cost"] = fin_df["id"].apply(lambda pid: calculate_product_cost_local(pid, supabase))

        # Display inventory sections
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 🧺 Raw Materials Inventory")
            if not raw_df.empty:
                # Summary stats for raw materials
                total_raw_items = len(raw_df)
                low_stock_raw = len(raw_df[raw_df.get('quantity_in_stock', 0) <= 10])
                
                col1a, col1b = st.columns(2)
                with col1a:
                    st.metric("Raw Materials", total_raw_items)
                with col1b:
                    st.metric("Low Stock", low_stock_raw)
                
                # Display raw materials table
                display_raw = raw_df[['name', 'sku', 'category', 'quantity_in_stock', 'price_paid']].copy()
                st.dataframe(display_raw, use_container_width=True)
            else:
                st.info("No raw materials found")
            
        with col2:
            st.markdown("### 🎯 Finished Products Inventory")
            if not fin_df.empty:
                # Summary stats for finished products
                total_finished_items = len(fin_df)
                low_stock_finished = len(fin_df[fin_df.get('quantity_in_stock', 0) <= 10])
                
                col2a, col2b = st.columns(2)
                with col2a:
                    st.metric("Finished Products", total_finished_items)
                with col2b:
                    st.metric("Low Stock", low_stock_finished)
                
                # Display finished products table
                display_finished = fin_df[['name', 'sku', 'quantity_in_stock', 'price_selling', 'Cost']].copy()
                st.dataframe(display_finished, use_container_width=True)
            else:
                st.info("No finished products found")

        # Overall metrics
        st.markdown("### 📈 Summary Metrics")
        col3, col4, col5, col6 = st.columns(4)
        
        with col3:
            if not raw_df.empty and 'quantity_in_stock' in raw_df.columns and 'price_paid' in raw_df.columns:
                raw_value = (raw_df['quantity_in_stock'] * raw_df['price_paid']).sum()
                st.metric("Raw Material Value", f"${raw_value:,.2f}")
            else:
                st.metric("Raw Material Value", "$0.00")
                
        with col4:
            if not fin_df.empty and 'Cost' in fin_df.columns:
                finished_cost = fin_df['Cost'].sum()
                st.metric("Finished Goods Cost", f"${finished_cost:,.2f}")
            else:
                st.metric("Finished Goods Cost", "$0.00")
        
        with col5:
            # Get recent sales
            try:
                sales_response = supabase.table('sales').select('total_amount').execute()
                if sales_response.data:
                    total_sales = sum(sale['total_amount'] for sale in sales_response.data)
                    st.metric("Total Sales", f"${total_sales:,.2f}")
                else:
                    st.metric("Total Sales", "$0.00")
            except:
                st.metric("Total Sales", "$0.00")
        
        with col6:
            # Get suppliers count
            try:
                suppliers_response = supabase.table('suppliers').select('id').execute()
                supplier_count = len(suppliers_response.data) if suppliers_response.data else 0
                st.metric("Suppliers", supplier_count)
            except:
                st.metric("Suppliers", "0")

        # Recent activity section
        st.markdown("### 📋 Recent Activity")
        
        col7, col8 = st.columns(2)
        
        with col7:
            # Show recent sales
            try:
                recent_sales = supabase.table('sales').select('*').order('sale_date', desc=True).limit(5).execute()
                if recent_sales.data:
                    st.markdown("**💰 Recent Sales:**")
                    for sale in recent_sales.data:
                        customer = sale.get('customer_name', 'Unknown')
                        amount = sale.get('total_amount', 0)
                        date = sale.get('sale_date', '')[:10]
                        st.write(f"• {customer} - ${amount:.2f} ({date})")
                else:
                    st.info("No recent sales")
            except:
                st.info("No sales data available")
        
        with col8:
            # Show recent production
            try:
                recent_production = supabase.table('production_orders').select('*').order('start_date', desc=True).limit(5).execute()
                if recent_production.data:
                    st.markdown("**🏭 Recent Production:**")
                    for order in recent_production.data:
                        product = order.get('product_name', 'Unknown')
                        quantity = order.get('quantity_planned', 0)
                        status = order.get('status', 'unknown')
                        status_emoji = "✅" if status == "completed" else "🔄" if status == "in_progress" else "📋"
                        st.write(f"• {status_emoji} {product} (Qty: {quantity})")
                else:
                    st.info("No recent production")
            except:
                st.info("No production data available")

        # Alerts and warnings section
        st.markdown("### ⚠️ Alerts & Warnings")
        
        alerts = []
        
        # Check for low stock items
        if not raw_df.empty:
            low_raw = raw_df[raw_df['quantity_in_stock'] <= 10]
            if not low_raw.empty:
                alerts.append(f"🔴 {len(low_raw)} raw materials are low in stock")
        
        if not fin_df.empty:
            low_finished = fin_df[fin_df['quantity_in_stock'] <= 10]
            if not low_finished.empty:
                alerts.append(f"🔴 {len(low_finished)} finished products are low in stock")
        
        # Check for items with no stock
        if not raw_df.empty:
            out_raw = raw_df[raw_df['quantity_in_stock'] == 0]
            if not out_raw.empty:
                alerts.append(f"❌ {len(out_raw)} raw materials are out of stock")
        
        if not fin_df.empty:
            out_finished = fin_df[fin_df['quantity_in_stock'] == 0]
            if not out_finished.empty:
                alerts.append(f"❌ {len(out_finished)} finished products are out of stock")
        
        # Display alerts
        if alerts:
            for alert in alerts:
                st.warning(alert)
        else:
            st.success("✅ No critical alerts at this time")
            
    except Exception as e:
        st.error(f"Dashboard error: {e}")


def calculate_product_cost_local(product_id, supabase):
    """Calculate cost of finished product based on BOM (local version)"""
    try:
        # Get BOM data with raw material prices
        bom_response = supabase.table('bill_of_materials').select(
            'quantity_required, raw_material:raw_material_id(price_paid)'
        ).eq('finished_product_id', product_id).execute()
        
        if not bom_response.data:
            return 0
            
        total_cost = 0
        for item in bom_response.data:
            quantity = item.get('quantity_required', 0)
            raw_material = item.get('raw_material', {})
            price = raw_material.get('price_paid', 0) if raw_material else 0
            total_cost += quantity * price
            
        return float(total_cost)
    except Exception as e:
        return 0