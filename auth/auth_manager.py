import streamlit as st
from database.connection import get_connection
import time


class AuthManager:
    def __init__(self):
        self.supabase = get_connection()

    def initialize_auth_state(self):
        """Initialize authentication state"""
        if 'authenticated' not in st.session_state:
            st.session_state.authenticated = False
        if 'user' not in st.session_state:
            st.session_state.user = None
        if 'user_email' not in st.session_state:
            st.session_state.user_email = None

    def show_login_form(self):
        """Display login form"""
        st.markdown("### 🔐 Login to Inventory Management System")

        tab1, tab2 = st.tabs(["Login", "Register"])

        with tab1:
            self._show_login_tab()

        with tab2:
            self._show_register_tab()

    def _show_login_tab(self):
        """Show login tab"""
        with st.form("login_form"):
            email = st.text_input("Email", placeholder="your.email@company.com")
            password = st.text_input("Password", type="password")

            col1, col2 = st.columns([1, 3])
            with col1:
                login_btn = st.form_submit_button("🔑 Login", type="primary")

            if login_btn and email and password:
                if self._authenticate_user(email, password):
                    st.success("✅ Login successful!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("❌ Invalid credentials")

    def _show_register_tab(self):
        """Show registration tab"""
        st.info("💡 Register a new user account")

        with st.form("register_form"):
            email = st.text_input("Email", placeholder="your.email@company.com")
            password = st.text_input("Password", type="password")
            password_confirm = st.text_input("Confirm Password", type="password")
            full_name = st.text_input("Full Name", placeholder="John Doe")

            register_btn = st.form_submit_button("👤 Register", type="secondary")

            if register_btn and email and password:
                if password != password_confirm:
                    st.error("❌ Passwords don't match")
                elif len(password) < 6:
                    st.error("❌ Password must be at least 6 characters")
                else:
                    if self._register_user(email, password, full_name):
                        st.success("✅ Registration successful! You can now login.")
                    else:
                        st.error("❌ Registration failed")

    def _authenticate_user(self, email, password):
        """Authenticate user with Supabase"""
        try:
            response = self.supabase.auth.sign_in_with_password({
                "email": email,
                "password": password
            })

            if response.user:
                st.session_state.authenticated = True
                st.session_state.user = response.user
                st.session_state.user_email = email
                return True
            return False

        except Exception as e:
            st.error(f"Login error: {e}")
            return False

    def _register_user(self, email, password, full_name):
        """Register new user with Supabase"""
        try:
            response = self.supabase.auth.sign_up({
                "email": email,
                "password": password,
                "options": {
                    "data": {
                        "full_name": full_name
                    }
                }
            })

            if response.user:
                return True
            return False

        except Exception as e:
            st.error(f"Registration error: {e}")
            return False

    def logout(self):
        """Logout current user"""
        try:
            self.supabase.auth.sign_out()
            st.session_state.authenticated = False
            st.session_state.user = None
            st.session_state.user_email = None
            st.rerun()
        except Exception as e:
            st.error(f"Logout error: {e}")

    def is_authenticated(self):
        """Check if user is authenticated"""
        return st.session_state.get('authenticated', False)

    def get_user_info(self):
        """Get current user information"""
        return st.session_state.get('user'), st.session_state.get('user_email')

    def show_user_info(self):
        """Show user info in sidebar"""
        if self.is_authenticated():
            user, email = self.get_user_info()

            with st.sidebar:
                st.markdown("---")
                st.markdown("### 👤 User Info")
                st.write(f"**Email:** {email}")

                if st.button("🚪 Logout", type="secondary"):
                    self.logout()


# Create global auth manager instance
@st.cache_resource
def get_auth_manager():
    return AuthManager()