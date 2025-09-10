import streamlit as st
import psycopg2
import os
from urllib.parse import urlparse

@st.cache_resource
def get_connection():
    """Get database connection (cached)"""
    try:
        # Try to get DATABASE_URL from secrets in different formats
        database_url = None
        
        try:
            # Try direct DATABASE_URL first
            database_url = st.secrets["DATABASE_URL"]
        except KeyError:
            try:
                # Try supabase format
                url = st.secrets["supabase"]["url"] 
                # Convert Supabase URL to PostgreSQL connection string
                database_url = f"postgresql://postgres:xubqab-hiphyK-4qeqcy@db.abhphxmehiitqhbyenut.supabase.co:5432/postgres"
            except KeyError:
                # Fallback to environment variable
                database_url = os.getenv("DATABASE_URL")
        
        if not database_url:
            # Final fallback - hardcoded for your Supabase
            database_url = "postgresql://postgres:xubqab-hiphyK-4qeqcy@db.abhphxmehiitqhbyenut.supabase.co:5432/postgres"
        
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