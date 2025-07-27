"""Multi-Asset DCA Dashboard Components."""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import asyncio
from datetime import datetime
from typing import Dict, List, Optional

from ..config.models import MultiAssetDCAConfig, AssetDCAConfig, TradeRecord
from ..trading.multi_asset_bot import MultiAssetDCABot
from ..utils.logging_config import get_logger
from .multi_asset_config import SUPPORTED_ASSETS

logger = get_logger(__name__)


def render_multi_asset_overview(bot: MultiAssetDCABot):
    """Render overview for all assets in the portfolio."""
    st.subheader("🌟 Multi-Asset Portfolio Overview")
    
    try:
        enabled_assets = bot.config.get_enabled_assets()
        
        if not enabled_assets:
            st.warning("No assets enabled. Go to Multi-Asset Config to set up your portfolio.")
            return
        
        # Load current prices and balances for all assets
        asset_data = {}
        
        with st.spinner("Loading portfolio data..."):
            for asset_config in enabled_assets:
                asset = asset_config.symbol
                try:
                    current_price = asyncio.run(bot.api_client.get_asset_price(asset))
                    usdc_balance = asyncio.run(bot.api_client.get_asset_balance(bot.config.wallet_address, "USDC"))
                    asset_balance = asyncio.run(bot.api_client.get_asset_balance(bot.config.wallet_address, asset))
                    
                    asset_data[asset] = {
                        "config": asset_config,
                        "price": current_price,
                        "balance": asset_balance,
                        "usdc_balance": usdc_balance,
                        "usd_value": asset_balance * current_price if current_price else 0
                    }
                except Exception as e:
                    logger.error(f"Error loading data for {asset}: {e}")
                    asset_data[asset] = {
                        "config": asset_config,
                        "price": None,
                        "balance": 0,
                        "usdc_balance": 0,
                        "usd_value": 0
                    }
        
        # Portfolio summary metrics
        total_usd_value = sum(data["usd_value"] for data in asset_data.values())
        avg_usdc_balance = sum(data["usdc_balance"] for data in asset_data.values()) / len(asset_data)
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Portfolio Value", f"${total_usd_value:,.2f}")
        
        with col2:
            st.metric("Active Assets", len(enabled_assets))
        
        with col3:
            st.metric("USDC Balance", f"${avg_usdc_balance:,.2f}")
        
        with col4:
            total_base = sum(config.base_amount for config in enabled_assets)
            st.metric("Total Base Investment", f"${total_base:,.0f}")
        
        # Asset breakdown cards
        st.markdown("### 📊 Asset Breakdown")
        
        cols = st.columns(min(len(asset_data), 3))
        
        for i, (asset, data) in enumerate(asset_data.items()):
            col_idx = i % len(cols)
            
            with cols[col_idx]:
                asset_info = SUPPORTED_ASSETS.get(asset, {"icon": "💎", "name": asset})
                config = data["config"]
                
                # Asset card
                st.markdown(f"""
                <div style="padding: 1rem; border: 1px solid #ddd; border-radius: 0.5rem; margin-bottom: 1rem;">
                    <h4>{asset_info['icon']} {asset}</h4>
                </div>
                """, unsafe_allow_html=True)
                
                # Metrics
                if data["price"]:
                    st.metric("Price", f"${data['price']:,.2f}")
                else:
                    st.metric("Price", "Loading...")
                
                st.metric("Balance", f"{data['balance']:.6f} {asset}")
                st.metric("USD Value", f"${data['usd_value']:,.2f}")
                
                # Configuration preview
                st.caption(f"📅 {config.frequency.title()}")
                st.caption(f"💰 ${config.base_amount:.0f} base")
                
                # Status indicator
                status = "🟢 Active" if config.enabled else "🔴 Disabled"
                st.caption(status)
        
        # Portfolio allocation chart
        render_portfolio_allocation_chart(asset_data)
        
    except Exception as e:
        st.error(f"❌ Error loading portfolio overview: {e}")
        logger.error(f"Portfolio overview error: {e}")


