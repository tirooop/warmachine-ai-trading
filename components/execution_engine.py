"""
Execution Engine Module
"""

import os
import sys
import time
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import uuid

from core.exceptions import ExecutionError, ValidationError
from core.config import get_config

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join('logs', 'execution_engine.log')),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger('ExecutionEngine')


class OrderType(Enum):
    """订单类型枚举"""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"
    TRAILING_STOP = "trailing_stop"


class OrderSide(Enum):
    """订单方向枚举"""
    BUY = "buy"
    SELL = "sell"


class OrderStatus(Enum):
    """订单状态枚举"""
    PENDING = "pending"
    SUBMITTED = "submitted"
    PARTIAL = "partial"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"


class ExecutionStrategy(Enum):
    """执行策略枚举"""
    IMMEDIATE = "immediate"
    TWAP = "twap"  # Time Weighted Average Price
    VWAP = "vwap"  # Volume Weighted Average Price
    ICEBERG = "iceberg"
    PARTICIPATE = "participate"


@dataclass
class Order:
    """订单数据类"""
    order_id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: float
    price: Optional[float] = None
    stop_price: Optional[float] = None
    limit_price: Optional[float] = None
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: float = 0.0
    average_price: Optional[float] = None
    commission: float = 0.0
    timestamp: datetime = None
    strategy: ExecutionStrategy = ExecutionStrategy.IMMEDIATE
    time_in_force: str = "DAY"
    additional_data: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class Trade:
    """成交数据类"""
    trade_id: str
    order_id: str
    symbol: str
    side: OrderSide
    quantity: float
    price: float
    commission: float
    timestamp: datetime
    exchange: str
    additional_data: Optional[Dict[str, Any]] = None


@dataclass
class Position:
    """持仓数据类"""
    symbol: str
    quantity: float
    average_price: float
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class OrderManager:
    """订单管理器"""
    
    def __init__(self):
        self.orders: Dict[str, Order] = {}
        self.trades: Dict[str, Trade] = {}
        self.positions: Dict[str, Position] = {}
        self.order_history: List[Order] = []
        self.trade_history: List[Trade] = []
    
    def create_order(self, symbol: str, side: OrderSide, order_type: OrderType, 
                    quantity: float, price: Optional[float] = None, 
                    strategy: ExecutionStrategy = ExecutionStrategy.IMMEDIATE) -> Order:
        """创建订单"""
        order_id = str(uuid.uuid4())
        
        order = Order(
            order_id=order_id,
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            price=price,
            status=OrderStatus.PENDING,
            strategy=strategy
        )
        
        self.orders[order_id] = order
        logger.info(f"创建订单: {order_id} {symbol} {side.value} {quantity}")
        
        return order
    
    def update_order_status(self, order_id: str, status: OrderStatus, 
                          filled_quantity: float = 0.0, average_price: Optional[float] = None):
        """更新订单状态"""
        if order_id not in self.orders:
            raise ExecutionError(f"订单不存在: {order_id}")
        
        order = self.orders[order_id]
        order.status = status
        order.filled_quantity = filled_quantity
        order.average_price = average_price
        
        if status in [OrderStatus.FILLED, OrderStatus.CANCELLED, OrderStatus.REJECTED]:
            self.order_history.append(order)
            if order_id in self.orders:
                del self.orders[order_id]
        
        logger.info(f"更新订单状态: {order_id} {status.value}")
    
    def add_trade(self, order_id: str, trade_id: str, quantity: float, 
                  price: float, commission: float = 0.0) -> Trade:
        """添加成交记录"""
        if order_id not in self.orders:
            raise ExecutionError(f"订单不存在: {order_id}")
        
        order = self.orders[order_id]
        
        trade = Trade(
            trade_id=trade_id,
            order_id=order_id,
            symbol=order.symbol,
            side=order.side,
            quantity=quantity,
            price=price,
            commission=commission,
            timestamp=datetime.now(),
            exchange="SIMULATED"
        )
        
        self.trades[trade_id] = trade
        self.trade_history.append(trade)
        
        # 更新持仓
        self._update_position(order.symbol, order.side, quantity, price)
        
        logger.info(f"添加成交: {trade_id} {order.symbol} {quantity} @ {price}")
        
        return trade
    
    def _update_position(self, symbol: str, side: OrderSide, quantity: float, price: float):
        """更新持仓"""
        if symbol not in self.positions:
            self.positions[symbol] = Position(symbol=symbol, quantity=0, average_price=0)
        
        position = self.positions[symbol]
        
        if side == OrderSide.BUY:
            # 买入
            total_cost = position.quantity * position.average_price + quantity * price
            position.quantity += quantity
            position.average_price = total_cost / position.quantity if position.quantity > 0 else 0
        else:
            # 卖出
            if position.quantity >= quantity:
                # 计算已实现盈亏
                realized_pnl = (price - position.average_price) * quantity
                position.realized_pnl += realized_pnl
                position.quantity -= quantity
                
                if position.quantity == 0:
                    position.average_price = 0
            else:
                raise ExecutionError(f"持仓不足: {symbol} 需要 {quantity}, 实际 {position.quantity}")
        
        position.timestamp = datetime.now()
    
    def get_order(self, order_id: str) -> Optional[Order]:
        """获取订单"""
        return self.orders.get(order_id)
    
    def get_orders(self, symbol: Optional[str] = None, status: Optional[OrderStatus] = None) -> List[Order]:
        """获取订单列表"""
        orders = list(self.orders.values())
        
        if symbol:
            orders = [o for o in orders if o.symbol == symbol]
        
        if status:
            orders = [o for o in orders if o.status == status]
        
        return orders
    
    def get_position(self, symbol: str) -> Optional[Position]:
        """获取持仓"""
        return self.positions.get(symbol)
    
    def get_positions(self) -> Dict[str, Position]:
        """获取所有持仓"""
        return self.positions.copy()
    
    def get_trade_history(self, symbol: Optional[str] = None) -> List[Trade]:
        """获取成交历史"""
        trades = self.trade_history.copy()
        
        if symbol:
            trades = [t for t in trades if t.symbol == symbol]
        
        return trades


