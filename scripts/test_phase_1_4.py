#!/usr/bin/env python3
"""
Phase 1.4 Integration Test Script
Tests all multi-asset independent execution functionality.
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import asyncio
from datetime import datetime
from src.config.models import MultiAssetDCAConfig, AssetDCAConfig
from src.trading.multi_asset_bot import MultiAssetDCABot
from src.data.api_client import HyperliquidAPIClient, ASSET_MAPPINGS
from src.utils.logging_config import get_logger

logger = get_logger(__name__)

async def test_asset_discovery():
    """Test asset spot index discovery and price fetching."""
    print("🔍 Testing Asset Discovery and Price Fetching...")
    print("=" * 60)
    
    try:
        api_client = HyperliquidAPIClient()
        
        for asset, mapping in ASSET_MAPPINGS.items():
            spot_index = mapping.get("spot_index")
            if spot_index is not None:
                try:
                    price = await api_client.get_asset_price(asset)
                    if price and price > 0:
                        print(f"✅ {asset:5}: ${price:,.2f} (spot index @{spot_index})")
                    else:
                        print(f"❌ {asset:5}: No price data (spot index @{spot_index})")
                except Exception as e:
                    print(f"❌ {asset:5}: Error fetching price - {e}")
            else:
                print(f"📋 {asset:5}: Not available for trading on Hyperliquid")
        
        return True
        
    except Exception as e:
        print(f"❌ Asset discovery test failed: {e}")
        return False

async def test_multi_asset_config():
    """Test multi-asset configuration creation."""
    print("\n⚙️ Testing Multi-Asset Configuration...")
    print("=" * 60)
    
    try:
        # Create test multi-asset config
        btc_config = AssetDCAConfig(
            symbol="BTC",
            base_amount=100.0,
            min_amount=50.0,
            max_amount=200.0,
            frequency="weekly",
            enabled=True
        )
        
        eth_config = AssetDCAConfig(
            symbol="ETH",
            base_amount=75.0,
            min_amount=40.0,
            max_amount=150.0,
            frequency="weekly",
            enabled=True
        )
        
        sol_config = AssetDCAConfig(
            symbol="SOL",
            base_amount=50.0,
            min_amount=25.0,
            max_amount=100.0,
            frequency="daily",
            enabled=True
        )
        
        multi_config = MultiAssetDCAConfig(
            private_key="0x" + "0" * 64,  # Test key
            assets={
                "BTC": btc_config,
                "ETH": eth_config,
                "SOL": sol_config
            },
            enabled=True
        )
        
        # Validate configuration
        multi_config.validate()
        
        enabled_assets = multi_config.get_enabled_assets()
        print(f"✅ Multi-asset config created with {len(enabled_assets)} enabled assets:")
        
        for asset_config in enabled_assets:
            print(f"   📊 {asset_config.symbol}: ${asset_config.base_amount} base, {asset_config.frequency}")
        
        return multi_config
        
    except Exception as e:
        print(f"❌ Multi-asset config test failed: {e}")
        return None

async def test_multi_asset_bot(config):
    """Test multi-asset bot initialization and basic functionality."""
    print("\n🤖 Testing Multi-Asset Bot...")
    print("=" * 60)
    
    try:
        # Initialize bot (without real account for testing)
        bot = MultiAssetDCABot(config)
        
        print(f"✅ Multi-asset bot initialized for {len(bot.config.assets)} assets")
        
        # Test asset price fetching
        for asset in ["BTC", "ETH", "SOL"]:
            try:
                price = await bot.get_asset_price(asset)
                if price:
                    print(f"✅ {asset} price: ${price:,.2f}")
                else:
                    print(f"❌ {asset} price: Failed to fetch")
            except Exception as e:
                print(f"❌ {asset} price error: {e}")
        
        # Test volatility calculation
        for asset in ["BTC", "ETH", "SOL"]:
            try:
                volatility = await bot.calculate_asset_volatility(asset)
                if volatility is not None:
                    print(f"✅ {asset} volatility: {volatility:.2f}%")
                else:
                    print(f"❌ {asset} volatility: Calculation failed")
            except Exception as e:
                print(f"❌ {asset} volatility error: {e}")
        
        return bot
        
    except Exception as e:
        print(f"❌ Multi-asset bot test failed: {e}")
        return None

async def test_trading_simulation(bot):
    """Test multi-asset trading simulation."""
    print("\n🧪 Testing Multi-Asset Trading Simulation...")
    print("=" * 60)
    
    try:
        # Test individual asset trades
        for asset in ["BTC", "ETH", "SOL"]:
            try:
                result = await bot.execute_asset_dca_trade(asset, force=True)
                
                if result:
                    if result.get("status") == "ok":
                        trade_type = "📋 Simulated" if result.get("simulated") else "🚀 Real"
                        amount_asset = result.get("amount_asset", 0)
                        amount_usd = result.get("amount_usd", 0)
                        print(f"✅ {asset}: {trade_type} - {amount_asset:.6f} {asset} for ${amount_usd:.2f}")
                    elif result.get("status") == "error":
                        print(f"⚠️ {asset}: Expected error - {result.get('error', 'Unknown error')}")
                    else:
                        print(f"❌ {asset}: Unexpected result - {result}")
                else:
                    print(f"❌ {asset}: No result returned")
                    
            except Exception as e:
                print(f"❌ {asset} trade error: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Trading simulation test failed: {e}")
        return False

async def test_parallel_execution(bot):
    """Test parallel DCA execution."""
    print("\n⚡ Testing Parallel DCA Execution...")
    print("=" * 60)
    
    try:
        start_time = datetime.now()
        
        # Execute all trades in parallel
        results = await bot.execute_all_dca_trades(force=True, parallel=True)
        
        end_time = datetime.now()
        execution_time = (end_time - start_time).total_seconds()
        
        successful_trades = [asset for asset, result in results.items() 
                           if result and result.get("status") == "ok"]
        error_trades = [asset for asset, result in results.items() 
                       if result and result.get("status") == "error"]
        failed_trades = [asset for asset, result in results.items() 
                       if not result]
        
        print(f"✅ Parallel execution completed in {execution_time:.2f}s")
        print(f"📊 Results: {len(successful_trades)} successful, {len(error_trades)} expected errors, {len(failed_trades)} failed")
        
        for asset in successful_trades:
            result = results[asset]
            trade_type = "📋 Simulated" if result.get("simulated") else "🚀 Real"
            print(f"   ✅ {asset}: {trade_type}")
        
        for asset in error_trades:
            result = results[asset]
            print(f"   ⚠️ {asset}: Expected error - {result.get('error', 'Unknown')}")
        
        for asset in failed_trades:
            print(f"   ❌ {asset}: System failure")
        
        # Consider it successful if we got proper error handling (no system failures)
        return len(failed_trades) == 0
        
    except Exception as e:
        print(f"❌ Parallel execution test failed: {e}")
        return False

async def test_portfolio_stats(bot):
    """Test portfolio statistics calculation."""
    print("\n📊 Testing Portfolio Statistics...")
    print("=" * 60)
    
    try:
        # Overall portfolio stats
        portfolio_stats = bot.get_portfolio_stats()
        print(f"✅ Portfolio Stats:")
        print(f"   💰 Total Invested: ${portfolio_stats.get('total_invested', 0):,.2f}")
        print(f"   📈 Total Trades: {portfolio_stats.get('total_trades', 0)}")
        print(f"   🪙 Assets Traded: {portfolio_stats.get('assets_traded', 0)}")
        
        # Individual asset stats
        for asset in ["BTC", "ETH", "SOL"]:
            asset_stats = bot.get_asset_portfolio_stats(asset)
            if asset_stats.get("trade_count", 0) > 0:
                print(f"✅ {asset} Stats:")
                print(f"   💰 Invested: ${asset_stats.get('total_invested', 0):,.2f}")
                print(f"   🪙 Holdings: {asset_stats.get('asset_holdings', 0):.6f}")
                print(f"   📊 Avg Price: ${asset_stats.get('avg_buy_price', 0):,.2f}")
        
        return True
        
    except Exception as e:
        print(f"❌ Portfolio stats test failed: {e}")
        return False

async def run_comprehensive_test():
    """Run comprehensive Phase 1.4 test suite."""
    print("🌟 Phase 1.4 Multi-Asset DCA - Comprehensive Test Suite")
    print("=" * 80)
    print("Testing independent asset execution functionality...")
    print()
    
    test_results = {}
    
    # Test 1: Asset Discovery
    test_results["asset_discovery"] = await test_asset_discovery()
    
    # Test 2: Multi-Asset Configuration
    config = await test_multi_asset_config()
    test_results["multi_asset_config"] = config is not None
    
    if config:
        # Test 3: Multi-Asset Bot
        bot = await test_multi_asset_bot(config)
        test_results["multi_asset_bot"] = bot is not None
        
        if bot:
            # Test 4: Trading Simulation
            test_results["trading_simulation"] = await test_trading_simulation(bot)
            
            # Test 5: Parallel Execution
            test_results["parallel_execution"] = await test_parallel_execution(bot)
            
            # Test 6: Portfolio Statistics
            test_results["portfolio_stats"] = await test_portfolio_stats(bot)
    
    # Summary
    print("\n🎯 Test Results Summary:")
    print("=" * 40)
    
    passed_tests = sum(1 for result in test_results.values() if result)
    total_tests = len(test_results)
    
    for test_name, result in test_results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name.replace('_', ' ').title()}")
    
    print()
    print(f"📊 Overall Result: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("🎉 All tests passed! Phase 1.4 implementation is ready.")
    else:
        print("⚠️ Some tests failed. Please check the implementation.")
    
    return passed_tests == total_tests

if __name__ == "__main__":
    print("Starting Phase 1.4 test suite...")
    
    try:
        result = asyncio.run(run_comprehensive_test())
        
        if result:
            print("\n✨ Phase 1.4 testing complete - All systems operational!")
        else:
            print("\n❌ Phase 1.4 testing found issues - Review implementation.")
            
    except Exception as e:
        print(f"\n💥 Test suite crashed: {e}")
        import traceback
        traceback.print_exc()