"""
Migration utilities for upgrading from single-asset to multi-asset DCA.
"""

import os
import json
from typing import Optional
from ..config.models import DCAConfig, AssetDCAConfig, MultiAssetDCAConfig
from ..utils.logging_config import get_logger

logger = get_logger(__name__)


def migrate_single_to_multi_asset(single_config: DCAConfig) -> MultiAssetDCAConfig:
    """
    Migrate a single-asset DCA configuration to multi-asset format.
    
    Args:
        single_config: Existing single-asset configuration
        
    Returns:
        New multi-asset configuration with BTC asset configured
    """
    logger.info("Migrating single-asset configuration to multi-asset format")
    
    # Create BTC asset configuration from single-asset config
    btc_config = AssetDCAConfig(
        symbol="BTC",
        base_amount=single_config.base_amount,
        min_amount=single_config.min_amount,
        max_amount=single_config.max_amount,
        frequency=single_config.frequency,
        volatility_window=single_config.volatility_window,
        low_vol_threshold=single_config.low_vol_threshold,
        high_vol_threshold=single_config.high_vol_threshold,
        enabled=single_config.enabled,
        # Enable smart indicators by default for migrated configs
        use_rsi=True,
        rsi_period=14,
        rsi_oversold_threshold=30.0,
        rsi_overbought_threshold=70.0,
        use_ma_dips=True,
        ma_periods="20,50,200",
        ma_type="SMA",
        ma_dip_thresholds="2,5,10"
    )
    
    # Create multi-asset configuration
    multi_config = MultiAssetDCAConfig(
        private_key=single_config.private_key,
        wallet_address=single_config.wallet_address,
        assets={"BTC": btc_config},
        enabled=single_config.enabled,
        notification_enabled=True
    )
    
    logger.info("Successfully migrated single-asset config with smart indicators enabled")
    return multi_config


def save_multi_asset_config(multi_config: MultiAssetDCAConfig, config_dir: str) -> bool:
    """
    Save multi-asset configuration to file.
    
    Args:
        multi_config: Multi-asset configuration to save
        config_dir: Directory to save configuration in
        
    Returns:
        True if saved successfully, False otherwise
    """
    try:
        config_file = os.path.join(config_dir, 'multi_asset_config.json')
        
        # Create directory if it doesn't exist
        os.makedirs(config_dir, exist_ok=True)
        
        # Convert to dictionary and save
        config_data = multi_config.to_dict()
        
        with open(config_file, 'w') as f:
            json.dump(config_data, f, indent=2)
        
        logger.info(f"Multi-asset configuration saved to {config_file}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to save multi-asset configuration: {e}")
        return False


def backup_single_asset_config(single_config: DCAConfig, config_dir: str) -> bool:
    """
    Create a backup of the single-asset configuration before migration.
    
    Args:
        single_config: Single-asset configuration to backup
        config_dir: Directory to save backup in
        
    Returns:
        True if backup created successfully, False otherwise
    """
    try:
        from datetime import datetime
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = os.path.join(config_dir, f'single_asset_config_backup_{timestamp}.json')
        
        # Create directory if it doesn't exist
        os.makedirs(config_dir, exist_ok=True)
        
        # Save backup
        config_data = {
            "base_amount": single_config.base_amount,
            "min_amount": single_config.min_amount,
            "max_amount": single_config.max_amount,
            "frequency": single_config.frequency,
            "volatility_window": single_config.volatility_window,
            "low_vol_threshold": single_config.low_vol_threshold,
            "high_vol_threshold": single_config.high_vol_threshold,
            "enabled": single_config.enabled,
            "wallet_address": single_config.wallet_address,
            "migration_timestamp": timestamp
        }
        
        with open(backup_file, 'w') as f:
            json.dump(config_data, f, indent=2)
        
        logger.info(f"Single-asset configuration backup saved to {backup_file}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to create backup: {e}")
        return False


def check_migration_needed() -> bool:
    """
    Check if migration from single-asset to multi-asset is needed.
    
    Returns:
        True if migration is needed, False otherwise
    """
    try:
        from ..config.loader import load_config
        
        # Try to load existing single-asset config
        single_config = load_config()
        if not single_config:
            return False
        
        # Check if multi-asset config already exists
        config_dir = os.path.dirname(single_config.__dict__.get('config_file', ''))
        multi_asset_file = os.path.join(config_dir, 'multi_asset_config.json')
        
        # Migration needed if single-asset exists but multi-asset doesn't
        migration_needed = not os.path.exists(multi_asset_file)
        
        if migration_needed:
            logger.info("Migration from single-asset to multi-asset needed")
        else:
            logger.info("Multi-asset configuration already exists, no migration needed")
        
        return migration_needed
        
    except Exception as e:
        logger.error(f"Error checking migration status: {e}")
        return False


def perform_migration() -> Optional[MultiAssetDCAConfig]:
    """
    Perform the complete migration from single-asset to multi-asset.
    
    Returns:
        New multi-asset configuration if successful, None otherwise
    """
    try:
        from ..config.loader import load_config
        
        logger.info("Starting migration from single-asset to multi-asset")
        
        # Load existing single-asset config
        single_config = load_config()
        if not single_config:
            logger.error("No single-asset configuration found to migrate")
            return None
        
        # Determine config directory
        config_dir = os.path.dirname(single_config.__dict__.get('config_file', ''))
        if not config_dir:
            config_dir = os.path.expanduser("~/.hyperliquid_dca")
        
        # Create backup
        backup_success = backup_single_asset_config(single_config, config_dir)
        if not backup_success:
            logger.warning("Failed to create backup, but continuing with migration")
        
        # Perform migration
        multi_config = migrate_single_to_multi_asset(single_config)
        
        # Save new multi-asset configuration
        save_success = save_multi_asset_config(multi_config, config_dir)
        if not save_success:
            logger.error("Failed to save migrated configuration")
            return None
        
        logger.info("Migration completed successfully!")
        logger.info("Your existing BTC configuration has been migrated with smart indicators enabled")
        logger.info("You can now add additional assets (ETH, SOL, etc.) in the Multi-Asset Config page")
        
        return multi_config
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        return None


def get_migration_summary(single_config: DCAConfig) -> dict:
    """
    Get a summary of what will be migrated.
    
    Args:
        single_config: Single-asset configuration to analyze
        
    Returns:
        Dictionary with migration summary information
    """
    return {
        "current_setup": {
            "asset": "BTC (single-asset)",
            "base_amount": f"${single_config.base_amount:.0f}",
            "frequency": single_config.frequency,
            "volatility_range": f"{single_config.low_vol_threshold:.0f}% - {single_config.high_vol_threshold:.0f}%",
            "enabled": single_config.enabled
        },
        "after_migration": {
            "asset": "BTC (in multi-asset portfolio)",
            "base_amount": f"${single_config.base_amount:.0f}",
            "frequency": single_config.frequency,
            "volatility_range": f"{single_config.low_vol_threshold:.0f}% - {single_config.high_vol_threshold:.0f}%",
            "smart_indicators": "✅ RSI + Moving Average Dips enabled",
            "additional_assets": "Ready to add ETH, SOL, AVAX, LINK",
            "enabled": single_config.enabled
        },
        "benefits": [
            "🧠 Smart indicators for better entry timing",
            "📊 Moving average dip detection",
            "🌟 Add multiple assets to your portfolio",
            "📈 Individual strategies per asset",
            "🎯 Advanced portfolio management"
        ]
    }