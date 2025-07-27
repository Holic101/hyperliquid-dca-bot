#!/usr/bin/env python3
"""
Autonomous Multi-Asset DCA Execution Script
Designed for VPS cron execution with smart indicators
"""

import sys
import os
import json
import asyncio
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.config.models import MultiAssetDCAConfig
from src.config.loader import load_config
from src.trading.smart_multi_asset_bot import SmartMultiAssetDCABot
from src.utils.logging_config import get_logger
from src.utils.migration import check_migration_needed, perform_migration

logger = get_logger("autonomous_dca")


class AutonomousDCAManager:
    """Manages autonomous execution of multi-asset DCA with smart indicators."""
    
    def __init__(self):
        self.multi_config = None
        self.smart_bot = None
        self.execution_log = []
        
    def load_multi_asset_config(self) -> Optional[MultiAssetDCAConfig]:
        """Load multi-asset configuration or migrate from single-asset."""
        try:
            # Check if migration is needed
            if check_migration_needed():
                logger.info("Single-asset config detected, performing automatic migration")
                migrated_config = perform_migration()
                if migrated_config:
                    logger.info("Migration successful, using new multi-asset config")
                    return migrated_config
                else:
                    logger.error("Migration failed")
                    return None
            
            # Load existing multi-asset config
            base_config = load_config()
            if not base_config:
                logger.error("No configuration found")
                return None
            
            config_dir = os.path.dirname(base_config.__dict__.get('config_file', ''))
            multi_asset_config_file = os.path.join(config_dir, 'multi_asset_config.json')
            
            if os.path.exists(multi_asset_config_file):
                with open(multi_asset_config_file, 'r') as f:
                    data = json.load(f)
                return MultiAssetDCAConfig.from_dict(data, base_config.private_key)
            else:
                logger.error("Multi-asset config file not found")
                return None
                
        except Exception as e:
            logger.error(f"Error loading multi-asset config: {e}")
            return None
    
    def initialize_smart_bot(self) -> bool:
        """Initialize the smart multi-asset bot."""
        try:
            self.multi_config = self.load_multi_asset_config()
            if not self.multi_config:
                logger.error("Failed to load multi-asset configuration")
                return False
            
            self.smart_bot = SmartMultiAssetDCABot(self.multi_config)
            logger.info("Smart multi-asset bot initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize smart bot: {e}")
            return False
    
    def should_execute_asset(self, asset: str) -> Dict[str, any]:
        """
        Check if an asset should be executed based on frequency and smart indicators.
        
        Args:
            asset: Asset symbol to check
            
        Returns:
            Dictionary with execution decision and reasoning
        """
        try:
            asset_config = self.multi_config.assets.get(asset)
            if not asset_config or not asset_config.enabled:
                return {
                    "should_execute": False,
                    "reason": f"{asset} not enabled or configured",
                    "skip_type": "disabled"
                }
            
            # Check frequency timing
            last_trade = self.smart_bot.get_last_trade_time(asset)
            frequency_check = self.smart_bot.should_execute_based_on_frequency(asset, last_trade)
            
            if not frequency_check["should_execute"]:
                return {
                    "should_execute": False,
                    "reason": frequency_check["reason"],
                    "skip_type": "frequency",
                    "next_execution": frequency_check.get("next_execution")
                }
            
            # For autonomous execution, we want to respect smart indicators
            # but not be too restrictive - we'll use force=False to let indicators decide
            return {
                "should_execute": True,
                "reason": "Ready for smart indicator evaluation",
                "skip_type": None
            }
            
        except Exception as e:
            logger.error(f"Error checking execution for {asset}: {e}")
            return {
                "should_execute": False,
                "reason": f"Error: {e}",
                "skip_type": "error"
            }
    
    async def execute_smart_dca_for_asset(self, asset: str) -> Dict[str, any]:
        """
        Execute smart DCA for a specific asset.
        
        Args:
            asset: Asset symbol to execute
            
        Returns:
            Dictionary with execution results
        """
        logger.info(f"Starting smart DCA execution for {asset}")
        
        try:
            # Check if execution should proceed
            execution_check = self.should_execute_asset(asset)
            if not execution_check["should_execute"]:
                logger.info(f"Skipping {asset}: {execution_check['reason']}")
                return {
                    "asset": asset,
                    "status": "skipped",
                    "reason": execution_check["reason"],
                    "skip_type": execution_check["skip_type"]
                }
            
            # Execute smart DCA trade (let smart indicators decide)
            result = await self.smart_bot.execute_smart_asset_dca_trade(asset, force=False)
            
            if result and result.get("status") == "ok":
                trade_type = "simulation" if result.get("simulated") else "real"
                logger.info(f"✅ {asset} {trade_type} trade executed successfully")
                logger.info(f"   Amount: {result.get('amount_asset', 0):.6f} {asset}")
                logger.info(f"   USD: ${result.get('amount_usd', 0):.2f}")
                logger.info(f"   Reasoning: {result.get('reasoning', 'N/A')}")
                
                return {
                    "asset": asset,
                    "status": "executed",
                    "trade_type": trade_type,
                    "amount_asset": result.get("amount_asset", 0),
                    "amount_usd": result.get("amount_usd", 0),
                    "price": result.get("price", 0),
                    "reasoning": result.get("reasoning", ""),
                    "indicators_used": result.get("indicators_used", {}),
                    "position_multiplier": result.get("position_multiplier", 1.0)
                }
            else:
                error_msg = result.get("error", "Unknown error") if result else "No result returned"
                logger.warning(f"❌ {asset} trade failed: {error_msg}")
                
                return {
                    "asset": asset,
                    "status": "failed",
                    "error": error_msg,
                    "reasoning": result.get("reasoning", "") if result else ""
                }
                
        except Exception as e:
            logger.error(f"Error executing {asset} DCA: {e}")
            return {
                "asset": asset,
                "status": "error",
                "error": str(e)
            }
    
    async def execute_all_assets(self) -> Dict[str, any]:
        """
        Execute DCA for all enabled assets with smart indicators.
        
        Returns:
            Dictionary with execution summary
        """
        logger.info("Starting autonomous multi-asset DCA execution")
        
        if not self.multi_config or not self.multi_config.enabled:
            logger.warning("Multi-asset DCA is disabled globally")
            return {
                "status": "skipped",
                "reason": "Multi-asset DCA disabled globally",
                "results": {}
            }
        
        enabled_assets = [
            asset for asset, config in self.multi_config.assets.items() 
            if config.enabled
        ]
        
        if not enabled_assets:
            logger.warning("No assets enabled for DCA")
            return {
                "status": "skipped", 
                "reason": "No assets enabled",
                "results": {}
            }
        
        logger.info(f"Executing DCA for {len(enabled_assets)} assets: {', '.join(enabled_assets)}")
        
        # Execute all assets
        results = {}
        executed_count = 0
        skipped_count = 0
        failed_count = 0
        total_usd = 0
        
        for asset in enabled_assets:
            result = await self.execute_smart_dca_for_asset(asset)
            results[asset] = result
            
            if result["status"] == "executed":
                executed_count += 1
                total_usd += result.get("amount_usd", 0)
            elif result["status"] == "skipped":
                skipped_count += 1
            else:
                failed_count += 1
        
        # Log summary
        logger.info(f"Execution completed:")
        logger.info(f"  ✅ Executed: {executed_count}")
        logger.info(f"  ⏭️ Skipped: {skipped_count}")
        logger.info(f"  ❌ Failed: {failed_count}")
        logger.info(f"  💰 Total invested: ${total_usd:.2f}")
        
        return {
            "status": "completed",
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "executed": executed_count,
                "skipped": skipped_count,
                "failed": failed_count,
                "total_usd": total_usd
            },
            "results": results
        }
    
    def log_execution_results(self, execution_summary: Dict[str, any]) -> None:
        """Log execution results to file for monitoring."""
        try:
            log_file = Path(__file__).parent.parent / "logs" / "autonomous_execution.log"
            log_file.parent.mkdir(exist_ok=True)
            
            with open(log_file, "a") as f:
                f.write(f"\n{'-' * 80}\n")
                f.write(f"Execution Time: {execution_summary.get('timestamp', 'Unknown')}\n")
                f.write(f"Status: {execution_summary.get('status', 'Unknown')}\n")
                
                if execution_summary.get("summary"):
                    summary = execution_summary["summary"]
                    f.write(f"Summary: {summary['executed']} executed, {summary['skipped']} skipped, {summary['failed']} failed\n")
                    f.write(f"Total USD: ${summary['total_usd']:.2f}\n")
                
                if execution_summary.get("results"):
                    f.write("\nAsset Results:\n")
                    for asset, result in execution_summary["results"].items():
                        f.write(f"  {asset}: {result['status']}")
                        if result['status'] == 'executed':
                            f.write(f" - ${result.get('amount_usd', 0):.2f}")
                            if result.get('reasoning'):
                                f.write(f" ({result['reasoning']})")
                        elif result['status'] == 'skipped':
                            f.write(f" - {result.get('reason', 'Unknown reason')}")
                        f.write("\n")
                
                f.write(f"{'-' * 80}\n")
                
        except Exception as e:
            logger.error(f"Failed to log execution results: {e}")


