import streamlit as st
import psycopg2
import os
from urllib.parse import urlparse

@st.cache_resource
def get_connection():
    """Get database connection (cached)"""
    try:
        # Try different ways to get DATABASE_URL from secrets
        database_url = None
        
        # First try: st.secrets["db"]["DATABASE_URL"]
        try:
            database_url = st.secrets["db"]["DATABASE_URL"]
        except KeyError:
            pass
        
        # Second try: st.secrets["DATABASE_URL"]
        if not database_url:
            try:
                database_url = st.secrets["DATABASE_URL"]
            except KeyError:
                pass
        
        # Third try: environment variable as fallback
        if not database_url:
            database_url = os.getenv("DATABASE_URL")
        
        if not database_url:
            st.error("❌ DATABASE_URL not found in secrets or environment variables.")
            st.error("Please check your .streamlit/secrets.toml file structure.")
            st.stop()
        
        # Parse the DATABASE_URL
        parsed = urlparse(database_url)
        
        conn = psycopg2.connect(
            host=parsed.hostname,
            database=parsed.path[1:],  # Remove leading slash
            user=parsed.username,
            password=parsed.password,
            port=parsed.port or 5432,
            sslmode='require'  # Required for Supabase
        )
        
        return conn
        
    except psycopg2.OperationalError as e:
        st.error(f"❌ Could not connect to PostgreSQL: {e}")
        st.stop()
    except Exception as e:
        st.error(f"❌ Database connection error: {e}")
        st.stop()

def get_cursor():
    """Get database cursor"""
    conn = get_connection()
    return conn, conn.cursor()