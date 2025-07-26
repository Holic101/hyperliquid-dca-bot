"""Trade history storage and data persistence."""

import json
from pathlib import Path
from typing import List
from datetime import datetime, timedelta

from ..config.models import TradeRecord
from ..utils.constants import HISTORY_FILE
from ..utils.logging_config import get_logger

logger = get_logger(__name__)


class TradeHistoryStorage:
    """Handles persistence of trade history data."""
    
    def __init__(self, file_path: str = HISTORY_FILE):
        self.file_path = Path(file_path)
        self._ensure_file_exists()
    
    def _ensure_file_exists(self):
        """Ensure the history file exists."""
        if not self.file_path.exists():
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            self.save([])  # Create empty file
    
    def load(self) -> List[TradeRecord]:
        """Load trade history from file."""
        try:
            if not self.file_path.exists():
                logger.info("No trade history file found, starting with empty history")
                return []
            
            with open(self.file_path, 'r') as f:
                data = json.load(f)
            
            trades = [TradeRecord.from_dict(item) for item in data]
            logger.info(f"Loaded {len(trades)} trades from history")
            return trades
            
        except Exception as e:
            logger.error(f"Error loading trade history: {e}")
            return []
    
    def save(self, trades: List[TradeRecord]) -> bool:
        """Save trade history to file."""
        try:
            # Create backup
            if self.file_path.exists():
                backup_path = self.file_path.with_suffix('.json.backup')
                self.file_path.rename(backup_path)
            
            # Save new data
            data = [trade.to_dict() for trade in trades]
            with open(self.file_path, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            
            logger.info(f"Saved {len(trades)} trades to history")
            return True
            
        except Exception as e:
            logger.error(f"Error saving trade history: {e}")
            # Restore backup if save failed
            backup_path = self.file_path.with_suffix('.json.backup')
            if backup_path.exists():
                backup_path.rename(self.file_path)
                logger.info("Restored backup after save failure")
            return False
    
    def add_trade(self, trade: TradeRecord) -> bool:
        """Add a single trade to history."""
        try:
            trades = self.load()
            trades.append(trade)
            return self.save(trades)
        except Exception as e:
            logger.error(f"Error adding trade to history: {e}")
            return False
    
    def get_recent_trades(self, days: int = 30) -> List[TradeRecord]:
        """Get recent trades within specified days."""
        try:
            trades = self.load()
            cutoff_date = datetime.now() - timedelta(days=days)
            recent_trades = [t for t in trades if t.timestamp >= cutoff_date]
            logger.info(f"Found {len(recent_trades)} trades in last {days} days")
            return recent_trades
        except Exception as e:
            logger.error(f"Error getting recent trades: {e}")
            return []
    
    def get_stats(self) -> dict:
        """Get trade history statistics."""
        try:
            trades = self.load()
            if not trades:
                return {"total_trades": 0, "total_invested": 0, "total_btc": 0}
            
            return {
                "total_trades": len(trades),
                "total_invested": sum(t.amount_usd for t in trades),
                "total_btc": sum(t.amount_btc for t in trades),
                "first_trade": min(t.timestamp for t in trades),
                "last_trade": max(t.timestamp for t in trades),
                "avg_trade_size": sum(t.amount_usd for t in trades) / len(trades)
            }
        except Exception as e:
            logger.error(f"Error calculating trade stats: {e}")
            return {"error": str(e)}