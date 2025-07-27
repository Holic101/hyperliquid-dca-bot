"""
Enhanced Volatility Indicator for Dynamic DCA Frequency.
"""

import pandas as pd
import numpy as np
from typing import Optional, Dict, List
from datetime import datetime, timedelta
from ..utils.logging_config import get_logger

logger = get_logger(__name__)


class VolatilityIndicator:
    """Enhanced volatility calculations for dynamic DCA frequency adjustment."""
    
    def __init__(self, window: int = 30):
        """Initialize volatility indicator.
        
        Args:
            window: Rolling window for volatility calculation (default: 30 days)
        """
        self.window = window
        self._vol_cache = {}
    
    def calculate_realized_volatility(self, prices: pd.DataFrame) -> Optional[float]:
        """Calculate realized volatility (annualized standard deviation of returns).
        
        Args:
            prices: DataFrame with 'price' column and datetime index
            
        Returns:
            Annualized volatility as percentage or None if insufficient data
        """
        try:
            if len(prices) < self.window:
                logger.warning(f"Insufficient data for volatility: {len(prices)} < {self.window}")
                return None
            
            if 'price' not in prices.columns:
                logger.error("Price data missing 'price' column")
                return None
            
            # Calculate daily returns
            returns = prices['price'].pct_change().dropna()
            
            if len(returns) < self.window - 1:
                return None
            
            # Calculate rolling standard deviation of returns
            rolling_std = returns.rolling(window=self.window - 1, min_periods=self.window - 1).std()
            
            # Annualize volatility (assuming daily data)
            # Multiply by sqrt(365) for daily data to get annual volatility
            current_vol = rolling_std.iloc[-1] * np.sqrt(365) * 100  # Convert to percentage
            
            logger.info(f"Realized volatility ({self.window}d): {current_vol:.2f}%")
            return float(current_vol)
            
        except Exception as e:
            logger.error(f"Error calculating realized volatility: {e}")
            return None
    
    def calculate_parkinson_volatility(self, prices: pd.DataFrame) -> Optional[float]:
        """Calculate Parkinson volatility estimator (uses high-low range).
        
        More efficient for intraday volatility estimation if OHLC data available.
        
        Args:
            prices: DataFrame with 'high' and 'low' columns
            
        Returns:
            Parkinson volatility estimate or None
        """
        try:
            if 'high' not in prices.columns or 'low' not in prices.columns:
                # Fallback to realized volatility if no OHLC data
                return self.calculate_realized_volatility(prices)
            
            if len(prices) < self.window:
                return None
            
            # Parkinson estimator: (1/(4*ln(2))) * ln(H/L)^2
            hl_ratios = np.log(prices['high'] / prices['low']) ** 2
            parkinson_vol = np.sqrt(hl_ratios.rolling(window=self.window).mean() / (4 * np.log(2)))
            
            # Annualize and convert to percentage
            current_vol = parkinson_vol.iloc[-1] * np.sqrt(365) * 100
            
            logger.info(f"Parkinson volatility ({self.window}d): {current_vol:.2f}%")
            return float(current_vol)
            
        except Exception as e:
            logger.error(f"Error calculating Parkinson volatility: {e}")
            return self.calculate_realized_volatility(prices)  # Fallback
    
    def calculate_volatility_percentile(self, prices: pd.DataFrame, lookback: int = 252) -> Optional[float]:
        """Calculate current volatility percentile vs historical range.
        
        Args:
            prices: Historical price data
            lookback: Days to look back for percentile calculation
            
        Returns:
            Volatility percentile (0-100) or None
        """
        try:
            if len(prices) < max(self.window, lookback):
                return None
            
            # Calculate rolling volatility over the lookback period
            returns = prices['price'].pct_change().dropna()
            rolling_vol = returns.rolling(window=self.window).std() * np.sqrt(365) * 100
            
            if len(rolling_vol) < lookback:
                return None
            
            # Get historical volatility values
            historical_vols = rolling_vol.iloc[-lookback:].dropna()
            current_vol = rolling_vol.iloc[-1]
            
            # Calculate percentile
            percentile = (historical_vols <= current_vol).mean() * 100
            
            logger.info(f"Volatility percentile: {percentile:.1f}% (current: {current_vol:.2f}%)")
            return float(percentile)
            
        except Exception as e:
            logger.error(f"Error calculating volatility percentile: {e}")
            return None
    
    def get_volatility_regime(self, volatility: float, 
                            low_threshold: float = 25.0, 
                            high_threshold: float = 50.0) -> str:
        """Classify current volatility regime.
        
        Args:
            volatility: Current volatility percentage
            low_threshold: Low volatility threshold
            high_threshold: High volatility threshold
            
        Returns:
            'low', 'medium', or 'high' volatility regime
        """
        if volatility is None:
            return 'unknown'
        
        if volatility < low_threshold:
            return 'low'
        elif volatility < high_threshold:
            return 'medium'
        else:
            return 'high'
    
    def calculate_volatility_trend(self, prices: pd.DataFrame, short_window: int = 7, 
                                 long_window: int = 30) -> Optional[str]:
        """Calculate volatility trend (increasing/decreasing).
        
        Args:
            prices: Price data
            short_window: Short-term volatility window
            long_window: Long-term volatility window
            
        Returns:
            'increasing', 'decreasing', or 'stable'
        """
        try:
            if len(prices) < long_window + self.window:
                return None
            
            returns = prices['price'].pct_change().dropna()
            
            # Calculate short and long-term volatilities
            short_vol = returns.rolling(window=short_window).std().iloc[-1] * np.sqrt(365) * 100
            long_vol = returns.rolling(window=long_window).std().iloc[-1] * np.sqrt(365) * 100
            
            ratio = short_vol / long_vol
            
            if ratio > 1.2:  # 20% higher
                return 'increasing'
            elif ratio < 0.8:  # 20% lower
                return 'decreasing'
            else:
                return 'stable'
                
        except Exception as e:
            logger.error(f"Error calculating volatility trend: {e}")
            return None


