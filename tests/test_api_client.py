"""Tests for API client functionality."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
import pandas as pd

from src.data.api_client import HyperliquidAPIClient


class TestHyperliquidAPIClient:
    """Test cases for HyperliquidAPIClient class."""
    
    @pytest.fixture
    def mock_account(self):
        """Create a mock account."""
        account = MagicMock()
        account.address = "0x1234567890123456789012345678901234567890"
        return account
    
    @patch('src.data.api_client.Info')
    @patch('src.data.api_client.Exchange')
    @patch('src.data.api_client.CoinGeckoAPI')
    def test_initialization_with_account(self, mock_coingecko, mock_exchange, mock_info, mock_account):
        """Test API client initialization with account."""
        client = HyperliquidAPIClient(mock_account)
        
        assert client.info is not None
        assert client.exchange is not None
        assert client.coingecko is not None
        assert client._price_cache == {}
        mock_exchange.assert_called_once_with(mock_account, "https://api.hyperliquid.xyz")
    
    @patch('src.data.api_client.Info')
    @patch('src.data.api_client.Exchange')
    @patch('src.data.api_client.CoinGeckoAPI')
    def test_initialization_without_account(self, mock_coingecko, mock_exchange, mock_info):
        """Test API client initialization without account."""
        client = HyperliquidAPIClient(None)
        
        assert client.info is not None
        assert client.exchange is None
        assert client.coingecko is not None
        mock_exchange.assert_not_called()
    
    @patch('src.data.api_client.Info')
    @patch('src.data.api_client.Exchange')
    @patch('src.data.api_client.CoinGeckoAPI')
    def test_cache_validity_check(self, mock_coingecko, mock_exchange, mock_info):
        """Test cache validity checking."""
        client = HyperliquidAPIClient(None)
        
        # No cache entry
        assert client._is_cache_valid("test_key") is False
        
        # Valid cache entry
        client._price_cache["test_key"] = (datetime.now(), 50000.0)
        assert client._is_cache_valid("test_key") is True
        
        # Expired cache entry
        old_time = datetime.now() - timedelta(minutes=5)
        client._price_cache["test_key"] = (old_time, 50000.0)
        assert client._is_cache_valid("test_key") is False
    
    @patch('src.data.api_client.Info')
    @patch('src.data.api_client.Exchange')
    @patch('src.data.api_client.CoinGeckoAPI')
    async def test_get_current_price_hyperliquid_success(self, mock_coingecko, mock_exchange, mock_info):
        """Test getting current price from Hyperliquid successfully."""
        mock_info.return_value.all_mids.return_value = {"UBTC": "50000.0"}
        
        client = HyperliquidAPIClient(None)
        price = await client.get_current_price(use_cache=False)
        
        assert price == 50000.0
        assert "ubtc_price" in client._price_cache
    
    @patch('src.data.api_client.Info')
    @patch('src.data.api_client.Exchange')
    @patch('src.data.api_client.CoinGeckoAPI')
    async def test_get_current_price_cached(self, mock_coingecko, mock_exchange, mock_info):
        """Test getting current price from cache."""
        client = HyperliquidAPIClient(None)
        client._price_cache["ubtc_price"] = (datetime.now(), 50000.0)
        
        price = await client.get_current_price(use_cache=True)
        
        assert price == 50000.0
        # Should not call Hyperliquid API
        mock_info.return_value.all_mids.assert_not_called()
    
    @patch('src.data.api_client.Info')
    @patch('src.data.api_client.Exchange')
    @patch('src.data.api_client.CoinGeckoAPI')
    async def test_get_current_price_coingecko_fallback(self, mock_coingecko, mock_exchange, mock_info):
        """Test falling back to CoinGecko when Hyperliquid fails."""
        # Hyperliquid fails
        mock_info.return_value.all_mids.side_effect = Exception("API Error")
        
        # CoinGecko succeeds
        mock_coingecko.return_value.get_price.return_value = {'bitcoin': {'usd': 51000.0}}
        
        client = HyperliquidAPIClient(None)
        price = await client.get_current_price(use_cache=False)
        
        assert price == 51000.0
        assert "ubtc_price" in client._price_cache
    
    @patch('src.data.api_client.Info')
    @patch('src.data.api_client.Exchange')
    @patch('src.data.api_client.CoinGeckoAPI')
    async def test_get_current_price_all_sources_fail(self, mock_coingecko, mock_exchange, mock_info):
        """Test when all price sources fail."""
        # Both sources fail
        mock_info.return_value.all_mids.side_effect = Exception("Hyperliquid Error")
        mock_coingecko.return_value.get_price.side_effect = Exception("CoinGecko Error")
        
        client = HyperliquidAPIClient(None)
        price = await client.get_current_price(use_cache=False)
        
        assert price is None
    
    @patch('src.data.api_client.Info')
    @patch('src.data.api_client.Exchange')
    @patch('src.data.api_client.CoinGeckoAPI')
    async def test_get_account_balance_success(self, mock_coingecko, mock_exchange, mock_info):
        """Test getting account balance successfully."""
        mock_spot_state = {
            "balances": [
                {"coin": "USDC", "total": "1000.50"},
                {"coin": "UBTC", "total": "0.005"}
            ]
        }
        mock_info.return_value.spot_user_state.return_value = mock_spot_state
        
        client = HyperliquidAPIClient(None)
        
        # Test USDC balance
        usdc_balance = await client.get_account_balance("0x123", "USDC")
        assert usdc_balance == 1000.50
        
        # Test UBTC balance
        ubtc_balance = await client.get_account_balance("0x123", "UBTC")
        assert ubtc_balance == 0.005
        
        # Test non-existent coin
        eth_balance = await client.get_account_balance("0x123", "ETH")
        assert eth_balance == 0.0
    
    @patch('src.data.api_client.Info')
    @patch('src.data.api_client.Exchange')
    @patch('src.data.api_client.CoinGeckoAPI')
    async def test_get_account_balance_error(self, mock_coingecko, mock_exchange, mock_info):
        """Test error handling in get_account_balance."""
        mock_info.return_value.spot_user_state.side_effect = Exception("API Error")
        
        client = HyperliquidAPIClient(None)
        balance = await client.get_account_balance("0x123", "USDC")
        
        assert balance == 0.0
    
    @patch('src.data.api_client.Info')
    @patch('src.data.api_client.Exchange')
    @patch('src.data.api_client.CoinGeckoAPI')
    async def test_get_historical_prices_success(self, mock_coingecko, mock_exchange, mock_info):
        """Test getting historical prices successfully."""
        mock_data = {
            'prices': [
                [1672531200000, 50000],  # 2023-01-01
                [1672617600000, 51000],  # 2023-01-02
                [1672704000000, 49000]   # 2023-01-03
            ]
        }
        mock_coingecko.return_value.get_coin_market_chart_by_id.return_value = mock_data
        
        client = HyperliquidAPIClient(None)
        prices_df = await client.get_historical_prices(30)
        
        assert prices_df is not None
        assert isinstance(prices_df, pd.DataFrame)
        assert len(prices_df) <= 3  # May be grouped by date
        assert 'price' in prices_df.columns
    
    @patch('src.data.api_client.Info')
    @patch('src.data.api_client.Exchange')
    @patch('src.data.api_client.CoinGeckoAPI')
    async def test_get_historical_prices_error(self, mock_coingecko, mock_exchange, mock_info):
        """Test error handling in get_historical_prices."""
        mock_coingecko.return_value.get_coin_market_chart_by_id.side_effect = Exception("API Error")
        
        client = HyperliquidAPIClient(None)
        prices_df = await client.get_historical_prices(30)
        
        assert prices_df is None
    
    @patch('src.data.api_client.Info')
    @patch('src.data.api_client.Exchange')
    @patch('src.data.api_client.CoinGeckoAPI')
    async def test_execute_spot_order_success(self, mock_coingecko, mock_exchange, mock_info, mock_account):
        """Test successful spot order execution."""
        order_result = {"status": "ok", "oid": "12345"}
        mock_exchange.return_value.order.return_value = order_result
        
        client = HyperliquidAPIClient(mock_account)
        result = await client.execute_spot_order(100.0, 50000.0)
        
        assert result == order_result
        mock_exchange.return_value.order.assert_called_once()
    
    @patch('src.data.api_client.Info')
    @patch('src.data.api_client.Exchange')
    @patch('src.data.api_client.CoinGeckoAPI')
    async def test_execute_spot_order_no_exchange(self, mock_coingecko, mock_exchange, mock_info):
        """Test spot order execution without exchange connection."""
        client = HyperliquidAPIClient(None)  # No account
        result = await client.execute_spot_order(100.0, 50000.0)
        
        assert result is None
    
    @patch('src.data.api_client.Info')
    @patch('src.data.api_client.Exchange')
    @patch('src.data.api_client.CoinGeckoAPI')
    async def test_execute_spot_order_failure(self, mock_coingecko, mock_exchange, mock_info, mock_account):
        """Test failed spot order execution."""
        order_result = {"status": "error", "msg": "Insufficient balance"}
        mock_exchange.return_value.order.return_value = order_result
        
        client = HyperliquidAPIClient(mock_account)
        result = await client.execute_spot_order(100.0, 50000.0)
        
        assert result is None
    
    @patch('src.data.api_client.Info')
    @patch('src.data.api_client.Exchange')
    @patch('src.data.api_client.CoinGeckoAPI')
    async def test_execute_spot_order_exception(self, mock_coingecko, mock_exchange, mock_info, mock_account):
        """Test exception handling in spot order execution."""
        mock_exchange.return_value.order.side_effect = Exception("Order Error")
        
        client = HyperliquidAPIClient(mock_account)
        result = await client.execute_spot_order(100.0, 50000.0)
        
        assert result is None
    
    @patch('src.data.api_client.Info')
    @patch('src.data.api_client.Exchange')
    @patch('src.data.api_client.CoinGeckoAPI')
    async def test_get_spot_fills_success(self, mock_coingecko, mock_exchange, mock_info):
        """Test getting spot fills successfully."""
        mock_meta = {
            "tokens": [
                {"name": "USDC", "index": 0},
                {"name": "UBTC", "index": 1}
            ]
        }
        mock_fills = [
            {"asset": 1, "px": "50000", "sz": "0.002"},
            {"asset": 0, "px": "1", "sz": "100"},  # USDC fill, should be filtered
            {"asset": 1, "px": "51000", "sz": "0.001"}
        ]
        
        mock_info.return_value.spot_meta.return_value = mock_meta
        mock_info.return_value.user_fills_by_time.return_value = mock_fills
        
        client = HyperliquidAPIClient(None)
        fills = await client.get_spot_fills("0x123", 30)
        
        assert len(fills) == 2  # Only UBTC fills
        assert all(f["asset"] == 1 for f in fills)
    
    @patch('src.data.api_client.Info')
    @patch('src.data.api_client.Exchange')
    @patch('src.data.api_client.CoinGeckoAPI')
    async def test_get_spot_fills_no_ubtc_index(self, mock_coingecko, mock_exchange, mock_info):
        """Test getting spot fills when UBTC index not found."""
        mock_meta = {
            "tokens": [
                {"name": "USDC", "index": 0},
                {"name": "ETH", "index": 2}  # No UBTC
            ]
        }
        
        mock_info.return_value.spot_meta.return_value = mock_meta
        
        client = HyperliquidAPIClient(None)
        fills = await client.get_spot_fills("0x123", 30)
        
        assert fills == []
    
    @patch('src.data.api_client.Info')
    @patch('src.data.api_client.Exchange')
    @patch('src.data.api_client.CoinGeckoAPI')
    async def test_get_spot_fills_error(self, mock_coingecko, mock_exchange, mock_info):
        """Test error handling in get_spot_fills."""
        mock_info.return_value.spot_meta.side_effect = Exception("API Error")
        
        client = HyperliquidAPIClient(None)
        fills = await client.get_spot_fills("0x123", 30)
        
        assert fills == []