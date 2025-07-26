"""Tests for volatility calculation functionality."""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from src.trading.volatility import VolatilityCalculator
from src.config.models import DCAConfig


class TestVolatilityCalculator:
    """Test cases for VolatilityCalculator class."""
    
    @pytest.fixture
    def config(self):
        """Create a test configuration."""
        return DCAConfig(
            private_key='0x' + 'a' * 64,
            base_amount=100.0,
            min_amount=50.0,
            max_amount=200.0,
            low_vol_threshold=20.0,
            high_vol_threshold=40.0
        )
    
    @pytest.fixture
    def sample_prices_stable(self):
        """Create sample price data with low volatility."""
        dates = pd.date_range('2023-01-01', periods=30, freq='D')
        prices = [50000 + np.random.normal(0, 100) for _ in range(30)]  # Small variations
        return pd.DataFrame({'price': prices}, index=dates)
    
    @pytest.fixture
    def sample_prices_volatile(self):
        """Create sample price data with high volatility."""
        dates = pd.date_range('2023-01-01', periods=30, freq='D')
        prices = [50000 + np.random.normal(0, 5000) for _ in range(30)]  # Large variations
        return pd.DataFrame({'price': prices}, index=dates)
    
    def test_calculator_initialization(self):
        """Test volatility calculator initialization."""
        calculator = VolatilityCalculator(window_days=30)
        
        assert calculator.window_days == 30
    
    def test_calculate_volatility_stable_prices(self, sample_prices_stable):
        """Test volatility calculation with stable prices."""
        calculator = VolatilityCalculator(window_days=30)
        
        volatility = calculator.calculate_volatility(sample_prices_stable)
        
        assert volatility is not None
        assert volatility > 0
        assert volatility < 10  # Should be low volatility
    
    def test_calculate_volatility_volatile_prices(self, sample_prices_volatile):
        """Test volatility calculation with volatile prices."""
        calculator = VolatilityCalculator(window_days=30)
        
        volatility = calculator.calculate_volatility(sample_prices_volatile)
        
        assert volatility is not None
        assert volatility > 10  # Should be higher volatility
    
    def test_calculate_volatility_insufficient_data(self):
        """Test volatility calculation with insufficient data."""
        calculator = VolatilityCalculator(window_days=30)
        
        # Only 5 days of data
        dates = pd.date_range('2023-01-01', periods=5, freq='D')
        prices = pd.DataFrame({'price': [50000, 51000, 49000, 52000, 48000]}, index=dates)
        
        volatility = calculator.calculate_volatility(prices)
        
        assert volatility is None
    
    def test_calculate_volatility_empty_data(self):
        """Test volatility calculation with empty data."""
        calculator = VolatilityCalculator(window_days=30)
        
        empty_df = pd.DataFrame(columns=['price'])
        volatility = calculator.calculate_volatility(empty_df)
        
        assert volatility is None
    
    def test_calculate_volatility_none_input(self):
        """Test volatility calculation with None input."""
        calculator = VolatilityCalculator(window_days=30)
        
        volatility = calculator.calculate_volatility(None)
        
        assert volatility is None
    
    def test_calculate_volatility_constant_prices(self):
        """Test volatility calculation with constant prices."""
        calculator = VolatilityCalculator(window_days=30)
        
        # All prices the same
        dates = pd.date_range('2023-01-01', periods=30, freq='D')
        prices = pd.DataFrame({'price': [50000] * 30}, index=dates)
        
        volatility = calculator.calculate_volatility(prices)
        
        assert volatility == 0.0  # No volatility
    
    def test_calculate_position_size_low_volatility(self, config):
        """Test position size calculation with low volatility."""
        calculator = VolatilityCalculator(window_days=30)
        
        low_volatility = 15.0  # Below low_vol_threshold
        position_size = calculator.calculate_position_size(low_volatility, config)
        
        assert position_size == config.max_amount  # Should use max amount
    
    def test_calculate_position_size_high_volatility(self, config):
        """Test position size calculation with high volatility."""
        calculator = VolatilityCalculator(window_days=30)
        
        high_volatility = 45.0  # Above high_vol_threshold
        position_size = calculator.calculate_position_size(high_volatility, config)
        
        assert position_size == config.min_amount  # Should use min amount
    
    def test_calculate_position_size_medium_volatility(self, config):
        """Test position size calculation with medium volatility."""
        calculator = VolatilityCalculator(window_days=30)
        
        medium_volatility = 30.0  # Between thresholds
        position_size = calculator.calculate_position_size(medium_volatility, config)
        
        # Should be scaled between min and max
        assert config.min_amount < position_size < config.max_amount
    
    def test_calculate_position_size_none_volatility(self, config):
        """Test position size calculation with None volatility."""
        calculator = VolatilityCalculator(window_days=30)
        
        position_size = calculator.calculate_position_size(None, config)
        
        assert position_size == config.base_amount  # Should use base amount
    
    def test_calculate_position_size_edge_cases(self, config):
        """Test position size calculation at threshold boundaries."""
        calculator = VolatilityCalculator(window_days=30)
        
        # Exactly at low threshold
        position_size = calculator.calculate_position_size(config.low_vol_threshold, config)
        assert position_size == config.max_amount
        
        # Exactly at high threshold
        position_size = calculator.calculate_position_size(config.high_vol_threshold, config)
        assert position_size == config.min_amount
    
    def test_calculate_position_size_extreme_volatility(self, config):
        """Test position size calculation with extreme volatility values."""
        calculator = VolatilityCalculator(window_days=30)
        
        # Negative volatility (shouldn't happen but test robustness)
        position_size = calculator.calculate_position_size(-5.0, config)
        assert position_size == config.max_amount
        
        # Very high volatility
        position_size = calculator.calculate_position_size(100.0, config)
        assert position_size == config.min_amount
    
    def test_scaling_calculation(self, config):
        """Test that volatility scaling works correctly."""
        calculator = VolatilityCalculator(window_days=30)
        
        # Test multiple points in the scaling range
        vol_25 = 25.0  # 25% between 20 and 40
        vol_30 = 30.0  # 50% between 20 and 40
        vol_35 = 35.0  # 75% between 20 and 40
        
        pos_25 = calculator.calculate_position_size(vol_25, config)
        pos_30 = calculator.calculate_position_size(vol_30, config)
        pos_35 = calculator.calculate_position_size(vol_35, config)
        
        # Higher volatility should result in smaller position size
        assert pos_25 > pos_30 > pos_35
        
        # All should be between min and max
        assert config.min_amount <= pos_35 <= pos_30 <= pos_25 <= config.max_amount
    
    def test_volatility_percentage_conversion(self):
        """Test that volatility is correctly converted to percentage."""
        calculator = VolatilityCalculator(window_days=30)
        
        # Create price data with known returns
        dates = pd.date_range('2023-01-01', periods=10, freq='D')
        prices = [100, 110, 99, 108, 95, 105, 92, 102, 88, 98]  # 10% daily changes
        price_df = pd.DataFrame({'price': prices}, index=dates)
        
        volatility = calculator.calculate_volatility(price_df)
        
        # Should be a reasonable percentage value
        assert 0 < volatility < 100
        assert isinstance(volatility, float)
    
    def test_calculator_with_different_windows(self):
        """Test calculator with different window sizes."""
        dates = pd.date_range('2023-01-01', periods=60, freq='D')
        prices = pd.DataFrame({'price': [50000 + i * 100 for i in range(60)]}, index=dates)
        
        calc_7 = VolatilityCalculator(window_days=7)
        calc_30 = VolatilityCalculator(window_days=30)
        calc_60 = VolatilityCalculator(window_days=60)
        
        vol_7 = calc_7.calculate_volatility(prices)
        vol_30 = calc_30.calculate_volatility(prices)
        vol_60 = calc_60.calculate_volatility(prices)
        
        # All should return valid volatility
        assert all(v is not None for v in [vol_7, vol_30, vol_60])
        assert all(v >= 0 for v in [vol_7, vol_30, vol_60])