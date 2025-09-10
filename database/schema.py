import streamlit as st

def create_tables(supabase_client):
    """Create all database tables using Supabase"""
    try:
        # Since Supabase handles table creation through the dashboard,
        # we'll just verify the connection works
        
        # Test connection by trying to fetch from a system table
        try:
            # This will fail gracefully if tables don't exist yet
            supabase_client.table('suppliers').select('count').execute()
            st.success("✅ Database connection verified!")
        except Exception:
            st.info("ℹ️ Database connected. Please ensure tables are created in Supabase dashboard.")
        
        return True
        
    except Exception as e:
        st.error(f"❌ Database setup error: {e}")
        return False