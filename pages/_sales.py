import streamlit as st
import pandas as pd
import io
from datetime import datetime
from database.connection import get_connection
from database.schema import create_tables

# Try to import PDF generation (optional)
REPORTLAB_AVAILABLE = False
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib import colors

    REPORTLAB_AVAILABLE = True
except ImportError:
    pass


def show_sales():
    """Display sales page"""
    st.subheader("💰 Sales")
    conn = get_connection()
    c = conn.cursor()

    try:
        create_tables(conn)

        # Get available finished products
        finished_products_query = """
                                  SELECT id, name, sku, quantity_in_stock, price_selling
                                  FROM products
                                  WHERE product_type = 'finished'
                                    AND quantity_in_stock > 0
                                  ORDER BY name \
                                  """

        available_products = pd.read_sql(finished_products_query, conn)

        if available_products.empty:
            st.warning("No finished products available for sale.")
            st.info("💡 Use the Manufacturing module to produce finished goods first.")
        else:
            st.markdown("### 📦 Available Products")
            st.dataframe(available_products, use_container_width=True)

            # Show sales form
            show_sales_form(available_products, conn, c)

        # Show recent sales
        show_recent_sales(conn)

    except Exception as e:
        st.error(f"Sales error: {e}")
        import traceback
        st.code(traceback.format_exc())


def show_sales_form(available_products, conn, c):
    """Show the sales form"""
    st.markdown("### 🛒 Create New Sale")

    with st.form("sales_form"):
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**👤 Customer Information**")
            customer_name = st.text_input("Customer Name *", help="Required")
            customer_phone = st.text_input("Phone")
            customer_email = st.text_input("Email")
            customer_address = st.text_area("Address")

        with col2:
            st.markdown("**📦 Product Information**")
            product_options = [f"{row['name']} (SKU: {row['sku']}) - Stock: {row['quantity_in_stock']}"
                               for _, row in available_products.iterrows()]
            selected_product = st.selectbox("Product *", product_options, help="Required")

            quantity = st.number_input("Quantity *", min_value=1, value=1, help="Required")

            # Get default price for selected product
            if selected_product:
                product_idx = [i for i, opt in enumerate(product_options) if opt == selected_product][0]
                default_price = float(available_products.iloc[product_idx]['price_selling'])
            else:
                default_price = 0.0

            unit_price = st.number_input("Unit Price *", min_value=0.0, value=default_price, format="%.2f",
                                         help="Required")

        notes = st.text_area("Sale Notes (optional)")

        # Calculate total
        total_price = quantity * unit_price
        st.write(f"**Total: ${total_price:.2f}**")

        submitted = st.form_submit_button("🛒 Process Sale", type="primary")

    # Process form submission OUTSIDE the form
    if submitted:
        if not customer_name:
            st.error("Customer name is required")
        elif not selected_product:
            st.error("Please select a product")
        elif quantity <= 0:
            st.error("Quantity must be greater than 0")
        elif unit_price <= 0:
            st.error("Unit price must be greater than 0")
        else:
            # Store sale data in session state to pass between form and summary
            sale_result = process_sale(selected_product, product_options, available_products, customer_name,
                                       customer_email, customer_phone, customer_address, quantity, unit_price, notes,
                                       conn, c)

            if sale_result:
                st.session_state.latest_sale = sale_result
                st.rerun()

    # Show sale summary if we have a completed sale (outside form)
    if 'latest_sale' in st.session_state:
        sale_data, items_data = st.session_state.latest_sale
        show_sale_summary(sale_data, items_data)
        # Clear the sale data after showing
        del st.session_state.latest_sale


def process_sale(selected_product, product_options, available_products, customer_name,
                 customer_email, customer_phone, customer_address, quantity, unit_price, notes, conn, c):
    """Process the sale transaction and return sale data"""
    try:
        # Get product details
        product_idx = [i for i, opt in enumerate(product_options) if opt == selected_product][0]
        selected_product_row = available_products.iloc[product_idx]
        product_id = int(selected_product_row['id'])
        available_stock = int(selected_product_row['quantity_in_stock'])

        # Check stock availability
        if quantity > available_stock:
            st.error(f"❌ Insufficient stock! Available: {available_stock}, Requested: {quantity}")
            return None

        total_price = quantity * unit_price
        invoice_number = generate_invoice_number()

        # Process the sale
        c.execute("BEGIN")

        # Create sale record
        c.execute("""
                  INSERT INTO sales (invoice_number, customer_name, customer_email, customer_phone,
                                     customer_address, total_amount, notes)
                  VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id
                  """, (invoice_number, customer_name, customer_email or None, customer_phone or None,
                        customer_address or None, total_price, notes or None))

        sale_id = c.fetchone()[0]

        # Create sale item record
        c.execute("""
                  INSERT INTO sales_items (sale_id, product_id, quantity, unit_price, total_price)
                  VALUES (%s, %s, %s, %s, %s)
                  """, (sale_id, product_id, quantity, unit_price, total_price))

        # Update product stock
        c.execute("""
                  UPDATE products
                  SET quantity_in_stock = quantity_in_stock - %s
                  WHERE id = %s
                  """, (quantity, product_id))

        # Record transaction
        try:
            c.execute("""
                      INSERT INTO transactions (product_id, tx_type, quantity, price, notes)
                      VALUES (%s, 'out', %s, %s, %s)
                      """, (product_id, quantity, unit_price, f"Sale - Invoice: {invoice_number}"))
        except Exception:
            pass  # Transaction logging is optional

        conn.commit()

        st.success(f"✅ Sale completed successfully!")
        st.balloons()

        # Prepare sale data for summary
        sale_data = {
            'invoice_number': invoice_number,
            'customer_name': customer_name,
            'customer_email': customer_email,
            'customer_phone': customer_phone,
            'customer_address': customer_address,
            'sale_date': datetime.now(),
            'total_amount': total_price,
            'notes': notes
        }

        items_data = [{
            'product_name': selected_product_row['name'],
            'product_sku': selected_product_row['sku'],
            'quantity': quantity,
            'unit_price': unit_price,
            'total_price': total_price
        }]

        return (sale_data, items_data)

    except Exception as e:
        conn.rollback()
        st.error(f"❌ Sale failed: {e}")
        import traceback
        st.code(traceback.format_exc())
        return None


