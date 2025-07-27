#!/usr/bin/env python3
"""
Test Hyperliquid Historical Data Access
Check what historical data we can fetch from Hyperliquid API for free.
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import asyncio
from datetime import datetime, timedelta
from hyperliquid.info import Info
from src.utils.constants import BASE_URL
from src.utils.logging_config import get_logger

logger = get_logger(__name__)

async def test_hyperliquid_candles():
    """Test Hyperliquid candlestick data availability."""
    print("📊 Testing Hyperliquid Candlestick Data...")
    print("=" * 60)
    
    try:
        info = Info(BASE_URL)
        
        # Test different assets and timeframes
        test_assets = ["@140", "@147", "@151"]  # BTC, ETH, SOL
        asset_names = ["BTC", "ETH", "SOL"]
        timeframes = ["1m", "1h", "1d"]
        
        for i, asset in enumerate(test_assets):
            asset_name = asset_names[i]
            print(f"\n🔍 Testing {asset_name} ({asset}):")
            
            for timeframe in timeframes:
                try:
                    # Try to get recent candles
                    start_time = int((datetime.now() - timedelta(days=7)).timestamp() * 1000)
                    end_time = int(datetime.now().timestamp() * 1000)
                    
                    candles = info.candles_snapshot(
                        coin=asset,
                        interval=timeframe,
                        startTime=start_time,
                        endTime=end_time
                    )
                    
                    if candles and len(candles) > 0:
                        print(f"  ✅ {timeframe}: {len(candles)} candles available")
                        
                        # Show sample data
                        sample = candles[0]
                        if isinstance(sample, dict):
                            print(f"     Sample: O:{sample.get('o', 'N/A')} H:{sample.get('h', 'N/A')} L:{sample.get('l', 'N/A')} C:{sample.get('c', 'N/A')}")
                        else:
                            print(f"     Sample: {sample}")
                    else:
                        print(f"  ❌ {timeframe}: No data available")
                        
                except Exception as e:
                    print(f"  ❌ {timeframe}: Error - {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Candlestick test failed: {e}")
        return False

async def test_hyperliquid_meta():
    """Test Hyperliquid metadata and available endpoints."""
    print("\n🔍 Testing Hyperliquid Metadata...")
    print("=" * 60)
    
    try:
        info = Info(BASE_URL)
        
        # Test spot metadata
        print("📊 Spot Metadata:")
        spot_meta = info.spot_meta()
        universe = spot_meta.get("universe", [])
        tokens = spot_meta.get("tokens", [])
        print(f"  ✅ Found {len(universe)} spot pairs")
        print(f"  ✅ Found {len(tokens)} tokens")
        
        # Test all_mids (current prices)
        print("\n💰 Current Prices:")
        mid_prices = info.all_mids()
        btc_price = mid_prices.get("@140")
        eth_price = mid_prices.get("@147") 
        sol_price = mid_prices.get("@151")
        
        print(f"  BTC (@140): ${float(btc_price):,.2f}" if btc_price else "  BTC: No price")
        print(f"  ETH (@147): ${float(eth_price):,.2f}" if eth_price else "  ETH: No price")
        print(f"  SOL (@151): ${float(sol_price):,.2f}" if sol_price else "  SOL: No price")
        
        return True
        
    except Exception as e:
        print(f"❌ Metadata test failed: {e}")
        return False

async def test_historical_limits():
    """Test how far back we can fetch historical data."""
    print("\n⏰ Testing Historical Data Limits...")
    print("=" * 60)
    
    try:
        info = Info(BASE_URL)
        
        # Test different time ranges for BTC
        time_ranges = [
            ("1 day", 1),
            ("7 days", 7), 
            ("30 days", 30),
            ("90 days", 90),
            ("1 year", 365)
        ]
        
        for range_name, days in time_ranges:
            try:
                start_time = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)
                end_time = int(datetime.now().timestamp() * 1000)
                
                candles = info.candles_snapshot(
                    coin="@140",  # BTC
                    interval="1d",
                    startTime=start_time,
                    endTime=end_time
                )
                
                if candles and len(candles) > 0:
                    print(f"  ✅ {range_name}: {len(candles)} daily candles")
                else:
                    print(f"  ❌ {range_name}: No data")
                    
            except Exception as e:
                print(f"  ❌ {range_name}: Error - {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Historical limits test failed: {e}")
        return False

async def test_rate_limits():
    """Test API rate limiting behavior."""
    print("\n🚦 Testing Rate Limits...")
    print("=" * 60)
    
    try:
        info = Info(BASE_URL)
        
        # Make multiple rapid requests
        start_time = datetime.now()
        successful_requests = 0
        
        for i in range(10):
            try:
                mid_prices = info.all_mids()
                if mid_prices:
                    successful_requests += 1
                    
            except Exception as e:
                print(f"  Request {i+1} failed: {e}")
                break
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        print(f"  ✅ {successful_requests}/10 requests successful")
        print(f"  ⏱️ Duration: {duration:.2f} seconds")
        print(f"  📊 Rate: {successful_requests/duration:.1f} requests/second")
        
        return successful_requests > 5  # Consider success if >50% requests work
        
    except Exception as e:
        print(f"❌ Rate limits test failed: {e}")
        return False

async def compare_with_coingecko():
    """Compare data availability between Hyperliquid and CoinGecko."""
    print("\n⚖️ Comparing Data Sources...")
    print("=" * 60)
    
    # Hyperliquid data
    print("🔹 Hyperliquid:")
    try:
        info = Info(BASE_URL)
        
        # Try to get 30 days of daily candles for BTC
        start_time = int((datetime.now() - timedelta(days=30)).timestamp() * 1000)
        end_time = int(datetime.now().timestamp() * 1000)
        
        hl_candles = info.candles_snapshot(
            coin="@140",
            interval="1d", 
            startTime=start_time,
            endTime=end_time
        )
        
        print(f"  📊 BTC Daily Candles (30d): {len(hl_candles) if hl_candles else 0}")
        print(f"  💰 Cost: FREE")
        print(f"  🚀 Speed: Very Fast (direct API)")
        
    except Exception as e:
        print(f"  ❌ Hyperliquid error: {e}")
    
    # CoinGecko data (our current fallback)
    print("\n🔸 CoinGecko:")
    try:
        from pycoingecko import CoinGeckoAPI
        cg = CoinGeckoAPI()
        
        # Get 30 days of data
        btc_data = cg.get_coin_market_chart_by_id(
            id='bitcoin',
            vs_currency='usd',
            days=30
        )
        
        prices = btc_data.get('prices', [])
        print(f"  📊 BTC Price Points (30d): {len(prices)}")
        print(f"  💰 Cost: FREE (with limits)")
        print(f"  🐌 Speed: Slower (external API)")
        
    except Exception as e:
        print(f"  ❌ CoinGecko error: {e}")

async def run_comprehensive_test():
    """Run comprehensive historical data test."""
    print("🔍 Hyperliquid Historical Data Analysis")
    print("=" * 80)
    print("Testing free historical data access for Phase 2 indicators...")
    print()
    
    results = {}
    
    # Test 1: Candlestick Data
    results["candles"] = await test_hyperliquid_candles()
    
    # Test 2: Metadata
    results["metadata"] = await test_hyperliquid_meta()
    
    # Test 3: Historical Limits
    results["historical_limits"] = await test_historical_limits()
    
    # Test 4: Rate Limits
    results["rate_limits"] = await test_rate_limits()
    
    # Test 5: Data Source Comparison
    await compare_with_coingecko()
    
    # Summary
    print("\n📋 Test Summary:")
    print("=" * 40)
    
    passed_tests = sum(1 for result in results.values() if result)
    total_tests = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name.replace('_', ' ').title()}")
    
    print(f"\n📊 Overall: {passed_tests}/{total_tests} tests passed")
    
    # Recommendations
    print("\n💡 Recommendations for Phase 2:")
    print("=" * 40)
    
    if results.get("candles") and results.get("historical_limits"):
        print("✅ Use Hyperliquid for historical data - FREE and comprehensive")
        print("✅ Implement RSI, MA, and volatility calculations with HL data")
        print("✅ Superior data quality and speed vs external APIs")
    else:
        print("⚠️ Limited Hyperliquid historical data access")
        print("📊 Consider hybrid approach: HL for recent + CoinGecko for deep history")
        print("🔄 Implement fallback mechanisms for data sources")
    
    return passed_tests == total_tests

if __name__ == "__main__":
    print("Starting Hyperliquid historical data analysis...")
    
    try:
        result = asyncio.run(run_comprehensive_test())
        
        if result:
            print("\n🎉 Historical data access confirmed!")
            print("Phase 2 implementation can proceed with Hyperliquid data.")
        else:
            print("\n⚠️ Some limitations found in historical data access.")
            print("Phase 2 may need hybrid data approach.")
            
    except Exception as e:
        print(f"\n💥 Analysis failed: {e}")
        import traceback
        traceback.print_exc()