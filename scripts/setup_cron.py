#!/usr/bin/env python3
"""
Cron Setup Script for Autonomous Multi-Asset DCA
Helps configure cron jobs for different execution frequencies
"""

import os
import sys
from pathlib import Path
from datetime import datetime, time
from typing import Dict, List

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.utils.logging_config import get_logger

logger = get_logger("cron_setup")


class CronScheduleManager:
    """Manages cron schedule generation for multi-asset DCA."""
    
    def __init__(self, bot_directory: str):
        self.bot_directory = Path(bot_directory).resolve()
        self.script_path = self.bot_directory / "scripts" / "autonomous_dca.py"
        self.python_path = sys.executable
        
    def generate_cron_entry(self, frequency: str, execution_time: time, timezone: str = "CET") -> str:
        """
        Generate cron entry for specified frequency and time.
        
        Args:
            frequency: 'daily', 'weekly', or 'monthly'
            execution_time: Time to execute (hour, minute)
            timezone: Timezone for execution
            
        Returns:
            Cron entry string
        """
        hour = execution_time.hour
        minute = execution_time.minute
        
        # Base command
        cmd = f"{self.python_path} {self.script_path}"
        
        # Add logging
        log_file = self.bot_directory / "logs" / "cron_autonomous.log"
        cmd += f" >> {log_file} 2>&1"
        
        if frequency == "daily":
            # Daily at specified time
            cron_time = f"{minute} {hour} * * *"
        elif frequency == "weekly":
            # Weekly on Monday at specified time (your current setup)
            cron_time = f"{minute} {hour} * * 1"
        elif frequency == "monthly":
            # Monthly on 1st at specified time
            cron_time = f"{minute} {hour} 1 * *"
        else:
            raise ValueError(f"Unsupported frequency: {frequency}")
        
        return f"{cron_time} {cmd}"
    
    def generate_smart_cron_schedule(self, assets_config: Dict[str, str]) -> List[str]:
        """
        Generate multiple cron entries based on different asset frequencies.
        
        Args:
            assets_config: Dict of asset -> frequency mapping
            
        Returns:
            List of cron entries
        """
        # Group assets by frequency
        frequency_groups = {}
        for asset, frequency in assets_config.items():
            if frequency not in frequency_groups:
                frequency_groups[frequency] = []
            frequency_groups[frequency].append(asset)
        
        cron_entries = []
        
        # Generate entries for each frequency group
        for frequency, assets in frequency_groups.items():
            if frequency == "daily":
                # Daily execution at 9:00 AM CET
                entry = self.generate_cron_entry("daily", time(9, 0))
                cron_entries.append(f"# Daily DCA for: {', '.join(assets)}")
                cron_entries.append(entry)
                
            elif frequency == "weekly":
                # Weekly execution on Monday at 9:00 AM CET (your current setup)
                entry = self.generate_cron_entry("weekly", time(9, 0))
                cron_entries.append(f"# Weekly DCA for: {', '.join(assets)}")
                cron_entries.append(entry)
                
            elif frequency == "monthly":
                # Monthly execution on 1st at 9:00 AM CET
                entry = self.generate_cron_entry("monthly", time(9, 0))
                cron_entries.append(f"# Monthly DCA for: {', '.join(assets)}")
                cron_entries.append(entry)
        
        return cron_entries
    
    def generate_backup_cron(self) -> str:
        """Generate cron entry for daily configuration backup."""
        cmd = f"{self.python_path} {self.bot_directory}/scripts/backup_config.py"
        log_file = self.bot_directory / "logs" / "backup.log"
        cmd += f" >> {log_file} 2>&1"
        
        # Daily backup at 8:00 AM CET (before DCA execution)
        return f"0 8 * * * {cmd}"
    
    def create_cron_file(self, output_file: str = None) -> str:
        """
        Create a complete cron configuration file.
        
        Args:
            output_file: Path to output cron file
            
        Returns:
            Path to created cron file
        """
        if output_file is None:
            output_file = self.bot_directory / "config" / "hyperliquid_dca.cron"
        
        # Ensure config directory exists
        Path(output_file).parent.mkdir(exist_ok=True)
        
        cron_content = []
        
        # Header
        cron_content.extend([
            "# Hyperliquid Multi-Asset DCA Bot Cron Configuration",
            f"# Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"# Bot directory: {self.bot_directory}",
            "",
            "# Environment variables",
            f"PATH={os.environ.get('PATH', '/usr/local/bin:/usr/bin:/bin')}",
            f"PYTHONPATH={self.bot_directory}/src",
            "",
        ])
        
        # Smart execution based on your current Monday 9 AM setup
        # This will be the main execution that handles all assets with smart indicators
        main_execution = self.generate_cron_entry("weekly", time(9, 0))
        cron_content.extend([
            "# Main Multi-Asset DCA Execution",
            "# Runs Monday at 9:00 AM CET with smart indicators",
            "# Automatically handles all enabled assets based on their individual frequencies",
            main_execution,
            "",
        ])
        
        # Optional: Additional daily check for assets that need daily frequency
        daily_check = self.generate_cron_entry("daily", time(9, 0))
        cron_content.extend([
            "# Optional: Daily check for assets configured with daily frequency",
            "# Uncomment the line below if you have assets set to daily DCA",
            f"# {daily_check}",
            "",
        ])
        
        # Backup configuration
        backup_cron = self.generate_backup_cron()
        cron_content.extend([
            "# Daily configuration backup",
            backup_cron,
            "",
        ])
        
        # Health check
        health_check_cmd = f"{self.python_path} {self.bot_directory}/scripts/health_check.py"
        health_log = self.bot_directory / "logs" / "health.log"
        health_check = f"0 */6 * * * {health_check_cmd} >> {health_log} 2>&1"
        cron_content.extend([
            "# Health check every 6 hours",
            health_check,
            "",
        ])
        
        # Write to file
        with open(output_file, 'w') as f:
            f.write('\n'.join(cron_content))
        
        logger.info(f"Cron configuration written to: {output_file}")
        return str(output_file)


def main():
    """Main setup function."""
    print("🚀 Setting up Autonomous Multi-Asset DCA Cron Jobs")
    print()
    
    # Get bot directory
    if len(sys.argv) > 1:
        bot_directory = sys.argv[1]
    else:
        bot_directory = Path(__file__).parent.parent
    
    print(f"Bot directory: {bot_directory}")
    
    # Initialize manager
    manager = CronScheduleManager(bot_directory)
    
    # Create cron file
    cron_file = manager.create_cron_file()
    
    print(f"✅ Cron configuration created: {cron_file}")
    print()
    print("📋 Next steps:")
    print(f"1. Review the cron configuration: cat {cron_file}")
    print(f"2. Install the cron job: crontab {cron_file}")
    print("3. Verify installation: crontab -l")
    print("4. Check logs after first execution")
    print()
    print("🎯 Your current Monday 9 AM CET execution will now:")
    print("   • Use smart indicators (RSI, MA dips, dynamic frequency)")
    print("   • Handle multiple assets automatically") 
    print("   • Respect individual asset frequency settings")
    print("   • Skip trades when indicators suggest waiting")
    print("   • Increase position sizes during dips")
    print()
    print("💡 The autonomous system is much smarter than simple weekly execution!")
    print("   It will evaluate market conditions and make intelligent decisions.")


if __name__ == "__main__":
    main()