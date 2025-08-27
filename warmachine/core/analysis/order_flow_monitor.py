"""
Order Flow Monitor

Advanced order flow analytics for detecting liquidity anomalies:
- Dynamic entropy calculation for orderbook imbalance
- VWAP deviation tracking
- High-frequency bid/ask imbalance detection
- Iceberg order detection
- Aggressive market order analysis
"""

import math
import logging
import time
import asyncio
import json
from typing import Dict, List, Any, Optional, Set, Callable
from datetime import datetime
import numpy as np
import pandas as pd

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class OrderFlowMonitor:
    """Monitors order flow for anomalies and liquidity patterns"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Order Flow Monitor
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.symbols = config.get("symbols", [])
        self.running = True
        
        # Thresholds
        self.entropy_threshold = config.get("entropy_threshold", 0.5)
        self.imbalance_threshold = config.get("imbalance_threshold", 0.3)
        self.volume_spike_threshold = config.get("volume_spike_threshold", 1.5)
        self.vwap_deviation_threshold = config.get("vwap_deviation_threshold", 0.002)
        
        # Alert handlers
        self.alert_handlers = []
        
        # State data
        self.orderbooks = {}  # Latest orderbooks by symbol
        self.trade_history = {}  # Recent trades by symbol
        self.volume_history = {}  # Volume history by symbol
        self.vwap_history = {}  # VWAP history by symbol
        self.last_alert_time = {}  # Last alert time by symbol/alert type
        
        # Throttling
        self.min_alert_interval = config.get("min_alert_interval", 60)  # seconds
        
        logger.info("Order Flow Monitor initialized")
    
    def add_orderbook(self, symbol: str, orderbook: Dict[str, Any]):
        """
        Add orderbook update for monitoring
        
        Args:
            symbol: Trading symbol
            orderbook: Order book data dictionary
        """
        # Store orderbook
        self.orderbooks[symbol] = {
            "timestamp": orderbook.get("timestamp", int(time.time() * 1000)),
            "bids": orderbook.get("bids", []),
            "asks": orderbook.get("asks", []),
            "exchange": orderbook.get("exchange", ""),
            "raw_data": orderbook.get("raw_data", {})
        }
        
        # Calculate metrics
        self._calculate_orderbook_metrics(symbol)
    
    def add_trade(self, symbol: str, trade: Dict[str, Any]):
        """
        Add trade for monitoring
        
        Args:
            symbol: Trading symbol
            trade: Trade data dictionary
        """
        # Initialize trade history for symbol if needed
        if symbol not in self.trade_history:
            self.trade_history[symbol] = []
        
        # Add trade to history
        self.trade_history[symbol].append({
            "timestamp": trade.get("timestamp", int(time.time() * 1000)),
            "price": trade.get("price", 0),
            "quantity": trade.get("quantity", 0),
            "side": trade.get("side", ""),
            "exchange": trade.get("exchange", ""),
            "trade_id": trade.get("trade_id", ""),
        })
        
        # Keep only recent trades (last 1000)
        if len(self.trade_history[symbol]) > 1000:
            self.trade_history[symbol] = self.trade_history[symbol][-1000:]
        
        # Calculate trade metrics
        self._calculate_trade_metrics(symbol)
    
    def _calculate_orderbook_metrics(self, symbol: str):
        """
        Calculate orderbook metrics and detect anomalies
        
        Args:
            symbol: Trading symbol
        """
        if symbol not in self.orderbooks:
            return
        
        orderbook = self.orderbooks[symbol]
        bids = orderbook.get("bids", [])
        asks = orderbook.get("asks", [])
        
        if not bids or not asks:
            return
        
        try:
            # Calculate liquidity entropy
            entropy = self.calculate_liquidity_entropy(bids, asks)
            
            # Check for anomalies
            if entropy > self.entropy_threshold:
                self._create_alert(
                    symbol=symbol,
                    alert_type="entropy_anomaly",
                    title=f"Orderbook Entropy Anomaly for {symbol}",
                    content=f"Unusual order book imbalance detected. Entropy: {entropy:.4f}",
                    level="medium",
                    data={
                        "entropy": entropy,
                        "threshold": self.entropy_threshold,
                        "timestamp": orderbook.get("timestamp", 0)
                    }
                )
            
            # Check book depth imbalance
            book_depth_imbalance = self._calculate_book_depth_imbalance(bids, asks)
            if abs(book_depth_imbalance) > self.imbalance_threshold:
                direction = "buy" if book_depth_imbalance > 0 else "sell"
                self._create_alert(
                    symbol=symbol,
                    alert_type="depth_imbalance",
                    title=f"Orderbook Depth Imbalance for {symbol}",
                    content=f"Significant {direction} pressure detected. Imbalance: {book_depth_imbalance:.4f}",
                    level="medium" if abs(book_depth_imbalance) > self.imbalance_threshold * 1.5 else "low",
                    data={
                        "imbalance": book_depth_imbalance,
                        "threshold": self.imbalance_threshold,
                        "direction": direction,
                        "timestamp": orderbook.get("timestamp", 0)
                    }
                )
            
            # Check for large orders (potential walls)
            self._detect_large_orders(symbol, bids, asks)
            
        except Exception as e:
            logger.error(f"Error calculating orderbook metrics for {symbol}: {str(e)}")
    
    def _calculate_trade_metrics(self, symbol: str):
        """
        Calculate trade metrics and detect anomalies
        
        Args:
            symbol: Trading symbol
        """
        if symbol not in self.trade_history or len(self.trade_history[symbol]) < 10:
            return
        
        try:
            # Get recent trades
            recent_trades = self.trade_history[symbol][-100:]
            
            # Initialize volume history if needed
            if symbol not in self.volume_history:
                self.volume_history[symbol] = []
            
            # Calculate volume in last minute
            current_time = int(time.time() * 1000)
            one_minute_ago = current_time - 60000
            
            minute_volume = sum(
                trade["quantity"] for trade in recent_trades 
                if trade["timestamp"] >= one_minute_ago
            )
            
            # Add to volume history
            self.volume_history[symbol].append({
                "timestamp": current_time,
                "volume": minute_volume
            })
            
            # Keep only recent history (last 60 minutes)
            if len(self.volume_history[symbol]) > 60:
                self.volume_history[symbol] = self.volume_history[symbol][-60:]
            
            # Check for volume spike
            if len(self.volume_history[symbol]) > 5:
                avg_volume = sum(v["volume"] for v in self.volume_history[symbol][-6:-1]) / 5
                if avg_volume > 0 and minute_volume > avg_volume * self.volume_spike_threshold:
                    self._create_alert(
                        symbol=symbol,
                        alert_type="volume_spike",
                        title=f"Volume Spike for {symbol}",
                        content=f"Unusual trading volume detected. Current: {minute_volume:.2f}, Avg: {avg_volume:.2f}",
                        level="high",
                        data={
                            "current_volume": minute_volume,
                            "avg_volume": avg_volume,
                            "increase_pct": (minute_volume - avg_volume) / avg_volume * 100,
                            "timestamp": current_time
                        }
                    )
            
            # Calculate VWAP
            vwap = self._calculate_vwap(recent_trades)
            
            # Initialize VWAP history if needed
            if symbol not in self.vwap_history:
                self.vwap_history[symbol] = []
            
            # Add to VWAP history
            self.vwap_history[symbol].append({
                "timestamp": current_time,
                "vwap": vwap
            })
            
            # Keep only recent history
            if len(self.vwap_history[symbol]) > 100:
                self.vwap_history[symbol] = self.vwap_history[symbol][-100:]
            
            # Check for price deviation from VWAP
            if len(recent_trades) > 0 and len(self.vwap_history[symbol]) > 1:
                latest_price = recent_trades[-1]["price"]
                
                # Get recent VWAP
                recent_vwap = self.vwap_history[symbol][-2]["vwap"]
                
                if recent_vwap > 0:
                    deviation = abs(latest_price - recent_vwap) / recent_vwap
                    
                    if deviation > self.vwap_deviation_threshold:
                        direction = "above" if latest_price > recent_vwap else "below"
                        self._create_alert(
                            symbol=symbol,
                            alert_type="vwap_deviation",
                            title=f"Price-VWAP Deviation for {symbol}",
                            content=f"Price significantly {direction} VWAP. Deviation: {deviation:.2%}",
                            level="medium",
                            data={
                                "price": latest_price,
                                "vwap": recent_vwap,
                                "deviation": deviation,
                                "direction": direction,
                                "timestamp": current_time
                            }
                        )
            
            # Check for aggressive orders (large market orders)
            self._detect_aggressive_orders(symbol, recent_trades)
            
        except Exception as e:
            logger.error(f"Error calculating trade metrics for {symbol}: {str(e)}")
    
    def calculate_liquidity_entropy(self, bids: List[List[float]], asks: List[List[float]]) -> float:
        """
        Calculate liquidity entropy (order book imbalance measure)
        
        Args:
            bids: List of bid [price, quantity] pairs
            asks: List of ask [price, quantity] pairs
            
        Returns:
            Entropy value
        """
        # Calculate total volume on each side
        bid_volume = sum(qty for _, qty in bids)
        ask_volume = sum(qty for _, qty in asks)
        
        # Avoid division by zero
        if bid_volume == 0 or ask_volume == 0:
            return 0
        
        # Calculate entropy as log ratio
        return abs(math.log(bid_volume / ask_volume))
    
    def _calculate_book_depth_imbalance(self, bids: List[List[float]], asks: List[List[float]]) -> float:
        """
        Calculate order book depth imbalance
        
        Args:
            bids: List of bid [price, quantity] pairs
            asks: List of ask [price, quantity] pairs
            
        Returns:
            Imbalance ratio (-1 to 1, positive = buy pressure)
        """
        # Calculate total volume on each side
        bid_volume = sum(qty for _, qty in bids)
        ask_volume = sum(qty for _, qty in asks)
        
        total_volume = bid_volume + ask_volume
        
        # Avoid division by zero
        if total_volume == 0:
            return 0
        
        # Calculate imbalance (-1 to 1, positive = buy pressure)
        return (bid_volume - ask_volume) / total_volume
    
    def _calculate_vwap(self, trades: List[Dict[str, Any]]) -> float:
        """
        Calculate Volume-Weighted Average Price
        
        Args:
            trades: List of trade dictionaries
            
        Returns:
            VWAP value
        """
        if not trades:
            return 0
        
        volume_sum = sum(trade["quantity"] for trade in trades)
        
        if volume_sum == 0:
            return 0
        
        weighted_sum = sum(trade["price"] * trade["quantity"] for trade in trades)
        
        return weighted_sum / volume_sum
    
    def _detect_large_orders(self, symbol: str, bids: List[List[float]], asks: List[List[float]]):
        """
        Detect unusually large orders in the book
        
        Args:
            symbol: Trading symbol
            bids: List of bid [price, quantity] pairs
            asks: List of ask [price, quantity] pairs
        """
        if not bids or not asks:
            return
        
        # Calculate average order size
        avg_bid_size = sum(qty for _, qty in bids) / len(bids) if bids else 0
        avg_ask_size = sum(qty for _, qty in asks) / len(asks) if asks else 0
        
        # Threshold for large order detection
        large_bid_threshold = avg_bid_size * 5
        large_ask_threshold = avg_ask_size * 5
        
        # Find large bids
        large_bids = [(price, qty) for price, qty in bids if qty > large_bid_threshold]
        
        # Find large asks
        large_asks = [(price, qty) for price, qty in asks if qty > large_ask_threshold]
        
        # Generate alerts for large orders
        if large_bids:
            largest_bid = max(large_bids, key=lambda x: x[1])
            self._create_alert(
                symbol=symbol,
                alert_type="large_bid",
                title=f"Large Buy Order for {symbol}",
                content=f"Large buy order detected at ${largest_bid[0]:.2f} for {largest_bid[1]:.4f} units",
                level="medium",
                data={
                    "price": largest_bid[0],
                    "quantity": largest_bid[1],
                    "avg_size": avg_bid_size,
                    "timestamp": int(time.time() * 1000)
                }
            )
        
        if large_asks:
            largest_ask = max(large_asks, key=lambda x: x[1])
            self._create_alert(
                symbol=symbol,
                alert_type="large_ask",
                title=f"Large Sell Order for {symbol}",
                content=f"Large sell order detected at ${largest_ask[0]:.2f} for {largest_ask[1]:.4f} units",
                level="medium",
                data={
                    "price": largest_ask[0],
                    "quantity": largest_ask[1],
                    "avg_size": avg_ask_size,
                    "timestamp": int(time.time() * 1000)
                }
            )
    
    def _detect_aggressive_orders(self, symbol: str, trades: List[Dict[str, Any]]):
        """
        Detect aggressive market orders
        
        Args:
            symbol: Trading symbol
            trades: List of recent trades
        """
        if not trades or len(trades) < 10:
            return
        
        # Calculate average trade size
        avg_trade_size = sum(trade["quantity"] for trade in trades) / len(trades)
        
        # Threshold for aggressive order
        aggressive_threshold = avg_trade_size * 3
        
        # Find aggressive trades
        aggressive_trades = [
            trade for trade in trades[-10:] 
            if trade["quantity"] > aggressive_threshold
        ]
        
        if aggressive_trades:
            # Get largest aggressive trade
            largest_trade = max(aggressive_trades, key=lambda x: x["quantity"])
            
            self._create_alert(
                symbol=symbol,
                alert_type="aggressive_order",
                title=f"Aggressive {largest_trade['side']} for {symbol}",
                content=f"Large {largest_trade['side'].lower()} market order: {largest_trade['quantity']:.4f} units at ${largest_trade['price']:.2f}",
                level="high",
                data={
                    "price": largest_trade["price"],
                    "quantity": largest_trade["quantity"],
                    "side": largest_trade["side"],
                    "avg_size": avg_trade_size,
                    "timestamp": largest_trade["timestamp"]
                }
            )
    
    def _create_alert(self, symbol: str, alert_type: str, title: str, content: str, level: str = "medium", data: Dict[str, Any] = None):
        """
        Create an alert and notify handlers
        
        Args:
            symbol: Trading symbol
            alert_type: Alert type identifier
            title: Alert title
            content: Alert content
            level: Alert level (low, medium, high)
            data: Additional data dictionary
        """
        # Check if alert should be throttled
        alert_key = f"{symbol}:{alert_type}"
        current_time = time.time()
        
        if alert_key in self.last_alert_time:
            time_since_last = current_time - self.last_alert_time[alert_key]
            if time_since_last < self.min_alert_interval:
                # Skip alert due to throttling
                return
        
        # Update last alert time
        self.last_alert_time[alert_key] = current_time
        
        # Create alert object
        alert = {
            "symbol": symbol,
            "type": alert_type,
            "title": title,
            "content": content,
            "level": level,
            "timestamp": int(current_time * 1000),
            "data": data or {}
        }
        
        # Notify handlers
        for handler in self.alert_handlers:
            try:
                handler(alert)
            except Exception as e:
                logger.error(f"Error in alert handler: {str(e)}")
    
    def add_alert_handler(self, handler: Callable):
        """
        Add alert handler function
        
        Args:
            handler: Handler function that takes an alert dictionary
        """
        self.alert_handlers.append(handler)
    
    def stop(self):
        """Stop order flow monitor"""
        self.running = False
        logger.info("Order Flow Monitor stopped")

    async def start(self):
        """Async start method for compatibility with system startup."""
        pass

# For testing
if __name__ == "__main__":
    # Test config
    config = {
        "symbols": ["BTC-USDT", "ETH-USDT", "SPY"],
        "entropy_threshold": 0.5,
        "imbalance_threshold": 0.3,
        "volume_spike_threshold": 1.5,
        "vwap_deviation_threshold": 0.002,
        "min_alert_interval": 10
    }
    
    # Create monitor
    monitor = OrderFlowMonitor(config)
    
    # Add test alert handler
    def alert_handler(alert):
        print(f"ALERT: {alert['title']}")
        print(f"  {alert['content']}")
        print(f"  Level: {alert['level']}")
        print(f"  Data: {json.dumps(alert['data'], indent=2)}")
        print()
    
    monitor.add_alert_handler(alert_handler)
    
    # Test with synthetic data
    symbol = "BTC-USDT"
    
    # Add test orderbook
    orderbook = {
        "timestamp": int(time.time() * 1000),
        "bids": [[19500.0, 2.5], [19450.0, 3.0], [19400.0, 5.0]],
        "asks": [[19550.0, 1.0], [19600.0, 0.5], [19650.0, 0.3]],
        "exchange": "BINANCE"
    }
    
    monitor.add_orderbook(symbol, orderbook)
    
    # Add test trades
    for i in range(20):
        # Normal trade
        trade = {
            "timestamp": int(time.time() * 1000) - i * 1000,
            "price": 19500.0 + (i % 5) * 10,
            "quantity": 0.1 + (i % 3) * 0.05,
            "side": "BUY" if i % 2 == 0 else "SELL",
            "exchange": "BINANCE",
            "trade_id": f"test-{i}"
        }
        
        monitor.add_trade(symbol, trade)
    
    # Add aggressive trade
    large_trade = {
        "timestamp": int(time.time() * 1000),
        "price": 19520.0,
        "quantity": 5.0,  # Much larger than average
        "side": "BUY",
        "exchange": "BINANCE",
        "trade_id": "test-large"
    }
    
    monitor.add_trade(symbol, large_trade)
    
    # Add imbalanced orderbook
    imbalanced_orderbook = {
        "timestamp": int(time.time() * 1000),
        "bids": [[19500.0, 10.0], [19450.0, 15.0], [19400.0, 20.0]],  # Large bids
        "asks": [[19550.0, 0.5], [19600.0, 0.7], [19650.0, 0.3]],     # Small asks
        "exchange": "BINANCE"
    }
    
    monitor.add_orderbook(symbol, imbalanced_orderbook)
    
    print("Test completed") 