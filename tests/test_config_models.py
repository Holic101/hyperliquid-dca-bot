"""Tests for configuration models."""

import pytest
from datetime import datetime
from unittest.mock import patch

from src.config.models import DCAConfig, TradeRecord


class TestDCAConfig:
    """Test cases for DCAConfig class."""
    
    def test_create_valid_config(self):
        """Test creating a valid DCA configuration."""
        config = DCAConfig(
            private_key="0x" + "a" * 64,
            wallet_address="0x1234567890123456789012345678901234567890",
            base_amount=100.0,
            min_amount=50.0,
            max_amount=200.0,
            frequency="weekly",
            volatility_window=30,
            low_vol_threshold=15.0,
            high_vol_threshold=50.0,
            enabled=True
        )
        
        assert config.private_key == "0x" + "a" * 64
        assert config.wallet_address == "0x1234567890123456789012345678901234567890"
        assert config.base_amount == 100.0
        assert config.frequency == "weekly"
        assert config.enabled is True
    
    def test_default_values(self):
        """Test that default values are set correctly."""
        config = DCAConfig(private_key="0x" + "a" * 64)
        
        assert config.wallet_address is None
        assert config.base_amount == 50.0
        assert config.min_amount == 25.0
        assert config.max_amount == 100.0
        assert config.frequency == "weekly"
        assert config.volatility_window == 30
        assert config.low_vol_threshold == 35.0
        assert config.high_vol_threshold == 85.0
        assert config.enabled is True
    
    def test_validate_valid_config(self):
        """Test validation of a valid configuration."""
        config = DCAConfig(
            private_key="0x" + "a" * 64,
            base_amount=100.0,
            min_amount=50.0,
            max_amount=200.0
        )
        
        assert config.validate() is True
    
    def test_validate_invalid_private_key(self):
        """Test validation fails for invalid private key."""
        config = DCAConfig(private_key="invalid_key")
        
        with pytest.raises(ValueError, match="Invalid private key format"):
            config.validate()
    
    def test_validate_invalid_amounts(self):
        """Test validation fails for invalid amount relationships."""
        # Min > Base
        config = DCAConfig(
            private_key="0x" + "a" * 64,
            base_amount=50.0,
            min_amount=100.0
        )
        
        with pytest.raises(ValueError, match="min_amount must be < max_amount"):
            config.validate()
        
        # Base > Max
        config = DCAConfig(
            private_key="0x" + "a" * 64,
            base_amount=200.0,
            max_amount=100.0
        )
        
        with pytest.raises(ValueError, match="base_amount must be between min_amount and max_amount"):
            config.validate()
    
    def test_validate_invalid_frequency(self):
        """Test validation fails for invalid frequency."""
        config = DCAConfig(
            private_key="0x" + "a" * 64,
            frequency="invalid"
        )
        
        with pytest.raises(ValueError, match="frequency must be one of"):
            config.validate()
    
    def test_validate_invalid_volatility_thresholds(self):
        """Test validation fails for invalid volatility thresholds."""
        config = DCAConfig(
            private_key="0x" + "a" * 64,
            low_vol_threshold=50.0,
            high_vol_threshold=30.0
        )
        
        with pytest.raises(ValueError, match="low_vol_threshold must be < high_vol_threshold"):
            config.validate()
    
    def test_to_dict(self):
        """Test converting config to dictionary."""
        config = DCAConfig(
            private_key="0x" + "a" * 64,
            base_amount=100.0
        )
        
        config_dict = config.to_dict()
        
        assert isinstance(config_dict, dict)
        assert config_dict["base_amount"] == 100.0
        assert "private_key" not in config_dict  # Should be excluded
    
    def test_from_dict(self):
        """Test creating config from dictionary."""
        config_dict = {
            "base_amount": 100.0,
            "min_amount": 50.0,
            "max_amount": 200.0,
            "frequency": "daily",
            "enabled": False
        }
        
        config = DCAConfig.from_dict(config_dict, private_key="0x" + "a" * 64)
        
        assert config.base_amount == 100.0
        assert config.frequency == "daily"
        assert config.enabled is False
        assert config.private_key == "0x" + "a" * 64


class TestTradeRecord:
    """Test cases for TradeRecord class."""
    
    def test_create_trade_record(self):
        """Test creating a trade record."""
        timestamp = datetime.now()
        record = TradeRecord(
            timestamp=timestamp,
            price=50000.0,
            amount_usd=100.0,
            amount_btc=0.002,
            volatility=25.0,
            tx_hash="0xabcdef"
        )
        
        assert record.timestamp == timestamp
        assert record.price == 50000.0
        assert record.amount_usd == 100.0
        assert record.amount_btc == 0.002
        assert record.volatility == 25.0
        assert record.tx_hash == "0xabcdef"
    
    def test_to_dict(self):
        """Test converting trade record to dictionary."""
        timestamp = datetime(2023, 1, 1, 12, 0, 0)
        record = TradeRecord(
            timestamp=timestamp,
            price=50000.0,
            amount_usd=100.0,
            amount_btc=0.002,
            volatility=25.0
        )
        
        record_dict = record.to_dict()
        
        assert isinstance(record_dict, dict)
        assert record_dict["price"] == 50000.0
        assert record_dict["amount_usd"] == 100.0
        assert "timestamp" in record_dict
    
    def test_from_dict(self):
        """Test creating trade record from dictionary."""
        record_dict = {
            "timestamp": "2023-01-01T12:00:00",
            "price": 50000.0,
            "amount_usd": 100.0,
            "amount_btc": 0.002,
            "volatility": 25.0,
            "tx_hash": None
        }
        
        record = TradeRecord.from_dict(record_dict)
        
        assert record.price == 50000.0
        assert record.amount_usd == 100.0
        assert record.amount_btc == 0.002
        assert isinstance(record.timestamp, datetime)
        assert record.tx_hash is None