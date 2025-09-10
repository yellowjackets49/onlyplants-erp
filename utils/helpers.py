import pandas as pd
import io
from datetime import datetime
from database.connection import get_connection

def calculate_product_cost(product_id):
    """Calculate cost of finished product based on BOM"""
    conn = get_connection()
    try:
        df = pd.read_sql("""
            SELECT b.quantity_required, r.price_paid
            FROM bill_of_materials b
            JOIN products r ON b.raw_material_id = r.id
            WHERE b.finished_product_id=%s
        """, conn, params=(product_id,))
        return float((df["quantity_required"] * df["price_paid"]).sum()) if not df.empty else 0
    except Exception:
        return 0

def generate_invoice_number():
    """Generate unique invoice number"""
    now = datetime.now()
    return f"INV-{now.strftime('%Y%m%d')}-{now.strftime('%H%M%S')}"

def download_template(template_type):
    """Generate Excel template for bulk uploads"""
    buffer = io.BytesIO()
    if template_type == "Suppliers":
        df = pd.DataFrame([{"Name": "", "Contact": "", "Phone": "", "Email": "", "RawMaterials": "", "CategoryCodes": ""}])
    elif template_type == "RawMaterials":
        df = pd.DataFrame([{"Name": "", "SKU": "", "Category": "", "CategoryCode": "", "Quantity": 0, "PricePaid": 0.0, "Supplier": ""}])
    elif template_type == "Products":
        df = pd.DataFrame([{"Name": "", "SKU": "", "Category": "", "PriceSelling": 0.0, "Supplier": ""}])
    elif template_type == "BOM":
        df = pd.DataFrame([{
            "ProductID": "",
            "ProductName": "",
            "RawMaterialID": "",
            "QuantityRequired": 0,
            "Volume": 0
        }])
    df.to_excel(buffer, index=False, engine="openpyxl")
    buffer.seek(0)
    return buffer