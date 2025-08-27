"""
Binance Connector

Connects to Binance for cryptocurrency market data.
Handles both REST API and WebSocket connections.
"""

import os
import logging
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union, Callable
import json
import pandas as pd
import numpy as np
import hmac
import hashlib
import requests
from urllib.parse import urlencode

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class BinanceConnector:
    """Connector for Binance cryptocurrency market data"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the Binance connector
        
        Args:
            config: Configuration dictionary with Binance settings
        """
        self.config = config
        self.api_key = config.get("api_key", "")
        self.api_secret = config.get("api_secret", "")
        self.base_url = "https://api.binance.com"
        self.ws_url = "wss://stream.binance.com:9443/ws"
        
        # Optional testnet mode
        self.testnet = config.get("testnet", False)
        if self.testnet:
            self.base_url = "https://testnet.binance.vision"
            self.ws_url = "wss://testnet.binance.vision/ws"
        
        # Connection state
        self.ws = None
        self.ws_connected = False
        self.reconnect_interval = config.get("reconnect_interval", 30)
        self.subscriptions = {}
        self.callbacks = {}
        
        # Cache to avoid redundant API calls
        self.market_data_cache = {}
        self.websocket_lock = threading.RLock()
        self.stream_id = 1
        
        # Start WebSocket thread if enabled
        self.running = True
        self.enable_websocket = config.get("enable_websocket", True)
        
        if self.enable_websocket:
            self.ws_thread = threading.Thread(target=self._websocket_thread, daemon=True)
            self.ws_thread.start()
        
        logger.info("Binance connector initialized")
    
    def _generate_signature(self, query_string: str) -> str:
        """
        Generate HMAC SHA256 signature for API authentication
        
        Args:
            query_string: Query parameters as string
            
        Returns:
            Signature string
        """
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    def _make_rest_request(self, endpoint: str, method: str = "GET", 
                           params: Dict[str, Any] = None, signed: bool = False) -> Dict[str, Any]:
        """
        Make a REST API request to Binance
        
        Args:
            endpoint: API endpoint path
            method: HTTP method (GET, POST, DELETE)
            params: Query parameters
            signed: Whether the request requires signing
            
        Returns:
            Response data dictionary
        """
        url = f"{self.base_url}{endpoint}"
        headers = {
            "X-MBX-APIKEY": self.api_key
        }
        
        if params is None:
            params = {}
        
        if signed:
            # Add timestamp for signed endpoints
            params['timestamp'] = int(time.time() * 1000)
            query_string = urlencode(params)
            params['signature'] = self._generate_signature(query_string)
        
        try:
            if method == "GET":
                response = requests.get(url, headers=headers, params=params)
            elif method == "POST":
                response = requests.post(url, headers=headers, params=params)
            elif method == "DELETE":
                response = requests.delete(url, headers=headers, params=params)
            else:
                logger.error(f"Unsupported HTTP method: {method}")
                return {}
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Binance API error: {response.status_code} - {response.text}")
                return {}
                
        except Exception as e:
            logger.error(f"Error making REST request: {str(e)}")
            return {}
    
    def _websocket_thread(self):
        """Background thread that manages WebSocket connections"""
        import websocket
        
        while self.running:
            try:
                if self.subscriptions and not self.ws_connected:
                    self._connect_websocket()
                
                time.sleep(5)
            except Exception as e:
                logger.error(f"Error in WebSocket thread: {str(e)}")
                time.sleep(self.reconnect_interval)
    
    def _connect_websocket(self):
        """Connect to Binance WebSocket"""
        import websocket
        
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
                
                # Subscribe to active subscriptions
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
    
    def _send_websocket_subscriptions(self):
        """Send subscription messages for all subscribed streams"""
        if not self.ws_connected or not self.ws:
            return
        
        try:
            # Get all active subscriptions
            streams = []
            with self.websocket_lock:
                for symbol, sub_types in self.subscriptions.items():
                    symbol_lower = symbol.lower()
                    # Remove -USD or -USDT suffix if present
                    if "-USD" in symbol_lower:
                        symbol_lower = symbol_lower.replace("-usd", "usdt")
                    elif "-USDT" in symbol_lower:
                        symbol_lower = symbol_lower.replace("-usdt", "usdt")
                    
                    # Add streams based on subscription types
                    for sub_type in sub_types:
                        if sub_type == "kline":
                            timeframes = self.subscriptions.get(f"{symbol}:timeframes", ["1m"])
                            for timeframe in timeframes:
                                # Convert timeframe to Binance format
                                interval = self._convert_timeframe_to_binance(timeframe)
                                streams.append(f"{symbol_lower}@kline_{interval}")
                        elif sub_type == "ticker":
                            streams.append(f"{symbol_lower}@ticker")
                        elif sub_type == "depth":
                            streams.append(f"{symbol_lower}@depth20@100ms")
                        elif sub_type == "trade":
                            streams.append(f"{symbol_lower}@trade")
            
            # Create subscription message
            if streams:
                sub_id = self.stream_id
                self.stream_id += 1
                
                sub_message = {
                    "method": "SUBSCRIBE",
                    "params": streams,
                    "id": sub_id
                }
                
                # Send subscription
                self.ws.send(json.dumps(sub_message))
                logger.info(f"Subscribed to {len(streams)} Binance streams")
        
        except Exception as e:
            logger.error(f"Error sending WebSocket subscriptions: {str(e)}")
    
    def _handle_websocket_message(self, data: Dict[str, Any]):
        """
        Process incoming WebSocket messages
        
        Args:
            data: WebSocket message data
        """
        # Check if this is a subscription confirmation
        if "id" in data and "result" in data:
            logger.debug(f"Subscription confirmed: {data}")
            return
        
        try:
            # Handle different stream types
            if "e" in data:
                event_type = data["e"]
                
                # Kline/Candlestick event
                if event_type == "kline":
                    self._handle_kline_event(data)
                
                # 24hr Ticker event
                elif event_type == "24hrTicker":
                    self._handle_ticker_event(data)
                
                # Trade event
                elif event_type == "trade":
                    self._handle_trade_event(data)
            
            # Handle depth update (order book)
            elif "lastUpdateId" in data and "bids" in data and "asks" in data:
                self._handle_depth_event(data)
                
        except Exception as e:
            logger.error(f"Error processing WebSocket message: {str(e)}")
    
    def _handle_kline_event(self, data: Dict[str, Any]):
        """Handle kline/candlestick event"""
        try:
            symbol = data["s"]
            kline = data["k"]
            
            # Extract data
            timeframe = self._convert_binance_to_timeframe(kline["i"])
            is_closed = kline["x"]
            
            if is_closed:
                kline_data = {
                    "symbol": symbol,
                    "timestamp": datetime.fromtimestamp(kline["t"] / 1000).isoformat(),
                    "open": float(kline["o"]),
                    "high": float(kline["h"]),
                    "low": float(kline["l"]),
                    "close": float(kline["c"]),
                    "volume": float(kline["v"]),
                    "timeframe": timeframe,
                    "closed": is_closed
                }
                
                # Notify callbacks
                callback_key = f"kline:{symbol}:{timeframe}"
                if callback_key in self.callbacks:
                    for callback in self.callbacks[callback_key]:
                        callback(kline_data)
        
        except Exception as e:
            logger.error(f"Error handling kline event: {str(e)}")
    
    def _handle_ticker_event(self, data: Dict[str, Any]):
        """Handle 24hr ticker event"""
        try:
            symbol = data["s"]
            
            ticker_data = {
                "symbol": symbol,
                "timestamp": datetime.fromtimestamp(data["E"] / 1000).isoformat(),
                "price": float(data["c"]),
                "price_change": float(data["p"]),
                "price_change_percent": float(data["P"]),
                "volume": float(data["v"]),
                "high": float(data["h"]),
                "low": float(data["l"]),
                "open": float(data["o"])
            }
            
            # Notify callbacks
            callback_key = f"ticker:{symbol}"
            if callback_key in self.callbacks:
                for callback in self.callbacks[callback_key]:
                    callback(ticker_data)
        
        except Exception as e:
            logger.error(f"Error handling ticker event: {str(e)}")
    
    def _handle_trade_event(self, data: Dict[str, Any]):
        """Handle trade event"""
        try:
            symbol = data["s"]
            
            trade_data = {
                "symbol": symbol,
                "timestamp": datetime.fromtimestamp(data["T"] / 1000).isoformat(),
                "price": float(data["p"]),
                "size": float(data["q"]),
                "trade_id": data["t"],
                "is_buyer_maker": data["m"]
            }
            
            # Notify callbacks
            callback_key = f"trade:{symbol}"
            if callback_key in self.callbacks:
                for callback in self.callbacks[callback_key]:
                    callback(trade_data)
        
        except Exception as e:
            logger.error(f"Error handling trade event: {str(e)}")
    
    def _handle_depth_event(self, data: Dict[str, Any]):
        """Handle depth (order book) event"""
        try:
            # Extract symbol from stream name
            if "stream" in data:
                stream = data["stream"]
                symbol = stream.split("@")[0].upper()
                if symbol.endswith("USDT"):
                    base = symbol[:-4]
                    symbol = f"{base}-USDT"
            else:
                # Use placeholder if we can't determine the symbol
                symbol = "UNKNOWN"
            
            bids = [[float(price), float(qty)] for price, qty in data["bids"]]
            asks = [[float(price), float(qty)] for price, qty in data["asks"]]
            
            depth_data = {
                "symbol": symbol,
                "timestamp": datetime.now().isoformat(),
                "bids": bids,
                "asks": asks,
                "last_update_id": data["lastUpdateId"]
            }
            
            # Format for order book
            formatted_bids = [(float(price), float(qty)) for price, qty in data["bids"]]
            formatted_asks = [(float(price), float(qty)) for price, qty in data["asks"]]
            
            order_book_data = {
                "symbol": symbol,
                "timestamp": datetime.now().isoformat(),
                "bids": formatted_bids,
                "asks": formatted_asks
            }
            
            # Notify callbacks
            callback_key = f"depth:{symbol}"
            if callback_key in self.callbacks:
                for callback in self.callbacks[callback_key]:
                    callback(depth_data)
            
            # Also notify order_book callbacks
            callback_key = f"order_book:{symbol}"
            if callback_key in self.callbacks:
                for callback in self.callbacks[callback_key]:
                    callback(order_book_data)
        
        except Exception as e:
            logger.error(f"Error handling depth event: {str(e)}")
    
    def _convert_timeframe_to_binance(self, timeframe: str) -> str:
        """
        Convert standard timeframe to Binance interval format
        
        Args:
            timeframe: Timeframe string (e.g., "1m", "1h", "1d")
            
        Returns:
            Binance interval format
        """
        # Binance uses the same format for most timeframes
        return timeframe
    
    def _convert_binance_to_timeframe(self, interval: str) -> str:
        """
        Convert Binance interval to standard timeframe format
        
        Args:
            interval: Binance interval (e.g., "1m", "1h", "1d")
            
        Returns:
            Standard timeframe format
        """
        # Binance uses the same format for most timeframes
        return interval
    
    def get_exchange_info(self) -> Dict[str, Any]:
        """
        Get exchange information
        
        Returns:
            Exchange information
        """
        return self._make_rest_request("/api/v3/exchangeInfo")
    
    def get_symbol_info(self, symbol: str) -> Dict[str, Any]:
        """
        Get information for a specific symbol
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Symbol information
        """
        exchange_info = self.get_exchange_info()
        
        if "symbols" in exchange_info:
            symbol_formatted = self._format_symbol_for_api(symbol)
            for symbol_info in exchange_info["symbols"]:
                if symbol_info["symbol"] == symbol_formatted:
                    return symbol_info
        
        return {}
    
    def _format_symbol_for_api(self, symbol: str) -> str:
        """
        Format a symbol for Binance API
        
        Args:
            symbol: Symbol string (e.g., "BTC-USDT", "ETH-USD")
            
        Returns:
            Formatted symbol for Binance API
        """
        # Convert formats like BTC-USDT to BTCUSDT
        if "-" in symbol:
            parts = symbol.split("-")
            if parts[1] == "USD":
                return f"{parts[0]}USDT"
            return f"{parts[0]}{parts[1]}"
        
        return symbol
    
    def get_ticker(self, symbol: str) -> Dict[str, Any]:
        """
        Get 24hr price ticker
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Ticker data
        """
        symbol_formatted = self._format_symbol_for_api(symbol)
        return self._make_rest_request("/api/v3/ticker/24hr", params={"symbol": symbol_formatted})
    
    def get_recent_trades(self, symbol: str, limit: int = 500) -> List[Dict[str, Any]]:
        """
        Get recent trades
        
        Args:
            symbol: Trading symbol
            limit: Number of trades to return (max 1000)
            
        Returns:
            List of recent trades
        """
        symbol_formatted = self._format_symbol_for_api(symbol)
        result = self._make_rest_request("/api/v3/trades", params={
            "symbol": symbol_formatted,
            "limit": min(limit, 1000)
        })
        return result if isinstance(result, list) else []
    
    def get_order_book(self, symbol: str, limit: int = 100) -> Dict[str, Any]:
        """
        Get order book (market depth)
        
        Args:
            symbol: Trading symbol
            limit: Depth of the order book (max 5000)
            
        Returns:
            Order book data
        """
        # Binance limits: 5, 10, 20, 50, 100, 500, 1000, 5000
        valid_limits = [5, 10, 20, 50, 100, 500, 1000, 5000]
        
        # Find closest valid limit
        actual_limit = min(valid_limits, key=lambda x: abs(x - limit))
        
        symbol_formatted = self._format_symbol_for_api(symbol)
        result = self._make_rest_request("/api/v3/depth", params={
            "symbol": symbol_formatted,
            "limit": actual_limit
        })
        
        if not result or "bids" not in result or "asks" not in result:
            logger.warning(f"Failed to get order book for {symbol}")
            return {"bids": [], "asks": []}
        
        # Format response
        try:
            formatted_bids = [(float(price), float(qty)) for price, qty in result["bids"]]
            formatted_asks = [(float(price), float(qty)) for price, qty in result["asks"]]
            
            return {
                "symbol": symbol,
                "timestamp": datetime.now().isoformat(),
                "bids": formatted_bids,
                "asks": formatted_asks
            }
        except Exception as e:
            logger.error(f"Error formatting order book: {str(e)}")
            return {"bids": [], "asks": []}
    
    def get_klines(self, symbol: str, interval: str, limit: int = 500,
                  start_time: Optional[int] = None, end_time: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get klines/candlestick data
        
        Args:
            symbol: Trading symbol
            interval: Time interval (1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d, 3d, 1w, 1M)
            limit: Number of candles to return (max 1000)
            start_time: Start time in milliseconds
            end_time: End time in milliseconds
            
        Returns:
            List of kline data
        """
        symbol_formatted = self._format_symbol_for_api(symbol)
        params = {
            "symbol": symbol_formatted,
            "interval": interval,
            "limit": min(limit, 1000)
        }
        
        if start_time:
            params["startTime"] = start_time
        
        if end_time:
            params["endTime"] = end_time
        
        result = self._make_rest_request("/api/v3/klines", params=params)
        
        if not isinstance(result, list):
            logger.warning(f"Failed to get klines for {symbol}")
            return []
        
        # Format response
        formatted_klines = []
        for kline in result:
            formatted_klines.append({
                "timestamp": datetime.fromtimestamp(kline[0] / 1000).isoformat(),
                "open": float(kline[1]),
                "high": float(kline[2]),
                "low": float(kline[3]),
                "close": float(kline[4]),
                "volume": float(kline[5]),
                "close_time": datetime.fromtimestamp(kline[6] / 1000).isoformat(),
                "quote_volume": float(kline[7]),
                "trades": int(kline[8]),
                "taker_buy_base_volume": float(kline[9]),
                "taker_buy_quote_volume": float(kline[10])
            })
        
        return formatted_klines
    
    def get_bars(self, symbol: str, timeframe: str, limit: int = 100) -> pd.DataFrame:
        """
        Get historical price bars as a DataFrame
        
        Args:
            symbol: Trading symbol
            timeframe: Bar duration (1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d, 3d, 1w, 1M)
            limit: Maximum number of bars to return
            
        Returns:
            DataFrame with price data
        """
        klines = self.get_klines(symbol, timeframe, limit)
        
        if not klines:
            logger.warning(f"No kline data for {symbol}")
            return pd.DataFrame()
        
        # Convert to DataFrame
        df = pd.DataFrame(klines)
        
        # Set timestamp as index
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            df.set_index("timestamp", inplace=True)
            df.sort_index(inplace=True)
        
        return df
    
    def subscribe(self, symbol: str, data_type: str, callback: Callable, timeframe: str = "1m") -> bool:
        """
        Subscribe to market data stream
        
        Args:
            symbol: Trading symbol
            data_type: Type of data to subscribe to (kline, ticker, depth, trade)
            callback: Function to call with data updates
            timeframe: Timeframe for kline data
            
        Returns:
            True if subscription was successful
        """
        if not self.enable_websocket:
            logger.warning("WebSocket is not enabled, cannot subscribe")
            return False
        
        try:
            with self.websocket_lock:
                # Add to subscriptions
                if symbol not in self.subscriptions:
                    self.subscriptions[symbol] = set()
                
                # Map data type
                ws_data_type = data_type
                if data_type == "crypto_bars":
                    ws_data_type = "kline"
                    # Store timeframe information
                    timeframe_key = f"{symbol}:timeframes"
                    if timeframe_key not in self.subscriptions:
                        self.subscriptions[timeframe_key] = []
                    self.subscriptions[timeframe_key].append(timeframe)
                elif data_type == "crypto_quotes":
                    ws_data_type = "ticker"
                elif data_type == "crypto_trades":
                    ws_data_type = "trade"
                elif data_type == "order_book":
                    ws_data_type = "depth"
                
                self.subscriptions[symbol].add(ws_data_type)
                
                # Add callback
                callback_key = f"{ws_data_type}:{symbol}"
                if ws_data_type == "kline":
                    callback_key = f"{ws_data_type}:{symbol}:{timeframe}"
                
                if callback_key not in self.callbacks:
                    self.callbacks[callback_key] = []
                
                self.callbacks[callback_key].append(callback)
                
                # Update websocket subscriptions if connected
                if self.ws_connected:
                    self._send_websocket_subscriptions()
                
                return True
        
        except Exception as e:
            logger.error(f"Error subscribing to {data_type} for {symbol}: {str(e)}")
            return False
    
    def unsubscribe(self, symbol: str, data_type: str, callback: Optional[Callable] = None, timeframe: str = "1m") -> bool:
        """
        Unsubscribe from market data stream
        
        Args:
            symbol: Trading symbol
            data_type: Type of data to unsubscribe from
            callback: Specific callback to remove (or None to remove all)
            timeframe: Timeframe for kline data
            
        Returns:
            True if unsubscription was successful
        """
        try:
            with self.websocket_lock:
                # Map data type
                ws_data_type = data_type
                if data_type == "crypto_bars":
                    ws_data_type = "kline"
                    # Remove timeframe information
                    timeframe_key = f"{symbol}:timeframes"
                    if timeframe_key in self.subscriptions:
                        if timeframe in self.subscriptions[timeframe_key]:
                            self.subscriptions[timeframe_key].remove(timeframe)
                elif data_type == "crypto_quotes":
                    ws_data_type = "ticker"
                elif data_type == "crypto_trades":
                    ws_data_type = "trade"
                elif data_type == "order_book":
                    ws_data_type = "depth"
                
                # Remove callback
                callback_key = f"{ws_data_type}:{symbol}"
                if ws_data_type == "kline":
                    callback_key = f"{ws_data_type}:{symbol}:{timeframe}"
                
                if callback_key in self.callbacks:
                    if callback:
                        if callback in self.callbacks[callback_key]:
                            self.callbacks[callback_key].remove(callback)
                    else:
                        self.callbacks[callback_key] = []
                    
                    # If no more callbacks, remove subscription
                    if not self.callbacks[callback_key]:
                        if symbol in self.subscriptions:
                            if ws_data_type in self.subscriptions[symbol]:
                                self.subscriptions[symbol].remove(ws_data_type)
                            
                            # If no more subscriptions for this symbol, remove it
                            if not self.subscriptions[symbol]:
                                del self.subscriptions[symbol]
                
                return True
        
        except Exception as e:
            logger.error(f"Error unsubscribing from {data_type} for {symbol}: {str(e)}")
            return False
    
    def stop(self):
        """Stop the connector and all background threads"""
        logger.info("Stopping Binance connector")
        self.running = False
        
        # Close WebSocket connection
        if self.ws:
            try:
                self.ws.close()
            except:
                pass
            self.ws = None

# For testing
if __name__ == "__main__":
    # Test configuration
    test_config = {
        "api_key": "YOUR_API_KEY",
        "api_secret": "YOUR_API_SECRET",
        "enable_websocket": True
    }
    
    # Create connector
    connector = BinanceConnector(test_config)
    
    # Test exchange info
    info = connector.get_exchange_info()
    print(f"Exchange info symbols: {len(info.get('symbols', []))}")
    
    # Test ticker
    ticker = connector.get_ticker("BTC-USDT")
    print(f"BTC-USDT price: {ticker.get('lastPrice', 'N/A')}")
    
    # Test order book
    book = connector.get_order_book("BTC-USDT", 10)
    print(f"Order book: {len(book['bids'])} bids, {len(book['asks'])} asks")
    
    # Test klines
    bars = connector.get_bars("BTC-USDT", "1h", 10)
    print(f"Retrieved {len(bars)} bars")
    print(bars)
    
    # Sleep to keep the script running for WebSocket tests
    try:
        print("Press Ctrl+C to exit")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        connector.stop()
        print("Stopped.") 