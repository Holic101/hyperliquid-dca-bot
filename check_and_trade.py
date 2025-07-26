#!/usr/bin/env python3
"""
Automated trading script for Hyperliquid DCA Bot
This script is designed to be run via cron job
"""
import asyncio
import argparse
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Local imports
from src.config.loader import load_config
from src.trading.bot import HyperliquidDCABot
from src.utils.logging_config import setup_logging
from notifications import send_telegram_message

# Load environment variables
load_dotenv()

# Setup logging
logger = setup_logging("dca_cron")

async def main():
    """Main execution function"""
    parser = argparse.ArgumentParser(description="Hyperliquid DCA Bot automated trading script.")
    parser.add_argument("--force", action="store_true", help="Force a trade to execute, ignoring the frequency schedule.")
    args = parser.parse_args()

    if args.force:
        logger.info("⚡️ --force flag detected. Attempting to execute trade immediately.")

    logger.info("=== Starting DCA Bot Automated Check ===")
    
    try:
        # Load configuration using the new config loader
        config = load_config()
        if not config:
            logger.error("Failed to load configuration. Please check your setup.")
            return 1
        
        if not config.enabled:
            logger.info("Bot is disabled in configuration. Exiting.")
            return 0
        
        if not config.private_key:
            logger.error("Private key not found in environment variables.")
            return 1
        
        # Initialize bot
        bot = HyperliquidDCABot(config)
        logger.info(f"Bot initialized for wallet: {config.wallet_address[:6]}...{config.wallet_address[-4:]}")
        
        # Execute DCA trade (using force flag if provided)
        result = await bot.execute_dca_trade(force=args.force)
        
        if result:
            logger.info("✅ Trade executed successfully!")
            
            # Send success notification
            if bot.trade_history:
                last_trade = bot.trade_history[-1]
                success_message = (
                    f"🚀 **DCA Trade Executed Successfully!**\n\n"
                    f"💰 **Amount:** ${last_trade.amount_usd:.2f} USDC\n"
                    f"📈 **Price:** ${last_trade.price:,.2f}\n"
                    f"₿ **UBTC:** {last_trade.amount_btc:.6f}\n"
                    f"📊 **Volatility:** {last_trade.volatility:.1f}%\n"
                    f"🕐 **Time:** {last_trade.timestamp.strftime('%Y-%m-%d %H:%M')}"
                )
                await send_telegram_message(success_message)
            return 0
        else:
            logger.info("No trade executed (conditions not met or trade skipped)")
            return 0
            
    except Exception as e:
        logger.error(f"Error in automated trading script: {e}", exc_info=True)
        return 1
    
    finally:
        logger.info("=== DCA Bot Automated Check Complete ===\n")

if __name__ == "__main__":
    # Note: asyncio.run creates a new event loop.
    # If this script were part of a larger asyncio app, you might manage the loop differently.
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 