"""Main dashboard components."""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import asyncio
from datetime import datetime
from typing import Optional

from ..config.models import DCAConfig
from ..config.loader import load_config, save_config
from ..trading.bot import HyperliquidDCABot
from ..utils.constants import PAGE_TITLE, PAGE_ICON
from ..utils.logging_config import get_logger
from ..utils.performance import StreamlitCache, performance_monitor, DataLoader

logger = get_logger(__name__)


def setup_page_config():
    """Configure Streamlit page settings."""
    st.set_page_config(
        page_title=PAGE_TITLE,
        page_icon=PAGE_ICON,
        layout="wide",
        initial_sidebar_state="expanded"
    )


def load_bot_config() -> Optional[DCAConfig]:
    """Load bot configuration with error handling."""
    try:
        config = load_config()
        if config:
            logger.info("Configuration loaded successfully")
        return config
    except Exception as e:
        st.error(f"❌ Configuration Error: {e}")
        logger.error(f"Failed to load configuration: {e}")
        return None


def initialize_bot(config: DCAConfig) -> Optional[HyperliquidDCABot]:
    """Initialize the trading bot."""
    try:
        bot = HyperliquidDCABot(config)
        logger.info("Bot initialized successfully")
        return bot
    except Exception as e:
        st.error(f"❌ Bot Initialization Error: {e}")
        logger.error(f"Failed to initialize bot: {e}")
        return None


def render_sidebar(config: DCAConfig) -> DCAConfig:
    """Render sidebar with configuration options."""
    st.sidebar.title("⚙️ Configuration")
    
    with st.sidebar.form("config_form"):
        st.subheader("Trading Parameters")
        
        base_amount = st.number_input(
            "Base Amount ($)", 
            min_value=1.0, 
            max_value=10000.0,
            value=float(config.base_amount),
            step=1.0
        )
        
        min_amount = st.number_input(
            "Min Amount ($)", 
            min_value=1.0, 
            max_value=10000.0,
            value=float(config.min_amount),
            step=1.0
        )
        
        max_amount = st.number_input(
            "Max Amount ($)", 
            min_value=1.0, 
            max_value=10000.0,
            value=float(config.max_amount),
            step=1.0
        )
        
        frequency = st.selectbox(
            "Frequency",
            ["daily", "weekly", "monthly"],
            index=["daily", "weekly", "monthly"].index(config.frequency)
        )
        
        st.subheader("Volatility Settings")
        
        volatility_window = st.number_input(
            "Volatility Window (days)",
            min_value=7,
            max_value=365,
            value=config.volatility_window,
            step=1
        )
        
        low_vol_threshold = st.number_input(
            "Low Volatility Threshold (%)",
            min_value=1.0,
            max_value=100.0,
            value=float(config.low_vol_threshold),
            step=1.0
        )
        
        high_vol_threshold = st.number_input(
            "High Volatility Threshold (%)",
            min_value=1.0,
            max_value=200.0,
            value=float(config.high_vol_threshold),
            step=1.0
        )
        
        enabled = st.checkbox("Bot Enabled", value=config.enabled)
        
        if st.form_submit_button("💾 Save Configuration"):
            # Create updated config
            updated_config = DCAConfig(
                private_key=config.private_key,
                wallet_address=config.wallet_address,
                base_amount=base_amount,
                min_amount=min_amount,
                max_amount=max_amount,
                frequency=frequency,
                volatility_window=volatility_window,
                low_vol_threshold=low_vol_threshold,
                high_vol_threshold=high_vol_threshold,
                enabled=enabled
            )
            
            try:
                updated_config.validate()
                if save_config(updated_config):
                    st.success("✅ Configuration saved!")
                    st.rerun()
                else:
                    st.error("❌ Failed to save configuration")
            except ValueError as e:
                st.error(f"❌ Configuration Error: {e}")
    
    return config