class DynamicFrequencyStrategy:
    """Dynamic DCA frequency adjustment based on volatility."""
    
    def __init__(self, 
                 volatility_window: int = 30,
                 low_vol_threshold: float = 25.0,
                 high_vol_threshold: float = 50.0,
                 frequency_map: Dict[str, str] = None):
        """Initialize dynamic frequency strategy.
        
        Args:
            volatility_window: Window for volatility calculation
            low_vol_threshold: Low volatility threshold (%)
            high_vol_threshold: High volatility threshold (%)
            frequency_map: Mapping of vol regime to frequency
        """
        self.vol_indicator = VolatilityIndicator(volatility_window)
        self.low_vol_threshold = low_vol_threshold
        self.high_vol_threshold = high_vol_threshold
        self.frequency_map = frequency_map or {
            'low': 'monthly',      # Low volatility -> less frequent DCA
            'medium': 'weekly',    # Medium volatility -> regular DCA
            'high': 'daily'        # High volatility -> more frequent DCA
        }
    
    async def calculate_optimal_frequency(self, prices: pd.DataFrame, 
                                        current_frequency: str = 'weekly') -> Dict:
        """Calculate optimal DCA frequency based on current volatility.
        
        Args:
            prices: Historical price data
            current_frequency: Current DCA frequency
            
        Returns:
            Dict with frequency recommendation and analysis
        """
        try:
            # Calculate current volatility
            volatility = self.vol_indicator.calculate_realized_volatility(prices)
            
            if volatility is None:
                return {
                    "recommended_frequency": current_frequency,
                    "volatility": None,
                    "volatility_regime": "unknown",
                    "reason": "Insufficient data for volatility calculation",
                    "should_change": False
                }
            
            # Determine volatility regime
            vol_regime = self.vol_indicator.get_volatility_regime(
                volatility, self.low_vol_threshold, self.high_vol_threshold
            )
            
            # Get recommended frequency
            recommended_frequency = self.frequency_map[vol_regime]
            
            # Calculate volatility percentile for context
            vol_percentile = self.vol_indicator.calculate_volatility_percentile(prices)
            
            # Calculate volatility trend
            vol_trend = self.vol_indicator.calculate_volatility_trend(prices)
            
            # Determine if frequency should change
            should_change = recommended_frequency != current_frequency
            
            result = {
                "recommended_frequency": recommended_frequency,
                "current_frequency": current_frequency,
                "volatility": volatility,
                "volatility_regime": vol_regime,
                "volatility_percentile": vol_percentile,
                "volatility_trend": vol_trend,
                "should_change": should_change,
                "reason": self._get_frequency_reason(vol_regime, volatility, vol_trend),
                "confidence": self._calculate_confidence(volatility, vol_percentile)
            }
            
            if should_change:
                logger.info(f"Frequency change recommended: {current_frequency} -> {recommended_frequency} "
                           f"(volatility: {volatility:.1f}%, regime: {vol_regime})")
            
            return result
            
        except Exception as e:
            logger.error(f"Error calculating optimal frequency: {e}")
            return {
                "recommended_frequency": current_frequency,
                "error": str(e),
                "should_change": False
            }
    
    def _get_frequency_reason(self, regime: str, volatility: float, trend: str) -> str:
        """Get human-readable reason for frequency recommendation."""
        base_reasons = {
            'low': f"Low volatility ({volatility:.1f}%) - reduce frequency to monthly",
            'medium': f"Medium volatility ({volatility:.1f}%) - maintain weekly frequency", 
            'high': f"High volatility ({volatility:.1f}%) - increase to daily for opportunities"
        }
        
        base_reason = base_reasons.get(regime, "Unknown volatility regime")
        
        if trend == 'increasing':
            return base_reason + " (volatility increasing)"
        elif trend == 'decreasing':
            return base_reason + " (volatility decreasing)"
        else:
            return base_reason
    
    def _calculate_confidence(self, volatility: float, percentile: Optional[float]) -> str:
        """Calculate confidence level in frequency recommendation."""
        if volatility is None:
            return "low"
        
        # High confidence if volatility is clearly in one regime
        if volatility < self.low_vol_threshold * 0.8 or volatility > self.high_vol_threshold * 1.2:
            return "high"
        
        # Medium confidence if percentile data supports the decision
        if percentile is not None:
            if (percentile < 25 and volatility < self.low_vol_threshold) or \
               (percentile > 75 and volatility > self.high_vol_threshold):
                return "high"
        
        # Lower confidence if near thresholds
        if abs(volatility - self.low_vol_threshold) < 5 or \
           abs(volatility - self.high_vol_threshold) < 5:
            return "low"
        
        return "medium"
    
    def get_frequency_multiplier(self, recommended_frequency: str, base_frequency: str = 'weekly') -> float:
        """Get position size multiplier based on frequency change.
        
        If increasing frequency (weekly->daily), reduce individual trade size.
        If decreasing frequency (weekly->monthly), increase individual trade size.
        
        Args:
            recommended_frequency: Recommended frequency
            base_frequency: Base/normal frequency
            
        Returns:
            Multiplier for individual trade size
        """
        frequency_weights = {
            'daily': 1.0,
            'weekly': 7.0,
            'monthly': 30.0
        }
        
        try:
            recommended_weight = frequency_weights[recommended_frequency]
            base_weight = frequency_weights[base_frequency]
            
            # Calculate multiplier to maintain similar total investment over time
            multiplier = base_weight / recommended_weight
            
            # Cap multipliers to reasonable ranges
            multiplier = max(0.3, min(3.0, multiplier))
            
            logger.info(f"Frequency multiplier: {multiplier:.2f}x "
                       f"({base_frequency} -> {recommended_frequency})")
            
            return multiplier
            
        except Exception as e:
            logger.error(f"Error calculating frequency multiplier: {e}")
            return 1.0  # Default to no change