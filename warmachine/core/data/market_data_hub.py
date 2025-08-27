"""
Market Data Hub

Centralized data management system for the WarMachine AI Option Trader.
Handles real-time and historical data for stocks, options, and crypto.
Provides standardized access to all data sources.
"""

import os
import logging
import json
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union, Callable
import pandas as pd
import numpy as np
import yfinance as yf
from connectors.ibkr_connector import IBKRConnector
from connectors.polygon_connector import PolygonConnector
from connectors.alphavantage_connector import AlphaVantageConnector
from connectors.binance_connector import BinanceConnector

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DataType:
    """Enumeration of data types"""
    STOCK_BARS = "stock_bars"
    STOCK_QUOTES = "stock_quotes"
    STOCK_TRADES = "stock_trades"
    OPTION_CHAIN = "option_chain"
    OPTION_QUOTES = "option_quotes"
    OPTION_TRADES = "option_trades"
    CRYPTO_BARS = "crypto_bars"
    CRYPTO_QUOTES = "crypto_quotes"
    CRYPTO_TRADES = "crypto_trades"
    ORDER_BOOK = "order_book"
    MARKET_DEPTH = "market_depth"

class TimeFrame:
    """Enumeration of time frames"""
    TICK = "tick"
    SECOND_1 = "1s"
    SECOND_5 = "5s"
    SECOND_15 = "15s"
    SECOND_30 = "30s"
    MINUTE_1 = "1m"
    MINUTE_3 = "3m"
    MINUTE_5 = "5m"
    MINUTE_15 = "15m"
    MINUTE_30 = "30m"
    HOUR_1 = "1h"
    HOUR_4 = "4h"
    DAY_1 = "1d"
    WEEK_1 = "1w"

