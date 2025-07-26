"""Authentication components for Streamlit."""

import streamlit as st
import os
from ..utils.logging_config import get_logger

logger = get_logger(__name__)


def init_session_state():
    """Initialize Streamlit session state variables."""
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    if "bot" not in st.session_state:
        st.session_state.bot = None
    if "config" not in st.session_state:
        st.session_state.config = None


def handle_authentication() -> bool:
    """Handle user authentication and return True if authenticated."""
    
    if st.session_state.logged_in:
        return True
    
    st.title("🔐 Login")
    st.write("Please enter your password to access the DCA Bot dashboard.")
    
    with st.form("login_form"):
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login", use_container_width=True)
        
        if submit:
            expected_password = os.getenv("DCA_BOT_PASSWORD")
            if not expected_password:
                st.error("❌ No password configured. Please set DCA_BOT_PASSWORD in your .env file.")
                return False
                
            if password == expected_password:
                st.session_state.logged_in = True
                logger.info("User authenticated successfully")
                st.success("✅ Login successful!")
                st.rerun()
            else:
                logger.warning("Failed authentication attempt")
                st.error("❌ Invalid password. Please try again.")
    
    return False


def render_logout():
    """Render logout button in sidebar."""
    if st.sidebar.button("🚪 Logout"):
        st.session_state.logged_in = False
        st.session_state.bot = None
        st.session_state.config = None
        logger.info("User logged out")
        st.rerun()