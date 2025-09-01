"""
Polygon Connector

Connects to Polygon.io for stock, option, and crypto market data.
Can be used as a complement to or fallback for IBKR data.
"""

import os
import logging
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union, Callable
import json
import websocket
import requests
import pandas as pd
import numpy as np

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class PolygonConnector:
    """Connector for Polygon.io market data"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Polygon connector
        
        Args:
            config: Configuration dictionary with Polygon settings
        """
        self.config = config
        self.api_key = config.get("api_key", "")
        self.base_url = "https://api.polygon.io"
        self.ws_url = "wss://socket.polygon.io/stocks"
        self.ws_crypto_url = "wss://socket.polygon.io/crypto"
        
        # Validate API key
        if not self.api_key:
            logger.error("Polygon API key is required")
            raise ValueError("Polygon API key is required")
        
        # Connection state
        self.ws = None
        self.ws_crypto = None
        self.ws_connected = False
        self.ws_crypto_connected = False
        self.reconnect_interval = config.get("reconnect_interval", 30)
        self.subscriptions = {}
        self.callbacks = {}
        
        # Cache to avoid redundant API calls
        self.market_data_cache = {}
        self.option_chains_cache = {}
        self.websocket_lock = threading.RLock()
        
        # Start WebSocket thread if enabled
        self.running = True
        self.enable_websocket = config.get("enable_websocket", False)
        
        if self.enable_websocket:
            self.ws_thread = threading.Thread(target=self._websocket_thread, daemon=True)
            self.ws_thread.start()
        
        logger.info("Polygon connector initialized")
    
    def _websocket_thread(self):
        """Background thread that manages WebSocket connections"""
        while self.running:
            try:
                if not self.ws_connected and self.subscriptions:
                    self._connect_websocket()
                
                if not self.ws_crypto_connected and any(s.startswith("X:") for s in self.subscriptions):
                    self._connect_crypto_websocket()
                
                time.sleep(5)
            except Exception as e:
                logger.error(f"Error in WebSocket thread: {str(e)}")
                time.sleep(self.reconnect_interval)
    
    def _connect_websocket(self):
        """Connect to Polygon WebSocket for stock/option data"""
        try:
            # Close existing connection if any
            if self.ws:
                try:
                    self.ws.close()
                except:
                    pass
            
            # Define callbacks
            def on_message(ws, message):
                try:
                    data = json.loads(message)
                    self._handle_websocket_message(data)
                except Exception as e:
                    logger.error(f"Error handling WebSocket message: {str(e)}")
            
            def on_error(ws, error):
                logger.error(f"WebSocket error: {str(error)}")
                self.ws_connected = False
            
            def on_close(ws, close_status_code, close_msg):
                logger.info("WebSocket connection closed")
                self.ws_connected = False
            
            def on_open(ws):
                logger.info("WebSocket connection opened")
                self.ws_connected = True
                
                # Authenticate
                auth_message = {"action": "auth", "params": self.api_key}
                ws.send(json.dumps(auth_message))
                
                # Subscribe to tickers
                self._send_websocket_subscriptions()
            
            # Create WebSocket connection
            websocket.enableTrace(False)
            self.ws = websocket.WebSocketApp(
                self.ws_url,
                on_message=on_message,
                on_error=on_error,
                on_close=on_close,
                on_open=on_open
            )
            
            # Start WebSocket in a thread
            ws_thread = threading.Thread(target=self.ws.run_forever, daemon=True)
            ws_thread.start()
            
        except Exception as e:
            logger.error(f"Error connecting to WebSocket: {str(e)}")
            self.ws_connected = False
    
    def _connect_crypto_websocket(self):
        """Connect to Polygon WebSocket for crypto data"""
        try:
            # Close existing connection if any
            if self.ws_crypto:
                try:
                    self.ws_crypto.close()
                except:
                    pass
            
            # Define callbacks
            def on_message(ws, message):
                try:
                    data = json.loads(message)
                    self._handle_websocket_message(data, is_crypto=True)
                except Exception as e:
                    logger.error(f"Error handling Crypto WebSocket message: {str(e)}")
            
            def on_error(ws, error):
                logger.error(f"Crypto WebSocket error: {str(error)}")
                self.ws_crypto_connected = False
            
            def on_close(ws, close_status_code, close_msg):
                logger.info("Crypto WebSocket connection closed")
                self.ws_crypto_connected = False
            
            def on_open(ws):
                logger.info("Crypto WebSocket connection opened")
                self.ws_crypto_connected = True
                
                # Authenticate
                auth_message = {"action": "auth", "params": self.api_key}
                ws.send(json.dumps(auth_message))
                
                # Subscribe to crypto tickers
                self._send_crypto_websocket_subscriptions()
            
            # Create WebSocket connection
            websocket.enableTrace(False)
            self.ws_crypto = websocket.WebSocketApp(
                self.ws_crypto_url,
                on_message=on_message,
                on_error=on_error,
                on_close=on_close,
                on_open=on_open
            )
            
            # Start WebSocket in a thread
            ws_thread = threading.Thread(target=self.ws_crypto.run_forever, daemon=True)
            ws_thread.start()
            
        except Exception as e:
            logger.error(f"Error connecting to Crypto WebSocket: {str(e)}")
            self.ws_crypto_connected = False
    
    def _send_websocket_subscriptions(self):
        """Send subscription messages for all subscribed tickers"""
        if not self.ws_connected or not self.ws:
            return
        
        # Get stock/option subscriptions
        stock_subscriptions = [s for s in self.subscriptions if not s.startswith("X:")]
        if not stock_subscriptions:
            return
        
        # Group by subscription type
        subs_by_type = {}
        for symbol in stock_subscriptions:
            sub_types = self.subscriptions[symbol]
            for sub_type in sub_types:
                if sub_type not in subs_by_type:
                    subs_by_type[sub_type] = []
                subs_by_type[sub_type].append(symbol)
        
        # Send subscription messages
        for sub_type, symbols in subs_by_type.items():
            # Format subscription message based on type
            if sub_type == "trades":
                channels = [f"T.{symbol}" for symbol in symbols]
            elif sub_type == "quotes":
                channels = [f"Q.{symbol}" for symbol in symbols]
            elif sub_type == "bars":
                channels = [f"AM.{symbol}" for symbol in symbols]  # 1-minute aggregates
            else:
                continue
            
            # Send subscription
            sub_message = {
                "action": "subscribe",
                "params": ",".join(channels)
            }
            
            try:
                self.ws.send(json.dumps(sub_message))
                logger.info(f"Subscribed to {sub_type} for {len(symbols)} symbols")
            except Exception as e:
                logger.error(f"Error sending subscription: {str(e)}")
    
    def _send_crypto_websocket_subscriptions(self):
        """Send subscription messages for all subscribed crypto tickers"""
        if not self.ws_crypto_connected or not self.ws_crypto:
            return
        
        # Get crypto subscriptions
        crypto_subscriptions = [s for s in self.subscriptions if s.startswith("X:")]
        if not crypto_subscriptions:
            return
        
        # Group by subscription type
        subs_by_type = {}
        for symbol in crypto_subscriptions:
            sub_types = self.subscriptions[symbol]
            symbol_clean = symbol[2:]  # Remove 'X:' prefix
            for sub_type in sub_types:
                if sub_type not in subs_by_type:
                    subs_by_type[sub_type] = []
                subs_by_type[sub_type].append(symbol_clean)
        
        # Send subscription messages
        for sub_type, symbols in subs_by_type.items():
            # Format subscription message based on type
            if sub_type == "trades":
                channels = [f"XT.{symbol}" for symbol in symbols]
            elif sub_type == "quotes":
                channels = [f"XQ.{symbol}" for symbol in symbols]
            elif sub_type == "bars":
                channels = [f"XA.{symbol}" for symbol in symbols]  # 1-minute aggregates
            else:
                continue
            
            # Send subscription
            sub_message = {
                "action": "subscribe",
                "params": ",".join(channels)
            }
            
            try:
                self.ws_crypto.send(json.dumps(sub_message))
                logger.info(f"Subscribed to crypto {sub_type} for {len(symbols)} symbols")
            except Exception as e:
                logger.error(f"Error sending crypto subscription: {str(e)}")
    
    def _handle_websocket_message(self, data, is_crypto=False):
        """Process incoming WebSocket messages"""
        # Check if it's a status message
        if isinstance(data, dict) and 'status' in data:
            if data['status'] == 'connected':
                logger.info(f"WebSocket {'crypto ' if is_crypto else ''}connected")
            elif data['status'] == 'auth_success':
                logger.info(f"WebSocket {'crypto ' if is_crypto else ''}authenticated")
            return
        
        # Handle data messages
        if not isinstance(data, list):
            return
        
        for msg in data:
            try:
                # Extract message type and symbol
                if 'ev' not in msg or 'sym' not in msg:
                    continue
                
                event_type = msg['ev']
                symbol = msg['sym']
                
                # Add X: prefix for crypto symbols
                if is_crypto and not symbol.startswith("X:"):
                    symbol = f"X:{symbol}"
                
                # Map event type to our data types
                data_type = None
                if event_type == 'T':  # Trade
                    data_type = "trades"
                elif event_type == 'Q':  # Quote
                    data_type = "quotes"
                elif event_type == 'AM':  # Aggregate/Bar
                    data_type = "bars"
                elif event_type == 'XT':  # Crypto Trade
                    data_type = "trades"
                elif event_type == 'XQ':  # Crypto Quote
                    data_type = "quotes"
                elif event_type == 'XA':  # Crypto Aggregate/Bar
                    data_type = "bars"
                
                if not data_type:
                    continue
                
                # Format the data based on type
                formatted_data = None
                timestamp = datetime.fromtimestamp(msg.get('t', 0) / 1000.0).isoformat() if 't' in msg else datetime.now().isoformat()
                
                if data_type == "trades":
                    formatted_data = {
                        "symbol": symbol,
                        "timestamp": timestamp,
                        "price": msg.get('p', 0),
                        "size": msg.get('s', 0),
                        "exchange": msg.get('x', ''),
                        "trade_id": msg.get('i', '')
                    }
                elif data_type == "quotes":
                    formatted_data = {
                        "symbol": symbol,
                        "timestamp": timestamp,
                        "bid_price": msg.get('bp', 0),
                        "bid_size": msg.get('bs', 0),
                        "ask_price": msg.get('ap', 0),
                        "ask_size": msg.get('as', 0),
                        "exchange": msg.get('x', '')
                    }
                elif data_type == "bars":
                    formatted_data = {
                        "symbol": symbol,
                        "timestamp": timestamp,
                        "open": msg.get('o', 0),
                        "high": msg.get('h', 0),
                        "low": msg.get('l', 0),
                        "close": msg.get('c', 0),
                        "volume": msg.get('v', 0),
                        "vwap": msg.get('vw', 0)
                    }
                
                # Notify callbacks
                if formatted_data:
                    callback_key = f"{data_type}:{symbol}"
                    if callback_key in self.callbacks:
                        for callback in self.callbacks[callback_key]:
                            callback(formatted_data)
            
            except Exception as e:
                logger.error(f"Error processing WebSocket message: {str(e)}")
    
    def _make_rest_request(self, endpoint: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Make a REST API request to Polygon
        
        Args:
            endpoint: API endpoint path
            params: Query parameters
            
        Returns:
            Response data dictionary
        """
        url = f"{self.base_url}{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.api_key}"
        }
        
        try:
            response = requests.get(url, headers=headers, params=params)
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Polygon API error: {response.status_code} - {response.text}")
                return {}
                
        except Exception as e:
            logger.error(f"Error making REST request: {str(e)}")
            return {}
    
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
        # Map timeframe to Polygon timespan
        tf_map = {
            "1m": "minute",
            "5m": "minute",
            "15m": "minute",
            "30m": "minute",
            "1h": "hour",
            "4h": "hour",
            "1d": "day",
            "1w": "week"
        }
        
        # Map timeframe to Polygon multiplier
        multiplier_map = {
            "1m": 1,
            "5m": 5,
            "15m": 15,
            "30m": 30,
            "1h": 1,
            "4h": 4,
            "1d": 1,
            "1w": 1
        }
        
        if timeframe not in tf_map:
            logger.error(f"Unsupported timeframe: {timeframe}")
            return pd.DataFrame()
        
        # Determine if we're dealing with a crypto symbol
        is_crypto = symbol.startswith("X:") or "-USD" in symbol or "-USDT" in symbol
        
        # Format symbol for API
        api_symbol = symbol
        if is_crypto and not symbol.startswith("X:"):
            currency_pair = symbol.replace("-", "")
            api_symbol = f"X:{currency_pair}"
        
        # Construct API endpoint
        timespan = tf_map[timeframe]
        multiplier = multiplier_map[timeframe]
        
        # Calculate adjusted limit based on timeframe
        adjusted_limit = limit
        if timeframe in ["5m", "15m", "30m", "4h"]:
            # For aggregated timeframes, we need more 1m/1h bars
            adjusted_limit = limit * multiplier
        
        if adjusted_limit > 5000:
            adjusted_limit = 5000  # API limit
        
        endpoint = f"/v2/aggs/ticker/{api_symbol}/range/{multiplier}/{timespan}/2000-01-01/{datetime.now().strftime('%Y-%m-%d')}"
        params = {
            "limit": adjusted_limit,
            "sort": "desc"
        }
        
        # Make API request
        response = self._make_rest_request(endpoint, params)
        
        if not response or "results" not in response or not response["results"]:
            logger.warning(f"No bar data returned for {symbol}")
            return pd.DataFrame()
        
        # Convert to DataFrame
        try:
            results = response["results"]
            df = pd.DataFrame(results)
            
            # Convert timestamp to datetime
            df['timestamp'] = pd.to_datetime(df['t'], unit='ms')
            
            # Select and rename columns
            df = df.rename(columns={
                't': 'raw_timestamp',
                'o': 'open',
                'h': 'high',
                'l': 'low',
                'c': 'close',
                'v': 'volume',
                'vw': 'vwap'
            })
            
            # Set timestamp as index
            df.set_index('timestamp', inplace=True)
            
            # Sort by timestamp (ascending)
            df.sort_index(inplace=True)
            
            # For non-standard timeframes (5m, 15m, 30m, 4h), we need to resample
            if timeframe in ["5m", "15m", "30m", "4h"]:
                # Map to pandas resample rule
                resample_map = {
                    "5m": "5min",
                    "15m": "15min",
                    "30m": "30min",
                    "4h": "4H"
                }
                rule = resample_map[timeframe]
                
                # Resample to desired timeframe
                df = df.resample(rule).agg({
                    'open': 'first',
                    'high': 'max',
                    'low': 'min',
                    'close': 'last',
                    'volume': 'sum',
                    'vwap': 'mean'
                })
            
            # Limit to requested number of bars
            return df.tail(limit)
            
        except Exception as e:
            logger.error(f"Error processing bar data for {symbol}: {str(e)}")
            return pd.DataFrame()
    
    def get_crypto_bars(self, symbol: str, timeframe: str, limit: int = 100) -> pd.DataFrame:
        """
        Get cryptocurrency price bars
        
        Args:
            symbol: Crypto symbol (e.g., BTC-USD)
            timeframe: Bar duration (1m, 5m, 15m, 1h, 1d)
            limit: Maximum number of bars to return
            
        Returns:
            DataFrame with price data
        """
        # Remove "-USD" suffix if present
        if "-USD" in symbol:
            clean_symbol = symbol.replace("-USD", "")
            api_symbol = f"X:{clean_symbol}USD"
        elif "-USDT" in symbol:
            clean_symbol = symbol.replace("-USDT", "")
            api_symbol = f"X:{clean_symbol}USDT"
        else:
            api_symbol = f"X:{symbol}"
        
        # Use the generic bars method
        return self.get_bars(api_symbol, timeframe, limit)
    
    def get_option_chain(self, symbol: str) -> Dict[str, Any]:
        """
        Get full option chain for a symbol
        
        Args:
            symbol: Underlying symbol
            
        Returns:
            Dictionary with option chain data
        """
        cache_key = f"option_chain_{symbol}"
        
        # Check cache first (valid for 5 minutes)
        if cache_key in self.option_chains_cache:
            cache_entry = self.option_chains_cache[cache_key]
            age = datetime.now() - cache_entry["timestamp"]
            if age.total_seconds() < 300:  # 5 minutes
                return cache_entry["data"]
        
        try:
            # Get current stock price
            latest_quote = self._make_rest_request(f"/v2/last/trade/{symbol}")
            if not latest_quote or "results" not in latest_quote:
                logger.warning(f"Could not get latest price for {symbol}")
                return {}
            
            underlying_price = latest_quote["results"]["p"]
            
            # Get option expiry dates
            contract_path = f"/v3/reference/options/contracts"
            params = {
                "underlying_ticker": symbol,
                "limit": 1000
            }
            
            contracts_response = self._make_rest_request(contract_path, params)
            
            if not contracts_response or "results" not in contracts_response or not contracts_response["results"]:
                logger.warning(f"No option contracts found for {symbol}")
                return {}
            
            # Get unique expiry dates
            contracts = contracts_response["results"]
            expirations = sorted(list(set(contract["expiration_date"] for contract in contracts)))
            
            # Limit to first 10 expirations
            expirations = expirations[:10]
            
            # Build result structure
            result = {
                "symbol": symbol,
                "underlying_price": underlying_price,
                "timestamp": datetime.now().isoformat(),
                "expirations": []
            }
            
            # Process options for each expiration
            for exp_date in expirations:
                exp_contracts = [c for c in contracts if c["expiration_date"] == exp_date]
                
                # Group by strike price
                strikes = {}
                for contract in exp_contracts:
                    strike = contract["strike_price"]
                    if strike not in strikes:
                        strikes[strike] = {"call": None, "put": None}
                    
                    contract_type = contract["contract_type"].lower()
                    if contract_type == "call":
                        strikes[strike]["call"] = contract
                    elif contract_type == "put":
                        strikes[strike]["put"] = contract
                
                # Filter to reasonable strike range (70% to 130% of current price)
                filtered_strikes = {}
                for strike, data in strikes.items():
                    if 0.7 * underlying_price <= strike <= 1.3 * underlying_price:
                        filtered_strikes[strike] = data
                
                # Convert to sorted list
                strike_list = sorted(filtered_strikes.items(), key=lambda x: x[0])
                
                # Limit to 30 strikes around ATM
                if len(strike_list) > 30:
                    atm_idx = min(range(len(strike_list)), key=lambda i: abs(strike_list[i][0] - underlying_price))
                    start_idx = max(0, atm_idx - 15)
                    end_idx = min(len(strike_list), start_idx + 30)
                    strike_list = strike_list[start_idx:end_idx]
                
                # Format expiration entry
                exp_entry = {
                    "date": exp_date,
                    "options": []
                }
                
                # Process each strike
                for strike, contracts in strike_list:
                    # Get option details
                    call_contract = contracts["call"]
                    put_contract = contracts["put"]
                    
                    option_data = {
                        "strike": strike,
                        "call": self._get_option_data_from_contract(call_contract) if call_contract else {},
                        "put": self._get_option_data_from_contract(put_contract) if put_contract else {}
                    }
                    
                    exp_entry["options"].append(option_data)
                
                result["expirations"].append(exp_entry)
            
            # Update cache
            self.option_chains_cache[cache_key] = {
                "timestamp": datetime.now(),
                "data": result
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting option chain for {symbol}: {str(e)}")
            return {}
    
    def _get_option_data_from_contract(self, contract: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract option data from a contract record
        
        Args:
            contract: Contract data dictionary
            
        Returns:
            Formatted option data
        """
        if not contract:
            return {}
        
        try:
            # Get ticker symbol
            ticker = contract.get("ticker", "")
            
            # Try to get latest quote
            quote = self._make_rest_request(f"/v2/last/trade/{ticker}")
            
            if quote and "results" in quote:
                price = quote["results"].get("p", 0)
                size = quote["results"].get("s", 0)
            else:
                price = 0
                size = 0
            
            # Calculate implied volatility
            # This is a simplistic approach - for real IV you'd need options pricing model
            iv = contract.get("implied_volatility", 0)
            
            # Get greeks if available
            delta = contract.get("delta", 0)
            gamma = contract.get("gamma", 0)
            theta = contract.get("theta", 0)
            vega = contract.get("vega", 0)
            
            # Get open interest if available
            open_interest = contract.get("open_interest", 0)
            
            return {
                "bid": price * 0.95,  # Estimated bid
                "ask": price * 1.05,  # Estimated ask
                "last": price,
                "volume": size,
                "open_interest": open_interest,
                "iv": iv,
                "delta": delta,
                "gamma": gamma,
                "theta": theta,
                "vega": vega
            }
            
        except Exception as e:
            logger.error(f"Error processing option data: {str(e)}")
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
        try:
            # For crypto symbols, format properly
            is_crypto = symbol.startswith("X:") or "-USD" in symbol or "-USDT" in symbol
            api_symbol = symbol
            
            if is_crypto:
                if "-USD" in symbol:
                    clean_symbol = symbol.replace("-USD", "")
                    api_symbol = f"X:{clean_symbol}USD"
                elif "-USDT" in symbol:
                    clean_symbol = symbol.replace("-USDT", "")
                    api_symbol = f"X:{clean_symbol}USDT"
            
            # Get latest quote
            quote_path = f"/v2/last/nbbo/{api_symbol}"
            quote = self._make_rest_request(quote_path)
            
            if not quote or "results" not in quote or not quote["results"]:
                logger.warning(f"No quote data for {symbol}")
                return {"bids": [], "asks": []}
            
            # Simulate order book from NBBO
            # This is a limitation - Polygon doesn't provide full book depth via REST
            results = quote["results"]
            bid_price = results.get("p", 0)
            bid_size = results.get("s", 0)
            
            # Get ask from a separate quote
            ask_quote_path = f"/v2/last/trade/{api_symbol}"
            ask_quote = self._make_rest_request(ask_quote_path)
            
            if ask_quote and "results" in ask_quote and ask_quote["results"]:
                ask_results = ask_quote["results"]
                ask_price = ask_results.get("p", 0) * 1.001  # Slightly higher than last trade
                ask_size = ask_results.get("s", 0)
            else:
                ask_price = bid_price * 1.001  # Default fallback
                ask_size = bid_size
            
            # Create simulated order book with price variation
            bids = []
            asks = []
            
            # Generate bids (descending prices)
            for i in range(depth):
                price_factor = 1 - (i * 0.001)
                size_factor = 1 - (i * 0.1)
                price = bid_price * price_factor
                size = max(1, bid_size * size_factor)
                bids.append((price, size))
            
            # Generate asks (ascending prices)
            for i in range(depth):
                price_factor = 1 + (i * 0.001)
                size_factor = 1 - (i * 0.1)
                price = ask_price * price_factor
                size = max(1, ask_size * size_factor)
                asks.append((price, size))
            
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
        if not self.enable_websocket:
            logger.warning("WebSocket is not enabled, cannot subscribe")
            return False
        
        # Add to subscriptions
        with self.websocket_lock:
            if symbol not in self.subscriptions:
                self.subscriptions[symbol] = set()
            
            # Map data type to websocket channel
            if data_type == "stock_bars":
                self.subscriptions[symbol].add("bars")
            elif data_type == "stock_quotes":
                self.subscriptions[symbol].add("quotes")
            elif data_type == "stock_trades":
                self.subscriptions[symbol].add("trades")
            elif data_type == "crypto_bars":
                self.subscriptions[symbol].add("bars")
            elif data_type == "crypto_quotes":
                self.subscriptions[symbol].add("quotes")
            elif data_type == "crypto_trades":
                self.subscriptions[symbol].add("trades")
            elif data_type == "order_book":
                self.subscriptions[symbol].add("quotes")
            else:
                logger.warning(f"Unsupported data type: {data_type}")
                return False
            
            # Register callback
            callback_key = f"{data_type}:{symbol}"
            if callback_key not in self.callbacks:
                self.callbacks[callback_key] = []
            self.callbacks[callback_key].append(callback)
            
            # Update websocket subscriptions if connected
            if self.ws_connected and not symbol.startswith("X:"):
                self._send_websocket_subscriptions()
            elif self.ws_crypto_connected and symbol.startswith("X:"):
                self._send_crypto_websocket_subscriptions()
        
        return True

# For testing
if __name__ == "__main__":
    # Test configuration
    test_config = {
        "api_key": "YOUR_POLYGON_API_KEY",
        "enable_websocket": True
    }
    
    # Create connector
    connector = PolygonConnector(test_config)
    
    # Test stock data
    bars = connector.get_bars("AAPL", "1d", 5)
    print(f"AAPL bars: {len(bars)}")
    print(bars)
    
    # Test crypto data
    crypto_bars = connector.get_crypto_bars("BTC-USD", "1h", 5)
    print(f"BTC-USD bars: {len(crypto_bars)}")
    print(crypto_bars)
    
    # Test option chain
    chain = connector.get_option_chain("SPY")
    if chain and "expirations" in chain:
        print(f"SPY option chain: {len(chain['expirations'])} expirations")
        if chain["expirations"]:
            print(f"First expiration: {chain['expirations'][0]['date']}")
            print(f"Strikes: {len(chain['expirations'][0]['options'])}")
    
    # Test order book
    book = connector.get_order_book("AAPL")
    print(f"AAPL order book: {len(book['bids'])} bids, {len(book['asks'])} asks") 