"""Multi-Asset DCA Configuration UI Components."""

import streamlit as st
from typing import Dict, List
from ..config.models import AssetDCAConfig, MultiAssetDCAConfig
from ..utils.logging_config import get_logger

logger = get_logger(__name__)

# Supported assets with their display info (Updated Phase 1.4.1)
SUPPORTED_ASSETS = {
    "BTC": {
        "name": "Bitcoin",
        "icon": "₿",
        "default_base": 100.0,
        "default_min": 50.0,
        "default_max": 200.0,
        "trading_available": True,  # @140 on Hyperliquid
        "spot_index": 140,
    },
    "ETH": {
        "name": "Ethereum", 
        "icon": "Ξ",
        "default_base": 75.0,
        "default_min": 40.0,
        "default_max": 150.0,
        "trading_available": True,  # @147 on Hyperliquid
        "spot_index": 147,
    },
    "SOL": {
        "name": "Solana",
        "icon": "◎",
        "default_base": 50.0,
        "default_min": 25.0,
        "default_max": 100.0,
        "trading_available": True,  # @151 on Hyperliquid
        "spot_index": 151,
    },
    "AVAX": {
        "name": "Avalanche",
        "icon": "🔺",
        "default_base": 40.0,
        "default_min": 20.0,
        "default_max": 80.0,
        "trading_available": False,  # Not available on Hyperliquid spot
        "spot_index": None,
    },
    "LINK": {
        "name": "Chainlink",
        "icon": "🔗",
        "default_base": 30.0,
        "default_min": 15.0,
        "default_max": 60.0,
        "trading_available": False,  # Not available on Hyperliquid spot
        "spot_index": None,
    }
}


def render_asset_selector(current_assets: Dict[str, AssetDCAConfig]) -> List[str]:
    """Render asset selection interface."""
    st.subheader("🪙 Asset Selection")
    
    # Show currently selected assets
    current_symbols = list(current_assets.keys())
    
    # Asset selection with icons
    available_assets = list(SUPPORTED_ASSETS.keys())
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        selected_assets = st.multiselect(
            "Select Assets for DCA",
            options=available_assets,
            default=current_symbols,
            format_func=lambda x: f"{SUPPORTED_ASSETS[x]['icon']} {SUPPORTED_ASSETS[x]['name']} ({x}) {'🚀' if SUPPORTED_ASSETS[x]['trading_available'] else '📋'}",
            help="Choose which assets you want to DCA into. 🚀 = Real trading available, 📋 = Simulation only"
        )
    
    with col2:
        st.metric("Total Assets", len(selected_assets))
        
        if selected_assets:
            total_min = sum(SUPPORTED_ASSETS[asset]["default_min"] for asset in selected_assets)
            total_max = sum(SUPPORTED_ASSETS[asset]["default_max"] for asset in selected_assets)
            st.metric("Budget Range", f"${total_min:.0f} - ${total_max:.0f}")
    
    return selected_assets


