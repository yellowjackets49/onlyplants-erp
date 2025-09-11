import streamlit as st
import os

st.write("Hello from Render!")
st.write(f"Environment variables found: {len(os.environ)}")

for key in ['SUPABASE_URL', 'SUPABASE_KEY', 'PORT']:
    value = os.getenv(key)
    st.write(f"{key}: {'Found' if value else 'Missing'}")
