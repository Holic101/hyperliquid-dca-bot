"""
Hyperliquid DCA Bot - Main Application
Refactored modular version with separated concerns
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Third-party imports
import streamlit as st
from dotenv import load_dotenv

# Local imports
from src.config.loader import load_config
from src.trading.bot import HyperliquidDCABot
from src.ui.auth import init_session_state, handle_authentication, render_logout
from src.ui.dashboard import setup_page_config, render_dashboard, load_bot_config, initialize_bot
from src.utils.logging_config import setup_logging

# Load environment variables
load_dotenv()

# Setup logging
logger = setup_logging("dca_dashboard")


def main():
    """Main application entry point."""
    
    # Configure Streamlit page
    setup_page_config()
    
    # Initialize session state
    init_session_state()
    
    # Handle authentication
    if not handle_authentication():
        return
    
    # Show logout button in sidebar
    render_logout()
    
    # Load configuration
    if not st.session_state.config:
        st.session_state.config = load_bot_config()
    
    if not st.session_state.config:
        st.error("❌ Unable to load configuration. Please check your setup.")
        st.stop()
    
    # Initialize bot
    if not st.session_state.bot:
        st.session_state.bot = initialize_bot(st.session_state.config)
    
    if not st.session_state.bot:
        st.error("❌ Unable to initialize bot. Please check your configuration.")
        st.stop()
    
    # Render main dashboard
    try:
        render_dashboard(st.session_state.config, st.session_state.bot)
    except Exception as e:
        st.error(f"❌ Dashboard Error: {e}")
        logger.error(f"Dashboard rendering error: {e}", exc_info=True)


if __name__ == "__main__":
    main()