import streamlit as st
import time

class AuthManager:
    def __init__(self):
        # Don't initialize Supabase in __init__ - do it later
        self.supabase = None

    def initialize_auth_state(self):
        """Initialize authentication state - temporary bypass for debugging"""
        st.write("🔍 Debug: Initializing auth state...")
        
        # Temporary: Always authenticate for development
        st.session_state.authenticated = True
        st.session_state.user = {"id": 1, "email": "admin@company.com", "full_name": "Administrator"}
        st.session_state.user_email = "admin@company.com"
        
        st.write("✅ Debug: Auth bypassed for debugging")

    def show_login_form(self):
        """Display login form - temporary bypass"""
        st.info("🚀 Authentication temporarily disabled for development")
        st.info("The app will load automatically...")

    def logout(self):
        """Logout current user"""
        st.session_state.authenticated = False
        st.session_state.user = None
        st.session_state.user_email = None
        st.rerun()

    def is_authenticated(self):
        """Check if user is authenticated - always true for development"""
        return True

    def get_user_info(self):
        """Get current user information"""
        return st.session_state.get('user'), st.session_state.get('user_email')

    def show_user_info(self):
        """Show user info in sidebar"""
        with st.sidebar:
            st.markdown("---")
            st.markdown("### 👤 User Info")
            st.write("**Email:** admin@company.com")
            st.write("**Mode:** Development/Debug")

            if st.button("🚪 Logout", type="secondary"):
                self.logout()

# Create global auth manager instance
@st.cache_resource
def get_auth_manager():
    return AuthManager()