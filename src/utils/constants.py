"""Application constants."""

from hyperliquid.utils import constants

# API Configuration
BASE_URL = constants.MAINNET_API_URL  # Use TESTNET_API_URL for testing
SPOT_ASSET_CTX_ID = 10_000  # Context ID for spot trading

# Asset Configuration
BITCOIN_SYMBOL = "BTC"  # For price data
BITCOIN_SPOT_SYMBOL = "UBTC/USDC"  # For spot orders

# Trading Configuration
MIN_USDC_BALANCE = 100.0  # Minimum USDC balance required for trading

# File Configuration
CONFIG_FILE = "dca_config.json"
HISTORY_FILE = "dca_history.json"

# UI Configuration
PAGE_TITLE = "Hyperliquid DCA Bot"
PAGE_ICON = "🚀"