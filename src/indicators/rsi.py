"""
RSI (Relative Strength Index) Indicator for DCA Entry Timing.
"""

import pandas as pd
import numpy as np
from typing import Optional, List
from datetime import datetime, timedelta
from ..utils.logging_config import get_logger

logger = get_logger(__name__)


class RSIIndicator:
    """RSI indicator for determining overbought/oversold conditions."""
    
    def __init__(self, period: int = 14):
        """Initialize RSI indicator.
        
        Args:
            period: Number of periods for RSI calculation (default: 14)
        """
        self.period = period
        self._price_cache = {}
        self._rsi_cache = {}
        
    def calculate_rsi(self, prices: pd.DataFrame) -> Optional[float]:
        """Calculate RSI from price data.
        
        Args:
            prices: DataFrame with 'price' column and datetime index
            
        Returns:
            Current RSI value (0-100) or None if insufficient data
        """
        try:
            if len(prices) < self.period + 1:
                logger.warning(f"Insufficient data for RSI calculation: {len(prices)} < {self.period + 1}")
                return None
            
            # Ensure we have price column
            if 'price' not in prices.columns:
                logger.error("Price data missing 'price' column")
                return None
            
            # Calculate price changes
            price_changes = prices['price'].diff().dropna()
            
            if len(price_changes) < self.period:
                logger.warning(f"Insufficient price changes for RSI: {len(price_changes)} < {self.period}")
                return None
            
            # Separate gains and losses
            gains = price_changes.where(price_changes > 0, 0)
            losses = -price_changes.where(price_changes < 0, 0)
            
            # Calculate average gain and loss using Wilder's smoothing
            avg_gain = gains.rolling(window=self.period, min_periods=self.period).mean().iloc[-1]
            avg_loss = losses.rolling(window=self.period, min_periods=self.period).mean().iloc[-1]
            
            # Avoid division by zero
            if avg_loss == 0:
                return 100.0  # RSI = 100 when no losses
            
            # Calculate RSI
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
            
            logger.info(f"RSI calculated: {rsi:.2f} (period: {self.period})")
            return float(rsi)
            
        except Exception as e:
            logger.error(f"Error calculating RSI: {e}")
            return None
    
    def calculate_wilder_rsi(self, prices: pd.DataFrame) -> Optional[float]:
        """Calculate RSI using Wilder's exponential smoothing method.
        
        This is more accurate for continuous RSI calculation.
        
        Args:
            prices: DataFrame with 'price' column and datetime index
            
        Returns:
            Current RSI value using Wilder's method
        """
        try:
            if len(prices) < self.period + 1:
                return None
            
            price_changes = prices['price'].diff().dropna()
            gains = price_changes.where(price_changes > 0, 0)
            losses = -price_changes.where(price_changes < 0, 0)
            
            # Wilder's smoothing factor
            alpha = 1.0 / self.period
            
            # Initialize with simple average for first period
            avg_gain = gains.iloc[:self.period].mean()
            avg_loss = losses.iloc[:self.period].mean()
            
            # Apply Wilder's smoothing for remaining periods
            for i in range(self.period, len(gains)):
                avg_gain = alpha * gains.iloc[i] + (1 - alpha) * avg_gain
                avg_loss = alpha * losses.iloc[i] + (1 - alpha) * avg_loss
            
            if avg_loss == 0:
                return 100.0
            
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
            
            return float(rsi)
            
        except Exception as e:
            logger.error(f"Error calculating Wilder RSI: {e}")
            return None
    
    def should_buy(self, rsi: float, oversold_threshold: float = 30.0) -> bool:
        """Determine if RSI indicates a buy signal.
        
        Args:
            rsi: Current RSI value
            oversold_threshold: RSI level considered oversold (default: 30)
            
        Returns:
            True if RSI indicates oversold (buy signal)
        """
        if rsi is None:
            return False
        
        is_oversold = rsi < oversold_threshold
        
        if is_oversold:
            logger.info(f"RSI buy signal: {rsi:.2f} < {oversold_threshold}")
        else:
            logger.info(f"RSI no signal: {rsi:.2f} >= {oversold_threshold}")
        
        return is_oversold
    
    def should_skip(self, rsi: float, overbought_threshold: float = 70.0) -> bool:
        """Determine if RSI indicates skipping the trade.
        
        Args:
            rsi: Current RSI value
            overbought_threshold: RSI level considered overbought (default: 70)
            
        Returns:
            True if RSI indicates overbought (skip trade)
        """
        if rsi is None:
            return False
        
        is_overbought = rsi > overbought_threshold
        
        if is_overbought:
            logger.info(f"RSI skip signal: {rsi:.2f} > {overbought_threshold}")
        
        return is_overbought
    
    def get_signal_strength(self, rsi: float) -> str:
        """Get human-readable signal strength.
        
        Args:
            rsi: Current RSI value
            
        Returns:
            Signal strength description
        """
        if rsi is None:
            return "Unknown"
        
        if rsi < 20:
            return "Extremely Oversold"
        elif rsi < 30:
            return "Oversold"
        elif rsi < 40:
            return "Weak"
        elif rsi < 60:
            return "Neutral"
        elif rsi < 70:
            return "Strong"
        elif rsi < 80:
            return "Overbought"
        else:
            return "Extremely Overbought"
    
    def get_divergence_signal(self, prices: pd.DataFrame, rsi_values: List[float], lookback: int = 5) -> Optional[str]:
        """Detect bullish/bearish divergence between price and RSI.
        
        Args:
            prices: Recent price data
            rsi_values: Recent RSI values
            lookback: Periods to look back for divergence
            
        Returns:
            'bullish', 'bearish', or None if no divergence
        """
        try:
            if len(prices) < lookback or len(rsi_values) < lookback:
                return None
            
            recent_prices = prices['price'].iloc[-lookback:].values
            recent_rsi = rsi_values[-lookback:]
            
            # Check for bullish divergence: price making lower lows, RSI making higher lows
            price_trend = recent_prices[-1] < recent_prices[0]
            rsi_trend = recent_rsi[-1] > recent_rsi[0]
            
            if price_trend and rsi_trend:
                return "bullish"
            
            # Check for bearish divergence: price making higher highs, RSI making lower highs
            price_trend = recent_prices[-1] > recent_prices[0]
            rsi_trend = recent_rsi[-1] < recent_rsi[0]
            
            if price_trend and rsi_trend:
                return "bearish"
            
            return None
            
        except Exception as e:
            logger.error(f"Error detecting RSI divergence: {e}")
            return None