def render_portfolio_allocation_chart(asset_data: Dict):
    """Render portfolio allocation pie chart."""
    if not asset_data:
        return
    
    # Filter assets with non-zero values
    assets_with_value = {k: v for k, v in asset_data.items() if v["usd_value"] > 0}
    
    if not assets_with_value:
        st.info("No asset balances to display in allocation chart.")
        return
    
    st.markdown("### 🥧 Portfolio Allocation")
    
    # Prepare data for pie chart
    labels = []
    values = []
    colors = ["#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FFEAA7", "#DDA0DD"]
    
    for i, (asset, data) in enumerate(assets_with_value.items()):
        asset_info = SUPPORTED_ASSETS.get(asset, {"icon": "💎", "name": asset})
        labels.append(f"{asset_info['icon']} {asset}")
        values.append(data["usd_value"])
    
    # Create pie chart
    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=0.4,
        marker_colors=colors[:len(labels)],
        textinfo='label+percent',
        textposition='outside'
    )])
    
    fig.update_layout(
        title="Portfolio Allocation by USD Value",
        showlegend=True,
        height=400,
        margin=dict(t=50, b=50, l=50, r=50)
    )
    
    st.plotly_chart(fig, use_container_width=True)


def render_asset_specific_dashboard(bot: MultiAssetDCABot, asset: str):
    """Render detailed dashboard for a specific asset."""
    st.subheader(f"{SUPPORTED_ASSETS.get(asset, {}).get('icon', '💎')} {asset} Dashboard")
    
    try:
        # Get asset configuration
        asset_config = bot.config.assets.get(asset)
        if not asset_config:
            st.error(f"No configuration found for {asset}")
            return
        
        # Load asset data
        with st.spinner(f"Loading {asset} data..."):
            current_price = asyncio.run(bot.api_client.get_asset_price(asset))
            asset_balance = asyncio.run(bot.api_client.get_asset_balance(bot.config.wallet_address, asset))
            usdc_balance = asyncio.run(bot.api_client.get_asset_balance(bot.config.wallet_address, "USDC"))
            
            # Get trade history for this asset
            asset_trades = [t for t in bot.trade_history if t.asset == asset]
        
        # Asset overview metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if current_price:
                st.metric(f"{asset} Price", f"${current_price:,.2f}")
            else:
                st.metric(f"{asset} Price", "Loading...")
        
        with col2:
            st.metric(f"{asset} Balance", f"{asset_balance:.6f}")
        
        with col3:
            usd_value = asset_balance * current_price if current_price else 0
            st.metric("USD Value", f"${usd_value:,.2f}")
        
        with col4:
            st.metric("USDC Available", f"${usdc_balance:,.2f}")
        
        # DCA Configuration Status
        st.markdown("### ⚙️ DCA Configuration")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            status = "🟢 Active" if asset_config.enabled else "🔴 Disabled"
            st.metric("Status", status)
        
        with col2:
            st.metric("Frequency", asset_config.frequency.title())
        
        with col3:
            st.metric("Base Amount", f"${asset_config.base_amount:.0f}")
        
        # Volatility and position sizing info
        if current_price:
            st.markdown("### 📊 Market Analysis")
            
            try:
                # Calculate volatility (placeholder for now)
                volatility = 25.0  # Will be implemented with real calculation
                
                # Calculate position size based on volatility (placeholder implementation)
                if volatility <= asset_config.low_vol_threshold:
                    position_size = asset_config.max_amount
                    strategy = "🟢 Max Investment (Low Volatility)"
                elif volatility >= asset_config.high_vol_threshold:
                    position_size = asset_config.min_amount
                    strategy = "🔴 Min Investment (High Volatility)"
                else:
                    # Linear interpolation between min and max
                    vol_range = asset_config.high_vol_threshold - asset_config.low_vol_threshold
                    vol_position = (volatility - asset_config.low_vol_threshold) / vol_range
                    position_size = asset_config.max_amount - (vol_position * (asset_config.max_amount - asset_config.min_amount))
                    strategy = "🟡 Scaled Investment"
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("30d Volatility", f"{volatility:.1f}%")
                
                with col2:
                    st.metric("Next Position Size", f"${position_size:.0f}")
                
                with col3:
                    st.metric("Strategy", strategy)
                
            except Exception as e:
                st.warning(f"Could not calculate market analysis: {e}")
        
        # Trade history for this asset
        if asset_trades:
            st.markdown(f"### 📜 {asset} Trade History")
            
            # Trade summary
            total_invested = sum(t.amount_usd for t in asset_trades)
            total_acquired = sum(t.amount_asset for t in asset_trades)
            avg_price = total_invested / total_acquired if total_acquired > 0 else 0
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Total Invested", f"${total_invested:,.2f}")
            
            with col2:
                st.metric("Total Acquired", f"{total_acquired:.6f} {asset}")
            
            with col3:
                if avg_price > 0 and current_price:
                    pnl_pct = ((current_price / avg_price - 1) * 100)
                    st.metric("Avg Entry Price", f"${avg_price:,.2f}", delta=f"{pnl_pct:+.1f}%")
                else:
                    st.metric("Avg Entry Price", f"${avg_price:,.2f}")
            
            # Trade history table
            trade_data = []
            for trade in sorted(asset_trades, key=lambda x: x.timestamp, reverse=True):
                trade_data.append({
                    "Date": trade.timestamp.strftime('%Y-%m-%d %H:%M'),
                    "Price": f"${trade.price:,.2f}",
                    "USD Amount": f"${trade.amount_usd:.2f}",
                    f"{asset} Amount": f"{trade.amount_asset:.6f}",
                    "Volatility": f"{trade.volatility:.2f}%"
                })
            
            df = pd.DataFrame(trade_data)
            st.dataframe(df, use_container_width=True, hide_index=True)
            
        else:
            st.info(f"No {asset} trade history found. Trades will appear here after execution.")
        
        # Manual trade execution
        render_asset_manual_trade(bot, asset, asset_config, current_price)
        
    except Exception as e:
        st.error(f"❌ Error loading {asset} dashboard: {e}")
        logger.error(f"{asset} dashboard error: {e}")


