"""Configuration loading and saving utilities."""

import json
import os
import logging
from pathlib import Path
from typing import Optional
import eth_account
from .models import DCAConfig

logger = logging.getLogger(__name__)

CONFIG_FILE = "dca_config.json"


def load_config() -> Optional[DCAConfig]:
    """Load configuration with automatic fallback and creation for dev environment."""
    
    # First, try to get essential info from environment variables
    wallet_address = os.getenv("HYPERLIQUID_WALLET_ADDRESS")
    private_key = os.getenv("HYPERLIQUID_PRIVATE_KEY", "")
    
    # If no wallet address but we have private key, derive it
    if not wallet_address and private_key:
        try:
            account = eth_account.Account.from_key(private_key)
            wallet_address = account.address
            logger.info(f"Derived wallet address from private key: {wallet_address}")
        except Exception as e:
            logger.error(f"Error deriving wallet address from private key: {e}")
            return None
    
    # Load or create config file
    config_data = {}
    try:
        with open(CONFIG_FILE, 'r') as f:
            config_data = json.load(f)
            logger.info(f"Loaded existing config from {CONFIG_FILE}")
    except FileNotFoundError:
        # Create default config file for development
        logger.info(f"{CONFIG_FILE} not found, creating default config...")
        
        default_config = {
            "base_amount": 50.0,
            "min_amount": 25.0, 
            "max_amount": 100.0,
            "frequency": "weekly",
            "volatility_window": 30,
            "low_vol_threshold": 35.0,
            "high_vol_threshold": 85.0,
            "enabled": True
        }
        
        # Add wallet_address to config if we have it
        if wallet_address:
            default_config["wallet_address"] = wallet_address
            
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(default_config, f, indent=2)
            logger.info(f"Created default {CONFIG_FILE} file")
            config_data = default_config
        except Exception as e:
            logger.warning(f"Could not create {CONFIG_FILE}: {e}. Using memory-only config.")
            config_data = default_config
            
    except Exception as e:
        logger.error(f"Error loading config: {e}")
        return None
    
    try:
        # Priority order: Environment variables > Config file
        final_wallet_address = wallet_address or config_data.get("wallet_address")
        final_private_key = private_key or config_data.get("private_key", "")

        if not final_wallet_address:
            logger.error("Wallet address not found in environment variables or config file")
            return None

        config = DCAConfig(
            wallet_address=final_wallet_address,
            private_key=final_private_key,
            **{k: v for k, v in config_data.items() if k not in ["wallet_address", "private_key"]}
        )
        
        # Validate configuration
        config.validate()
        return config
        
    except Exception as e:
        logger.error(f"Error creating config: {e}")
        return None


def save_config(config: DCAConfig) -> bool:
    """Save configuration to file."""
    try:
        # Create directory if it doesn't exist
        Path(CONFIG_FILE).parent.mkdir(parents=True, exist_ok=True)
        
        save_data = config.to_dict()
        
        with open(CONFIG_FILE, 'w') as f:
            json.dump(save_data, f, indent=2)
        
        logger.info(f"Configuration saved to {CONFIG_FILE}")
        return True
        
    except Exception as e:
        logger.error(f"Error saving config: {e}")
        return False


def _create_default_config_file(config: DCAConfig) -> bool:
    """Create a default configuration file."""
    try:
        # Create directory if it doesn't exist
        Path(CONFIG_FILE).parent.mkdir(parents=True, exist_ok=True)
        
        default_data = config.to_dict()
        
        with open(CONFIG_FILE, 'w') as f:
            json.dump(default_data, f, indent=2)
        
        logger.info(f"Created default configuration file: {CONFIG_FILE}")
        return True
        
    except Exception as e:
        logger.error(f"Error creating default config file: {e}")
        return False