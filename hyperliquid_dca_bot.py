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
import sys

# Local imports
from notifications import send_telegram_message

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

# --- Robust Logging Setup ---
# When running via Streamlit, basicConfig can be unreliable. This is a more robust way.
log_directory = Path(__file__).parent / "logs"
log_directory.mkdir(exist_ok=True)
log_file_path = log_directory / f"dca_bot_dashboard_{datetime.now().strftime('%Y%m%d')}.log"

# Get the root logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Remove existing handlers to avoid duplicates
if logger.hasHandlers():
    logger.handlers.clear()

# Create handlers
stream_handler = logging.StreamHandler(sys.stdout)
file_handler = logging.FileHandler(log_file_path)

# Create formatters and add it to handlers
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
stream_handler.setFormatter(formatter)
file_handler.setFormatter(formatter)

# Add handlers to the logger
logger.addHandler(stream_handler)
logger.addHandler(file_handler)
# --- End Logging Setup ---

# Constants
BASE_URL = constants.MAINNET_API_URL
CONFIG_FILE = "dca_config.json"
HISTORY_FILE = "dca_history.json"
BITCOIN_SYMBOL = "BTC"  # For price data from L2 snapshot
BITCOIN_SPOT_SYMBOL = "UBTC/USDC"  # For spot trading orders
MIN_USDC_BALANCE = 100.0

@dataclass
class DCAConfig:
    """Configuration for DCA strategy"""
    private_key: str
    wallet_address: Optional[str] = None
    base_amount: float = 50.0
    min_amount: float = 25.0
    max_amount: float = 100.0
    frequency: str = "weekly"
    volatility_window: int = 30
    low_vol_threshold: float = 35.0
    high_vol_threshold: float = 85.0
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

    def calculate_volatility(self, prices: pd.DataFrame) -> Optional[float]:
        if prices is None or len(prices) < self.window:
            logger.warning(f"Not enough historical data to calculate volatility (have {len(prices if prices is not None else [])}, need {self.window}).")
            return None
        prices['price'] = pd.to_numeric(prices['price'])
        returns = prices['price'].pct_change().dropna()
        if len(returns) < 2:
            return None
        daily_vol = returns.std()
        annualized_vol = daily_vol * np.sqrt(365) * 100
        return annualized_vol

