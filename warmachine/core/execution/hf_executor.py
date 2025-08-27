#!/usr/bin/env python
"""
WarMachine AI Option Trader - High-Frequency Execution Module
Optimized with asyncio + uvloop for microsecond-level performance
"""

import os
import sys
import json
import time
import logging
import asyncio
import signal
import threading
import traceback
from typing import Dict, List, Optional, Union, Any
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import numpy as np
from collections import deque

# Setup platform-specific event loop policy
try:
    import uvloop
    asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    HAS_UVLOOP = True
except ImportError:
    HAS_UVLOOP = False
    logging.warning("uvloop not available, falling back to standard asyncio")

import aiohttp
from aiohttp import ClientSession, ClientTimeout, TCPConnector

logger = logging.getLogger(__name__)

class OrderPriority:
    CRITICAL = 0  # Immediate execution required
    HIGH = 1      # High priority order
    MEDIUM = 2    # Normal priority order
    LOW = 3       # Low priority order
    SCHEDULED = 4 # Scheduled order

class OrderStatus:
    PENDING = "pending"
    SUBMITTED = "submitted"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"

class OrderQueue:
    """Priority queue for order processing"""
    
    def __init__(self, max_size: int = 1000):
        """Initialize the queue"""
        self.max_size = max_size
        self.queues = {
            OrderPriority.CRITICAL: deque(maxlen=max_size),
            OrderPriority.HIGH: deque(maxlen=max_size),
            OrderPriority.MEDIUM: deque(maxlen=max_size),
            OrderPriority.LOW: deque(maxlen=max_size),
            OrderPriority.SCHEDULED: deque(maxlen=max_size)
        }
        self.stats = {
            "total_orders": 0,
            "processed_orders": 0,
            "avg_wait_time": 0.0,
            "max_wait_time": 0.0
        }
    
    def put(self, order: Dict[str, Any]):
        """Add order to queue"""
        priority = order.get("priority", OrderPriority.MEDIUM)
        order["timestamp"] = time.time()
        self.queues[priority].append(order)
        self.stats["total_orders"] += 1
    
    def get(self) -> Optional[Dict[str, Any]]:
        """Get next order from queue"""
        for priority in range(OrderPriority.CRITICAL, OrderPriority.SCHEDULED + 1):
            if self.queues[priority]:
                order = self.queues[priority].popleft()
                wait_time = time.time() - order["timestamp"]
                self.stats["processed_orders"] += 1
                self.stats["avg_wait_time"] = (
                    (self.stats["avg_wait_time"] * (self.stats["processed_orders"] - 1) + wait_time) /
                    self.stats["processed_orders"]
                )
                self.stats["max_wait_time"] = max(self.stats["max_wait_time"], wait_time)
                return order
        return None
    
    def get_stats(self) -> Dict[str, Any]:
        """Get queue statistics"""
        return {
            "total_orders": self.stats["total_orders"],
            "processed_orders": self.stats["processed_orders"],
            "avg_wait_time": self.stats["avg_wait_time"],
            "max_wait_time": self.stats["max_wait_time"],
            "queue_sizes": {p: len(q) for p, q in self.queues.items()}
        }