class ExecutionStrategyManager:
    """执行策略管理器"""
    
    def __init__(self):
        self.strategies = {
            ExecutionStrategy.IMMEDIATE: self._execute_immediate,
            ExecutionStrategy.TWAP: self._execute_twap,
            ExecutionStrategy.VWAP: self._execute_vwap,
            ExecutionStrategy.ICEBERG: self._execute_iceberg,
            ExecutionStrategy.PARTICIPATE: self._execute_participate
        }
    
    async def execute_order(self, order: Order, market_data: Dict[str, Any]) -> List[Trade]:
        """执行订单"""
        strategy_func = self.strategies.get(order.strategy)
        if not strategy_func:
            raise ExecutionError(f"不支持的执行策略: {order.strategy}")
        
        return await strategy_func(order, market_data)
    
    async def _execute_immediate(self, order: Order, market_data: Dict[str, Any]) -> List[Trade]:
        """立即执行策略"""
        trades = []
        
        # 模拟立即执行
        if order.order_type == OrderType.MARKET:
            # 市价单立即成交
            current_price = market_data.get("current_price", order.price or 100.0)
            trade = Trade(
                trade_id=str(uuid.uuid4()),
                order_id=order.order_id,
                symbol=order.symbol,
                side=order.side,
                quantity=order.quantity,
                price=current_price,
                commission=0.0,
                timestamp=datetime.now(),
                exchange="SIMULATED"
            )
            trades.append(trade)
        
        elif order.order_type == OrderType.LIMIT:
            # 限价单检查是否可以成交
            current_price = market_data.get("current_price", 100.0)
            
            if (order.side == OrderSide.BUY and current_price <= order.price) or \
               (order.side == OrderSide.SELL and current_price >= order.price):
                trade = Trade(
                    trade_id=str(uuid.uuid4()),
                    order_id=order.order_id,
                    symbol=order.symbol,
                    side=order.side,
                    quantity=order.quantity,
                    price=order.price,
                    commission=0.0,
                    timestamp=datetime.now(),
                    exchange="SIMULATED"
                )
                trades.append(trade)
        
        return trades
    
    async def _execute_twap(self, order: Order, market_data: Dict[str, Any]) -> List[Trade]:
        """时间加权平均价格策略"""
        # 将订单分成多个小订单，在指定时间内均匀执行
        trades = []
        num_slices = 10
        slice_quantity = order.quantity / num_slices
        
        for i in range(num_slices):
            # 模拟时间间隔
            await asyncio.sleep(0.1)
            
            # 获取当前市场价格
            current_price = market_data.get("current_price", order.price or 100.0)
            
            trade = Trade(
                trade_id=str(uuid.uuid4()),
                order_id=order.order_id,
                symbol=order.symbol,
                side=order.side,
                quantity=slice_quantity,
                price=current_price,
                commission=0.0,
                timestamp=datetime.now(),
                exchange="SIMULATED"
            )
            trades.append(trade)
        
        return trades
    
    async def _execute_vwap(self, order: Order, market_data: Dict[str, Any]) -> List[Trade]:
        """成交量加权平均价格策略"""
        # 根据市场成交量分布执行订单
        trades = []
        remaining_quantity = order.quantity
        
        # 模拟根据成交量分布执行
        volume_distribution = market_data.get("volume_distribution", [0.1, 0.2, 0.3, 0.2, 0.1, 0.1])
        
        for volume_ratio in volume_distribution:
            if remaining_quantity <= 0:
                break
            
            slice_quantity = min(remaining_quantity, order.quantity * volume_ratio)
            current_price = market_data.get("current_price", order.price or 100.0)
            
            trade = Trade(
                trade_id=str(uuid.uuid4()),
                order_id=order.order_id,
                symbol=order.symbol,
                side=order.side,
                quantity=slice_quantity,
                price=current_price,
                commission=0.0,
                timestamp=datetime.now(),
                exchange="SIMULATED"
            )
            trades.append(trade)
            
            remaining_quantity -= slice_quantity
            await asyncio.sleep(0.1)
        
        return trades
    
    async def _execute_iceberg(self, order: Order, market_data: Dict[str, Any]) -> List[Trade]:
        """冰山订单策略"""
        # 将大订单隐藏，只显示小部分
        trades = []
        visible_quantity = order.quantity * 0.1  # 显示10%
        remaining_quantity = order.quantity
        
        while remaining_quantity > 0:
            slice_quantity = min(visible_quantity, remaining_quantity)
            current_price = market_data.get("current_price", order.price or 100.0)
            
            trade = Trade(
                trade_id=str(uuid.uuid4()),
                order_id=order.order_id,
                symbol=order.symbol,
                side=order.side,
                quantity=slice_quantity,
                price=current_price,
                commission=0.0,
                timestamp=datetime.now(),
                exchange="SIMULATED"
            )
            trades.append(trade)
            
            remaining_quantity -= slice_quantity
            await asyncio.sleep(0.2)  # 等待市场消化
        
        return trades
    
    async def _execute_participate(self, order: Order, market_data: Dict[str, Any]) -> List[Trade]:
        """参与策略"""
        # 根据市场参与度执行订单
        trades = []
        market_participation = market_data.get("market_participation", 0.05)  # 5%市场参与度
        remaining_quantity = order.quantity
        
        while remaining_quantity > 0:
            # 根据市场参与度计算执行数量
            slice_quantity = min(remaining_quantity, order.quantity * market_participation)
            current_price = market_data.get("current_price", order.price or 100.0)
            
            trade = Trade(
                trade_id=str(uuid.uuid4()),
                order_id=order.order_id,
                symbol=order.symbol,
                side=order.side,
                quantity=slice_quantity,
                price=current_price,
                commission=0.0,
                timestamp=datetime.now(),
                exchange="SIMULATED"
            )
            trades.append(trade)
            
            remaining_quantity -= slice_quantity
            await asyncio.sleep(0.1)
        
        return trades


