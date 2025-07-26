# Hyperliquid DCA Bot

A sophisticated volatility-based Dollar Cost Averaging (DCA) bot for Bitcoin spot trading on Hyperliquid. This bot automatically adjusts position sizes based on market volatility, helping you accumulate Bitcoin more efficiently.

## 🚀 Features

- **Volatility-Based Position Sizing**: Dynamically adjusts investment amounts based on 30-day Bitcoin volatility
- **Automated Trading**: Execute trades automatically via cron jobs
- **Web Dashboard**: Beautiful Streamlit interface with real-time analytics
- **Portfolio Tracking**: Monitor performance, P&L, and trade history
- **Spot Trading**: Uses Hyperliquid's spot market (UBTC/USDC) for actual Bitcoin purchases
- **Multiple Data Sources**: Averages prices from CoinGecko and Hyperliquid for accuracy
- **Secure**: Password-protected interface with environment-based configuration

## 📈 Strategy

The bot implements an intelligent DCA strategy that invests more when volatility is low (better for accumulation) and less when volatility is high (risk management):

- **Low Volatility (≤30%)**: Invest maximum amount ($500 default)
- **High Volatility (≥100%)**: Invest minimum amount ($100 default)
- **Medium Volatility (30-100%)**: Linear interpolation between min and max

## 🛠️ Installation

### Prerequisites
- Python 3.8+
- Hyperliquid account with USDC balance (minimum $100)
- Private key for your Hyperliquid wallet

### Setup Steps

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/hyperliquid-dca-bot.git
   cd hyperliquid-dca-bot
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables**
   ```bash
   cp env.example .env
   # Edit .env and add your private key and password
   ```

4. **Set up configuration**
   ```bash
   cp dca_config.json.example dca_config.json
   # Edit dca_config.json with your wallet address and preferences
   ```

## ⚙️ Configuration

The bot supports flexible configuration for both development and production environments.

### Environment Variables (.env)
```bash
# Required: Your Hyperliquid wallet private key
HYPERLIQUID_PRIVATE_KEY=your_private_key_here

# Optional: Wallet address (will be derived from private key if not provided)
# Recommended for development environment
HYPERLIQUID_WALLET_ADDRESS=0xYourWalletAddress

# Required: Password for web interface
DCA_BOT_PASSWORD=your_secure_password_here

# Optional: Telegram notifications
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_id
```

### Bot Configuration (dca_config.json)
The app will automatically create this file with default values if it doesn't exist.

```json
{
  "wallet_address": "0xYourWalletAddress",
  "base_amount": 50.0,
  "min_amount": 25.0,
  "max_amount": 100.0,
  "frequency": "weekly",
  "volatility_window": 30,
  "low_vol_threshold": 35.0,
  "high_vol_threshold": 85.0,
  "enabled": true
}
```

### Configuration Priority
1. **Environment variables** (highest priority - recommended for security)
2. **dca_config.json file** (lower priority)
3. **Auto-generated defaults** (if no config exists)

### Development Setup
For local development, you have two options:

**Option 1: Environment variables only (recommended)**
```bash
cp env.example .env
# Edit .env and set HYPERLIQUID_WALLET_ADDRESS and HYPERLIQUID_PRIVATE_KEY
```

**Option 2: Config file**
```bash
cp dca_config.example.json dca_config.json
# Edit dca_config.json with your wallet address
```

## 🖥️ Usage

### Web Interface

1. **Start the dashboard**
   ```bash
   streamlit run main.py
   # or for legacy compatibility:
   # streamlit run hyperliquid_dca_bot.py
   ```

2. **Access the interface**
   - Open http://localhost:8501 in your browser
   - Login with your password (from .env)

3. **Dashboard Features**
   - **Overview Tab**: Real-time metrics, bot status, account balance with optimized data loading
   - **Portfolio Tab**: Performance charts, position history with enhanced visualizations
   - **Trade History Tab**: Detailed trade log with export functionality
   - **Volatility Analysis Tab**: Market volatility trends and position sizing analytics

### Automated Trading

1. **Set up cron job** (Unix/Linux/macOS)
   ```bash
   chmod +x setup_cron.sh
   ./setup_cron.sh
   ```

2. **Manual execution**
   ```bash
   python3 check_and_trade.py
   ```

3. **Test the bot**
   ```bash
   python3 test_dca_execution.py
   ```

## 📊 How It Works

1. **Volatility Calculation**: Fetches 30-day price history from CoinGecko
2. **Position Sizing**: Calculates investment amount based on current volatility
3. **Price Averaging**: Gets prices from both CoinGecko and Hyperliquid
4. **Order Execution**: Places spot market orders on Hyperliquid with 0.01% slippage
5. **Record Keeping**: Saves all trades to `dca_history.json`

## 🔒 Security Best Practices

- **Never commit your private key** - Always use environment variables
- **Use a dedicated wallet** - Don't use your main wallet for the bot
- **Set a strong password** - For the web interface
- **Monitor regularly** - Check the dashboard and logs periodically
- **Start small** - Test with minimum amounts first