class YahooFinanceConnector:
    """Yahoo Finance data connector"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """Initialize Yahoo Finance connector"""
        self.config = config or {}
        logger.info("Yahoo Finance connector initialized")
    
    def get_stock_data(self, symbol: str, timeframe: str = TimeFrame.MINUTE_1, limit: int = 100) -> pd.DataFrame:
        """Get stock data from Yahoo Finance"""
        try:
            # Convert timeframe to yfinance interval
            interval_map = {
                TimeFrame.MINUTE_1: "1m",
                TimeFrame.MINUTE_5: "5m",
                TimeFrame.MINUTE_15: "15m",
                TimeFrame.MINUTE_30: "30m",
                TimeFrame.HOUR_1: "1h",
                TimeFrame.DAY_1: "1d",
                TimeFrame.WEEK_1: "1w"
            }
            interval = interval_map.get(timeframe, "1m")
            
            # Get data
            stock = yf.Ticker(symbol)
            data = stock.history(period=f"{limit}d", interval=interval)
            return data
        except Exception as e:
            logger.error(f"Error getting Yahoo Finance data for {symbol}: {str(e)}")
            return pd.DataFrame()
    
    def get_option_chain(self, symbol: str) -> Dict[str, Any]:
        """Get option chain from Yahoo Finance"""
        try:
            stock = yf.Ticker(symbol)
            options = stock.options
            if not options:
                return {}
            
            # Get the nearest expiry
            expiry = options[0]
            opt = stock.option_chain(expiry)
            
            return {
                "expiry": expiry,
                "calls": opt.calls.to_dict(),
                "puts": opt.puts.to_dict()
            }
        except Exception as e:
            logger.error(f"Error getting Yahoo Finance option chain for {symbol}: {str(e)}")
            return {}
    
    def get_crypto_data(self, symbol: str, timeframe: str = TimeFrame.MINUTE_1, limit: int = 100) -> pd.DataFrame:
        """Get cryptocurrency data from Yahoo Finance"""
        try:
            # Add -USD suffix if not present
            if not symbol.endswith("-USD"):
                symbol = f"{symbol}-USD"
            
            # Get data
            crypto = yf.Ticker(symbol)
            data = crypto.history(period=f"{limit}d", interval=timeframe)
            return data
        except Exception as e:
            logger.error(f"Error getting Yahoo Finance crypto data for {symbol}: {str(e)}")
            return pd.DataFrame()

class MarketDataHub:
    """Central hub for all market data"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the market data hub
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.data_sources = {}
        self.data_cache = {}
        self.last_update = {}
        self.callbacks = {}
        
        # Create data directory
        self.data_dir = "data/market"
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Lock for thread safety
        self.lock = threading.RLock()
        
        # Initialize data sources based on config
        self._init_data_sources()
        
        logger.info("Market Data Hub initialized")
    
    def _init_data_sources(self):
        """Initialize data sources based on configuration"""
        # Always initialize Yahoo Finance as fallback
        self.data_sources["yahoo"] = YahooFinanceConnector()
        logger.info("Yahoo Finance connector initialized")
        
        # Check for Interactive Brokers
        if self.config.get("ibkr", {}).get("enabled", False):
            try:
                ibkr_config = self.config.get("ibkr", {})
                self.data_sources["ibkr"] = IBKRConnector(ibkr_config)
                logger.info("IBKR connector initialized")
            except Exception as e:
                logger.error(f"Failed to initialize IBKR connector: {str(e)}")
        
        # Check for Polygon.io
        if self.config.get("polygon", {}).get("enabled", False):
            try:
                polygon_config = self.config.get("polygon", {})
                self.data_sources["polygon"] = PolygonConnector(polygon_config)
                logger.info("Polygon connector initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Polygon connector: {str(e)}")
        
        # Check for Alpha Vantage
        if self.config.get("alpha_vantage", {}).get("enabled", False):
            try:
                av_config = self.config.get("alpha_vantage", {})
                self.data_sources["alpha_vantage"] = AlphaVantageConnector(av_config)
                logger.info("Alpha Vantage connector initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Alpha Vantage connector: {str(e)}")
        
        # Check for Binance
        if self.config.get("binance", {}).get("enabled", False):
            try:
                binance_config = self.config.get("binance", {})
                self.data_sources["binance"] = BinanceConnector(binance_config)
                logger.info("Binance connector initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Binance connector: {str(e)}")
    
    def register_data_callback(self, data_type: str, symbol: str, callback: Callable):
        """
        Register a callback for real-time data updates
        
        Args:
            data_type: Type of data (from DataType class)
            symbol: Symbol to receive updates for
            callback: Function to call with updates
        """
        with self.lock:
            key = f"{data_type}:{symbol}"
            if key not in self.callbacks:
                self.callbacks[key] = []
            self.callbacks[key].append(callback)
            logger.debug(f"Registered callback for {key}")
    
    def _notify_callbacks(self, data_type: str, symbol: str, data: Any):
        """
        Notify all callbacks for a specific data type and symbol
        
        Args:
            data_type: Type of data
            symbol: Symbol
            data: New data
        """
        with self.lock:
            key = f"{data_type}:{symbol}"
            if key in self.callbacks:
                for callback in self.callbacks[key]:
                    try:
                        callback(data)
                    except Exception as e:
                        logger.error(f"Error in callback for {key}: {str(e)}")
    
    def get_stock_data(self, symbol: str, timeframe: str = TimeFrame.MINUTE_1, 
                      limit: int = 100, source: str = None) -> pd.DataFrame:
        """
        Get stock price data
        
        Args:
            symbol: Stock symbol
            timeframe: Time frame (from TimeFrame class)
            limit: Maximum number of bars to return
            source: Specific data source to use (None = auto-select)
            
        Returns:
            DataFrame with price data
        """
        data_type = DataType.STOCK_BARS
        cache_key = f"{data_type}:{symbol}:{timeframe}"
        
        with self.lock:
            # Check cache first
            if cache_key in self.data_cache:
                cache_entry = self.data_cache[cache_key]
                age = datetime.now() - cache_entry["timestamp"]
                # If cache is fresh and has enough data, return it
                if age.total_seconds() < 60 and len(cache_entry["data"]) >= limit:
                    return cache_entry["data"].tail(limit)
            
            # Select data source
            if source:
                if source not in self.data_sources:
                    logger.error(f"Data source {source} not available")
                    return pd.DataFrame()
                sources = [self.data_sources[source]]
            else:
                # Priority order: IBKR -> Polygon -> Alpha Vantage -> Yahoo Finance
                sources = [
                    self.data_sources.get("ibkr"),
                    self.data_sources.get("polygon"),
                    self.data_sources.get("alpha_vantage"),
                    self.data_sources.get("yahoo")  # Always available as fallback
                ]
                sources = [s for s in sources if s is not None]
            
            # Try each source in order
            for source in sources:
                try:
                    data = source.get_stock_data(symbol, timeframe, limit)
                    if not data.empty:
                        # Cache the result
                        self.save_to_cache(data_type, symbol, timeframe, data)
                        return data
                except Exception as e:
                    logger.warning(f"Error getting data from {source.__class__.__name__}: {str(e)}")
                    continue
            
            # If all sources fail, return empty DataFrame
            return pd.DataFrame()
    
    def get_option_chain(self, symbol: str, source: str = None) -> Dict[str, Any]:
        """
        Get full option chain for a symbol
        
        Args:
            symbol: Underlying symbol
            source: Specific data source to use (None = auto-select)
            
        Returns:
            Dictionary with option chain data
        """
        data_type = DataType.OPTION_CHAIN
        cache_key = f"{data_type}:{symbol}"
        
        with self.lock:
            # Check cache first
            if cache_key in self.data_cache:
                cache_entry = self.data_cache[cache_key]
                age = datetime.now() - cache_entry["timestamp"]
                # For option chains, refresh every minute
                if age.total_seconds() < 60:
                    return cache_entry["data"]
            
            # Select data source
            if source:
                if source not in self.data_sources:
                    logger.error(f"Data source {source} not available")
                    return {}
                sources = [self.data_sources[source]]
            else:
                # Priority order
                sources = [
                    self.data_sources.get("ibkr"),
                    self.data_sources.get("polygon")
                ]
                sources = [s for s in sources if s]
            
            # Try each source
            for source_obj in sources:
                try:
                    if hasattr(source_obj, "get_option_chain"):
                        data = source_obj.get_option_chain(symbol)
                        if data:
                            # Update cache
                            self.data_cache[cache_key] = {
                                "timestamp": datetime.now(),
                                "data": data
                            }
                            self.last_update[cache_key] = datetime.now()
                            return data
                except Exception as e:
                    logger.warning(f"Error getting option chain from {source_obj.__class__.__name__}: {str(e)}")
            
            # No data found
            logger.warning(f"No option chain found for {symbol}")
            return {}
    
    def get_crypto_data(self, symbol: str, timeframe: str = TimeFrame.MINUTE_1, 
                       limit: int = 100, source: str = None) -> pd.DataFrame:
        """
        Get cryptocurrency price data
        
        Args:
            symbol: Crypto symbol (e.g., BTC-USD)
            timeframe: Time frame (from TimeFrame class)
            limit: Maximum number of bars to return
            source: Specific data source to use (None = auto-select)
            
        Returns:
            DataFrame with price data
        """
        data_type = DataType.CRYPTO_BARS
        cache_key = f"{data_type}:{symbol}:{timeframe}"
        
        with self.lock:
            # Check cache first
            if cache_key in self.data_cache:
                cache_entry = self.data_cache[cache_key]
                age = datetime.now() - cache_entry["timestamp"]
                # If cache is fresh and has enough data, return it
                if age.total_seconds() < 60 and len(cache_entry["data"]) >= limit:
                    return cache_entry["data"].tail(limit)
            
            # Select data source
            if source:
                if source not in self.data_sources:
                    logger.error(f"Data source {source} not available")
                    return pd.DataFrame()
                sources = [self.data_sources[source]]
            else:
                # Priority order
                sources = [
                    self.data_sources.get("binance"),
                    self.data_sources.get("polygon"),
                    self.data_sources.get("alpha_vantage")
                ]
                sources = [s for s in sources if s]
            
            # Try each source
            for source_obj in sources:
                try:
                    if hasattr(source_obj, "get_crypto_bars"):
                        data = source_obj.get_crypto_bars(symbol, timeframe, limit)
                        if isinstance(data, pd.DataFrame) and not data.empty:
                            # Update cache
                            self.data_cache[cache_key] = {
                                "timestamp": datetime.now(),
                                "data": data
                            }
                            self.last_update[cache_key] = datetime.now()
                            return data
                except Exception as e:
                    logger.warning(f"Error getting crypto data from {source_obj.__class__.__name__}: {str(e)}")
            
            # No data found
            logger.warning(f"No crypto data found for {symbol} with timeframe {timeframe}")
            return pd.DataFrame()
    
    def get_order_book(self, symbol: str, depth: int = 10, source: str = None) -> Dict[str, Any]:
        """
        Get market order book
        
        Args:
            symbol: Instrument symbol
            depth: Book depth
            source: Specific data source to use (None = auto-select)
            
        Returns:
            Dictionary with order book data
        """
        data_type = DataType.ORDER_BOOK
        cache_key = f"{data_type}:{symbol}:{depth}"
        
        with self.lock:
            # Check cache first - order books need very fresh data
            if cache_key in self.data_cache:
                cache_entry = self.data_cache[cache_key]
                age = datetime.now() - cache_entry["timestamp"]
                # For order books, refresh every 5 seconds
                if age.total_seconds() < 5:
                    return cache_entry["data"]
            
            # Select data source
            if source:
                if source not in self.data_sources:
                    logger.error(f"Data source {source} not available")
                    return {"bids": [], "asks": []}
                sources = [self.data_sources[source]]
            else:
                # Priority order - depends on instrument type
                if symbol.endswith("-USD") or symbol.endswith("USDT"):
                    # Crypto order
                    sources = [
                        self.data_sources.get("binance"),
                        self.data_sources.get("polygon")
                    ]
                else:
                    # Stock/option order
                    sources = [
                        self.data_sources.get("ibkr"),
                        self.data_sources.get("polygon")
                    ]
                sources = [s for s in sources if s]
            
            # Try each source
            for source_obj in sources:
                try:
                    if hasattr(source_obj, "get_order_book"):
                        data = source_obj.get_order_book(symbol, depth)
                        if data and "bids" in data and "asks" in data:
                            # Update cache
                            self.data_cache[cache_key] = {
                                "timestamp": datetime.now(),
                                "data": data
                            }
                            self.last_update[cache_key] = datetime.now()
                            return data
                except Exception as e:
                    logger.warning(f"Error getting order book from {source_obj.__class__.__name__}: {str(e)}")
            
            # No data found
            logger.warning(f"No order book found for {symbol}")
            return {"bids": [], "asks": []}
    
    def subscribe_market_data(self, symbol: str, data_type: str, callback: Callable = None) -> bool:
        """
        Subscribe to real-time market data
        
        Args:
            symbol: Instrument symbol
            data_type: Type of data (from DataType class)
            callback: Function to call with updates
            
        Returns:
            True if subscription successful, False otherwise
        """
        # Register callback if provided
        if callback:
            self.register_data_callback(data_type, symbol, callback)
        
        # Try to subscribe with each data source
        success = False
        
        for name, source in self.data_sources.items():
            if hasattr(source, "subscribe"):
                try:
                    source_success = source.subscribe(symbol, data_type, 
                                                     lambda data: self._on_market_data(data_type, symbol, data))
                    success = success or source_success
                    if source_success:
                        logger.info(f"Subscribed to {symbol} {data_type} with {name}")
                except Exception as e:
                    logger.error(f"Error subscribing to {symbol} with {name}: {str(e)}")
        
        return success
    
    def _on_market_data(self, data_type: str, symbol: str, data: Any):
        """
        Handle incoming market data
        
        Args:
            data_type: Type of data
            symbol: Symbol
            data: New data
        """
        # Update cache
        cache_key = f"{data_type}:{symbol}"
        
        with self.lock:
            # Update cache entry
            if data_type in [DataType.STOCK_BARS, DataType.CRYPTO_BARS]:
                # For bars, append to existing dataframe
                if cache_key in self.data_cache:
                    existing_data = self.data_cache[cache_key]["data"]
                    # Append new bar if it's a new timestamp
                    if data["timestamp"] not in existing_data.index:
                        self.data_cache[cache_key]["data"] = pd.concat([
                            existing_data,
                            pd.DataFrame([data], index=[data["timestamp"]])
                        ])
                else:
                    # Create new cache entry
                    self.data_cache[cache_key] = {
                        "timestamp": datetime.now(),
                        "data": pd.DataFrame([data], index=[data["timestamp"]])
                    }
            else:
                # For other data types, just replace
                self.data_cache[cache_key] = {
                    "timestamp": datetime.now(),
                    "data": data
                }
            
            self.last_update[cache_key] = datetime.now()
        
        # Notify callbacks
        self._notify_callbacks(data_type, symbol, data)
    
    def get_liquidity_imbalance(self, symbol: str) -> float:
        """
        Calculate liquidity imbalance for a symbol
        
        Args:
            symbol: Instrument symbol
            
        Returns:
            Imbalance score (-1 to 1, positive = buy pressure)
        """
        # Get order book
        order_book = self.get_order_book(symbol)
        
        if not order_book or "bids" not in order_book or "asks" not in order_book:
            return 0.0
        
        bids = order_book["bids"]
        asks = order_book["asks"]
        
        if not bids or not asks:
            return 0.0
        
        # Calculate bid and ask liquidity
        bid_liquidity = sum(price * size for price, size in bids)
        ask_liquidity = sum(price * size for price, size in asks)
        
        total_liquidity = bid_liquidity + ask_liquidity
        if total_liquidity == 0:
            return 0.0
        
        # Calculate imbalance (-1 to 1)
        imbalance = (bid_liquidity - ask_liquidity) / total_liquidity
        return imbalance
    
    def get_option_implied_volatility(self, symbol: str, expiry: str = None, strike: float = None) -> Dict[str, Any]:
        """
        Get option implied volatility data
        
        Args:
            symbol: Underlying symbol
            expiry: Option expiry date (None = all)
            strike: Option strike price (None = all)
            
        Returns:
            Dictionary with IV data
        """
        # Get option chain
        chain = self.get_option_chain(symbol)
        
        if not chain or "expirations" not in chain:
            return {}
        
        # Filter by expiry if provided
        if expiry:
            expirations = [exp for exp in chain["expirations"] if exp["date"] == expiry]
        else:
            expirations = chain["expirations"]
        
        # Prepare result
        result = {
            "symbol": symbol,
            "timestamp": datetime.now().isoformat(),
            "expirations": []
        }
        
        for exp in expirations:
            exp_data = {
                "date": exp["date"],
                "strikes": []
            }
            
            for option in exp["options"]:
                if strike is None or abs(option["strike"] - strike) < 0.01:
                    exp_data["strikes"].append({
                        "strike": option["strike"],
                        "call_iv": option.get("call", {}).get("iv", 0),
                        "put_iv": option.get("put", {}).get("iv", 0),
                        "call_volume": option.get("call", {}).get("volume", 0),
                        "put_volume": option.get("put", {}).get("volume", 0),
                        "call_open_interest": option.get("call", {}).get("open_interest", 0),
                        "put_open_interest": option.get("put", {}).get("open_interest", 0)
                    })
            
            result["expirations"].append(exp_data)
        
        return result
    
    def save_to_cache(self, data_type: str, symbol: str, timeframe: str = None, data: Any = None):
        """
        Save data to local cache file
        
        Args:
            data_type: Type of data
            symbol: Symbol
            timeframe: Time frame (optional)
            data: Data to save (None = use current cache)
        """
        try:
            cache_key = f"{data_type}:{symbol}"
            if timeframe:
                cache_key += f":{timeframe}"
            
            with self.lock:
                if data is None:
                    if cache_key not in self.data_cache:
                        logger.warning(f"No cache data for {cache_key}")
                        return
                    data = self.data_cache[cache_key]["data"]
                
                # Create directory for symbol
                symbol_dir = os.path.join(self.data_dir, symbol)
                os.makedirs(symbol_dir, exist_ok=True)
                
                # Create filename
                date_str = datetime.now().strftime("%Y%m%d")
                filename = f"{data_type}"
                if timeframe:
                    filename += f"_{timeframe}"
                filename += f"_{date_str}.json"
                
                filepath = os.path.join(symbol_dir, filename)
                
                # Convert data to JSON-serializable format
                if isinstance(data, pd.DataFrame):
                    json_data = data.reset_index().to_json(orient="records")
                    data_to_save = json.loads(json_data)
                else:
                    data_to_save = data
                
                # Save to file
                with open(filepath, 'w') as f:
                    json.dump(data_to_save, f, indent=2)
                
                logger.debug(f"Saved {cache_key} to {filepath}")
        
        except Exception as e:
            logger.error(f"Error saving data to cache: {str(e)}")
    
    def load_from_cache(self, data_type: str, symbol: str, timeframe: str = None, date: str = None) -> Any:
        """
        Load data from local cache file
        
        Args:
            data_type: Type of data
            symbol: Symbol
            timeframe: Time frame (optional)
            date: Date string in YYYYMMDD format (None = latest)
            
        Returns:
            Loaded data
        """
        try:
            # Create directory path
            symbol_dir = os.path.join(self.data_dir, symbol)
            if not os.path.exists(symbol_dir):
                logger.warning(f"No cache directory for {symbol}")
                return None
            
            # Create filename pattern
            filename_pattern = f"{data_type}"
            if timeframe:
                filename_pattern += f"_{timeframe}"
            
            if date:
                filename_pattern += f"_{date}.json"
            else:
                filename_pattern += "_*.json"
            
            # Find matching files
            import glob
            matching_files = glob.glob(os.path.join(symbol_dir, filename_pattern))
            
            if not matching_files:
                logger.warning(f"No cache files matching {filename_pattern}")
                return None
            
            # Get the latest file
            latest_file = max(matching_files, key=os.path.getmtime)
            
            # Load data
            with open(latest_file, 'r') as f:
                data = json.load(f)
            
            # Convert to appropriate format
            if data_type in [DataType.STOCK_BARS, DataType.CRYPTO_BARS]:
                df = pd.DataFrame(data)
                if "timestamp" in df.columns:
                    df.set_index("timestamp", inplace=True)
                return df
            else:
                return data
            
            logger.debug(f"Loaded {data_type} for {symbol} from {latest_file}")
            
        except Exception as e:
            logger.error(f"Error loading data from cache: {str(e)}")
            return None

# For testing
if __name__ == "__main__":
    # Test configuration
    test_config = {
        "ibkr": {
            "enabled": True,
            "host": "127.0.0.1",
            "port": 7496,
            "client_id": 1
        },
        "polygon": {
            "enabled": True,
            "api_key": "YOUR_POLYGON_API_KEY"
        },
        "binance": {
            "enabled": True,
            "api_key": "YOUR_BINANCE_API_KEY",
            "api_secret": "YOUR_BINANCE_API_SECRET"
        }
    }
    
    # Create data hub
    hub = MarketDataHub(test_config)
    
    # Test stock data
    spy_data = hub.get_stock_data("SPY", TimeFrame.MINUTE_5, 10)
    print(f"SPY data: {len(spy_data)} bars")
    
    # Test order book
    spy_book = hub.get_order_book("SPY")
    print(f"SPY order book: {len(spy_book['bids'])} bids, {len(spy_book['asks'])} asks")
    
    # Test liquidity imbalance
    imbalance = hub.get_liquidity_imbalance("SPY")
    print(f"SPY liquidity imbalance: {imbalance}") 