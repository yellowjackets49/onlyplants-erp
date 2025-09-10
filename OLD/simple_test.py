import streamlit as st


def main():
    st.set_page_config(page_title="Simple Test", layout="wide")
    st.title("🧪 Simple Navigation Test")

    menu = ["Dashboard", "Suppliers"]
    choice = st.sidebar.selectbox("Menu", menu)

    st.write(f"Selected: {choice}")

    if choice == "Dashboard":
        st.subheader("📊 Dashboard")
        st.write("Dashboard content here")
        st.success("Dashboard working!")

    elif choice == "Suppliers":
        st.subheader("🏭 Suppliers")
        st.write("Suppliers content here")
        st.success("Suppliers working!")


if __name__ == "__main__":
    main()