@performance_monitor
def _render_current_metrics(bot: HyperliquidDCABot, dashboard_data: dict = None):
    """Render current market and balance metrics."""
    if dashboard_data:
        # Use pre-loaded data for better performance
        current_price = dashboard_data.get('current_price')
        usdc_balance = dashboard_data.get('usdc_balance', 0.0)
        ubtc_balance = dashboard_data.get('ubtc_balance', 0.0)
        historical_prices = dashboard_data.get('historical_prices')
        
        # Calculate volatility from historical data
        volatility = None
        if historical_prices is not None:
            volatility = bot.volatility_calc.calculate_volatility(historical_prices)
    else:
        # Fallback to individual API calls
        current_price = asyncio.run(bot.get_btc_price())
        usdc_balance = asyncio.run(bot.get_usdc_balance())
        ubtc_balance = asyncio.run(bot.get_ubtc_balance())
        volatility = asyncio.run(bot.calculate_volatility())
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if current_price:
            st.metric("Current BTC Price", f"${current_price:,.2f}")
        else:
            st.metric("Current BTC Price", "Loading...")
    
    with col2:
        st.metric("USDC Balance", f"${usdc_balance:,.2f}")
        
    with col3:
        # Show USD value in the delta if we have current price
        usd_value_delta = f"${ubtc_balance * current_price:,.2f} USD" if current_price and ubtc_balance > 0 else None
        st.metric("UBTC Balance", f"{ubtc_balance:.6f} UBTC", delta=usd_value_delta)
        
        # Show average entry price and PnL if we have trade history
        if bot and bot.trade_history and ubtc_balance > 0 and current_price:
            # Calculate average entry price from trade history
            total_usd_spent = sum(t.amount_usd for t in bot.trade_history)
            total_ubtc_bought = sum(t.amount_btc for t in bot.trade_history)
            avg_entry_price = total_usd_spent / total_ubtc_bought if total_ubtc_bought > 0 else 0
            
            # Calculate unrealized PnL
            ubtc_usd_value = ubtc_balance * current_price
            cost_basis = ubtc_balance * avg_entry_price
            unrealized_pnl = ubtc_usd_value - cost_basis
            pnl_pct = ((current_price / avg_entry_price - 1) * 100) if avg_entry_price > 0 else 0
            
            # Display additional info
            st.caption(f"📊 Avg Entry: ${avg_entry_price:,.2f}")
            pnl_color = "green" if unrealized_pnl >= 0 else "red"
            pnl_symbol = "📈" if unrealized_pnl >= 0 else "📉"
            st.caption(f"{pnl_symbol} PnL: ::{pnl_color}[${unrealized_pnl:+,.2f} ({pnl_pct:+.1f}%)]")
        
    with col4:
        if volatility:
            st.metric("30d Volatility", f"{volatility:.1f}%")
            position_size = bot.calculate_position_size(volatility)
            st.metric("Next Trade Size", f"${position_size:.2f}")
        else:
            st.metric("30d Volatility", "Calculating...")


def _render_portfolio_stats(stats: dict):
    """Render portfolio statistics section."""
    if stats["total_invested"] > 0:
        st.subheader("📈 Portfolio Statistics")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Invested", f"${stats['total_invested']:,.2f}")
            
        with col2:
            st.metric("BTC Holdings", f"{stats['btc_holdings']:.6f}")
            
        with col3:
            st.metric("Avg Buy Price", f"${stats['avg_buy_price']:,.2f}")


def _render_manual_trade_section(bot: HyperliquidDCABot):
    """Render manual trade execution section."""
    st.subheader("🚀 Manual Trade Execution")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.info("Click the button below to execute a trade immediately, bypassing frequency restrictions.")
        
    with col2:
        if st.button("🔥 Execute Trade Now", type="primary"):
            with st.spinner("Executing trade..."):
                result = asyncio.run(bot.execute_dca_trade(force=True))
                
            if result:
                st.success("✅ Trade executed successfully!")
                st.rerun()
            else:
                st.error("❌ Trade execution failed. Check logs for details.")


@performance_monitor
def render_overview_tab(bot: HyperliquidDCABot):
    """Render the overview tab with optimized data loading."""
    st.subheader("📊 Bot Overview")
    
    try:
        # Initialize data loader if not in session state
        if 'data_loader' not in st.session_state:
            st.session_state.data_loader = DataLoader(bot.api_client)
        
        # Add refresh and sync buttons
        col1, col2, col3 = st.columns([3, 1, 1])
        with col2:
            if st.button("🔄 Refresh", key="overview_refresh"):
                st.session_state.data_loader.clear_cache()
                st.rerun()
        with col3:
            if st.button("📥 Sync History", key="sync_history", help="Sync trade history from Hyperliquid API"):
                with st.spinner("Syncing trade history..."):
                    try:
                        sync_result = asyncio.run(bot.sync_trade_history_from_api())
                        if sync_result:
                            st.success("✅ Trade history synced!")
                            st.rerun()
                        else:
                            st.warning("⚠️ Sync completed but no new trades found")
                    except Exception as e:
                        st.error(f"❌ Sync failed: {e}")
        
        # Load dashboard data
        with st.spinner("Loading data..."):
            dashboard_data = asyncio.run(
                st.session_state.data_loader.load_dashboard_data(bot.config)
            )
        
        stats = bot.get_portfolio_stats()
        
        _render_current_metrics(bot, dashboard_data)
        _render_portfolio_stats(stats)
        _render_manual_trade_section(bot)
        
        # Show last update time
        if dashboard_data and dashboard_data.get('last_updated'):
            st.caption(f"Last updated: {dashboard_data['last_updated'].strftime('%H:%M:%S')}")
        
    except Exception as e:
        st.error(f"❌ Error loading overview data: {e}")
        logger.error(f"Overview tab error: {e}")


