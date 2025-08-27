"""
Routine Scheduler

Coordinates and schedules routine operations of the WarMachine AI system, including:
- Data collection
- Market analysis
- Periodic reports
- System maintenance
"""

import os
import logging
import time
import threading
import schedule
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union, Callable
import json

from ..ai_event_pool import EventPriority
from core.tg_bot.super_commander import SuperCommander

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class RoutineScheduler:
    """Scheduler for system routines and tasks"""
    
    def __init__(self, config: Dict[str, Any], components: Dict[str, Any]):
        """
        Initialize the routine scheduler
        
        Args:
            config: Configuration dictionary
            components: Dictionary of system components
        """
        self.config = config
        self.components = components
        
        # Extract components
        self.data_hub = components.get("data_hub")
        self.event_pool = components.get("event_pool")
        self.intelligence_dispatcher = components.get("intelligence_dispatcher")
        self.liquidity_sniper = components.get("liquidity_sniper")
        
        # Schedule settings
        self.market_hours = config.get("market_hours", {
            "open": "09:30",
            "close": "16:00",
            "timezone": "America/New_York"
        })
        self.market_days = config.get("market_days", ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"])
        self.extended_hours = config.get("extended_hours", False)
        
        # Schedule storage
        self.scheduled_tasks = {}
        self.is_market_open = False
        
        # Initialize schedule
        self._initialize_schedule()
        
        # Start the scheduler thread
        self.running = False
        self._shutdown_event = threading.Event()
        self.scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        
        logger.info("Routine Scheduler initialized")
    
    async def start(self):
        """Start the scheduler"""
        self.running = True
        self._shutdown_event.clear()
        logger.info("Routine Scheduler started")
    
    async def shutdown(self):
        """Shutdown the scheduler"""
        logger.info("Shutting down Routine Scheduler...")
        self.running = False
        self._shutdown_event.set()
        logger.info("Routine Scheduler shutdown complete")
    
    def _initialize_schedule(self):
        """Initialize the task schedule"""
        # Clear any existing schedules
        schedule.clear()
        
        # Market open routines
        schedule.every().day.at(self.market_hours["open"]).do(self._market_open_routine)
        
        # Market close routines
        schedule.every().day.at(self.market_hours["close"]).do(self._market_close_routine)
        
        # Regular market hour routines
        schedule.every(5).minutes.do(self._periodic_market_analysis)
        schedule.every(15).minutes.do(self._generate_status_report)
        schedule.every(60).minutes.do(self._hourly_summary)
        
        # Daily maintenance (after hours)
        maintenance_time = (datetime.strptime(self.market_hours["close"], "%H:%M") + timedelta(hours=1)).strftime("%H:%M")
        schedule.every().day.at(maintenance_time).do(self._daily_maintenance)
        
        logger.info("Schedule initialized")
    
    def _scheduler_loop(self):
        """Main scheduler loop"""
        while self.running:
            try:
                # Run pending scheduled tasks
                schedule.run_pending()
                
                # Sleep briefly
                time.sleep(1)
            except Exception as e:
                logger.error(f"Error in scheduler loop: {str(e)}")
                time.sleep(5)  # Longer sleep on error
    
    def _market_open_routine(self):
        """Tasks to run at market open"""
        # Check if today is a market day
        if datetime.now().strftime("%A") not in self.market_days:
            return
        
        logger.info("Running market open routine")
        self.is_market_open = True
        
        try:
            # Generate market open report
            self._generate_market_open_report()
            
            # Initialize data subscriptions for the day
            if self.data_hub:
                self._initialize_data_subscriptions()
            
        except Exception as e:
            logger.error(f"Error in market open routine: {str(e)}")
    
    def _market_close_routine(self):
        """Tasks to run at market close"""
        # Check if today is a market day
        if datetime.now().strftime("%A") not in self.market_days:
            return
        
        logger.info("Running market close routine")
        self.is_market_open = False
        
        try:
            # Generate end of day summary
            self._generate_market_close_report()
            
        except Exception as e:
            logger.error(f"Error in market close routine: {str(e)}")
    
    def _periodic_market_analysis(self):
        """Regular market analysis routine"""
        # Only run during market hours
        if not self._is_during_market_hours():
            return
        
        logger.debug("Running periodic market analysis")
        
        try:
            # Update market data
            if self.data_hub:
                for symbol in self.config.get("symbols", []):
                    # Get latest data
                    self.data_hub.get_stock_data(symbol, "1m", 10)
                    self.data_hub.get_order_book(symbol)
            
            # Run additional analyses as needed
            
        except Exception as e:
            logger.error(f"Error in periodic market analysis: {str(e)}")
    
    def _generate_status_report(self):
        """Generate a system status report"""
        # Only run during market hours
        if not self._is_during_market_hours():
            return
        
        logger.debug("Generating status report")
        
        try:
            if self.event_pool and self.intelligence_dispatcher:
                # Generate system status event
                self._create_system_status_event()
            
        except Exception as e:
            logger.error(f"Error generating status report: {str(e)}")
    
    def _hourly_summary(self):
        """Generate an hourly market summary"""
        # Only run during market hours
        if not self._is_during_market_hours():
            return
        
        logger.info("Generating hourly market summary")
        
        try:
            if self.event_pool:
                # Get current time
                current_time = datetime.now().strftime("%H:%M")
                
                # Generate summary
                title = f"Hourly Market Update - {current_time}"
                content = self._generate_market_summary_content()
                
                # Create event
                from ...ai_event_pool import EventPriority
                self.event_pool.create_ai_insight(
                    symbol="MARKET",
                    title=title,
                    analysis=content,
                    priority=EventPriority.MEDIUM
                )
            
        except Exception as e:
            logger.error(f"Error generating hourly summary: {str(e)}")
    
    def _daily_maintenance(self):
        """Daily system maintenance tasks"""
        # Check if today was a market day
        if datetime.now().strftime("%A") not in self.market_days:
            return
        
        logger.info("Running daily maintenance")
        
        try:
            # Clean up data caches
            if self.data_hub:
                # Save important data to disk
                for symbol in self.config.get("symbols", []):
                    self.data_hub.save_to_cache("stock_bars", symbol, "1d")
            
            # Update system configuration if needed
            self._check_for_config_updates()
            
        except Exception as e:
            logger.error(f"Error in daily maintenance: {str(e)}")
    
    def _initialize_data_subscriptions(self):
        """Initialize data subscriptions for all monitored symbols"""
        if not self.data_hub:
            return
        
        # Stock symbols
        symbols = self.config.get("symbols", [])
        for symbol in symbols:
            # Subscribe to key data types
            from market_data_hub import DataType
            self.data_hub.subscribe_market_data(symbol, DataType.STOCK_BARS)
            self.data_hub.subscribe_market_data(symbol, DataType.STOCK_QUOTES)
            self.data_hub.subscribe_market_data(symbol, DataType.ORDER_BOOK)
            self.data_hub.subscribe_market_data(symbol, DataType.OPTION_CHAIN)
        
        # Crypto symbols
        crypto_symbols = self.config.get("crypto_symbols", [])
        for symbol in crypto_symbols:
            self.data_hub.subscribe_market_data(symbol, DataType.CRYPTO_BARS)
            self.data_hub.subscribe_market_data(symbol, DataType.CRYPTO_QUOTES)
            self.data_hub.subscribe_market_data(symbol, DataType.ORDER_BOOK)
        
        logger.info(f"Initialized data subscriptions for {len(symbols)} stocks and {len(crypto_symbols)} crypto symbols")
    
    def _generate_market_open_report(self):
        """Generate a market open report"""
        if not self.event_pool:
            return
        
        try:
            # Get information about major indices
            indices_data = self._get_indices_data()
            
            # Generate title and content
            title = f"Market Open Report - {datetime.now().strftime('%Y-%m-%d')}"
            
            content = f"# Market Open Report\n\n"
            content += f"## Market Overview\n\n"
            
            # Add index data
            for symbol, data in indices_data.items():
                content += f"**{symbol}**: ${data['price']:.2f} ({data['change']:+.2f}%)\n"
            
            content += f"\n## Pre-Market Highlights\n\n"
            
            # Add futures info if available
            content += f"- S&P 500 Futures: {indices_data.get('ES', {}).get('change', 0):+.2f}%\n"
            content += f"- Nasdaq Futures: {indices_data.get('NQ', {}).get('change', 0):+.2f}%\n"
            
            content += f"\n## Key Events Today\n\n"
            
            # Add scheduled economic events
            content += "- (Check economic calendar for today's events)\n"
            
            # Add earnings
            content += f"\n## Notable Earnings\n\n"
            content += "- (Check earnings calendar for today's reports)\n"
            
            # Create event
            from ...ai_event_pool import EventPriority
            self.event_pool.create_ai_insight(
                symbol="MARKET",
                title=title,
                analysis=content,
                priority=EventPriority.HIGH
            )
            
            logger.info("Generated market open report")
            
        except Exception as e:
            logger.error(f"Error generating market open report: {str(e)}")
    
    def _generate_market_close_report(self):
        """Generate a market close report"""
        if not self.event_pool:
            return
        
        try:
            # Get information about major indices
            indices_data = self._get_indices_data()
            
            # Generate title and content
            title = f"Market Close Report - {datetime.now().strftime('%Y-%m-%d')}"
            
            content = f"# Market Close Report\n\n"
            content += f"## Market Summary\n\n"
            
            # Add index data
            for symbol, data in indices_data.items():
                content += f"**{symbol}**: ${data['price']:.2f} ({data['change']:+.2f}%)\n"
            
            content += f"\n## Sector Performance\n\n"
            
            # Try to get sector ETF data
            sectors = ["XLK", "XLF", "XLE", "XLV", "XLI", "XLP", "XLY", "XLU", "XLB", "XLRE"]
            sector_names = {
                "XLK": "Technology", "XLF": "Financials", "XLE": "Energy", 
                "XLV": "Healthcare", "XLI": "Industrials", "XLP": "Consumer Staples",
                "XLY": "Consumer Discretionary", "XLU": "Utilities", "XLB": "Materials", 
                "XLRE": "Real Estate"
            }
            
            sector_data = {}
            if self.data_hub:
                for symbol in sectors:
                    try:
                        df = self.data_hub.get_stock_data(symbol, "1d", 2)
                        if not df.empty and len(df) >= 2:
                            prev_close = df.iloc[-2]["close"]
                            close = df.iloc[-1]["close"]
                            change = (close - prev_close) / prev_close * 100
                            sector_data[symbol] = {
                                "name": sector_names.get(symbol, symbol),
                                "change": change
                            }
                    except:
                        pass
            
            # Sort sectors by performance
            sorted_sectors = sorted(sector_data.items(), key=lambda x: x[1]["change"], reverse=True)
            
            # Add top 3 and bottom 3 sectors
            content += "**Top Performing Sectors:**\n"
            for symbol, data in sorted_sectors[:3]:
                content += f"- {data['name']}: {data['change']:+.2f}%\n"
            
            content += "\n**Worst Performing Sectors:**\n"
            for symbol, data in sorted_sectors[-3:]:
                content += f"- {data['name']}: {data['change']:+.2f}%\n"
            
            content += f"\n## Notable Movers\n\n"
            
            # Try to add notable stock moves
            # This would be enhanced with a more comprehensive market scanner
            
            content += f"\n## Market Intelligence\n\n"
            
            # Try to add count of events from today
            if self.event_pool:
                # You would need to implement a method to get today's events by category
                content += "- Intelligence events will be summarized here\n"
            
            # Create event
            from ...ai_event_pool import EventPriority
            self.event_pool.create_ai_insight(
                symbol="MARKET",
                title=title,
                analysis=content,
                priority=EventPriority.HIGH
            )
            
            logger.info("Generated market close report")
            
        except Exception as e:
            logger.error(f"Error generating market close report: {str(e)}")
    
    def _get_indices_data(self) -> Dict[str, Dict[str, float]]:
        """Get data for major market indices"""
        indices = {
            "SPY": "S&P 500",
            "QQQ": "Nasdaq",
            "DIA": "Dow Jones",
            "IWM": "Russell 2000"
        }
        
        result = {}
        
        if self.data_hub:
            for symbol in indices.keys():
                try:
                    df = self.data_hub.get_stock_data(symbol, "1d", 2)
                    if not df.empty and len(df) >= 2:
                        prev_close = df.iloc[-2]["close"]
                        close = df.iloc[-1]["close"]
                        change = (close - prev_close) / prev_close * 100
                        result[symbol] = {
                            "name": indices[symbol],
                            "price": close,
                            "change": change
                        }
                except:
                    # Default values if data not available
                    result[symbol] = {
                        "name": indices[symbol],
                        "price": 0.0,
                        "change": 0.0
                    }
        
        return result
    
    def _generate_market_summary_content(self) -> str:
        """Generate summary content for market reports"""
        content = f"Market Summary as of {datetime.now().strftime('%Y-%m-%d %H:%M')}:\n\n"
        
        # Add index data
        indices_data = self._get_indices_data()
        for symbol, data in indices_data.items():
            content += f"{data['name']}: ${data['price']:.2f} ({data['change']:+.2f}%)\n"
        
        content += "\n"
        
        # Add intelligence summary if available
        if self.liquidity_sniper:
            # The implementation would depend on your LiquiditySniper class
            # You might want to add methods to get summary statistics
            content += "Recent Market Intelligence:\n"
            content += "- Liquidity data will be summarized here\n"
            content += "- Whale alerts will be summarized here\n"
            content += "- Option activity will be summarized here\n"
        
        return content
    
    def _create_system_status_event(self):
        """Create a system status event"""
        if not self.event_pool:
            return
        
        from ...ai_event_pool import EventPriority
        
        # Get component statuses
        components_status = {}
        for name, component in self.components.items():
            status = "active" if component else "inactive"
            components_status[name] = status
        
        # Create event
        self.event_pool.create_ai_insight(
            symbol="SYSTEM",
            title="System Status Update",
            analysis=f"System status as of {datetime.now().isoformat()}:\n\n" + 
                    "\n".join([f"- {name}: {status}" for name, status in components_status.items()]),
            priority=EventPriority.LOW,
            metadata={
                "components": components_status,
                "timestamp": datetime.now().isoformat()
            }
        )
    
    def _check_for_config_updates(self):
        """Check for and apply configuration updates"""
        config_path = self.config.get("config_path", "config/warmachine_config.json")
        
        try:
            # Re-read configuration file
            with open(config_path, "r") as f:
                updated_config = json.load(f)
            
            # Check if configuration has changed
            if updated_config != self.config:
                logger.info("Detected configuration changes, updating...")
                self.config = updated_config
                
                # Reinitialize schedule
                self._initialize_schedule()
        except Exception as e:
            logger.error(f"Error checking for config updates: {str(e)}")
    
    def _is_during_market_hours(self) -> bool:
        """Check if current time is during market hours"""
        # Get current day and time
        now = datetime.now()
        current_day = now.strftime("%A")
        current_time = now.strftime("%H:%M")
        
        # Check if it's a market day
        if current_day not in self.market_days:
            return False
        
        # Parse market hours
        market_open = self.market_hours["open"]
        market_close = self.market_hours["close"]
        
        # Check if within market hours
        if market_open <= current_time <= market_close:
            return True
        
        # Check extended hours if enabled
        if self.extended_hours:
            extended_open = (datetime.strptime(market_open, "%H:%M") - timedelta(hours=1.5)).strftime("%H:%M")
            extended_close = (datetime.strptime(market_close, "%H:%M") + timedelta(hours=1.5)).strftime("%H:%M")
            
            if extended_open <= current_time <= extended_close:
                return True
        
        return False
    
    def add_task(self, name: str, task: Callable, schedule_str: str):
        """
        Add a custom task to the scheduler
        
        Args:
            name: Task name
            task: Function to call
            schedule_str: Schedule string (e.g., 'every().day.at("10:30")')
        """
        try:
            # Parse and add to schedule
            task_schedule = eval(f"schedule.{schedule_str}")
            task_schedule.do(task)
            
            # Store in tasks
            self.scheduled_tasks[name] = task
            
            logger.info(f"Added task '{name}' with schedule: {schedule_str}")
        except Exception as e:
            logger.error(f"Error adding task '{name}': {str(e)}")
    
    def remove_task(self, name: str):
        """
        Remove a task from the scheduler
        
        Args:
            name: Task name
        """
        if name in self.scheduled_tasks:
            # Remove from schedule
            schedule.clear(name)
            
            # Remove from tasks
            del self.scheduled_tasks[name]
            
            logger.info(f"Removed task '{name}'")

# For testing
if __name__ == "__main__":
    # Load config
    with open("config/warmachine_config.json", "r") as f:
        config = json.load(f)
    
    # Create components
    from market_data_hub import MarketDataHub
    from ai_event_pool import AIEventPool
    
    data_hub = MarketDataHub(config.get("market_data", {}))
    event_pool = AIEventPool(config.get("event_pool", {}))
    
    # Create components dictionary
    components = {
        "data_hub": data_hub,
        "event_pool": event_pool,
        "intelligence_dispatcher": None,
        "liquidity_sniper": None
    }
    
    # Create scheduler
    scheduler = RoutineScheduler(config, components)
    
    # Run for a while
    try:
        print("Routine Scheduler running. Press Ctrl+C to stop.")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        scheduler.shutdown()
        print("Stopped.") 