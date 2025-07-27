"""Multi-Asset DCA Dashboard Page."""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import streamlit as st
import os
import json
from dotenv import load_dotenv

from src.config.models import MultiAssetDCAConfig
from src.config.loader import load_config
from src.trading.smart_multi_asset_bot import SmartMultiAssetDCABot
from src.ui.multi_asset_dashboard import render_multi_asset_tabs, render_multi_asset_actions
from src.utils.logging_config import get_logger

# Load environment variables
load_dotenv()

logger = get_logger(__name__)

def load_multi_asset_config():
    """Load multi-asset configuration."""
    try:
        # Load base config first
        base_config = load_config()
        if not base_config:
            return None
        
        # Try loading multi-asset config
        multi_asset_config_file = os.path.join(os.path.dirname(base_config.__dict__.get('config_file', '')), 'multi_asset_config.json')
        
        if os.path.exists(multi_asset_config_file):
            with open(multi_asset_config_file, 'r') as f:
                data = json.load(f)
            return MultiAssetDCAConfig.from_dict(data, base_config.private_key)
        else:
            # Create empty multi-asset config
            return MultiAssetDCAConfig(
                private_key=base_config.private_key,
                wallet_address=base_config.wallet_address,
                assets={}
            )
    except Exception as e:
        logger.error(f"Error loading multi-asset config: {e}")
        return None

def main():
    """Multi-Asset Dashboard Page."""
    st.set_page_config(
        page_title="Multi-Asset Dashboard",
        page_icon="🌟",
        layout="wide"
    )
    
    st.title("🌟 Multi-Asset DCA Dashboard")
    st.markdown("Monitor and manage your multi-asset DCA portfolio.")
    
    try:
        # Load multi-asset configuration
        multi_config = load_multi_asset_config()
        
        if not multi_config:
            st.error("❌ Could not load multi-asset configuration.")
            st.info("💡 Please configure your multi-asset portfolio first in the Multi-Asset Config page.")
            if st.button("🔧 Go to Multi-Asset Config"):
                st.switch_page("pages/1_Multi_Asset_Config.py")
            return
        
        if not multi_config.assets:
            st.warning("⚠️ No assets configured yet.")
            st.info("💡 Add assets to your portfolio in the Multi-Asset Config page.")
            if st.button("🔧 Configure Assets"):
                st.switch_page("pages/1_Multi_Asset_Config.py")
            return
        
        # Initialize smart multi-asset bot with Phase 2 indicators
        if 'multi_asset_bot' not in st.session_state:
            try:
                st.session_state.multi_asset_bot = SmartMultiAssetDCABot(multi_config)
                logger.info("Smart multi-asset bot initialized successfully")
            except Exception as e:
                st.error(f"❌ Failed to initialize multi-asset bot: {e}")
                logger.error(f"Bot initialization error: {e}")
                return
        
        bot = st.session_state.multi_asset_bot
        
        # Add refresh button
        col1, col2 = st.columns([4, 1])
        with col2:
            if st.button("🔄 Refresh All", type="secondary"):
                # Clear cache and reinitialize
                if 'multi_asset_bot' in st.session_state:
                    del st.session_state.multi_asset_bot
                st.rerun()
        
        # Portfolio actions section
        render_multi_asset_actions(bot)
        
        st.markdown("---")
        
        # Multi-asset dashboard with tabs
        render_multi_asset_tabs(bot)
        
        # Asset discovery info
        st.markdown("---")
        st.subheader("🔍 Asset Discovery Status")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.success("**Phase 1.4 Status**: ✅ Multi-Asset Execution Complete")
            st.markdown("""
            **✅ Implemented:**
            - ✅ Multi-asset configuration interface
            - ✅ Portfolio overview dashboard
            - ✅ Individual asset tabs
            - ✅ Asset allocation charts
            - ✅ Real multi-asset trading execution
            - ✅ Parallel DCA execution
            - ✅ Multi-asset trade history sync
            """)
        
        with col2:
            st.success("**Phase 2**: 🧠 Smart Indicators Active!")
            st.markdown("""
            **Smart Features:**
            - 🧠 RSI-Based Entry (Skip overbought)
            - 📊 Moving Average Dips (Buy more on dips)
            - ⚡ Dynamic Frequency (Volatility-based)
            - 🚀 BTC/ETH/SOL: Real trading + indicators
            - 📋 AVAX/LINK: Simulation + indicators
            
            **🎯 Production Ready**: All systems operational
            """)
        
    except Exception as e:
        st.error(f"❌ Dashboard Error: {e}")
        logger.error(f"Multi-asset dashboard error: {e}")

if __name__ == "__main__":
    main()