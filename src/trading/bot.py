"""Main DCA Bot trading logic."""

import asyncio
from datetime import datetime, timedelta
from typing import List, Optional
import eth_account
from eth_account.signers.local import LocalAccount

# Local imports
from ..config.models import DCAConfig, TradeRecord
from ..data.storage import TradeHistoryStorage
from ..data.api_client import HyperliquidAPIClient
from ..utils.logging_config import get_logger
from .volatility import VolatilityCalculator

logger = get_logger(__name__)


class HyperliquidDCABot:
    """Main DCA Bot implementation with separated concerns."""
    
    def __init__(self, config: DCAConfig):
        """Initialize the DCA bot."""
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
        self.volatility_calc = VolatilityCalculator(config.volatility_window)
        self.storage = TradeHistoryStorage()
        self.api_client = HyperliquidAPIClient(self.account)
        
        # Load historical data
        self.trade_history = self.storage.load()
        
        # Also try to load recent trades from API if we have wallet address
        if self.config.wallet_address:
            logger.info(f"Loading trade history for wallet: {self.config.wallet_address}")
        else:
            logger.info("No wallet address configured, using local trade history only")

    async def get_historical_prices(self, days: int):
        """Fetch historical price data."""
        return await self.api_client.get_historical_prices(days)

    async def get_btc_price(self) -> float:
        """Get current BTC price."""
        price = await self.api_client.get_current_price()
        if price is None:
            raise ConnectionError("Could not fetch BTC price from any source")
        return price

    async def calculate_volatility(self) -> Optional[float]:
        """Calculate current market volatility."""
        try:
            prices = await self.get_historical_prices(self.config.volatility_window)
            return self.volatility_calc.calculate_volatility(prices)
        except Exception as e:
            logger.error(f"Error calculating volatility: {e}")
            return None

    def calculate_position_size(self, volatility: Optional[float]) -> float:
        """Calculate position size based on volatility."""
        return self.volatility_calc.calculate_position_size(volatility, self.config)

    def should_execute_trade(self) -> bool:
        """Check if a trade should be executed based on frequency."""
        if not self.config.enabled:
            logger.info("Bot is disabled in configuration")
            return False
            
        if not self.trade_history:
            logger.info("No trade history - executing first trade")
            return True
        
        last_trade_time = self.trade_history[-1].timestamp
        
        # Calculate time delta based on frequency
        delta_map = {
            "daily": timedelta(days=1),
            "weekly": timedelta(days=7),
            "monthly": timedelta(days=30)
        }
        
        required_delta = delta_map.get(self.config.frequency, timedelta(days=7))
        time_since_last = datetime.now() - last_trade_time
        
        should_trade = time_since_last >= required_delta
        
        if should_trade:
            logger.info(f"Time for next trade - {time_since_last} since last trade")
        else:
            remaining = required_delta - time_since_last
            logger.info(f"Not time for trade yet - {remaining} remaining")
            
        return should_trade

    async def get_usdc_balance(self) -> float:
        """Get current USDC balance from spot account."""
        return await self.api_client.get_account_balance(self.config.wallet_address, "USDC")

    async def get_ubtc_balance(self) -> float:
        """Get current UBTC balance from spot account."""
        return await self.api_client.get_account_balance(self.config.wallet_address, "UBTC")

    async def execute_spot_trade(self, amount_usd: float, current_price: float, volatility: float) -> Optional[dict]:
        """Execute a spot trade on Hyperliquid."""
        try:
            logger.info(f"Executing spot trade: ${amount_usd:.2f} USDC for UBTC at ~${current_price:.2f}")
            
            # Execute the trade using API client
            order_result = await self.api_client.execute_spot_order(amount_usd, current_price)
            
            if order_result and order_result.get("status") == "ok":
                logger.info(f"Trade executed successfully: {order_result}")
                
                # Calculate UBTC amount for record
                ubtc_amount = round(amount_usd / current_price, 6)
                
                # Record the trade
                trade_record = TradeRecord(
                    timestamp=datetime.now(),
                    price=current_price,
                    amount_usd=amount_usd,
                    amount_btc=ubtc_amount,
                    volatility=volatility,
                    tx_hash=None  # Hyperliquid doesn't provide tx hash in the same way
                )
                
                # Save trade to storage
                self.storage.add_trade(trade_record)
                
                # Update local history
                self.trade_history.append(trade_record)
                
                return order_result
            else:
                logger.error(f"Trade failed: {order_result}")
                return None
                
        except Exception as e:
            logger.error(f"Error executing trade: {e}")
            return None

    async def sync_trade_history_from_api(self, days: int = 30) -> bool:
        """Sync trade history from Hyperliquid API fills."""
        if not self.config.wallet_address:
            logger.warning("No wallet address configured, cannot sync from API")
            return False
            
        try:
            logger.info(f"Syncing trade history from API for last {days} days...")
            
            # Get spot fills from API with extended timeframe
            fills = await self.api_client.get_spot_fills(self.config.wallet_address, days)
            
            if not fills:
                # Try longer timeframe if no recent fills found
                if days < 365:
                    logger.info(f"No fills found in {days} days, trying last year...")
                    fills = await self.api_client.get_spot_fills(self.config.wallet_address, 365)
            
            if not fills:
                logger.info("No BTC fills found on Hyperliquid (checked up to 1 year)")
                return True  # Return True since sync completed, just no data found
            
            logger.info(f"Found {len(fills)} BTC fills from API")
            
            # Convert API fills to TradeRecord format and add to history
            new_trades = []
            for fill in fills:
                try:
                    # Parse fill data (adjust based on actual API response format)
                    timestamp = datetime.fromtimestamp(int(fill.get('time', 0)) / 1000)
                    price = float(fill.get('px', 0))
                    size = float(fill.get('sz', 0))
                    amount_usd = price * size
                    side = fill.get('dir', fill.get('side', ''))  # Try both 'dir' and 'side' fields
                    
                    # Only add buy orders (DCA purchases) - try different possible values
                    if side in ['B', 'Buy', 'buy', 'Open Long']:
                        trade_record = TradeRecord(
                            timestamp=timestamp,
                            price=price,
                            amount_usd=amount_usd,
                            amount_btc=size,
                            volatility=0.0,  # We don't have volatility data from API
                            tx_hash=fill.get('oid')  # Order ID as reference
                        )
                        new_trades.append(trade_record)
                        logger.info(f"Found buy trade: {price} @ {size} UBTC on {timestamp.strftime('%Y-%m-%d')}")
                        
                except Exception as e:
                    logger.warning(f"Error parsing fill: {e}")
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
                    
                    logger.info(f"Added {len(unique_new_trades)} new trades from API")
                    return True
                else:
                    logger.info("No new trades found (all already in history)")
                    return True
            else:
                logger.info("No buy trades found in the fills")
                return True
            
        except Exception as e:
            logger.error(f"Error syncing trade history from API: {e}")
            return False

    def get_portfolio_stats(self) -> dict:
        """Calculate portfolio statistics."""
        if not self.trade_history:
            return {
                "total_invested": 0, 
                "btc_holdings": 0, 
                "avg_buy_price": 0, 
                "current_value": 0, 
                "pnl": 0
            }
        
        total_invested = sum(t.amount_usd for t in self.trade_history)
        btc_holdings = sum(t.amount_btc for t in self.trade_history)
        avg_buy_price = total_invested / btc_holdings if btc_holdings > 0 else 0
        
        return {
            "total_invested": total_invested,
            "btc_holdings": btc_holdings,
            "avg_buy_price": avg_buy_price,
        }

    async def execute_dca_trade(self, force: bool = False) -> Optional[dict]:
        """Execute a DCA trade if conditions are met."""
        try:
            # Check if trade should execute
            if not force and not self.should_execute_trade():
                logger.info("Trade conditions not met, skipping")
                return None
            
            # Check USDC balance
            usdc_balance = await self.get_usdc_balance()
            if usdc_balance < self.config.min_amount:
                logger.error(f"Insufficient USDC balance: ${usdc_balance:.2f} < ${self.config.min_amount:.2f}")
                return None
            
            # Calculate volatility and position size
            volatility = await self.calculate_volatility()
            position_size = self.calculate_position_size(volatility)
            
            # Ensure we don't exceed available balance
            trade_amount = min(position_size, usdc_balance)
            
            # Get current price
            current_price = await self.get_btc_price()
            
            # Execute the trade
            result = await self.execute_spot_trade(trade_amount, current_price, volatility or 0)
            
            if result:
                logger.info(f"DCA trade completed successfully: ${trade_amount:.2f} at ${current_price:.2f}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error executing DCA trade: {e}")
            return None