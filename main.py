import streamlit as st
import sys
import os

# Add current directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

try:
    # Import modules
    from database.connection import get_connection
    from auth.auth_manager import get_auth_manager
    from pages._dashboard import show_dashboard
    from pages._suppliers import show_suppliers_v2 as show_suppliers
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


def show_authenticated_app():
    """Show the main application for authenticated users"""
    st.title("📦 Inventory & BOM Management")

    try:
        # Test Supabase connection
        supabase = get_connection()
        test_response = supabase.table('suppliers').select('id').limit(1).execute()
        st.success("✅ Connected to Supabase successfully!")
        
    except Exception as e:
        st.error(f"❌ Database connection error: {e}")
        st.error("Please check your Supabase credentials in secrets.toml")
        st.stop()

    # Navigation menu
    menu = ["Dashboard", "Suppliers", "Raw Materials", "Products", "BOM", 
           "Manufacturing", "Sales", "Receiving", "Uploads"]
    choice = st.sidebar.selectbox("📋 Menu", menu)

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


def main():
    st.set_page_config(
        page_title="Inventory & BOM Management", 
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # Hide default navigation
    hide_navigation()

    # Initialize authentication
    auth_manager = get_auth_manager()
    auth_manager.initialize_auth_state()

    # Check authentication status
    if not auth_manager.is_authenticated():
        # Show login page
        st.title("📦 Inventory & BOM Management System")
        st.markdown("---")
        auth_manager.show_login_form()
        
        # Show some info about the system
        st.markdown("---")
        st.markdown("""
        ### 🏢 System Features
        - **📊 Dashboard** - Real-time inventory overview
        - **🏭 Suppliers** - Manage supplier information  
        - **📦 Raw Materials** - Track raw material inventory
        - **🎯 Products** - Manage finished products
        - **🔧 BOM** - Bill of Materials management
        - **⚙️ Manufacturing** - Production planning & execution
        - **💰 Sales** - Process sales & generate invoices
        - **📥 Receiving** - Inventory receiving & stock updates
        """)
    else:
        # Show main application
        auth_manager.show_user_info()
        show_authenticated_app()


if __name__ == "__main__":
    main()