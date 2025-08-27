"""
Virtual Trading Manager - 虚拟交易管理器

Connects AI signals and analysis with the virtual trading system.
Manages virtual trades, records results, and provides feedback to the AI system.
"""

import os
import json
import logging
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

# Import necessary modules
from ..ai_intelligence_dispatcher import AIIntelligenceDispatcher
from trading.virtual_trading import VirtualTrader, VirtualTrade
from ..ai_event_pool import AIEventPool, EventPriority
from ..market_data_hub import MarketDataHub
from core.tg_bot.super_commander import SuperCommander

logger = logging.getLogger(__name__)

class VirtualTradingManager:
    """
    Manages virtual trading activities based on AI signals.
    Records trade outcomes and provides feedback to the AI system.
    """
    
    def __init__(self, 
                 config: Dict, 
                 event_pool: AIEventPool, 
                 market_data_hub: MarketDataHub,
                 intelligence_dispatcher: Optional[AIIntelligenceDispatcher] = None,
                 commander: Optional[SuperCommander] = None):
        """
        Initialize the virtual trading manager.
        
        Args:
            config: Configuration dictionary
            event_pool: AI Event Pool for receiving signals and publishing results
            market_data_hub: Market Data Hub for price data
            intelligence_dispatcher: Optional intelligence dispatcher for notifications
            commander: SuperCommander instance for command integration
        """
        self.config = config
        self.event_pool = event_pool
        self.market_data_hub = market_data_hub
        self.intelligence_dispatcher = intelligence_dispatcher
        self.commander = commander
        
        # Initialize virtual trader
        data_dir = config.get("data_dir", "data/virtual_trading")
        self.virtual_trader = VirtualTrader(data_dir=data_dir)
        
        # Trading settings
        self.auto_trade = config.get("auto_trade", False)
        self.risk_per_trade = config.get("risk_per_trade", 0.02)  # 2% risk per trade
        self.max_positions = config.get("max_positions", 5)
        
        # Setup directories
        self.reports_dir = Path(config.get("reports_dir", "data/reports"))
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        
        # Analytics
        self.trade_history_df = None
        self.performance_metrics = {}
        
        # Register event handlers
        self._register_event_handlers()
        
        # Register commands with SuperCommander if available
        if self.commander:
            self._register_commands()
        
        logger.info("Virtual Trading Manager initialized")
    
    def _register_event_handlers(self):
        """Register handlers for AI events"""
        if self.event_pool:
            self.event_pool.register_handler("TRADE_SIGNAL", self._handle_trade_signal)
            self.event_pool.register_handler("PRICE_UPDATE", self._handle_price_update)
            logger.info("Event handlers registered")
    
    def _handle_trade_signal(self, event_data: Dict):
        """
        Handle incoming trade signals from the AI system.
        
        Args:
            event_data: Trade signal event data
        """
        logger.info(f"Received trade signal: {event_data}")
        
        try:
            # Extract signal details
            symbol = event_data.get("symbol")
            action = event_data.get("action")
            price = event_data.get("price")
            confidence = event_data.get("confidence", 0.5)
            strategy = event_data.get("strategy", "AI_SIGNAL")
            risk_level = event_data.get("risk_level", "MEDIUM")
            
            # Validate required fields
            if not all([symbol, action, price]):
                logger.error(f"Invalid trade signal, missing required fields: {event_data}")
                return
            
            # Check if auto-trading is enabled
            if not self.auto_trade:
                self._notify_trade_signal(event_data)
                return
            
            # Process the trade signal
            if action.upper() == "BUY":
                quantity = self._calculate_position_size(symbol, price, risk_level)
                trade = self.virtual_trader.buy(
                    symbol=symbol,
                    price=price,
                    quantity=quantity,
                    strategy=strategy,
                    confidence=confidence,
                    risk_level=risk_level
                )
                if trade:
                    self._notify_trade_execution(trade, "BUY")
            
            elif action.upper() == "SELL":
                trade = self.virtual_trader.sell(
                    symbol=symbol,
                    price=price
                )
                if trade:
                    self._notify_trade_execution(trade, "SELL")
            
            # Update analytics
            self._update_analytics()
            
        except Exception as e:
            logger.error(f"Error processing trade signal: {str(e)}")
    
    def _handle_price_update(self, event_data: Dict):
        """
        Handle price updates to update portfolio values.
        
        Args:
            event_data: Price update event data
        """
        try:
            prices = {}
            for update in event_data.get("updates", []):
                symbol = update.get("symbol")
                price = update.get("price")
                if symbol and price:
                    prices[symbol] = price
            
            if prices:
                self.virtual_trader.update_prices(prices)
                logger.debug(f"Updated prices for {len(prices)} symbols")
        except Exception as e:
            logger.error(f"Error updating prices: {str(e)}")
    
    def _calculate_position_size(self, symbol: str, price: float, risk_level: str) -> float:
        """
        Calculate appropriate position size based on risk parameters.
        
        Args:
            symbol: Trading symbol
            price: Current price
            risk_level: Risk level (LOW, MEDIUM, HIGH)
            
        Returns:
            Quantity to trade
        """
        # Get portfolio value
        portfolio = self.virtual_trader.get_portfolio_summary()
        portfolio_value = portfolio.get("total_value", 100000)
        
        # Adjust risk based on risk level
        risk_multipliers = {
            "LOW": 0.5,
            "MEDIUM": 1.0,
            "HIGH": 2.0
        }
        risk_multiplier = risk_multipliers.get(risk_level, 1.0)
        
        # Calculate risk amount
        risk_amount = portfolio_value * self.risk_per_trade * risk_multiplier
        
        # Calculate quantity based on price and risk amount
        # Using a simplified approach - in real trading would include stop loss
        quantity = risk_amount / price
        
        # Round to appropriate precision
        quantity = round(quantity, 2)
        
        return max(quantity, 0.01)  # Ensure minimum quantity
    
    def _notify_trade_signal(self, event_data: Dict):
        """
        Notify users about a trade signal when auto-trading is disabled.
        
        Args:
            event_data: Trade signal event data
        """
        if self.intelligence_dispatcher:
            symbol = event_data.get("symbol")
            action = event_data.get("action")
            price = event_data.get("price")
            confidence = event_data.get("confidence", 0.5)
            
            title = f"{action} Signal: {symbol} @ ${price:.2f}"
            message = (
                f"Trading Signal Generated\n"
                f"Symbol: {symbol}\n"
                f"Action: {action}\n"
                f"Price: ${price:.2f}\n"
                f"Confidence: {confidence:.2f}\n\n"
                f"Auto-trading is disabled. This is for informational purposes only."
            )
            
            # Create AI insight for the notification
            self.event_pool.create_ai_insight(
                symbol=symbol,
                title=title,
                analysis=message,
                priority=EventPriority.HIGH,
                metadata=event_data
            )
    
    def _notify_trade_execution(self, trade: VirtualTrade, action: str):
        """
        Notify users about a virtual trade execution.
        
        Args:
            trade: The executed virtual trade
            action: Trade action (BUY/SELL)
        """
        if self.intelligence_dispatcher:
            title = f"Virtual {action}: {trade.symbol} @ ${trade.entry_price:.2f}"
            message = (
                f"Virtual Trade Executed\n"
                f"Symbol: {trade.symbol}\n"
                f"Action: {action}\n"
                f"Quantity: {trade.quantity:.2f}\n"
                f"Price: ${trade.entry_price:.2f}\n"
                f"Time: {trade.entry_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"Strategy: {trade.strategy}\n"
                f"Confidence: {trade.confidence:.2f}"
            )
            
            # If it's a sell/exit, include P&L information
            if action == "SELL" and trade.pnl is not None:
                message += f"\nP&L: ${trade.pnl:.2f} ({trade.pnl_pct:.2f}%)"
            
            # Create AI insight for the notification
            self.event_pool.create_ai_insight(
                symbol=trade.symbol,
                title=title,
                analysis=message,
                priority=EventPriority.HIGH,
                metadata=trade.to_dict()
            )
    
    def _update_analytics(self):
        """Update analytics data for reporting"""
        # Get completed trades and convert to DataFrame
        trades = self.virtual_trader.get_completed_trades()
        if trades:
            trade_dicts = [t.to_dict() for t in trades]
            self.trade_history_df = pd.DataFrame(trade_dicts)
            
            # Convert datetime strings back to datetime objects
            if 'entry_time' in self.trade_history_df.columns:
                self.trade_history_df['entry_time'] = pd.to_datetime(self.trade_history_df['entry_time'])
            if 'exit_time' in self.trade_history_df.columns:
                self.trade_history_df['exit_time'] = pd.to_datetime(self.trade_history_df['exit_time'])
        
        # Update performance metrics
        self.performance_metrics = self.virtual_trader.get_performance_metrics()
    
    def generate_daily_report(self) -> str:
        """
        Generate a daily trading performance report.
        
        Returns:
            Path to the generated report file
        """
        today = datetime.now().strftime("%Y-%m-%d")
        report_path = self.reports_dir / f"daily_report_{today}.csv"
        
        try:
            if self.trade_history_df is not None and not self.trade_history_df.empty:
                # Filter trades for today
                today_mask = self.trade_history_df['entry_time'].dt.date == datetime.now().date()
                today_trades = self.trade_history_df[today_mask]
                
                if not today_trades.empty:
                    today_trades.to_csv(report_path, index=False)
                    logger.info(f"Daily report generated: {report_path}")
                    
                    # Also create a summary JSON
                    summary = {
                        "date": today,
                        "total_trades": len(today_trades),
                        "winning_trades": len(today_trades[today_trades['pnl'] > 0]),
                        "losing_trades": len(today_trades[today_trades['pnl'] < 0]),
                        "net_pnl": today_trades['pnl'].sum(),
                        "win_rate": len(today_trades[today_trades['pnl'] > 0]) / len(today_trades) if len(today_trades) > 0 else 0,
                        "portfolio": self.virtual_trader.get_portfolio_summary()
                    }
                    
                    summary_path = self.reports_dir / f"daily_summary_{today}.json"
                    with open(summary_path, 'w') as f:
                        json.dump(summary, f, indent=2)
                    
                    return str(report_path)
            
            logger.info("No trades today to generate report")
            return ""
            
        except Exception as e:
            logger.error(f"Error generating daily report: {str(e)}")
            return ""
    
    def generate_weekly_report(self) -> str:
        """
        Generate a weekly trading performance report.
        
        Returns:
            Path to the generated report file
        """
        # Get current week number
        week_num = datetime.now().isocalendar()[1]
        year = datetime.now().year
        report_path = self.reports_dir / f"weekly_report_{year}_week{week_num}.csv"
        
        try:
            if self.trade_history_df is not None and not self.trade_history_df.empty:
                # Filter trades for this week
                # Get the start of the week (Monday)
                today = datetime.now().date()
                start_of_week = today - pd.Timedelta(days=today.weekday())
                
                week_mask = self.trade_history_df['entry_time'].dt.date >= start_of_week
                week_trades = self.trade_history_df[week_mask]
                
                if not week_trades.empty:
                    week_trades.to_csv(report_path, index=False)
                    logger.info(f"Weekly report generated: {report_path}")
                    
                    # Create a summary JSON
                    by_day = week_trades.groupby(week_trades['entry_time'].dt.date).agg({
                        'pnl': ['sum', 'count'],
                        'symbol': 'nunique'
                    })
                    
                    summary = {
                        "year": year,
                        "week": week_num,
                        "total_trades": len(week_trades),
                        "winning_trades": len(week_trades[week_trades['pnl'] > 0]),
                        "losing_trades": len(week_trades[week_trades['pnl'] < 0]),
                        "net_pnl": week_trades['pnl'].sum(),
                        "win_rate": len(week_trades[week_trades['pnl'] > 0]) / len(week_trades) if len(week_trades) > 0 else 0,
                        "daily_summary": by_day.to_dict(),
                        "performance_metrics": self.performance_metrics
                    }
                    
                    summary_path = self.reports_dir / f"weekly_summary_{year}_week{week_num}.json"
                    with open(summary_path, 'w') as f:
                        json.dump(summary, f, indent=2)
                    
                    return str(report_path)
            
            logger.info("No trades this week to generate report")
            return ""
            
        except Exception as e:
            logger.error(f"Error generating weekly report: {str(e)}")
            return ""
    
    def feed_results_to_ai(self):
        """
        Feed trading results back to the AI system for learning.
        This creates events that can be consumed by the AI learning components.
        """
        try:
            # Get performance data
            performance = self.virtual_trader.get_performance_metrics()
            
            # Create AI learning event
            learning_event = {
                "event_type": "AI_LEARNING_DATA",
                "timestamp": datetime.now().isoformat(),
                "performance_metrics": performance,
                "recent_trades": [t.to_dict() for t in self.virtual_trader.get_completed_trades()[-20:] if t],
                "portfolio_state": self.virtual_trader.get_portfolio_summary()
            }
            
            # Publish to event pool
            self.event_pool.publish_event("AI_LEARNING_DATA", learning_event)
            logger.info("Published trading results to AI learning system")
            
        except Exception as e:
            logger.error(f"Error feeding results to AI: {str(e)}")
    
    def stop(self):
        """Stop the virtual trading manager"""
        logger.info("Stopping Virtual Trading Manager...")
        # Save final data
        if hasattr(self.virtual_trader, '_save_data'):
            self.virtual_trader._save_data()
    
    def _register_commands(self):
        """Register trading commands with SuperCommander"""
        if not self.commander:
            return
            
        # Register trading commands
        self.commander.register_command(
            "get_portfolio",
            self.virtual_trader.get_portfolio_summary,
            "Get current portfolio summary",
            []
        )
        
        self.commander.register_command(
            "get_trade_history",
            self.virtual_trader.get_trade_history,
            "Get trade history",
            ["limit"]
        )
        
        self.commander.register_command(
            "get_daily_report",
            self.generate_daily_report,
            "Generate daily trading report",
            []
        )
        
        self.commander.register_command(
            "get_weekly_report",
            self.generate_weekly_report,
            "Generate weekly trading report",
            []
        )
        
        self.commander.register_command(
            "set_auto_trade",
            self._set_auto_trade,
            "Enable/disable auto-trading",
            ["enabled"]
        )
        
        logger.info("Trading commands registered with SuperCommander")
        
    def _set_auto_trade(self, enabled: bool):
        """Enable or disable auto-trading
        
        Args:
            enabled: Whether to enable auto-trading
        """
        self.auto_trade = enabled
        logger.info(f"Auto-trading {'enabled' if enabled else 'disabled'}") 