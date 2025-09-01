from dataclasses import dataclass
from typing import Dict, List, Optional
import numpy as np
from datetime import datetime

@dataclass
class Position:
    symbol: str
    quantity: int
    entry_price: float
    current_price: float
    greeks: Dict[str, float]
    timestamp: datetime

class RiskController:
    def __init__(self, config: Dict):
        self.max_position_size = config.get("max_position_size", 1000)
        self.max_loss_per_trade = config.get("max_loss_per_trade", 0.02)
        self.max_portfolio_risk = config.get("max_portfolio_risk", 0.1)
        self.positions: Dict[str, Position] = {}
        self.logger = logging.getLogger(__name__)
        
    def validate_trade(self, trade: Dict) -> bool:
        """验证交易是否符合风险控制要求"""
        try:
            # 检查仓位大小
            if trade["quantity"] > self.max_position_size:
                self.logger.warning(f"Position size {trade['quantity']} exceeds limit {self.max_position_size}")
                return False
                
            # 检查单笔损失
            max_loss = trade["quantity"] * trade["entry_price"] * self.max_loss_per_trade
            if trade["max_loss"] > max_loss:
                self.logger.warning(f"Max loss {trade['max_loss']} exceeds limit {max_loss}")
                return False
                
            # 检查组合风险
            if not self._check_portfolio_risk(trade):
                return False
                
            return True
            
        except Exception as e:
            self.logger.error(f"Error validating trade: {str(e)}")
            return False
            
    def _check_portfolio_risk(self, new_trade: Dict) -> bool:
        """检查新增交易后的组合风险"""
        total_exposure = sum(
            pos.quantity * pos.current_price 
            for pos in self.positions.values()
        )
        
        new_exposure = new_trade["quantity"] * new_trade["entry_price"]
        total_risk = (total_exposure + new_exposure) / self.max_portfolio_risk
        
        return total_risk <= 1.0
        
    def update_position(self, symbol: str, data: Dict) -> None:
        """更新持仓信息"""
        if symbol in self.positions:
            position = self.positions[symbol]
            position.current_price = data["price"]
            position.greeks = data["greeks"]
            position.timestamp = datetime.now()
            
    def get_risk_metrics(self) -> Dict:
        """获取风险指标"""
        return {
            "total_exposure": sum(
                pos.quantity * pos.current_price 
                for pos in self.positions.values()
            ),
            "position_count": len(self.positions),
            "max_drawdown": self._calculate_max_drawdown(),
            "portfolio_delta": sum(
                pos.quantity * pos.greeks.get("delta", 0)
                for pos in self.positions.values()
            )
        }
        
    def _calculate_max_drawdown(self) -> float:
        """计算最大回撤"""
        if not self.positions:
            return 0.0
            
        peak = float("-inf")
        max_drawdown = 0.0
        
        for position in self.positions.values():
            current_value = position.quantity * position.current_price
            if current_value > peak:
                peak = current_value
            drawdown = (peak - current_value) / peak
            max_drawdown = max(max_drawdown, drawdown)
            
        return max_drawdown
        
    def generate_hedge_suggestion(self) -> Optional[Dict]:
        """生成对冲建议"""
        total_delta = sum(
            pos.quantity * pos.greeks.get("delta", 0)
            for pos in self.positions.values()
        )
        
        if abs(total_delta) > 10:
            return {
                "action": "hedge",
                "direction": "short" if total_delta > 0 else "long",
                "quantity": round(abs(total_delta))
            }
        return None 