import streamlit as st
import os
from supabase import create_client

@st.cache_resource
def get_supabase_client():
    """Get Supabase client (cached) using environment variables"""
    try:
        # Get credentials from environment variables
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")
        
        # Check if credentials are available
        if not supabase_url or not supabase_key:
            raise Exception(
                "Missing Supabase credentials. Please set environment variables:\n"
                "- SUPABASE_URL\n" 
                "- SUPABASE_KEY"
            )
        
        supabase = create_client(supabase_url, supabase_key)
        return supabase
        
    except Exception as e:
        st.error(f"❌ Supabase connection error: {e}")
        st.error("Please check your environment variables are set correctly")
        st.stop()

def get_connection():
    """Get Supabase client (for backward compatibility)"""
    return get_supabase_client()