"""Tests for data storage functionality."""

import pytest
import json
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import patch, mock_open, MagicMock

from src.data.storage import TradeHistoryStorage
from src.config.models import TradeRecord


class TestTradeHistoryStorage:
    """Test cases for TradeHistoryStorage class."""
    
    @pytest.fixture
    def temp_file(self):
        """Create a temporary file for testing."""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.json') as f:
            yield f.name
        Path(f.name).unlink(missing_ok=True)
    
    @pytest.fixture
    def sample_trades(self):
        """Create sample trade records."""
        return [
            TradeRecord(
                timestamp=datetime(2023, 1, 1, 12, 0, 0),
                price=50000.0,
                amount_usd=100.0,
                amount_btc=0.002,
                volatility=25.0
            ),
            TradeRecord(
                timestamp=datetime(2023, 1, 8, 12, 0, 0),
                price=52000.0,
                amount_usd=120.0,
                amount_btc=0.0023,
                volatility=30.0
            )
        ]
    
    def test_initialization_new_file(self, temp_file):
        """Test storage initialization with new file."""
        storage = TradeHistoryStorage(temp_file)
        
        assert storage.file_path == Path(temp_file)
        assert storage.file_path.exists()
    
    def test_initialization_existing_file(self, temp_file):
        """Test storage initialization with existing file."""
        # Create file first
        Path(temp_file).touch()
        
        storage = TradeHistoryStorage(temp_file)
        
        assert storage.file_path == Path(temp_file)
        assert storage.file_path.exists()
    
    def test_save_and_load_trades(self, temp_file, sample_trades):
        """Test saving and loading trade records."""
        storage = TradeHistoryStorage(temp_file)
        
        # Save trades
        result = storage.save(sample_trades)
        assert result is True
        
        # Load trades
        loaded_trades = storage.load()
        
        assert len(loaded_trades) == 2
        assert loaded_trades[0].price == 50000.0
        assert loaded_trades[1].amount_usd == 120.0
        assert isinstance(loaded_trades[0].timestamp, datetime)
    
    def test_save_empty_list(self, temp_file):
        """Test saving empty trade list."""
        storage = TradeHistoryStorage(temp_file)
        
        result = storage.save([])
        assert result is True
        
        loaded_trades = storage.load()
        assert loaded_trades == []
    
    def test_load_nonexistent_file(self):
        """Test loading from nonexistent file."""
        storage = TradeHistoryStorage("/nonexistent/path/file.json")
        
        trades = storage.load()
        assert trades == []
    
    @patch('builtins.open', mock_open(read_data='invalid json'))
    def test_load_invalid_json(self, temp_file):
        """Test loading invalid JSON file."""
        Path(temp_file).touch()  # Create the file
        
        with patch('pathlib.Path.exists', return_value=True):
            storage = TradeHistoryStorage(temp_file)
            trades = storage.load()
        
        assert trades == []
    
    def test_backup_creation(self, temp_file, sample_trades):
        """Test that backup is created when saving over existing file."""
        storage = TradeHistoryStorage(temp_file)
        
        # Save initial trades
        storage.save(sample_trades[:1])
        
        # Save new trades (should create backup)
        result = storage.save(sample_trades)
        assert result is True
        
        # Check backup exists
        backup_path = Path(temp_file).with_suffix('.json.backup')
        assert backup_path.exists()
        
        # Verify backup content
        with open(backup_path, 'r') as f:
            backup_data = json.load(f)
        assert len(backup_data) == 1
    
    @patch('builtins.open')
    def test_save_error_with_backup_restore(self, mock_file, temp_file, sample_trades):
        """Test backup restoration when save fails."""
        storage = TradeHistoryStorage(temp_file)
        
        # Create initial file
        storage.save(sample_trades[:1])
        
        # Mock file write error
        mock_file.side_effect = [
            mock_open().return_value,  # Backup creation
            IOError("Write error")     # Save failure
        ]
        
        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.rename') as mock_rename:
            result = storage.save(sample_trades)
        
        assert result is False
        # Should attempt to restore backup
        assert mock_rename.call_count >= 1
    
    def test_add_trade(self, temp_file, sample_trades):
        """Test adding a single trade."""
        storage = TradeHistoryStorage(temp_file)
        
        # Add first trade
        result = storage.add_trade(sample_trades[0])
        assert result is True
        
        # Verify trade was added
        trades = storage.load()
        assert len(trades) == 1
        assert trades[0].price == 50000.0
        
        # Add second trade
        result = storage.add_trade(sample_trades[1])
        assert result is True
        
        # Verify both trades exist
        trades = storage.load()
        assert len(trades) == 2
    
    @patch('src.data.storage.TradeHistoryStorage.load')
    @patch('src.data.storage.TradeHistoryStorage.save')
    def test_add_trade_error(self, mock_save, mock_load, temp_file, sample_trades):
        """Test error handling in add_trade."""
        storage = TradeHistoryStorage(temp_file)
        
        mock_load.return_value = []
        mock_save.return_value = False
        
        result = storage.add_trade(sample_trades[0])
        assert result is False
    
    def test_get_recent_trades(self, temp_file):
        """Test getting recent trades."""
        storage = TradeHistoryStorage(temp_file)
        
        now = datetime.now()
        trades = [
            TradeRecord(
                timestamp=now - timedelta(days=5),
                price=50000.0,
                amount_usd=100.0,
                amount_btc=0.002,
                volatility=25.0
            ),
            TradeRecord(
                timestamp=now - timedelta(days=45),  # Old trade
                price=45000.0,
                amount_usd=100.0,
                amount_btc=0.0022,
                volatility=20.0
            ),
            TradeRecord(
                timestamp=now - timedelta(days=10),
                price=52000.0,
                amount_usd=120.0,
                amount_btc=0.0023,
                volatility=30.0
            )
        ]
        
        storage.save(trades)
        
        # Get trades from last 30 days
        recent_trades = storage.get_recent_trades(days=30)
        
        assert len(recent_trades) == 2  # Should exclude the 45-day old trade
        assert all(t.timestamp >= now - timedelta(days=30) for t in recent_trades)
    
    @patch('src.data.storage.TradeHistoryStorage.load')
    def test_get_recent_trades_error(self, mock_load, temp_file):
        """Test error handling in get_recent_trades."""
        storage = TradeHistoryStorage(temp_file)
        
        mock_load.side_effect = Exception("Load error")
        
        recent_trades = storage.get_recent_trades()
        assert recent_trades == []
    
    def test_get_stats_empty(self, temp_file):
        """Test getting stats with empty history."""
        storage = TradeHistoryStorage(temp_file)
        
        stats = storage.get_stats()
        
        assert stats["total_trades"] == 0
        assert stats["total_invested"] == 0
        assert stats["total_btc"] == 0
    
    def test_get_stats_with_trades(self, temp_file, sample_trades):
        """Test getting stats with trade history."""
        storage = TradeHistoryStorage(temp_file)
        storage.save(sample_trades)
        
        stats = storage.get_stats()
        
        assert stats["total_trades"] == 2
        assert stats["total_invested"] == 220.0  # 100 + 120
        assert stats["total_btc"] == 0.0043  # 0.002 + 0.0023
        assert stats["first_trade"] == datetime(2023, 1, 1, 12, 0, 0)
        assert stats["last_trade"] == datetime(2023, 1, 8, 12, 0, 0)
        assert stats["avg_trade_size"] == 110.0  # 220 / 2
    
    @patch('src.data.storage.TradeHistoryStorage.load')
    def test_get_stats_error(self, mock_load, temp_file):
        """Test error handling in get_stats."""
        storage = TradeHistoryStorage(temp_file)
        
        mock_load.side_effect = Exception("Load error")
        
        stats = storage.get_stats()
        assert "error" in stats
    
    def test_file_path_creation(self, temp_file):
        """Test that parent directories are created."""
        nested_path = Path(temp_file).parent / "nested" / "path" / "trades.json"
        
        storage = TradeHistoryStorage(str(nested_path))
        
        assert nested_path.parent.exists()
        assert nested_path.exists()