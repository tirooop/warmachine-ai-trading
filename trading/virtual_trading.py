"""
Virtual Trading System - 虚拟交易系统

Provides virtual trading capabilities with portfolio management and performance tracking.
"""

import os
import json
import logging
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

@dataclass
class VirtualTrade:
    """Virtual trade data class"""
    symbol: str
    quantity: float
    entry_price: float
    entry_time: datetime
    strategy: str
    confidence: float
    risk_level: str
    exit_price: Optional[float] = None
    exit_time: Optional[datetime] = None
    pnl: Optional[float] = None
    pnl_pct: Optional[float] = None
    
    def to_dict(self) -> Dict:
        """Convert trade to dictionary"""
        return asdict(self)

class VirtualTrader:
    """Virtual trading system with portfolio management"""
    
    def __init__(self, data_dir: Union[str, Path] = "data/virtual_trading", initial_capital: float = 100000):
        """
        Initialize virtual trader
        
        Args:
            data_dir: Directory for data storage
            initial_capital: Initial capital amount
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Portfolio state
        self.portfolio = {
            "cash": initial_capital,
            "total_value": initial_capital,
            "positions": {},  # symbol -> {quantity, avg_price, current_price}
            "history": []  # List of portfolio snapshots
        }
        
        # Trading history
        self.trades: List[VirtualTrade] = []
        self.completed_trades: List[VirtualTrade] = []
        
        # Load existing data if available
        self._load_data()
        
        logger.info(f"Virtual trader initialized with ${initial_capital:,.2f}")
    
    async def initialize(self):
        """Initialize the virtual trader"""
        # Nothing to initialize asynchronously
        pass
    
    async def stop(self):
        """Stop the virtual trader"""
        self._save_data()
    
    def buy(self, symbol: str, price: float, quantity: float, 
            strategy: str = "MANUAL", confidence: float = 1.0,
            risk_level: str = "MEDIUM") -> Optional[VirtualTrade]:
        """
        Execute a buy trade
        
        Args:
            symbol: Trading symbol
            price: Entry price
            quantity: Quantity to buy
            strategy: Trading strategy name
            confidence: Trade confidence score
            risk_level: Risk level (LOW/MEDIUM/HIGH)
            
        Returns:
            VirtualTrade if successful, None otherwise
        """
        cost = price * quantity
        
        # Check if we have enough cash
        if cost > self.portfolio["cash"]:
            logger.warning(f"Insufficient funds for trade: {cost} > {self.portfolio['cash']}")
            return None
        
        # Create trade
        trade = VirtualTrade(
            symbol=symbol,
            quantity=quantity,
            entry_price=price,
            entry_time=datetime.now(),
            strategy=strategy,
            confidence=confidence,
            risk_level=risk_level
        )
        
        # Update portfolio
        if symbol in self.portfolio["positions"]:
            # Average down/up
            pos = self.portfolio["positions"][symbol]
            total_quantity = pos["quantity"] + quantity
            pos["avg_price"] = (pos["avg_price"] * pos["quantity"] + price * quantity) / total_quantity
            pos["quantity"] = total_quantity
            pos["current_price"] = price
        else:
            # New position
            self.portfolio["positions"][symbol] = {
                "quantity": quantity,
                "avg_price": price,
                "current_price": price
            }
        
        # Update cash and total value
        self.portfolio["cash"] -= cost
        self._update_portfolio_value()
        
        # Record trade
        self.trades.append(trade)
        
        logger.info(f"Bought {quantity} {symbol} @ ${price:.2f}")
        return trade
    
    def sell(self, symbol: str, price: float, quantity: Optional[float] = None) -> Optional[VirtualTrade]:
        """
        Execute a sell trade
        
        Args:
            symbol: Trading symbol
            price: Exit price
            quantity: Quantity to sell (None for all)
            
        Returns:
            VirtualTrade if successful, None otherwise
        """
        if symbol not in self.portfolio["positions"]:
            logger.warning(f"No position found for {symbol}")
            return None
        
        pos = self.portfolio["positions"][symbol]
        
        # If quantity not specified, sell all
        if quantity is None:
            quantity = pos["quantity"]
        elif quantity > pos["quantity"]:
            logger.warning(f"Insufficient quantity: {quantity} > {pos['quantity']}")
            return None
        
        # Find the corresponding buy trade
        for trade in reversed(self.trades):
            if trade.symbol == symbol and trade.exit_time is None:
                # Calculate P&L
                pnl = (price - trade.entry_price) * quantity
                pnl_pct = (price / trade.entry_price - 1) * 100
                
                # Update trade
                trade.exit_price = price
                trade.exit_time = datetime.now()
                trade.pnl = pnl
                trade.pnl_pct = pnl_pct
                
                # Move to completed trades
                self.completed_trades.append(trade)
                self.trades.remove(trade)
                break
        
        # Update portfolio
        proceeds = price * quantity
        self.portfolio["cash"] += proceeds
        
        if quantity == pos["quantity"]:
            # Close position
            del self.portfolio["positions"][symbol]
        else:
            # Reduce position
            pos["quantity"] -= quantity
        
        self._update_portfolio_value()
        
        logger.info(f"Sold {quantity} {symbol} @ ${price:.2f}")
        return trade
    
    def update_prices(self, prices: Dict[str, float]):
        """
        Update current prices for positions
        
        Args:
            prices: Dictionary of symbol -> price
        """
        for symbol, price in prices.items():
            if symbol in self.portfolio["positions"]:
                self.portfolio["positions"][symbol]["current_price"] = price
        
        self._update_portfolio_value()
    
    def get_portfolio_summary(self) -> Dict:
        """Get portfolio summary"""
        return {
            "total_value": self.portfolio["total_value"],
            "cash": self.portfolio["cash"],
            "positions_value": self.portfolio["total_value"] - self.portfolio["cash"],
            "total_return": (self.portfolio["total_value"] / 100000 - 1) * 100,  # Assuming 100k initial capital
            "positions": self.portfolio["positions"]
        }
    
    def get_completed_trades(self) -> List[VirtualTrade]:
        """Get list of completed trades"""
        return self.completed_trades
    
    def get_performance_metrics(self) -> Dict:
        """Calculate performance metrics"""
        if not self.completed_trades:
            return {
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate": 0,
                "total_pnl": 0,
                "avg_profit": 0,
                "avg_loss": 0,
                "profit_factor": 0
            }
        
        winning_trades = [t for t in self.completed_trades if t.pnl > 0]
        losing_trades = [t for t in self.completed_trades if t.pnl < 0]
        
        total_profit = sum(t.pnl for t in winning_trades) if winning_trades else 0
        total_loss = abs(sum(t.pnl for t in losing_trades)) if losing_trades else 0
        
        return {
            "total_trades": len(self.completed_trades),
            "winning_trades": len(winning_trades),
            "losing_trades": len(losing_trades),
            "win_rate": len(winning_trades) / len(self.completed_trades),
            "total_pnl": sum(t.pnl for t in self.completed_trades),
            "avg_profit": total_profit / len(winning_trades) if winning_trades else 0,
            "avg_loss": total_loss / len(losing_trades) if losing_trades else 0,
            "profit_factor": total_profit / total_loss if total_loss > 0 else float('inf')
        }
    
    def _update_portfolio_value(self):
        """Update total portfolio value"""
        positions_value = sum(
            pos["quantity"] * pos["current_price"]
            for pos in self.portfolio["positions"].values()
        )
        
        self.portfolio["total_value"] = self.portfolio["cash"] + positions_value
        
        # Record portfolio snapshot
        self.portfolio["history"].append({
            "timestamp": datetime.now().isoformat(),
            "total_value": self.portfolio["total_value"],
            "cash": self.portfolio["cash"],
            "positions_value": positions_value
        })
    
    def _load_data(self):
        """Load trading data from files"""
        try:
            portfolio_file = self.data_dir / "portfolio.json"
            trades_file = self.data_dir / "trades.json"
            
            if portfolio_file.exists():
                with open(portfolio_file, 'r') as f:
                    self.portfolio = json.load(f)
            
            if trades_file.exists():
                with open(trades_file, 'r') as f:
                    trades_data = json.load(f)
                    self.trades = [VirtualTrade(**t) for t in trades_data["active"]]
                    self.completed_trades = [VirtualTrade(**t) for t in trades_data["completed"]]
            
            logger.info("Trading data loaded successfully")
            
        except Exception as e:
            logger.error(f"Error loading trading data: {str(e)}")
    
    def _save_data(self):
        """Save trading data to files"""
        try:
            portfolio_file = self.data_dir / "portfolio.json"
            trades_file = self.data_dir / "trades.json"
            
            with open(portfolio_file, 'w') as f:
                json.dump(self.portfolio, f, indent=2)
            
            trades_data = {
                "active": [t.to_dict() for t in self.trades],
                "completed": [t.to_dict() for t in self.completed_trades]
            }
            with open(trades_file, 'w') as f:
                json.dump(trades_data, f, indent=2)
            
            logger.info("Trading data saved successfully")
            
        except Exception as e:
            logger.error(f"Error saving trading data: {str(e)}")





import os


import logging


import argparse


import threading


import time


from pathlib import Path





# Configure logging


logging.basicConfig(


    level=logging.INFO,


    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',


    handlers=[


        logging.FileHandler("virtual_trading_system.log"),


        logging.StreamHandler()


    ]


)


logger = logging.getLogger("virtual_trading_system")





def run_telegram_bot():


    """Run Telegram bot"""


    logger.info("Starting Telegram bot...")


    from utils.telegram_bot import telegram_bot


    


    if telegram_bot:


        telegram_bot.start()


        logger.info("Telegram bot started successfully")


    else:


        logger.error("Telegram bot not found or failed to initialize")





def run_price_updater(interval=60):


    """Run price updater thread"""


    logger.info("Starting price updater thread...")


    from utils.trading_integration import trading_integration


    


    while True:


        try:


            trading_integration.auto_update_prices()


            logger.info("Updated prices successfully")


        except Exception as e:


            logger.error(f"Error updating prices: {str(e)}")


        


        time.sleep(interval)





def run_auto_trader(symbols, interval=300, min_confidence=0.7):


    """Run auto trader thread"""


    logger.info(f"Starting auto trader thread (interval: {interval}s)...")


    from utils.trading_integration import trading_integration


    


    while True:


        try:


            results = trading_integration.auto_trade(symbols, min_confidence)


            logger.info(f"Auto trade results: {results}")


        except Exception as e:


            logger.error(f"Error in auto trader: {str(e)}")


        


        time.sleep(interval)





def run_streamlit():


    """Run Streamlit dashboard"""


    logger.info("Starting Streamlit dashboard...")


    os.system("streamlit run streamlit_virtual_trade_dashboard.py")





def main():


    """Main entry point"""


    parser = argparse.ArgumentParser(description="Run Virtual Trading System")


    parser.add_argument("--telegram", action="store_true", help="Run Telegram bot")


    parser.add_argument("--streamlit", action="store_true", help="Run Streamlit dashboard")


    parser.add_argument("--updater", action="store_true", help="Run price updater")


    parser.add_argument("--trader", action="store_true", help="Run auto trader")


    parser.add_argument("--all", action="store_true", help="Run all components")


    parser.add_argument("--update-interval", type=int, default=60, help="Price update interval in seconds")


    parser.add_argument("--trade-interval", type=int, default=300, help="Auto trade interval in seconds")


    parser.add_argument("--min-confidence", type=float, default=0.7, help="Minimum confidence for auto trading")


    parser.add_argument("--symbols", type=str, default="SPY,AAPL,MSFT", help="Symbols to trade (comma-separated)")


    


    args = parser.parse_args()


    


    # Parse symbols


    trading_symbols = args.symbols.split(",")


    


    # Run components based on arguments


    threads = []


    


    # Telegram bot


    if args.telegram or args.all:


        telegram_thread = threading.Thread(target=run_telegram_bot)


        telegram_thread.daemon = True


        threads.append(telegram_thread)


    


    # Price updater


    if args.updater or args.all:


        updater_thread = threading.Thread(


            target=run_price_updater, 


            args=(args.update_interval,)


        )


        updater_thread.daemon = True


        threads.append(updater_thread)


    


    # Auto trader


    if args.trader or args.all:


        trader_thread = threading.Thread(


            target=run_auto_trader,


            args=(trading_symbols, args.trade_interval, args.min_confidence)


        )


        trader_thread.daemon = True


        threads.append(trader_thread)


    


    # Start all threads


    for thread in threads:


        thread.start()


    


    # Run Streamlit (blocks the main thread)


    if args.streamlit or args.all:


        run_streamlit()


    else:


        # If not running Streamlit, keep the main thread alive


        try:


            while True:


                time.sleep(1)


        except KeyboardInterrupt:


            logger.info("Shutting down...")





if __name__ == "__main__":


    main() 