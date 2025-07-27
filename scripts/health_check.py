#!/usr/bin/env python3
"""
Health Check Script for Multi-Asset DCA Bot
Monitors system health and sends alerts if needed
"""

import os
import sys
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

logger = get_logger("health_check")


class HealthChecker:
    """Monitors the health of the multi-asset DCA system."""
    
    def __init__(self):
        self.bot_dir = Path(__file__).parent.parent
        self.health_status = {}
        
    def check_configuration_health(self) -> Dict[str, any]:
        """Check if configurations are valid and accessible."""
        try:
            # Check if config files exist
            config_dir = self.bot_dir / "config"
            
            status = {
                "config_files_exist": False,
                "multi_asset_config_valid": False,
                "enabled_assets": 0,
                "issues": []
            }
            
            # Check for configuration files
            config_files = ["config.json", "multi_asset_config.json"]
            existing_files = [f for f in config_files if (config_dir / f).exists()]
            
            if not existing_files:
                status["issues"].append("No configuration files found")
                return status
            
            status["config_files_exist"] = True
            
            # Try to load multi-asset config
            base_config = load_config()
            if base_config:
                multi_asset_file = config_dir / "multi_asset_config.json"
                if multi_asset_file.exists():
                    with open(multi_asset_file, 'r') as f:
                        data = json.load(f)
                    
                    multi_config = MultiAssetDCAConfig.from_dict(data, base_config.private_key)
                    status["multi_asset_config_valid"] = True
                    status["enabled_assets"] = len([
                        asset for asset, config in multi_config.assets.items() 
                        if config.enabled
                    ])
                    
                    if not multi_config.enabled:
                        status["issues"].append("Multi-asset DCA is globally disabled")
                    
                    if status["enabled_assets"] == 0:
                        status["issues"].append("No assets are enabled for DCA")
                        
                else:
                    status["issues"].append("Multi-asset config file not found")
            else:
                status["issues"].append("Could not load base configuration")
            
            return status
            
        except Exception as e:
            logger.error(f"Configuration health check failed: {e}")
            return {
                "config_files_exist": False,
                "multi_asset_config_valid": False,
                "enabled_assets": 0,
                "issues": [f"Health check error: {e}"]
            }
    
    async def check_api_connectivity(self) -> Dict[str, any]:
        """Check if API connections are working."""
        try:
            # Load config and initialize bot
            base_config = load_config()
            if not base_config:
                return {
                    "api_accessible": False,
                    "issues": ["Cannot load configuration for API test"]
                }
            
            config_dir = os.path.dirname(base_config.__dict__.get('config_file', ''))
            multi_asset_file = os.path.join(config_dir, 'multi_asset_config.json')
            
            if not os.path.exists(multi_asset_file):
                return {
                    "api_accessible": False,
                    "issues": ["Multi-asset config not found for API test"]
                }
            
            with open(multi_asset_file, 'r') as f:
                data = json.load(f)
            
            multi_config = MultiAssetDCAConfig.from_dict(data, base_config.private_key)
            smart_bot = SmartMultiAssetDCABot(multi_config)
            
            # Test API connectivity with a simple balance check
            usdc_balance = await smart_bot.api_client.get_asset_balance(
                multi_config.wallet_address, "USDC"
            )
            
            status = {
                "api_accessible": True,
                "usdc_balance": usdc_balance,
                "wallet_address": multi_config.wallet_address[:10] + "...",
                "issues": []
            }
            
            if usdc_balance < 10:
                status["issues"].append(f"Low USDC balance: ${usdc_balance:.2f}")
            
            return status
            
        except Exception as e:
            logger.error(f"API connectivity check failed: {e}")
            return {
                "api_accessible": False,
                "issues": [f"API connectivity error: {e}"]
            }
    
    def check_recent_execution(self) -> Dict[str, any]:
        """Check if autonomous execution has run recently."""
        try:
            log_file = self.bot_dir / "logs" / "autonomous_execution.log"
            
            status = {
                "recent_execution": False,
                "last_execution": None,
                "days_since_execution": None,
                "issues": []
            }
            
            if not log_file.exists():
                status["issues"].append("No execution log found")
                return status
            
            # Read log file and find last execution
            with open(log_file, 'r') as f:
                content = f.read()
            
            # Look for recent execution timestamps
            lines = content.split('\n')
            execution_times = []
            
            for line in lines:
                if "Execution Time:" in line:
                    try:
                        timestamp_str = line.split("Execution Time: ")[1]
                        execution_time = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                        execution_times.append(execution_time)
                    except:
                        continue
            
            if execution_times:
                last_execution = max(execution_times)
                status["last_execution"] = last_execution.isoformat()
                
                days_since = (datetime.now() - last_execution.replace(tzinfo=None)).days
                status["days_since_execution"] = days_since
                
                # Consider execution recent if within last 8 days (weekly + buffer)
                if days_since <= 8:
                    status["recent_execution"] = True
                else:
                    status["issues"].append(f"No execution in {days_since} days")
            else:
                status["issues"].append("No execution timestamps found in log")
            
            return status
            
        except Exception as e:
            logger.error(f"Execution check failed: {e}")
            return {
                "recent_execution": False,
                "last_execution": None,
                "days_since_execution": None,
                "issues": [f"Execution check error: {e}"]
            }
    
    def check_disk_space(self) -> Dict[str, any]:
        """Check available disk space."""
        try:
            statvfs = os.statvfs(self.bot_dir)
            
            # Calculate disk usage
            total_bytes = statvfs.f_frsize * statvfs.f_blocks
            free_bytes = statvfs.f_frsize * statvfs.f_available
            used_bytes = total_bytes - free_bytes
            
            usage_percent = (used_bytes / total_bytes) * 100
            free_gb = free_bytes / (1024**3)
            
            status = {
                "disk_usage_percent": round(usage_percent, 2),
                "free_space_gb": round(free_gb, 2),
                "issues": []
            }
            
            if usage_percent > 90:
                status["issues"].append(f"High disk usage: {usage_percent:.1f}%")
            elif free_gb < 1:
                status["issues"].append(f"Low free space: {free_gb:.2f} GB")
            
            return status
            
        except Exception as e:
            logger.error(f"Disk space check failed: {e}")
            return {
                "disk_usage_percent": None,
                "free_space_gb": None,
                "issues": [f"Disk check error: {e}"]
            }
    
    async def run_full_health_check(self) -> Dict[str, any]:
        """Run complete health check."""
        logger.info("Starting health check")
        
        health_report = {
            "timestamp": datetime.now().isoformat(),
            "overall_status": "healthy",
            "checks": {},
            "all_issues": []
        }
        
        # Run all checks
        checks = {
            "configuration": self.check_configuration_health(),
            "api_connectivity": await self.check_api_connectivity(),
            "recent_execution": self.check_recent_execution(),
            "disk_space": self.check_disk_space()
        }
        
        health_report["checks"] = checks
        
        # Collect all issues
        for check_name, check_result in checks.items():
            issues = check_result.get("issues", [])
            health_report["all_issues"].extend(issues)
        
        # Determine overall status
        if health_report["all_issues"]:
            health_report["overall_status"] = "issues_detected"
            logger.warning(f"Health check found {len(health_report['all_issues'])} issues")
        else:
            logger.info("Health check: All systems healthy")
        
        return health_report
    
    def save_health_report(self, health_report: Dict[str, any]) -> None:
        """Save health report to file."""
        try:
            health_dir = self.bot_dir / "logs" / "health"
            health_dir.mkdir(exist_ok=True)
            
            # Save latest report
            latest_file = health_dir / "latest_health.json"
            with open(latest_file, 'w') as f:
                json.dump(health_report, f, indent=2)
            
            # Save timestamped report
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            timestamped_file = health_dir / f"health_{timestamp}.json"
            with open(timestamped_file, 'w') as f:
                json.dump(health_report, f, indent=2)
            
            logger.info(f"Health report saved to {latest_file}")
            
        except Exception as e:
            logger.error(f"Failed to save health report: {e}")


async def main():
    """Main health check function."""
    print("🏥 Running Multi-Asset DCA Health Check")
    
    checker = HealthChecker()
    health_report = await checker.run_full_health_check()
    
    # Save report
    checker.save_health_report(health_report)
    
    # Print summary
    print(f"Health Status: {health_report['overall_status'].upper()}")
    
    if health_report["all_issues"]:
        print(f"Issues Found ({len(health_report['all_issues'])}):")
        for issue in health_report["all_issues"]:
            print(f"  ⚠️ {issue}")
        return 1
    else:
        print("✅ All systems healthy")
        return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)