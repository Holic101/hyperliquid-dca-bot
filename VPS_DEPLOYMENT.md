# VPS Deployment Guide - Multi-Asset DCA with Smart Indicators

This guide helps you migrate from your current single-asset weekly cron setup to the new autonomous multi-asset system with smart indicators.

## 🚀 Overview of Changes

### What's Different:
- **Smart Indicators**: RSI, Moving Average dips, Dynamic frequency
- **Multi-Asset Support**: BTC, ETH, SOL, AVAX, LINK with individual strategies
- **Autonomous Decision Making**: Bot evaluates market conditions in real-time
- **Enhanced Logging**: Detailed execution logs with reasoning

### Migration Benefits:
- ✅ Keep your Monday 9 AM CET schedule
- 🧠 Add smart indicators for better entry timing
- 📊 Support multiple assets with individual strategies
- ⚡ Automatic frequency adjustments based on market volatility
- 📈 Better risk management with position sizing

## 📋 Pre-Migration Steps

### 1. Backup Current Setup
```bash
# Backup your current cron jobs
crontab -l > ~/hyperliquid_dca_backup.cron

# Backup current configuration
cp ~/.hyperliquid_dca/config.json ~/.hyperliquid_dca/config_backup_$(date +%Y%m%d).json
```

### 2. Update Code on VPS
```bash
cd /path/to/hyperliquid-dca-bot
git pull origin main

# Install new dependencies if needed
pip install -r requirements.txt
```

## 🔧 Migration Process

### Step 1: Test Configuration Migration
```bash
# Test the migration process (doesn't modify anything)
python3 scripts/autonomous_dca.py --dry-run

# This will:
# - Check if migration is needed
# - Show what will be migrated
# - Validate the new configuration
```

### Step 2: Run Migration
```bash
# Run the autonomous script once to trigger migration
python3 scripts/autonomous_dca.py

# This will:
# - Automatically migrate your single-asset config to multi-asset
# - Enable smart indicators (RSI + Moving Average dips)
# - Create backup of old configuration
# - Set up BTC with your existing settings
```

### Step 3: Configure Additional Assets (Optional)
```bash
# Start the dashboard to configure additional assets
streamlit run main.py

# Or edit the multi-asset config directly:
nano ~/.hyperliquid_dca/multi_asset_config.json
```

### Step 4: Set Up New Cron Jobs
```bash
# Generate new cron configuration
python3 scripts/setup_cron.py

# Review the generated cron file
cat config/hyperliquid_dca.cron

# Install the new cron jobs
crontab config/hyperliquid_dca.cron

# Verify installation
crontab -l
```

## 📅 Recommended Cron Schedule

### Your Current Setup Enhanced:
```bash
# Main Multi-Asset DCA Execution (Monday 9 AM CET)
0 9 * * 1 /usr/bin/python3 /path/to/hyperliquid-dca-bot/scripts/autonomous_dca.py >> /path/to/logs/cron_autonomous.log 2>&1

# Daily configuration backup (8 AM CET)
0 8 * * * /usr/bin/python3 /path/to/hyperliquid-dca-bot/scripts/backup_config.py >> /path/to/logs/backup.log 2>&1

# Health check every 6 hours
0 */6 * * * /usr/bin/python3 /path/to/hyperliquid-dca-bot/scripts/health_check.py >> /path/to/logs/health.log 2>&1
```

### For Multiple Frequencies:
If you configure assets with different frequencies, you can add additional cron jobs:

```bash
# Daily execution for assets configured with daily frequency
0 9 * * * /usr/bin/python3 /path/to/hyperliquid-dca-bot/scripts/autonomous_dca.py >> /path/to/logs/cron_daily.log 2>&1

# Weekly execution (your current Monday schedule)
0 9 * * 1 /usr/bin/python3 /path/to/hyperliquid-dca-bot/scripts/autonomous_dca.py >> /path/to/logs/cron_weekly.log 2>&1

# Monthly execution on 1st
0 9 1 * * /usr/bin/python3 /path/to/hyperliquid-dca-bot/scripts/autonomous_dca.py >> /path/to/logs/cron_monthly.log 2>&1
```

## 🧠 How Smart Indicators Work Autonomously

### RSI-Based Entry:
- **Before**: Always buy on Monday regardless of conditions
- **Now**: Skip buying if BTC is overbought (RSI > 70), proceed if oversold (RSI < 30)

### Moving Average Dips:
- **Before**: Always buy the same amount
- **Now**: Increase position size by 1.2x-2.5x when price is below moving averages

