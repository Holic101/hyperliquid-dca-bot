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
    
    # Check if user should be redirected to multi-asset system
    from src.utils.migration import check_migration_needed
    
    # Load configuration
    if not st.session_state.config:
        st.session_state.config = load_bot_config()
    
    # Handle new users or users who should use multi-asset directly
    if not st.session_state.config:
        # New user - redirect to multi-asset setup
        st.title("🌟 Welcome to Hyperliquid DCA Bot!")
        st.success("🎉 **You're starting with the latest Multi-Asset DCA system with smart indicators!**")
        
        st.markdown("""
        ### 🚀 Getting Started
        
        **Your DCA bot supports:**
        - 🧠 **Smart Indicators**: RSI-based entry, Moving Average dips
        - 🌟 **Multiple Assets**: BTC, ETH, SOL, AVAX, LINK
        - 📊 **Individual Strategies**: Custom settings per asset
        - ⚡ **Dynamic Frequency**: Volatility-based timing
        
        **Next Steps:**
        1. Click "Setup Multi-Asset Config" below
        2. Choose your assets (we recommend starting with BTC + ETH)
        3. Configure your DCA amounts and frequency
        4. Enable smart indicators for better entry timing
        """)
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("🚀 Setup Multi-Asset Config", type="primary", use_container_width=True):
                st.switch_page("pages/1_Multi_Asset_Config.py")
        
        st.markdown("---")
        st.info("💡 **Need help?** The Multi-Asset Config page has comprehensive guides for beginners!")
        return
    
    # Existing user - check if migration is needed
    if not check_migration_needed():
        # User already has multi-asset setup - redirect them there
        st.title("🌟 Hyperliquid Multi-Asset DCA")
        st.success("✅ **Multi-Asset DCA System Active** - Your advanced DCA setup is ready!")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🌟 Multi-Asset Config", type="primary", use_container_width=True):
                st.switch_page("pages/1_Multi_Asset_Config.py")
        with col2:
            if st.button("📊 Multi-Asset Dashboard", type="primary", use_container_width=True):
                st.switch_page("pages/2_Multi_Asset_Dashboard.py")
        
        st.markdown("---")
        st.info("🎯 **Quick Access**: Use the buttons above to manage your multi-asset portfolio with smart indicators!")
        
        # Still show legacy interface for completeness
        st.markdown("---")
        st.subheader("📊 Legacy Interface")
        st.caption("Single-asset interface (legacy support only)")
        
        # Initialize bot for legacy interface
        if not st.session_state.bot:
            st.session_state.bot = initialize_bot(st.session_state.config)
        
        if st.session_state.bot:
            try:
                render_dashboard(st.session_state.config, st.session_state.bot)
            except Exception as e:
                st.error(f"❌ Dashboard Error: {e}")
                logger.error(f"Dashboard rendering error: {e}", exc_info=True)
        return
    
    # User needs migration from single-asset to multi-asset
    # Initialize bot
    if not st.session_state.bot:
        st.session_state.bot = initialize_bot(st.session_state.config)
    
    if not st.session_state.bot:
        st.error("❌ Unable to initialize bot. Please check your configuration.")
        st.stop()
    
    # Render main dashboard with migration interface
    try:
        render_dashboard(st.session_state.config, st.session_state.bot)
    except Exception as e:
        st.error(f"❌ Dashboard Error: {e}")
        logger.error(f"Dashboard rendering error: {e}", exc_info=True)


if __name__ == "__main__":
    main()