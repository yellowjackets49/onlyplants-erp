import streamlit as st
import sys
import os

# Add path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)


def force_show_suppliers():
    """Force display suppliers with explicit container"""
    container = st.container()
    with container:
        st.write("🔍 Force suppliers called")
        st.subheader("🏭 Force Suppliers")
        st.success("This should definitely show!")

        # Add a form to test interactivity
        with st.form("test_form"):
            test_input = st.text_input("Test input")
            submitted = st.form_submit_button("Test button")
            if submitted:
                st.write(f"You entered: {test_input}")


def main():
    st.set_page_config(page_title="Simple Test", layout="wide")
    st.title("🔧 Simple Force Test")

    menu = ["Dashboard", "Suppliers"]
    choice = st.sidebar.selectbox("Menu", menu)

    # Debug info
    st.write(f"Choice: {choice}")
    st.write(f"Python path: {sys.path[0]}")

    # Force clear any previous content
    if choice == "Dashboard":
        st.subheader("📊 Forced Dashboard")
        st.write("Dashboard content")
        st.success("Dashboard working")
    elif choice == "Suppliers":
        force_show_suppliers()


if __name__ == "__main__":
    main()