class HyperliquidDCABot:
    """Main DCA Bot implementation"""
    def __init__(self, config: DCAConfig):
        self.config = config
        self.info = Info(BASE_URL)
        if config.private_key:
            self.account: Optional[LocalAccount] = eth_account.Account.from_key(config.private_key)
            self.exchange = Exchange(self.account, BASE_URL)
        else:
            self.account = None
            self.exchange = None
        self.volatility_calc = VolatilityCalculator(config.volatility_window)
        self.trade_history: List[TradeRecord] = []
        self.load_history()
        self.coingecko = CoinGeckoAPI()

    def load_history(self):
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
        try:
            cg_data = self.coingecko.get_coin_market_chart_by_id(
                id='bitcoin', vs_currency='usd', days=days
            )
            prices_cg = pd.DataFrame(cg_data['prices'], columns=['timestamp', 'price'])
            prices_cg['timestamp'] = pd.to_datetime(prices_cg['timestamp'], unit='ms').dt.date
            prices_cg = prices_cg.groupby('timestamp').last().reset_index()
            prices_cg.set_index('timestamp', inplace=True)
            return prices_cg
        except Exception as e:
            logger.error(f"Error fetching historical prices: {e}")
            return None

    async def get_btc_price(self) -> float:
        try:
            # Use all_mids() to get current price from Hyperliquid
            mid_prices = self.info.all_mids()
            # For Bitcoin, we need to use "UBTC" as the symbol
            hl_price = float(mid_prices.get("UBTC", 0))
            if hl_price > 0:
                logger.info(f"Using Hyperliquid price: ${hl_price:.2f}")
                return hl_price
            else:
                raise ValueError("No valid price found in all_mids")
        except Exception as e:
            logger.warning(f"Could not fetch price from Hyperliquid, falling back to CoinGecko: {e}")
            try:
                cg_price_data = self.coingecko.get_price(ids='bitcoin', vs_currencies='usd')
                cg_price = cg_price_data['bitcoin']['usd']
                logger.info(f"Using CoinGecko price: ${cg_price:.2f}")
                return cg_price
            except Exception as cg_e:
                logger.error(f"Failed to fetch price from all sources: {cg_e}")
                raise ConnectionError("Could not fetch BTC price.")

    def calculate_position_size(self, volatility: float) -> float:
        if volatility is None:
            return self.config.base_amount
        if volatility <= self.config.low_vol_threshold:
            return self.config.max_amount
        elif volatility >= self.config.high_vol_threshold:
            return self.config.min_amount
        else:
            vol_range = self.config.high_vol_threshold - self.config.low_vol_threshold
            vol_factor = (self.config.high_vol_threshold - volatility) / vol_range
            position_size = self.config.min_amount + (self.config.max_amount - self.config.min_amount) * vol_factor
            return max(self.config.min_amount, min(position_size, self.config.max_amount))

    async def execute_dca_trade(self) -> Optional[TradeRecord]:
        if not self.exchange or not self.account:
            logger.error("Exchange not initialized. Private key might be missing.")
            await send_telegram_message("❌ **Trade Error:** Bot is not initialized. Private key might be missing.")
            return None
        try:
            spot_state = self.info.spot_user_state(self.config.wallet_address)
            usdc_balance = next((float(b["total"]) for b in spot_state.get("balances", []) if b["coin"] == "USDC"), 0.0)
            if usdc_balance < MIN_USDC_BALANCE:
                message = f"⚠️ **Trade Skipped:** Balance \\({usdc_balance:.2f} USDC\\) is below minimum threshold \\(${MIN_USDC_BALANCE:.2f} USDC\\)\\."
                logger.error(message)
                await send_telegram_message(message)
                return None

            historical_prices = await self.get_historical_prices(self.config.volatility_window + 5)
            volatility = self.volatility_calc.calculate_volatility(historical_prices)
            position_size_usd = self.calculate_position_size(volatility)
            current_price = await self.get_btc_price()
            size_btc_unrounded = position_size_usd / current_price
            
            # Round to 5 decimal places to avoid float_to_wire error
            size_btc = round(size_btc_unrounded, 5)

            if position_size_usd < 10:
                logger.warning(f"Calculated trade size (${position_size_usd:.2f}) is below the $10 minimum. Skipping trade.")
                return None

            # Calculate a more aggressive limit price to improve fill rate
            # Use 0.1% slippage instead of market price to ensure better fills
            limit_price = current_price * 1.001  # 0.1% above current price for buy orders
            # Round to nearest dollar (BTC has $1 tick size)
            limit_price_rounded = round(limit_price)
            
            logger.info(f"Attempting to place spot order: size={size_btc:.8f} BTC (${position_size_usd:.2f}) at limit price ${limit_price_rounded:,.2f} (current: ${current_price:,.2f})")
            order_result = self.exchange.order(
                BITCOIN_SPOT_SYMBOL, True, size_btc, limit_price_rounded, {"limit": {"tif": "Ioc"}}
            )

            if order_result["status"] == "ok":
                # Debug: Log the full order response to understand the structure
                logger.info(f"Order response structure: {order_result}")
                
                statuses = order_result["response"]["data"]["statuses"]
                logger.info(f"Statuses: {statuses}")
                
                # Check multiple possible fields for transaction hash
                tx_hash = None
                if statuses:
                    first_status = statuses[0]
                    logger.info(f"First status: {first_status}")
                    
                    # Try different possible field names for transaction hash
                    tx_hash = first_status.get("txHash") or first_status.get("tx_hash") or first_status.get("hash") or first_status.get("transactionHash")
                    
                    # Also check if there's a "hash" field at the top level
                    if not tx_hash and "hash" in order_result["response"]["data"]:
                        tx_hash = order_result["response"]["data"]["hash"]
                
                logger.info(f"Extracted tx_hash: {tx_hash}")
                
                # Alternative: Check if order was filled by looking at status or fill information
                order_filled = False
                if statuses:
                    first_status = statuses[0]
                    # Check if order status indicates it was filled
                    status_text = first_status.get("status", "").lower()
                    filled_text = first_status.get("filled", "").lower()
                    
                    # Consider order filled if:
                    # 1. We have a tx_hash, OR
                    # 2. Status indicates filled, OR  
                    # 3. There's fill information
                    order_filled = (tx_hash is not None or 
                                   "filled" in status_text or 
                                   "filled" in filled_text or
                                   first_status.get("filledSz", 0) > 0)
                    
                    logger.info(f"Order status: {status_text}, filled: {filled_text}, filledSz: {first_status.get('filledSz', 0)}")
                    logger.info(f"Order filled determination: {order_filled}")

                if tx_hash or order_filled:
                    logger.info(f"✅ Trade executed successfully! Tx Hash: {tx_hash}")

                    # Send Telegram notification on success
                    # Escape special characters for Telegram Markdown
                    safe_tx_hash = str(tx_hash).replace('_', '\\_').replace('*', '\\*').replace('[', '\\[').replace(']', '\\]').replace('(', '\\(').replace(')', '\\)').replace('~', '\\~').replace('`', '\\`').replace('>', '\\>').replace('#', '\\#').replace('+', '\\+').replace('-', '\\-').replace('=', '\\=').replace('|', '\\|').replace('{', '\\{').replace('}', '\\}').replace('.', '\\.').replace('!', '\\!')
                    success_message = (
                        f"✅ **Trade Executed**\n\n"
                        f"Bought **{size_btc:.6f} BTC** for **${position_size_usd:,.2f}**\n"
                        f"Price: `${current_price:,.2f}`\n"
                        f"Volatility: `{volatility:.2f}%`\n\n"
                        f"Tx: `{safe_tx_hash}`"
                    )
                    await send_telegram_message(success_message)

                    trade = TradeRecord(
                        timestamp=datetime.now(),
                        price=current_price,
                        amount_usd=position_size_usd,
                        amount_btc=size_btc,
                        volatility=volatility if volatility is not None else 0,
                        tx_hash=tx_hash
                    )
                    self.trade_history.append(trade)
                    self.save_history()
                    return trade
                else:
                    # This case handles when the order is accepted but not filled (e.g., an IoC that doesn't fill)
                    logger.warning("⚠️ Trade submitted but not filled (no tx_hash). Order likely expired or was cancelled immediately.")
                    
                    # Try one more time with a slightly higher price (0.2% slippage)
                    retry_limit_price = current_price * 1.002
                    retry_limit_price_rounded = round(retry_limit_price)
                    
                    logger.info(f"Retrying with higher limit price: ${retry_limit_price_rounded:,.2f}")
                    retry_order_result = self.exchange.order(
                        BITCOIN_SPOT_SYMBOL, True, size_btc, retry_limit_price_rounded, {"limit": {"tif": "Ioc"}}
                    )
                    
                    if retry_order_result["status"] == "ok":
                        # Debug: Log the full retry order response
                        logger.info(f"Retry order response structure: {retry_order_result}")
                        
                        retry_statuses = retry_order_result["response"]["data"]["statuses"]
                        logger.info(f"Retry statuses: {retry_statuses}")
                        
                        # Check multiple possible fields for transaction hash
                        retry_tx_hash = None
                        if retry_statuses:
                            first_retry_status = retry_statuses[0]
                            logger.info(f"First retry status: {first_retry_status}")
                            
                            # Try different possible field names for transaction hash
                            retry_tx_hash = first_retry_status.get("txHash") or first_retry_status.get("tx_hash") or first_retry_status.get("hash") or first_retry_status.get("transactionHash")
                            
                            # Also check if there's a "hash" field at the top level
                            if not retry_tx_hash and "hash" in retry_order_result["response"]["data"]:
                                retry_tx_hash = retry_order_result["response"]["data"]["hash"]
                        
                        logger.info(f"Extracted retry_tx_hash: {retry_tx_hash}")
                        
                        # Alternative: Check if retry order was filled
                        retry_order_filled = False
                        if retry_statuses:
                            first_retry_status = retry_statuses[0]
                            retry_status_text = first_retry_status.get("status", "").lower()
                            retry_filled_text = first_retry_status.get("filled", "").lower()
                            
                            retry_order_filled = (retry_tx_hash is not None or 
                                                 "filled" in retry_status_text or 
                                                 "filled" in retry_filled_text or
                                                 first_retry_status.get("filledSz", 0) > 0)
                            
                            logger.info(f"Retry order status: {retry_status_text}, filled: {retry_filled_text}, filledSz: {first_retry_status.get('filledSz', 0)}")
                            logger.info(f"Retry order filled determination: {retry_order_filled}")
                        
                        if retry_tx_hash or retry_order_filled:
                            logger.info(f"✅ Retry successful! Tx Hash: {retry_tx_hash}")
                            
                            # Send Telegram notification on success
                            safe_tx_hash = str(retry_tx_hash).replace('_', '\\_').replace('*', '\\*').replace('[', '\\[').replace(']', '\\]').replace('(', '\\(').replace(')', '\\)').replace('~', '\\~').replace('`', '\\`').replace('>', '\\>').replace('#', '\\#').replace('+', '\\+').replace('-', '\\-').replace('=', '\\=').replace('|', '\\|').replace('{', '\\{').replace('}', '\\}').replace('.', '\\.').replace('!', '\\!')
                            success_message = (
                                f"✅ **Trade Executed (Retry)**\n\n"
                                f"Bought **{size_btc:.6f} BTC** for **${position_size_usd:.2f}**\n"
                                f"Price: `${retry_limit_price_rounded:,.2f}`\n"
                                f"Volatility: `{volatility:.2f}%`\n\n"
                                f"Tx: `{safe_tx_hash}`"
                            )
                            await send_telegram_message(success_message)

                            trade = TradeRecord(
                                timestamp=datetime.now(),
                                price=retry_limit_price_rounded,
                                amount_usd=position_size_usd,
                                amount_btc=size_btc,
                                volatility=volatility if volatility is not None else 0,
                                tx_hash=retry_tx_hash
                            )
                            self.trade_history.append(trade)
                            self.save_history()
                            return trade
                    
                    # If retry also failed, send warning
                    await send_telegram_message("⚠️ **Trade Warning:**\nOrder submitted but may not have filled \\(no tx\\_hash found\\)\\. Retry also failed\\.")
                    return None
            else:
                error_info = order_result.get("response", "No response data.")
                logger.error(f"❌ Trade failed: {error_info}")
                # Escape special characters for Telegram Markdown
                safe_error = str(error_info).replace('_', '\\_').replace('*', '\\*').replace('[', '\\[').replace(']', '\\]').replace('(', '\\(').replace(')', '\\)').replace('~', '\\~').replace('`', '\\`').replace('>', '\\>').replace('#', '\\#').replace('+', '\\+').replace('-', '\\-').replace('=', '\\=').replace('|', '\\|').replace('{', '\\{').replace('}', '\\}').replace('.', '\\.').replace('!', '\\!')
                await send_telegram_message(f"❌ **Trade Failed:**\n`{safe_error}`")
                return None
        except Exception as e:
            logger.error(f"Error during DCA trade execution: {e}", exc_info=True)
            # Escape special characters for Telegram Markdown
            safe_error = str(e).replace('_', '\\_').replace('*', '\\*').replace('[', '\\[').replace(']', '\\]').replace('(', '\\(').replace(')', '\\)').replace('~', '\\~').replace('`', '\\`').replace('>', '\\>').replace('#', '\\#').replace('+', '\\+').replace('-', '\\-').replace('=', '\\=').replace('|', '\\|').replace('{', '\\{').replace('}', '\\}').replace('.', '\\.').replace('!', '\\!')
            await send_telegram_message(f"🚨 **Bot Error:**\nAn unexpected error occurred during trade execution:\n`{safe_error}`")
            return None

    async def get_spot_asset_index(self, asset_name: str) -> Optional[int]:
        """Gets the spot asset TOKEN index for a given asset name, e.g., 'BTC'."""
        try:
            logger.info(f"Attempting to fetch spot metadata to find TOKEN index for '{asset_name}'...")
            spot_meta = self.info.spot_meta()
            
            # Step 1: Create a mapping from token symbol (e.g., "BTC") to its index.
            tokens_map = {token['name']: token['index'] for token in spot_meta.get("tokens", [])}
            logger.info(f"Built token map: {tokens_map}")

            # Handle API-specific ticker names. The API uses "UBTC" for Bitcoin.
            lookup_asset_name = asset_name.upper()
            if lookup_asset_name == "BTC":
                lookup_asset_name = "UBTC"
                logger.info("Mapping 'BTC' to 'UBTC' for API lookup.")

            # Step 2: Get the token index for the base asset (e.g., UBTC).
            base_asset_token_index = tokens_map.get(lookup_asset_name)

            if base_asset_token_index is None:
                logger.error(f"Could not find token index for base asset '{lookup_asset_name}' in the API's token list.")
                return None
            
            logger.info(f"Successfully found token index for {lookup_asset_name}: {base_asset_token_index}")
            return base_asset_token_index

        except Exception as e:
            logger.error(f"An unexpected error occurred in get_spot_asset_index: {e}", exc_info=True)
            return None

    async def get_usdc_balance(self) -> float:
        """Gets the user's spot USDC balance."""
        try:
            spot_state = self.info.spot_user_state(self.config.wallet_address)
            return next((float(b["total"]) for b in spot_state.get("balances", []) if b["coin"] == "USDC"), 0.0)
        except Exception as e:
            logger.error(f"Error fetching USDC balance: {e}")
            return 0.0

    # --- NEU: Spot-PnL-Utils ---
    def get_spot_fills(self, days: int = 365 * 5):
        """Alle Spot-Fills der letzten <days> Tage holen & filtern."""
        try:
            # Step 1: Use the single, correct function to get the asset index.
            # We use asyncio.run because this function is synchronous, but the one we're calling is async.
            btc_asset_index = asyncio.run(self.get_spot_asset_index("BTC"))
            
            if btc_asset_index is None:
                # The error is now correctly reported from the source function.
                return []

            # Step 2: Fetch fills and filter by the asset index
            start_ms = int((datetime.utcnow() - timedelta(days=days)).timestamp() * 1000)
            logger.info("Fetching user fills from API...")
            fills = self.info.user_fills_by_time(self.config.wallet_address, start_time=start_ms)
            logger.info(f"Found {len(fills)} total user fills (before filtering).")
            
            # The API returns fills with the asset index in the 'asset' field.
            filtered_fills = [f for f in fills if f.get("asset") == btc_asset_index]
            logger.info(f"Found {len(filtered_fills)} spot BTC fills (after filtering).")
            
            return filtered_fills

        except Exception as e:
            logger.error(f"Error getting spot fills: {e}", exc_info=True)
            return []

    def calc_realized_pnl(self, fills):
        """Summe der realisierten USDC-Gewinne."""
        return sum(float(f["closedPnl"]) for f in fills if float(f.get("closedPnl", 0)) != 0)

    def calc_unrealized_pnl(self):
        """Bestand, Kostenbasis & unrealisierte PnL via balances + Mid."""
        try:
            spot_state = self.info.spot_user_state(self.config.wallet_address)
            # For spot balances, we need to look for "UBTC" not "BTC"
            bal = next((b for b in spot_state["balances"] if b["coin"] == "UBTC"), None)
            if not bal:
                return 0.0, 0.0, 0.0
            
            pos_sz = float(bal["total"])
            cost_basis = float(bal.get("entryNtl", 0)) / pos_sz if pos_sz else 0
            mid_prices = self.info.all_mids()
            mid = float(mid_prices.get("UBTC", 0))
            
            unrealized_pnl = pos_sz * (mid - cost_basis) if mid > 0 else 0
            return unrealized_pnl, pos_sz, cost_basis
        except Exception as e:
            logger.error(f"Error calculating unrealized PnL: {e}")
            return 0.0, 0.0, 0.0
            
    def filter_by_period(self, fills, period: str):
        now = datetime.utcnow()
        delta = {
            "Tag": timedelta(days=1),
            "Woche": timedelta(weeks=1),
            "Monat": timedelta(days=30),
            "Jahr": timedelta(days=365),
            "Alles": None,
        }.get(period)
        
        if delta is None:
            return fills
        since = int((now - delta).timestamp() * 1000)
        return [f for f in fills if f["time"] >= since]
        
    async def get_account_trade_history(self) -> List[Dict]:
        """Fetch all historical fills for the user from the API."""
        try:
            return self.info.user_fills(self.config.wallet_address)
        except Exception as e:
            logger.error(f"Error fetching account trade history: {e}")
            return []

    def get_portfolio_stats(self) -> Dict:
        if not self.trade_history:
            return {"total_invested": 0, "btc_holdings": 0, "avg_buy_price": 0, "current_value": 0, "pnl": 0}
        
        total_invested = sum(t.amount_usd for t in self.trade_history)
        btc_holdings = sum(t.amount_btc for t in self.trade_history)
        avg_buy_price = total_invested / btc_holdings if btc_holdings > 0 else 0
        
        # This is a simple P&L calculation and does not fetch real-time value.
        # For a more accurate P&L, you would fetch the current price here.
        return {
            "total_invested": total_invested,
            "btc_holdings": btc_holdings,
            "avg_buy_price": avg_buy_price,
        }

    def should_execute_trade(self) -> bool:
        if not self.config.enabled:
            return False
        if not self.trade_history:
            return True
        
        last_trade_time = self.trade_history[-1].timestamp
        delta = timedelta(days=1 if self.config.frequency == "daily" else 7 if self.config.frequency == "weekly" else 30)
        
        return datetime.now() - last_trade_time >= delta

