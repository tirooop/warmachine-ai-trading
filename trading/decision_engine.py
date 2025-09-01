"""
Decision Engine for WarMachine Trading System

This module implements the decision-making logic for trading actions,
integrating with PPO for reinforcement learning-based decisions.
"""

import logging
from typing import Dict, Any, Optional, Tuple
import numpy as np

from trading.ppo_integration import PPOTrainer
from core.data.market_data_hub import MarketDataHub
from core.risk.risk_manager import RiskManager

logger = logging.getLogger(__name__)

class RiskControlError(Exception):
    """Exception raised for risk control violations"""
    pass

class DecisionEngine:
    """Decision engine for trading actions"""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize decision engine
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        
        # Initialize components
        self.market_data = MarketDataHub(config.get("market_data", {}))
        self.risk_manager = RiskManager(config.get("risk", {}))
        self.ppo_trainer = PPOTrainer(config.get("ppo", {}))
        
        # Initialize state
        self.account_balance = config.get("initial_balance", 100000.0)
        self.positions = {}
        self.trade_history = []
        
    def step(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute one step of decision making
        
        Args:
            market_data: Current market data
            
        Returns:
            Dictionary containing decision results
        """
        try:
            # Get current state
            state = self._get_state(market_data)
            
            # Get action from PPO
            action, action_prob = self.ppo_trainer.get_action(state)
            
            # Convert action to order
            order = self._action_to_order(action, market_data)
            
            # Validate and execute order
            if self._validate_order(order):
                result = self._execute_order(order)
            else:
                result = {
                    "status": "rejected",
                    "reason": "Order validation failed"
                }
                
            # Update state
            self._update_state(result)
            
            # Prepare return value
            return {
                "action": action,
                "action_probability": action_prob,
                "order": order,
                "result": result,
                "state": state
            }
            
        except Exception as e:
            logger.error(f"Error in decision step: {str(e)}")
            return {
                "status": "error",
                "error": str(e)
            }
            
    def _get_state(self, market_data: Dict[str, Any]) -> np.ndarray:
        """Get current state representation
        
        Args:
            market_data: Current market data
            
        Returns:
            State array
        """
        try:
            # Extract features
            price = market_data.get("price", 0.0)
            volume = market_data.get("volume", 0.0)
            volatility = market_data.get("volatility", 0.0)
            
            # Get position information
            position_size = sum(self.positions.values())
            position_value = position_size * price
            
            # Get account information
            available_balance = self.account_balance - position_value
            
            # Combine features
            state = np.array([
                price,
                volume,
                volatility,
                position_size,
                position_value,
                available_balance,
                self.account_balance,
                len(self.positions),
                len(self.trade_history),
                np.mean([t["pnl"] for t in self.trade_history[-10:]]) if self.trade_history else 0.0
            ])
            
            return state
            
        except Exception as e:
            logger.error(f"Error getting state: {str(e)}")
            raise
            
    def _action_to_order(self, action: int, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert action to order
        
        Args:
            action: Action from PPO
            market_data: Current market data
            
        Returns:
            Order dictionary
        """
        try:
            # Define action mapping
            action_map = {
                0: "BUY",
                1: "SELL",
                2: "HOLD"
            }
            
            # Get action type
            action_type = action_map.get(action, "HOLD")
            
            if action_type == "HOLD":
                return {
                    "type": "HOLD",
                    "amount": 0.0
                }
                
            # Calculate order amount
            price = market_data.get("price", 0.0)
            available_balance = self.account_balance - sum(self.positions.values()) * price
            
            # Use 5% of available balance
            amount = available_balance * 0.05 / price
            
            return {
                "type": action_type,
                "amount": amount,
                "price": price,
                "symbol": market_data.get("symbol", "UNKNOWN")
            }
            
        except Exception as e:
            logger.error(f"Error converting action to order: {str(e)}")
            raise
            
    def _validate_order(self, order: Dict[str, Any]) -> bool:
        """Validate order
        
        Args:
            order: Order dictionary
            
        Returns:
            True if order is valid
        """
        try:
            # Check order type
            if order["type"] not in ["BUY", "SELL", "HOLD"]:
                return False
                
            # Skip validation for HOLD
            if order["type"] == "HOLD":
                return True
                
            # Check amount
            if order["amount"] <= 0:
                return False
                
            # Check balance
            if order["type"] == "BUY":
                required_balance = order["amount"] * order["price"]
                if required_balance > self.account_balance * 0.05:
                    raise RiskControlError("Order amount exceeds 5% of balance")
                    
            # Check position
            if order["type"] == "SELL":
                current_position = self.positions.get(order["symbol"], 0)
                if order["amount"] > current_position:
                    return False
                    
            return True
            
        except RiskControlError as e:
            logger.warning(f"Risk control violation: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Error validating order: {str(e)}")
            return False
            
    def _execute_order(self, order: Dict[str, Any]) -> Dict[str, Any]:
        """Execute order
        
        Args:
            order: Order dictionary
            
        Returns:
            Execution result
        """
        try:
            # Skip execution for HOLD
            if order["type"] == "HOLD":
                return {
                    "status": "executed",
                    "type": "HOLD",
                    "amount": 0.0
                }
                
            # Execute order
            symbol = order["symbol"]
            amount = order["amount"]
            price = order["price"]
            
            if order["type"] == "BUY":
                # Update position
                self.positions[symbol] = self.positions.get(symbol, 0) + amount
                # Update balance
                self.account_balance -= amount * price
                
            elif order["type"] == "SELL":
                # Update position
                self.positions[symbol] = self.positions.get(symbol, 0) - amount
                # Update balance
                self.account_balance += amount * price
                
            # Record trade
            trade = {
                "type": order["type"],
                "symbol": symbol,
                "amount": amount,
                "price": price,
                "timestamp": self.market_data.get_current_time()
            }
            self.trade_history.append(trade)
            
            return {
                "status": "executed",
                "type": order["type"],
                "amount": amount,
                "price": price,
                "symbol": symbol
            }
            
        except Exception as e:
            logger.error(f"Error executing order: {str(e)}")
            raise
            
    def _update_state(self, result: Dict[str, Any]):
        """Update internal state
        
        Args:
            result: Execution result
        """
        try:
            # Update metrics
            if result["status"] == "executed":
                # Calculate PnL
                if result["type"] != "HOLD":
                    trade = self.trade_history[-1]
                    trade["pnl"] = (
                        (result["price"] - trade["price"]) * trade["amount"]
                        if result["type"] == "SELL"
                        else 0.0
                    )
                    
        except Exception as e:
            logger.error(f"Error updating state: {str(e)}")
            raise
            
    def get_state(self) -> Dict[str, Any]:
        """Get current state
        
        Returns:
            State dictionary
        """
        return {
            "account_balance": self.account_balance,
            "positions": self.positions,
            "trade_history": self.trade_history
        } 