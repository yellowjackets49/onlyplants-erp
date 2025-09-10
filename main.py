import streamlit as st
import sys
import os

# Add current directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

try:
    # Import modules with updated names
    from database.connection import get_connection
    from database.schema import create_tables
    from pages._dashboard import show_dashboard
    from pages._suppliers import show_suppliers
    from pages._raw_materials import show_raw_materials
    from pages._products import show_products
    from pages._bom import show_bom
    from pages._manufacturing import show_manufacturing
    from pages._sales import show_sales
    from pages._receiving import show_receiving

except ImportError as e:
    st.error(f"❌ Import error: {e}")
    st.error("Please ensure all module files are created in the correct folders")
    st.stop()


def hide_navigation():
    """Hide Streamlit's default navigation"""
    hide_nav_css = """
    <style>
        .css-1d391kg {display: none}
        .css-1rs6os {display: none}
        .css-17lntkn {display: none}
        [data-testid="stSidebarNav"] {display: none}
        .css-pkbazv {display: none}
    </style>
    """
    st.markdown(hide_nav_css, unsafe_allow_html=True)


def main():
    st.set_page_config(page_title="Inventory & BOM Management", layout="wide")

    # Hide the navigation links
    hide_navigation()

    st.title("📦 Inventory & BOM Management")

    try:
        # Test Supabase connection
        supabase = get_connection()
        
        # Test the connection with a simple query
        test_response = supabase.table('suppliers').select('id').limit(1).execute()
        
        st.success("✅ Connected to Supabase successfully!")
        
    except Exception as e:
        st.error(f"❌ Database connection error: {e}")
        st.error("Please check your Supabase credentials in secrets.toml")
        st.stop()

    # Navigation
    menu = ["Dashboard", "Suppliers", "Raw Materials", "Products", "BOM", "Manufacturing", "Sales", "Receiving",
            "Uploads"]
    choice = st.sidebar.selectbox("Menu", menu)

    # Route to pages
    try:
        if choice == "Dashboard":
            show_dashboard()
        elif choice == "Suppliers":
            show_suppliers()
        elif choice == "Raw Materials":
            show_raw_materials()
        elif choice == "Products":
            show_products()
        elif choice == "BOM":
            show_bom()
        elif choice == "Manufacturing":
            show_manufacturing()
        elif choice == "Sales":
            show_sales()
        elif choice == "Receiving":
            show_receiving()
        elif choice == "Uploads":
            st.subheader("📤 Bulk Uploads")
            st.info("Upload module - to be implemented")
    except Exception as e:
        st.error(f"Error loading page '{choice}': {e}")
        import traceback
        st.code(traceback.format_exc())


if __name__ == "__main__":
    main()