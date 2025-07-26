# hyperliquid_dca_bot.py
"""
Hyperliquid Volatility-Based DCA Bot
Implements the researched strategy with Streamlit frontend
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import json
import asyncio
from typing import Dict, List, Optional
import plotly.graph_objects as go
import plotly.express as px
from dataclasses import dataclass
import logging
import os
from pathlib import Path
from dotenv import load_dotenv
from pycoingecko import CoinGeckoAPI

# Hyperliquid SDK imports
from hyperliquid.info import Info
from hyperliquid.exchange import Exchange
from hyperliquid.utils import constants
from hyperliquid.utils.types import (
    Cloid,
)
import eth_account
from eth_account.signers.local import LocalAccount

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
BASE_URL = constants.MAINNET_API_URL  # Use TESTNET_API_URL for testing
SPOT_ASSET_CTX_ID = 10_000  # Context ID for spot trading - Note: not used in spot_order
CONFIG_FILE = "dca_config.json"
HISTORY_FILE = "dca_history.json"
BITCOIN_SYMBOL = "BTC" # For price data
BITCOIN_SPOT_SYMBOL = "UBTC/USDC" # For spot orders
MIN_USDC_BALANCE = 100.0  # Minimum USDC balance required for trading

@dataclass
class DCAConfig:
    """Configuration for DCA strategy"""
    wallet_address: str
    private_key: str
    base_amount: float = 100.0 # Defaulting to $100 as per user request
    min_amount: float = 100.0
    max_amount: float = 500.0
    frequency: str = "weekly"  # daily, weekly, monthly
    volatility_window: int = 30
    low_vol_threshold: float = 30.0 # Updated threshold
    high_vol_threshold: float = 100.0 # Updated threshold
    enabled: bool = True

@dataclass
class TradeRecord:
    """Record of a DCA trade"""
    timestamp: datetime
    price: float
    amount_usd: float
    amount_btc: float
    volatility: float
    tx_hash: Optional[str] = None

class VolatilityCalculator:
    """Calculate Bitcoin volatility metrics"""
    
    def __init__(self, window: int = 30):
        self.window = window
        self.price_history: List[float] = []
        self.timestamps: List[datetime] = []
    
    def add_price(self, price: float, timestamp: datetime):
        """Add a new price point"""
        self.price_history.append(price)
        self.timestamps.append(timestamp)
        
        # Keep only necessary history
        if len(self.price_history) > self.window * 2:
            self.price_history = self.price_history[-self.window * 2:]
            self.timestamps = self.timestamps[-self.window * 2:]
    
    def calculate_volatility(self, prices: pd.DataFrame) -> Optional[float]:
        """Calculate annualized volatility from a DataFrame of prices."""
        if prices is None or len(prices) < self.window:
            logger.warning(f"Not enough historical data to calculate volatility (have {len(prices if prices is not None else [])}, need {self.window}).")
            return None
        
        # Ensure the price column is numeric
        prices['price'] = pd.to_numeric(prices['price'])
        
        returns = prices['price'].pct_change().dropna()
        
        if len(returns) < 2:
            return None
        
        # Annualized volatility
        daily_vol = returns.std()
        annualized_vol = daily_vol * np.sqrt(365) * 100
        
        return annualized_vol

class HyperliquidDCABot:
    """Main DCA Bot implementation"""
    
    def __init__(self, config: DCAConfig):
        self.config = config
        self.info = Info(BASE_URL)
        self.account: LocalAccount = eth_account.Account.from_key(config.private_key)
        self.exchange = Exchange(self.account, BASE_URL)
        self.volatility_calc = VolatilityCalculator(config.volatility_window)
        self.trade_history: List[TradeRecord] = []
        self.load_history()
        self.coingecko = CoinGeckoAPI()
    
    def load_history(self):
        """Load trade history from file"""
        if Path(HISTORY_FILE).exists():
            try:
                with open(HISTORY_FILE, 'r') as f:
                    data = json.load(f)
                    self.trade_history = [
                        TradeRecord(
                            timestamp=datetime.fromisoformat(t['timestamp']),
                            price=t['price'],
                            amount_usd=t['amount_usd'],
                            amount_btc=t['amount_btc'],
                            volatility=t['volatility'],
                            tx_hash=t.get('tx_hash')
                        ) for t in data
                    ]
            except Exception as e:
                logger.error(f"Error loading history: {e}")
    
    def save_history(self):
        """Save trade history to file"""
        try:
            data = [
                {
                    'timestamp': t.timestamp.isoformat(),
                    'price': t.price,
                    'amount_usd': t.amount_usd,
                    'amount_btc': t.amount_btc,
                    'volatility': t.volatility,
                    'tx_hash': t.tx_hash
                } for t in self.trade_history
            ]
            with open(HISTORY_FILE, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving history: {e}")
    
    async def get_historical_prices(self, days: int) -> Optional[pd.DataFrame]:
        """Fetch historical prices from CoinGecko and Hyperliquid."""
        try:
            # 1. Fetch from CoinGecko (primary source)
            cg_data = self.coingecko.get_coin_market_chart_by_id(
                id='bitcoin', vs_currency='usd', days=days
            )
            prices_cg = pd.DataFrame(cg_data['prices'], columns=['timestamp', 'price'])
            prices_cg['timestamp'] = pd.to_datetime(prices_cg['timestamp'], unit='ms').dt.date
            prices_cg = prices_cg.groupby('timestamp').last().reset_index()
            prices_cg.set_index('timestamp', inplace=True)
            
            # 2. Fetch from Hyperliquid (for recent data, as fallback/average)
            # The SDK does not have a direct historical API, so we rely on what's available.
            # For this implementation, we'll primarily use CoinGecko and supplement
            # with Hyperliquid's current price for the most recent data point.
            
            # For a more robust solution, one might need to query a different endpoint
            # or use a third-party service that archives Hyperliquid's data.
            # For now, CoinGecko is sufficient for the 30-day window.
            
            return prices_cg

        except Exception as e:
            logger.error(f"Error fetching historical prices: {e}")
            return None

    async def get_btc_price(self) -> float:
        """Get current BTC price, averaging CoinGecko and Hyperliquid if possible."""
        cg_price = None
        hl_price = None
        
        try:
            # Get CoinGecko price
            cg_price_data = self.coingecko.get_price(ids='bitcoin', vs_currencies='usd')
            cg_price = cg_price_data['bitcoin']['usd']
        except Exception as e:
            logger.warning(f"Could not fetch price from CoinGecko: {e}")

        try:
            # Get Hyperliquid price using L2 snapshot
            l2_snapshot = self.info.l2_snapshot(BITCOIN_SYMBOL)
            hl_price = (float(l2_snapshot["levels"][0][0]["px"]) + float(l2_snapshot["levels"][1][0]["px"])) / 2
        except Exception as e:
            logger.warning(f"Could not fetch price from Hyperliquid: {e}")

        if cg_price and hl_price:
            avg_price = (cg_price + hl_price) / 2
            logger.info(f"Averaged price: ${avg_price:.2f} (CG: ${cg_price:.2f}, HL: ${hl_price:.2f})")
            return avg_price
        elif cg_price:
            logger.info(f"Using CoinGecko price: ${cg_price:.2f}")
            return cg_price
        elif hl_price:
            logger.info(f"Using Hyperliquid price: ${hl_price:.2f}")
            return hl_price
        else:
            logger.error("Failed to fetch price from all sources.")
            raise ConnectionError("Could not fetch BTC price from any source.")

    def calculate_position_size(self, volatility: float) -> float:
        """Calculate position size based on volatility"""
        if volatility is None:
            return self.config.base_amount
        
        if volatility <= self.config.low_vol_threshold:
            return self.config.max_amount
        elif volatility >= self.config.high_vol_threshold:
            return self.config.min_amount
        else:
            # Linear interpolation
            vol_range = self.config.high_vol_threshold - self.config.low_vol_threshold
            vol_factor = (self.config.high_vol_threshold - volatility) / vol_range
            position_size = self.config.min_amount + (self.config.max_amount - self.config.min_amount) * vol_factor
            
            return max(self.config.min_amount, min(position_size, self.config.max_amount))
    
    async def execute_dca_trade(self) -> Optional[TradeRecord]:
        """Execute a single DCA trade using spot orders"""
        try:
            # Check balance before proceeding
            spot_state = self.info.spot_user_state(self.config.wallet_address)
            usdc_balance = next((float(b["total"]) for b in spot_state.get("balances", []) if b["coin"] == "USDC"), 0.0)
            if usdc_balance < MIN_USDC_BALANCE:
                logger.error(f"Trade skipped: Balance ({usdc_balance:.2f}) is below minimum (${MIN_USDC_BALANCE:.2f}).")
                return None

            # 1. Fetch historical data for volatility calculation
            historical_prices = await self.get_historical_prices(self.config.volatility_window + 5) # Fetch a bit extra
            
            # 2. Calculate volatility
            current_volatility = self.volatility_calc.calculate_volatility(historical_prices)
            
            if current_volatility is None:
                logger.warning("Could not calculate volatility. Using base amount for this trade.")
                # Fallback to base amount if volatility calculation fails
                usd_amount = self.config.base_amount
            else:
                logger.info(f"Calculated 30-day volatility: {current_volatility:.2f}%")
                # 3. Calculate position size based on volatility
                usd_amount = self.calculate_position_size(current_volatility)

            logger.info(f"Determined position size: ${usd_amount:.2f}")

            # 4. Get current price for execution
            btc_price = await self.get_btc_price()
            btc_amount = usd_amount / btc_price
            
            # Get token info for rounding (use UBTC for metadata)
            spot_meta = self.info.spot_meta()
            btc_token = next((t for t in spot_meta["tokens"] if t["name"] == "UBTC"), None)
            if not btc_token:
                logger.error(f"Could not find UBTC in spot meta. Aborting trade.")
                return None
            
            btc_amount_rounded = round(btc_amount, btc_token["szDecimals"])

            # Check if we have enough balance for the trade
            if usdc_balance < usd_amount:
                logger.error(f"Trade skipped: Insufficient USDC balance ({usdc_balance:.2f}) for a ${usd_amount:.2f} trade.")
                return None

            # Calculate limit price with slippage
            limit_px = btc_price * 1.0001  # 0.01% slippage
            # Round to nearest dollar (BTC has $1 tick size)
            limit_px_rounded = round(limit_px)
            
            # Execute the order using the correct method signature
            logger.info(f"Executing spot order: {BITCOIN_SPOT_SYMBOL}, buy, {btc_amount_rounded}, ${limit_px_rounded}")
            result = self.exchange.order(
                BITCOIN_SPOT_SYMBOL,  # Use spot trading pair format
                True,   # is_buy
                btc_amount_rounded,
                limit_px_rounded,
                {"limit": {"tif": "Ioc"}}
            )

            # Check result and record trade
            if result["status"] == "ok":
                status = result["response"]["data"]["statuses"][0]
                if "filled" in status:
                    trade = TradeRecord(
                        timestamp=datetime.now(),
                        price=btc_price,
                        amount_usd=usd_amount,
                        amount_btc=btc_amount_rounded,
                        volatility=current_volatility or 0.0,
                        tx_hash=status.get("txHash")
                    )
                    self.trade_history.append(trade)
                    self.save_history()
                    logger.info(f"✅ DCA Trade executed successfully: {trade}")
                    # TODO: Add Telegram alert here
                    return trade
                else:
                    logger.warning(f"Order placed but not filled (IOC): {status}")
                    return None
            else:
                logger.error(f"❌ Order execution failed: {result}")
                # TODO: Add Telegram alert here
                return None

        except Exception as e:
            logger.error(f"Error executing DCA trade: {e}", exc_info=True)
            return None

    def get_portfolio_stats(self) -> Dict:
        """Calculate portfolio statistics"""
        if not self.trade_history:
            return {
                'total_invested': 0, 'total_btc': 0, 'avg_price': 0,
                'current_value': 0, 'pnl': 0, 'pnl_pct': 0, 
                'current_price': 0, 'trade_count': 0
            }
        
        total_invested = sum(t.amount_usd for t in self.trade_history)
        total_btc = sum(t.amount_btc for t in self.trade_history)
        avg_price = total_invested / total_btc if total_btc > 0 else 0
        
        try:
            # Simplified for now
            current_price = self.trade_history[-1].price if self.trade_history else 0
        except Exception:
            current_price = 0.0

        current_value = total_btc * current_price
        pnl = current_value - total_invested
        pnl_pct = (pnl / total_invested * 100) if total_invested > 0 else 0
        
        return {
            'total_invested': total_invested, 'total_btc': total_btc,
            'avg_price': avg_price, 'current_value': current_value,
            'current_price': current_price, 'pnl': pnl,
            'pnl_pct': pnl_pct, 'trade_count': len(self.trade_history)
        }
    
    def should_execute_trade(self) -> bool:
        """Check if it's time to execute a trade based on frequency"""
        if not self.config.enabled: return False
        if not self.trade_history: return True
        
        last_trade = self.trade_history[-1]
        time_since_last = datetime.now() - last_trade.timestamp
        
        if self.config.frequency == "daily": return time_since_last >= timedelta(days=1)
        if self.config.frequency == "weekly": return time_since_last >= timedelta(days=7)
        if self.config.frequency == "monthly": return time_since_last >= timedelta(days=30)
        
        return False

