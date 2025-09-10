import streamlit as st
import os
from supabase import create_client, Client

@st.cache_resource
def get_supabase_client():
    """Get Supabase client (cached)"""
    try:
        # Try to get from Streamlit secrets first
        try:
            url = st.secrets["supabase"]["url"]
            key = st.secrets["supabase"]["key"]
        except KeyError:
            # Fallback to environment variables
            url = os.getenv("SUPABASE_URL")
            key = os.getenv("SUPABASE_KEY")
        
        if not url or not key:
            st.error("❌ Supabase URL and key not found in secrets or environment variables.")
            st.error("Please add them to your .streamlit/secrets.toml file.")
            st.stop()
        
        supabase: Client = create_client(url, key)
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
    return client, client  # Return client twice for compatibility