class HighFrequencyExecutor:
    """Advanced high-frequency order execution system"""
    
    def __init__(self, config: Dict[str, Any], notification_system: Any):
        """Initialize the executor"""
        self.config = config.get("execution", {})
        self.notification_system = notification_system
        
        # Execution settings
        self.max_order_size = self.config.get("max_order_size", 1000)
        self.min_order_size = self.config.get("min_order_size", 1)
        self.max_position_size = self.config.get("max_position_size", 10000)
        self.max_daily_loss = self.config.get("max_daily_loss", 1000)
        self.max_leverage = self.config.get("max_leverage", 2.0)
        
        # Order queue
        self.order_queue = OrderQueue()
        
        # Exchange connections
        self.exchanges = {}
        self.exchange_weights = self.config.get("exchange_weights", {
            "binance": 0.4,
            "coinbase": 0.3,
            "kraken": 0.3
        })
        
        # Risk management
        self.positions = defaultdict(float)
        self.daily_pnl = defaultdict(float)
        self.order_history = defaultdict(list)
        self.risk_limits = self.config.get("risk_limits", {
            "max_drawdown": 0.1,
            "max_daily_trades": 100,
            "max_slippage": 0.001
        })
        
        # Performance metrics
        self.metrics = {
            "total_orders": 0,
            "successful_orders": 0,
            "failed_orders": 0,
            "avg_execution_time": 0.0,
            "max_execution_time": 0.0,
            "total_commission": 0.0,
            "total_slippage": 0.0
        }
        
        # Initialize components
        self._initialize_components()
        
        logger.info("High-Frequency Executor initialized")
    
    def _initialize_components(self):
        """Initialize execution components"""
        try:
            # Initialize exchange connections
            self._init_exchange_connections()
            
            # Initialize risk management
            self._init_risk_management()
            
            # Initialize performance monitoring
            self._init_performance_monitoring()
            
        except Exception as e:
            logger.error(f"Error initializing components: {str(e)}")
    
    async def submit_order(self, 
                          symbol: str,
                          side: str,
                          quantity: float,
                          order_type: str = "market",
                          price: Optional[float] = None,
                          priority: int = OrderPriority.MEDIUM,
                          metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Submit an order for execution
        
        Args:
            symbol: Trading symbol
            side: Order side (buy/sell)
            quantity: Order quantity
            order_type: Order type (market/limit)
            price: Order price (required for limit orders)
            priority: Order priority
            metadata: Additional order metadata
            
        Returns:
            Order submission result
        """
        try:
            # Validate order
            if not self._validate_order(symbol, side, quantity, order_type, price):
                return {
                    "status": "rejected",
                    "error": "Order validation failed"
                }
            
            # Check risk limits
            if not self._check_risk_limits(symbol, side, quantity, price):
                return {
                    "status": "rejected",
                    "error": "Risk limits exceeded"
                }
            
            # Prepare order
            order = {
                "symbol": symbol,
                "side": side,
                "quantity": quantity,
                "type": order_type,
                "price": price,
                "priority": priority,
                "metadata": metadata or {},
                "timestamp": datetime.now().isoformat()
            }
            
            # Add to queue
            self.order_queue.put(order)
            
            # Start order processor if not running
            if not hasattr(self, "_processor_task") or self._processor_task.done():
                self._processor_task = asyncio.create_task(self._order_processor())
            
            return {
                "status": "submitted",
                "order": order
            }
            
        except Exception as e:
            logger.error(f"Error submitting order: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def _validate_order(self, 
                       symbol: str,
                       side: str,
                       quantity: float,
                       order_type: str,
                       price: Optional[float]) -> bool:
        """Validate order parameters"""
        try:
            # Check quantity
            if quantity < self.min_order_size or quantity > self.max_order_size:
                logger.warning(f"Invalid order quantity: {quantity}")
                return False
            
            # Check price for limit orders
            if order_type == "limit" and (price is None or price <= 0):
                logger.warning("Invalid price for limit order")
                return False
            
            # Check position size
            current_position = self.positions.get(symbol, 0)
            new_position = current_position + (quantity if side == "buy" else -quantity)
            if abs(new_position) > self.max_position_size:
                logger.warning(f"Position size limit exceeded: {new_position}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating order: {str(e)}")
            return False
    
    def _check_risk_limits(self,
                          symbol: str,
                          side: str,
                          quantity: float,
                          price: Optional[float]) -> bool:
        """Check risk management limits"""
        try:
            # Check daily loss limit
            if self.daily_pnl[symbol] <= -self.max_daily_loss:
                logger.warning(f"Daily loss limit exceeded for {symbol}")
                return False
            
            # Check daily trade limit
            if len(self.order_history[symbol]) >= self.risk_limits["max_daily_trades"]:
                logger.warning(f"Daily trade limit exceeded for {symbol}")
                return False
            
            # Check leverage
            if price:
                position_value = abs(self.positions.get(symbol, 0)) * price
                order_value = quantity * price
                if position_value > 0:
                    leverage = (position_value + order_value) / position_value
                    if leverage > self.max_leverage:
                        logger.warning(f"Leverage limit exceeded: {leverage}")
                        return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking risk limits: {str(e)}")
            return False
    
    async def _order_processor(self):
        """Process orders from the queue"""
        try:
            while True:
                # Get next order
                order = self.order_queue.get()
                if not order:
                    await asyncio.sleep(0.001)
                    continue
                
                # Process order
                start_time = time.time()
                try:
                    result = await self._execute_order(order)
                    
                    # Update metrics
                    execution_time = time.time() - start_time
                    self.metrics["total_orders"] += 1
                    self.metrics["avg_execution_time"] = (
                        (self.metrics["avg_execution_time"] * (self.metrics["total_orders"] - 1) + execution_time) /
                        self.metrics["total_orders"]
                    )
                    self.metrics["max_execution_time"] = max(
                        self.metrics["max_execution_time"],
                        execution_time
                    )
                    
                    if result["status"] == "filled":
                        self.metrics["successful_orders"] += 1
                        self._update_position(order["symbol"], order["side"], order["quantity"])
                        self._update_pnl(order["symbol"], result.get("pnl", 0))
                    else:
                        self.metrics["failed_orders"] += 1
                    
                    # Send notification
                    await self._send_order_notification(order, result)
                    
                except Exception as e:
                    logger.error(f"Error processing order: {str(e)}")
                    self.metrics["failed_orders"] += 1
                
                # Small delay to prevent CPU overload
                await asyncio.sleep(0.001)
                
        except Exception as e:
            logger.error(f"Error in order processor: {str(e)}")
    
    async def _execute_order(self, order: Dict[str, Any]) -> Dict[str, Any]:
        """Execute order on selected exchange"""
        try:
            # Select exchange
            exchange = self._select_exchange(order)
            
            # Execute order
            if exchange:
                result = await exchange.execute_order(order)
                
                # Update order history
                self.order_history[order["symbol"]].append({
                    "order": order,
                    "result": result,
                    "timestamp": datetime.now().isoformat()
                })
                
                return result
            else:
                return {
                    "status": "rejected",
                    "error": "No suitable exchange found"
                }
            
        except Exception as e:
            logger.error(f"Error executing order: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def _select_exchange(self, order: Dict[str, Any]) -> Optional[Any]:
        """Select best exchange for order execution"""
        try:
            # Get available exchanges
            available_exchanges = [
                ex for ex in self.exchanges.values()
                if ex.is_available() and ex.supports_symbol(order["symbol"])
            ]
            
            if not available_exchanges:
                return None
            
            # Calculate exchange scores
            scores = []
            for exchange in available_exchanges:
                score = 0
                
                # Weight factor
                score += self.exchange_weights.get(exchange.name, 0.1)
                
                # Latency factor
                latency = exchange.get_latency()
                if latency:
                    score += 1 / (1 + latency)
                
                # Liquidity factor
                liquidity = exchange.get_liquidity(order["symbol"])
                if liquidity:
                    score += min(1, liquidity / order["quantity"])
                
                # Fee factor
                fees = exchange.get_fees(order["symbol"])
                if fees:
                    score += 1 / (1 + fees)
                
                scores.append((exchange, score))
            
            # Select exchange with highest score
            return max(scores, key=lambda x: x[1])[0]
            
        except Exception as e:
            logger.error(f"Error selecting exchange: {str(e)}")
            return None
    
    def _update_position(self, symbol: str, side: str, quantity: float):
        """Update position after order execution"""
        try:
            current_position = self.positions.get(symbol, 0)
            if side == "buy":
                self.positions[symbol] = current_position + quantity
            else:
                self.positions[symbol] = current_position - quantity
        except Exception as e:
            logger.error(f"Error updating position: {str(e)}")
    
    def _update_pnl(self, symbol: str, pnl: float):
        """Update P&L after order execution"""
        try:
            self.daily_pnl[symbol] += pnl
        except Exception as e:
            logger.error(f"Error updating P&L: {str(e)}")
    
    async def _send_order_notification(self, order: Dict[str, Any], result: Dict[str, Any]):
        """Send order execution notification"""
        try:
            if not self.notification_system:
                return
            
            # Prepare notification data
            notification_data = {
                "title": f"Order {result['status'].upper()}: {order['symbol']}",
                "message": self._format_order_message(order, result),
                "priority": order["priority"],
                "metadata": {
                    "symbol": order["symbol"],
                    "side": order["side"],
                    "quantity": order["quantity"],
                    "type": order["type"],
                    "status": result["status"]
                }
            }
            
            # Send notification
            await self.notification_system.generate_alert(**notification_data)
            
        except Exception as e:
            logger.error(f"Error sending order notification: {str(e)}")
    
    def _format_order_message(self, order: Dict[str, Any], result: Dict[str, Any]) -> str:
        """Format order execution message"""
        try:
            message = []
            
            # Add order details
            message.append(f"Symbol: {order['symbol']}")
            message.append(f"Side: {order['side'].upper()}")
            message.append(f"Quantity: {order['quantity']}")
            message.append(f"Type: {order['type'].upper()}")
            if order['price']:
                message.append(f"Price: {order['price']}")
            message.append("")
            
            # Add execution details
            message.append("Execution:")
            message.append(f"Status: {result['status'].upper()}")
            if "price" in result:
                message.append(f"Execution Price: {result['price']}")
            if "commission" in result:
                message.append(f"Commission: {result['commission']}")
            if "slippage" in result:
                message.append(f"Slippage: {result['slippage']}")
            if "pnl" in result:
                message.append(f"P&L: {result['pnl']}")
            
            return "\n".join(message)
            
        except Exception as e:
            logger.error(f"Error formatting order message: {str(e)}")
            return "Error formatting order message"
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get execution metrics"""
        return {
            "total_orders": self.metrics["total_orders"],
            "successful_orders": self.metrics["successful_orders"],
            "failed_orders": self.metrics["failed_orders"],
            "avg_execution_time": self.metrics["avg_execution_time"],
            "max_execution_time": self.metrics["max_execution_time"],
            "total_commission": self.metrics["total_commission"],
            "total_slippage": self.metrics["total_slippage"],
            "queue_stats": self.order_queue.get_stats(),
            "positions": dict(self.positions),
            "daily_pnl": dict(self.daily_pnl)
        }
    
    def get_order_history(self, 
                         symbol: Optional[str] = None,
                         limit: int = 100) -> List[Dict[str, Any]]:
        """Get order history"""
        if symbol is not None:
            return self.order_history[symbol][-limit:]
        
        # Combine all symbols
        all_orders = []
        for orders in self.order_history.values():
            all_orders.extend(orders)
        
        # Sort by timestamp
        all_orders.sort(key=lambda x: x["timestamp"], reverse=True)
        return all_orders[:limit]

# For testing
if __name__ == "__main__":
    # Load config
    with open("config/warmachine_config.json", "r") as f:
        config = json.load(f)
    
    # Create executor
    executor = HighFrequencyExecutor(config, None)
    
    # Test order
    async def test_order():
        result = await executor.submit_order(
            symbol="SPY",
            side="buy",
            quantity=100,
            order_type="market",
            priority=OrderPriority.HIGH
        )
        print(json.dumps(result, indent=2))
    
    # Run test
    asyncio.run(test_order()) 