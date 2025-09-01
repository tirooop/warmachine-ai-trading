"""
风险控制组件
负责监控和管理交易风险
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
import numpy as np
import pandas as pd

from core.exceptions import RiskManagementError, ValidationError
from core.config import get_config

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join('logs', 'risk_manager.log')),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger('RiskManager')


class RiskLevel(Enum):
    """风险等级枚举"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RiskType(Enum):
    """风险类型枚举"""
    PORTFOLIO = "portfolio"
    POSITION = "position"
    MARKET = "market"
    LIQUIDITY = "liquidity"
    CREDIT = "credit"
    OPERATIONAL = "operational"


@dataclass
class RiskMetrics:
    """风险指标数据类"""
    risk_type: RiskType
    value: float
    threshold: float
    level: RiskLevel
    timestamp: datetime
    details: Dict[str, Any]


@dataclass
class Position:
    """持仓数据类"""
    symbol: str
    quantity: float
    entry_price: float
    current_price: float
    side: str  # "long" or "short"
    timestamp: datetime
    pnl: float = 0.0
    unrealized_pnl: float = 0.0


@dataclass
class RiskLimit:
    """风险限制数据类"""
    max_position_size: float = 0.1  # 最大持仓比例
    max_total_risk: float = 0.2     # 最大总风险
    max_daily_loss: float = 0.05    # 最大日损失
    max_drawdown: float = 0.15       # 最大回撤
    max_open_positions: int = 10     # 最大开仓数量
    stop_loss: float = 0.02          # 止损比例
    take_profit: float = 0.05        # 止盈比例


