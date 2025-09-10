import streamlit as st

st.title("Basic Test")
choice = st.sidebar.selectbox("Menu", ["Page 1", "Page 2"])

if choice == "Page 1":
    st.header("This is Page 1")
    st.write("Page 1 content")
elif choice == "Page 2":
    st.header("This is Page 2")
    st.write("Page 2 content")

st.write(f"Current choice: {choice}")