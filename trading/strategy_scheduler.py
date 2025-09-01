import argparse
import logging
import time
import json
import os
import signal
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
import schedule
import yaml
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Add project root to path
project_root = str(Path(__file__).parent)
if project_root not in sys.path:
    sys.path.append(project_root)

from utils.strategy_executor import StrategyExecutor
from utils.unified_notifier import NotificationConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("strategy_scheduler.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("StrategyScheduler")

class StrategyScheduler:
    """
    Scheduler for running trading strategies at regular intervals.
    Manages the execution, result storage, and notification processes.
    """
    
    def __init__(self, config_path: str = "config/signal_config.yaml"):
        """
        Initialize the strategy scheduler.
        
        Args:
            config_path (str): Path to the configuration file
        """
        self.config_path = config_path
        self.config = self._load_config()
        self.running = False
        self.executor = None
        self.last_run_times = {}  # Symbol -> last run time
        self.results_history = {}  # Symbol -> list of results
        
        # Initialize signal storage
        self.signals_dir = Path("data/signals")
        self.signals_dir.mkdir(exist_ok=True, parents=True)
        
        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)
        
        logger.info(f"StrategyScheduler initialized with config from {config_path}")
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        try:
            if not os.path.exists(self.config_path):
                logger.warning(f"Config file {self.config_path} not found, using default config")
                return {
                    'symbols': ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'TSLA'],
                    'interval': 300,  # 5 minutes
                    'min_confidence': 0.7,
                    'risk_levels': {
                        'LOW': 0.3,
                        'MEDIUM': 0.6,
                        'HIGH': 1.0
                    },
                    'notification': {
                        'telegram_enabled': True,
                        'feishu_enabled': False,
                        'min_confidence': 0.7
                    },
                    'intervals': {
                        'default': 300,  # 5 minutes
                        'extended': 900,  # 15 minutes
                        'off_hours': 3600  # 1 hour
                    },
                    'market_hours': {
                        'start': '09:30',
                        'end': '16:00',
                        'timezone': 'America/New_York'
                    },
                    'preset_strategies': ['trend_following', 'breakout', 'sector_divergence'],
                    'data_source': 'databento'  # or 'yfinance'
                }
            
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Error loading config: {str(e)}")
            raise
    
    def _initialize_executor(self):
        """Initialize the strategy executor with current configuration"""
        # Create notification config
        notification_config = NotificationConfig(
            telegram_enabled=self.config.get('notification', {}).get('telegram_enabled', True),
            feishu_enabled=self.config.get('notification', {}).get('feishu_enabled', False),
            min_confidence=self.config.get('notification', {}).get('min_confidence', 0.7)
        )
        
        # Create executor
        self.executor = StrategyExecutor(
            symbols=self.config.get('symbols', []),
            interval=self.config.get('interval', 300),
            min_confidence=self.config.get('min_confidence', 0.7),
            risk_levels=self.config.get('risk_levels', {}),
            notification_config=notification_config
        )
        
        # Load any saved signals
        self._load_signal_history()
        
        logger.info("Strategy executor initialized")
    
    def _save_signal_history(self):
        """Save all signals to individual JSON files by symbol and date"""
        if not self.executor:
            return
            
        for symbol, signals in self.executor.signal_history.items():
            if not signals:
                continue
                
            # Group signals by date
            signals_by_date = {}
            for signal in signals:
                date_str = signal.timestamp.strftime('%Y-%m-%d')
                if date_str not in signals_by_date:
                    signals_by_date[date_str] = []
                signals_by_date[date_str].append(signal.to_dict())
            
            # Save each date's signals to a separate file
            for date_str, date_signals in signals_by_date.items():
                symbol_dir = self.signals_dir / symbol
                symbol_dir.mkdir(exist_ok=True)
                
                file_path = symbol_dir / f"{date_str}.json"
                with open(file_path, 'w') as f:
                    json.dump(date_signals, f, indent=2)
                    
            logger.info(f"Saved {len(signals)} signals for {symbol}")
    
    def _load_signal_history(self):
        """Load saved signals from JSON files"""
        if not self.executor:
            return
            
        # Get all symbol directories
        for symbol_dir in self.signals_dir.iterdir():
            if not symbol_dir.is_dir():
                continue
                
            symbol = symbol_dir.name
            signals = []
            
            # Load all date files for this symbol
            for date_file in symbol_dir.glob("*.json"):
                try:
                    with open(date_file, 'r') as f:
                        date_signals = json.load(f)
                        for signal_dict in date_signals:
                            from utils.strategy_executor import Signal
                            signal = Signal(
                                symbol=signal_dict["symbol"],
                                action=signal_dict["action"],
                                confidence=signal_dict["confidence"],
                                timestamp=datetime.fromisoformat(signal_dict["timestamp"]),
                                risk_level=signal_dict.get("risk_level", "MEDIUM"),
                                final_score=signal_dict.get("final_score", 0.0),
                                reasoning=signal_dict.get("reasoning", ""),
                                recommendation=signal_dict.get("recommendation", ""),
                                strategy_type=signal_dict.get("strategy_type", "")
                            )
                            signals.append(signal)
                except Exception as e:
                    logger.error(f"Error loading signals from {date_file}: {str(e)}")
            
            # Add signals to executor
            if symbol not in self.executor.signal_history:
                self.executor.signal_history[symbol] = []
            self.executor.signal_history[symbol].extend(signals)
            
            logger.info(f"Loaded {len(signals)} signals for {symbol}")
    
    def _is_market_hours(self) -> bool:
        """Check if current time is within market hours"""
        # Get market hours from config
        market_hours = self.config.get('market_hours', {})
        start_time_str = market_hours.get('start', '09:30')
        end_time_str = market_hours.get('end', '16:00')
        
        # Parse times
        try:
            from datetime import datetime
            now = datetime.now()
            
            # Parse start and end times
            start_hour, start_min = map(int, start_time_str.split(':'))
            end_hour, end_min = map(int, end_time_str.split(':'))
            
            # Create datetime objects for today's market hours
            start_time = now.replace(hour=start_hour, minute=start_min, second=0, microsecond=0)
            end_time = now.replace(hour=end_hour, minute=end_min, second=0, microsecond=0)
            
            # Check if current time is within market hours
            return start_time <= now <= end_time
        except Exception as e:
            logger.error(f"Error checking market hours: {str(e)}")
            return True  # Default to assuming market is open
    
    def _get_run_interval(self) -> int:
        """Get the interval to run strategies based on current time"""
        intervals = self.config.get('intervals', {})
        
        # Check if market is open
        if self._is_market_hours():
            return intervals.get('default', 300)  # 5 minutes during market hours
        else:
            return intervals.get('off_hours', 3600)  # 1 hour outside market hours
    
    def _execute_strategies(self, symbols: Optional[List[str]] = None):
        """Execute strategies for specified symbols or all configured symbols"""
        if not self.executor:
            logger.error("Strategy executor not initialized")
            return
        
        # Use specified symbols or all configured symbols
        symbols_to_run = symbols or self.config.get('symbols', [])
        if not symbols_to_run:
            logger.warning("No symbols configured to run")
            return
        
        # Get current time
        now = datetime.now()
        
        # Execute strategies for each symbol
        logger.info(f"Executing strategies for {len(symbols_to_run)} symbols")
        results = self.executor.batch_execute(symbols_to_run)
        
        # Update last run times
        for symbol in symbols_to_run:
            self.last_run_times[symbol] = now
        
        # Save results to history
        for symbol, result in results.items():
            if symbol not in self.results_history:
                self.results_history[symbol] = []
            self.results_history[symbol].append({
                'timestamp': now.isoformat(),
                'result': result
            })
        
        # Save signal history
        self._save_signal_history()
        
        logger.info(f"Executed strategies for {len(symbols_to_run)} symbols")
        return results
    
    def _schedule_jobs(self):
        """Schedule jobs based on configuration"""
        # Clear existing jobs
        schedule.clear()
        
        # Get run interval
        interval = self._get_run_interval()
        
        # Convert to minutes for schedule
        interval_minutes = max(1, interval // 60)
        
        # Schedule job to run every X minutes
        schedule.every(interval_minutes).minutes.do(self._execute_strategies)
        
        # Schedule job to check and update intervals every hour
        schedule.every(1).hour.do(self._update_schedule)
        
        logger.info(f"Scheduled to run every {interval_minutes} minutes")
    
    def _update_schedule(self):
        """Update schedule based on current time and market hours"""
        # Clear existing jobs
        schedule.clear()
        
        # Re-schedule jobs
        self._schedule_jobs()
        
        logger.info("Updated schedule based on current time")
    
    def _handle_shutdown(self, signum, frame):
        """Handle shutdown signals"""
        logger.info("Received shutdown signal, stopping...")
        self.stop()
        sys.exit(0)
    
    def start(self):
        """Start the scheduler"""
        if self.running:
            logger.warning("Scheduler is already running")
            return
        
        # Initialize executor
        self._initialize_executor()
        
        # Schedule jobs
        self._schedule_jobs()
        
        # Mark as running
        self.running = True
        
        # Run initially for all symbols
        self._execute_strategies()
        
        logger.info("Scheduler started")
        
        # Run the scheduler loop
        while self.running:
            schedule.run_pending()
            time.sleep(1)
    
    def stop(self):
        """Stop the scheduler"""
        if not self.running:
            logger.warning("Scheduler is not running")
            return
        
        # Mark as not running
        self.running = False
        
        # Save signal history
        if self.executor:
            self._save_signal_history()
        
        logger.info("Scheduler stopped")
    
    def run_once(self, symbols: Optional[List[str]] = None):
        """Run strategies once for specified symbols"""
        # Initialize executor if needed
        if not self.executor:
            self._initialize_executor()
        
        # Execute strategies
        results = self._execute_strategies(symbols)
        
        return results

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Strategy Scheduler")
    parser.add_argument("--config", type=str, default="config/signal_config.yaml",
                        help="Path to configuration file")
    parser.add_argument("--symbols", type=str, nargs="+",
                        help="Symbols to run strategies for (overrides config)")
    parser.add_argument("--run-once", action="store_true",
                        help="Run strategies once and exit")
    parser.add_argument("--interval", type=int,
                        help="Override interval in seconds")
    
    args = parser.parse_args()
    
    # Create scheduler
    scheduler = StrategyScheduler(config_path=args.config)
    
    # Override interval if specified
    if args.interval:
        scheduler.config['interval'] = args.interval
    
    # Override symbols if specified
    if args.symbols:
        scheduler.config['symbols'] = args.symbols
    
    try:
        if args.run_once:
            # Run once and exit
            logger.info("Running strategies once")
            results = scheduler.run_once()
            logger.info(f"Completed with {len(results)} results")
        else:
            # Start the scheduler
            logger.info("Starting scheduler")
            scheduler.start()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Error running scheduler: {str(e)}")
    finally:
        # Make sure to stop the scheduler
        scheduler.stop()

if __name__ == "__main__":
    main() 