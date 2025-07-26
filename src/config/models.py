"""Data models for configuration and trading records."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class DCAConfig:
    """Configuration for DCA strategy"""
    private_key: str
    wallet_address: Optional[str] = None
    base_amount: float = 50.0
    min_amount: float = 25.0
    max_amount: float = 100.0
    frequency: str = "weekly"
    volatility_window: int = 30
    low_vol_threshold: float = 35.0
    high_vol_threshold: float = 85.0
    enabled: bool = True

    def validate(self) -> bool:
        """Validate configuration parameters."""
        if not self.private_key:
            raise ValueError("Private key is required")
        if not self.private_key.startswith('0x') or len(self.private_key) != 66:
            raise ValueError("Invalid private key format")
        if self.min_amount <= 0 or self.max_amount <= 0 or self.base_amount <= 0:
            raise ValueError("All amounts must be positive")
        if self.min_amount >= self.max_amount:
            raise ValueError("min_amount must be < max_amount")
        if self.base_amount < self.min_amount or self.base_amount > self.max_amount:
            raise ValueError("base_amount must be between min_amount and max_amount")
        if self.frequency not in ["daily", "weekly", "monthly"]:
            raise ValueError("frequency must be one of: daily, weekly, monthly")
        if self.volatility_window <= 0:
            raise ValueError("volatility_window must be positive")
        if self.low_vol_threshold >= self.high_vol_threshold:
            raise ValueError("low_vol_threshold must be < high_vol_threshold")
        return True

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization (excludes private_key)."""
        return {
            'wallet_address': self.wallet_address,
            'base_amount': self.base_amount,
            'min_amount': self.min_amount,
            'max_amount': self.max_amount,
            'frequency': self.frequency,
            'volatility_window': self.volatility_window,
            'low_vol_threshold': self.low_vol_threshold,
            'high_vol_threshold': self.high_vol_threshold,
            'enabled': self.enabled
        }

    @classmethod
    def from_dict(cls, data: dict, private_key: str = '') -> 'DCAConfig':
        """Create from dictionary (JSON deserialization)."""
        return cls(
            private_key=private_key,
            wallet_address=data.get('wallet_address'),
            base_amount=data.get('base_amount', 50.0),
            min_amount=data.get('min_amount', 25.0),
            max_amount=data.get('max_amount', 100.0),
            frequency=data.get('frequency', 'weekly'),
            volatility_window=data.get('volatility_window', 30),
            low_vol_threshold=data.get('low_vol_threshold', 35.0),
            high_vol_threshold=data.get('high_vol_threshold', 85.0),
            enabled=data.get('enabled', True)
        )


@dataclass
class TradeRecord:
    """Record of a DCA trade execution"""
    timestamp: datetime
    price: float
    amount_usd: float
    amount_btc: float
    volatility: float
    tx_hash: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'timestamp': self.timestamp.isoformat(),
            'price': self.price,
            'amount_usd': self.amount_usd,
            'amount_btc': self.amount_btc,
            'volatility': self.volatility,
            'tx_hash': self.tx_hash
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'TradeRecord':
        """Create from dictionary (JSON deserialization)."""
        return cls(
            timestamp=datetime.fromisoformat(data['timestamp']),
            price=data['price'],
            amount_usd=data['amount_usd'],
            amount_btc=data['amount_btc'],
            volatility=data['volatility'],
            tx_hash=data.get('tx_hash')
        )