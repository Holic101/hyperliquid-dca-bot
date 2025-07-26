"""Tests for trading bot functionality."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
import pandas as pd

from src.trading.bot import HyperliquidDCABot
from src.config.models import DCAConfig, TradeRecord


class TestHyperliquidDCABot:
    """Test cases for HyperliquidDCABot class."""
    
    @pytest.fixture
    def config(self):
        """Create a test configuration."""
        return DCAConfig(
            private_key='0x' + 'a' * 64,
            wallet_address='0x1234567890123456789012345678901234567890',
            base_amount=100.0,
            min_amount=50.0,
            max_amount=200.0,
            frequency='weekly',
            volatility_window=30,
            low_vol_threshold=20.0,
            high_vol_threshold=40.0,
            enabled=True
        )
    
    @pytest.fixture
    def mock_trade_history(self):
        """Create mock trade history."""
        return [
            TradeRecord(
                timestamp=datetime.now() - timedelta(days=10),
                price=50000.0,
                amount_usd=100.0,
                amount_btc=0.002,
                volatility=25.0
            ),
            TradeRecord(
                timestamp=datetime.now() - timedelta(days=3),
                price=52000.0,
                amount_usd=120.0,
                amount_btc=0.0023,
                volatility=30.0
            )
        ]
    
    @patch('src.trading.bot.TradeHistoryStorage')
    @patch('src.trading.bot.HyperliquidAPIClient')
    @patch('eth_account.Account.from_key')
    def test_bot_initialization(self, mock_account, mock_api_client, mock_storage, config):
        """Test bot initialization."""
        mock_account.return_value.address = config.wallet_address
        mock_storage.return_value.load.return_value = []
        
        bot = HyperliquidDCABot(config)
        
        assert bot.config == config
        assert bot.account is not None
        assert bot.storage is not None
        assert bot.api_client is not None
        assert bot.trade_history == []
    
    @patch('src.trading.bot.TradeHistoryStorage')
    @patch('src.trading.bot.HyperliquidAPIClient')
    def test_bot_initialization_no_private_key(self, mock_api_client, mock_storage):
        """Test bot initialization without private key."""
        config = DCAConfig(private_key='')
        mock_storage.return_value.load.return_value = []
        
        bot = HyperliquidDCABot(config)
        
        assert bot.account is None
        assert bot.config.private_key == ''
    
    @patch('src.trading.bot.TradeHistoryStorage')
    @patch('src.trading.bot.HyperliquidAPIClient')
    @patch('eth_account.Account.from_key')
    async def test_get_btc_price(self, mock_account, mock_api_client, mock_storage, config):
        """Test getting BTC price."""
        mock_storage.return_value.load.return_value = []
        mock_api_client.return_value.get_current_price = AsyncMock(return_value=50000.0)
        
        bot = HyperliquidDCABot(config)
        price = await bot.get_btc_price()
        
        assert price == 50000.0
    
    @patch('src.trading.bot.TradeHistoryStorage')
    @patch('src.trading.bot.HyperliquidAPIClient')
    @patch('eth_account.Account.from_key')
    async def test_get_btc_price_error(self, mock_account, mock_api_client, mock_storage, config):
        """Test handling BTC price fetch error."""
        mock_storage.return_value.load.return_value = []
        mock_api_client.return_value.get_current_price = AsyncMock(return_value=None)
        
        bot = HyperliquidDCABot(config)
        
        with pytest.raises(ConnectionError):
            await bot.get_btc_price()
    
    @patch('src.trading.bot.TradeHistoryStorage')
    @patch('src.trading.bot.HyperliquidAPIClient')
    @patch('eth_account.Account.from_key')
    async def test_calculate_volatility(self, mock_account, mock_api_client, mock_storage, config):
        """Test volatility calculation."""
        mock_storage.return_value.load.return_value = []
        
        # Mock historical prices
        prices_df = pd.DataFrame({
            'price': [50000, 51000, 49000, 52000, 48000]
        }, index=pd.date_range('2023-01-01', periods=5))
        
        mock_api_client.return_value.get_historical_prices = AsyncMock(return_value=prices_df)
        
        bot = HyperliquidDCABot(config)
        
        with patch.object(bot.volatility_calc, 'calculate_volatility', return_value=25.0):
            volatility = await bot.calculate_volatility()
        
        assert volatility == 25.0
    
    @patch('src.trading.bot.TradeHistoryStorage')
    @patch('src.trading.bot.HyperliquidAPIClient')
    @patch('eth_account.Account.from_key')
    async def test_calculate_volatility_error(self, mock_account, mock_api_client, mock_storage, config):
        """Test volatility calculation error handling."""
        mock_storage.return_value.load.return_value = []
        mock_api_client.return_value.get_historical_prices = AsyncMock(side_effect=Exception("API Error"))
        
        bot = HyperliquidDCABot(config)
        volatility = await bot.calculate_volatility()
        
        assert volatility is None
    
    @patch('src.trading.bot.TradeHistoryStorage')
    @patch('src.trading.bot.HyperliquidAPIClient')
    @patch('eth_account.Account.from_key')
    def test_should_execute_trade_no_history(self, mock_account, mock_api_client, mock_storage, config):
        """Test trade execution logic with no history."""
        mock_storage.return_value.load.return_value = []
        
        bot = HyperliquidDCABot(config)
        
        assert bot.should_execute_trade() is True
    
    @patch('src.trading.bot.TradeHistoryStorage')
    @patch('src.trading.bot.HyperliquidAPIClient')
    @patch('eth_account.Account.from_key')
    def test_should_execute_trade_disabled(self, mock_account, mock_api_client, mock_storage, config):
        """Test trade execution logic when bot is disabled."""
        config.enabled = False
        mock_storage.return_value.load.return_value = []
        
        bot = HyperliquidDCABot(config)
        
        assert bot.should_execute_trade() is False
    
    @patch('src.trading.bot.TradeHistoryStorage')
    @patch('src.trading.bot.HyperliquidAPIClient')
    @patch('eth_account.Account.from_key')
    def test_should_execute_trade_recent_trade(self, mock_account, mock_api_client, mock_storage, config):
        """Test trade execution logic with recent trade."""
        recent_trade = TradeRecord(
            timestamp=datetime.now() - timedelta(hours=1),
            price=50000.0,
            amount_usd=100.0,
            amount_btc=0.002,
            volatility=25.0
        )
        mock_storage.return_value.load.return_value = [recent_trade]
        
        bot = HyperliquidDCABot(config)
        
        assert bot.should_execute_trade() is False
    
    @patch('src.trading.bot.TradeHistoryStorage')
    @patch('src.trading.bot.HyperliquidAPIClient')
    @patch('eth_account.Account.from_key')
    def test_should_execute_trade_old_trade(self, mock_account, mock_api_client, mock_storage, config):
        """Test trade execution logic with old trade."""
        old_trade = TradeRecord(
            timestamp=datetime.now() - timedelta(days=10),
            price=50000.0,
            amount_usd=100.0,
            amount_btc=0.002,
            volatility=25.0
        )
        mock_storage.return_value.load.return_value = [old_trade]
        
        bot = HyperliquidDCABot(config)
        
        assert bot.should_execute_trade() is True
    
    @patch('src.trading.bot.TradeHistoryStorage')
    @patch('src.trading.bot.HyperliquidAPIClient')
    @patch('eth_account.Account.from_key')
    async def test_get_usdc_balance(self, mock_account, mock_api_client, mock_storage, config):
        """Test getting USDC balance."""
        mock_storage.return_value.load.return_value = []
        mock_api_client.return_value.get_account_balance = AsyncMock(return_value=1000.0)
        
        bot = HyperliquidDCABot(config)
        balance = await bot.get_usdc_balance()
        
        assert balance == 1000.0
        mock_api_client.return_value.get_account_balance.assert_called_with(config.wallet_address, "USDC")
    
    @patch('src.trading.bot.TradeHistoryStorage')
    @patch('src.trading.bot.HyperliquidAPIClient')
    @patch('eth_account.Account.from_key')
    async def test_get_ubtc_balance(self, mock_account, mock_api_client, mock_storage, config):
        """Test getting UBTC balance."""
        mock_storage.return_value.load.return_value = []
        mock_api_client.return_value.get_account_balance = AsyncMock(return_value=0.005)
        
        bot = HyperliquidDCABot(config)
        balance = await bot.get_ubtc_balance()
        
        assert balance == 0.005
        mock_api_client.return_value.get_account_balance.assert_called_with(config.wallet_address, "UBTC")
    
    @patch('src.trading.bot.TradeHistoryStorage')
    @patch('src.trading.bot.HyperliquidAPIClient')
    @patch('eth_account.Account.from_key')
    def test_calculate_position_size(self, mock_account, mock_api_client, mock_storage, config):
        """Test position size calculation."""
        mock_storage.return_value.load.return_value = []
        
        bot = HyperliquidDCABot(config)
        
        with patch.object(bot.volatility_calc, 'calculate_position_size', return_value=150.0):
            position_size = bot.calculate_position_size(25.0)
        
        assert position_size == 150.0
    
    @patch('src.trading.bot.TradeHistoryStorage')
    @patch('src.trading.bot.HyperliquidAPIClient')
    @patch('eth_account.Account.from_key')
    async def test_execute_spot_trade_success(self, mock_account, mock_api_client, mock_storage, config):
        """Test successful spot trade execution."""
        mock_storage.return_value.load.return_value = []
        mock_storage.return_value.add_trade = MagicMock(return_value=True)
        
        order_result = {"status": "ok", "oid": "12345"}
        mock_api_client.return_value.execute_spot_order = AsyncMock(return_value=order_result)
        
        bot = HyperliquidDCABot(config)
        result = await bot.execute_spot_trade(100.0, 50000.0, 25.0)
        
        assert result == order_result
        assert len(bot.trade_history) == 1
        mock_storage.return_value.add_trade.assert_called_once()
    
    @patch('src.trading.bot.TradeHistoryStorage')
    @patch('src.trading.bot.HyperliquidAPIClient')
    @patch('eth_account.Account.from_key')
    async def test_execute_spot_trade_failure(self, mock_account, mock_api_client, mock_storage, config):
        """Test failed spot trade execution."""
        mock_storage.return_value.load.return_value = []
        
        order_result = {"status": "error", "msg": "Insufficient balance"}
        mock_api_client.return_value.execute_spot_order = AsyncMock(return_value=order_result)
        
        bot = HyperliquidDCABot(config)
        result = await bot.execute_spot_trade(100.0, 50000.0, 25.0)
        
        assert result is None
        assert len(bot.trade_history) == 0
    
    @patch('src.trading.bot.TradeHistoryStorage')
    @patch('src.trading.bot.HyperliquidAPIClient')
    @patch('eth_account.Account.from_key')
    def test_get_portfolio_stats_empty(self, mock_account, mock_api_client, mock_storage, config):
        """Test portfolio stats with empty history."""
        mock_storage.return_value.load.return_value = []
        
        bot = HyperliquidDCABot(config)
        stats = bot.get_portfolio_stats()
        
        assert stats["total_invested"] == 0
        assert stats["btc_holdings"] == 0
        assert stats["avg_buy_price"] == 0
    
    @patch('src.trading.bot.TradeHistoryStorage')
    @patch('src.trading.bot.HyperliquidAPIClient')
    @patch('eth_account.Account.from_key')
    def test_get_portfolio_stats_with_trades(self, mock_account, mock_api_client, mock_storage, config, mock_trade_history):
        """Test portfolio stats with trade history."""
        mock_storage.return_value.load.return_value = mock_trade_history
        
        bot = HyperliquidDCABot(config)
        stats = bot.get_portfolio_stats()
        
        assert stats["total_invested"] == 220.0  # 100 + 120
        assert stats["btc_holdings"] == 0.0043  # 0.002 + 0.0023
        assert stats["avg_buy_price"] == pytest.approx(51162.79, rel=1e-2)  # 220 / 0.0043
    
    @patch('src.trading.bot.TradeHistoryStorage')
    @patch('src.trading.bot.HyperliquidAPIClient')
    @patch('eth_account.Account.from_key')
    async def test_execute_dca_trade_conditions_not_met(self, mock_account, mock_api_client, mock_storage, config):
        """Test DCA trade execution when conditions not met."""
        mock_storage.return_value.load.return_value = []
        
        bot = HyperliquidDCABot(config)
        
        with patch.object(bot, 'should_execute_trade', return_value=False):
            result = await bot.execute_dca_trade()
        
        assert result is None
    
    @patch('src.trading.bot.TradeHistoryStorage')
    @patch('src.trading.bot.HyperliquidAPIClient')
    @patch('eth_account.Account.from_key')
    async def test_execute_dca_trade_insufficient_balance(self, mock_account, mock_api_client, mock_storage, config):
        """Test DCA trade execution with insufficient balance."""
        mock_storage.return_value.load.return_value = []
        
        bot = HyperliquidDCABot(config)
        
        with patch.object(bot, 'should_execute_trade', return_value=True), \
             patch.object(bot, 'get_usdc_balance', return_value=10.0):  # Less than min_amount
            result = await bot.execute_dca_trade()
        
        assert result is None
    
    @patch('src.trading.bot.TradeHistoryStorage')
    @patch('src.trading.bot.HyperliquidAPIClient')
    @patch('eth_account.Account.from_key')
    async def test_execute_dca_trade_success(self, mock_account, mock_api_client, mock_storage, config):
        """Test successful DCA trade execution."""
        mock_storage.return_value.load.return_value = []
        
        order_result = {"status": "ok", "oid": "12345"}
        
        bot = HyperliquidDCABot(config)
        
        with patch.object(bot, 'should_execute_trade', return_value=True), \
             patch.object(bot, 'get_usdc_balance', return_value=1000.0), \
             patch.object(bot, 'calculate_volatility', return_value=25.0), \
             patch.object(bot, 'calculate_position_size', return_value=100.0), \
             patch.object(bot, 'get_btc_price', return_value=50000.0), \
             patch.object(bot, 'execute_spot_trade', return_value=order_result):
            result = await bot.execute_dca_trade()
        
        assert result == order_result