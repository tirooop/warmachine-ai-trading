"""
Connector Manager Module

This module provides a unified interface for managing and accessing different market data connectors.
It implements the Singleton pattern to ensure only one instance manages all connections.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime
import asyncio
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ConnectorManager:
    """
    A singleton class that manages all market data connectors.
    Provides a unified interface for accessing different data sources.
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConnectorManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self._connectors: Dict[str, Any] = {}
        self._config: Dict[str, Any] = {}
        self._cache_dir = Path("data/cache")
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize connection status tracking
        self._connection_status = {}
        self._last_update = {}
        
        self._initialized = True
        logger.info("ConnectorManager initialized")
    
    async def initialize(self, config: Dict[str, Any]) -> bool:
        """
        Initialize all connectors with the provided configuration.
        
        Args:
            config: Configuration dictionary containing API keys and settings
            
        Returns:
            bool: True if all connectors initialized successfully
        """
        try:
            self._config = config
            
            # Initialize IBKR connector
            if "ibkr" in config.get("market_data", {}).get("providers", {}):
                from connectors.ibkr_connector import IBKRConnector
                self._connectors["ibkr"] = IBKRConnector(
                    config["market_data"]["providers"]["ibkr"]
                )
                logger.info("IBKR connector initialized")
            
            # Initialize Polygon connector
            if "polygon" in config.get("market_data", {}).get("providers", {}):
                from connectors.polygon_connector import PolygonConnector
                self._connectors["polygon"] = PolygonConnector(
                    config["market_data"]["providers"]["polygon"]
                )
                logger.info("Polygon connector initialized")
            
            # Initialize Binance connector
            if "binance" in config.get("market_data", {}).get("providers", {}):
                from connectors.binance_connector import BinanceConnector
                self._connectors["binance"] = BinanceConnector(
                    config["market_data"]["providers"]["binance"]
                )
                logger.info("Binance connector initialized")
            
            # Initialize AlphaVantage connector
            if "alphavantage" in config.get("market_data", {}).get("providers", {}):
                from connectors.alphavantage_connector import AlphaVantageConnector
                self._connectors["alphavantage"] = AlphaVantageConnector(
                    config["market_data"]["providers"]["alphavantage"]
                )
                logger.info("AlphaVantage connector initialized")
            
            return True
            
        except Exception as e:
            logger.error(f"Error initializing connectors: {str(e)}")
            return False
    
    async def connect_all(self) -> bool:
        """
        Connect to all initialized data sources.
        
        Returns:
            bool: True if all connections successful
        """
        success = True
        for source, connector in self._connectors.items():
            try:
                if hasattr(connector, 'connect'):
                    connected = await connector.connect()
                    self._connection_status[source] = connected
                    if connected:
                        logger.info(f"Connected to {source}")
                    else:
                        logger.error(f"Failed to connect to {source}")
                        success = False
            except Exception as e:
                logger.error(f"Error connecting to {source}: {str(e)}")
                self._connection_status[source] = False
                success = False
        
        return success
    
    async def disconnect_all(self):
        """Disconnect from all data sources."""
        for source, connector in self._connectors.items():
            try:
                if hasattr(connector, 'disconnect'):
                    await connector.disconnect()
                    self._connection_status[source] = False
                    logger.info(f"Disconnected from {source}")
            except Exception as e:
                logger.error(f"Error disconnecting from {source}: {str(e)}")
    
    async def get_data(self, source: str, data_type: str, **kwargs) -> Any:
        """
        Get data from specified source and type.
        
        Args:
            source: Data source identifier (ibkr, polygon, binance, etc.)
            data_type: Type of data to retrieve (real_time, historical, etc.)
            **kwargs: Additional parameters for data retrieval
            
        Returns:
            Any: Requested data
        """
        if source not in self._connectors:
            raise ValueError(f"Unknown data source: {source}")
            
        connector = self._connectors[source]
        
        try:
            if data_type == "real_time":
                if hasattr(connector, 'stream'):
                    return await connector.stream(**kwargs)
            elif data_type == "historical":
                if hasattr(connector, 'get_history'):
                    return await connector.get_history(**kwargs)
            elif data_type == "option_chain":
                if hasattr(connector, 'get_option_chain'):
                    return await connector.get_option_chain(**kwargs)
            else:
                raise ValueError(f"Unsupported data type: {data_type}")
                
        except Exception as e:
            logger.error(f"Error getting {data_type} data from {source}: {str(e)}")
            raise
    
    def get_connection_status(self) -> Dict[str, bool]:
        """Get current connection status for all connectors."""
        return self._connection_status.copy()
    
    def get_last_update(self, source: Optional[str] = None) -> Dict[str, datetime]:
        """Get timestamp of last data update for specified source or all sources."""
        if source:
            return {source: self._last_update.get(source)}
        return self._last_update.copy()
    
    async def validate_connections(self) -> Dict[str, bool]:
        """
        Validate all active connections.
        
        Returns:
            Dict[str, bool]: Connection validation results
        """
        results = {}
        for source, connector in self._connectors.items():
            try:
                if hasattr(connector, 'validate_connection'):
                    results[source] = await connector.validate_connection()
                else:
                    results[source] = self._connection_status.get(source, False)
            except Exception as e:
                logger.error(f"Error validating {source} connection: {str(e)}")
                results[source] = False
        return results 