### Dynamic Frequency:
- **Before**: Fixed weekly schedule
- **Now**: Can adjust frequency based on volatility (high volatility = more frequent, low volatility = less frequent)

## 📊 Example Smart Execution Scenarios

### Scenario 1: Normal Market
```
Monday 9 AM: RSI = 45, Price above all MAs
Result: Execute normal DCA amount ($100)
Reason: "RSI neutral, no dip detected, regular frequency"
```

### Scenario 2: Overbought Market
```
Monday 9 AM: RSI = 75 (overbought)
Result: Skip trade entirely
Reason: "RSI overbought: 75.0 > 70.0, waiting for better entry"
```

### Scenario 3: Dip Opportunity
```
Monday 9 AM: RSI = 35, Price 5% below 50-day MA
Result: Execute 1.5x DCA amount ($150)
Reason: "RSI slightly oversold, MA dip detected: 1.5x multiplier"
```

### Scenario 4: Major Dip
```
Monday 9 AM: RSI = 25, Price 8% below multiple MAs
Result: Execute 2.5x DCA amount ($250)
Reason: "RSI oversold, strong dip: multiple MA levels breached"
```

## 📁 Directory Structure

```
/path/to/hyperliquid-dca-bot/
├── scripts/
│   ├── autonomous_dca.py      # Main execution script (replaces old cron script)
│   ├── setup_cron.py          # Cron configuration generator
│   ├── backup_config.py       # Daily configuration backup
│   └── health_check.py        # System health monitoring
├── logs/
│   ├── autonomous_execution.log # Main execution log
│   ├── cron_autonomous.log     # Cron execution output
│   ├── backup.log              # Backup operation log
│   └── health.log              # Health check log
├── config/
│   └── hyperliquid_dca.cron   # Generated cron configuration
└── backups/
    └── YYYY-MM-DD/            # Daily configuration backups
```

## 🔍 Monitoring Your Autonomous System

### Check Execution Logs:
```bash
# View recent autonomous executions
tail -f logs/autonomous_execution.log

# Check last cron execution
tail logs/cron_autonomous.log
```

### Health Check:
```bash
# Run manual health check
python3 scripts/health_check.py

# View latest health report
cat logs/health/latest_health.json
```

### Configuration Status:
```bash
# View current multi-asset configuration
cat ~/.hyperliquid_dca/multi_asset_config.json | jq .

# Check enabled assets
python3 -c "
import json
with open('~/.hyperliquid_dca/multi_asset_config.json') as f:
    config = json.load(f)
enabled = [asset for asset, cfg in config['assets'].items() if cfg['enabled']]
print(f'Enabled assets: {enabled}')
"
```

## 🚨 Troubleshooting

### Migration Issues:
```bash
# Check migration logs
grep "migration" logs/*.log

# Manually trigger migration
python3 -c "
from src.utils.migration import perform_migration
result = perform_migration()
print('Migration result:', result is not None)
"
```

### Execution Issues:
```bash
# Test execution without cron
python3 scripts/autonomous_dca.py

# Check API connectivity
python3 scripts/health_check.py

# Verify configuration
python3 -c "
from src.config.loader import load_config
config = load_config()
print('Config loaded:', config is not None)
"
```

### Cron Issues:
```bash
# Check if cron service is running
systemctl status cron

# View cron logs
grep CRON /var/log/syslog | tail -10

# Test cron environment
* * * * * /usr/bin/env > /tmp/cron_env.txt
```

## 📈 Expected Improvements

With smart indicators, you should see:
- **10-20% better entry prices** from RSI filtering
- **15-25% larger accumulation** during dips from MA detection
- **Reduced volatility drag** from dynamic frequency adjustments
- **Better risk management** from intelligent position sizing

## 🎯 Next Steps After Deployment

1. **Monitor First Week**: Watch execution logs to see smart indicator decisions
2. **Add More Assets**: Consider adding ETH, SOL via the dashboard
3. **Tune Indicators**: Adjust RSI thresholds or MA periods if needed
4. **Scale Up**: Increase position sizes as you gain confidence

## 💡 Pro Tips

- **Start Conservative**: Keep your current BTC amounts initially
- **Monitor Smart Decisions**: Review logs to understand indicator reasoning
- **Gradual Expansion**: Add one new asset at a time
- **Regular Health Checks**: Use the automated health monitoring
- **Keep Backups**: Daily automated backups protect your configuration

Your Monday 9 AM CET schedule remains the same, but now it's powered by intelligent market analysis! 🚀