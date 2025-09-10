import streamlit as st
import os
from supabase import create_client

@st.cache_resource
def get_supabase_client():
    """Get Supabase client (cached)"""
    try:
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["key"]
        supabase = create_client(url, key)
        return supabase
    except Exception as e:
        st.error(f"❌ Supabase connection error: {e}")
        st.stop()

def get_connection():
    """Get Supabase client (for backward compatibility)"""
    return get_supabase_client()

def get_cursor():
    """Get Supabase client (for backward compatibility with existing code)"""
    client = get_supabase_client()
    return client, client