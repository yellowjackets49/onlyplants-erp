import streamlit as st
import psycopg2
import os
from urllib.parse import urlparse

@st.cache_resource
def get_connection():
    """Get database connection (cached)"""
    try:
        # Get DATABASE_URL from Streamlit secrets
        database_url = st.secrets["db"]["DATABASE_URL"]
        
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
        
    except KeyError:
        st.error("❌ DATABASE_URL not found in secrets. Please add it to your Streamlit secrets.")
        st.stop()
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