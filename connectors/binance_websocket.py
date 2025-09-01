"""
Binance WebSocket Connector

High-performance WebSocket connection to Binance for real-time market data:
- Trades
- Order book updates
- Kline/candlestick data
- Ticker information

Uses asyncio for parallel processing and efficient data handling.
"""

import json
import logging
import asyncio
import websockets
import time
from typing import Dict, List, Any, Optional, Set, Callable
from datetime import datetime
import hmac
import hashlib
import urllib.parse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class RealTimeBuffer:
    """Fast, thread-safe buffer for real-time market data"""
    
    def __init__(self, size: int = 100000):
        """Initialize buffer with given size"""
        self.size = size
        self.buffer = [None] * size
        self.head = 0
        self.tail = 0
        self.count = 0
        self.lock = asyncio.Lock()
    
    async def push(self, item: Any):
        """Add item to buffer"""
        async with self.lock:
            self.buffer[self.head] = item
            self.head = (self.head + 1) % self.size
            
            if self.count < self.size:
                self.count += 1
            else:
                self.tail = (self.tail + 1) % self.size
    
    async def get_latest(self, n: int = 1) -> List[Any]:
        """Get the latest n items from buffer"""
        async with self.lock:
            if self.count == 0:
                return []
            
            items = []
            n = min(n, self.count)
            
            for i in range(n):
                idx = (self.head - i - 1) % self.size
                items.append(self.buffer[idx])
            
            return items
    
    async def get_all(self) -> List[Any]:
        """Get all items in buffer"""
        async with self.lock:
            if self.count == 0:
                return []
            
            items = []
            for i in range(self.count):
                idx = (self.tail + i) % self.size
                items.append(self.buffer[idx])
            
            return items