def init_session_state():
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    if "bot" not in st.session_state:
        st.session_state.bot = None
    if "config" not in st.session_state:
        st.session_state.config = load_config()

def load_config() -> Optional[DCAConfig]:
    try:
        with open(CONFIG_FILE, 'r') as f:
            config_data = json.load(f)
        
        wallet_address = os.getenv("HYPERLIQUID_WALLET_ADDRESS") or config_data.get("wallet_address")
        private_key = os.getenv("HYPERLIQUID_PRIVATE_KEY") or config_data.get("private_key", "")

        if not wallet_address:
            st.error("Wallet address not found. Please set HYPERLIQUID_WALLET_ADDRESS in your .env file or dca_config.json.")
            return None

        return DCAConfig(
            wallet_address=wallet_address,
            private_key=private_key,
            **{k: v for k, v in config_data.items() if k not in ["wallet_address", "private_key"]}
        )
    except FileNotFoundError:
        st.error(f"{CONFIG_FILE} not found. Please create it from the example.")
        return None
    except Exception as e:
        st.error(f"Error loading config: {e}")
        return None

def save_config(config: DCAConfig):
    save_data = {
        "base_amount": config.base_amount,
        "min_amount": config.min_amount,
        "max_amount": config.max_amount,
        "frequency": config.frequency,
        "volatility_window": config.volatility_window,
        "low_vol_threshold": config.low_vol_threshold,
        "high_vol_threshold": config.high_vol_threshold,
        "enabled": config.enabled
    }
    with open(CONFIG_FILE, 'w') as f:
        json.dump(save_data, f, indent=2)