class RiskCalculator:
    """风险计算器"""
    
    def __init__(self):
        self.config = get_config()
        self.risk_limits = RiskLimit()
    
    def calculate_portfolio_risk(self, positions: List[Position], portfolio_value: float) -> RiskMetrics:
        """计算组合风险"""
        try:
            if not positions:
                return RiskMetrics(
                    risk_type=RiskType.PORTFOLIO,
                    value=0.0,
                    threshold=self.risk_limits.max_total_risk,
                    level=RiskLevel.LOW,
                    timestamp=datetime.now(),
                    details={"positions_count": 0}
                )
            
            # 计算总持仓价值
            total_position_value = sum(abs(pos.quantity * pos.current_price) for pos in positions)
            portfolio_risk = total_position_value / portfolio_value if portfolio_value > 0 else 0
            
            # 计算风险等级
            level = self._calculate_risk_level(portfolio_risk, self.risk_limits.max_total_risk)
            
            return RiskMetrics(
                risk_type=RiskType.PORTFOLIO,
                value=portfolio_risk,
                threshold=self.risk_limits.max_total_risk,
                level=level,
                timestamp=datetime.now(),
                details={
                    "positions_count": len(positions),
                    "total_position_value": total_position_value,
                    "portfolio_value": portfolio_value
                }
            )
        except Exception as e:
            logger.error(f"计算组合风险失败: {e}")
            raise RiskManagementError(f"计算组合风险失败: {e}")
    
    def calculate_position_risk(self, position: Position, portfolio_value: float) -> RiskMetrics:
        """计算单个持仓风险"""
        try:
            position_value = abs(position.quantity * position.current_price)
            position_risk = position_value / portfolio_value if portfolio_value > 0 else 0
            
            # 计算未实现盈亏
            if position.side == "long":
                unrealized_pnl = (position.current_price - position.entry_price) * position.quantity
            else:
                unrealized_pnl = (position.entry_price - position.current_price) * position.quantity
            
            # 计算风险等级
            level = self._calculate_risk_level(position_risk, self.risk_limits.max_position_size)
            
            return RiskMetrics(
                risk_type=RiskType.POSITION,
                value=position_risk,
                threshold=self.risk_limits.max_position_size,
                level=level,
                timestamp=datetime.now(),
                details={
                    "symbol": position.symbol,
                    "position_value": position_value,
                    "unrealized_pnl": unrealized_pnl,
                    "pnl_percentage": unrealized_pnl / portfolio_value if portfolio_value > 0 else 0
                }
            )
        except Exception as e:
            logger.error(f"计算持仓风险失败: {e}")
            raise RiskManagementError(f"计算持仓风险失败: {e}")
    
    def calculate_market_risk(self, positions: List[Position], market_data: Dict[str, Any]) -> RiskMetrics:
        """计算市场风险"""
        try:
            if not positions:
                return RiskMetrics(
                    risk_type=RiskType.MARKET,
                    value=0.0,
                    threshold=0.1,  # 市场风险阈值
                    level=RiskLevel.LOW,
                    timestamp=datetime.now(),
                    details={"volatility": 0.0}
                )
            
            # 计算组合波动率
            returns = []
            for pos in positions:
                if hasattr(pos, 'price_history') and pos.price_history:
                    price_changes = np.diff(pos.price_history) / pos.price_history[:-1]
                    returns.extend(price_changes)
            
            if returns:
                volatility = np.std(returns) * np.sqrt(252)  # 年化波动率
            else:
                volatility = 0.0
            
            # 计算风险等级
            level = self._calculate_risk_level(volatility, 0.3)  # 30%波动率阈值
            
            return RiskMetrics(
                risk_type=RiskType.MARKET,
                value=volatility,
                threshold=0.3,
                level=level,
                timestamp=datetime.now(),
                details={
                    "volatility": volatility,
                    "positions_count": len(positions),
                    "market_conditions": market_data.get("market_conditions", "normal")
                }
            )
        except Exception as e:
            logger.error(f"计算市场风险失败: {e}")
            raise RiskManagementError(f"计算市场风险失败: {e}")
    
    def calculate_liquidity_risk(self, positions: List[Position], market_data: Dict[str, Any]) -> RiskMetrics:
        """计算流动性风险"""
        try:
            if not positions:
                return RiskMetrics(
                    risk_type=RiskType.LIQUIDITY,
                    value=0.0,
                    threshold=0.1,
                    level=RiskLevel.LOW,
                    timestamp=datetime.now(),
                    details={"liquidity_score": 1.0}
                )
            
            # 计算流动性评分
            liquidity_scores = []
            for pos in positions:
                symbol_data = market_data.get(pos.symbol, {})
                volume = symbol_data.get("volume", 0)
                spread = symbol_data.get("spread", 0.01)
                
                # 简单的流动性评分 (0-1, 1表示最流动)
                liquidity_score = min(1.0, volume / 1000000) * (1 - spread)
                liquidity_scores.append(liquidity_score)
            
            avg_liquidity = np.mean(liquidity_scores) if liquidity_scores else 1.0
            liquidity_risk = 1 - avg_liquidity
            
            # 计算风险等级
            level = self._calculate_risk_level(liquidity_risk, 0.5)
            
            return RiskMetrics(
                risk_type=RiskType.LIQUIDITY,
                value=liquidity_risk,
                threshold=0.5,
                level=level,
                timestamp=datetime.now(),
                details={
                    "liquidity_score": avg_liquidity,
                    "positions_count": len(positions),
                    "avg_spread": np.mean([market_data.get(pos.symbol, {}).get("spread", 0.01) for pos in positions])
                }
            )
        except Exception as e:
            logger.error(f"计算流动性风险失败: {e}")
            raise RiskManagementError(f"计算流动性风险失败: {e}")
    
    def calculate_drawdown(self, portfolio_history: List[float]) -> RiskMetrics:
        """计算回撤"""
        try:
            if len(portfolio_history) < 2:
                return RiskMetrics(
                    risk_type=RiskType.PORTFOLIO,
                    value=0.0,
                    threshold=self.risk_limits.max_drawdown,
                    level=RiskLevel.LOW,
                    timestamp=datetime.now(),
                    details={"peak_value": portfolio_history[0] if portfolio_history else 0}
                )
            
            portfolio_array = np.array(portfolio_history)
            peak = np.maximum.accumulate(portfolio_array)
            drawdown = (peak - portfolio_array) / peak
            current_drawdown = drawdown[-1]
            
            # 计算风险等级
            level = self._calculate_risk_level(current_drawdown, self.risk_limits.max_drawdown)
            
            return RiskMetrics(
                risk_type=RiskType.PORTFOLIO,
                value=current_drawdown,
                threshold=self.risk_limits.max_drawdown,
                level=level,
                timestamp=datetime.now(),
                details={
                    "peak_value": peak[-1],
                    "current_value": portfolio_array[-1],
                    "max_drawdown": np.max(drawdown)
                }
            )
        except Exception as e:
            logger.error(f"计算回撤失败: {e}")
            raise RiskManagementError(f"计算回撤失败: {e}")
    
    def _calculate_risk_level(self, value: float, threshold: float) -> RiskLevel:
        """计算风险等级"""
        if value <= threshold * 0.5:
            return RiskLevel.LOW
        elif value <= threshold:
            return RiskLevel.MEDIUM
        elif value <= threshold * 1.5:
            return RiskLevel.HIGH
        else:
            return RiskLevel.CRITICAL