async def main():
    """Main autonomous execution function."""
    logger.info("🚀 Starting autonomous multi-asset DCA execution")
    
    try:
        # Initialize manager
        manager = AutonomousDCAManager()
        
        # Initialize smart bot
        if not manager.initialize_smart_bot():
            logger.error("Failed to initialize smart bot")
            return 1
        
        # Execute all assets
        execution_summary = await manager.execute_all_assets()
        
        # Log results
        manager.log_execution_results(execution_summary)
        
        # Print summary for cron output
        if execution_summary["status"] == "completed":
            summary = execution_summary["summary"]
            print(f"✅ DCA Execution Complete: {summary['executed']} executed, {summary['skipped']} skipped, {summary['failed']} failed")
            print(f"💰 Total invested: ${summary['total_usd']:.2f}")
            
            if summary['failed'] > 0:
                print("⚠️ Some trades failed - check logs")
                return 1
        else:
            print(f"⏭️ DCA Execution: {execution_summary.get('reason', 'Skipped')}")
        
        return 0
        
    except Exception as e:
        logger.error(f"Autonomous execution failed: {e}")
        print(f"❌ Autonomous DCA failed: {e}")
        return 1


if __name__ == "__main__":
    import sys
    exit_code = asyncio.run(main())
    sys.exit(exit_code)