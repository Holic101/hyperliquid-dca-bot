#!/usr/bin/env python3
"""
Asset Spot Index Discovery Script
Discovers the correct Hyperliquid spot indices for all supported assets.
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import asyncio
from hyperliquid.info import Info
from src.utils.constants import BASE_URL
from src.utils.logging_config import get_logger

logger = get_logger(__name__)

# Assets we want to find indices for
TARGET_ASSETS = {
    'UBTC': 'BTC',
    'UETH': 'ETH', 
    'USOL': 'SOL',
    'UAVAX': 'AVAX',
    'ULINK': 'LINK',
    'AVAX': 'AVAX',  # Try alternative names
    'LINK': 'LINK',
    'CHAINLINK': 'LINK'
}

async def discover_all_asset_indices():
    """Discover spot indices for all supported assets."""
    try:
        print("🔍 Discovering Hyperliquid Spot Asset Indices...")
        print("=" * 60)
        
        info = Info(BASE_URL)
        
        # Get spot metadata
        spot_meta = info.spot_meta()
        universe = spot_meta.get("universe", [])
        tokens = spot_meta.get("tokens", [])
        
        print(f"📊 Found {len(universe)} spot pairs and {len(tokens)} tokens")
        print()
        
        discovered_indices = {}
        
        # Look through all spot pairs
        for i, pair in enumerate(universe):
            try:
                token_indices = pair.get('tokens', [])
                if len(token_indices) == 2:
                    token1_idx, token2_idx = token_indices
                    
                    # Check if USDC is one of the tokens (USDC should be index 0)
                    if token2_idx == 0 and token1_idx < len(tokens):
                        token_name = tokens[token1_idx].get('name', '')
                        
                        if token_name in TARGET_ASSETS:
                            asset_symbol = TARGET_ASSETS[token_name]
                            discovered_indices[asset_symbol] = i
                            
                            print(f"✅ {asset_symbol:5} ({token_name}): @{i}")
                        elif token_name and not token_name.startswith('sz'):
                            # Show other interesting tokens for reference
                            print(f"📝 {token_name}: @{i}")
                            
            except Exception as e:
                logger.warning(f"Error processing pair {i}: {e}")
                continue
        
        print()
        print("🎯 Discovery Results:")
        print("=" * 40)
        
        for asset in ['BTC', 'ETH', 'SOL', 'AVAX', 'LINK']:
            if asset in discovered_indices:
                index = discovered_indices[asset]
                print(f"✅ {asset}: @{index}")
            else:
                print(f"❌ {asset}: Not found")
        
        print()
        print("🔧 Code Update Required:")
        print("Update ASSET_MAPPINGS in src/data/api_client.py:")
        print()
        
        # Generate the updated mapping
        print("ASSET_MAPPINGS = {")
        for asset in ['BTC', 'ETH', 'SOL', 'AVAX', 'LINK']:
            if asset in discovered_indices:
                index = discovered_indices[asset]
                coingecko_mapping = {
                    'BTC': 'bitcoin',
                    'ETH': 'ethereum', 
                    'SOL': 'solana',
                    'AVAX': 'avalanche-2',
                    'LINK': 'chainlink'
                }
                coingecko_id = coingecko_mapping.get(asset, asset.lower())
                print(f'    "{asset}": {{"spot_index": {index}, "coingecko_id": "{coingecko_id}"}},')
            else:
                print(f'    "{asset}": {{"spot_index": None, "coingecko_id": "unknown"}},  # Not found')
        print("}")
        
        print()
        print("🚀 Next Steps:")
        print("1. Update ASSET_MAPPINGS in api_client.py with discovered indices")
        print("2. Test asset price fetching with new indices")
        print("3. Implement multi-asset trading execution")
        
        return discovered_indices
        
    except Exception as e:
        print(f"❌ Discovery failed: {e}")
        logger.error(f"Asset discovery error: {e}")
        return {}

async def test_asset_prices(discovered_indices):
    """Test price fetching for discovered assets."""
    print("\n🧪 Testing Asset Price Fetching...")
    print("=" * 40)
    
    try:
        info = Info(BASE_URL)
        mid_prices = info.all_mids()
        
        for asset, index in discovered_indices.items():
            spot_format = f"@{index}"
            price = mid_prices.get(spot_format)
            
            if price:
                print(f"✅ {asset:5}: ${float(price):,.2f}")
            else:
                print(f"❌ {asset:5}: No price data")
                
    except Exception as e:
        print(f"❌ Price testing failed: {e}")

if __name__ == "__main__":
    print("🌟 Hyperliquid Multi-Asset DCA - Asset Discovery")
    print("Phase 1.4.1: Complete asset spot index discovery")
    print()
    
    # Run discovery
    discovered = asyncio.run(discover_all_asset_indices())
    
    # Test prices if we found any assets
    if discovered:
        asyncio.run(test_asset_prices(discovered))
    
    print("\n✨ Discovery complete!")