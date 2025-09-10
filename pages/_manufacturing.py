import streamlit as st
import pandas as pd
from database.connection import get_connection


def show_manufacturing():
    """Display manufacturing page"""
    st.subheader("🏭 Manufacturing")

    try:
        conn = get_connection()
        c = conn.cursor()

        manufacturing_query = """
                              SELECT DISTINCT p.id, \
                                              p.name, \
                                              p.sku, \
                                              p.quantity_in_stock as current_stock
                              FROM products p
                                       INNER JOIN bill_of_materials b ON p.id = b.finished_product_id
                              WHERE p.product_type = 'finished'
                              ORDER BY p.name \
                              """

        manufactureable_products = pd.read_sql(manufacturing_query, conn)

        if manufactureable_products.empty:
            st.warning("No finished products with BOMs found. Upload Products and BOMs first.")
            return

        st.markdown("### 📋 Available Products for Manufacturing")
        st.dataframe(manufactureable_products)

        # Production Planning Section
        st.markdown("### 🚀 Production Planning")

        col1, col2 = st.columns([2, 1])

        with col1:
            product_options = [f"{row.name} (SKU: {row.sku})" for _, row in manufactureable_products.iterrows()]
            selected_product = st.selectbox("Select Product to Manufacture", product_options)
            quantity_to_produce = st.number_input("Quantity to Produce", min_value=1, value=1)
            production_notes = st.text_area("Production Notes (optional)")

        with col2:
            st.markdown("### 🎯 Production Status")

            # Show current production status
            production_status = st.session_state.get('production_status', 'ready')

            if production_status == 'ready':
                st.info("🔵 Ready to start production")
            elif production_status == 'materials_checked':
                st.success("✅ Materials verified - Ready to start")
            elif production_status == 'in_progress':
                st.warning("🟡 Production in progress")
            elif production_status == 'ready_to_finish':
                st.success("🟢 Ready to finish production")

        # Production Control Buttons
        st.markdown("### 🎛️ Production Controls")

        col1, col2, col3 = st.columns(3)

        with col1:
            check_materials = st.button("🔍 Check Materials",
                                        type="secondary",
                                        use_container_width=True,
                                        disabled=st.session_state.get('production_status', 'ready') not in ['ready'])

        with col2:
            start_production = st.button("🚀 Start Production",
                                         type="primary",
                                         use_container_width=True,
                                         disabled=st.session_state.get('production_status',
                                                                       'ready') != 'materials_checked')

        with col3:
            finish_production = st.button("🏁 Finish Production",
                                          type="primary",
                                          use_container_width=True,
                                          disabled=st.session_state.get('production_status',
                                                                        'ready') != 'ready_to_finish')

        # Handle Check Materials
        if check_materials and selected_product:
            handle_check_materials(selected_product, quantity_to_produce, production_notes, manufactureable_products,
                                   product_options, conn, c)

        # Handle Start Production
        if start_production:
            handle_start_production()

        # Handle Finish Production
        if finish_production:
            handle_finish_production(conn, c)

        # Show current production details if in progress
        show_current_production_status()

        # Show recent activity
        show_recent_manufacturing_activity(conn)

    except Exception as e:
        st.error(f"Error in manufacturing module: {e}")
        import traceback
        st.code(traceback.format_exc())


def handle_check_materials(selected_product, quantity_to_produce, production_notes, manufactureable_products,
                           product_options, conn, c):
    """Handle material availability checking"""
    # Get product details
    product_idx = product_options.index(selected_product)
    selected_product_row = manufactureable_products.iloc[product_idx]
    product_id = int(selected_product_row.id)
    product_name = selected_product_row.name

    st.markdown(f"### 📊 Material Requirements for {product_name} (Qty: {quantity_to_produce})")

    # Check BOM
    bom_query = """
                SELECT b.raw_material_id, \
                       r.name                     as raw_material_name, \
                       r.sku                      as raw_material_sku, \
                       r.quantity_in_stock        as available_stock, \
                       b.quantity_required, \
                       (b.quantity_required * %s) as total_needed
                FROM bill_of_materials b
                         JOIN products r ON b.raw_material_id = r.id
                WHERE b.finished_product_id = %s
                ORDER BY r.name \
                """

    try:
        bom_requirements = pd.read_sql(bom_query, conn, params=(int(quantity_to_produce), int(product_id)))

        if not bom_requirements.empty:
            # Display material requirements
            materials_ok = True

            st.markdown("**📋 Material Availability Check:**")

            for _, row in bom_requirements.iterrows():
                available = row['available_stock']
                needed = row['total_needed']
                material_name = row['raw_material_name']
                sku = row['raw_material_sku']

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
                    'bom_requirements': bom_requirements.to_dict('records')
                }
                st.rerun()
            else:
                st.error("❌ Insufficient materials for production.")
                st.session_state.production_status = 'ready'

                # Show shortages
                st.write("**Materials needed:**")
                for _, row in bom_requirements.iterrows():
                    if row['available_stock'] < row['total_needed']:
                        shortage = row['total_needed'] - row['available_stock']
                        st.write(f"• {row['raw_material_name']}: Need {shortage:.0f} more units")

        else:
            st.error("No BOM found for this product!")
            st.session_state.production_status = 'ready'

    except Exception as e:
        st.error(f"Error checking BOM: {e}")
        st.session_state.production_status = 'ready'


