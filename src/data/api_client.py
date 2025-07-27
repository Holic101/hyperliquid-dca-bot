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

# Asset mapping for Hyperliquid spot pairs (Updated Phase 1.4.1)
ASSET_MAPPINGS = {
    "BTC": {"spot_index": 140, "coingecko_id": "bitcoin"},   # @140 - UBTC/USDC
    "ETH": {"spot_index": 147, "coingecko_id": "ethereum"},  # @147 - UETH/USDC
    "SOL": {"spot_index": 151, "coingecko_id": "solana"},    # @151 - USOL/USDC
    "AVAX": {"spot_index": None, "coingecko_id": "avalanche-2"},  # Not available on Hyperliquid spot
    "LINK": {"spot_index": None, "coingecko_id": "chainlink"},    # Not available on Hyperliquid spot
}


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
    
    async def discover_asset_spot_indices(self) -> Dict[str, int]:
        """Discover spot indices for all supported assets."""
        try:
            spot_meta = self.info.spot_meta()
            universe = spot_meta.get("universe", [])
            tokens = spot_meta.get("tokens", [])
            
            discovered_indices = {}
            
            for i, pair in enumerate(universe):
                token_indices = pair.get('tokens', [])
                if len(token_indices) == 2:
                    token1_idx, token2_idx = token_indices
                    
                    # Check if USDC is one of the tokens (index 0 is USDC)
                    if token2_idx == 0 and token1_idx < len(tokens):
                        token_name = tokens[token1_idx].get('name', '')
                        
                        # Map known tokens to our asset symbols
                        asset_mappings = {
                            'UBTC': 'BTC',
                            'UETH': 'ETH', 
                            'USOL': 'SOL',
                            'UAVAX': 'AVAX',
                            'ULINK': 'LINK'
                        }
                        
                        if token_name in asset_mappings:
                            asset_symbol = asset_mappings[token_name]
                            discovered_indices[asset_symbol] = i
                            logger.info(f"Discovered {asset_symbol}: @{i} ({token_name}/USDC)")
            
            return discovered_indices
            
        except Exception as e:
            logger.error(f"Error discovering asset indices: {e}")
            return {}
    
    async def get_asset_price(self, asset: str, use_cache: bool = True) -> Optional[float]:
        """Get current price for any supported asset."""
        cache_key = f"{asset.lower()}_price"
        
        if use_cache and self._is_cache_valid(cache_key):
            price = self._get_cache(cache_key)
            logger.info(f"Using cached {asset} price: ${price:.2f}")
            return price
        
        try:
            # Try Hyperliquid first for supported spot assets
            if asset in ASSET_MAPPINGS and ASSET_MAPPINGS[asset]["spot_index"] is not None:
                mid_prices = self.info.all_mids()
                spot_index = ASSET_MAPPINGS[asset]["spot_index"]
                spot_format = f"@{spot_index}"
                hl_price = float(mid_prices.get(spot_format, 0))
                
                if hl_price > 0:
                    self._set_cache(cache_key, hl_price)
                    logger.info(f"Fetched Hyperliquid {asset} price: ${hl_price:.2f} from {spot_format}")
                    return hl_price
            
            # Fallback to CoinGecko for all assets
            if asset in ASSET_MAPPINGS:
                coingecko_id = ASSET_MAPPINGS[asset]["coingecko_id"]
                cg_data = self.coingecko.get_price(ids=coingecko_id, vs_currencies='usd')
                cg_price = cg_data[coingecko_id]['usd']
                
                self._set_cache(cache_key, cg_price)
                logger.info(f"Fetched CoinGecko {asset} price: ${cg_price:.2f}")
                return cg_price
            else:
                logger.error(f"Unsupported asset: {asset}")
                return None
                
        except Exception as e:
            logger.error(f"All price sources failed for {asset}: {e}")
            return None

    async def get_current_price(self, use_cache: bool = True) -> Optional[float]:
        """Legacy method for BTC price (backwards compatibility)."""
        return await self.get_asset_price("BTC", use_cache)
    
    async def get_asset_balance(self, wallet_address: str, asset: str, use_cache: bool = True) -> float:
        """Get balance for any supported asset."""
        # Map asset to actual token name on Hyperliquid
        token_mappings = {
            "BTC": "UBTC",
            "ETH": "UETH", 
            "SOL": "USOL",
            "AVAX": "UAVAX",
            "LINK": "ULINK",
            "USDC": "USDC"
        }
        
        token_name = token_mappings.get(asset, asset)
        cache_key = f"balance_{wallet_address}_{asset}"
        
        if use_cache and self._is_cache_valid(cache_key, self._balance_cache, self._balance_cache_timeout):
            balance = self._get_cache(cache_key, self._balance_cache)
            logger.info(f"Using cached {asset} balance: {balance}")
            return balance
        
        try:
            spot_state = self.info.spot_user_state(wallet_address)
            balance = next(
                (float(b["total"]) for b in spot_state.get("balances", []) if b["coin"] == token_name), 
                0.0
            )
            
            self._set_cache(cache_key, balance, self._balance_cache)
            logger.info(f"{asset} balance: {balance}")
            return balance
            
        except Exception as e:
            logger.error(f"Error fetching {asset} balance: {e}")
            return 0.0

    async def get_account_balance(self, wallet_address: str, coin: str, use_cache: bool = True) -> float:
        """Legacy method for getting balance (backwards compatibility)."""
        return await self.get_asset_balance(wallet_address, coin, use_cache)
    
    async def get_asset_historical_prices(self, asset: str, days: int, use_cache: bool = True) -> Optional[pd.DataFrame]:
        """Get historical price data for any asset from CoinGecko with caching."""
        cache_key = f"historical_prices_{asset.lower()}_{days}"
        
        if use_cache and self._is_cache_valid(cache_key, self._historical_cache, self._historical_cache_timeout):
            prices_df = self._get_cache(cache_key, self._historical_cache)
            logger.info(f"Using cached {asset} historical price data ({days} days)")
            return prices_df
        
        try:
            logger.info(f"Fetching {days} days of {asset} historical price data")
            
            if asset not in ASSET_MAPPINGS:
                logger.error(f"Unsupported asset for historical data: {asset}")
                return None
            
            coingecko_id = ASSET_MAPPINGS[asset]["coingecko_id"]
            cg_data = self.coingecko.get_coin_market_chart_by_id(
                id=coingecko_id, vs_currency='usd', days=days
            )
            
            prices_df = pd.DataFrame(cg_data['prices'], columns=['timestamp', 'price'])
            prices_df['timestamp'] = pd.to_datetime(prices_df['timestamp'], unit='ms').dt.date
            prices_df = prices_df.groupby('timestamp').last().reset_index()
            prices_df.set_index('timestamp', inplace=True)
            
            self._set_cache(cache_key, prices_df, self._historical_cache)
            logger.info(f"Retrieved {len(prices_df)} daily {asset} price points")
            return prices_df
            
        except Exception as e:
            logger.error(f"Error fetching {asset} historical prices: {e}")
            return None

    async def get_historical_prices(self, days: int, use_cache: bool = True) -> Optional[pd.DataFrame]:
        """Legacy method for BTC historical prices (backwards compatibility)."""
        return await self.get_asset_historical_prices("BTC", days, use_cache)
    
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
    
    async def get_asset_spot_fills(self, wallet_address: str, asset: str, days: int = 30) -> list:
        """Get spot fills for any supported asset."""
        try:
            logger.info(f"Fetching spot {asset}/USDC fills for {wallet_address} (last {days} days)")
            
            # Get the spot index for this asset
            spot_index = ASSET_MAPPINGS.get(asset, {}).get("spot_index")
            if spot_index is None:
                logger.error(f"No spot index found for {asset}")
                return []
            
            spot_coin_format = f"@{spot_index}"
            logger.info(f"Looking for {asset} fills in format: {spot_coin_format}")
            
            # Query fills with extended timeframe (up to 1 year for better coverage)
            start_ms = int((datetime.now() - timedelta(days=min(days, 365))).timestamp() * 1000)
            
            logger.info(f"Querying fills from {datetime.fromtimestamp(start_ms/1000).strftime('%Y-%m-%d')}")
            
            # Get all fills first to see what we have
            all_fills = self.info.user_fills_by_time(wallet_address, start_time=start_ms)
            logger.info(f"Retrieved {len(all_fills)} total fills")
            
            # Filter for this asset's spot trades
            asset_spot_fills = []
            for f in all_fills:
                coin = f.get("coin", "")
                if coin == spot_coin_format:
                    asset_spot_fills.append(f)
                    logger.info(f"Found {asset} spot fill: {coin} - {f.get('dir', f.get('side', ''))} - ${f.get('px', 0)} - {f.get('sz', 0)}")
            
            logger.info(f"Found {len(asset_spot_fills)} {asset} spot fills in last {days} days")
            
            # If no direct matches, log all unique coins to help debug
            if not asset_spot_fills and all_fills:
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
                logger.info(f"Looking for {asset}/USDC as: {spot_coin_format}")
            
            return asset_spot_fills
            
        except Exception as e:
            logger.error(f"Error fetching spot {asset} fills: {e}")
            return []

    async def get_spot_fills(self, wallet_address: str, days: int = 30) -> list:
        """Legacy method for BTC spot fills (backwards compatibility)."""
        return await self.get_asset_spot_fills(wallet_address, "BTC", days)