class BinanceWebSocketClient:
    """Binance WebSocket client for real-time market data"""
    
    BASE_STREAM_URL = "wss://stream.binance.com:9443/ws"
    BASE_API_URL = "https://api.binance.com"
    
    def __init__(self, api_key: str = "", api_secret: str = "", 
                 buffer_size: int = 100000, reconnect_interval: int = 30):
        """
        Initialize Binance WebSocket client
        
        Args:
            api_key: Binance API key
            api_secret: Binance API secret
            buffer_size: Size of data buffer
            reconnect_interval: Reconnection interval in seconds
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.reconnect_interval = reconnect_interval
        
        # Data buffers for different data types
        self.trade_buffer = RealTimeBuffer(buffer_size)
        self.kline_buffer = RealTimeBuffer(buffer_size)
        self.depth_buffer = RealTimeBuffer(buffer_size)
        self.ticker_buffer = RealTimeBuffer(buffer_size)
        
        # Track active connections
        self.connections = {}
        self.active_streams = set()
        
        # Track symbols being monitored
        self.symbols = set()
        
        # Callbacks for different data types
        self.callbacks = {
            "trade": [],
            "kline": [],
            "depth": [],
            "ticker": []
        }
        
        # Control flag
        self.running = True
        
    async def _create_signature(self, params: Dict[str, Any]) -> str:
        """Create HMAC SHA256 signature for API request"""
        query_string = urllib.parse.urlencode(params)
        signature = hmac.new(
            self.api_secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    async def connect(self, symbols: List[str], channels: List[str] = None):
        """
        Connect to Binance WebSocket for specific symbols and channels
        
        Args:
            symbols: List of trading symbols
            channels: List of channels to subscribe to (default: trade, kline, depth, ticker)
        """
        if not channels:
            channels = ["trade", "kline_1m", "depth20", "ticker"]
        
        try:
            # Convert symbols to lowercase (Binance format)
            symbols = [s.lower() for s in symbols]
            self.symbols.update(symbols)
            
            # Create stream names
            streams = []
            for symbol in symbols:
                for channel in channels:
                    if channel.startswith("kline_"):
                        interval = channel.split("_")[1]
                        stream = f"{symbol}@kline_{interval}"
                    else:
                        stream = f"{symbol}@{channel}"
                    
                    streams.append(stream)
                    self.active_streams.add(stream)
            
            # Create stream URL
            stream_url = f"{self.BASE_STREAM_URL}/{''.join(streams)}" if len(streams) == 1 else f"{self.BASE_STREAM_URL}"
            
            # Start connection
            asyncio.create_task(self._maintain_connection(stream_url, streams))
            
            logger.info(f"Connected to Binance WebSocket for symbols: {', '.join(symbols)}")
            
        except Exception as e:
            logger.error(f"Error connecting to Binance WebSocket: {str(e)}")
    
    async def _maintain_connection(self, url: str, streams: List[str]):
        """
        Maintain WebSocket connection with automatic reconnection
        
        Args:
            url: WebSocket URL
            streams: List of stream names
        """
        connection_id = f"{url}_{time.time()}"
        self.connections[connection_id] = {"active": True, "last_message": time.time()}
        
        while self.running and self.connections[connection_id]["active"]:
            try:
                async with websockets.connect(url) as websocket:
                    # Subscribe to multiple streams
                    if len(streams) > 1:
                        subscribe_msg = {
                            "method": "SUBSCRIBE",
                            "params": streams,
                            "id": int(time.time())
                        }
                        await websocket.send(json.dumps(subscribe_msg))
                    
                    # Process messages
                    while self.running and self.connections[connection_id]["active"]:
                        try:
                            message = await asyncio.wait_for(websocket.recv(), timeout=30)
                            await self._process_message(json.loads(message))
                            self.connections[connection_id]["last_message"] = time.time()
                        except asyncio.TimeoutError:
                            # Send ping to keep connection alive
                            pong = await websocket.ping()
                            try:
                                await asyncio.wait_for(pong, timeout=10)
                            except asyncio.TimeoutError:
                                # Connection lost
                                logger.warning(f"Binance WebSocket ping timeout, reconnecting...")
                                break
                        except Exception as e:
                            logger.error(f"Error processing WebSocket message: {str(e)}")
                            await asyncio.sleep(1)
            
            except Exception as e:
                logger.error(f"Binance WebSocket connection error: {str(e)}")
            
            # Reconnect after delay
            logger.info(f"Reconnecting to Binance WebSocket in {self.reconnect_interval} seconds...")
            await asyncio.sleep(self.reconnect_interval)
    
    async def _process_message(self, message: Dict[str, Any]):
        """
        Process WebSocket message
        
        Args:
            message: Message dictionary
        """
        try:
            # Handle different types of messages
            if "e" in message:
                event_type = message["e"]
                
                if event_type == "trade":
                    # Trade event
                    await self.trade_buffer.push(message)
                    await self._call_callbacks("trade", message)
                    
                elif event_type == "kline":
                    # Kline/candlestick event
                    await self.kline_buffer.push(message)
                    await self._call_callbacks("kline", message)
                    
                elif event_type == "depthUpdate":
                    # Order book update
                    await self.depth_buffer.push(message)
                    await self._call_callbacks("depth", message)
                    
                elif event_type == "24hrTicker":
                    # 24-hour ticker
                    await self.ticker_buffer.push(message)
                    await self._call_callbacks("ticker", message)
        
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
    
    async def _call_callbacks(self, event_type: str, data: Dict[str, Any]):
        """
        Call registered callbacks for event type
        
        Args:
            event_type: Event type
            data: Event data
        """
        for callback in self.callbacks.get(event_type, []):
            try:
                await callback(data)
            except Exception as e:
                logger.error(f"Error in {event_type} callback: {str(e)}")
    
    def add_callback(self, event_type: str, callback: Callable):
        """
        Add callback for event type
        
        Args:
            event_type: Event type (trade, kline, depth, ticker)
            callback: Async callback function
        """
        if event_type in self.callbacks:
            self.callbacks[event_type].append(callback)
    
    async def get_trades(self, symbol: str = None, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get latest trades
        
        Args:
            symbol: Symbol filter (optional)
            limit: Maximum number of trades to return
            
        Returns:
            List of trade events
        """
        trades = await self.trade_buffer.get_latest(limit)
        
        if symbol:
            symbol = symbol.lower()
            return [t for t in trades if t.get("s", "").lower() == symbol]
        
        return trades
    
    async def get_klines(self, symbol: str = None, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get latest klines/candlesticks
        
        Args:
            symbol: Symbol filter (optional)
            limit: Maximum number of klines to return
            
        Returns:
            List of kline events
        """
        klines = await self.kline_buffer.get_latest(limit)
        
        if symbol:
            symbol = symbol.lower()
            return [k for k in klines if k.get("s", "").lower() == symbol]
        
        return klines
    
    async def get_order_book(self, symbol: str) -> Dict[str, Any]:
        """
        Get latest order book
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Latest order book state
        """
        symbol = symbol.lower()
        book_updates = await self.depth_buffer.get_latest(100)
        filtered = [b for b in book_updates if b.get("s", "").lower() == symbol]
        
        if filtered:
            return filtered[0]
        
        return None
    
    async def close_connections(self):
        """Close all WebSocket connections"""
        self.running = False
        
        for conn_id in self.connections:
            self.connections[conn_id]["active"] = False
        
        logger.info("Binance WebSocket connections closed")

class EnhancedDataFeed:
    """Enhanced data feed combining multiple exchange data sources"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize enhanced data feed
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.symbols = config.get("symbols", ["BTC-USDT", "ETH-USDT", "SPY", "QQQ", "NVDA"])
        self.buffer = RealTimeBuffer(config.get("buffer_size", 100000))
        
        # Exchange clients
        self.binance_client = None
        self.ibkr_client = None
        self.bybit_client = None
        
        # Initialize Binance client if configured
        binance_config = config.get("binance", {})
        if binance_config.get("enabled", False):
            self.binance_client = BinanceWebSocketClient(
                api_key=binance_config.get("api_key", ""),
                api_secret=binance_config.get("api_secret", ""),
                buffer_size=config.get("buffer_size", 100000),
                reconnect_interval=binance_config.get("reconnect_interval", 30)
            )
        
        # Event handlers
        self.handlers = []
        
        # Running flag
        self.running = True
    
    async def start(self):
        """Start data feed connections"""
        # Start Binance connection if available
        if self.binance_client:
            crypto_symbols = [s for s in self.symbols if '-' in s]
            binance_symbols = [s.replace('-', '') for s in crypto_symbols]
            
            if binance_symbols:
                # Connect to Binance WebSocket
                await self.binance_client.connect(
                    symbols=binance_symbols,
                    channels=["trade", "kline_1m", "depth20", "ticker"]
                )
                
                # Register callbacks
                self.binance_client.add_callback("trade", self._handle_binance_trade)
                self.binance_client.add_callback("depth", self._handle_binance_depth)
                self.binance_client.add_callback("kline", self._handle_binance_kline)
    
    async def _handle_binance_trade(self, trade_data: Dict[str, Any]):
        """Handle Binance trade data"""
        # Standardize trade data
        symbol = trade_data.get("s", "").upper()
        if "-" not in symbol:
            if symbol.endswith("USDT"):
                base = symbol[:-4]
                symbol = f"{base}-USDT"
        
        standardized = {
            "timestamp": trade_data.get("T", int(time.time() * 1000)),
            "exchange": "BINANCE",
            "symbol": symbol,
            "price": float(trade_data.get("p", 0)),
            "quantity": float(trade_data.get("q", 0)),
            "side": "BUY" if trade_data.get("m", False) else "SELL",
            "trade_id": str(trade_data.get("t", "")),
            "raw_data": trade_data
        }
        
        # Push to buffer
        await self.buffer.push(standardized)
        
        # Call handlers
        for handler in self.handlers:
            try:
                await handler(standardized)
            except Exception as e:
                logger.error(f"Error in trade handler: {str(e)}")
    
    async def _handle_binance_depth(self, depth_data: Dict[str, Any]):
        """Handle Binance order book data"""
        # Standardize order book data
        symbol = depth_data.get("s", "").upper()
        if "-" not in symbol:
            if symbol.endswith("USDT"):
                base = symbol[:-4]
                symbol = f"{base}-USDT"
        
        bids = depth_data.get("b", [])
        asks = depth_data.get("a", [])
        
        standardized = {
            "timestamp": depth_data.get("E", int(time.time() * 1000)),
            "exchange": "BINANCE",
            "symbol": symbol,
            "bids": [[float(price), float(qty)] for price, qty in bids],
            "asks": [[float(price), float(qty)] for price, qty in asks],
            "raw_data": depth_data
        }
        
        # Push to specific order book buffer
        # (implement separate buffer for order books if needed)
        
        # Call handlers
        for handler in self.handlers:
            try:
                await handler(standardized)
            except Exception as e:
                logger.error(f"Error in depth handler: {str(e)}")
    
    async def _handle_binance_kline(self, kline_data: Dict[str, Any]):
        """Handle Binance kline/candlestick data"""
        # Standardize kline data
        symbol = kline_data.get("s", "").upper()
        if "-" not in symbol:
            if symbol.endswith("USDT"):
                base = symbol[:-4]
                symbol = f"{base}-USDT"
        
        k = kline_data.get("k", {})
        
        standardized = {
            "timestamp": kline_data.get("E", int(time.time() * 1000)),
            "exchange": "BINANCE",
            "symbol": symbol,
            "interval": k.get("i", "1m"),
            "open_time": k.get("t", 0),
            "close_time": k.get("T", 0),
            "open": float(k.get("o", 0)),
            "high": float(k.get("h", 0)),
            "low": float(k.get("l", 0)),
            "close": float(k.get("c", 0)),
            "volume": float(k.get("v", 0)),
            "is_closed": k.get("x", False),
            "raw_data": kline_data
        }
        
        # Push to buffer
        await self.buffer.push(standardized)
        
        # Call handlers
        for handler in self.handlers:
            try:
                await handler(standardized)
            except Exception as e:
                logger.error(f"Error in kline handler: {str(e)}")
    
    def add_handler(self, handler: Callable):
        """Add data handler"""
        self.handlers.append(handler)
    
    async def get_latest_data(self, symbol: str = None, count: int = 100) -> List[Dict[str, Any]]:
        """Get latest data from buffer"""
        data = await self.buffer.get_latest(count)
        
        if symbol:
            return [d for d in data if d.get("symbol") == symbol]
        
        return data
    
    async def stop(self):
        """Stop data feed"""
        self.running = False
        
        # Close Binance connection
        if self.binance_client:
            await self.binance_client.close_connections()
        
        logger.info("Enhanced data feed stopped")

# For testing
if __name__ == "__main__":
    import asyncio
    
    async def print_handler(data):
        print(f"Received: {json.dumps(data, indent=2)}")
    
    async def main():
        # Config
        config = {
            "binance": {
                "enabled": True,
                "api_key": "",
                "api_secret": ""
            },
            "symbols": ["BTC-USDT", "ETH-USDT"],
            "buffer_size": 1000
        }
        
        # Create data feed
        data_feed = EnhancedDataFeed(config)
        data_feed.add_handler(print_handler)
        
        # Start data feed
        await data_feed.start()
        
        print("Data feed started. Press Ctrl+C to stop.")
        
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            await data_feed.stop()
            print("Data feed stopped.")
    
    # Run main
    asyncio.run(main()) 