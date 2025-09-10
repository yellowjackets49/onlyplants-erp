import streamlit as st
import pandas as pd
from datetime import datetime, date
from database.connection import get_connection


def show_receiving():
    """Display receiving page"""
    st.subheader("🚚 Receiving")
    conn = get_connection()
    c = conn.cursor()

    try:
        # Show recent batches first
        st.markdown("### 📦 Recent Batches Received")
        recent_batches = pd.read_sql("""
                                     SELECT b.batch_number,
                                            p.name as product_name,
                                            p.sku,
                                            s.name as supplier_name,
                                            b.quantity_received,
                                            b.quantity_remaining,
                                            b.date_received,
                                            b.expiration_date,
                                            b.receiver_name,
                                            b.coa_provided,
                                            q.overall_status
                                     FROM raw_material_batches b
                                              LEFT JOIN products p ON b.product_id = p.id
                                              LEFT JOIN suppliers s ON b.supplier_id = s.id
                                              LEFT JOIN receiving_quality_checks q ON b.id = q.batch_id
                                     ORDER BY b.created_at DESC LIMIT 20
                                     """, conn)

        if not recent_batches.empty:
            st.dataframe(recent_batches, use_container_width=True)
        else:
            st.info("No batches received yet.")

        # Receiving form
        st.markdown("### 📥 Receive New Batch")

        # Get existing raw materials and suppliers
        raw_materials = pd.read_sql("SELECT id, name, sku FROM products WHERE product_type='raw' ORDER BY name", conn)
        suppliers = pd.read_sql("SELECT id, name FROM suppliers ORDER BY name", conn)

        with st.form("receive_batch"):
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("**📦 Batch Information**")

                # Material selection with option to add new
                material_options = [f"{row['name']} ({row['sku']})" for _, row in raw_materials.iterrows()]
                material_options.append("➕ Add New Raw Material")

                selected_material = st.selectbox("Raw Material", material_options)

                # Handle new material creation
                if selected_material == "➕ Add New Raw Material":
                    with st.expander("Add New Raw Material", expanded=True):
                        new_material_name = st.text_input("Material Name")
                        new_material_sku = st.text_input("SKU")
                        new_material_category = st.text_input("Category")
                        new_material_category_code = st.text_input("Category Code")

                        if st.form_submit_button("Create Material First"):
                            if new_material_name and new_material_sku:
                                try:
                                    c.execute("""
                                              INSERT INTO products (name, sku, product_type, category, category_code, quantity_in_stock)
                                              VALUES (%s, %s, 'raw', %s, %s, 0)
                                              """, (new_material_name, new_material_sku, new_material_category,
                                                    new_material_category_code))
                                    conn.commit()
                                    st.success(f"✅ Material '{new_material_name}' created! Please refresh to use it.")
                                except Exception as e:
                                    st.error(f"Error creating material: {e}")
                            else:
                                st.error("Please fill in material name and SKU")
                    selected_material_id = None
                else:
                    # Get selected material ID and convert to int
                    selected_idx = material_options.index(selected_material)
                    selected_material_id = int(raw_materials.iloc[selected_idx]['id'])

                batch_number = st.text_input("Batch Number", help="Supplier's batch/lot number")
                quantity_received = st.number_input("Quantity Received", min_value=0.0, format="%.2f")

                # Supplier selection
                supplier_options = [""] + [row['name'] for _, row in suppliers.iterrows()]
                selected_supplier_name = st.selectbox("Supplier", supplier_options)

                supplier_id = None
                if selected_supplier_name:
                    supplier_id = int(suppliers[suppliers['name'] == selected_supplier_name]['id'].iloc[0])

            with col2:
                st.markdown("**📅 Dates & Details**")

                date_received = st.date_input("Date Received", value=date.today())
                expiration_date = st.date_input("Expiration Date", value=None)

                price_per_unit = st.number_input("Price per Unit", min_value=0.0, format="%.2f")

                receiver_name = st.text_input("Received By", help="Name of person receiving")

                barcode = st.text_input("Barcode", help="Optional barcode/QR code")
                kebs_smark = st.text_input("KEBS S-Mark Number", help="Quality certification number")

                coa_provided = st.checkbox("Certificate of Analysis (COA) Provided")

            # Quality check section
            st.markdown("**🔍 Quality Check**")

            col3, col4, col5 = st.columns(3)

            quality_options = ["na", "acceptable", "not_acceptable"]
            quality_labels = {"na": "N/A", "acceptable": "Acceptable", "not_acceptable": "Not Acceptable"}

            with col3:
                color_check = st.selectbox("Color", quality_options, format_func=lambda x: quality_labels[x])
                packaging_check = st.selectbox("Packaging", quality_options, format_func=lambda x: quality_labels[x])
                shelf_life_check = st.selectbox("Shelf Life", quality_options, format_func=lambda x: quality_labels[x])

            with col4:
                weight_check = st.selectbox("Weight", quality_options, format_func=lambda x: quality_labels[x])
                coa_check = st.selectbox("COA Quality", quality_options, format_func=lambda x: quality_labels[x])
                seal_integrity_check = st.selectbox("Seal Integrity", quality_options,
                                                    format_func=lambda x: quality_labels[x])

            with col5:
                labelling_check = st.selectbox("Labelling", quality_options, format_func=lambda x: quality_labels[x])
                storage_conditions_check = st.selectbox("Storage Conditions", quality_options,
                                                        format_func=lambda x: quality_labels[x])

                # Overall status
                overall_status = st.selectbox("Overall Status", ["accepted", "rejected"])

            quality_notes = st.text_area("Quality Check Notes", help="Additional observations or comments")

            submitted = st.form_submit_button("📦 Receive Batch", type="primary")

            if submitted and selected_material_id and batch_number and quantity_received > 0 and receiver_name:
                try:
                    c.execute("BEGIN")

                    # Convert values to proper types for PostgreSQL
                    material_id = int(selected_material_id)
                    qty_received = float(quantity_received)
                    qty_remaining = float(quantity_received)
                    price_unit = float(price_per_unit)
                    supplier_id_clean = int(supplier_id) if supplier_id else None

                    # Handle empty strings for optional fields
                    barcode_clean = barcode if barcode else None
                    kebs_smark_clean = kebs_smark if kebs_smark else None
                    expiration_date_clean = expiration_date if expiration_date else None

                    # Insert batch record
                    c.execute("""
                              INSERT INTO raw_material_batches
                              (product_id, batch_number, quantity_received, quantity_remaining, date_received,
                               expiration_date, barcode, coa_provided, kebs_smark_number, receiver_name,
                               supplier_id, price_per_unit)
                              VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
                              """, (material_id, batch_number, qty_received, qty_remaining,
                                    date_received, expiration_date_clean, barcode_clean, coa_provided, kebs_smark_clean,
                                    receiver_name, supplier_id_clean, price_unit))

                    batch_id = c.fetchone()[0]

                    # Insert quality check record
                    quality_notes_clean = quality_notes if quality_notes else None

                    c.execute("""
                              INSERT INTO receiving_quality_checks
                              (batch_id, color, packaging, shelf_life, weight, coa, seal_integrity,
                               labelling, storage_conditions, overall_status, notes)
                              VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                              """, (batch_id, color_check, packaging_check, shelf_life_check, weight_check,
                                    coa_check, seal_integrity_check, labelling_check, storage_conditions_check,
                                    overall_status, quality_notes_clean))

                    # Update product inventory (only if accepted)
                    if overall_status == "accepted":
                        # Update raw material stock
                        c.execute("""
                                  UPDATE products
                                  SET quantity_in_stock = quantity_in_stock + %s,
                                      price_paid        = %s
                                  WHERE id = %s
                                  """, (qty_received, price_unit, material_id))

                        # Add transaction record
                        try:
                            c.execute("""
                                      INSERT INTO transactions (product_id, tx_type, quantity, price, notes)
                                      VALUES (%s, 'in', %s, %s, %s)
                                      """, (material_id, qty_received, price_unit,
                                            f"Received batch {batch_number} from {selected_supplier_name or 'Unknown'}"))
                        except Exception:
                            # Transaction logging is optional
                            pass

                    conn.commit()

                    if overall_status == "accepted":
                        st.success(f"✅ Batch {batch_number} received successfully and added to inventory!")
                    else:
                        st.warning(f"⚠️ Batch {batch_number} received but REJECTED - not added to inventory")

                    st.balloons()
                    st.rerun()

                except Exception as e:
                    conn.rollback()
                    st.error(f"Error receiving batch: {e}")
                    import traceback
                    st.code(traceback.format_exc())
            elif submitted:
                st.error("Please fill in all required fields: Material, Batch Number, Quantity, and Receiver Name")

        # Batch tracking section
        st.markdown("### 🔍 Batch Tracking")

        col1, col2 = st.columns(2)

        with col1:
            search_batch = st.text_input("Search Batch Number")
            if search_batch:
                batch_details = pd.read_sql("""
                                            SELECT b.batch_number,
                                                   p.name as product_name,
                                                   p.sku,
                                                   s.name as supplier_name,
                                                   b.quantity_received,
                                                   b.quantity_remaining,
                                                   b.date_received,
                                                   b.expiration_date,
                                                   b.receiver_name,
                                                   q.overall_status,
                                                   q.notes
                                            FROM raw_material_batches b
                                                     LEFT JOIN products p ON b.product_id = p.id
                                                     LEFT JOIN suppliers s ON b.supplier_id = s.id
                                                     LEFT JOIN receiving_quality_checks q ON b.id = q.batch_id
                                            WHERE b.batch_number ILIKE %s
                                            ORDER BY b.created_at DESC
                                            """, conn, params=(f"%{search_batch}%",))

                if not batch_details.empty:
                    st.dataframe(batch_details, use_container_width=True)
                else:
                    st.info("No batches found")

        with col2:
            if st.button("📊 Show Expiring Batches"):
                try:
                    expiring_batches = pd.read_sql("""
                                                   SELECT b.batch_number,
                                                          p.name                             as product_name,
                                                          b.quantity_remaining,
                                                          b.expiration_date,
                                                          (b.expiration_date - CURRENT_DATE) as days_until_expiry
                                                   FROM raw_material_batches b
                                                            JOIN products p ON b.product_id = p.id
                                                   WHERE b.expiration_date IS NOT NULL
                                                     AND b.expiration_date <= CURRENT_DATE + INTERVAL '30 days'
                                                     AND b.quantity_remaining
                                                       > 0
                                                   ORDER BY b.expiration_date
                                                   """, conn)

                    if not expiring_batches.empty:
                        st.warning("⚠️ Batches expiring within 30 days:")
                        st.dataframe(expiring_batches)
                    else:
                        st.success("✅ No batches expiring soon")
                except Exception as e:
                    st.info("Expiration tracking not available")

    except Exception as e:
        st.error(f"Receiving error: {e}")
        import traceback
        st.code(traceback.format_exc())