## 📁 Project Structure

```
hyperliquid-dca-bot/
├── main.py                    # New modular main application entry point
├── hyperliquid_dca_bot.py    # Legacy main application (for compatibility)
├── check_and_trade.py         # Automated trading script for cron
├── run_tests.py              # Test runner with comprehensive test suite
├── setup_cron.sh              # Cron job setup helper
├── pytest.ini               # Test configuration
├── dca_config.json            # Bot configuration
├── dca_history.json           # Trade history (auto-generated)
├── requirements.txt           # Python dependencies (includes testing deps)
├── .env                       # Environment variables (create this)
├── src/                       # Modular source code
│   ├── __init__.py
│   ├── config/               # Configuration management
│   │   ├── __init__.py
│   │   ├── models.py         # Data models and validation
│   │   └── loader.py         # Configuration loading logic
│   ├── trading/              # Core trading functionality
│   │   ├── __init__.py
│   │   ├── bot.py            # Main DCA bot implementation
│   │   └── volatility.py     # Volatility calculation engine
│   ├── data/                 # Data access and persistence
│   │   ├── __init__.py
│   │   ├── storage.py        # Trade history storage
│   │   └── api_client.py     # Enhanced Hyperliquid API client
│   ├── ui/                   # User interface components
│   │   ├── __init__.py
│   │   ├── auth.py           # Authentication logic
│   │   └── dashboard.py      # Streamlit dashboard components
│   └── utils/                # Shared utilities
│       ├── __init__.py
│       ├── constants.py      # Application constants
│       ├── logging_config.py # Logging configuration
│       └── performance.py    # Performance optimization utilities
├── tests/                     # Comprehensive test suite
│   ├── __init__.py
│   ├── test_config_models.py      # Configuration tests
│   ├── test_config_loader.py      # Config loading tests
│   ├── test_trading_bot.py        # Bot functionality tests
│   ├── test_data_storage.py       # Storage layer tests
│   ├── test_api_client.py         # API client tests
│   └── test_volatility.py         # Volatility calculation tests
└── logs/                      # Log files (auto-created)
```

## 🧪 Testing

The project includes a comprehensive test suite with multiple test runners:

### Quick Testing
```bash
# Run all tests with coverage
python run_tests.py all

# Run only unit tests (fast)
python run_tests.py unit

# Run tests without coverage (faster)
python run_tests.py fast
```

### Advanced Testing
```bash
# Generate detailed coverage report
python run_tests.py coverage

# Run code linting
python run_tests.py lint

# Format code
python run_tests.py format

# Run comprehensive checks (tests + lint + format)
python run_tests.py check
```

### Using pytest directly
```bash
# Install test dependencies
pip install pytest pytest-asyncio pytest-mock pytest-cov

# Run specific test files
pytest tests/test_trading_bot.py -v
pytest tests/test_config_models.py -v

# Run with coverage
pytest --cov=src --cov-report=html
```

### Test Coverage
The test suite covers:
- ✅ Configuration management and validation
- ✅ Trading bot core functionality  
- ✅ Data storage and persistence
- ✅ API client with caching
- ✅ Volatility calculation engine
- ✅ Error handling and edge cases

## 📝 Troubleshooting

### Common Issues

1. **"Insufficient margin" error**
   - Ensure you have at least $100 USDC in your spot wallet
   - Check that you're using the correct wallet address

2. **"Order has invalid price" error**
   - The bot automatically rounds to whole dollars (BTC has $1 tick size)

3. **SSL Certificate errors**
   - This is a known issue with websockets, doesn't affect functionality

4. **Bot not trading**
   - Check if bot is enabled in configuration
   - Verify the frequency settings match your cron schedule
   - Ensure sufficient time has passed since last trade

## 🚧 Roadmap

### Recently Completed ✅
- ✅ **Modular Architecture**: Complete refactoring with separated concerns
- ✅ **Enhanced Testing**: Comprehensive test suite with 90%+ coverage  
- ✅ **Performance Optimization**: API caching and optimized data loading
- ✅ **Improved Code Structure**: Function decomposition and clean architecture
- ✅ **Better Data Management**: Robust storage layer with backup functionality

### Upcoming Features 🚀
- [ ] Telegram notifications integration
- [ ] Multiple asset support (ETH, other tokens)
- [ ] Advanced order types (limit orders, stop-loss)
- [ ] Tax reporting and export features  
- [ ] Docker containerization
- [ ] Cloud deployment guides
- [ ] Mobile-responsive dashboard
- [ ] Risk management enhancements
- [ ] Backtesting framework
- [ ] API rate limiting and queue management

## ⚠️ Disclaimer

This bot is for educational purposes. Cryptocurrency trading carries significant risk. Only invest what you can afford to lose. The authors are not responsible for any financial losses.

## 📄 License

MIT License - see LICENSE file for details

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 💬 Support

For issues and questions:
- Open an issue on GitHub
- Check the logs in the `logs/` directory
- Review the troubleshooting section above 