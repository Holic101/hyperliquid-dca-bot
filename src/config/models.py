"""Data models for configuration and trading records."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict


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
class AssetDCAConfig:
    """Configuration for a single asset DCA strategy"""
    symbol: str  # "BTC", "ETH", "SOL", etc.
    base_amount: float = 50.0
    min_amount: float = 25.0
    max_amount: float = 100.0
    frequency: str = "weekly"  # "daily", "weekly", "monthly"
    volatility_window: int = 30
    low_vol_threshold: float = 35.0
    high_vol_threshold: float = 85.0
    enabled: bool = True
    
    # Phase 2: Smart Indicators Settings
    use_rsi: bool = False
    rsi_period: int = 14
    rsi_oversold_threshold: float = 30.0
    rsi_overbought_threshold: float = 70.0
    rsi_use_wilder: bool = True
    
    use_ma_dips: bool = False
    ma_periods: str = "20,50,200"  # Comma-separated MA periods
    ma_type: str = "SMA"  # "SMA" or "EMA"
    ma_dip_thresholds: str = "2,5,10"  # Dip percentages for each MA (comma-separated)
    
    use_dynamic_frequency: bool = False
    dynamic_low_vol_threshold: float = 25.0
    dynamic_high_vol_threshold: float = 50.0
    
    def validate(self) -> bool:
        """Validate asset configuration parameters."""
        if not self.symbol:
            raise ValueError("Asset symbol is required")
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
        """Convert to dictionary for JSON serialization."""
        return {
            'symbol': self.symbol,
            'base_amount': self.base_amount,
            'min_amount': self.min_amount,
            'max_amount': self.max_amount,
            'frequency': self.frequency,
            'volatility_window': self.volatility_window,
            'low_vol_threshold': self.low_vol_threshold,
            'high_vol_threshold': self.high_vol_threshold,
            'enabled': self.enabled,
            # Phase 2: Smart Indicators
            'use_rsi': self.use_rsi,
            'rsi_period': self.rsi_period,
            'rsi_oversold_threshold': self.rsi_oversold_threshold,
            'rsi_overbought_threshold': self.rsi_overbought_threshold,
            'rsi_use_wilder': self.rsi_use_wilder,
            'use_ma_dips': self.use_ma_dips,
            'ma_periods': self.ma_periods,
            'ma_type': self.ma_type,
            'ma_dip_thresholds': self.ma_dip_thresholds,
            'use_dynamic_frequency': self.use_dynamic_frequency,
            'dynamic_low_vol_threshold': self.dynamic_low_vol_threshold,
            'dynamic_high_vol_threshold': self.dynamic_high_vol_threshold
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'AssetDCAConfig':
        """Create from dictionary (JSON deserialization)."""
        return cls(
            symbol=data['symbol'],
            base_amount=data.get('base_amount', 50.0),
            min_amount=data.get('min_amount', 25.0),
            max_amount=data.get('max_amount', 100.0),
            frequency=data.get('frequency', 'weekly'),
            volatility_window=data.get('volatility_window', 30),
            low_vol_threshold=data.get('low_vol_threshold', 35.0),
            high_vol_threshold=data.get('high_vol_threshold', 85.0),
            enabled=data.get('enabled', True),
            # Phase 2: Smart Indicators
            use_rsi=data.get('use_rsi', False),
            rsi_period=data.get('rsi_period', 14),
            rsi_oversold_threshold=data.get('rsi_oversold_threshold', 30.0),
            rsi_overbought_threshold=data.get('rsi_overbought_threshold', 70.0),
            rsi_use_wilder=data.get('rsi_use_wilder', True),
            use_ma_dips=data.get('use_ma_dips', False),
            ma_periods=data.get('ma_periods', "20,50,200"),
            ma_type=data.get('ma_type', "SMA"),
            ma_dip_thresholds=data.get('ma_dip_thresholds', "2,5,10"),
            use_dynamic_frequency=data.get('use_dynamic_frequency', False),
            dynamic_low_vol_threshold=data.get('dynamic_low_vol_threshold', 25.0),
            dynamic_high_vol_threshold=data.get('dynamic_high_vol_threshold', 50.0)
        )


@dataclass
class MultiAssetDCAConfig:
    """Configuration for Multi-Asset DCA with global settings"""
    private_key: str
    wallet_address: Optional[str] = None
    assets: Dict[str, AssetDCAConfig] = field(default_factory=dict)
    
    # Global settings
    enabled: bool = True
    notification_enabled: bool = True
    
    def validate(self) -> bool:
        """Validate multi-asset configuration."""
        if not self.private_key:
            raise ValueError("Private key is required")
        if not self.private_key.startswith('0x') or len(self.private_key) != 66:
            raise ValueError("Invalid private key format")
        if not self.assets:
            raise ValueError("At least one asset configuration is required")
        
        # Validate each asset config
        for symbol, asset_config in self.assets.items():
            asset_config.validate()
        
        return True

    def add_asset(self, asset_config: AssetDCAConfig) -> None:
        """Add an asset configuration."""
        self.assets[asset_config.symbol] = asset_config

    def remove_asset(self, symbol: str) -> None:
        """Remove an asset configuration."""
        if symbol in self.assets:
            del self.assets[symbol]

    def get_enabled_assets(self) -> List[AssetDCAConfig]:
        """Get all enabled asset configurations."""
        return [config for config in self.assets.values() if config.enabled]

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization (excludes private_key)."""
        return {
            'wallet_address': self.wallet_address,
            'assets': {symbol: config.to_dict() for symbol, config in self.assets.items()},
            'enabled': self.enabled,
            'notification_enabled': self.notification_enabled
        }

    @classmethod
    def from_dict(cls, data: dict, private_key: str = '') -> 'MultiAssetDCAConfig':
        """Create from dictionary (JSON deserialization)."""
        assets = {}
        for symbol, asset_data in data.get('assets', {}).items():
            assets[symbol] = AssetDCAConfig.from_dict(asset_data)
        
        return cls(
            private_key=private_key,
            wallet_address=data.get('wallet_address'),
            assets=assets,
            enabled=data.get('enabled', True),
            notification_enabled=data.get('notification_enabled', True)
        )