def render_asset_configuration(asset: str, config: AssetDCAConfig = None) -> AssetDCAConfig:
    """Render configuration for a single asset."""
    asset_info = SUPPORTED_ASSETS[asset]
    
    # Use existing config or create default
    if config is None:
        config = AssetDCAConfig(
            symbol=asset,
            base_amount=asset_info["default_base"],
            min_amount=asset_info["default_min"],
            max_amount=asset_info["default_max"]
        )
    
    trading_status = "🚀 Real Trading" if asset_info.get('trading_available') else "📋 Simulation Only"
    with st.expander(f"{asset_info['icon']} {asset_info['name']} ({asset}) Configuration - {trading_status}", expanded=True):
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown(f"### 💰 **{asset} Investment Settings**")
            
            # Amount settings
            col_a, col_b, col_c = st.columns(3)
            
            with col_a:
                base_amount = st.number_input(
                    f"Base Amount ($)",
                    min_value=1.0,
                    max_value=10000.0,
                    value=float(config.base_amount),
                    step=5.0,
                    key=f"{asset}_base_amount",
                    help=f"Normal purchase amount for {asset}"
                )
            
            with col_b:
                min_amount = st.number_input(
                    f"Min Amount ($)",
                    min_value=1.0,
                    max_value=1000.0,
                    value=float(config.min_amount),
                    step=5.0,
                    key=f"{asset}_min_amount",
                    help=f"Minimum purchase amount"
                )
            
            with col_c:
                max_amount = st.number_input(
                    f"Max Amount ($)",
                    min_value=10.0,
                    max_value=10000.0,
                    value=float(config.max_amount),
                    step=10.0,
                    key=f"{asset}_max_amount",
                    help=f"Maximum purchase amount"
                )
            
            # Frequency and volatility settings
            col_d, col_e = st.columns(2)
            
            with col_d:
                frequency = st.selectbox(
                    f"Purchase Frequency",
                    options=["daily", "weekly", "monthly"],
                    index=["daily", "weekly", "monthly"].index(config.frequency),
                    key=f"{asset}_frequency",
                    help=f"How often to buy {asset}"
                )
            
            with col_e:
                volatility_window = st.number_input(
                    f"Volatility Window (days)",
                    min_value=7,
                    max_value=90,
                    value=config.volatility_window,
                    step=1,
                    key=f"{asset}_vol_window",
                    help="Days to calculate volatility over"
                )
            
            # Volatility thresholds
            st.markdown("#### 📊 Volatility-Based Position Sizing")
            col_f, col_g = st.columns(2)
            
            with col_f:
                low_vol_threshold = st.number_input(
                    f"Low Volatility Threshold (%)",
                    min_value=5.0,
                    max_value=50.0,
                    value=float(config.low_vol_threshold),
                    step=1.0,
                    key=f"{asset}_low_vol",
                    help="Below this volatility, buy maximum amount"
                )
            
            with col_g:
                high_vol_threshold = st.number_input(
                    f"High Volatility Threshold (%)",
                    min_value=30.0,
                    max_value=200.0,
                    value=float(config.high_vol_threshold),
                    step=5.0,
                    key=f"{asset}_high_vol",
                    help="Above this volatility, buy minimum amount"
                )
        
        with col2:
            st.markdown(f"### ⚙️ **{asset} Advanced Settings**")
            
            # Enable/disable asset
            enabled = st.checkbox(
                f"Enable {asset} DCA",
                value=config.enabled,
                key=f"{asset}_enabled",
                help=f"Enable or disable DCA for {asset}"
            )
            
            # Advanced indicators (Phase 2 features - for now just show as coming soon)
            st.markdown("#### 🧠 Smart Entry Signals")
            st.info("Advanced features coming in Phase 2:")
            
            # Phase 2 preview toggles (disabled for now)
            use_rsi = st.checkbox(
                "RSI-Based Entry",
                value=config.use_rsi,
                disabled=True,
                key=f"{asset}_use_rsi",
                help="Only buy when RSI indicates oversold conditions"
            )
            
            if use_rsi:
                rsi_threshold = st.slider(
                    "RSI Oversold Threshold",
                    min_value=20,
                    max_value=40,
                    value=int(config.rsi_oversold_threshold),
                    disabled=True,
                    key=f"{asset}_rsi_threshold"
                )
            else:
                rsi_threshold = config.rsi_oversold_threshold
            
            use_ma_dips = st.checkbox(
                "Moving Average Dips",
                value=config.use_ma_dips,
                disabled=True,
                key=f"{asset}_use_ma",
                help="Buy more when price dips below moving average"
            )
            
            use_dynamic_freq = st.checkbox(
                "Dynamic Frequency",
                value=config.use_dynamic_frequency,
                disabled=True,
                key=f"{asset}_dynamic_freq",
                help="Adjust frequency based on volatility"
            )
            
            # Quick stats preview
            st.markdown("#### 📈 Quick Stats")
            monthly_estimate = base_amount * 4.33 if frequency == "weekly" else (
                base_amount * 30 if frequency == "daily" else base_amount
            )
            st.metric("Est. Monthly Investment", f"${monthly_estimate:.0f}")
            
            volatility_range = high_vol_threshold - low_vol_threshold
            st.metric("Volatility Range", f"{volatility_range:.0f}%")
    
    # Create updated config
    updated_config = AssetDCAConfig(
        symbol=asset,
        base_amount=base_amount,
        min_amount=min_amount,
        max_amount=max_amount,
        frequency=frequency,
        volatility_window=volatility_window,
        low_vol_threshold=low_vol_threshold,
        high_vol_threshold=high_vol_threshold,
        enabled=enabled,
        use_rsi=use_rsi,
        rsi_oversold_threshold=rsi_threshold,
        use_ma_dips=use_ma_dips,
        use_dynamic_frequency=use_dynamic_freq
    )
    
    return updated_config