class RiskMonitor:
    """风险监控器"""
    
    def __init__(self):
        self.calculator = RiskCalculator()
        self.risk_history: List[RiskMetrics] = []
        self.alerts: List[Dict[str, Any]] = []
        self.running = False
    
    async def monitor_risk(self, positions: List[Position], portfolio_value: float, market_data: Dict[str, Any]):
        """监控风险"""
        try:
            # 计算各种风险指标
            portfolio_risk = self.calculator.calculate_portfolio_risk(positions, portfolio_value)
            market_risk = self.calculator.calculate_market_risk(positions, market_data)
            liquidity_risk = self.calculator.calculate_liquidity_risk(positions, market_data)
            
            # 计算单个持仓风险
            position_risks = []
            for position in positions:
                pos_risk = self.calculator.calculate_position_risk(position, portfolio_value)
                position_risks.append(pos_risk)
            
            # 检查风险警报
            await self._check_risk_alerts([portfolio_risk, market_risk, liquidity_risk] + position_risks)
            
            # 记录风险历史
            self.risk_history.extend([portfolio_risk, market_risk, liquidity_risk])
            
            # 保持历史记录在合理范围内
            if len(self.risk_history) > 1000:
                self.risk_history = self.risk_history[-1000:]
            
            return {
                "portfolio_risk": portfolio_risk,
                "market_risk": market_risk,
                "liquidity_risk": liquidity_risk,
                "position_risks": position_risks
            }
        except Exception as e:
            logger.error(f"风险监控失败: {e}")
            raise RiskManagementError(f"风险监控失败: {e}")
    
    async def _check_risk_alerts(self, risk_metrics: List[RiskMetrics]):
        """检查风险警报"""
        for metric in risk_metrics:
            if metric.level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
                alert = {
                    "timestamp": datetime.now(),
                    "risk_type": metric.risk_type.value,
                    "level": metric.level.value,
                    "value": metric.value,
                    "threshold": metric.threshold,
                    "details": metric.details,
                    "message": f"风险警报: {metric.risk_type.value} 风险达到 {metric.level.value} 级别"
                }
                self.alerts.append(alert)
                logger.warning(f"风险警报: {alert['message']}")
    
    def get_risk_summary(self) -> Dict[str, Any]:
        """获取风险摘要"""
        if not self.risk_history:
            return {"status": "no_data"}
        
        recent_risks = self.risk_history[-100:]  # 最近100个风险指标
        
        return {
            "total_alerts": len(self.alerts),
            "recent_alerts": len([a for a in self.alerts if (datetime.now() - a["timestamp"]).days <= 1]),
            "avg_portfolio_risk": np.mean([r.value for r in recent_risks if r.risk_type == RiskType.PORTFOLIO]),
            "avg_market_risk": np.mean([r.value for r in recent_risks if r.risk_type == RiskType.MARKET]),
            "avg_liquidity_risk": np.mean([r.value for r in recent_risks if r.risk_type == RiskType.LIQUIDITY]),
            "max_risk_level": max([r.level.value for r in recent_risks], default="low")
        }


