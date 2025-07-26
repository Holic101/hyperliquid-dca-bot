"""Tests for configuration loader."""

import pytest
import json
import os
from pathlib import Path
from unittest.mock import patch, mock_open, MagicMock

from src.config.loader import load_config, save_config, _create_default_config_file
from src.config.models import DCAConfig


class TestConfigLoader:
    """Test cases for configuration loading functionality."""
    
    @patch('src.config.loader.Path.exists')
    @patch('builtins.open', new_callable=mock_open)
    @patch.dict(os.environ, {
        'HYPERLIQUID_PRIVATE_KEY': '0x' + 'a' * 64,
        'HYPERLIQUID_WALLET_ADDRESS': '0x1234567890123456789012345678901234567890'
    })
    def test_load_config_from_env_vars(self, mock_file, mock_exists):
        """Test loading configuration from environment variables."""
        mock_exists.return_value = False  # No config file exists
        
        config = load_config()
        
        assert config is not None
        assert config.private_key == '0x' + 'a' * 64
        assert config.wallet_address == '0x1234567890123456789012345678901234567890'
        
        # Should create default config file
        mock_file.assert_called()
    
    @patch('src.config.loader.Path.exists')
    @patch('builtins.open', new_callable=mock_open)
    @patch.dict(os.environ, {'HYPERLIQUID_PRIVATE_KEY': '0x' + 'a' * 64})
    def test_load_config_from_file(self, mock_file, mock_exists):
        """Test loading configuration from JSON file."""
        mock_exists.return_value = True
        
        config_data = {
            "base_amount": 75.0,
            "frequency": "daily",
            "enabled": False
        }
        mock_file.return_value.read.return_value = json.dumps(config_data)
        
        config = load_config()
        
        assert config is not None
        assert config.base_amount == 75.0
        assert config.frequency == "daily"
        assert config.enabled is False
        assert config.private_key == '0x' + 'a' * 64
    
    @patch('src.config.loader.Path.exists')
    @patch('builtins.open', new_callable=mock_open)
    def test_load_config_no_private_key(self, mock_file, mock_exists):
        """Test loading configuration without private key."""
        mock_exists.return_value = False
        
        with patch.dict(os.environ, {}, clear=True):
            config = load_config()
        
        assert config is None
    
    @patch('src.config.loader.Path.exists')
    @patch('builtins.open', new_callable=mock_open)
    @patch.dict(os.environ, {'HYPERLIQUID_PRIVATE_KEY': 'invalid_key'})
    def test_load_config_invalid_private_key(self, mock_file, mock_exists):
        """Test loading configuration with invalid private key."""
        mock_exists.return_value = False
        
        config = load_config()
        
        assert config is None
    
    @patch('src.config.loader.Path.exists')
    @patch('builtins.open')
    @patch.dict(os.environ, {'HYPERLIQUID_PRIVATE_KEY': '0x' + 'a' * 64})
    def test_load_config_file_error(self, mock_file, mock_exists):
        """Test handling file read errors."""
        mock_exists.return_value = True
        mock_file.side_effect = IOError("File read error")
        
        config = load_config()
        
        # Should fall back to environment variables
        assert config is not None
        assert config.private_key == '0x' + 'a' * 64
    
    @patch('src.config.loader.Path.exists')
    @patch('builtins.open', new_callable=mock_open)
    @patch.dict(os.environ, {'HYPERLIQUID_PRIVATE_KEY': '0x' + 'a' * 64})
    def test_load_config_invalid_json(self, mock_file, mock_exists):
        """Test handling invalid JSON in config file."""
        mock_exists.return_value = True
        mock_file.return_value.read.return_value = "invalid json"
        
        config = load_config()
        
        # Should fall back to environment variables
        assert config is not None
        assert config.private_key == '0x' + 'a' * 64
    
    @patch('builtins.open', new_callable=mock_open)
    @patch('src.config.loader.Path.parent')
    def test_save_config(self, mock_parent, mock_file):
        """Test saving configuration to file."""
        mock_parent.mkdir = MagicMock()
        
        config = DCAConfig(
            private_key='0x' + 'a' * 64,
            base_amount=150.0,
            frequency="monthly"
        )
        
        result = save_config(config)
        
        assert result is True
        mock_file.assert_called()
        
        # Check that JSON was written
        written_content = mock_file.return_value.write.call_args[0][0]
        config_data = json.loads(written_content)
        assert config_data["base_amount"] == 150.0
        assert config_data["frequency"] == "monthly"
        assert "private_key" not in config_data  # Should not be saved
    
    @patch('builtins.open')
    @patch('src.config.loader.Path.parent')
    def test_save_config_file_error(self, mock_parent, mock_file):
        """Test handling file write errors."""
        mock_parent.mkdir = MagicMock()
        mock_file.side_effect = IOError("File write error")
        
        config = DCAConfig(private_key='0x' + 'a' * 64)
        
        result = save_config(config)
        
        assert result is False
    
    @patch('builtins.open', new_callable=mock_open)
    @patch('src.config.loader.Path.parent')
    def test_create_default_config_file(self, mock_parent, mock_file):
        """Test creating default configuration file."""
        mock_parent.mkdir = MagicMock()
        
        config = DCAConfig(private_key='0x' + 'a' * 64)
        
        result = _create_default_config_file(config)
        
        assert result is True
        mock_file.assert_called()
        
        # Verify content was written
        mock_file.return_value.write.assert_called()
    
    @patch('builtins.open')
    @patch('src.config.loader.Path.parent')
    def test_create_default_config_file_error(self, mock_parent, mock_file):
        """Test handling errors when creating default config file."""
        mock_parent.mkdir = MagicMock()
        mock_file.side_effect = IOError("File write error")
        
        config = DCAConfig(private_key='0x' + 'a' * 64)
        
        result = _create_default_config_file(config)
        
        assert result is False