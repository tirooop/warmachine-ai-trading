#!/usr/bin/env python
"""
WarMachine AI Trading System

Runs the integrated AI trading system with virtual trading capabilities,
automatic AI learning, and performance reporting.
"""

import os
import sys
import json
import time
import signal
import logging
import argparse
from datetime import datetime
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(f"logs/ai_trading_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    ]
)
logger = logging.getLogger(__name__)

# Ensure directories exist
def ensure_directories_exist():
    """Ensure required directories exist"""
    directories = ['logs', 'data', 'data/virtual_trading', 'data/reports', 'data/models', 'data/insights']
    for directory in directories:
        os.makedirs(directory, exist_ok=True)

# Banner display
def display_banner():
    """Display a fancy banner for the system startup"""
    banner = """
 __      __          __  __            _     _            
 \ \    / /         |  \/  |          | |   (_)           
  \ \  / /_ _ _ __  | \  / | __ _  ___| |__  _ _ __   ___ 
   \ \/ / _` | '__| | |\/| |/ _` |/ __| '_ \| | '_ \ / _ \\
    \  / (_| | |    | |  | | (_| | (__| | | | | | | |  __/
     \/ \__,_|_|    |_|  |_|\__,_|\___|_| |_|_|_| |_|\___|
                                                           
              AI Trading System v1.0.0                    
    """
    print(banner)
    print("=" * 60)
    print(f"Starting AI Trading System at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

# Load configuration
def load_config(config_path="config/warmachine_config.json"):
    """Load the system configuration from file"""
    try:
        if not os.path.exists(config_path):
            logger.warning(f"Configuration file not found: {config_path}")
            return create_default_config()
            
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        logger.info(f"Configuration loaded from {config_path}")
        
        # Make sure trading system config exists
        if 'trading_system' not in config:
            config['trading_system'] = create_default_trading_config()
        
        return config
    except Exception as e:
        logger.error(f"Error loading configuration: {str(e)}")
        return create_default_config()

def create_default_config():
    """Create a default configuration"""
    config = {
        "system": {
            "version": "1.0.0",
            "data_dir": "data",
            "cache_dir": "cache",
            "log_dir": "logs"
        },
        "market_data": {
            "providers": {
                "polygon": {
                    "enabled": True,
                    "api_key": "YOUR_POLYGON_API_KEY"
                },
                "binance": {
                    "enabled": False
                },
                "alpha_vantage": {
                    "enabled": True,
                    "api_key": "YOUR_ALPHA_VANTAGE_API_KEY"
                }
            }
        },
        "trading_system": create_default_trading_config()
    }
    
    return config

def create_default_trading_config():
    """Create default trading system configuration"""
    return {
        "enabled": True,
        "virtual_trading_manager": {
            "auto_trade": True,
            "risk_per_trade": 0.02,  # 2% risk per trade
            "max_positions": 5,
            "data_dir": "data/virtual_trading",
            "reports_dir": "data/reports"
        },
        "ai_feedback_learner": {
            "learning_enabled": True,
            "min_trades_for_learning": 20,
            "learning_interval": 24,  # hours
            "models_dir": "data/models",
            "insights_dir": "data/insights"
        }
    }

def save_config(config, config_path="config/warmachine_config.json"):
    """Save the configuration to file"""
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        logger.info(f"Configuration saved to {config_path}")
        return True
    except Exception as e:
        logger.error(f"Error saving configuration: {str(e)}")
        return False

def initialize_system(config, args):
    """Initialize the WarMachine system and trading components"""
    try:
        # Import core system components
        from warmachine.market_data_hub import MarketDataHub
        from warmachine.ai_event_pool import AIEventPool
        from warmachine.ai_intelligence_dispatcher import AIIntelligenceDispatcher
        from warmachine.ai_model_router import AIModelRouter
        
        # Import trading system components
        from warmachine.trading.trading_system_integrator import TradingSystemIntegrator
        
        # Components dictionary
        components = {}
        
        # Initialize core components
        logger.info("Initializing Market Data Hub...")
        data_hub = MarketDataHub(config.get("market_data", {}))
        components["data_hub"] = data_hub
        
        logger.info("Initializing AI Event Pool...")
        event_pool = AIEventPool(config.get("event_pool", {}))
        components["event_pool"] = event_pool
        
        logger.info("Initializing AI Intelligence Dispatcher...")
        intelligence_dispatcher = AIIntelligenceDispatcher(
            config.get("intelligence_dispatcher", {}),
            event_pool
        )
        components["intelligence_dispatcher"] = intelligence_dispatcher
        
        # Initialize AI Model Router if enabled (for AI feedback)
        ai_model_router = None
        if config.get("ai_models", {}).get("enabled", True):
            logger.info("Initializing AI Model Router...")
            ai_model_router = AIModelRouter(config.get("ai_models", {}))
            components["ai_model_router"] = ai_model_router
        
        # Initialize Trading System Integrator
        logger.info("Initializing Trading System Integrator...")
        trading_system = TradingSystemIntegrator(config)
        if trading_system.initialize_components(
            market_data_hub=data_hub,
            event_pool=event_pool,
            intelligence_dispatcher=intelligence_dispatcher,
            ai_model_router=ai_model_router
        ):
            components["trading_system"] = trading_system
            logger.info("Trading System initialized successfully")
        else:
            logger.error("Failed to initialize Trading System")
        
        return components
    except Exception as e:
        logger.error(f"Error initializing system: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return None

def start_system(components):
    """Start all system components"""
    try:
        # Start components in the right order
        for name in ["data_hub", "event_pool", "intelligence_dispatcher", "ai_model_router"]:
            if name in components:
                component = components[name]
                if hasattr(component, 'start'):
                    logger.info(f"Starting {name}...")
                    component.start()
        
        # Start trading system last
        if "trading_system" in components:
            logger.info("Starting Trading System...")
            components["trading_system"].start()
        
        logger.info("All components started successfully")
        return True
    except Exception as e:
        logger.error(f"Error starting system: {str(e)}")
        return False

def stop_system(components):
    """Stop all system components"""
    try:
        # Stop in reverse order of starting
        if "trading_system" in components:
            logger.info("Stopping Trading System...")
            components["trading_system"].stop()
        
        # Stop other components
        for name in ["ai_model_router", "intelligence_dispatcher", "event_pool", "data_hub"]:
            if name in components:
                component = components[name]
                if hasattr(component, 'stop'):
                    logger.info(f"Stopping {name}...")
                    component.stop()
        
        logger.info("All components stopped successfully")
        return True
    except Exception as e:
        logger.error(f"Error stopping system: {str(e)}")
        return False

def run_system(config, args):
    """Run the system until interrupted"""
    # Make sure directories exist
    ensure_directories_exist()
    
    # Display banner
    display_banner()
    
    # Initialize components
    components = initialize_system(config, args)
    if not components:
        logger.error("Failed to initialize system, exiting")
        return False
    
    # Set up signal handlers for graceful shutdown
    def signal_handler(sig, frame):
        logger.info("Shutdown signal received, stopping components...")
        stop_system(components)
        sys.exit(0)
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start components
    start_result = start_system(components)
    if not start_result:
        logger.error("Failed to start system, exiting")
        stop_system(components)
        return False
    
    # Keep the script running until Ctrl+C
    logger.info("System running. Press Ctrl+C to exit")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received, stopping components...")
        stop_system(components)
    
    return True

def manual_signal(config, args):
    """Process a manual trading signal"""
    # Make sure directories exist
    ensure_directories_exist()
    
    # Initialize components
    components = initialize_system(config, args)
    if not components:
        logger.error("Failed to initialize system, exiting")
        return False
    
    # Start components
    start_result = start_system(components)
    if not start_result:
        logger.error("Failed to start system, exiting")
        stop_system(components)
        return False
    
    # Send the signal
    try:
        if "trading_system" in components:
            result = components["trading_system"].manual_signal(
                symbol=args.symbol,
                action=args.action,
                price=args.price,
                confidence=args.confidence,
                strategy=args.strategy
            )
            
            if result:
                logger.info(f"Manual signal sent: {args.symbol} {args.action} @ ${args.price}")
                # Wait a bit for the signal to be processed
                time.sleep(3)
            else:
                logger.error("Failed to send manual signal")
        else:
            logger.error("Trading system not available")
    finally:
        # Stop all components
        stop_system(components)
    
    return True

def generate_reports(config, args):
    """Generate trading system reports"""
    # Make sure directories exist
    ensure_directories_exist()
    
    # Initialize components
    components = initialize_system(config, args)
    if not components:
        logger.error("Failed to initialize system, exiting")
        return False
    
    # Generate reports without fully starting the system
    try:
        if "trading_system" in components and "virtual_trading_manager" in components["trading_system"].components:
            vtm = components["trading_system"].components["virtual_trading_manager"]
            
            if args.type == "daily" or args.type == "all":
                daily_report = vtm.generate_daily_report()
                if daily_report:
                    logger.info(f"Generated daily report: {daily_report}")
                else:
                    logger.info("No daily report generated")
            
            if args.type == "weekly" or args.type == "all":
                weekly_report = vtm.generate_weekly_report()
                if weekly_report:
                    logger.info(f"Generated weekly report: {weekly_report}")
                else:
                    logger.info("No weekly report generated")
            
        else:
            logger.error("Trading system or Virtual Trading Manager not available")
    finally:
        # Stop all components (even though we didn't fully start them)
        stop_system(components)
    
    return True

def main():
    """Main entry point function"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="WarMachine AI Trading System")
    
    # General arguments
    parser.add_argument("--config", type=str, default="config/warmachine_config.json", 
                        help="Path to configuration file")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    
    # Add subparsers for different modes
    subparsers = parser.add_subparsers(dest="mode", help="Operation mode")
    
    # Run mode
    run_parser = subparsers.add_parser("run", help="Run the trading system")
    
    # Signal mode
    signal_parser = subparsers.add_parser("signal", help="Send a manual trading signal")
    signal_parser.add_argument("--symbol", type=str, required=True, help="Trading symbol (e.g., AAPL)")
    signal_parser.add_argument("--action", type=str, required=True, choices=["BUY", "SELL"], 
                               help="Trade action (BUY or SELL)")
    signal_parser.add_argument("--price", type=float, required=True, help="Trade price")
    signal_parser.add_argument("--confidence", type=float, default=0.8, help="Signal confidence (0.0-1.0)")
    signal_parser.add_argument("--strategy", type=str, default="MANUAL", help="Strategy name")
    
    # Report mode
    report_parser = subparsers.add_parser("report", help="Generate trading reports")
    report_parser.add_argument("--type", type=str, default="all", choices=["daily", "weekly", "all"],
                              help="Report type to generate")
    
    # Create config mode
    config_parser = subparsers.add_parser("config", help="Create default configuration file")
    config_parser.add_argument("--save", type=str, default="config/warmachine_config.json", 
                              help="Path to save configuration file")
    
    args = parser.parse_args()
    
    # Set debug logging if requested
    if args.debug:
        logger.setLevel(logging.DEBUG)
        for handler in logger.handlers:
            handler.setLevel(logging.DEBUG)
        
        # Set package-level debugging
        logging.getLogger("warmachine").setLevel(logging.DEBUG)
    
    # Process based on mode
    if args.mode == "config":
        # Create and save default configuration
        config = create_default_config()
        if save_config(config, args.save):
            logger.info(f"Default configuration created at {args.save}")
            return 0
        else:
            return 1
    
    # Load configuration for other modes
    config = load_config(args.config)
    
    # Execute the selected mode
    if args.mode == "run" or args.mode is None:
        run_system(config, args)
    elif args.mode == "signal":
        manual_signal(config, args)
    elif args.mode == "report":
        generate_reports(config, args)
    else:
        logger.error(f"Unknown mode: {args.mode}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 