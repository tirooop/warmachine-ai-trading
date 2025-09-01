"""
WarMachine Shared Interfaces

This module defines the core interfaces and protocols used across the WarMachine system.
These interfaces help prevent circular dependencies and provide clear contracts between components.
"""

from typing import Protocol, Dict, Any, List, Optional
from datetime import datetime
from enum import Enum

class DataType(Enum):
    """Market data types"""
    OHLCV = "ohlcv"
    TRADES = "trades"
    ORDERBOOK = "orderbook"
    TICKER = "ticker"
    FUNDAMENTAL = "fundamental"

class TimeFrame(Enum):
    """Time frames for market data"""
    MINUTE_1 = "1m"
    MINUTE_5 = "5m"
    MINUTE_15 = "15m"
    MINUTE_30 = "30m"
    HOUR_1 = "1h"
    HOUR_4 = "4h"
    DAY_1 = "1d"
    WEEK_1 = "1w"
    MONTH_1 = "1m"

class AIAnalyzerProtocol(Protocol):
    """Protocol for AI analysis components"""
    
    async def analyze_market_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze market data and return insights"""
        ...
    
    async def generate_signals(self, analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate trading signals based on analysis"""
        ...
    
    async def update_model(self, feedback: Dict[str, Any]) -> None:
        """Update AI model based on feedback"""
        ...

class MarketDataProtocol(Protocol):
    """Protocol for market data components"""
    
    async def get_data(self, symbol: str, data_type: DataType, 
                      timeframe: TimeFrame, start: datetime, 
                      end: datetime) -> Dict[str, Any]:
        """Get market data for specified parameters"""
        ...
    
    async def subscribe(self, symbol: str, data_type: DataType, 
                       callback: callable) -> None:
        """Subscribe to real-time market data"""
        ...

class TradingHandlerProtocol(Protocol):
    """Protocol for trading execution components"""
    
    async def execute_order(self, order: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a trading order"""
        ...
    
    async def get_position(self, symbol: str) -> Dict[str, Any]:
        """Get current position for a symbol"""
        ...
    
    async def get_account_info(self) -> Dict[str, Any]:
        """Get account information"""
        ...

class NotificationProtocol(Protocol):
    """Protocol for notification components"""
    
    async def send_alert(self, alert: Dict[str, Any]) -> None:
        """Send an alert/notification"""
        ...
    
    async def subscribe(self, user_id: str, alert_types: List[str]) -> None:
        """Subscribe to alerts"""
        ...

# Export all interfaces
__all__ = [
    'DataType',
    'TimeFrame',
    'AIAnalyzerProtocol',
    'MarketDataProtocol',
    'TradingHandlerProtocol',
    'NotificationProtocol'
] 