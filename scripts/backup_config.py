#!/usr/bin/env python3
"""
Configuration Backup Script
Creates daily backups of configuration files for safety
"""

import os
import json
import shutil
from pathlib import Path
from datetime import datetime
from typing import List

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.utils.logging_config import get_logger

logger = get_logger("backup")


def backup_configurations() -> bool:
    """Backup all configuration files."""
    try:
        bot_dir = Path(__file__).parent.parent
        config_dir = bot_dir / "config"
        backup_dir = bot_dir / "backups" / datetime.now().strftime("%Y-%m-%d")
        
        # Create backup directory
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Files to backup
        config_files = [
            "config.json",
            "multi_asset_config.json"
        ]
        
        backed_up = []
        
        for config_file in config_files:
            source = config_dir / config_file
            if source.exists():
                dest = backup_dir / config_file
                shutil.copy2(source, dest)
                backed_up.append(config_file)
                logger.info(f"Backed up {config_file}")
        
        # Cleanup old backups (keep last 30 days)
        cleanup_old_backups(bot_dir / "backups", days=30)
        
        if backed_up:
            logger.info(f"Backup completed: {len(backed_up)} files backed up to {backup_dir}")
            return True
        else:
            logger.warning("No configuration files found to backup")
            return False
            
    except Exception as e:
        logger.error(f"Backup failed: {e}")
        return False


def cleanup_old_backups(backup_root: Path, days: int = 30) -> None:
    """Remove backup directories older than specified days."""
    try:
        cutoff_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        cutoff_date = cutoff_date - timedelta(days=days)
        
        for backup_dir in backup_root.iterdir():
            if backup_dir.is_dir():
                try:
                    dir_date = datetime.strptime(backup_dir.name, "%Y-%m-%d")
                    if dir_date < cutoff_date:
                        shutil.rmtree(backup_dir)
                        logger.info(f"Removed old backup: {backup_dir.name}")
                except ValueError:
                    # Skip directories that don't match date format
                    continue
                    
    except Exception as e:
        logger.warning(f"Cleanup of old backups failed: {e}")


if __name__ == "__main__":
    success = backup_configurations()
    if success:
        print("✅ Configuration backup completed")
    else:
        print("❌ Configuration backup failed")
        sys.exit(1)