class RSIStrategy:
    """RSI-based DCA strategy implementation."""
    
    def __init__(self, 
                 rsi_period: int = 14,
                 oversold_threshold: float = 30.0,
                 overbought_threshold: float = 70.0,
                 use_wilder_method: bool = True):
        """Initialize RSI strategy.
        
        Args:
            rsi_period: RSI calculation period
            oversold_threshold: Buy when RSI below this level
            overbought_threshold: Skip when RSI above this level
            use_wilder_method: Use Wilder's smoothing (more accurate)
        """
        self.rsi_indicator = RSIIndicator(period=rsi_period)
        self.oversold_threshold = oversold_threshold
        self.overbought_threshold = overbought_threshold
        self.use_wilder_method = use_wilder_method
        
    async def should_execute_trade(self, prices: pd.DataFrame) -> dict:
        """Determine if trade should execute based on RSI.
        
        Args:
            prices: Historical price data
            
        Returns:
            Dict with decision, RSI value, and reasoning
        """
        try:
            # Calculate RSI
            if self.use_wilder_method:
                rsi = self.rsi_indicator.calculate_wilder_rsi(prices)
            else:
                rsi = self.rsi_indicator.calculate_rsi(prices)
            
            if rsi is None:
                return {
                    "execute": True,  # Default to execute if no RSI data
                    "rsi": None,
                    "reason": "Insufficient data for RSI calculation",
                    "signal_strength": "Unknown"
                }
            
            # Check buy/skip signals
            should_buy = self.rsi_indicator.should_buy(rsi, self.oversold_threshold)
            should_skip = self.rsi_indicator.should_skip(rsi, self.overbought_threshold)
            
            signal_strength = self.rsi_indicator.get_signal_strength(rsi)
            
            if should_skip:
                return {
                    "execute": False,
                    "rsi": rsi,
                    "reason": f"RSI overbought: {rsi:.2f} > {self.overbought_threshold}",
                    "signal_strength": signal_strength
                }
            elif should_buy:
                return {
                    "execute": True,
                    "rsi": rsi,
                    "reason": f"RSI oversold: {rsi:.2f} < {self.oversold_threshold}",
                    "signal_strength": signal_strength
                }
            else:
                return {
                    "execute": True,  # Neutral RSI, proceed with regular DCA
                    "rsi": rsi,
                    "reason": f"RSI neutral: {rsi:.2f}",
                    "signal_strength": signal_strength
                }
                
        except Exception as e:
            logger.error(f"Error in RSI strategy execution check: {e}")
            return {
                "execute": True,  # Default to execute on error
                "rsi": None,
                "reason": f"RSI calculation error: {e}",
                "signal_strength": "Error"
            }