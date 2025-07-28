"""Multi-Asset DCA Bot implementation."""

import asyncio
from datetime import datetime, timedelta
from typing import List, Optional, Dict
import eth_account
from eth_account.signers.local import LocalAccount

from ..config.models import MultiAssetDCAConfig, AssetDCAConfig, TradeRecord
from ..data.storage import TradeHistoryStorage
from ..data.api_client import HyperliquidAPIClient
from ..utils.logging_config import get_logger
from ..trading.volatility import VolatilityCalculator

logger = get_logger(__name__)


class MultiAssetDCABot:
    """Multi-Asset DCA Bot for managing multiple cryptocurrency DCA strategies."""
    
    def __init__(self, config: MultiAssetDCAConfig):
        """Initialize the Multi-Asset DCA bot."""
        self.config = config
        
        # Initialize trading account if private key provided
        if config.private_key:
            self.account: Optional[LocalAccount] = eth_account.Account.from_key(config.private_key)
            
            # Set wallet address from account if not provided in config
            if not self.config.wallet_address:
                self.config.wallet_address = self.account.address
                logger.info(f"Using wallet address from private key: {self.account.address}")
        else:
            self.account = None
            logger.warning("No private key provided - bot will run in read-only mode")
        
        # Initialize components
        self.api_client = HyperliquidAPIClient(self.account)
        self.storage = TradeHistoryStorage()
        
        # Load historical data (all assets combined for now)
        self.trade_history = self.storage.load()
        
        # Initialize volatility calculators per asset
        self.volatility_calculators = {}
        for asset_config in self.config.assets.values():
            self.volatility_calculators[asset_config.symbol] = VolatilityCalculator(
                asset_config.volatility_window
            )
        
        logger.info(f"Multi-Asset DCA Bot initialized for {len(self.config.assets)} assets")
    
    async def get_asset_price(self, asset: str) -> Optional[float]:
        """Get current price for specific asset."""
        return await self.api_client.get_asset_price(asset)
    
    async def get_asset_balance(self, asset: str) -> float:
        """Get current balance for specific asset."""
        return await self.api_client.get_asset_balance(self.config.wallet_address, asset)
    
    async def get_asset_historical_prices(self, asset: str, days: int):
        """Fetch historical price data for specific asset."""
        return await self.api_client.get_asset_historical_prices(asset, days)
    
    async def calculate_asset_volatility(self, asset: str) -> Optional[float]:
        """Calculate current market volatility for specific asset."""
        try:
            asset_config = self.config.assets.get(asset)
            if not asset_config:
                logger.error(f"No configuration found for asset: {asset}")
                return None
            
            prices = await self.get_asset_historical_prices(asset, asset_config.volatility_window)
            if prices is None:
                logger.warning(f"Could not fetch historical prices for {asset}")
                return None
            
            calculator = self.volatility_calculators.get(asset)
            if not calculator:
                logger.error(f"No volatility calculator found for {asset}")
                return None
            
            volatility = calculator.calculate_volatility(prices)
            logger.info(f"{asset} volatility: {volatility:.2f}%")
            return volatility
            
        except Exception as e:
            logger.error(f"Error calculating volatility for {asset}: {e}")
            return None
    
    def calculate_asset_position_size(self, asset: str, volatility: Optional[float]) -> float:
        """Calculate position size based on volatility for specific asset."""
        asset_config = self.config.assets.get(asset)
        if not asset_config:
            logger.error(f"No configuration found for asset: {asset}")
            return 0.0
        
        calculator = self.volatility_calculators.get(asset)
        if not calculator:
            logger.error(f"No volatility calculator found for {asset}")
            return asset_config.base_amount
        
        return calculator.calculate_position_size(volatility, asset_config)
    
    def should_execute_asset_trade(self, asset: str) -> bool:
        """Check if a trade should be executed for specific asset based on frequency."""
        asset_config = self.config.assets.get(asset)
        if not asset_config or not asset_config.enabled:
            logger.info(f"{asset} is disabled in configuration")
            return False
        
        # Get trade history for this specific asset
        asset_trades = [t for t in self.trade_history if t.asset == asset]
        
        if not asset_trades:
            logger.info(f"No trade history for {asset} - executing first trade")
            return True
        
        last_trade_time = asset_trades[-1].timestamp
        
        # Calculate time delta based on frequency
        delta_map = {
            "daily": timedelta(days=1),
            "weekly": timedelta(days=7),
            "monthly": timedelta(days=30)
        }
        
        required_delta = delta_map.get(asset_config.frequency, timedelta(days=7))
        time_since_last = datetime.now() - last_trade_time
        
        should_trade = time_since_last >= required_delta
        
        if should_trade:
            logger.info(f"{asset}: Time for next trade - {time_since_last} since last trade")
        else:
            remaining = required_delta - time_since_last
            logger.info(f"{asset}: Not time for trade yet - {remaining} remaining")
        
        return should_trade
    
    async def execute_asset_spot_trade(self, asset: str, amount_usd: float, current_price: float, volatility: float) -> Optional[dict]:
        """Execute a spot trade for specific asset."""
        logger.info(f"Executing {asset} spot trade: ${amount_usd:.2f} at ~${current_price:.2f}")
        
        try:
            # Calculate asset amount for the trade
            asset_amount = round(amount_usd / current_price, 6)
            
            # Check if we have exchange connection for real trading
            if not self.account:
                logger.warning(f"No account configured - simulating {asset} trade")
                return await self._simulate_asset_trade(asset, amount_usd, current_price, volatility, asset_amount)
            
            # Get asset mapping for Hyperliquid
            from ..data.api_client import ASSET_MAPPINGS
            asset_mapping = ASSET_MAPPINGS.get(asset)
            
            if not asset_mapping or asset_mapping["spot_index"] is None:
                logger.error(f"Asset {asset} not supported for trading on Hyperliquid")
                return await self._simulate_asset_trade(asset, amount_usd, current_price, volatility, asset_amount)
            
            # Execute real spot trade
            spot_index = asset_mapping["spot_index"]
            spot_symbol = f"@{spot_index}"  # Format: @140, @147, @151
            
            logger.info(f"Executing real {asset} spot order: {asset_amount:.6f} {asset} for ${amount_usd:.2f} via {spot_symbol}")
            
            # Create exchange connection if not exists
            if not hasattr(self, 'exchange') or not self.exchange:
                from hyperliquid.exchange import Exchange
                self.exchange = Exchange(self.account, self.api_client.info.base_url)
            
            # Execute the spot order
            result = self.exchange.order(
                coin=spot_symbol,
                is_buy=True,
                sz=asset_amount,
                px=current_price,
                order_type={"limit": {"tif": "Ioc"}}  # Immediate or Cancel
            )
            
            if result and result.get("status") == "ok":
                logger.info(f"✅ {asset} order executed successfully: {result}")
                
                # Create trade record for successful execution
                trade_record = TradeRecord(
                    timestamp=datetime.now(),
                    asset=asset,
                    price=current_price,
                    amount_usd=amount_usd,
                    amount_asset=asset_amount,
                    volatility=volatility,
                    tx_hash=result.get("response", {}).get("data", {}).get("statuses", [{}])[0].get("resting", {}).get("oid", "unknown")
                )
                
                # Save trade to storage
                self.storage.add_trade(trade_record)
                
                # Update local history
                self.trade_history.append(trade_record)
                
                logger.info(f"✅ {asset} trade recorded: {asset_amount:.6f} {asset} for ${amount_usd:.2f}")
                
                return {
                    "status": "ok",
                    "asset": asset,
                    "amount_usd": amount_usd,
                    "amount_asset": asset_amount,
                    "price": current_price,
                    "tx_hash": trade_record.tx_hash,
                    "simulated": False
                }
            else:
                logger.error(f"❌ {asset} order failed: {result}")
                # Fall back to simulation on failure
                return await self._simulate_asset_trade(asset, amount_usd, current_price, volatility, asset_amount)
                
        except Exception as e:
            logger.error(f"Error executing {asset} spot trade: {e}")
            # Fall back to simulation on error
            return await self._simulate_asset_trade(asset, amount_usd, current_price, volatility, asset_amount)
    
    async def _simulate_asset_trade(self, asset: str, amount_usd: float, current_price: float, volatility: float, asset_amount: float) -> dict:
        """Simulate an asset trade when real trading is not possible."""
        logger.warning(f"📋 SIMULATION ONLY - {asset} trade: {asset_amount:.6f} {asset} for ${amount_usd:.2f} (NOT SAVED TO HISTORY)")
        
        try:
            # CRITICAL: DO NOT save simulated trades to permanent storage or history
            # This was causing fake trades to appear in the dashboard
            
            logger.info(f"📋 Simulated {asset} trade (not recorded): {asset_amount:.6f} {asset} for ${amount_usd:.2f}")
            
            return {
                "status": "ok",
                "asset": asset,
                "amount_usd": amount_usd,
                "amount_asset": asset_amount,
                "price": current_price,
                "tx_hash": trade_record.tx_hash,
                "simulated": True
            }
            
        except Exception as e:
            logger.error(f"Error simulating {asset} trade: {e}")
            return {
                "status": "error",
                "asset": asset,
                "error": str(e),
                "simulated": True
            }
    
    async def execute_asset_dca_trade(self, asset: str, force: bool = False) -> Optional[dict]:
        """Execute a DCA trade for specific asset."""
        try:
            asset_config = self.config.assets.get(asset)
            if not asset_config:
                logger.error(f"No configuration found for asset: {asset}")
                return None
            
            # Check if trade should execute
            if not force and not self.should_execute_asset_trade(asset):
                logger.info(f"{asset}: Trade conditions not met, skipping")
                return None
            
            # Check USDC balance
            usdc_balance = await self.api_client.get_asset_balance(self.config.wallet_address, "USDC")
            if usdc_balance < asset_config.min_amount:
                logger.error(f"{asset}: Insufficient USDC balance: ${usdc_balance:.2f} < ${asset_config.min_amount:.2f}")
                return {
                    "status": "error",
                    "asset": asset,
                    "error": f"Insufficient USDC balance: ${usdc_balance:.2f} < ${asset_config.min_amount:.2f}",
                    "simulated": True
                }
            
            # Calculate volatility and position size
            volatility = await self.calculate_asset_volatility(asset)
            position_size = self.calculate_asset_position_size(asset, volatility)
            
            # Ensure we don't exceed available balance
            trade_amount = min(position_size, usdc_balance)
            
            # Get current price
            current_price = await self.get_asset_price(asset)
            if not current_price:
                logger.error(f"Could not fetch current price for {asset}")
                return {
                    "status": "error",
                    "asset": asset,
                    "error": f"Could not fetch current price for {asset}",
                    "simulated": True
                }
            
            # Execute the trade (simulated for now)
            result = await self.execute_asset_spot_trade(asset, trade_amount, current_price, volatility or 0)
            
            if result:
                logger.info(f"{asset} DCA trade completed successfully: ${trade_amount:.2f} at ${current_price:.2f}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error executing {asset} DCA trade: {e}")
            return {
                "status": "error",
                "asset": asset,
                "error": str(e),
                "simulated": True
            }
    
    async def execute_all_dca_trades(self, force: bool = False, parallel: bool = True) -> Dict[str, Optional[dict]]:
        """Execute DCA trades for all enabled assets, optionally in parallel."""
        results = {}
        
        enabled_assets = self.config.get_enabled_assets()
        
        if not enabled_assets:
            logger.warning("No assets enabled for DCA trading")
            return results
        
        logger.info(f"Executing DCA trades for {len(enabled_assets)} assets (parallel={parallel})")
        
        if parallel and len(enabled_assets) > 1:
            # Execute trades in parallel for better performance
            tasks = []
            
            for asset_config in enabled_assets:
                asset = asset_config.symbol
                task = self._execute_asset_trade_with_error_handling(asset, force)
                tasks.append((asset, task))
            
            # Wait for all trades to complete
            completed_tasks = await asyncio.gather(*[task for _, task in tasks], return_exceptions=True)
            
            # Process results
            for i, (asset, _) in enumerate(tasks):
                result = completed_tasks[i]
                if isinstance(result, Exception):
                    logger.error(f"Error executing parallel DCA trade for {asset}: {result}")
                    results[asset] = None
                else:
                    results[asset] = result
                    
        else:
            # Execute trades sequentially
            for asset_config in enabled_assets:
                asset = asset_config.symbol
                try:
                    result = await self.execute_asset_dca_trade(asset, force)
                    results[asset] = result
                    
                    # Small delay between trades to avoid rate limiting
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    logger.error(f"Error executing DCA trade for {asset}: {e}")
                    results[asset] = None
        
        # Log execution summary
        successful_trades = sum(1 for r in results.values() if r and r.get("status") == "ok")
        logger.info(f"DCA execution complete: {successful_trades}/{len(enabled_assets)} trades successful")
        
        return results
    
    async def _execute_asset_trade_with_error_handling(self, asset: str, force: bool = False) -> Optional[dict]:
        """Execute asset trade with proper error handling for parallel execution."""
        try:
            return await self.execute_asset_dca_trade(asset, force)
        except Exception as e:
            logger.error(f"Error in parallel execution for {asset}: {e}")
            return None
    
    async def sync_asset_trade_history(self, asset: str, days: int = 30) -> bool:
        """Sync trade history from API for specific asset."""
        if not self.config.wallet_address:
            logger.warning("No wallet address configured, cannot sync from API")
            return False
        
        try:
            logger.info(f"Syncing {asset} trade history from API for last {days} days...")
            
            # Get spot fills from API for this asset
            fills = await self.api_client.get_asset_spot_fills(self.config.wallet_address, asset, days)
            
            if not fills:
                # Try longer timeframe if no recent fills found
                if days < 365:
                    logger.info(f"No {asset} fills found in {days} days, trying last year...")
                    fills = await self.api_client.get_asset_spot_fills(self.config.wallet_address, asset, 365)
            
            if not fills:
                logger.info(f"No {asset} fills found on Hyperliquid (checked up to 1 year)")
                return True
            
            logger.info(f"Found {len(fills)} {asset} fills from API")
            
            # Convert API fills to TradeRecord format and add to history
            new_trades = []
            for fill in fills:
                try:
                    # Parse fill data
                    timestamp = datetime.fromtimestamp(int(fill.get('time', 0)) / 1000)
                    price = float(fill.get('px', 0))
                    size = float(fill.get('sz', 0))
                    amount_usd = price * size
                    side = fill.get('dir', fill.get('side', ''))
                    
                    # Only add buy orders (DCA purchases)
                    if side in ['B', 'Buy', 'buy', 'Open Long']:
                        trade_record = TradeRecord(
                            timestamp=timestamp,
                            asset=asset,
                            price=price,
                            amount_usd=amount_usd,
                            amount_asset=size,
                            volatility=0.0,  # We don't have volatility data from API
                            tx_hash=fill.get('oid')  # Order ID as reference
                        )
                        new_trades.append(trade_record)
                        logger.info(f"Found {asset} buy trade: {price} @ {size} on {timestamp.strftime('%Y-%m-%d')}")
                        
                except Exception as e:
                    logger.warning(f"Error parsing {asset} fill: {e}")
                    continue
            
            if new_trades:
                # Add new trades to history (avoid duplicates by checking timestamps/order IDs)
                existing_order_ids = {t.tx_hash for t in self.trade_history if t.tx_hash}
                unique_new_trades = [t for t in new_trades if t.tx_hash not in existing_order_ids]
                
                if unique_new_trades:
                    self.trade_history.extend(unique_new_trades)
                    self.trade_history.sort(key=lambda x: x.timestamp)  # Sort by timestamp
                    
                    # Save updated history
                    self.storage.save(self.trade_history)
                    
                    logger.info(f"Added {len(unique_new_trades)} new {asset} trades from API")
                    return True
                else:
                    logger.info(f"No new {asset} trades found (all already in history)")
                    return True
            else:
                logger.info(f"No {asset} buy trades found in the fills")
                return True
            
        except Exception as e:
            logger.error(f"Error syncing {asset} trade history from API: {e}")
            return False
    
    async def sync_all_trade_history(self, days: int = 30, parallel: bool = True) -> Dict[str, bool]:
        """Sync trade history for all assets, optionally in parallel."""
        results = {}
        
        # Only sync assets that have spot indices (can be traded on Hyperliquid)
        from ..data.api_client import ASSET_MAPPINGS
        tradeable_assets = [asset for asset in self.config.assets.keys() 
                           if ASSET_MAPPINGS.get(asset, {}).get("spot_index") is not None]
        
        if not tradeable_assets:
            logger.warning("No tradeable assets found for history sync")
            return results
        
        logger.info(f"Syncing trade history for {len(tradeable_assets)} assets (parallel={parallel})")
        
        if parallel and len(tradeable_assets) > 1:
            # Sync trade histories in parallel
            tasks = []
            
            for asset in tradeable_assets:
                task = self._sync_asset_history_with_error_handling(asset, days)
                tasks.append((asset, task))
            
            # Wait for all syncs to complete
            completed_tasks = await asyncio.gather(*[task for _, task in tasks], return_exceptions=True)
            
            # Process results
            for i, (asset, _) in enumerate(tasks):
                result = completed_tasks[i]
                if isinstance(result, Exception):
                    logger.error(f"Error syncing parallel history for {asset}: {result}")
                    results[asset] = False
                else:
                    results[asset] = result
                    
        else:
            # Sync trade histories sequentially
            for asset in tradeable_assets:
                try:
                    result = await self.sync_asset_trade_history(asset, days)
                    results[asset] = result
                    
                    # Small delay between API calls
                    await asyncio.sleep(0.5)
                    
                except Exception as e:
                    logger.error(f"Error syncing trade history for {asset}: {e}")
                    results[asset] = False
        
        # Log sync summary
        successful_syncs = sum(1 for r in results.values() if r)
        logger.info(f"History sync complete: {successful_syncs}/{len(tradeable_assets)} assets synced successfully")
        
        return results
    
    async def _sync_asset_history_with_error_handling(self, asset: str, days: int = 30) -> bool:
        """Sync asset history with proper error handling for parallel execution."""
        try:
            return await self.sync_asset_trade_history(asset, days)
        except Exception as e:
            logger.error(f"Error in parallel history sync for {asset}: {e}")
            return False
    
    def get_asset_portfolio_stats(self, asset: str) -> dict:
        """Calculate portfolio statistics for specific asset."""
        asset_trades = [t for t in self.trade_history if t.asset == asset]
        
        if not asset_trades:
            return {
                "total_invested": 0,
                "asset_holdings": 0,
                "avg_buy_price": 0,
                "trade_count": 0
            }
        
        total_invested = sum(t.amount_usd for t in asset_trades)
        asset_holdings = sum(t.amount_asset for t in asset_trades)
        avg_buy_price = total_invested / asset_holdings if asset_holdings > 0 else 0
        
        return {
            "total_invested": total_invested,
            "asset_holdings": asset_holdings,
            "avg_buy_price": avg_buy_price,
            "trade_count": len(asset_trades)
        }
    
    def get_portfolio_stats(self) -> dict:
        """Calculate overall portfolio statistics."""
        if not self.trade_history:
            return {
                "total_invested": 0,
                "total_trades": 0,
                "assets_traded": 0,
                "avg_trade_size": 0
            }
        
        total_invested = sum(t.amount_usd for t in self.trade_history)
        unique_assets = len(set(t.asset for t in self.trade_history))
        avg_trade_size = total_invested / len(self.trade_history)
        
        return {
            "total_invested": total_invested,
            "total_trades": len(self.trade_history),
            "assets_traded": unique_assets,
            "avg_trade_size": avg_trade_size
        }
    
    # Legacy compatibility methods
    async def get_btc_price(self) -> Optional[float]:
        """Legacy method for BTC price compatibility."""
        return await self.get_asset_price("BTC")
    
    async def get_usdc_balance(self) -> float:
        """Legacy method for USDC balance."""
        return await self.get_asset_balance("USDC")
    
    async def get_ubtc_balance(self) -> float:
        """Legacy method for UBTC balance."""
        return await self.get_asset_balance("BTC")