class RiskController:
    """风险控制器"""
    
    def __init__(self):
        self.monitor = RiskMonitor()
        self.running = False
        self.auto_stop_trading = False
        self.risk_limits = RiskLimit()
    
    async def start(self):
        """启动风险控制"""
        self.running = True
        logger.info("风险控制器启动")
        
        try:
            while self.running:
                # 这里应该从实际的数据源获取数据
                # 目前使用模拟数据
                positions = self._get_mock_positions()
                portfolio_value = 100000.0
                market_data = self._get_mock_market_data()
                
                # 监控风险
                risk_metrics = await self.monitor.monitor_risk(positions, portfolio_value, market_data)
                
                # 执行风险控制
                await self._execute_risk_control(risk_metrics)
                
                await asyncio.sleep(5)  # 每5秒检查一次
        except Exception as e:
            logger.error(f"风险控制出错: {e}")
            self.running = False
    
    async def stop(self):
        """停止风险控制"""
        self.running = False
        logger.info("风险控制器停止")
    
    async def _execute_risk_control(self, risk_metrics: Dict[str, Any]):
        """执行风险控制"""
        try:
            portfolio_risk = risk_metrics["portfolio_risk"]
            
            # 检查是否需要停止交易
            if portfolio_risk.level == RiskLevel.CRITICAL:
                self.auto_stop_trading = True
                logger.critical("检测到严重风险，自动停止交易")
            
            # 检查是否需要减仓
            if portfolio_risk.level == RiskLevel.HIGH:
                logger.warning("检测到高风险，建议减仓")
            
            # 检查单个持仓风险
            for pos_risk in risk_metrics["position_risks"]:
                if pos_risk.level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
                    logger.warning(f"持仓 {pos_risk.details['symbol']} 风险过高，建议平仓")
        
        except Exception as e:
            logger.error(f"执行风险控制失败: {e}")
    
    def _get_mock_positions(self) -> List[Position]:
        """获取模拟持仓数据"""
        return [
            Position(
                symbol="AAPL",
                quantity=100,
                entry_price=150.0,
                current_price=155.0,
                side="long",
                timestamp=datetime.now(),
                pnl=500.0,
                unrealized_pnl=500.0
            ),
            Position(
                symbol="TSLA",
                quantity=50,
                entry_price=200.0,
                current_price=190.0,
                side="short",
                timestamp=datetime.now(),
                pnl=500.0,
                unrealized_pnl=500.0
            )
        ]
    
    def _get_mock_market_data(self) -> Dict[str, Any]:
        """获取模拟市场数据"""
        return {
            "AAPL": {
                "volume": 50000000,
                "spread": 0.001,
                "volatility": 0.02
            },
            "TSLA": {
                "volume": 30000000,
                "spread": 0.002,
                "volatility": 0.04
            },
            "market_conditions": "normal"
        }
    
    def get_risk_metrics(self) -> Dict[str, Any]:
        """获取风险指标"""
        try:
            summary = self.monitor.get_risk_summary()
            return {
                "status": "success",
                "summary": summary,
                "auto_stop_trading": self.auto_stop_trading,
                "risk_limits": {
                    "max_position_size": self.risk_limits.max_position_size,
                    "max_total_risk": self.risk_limits.max_total_risk,
                    "max_daily_loss": self.risk_limits.max_daily_loss,
                    "max_drawdown": self.risk_limits.max_drawdown,
                    "max_open_positions": self.risk_limits.max_open_positions,
                    "stop_loss": self.risk_limits.stop_loss,
                    "take_profit": self.risk_limits.take_profit
                }
            }
        except Exception as e:
            logger.error(f"获取风险指标失败: {e}")
            return {"status": "error", "message": str(e)}
    
    def get_risk_limits(self) -> Dict[str, Any]:
        """获取风险限制"""
        return {
            "max_position_size": self.risk_limits.max_position_size,
            "max_total_risk": self.risk_limits.max_total_risk,
            "max_daily_loss": self.risk_limits.max_daily_loss,
            "max_drawdown": self.risk_limits.max_drawdown,
            "max_open_positions": self.risk_limits.max_open_positions,
            "stop_loss": self.risk_limits.stop_loss,
            "take_profit": self.risk_limits.take_profit
        }
    
    def update_risk_limits(self, new_limits: Dict[str, Any]):
        """更新风险限制"""
        try:
            for key, value in new_limits.items():
                if hasattr(self.risk_limits, key):
                    setattr(self.risk_limits, key, value)
            logger.info(f"风险限制已更新: {new_limits}")
        except Exception as e:
            logger.error(f"更新风险限制失败: {e}")
            raise RiskManagementError(f"更新风险限制失败: {e}")


class RiskManager:
    """风险管理器主类"""
    
    def __init__(self):
        self.controller = RiskController()
        self.running = False
        logger.info("风险管理器初始化完成")
    
    async def start(self):
        """启动风险管理"""
        self.running = True
        logger.info("风险管理器启动")
        
        try:
            await self.controller.start()
        except Exception as e:
            logger.error(f"风险管理出错: {e}")
            self.running = False
    
    async def stop(self):
        """停止风险管理"""
        self.running = False
        await self.controller.stop()
        logger.info("风险管理器停止")
    
    def get_risk_metrics(self) -> Dict[str, Any]:
        """获取风险指标"""
        return self.controller.get_risk_metrics()
    
    def get_risk_limits(self) -> Dict[str, Any]:
        """获取风险限制"""
        return self.controller.get_risk_limits()
    
    def update_risk_limits(self, new_limits: Dict[str, Any]):
        """更新风险限制"""
        self.controller.update_risk_limits(new_limits)


if __name__ == "__main__":
    async def main():
        manager = RiskManager()
        try:
            await manager.start()
        except KeyboardInterrupt:
            await manager.stop()
            logger.info("风险管理器已停止")
    
    asyncio.run(main()) 