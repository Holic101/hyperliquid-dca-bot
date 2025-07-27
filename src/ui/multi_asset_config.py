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
    
    # Educational section for beginners
    with st.expander("💡 What is Dollar-Cost Averaging (DCA)?", expanded=False):
        st.markdown("""
        **Dollar-Cost Averaging (DCA)** is a simple investment strategy where you buy a fixed amount of an asset at regular intervals, regardless of its price.
        
        **Why DCA works:**
        - **Reduces timing risk**: You don't need to guess the "perfect" time to buy
        - **Smooths volatility**: Buying at different prices averages out market ups and downs
        - **Builds discipline**: Automated investing removes emotional decisions
        - **Accessible**: You can start with small amounts
        
        **Example**: Instead of buying $1,200 of Bitcoin once, you buy $100 every month for 12 months.
        """)
    
    with st.expander("🎯 Choosing Your Assets - Beginner's Guide", expanded=False):
        st.markdown("""
        **For beginners, we recommend starting with 1-3 major assets:**
        
        **🥇 Tier 1 (Safest/Most Established)**:
        - **₿ Bitcoin (BTC)**: Digital gold, most established cryptocurrency
        - **Ξ Ethereum (ETH)**: Platform for smart contracts and DeFi
        
        **🥈 Tier 2 (Established but more volatile)**:
        - **◎ Solana (SOL)**: Fast, low-cost blockchain platform
        
        **🥉 Tier 3 (Smaller, higher risk/reward)**:
        - **🔺 Avalanche (AVAX)**: Competitor to Ethereum
        - **🔗 Chainlink (LINK)**: Oracle network connecting blockchains
        
        **💡 Beginner Strategy**: Start with 60% BTC, 30% ETH, 10% SOL
        """)
    
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
    
    # Add educational content at the top
    st.markdown("")
    with st.expander(f"📚 {asset} Configuration Guide - Read This First!", expanded=False):
        st.markdown(f"""
        **Setting up your {asset_info['name']} DCA Strategy:**
        
        **💰 Investment Amounts:**
        - **Base Amount**: Your normal purchase size (e.g., $100). This is what you'll buy most of the time.
        - **Min Amount**: Smallest purchase during high volatility (e.g., $50). When the market is very volatile, buy less.
        - **Max Amount**: Largest purchase during low volatility (e.g., $200). When the market is calm, buy more.
        
        **📅 Frequency:**
        - **Daily**: Best for small amounts ($10-50). More opportunities to catch dips.
        - **Weekly**: Good middle ground ($50-200). Recommended for most people.
        - **Monthly**: Best for larger amounts ($200+). Less frequent but larger purchases.
        
        **📊 Volatility Settings:**
        - **Low Volatility Threshold**: When {asset} is "calm" (recommended: 20-30%)
        - **High Volatility Threshold**: When {asset} is "crazy" (recommended: 50-80%)
        - The bot automatically adjusts your purchase size based on market conditions!
        
        **🧠 Smart Indicators (Advanced):**
        - **RSI**: Avoids buying when price might be too high
        - **Moving Average Dips**: Buys more when there's a good discount
        - **Dynamic Frequency**: Changes how often you buy based on market conditions
        
        **💡 Beginner Recommendation for {asset}:**
        - Base: ${asset_info['default_base']}, Min: ${asset_info['default_min']}, Max: ${asset_info['default_max']}
        - Frequency: Weekly
        - Enable RSI and MA Dips for smarter entry points
        """)
    
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
                    help=f"💡 Your regular purchase amount. Start with what you can afford to invest every week without stress. Example: If you want to invest $400/month in {asset}, set this to $100 for weekly purchases."
                )
            
            with col_b:
                min_amount = st.number_input(
                    f"Min Amount ($)",
                    min_value=1.0,
                    max_value=1000.0,
                    value=float(config.min_amount),
                    step=5.0,
                    key=f"{asset}_min_amount",
                    help=f"💡 Smallest amount to buy when {asset} is very volatile/risky. Usually 50% of your base amount. This protects you during uncertain times."
                )
            
            with col_c:
                max_amount = st.number_input(
                    f"Max Amount ($)",
                    min_value=10.0,
                    max_value=10000.0,
                    value=float(config.max_amount),
                    step=10.0,
                    key=f"{asset}_max_amount",
                    help=f"💡 Largest amount to buy when {asset} is stable/calm. Usually 2x your base amount. This lets you take advantage of stable periods."
                )
            
            # Frequency and volatility settings
            col_d, col_e = st.columns(2)
            
            with col_d:
                frequency = st.selectbox(
                    f"Purchase Frequency",
                    options=["daily", "weekly", "monthly"],
                    index=["daily", "weekly", "monthly"].index(config.frequency),
                    key=f"{asset}_frequency",
                    help=f"💡 How often to buy {asset}. Daily = more opportunities but smaller amounts. Weekly = good balance (recommended). Monthly = larger amounts but fewer chances to catch dips."
                )
            
            with col_e:
                volatility_window = st.number_input(
                    f"Volatility Window (days)",
                    min_value=7,
                    max_value=90,
                    value=config.volatility_window,
                    step=1,
                    key=f"{asset}_vol_window",
                    help="💡 How many recent days to analyze for volatility. 30 days is recommended - long enough to see patterns but short enough to react to changes."
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
                    help=f"💡 When {asset}'s volatility is below this %, the market is 'calm' and the bot buys your MAX amount. Lower = stricter (only very calm markets). Higher = more relaxed."
                )
            
            with col_g:
                high_vol_threshold = st.number_input(
                    f"High Volatility Threshold (%)",
                    min_value=30.0,
                    max_value=200.0,
                    value=float(config.high_vol_threshold),
                    step=5.0,
                    key=f"{asset}_high_vol",
                    help=f"💡 When {asset}'s volatility is above this %, the market is 'crazy' and the bot buys your MIN amount for safety. Lower = more cautious. Higher = more aggressive in volatile times."
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
            
            # Phase 2: Smart Indicators
            st.markdown("#### 🧠 Smart Entry Signals")
            st.success("✅ Phase 2 Smart Indicators Available!")
            
            with st.expander("📚 Smart Indicators Explained - Beginner's Guide", expanded=False):
                st.markdown("""
                **Smart indicators help you buy at better times and avoid bad times:**
                
                **🧠 RSI (Relative Strength Index)**:
                - **What it does**: Tells you if an asset is "overbought" (too expensive) or "oversold" (cheap)
                - **How it helps**: Skips purchases when price might be too high, proceeds when there might be a discount
                - **Best for**: Avoiding buying at peaks
                - **Recommended**: ✅ Turn this ON for better entry timing
                
                **📊 Moving Average Dips**:
                - **What it does**: Detects when price drops below its recent average (a "dip")
                - **How it helps**: Increases your purchase amount when there's a good discount
                - **Best for**: Taking advantage of temporary price drops
                - **Recommended**: ✅ Turn this ON to buy more during dips
                
                **⚡ Dynamic Frequency**:
                - **What it does**: Changes how often you buy based on market volatility
                - **How it helps**: Buys more frequently when markets are volatile (more opportunities)
                - **Best for**: Advanced users who want automatic frequency adjustment
                - **Recommended**: ⚠️ Start with this OFF until you're comfortable
                
                **💡 Beginner Setup**: Enable RSI + Moving Average Dips, keep Dynamic Frequency OFF initially.
                """)
            
            # Phase 2: Smart Indicators (now fully functional!)
            use_rsi = st.checkbox(
                "🧠 RSI-Based Entry",
                value=config.use_rsi,
                key=f"{asset}_use_rsi",
                help="💡 RECOMMENDED: Avoids buying when price might be too high. The bot will skip purchases when RSI shows 'overbought' conditions (usually above 70). Great for beginners!"
            )
            
            if use_rsi:
                col_rsi1, col_rsi2 = st.columns(2)
                with col_rsi1:
                    rsi_period = st.number_input(
                        "RSI Period",
                        min_value=7,
                        max_value=30,
                        value=config.rsi_period,
                        key=f"{asset}_rsi_period",
                        help="💡 How many days to calculate RSI over. 14 is the standard and works well for most people."
                    )
                    rsi_oversold = st.number_input(
                        "Oversold Threshold",
                        min_value=15.0,
                        max_value=40.0,
                        value=config.rsi_oversold_threshold,
                        step=1.0,
                        key=f"{asset}_rsi_oversold",
                        help="💡 RSI below this = 'oversold' (good time to buy). 30 is standard. Lower = more strict (only very oversold), Higher = more relaxed."
                    )
                with col_rsi2:
                    rsi_overbought = st.number_input(
                        "Overbought Threshold", 
                        min_value=60.0,
                        max_value=85.0,
                        value=config.rsi_overbought_threshold,
                        step=1.0,
                        key=f"{asset}_rsi_overbought",
                        help="💡 RSI above this = 'overbought' (skip purchase). 70 is standard. Lower = more cautious (skip more often), Higher = more aggressive."
                    )
                    rsi_use_wilder = st.checkbox(
                        "Use Wilder's Method",
                        value=config.rsi_use_wilder,
                        key=f"{asset}_rsi_wilder",
                        help="More accurate RSI calculation"
                    )
            else:
                rsi_period = config.rsi_period
                rsi_oversold = config.rsi_oversold_threshold
                rsi_overbought = config.rsi_overbought_threshold
                rsi_use_wilder = config.rsi_use_wilder
            
            use_ma_dips = st.checkbox(
                "📊 Moving Average Dips",
                value=config.use_ma_dips,
                key=f"{asset}_use_ma",
                help="💡 RECOMMENDED: Automatically increases your purchase amount when there's a price dip below recent averages. Great way to 'buy the dip' automatically!"
            )
            
            if use_ma_dips:
                col_ma1, col_ma2 = st.columns(2)
                with col_ma1:
                    ma_periods = st.text_input(
                        "MA Periods (comma-separated)",
                        value=config.ma_periods,
                        key=f"{asset}_ma_periods",
                        help="💡 Which moving averages to track. 20,50,200 is standard: 20=short-term, 50=medium-term, 200=long-term trend."
                    )
                    ma_type = st.selectbox(
                        "MA Type",
                        options=["SMA", "EMA"],
                        index=0 if config.ma_type == "SMA" else 1,
                        key=f"{asset}_ma_type"
                    )
                with col_ma2:
                    ma_dip_thresholds = st.text_input(
                        "Dip Thresholds % (comma-separated)",
                        value=config.ma_dip_thresholds,
                        key=f"{asset}_ma_thresholds",
                        help="💡 How much below moving averages = a 'dip'. 2,5,10 means: 2% below 20-day MA, 5% below 50-day MA, 10% below 200-day MA triggers larger purchases."
                    )
            else:
                ma_periods = config.ma_periods
                ma_type = config.ma_type
                ma_dip_thresholds = config.ma_dip_thresholds
            
            use_dynamic_freq = st.checkbox(
                "⚡ Dynamic Frequency",
                value=config.use_dynamic_frequency,
                key=f"{asset}_dynamic_freq",
                help="💡 ADVANCED: Automatically changes how often you buy based on market volatility. High volatility = daily purchases, Low volatility = monthly. Start with this OFF until comfortable."
            )
            
            if use_dynamic_freq:
                col_dyn1, col_dyn2 = st.columns(2)
                with col_dyn1:
                    dynamic_low_vol = st.number_input(
                        "Low Volatility Threshold %",
                        min_value=10.0,
                        max_value=40.0,
                        value=config.dynamic_low_vol_threshold,
                        step=5.0,
                        key=f"{asset}_dynamic_low",
                        help="Below this = monthly frequency"
                    )
                with col_dyn2:
                    dynamic_high_vol = st.number_input(
                        "High Volatility Threshold %",
                        min_value=40.0,
                        max_value=100.0,
                        value=config.dynamic_high_vol_threshold,
                        step=5.0,
                        key=f"{asset}_dynamic_high",
                        help="Above this = daily frequency"
                    )
            else:
                dynamic_low_vol = config.dynamic_low_vol_threshold
                dynamic_high_vol = config.dynamic_high_vol_threshold
            
            # Quick stats preview
            st.markdown("#### 📈 Quick Stats")
            monthly_estimate = base_amount * 4.33 if frequency == "weekly" else (
                base_amount * 30 if frequency == "daily" else base_amount
            )
            st.metric("Est. Monthly Investment", f"${monthly_estimate:.0f}")
            
            volatility_range = high_vol_threshold - low_vol_threshold
            st.metric("Volatility Range", f"{volatility_range:.0f}%")
    
    # Create updated config with Phase 2 indicators
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
        # Phase 2: Smart Indicators
        use_rsi=use_rsi,
        rsi_period=rsi_period,
        rsi_oversold_threshold=rsi_oversold,
        rsi_overbought_threshold=rsi_overbought,
        rsi_use_wilder=rsi_use_wilder,
        use_ma_dips=use_ma_dips,
        ma_periods=ma_periods,
        ma_type=ma_type,
        ma_dip_thresholds=ma_dip_thresholds,
        use_dynamic_frequency=use_dynamic_freq,
        dynamic_low_vol_threshold=dynamic_low_vol,
        dynamic_high_vol_threshold=dynamic_high_vol
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
    
    # Add comprehensive beginner's guide
    with st.expander("📖 Complete Beginner's Guide to DCA - READ THIS FIRST!", expanded=False):
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("""
            ### 🎯 Quick Start Guide
            
            **Step 1: Choose Your Assets**
            - **Beginner**: Start with just BTC + ETH
            - **Intermediate**: Add SOL as a third asset
            - **Advanced**: Consider AVAX or LINK
            
            **Step 2: Set Your Budget**
            - Decide how much you can invest monthly
            - Divide by your chosen frequency
            - Example: $400/month ÷ 4 weeks = $100/week
            
            **Step 3: Configure Amounts**
            - **Base**: Your normal weekly amount ($100)
            - **Min**: Half of base for volatile times ($50)
            - **Max**: Double base for calm times ($200)
            
            **Step 4: Enable Smart Features**
            - ✅ Turn ON RSI-Based Entry
            - ✅ Turn ON Moving Average Dips
            - ❌ Keep Dynamic Frequency OFF initially
            """)
        
        with col2:
            st.markdown("""
            ### 💡 Best Practices & Tips
            
            **Money Management**
            - Only invest what you can afford to lose
            - DCA works best over 6+ months
            - Don't check prices daily - trust the process!
            
            **Frequency Recommendations**
            - **$50-200/month**: Weekly DCA
            - **$200-500/month**: Bi-weekly DCA  
            - **$500+/month**: Weekly or daily DCA
            
            **Risk Management**
            - Start with smaller amounts to learn
            - BTC/ETH are generally safer than smaller coins
            - Diversify: don't put everything in one asset
            
            **Common Mistakes to Avoid**
            - ❌ Checking prices every day
            - ❌ Stopping DCA during market crashes (best time!)
            - ❌ FOMO buying extra during pumps
            - ❌ Using money you need for expenses
            """)
    
    # Portfolio Templates
    with st.expander("🎨 Portfolio Templates - Copy These Setups!", expanded=False):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("""
            ### 🥇 Conservative ($200/month)
            **Best for: Total beginners**
            
            **Assets:**
            - 60% BTC ($120/month = $30/week)
            - 40% ETH ($80/month = $20/week)
            
            **Settings:**
            - Frequency: Weekly
            - Smart Indicators: RSI + MA Dips ON
            - Total: $50/week
            
            **Why this works:**
            - Only proven, established assets
            - Simple 2-asset portfolio
            - Conservative amounts
            """)
        
        with col2:
            st.markdown("""
            ### 🥈 Balanced ($500/month)
            **Best for: Some crypto knowledge**
            
            **Assets:**
            - 50% BTC ($250/month = $62.50/week)
            - 30% ETH ($150/month = $37.50/week)
            - 20% SOL ($100/month = $25/week)
            
            **Settings:**
            - Frequency: Weekly
            - Smart Indicators: All ON
            - Total: $125/week
            
            **Why this works:**
            - Diversified across top 3 platforms
            - Includes some higher-growth potential
            - Smart indicators optimize entries
            """)
        
        with col3:
            st.markdown("""
            ### 🥉 Aggressive ($1000/month)
            **Best for: Experienced investors**
            
            **Assets:**
            - 40% BTC ($400/month = $100/week)
            - 30% ETH ($300/month = $75/week)
            - 20% SOL ($200/month = $50/week)
            - 10% AVAX/LINK ($100/month = $25/week)
            
            **Settings:**
            - Frequency: Weekly or Daily
            - Smart Indicators: All ON
            - Total: $250/week
            
            **Why this works:**
            - Full diversification
            - Higher risk/reward with smaller caps
            - All smart features active
            """)
    
    # Risk warnings
    st.warning("""
    ⚠️ **Important Risk Disclosure**: 
    Cryptocurrency investing is highly risky. Prices can go down 50-90% and stay there for years. 
    Only invest money you can afford to lose completely. Past performance doesn't guarantee future results.
    DCA reduces timing risk but doesn't eliminate investment risk.
    """)
    
    st.info("""
    💡 **DCA Success Tips**: 
    • Set it and forget it - check monthly, not daily
    • DCA works best over 1-3 year timeframes  
    • Market crashes are DCA opportunities, not failures
    • Focus on accumulating assets, not short-term price movements
    """)
    
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
        
        # Configuration Validation & Tips
        st.markdown("---")
        st.subheader("🔍 Configuration Review & Tips")
        
        with st.expander("📋 Review Your Settings", expanded=True):
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("#### ✅ Configuration Checklist")
                
                total_monthly = 0
                issues = []
                tips = []
                
                for asset, config in new_asset_configs.items():
                    if config.enabled:
                        asset_info = SUPPORTED_ASSETS[asset]
                        freq_mult = {"daily": 30, "weekly": 4.33, "monthly": 1}[config.frequency]
                        monthly_est = config.base_amount * freq_mult
                        total_monthly += monthly_est
                        
                        # Validation checks
                        if config.min_amount >= config.base_amount:
                            issues.append(f"⚠️ {asset}: Min amount should be less than base amount")
                        
                        if config.max_amount <= config.base_amount:
                            issues.append(f"⚠️ {asset}: Max amount should be greater than base amount")
                        
                        if config.high_vol_threshold <= config.low_vol_threshold:
                            issues.append(f"⚠️ {asset}: High volatility threshold should be higher than low")
                        
                        # Best practice tips
                        if not config.use_rsi and not config.use_ma_dips:
                            tips.append(f"💡 {asset}: Consider enabling RSI or MA Dips for smarter entries")
                        
                        if config.base_amount > 500 and config.frequency == "daily":
                            tips.append(f"💡 {asset}: High daily amounts - consider weekly frequency")
                        
                        if monthly_est < 50:
                            tips.append(f"💡 {asset}: Very small monthly investment - consider increasing or changing frequency")
                
                # Display results
                if issues:
                    st.error("**Issues Found:**")
                    for issue in issues:
                        st.write(issue)
                else:
                    st.success("✅ No configuration issues found!")
                
                if tips:
                    st.info("**Optimization Tips:**")
                    for tip in tips:
                        st.write(tip)
                
                st.metric("Total Monthly Investment", f"${total_monthly:.0f}")
                
                # Risk assessment
                if total_monthly < 100:
                    risk_level = "🟢 Conservative"
                elif total_monthly < 500:
                    risk_level = "🟡 Moderate"
                else:
                    risk_level = "🔴 Aggressive"
                
                st.metric("Risk Level", risk_level)
            
            with col2:
                st.markdown("#### 🎯 Strategy Summary")
                
                enabled_count = len([c for c in new_asset_configs.values() if c.enabled])
                
                if enabled_count == 0:
                    st.warning("No assets enabled - enable at least one asset")
                elif enabled_count <= 2:
                    st.info(f"**{enabled_count} Asset Strategy**: Good for beginners, focused approach")
                elif enabled_count <= 4:
                    st.info(f"**{enabled_count} Asset Strategy**: Balanced diversification")
                else:
                    st.warning(f"**{enabled_count} Asset Strategy**: High diversification - may be complex for beginners")
                
                # Smart indicators summary
                rsi_count = sum(1 for c in new_asset_configs.values() if c.enabled and c.use_rsi)
                ma_count = sum(1 for c in new_asset_configs.values() if c.enabled and c.use_ma_dips)
                freq_count = sum(1 for c in new_asset_configs.values() if c.enabled and c.use_dynamic_frequency)
                
                st.markdown("**Smart Indicators Active:**")
                st.write(f"• RSI-Based Entry: {rsi_count}/{enabled_count} assets")
                st.write(f"• Moving Average Dips: {ma_count}/{enabled_count} assets")
                st.write(f"• Dynamic Frequency: {freq_count}/{enabled_count} assets")
                
                # Frequency distribution
                freq_dist = {}
                for config in new_asset_configs.values():
                    if config.enabled:
                        freq_dist[config.frequency] = freq_dist.get(config.frequency, 0) + 1
                
                if freq_dist:
                    st.markdown("**Purchase Frequencies:**")
                    for freq, count in freq_dist.items():
                        st.write(f"• {freq.title()}: {count} asset{'s' if count > 1 else ''}")
                
                # Final recommendation
                if enabled_count >= 1 and not issues:
                    if total_monthly <= 200:
                        st.success("👍 **Good starter setup!** Conservative amounts with solid strategy.")
                    elif total_monthly <= 1000:
                        st.success("👍 **Well-balanced strategy!** Good diversification and risk management.")
                    else:
                        st.info("💰 **High-volume strategy** - Make sure you can sustain these amounts long-term.")
                else:
                    st.warning("⚠️ Review the issues above before saving your configuration.")
        
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