class RiskManager:
    """风险管理器"""
    
    def __init__(self):
        self.max_position_size = 0.1  # 最大持仓比例
        self.max_daily_loss = 0.05   # 最大日损失
        self.max_order_size = 0.02   # 最大单笔订单比例
        self.daily_pnl = 0.0
        self.daily_trades = []
    
    def check_order_risk(self, order: Order, portfolio_value: float, 
                        current_positions: Dict[str, Position]) -> bool:
        """检查订单风险"""
        try:
            # 检查订单大小
            order_value = order.quantity * (order.price or 100.0)
            if order_value / portfolio_value > self.max_order_size:
                logger.warning(f"订单大小超过限制: {order_value / portfolio_value:.2%}")
                return False
            
            # 检查持仓限制
            current_position = current_positions.get(order.symbol)
            if current_position:
                new_position_value = (current_position.quantity + order.quantity) * (order.price or 100.0)
                if new_position_value / portfolio_value > self.max_position_size:
                    logger.warning(f"持仓大小超过限制: {new_position_value / portfolio_value:.2%}")
                    return False
            
            # 检查日损失限制
            if self.daily_pnl < -portfolio_value * self.max_daily_loss:
                logger.warning(f"日损失超过限制: {self.daily_pnl:.2f}")
                return False
            
            return True
        
        except Exception as e:
            logger.error(f"风险检查失败: {e}")
            return False
    
    def update_daily_pnl(self, trade: Trade):
        """更新日盈亏"""
        trade_value = trade.quantity * trade.price
        if trade.side == OrderSide.SELL:
            self.daily_pnl += trade_value
        else:
            self.daily_pnl -= trade_value
        
        self.daily_trades.append(trade)
    
    def reset_daily_stats(self):
        """重置日统计"""
        self.daily_pnl = 0.0
        self.daily_trades.clear()