def render_asset_manual_trade(bot: MultiAssetDCABot, asset: str, config: AssetDCAConfig, current_price: float):
    """Render manual trade execution for specific asset."""
    st.markdown(f"### 🚀 Manual {asset} Trade")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.info(f"Execute a {asset} purchase immediately, bypassing frequency restrictions.")
    
    with col2:
        if st.button(f"🔥 Buy {asset} Now", type="primary", key=f"manual_trade_{asset}"):
            if not config.enabled:
                st.error(f"{asset} DCA is currently disabled. Enable it in configuration first.")
                return
            
            with st.spinner(f"Executing {asset} trade..."):
                try:
                    # Execute smart multi-asset trade (Phase 2 implementation)
                    if hasattr(bot, 'execute_smart_asset_dca_trade'):
                        result = asyncio.run(bot.execute_smart_asset_dca_trade(asset, force=True))
                    else:
                        result = asyncio.run(bot.execute_asset_dca_trade(asset, force=True))
                    
                    if result and result.get("status") == "ok":
                        if result.get("simulated"):
                            st.success(f"✅ {asset} trade simulated successfully!")
                            st.info(f"📋 Simulated: {result.get('amount_asset', 0):.6f} {asset} for ${result.get('amount_usd', 0):.2f}")
                        else:
                            st.success(f"✅ {asset} trade executed successfully!")
                            st.info(f"🚀 Real trade: {result.get('amount_asset', 0):.6f} {asset} for ${result.get('amount_usd', 0):.2f}")
                        
                        # Refresh the page to show updated data
                        st.rerun()
                    else:
                        st.error(f"❌ {asset} trade failed: {result.get('error', 'Unknown error')}")
                    
                except Exception as e:
                    st.error(f"❌ {asset} trade execution failed: {e}")


