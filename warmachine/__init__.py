"""
WarMachine AI Trading System
"""

__version__ = "1.0.0"
__author__ = "WarMachine Team"
__email__ = "your.email@example.com"

from .core.config import Config
from .utils.logging import setup_logging

__all__ = ["Config", "setup_logging"] 