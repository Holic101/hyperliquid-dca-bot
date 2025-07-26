"""
Hyperliquid DCA Bot - Core Package
Modular implementation with separated concerns
"""

__version__ = "2.0.0"
__author__ = "Hyperliquid DCA Bot Team"

from .config import DCAConfig, TradeRecord, load_config, save_config
from .trading import HyperliquidDCABot, VolatilityCalculator
from .utils import setup_logging

__all__ = [
    'DCAConfig', 
    'TradeRecord', 
    'load_config', 
    'save_config',
    'HyperliquidDCABot', 
    'VolatilityCalculator',
    'setup_logging'
]