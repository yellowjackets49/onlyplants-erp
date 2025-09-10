import io

# ReportLab imports for PDF generation (with error handling)
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


def create_pdf_invoice(sale_data, items_data, buffer):
    """Generate PDF invoice"""
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