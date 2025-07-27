"""
Moving Average indicators for DCA dip detection and trend analysis.
"""

import pandas as pd
import numpy as np
from typing import Optional, Dict, List, Tuple
from datetime import datetime
from ..utils.logging_config import get_logger

logger = get_logger(__name__)


class MovingAverageIndicator:
    """Moving Average calculations for trend analysis and dip detection."""
    
    def __init__(self, periods: List[int] = None):
        """Initialize Moving Average indicator.
        
        Args:
            periods: List of MA periods to calculate (default: [20, 50, 200])
        """
        self.periods = periods or [20, 50, 200]
        self._ma_cache = {}
    
    def calculate_sma(self, prices: pd.DataFrame, period: int) -> Optional[pd.Series]:
        """Calculate Simple Moving Average.
        
        Args:
            prices: DataFrame with 'price' column
            period: Number of periods for MA calculation
            
        Returns:
            Series with MA values or None if insufficient data
        """
        try:
            if len(prices) < period:
                logger.warning(f"Insufficient data for SMA{period}: {len(prices)} < {period}")
                return None
            
            if 'price' not in prices.columns:
                logger.error("Price data missing 'price' column")
                return None
            
            sma = prices['price'].rolling(window=period, min_periods=period).mean()
            logger.info(f"SMA{period} calculated: current value {sma.iloc[-1]:.2f}")
            return sma
            
        except Exception as e:
            logger.error(f"Error calculating SMA{period}: {e}")
            return None
    
    def calculate_ema(self, prices: pd.DataFrame, period: int) -> Optional[pd.Series]:
        """Calculate Exponential Moving Average.
        
        Args:
            prices: DataFrame with 'price' column
            period: Number of periods for EMA calculation
            
        Returns:
            Series with EMA values or None if insufficient data
        """
        try:
            if len(prices) < period:
                logger.warning(f"Insufficient data for EMA{period}: {len(prices)} < {period}")
                return None
            
            if 'price' not in prices.columns:
                logger.error("Price data missing 'price' column")
                return None
            
            ema = prices['price'].ewm(span=period, min_periods=period).mean()
            logger.info(f"EMA{period} calculated: current value {ema.iloc[-1]:.2f}")
            return ema
            
        except Exception as e:
            logger.error(f"Error calculating EMA{period}: {e}")
            return None
    
    def calculate_all_mas(self, prices: pd.DataFrame, ma_type: str = "SMA") -> Dict[int, Optional[float]]:
        """Calculate all configured moving averages.
        
        Args:
            prices: DataFrame with price data
            ma_type: "SMA" or "EMA"
            
        Returns:
            Dict mapping period to current MA value
        """
        mas = {}
        
        for period in self.periods:
            if ma_type.upper() == "EMA":
                ma_series = self.calculate_ema(prices, period)
            else:
                ma_series = self.calculate_sma(prices, period)
            
            if ma_series is not None and len(ma_series) > 0:
                mas[period] = float(ma_series.iloc[-1])
            else:
                mas[period] = None
        
        return mas
    
    def detect_dip(self, current_price: float, ma_values: Dict[int, float], 
                   dip_thresholds: Dict[int, float] = None) -> Dict[str, any]:
        """Detect price dips below moving averages.
        
        Args:
            current_price: Current asset price
            ma_values: Dict of MA period -> MA value
            dip_thresholds: Dict of MA period -> dip percentage threshold
            
        Returns:
            Dict with dip analysis and signals
        """
        if dip_thresholds is None:
            dip_thresholds = {20: 0.02, 50: 0.05, 200: 0.10}  # 2%, 5%, 10%
        
        dip_signals = {}
        max_dip_percentage = 0.0
        strongest_signal = None
        
        try:
            for period, ma_value in ma_values.items():
                if ma_value is None:
                    continue
                
                # Calculate percentage below MA
                dip_percentage = (ma_value - current_price) / ma_value
                threshold = dip_thresholds.get(period, 0.05)
                
                is_dip = dip_percentage > threshold
                
                dip_signals[f"MA{period}"] = {
                    "ma_value": ma_value,
                    "dip_percentage": dip_percentage * 100,  # Convert to percentage
                    "threshold": threshold * 100,
                    "is_dip": is_dip,
                    "signal_strength": self._get_dip_strength(dip_percentage)
                }
                
                if is_dip and dip_percentage > max_dip_percentage:
                    max_dip_percentage = dip_percentage
                    strongest_signal = f"MA{period}"
            
            # Overall dip assessment
            any_dip = any(signal["is_dip"] for signal in dip_signals.values())
            
            result = {
                "current_price": current_price,
                "has_dip": any_dip,
                "max_dip_percentage": max_dip_percentage * 100,
                "strongest_signal": strongest_signal,
                "ma_signals": dip_signals,
                "recommendation": self._get_dip_recommendation(dip_signals)
            }
            
            if any_dip:
                logger.info(f"Dip detected: {max_dip_percentage*100:.2f}% below {strongest_signal}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error detecting dip: {e}")
            return {
                "current_price": current_price,
                "has_dip": False,
                "error": str(e)
            }
    
    def _get_dip_strength(self, dip_percentage: float) -> str:
        """Get human-readable dip strength."""
        if dip_percentage < 0:
            return "Above MA"
        elif dip_percentage < 0.02:
            return "Weak Dip"
        elif dip_percentage < 0.05:
            return "Moderate Dip"
        elif dip_percentage < 0.10:
            return "Strong Dip"
        else:
            return "Extreme Dip"
    
    def _get_dip_recommendation(self, ma_signals: Dict) -> str:
        """Get trading recommendation based on MA signals."""
        dip_count = sum(1 for signal in ma_signals.values() if signal.get("is_dip", False))
        
        if dip_count == 0:
            return "No dip detected - regular DCA"
        elif dip_count == 1:
            return "Minor dip - consider small position increase"
        elif dip_count == 2:
            return "Moderate dip - increase position size"
        else:
            return "Major dip - strong buy opportunity"
    
    def calculate_position_multiplier(self, dip_analysis: Dict, 
                                    multiplier_config: Dict = None) -> float:
        """Calculate position size multiplier based on dip analysis.
        
        Args:
            dip_analysis: Result from detect_dip()
            multiplier_config: Configuration for multipliers
            
        Returns:
            Multiplier for position size (1.0 = normal, >1.0 = increased)
        """
        if multiplier_config is None:
            multiplier_config = {
                "weak_dip": 1.2,      # 20% increase
                "moderate_dip": 1.5,   # 50% increase
                "strong_dip": 2.0,     # 100% increase
                "extreme_dip": 2.5     # 150% increase
            }
        
        try:
            if not dip_analysis.get("has_dip", False):
                return 1.0  # No multiplier for no dip
            
            max_dip = dip_analysis.get("max_dip_percentage", 0)
            
            if max_dip < 2:
                return multiplier_config["weak_dip"]
            elif max_dip < 5:
                return multiplier_config["moderate_dip"]
            elif max_dip < 10:
                return multiplier_config["strong_dip"]
            else:
                return multiplier_config["extreme_dip"]
                
        except Exception as e:
            logger.error(f"Error calculating position multiplier: {e}")
            return 1.0  # Default to normal size on error
    
    def get_trend_direction(self, ma_values: Dict[int, float]) -> str:
        """Determine overall trend direction based on MA alignment.
        
        Args:
            ma_values: Dict of MA period -> current value
            
        Returns:
            "bullish", "bearish", or "neutral"
        """
        try:
            # Sort MAs by period (shorter to longer)
            sorted_mas = sorted([(period, value) for period, value in ma_values.items() 
                               if value is not None])
            
            if len(sorted_mas) < 2:
                return "neutral"
            
            # Check if shorter MAs are above longer MAs (bullish alignment)
            bullish_signals = 0
            bearish_signals = 0
            
            for i in range(len(sorted_mas) - 1):
                shorter_period, shorter_ma = sorted_mas[i]
                longer_period, longer_ma = sorted_mas[i + 1]
                
                if shorter_ma > longer_ma:
                    bullish_signals += 1
                elif shorter_ma < longer_ma:
                    bearish_signals += 1
            
            if bullish_signals > bearish_signals:
                return "bullish"
            elif bearish_signals > bullish_signals:
                return "bearish"
            else:
                return "neutral"
                
        except Exception as e:
            logger.error(f"Error determining trend direction: {e}")
            return "neutral"