def _render_current_holdings(current_price: float, usdc_balance: float, ubtc_balance: float, bot: HyperliquidDCABot = None):
    """Render current holdings metrics with average entry price and PnL."""
    ubtc_usd_value = ubtc_balance * current_price
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("UBTC Holdings", f"{ubtc_balance:.6f} UBTC", 
                 delta=f"${ubtc_usd_value:,.2f} USD")
        
        # Show average entry price and PnL if we have trade history
        if bot and bot.trade_history and ubtc_balance > 0:
            # Calculate average entry price from trade history
            total_usd_spent = sum(t.amount_usd for t in bot.trade_history)
            total_ubtc_bought = sum(t.amount_btc for t in bot.trade_history)
            avg_entry_price = total_usd_spent / total_ubtc_bought if total_ubtc_bought > 0 else 0
            
            # Calculate unrealized PnL
            cost_basis = ubtc_balance * avg_entry_price
            unrealized_pnl = ubtc_usd_value - cost_basis
            pnl_pct = ((current_price / avg_entry_price - 1) * 100) if avg_entry_price > 0 else 0
            
            # Display additional info
            st.caption(f"📊 Avg Entry: ${avg_entry_price:,.2f}")
            pnl_color = "green" if unrealized_pnl >= 0 else "red"
            pnl_symbol = "📈" if unrealized_pnl >= 0 else "📉"
            st.caption(f"{pnl_symbol} PnL: ::{pnl_color}[${unrealized_pnl:+,.2f} ({pnl_pct:+.1f}%)]")
    
    with col2:
        st.metric("USDC Balance", f"${usdc_balance:,.2f}")
    with col3:
        st.metric("UBTC Price", f"${current_price:,.2f}")


def _calculate_portfolio_metrics(bot: HyperliquidDCABot, current_price: float, ubtc_balance: float):
    """Calculate portfolio performance metrics."""
    buy_trades = [t for t in bot.trade_history]
    total_ubtc_bought = sum(t.amount_btc for t in buy_trades)
    total_usd_spent = sum(t.amount_usd for t in buy_trades)
    avg_buy_price = total_usd_spent / total_ubtc_bought if total_ubtc_bought > 0 else 0
    
    current_value = ubtc_balance * current_price
    unrealized_pnl = current_value - (ubtc_balance * avg_buy_price) if avg_buy_price > 0 else 0
    pnl_pct = ((current_price/avg_buy_price-1)*100) if avg_buy_price > 0 else 0
    
    return {
        'total_usd_spent': total_usd_spent,
        'avg_buy_price': avg_buy_price,
        'current_value': current_value,
        'unrealized_pnl': unrealized_pnl,
        'pnl_pct': pnl_pct
    }


def _render_portfolio_performance(metrics: dict):
    """Render portfolio performance metrics."""
    st.subheader("📊 Portfolio Performance")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Invested", f"${metrics['total_usd_spent']:,.2f}")
    with col2:
        st.metric("Avg Buy Price", f"${metrics['avg_buy_price']:,.2f}")
    with col3:
        st.metric("Current Value", f"${metrics['current_value']:,.2f}")
    with col4:
        st.metric("Unrealized P&L", f"${metrics['unrealized_pnl']:,.2f}", 
                 delta=f"{metrics['pnl_pct']:.2f}%")