def login_page():
    st.header("Login")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        if password == os.getenv("DCA_BOT_PASSWORD"):
            st.session_state.logged_in = True
            st.rerun()
        else:
            st.error("Incorrect password")

def dashboard_page():
    st.set_page_config(page_title="Hyperliquid DCA Bot", page_icon="📈", layout="wide")
    st.title("📈 Hyperliquid Spot DCA Bot")

    if st.session_state.config is None:
        st.error("Bot configuration is missing or invalid. Please check your config file.")
        return

    if st.session_state.bot is None:
        st.session_state.bot = HyperliquidDCABot(st.session_state.config)
    
    bot = st.session_state.bot

    # --- Sidebar ---
    with st.sidebar:
        st.header("Configuration")
        
        conf = st.session_state.config
        conf.enabled = st.toggle("Bot Enabled", value=conf.enabled)
        conf.base_amount = st.number_input("Base Amount ($)", value=float(conf.base_amount), step=10.0)
        conf.min_amount = st.number_input("Min Amount ($)", value=float(conf.min_amount), step=10.0)
        conf.max_amount = st.number_input("Max Amount ($)", value=float(conf.max_amount), step=10.0)
        conf.frequency = st.selectbox("Frequency", ["daily", "weekly", "monthly"], index=["daily", "weekly", "monthly"].index(conf.frequency))
        conf.volatility_window = st.slider("Volatility Window (days)", 10, 90, conf.volatility_window)
        conf.low_vol_threshold = st.slider("Low Volatility Threshold (%)", 10.0, 50.0, conf.low_vol_threshold)
        conf.high_vol_threshold = st.slider("High Volatility Threshold (%)", 50.0, 150.0, conf.high_vol_threshold)
        
        if st.button("Save Configuration"):
            save_config(conf)
            st.session_state.config = conf # Update session state
            st.success("Configuration saved!")
            st.rerun()

        st.header("Manual Control")
        if st.button("Execute Manual Trade", type="primary"):
            with st.spinner("Executing trade... Please wait."):
                try:
                    # Run the async function
                    trade_record = asyncio.run(bot.execute_dca_trade())
                    
                    if trade_record and trade_record.tx_hash:
                        st.success(f"✅ Trade executed! Bought {trade_record.amount_btc:.6f} BTC.")
                    elif trade_record:
                         st.warning("⚠️ Trade submitted but may not have filled (no tx_hash).")
                    else:
                        st.error("❌ Trade failed. Check logs for details.")
                    
                    # Add a small delay so the user can read the message before rerun
                    time.sleep(3)
                    st.rerun()

                except Exception as e:
                    st.error(f"An error occurred: {e}")
                    time.sleep(3)
                    st.rerun()


    # --- Main Page Tabs ---
    tab_overview, tab_portfolio, tab_trades, tab_vol = st.tabs(
        ["📊 Overview", "🪙 Portfolio", "📜 Trade History", "📈 Volatility Analysis"]
    )

    with tab_overview:
        period = st.selectbox("Zeitraum", ["Alles", "Jahr", "Monat", "Woche", "Tag"])
        
        # Data fetching and calculation
        spot_fills = bot.filter_by_period(bot.get_spot_fills(365 * 5), period)
        realized_pnl = bot.calc_realized_pnl(spot_fills)
        unrealized_pnl, position_size, avg_cost = bot.calc_unrealized_pnl()
        
        total_invested = sum(float(f["px"]) * float(f["sz"]) for f in spot_fills if f["side"] == "B")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Realisiert PnL", f"${realized_pnl:,.2f}")
        with col2:
            st.metric("Unrealisiert PnL", f"${unrealized_pnl:,.2f}")
        with col3:
            st.metric("Total Investiert (im Zeitraum)", f"${total_invested:,.2f}")

    with tab_portfolio:
        st.info("Portfolio analysis will be implemented here.")

    with tab_trades:
        st.subheader("Spot Trade History (UBTC/USDC)")
        if spot_fills:
            df = pd.DataFrame(spot_fills)
            df["time"] = pd.to_datetime(df["time"], unit="ms")
            # Ensure required columns exist before displaying
            display_cols = ["time", "side", "px", "sz", "closedPnl"]
            for col in display_cols:
                if col not in df.columns:
                    df[col] = 0 # Add missing columns with default value
            st.dataframe(df[display_cols].sort_values("time", ascending=False))
        else:
            st.info("No spot trades found for the selected period.")
            
    with tab_vol:
        st.info("Volatility analysis will be implemented here.")


def main():
    """Main Streamlit app function"""
    init_session_state()

    if not os.getenv("DCA_BOT_PASSWORD"):
        st.error("DCA_BOT_PASSWORD environment variable not set. Please set it to run the app.")
        return

    if st.session_state.logged_in:
        dashboard_page()
    else:
        login_page()

if __name__ == "__main__":
    main() 