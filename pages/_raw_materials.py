import streamlit as st
import pandas as pd
from database.connection import get_connection


def show_raw_materials():
    """Display raw materials inventory with expandable batch details"""
    st.subheader("🧺 Raw Materials Inventory")
    st.info(
        "📝 **Note**: Raw material quantities are managed through the Receiving module. This page is for viewing inventory only.")

    conn = get_connection()
    c = conn.cursor()

    try:
        # Main inventory view with batch counts
        df = pd.read_sql("""
                         SELECT p.id,
                                p.name,
                                p.sku,
                                p.category,
                                p.category_code,
                                p.quantity_in_stock,
                                p.price_paid,
                                s.name                                               as supplier_name,
                                ROUND(p.quantity_in_stock * p.price_paid, 2)         as total_value,
                                COUNT(b.id)                                          as batch_count,
                                COUNT(CASE WHEN b.quantity_remaining > 0 THEN 1 END) as active_batches
                         FROM products p
                                  LEFT JOIN suppliers s ON p.supplier_id = s.id
                                  LEFT JOIN raw_material_batches b ON p.id = b.product_id
                         WHERE p.product_type = 'raw'
                         GROUP BY p.id, p.name, p.sku, p.category, p.category_code, p.quantity_in_stock, p.price_paid,
                                  s.name
                         ORDER BY p.name
                         """, conn)

        if not df.empty:
            # Show summary metrics
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                total_items = len(df)
                st.metric("Total Items", total_items)

            with col2:
                total_quantity = df['quantity_in_stock'].sum()
                st.metric("Total Quantity", f"{total_quantity:,.0f}")

            with col3:
                total_value = df['total_value'].sum()
                st.metric("Total Value", f"${total_value:,.2f}")

            with col4:
                total_batches = df['batch_count'].sum()
                st.metric("Total Batches", f"{total_batches:,.0f}")

            # Filters
            st.markdown("### 🔍 Filters")
            col1, col2, col3 = st.columns(3)

            with col1:
                categories = ["All"] + sorted([cat for cat in df['category'].unique() if pd.notna(cat)])
                selected_category = st.selectbox("Category", categories)

            with col2:
                suppliers = ["All"] + sorted([sup for sup in df['supplier_name'].unique() if pd.notna(sup)])
                selected_supplier = st.selectbox("Supplier", suppliers)

            with col3:
                stock_filter = st.selectbox("Stock Level", ["All", "In Stock", "Low Stock", "Out of Stock"])

            # Apply filters
            filtered_df = df.copy()

            if selected_category != "All":
                filtered_df = filtered_df[filtered_df['category'] == selected_category]

            if selected_supplier != "All":
                filtered_df = filtered_df[filtered_df['supplier_name'] == selected_supplier]

            if stock_filter == "In Stock":
                filtered_df = filtered_df[filtered_df['quantity_in_stock'] > 0]
            elif stock_filter == "Low Stock":
                filtered_df = filtered_df[filtered_df['quantity_in_stock'] <= 10]
            elif stock_filter == "Out of Stock":
                filtered_df = filtered_df[filtered_df['quantity_in_stock'] == 0]

            # Display materials with expandable batch details
            st.markdown(f"### 📊 Raw Materials Inventory ({len(filtered_df)} items)")

            # View toggle
            view_mode = st.radio("View Mode", ["Summary Table", "Detailed with Batches"], horizontal=True)

            if view_mode == "Summary Table":
                # Original table view
                display_df = filtered_df[
                    ['name', 'sku', 'category', 'quantity_in_stock', 'price_paid', 'supplier_name', 'total_value',
                     'active_batches']]
                display_df.columns = ['Name', 'SKU', 'Category', 'Stock', 'Price/Unit', 'Supplier', 'Total Value',
                                      'Active Batches']
                st.dataframe(display_df, use_container_width=True)
            else:
                # Expandable batch details view
                for _, material in filtered_df.iterrows():
                    with st.expander(
                            f"📦 {material['name']} ({material['sku']}) - Stock: {material['quantity_in_stock']:,.0f} - Batches: {material['active_batches']}/{material['batch_count']}",
                            expanded=False
                    ):
                        # Material summary
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.metric("Total Stock", f"{material['quantity_in_stock']:,.0f}")
                        with col2:
                            st.metric("Price/Unit", f"${material['price_paid']:.2f}")
                        with col3:
                            st.metric("Total Value", f"${material['total_value']:,.2f}")
                        with col4:
                            st.metric("Category", material['category'] or "N/A")

                        # Get batch details for this material
                        batch_details = get_batch_details(conn, material['id'])

                        if not batch_details.empty:
                            st.markdown("**🧪 Batch Details:**")

                            # Color-code batches by status
                            def color_batches(row):
                                if row['quantity_remaining'] == 0:
                                    return ['background-color: #ffebee'] * len(row)  # Light red for empty
                                elif pd.notna(row['expiration_date']) and pd.to_datetime(
                                        row['expiration_date']) <= pd.Timestamp.now() + pd.Timedelta(days=30):
                                    return ['background-color: #fff3e0'] * len(row)  # Light orange for expiring soon
                                elif row['overall_status'] == 'rejected':
                                    return ['background-color: #ffcdd2'] * len(row)  # Red for rejected
                                else:
                                    return ['background-color: #e8f5e8'] * len(row)  # Light green for good

                            styled_batches = batch_details.style.apply(color_batches, axis=1)
                            st.dataframe(styled_batches, use_container_width=True)

                            # Batch summary stats
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                active_qty = batch_details[batch_details['quantity_remaining'] > 0][
                                    'quantity_remaining'].sum()
                                st.info(f"Active Stock: {active_qty:,.0f}")
                            with col2:
                                avg_age = (pd.Timestamp.now() - pd.to_datetime(
                                    batch_details['date_received'])).dt.days.mean()
                                st.info(f"Avg Age: {avg_age:.0f} days")
                            with col3:
                                expiring_soon = len(batch_details[
                                                        (pd.notna(batch_details['expiration_date'])) &
                                                        (pd.to_datetime(batch_details[
                                                                            'expiration_date']) <= pd.Timestamp.now() + pd.Timedelta(
                                                            days=30)) &
                                                        (batch_details['quantity_remaining'] > 0)
                                                        ])
                                if expiring_soon > 0:
                                    st.warning(f"Expiring Soon: {expiring_soon}")
                                else:
                                    st.success("No Expiring Batches")

                        else:
                            st.info("No batch details available for this material.")

            # Quick actions
            st.markdown("### ⚡ Quick Actions")
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                if st.button("📥 Export All Materials"):
                    csv = df.to_csv(index=False)
                    st.download_button(
                        label="💾 Download CSV",
                        data=csv,
                        file_name=f"raw_materials_{pd.Timestamp.now().strftime('%Y%m%d')}.csv",
                        mime="text/csv"
                    )

            with col2:
                if st.button("📥 Export Batch Details"):
                    all_batches = get_all_batch_details(conn, filtered_df['id'].tolist())
                    if not all_batches.empty:
                        csv = all_batches.to_csv(index=False)
                        st.download_button(
                            label="💾 Download Batch CSV",
                            data=csv,
                            file_name=f"batch_details_{pd.Timestamp.now().strftime('%Y%m%d')}.csv",
                            mime="text/csv"
                        )
                    else:
                        st.info("No batch data to export")

            with col3:
                if st.button("⚠️ Show Expiring Batches"):
                    show_expiring_batches(conn)

            with col4:
                if st.button("🔄 Refresh Data"):
                    st.rerun()

        else:
            st.info("No raw materials found. Use the Receiving module to add inventory.")

    except Exception as e:
        st.error(f"Raw Materials error: {e}")
        import traceback
        st.code(traceback.format_exc())