def _render_portfolio_growth_chart(bot: HyperliquidDCABot):
    """Render portfolio growth chart."""
    if len(bot.trade_history) > 1:
        st.subheader("📈 Portfolio Growth")
        
        df_trades = pd.DataFrame([
            {
                'date': t.timestamp,
                'cumulative_ubtc': sum(trade.amount_btc for trade in bot.trade_history[:i+1]),
                'cumulative_usd': sum(trade.amount_usd for trade in bot.trade_history[:i+1]),
                'price': t.price
            }
            for i, t in enumerate(bot.trade_history)
        ])
        
        df_trades['avg_cost_basis'] = df_trades['cumulative_usd'] / df_trades['cumulative_ubtc']
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=df_trades['date'],
            y=df_trades['cumulative_ubtc'],
            mode='lines+markers',
            name='UBTC Holdings',
            line=dict(color='orange')
        ))
        
        fig.update_layout(
            title='Cumulative UBTC Holdings Over Time',
            xaxis_title='Date',
            yaxis_title='UBTC Amount',
            hovermode='x unified'
        )
        
        st.plotly_chart(fig, use_container_width=True)


def render_portfolio_tab(bot: HyperliquidDCABot):
    """Render the portfolio tab."""
    st.subheader("🪙 Portfolio Overview")
    
    try:
        # Add refresh and sync buttons
        col1, col2, col3 = st.columns([3, 1, 1])
        with col2:
            if st.button("🔄 Refresh", key="portfolio_refresh"):
                st.rerun()
        with col3:
            if st.button("📥 Sync History", key="portfolio_sync_history", help="Sync trade history from Hyperliquid API"):
                with st.spinner("Syncing trade history..."):
                    try:
                        sync_result = asyncio.run(bot.sync_trade_history_from_api())
                        if sync_result:
                            st.success("✅ Trade history synced!")
                            st.rerun()
                        else:
                            st.warning("⚠️ Sync completed but no new trades found")
                    except Exception as e:
                        st.error(f"❌ Sync failed: {e}")
        
        # Get current data
        current_price = asyncio.run(bot.get_btc_price())
        usdc_balance = asyncio.run(bot.get_usdc_balance())
        ubtc_balance = asyncio.run(bot.get_ubtc_balance())
        
        _render_current_holdings(current_price, usdc_balance, ubtc_balance, bot)
        
        # Portfolio performance
        if bot.trade_history:
            metrics = _calculate_portfolio_metrics(bot, current_price, ubtc_balance)
            _render_portfolio_performance(metrics)
            _render_portfolio_growth_chart(bot)
        else:
            st.info("💡 No trading history found. Click 'Sync History' to load trades from Hyperliquid or execute your first trade.")
            
    except Exception as e:
        st.error(f"❌ Error loading portfolio data: {e}")
        logger.error(f"Portfolio tab error: {e}")


def _create_trades_dataframe(trade_history: list) -> pd.DataFrame:
    """Create DataFrame from trade history."""
    trades_data = []
    for trade in trade_history:
        trades_data.append({
            'Date': trade.timestamp.strftime('%Y-%m-%d %H:%M'),
            'Price ($)': f"{trade.price:,.2f}",
            'USD Amount': f"{trade.amount_usd:.2f}",
            'UBTC Amount': f"{trade.amount_btc:.6f}",
            'Volatility (%)': f"{trade.volatility:.2f}"
        })
    return pd.DataFrame(trades_data)


def _render_trade_summary(trade_history: list):
    """Render trade summary metrics."""
    st.subheader("📊 Trade Summary")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Trades", len(trade_history))
    with col2:
        total_volume = sum(t.amount_btc for t in trade_history)
        st.metric("Total Volume", f"{total_volume:.6f} UBTC")
    with col3:
        avg_trade_size = sum(t.amount_usd for t in trade_history) / len(trade_history)
        st.metric("Avg Trade Size", f"${avg_trade_size:.2f}")


