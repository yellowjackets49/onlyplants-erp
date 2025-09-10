import streamlit as st
import pandas as pd
from datetime import datetime
from database.connection import get_connection

# Check if reportlab is available for PDF generation
try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.units import inch
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

def show_sales():
    """Display sales page"""
    st.subheader("💰 Sales")
    supabase = get_connection()

    # Check if we have any products to sell
    try:
        products_response = supabase.table('products').select('*').eq('product_type', 'finished').execute()
        products_df = pd.DataFrame(products_response.data) if products_response.data else pd.DataFrame()

        if products_df.empty:
            st.warning("⚠️ No finished products available for sale. Please add products first.")
            return

        # Show sales summary
        show_sale_summary(supabase)

        # Show sales form
        show_sales_form(supabase, products_df)

        # Show recent sales
        show_recent_sales(supabase)

    except Exception as e:
        st.error(f"Sales error: {e}")


def show_sales_form(supabase, products_df):
    """Show the sales form"""
    st.markdown("### 🛒 New Sale")

    with st.form("sales_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            customer_name = st.text_input("Customer Name", placeholder="Enter customer name")
            customer_email = st.text_input("Customer Email", placeholder="customer@email.com")
            
        with col2:
            customer_phone = st.text_input("Customer Phone", placeholder="+1234567890")
            payment_method = st.selectbox("Payment Method", 
                                        ["Cash", "Credit Card", "Debit Card", "Bank Transfer", "Other"])

        st.markdown("#### 📦 Products")
        
        # Product selection
        products_in_stock = products_df[products_df['quantity_in_stock'] > 0] if 'quantity_in_stock' in products_df.columns else products_df
        
        if products_in_stock.empty:
            st.warning("No products in stock!")
            st.form_submit_button("Process Sale", disabled=True)
            return

        # Multi-product selection
        selected_items = []
        total_amount = 0

        for idx, product in products_in_stock.iterrows():
            col_prod1, col_prod2, col_prod3, col_prod4 = st.columns([3, 2, 1, 2])
            
            with col_prod1:
                st.write(f"**{product['name']}** ({product['sku']})")
            
            with col_prod2:
                available_stock = product.get('quantity_in_stock', 0)
                st.write(f"Stock: {available_stock}")
            
            with col_prod3:
                price = product.get('price_selling', 0)
                st.write(f"${price:.2f}")
            
            with col_prod4:
                quantity = st.number_input(
                    f"Qty", 
                    min_value=0, 
                    max_value=int(available_stock),
                    value=0,
                    key=f"qty_{product['id']}"
                )
                
                if quantity > 0:
                    item_total = quantity * price
                    selected_items.append({
                        'product_id': product['id'],
                        'product_name': product['name'],
                        'sku': product['sku'],
                        'quantity': quantity,
                        'unit_price': price,
                        'total_price': item_total,
                        'available_stock': available_stock
                    })
                    total_amount += item_total

        # Show order summary
        if selected_items:
            st.markdown("#### 📋 Order Summary")
            for item in selected_items:
                st.write(f"• {item['quantity']}x {item['product_name']} @ ${item['unit_price']:.2f} = ${item['total_price']:.2f}")
            
            st.markdown(f"**Total: ${total_amount:.2f}**")

        # Sales notes
        notes = st.text_area("Sale Notes", placeholder="Any additional notes about this sale...")

        # Submit button
        submitted = st.form_submit_button("💸 Process Sale", type="primary")

        if submitted:
            if not customer_name:
                st.error("Please enter customer name")
            elif not selected_items:
                st.error("Please select at least one product")
            else:
                process_sale(supabase, customer_name, customer_email, customer_phone, 
                           payment_method, selected_items, total_amount, notes)


def process_sale(supabase, customer_name, customer_email, customer_phone, 
                payment_method, selected_items, total_amount, notes):
    """Process the sale"""
    try:
        # Create sale record
        sale_data = {
            "customer_name": customer_name,
            "customer_email": customer_email,
            "customer_phone": customer_phone,
            "payment_method": payment_method,
            "total_amount": total_amount,
            "sale_date": datetime.now().isoformat(),
            "notes": notes,
            "invoice_number": generate_invoice_number()
        }
        
        sale_result = supabase.table('sales').insert(sale_data).execute()
        
        if sale_result.data:
            sale_id = sale_result.data[0]['id']
            
            # Create sale items and update inventory
            for item in selected_items:
                # Add sale item
                item_data = {
                    "sale_id": sale_id,
                    "product_id": item['product_id'],
                    "product_name": item['product_name'],
                    "quantity": item['quantity'],
                    "unit_price": item['unit_price'],
                    "total_price": item['total_price']
                }
                supabase.table('sale_items').insert(item_data).execute()
                
                # Update product inventory
                new_stock = item['available_stock'] - item['quantity']
                supabase.table('products').update({
                    'quantity_in_stock': new_stock
                }).eq('id', item['product_id']).execute()

            st.success(f"✅ Sale processed successfully! Invoice: {sale_data['invoice_number']}")
            
            # Offer to generate PDF invoice if reportlab is available
            if REPORTLAB_AVAILABLE:
                if st.button("📄 Generate PDF Invoice"):
                    pdf_data = create_pdf_invoice(sale_data, selected_items)
                    if pdf_data:
                        st.download_button(
                            label="⬇️ Download Invoice PDF",
                            data=pdf_data,
                            file_name=f"invoice_{sale_data['invoice_number']}.pdf",
                            mime="application/pdf"
                        )
            
            st.rerun()
            
    except Exception as e:
        st.error(f"Error processing sale: {e}")


def show_sale_summary(supabase):
    """Show sales summary"""
    st.markdown("### 📊 Sales Summary")
    
    try:
        # Get sales data
        sales_response = supabase.table('sales').select('*').execute()
        
        if sales_response.data:
            sales_df = pd.DataFrame(sales_response.data)
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                total_sales = len(sales_df)
                st.metric("Total Sales", total_sales)
            
            with col2:
                total_revenue = sales_df['total_amount'].sum()
                st.metric("Total Revenue", f"${total_revenue:.2f}")
            
            with col3:
                avg_sale = sales_df['total_amount'].mean()
                st.metric("Average Sale", f"${avg_sale:.2f}")
            
            with col4:
                # Today's sales
                today = datetime.now().date()
                sales_df['sale_date'] = pd.to_datetime(sales_df['sale_date']).dt.date
                today_sales = sales_df[sales_df['sale_date'] == today]['total_amount'].sum()
                st.metric("Today's Sales", f"${today_sales:.2f}")
        else:
            st.info("No sales data available yet")
            
    except Exception as e:
        st.error(f"Error loading sales summary: {e}")


def show_recent_sales(supabase):
    """Show recent sales"""
    st.markdown("### 📋 Recent Sales")
    
    try:
        response = supabase.table('sales').select('*').order('sale_date', desc=True).limit(10).execute()
        
        if response.data:
            df = pd.DataFrame(response.data)
            # Format the display
            display_df = df[['invoice_number', 'customer_name', 'total_amount', 'payment_method', 'sale_date']].copy()
            display_df['sale_date'] = pd.to_datetime(display_df['sale_date']).dt.strftime('%Y-%m-%d %H:%M')
            st.dataframe(display_df, use_container_width=True)
        else:
            st.info("No sales recorded yet")
            
    except Exception as e:
        st.error(f"Error loading recent sales: {e}")


def generate_invoice_number():
    """Generate a unique invoice number"""
    from datetime import datetime
    return f"INV-{datetime.now().strftime('%Y%m%d-%H%M%S')}"


def create_pdf_invoice(sale_data, items):
    """Create PDF invoice"""
    if not REPORTLAB_AVAILABLE:
        return None
        
    try:
        from io import BytesIO
        
        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter
        
        # Header
        c.setFont("Helvetica-Bold", 20)
        c.drawString(50, height - 50, "INVOICE")
        
        c.setFont("Helvetica", 12)
        c.drawString(50, height - 80, f"Invoice #: {sale_data['invoice_number']}")
        c.drawString(50, height - 100, f"Date: {datetime.fromisoformat(sale_data['sale_date']).strftime('%Y-%m-%d %H:%M')}")
        
        # Customer info
        c.setFont("Helvetica-Bold", 14)
        c.drawString(50, height - 140, "Bill To:")
        c.setFont("Helvetica", 12)
        c.drawString(50, height - 160, sale_data['customer_name'])
        if sale_data['customer_email']:
            c.drawString(50, height - 180, sale_data['customer_email'])
        if sale_data['customer_phone']:
            c.drawString(50, height - 200, sale_data['customer_phone'])
        
        # Items table header
        y_pos = height - 250
        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, y_pos, "Item")
        c.drawString(250, y_pos, "Qty")
        c.drawString(300, y_pos, "Unit Price")
        c.drawString(400, y_pos, "Total")
        
        # Draw line under header
        y_pos -= 10
        c.line(50, y_pos, 500, y_pos)
        
        # Items
        c.setFont("Helvetica", 11)
        y_pos -= 20
        for item in items:
            c.drawString(50, y_pos, item['product_name'][:30])  # Truncate long names
            c.drawString(250, y_pos, str(item['quantity']))
            c.drawString(300, y_pos, f"${item['unit_price']:.2f}")
            c.drawString(400, y_pos, f"${item['total_price']:.2f}")
            y_pos -= 20
        
        # Total
        y_pos -= 20
        c.line(300, y_pos, 500, y_pos)
        y_pos -= 20
        c.setFont("Helvetica-Bold", 12)
        c.drawString(300, y_pos, "Total:")
        c.drawString(400, y_pos, f"${sale_data['total_amount']:.2f}")
        
        # Payment method
        y_pos -= 40
        c.setFont("Helvetica", 11)
        c.drawString(50, y_pos, f"Payment Method: {sale_data['payment_method']}")
        
        # Notes
        if sale_data['notes']:
            y_pos -= 40
            c.drawString(50, y_pos, "Notes:")
            y_pos -= 20
            c.drawString(50, y_pos, sale_data['notes'][:80])  # Truncate long notes
        
        c.save()
        buffer.seek(0)
        return buffer.getvalue()
        
    except Exception as e:
        st.error(f"Error creating PDF: {e}")
        return None