def render_multi_asset_tabs(bot: MultiAssetDCABot):
    """Render tabbed interface for multi-asset dashboard."""
    enabled_assets = bot.config.get_enabled_assets()
    
    if not enabled_assets:
        st.warning("No assets enabled. Configure your multi-asset portfolio first.")
        return
    
    # Create tabs for overview + each asset
    tab_names = ["📊 Overview"] + [f"{SUPPORTED_ASSETS.get(config.symbol, {}).get('icon', '💎')} {config.symbol}" 
                                   for config in enabled_assets]
    
    tabs = st.tabs(tab_names)
    
    # Overview tab
    with tabs[0]:
        render_multi_asset_overview(bot)
    
    # Individual asset tabs
    for i, asset_config in enumerate(enabled_assets):
        with tabs[i + 1]:
            render_asset_specific_dashboard(bot, asset_config.symbol)


def render_multi_asset_actions(bot: MultiAssetDCABot):
    """Render action buttons for multi-asset operations."""
    st.subheader("⚡ Portfolio Actions")
    
    enabled_assets = bot.config.get_enabled_assets()
    
    if not enabled_assets:
        st.info("No assets enabled for trading.")
        return
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("🚀 Execute All DCA", type="primary", use_container_width=True):
            with st.spinner("Executing DCA for all enabled assets..."):
                try:
                    # Execute all smart DCA trades in parallel (Phase 2 implementation)
                    if hasattr(bot, 'execute_all_smart_dca_trades'):
                        results = asyncio.run(bot.execute_all_smart_dca_trades(force=True, parallel=True))
                    else:
                        results = asyncio.run(bot.execute_all_dca_trades(force=True, parallel=True))
                    
                    successful_trades = [asset for asset, result in results.items() 
                                       if result and result.get("status") == "ok"]
                    failed_trades = [asset for asset, result in results.items() 
                                   if not result or result.get("status") != "ok"]
                    
                    if successful_trades:
                        st.success(f"✅ {len(successful_trades)} trades executed successfully!")
                        
                        # Show execution details
                        for asset in successful_trades:
                            result = results[asset]
                            trade_type = "📋 Simulated" if result.get("simulated") else "🚀 Real"
                            st.info(f"{trade_type} {asset}: {result.get('amount_asset', 0):.6f} for ${result.get('amount_usd', 0):.2f}")
                    
                    if failed_trades:
                        st.warning(f"⚠️ {len(failed_trades)} trades failed: {', '.join(failed_trades)}")
                    
                    if not successful_trades and not failed_trades:
                        st.info("💡 No trades needed - all assets are within their frequency windows.")
                    
                    # Refresh to show updated data
                    if successful_trades:
                        st.rerun()
                        
                except Exception as e:
                    st.error(f"❌ Bulk execution failed: {e}")
    
    with col2:
        if st.button("📥 Sync All History", use_container_width=True):
            with st.spinner("Syncing trade history for all assets..."):
                try:
                    # Sync all trade histories in parallel (Phase 1.4 implementation)
                    results = asyncio.run(bot.sync_all_trade_history(days=30, parallel=True))
                    
                    successful_syncs = [asset for asset, success in results.items() if success]
                    failed_syncs = [asset for asset, success in results.items() if not success]
                    
                    if successful_syncs:
                        st.success(f"✅ History synced for {len(successful_syncs)} assets!")
                        st.info(f"📥 Synced: {', '.join(successful_syncs)}")
                    
                    if failed_syncs:
                        st.warning(f"⚠️ Sync failed for {len(failed_syncs)} assets: {', '.join(failed_syncs)}")
                    
                    if not successful_syncs and not failed_syncs:
                        st.info("💡 No tradeable assets found for history sync.")
                    
                    # Refresh to show updated data
                    if successful_syncs:
                        st.rerun()
                        
                except Exception as e:
                    st.error(f"❌ History sync failed: {e}")
    
    with col3:
        if st.button("🔄 Refresh Portfolio", use_container_width=True):
            # Clear cache and rerun
            st.cache_data.clear()
            st.rerun()
    
    with col4:
        if st.button("⚙️ Configure Assets", use_container_width=True):
            st.switch_page("pages/1_Multi_Asset_Config.py")