def show_sale_summary(sale_data, items_data):
    """Show sale summary and PDF download option (outside form context)"""
    st.markdown("### 📋 Sale Summary")

    col1, col2 = st.columns(2)
    with col1:
        st.info(f"**Invoice:** {sale_data['invoice_number']}")
        st.info(f"**Customer:** {sale_data['customer_name']}")
        st.info(f"**Total:** ${sale_data['total_amount']:.2f}")
    with col2:
        st.info(f"**Date:** {sale_data['sale_date'].strftime('%Y-%m-%d %H:%M')}")
        if sale_data.get('customer_email'):
            st.info(f"**Email:** {sale_data['customer_email']}")

    # PDF download (now outside form, so it works!)
    if REPORTLAB_AVAILABLE:
        try:
            buffer = io.BytesIO()
            create_pdf_invoice(sale_data, items_data, buffer)

            st.download_button(
                label="📄 Download Invoice PDF",
                data=buffer.getvalue(),
                file_name=f"invoice_{sale_data['invoice_number']}.pdf",
                mime="application/pdf",
                key=f"download_{sale_data['invoice_number']}"  # Unique key to avoid conflicts
            )
        except Exception as e:
            st.warning(f"PDF generation failed: {e}")
    else:
        st.info("💡 Install reportlab package to enable PDF invoice generation: `pip install reportlab`")


def show_recent_sales(conn):
    """Show recent sales history"""
    st.markdown("### 📊 Recent Sales")

    try:
        recent_sales = pd.read_sql("""
                                   SELECT s.invoice_number,
                                          s.customer_name,
                                          s.sale_date,
                                          s.total_amount,
                                          p.name as product_name,
                                          si.quantity,
                                          si.unit_price
                                   FROM sales s
                                            JOIN sales_items si ON s.id = si.sale_id
                                            JOIN products p ON si.product_id = p.id
                                   ORDER BY s.sale_date DESC LIMIT 20
                                   """, conn)

        if not recent_sales.empty:
            st.dataframe(recent_sales, use_container_width=True)

            # Sales summary
            col1, col2, col3 = st.columns(3)
            with col1:
                total_sales = recent_sales['total_amount'].sum()
                st.metric("Recent Sales Value", f"${total_sales:,.2f}")
            with col2:
                total_orders = recent_sales['invoice_number'].nunique()
                st.metric("Recent Orders", total_orders)
            with col3:
                avg_order = recent_sales.groupby('invoice_number')['total_amount'].first().mean()
                st.metric("Avg Order Value", f"${avg_order:.2f}")
        else:
            st.info("No sales recorded yet.")
    except Exception as e:
        st.info("Sales history not available yet.")


def generate_invoice_number():
    """Generate unique invoice number"""
    now = datetime.now()
    return f"INV-{now.strftime('%Y%m%d')}-{now.strftime('%H%M%S')}"


def create_pdf_invoice(sale_data, items_data, buffer):
    """Generate PDF invoice (if reportlab is available)"""
    if not REPORTLAB_AVAILABLE:
        raise ImportError("ReportLab is required for PDF generation")

    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30,
        textColor=colors.darkblue
    )
    story.append(Paragraph("INVOICE", title_style))
    story.append(Spacer(1, 12))

    # Company Info
    company_style = ParagraphStyle(
        'Company',
        parent=styles['Normal'],
        fontSize=12,
        textColor=colors.darkblue
    )
    story.append(
        Paragraph("<b>Your Company Name</b><br/>123 Business Street<br/>City, State 12345<br/>Phone: (555) 123-4567",
                  company_style))
    story.append(Spacer(1, 20))

    # Invoice details
    invoice_data = [
        ['Invoice Number:', sale_data['invoice_number']],
        ['Date:', sale_data['sale_date'].strftime('%Y-%m-%d %H:%M')],
        ['Customer:', sale_data['customer_name']],
        ['Email:', sale_data.get('customer_email', 'N/A')],
        ['Phone:', sale_data.get('customer_phone', 'N/A')],
    ]

    invoice_table = Table(invoice_data, colWidths=[1.5 * inch, 3 * inch])
    invoice_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(invoice_table)
    story.append(Spacer(1, 20))

    # Items table
    items_table_data = [['Product', 'SKU', 'Quantity', 'Unit Price', 'Total']]

    for item in items_data:
        items_table_data.append([
            item['product_name'],
            item['product_sku'],
            str(int(item['quantity'])),
            f"${item['unit_price']:.2f}",
            f"${item['total_price']:.2f}"
        ])

    # Add total row
    items_table_data.append(['', '', '', 'TOTAL:', f"${sale_data['total_amount']:.2f}"])

    items_table = Table(items_table_data, colWidths=[2.5 * inch, 1 * inch, 1 * inch, 1 * inch, 1 * inch])
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -2), colors.beige),
        ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    story.append(items_table)

    if sale_data.get('notes'):
        story.append(Spacer(1, 20))
        story.append(Paragraph(f"<b>Notes:</b> {sale_data['notes']}", styles['Normal']))

    doc.build(story)
    return buffer