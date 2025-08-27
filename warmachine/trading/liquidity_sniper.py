"""
Liquidity Sniper - Whale Tracking and Order Flow Analysis

This module tracks large orders (whales) and analyzes order flow across 
multiple markets to identify high-probability trading opportunities.

Features:
- Real-time monitoring of order books across exchanges
- Detection of large orders and smart money movement
- AI-powered analysis of market microstructure
- Signals generation for automated trading
"""

import os
import logging
import time
import json
import threading
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple

# Set up logging
logger = logging.getLogger(__name__)

class LiquiditySniper:
    """Liquidity Sniper for tracking whale movements and high-frequency trading opportunities"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the Liquidity Sniper
        
        Args:
            config: Platform configuration dictionary
        """
        self.config = config
        self.trading_config = config.get("trading", {})
        self.hf_config = config.get("hf_trading", {})
        self.running = False
        
        # Initialize trackers
        self.monitored_symbols = self.config.get("market_data", {}).get("symbols", [])
        self.whale_thresholds = self._initialize_whale_thresholds()
        
        # Order flow state
        self.order_flow = {}
        self.whale_alerts = []
        
        # Data storage paths
        self.data_path = "data/market/order_flow"
        os.makedirs(self.data_path, exist_ok=True)
        
        # Alert signal path
        self.alert_path = "data/alerts"
        os.makedirs(self.alert_path, exist_ok=True)
        
        logger.info("Liquidity Sniper initialized")
        
    def run(self):
        """Start the Liquidity Sniper's main processing loop"""
        self.running = True
        logger.info("Liquidity Sniper started")
        
        try:
            while self.running:
                # Monitor order flow
                self._monitor_order_flow()
                
                # Analyze whale movements
                self._analyze_whale_movements()
                
                # Generate trading signals
                self._generate_signals()
                
                # Sleep to prevent excessive CPU usage
                time.sleep(5)  # Check every 5 seconds
                
        except Exception as e:
            logger.error(f"Liquidity Sniper encountered an error: {str(e)}")
            self.running = False
            
        logger.info("Liquidity Sniper stopped")
        
    def shutdown(self):
        """Gracefully shutdown the Liquidity Sniper"""
        logger.info("Shutting down Liquidity Sniper...")
        self.running = False
        
    def _initialize_whale_thresholds(self) -> Dict[str, float]:
        """
        Initialize whale thresholds for different symbols
        
        Returns:
            Dictionary mapping symbols to whale threshold values
        """
        # Default thresholds
        default_thresholds = {
            "SPY": 1000000,      # $1M
            "QQQ": 750000,       # $750K
            "AAPL": 500000,      # $500K
            "MSFT": 500000,      # $500K
            "GOOGL": 500000,     # $500K
            "AMZN": 500000,      # $500K
            "TSLA": 300000,      # $300K
            "BTC-USD": 1000000,  # $1M
            "ETH-USD": 500000,   # $500K
        }
        
        # Override with config if provided
        custom_thresholds = self.hf_config.get("whale_thresholds", {})
        thresholds = {**default_thresholds, **custom_thresholds}
        
        # Fill in any missing symbols with a default value
        for symbol in self.monitored_symbols:
            if symbol not in thresholds:
                thresholds[symbol] = 100000  # $100K default
                
        return thresholds
        
    def _monitor_order_flow(self):
        """Monitor order flow across different markets"""
        try:
            # In a real implementation, this would connect to exchange APIs
            # For now, generate synthetic data
            
            for symbol in self.monitored_symbols:
                # Create a timestamp for this data point
                timestamp = datetime.now().isoformat()
                
                # Synthetic order flow data
                order_flow_data = {
                    "timestamp": timestamp,
                    "symbol": symbol,
                    "bid_volume": self._generate_random_volume(),
                    "ask_volume": self._generate_random_volume(),
                    "buy_market_orders": self._generate_random_orders(),
                    "sell_market_orders": self._generate_random_orders(),
                    "large_orders": self._generate_large_orders(symbol),
                }
                
                # Store in memory
                if symbol not in self.order_flow:
                    self.order_flow[symbol] = []
                
                self.order_flow[symbol].append(order_flow_data)
                
                # Keep only the last 100 data points for each symbol
                if len(self.order_flow[symbol]) > 100:
                    self.order_flow[symbol] = self.order_flow[symbol][-100:]
                
                # Write latest data to disk
                with open(os.path.join(self.data_path, f"{symbol}_order_flow.json"), "w") as f:
                    json.dump(self.order_flow[symbol][-10:], f, indent=2)
            
            logger.debug(f"Order flow monitored for {len(self.monitored_symbols)} symbols")
                
        except Exception as e:
            logger.error(f"Order flow monitoring failed: {str(e)}")
    
    def _analyze_whale_movements(self):
        """Analyze whale movements and detect significant market activity"""
        try:
            current_time = datetime.now().isoformat()
            
            for symbol, flow_data in self.order_flow.items():
                if not flow_data:
                    continue
                    
                # Get the latest order flow data
                latest_flow = flow_data[-1]
                
                # Check for large orders
                large_orders = latest_flow.get("large_orders", [])
                
                for order in large_orders:
                    # Check if the order exceeds the whale threshold
                    if order["volume"] * order["price"] >= self.whale_thresholds.get(symbol, 100000):
                        # Create a whale alert
                        whale_alert = {
                            "timestamp": current_time,
                            "symbol": symbol,
                            "side": order["side"],
                            "volume": order["volume"],
                            "price": order["price"],
                            "value": order["volume"] * order["price"],
                            "exchange": order.get("exchange", "unknown")
                        }
                        
                        self.whale_alerts.append(whale_alert)
                        
                        # Keep only the last 100 alerts
                        if len(self.whale_alerts) > 100:
                            self.whale_alerts = self.whale_alerts[-100:]
                        
                        # Write to disk
                        alert_file = os.path.join(self.alert_path, "whale_alerts.json")
                        with open(alert_file, "w") as f:
                            json.dump(self.whale_alerts[-20:], f, indent=2)
                        
                        logger.info(f"Whale alert: {whale_alert['side']} {whale_alert['symbol']} ${whale_alert['value']:,.2f}")
            
        except Exception as e:
            logger.error(f"Whale movement analysis failed: {str(e)}")
    
    def _generate_signals(self):
        """Generate trading signals based on order flow and whale movements"""
        try:
            current_time = datetime.now().isoformat()
            signals = []
            
            for symbol, flow_data in self.order_flow.items():
                if len(flow_data) < 5:  # Need at least 5 data points
                    continue
                
                # Calculate order flow imbalance
                last_5 = flow_data[-5:]
                bid_volume = sum(point["bid_volume"] for point in last_5)
                ask_volume = sum(point["ask_volume"] for point in last_5)
                
                # Calculate imbalance percentage
                total_volume = bid_volume + ask_volume
                if total_volume > 0:
                    imbalance = (bid_volume - ask_volume) / total_volume
                else:
                    imbalance = 0
                
                # Check for significant imbalance (>20%)
                if abs(imbalance) > 0.2:
                    signal = {
                        "timestamp": current_time,
                        "symbol": symbol,
                        "signal_type": "order_flow_imbalance",
                        "direction": "buy" if imbalance > 0 else "sell",
                        "strength": abs(imbalance),
                        "details": {
                            "bid_volume": bid_volume,
                            "ask_volume": ask_volume,
                            "imbalance": imbalance
                        }
                    }
                    
                    signals.append(signal)
                    logger.info(f"Signal generated: {signal['direction']} {symbol} (imbalance: {imbalance:.2f})")
            
            # Check for correlated whale movements
            if self.whale_alerts:
                # Group alerts by symbols
                symbol_alerts = {}
                for alert in self.whale_alerts[-20:]:  # Last 20 alerts
                    symbol = alert["symbol"]
                    if symbol not in symbol_alerts:
                        symbol_alerts[symbol] = []
                    symbol_alerts[symbol].append(alert)
                
                # Check symbols with multiple alerts
                for symbol, alerts in symbol_alerts.items():
                    if len(alerts) >= 3:  # At least 3 alerts
                        # Count buys and sells
                        buys = sum(1 for a in alerts if a["side"] == "buy")
                        sells = sum(1 for a in alerts if a["side"] == "sell")
                        
                        # Check for a clear direction
                        if buys >= 3 and buys > 2 * sells:
                            signal = {
                                "timestamp": current_time,
                                "symbol": symbol,
                                "signal_type": "whale_accumulation",
                                "direction": "buy",
                                "strength": 0.8,
                                "details": {
                                    "buy_alerts": buys,
                                    "sell_alerts": sells,
                                    "total_value": sum(a["value"] for a in alerts if a["side"] == "buy")
                                }
                            }
                            signals.append(signal)
                            logger.info(f"Whale accumulation signal: BUY {symbol}")
                            
                        elif sells >= 3 and sells > 2 * buys:
                            signal = {
                                "timestamp": current_time,
                                "symbol": symbol,
                                "signal_type": "whale_distribution",
                                "direction": "sell",
                                "strength": 0.8,
                                "details": {
                                    "buy_alerts": buys,
                                    "sell_alerts": sells,
                                    "total_value": sum(a["value"] for a in alerts if a["side"] == "sell")
                                }
                            }
                            signals.append(signal)
                            logger.info(f"Whale distribution signal: SELL {symbol}")
            
            # Write signals to disk
            if signals:
                signal_file = os.path.join(self.alert_path, "hf_signals.json")
                
                # Read existing signals if the file exists
                existing_signals = []
                if os.path.exists(signal_file):
                    try:
                        with open(signal_file, "r") as f:
                            existing_signals = json.load(f)
                    except:
                        pass
                
                # Combine and keep only the last 50
                all_signals = existing_signals + signals
                if len(all_signals) > 50:
                    all_signals = all_signals[-50:]
                
                # Write back to disk
                with open(signal_file, "w") as f:
                    json.dump(all_signals, f, indent=2)
                    
        except Exception as e:
            logger.error(f"Signal generation failed: {str(e)}")
    
    def _generate_random_volume(self) -> float:
        """Generate random volume for synthetic data"""
        import random
        return random.uniform(1000, 50000)
    
    def _generate_random_orders(self) -> int:
        """Generate random number of orders for synthetic data"""
        import random
        return random.randint(10, 100)
    
    def _generate_large_orders(self, symbol: str) -> List[Dict[str, Any]]:
        """Generate synthetic large orders for testing"""
        import random
        
        # Only generate large orders occasionally
        if random.random() > 0.3:  # 30% chance
            return []
        
        # Generate 1-3 large orders
        num_orders = random.randint(1, 3)
        orders = []
        
        for _ in range(num_orders):
            # Random price based on symbol
            base_price = {
                "SPY": 450.0,
                "QQQ": 380.0,
                "AAPL": 180.0,
                "MSFT": 350.0,
                "GOOGL": 140.0,
                "AMZN": 120.0,
                "TSLA": 220.0,
                "BTC-USD": 40000.0,
                "ETH-USD": 2200.0
            }.get(symbol, 100.0)
            
            price = base_price * random.uniform(0.98, 1.02)
            
            # Random volume to sometimes exceed whale threshold
            threshold = self.whale_thresholds.get(symbol, 100000)
            volume_for_threshold = threshold / price
            
            # 10% chance of exceeding threshold
            if random.random() < 0.1:
                volume = volume_for_threshold * random.uniform(1.0, 2.0)
            else:
                volume = volume_for_threshold * random.uniform(0.1, 0.9)
            
            order = {
                "side": "buy" if random.random() > 0.5 else "sell",
                "price": price,
                "volume": volume,
                "exchange": random.choice(["NYSE", "NASDAQ", "BINANCE", "COINBASE"])
            }
            
            orders.append(order)
        
        return orders
        
    def get_latest_signals(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get the latest trading signals
        
        Args:
            limit: Maximum number of signals to return
            
        Returns:
            List of signal dictionaries
        """
        try:
            signal_file = os.path.join(self.alert_path, "hf_signals.json")
            
            if not os.path.exists(signal_file):
                return []
                
            with open(signal_file, "r") as f:
                signals = json.load(f)
                
            # Return the most recent signals
            return signals[-limit:]
            
        except Exception as e:
            logger.error(f"Failed to retrieve signals: {str(e)}")
            return []
            
    def get_whale_alerts(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get the latest whale alerts
        
        Args:
            limit: Maximum number of alerts to return
            
        Returns:
            List of whale alert dictionaries
        """
        try:
            alert_file = os.path.join(self.alert_path, "whale_alerts.json")
            
            if not os.path.exists(alert_file):
                return []
                
            with open(alert_file, "r") as f:
                alerts = json.load(f)
                
            # Return the most recent alerts
            return alerts[-limit:]
            
        except Exception as e:
            logger.error(f"Failed to retrieve whale alerts: {str(e)}")
            return [] 