def get_batch_details(conn, product_id):
    """Get batch details for a specific product"""
    try:
        return pd.read_sql("""
                           SELECT b.batch_number,
                                  b.quantity_received,
                                  b.quantity_remaining,
                                  b.date_received,
                                  b.expiration_date,
                                  CASE
                                      WHEN b.expiration_date IS NOT NULL THEN
                                          (b.expiration_date - CURRENT_DATE)
                                      ELSE NULL
                                      END                                           as days_until_expiry,
                                  b.receiver_name,
                                  s.name                                            as supplier_name,
                                  b.price_per_unit,
                                  q.overall_status,
                                  ROUND(b.quantity_remaining * b.price_per_unit, 2) as batch_value
                           FROM raw_material_batches b
                                    LEFT JOIN suppliers s ON b.supplier_id = s.id
                                    LEFT JOIN receiving_quality_checks q ON b.id = q.batch_id
                           WHERE b.product_id = %s
                           ORDER BY b.date_received DESC, b.batch_number
                           """, conn, params=(product_id,))
    except Exception:
        return pd.DataFrame()


def get_all_batch_details(conn, product_ids):
    """Get all batch details for multiple products"""
    if not product_ids:
        return pd.DataFrame()

    try:
        product_ids_tuple = tuple(product_ids)
        return pd.read_sql("""
                           SELECT p.name                                            as material_name,
                                  p.sku,
                                  b.batch_number,
                                  b.quantity_received,
                                  b.quantity_remaining,
                                  b.date_received,
                                  b.expiration_date,
                                  b.receiver_name,
                                  s.name                                            as supplier_name,
                                  b.price_per_unit,
                                  q.overall_status,
                                  ROUND(b.quantity_remaining * b.price_per_unit, 2) as batch_value
                           FROM raw_material_batches b
                                    JOIN products p ON b.product_id = p.id
                                    LEFT JOIN suppliers s ON b.supplier_id = s.id
                                    LEFT JOIN receiving_quality_checks q ON b.id = q.batch_id
                           WHERE b.product_id IN %s
                           ORDER BY p.name, b.date_received DESC
                           """, conn, params=(product_ids_tuple,))
    except Exception:
        return pd.DataFrame()