class ExecutionEngine:
    """执行引擎主类"""
    
    def __init__(self):
        self.order_manager = OrderManager()
        self.strategy_manager = ExecutionStrategyManager()
        self.risk_manager = RiskManager()
        self.running = False
        self.execution_queue: asyncio.Queue = asyncio.Queue()
        logger.info("执行引擎初始化完成")
    
    async def start(self):
        """启动执行引擎"""
        self.running = True
        logger.info("执行引擎启动")
        
        try:
            # 启动执行任务
            execution_task = asyncio.create_task(self._execution_loop())
            
            # 等待任务完成
            await execution_task
        
        except Exception as e:
            logger.error(f"执行引擎出错: {e}")
            self.running = False
    
    async def stop(self):
        """停止执行引擎"""
        self.running = False
        logger.info("执行引擎停止")
    
    async def _execution_loop(self):
        """执行循环"""
        while self.running:
            try:
                # 从队列获取订单
                order = await asyncio.wait_for(self.execution_queue.get(), timeout=1.0)
                
                # 执行订单
                await self._execute_order(order)
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"执行循环出错: {e}")
    
    async def _execute_order(self, order: Order):
        """执行订单"""
        try:
            # 获取市场数据
            market_data = await self._get_market_data(order.symbol)
            
            # 风险检查
            portfolio_value = 100000.0  # 模拟组合价值
            current_positions = self.order_manager.get_positions()
            
            if not self.risk_manager.check_order_risk(order, portfolio_value, current_positions):
                self.order_manager.update_order_status(order.order_id, OrderStatus.REJECTED)
                return
            
            # 更新订单状态为已提交
            self.order_manager.update_order_status(order.order_id, OrderStatus.SUBMITTED)
            
            # 执行订单
            trades = await self.strategy_manager.execute_order(order, market_data)
            
            # 处理成交
            for trade in trades:
                self.order_manager.add_trade(order.order_id, trade.trade_id, 
                                          trade.quantity, trade.price, trade.commission)
                self.risk_manager.update_daily_pnl(trade)
            
            # 更新订单状态
            total_quantity = sum(t.quantity for t in trades)
            if total_quantity >= order.quantity:
                self.order_manager.update_order_status(order.order_id, OrderStatus.FILLED, 
                                                     total_quantity, order.price)
            elif total_quantity > 0:
                self.order_manager.update_order_status(order.order_id, OrderStatus.PARTIAL, 
                                                     total_quantity, order.price)
            
            logger.info(f"订单执行完成: {order.order_id} 成交 {total_quantity}/{order.quantity}")
        
        except Exception as e:
            logger.error(f"执行订单失败: {order.order_id} - {e}")
            self.order_manager.update_order_status(order.order_id, OrderStatus.REJECTED)
    
    async def _get_market_data(self, symbol: str) -> Dict[str, Any]:
        """获取市场数据（模拟）"""
        # 这里应该从实际的数据源获取数据
        return {
            "current_price": 100.0 + (hash(symbol) % 50),  # 模拟价格
            "volume_distribution": [0.1, 0.2, 0.3, 0.2, 0.1, 0.1],
            "market_participation": 0.05
        }
    
    async def submit_order(self, symbol: str, side: OrderSide, order_type: OrderType,
                          quantity: float, price: Optional[float] = None,
                          strategy: ExecutionStrategy = ExecutionStrategy.IMMEDIATE) -> Order:
        """提交订单"""
        # 创建订单
        order = self.order_manager.create_order(symbol, side, order_type, quantity, price, strategy)
        
        # 将订单加入执行队列
        await self.execution_queue.put(order)
        
        logger.info(f"提交订单: {order.order_id} {symbol} {side.value} {quantity}")
        
        return order
    
    def get_order_status(self, order_id: str) -> Optional[OrderStatus]:
        """获取订单状态"""
        order = self.order_manager.get_order(order_id)
        return order.status if order else None
    
    def get_orders(self, symbol: Optional[str] = None, status: Optional[OrderStatus] = None) -> List[Order]:
        """获取订单列表"""
        return self.order_manager.get_orders(symbol, status)
    
    def get_positions(self) -> Dict[str, Position]:
        """获取持仓"""
        return self.order_manager.get_positions()
    
    def get_trade_history(self, symbol: Optional[str] = None) -> List[Trade]:
        """获取成交历史"""
        return self.order_manager.get_trade_history(symbol)
    
    def get_execution_stats(self) -> Dict[str, Any]:
        """获取执行统计"""
        orders = self.order_manager.get_orders()
        positions = self.order_manager.get_positions()
        trades = self.order_manager.get_trade_history()
        
        return {
            "total_orders": len(orders),
            "pending_orders": len([o for o in orders if o.status == OrderStatus.PENDING]),
            "filled_orders": len([o for o in orders if o.status == OrderStatus.FILLED]),
            "total_positions": len(positions),
            "total_trades": len(trades),
            "daily_pnl": self.risk_manager.daily_pnl,
            "queue_size": self.execution_queue.qsize()
        }


if __name__ == "__main__":
    async def main():
        engine = ExecutionEngine()
        try:
            await engine.start()
        except KeyboardInterrupt:
            await engine.stop()
            logger.info("执行引擎已停止")
    
    asyncio.run(main()) 