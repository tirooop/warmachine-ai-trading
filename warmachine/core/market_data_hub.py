"""
Market Data Hub - 市场数据中心

Manages market data collection, processing, and distribution.
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from .abstractions.notifications import IAlertSender
from .ai_event_pool import AIEventPool

logger = logging.getLogger(__name__)

class MarketDataHub:
    """Market data hub for collecting and distributing market data"""
    
    def __init__(self, config: Dict[str, Any], event_pool: Optional[AIEventPool] = None):
        """
        Initialize market data hub
        
        Args:
            config: Configuration dictionary
            event_pool: Optional event pool for publishing updates
        """
        self.config = config
        self.event_pool = event_pool
        self.subscriptions = {}  # symbol -> [callback]
        self.latest_data = {}  # symbol -> data
        
        logger.info("Market Data Hub initialized")
    
    async def initialize(self):
        """Initialize market data hub"""
        # TODO: Initialize data sources
        pass
    
    async def stop(self):
        """Stop market data hub"""
        # TODO: Clean up data sources
        pass
    
    def subscribe_ticker(self, symbol: str, callback=None):
        """
        Subscribe to ticker updates for a symbol
        
        Args:
            symbol: Trading symbol
            callback: Optional callback function for updates
        """
        if symbol not in self.subscriptions:
            self.subscriptions[symbol] = []
        
        if callback:
            self.subscriptions[symbol].append(callback)
        
        logger.info(f"Subscribed to {symbol}")
    
    def unsubscribe_ticker(self, symbol: str, callback=None):
        """
        Unsubscribe from ticker updates
        
        Args:
            symbol: Trading symbol
            callback: Optional callback to remove (None for all)
        """
        if symbol in self.subscriptions:
            if callback:
                self.subscriptions[symbol].remove(callback)
            else:
                del self.subscriptions[symbol]
            
            logger.info(f"Unsubscribed from {symbol}")
    
    def update_ticker(self, symbol: str, data: Dict[str, Any]):
        """
        Update ticker data and notify subscribers
        
        Args:
            symbol: Trading symbol
            data: Ticker data
        """
        self.latest_data[symbol] = data
        
        # Notify subscribers
        if symbol in self.subscriptions:
            for callback in self.subscriptions[symbol]:
                try:
                    callback(symbol, data)
                except Exception as e:
                    logger.error(f"Error in ticker callback: {str(e)}")
        
        # Publish to event pool
        if self.event_pool:
            self.event_pool.publish_event("PRICE_UPDATE", {
                "symbol": symbol,
                "data": data,
                "timestamp": datetime.now().isoformat()
            })
    
    def get_ticker(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get latest ticker data for a symbol
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Latest ticker data or None if not available
        """
        return self.latest_data.get(symbol) 