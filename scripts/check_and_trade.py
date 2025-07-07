#!/usr/bin/env python3
"""
Automated trading script for Hyperliquid DCA Bot
This script is designed to be run via cron job
"""
import asyncio
import json
import os
import sys
import logging
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from hyperliquid_dca_bot import HyperliquidDCABot, DCAConfig

# Load environment variables
load_dotenv()

# Configure logging
log_file = Path(__file__).parent / "logs" / f"dca_bot_{datetime.now().strftime('%Y%m%d')}.log"
log_file.parent.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

async def main():
    """Main execution function"""
    logger.info("=== Starting DCA Bot Automated Check ===")
    
    try:
        # Load configuration
        config_file = Path(__file__).parent / "dca_config.json"
        if not config_file.exists():
            logger.error("Configuration file not found. Please run the web interface to configure the bot.")
            return 1
        
        with open(config_file, 'r') as f:
            config_data = json.load(f)
        
        # Create config object
        config = DCAConfig(
            wallet_address=config_data["wallet_address"],
            private_key=os.getenv("HYPERLIQUID_PRIVATE_KEY"),
            base_amount=config_data.get("base_amount", 200.0),
            min_amount=config_data.get("min_amount", 100.0),
            max_amount=config_data.get("max_amount", 500.0),
            frequency=config_data.get("frequency", "weekly"),
            volatility_window=config_data.get("volatility_window", 30),
            low_vol_threshold=config_data.get("low_vol_threshold", 30.0),
            high_vol_threshold=config_data.get("high_vol_threshold", 100.0),
            enabled=config_data.get("enabled", True)
        )
        
        if not config.enabled:
            logger.info("Bot is disabled in configuration. Exiting.")
            return 0
        
        if not config.private_key:
            logger.error("Private key not found in environment variables.")
            return 1
        
        # Initialize bot
        bot = HyperliquidDCABot(config)
        logger.info(f"Bot initialized for wallet: {config.wallet_address[:6]}...{config.wallet_address[-4:]}")
        
        # Check if trade should execute
        if not bot.should_execute_trade():
            logger.info("Not time to execute trade based on frequency setting.")
            if bot.trade_history:
                last_trade = bot.trade_history[-1]
                logger.info(f"Last trade was on: {last_trade.timestamp.strftime('%Y-%m-%d %H:%M')}")
            return 0
        
        # Execute DCA trade
        logger.info("Executing DCA trade...")
        trade_record = await bot.execute_dca_trade()
        
        if trade_record:
            logger.info(f"✅ Trade executed successfully!")
            logger.info(f"   Price: ${trade_record.price:,.2f}")
            logger.info(f"   USD amount: ${trade_record.amount_usd:.2f}")
            logger.info(f"   BTC amount: {trade_record.amount_btc:.8f}")
            logger.info(f"   Volatility: {trade_record.volatility:.2f}%")
            
            # TODO: Send Telegram notification
            # if telegram_bot:
            #     await send_telegram_notification(trade_record)
            
            return 0
        else:
            logger.warning("Trade was not executed. Check logs for details.")
            return 1
            
    except Exception as e:
        logger.error(f"Error in automated trading script: {e}", exc_info=True)
        return 1
    
    finally:
        logger.info("=== DCA Bot Automated Check Complete ===\n")

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 