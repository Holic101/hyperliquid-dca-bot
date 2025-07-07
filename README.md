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

### Environment Variables (.env)
```bash
HYPERLIQUID_PRIVATE_KEY=your_private_key_here
DCA_BOT_PASSWORD=your_secure_password_here
```

### Bot Configuration (dca_config.json)
```json
{
  "wallet_address": "0xYourWalletAddress",
  "base_amount": 200.0,
  "min_amount": 100.0,
  "max_amount": 500.0,
  "frequency": "weekly",
  "volatility_window": 30,
  "low_vol_threshold": 30.0,
  "high_vol_threshold": 100.0,
  "enabled": true
}
```

## 🖥️ Usage

### Web Interface

1. **Start the dashboard**
   ```bash
   streamlit run hyperliquid_dca_bot.py
   ```

2. **Access the interface**
   - Open http://localhost:8501 in your browser
   - Login with your password (from .env)

3. **Dashboard Features**
   - **Overview Tab**: Real-time metrics, bot status, account balance
   - **Portfolio Tab**: Performance charts, position history
   - **Trade History Tab**: Detailed trade log with export
   - **Volatility Analysis Tab**: Market volatility trends and position sizing

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
├── hyperliquid_dca_bot.py    # Main application with Streamlit UI
├── check_and_trade.py         # Automated trading script for cron
├── test_dca_execution.py      # Test script for the bot
├── setup_cron.sh              # Cron job setup helper
├── dca_config.json            # Bot configuration
├── dca_history.json           # Trade history (auto-generated)
├── requirements.txt           # Python dependencies
├── .env                       # Environment variables (create this)
└── logs/                      # Log files (auto-created)
```

## 🧪 Testing

Run the comprehensive test suite:
```bash
python3 test_dca_execution.py
```

This will test:
- API connections
- Price fetching
- Volatility calculation
- Position sizing logic
- Order execution (with confirmation)

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

- [ ] Telegram notifications
- [ ] Multiple asset support
- [ ] Advanced order types (limit orders)
- [ ] Tax reporting features
- [ ] Mobile app

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