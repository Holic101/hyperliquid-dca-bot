"""Multi-Asset DCA Configuration Page."""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import streamlit as st
import os
from dotenv import load_dotenv

from src.config.models import MultiAssetDCAConfig
from src.config.loader import load_config, save_config
from src.ui.multi_asset_config import render_multi_asset_config_page
from src.utils.logging_config import get_logger

# Load environment variables
load_dotenv()

logger = get_logger(__name__)

def main():
    """Multi-Asset Configuration Page."""
    st.set_page_config(
        page_title="Multi-Asset DCA Config",
        page_icon="🌟",
        layout="wide"
    )
    
    try:
        # Load existing single-asset config for initialization
        existing_config = load_config()
        
        if not existing_config:
            st.error("❌ No base configuration found. Please configure the main DCA bot first.")
            st.info("💡 Go back to the main page to set up your private key and basic configuration.")
            return
        
        # Load or create multi-asset config
        multi_asset_config_file = os.path.join(os.path.dirname(existing_config.__dict__.get('config_file', '')), 'multi_asset_config.json')
        
        try:
            # Try loading existing multi-asset config
            if os.path.exists(multi_asset_config_file):
                import json
                with open(multi_asset_config_file, 'r') as f:
                    data = json.load(f)
                current_multi_config = MultiAssetDCAConfig.from_dict(data, existing_config.private_key)
            else:
                # Create new multi-asset config from existing single-asset config
                current_multi_config = MultiAssetDCAConfig(
                    private_key=existing_config.private_key,
                    wallet_address=existing_config.wallet_address,
                    assets={}
                )
        except Exception as e:
            logger.warning(f"Could not load existing multi-asset config: {e}")
            # Fallback to new config
            current_multi_config = MultiAssetDCAConfig(
                private_key=existing_config.private_key,
                wallet_address=existing_config.wallet_address,
                assets={}
            )
        
        # Render the configuration page
        updated_config = render_multi_asset_config_page(current_multi_config)
        
        # Save the configuration if it was updated
        if updated_config != current_multi_config:
            try:
                # Save multi-asset config to separate file
                import json
                config_data = updated_config.to_dict()
                
                with open(multi_asset_config_file, 'w') as f:
                    json.dump(config_data, f, indent=2)
                
                logger.info(f"Multi-asset configuration saved to {multi_asset_config_file}")
                
                # Store in session state for other pages to use
                st.session_state.multi_asset_config = updated_config
                
            except Exception as e:
                st.error(f"❌ Failed to save multi-asset configuration: {e}")
                logger.error(f"Failed to save multi-asset config: {e}")
        
    except Exception as e:
        st.error(f"❌ Error loading configuration page: {e}")
        logger.error(f"Multi-asset config page error: {e}")

if __name__ == "__main__":
    main()