def show_expiring_batches(conn):
    """Show batches expiring within 30 days"""
    try:
        expiring = pd.read_sql("""
                               SELECT p.name                                            as material_name,
                                      p.sku,
                                      b.batch_number,
                                      b.quantity_remaining,
                                      b.expiration_date,
                                      (b.expiration_date - CURRENT_DATE)                as days_until_expiry,
                                      s.name                                            as supplier_name,
                                      ROUND(b.quantity_remaining * b.price_per_unit, 2) as value_at_risk
                               FROM raw_material_batches b
                                        JOIN products p ON b.product_id = p.id
                                        LEFT JOIN suppliers s ON b.supplier_id = s.id
                               WHERE b.expiration_date IS NOT NULL
                                 AND b.expiration_date <= CURRENT_DATE + INTERVAL '30 days'
                                 AND b.quantity_remaining
                                   > 0
                               ORDER BY b.expiration_date
                               """, conn)

        if not expiring.empty:
            st.warning("⚠️ Batches expiring within 30 days:")

            # Color code by urgency
            def color_expiring(row):
                days = row['days_until_expiry']
                if pd.isna(days):
                    return [''] * len(row)
                elif days <= 7:
                    return ['background-color: #ffcdd2'] * len(row)  # Red for ≤ 7 days
                elif days <= 14:
                    return ['background-color: #ffe0b2'] * len(row)  # Orange for ≤ 14 days
                else:
                    return ['background-color: #fff3e0'] * len(row)  # Light orange for ≤ 30 days

            styled_expiring = expiring.style.apply(color_expiring, axis=1)
            st.dataframe(styled_expiring, use_container_width=True)

            total_value_at_risk = expiring['value_at_risk'].sum()
            st.error(f"💰 Total value at risk: ${total_value_at_risk:,.2f}")
        else:
            st.success("✅ No batches expiring within 30 days!")
    except Exception as e:
        st.error(f"Error checking expiring batches: {e}")