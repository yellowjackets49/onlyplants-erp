import streamlit as st
import sys
import os

st.write("🔍 Python path:")
for path in sys.path:
    st.write(f"  - {path}")

st.write(f"🔍 Current working directory: {os.getcwd()}")

st.write("🔍 Files in current directory:")
for item in os.listdir("."):
    st.write(f"  - {item}")

if os.path.exists("pages"):
    st.write("🔍 Files in pages directory:")
    for item in os.listdir("pages"):
        st.write(f"  - pages/{item}")

# Test imports one by one
try:
    from database.connection import get_connection

    st.success("✅ database.connection import successful")
except Exception as e:
    st.error(f"❌ database.connection import failed: {e}")

try:
    from pages.dashboard import show_dashboard

    st.success("✅ pages.dashboard import successful")

    # Test if function exists
    if callable(show_dashboard):
        st.success("✅ show_dashboard is callable")
    else:
        st.error("❌ show_dashboard is not callable")

except Exception as e:
    st.error(f"❌ pages.dashboard import failed: {e}")

# Simple test
menu = ["Dashboard"]
choice = st.sidebar.selectbox("Menu", menu)

if choice == "Dashboard":
    st.write("About to call show_dashboard...")
    try:
        show_dashboard()
        st.write("show_dashboard completed")
    except Exception as e:
        st.error(f"show_dashboard failed: {e}")
        import traceback

        st.code(traceback.format_exc())