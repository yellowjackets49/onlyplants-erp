import pandas as pd
import io
from datetime import datetime
from database.connection import get_connection

def calculate_product_cost(product_id):
    """Calculate cost of finished product based on BOM"""
    supabase = get_connection()
    try:
        # Get BOM data with joined product information
        bom_response = supabase.table('bill_of_materials').select(
            'quantity_required, products:raw_material_id(price_paid)'
        ).eq('finished_product_id', product_id).execute()
        
        if not bom_response.data:
            return 0
            
        total_cost = 0
        for item in bom_response.data:
            quantity = item.get('quantity_required', 0)
            price = item.get('products', {}).get('price_paid', 0) if item.get('products') else 0
            total_cost += quantity * price
            
        return float(total_cost)
    except Exception as e:
        print(f"Error calculating product cost: {e}")
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