def handle_start_production():
    """Handle starting production"""
    if 'production_plan' in st.session_state:
        plan = st.session_state.production_plan

        st.session_state.production_status = 'ready_to_finish'

        st.success(f"🚀 Production started for {plan['quantity']} units of {plan['product_name']}!")
        st.info("📋 Materials are now allocated. Click 'Finish Production' when manufacturing is complete.")
        st.rerun()
    else:
        st.error("No production plan found. Please check materials first.")


def handle_finish_production(conn, c):
    """Handle finishing production and updating inventory"""
    if 'production_plan' not in st.session_state:
        st.error("No active production to finish.")
        return

    plan = st.session_state.production_plan

    st.markdown("### 🏁 Finishing Production")

    try:
        c.execute("BEGIN")

        st.info("🔧 Consuming raw materials...")

        # Consume raw materials
        for material in plan['bom_requirements']:
            new_stock = material['available_stock'] - material['total_needed']
            c.execute("""
                      UPDATE products
                      SET quantity_in_stock = %s
                      WHERE id = %s
                      """, (int(new_stock), int(material['raw_material_id'])))

            # Record outbound transaction
            try:
                c.execute("""
                          INSERT INTO transactions (product_id, tx_type, quantity, notes)
                          VALUES (%s, 'out', %s, %s)
                          """, (int(material['raw_material_id']), int(material['total_needed']),
                                f"Manufacturing: {plan['product_name']} (Qty: {plan['quantity']})"))
            except Exception:
                pass  # Transaction logging is optional

        st.info("📦 Adding finished products to inventory...")

        # Add finished products
        c.execute("""
                  UPDATE products
                  SET quantity_in_stock = quantity_in_stock + %s
                  WHERE id = %s
                  """, (int(plan['quantity']), int(plan['product_id'])))

        # Record inbound transaction
        try:
            c.execute("""
                      INSERT INTO transactions (product_id, tx_type, quantity, notes)
                      VALUES (%s, 'in', %s, %s)
                      """, (int(plan['product_id']), int(plan['quantity']),
                            f"Manufacturing completed. Notes: {plan['notes']}"))
        except Exception:
            pass  # Transaction logging is optional

        conn.commit()

        st.success(f"🎉 Successfully produced {plan['quantity']} units of {plan['product_name']}!")
        st.balloons()

        # Show updated inventory
        show_production_summary(plan, conn)

        # Clear production state
        st.session_state.production_status = 'ready'
        if 'production_plan' in st.session_state:
            del st.session_state.production_plan

        st.rerun()

    except Exception as e:
        conn.rollback()
        st.error(f"Production failed: {e}")
        import traceback
        st.code(traceback.format_exc())


def show_current_production_status():
    """Show current production status details"""
    if st.session_state.get('production_status', 'ready') in ['materials_checked',
                                                              'ready_to_finish'] and 'production_plan' in st.session_state:
        plan = st.session_state.production_plan

        st.markdown("### 📋 Current Production Plan")

        col1, col2, col3 = st.columns(3)
        with col1:
            st.info(f"**Product:** {plan['product_name']}")
        with col2:
            st.info(f"**Quantity:** {plan['quantity']}")
        with col3:
            st.info(f"**Status:** {st.session_state.get('production_status', 'ready').replace('_', ' ').title()}")

        if plan.get('notes'):
            st.write(f"**Notes:** {plan['notes']}")

        # Show materials to be consumed
        st.markdown("**Materials to be consumed:**")
        materials_df = pd.DataFrame(plan['bom_requirements'])
        if not materials_df.empty:
            display_materials = materials_df[['raw_material_name', 'raw_material_sku', 'total_needed']].copy()
            display_materials.columns = ['Material', 'SKU', 'Quantity to Consume']
            st.dataframe(display_materials, use_container_width=True)


def show_production_summary(plan, conn):
    """Show production completion summary"""
    st.markdown("### 📦 Production Summary")

    # Show updated finished product
    updated_finished = pd.read_sql(
        "SELECT name, sku, quantity_in_stock FROM products WHERE id = %s",
        conn, params=(int(plan['product_id']),))
    st.write("**Updated Finished Product:**")
    st.dataframe(updated_finished, use_container_width=True)

    # Show updated raw materials
    raw_material_ids = tuple(int(material['raw_material_id']) for material in plan['bom_requirements'])
    updated_raw = pd.read_sql(f"""
        SELECT name, sku, quantity_in_stock 
        FROM products 
        WHERE id IN {raw_material_ids}
    """, conn)
    st.write("**Updated Raw Materials:**")
    st.dataframe(updated_raw, use_container_width=True)


def show_recent_manufacturing_activity(conn):
    """Show recent manufacturing activity"""
    st.markdown("### 📊 Recent Manufacturing Activity")
    try:
        recent_manufacturing = pd.read_sql("""
                                           SELECT t.date,
                                                  p.name as product_name,
                                                  p.sku,
                                                  t.tx_type,
                                                  t.quantity,
                                                  t.notes
                                           FROM transactions t
                                                    JOIN products p ON t.product_id = p.id
                                           WHERE t.notes LIKE 'Manufacturing%'
                                           ORDER BY t.date DESC LIMIT 10
                                           """, conn)

        if not recent_manufacturing.empty:
            st.dataframe(recent_manufacturing, use_container_width=True)
        else:
            st.info("No manufacturing activity yet.")
    except Exception as e:
        st.info("Transaction logging not available yet.")