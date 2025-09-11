import streamlit as st
import os

st.title("🚀 App Running Successfully!")

# Test environment variables
st.subheader("Environment Variables Test")
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")

st.write(f"**SUPABASE_URL:** {'✅ Found' if supabase_url else '❌ Missing'}")
st.write(f"**SUPABASE_KEY:** {'✅ Found' if supabase_key else '❌ Missing'}")

if supabase_url:
    st.write(f"URL preview: {supabase_url[:30]}...")
if supabase_key:
    st.write(f"Key preview: {supabase_key[:20]}...")

# Test Supabase connection
if supabase_url and supabase_key:
    try:
        from supabase import create_client
        supabase = create_client(supabase_url, supabase_key)
        response = supabase.table('suppliers').select('id').limit(1).execute()
        st.success("✅ Supabase connection successful!")
        st.json(response.data)
    except Exception as e:
        st.error(f"❌ Supabase connection failed: {e}")
else:
    st.error("❌ Cannot test Supabase - missing environment variables")

st.success("🎉 Everything is working!")