"""
Smart Multi-Asset DCA Bot with Phase 2 Indicators.
Integrates RSI, Moving Average, and Dynamic Frequency strategies.
"""

import asyncio
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import pandas as pd
import eth_account
from eth_account.signers.local import LocalAccount

from ..config.models import MultiAssetDCAConfig, AssetDCAConfig, TradeRecord
from ..data.storage import TradeHistoryStorage
from ..data.api_client import HyperliquidAPIClient
from ..utils.logging_config import get_logger
from ..trading.volatility import VolatilityCalculator
from ..trading.multi_asset_bot import MultiAssetDCABot

# Phase 2 Indicators
from ..indicators.rsi import RSIStrategy
from ..indicators.moving_average import MovingAverageStrategy
from ..indicators.volatility import DynamicFrequencyStrategy

logger = get_logger(__name__)


class SmartMultiAssetDCABot(MultiAssetDCABot):
    """Enhanced Multi-Asset DCA Bot with smart indicators (Phase 2)."""
    
    def __init__(self, config: MultiAssetDCAConfig):
        """Initialize smart multi-asset bot with indicators."""
        super().__init__(config)
        
        # Initialize indicator strategies per asset
        self.rsi_strategies = {}
        self.ma_strategies = {}
        self.dynamic_freq_strategies = {}
        
        # Initialize indicators for each asset
        for asset_config in self.config.assets.values():
            self._initialize_asset_indicators(asset_config)
        
        logger.info(f"Smart Multi-Asset DCA Bot initialized with Phase 2 indicators")
    
    def get_last_trade_time(self, asset: str) -> Optional[datetime]:
        """Get the timestamp of the last trade for an asset."""
        try:
            asset_trades = [t for t in self.trade_history if t.asset == asset]
            if asset_trades:
                # Sort by timestamp and get the most recent
                latest_trade = max(asset_trades, key=lambda x: x.timestamp)
                return latest_trade.timestamp
            return None
        except Exception as e:
            logger.error(f"Error getting last trade time for {asset}: {e}")
            return None
    
    def should_execute_based_on_frequency(self, asset: str, last_trade_time: Optional[datetime]) -> Dict[str, Any]:
        """Check if asset should execute based on frequency timing."""
        try:
            asset_config = self.config.assets.get(asset)
            if not asset_config:
                return {
                    "should_execute": False,
                    "reason": f"No configuration for {asset}"
                }
            
            now = datetime.now()
            
            # If no previous trade, allow execution
            if last_trade_time is None:
                return {
                    "should_execute": True,
                    "reason": "No previous trades found"
                }
            
            # Calculate time since last trade
            time_since_last = now - last_trade_time
            
            # Determine minimum interval based on frequency
            if asset_config.frequency == "daily":
                min_interval = timedelta(days=1)
            elif asset_config.frequency == "weekly":
                min_interval = timedelta(weeks=1)
            elif asset_config.frequency == "monthly":
                min_interval = timedelta(days=30)
            else:
                # Default to weekly
                min_interval = timedelta(weeks=1)
            
            # Check if enough time has passed
            if time_since_last >= min_interval:
                return {
                    "should_execute": True,
                    "reason": f"Frequency check passed: {time_since_last.days} days since last trade"
                }
            else:
                remaining_time = min_interval - time_since_last
                next_execution = now + remaining_time
                return {
                    "should_execute": False,
                    "reason": f"Too soon: {remaining_time.days} days remaining",
                    "next_execution": next_execution
                }
                
        except Exception as e:
            logger.error(f"Error checking frequency for {asset}: {e}")
            return {
                "should_execute": False,
                "reason": f"Frequency check error: {e}"
            }
    
    def _initialize_asset_indicators(self, asset_config: AssetDCAConfig):
        """Initialize indicators for a specific asset."""
        asset = asset_config.symbol
        
        # RSI Strategy
        if asset_config.use_rsi:
            self.rsi_strategies[asset] = RSIStrategy(
                rsi_period=asset_config.rsi_period,
                oversold_threshold=asset_config.rsi_oversold_threshold,
                overbought_threshold=asset_config.rsi_overbought_threshold,
                use_wilder_method=asset_config.rsi_use_wilder
            )
            logger.info(f"RSI strategy initialized for {asset}")
        
        # Moving Average Strategy
        if asset_config.use_ma_dips:
            ma_periods = [int(p.strip()) for p in asset_config.ma_periods.split(',')]
            dip_thresholds = [float(t.strip()) / 100 for t in asset_config.ma_dip_thresholds.split(',')]
            
            # Create threshold mapping
            ma_dip_thresholds = {}
            for i, period in enumerate(ma_periods):
                if i < len(dip_thresholds):
                    ma_dip_thresholds[period] = dip_thresholds[i]
                else:
                    ma_dip_thresholds[period] = 0.05  # Default 5%
            
            self.ma_strategies[asset] = MovingAverageStrategy(
                ma_periods=ma_periods,
                ma_type=asset_config.ma_type,
                dip_thresholds=ma_dip_thresholds
            )
            logger.info(f"MA strategy initialized for {asset}: {ma_periods} periods")
        
        # Dynamic Frequency Strategy
        if asset_config.use_dynamic_frequency:
            self.dynamic_freq_strategies[asset] = DynamicFrequencyStrategy(
                volatility_window=asset_config.volatility_window,
                low_vol_threshold=asset_config.dynamic_low_vol_threshold,
                high_vol_threshold=asset_config.dynamic_high_vol_threshold
            )
            logger.info(f"Dynamic frequency strategy initialized for {asset}")
    
    async def analyze_asset_with_indicators(self, asset: str, 
                                          current_price: float) -> Dict[str, Any]:
        """Comprehensive asset analysis using all enabled indicators.
        
        Args:
            asset: Asset symbol
            current_price: Current asset price
            
        Returns:
            Dict with complete indicator analysis
        """
        try:
            asset_config = self.config.assets.get(asset)
            if not asset_config:
                logger.error(f"No configuration found for asset: {asset}")
                return {"error": "No asset configuration"}
            
            # Get historical price data
            historical_prices = await self.get_asset_historical_prices(asset, 100)  # 100 days for indicators
            
            if historical_prices is None or len(historical_prices) < 30:
                logger.warning(f"Insufficient historical data for {asset} indicators")
                return {
                    "asset": asset,
                    "current_price": current_price,
                    "error": "Insufficient historical data",
                    "indicators_enabled": False
                }
            
            # Convert to DataFrame format expected by indicators
            price_df = pd.DataFrame({
                'price': historical_prices['price']
            }, index=historical_prices.index)
            
            analysis = {
                "asset": asset,
                "current_price": current_price,
                "data_points": len(price_df),
                "indicators_enabled": True
            }
            
            # RSI Analysis
            if asset in self.rsi_strategies:
                try:
                    rsi_analysis = await self.rsi_strategies[asset].should_execute_trade(price_df)
                    analysis["rsi"] = rsi_analysis
                    logger.info(f"{asset} RSI analysis: {rsi_analysis.get('reason', 'N/A')}")
                except Exception as e:
                    logger.error(f"RSI analysis failed for {asset}: {e}")
                    analysis["rsi"] = {"error": str(e)}
            
            # Moving Average Analysis
            if asset in self.ma_strategies:
                try:
                    ma_analysis = await self.ma_strategies[asset].analyze_dip_opportunity(price_df, current_price)
                    analysis["moving_averages"] = ma_analysis
                    logger.info(f"{asset} MA analysis: {ma_analysis.get('recommendation', 'N/A')}")
                except Exception as e:
                    logger.error(f"MA analysis failed for {asset}: {e}")
                    analysis["moving_averages"] = {"error": str(e)}
            
            # Dynamic Frequency Analysis
            if asset in self.dynamic_freq_strategies:
                try:
                    freq_analysis = await self.dynamic_freq_strategies[asset].calculate_optimal_frequency(
                        price_df, asset_config.frequency
                    )
                    analysis["dynamic_frequency"] = freq_analysis
                    logger.info(f"{asset} frequency analysis: {freq_analysis.get('recommended_frequency', 'N/A')}")
                except Exception as e:
                    logger.error(f"Dynamic frequency analysis failed for {asset}: {e}")
                    analysis["dynamic_frequency"] = {"error": str(e)}
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error in asset indicator analysis for {asset}: {e}")
            return {
                "asset": asset,
                "current_price": current_price,
                "error": f"Analysis failed: {e}"
            }
    
    async def should_execute_smart_trade(self, asset: str) -> Dict[str, Any]:
        """Determine if trade should execute based on smart indicators.
        
        Args:
            asset: Asset symbol
            
        Returns:
            Dict with execution decision and reasoning
        """
        try:
            asset_config = self.config.assets.get(asset)
            if not asset_config:
                return {"execute": False, "reason": "No asset configuration"}
            
            # Check basic frequency timing first
            basic_should_execute = self.should_execute_asset_trade(asset)
            
            # Get current price
            current_price = await self.get_asset_price(asset)
            if not current_price:
                return {"execute": False, "reason": "Could not fetch current price"}
            
            # Get comprehensive indicator analysis
            analysis = await self.analyze_asset_with_indicators(asset, current_price)
            
            if analysis.get("error"):
                # Fallback to basic DCA if indicators fail
                return {
                    "execute": basic_should_execute,
                    "reason": f"Indicators failed, using basic timing: {analysis['error']}",
                    "strategy": "basic_dca",
                    "position_multiplier": 1.0
                }
            
            # Smart execution logic
            execution_decision = {
                "execute": basic_should_execute,
                "asset": asset,
                "current_price": current_price,
                "strategy": "smart_dca",
                "position_multiplier": 1.0,
                "indicators_used": [],
                "reasons": []
            }
            
            # RSI Check
            rsi_data = analysis.get("rsi", {})
            if rsi_data and not rsi_data.get("error"):
                execution_decision["indicators_used"].append("RSI")
                
                if not rsi_data.get("execute", True):
                    execution_decision["execute"] = False
                    execution_decision["reasons"].append(rsi_data.get("reason", "RSI signal"))
                else:
                    execution_decision["reasons"].append(rsi_data.get("reason", "RSI neutral"))
            
            # Moving Average Check & Position Sizing
            ma_data = analysis.get("moving_averages", {})
            if ma_data and not ma_data.get("error"):
                execution_decision["indicators_used"].append("MA")
                
                position_multiplier = ma_data.get("position_multiplier", 1.0)
                execution_decision["position_multiplier"] *= position_multiplier
                
                if ma_data.get("has_dip", False):
                    execution_decision["reasons"].append(
                        f"MA dip detected: {ma_data.get('max_dip_percentage', 0):.1f}% below MA"
                    )
                else:
                    execution_decision["reasons"].append("No significant MA dip")
            
            # Dynamic Frequency Check
            freq_data = analysis.get("dynamic_frequency", {})
            if freq_data and not freq_data.get("error"):
                execution_decision["indicators_used"].append("Dynamic Frequency")
                
                recommended_freq = freq_data.get("recommended_frequency")
                current_freq = asset_config.frequency
                
                if recommended_freq != current_freq:
                    freq_multiplier = self.dynamic_freq_strategies[asset].get_frequency_multiplier(
                        recommended_freq, current_freq
                    )
                    execution_decision["position_multiplier"] *= freq_multiplier
                    execution_decision["reasons"].append(
                        f"Frequency adjustment: {current_freq} -> {recommended_freq} (multiplier: {freq_multiplier:.2f}x)"
                    )
            
            # Final decision reasoning
            if execution_decision["execute"]:
                if execution_decision["position_multiplier"] > 1.5:
                    execution_decision["strategy"] = "aggressive_buy"
                elif execution_decision["position_multiplier"] > 1.2:
                    execution_decision["strategy"] = "enhanced_dca"
                else:
                    execution_decision["strategy"] = "regular_dca"
            else:
                execution_decision["strategy"] = "skip_trade"
            
            # Combine reasons
            execution_decision["reason"] = "; ".join(execution_decision["reasons"])
            
            logger.info(f"{asset} smart execution decision: {execution_decision['strategy']} "
                       f"(execute: {execution_decision['execute']}, "
                       f"multiplier: {execution_decision['position_multiplier']:.2f}x)")
            
            return execution_decision
            
        except Exception as e:
            logger.error(f"Error in smart trade decision for {asset}: {e}")
            return {
                "execute": basic_should_execute,
                "reason": f"Smart analysis failed: {e}",
                "strategy": "fallback_dca",
                "position_multiplier": 1.0
            }
    
    async def execute_smart_asset_dca_trade(self, asset: str, force: bool = False) -> Optional[dict]:
        """Execute DCA trade with smart indicator integration.
        
        Args:
            asset: Asset symbol
            force: Force execution regardless of timing/indicators
            
        Returns:
            Trade execution result
        """
        try:
            asset_config = self.config.assets.get(asset)
            if not asset_config:
                logger.error(f"No configuration found for asset: {asset}")
                return {
                    "status": "error",
                    "asset": asset,
                    "error": "No asset configuration",
                    "simulated": True
                }
            
            # Get smart execution decision
            if force:
                # For forced trades, skip indicator checks but still get analysis for position sizing
                current_price = await self.get_asset_price(asset)
                if not current_price:
                    return {
                        "status": "error",
                        "asset": asset,
                        "error": "Could not fetch current price",
                        "simulated": True
                    }
                
                analysis = await self.analyze_asset_with_indicators(asset, current_price)
                ma_data = analysis.get("moving_averages", {})
                position_multiplier = ma_data.get("position_multiplier", 1.0) if ma_data else 1.0
                
                execution_decision = {
                    "execute": True,
                    "reason": "Forced execution",
                    "strategy": "forced_smart_dca",
                    "position_multiplier": position_multiplier,
                    "current_price": current_price
                }
            else:
                execution_decision = await self.should_execute_smart_trade(asset)
            
            if not execution_decision.get("execute", False):
                logger.info(f"{asset}: Smart indicators recommend skipping trade - {execution_decision.get('reason', 'Unknown')}")
                return {
                    "status": "skipped",
                    "asset": asset,
                    "reason": execution_decision.get("reason", "Smart indicators recommend skip"),
                    "strategy": execution_decision.get("strategy", "unknown"),
                    "simulated": True
                }
            
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
            
            # Calculate enhanced position size with indicators
            base_volatility = await self.calculate_asset_volatility(asset)
            base_position_size = self.calculate_asset_position_size(asset, base_volatility)
            
            # Apply smart indicator multiplier
            smart_multiplier = execution_decision.get("position_multiplier", 1.0)
            enhanced_position_size = base_position_size * smart_multiplier
            
            # Ensure we don't exceed available balance or configured max
            final_trade_amount = min(enhanced_position_size, usdc_balance, asset_config.max_amount)
            
            current_price = execution_decision.get("current_price") or await self.get_asset_price(asset)
            if not current_price:
                return {
                    "status": "error",
                    "asset": asset,
                    "error": "Could not fetch current price",
                    "simulated": True
                }
            
            # Execute the enhanced trade
            result = await self.execute_asset_spot_trade(asset, final_trade_amount, current_price, base_volatility or 0)
            
            if result and result.get("status") == "ok":
                # Enhance result with smart strategy info
                result.update({
                    "strategy": execution_decision.get("strategy", "smart_dca"),
                    "indicators_used": execution_decision.get("indicators_used", []),
                    "position_multiplier": smart_multiplier,
                    "base_position_size": base_position_size,
                    "enhanced_position_size": enhanced_position_size,
                    "strategy_reason": execution_decision.get("reason", "Smart DCA execution")
                })
                
                logger.info(f"✅ {asset} smart DCA trade completed: ${final_trade_amount:.2f} "
                           f"(strategy: {result['strategy']}, multiplier: {smart_multiplier:.2f}x)")
            
            return result
            
        except Exception as e:
            logger.error(f"Error executing smart DCA trade for {asset}: {e}")
            return {
                "status": "error",
                "asset": asset,
                "error": str(e),
                "simulated": True
            }
    
    async def execute_all_smart_dca_trades(self, force: bool = False, parallel: bool = True) -> Dict[str, Optional[dict]]:
        """Execute smart DCA trades for all enabled assets.
        
        Args:
            force: Force execution for all assets
            parallel: Execute trades in parallel
            
        Returns:
            Dict mapping asset to execution result
        """
        results = {}
        
        enabled_assets = self.config.get_enabled_assets()
        
        if not enabled_assets:
            logger.warning("No assets enabled for smart DCA trading")
            return results
        
        logger.info(f"Executing smart DCA trades for {len(enabled_assets)} assets (parallel={parallel})")
        
        if parallel and len(enabled_assets) > 1:
            # Execute trades in parallel
            tasks = []
            
            for asset_config in enabled_assets:
                asset = asset_config.symbol
                task = self._execute_smart_asset_trade_with_error_handling(asset, force)
                tasks.append((asset, task))
            
            # Wait for all trades to complete
            completed_tasks = await asyncio.gather(*[task for _, task in tasks], return_exceptions=True)
            
            # Process results
            for i, (asset, _) in enumerate(tasks):
                result = completed_tasks[i]
                if isinstance(result, Exception):
                    logger.error(f"Error executing smart parallel DCA trade for {asset}: {result}")
                    results[asset] = None
                else:
                    results[asset] = result
                    
        else:
            # Execute trades sequentially
            for asset_config in enabled_assets:
                asset = asset_config.symbol
                try:
                    result = await self.execute_smart_asset_dca_trade(asset, force)
                    results[asset] = result
                    
                    # Small delay between trades
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    logger.error(f"Error executing smart DCA trade for {asset}: {e}")
                    results[asset] = None
        
        # Log execution summary
        successful_trades = sum(1 for r in results.values() if r and r.get("status") == "ok")
        skipped_trades = sum(1 for r in results.values() if r and r.get("status") == "skipped")
        failed_trades = len(results) - successful_trades - skipped_trades
        
        logger.info(f"Smart DCA execution complete: {successful_trades} successful, "
                   f"{skipped_trades} skipped by indicators, {failed_trades} failed")
        
        return results
    
    async def _execute_smart_asset_trade_with_error_handling(self, asset: str, force: bool = False) -> Optional[dict]:
        """Execute smart asset trade with error handling for parallel execution."""
        try:
            return await self.execute_smart_asset_dca_trade(asset, force)
        except Exception as e:
            logger.error(f"Error in smart parallel execution for {asset}: {e}")
            return None
    
    def get_asset_indicator_status(self, asset: str) -> Dict[str, Any]:
        """Get status of all indicators for an asset.
        
        Args:
            asset: Asset symbol
            
        Returns:
            Dict with indicator status and configuration
        """
        asset_config = self.config.assets.get(asset)
        if not asset_config:
            return {"error": "No asset configuration"}
        
        status = {
            "asset": asset,
            "indicators": {
                "rsi": {
                    "enabled": asset_config.use_rsi,
                    "configured": asset in self.rsi_strategies,
                    "period": asset_config.rsi_period,
                    "oversold_threshold": asset_config.rsi_oversold_threshold,
                    "overbought_threshold": asset_config.rsi_overbought_threshold
                },
                "moving_averages": {
                    "enabled": asset_config.use_ma_dips,
                    "configured": asset in self.ma_strategies,
                    "periods": asset_config.ma_periods,
                    "type": asset_config.ma_type,
                    "dip_thresholds": asset_config.ma_dip_thresholds
                },
                "dynamic_frequency": {
                    "enabled": asset_config.use_dynamic_frequency,
                    "configured": asset in self.dynamic_freq_strategies,
                    "low_vol_threshold": asset_config.dynamic_low_vol_threshold,
                    "high_vol_threshold": asset_config.dynamic_high_vol_threshold
                }
            }
        }
        
        return status