import streamlit as st
import os
from supabase import create_client

def get_supabase_client():
    """Get Supabase client (no caching for debugging)"""
    try:
        st.write("🔍 Getting environment variables...")
        
        # Get credentials from environment variables
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")
        
        st.write(f"URL: {'Found' if supabase_url else 'Missing'}")
        st.write(f"Key: {'Found' if supabase_key else 'Missing'}")
        
        if not supabase_url or not supabase_key:
            raise Exception(f"Missing env vars: URL={bool(supabase_url)}, KEY={bool(supabase_key)}")
        
        supabase = create_client(supabase_url, supabase_key)
        st.write("✅ Supabase client created")
        return supabase
        
    except Exception as e:
        st.error(f"❌ Connection error: {e}")
        st.stop()

def get_connection():
    return get_supabase_client()