def render_portfolio_overview(asset_configs: Dict[str, AssetDCAConfig]):
    """Render portfolio overview with all assets."""
    st.subheader("📊 Portfolio Overview")
    
    if not asset_configs:
        st.info("No assets configured yet. Select assets above to get started.")
        return
    
    # Calculate totals
    enabled_assets = [config for config in asset_configs.values() if config.enabled]
    total_base = sum(config.base_amount for config in enabled_assets)
    total_min = sum(config.min_amount for config in enabled_assets)
    total_max = sum(config.max_amount for config in enabled_assets)
    
    # Overview metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Active Assets", len(enabled_assets))
    
    with col2:
        st.metric("Base Investment", f"${total_base:.0f}")
    
    with col3:
        st.metric("Min Range", f"${total_min:.0f}")
    
    with col4:
        st.metric("Max Range", f"${total_max:.0f}")
    
    # Asset breakdown table
    if enabled_assets:
        st.markdown("#### 📋 Asset Breakdown")
        
        asset_data = []
        for config in enabled_assets:
            asset_info = SUPPORTED_ASSETS[config.symbol]
            frequency_multiplier = {"daily": 30, "weekly": 4.33, "monthly": 1}[config.frequency]
            monthly_est = config.base_amount * frequency_multiplier
            
            asset_data.append({
                "Asset": f"{asset_info['icon']} {config.symbol}",
                "Base Amount": f"${config.base_amount:.0f}",
                "Frequency": config.frequency.title(),
                "Monthly Est.": f"${monthly_est:.0f}",
                "Vol. Range": f"{config.low_vol_threshold:.0f}% - {config.high_vol_threshold:.0f}%",
                "Status": "🟢 Active" if config.enabled else "🔴 Disabled"
            })
        
        import pandas as pd
        df = pd.DataFrame(asset_data)
        st.dataframe(df, use_container_width=True, hide_index=True)


def render_multi_asset_config_page(current_config: MultiAssetDCAConfig = None) -> MultiAssetDCAConfig:
    """Render the complete multi-asset configuration page."""
    st.title("🌟 Multi-Asset DCA Configuration")
    st.markdown("Configure independent DCA strategies for multiple cryptocurrencies.")
    
    # Initialize with current config or create new
    if current_config is None:
        current_config = MultiAssetDCAConfig(
            private_key="",  # Will be set from main config
            assets={}
        )
    
    # Asset selection
    selected_assets = render_asset_selector(current_config.assets)
    
    # Configure each selected asset
    new_asset_configs = {}
    
    if selected_assets:
        st.markdown("---")
        st.subheader("⚙️ Individual Asset Configuration")
        
        for asset in selected_assets:
            existing_config = current_config.assets.get(asset)
            new_config = render_asset_configuration(asset, existing_config)
            new_asset_configs[asset] = new_config
        
        # Portfolio overview
        st.markdown("---")
        render_portfolio_overview(new_asset_configs)
        
        # Global settings
        st.markdown("---")
        st.subheader("🌐 Global Settings")
        
        col1, col2 = st.columns(2)
        
        with col1:
            global_enabled = st.checkbox(
                "Enable Multi-Asset DCA",
                value=current_config.enabled,
                help="Master switch for all DCA operations"
            )
        
        with col2:
            notifications_enabled = st.checkbox(
                "Enable Notifications",
                value=current_config.notification_enabled,
                help="Get notified about trades and important events"
            )
        
        # Save configuration button
        st.markdown("---")
        if st.button("💾 Save Multi-Asset Configuration", type="primary", use_container_width=True):
            try:
                # Validate all configurations
                for config in new_asset_configs.values():
                    config.validate()
                
                # Create updated multi-asset config
                updated_config = MultiAssetDCAConfig(
                    private_key=current_config.private_key,
                    wallet_address=current_config.wallet_address,
                    assets=new_asset_configs,
                    enabled=global_enabled,
                    notification_enabled=notifications_enabled
                )
                
                updated_config.validate()
                st.success(f"✅ Configuration saved for {len(new_asset_configs)} assets!")
                return updated_config
                
            except ValueError as e:
                st.error(f"❌ Configuration Error: {e}")
                return current_config
    
    else:
        st.info("👆 Select at least one asset to configure your DCA strategy.")
    
    return current_config


def render_quick_asset_actions(asset_configs: Dict[str, AssetDCAConfig]):
    """Render quick action buttons for asset management."""
    if not asset_configs:
        return
    
    st.subheader("⚡ Quick Actions")
    
    cols = st.columns(min(len(asset_configs), 4))
    
    for i, (asset, config) in enumerate(asset_configs.items()):
        if i < len(cols):
            with cols[i]:
                asset_info = SUPPORTED_ASSETS[asset]
                
                # Asset status card
                status_color = "🟢" if config.enabled else "🔴"
                st.markdown(f"""
                <div style="padding: 1rem; border: 1px solid #ddd; border-radius: 0.5rem; text-align: center;">
                    <h4>{asset_info['icon']} {asset}</h4>
                    <p>{status_color} {config.frequency.title()}</p>
                    <p><strong>${config.base_amount:.0f}</strong></p>
                </div>
                """, unsafe_allow_html=True)
                
                # Quick toggle
                if st.button(f"Toggle {asset}", key=f"toggle_{asset}", use_container_width=True):
                    config.enabled = not config.enabled
                    st.rerun()