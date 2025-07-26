"""Volatility calculation utilities."""

import numpy as np
import pandas as pd
from typing import Optional
from ..utils.logging_config import get_logger

logger = get_logger(__name__)


class VolatilityCalculator:
    """Calculate Bitcoin volatility metrics"""
    
    def __init__(self, window_days: int = 30):
        """Initialize with calculation window."""
        self.window_days = window_days

    def calculate_volatility(self, prices: pd.DataFrame) -> Optional[float]:
        """Calculate annualized volatility from price data."""
        if prices is None or len(prices) < self.window_days:
            logger.warning(
                f"Not enough historical data to calculate volatility "
                f"(have {len(prices) if prices is not None else 0}, need {self.window_days})."
            )
            return None
            
        try:
            prices['price'] = pd.to_numeric(prices['price'])
            returns = prices['price'].pct_change().dropna()
            
            if len(returns) < 2:
                logger.warning("Insufficient return data for volatility calculation")
                return None
                
            daily_vol = returns.std()
            annualized_vol = daily_vol * np.sqrt(365) * 100
            
            logger.info(f"Calculated volatility: {annualized_vol:.2f}%")
            return annualized_vol
            
        except Exception as e:
            logger.error(f"Error calculating volatility: {e}")
            return None

    def calculate_position_size(self, volatility: float, config) -> float:
        """Calculate position size based on volatility and configuration."""
        if volatility is None:
            logger.warning("No volatility data, using base amount")
            return config.base_amount
            
        try:
            if volatility <= config.low_vol_threshold:
                size = config.max_amount
                logger.info(f"Low volatility ({volatility:.2f}% ≤ {config.low_vol_threshold}%), using max amount: ${size}")
            elif volatility >= config.high_vol_threshold:
                size = config.min_amount
                logger.info(f"High volatility ({volatility:.2f}% ≥ {config.high_vol_threshold}%), using min amount: ${size}")
            else:
                # Linear interpolation
                ratio = (volatility - config.low_vol_threshold) / (config.high_vol_threshold - config.low_vol_threshold)
                size = config.max_amount - (ratio * (config.max_amount - config.min_amount))
                logger.info(f"Medium volatility ({volatility:.2f}%), using interpolated amount: ${size:.2f}")
                
            return round(size, 2)
            
        except Exception as e:
            logger.error(f"Error calculating position size: {e}")
            return config.base_amount