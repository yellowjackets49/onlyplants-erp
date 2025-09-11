import streamlit as st
import sys
import os

# Add current directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

try:
    # Import modules - use no-cache version for debugging
    from database.connection_nocache import get_connection
    # Skip auth for now
    # from auth.auth_manager import get_auth_manager
    from pages._dashboard import show_dashboard

except ImportError as e:
    st.error(f"❌ Import error: {e}")
    st.stop()

st.set_page_config(page_title="Debug App", layout="wide")

st.title("🔍 Debug Mode")

# Test connection directly
try:
    supabase = get_connection()
    st.success("✅ Connection successful!")
except Exception as e:
    st.error(f"❌ Connection failed: {e}")
    st.stop()

# Test basic query
try:
    response = supabase.table('suppliers').select('id').limit(1).execute()
    st.success(f"✅ Query successful! Response: {response}")
except Exception as e:
    st.error(f"❌ Query failed: {e}")