def render_trades_tab(bot: HyperliquidDCABot):
    """Render the trade history tab."""
    st.subheader("📜 Trade History")
    
    # Add refresh and sync buttons
    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
    with col2:
        if st.button("🔄 Refresh", key="trades_refresh"):
            st.rerun()
    with col3:
        if st.button("📥 Sync History", key="trades_sync_history", help="Sync trade history from Hyperliquid API"):
            with st.spinner("Syncing trade history..."):
                try:
                    sync_result = asyncio.run(bot.sync_trade_history_from_api())
                    if sync_result:
                        st.success("✅ Trade history synced!")
                        st.rerun()
                    else:
                        st.warning("⚠️ Sync completed but no new trades found")
                except Exception as e:
                    st.error(f"❌ Sync failed: {e}")
    with col4:
        show_manual_entry = st.button("➕ Add Trade", key="show_manual_entry", help="Manually add a historical trade")
    
    # Manual trade entry form
    if show_manual_entry:
        with st.expander("📝 Add Historical Trade", expanded=True):
            with st.form("manual_trade_form"):
                st.write("Add a historical trade manually if API sync doesn't find your trades:")
                
                col1, col2 = st.columns(2)
                with col1:
                    trade_date = st.date_input("Trade Date", value=datetime.now().date())
                    trade_price = st.number_input("BTC Price ($)", min_value=1.0, value=50000.0, step=100.0)
                with col2:
                    trade_time = st.time_input("Trade Time", value=datetime.now().time())
                    trade_amount_usd = st.number_input("USD Amount", min_value=1.0, value=100.0, step=1.0)
                
                if st.form_submit_button("💾 Add Trade"):
                    try:
                        from ..config.models import TradeRecord
                        
                        # Combine date and time
                        trade_datetime = datetime.combine(trade_date, trade_time)
                        btc_amount = trade_amount_usd / trade_price
                        
                        # Create trade record
                        trade_record = TradeRecord(
                            timestamp=trade_datetime,
                            price=trade_price,
                            amount_usd=trade_amount_usd,
                            amount_btc=btc_amount,
                            volatility=0.0,  # Manual entry
                            tx_hash=f"manual_{int(trade_datetime.timestamp())}"
                        )
                        
                        # Add to history
                        bot.trade_history.append(trade_record)
                        bot.trade_history.sort(key=lambda x: x.timestamp)
                        
                        # Save to storage
                        bot.storage.save(bot.trade_history)
                        
                        st.success(f"✅ Added trade: {btc_amount:.6f} UBTC at ${trade_price:,.2f}")
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"❌ Error adding trade: {e}")
    
    if bot.trade_history:
        # Create and display DataFrame
        df = _create_trades_dataframe(bot.trade_history)
        st.dataframe(df, use_container_width=True)
        
        # Download button
        csv = df.to_csv(index=False)
        st.download_button(
            label="📥 Download Trade History",
            data=csv,
            file_name=f"dca_trades_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
        
        _render_trade_summary(bot.trade_history)
    else:
        st.info("💡 No trades found. Try 'Sync History' to load from Hyperliquid API, 'Add Trade' to manually enter trades, or execute your first automated trade.")


def _render_volatility_metrics(bot: HyperliquidDCABot, current_volatility: float):
    """Render volatility metrics section."""
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Current Volatility", f"{current_volatility:.1f}%")
    
    with col2:
        position_size = bot.calculate_position_size(current_volatility) 
        st.metric("Recommended Position", f"${position_size:.2f}")
    
    with col3:
        if current_volatility <= bot.config.low_vol_threshold:
            strategy = "🟢 Max Investment"
        elif current_volatility >= bot.config.high_vol_threshold:
            strategy = "🔴 Min Investment"
        else:
            strategy = "🟡 Scaled Investment"
        st.metric("Strategy", strategy)


def _render_volatility_chart(bot: HyperliquidDCABot, current_volatility: float):
    """Render volatility thresholds chart."""
    st.subheader("🎯 Volatility Thresholds")
    
    fig = go.Figure()
    
    # Add threshold lines
    fig.add_hline(
        y=bot.config.low_vol_threshold,
        line_dash="dash",
        line_color="green",
        annotation_text=f"Low Threshold: {bot.config.low_vol_threshold}%"
    )
    
    fig.add_hline(
        y=bot.config.high_vol_threshold,
        line_dash="dash", 
        line_color="red",
        annotation_text=f"High Threshold: {bot.config.high_vol_threshold}%"
    )
    
    # Add current volatility
    fig.add_hline(
        y=current_volatility,
        line_color="blue",
        annotation_text=f"Current: {current_volatility:.1f}%"
    )
    
    fig.update_layout(
        title='Volatility Thresholds and Current Level',
        yaxis_title='Volatility (%)',
        showlegend=False
    )
    
    st.plotly_chart(fig, use_container_width=True)


def render_volatility_tab(bot: HyperliquidDCABot):
    """Render the volatility analysis tab."""
    st.subheader("📈 Volatility Analysis")
    
    try:
        # Get data
        prices = asyncio.run(bot.get_historical_prices(bot.config.volatility_window))
        current_volatility = asyncio.run(bot.calculate_volatility())
        
        if prices is not None and current_volatility is not None:
            _render_volatility_metrics(bot, current_volatility)
            _render_volatility_chart(bot, current_volatility)
        else:
            st.warning("Unable to load volatility data. Please check your internet connection.")
            
    except Exception as e:
        st.error(f"❌ Error loading volatility data: {e}")
        logger.error(f"Volatility tab error: {e}")


def render_dashboard(config: DCAConfig, bot: HyperliquidDCABot):
    """Render the main dashboard with migration to multi-asset."""
    st.title(f"{PAGE_ICON} {PAGE_TITLE}")
    
    # Check if migration is needed
    from ..utils.migration import check_migration_needed, perform_migration, get_migration_summary
    
    if check_migration_needed():
        # Show migration interface
        st.success("🚀 **Upgrade Available!** Your single-asset DCA can be upgraded to the new Multi-Asset system with smart indicators!")
        
        with st.expander("📋 See What Will Be Migrated", expanded=False):
            migration_summary = get_migration_summary(config)
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("#### 📊 Current Setup")
                current = migration_summary["current_setup"]
                st.write(f"• Asset: {current['asset']}")
                st.write(f"• Amount: {current['base_amount']}")
                st.write(f"• Frequency: {current['frequency']}")
                st.write(f"• Volatility: {current['volatility_range']}")
                st.write(f"• Status: {'✅ Enabled' if current['enabled'] else '❌ Disabled'}")
            
            with col2:
                st.markdown("#### 🌟 After Migration")
                after = migration_summary["after_migration"]
                st.write(f"• Asset: {after['asset']}")
                st.write(f"• Amount: {after['base_amount']}")
                st.write(f"• Frequency: {after['frequency']}")
                st.write(f"• Smart Indicators: {after['smart_indicators']}")
                st.write(f"• Ready for: {after['additional_assets']}")
            
            st.markdown("#### 🎯 Migration Benefits")
            for benefit in migration_summary["benefits"]:
                st.write(benefit)
        
        st.warning("⚠️ **Important**: Your current configuration will be backed up before migration. No data will be lost.")
        
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            if st.button("🚀 Migrate to Multi-Asset System", type="primary", use_container_width=True):
                with st.spinner("Migrating your configuration..."):
                    migrated_config = perform_migration()
                    
                    if migrated_config:
                        st.success("✅ Migration completed successfully!")
                        st.success("🎉 Your BTC configuration has been upgraded with smart indicators!")
                        st.info("💡 You can now add ETH, SOL, and other assets to your portfolio.")
                        
                        # Add a small delay and redirect
                        import time
                        time.sleep(2)
                        st.switch_page("pages/2_Multi_Asset_Dashboard.py")
                    else:
                        st.error("❌ Migration failed. Please check the logs or contact support.")
        
        st.markdown("---")
        st.subheader("📊 Current Single-Asset Dashboard")
        st.caption("⬆️ Migrate to Multi-Asset above for the best experience!")
    
    else:
        # Multi-Asset system is available - redirect users there
        st.success("🌟 **Multi-Asset DCA System Active!** Your configuration has been upgraded.")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🌟 Multi-Asset Config", type="primary", use_container_width=True):
                st.switch_page("pages/1_Multi_Asset_Config.py")
        with col2:
            if st.button("📊 Multi-Asset Dashboard", type="primary", use_container_width=True):
                st.switch_page("pages/2_Multi_Asset_Dashboard.py")
        
        st.markdown("---")
        st.info("💡 **New Users**: Use the Multi-Asset Config above to set up your DCA strategy with smart indicators!")
        st.markdown("---")
        st.subheader("📊 Legacy Single-Asset Interface")
        st.caption("The interface below is for legacy support only. We recommend using the Multi-Asset system above.")
    
    # Render sidebar configuration
    updated_config = render_sidebar(config)
    
    # Main dashboard tabs
    tab_overview, tab_portfolio, tab_trades, tab_volatility = st.tabs([
        "📊 Overview", 
        "🪙 Portfolio", 
        "📜 Trade History", 
        "📈 Volatility Analysis"
    ])
    
    with tab_overview:
        render_overview_tab(bot)
    
    with tab_portfolio:
        render_portfolio_tab(bot)
    
    with tab_trades:
        render_trades_tab(bot)
    
    with tab_volatility:
        render_volatility_tab(bot)