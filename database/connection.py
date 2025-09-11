import streamlit as st
import os
from supabase import create_client

@st.cache_resource
def get_supabase_client():
    """Get Supabase client (cached) using environment variables"""
    try:
        # Debug: Show what we're trying to get
        st.write("🔍 Debug: Looking for environment variables...")
        
        # Get credentials from environment variables
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")
        
        # Debug: Show what we found (without exposing full keys)
        st.write(f"SUPABASE_URL found: {'Yes' if supabase_url else 'No'}")
        st.write(f"SUPABASE_KEY found: {'Yes' if supabase_key else 'No'}")
        
        if supabase_url:
            st.write(f"URL starts with: {supabase_url[:20]}...")
        if supabase_key:
            st.write(f"Key starts with: {supabase_key[:20]}...")
        
        # Check if credentials are available
        if not supabase_url or not supabase_key:
            raise Exception(
                "Missing Supabase credentials. Please set environment variables:\n"
                "- SUPABASE_URL\n" 
                "- SUPABASE_KEY"
            )
        
        supabase = create_client(supabase_url, supabase_key)
        st.write("✅ Supabase client created successfully")
        return supabase
        
    except Exception as e:
        st.error(f"❌ Supabase connection error: {e}")
        st.error("Please check your environment variables are set correctly")
        
        # Debug: Show all environment variables (be careful in production)
        st.write("🔍 Debug: All environment variables containing 'SUPABASE':")
        for key, value in os.environ.items():
            if 'SUPABASE' in key.upper():
                st.write(f"{key}: {value[:20] if value else 'None'}...")
        
        st.stop()

def get_connection():
    """Get Supabase client (for backward compatibility)"""
    return get_supabase_client()