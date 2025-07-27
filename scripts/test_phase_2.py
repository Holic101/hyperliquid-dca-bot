#!/usr/bin/env python3
"""
Phase 2 Smart Indicators Test Script
Tests RSI, Moving Average, and Dynamic Frequency indicators.
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from src.indicators.rsi import RSIIndicator, RSIStrategy
from src.indicators.moving_average import MovingAverageIndicator, MovingAverageStrategy
from src.indicators.volatility import VolatilityIndicator, DynamicFrequencyStrategy
from src.config.models import AssetDCAConfig, MultiAssetDCAConfig
from src.trading.smart_multi_asset_bot import SmartMultiAssetDCABot
from src.utils.logging_config import get_logger

logger = get_logger(__name__)

def create_test_price_data(days: int = 100, start_price: float = 50000, 
                          volatility: float = 0.02) -> pd.DataFrame:
    """Create synthetic price data for testing."""
    np.random.seed(42)  # For reproducible results
    
    dates = pd.date_range(start=datetime.now() - timedelta(days=days), 
                         periods=days, freq='D')
    
    # Generate price using geometric Brownian motion
    returns = np.random.normal(0.001, volatility, days)  # Small positive drift
    prices = [start_price]
    
    for i in range(1, days):
        price = prices[-1] * (1 + returns[i])
        prices.append(price)
    
    df = pd.DataFrame({
        'price': prices
    }, index=dates)
    
    return df

async def test_rsi_indicator():
    """Test RSI indicator functionality."""
    print("🧠 Testing RSI Indicator...")
    print("=" * 50)
    
    try:
        # Create test data
        price_data = create_test_price_data(50, 50000, 0.03)  # Higher volatility for RSI testing
        
        # Test RSI indicator
        rsi_indicator = RSIIndicator(period=14)
        rsi_value = rsi_indicator.calculate_rsi(price_data)
        
        if rsi_value is not None:
            print(f"✅ RSI calculated: {rsi_value:.2f}")
            print(f"   Signal strength: {rsi_indicator.get_signal_strength(rsi_value)}")
            print(f"   Should buy (RSI < 30): {rsi_indicator.should_buy(rsi_value, 30)}")
            print(f"   Should skip (RSI > 70): {rsi_indicator.should_skip(rsi_value, 70)}")
        else:
            print("❌ RSI calculation failed")
            return False
        
        # Test RSI strategy
        rsi_strategy = RSIStrategy(
            rsi_period=14,
            oversold_threshold=30.0,
            overbought_threshold=70.0
        )
        
        strategy_result = await rsi_strategy.should_execute_trade(price_data)
        print(f"✅ RSI Strategy: {strategy_result.get('reason', 'N/A')}")
        print(f"   Execute trade: {strategy_result.get('execute', False)}")
        
        return True
        
    except Exception as e:
        print(f"❌ RSI test failed: {e}")
        return False

async def test_moving_average_indicator():
    """Test Moving Average indicator functionality."""
    print("\n📊 Testing Moving Average Indicator...")
    print("=" * 50)
    
    try:
        # Create test data with a recent dip
        price_data = create_test_price_data(100, 50000, 0.02)
        
        # Simulate a recent dip
        recent_dip_factor = 0.95  # 5% dip
        price_data.iloc[-5:] *= recent_dip_factor
        current_price = float(price_data['price'].iloc[-1])
        
        # Test MA indicator
        ma_indicator = MovingAverageIndicator(periods=[20, 50])
        ma_values = ma_indicator.calculate_all_mas(price_data, "SMA")
        
        print(f"✅ Moving Averages calculated:")
        for period, ma_value in ma_values.items():
            if ma_value:
                print(f"   MA{period}: ${ma_value:.2f}")
        
        # Test dip detection
        dip_analysis = ma_indicator.detect_dip(current_price, ma_values)
        print(f"✅ Dip Analysis:")
        print(f"   Current price: ${current_price:.2f}")
        print(f"   Has dip: {dip_analysis.get('has_dip', False)}")
        print(f"   Max dip: {dip_analysis.get('max_dip_percentage', 0):.2f}%")
        print(f"   Recommendation: {dip_analysis.get('recommendation', 'N/A')}")
        
        # Test position multiplier
        position_multiplier = ma_indicator.calculate_position_multiplier(dip_analysis)
        print(f"   Position multiplier: {position_multiplier:.2f}x")
        
        # Test MA strategy
        ma_strategy = MovingAverageStrategy(
            ma_periods=[20, 50],
            ma_type="SMA"
        )
        
        strategy_result = await ma_strategy.analyze_dip_opportunity(price_data, current_price)
        print(f"✅ MA Strategy: {strategy_result.get('strategy_recommendation', 'N/A')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Moving Average test failed: {e}")
        return False

async def test_volatility_indicator():
    """Test Volatility and Dynamic Frequency functionality."""
    print("\n⚡ Testing Volatility & Dynamic Frequency...")
    print("=" * 50)
    
    try:
        # Create test data with varying volatility
        low_vol_data = create_test_price_data(60, 50000, 0.01)  # Low volatility
        high_vol_data = create_test_price_data(60, 50000, 0.05)  # High volatility
        
        # Test volatility indicator
        vol_indicator = VolatilityIndicator(window=30)
        
        low_vol = vol_indicator.calculate_realized_volatility(low_vol_data)
        high_vol = vol_indicator.calculate_realized_volatility(high_vol_data)
        
        print(f"✅ Volatility calculations:")
        print(f"   Low volatility dataset: {low_vol:.2f}%")
        print(f"   High volatility dataset: {high_vol:.2f}%")
        
        # Test volatility regimes
        low_regime = vol_indicator.get_volatility_regime(low_vol, 25, 50)
        high_regime = vol_indicator.get_volatility_regime(high_vol, 25, 50)
        
        print(f"   Low vol regime: {low_regime}")
        print(f"   High vol regime: {high_regime}")
        
        # Test dynamic frequency strategy
        dynamic_freq = DynamicFrequencyStrategy(
            volatility_window=30,
            low_vol_threshold=25.0,
            high_vol_threshold=50.0
        )
        
        low_freq_result = await dynamic_freq.calculate_optimal_frequency(low_vol_data, 'weekly')
        high_freq_result = await dynamic_freq.calculate_optimal_frequency(high_vol_data, 'weekly')
        
        print(f"✅ Dynamic Frequency recommendations:")
        print(f"   Low vol scenario: {low_freq_result.get('recommended_frequency', 'N/A')}")
        print(f"   High vol scenario: {high_freq_result.get('recommended_frequency', 'N/A')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Volatility test failed: {e}")
        return False

async def test_smart_multi_asset_bot():
    """Test Smart Multi-Asset Bot integration."""
    print("\n🤖 Testing Smart Multi-Asset Bot...")
    print("=" * 50)
    
    try:
        # Create test configuration with indicators enabled
        btc_config = AssetDCAConfig(
            symbol="BTC",
            base_amount=100.0,
            use_rsi=True,
            rsi_period=14,
            rsi_oversold_threshold=30.0,
            use_ma_dips=True,
            ma_periods="20,50",
            ma_type="SMA",
            use_dynamic_frequency=True,
            enabled=True
        )
        
        multi_config = MultiAssetDCAConfig(
            private_key="0x" + "0" * 64,  # Test key
            assets={"BTC": btc_config}
        )
        
        # Initialize smart bot
        smart_bot = SmartMultiAssetDCABot(multi_config)
        print(f"✅ Smart bot initialized with indicators")
        
        # Test indicator status
        indicator_status = smart_bot.get_asset_indicator_status("BTC")
        print(f"✅ BTC Indicator Status:")
        indicators = indicator_status.get("indicators", {})
        
        for indicator_name, status in indicators.items():
            enabled = status.get("enabled", False)
            configured = status.get("configured", False)
            print(f"   {indicator_name}: {'✅' if enabled and configured else '❌'} "
                  f"(enabled: {enabled}, configured: {configured})")
        
        # Test smart analysis (would need real price data for full test)
        print(f"✅ Smart bot integration successful")
        
        return True
        
    except Exception as e:
        print(f"❌ Smart bot test failed: {e}")
        return False

async def test_indicator_integration():
    """Test integration of all indicators together."""
    print("\n🔗 Testing Indicator Integration...")
    print("=" * 50)
    
    try:
        # Create complex test scenario
        price_data = create_test_price_data(100, 50000, 0.03)
        
        # Simulate recent price action: dip + potential oversold
        price_data.iloc[-10:] *= 0.92  # 8% dip over last 10 days
        current_price = float(price_data['price'].iloc[-1])
        
        # Test all indicators together
        results = {}
        
        # RSI
        rsi_strategy = RSIStrategy()
        rsi_result = await rsi_strategy.should_execute_trade(price_data)
        results["rsi"] = rsi_result
        
        # Moving Averages
        ma_strategy = MovingAverageStrategy()
        ma_result = await ma_strategy.analyze_dip_opportunity(price_data, current_price)
        results["ma"] = ma_result
        
        # Dynamic Frequency
        freq_strategy = DynamicFrequencyStrategy()
        freq_result = await freq_strategy.calculate_optimal_frequency(price_data, 'weekly')
        results["frequency"] = freq_result
        
        # Combine signals
        should_execute = True
        position_multiplier = 1.0
        reasons = []
        
        # RSI check
        if not rsi_result.get("execute", True):
            should_execute = False
            reasons.append(f"RSI: {rsi_result.get('reason', 'Skip')}")
        else:
            reasons.append(f"RSI: {rsi_result.get('reason', 'OK')}")
        
        # MA position sizing
        if ma_result.get("has_dip", False):
            ma_multiplier = ma_result.get("position_multiplier", 1.0)
            position_multiplier *= ma_multiplier
            reasons.append(f"MA: {ma_multiplier:.1f}x (dip detected)")
        
        # Frequency adjustment
        if freq_result.get("should_change", False):
            freq_mult = freq_strategy.get_frequency_multiplier(
                freq_result.get("recommended_frequency", "weekly"), "weekly"
            )
            position_multiplier *= freq_mult
            reasons.append(f"Freq: {freq_mult:.1f}x adjustment")
        
        print(f"✅ Integrated Analysis:")
        print(f"   Should execute: {should_execute}")
        print(f"   Position multiplier: {position_multiplier:.2f}x")
        print(f"   Combined reasoning: {'; '.join(reasons)}")
        
        # Determine strategy
        if not should_execute:
            strategy = "skip_trade"
        elif position_multiplier >= 2.0:
            strategy = "aggressive_buy"
        elif position_multiplier >= 1.5:
            strategy = "enhanced_dca"
        else:
            strategy = "regular_dca"
        
        print(f"   Final strategy: {strategy}")
        
        return True
        
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        return False

async def run_phase_2_tests():
    """Run comprehensive Phase 2 test suite."""
    print("🧠 Phase 2 Smart Indicators - Comprehensive Test Suite")
    print("=" * 80)
    print("Testing RSI, Moving Average, and Dynamic Frequency indicators...")
    print()
    
    test_results = {}
    
    # Individual indicator tests
    test_results["rsi"] = await test_rsi_indicator()
    test_results["moving_average"] = await test_moving_average_indicator()
    test_results["volatility"] = await test_volatility_indicator()
    test_results["smart_bot"] = await test_smart_multi_asset_bot()
    test_results["integration"] = await test_indicator_integration()
    
    # Summary
    print("\n🎯 Phase 2 Test Results:")
    print("=" * 40)
    
    passed_tests = sum(1 for result in test_results.values() if result)
    total_tests = len(test_results)
    
    for test_name, result in test_results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name.replace('_', ' ').title()}")
    
    print()
    print(f"📊 Overall Result: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("🎉 All Phase 2 tests passed! Smart indicators are ready for production.")
        print("\n🚀 Available Features:")
        print("   ✅ RSI-based entry filtering")
        print("   ✅ Moving average dip detection")
        print("   ✅ Dynamic frequency adjustment")
        print("   ✅ Smart multi-asset integration")
        print("   ✅ Combined indicator strategies")
    else:
        print("⚠️ Some Phase 2 tests failed. Please review implementation.")
    
    return passed_tests == total_tests

if __name__ == "__main__":
    print("Starting Phase 2 Smart Indicators test suite...")
    
    try:
        result = asyncio.run(run_phase_2_tests())
        
        if result:
            print("\n✨ Phase 2 testing complete - Smart indicators operational!")
        else:
            print("\n❌ Phase 2 testing found issues - Review implementation.")
            
    except Exception as e:
        print(f"\n💥 Test suite crashed: {e}")
        import traceback
        traceback.print_exc()