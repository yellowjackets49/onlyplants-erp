import streamlit as st
import psycopg2
import os

def get_connection():
    """Get database connection (non-cached for debugging)"""
    try:
        db_cfg = st.secrets["db"]
    except Exception:
        db_cfg = {}

    host = db_cfg.get("host") or os.getenv("PGHOST", "127.0.0.1")
    database = db_cfg.get("database") or os.getenv("PGDATABASE", "inventory")
    user = db_cfg.get("user") or os.getenv("PGUSER", "admin")
    password = db_cfg.get("password") or os.getenv("PGPASSWORD", "admin")
    port = int(db_cfg.get("port") or os.getenv("PGPORT", "5432"))

    try:
        conn = psycopg2.connect(
            host=host,
            database=database,
            user=user,
            password=password,
            port=port,
        )
        return conn
    except psycopg2.OperationalError as e:
        st.error(f"Could not connect to PostgreSQL: {e}")
        st.stop()

def get_cursor():
    """Get database cursor"""
    conn = get_connection()
    return conn, conn.cursor()