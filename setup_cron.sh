#!/bin/bash

# Hyperliquid DCA Bot - Cron Setup Script
# This script helps you set up automated trading via cron

echo "=== Hyperliquid DCA Bot - Cron Setup ==="
echo

# Get the script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PYTHON_PATH=$(which python3)

# Check if check_and_trade.py exists
if [ ! -f "$SCRIPT_DIR/check_and_trade.py" ]; then
    echo "Error: check_and_trade.py not found in $SCRIPT_DIR"
    exit 1
fi

# Create logs directory if it doesn't exist
mkdir -p "$SCRIPT_DIR/logs"

echo "Script directory: $SCRIPT_DIR"
echo "Python path: $PYTHON_PATH"
echo

# Ask user for frequency
echo "Select trading frequency:"
echo "1) Daily (at 9:00 AM)"
echo "2) Weekly (Mondays at 9:00 AM)"
echo "3) Monthly (1st of each month at 9:00 AM)"
echo "4) Custom"
read -p "Enter your choice (1-4): " choice

case $choice in
    1)
        CRON_SCHEDULE="0 9 * * *"
        FREQUENCY="daily"
        ;;
    2)
        CRON_SCHEDULE="0 9 * * 1"
        FREQUENCY="weekly"
        ;;
    3)
        CRON_SCHEDULE="0 9 1 * *"
        FREQUENCY="monthly"
        ;;
    4)
        echo
        echo "Enter custom cron schedule (e.g., '0 */6 * * *' for every 6 hours)"
        echo "Format: MIN HOUR DAY MONTH DAYOFWEEK"
        read -p "Schedule: " CRON_SCHEDULE
        FREQUENCY="custom"
        ;;
    *)
        echo "Invalid choice"
        exit 1
        ;;
esac

# Create the cron command
CRON_CMD="cd $SCRIPT_DIR && $PYTHON_PATH check_and_trade.py >> $SCRIPT_DIR/logs/cron.log 2>&1"

echo
echo "The following cron job will be added:"
echo "$CRON_SCHEDULE $CRON_CMD"
echo

read -p "Do you want to add this cron job? (y/n): " confirm

if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
    # Add to crontab
    (crontab -l 2>/dev/null; echo "$CRON_SCHEDULE $CRON_CMD") | crontab -
    
    echo
    echo "✅ Cron job added successfully!"
    echo
    echo "To view your cron jobs: crontab -l"
    echo "To remove this cron job: crontab -e (then delete the line)"
    echo "To check logs: tail -f $SCRIPT_DIR/logs/cron.log"
    echo
    echo "⚠️  Important: Make sure your configuration has frequency set to '$FREQUENCY'"
    echo "   The bot will only trade when both cron runs AND frequency check passes."
else
    echo "Cron job setup cancelled."
fi

echo
echo "=== Setup Complete === 