class MovingAverageStrategy:
    """Moving Average-based DCA strategy for dip buying."""
    
    def __init__(self, 
                 ma_periods: List[int] = None,
                 ma_type: str = "SMA",
                 dip_thresholds: Dict[int, float] = None,
                 position_multipliers: Dict[str, float] = None):
        """Initialize MA strategy.
        
        Args:
            ma_periods: MA periods to use
            ma_type: "SMA" or "EMA"
            dip_thresholds: Dip percentage thresholds per MA
            position_multipliers: Position size multipliers for different dip levels
        """
        self.ma_indicator = MovingAverageIndicator(ma_periods)
        self.ma_type = ma_type
        self.dip_thresholds = dip_thresholds or {20: 0.02, 50: 0.05, 200: 0.10}
        self.position_multipliers = position_multipliers or {
            "weak_dip": 1.2,
            "moderate_dip": 1.5,
            "strong_dip": 2.0,
            "extreme_dip": 2.5
        }
    
    async def analyze_dip_opportunity(self, prices: pd.DataFrame, current_price: float) -> Dict:
        """Analyze current dip opportunity based on moving averages.
        
        Args:
            prices: Historical price data
            current_price: Current asset price
            
        Returns:
            Comprehensive dip analysis with trading recommendations
        """
        try:
            # Calculate all moving averages
            ma_values = self.ma_indicator.calculate_all_mas(prices, self.ma_type)
            
            # Filter out None values
            valid_mas = {k: v for k, v in ma_values.items() if v is not None}
            
            if not valid_mas:
                return {
                    "has_dip": False,
                    "position_multiplier": 1.0,
                    "reason": "Insufficient data for MA calculation",
                    "ma_values": {}
                }
            
            # Detect dips
            dip_analysis = self.ma_indicator.detect_dip(current_price, valid_mas, self.dip_thresholds)
            
            # Calculate position multiplier
            position_multiplier = self.ma_indicator.calculate_position_multiplier(
                dip_analysis, self.position_multipliers
            )
            
            # Get trend direction
            trend_direction = self.ma_indicator.get_trend_direction(valid_mas)
            
            result = {
                **dip_analysis,
                "position_multiplier": position_multiplier,
                "trend_direction": trend_direction,
                "ma_type": self.ma_type,
                "strategy_recommendation": self._get_strategy_recommendation(
                    dip_analysis, trend_direction, position_multiplier
                )
            }
            
            logger.info(f"MA Analysis: Dip={dip_analysis.get('has_dip', False)}, "
                       f"Multiplier={position_multiplier:.1f}x, Trend={trend_direction}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error in MA dip analysis: {e}")
            return {
                "has_dip": False,
                "position_multiplier": 1.0,
                "reason": f"Analysis error: {e}",
                "error": str(e)
            }
    
    def _get_strategy_recommendation(self, dip_analysis: Dict, trend_direction: str, 
                                   position_multiplier: float) -> str:
        """Get comprehensive strategy recommendation."""
        has_dip = dip_analysis.get("has_dip", False)
        max_dip = dip_analysis.get("max_dip_percentage", 0)
        
        if not has_dip:
            if trend_direction == "bullish":
                return "Regular DCA - bullish trend, no significant dip"
            elif trend_direction == "bearish":
                return "Cautious DCA - bearish trend, wait for deeper dip"
            else:
                return "Regular DCA - neutral trend"
        
        # Has dip
        if trend_direction == "bullish" and position_multiplier >= 2.0:
            return f"Strong Buy - {max_dip:.1f}% dip in bullish trend"
        elif trend_direction == "bearish" and position_multiplier >= 1.5:
            return f"Moderate Buy - {max_dip:.1f}% dip, but bearish trend"
        elif position_multiplier >= 2.0:
            return f"Aggressive Buy - {max_dip:.1f}% significant dip"
        else:
            return f"Enhanced DCA - {max_dip:.1f}% minor dip opportunity"