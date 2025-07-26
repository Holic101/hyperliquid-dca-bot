"""Hyperliquid API client with improved error handling and caching."""

import asyncio
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import pandas as pd
from pycoingecko import CoinGeckoAPI

# Hyperliquid SDK imports
from hyperliquid.info import Info
from hyperliquid.exchange import Exchange

from ..utils.constants import BASE_URL, BITCOIN_SPOT_SYMBOL
from ..utils.logging_config import get_logger

logger = get_logger(__name__)


class HyperliquidAPIClient:
    """Enhanced API client with caching and error handling."""
    
    def __init__(self, account=None):
        self.info = Info(BASE_URL)
        self.exchange = Exchange(account, BASE_URL) if account else None
        self.coingecko = CoinGeckoAPI()
        
        # Enhanced caching system
        self._price_cache = {}
        self._balance_cache = {}
        self._historical_cache = {}
        self._cache_timeout = timedelta(minutes=1)
        self._balance_cache_timeout = timedelta(seconds=30)
        self._historical_cache_timeout = timedelta(minutes=5)
    
    def _is_cache_valid(self, cache_key: str, cache_dict: dict = None, timeout: timedelta = None) -> bool:
        """Check if cached data is still valid."""
        if cache_dict is None:
            cache_dict = self._price_cache
        if timeout is None:
            timeout = self._cache_timeout
            
        if cache_key not in cache_dict:
            return False
        
        cached_time, _ = cache_dict[cache_key]
        return datetime.now() - cached_time < timeout
    
    def _set_cache(self, cache_key: str, value: any, cache_dict: dict = None) -> None:
        """Set a value in the specified cache."""
        if cache_dict is None:
            cache_dict = self._price_cache
        cache_dict[cache_key] = (datetime.now(), value)
    
    def _get_cache(self, cache_key: str, cache_dict: dict = None) -> any:
        """Get a value from the specified cache."""
        if cache_dict is None:
            cache_dict = self._price_cache
        if cache_key in cache_dict:
            _, value = cache_dict[cache_key]
            return value
        return None
    
    def clear_cache(self) -> None:
        """Clear all caches."""
        self._price_cache.clear()
        self._balance_cache.clear()
        self._historical_cache.clear()
        logger.info("All caches cleared")
    
    async def get_current_price(self, use_cache: bool = True) -> Optional[float]:
        """Get current UBTC price with caching."""
        cache_key = "ubtc_price"
        
        if use_cache and self._is_cache_valid(cache_key):
            price = self._get_cache(cache_key)
            logger.info(f"Using cached UBTC price: ${price:.2f}")
            return price
        
        try:
            # Try Hyperliquid first
            mid_prices = self.info.all_mids()
            hl_price = float(mid_prices.get("UBTC", 0))
            
            if hl_price > 0:
                self._set_cache(cache_key, hl_price)
                logger.info(f"Fetched Hyperliquid UBTC price: ${hl_price:.2f}")
                return hl_price
            else:
                raise ValueError("No valid UBTC price from Hyperliquid")
                
        except Exception as e:
            logger.warning(f"Hyperliquid price fetch failed: {e}, trying CoinGecko")
            
            try:
                cg_data = self.coingecko.get_price(ids='bitcoin', vs_currencies='usd')
                cg_price = cg_data['bitcoin']['usd']
                
                self._set_cache(cache_key, cg_price)
                logger.info(f"Fetched CoinGecko BTC price: ${cg_price:.2f}")
                return cg_price
                
            except Exception as cg_e:
                logger.error(f"All price sources failed: {cg_e}")
                return None
    
    async def get_account_balance(self, wallet_address: str, coin: str, use_cache: bool = True) -> float:
        """Get balance for specific coin with caching."""
        cache_key = f"balance_{wallet_address}_{coin}"
        
        if use_cache and self._is_cache_valid(cache_key, self._balance_cache, self._balance_cache_timeout):
            balance = self._get_cache(cache_key, self._balance_cache)
            logger.info(f"Using cached {coin} balance: {balance}")
            return balance
        
        try:
            spot_state = self.info.spot_user_state(wallet_address)
            balance = next(
                (float(b["total"]) for b in spot_state.get("balances", []) if b["coin"] == coin), 
                0.0
            )
            
            self._set_cache(cache_key, balance, self._balance_cache)
            logger.info(f"{coin} balance: {balance}")
            return balance
            
        except Exception as e:
            logger.error(f"Error fetching {coin} balance: {e}")
            return 0.0
    
    async def get_historical_prices(self, days: int, use_cache: bool = True) -> Optional[pd.DataFrame]:
        """Get historical price data from CoinGecko with caching."""
        cache_key = f"historical_prices_{days}"
        
        if use_cache and self._is_cache_valid(cache_key, self._historical_cache, self._historical_cache_timeout):
            prices_df = self._get_cache(cache_key, self._historical_cache)
            logger.info(f"Using cached historical price data ({days} days)")
            return prices_df
        
        try:
            logger.info(f"Fetching {days} days of historical price data")
            
            cg_data = self.coingecko.get_coin_market_chart_by_id(
                id='bitcoin', vs_currency='usd', days=days
            )
            
            prices_df = pd.DataFrame(cg_data['prices'], columns=['timestamp', 'price'])
            prices_df['timestamp'] = pd.to_datetime(prices_df['timestamp'], unit='ms').dt.date
            prices_df = prices_df.groupby('timestamp').last().reset_index()
            prices_df.set_index('timestamp', inplace=True)
            
            self._set_cache(cache_key, prices_df, self._historical_cache)
            logger.info(f"Retrieved {len(prices_df)} daily price points")
            return prices_df
            
        except Exception as e:
            logger.error(f"Error fetching historical prices: {e}")
            return None
    
    async def execute_spot_order(self, amount_usd: float, current_price: float) -> Optional[Dict[str, Any]]:
        """Execute a spot order."""
        if not self.exchange:
            logger.error("Cannot execute order - no exchange connection")
            return None
        
        try:
            # Calculate UBTC amount
            ubtc_amount = round(amount_usd / current_price, 6)
            
            logger.info(f"Executing spot order: ${amount_usd:.2f} USDC for {ubtc_amount:.6f} UBTC")
            
            # Execute the order
            result = self.exchange.order(
                coin=BITCOIN_SPOT_SYMBOL,
                is_buy=True,
                sz=ubtc_amount,
                px=current_price,
                order_type={"limit": {"tif": "Ioc"}}  # Immediate or Cancel
            )
            
            if result.get("status") == "ok":
                logger.info(f"Order executed successfully: {result}")
                return result
            else:
                logger.error(f"Order failed: {result}")
                return None
                
        except Exception as e:
            logger.error(f"Error executing spot order: {e}")
            return None
    
    async def get_spot_fills(self, wallet_address: str, days: int = 30) -> list:
        """Get spot BTC/USDC fills for the wallet (includes @142 which shows as BTC/USDC in UI)."""
        try:
            logger.info(f"Fetching spot BTC/USDC fills for {wallet_address} (last {days} days)")
            
            # Query fills with extended timeframe (up to 1 year for better coverage)
            start_ms = int((datetime.now() - timedelta(days=min(days, 365))).timestamp() * 1000)
            
            logger.info(f"Querying fills from {datetime.fromtimestamp(start_ms/1000).strftime('%Y-%m-%d')}")
            
            # Get all fills first to see what we have
            all_fills = self.info.user_fills_by_time(wallet_address, start_time=start_ms)
            logger.info(f"Retrieved {len(all_fills)} total fills")
            
            # Log some sample fills for debugging
            if all_fills:
                sample_fills = all_fills[:3]
                for i, fill in enumerate(sample_fills):
                    logger.info(f"Sample fill {i+1}: {fill}")
            
            # Filter for BTC spot trades - @142 shows as BTC/USDC in the Hyperliquid UI
            btc_spot_fills = []
            for f in all_fills:
                coin = f.get("coin", "")
                # Look for @142 which corresponds to BTC/USDC trades as shown in the UI
                if coin == "@142":
                    btc_spot_fills.append(f)
                    logger.info(f"Found BTC spot fill: {coin} - {f.get('dir', f.get('side', ''))} - ${f.get('px', 0)} - {f.get('sz', 0)}")
            
            logger.info(f"Found {len(btc_spot_fills)} BTC spot fills in last {days} days")
            
            # If no direct matches, log all unique coins to help debug
            if not btc_spot_fills and all_fills:
                unique_coins = set()
                spot_coins = []
                for f in all_fills:
                    coin = f.get("coin")
                    if coin is not None:
                        unique_coins.add(coin)
                        if coin.startswith("@"):
                            spot_coins.append(coin)
                
                logger.info(f"Unique coins in fills: {unique_coins}")
                logger.info(f"Spot format coins found: {spot_coins}")
                logger.info(f"Looking for BTC/USDC as: @142")
            
            return btc_spot_fills
            
        except Exception as e:
            logger.error(f"Error fetching spot BTC fills: {e}")
            return []