@dataclass
class TradeRecord:
    """Record of a DCA trade execution"""
    timestamp: datetime
    asset: str  # "BTC", "ETH", "SOL", etc.
    price: float
    amount_usd: float
    amount_asset: float  # Amount of the asset purchased
    volatility: float
    tx_hash: Optional[str] = None
    
    # Legacy support for existing BTC-only records
    @property
    def amount_btc(self) -> float:
        """Legacy property for BTC amount compatibility."""
        return self.amount_asset if self.asset == "BTC" else 0.0

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'timestamp': self.timestamp.isoformat(),
            'asset': self.asset,
            'price': self.price,
            'amount_usd': self.amount_usd,
            'amount_asset': self.amount_asset,
            'amount_btc': self.amount_btc,  # Legacy compatibility
            'volatility': self.volatility,
            'tx_hash': self.tx_hash
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'TradeRecord':
        """Create from dictionary (JSON deserialization)."""
        # Handle legacy format (BTC-only records)
        if 'asset' not in data:
            return cls(
                timestamp=datetime.fromisoformat(data['timestamp']),
                asset='BTC',  # Default to BTC for legacy records
                price=data['price'],
                amount_usd=data['amount_usd'],
                amount_asset=data.get('amount_btc', 0.0),  # Legacy field
                volatility=data['volatility'],
                tx_hash=data.get('tx_hash')
            )
        
        # New multi-asset format
        return cls(
            timestamp=datetime.fromisoformat(data['timestamp']),
            asset=data['asset'],
            price=data['price'],
            amount_usd=data['amount_usd'],
            amount_asset=data['amount_asset'],
            volatility=data['volatility'],
            tx_hash=data.get('tx_hash')
        )