# Streamlit Application
def init_session_state():
    """Initialize Streamlit session state"""
    if 'authenticated' not in st.session_state: st.session_state.authenticated = False
    if 'bot' not in st.session_state: st.session_state.bot = None
    if 'config' not in st.session_state: st.session_state.config = load_config()

def load_config() -> Optional[DCAConfig]:
    """Load configuration from file"""
    if Path(CONFIG_FILE).exists():
        try:
            with open(CONFIG_FILE, 'r') as f:
                data = json.load(f)
                return DCAConfig(**data)
        except Exception as e:
            logger.error(f"Error loading config: {e}")
    return None

def save_config(config: DCAConfig):
    """Save configuration to file"""
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config.__dict__, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving config: {e}")

# --- UI Components ---
def login_page():
    """Display login page"""
    st.title("🔐 Hyperliquid DCA Bot Login")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("login_form"):
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Login", use_container_width=True)
            
            if submit:
                # Use environment variable for password check
                if password == os.getenv("DCA_BOT_PASSWORD"):
                    st.session_state.authenticated = True
                    st.rerun()
                else:
                    st.error("Invalid password")

def dashboard_page():
    """Display main dashboard"""
    st.title("📈 Hyperliquid Volatility-Based DCA Bot")
    
    # Initialize bot if needed
    if st.session_state.bot is None and st.session_state.config:
        try:
            # Augment config with private key from env if not in json
            if not st.session_state.config.private_key or "YOUR_PRIVATE_KEY" in st.session_state.config.private_key:
                 st.session_state.config.private_key = os.getenv("HYPERLIQUID_PRIVATE_KEY")
            
            if not st.session_state.config.private_key:
                st.error("Private key not found. Please set HYPERLIQUID_PRIVATE_KEY in your .env file.")
                return

            st.session_state.bot = HyperliquidDCABot(st.session_state.config)
        except Exception as e:
            st.error(f"Error initializing bot: {e}")
    
    # Sidebar configuration
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        if st.session_state.config is None:
            st.warning("No configuration found. Please set up the bot.")
            
            with st.form("config_form"):
                st.subheader("Wallet Settings")
                wallet_address = st.text_input("Wallet Address")
                # Private key is handled via .env for security
                st.info("The private key must be set as `HYPERLIQUID_PRIVATE_KEY` in your `.env` file.")

                st.subheader("DCA Settings")
                base_amount = st.number_input("Base Amount ($)", value=100.0, min_value=10.0, help="The default amount to invest per interval.")
                min_amount = st.number_input("Min Amount ($)", value=100.0, min_value=10.0)
                max_amount = st.number_input("Max Amount ($)", value=500.0, min_value=10.0)
                
                frequency = st.selectbox("Frequency", ["daily", "weekly", "monthly"], index=1)
                
                st.subheader("Volatility Settings")
                volatility_window = st.number_input("Volatility Window (days)", value=30, min_value=7)
                low_vol_threshold = st.number_input("Low Vol Threshold (%)", value=30.0, min_value=0.0)
                high_vol_threshold = st.number_input("High Vol Threshold (%)", value=100.0, min_value=0.0)
                
                submit = st.form_submit_button("Save Configuration", use_container_width=True)
                
                if submit:
                    private_key_from_env = os.getenv("HYPERLIQUID_PRIVATE_KEY")
                    if not private_key_from_env:
                        st.error("HYPERLIQUID_PRIVATE_KEY not set in .env file.")
                        return

                    config = DCAConfig(
                        wallet_address=wallet_address,
                        private_key=private_key_from_env, # Loaded from env
                        base_amount=base_amount,
                        min_amount=min_amount,
                        max_amount=max_amount,
                        frequency=frequency,
                        volatility_window=volatility_window,
                        low_vol_threshold=low_vol_threshold,
                        high_vol_threshold=high_vol_threshold
                    )
                    save_config(config)
                    st.session_state.config = config
                    st.success("Configuration saved!")
                    st.rerun()
        else:
            # Display current configuration
            config = st.session_state.config
            
            with st.expander("Current Settings", expanded=True):
                st.write(f"**Wallet:** `{config.wallet_address[:6]}...{config.wallet_address[-4:]}`")
                st.write(f"**Base Amount:** ${config.base_amount}")
                st.write(f"**Range:** ${config.min_amount} - ${config.max_amount}")
                st.write(f"**Frequency:** {config.frequency.capitalize()}")
                st.write(f"**Vol Window:** {config.volatility_window} days")
                st.write(f"**Vol Thresholds:** {config.low_vol_threshold}% - {config.high_vol_threshold}%")
            
            # Bot control
            st.subheader("Bot Control")
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("🟢 Enable Bot" if not config.enabled else "🔴 Disable Bot", 
                           use_container_width=True,
                           type="primary" if not config.enabled else "secondary"):
                    config.enabled = not config.enabled
                    save_config(config)
                    st.success(f"Bot {'enabled' if config.enabled else 'disabled'}!")
                    st.rerun()
            
            with col2:
                if st.button("💱 Execute Trade Now", use_container_width=True, disabled=not config.enabled):
                    with st.spinner("Executing trade..."):
                        trade_result = asyncio.run(st.session_state.bot.execute_dca_trade())
                        if trade_result:
                            st.success(f"Trade executed! Bought {trade_result.amount_btc:.8f} BTC")
                        else:
                            st.error("Trade failed. Check logs for details.")
            
            # Edit configuration
            if st.button("✏️ Edit Configuration", use_container_width=True):
                st.session_state.editing_config = True
                st.rerun()
            
            if hasattr(st.session_state, 'editing_config') and st.session_state.editing_config:
                with st.form("edit_config_form"):
                    st.subheader("Edit Configuration")
                    
                    base_amount = st.number_input("Base Amount ($)", value=config.base_amount, min_value=10.0)
                    min_amount = st.number_input("Min Amount ($)", value=config.min_amount, min_value=10.0)
                    max_amount = st.number_input("Max Amount ($)", value=config.max_amount, min_value=10.0)
                    frequency = st.selectbox("Frequency", ["daily", "weekly", "monthly"], 
                                           index=["daily", "weekly", "monthly"].index(config.frequency))
                    volatility_window = st.number_input("Volatility Window (days)", value=config.volatility_window, min_value=7)
                    low_vol_threshold = st.number_input("Low Vol Threshold (%)", value=config.low_vol_threshold, min_value=0.0)
                    high_vol_threshold = st.number_input("High Vol Threshold (%)", value=config.high_vol_threshold, min_value=0.0)
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.form_submit_button("Save Changes", use_container_width=True):
                            config.base_amount = base_amount
                            config.min_amount = min_amount
                            config.max_amount = max_amount
                            config.frequency = frequency
                            config.volatility_window = volatility_window
                            config.low_vol_threshold = low_vol_threshold
                            config.high_vol_threshold = high_vol_threshold
                            save_config(config)
                            st.session_state.editing_config = False
                            st.success("Configuration updated!")
                            st.rerun()
                    with col2:
                        if st.form_submit_button("Cancel", use_container_width=True):
                            st.session_state.editing_config = False
                            st.rerun()
    
    # Main dashboard content
    if st.session_state.bot:
        bot = st.session_state.bot
        
        # Tabs for different views
        tab1, tab2, tab3, tab4 = st.tabs(["📊 Overview", "📈 Portfolio", "📜 Trade History", "📉 Volatility Analysis"])
        
        with tab1:
            # Overview metrics
            col1, col2, col3, col4 = st.columns(4)
            
            # Get current stats
            stats = bot.get_portfolio_stats()
            
            # Fetch current price and balance
            try:
                current_price = asyncio.run(bot.get_btc_price())
                spot_state = bot.info.spot_user_state(bot.config.wallet_address)
                usdc_balance = next((float(b["total"]) for b in spot_state.get("balances", []) if b["coin"] == "USDC"), 0.0)
            except Exception as e:
                current_price = 0
                usdc_balance = 0
                st.error(f"Error fetching live data: {e}")
            
            with col1:
                st.metric("BTC Price", f"${current_price:,.2f}")
            
            with col2:
                st.metric("USDC Balance", f"${usdc_balance:.2f}")
            
            with col3:
                st.metric("Total Invested", f"${stats['total_invested']:,.2f}")
            
            with col4:
                st.metric("Total BTC", f"{stats['total_btc']:.8f}")
            
            # Second row of metrics
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Average Price", f"${stats['avg_price']:,.2f}")
            
            with col2:
                st.metric("Current Value", f"${stats['current_value']:,.2f}")
            
            with col3:
                pnl_color = "green" if stats['pnl'] >= 0 else "red"
                st.metric("P&L", f"${stats['pnl']:,.2f}", f"{stats['pnl_pct']:.2f}%")
            
            with col4:
                st.metric("Trade Count", stats['trade_count'])
            
            # Bot status
            st.subheader("🤖 Bot Status")
            
            status_col1, status_col2 = st.columns(2)
            
            with status_col1:
                st.info(f"**Status:** {'🟢 Active' if bot.config.enabled else '🔴 Inactive'}")
                st.info(f"**Frequency:** {bot.config.frequency.capitalize()}")
            
            with status_col2:
                should_trade = bot.should_execute_trade()
                st.info(f"**Next Trade:** {'Ready' if should_trade else 'Not yet'}")
                if bot.trade_history:
                    last_trade = bot.trade_history[-1]
                    st.info(f"**Last Trade:** {last_trade.timestamp.strftime('%Y-%m-%d %H:%M')}")
        
        with tab2:
            # Portfolio performance chart
            st.subheader("📈 Portfolio Performance")
            
            if bot.trade_history:
                # Create performance chart
                dates = [t.timestamp for t in bot.trade_history]
                invested = []
                values = []
                total_inv = 0
                total_btc = 0
                
                for trade in bot.trade_history:
                    total_inv += trade.amount_usd
                    total_btc += trade.amount_btc
                    invested.append(total_inv)
                    values.append(total_btc * trade.price)
                
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=dates, y=invested, name='Total Invested', line=dict(color='blue')))
                fig.add_trace(go.Scatter(x=dates, y=values, name='Portfolio Value', line=dict(color='green')))
                fig.update_layout(title='Portfolio Value vs Investment', xaxis_title='Date', yaxis_title='USD Value')
                st.plotly_chart(fig, use_container_width=True)
                
                # Position size history
                st.subheader("💰 Position Size History")
                sizes = [t.amount_usd for t in bot.trade_history]
                fig2 = go.Figure()
                fig2.add_trace(go.Bar(x=dates, y=sizes, name='Position Size'))
                fig2.update_layout(title='DCA Position Sizes', xaxis_title='Date', yaxis_title='USD Amount')
                st.plotly_chart(fig2, use_container_width=True)
            else:
                st.info("No trades yet. Start trading to see portfolio performance.")
        
        with tab3:
            # Trade history table
            st.subheader("📜 Trade History")
            
            if bot.trade_history:
                # Convert to DataFrame for display
                trade_data = []
                for trade in bot.trade_history:
                    trade_data.append({
                        'Date': trade.timestamp.strftime('%Y-%m-%d %H:%M'),
                        'Price': f"${trade.price:,.2f}",
                        'USD Amount': f"${trade.amount_usd:.2f}",
                        'BTC Amount': f"{trade.amount_btc:.8f}",
                        'Volatility': f"{trade.volatility:.2f}%"
                    })
                
                df = pd.DataFrame(trade_data)
                st.dataframe(df, use_container_width=True)
                
                # Download button
                csv = df.to_csv(index=False)
                st.download_button(
                    label="📥 Download Trade History",
                    data=csv,
                    file_name=f"dca_trades_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv"
                )
            else:
                st.info("No trades yet.")
        
        with tab4:
            # Volatility analysis
            st.subheader("📉 Volatility Analysis")
            
            # Fetch historical data
            with st.spinner("Fetching historical data..."):
                try:
                    historical_prices = asyncio.run(bot.get_historical_prices(60))
                    
                    if historical_prices is not None and len(historical_prices) > 0:
                        # Calculate rolling volatility
                        returns = historical_prices['price'].pct_change().dropna()
                        rolling_vol = returns.rolling(window=bot.config.volatility_window).std() * np.sqrt(365) * 100
                        
                        # Current volatility
                        current_vol = bot.volatility_calc.calculate_volatility(historical_prices.tail(bot.config.volatility_window + 5))
                        
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.metric("Current 30-day Volatility", f"{current_vol:.2f}%" if current_vol else "N/A")
                        
                        with col2:
                            if current_vol:
                                position_size = bot.calculate_position_size(current_vol)
                                st.metric("Current Position Size", f"${position_size:.2f}")
                        
                        # Volatility chart
                        fig = go.Figure()
                        fig.add_trace(go.Scatter(x=rolling_vol.index, y=rolling_vol.values, name='30-day Volatility'))
                        
                        # Add threshold lines
                        fig.add_hline(y=bot.config.low_vol_threshold, line_dash="dash", line_color="green", 
                                    annotation_text=f"Low Vol ({bot.config.low_vol_threshold}%)")
                        fig.add_hline(y=bot.config.high_vol_threshold, line_dash="dash", line_color="red",
                                    annotation_text=f"High Vol ({bot.config.high_vol_threshold}%)")
                        
                        fig.update_layout(title='Bitcoin 30-day Rolling Volatility', 
                                        xaxis_title='Date', yaxis_title='Volatility (%)')
                        st.plotly_chart(fig, use_container_width=True)
                        
                        # Position size vs volatility visualization
                        st.subheader("🎯 Position Sizing Strategy")
                        
                        vol_range = np.linspace(0, 150, 100)
                        position_sizes = [bot.calculate_position_size(v) for v in vol_range]
                        
                        fig2 = go.Figure()
                        fig2.add_trace(go.Scatter(x=vol_range, y=position_sizes, name='Position Size'))
                        fig2.add_vline(x=bot.config.low_vol_threshold, line_dash="dash", line_color="green")
                        fig2.add_vline(x=bot.config.high_vol_threshold, line_dash="dash", line_color="red")
                        if current_vol:
                            fig2.add_vline(x=current_vol, line_dash="solid", line_color="blue",
                                         annotation_text=f"Current ({current_vol:.1f}%)")
                        
                        fig2.update_layout(title='Position Size vs Volatility', 
                                         xaxis_title='Volatility (%)', yaxis_title='Position Size ($)')
                        st.plotly_chart(fig2, use_container_width=True)
                        
                    else:
                        st.error("Could not fetch historical price data.")
                        
                except Exception as e:
                    st.error(f"Error analyzing volatility: {e}")

def main():
    """Main application entry point"""
    st.set_page_config(page_title="Hyperliquid DCA Bot", layout="wide")
    init_session_state()
    
    if not st.session_state.authenticated:
        login_page()
    else:
        dashboard_page()

if __name__ == "__main__":
    main() 