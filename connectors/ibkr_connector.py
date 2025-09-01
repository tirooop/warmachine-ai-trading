"""
IBKR Connector

Connects to Interactive Brokers for real-time stock, option, and market data.
Uses ib_insync library to interact with TWS or IB Gateway.
"""

import os
import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union, Callable

import pandas as pd
import numpy as np
from ib_insync import IB, Stock, Option, Contract, Forex, CFD
from ib_insync import util as ib_util

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class IBKRConnector:
    """Connector for Interactive Brokers"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize IBKR connector
        
        Args:
            config: Configuration dictionary with IBKR settings
        """
        self.config = config
        self.host = config.get("host", "127.0.0.1")
        self.port = config.get("port", 7496)  # 7496 for TWS, 4002 for Gateway
        self.client_id = config.get("client_id", 1)
        self.timeout = config.get("timeout", 30)
        self.read_only = config.get("read_only", True)
        self.reconnect_interval = config.get("reconnect_interval", 60)
        
        # Set up IB instance
        self.ib = IB()
        self.connected = False
        self.lock = threading.RLock()
        
        # Cache to avoid redundant API calls
        self.market_data_cache = {}
        self.option_chains_cache = {}
        self.contracts_cache = {}
        
        # Start connection management thread
        self.running = True
        self.connection_thread = threading.Thread(target=self._connection_manager, daemon=True)
        self.connection_thread.start()
        
        # Try to connect
        self._connect()
        
        logger.info(f"IBKR connector initialized (connected: {self.connected})")
    
    def _connect(self) -> bool:
        """
        Connect to IBKR
        
        Returns:
            True if connected successfully, False otherwise
        """
        if self.connected:
            return True
        
        try:
            logger.info(f"Connecting to IBKR at {self.host}:{self.port} (client ID: {self.client_id})")
            self.ib.connect(
                host=self.host,
                port=self.port,
                clientId=self.client_id,
                timeout=self.timeout,
                readonly=self.read_only
            )
            self.connected = True
            logger.info("Connected to IBKR successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to IBKR: {str(e)}")
            self.connected = False
            return False
    
    def _connection_manager(self):
        """Background thread that maintains the IBKR connection"""
        while self.running:
            try:
                if not self.connected or not self.ib.isConnected():
                    logger.warning("IBKR connection lost, attempting to reconnect")
                    try:
                        if self.ib.isConnected():
                            self.ib.disconnect()
                    except:
                        pass
                    
                    self.connected = False
                    self._connect()
            except Exception as e:
                logger.error(f"Error in connection manager: {str(e)}")
            
            # Sleep before checking again
            time.sleep(10)
    
    def disconnect(self):
        """Disconnect from IBKR"""
        self.running = False
        try:
            if self.ib.isConnected():
                self.ib.disconnect()
            self.connected = False
            logger.info("Disconnected from IBKR")
        except Exception as e:
            logger.error(f"Error disconnecting from IBKR: {str(e)}")
    
    def _ensure_connected(self) -> bool:
        """
        Ensure we're connected to IBKR
        
        Returns:
            True if connected, False otherwise
        """
        if not self.connected or not self.ib.isConnected():
            return self._connect()
        return True
    
    def _create_stock_contract(self, symbol: str) -> Optional[Stock]:
        """
        Create a stock contract
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Stock contract object or None if error
        """
        cache_key = f"stock_{symbol}"
        
        with self.lock:
            if cache_key in self.contracts_cache:
                return self.contracts_cache[cache_key]
            
            try:
                contract = Stock(symbol, 'SMART', 'USD')
                self.contracts_cache[cache_key] = contract
                return contract
            except Exception as e:
                logger.error(f"Error creating stock contract for {symbol}: {str(e)}")
                return None
    
    def _create_option_contract(self, symbol: str, expiry: str, strike: float, option_type: str) -> Optional[Option]:
        """
        Create an option contract
        
        Args:
            symbol: Underlying symbol
            expiry: Expiry date (YYYYMMDD format)
            strike: Strike price
            option_type: 'C' for call, 'P' for put
            
        Returns:
            Option contract object or None if error
        """
        cache_key = f"option_{symbol}_{expiry}_{strike}_{option_type}"
        
        with self.lock:
            if cache_key in self.contracts_cache:
                return self.contracts_cache[cache_key]
            
            try:
                contract = Option(symbol, expiry, strike, option_type, 'SMART', multiplier='100', currency='USD')
                self.contracts_cache[cache_key] = contract
                return contract
            except Exception as e:
                logger.error(f"Error creating option contract: {str(e)}")
                return None
    
    def _create_forex_contract(self, symbol: str) -> Optional[Forex]:
        """
        Create a forex contract
        
        Args:
            symbol: Forex pair (e.g., 'EURUSD')
            
        Returns:
            Forex contract object or None if error
        """
        cache_key = f"forex_{symbol}"
        
        with self.lock:
            if cache_key in self.contracts_cache:
                return self.contracts_cache[cache_key]
            
            try:
                base_currency = symbol[:3]
                quote_currency = symbol[3:]
                contract = Forex(base_currency, quote_currency)
                self.contracts_cache[cache_key] = contract
                return contract
            except Exception as e:
                logger.error(f"Error creating forex contract for {symbol}: {str(e)}")
                return None
    
    def _get_contract_details(self, contract: Contract) -> List[Any]:
        """
        Get contract details from IB
        
        Args:
            contract: Contract object
            
        Returns:
            List of contract details
        """
        if not self._ensure_connected():
            return []
        
        try:
            details = self.ib.reqContractDetails(contract)
            return details
        except Exception as e:
            logger.error(f"Error getting contract details: {str(e)}")
            return []
    
    def get_bars(self, symbol: str, timeframe: str, limit: int = 100) -> pd.DataFrame:
        """
        Get historical price bars
        
        Args:
            symbol: Instrument symbol
            timeframe: Bar duration (1m, 5m, 15m, 1h, 1d)
            limit: Maximum number of bars to return
            
        Returns:
            DataFrame with price data
        """
        if not self._ensure_connected():
            return pd.DataFrame()
        
        # Map timeframe to IB duration
        tf_map = {
            "1s": "1 secs",
            "5s": "5 secs",
            "15s": "15 secs",
            "30s": "30 secs",
            "1m": "1 min",
            "3m": "3 mins",
            "5m": "5 mins",
            "15m": "15 mins",
            "30m": "30 mins",
            "1h": "1 hour",
            "4h": "4 hours",
            "1d": "1 day",
            "1w": "1 week"
        }
        
        duration = tf_map.get(timeframe, "1 min")
        
        # Calculate end time and duration
        end_time = datetime.now().replace(second=0, microsecond=0)
        duration_str = f"{limit} {duration.split(' ')[1]}"
        
        try:
            # Create contract
            if symbol.endswith('USD') and len(symbol) == 6:  # Forex pair
                contract = self._create_forex_contract(symbol)
            else:  # Stock
                contract = self._create_stock_contract(symbol)
            
            if not contract:
                logger.error(f"Failed to create contract for {symbol}")
                return pd.DataFrame()
            
            # Request historical data
            bars = self.ib.reqHistoricalData(
                contract,
                endDateTime=end_time,
                durationStr=duration_str,
                barSizeSetting=duration,
                whatToShow='MIDPOINT' if isinstance(contract, Forex) else 'TRADES',
                useRTH=True,
                formatDate=1
            )
            
            if not bars:
                logger.warning(f"No historical data returned for {symbol}")
                return pd.DataFrame()
            
            # Convert to dataframe
            df = ib_util.df(bars)
            
            # Rename columns to standard names
            df = df.rename(columns={
                'date': 'timestamp',
                'open': 'open',
                'high': 'high',
                'low': 'low',
                'close': 'close',
                'volume': 'volume'
            })
            
            # Set timestamp as index
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df.set_index('timestamp', inplace=True)
            
            # Make sure all the required columns exist
            for col in ['open', 'high', 'low', 'close', 'volume']:
                if col not in df.columns:
                    df[col] = 0
            
            return df
        
        except Exception as e:
            logger.error(f"Error getting bars for {symbol}: {str(e)}")
            return pd.DataFrame()
    
    def get_option_chain(self, symbol: str) -> Dict[str, Any]:
        """
        Get full option chain for a symbol
        
        Args:
            symbol: Underlying symbol
            
        Returns:
            Dictionary with option chain data
        """
        if not self._ensure_connected():
            return {}
        
        cache_key = f"option_chain_{symbol}"
        
        # Check cache first (valid for 1 minute)
        with self.lock:
            if cache_key in self.option_chains_cache:
                cache_entry = self.option_chains_cache[cache_key]
                age = datetime.now() - cache_entry["timestamp"]
                if age.total_seconds() < 60:
                    return cache_entry["data"]
        
        try:
            # Get contract details for the underlying
            underlying = self._create_stock_contract(symbol)
            if not underlying:
                logger.error(f"Failed to create contract for {symbol}")
                return {}
            
            # Get option chains
            opt_chain_details = self.ib.reqSecDefOptParams(
                underlying.symbol,
                '',  # exchange
                underlying.secType,
                underlying.conId
            )
            
            if not opt_chain_details:
                logger.warning(f"No option chain data for {symbol}")
                return {}
            
            # Get underlying price
            self.ib.qualifyContracts(underlying)
            ticker = self.ib.reqMktData(underlying)
            
            # Wait for market data
            end_time = time.time() + 5  # 5 second timeout
            while time.time() < end_time and not ticker.marketPrice():
                self.ib.sleep(0.1)
            
            underlying_price = ticker.marketPrice()
            if not underlying_price or underlying_price <= 0:
                underlying_price = ticker.last if ticker.last else ticker.close
            
            # Process expirations and strikes
            result = {
                "symbol": symbol,
                "underlying_price": underlying_price,
                "timestamp": datetime.now().isoformat(),
                "expirations": []
            }
            
            # We'll get a list of strikes per expiration
            for chain in opt_chain_details:
                # Get expiration dates
                for exp in chain.expirations[:10]:  # Limit to first 10 expirations
                    exp_date = exp
                    
                    # Focus on strikes near the money
                    atm_strikes = []
                    for strike in chain.strikes:
                        if 0.7 * underlying_price <= strike <= 1.3 * underlying_price:
                            atm_strikes.append(strike)
                    
                    # Limit to reasonable number of strikes
                    if len(atm_strikes) > 30:
                        atm_strikes.sort(key=lambda x: abs(x - underlying_price))
                        atm_strikes = atm_strikes[:30]
                    
                    atm_strikes.sort()
                    
                    # Set up expiration entry
                    exp_entry = {
                        "date": exp_date,
                        "options": []
                    }
                    
                    # Request option data for calls and puts at each strike
                    for strike in atm_strikes:
                        opt_data = {
                            "strike": strike,
                            "call": self._get_option_data(symbol, exp_date, strike, 'C'),
                            "put": self._get_option_data(symbol, exp_date, strike, 'P')
                        }
                        exp_entry["options"].append(opt_data)
                    
                    result["expirations"].append(exp_entry)
            
            # Update cache
            with self.lock:
                self.option_chains_cache[cache_key] = {
                    "timestamp": datetime.now(),
                    "data": result
                }
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting option chain for {symbol}: {str(e)}")
            return {}
    
    def _get_option_data(self, symbol: str, expiry: str, strike: float, option_type: str) -> Dict[str, Any]:
        """
        Get market data for a specific option
        
        Args:
            symbol: Underlying symbol
            expiry: Expiry date (YYYYMMDD format)
            strike: Strike price
            option_type: 'C' for call, 'P' for put
            
        Returns:
            Dictionary with option data
        """
        try:
            # Create option contract
            contract = self._create_option_contract(symbol, expiry, strike, option_type)
            if not contract:
                return {}
            
            # Request market data
            self.ib.qualifyContracts(contract)
            ticker = self.ib.reqMktData(contract, '', False, False)
            
            # Wait briefly for data
            end_time = time.time() + 1
            while time.time() < end_time and not ticker.modelGreeks:
                self.ib.sleep(0.1)
            
            # Extract option data
            option_data = {
                "bid": ticker.bid if hasattr(ticker, 'bid') else 0,
                "ask": ticker.ask if hasattr(ticker, 'ask') else 0,
                "last": ticker.last if hasattr(ticker, 'last') else 0,
                "volume": ticker.volume if hasattr(ticker, 'volume') else 0,
                "open_interest": ticker.openInterest if hasattr(ticker, 'openInterest') else 0,
                "iv": 0,  # Default value
                "delta": 0,
                "gamma": 0,
                "theta": 0,
                "vega": 0
            }
            
            # Add Greeks if available
            if hasattr(ticker, 'modelGreeks') and ticker.modelGreeks:
                greeks = ticker.modelGreeks
                option_data["iv"] = greeks.impliedVol if hasattr(greeks, 'impliedVol') else 0
                option_data["delta"] = greeks.delta if hasattr(greeks, 'delta') else 0
                option_data["gamma"] = greeks.gamma if hasattr(greeks, 'gamma') else 0
                option_data["theta"] = greeks.theta if hasattr(greeks, 'theta') else 0
                option_data["vega"] = greeks.vega if hasattr(greeks, 'vega') else 0
            
            return option_data
            
        except Exception as e:
            logger.error(f"Error getting option data: {str(e)}")
            return {}
    
    def get_order_book(self, symbol: str, depth: int = 10) -> Dict[str, Any]:
        """
        Get market order book
        
        Args:
            symbol: Instrument symbol
            depth: Book depth
            
        Returns:
            Dictionary with order book data
        """
        if not self._ensure_connected():
            return {"bids": [], "asks": []}
        
        try:
            # Create contract
            if symbol.endswith('USD') and len(symbol) == 6:  # Forex pair
                contract = self._create_forex_contract(symbol)
            else:  # Stock
                contract = self._create_stock_contract(symbol)
            
            if not contract:
                logger.error(f"Failed to create contract for {symbol}")
                return {"bids": [], "asks": []}
            
            # Request market data with deep book
            self.ib.qualifyContracts(contract)
            
            # First try to get deep book data
            try:
                # Clear any existing deep book callbacks
                self.ib.cancelMktDepth(contract)
                
                # Request deep book
                self.ib.reqMktDepth(contract, depth)
                
                # Wait briefly for data
                self.ib.sleep(0.5)
                
                # Get the DOM data
                dom = self.ib.domTickers().get(contract, None)
                
                if dom and dom.domBids and dom.domAsks:
                    bids = [(row.price, row.size) for row in dom.domBids]
                    asks = [(row.price, row.size) for row in dom.domAsks]
                    
                    # Clean up
                    self.ib.cancelMktDepth(contract)
                    
                    return {
                        "symbol": symbol,
                        "timestamp": datetime.now().isoformat(),
                        "bids": bids,
                        "asks": asks
                    }
            except Exception as e:
                logger.warning(f"Failed to get deep book for {symbol}, falling back to top of book: {str(e)}")
            
            # Fallback to regular market data for top of book
            ticker = self.ib.reqMktData(contract)
            
            # Wait briefly for data
            end_time = time.time() + 2
            while time.time() < end_time and ticker.bid == 0 and ticker.ask == 0:
                self.ib.sleep(0.1)
            
            # Create simplified order book
            bids = [(ticker.bid, ticker.bidSize)] if ticker.bid and ticker.bid > 0 else []
            asks = [(ticker.ask, ticker.askSize)] if ticker.ask and ticker.ask > 0 else []
            
            return {
                "symbol": symbol,
                "timestamp": datetime.now().isoformat(),
                "bids": bids,
                "asks": asks
            }
            
        except Exception as e:
            logger.error(f"Error getting order book for {symbol}: {str(e)}")
            return {"bids": [], "asks": []}
    
    def subscribe(self, symbol: str, data_type: str, callback: Callable) -> bool:
        """
        Subscribe to real-time market data
        
        Args:
            symbol: Instrument symbol
            data_type: Type of data to subscribe to
            callback: Function to call with updates
            
        Returns:
            True if subscription successful, False otherwise
        """
        if not self._ensure_connected():
            return False
        
        try:
            # Create contract
            if symbol.endswith('USD') and len(symbol) == 6:  # Forex pair
                contract = self._create_forex_contract(symbol)
            elif data_type == "option_chain":
                # For option chains, we'll subscribe to the underlying
                contract = self._create_stock_contract(symbol)
            else:  # Stock
                contract = self._create_stock_contract(symbol)
            
            if not contract:
                logger.error(f"Failed to create contract for {symbol}")
                return False
            
            # Qualify the contract
            self.ib.qualifyContracts(contract)
            
            # Set up subscription based on data type
            if data_type == "order_book":
                # Set up callback for deep book updates
                def on_dom_update(ticker):
                    if ticker.contract == contract:
                        book_data = {
                            "symbol": symbol,
                            "timestamp": datetime.now().isoformat(),
                            "bids": [(row.price, row.size) for row in ticker.domBids],
                            "asks": [(row.price, row.size) for row in ticker.domAsks]
                        }
                        callback(book_data)
                
                # Subscribe to deep book
                self.ib.reqMktDepth(contract, 10)
                self.ib.domUpdated += on_dom_update
                
                logger.info(f"Subscribed to order book for {symbol}")
                return True
                
            elif data_type == "option_chain":
                # For option chains, we need periodic polling
                # This is not ideal but IB doesn't provide streaming option chains
                
                # Set up a thread to poll option chain data
                def option_chain_poller():
                    while self.running and self.connected:
                        try:
                            chain = self.get_option_chain(symbol)
                            callback(chain)
                        except Exception as e:
                            logger.error(f"Error in option chain poller: {str(e)}")
                        
                        # Sleep before next update
                        time.sleep(60)  # Update once per minute
                
                option_thread = threading.Thread(target=option_chain_poller, daemon=True)
                option_thread.start()
                
                logger.info(f"Started option chain poller for {symbol}")
                return True
                
            else:  # Default to market data
                # Set up callback for price updates
                def on_tick_update(ticker):
                    if ticker.contract == contract:
                        tick_data = {
                            "symbol": symbol,
                            "timestamp": datetime.now().isoformat(),
                            "last": ticker.last if hasattr(ticker, 'last') else None,
                            "bid": ticker.bid if hasattr(ticker, 'bid') else None,
                            "ask": ticker.ask if hasattr(ticker, 'ask') else None,
                            "volume": ticker.volume if hasattr(ticker, 'volume') else None
                        }
                        callback(tick_data)
                
                # Subscribe to market data
                self.ib.reqMktData(contract)
                self.ib.pendingTickersEvent += on_tick_update
                
                logger.info(f"Subscribed to market data for {symbol}")
                return True
        
        except Exception as e:
            logger.error(f"Error subscribing to {symbol}: {str(e)}")
            return False

# For testing
if __name__ == "__main__":
    # Test configuration
    test_config = {
        "host": "127.0.0.1",
        "port": 7496,
        "client_id": 1
    }
    
    # Create connector
    connector = IBKRConnector(test_config)
    
    # Test connection
    if connector.connected:
        print("Connected to IBKR")
        
        # Test bars
        bars = connector.get_bars("SPY", "1d", 5)
        print(f"SPY bars: {len(bars)}")
        print(bars)
        
        # Test option chain
        chain = connector.get_option_chain("SPY")
        if chain and "expirations" in chain:
            print(f"SPY option chain: {len(chain['expirations'])} expirations")
            if chain["expirations"]:
                print(f"First expiration: {chain['expirations'][0]['date']}")
                print(f"Strikes: {len(chain['expirations'][0]['options'])}")
        
        # Test order book
        book = connector.get_order_book("SPY")
        print(f"SPY order book: {len(book['bids'])} bids, {len(book['asks'])} asks")
        
        # Clean up
        connector.disconnect()
    else:
        print("Failed to connect to IBKR") 