#!/usr/bin/env python
"""
Market Data Connection Test

Tests connections to market data providers and verifies real-time data flow.
"""

import os
import sys
import json
import time
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
        logging.FileHandler(f"logs/market_data_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    ]
)
logger = logging.getLogger(__name__)

# Ensure directories exist
def ensure_directories_exist():
    """Ensure required directories exist"""
    directories = ['logs', 'data/market_test']
    for directory in directories:
        os.makedirs(directory, exist_ok=True)

# Load configuration
def load_config(config_path="config/warmachine_config.json"):
    """Load the system configuration from file"""
    try:
        if not os.path.exists(config_path):
            logger.error(f"Configuration file not found: {config_path}")
            sys.exit(1)
            
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        logger.info(f"Configuration loaded from {config_path}")
        return config
    except Exception as e:
        logger.error(f"Error loading configuration: {str(e)}")
        sys.exit(1)

# Test market data connections
def test_market_data_connections(config, symbols, duration=60):
    """Test connections to market data providers"""
    try:
        # Import components
        from market_data_hub import MarketDataHub
        from ai_event_pool import AIEventPool
        
        # Create an event pool for receiving data
        event_pool = AIEventPool({})
        
        # Set up data collector
        class DataCollector:
            def __init__(self):
                self.data_received = {}
                self.ticker_updates = 0
                self.option_updates = 0
                self.errors = []
                
            def handle_ticker_update(self, event_data):
                self.ticker_updates += 1
                for update in event_data.get("updates", []):
                    symbol = update.get("symbol")
                    if symbol:
                        if symbol not in self.data_received:
                            self.data_received[symbol] = []
                        self.data_received[symbol].append(update)
                        logger.info(f"Received ticker update for {symbol}: {update.get('price')}")
            
            def handle_option_update(self, event_data):
                self.option_updates += 1
                symbol = event_data.get("symbol")
                if symbol:
                    logger.info(f"Received option update for {symbol}")
            
            def handle_error(self, event_data):
                error = event_data.get("error")
                provider = event_data.get("provider")
                self.errors.append({"provider": provider, "error": error})
                logger.error(f"Data provider error - {provider}: {error}")
        
        # Create data collector
        collector = DataCollector()
        
        # Register event handlers
        event_pool.register_handler("TICKER_UPDATE", collector.handle_ticker_update)
        event_pool.register_handler("OPTION_CHAIN_UPDATE", collector.handle_option_update)
        event_pool.register_handler("MARKET_DATA_ERROR", collector.handle_error)
        
        # Initialize Market Data Hub
        logger.info("Initializing Market Data Hub...")
        data_hub = MarketDataHub(config.get("market_data", {}), event_pool=event_pool)
        
        # Start Market Data Hub
        logger.info("Starting Market Data Hub...")
        if hasattr(data_hub, 'start'):
            data_hub.start()
        
        # Subscribe to symbols
        logger.info(f"Subscribing to symbols: {symbols}")
        for symbol in symbols:
            try:
                data_hub.subscribe_ticker(symbol)
                logger.info(f"Subscribed to ticker for {symbol}")
                # Try to subscribe to options if applicable
                try:
                    data_hub.subscribe_option_chain(symbol)
                    logger.info(f"Subscribed to option chain for {symbol}")
                except Exception as e:
                    logger.warning(f"Could not subscribe to option chain for {symbol}: {str(e)}")
            except Exception as e:
                logger.error(f"Error subscribing to {symbol}: {str(e)}")
        
        # Track connection status
        providers_status = {}
        for provider_name, provider_config in config.get("market_data", {}).get("providers", {}).items():
            if provider_config.get("enabled", False):
                providers_status[provider_name] = {
                    "connected": False,
                    "updates": 0
                }
        
        # Wait for data
        logger.info(f"Listening for market data for {duration} seconds...")
        start_time = time.time()
        last_status_time = start_time
        
        try:
            while time.time() - start_time < duration:
                # Print status every 10 seconds
                current_time = time.time()
                if current_time - last_status_time >= 10:
                    logger.info(f"Status after {int(current_time - start_time)} seconds:")
                    logger.info(f"Ticker updates: {collector.ticker_updates}")
                    logger.info(f"Option updates: {collector.option_updates}")
                    logger.info(f"Symbols with data: {list(collector.data_received.keys())}")
                    last_status_time = current_time
                
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Test interrupted by user")
        
        # Stop Market Data Hub
        logger.info("Stopping Market Data Hub...")
        if hasattr(data_hub, 'stop'):
            data_hub.stop()
        
        # Print summary
        logger.info("=" * 50)
        logger.info("Market Data Test Summary")
        logger.info("=" * 50)
        logger.info(f"Total ticker updates: {collector.ticker_updates}")
        logger.info(f"Total option updates: {collector.option_updates}")
        logger.info(f"Symbols with data: {list(collector.data_received.keys())}")
        if collector.errors:
            logger.info(f"Errors encountered: {len(collector.errors)}")
            for error in collector.errors:
                logger.info(f"  {error['provider']}: {error['error']}")
        
        # Determine success
        success = (collector.ticker_updates > 0)
        logger.info(f"Test result: {'SUCCESS' if success else 'FAILURE'}")
        
        # Save test data to file
        test_results = {
            "timestamp": datetime.now().isoformat(),
            "duration": duration,
            "symbols_requested": symbols,
            "symbols_received": list(collector.data_received.keys()),
            "ticker_updates": collector.ticker_updates,
            "option_updates": collector.option_updates,
            "errors": collector.errors,
            "success": success
        }
        
        results_path = Path("data/market_test") / f"test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_path, 'w') as f:
            json.dump(test_results, f, indent=2)
        
        logger.info(f"Test results saved to {results_path}")
        
        return success
    
    except Exception as e:
        logger.error(f"Error testing market data connections: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

# Feed sample data to the event system
def feed_sample_data(config, symbols, count=10):
    """Feed sample market data to test the event system"""
    try:
        # Import components
        from ai_event_pool import AIEventPool
        
        # Create an event pool
        logger.info("Creating AI Event Pool...")
        event_pool = AIEventPool({})
        
        # Track received events
        received_events = {
            "TRADE_SIGNAL": 0,
            "PRICE_UPDATE": 0
        }
        
        # Set up event handlers
        def handle_trade_signal(event_data):
            received_events["TRADE_SIGNAL"] += 1
            symbol = event_data.get("symbol")
            action = event_data.get("action")
            price = event_data.get("price")
            logger.info(f"Received TRADE_SIGNAL: {symbol} {action} @ ${price}")
        
        def handle_price_update(event_data):
            received_events["PRICE_UPDATE"] += 1
            updates = event_data.get("updates", [])
            logger.info(f"Received PRICE_UPDATE with {len(updates)} updates")
            for update in updates:
                symbol = update.get("symbol")
                price = update.get("price")
                logger.info(f"  {symbol}: ${price}")
        
        # Register handlers
        event_pool.register_handler("TRADE_SIGNAL", handle_trade_signal)
        event_pool.register_handler("PRICE_UPDATE", handle_price_update)
        
        # Generate sample price updates
        import random
        for i in range(count):
            # Create updates for all symbols
            updates = []
            for symbol in symbols:
                base_price = 100.0  # Base price for demonstration
                # Add some randomness
                price = base_price + random.uniform(-5.0, 5.0)
                updates.append({
                    "symbol": symbol,
                    "price": price,
                    "timestamp": datetime.now().isoformat()
                })
            
            # Create price update event
            price_update_event = {
                "updates": updates,
                "timestamp": datetime.now().isoformat()
            }
            
            # Publish event
            event_pool.publish_event("PRICE_UPDATE", price_update_event)
            logger.info(f"Published PRICE_UPDATE event with {len(updates)} updates")
            
            # Create trade signal for a random symbol
            if random.random() > 0.7:  # 30% chance to generate a signal
                random_symbol = random.choice(symbols)
                random_price = base_price + random.uniform(-5.0, 5.0)
                action = "BUY" if random.random() > 0.5 else "SELL"
                
                trade_signal = {
                    "symbol": random_symbol,
                    "action": action,
                    "price": random_price,
                    "confidence": 0.8,
                    "strategy": "TEST_STRATEGY",
                    "timestamp": datetime.now().isoformat()
                }
                
                # Publish event
                event_pool.publish_event("TRADE_SIGNAL", trade_signal)
                logger.info(f"Published TRADE_SIGNAL event: {random_symbol} {action} @ ${random_price:.2f}")
            
            # Wait a bit
            time.sleep(1)
        
        # Print summary
        logger.info("=" * 50)
        logger.info("Sample Data Feed Summary")
        logger.info("=" * 50)
        logger.info(f"Price updates published: {count}")
        logger.info(f"Price updates received: {received_events['PRICE_UPDATE']}")
        logger.info(f"Trade signals received: {received_events['TRADE_SIGNAL']}")
        
        # Determine success
        success = (received_events["PRICE_UPDATE"] > 0)
        logger.info(f"Test result: {'SUCCESS' if success else 'FAILURE'}")
        
        return success
    
    except Exception as e:
        logger.error(f"Error feeding sample data: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

# Test the end-to-end system with virtual trades
def test_virtual_trading_system(config, symbols, duration=60):
    """Test the end-to-end virtual trading system with simulated data"""
    try:
        # Import components
        from market_data_hub import MarketDataHub
        from ai_event_pool import AIEventPool
        from ai_intelligence_dispatcher import AIIntelligenceDispatcher
        from trading.trading_system_integrator import TradingSystemIntegrator
        
        # Create components
        logger.info("Creating system components...")
        event_pool = AIEventPool({})
        market_data_hub = MarketDataHub(config.get("market_data", {}), event_pool=event_pool)
        intelligence_dispatcher = AIIntelligenceDispatcher({}, event_pool)
        
        # Initialize Trading System Integrator
        logger.info("Initializing Trading System...")
        trading_system = TradingSystemIntegrator(config)
        
        # Initialize components
        success = trading_system.initialize_components(
            market_data_hub=market_data_hub,
            event_pool=event_pool,
            intelligence_dispatcher=intelligence_dispatcher
        )
        
        if not success:
            logger.error("Failed to initialize trading system")
            return False
        
        # Track trading system activity
        class ActivityTracker:
            def __init__(self):
                self.signals = 0
                self.trades = 0
                self.portfolio_updates = 0
                
            def handle_trade_signal(self, event_data):
                self.signals += 1
                symbol = event_data.get("symbol")
                action = event_data.get("action")
                price = event_data.get("price")
                logger.info(f"Signal detected: {symbol} {action} @ ${price}")
            
            def handle_trade_executed(self, event_data):
                self.trades += 1
                symbol = event_data.get("symbol")
                action = event_data.get("action", "UNKNOWN")
                price = event_data.get("price", 0)
                logger.info(f"Trade executed: {symbol} {action} @ ${price}")
            
            def handle_portfolio_update(self, event_data):
                self.portfolio_updates += 1
                portfolio = event_data.get("portfolio", {})
                total_value = portfolio.get("total_value", 0)
                logger.info(f"Portfolio updated: Total value = ${total_value}")
        
        # Create tracker
        tracker = ActivityTracker()
        
        # Register event handlers
        event_pool.register_handler("TRADE_SIGNAL", tracker.handle_trade_signal)
        event_pool.register_handler("TRADE_EXECUTED", tracker.handle_trade_executed)
        event_pool.register_handler("PORTFOLIO_UPDATE", tracker.handle_portfolio_update)
        
        # Start components
        logger.info("Starting system components...")
        market_data_hub.start()
        trading_system.start()
        
        # Subscribe to symbols
        logger.info(f"Subscribing to symbols: {symbols}")
        for symbol in symbols:
            market_data_hub.subscribe_ticker(symbol)
        
        # Create thread to send simulated price updates
        import threading
        import random
        
        def send_price_updates():
            logger.info("Starting price update thread...")
            try:
                base_prices = {symbol: 100.0 + random.uniform(-20.0, 20.0) for symbol in symbols}
                update_count = 0
                
                while update_count < duration:
                    # Create updates for all symbols
                    updates = []
                    for symbol in symbols:
                        # Add some randomness but maintain a trend
                        price_change = random.uniform(-1.0, 1.0)  # Random price movement
                        base_prices[symbol] += price_change
                        
                        updates.append({
                            "symbol": symbol,
                            "price": base_prices[symbol],
                            "timestamp": datetime.now().isoformat()
                        })
                    
                    # Create price update event
                    price_update_event = {
                        "updates": updates,
                        "timestamp": datetime.now().isoformat()
                    }
                    
                    # Publish event
                    event_pool.publish_event("PRICE_UPDATE", price_update_event)
                    
                    # Generate occasional trade signals
                    if random.random() > 0.8:  # 20% chance
                        random_symbol = random.choice(symbols)
                        action = "BUY" if random.random() > 0.5 else "SELL"
                        
                        trade_signal = {
                            "symbol": random_symbol,
                            "action": action,
                            "price": base_prices[random_symbol],
                            "confidence": random.uniform(0.6, 0.9),
                            "strategy": "TEST_STRATEGY",
                            "timestamp": datetime.now().isoformat()
                        }
                        
                        # Publish event
                        event_pool.publish_event("TRADE_SIGNAL", trade_signal)
                        logger.info(f"Generated signal: {random_symbol} {action} @ ${base_prices[random_symbol]:.2f}")
                    
                    update_count += 1
                    time.sleep(1)
                
                logger.info("Price update thread finished")
            except Exception as e:
                logger.error(f"Error in price update thread: {str(e)}")
        
        # Start price update thread
        update_thread = threading.Thread(target=send_price_updates)
        update_thread.daemon = True
        update_thread.start()
        
        # Wait for test duration
        logger.info(f"Running test for {duration} seconds...")
        start_time = time.time()
        last_status_time = start_time
        
        try:
            while time.time() - start_time < duration:
                # Print status every 10 seconds
                current_time = time.time()
                if current_time - last_status_time >= 10:
                    logger.info(f"Status after {int(current_time - start_time)} seconds:")
                    logger.info(f"Signals detected: {tracker.signals}")
                    logger.info(f"Trades executed: {tracker.trades}")
                    logger.info(f"Portfolio updates: {tracker.portfolio_updates}")
                    
                    # Get portfolio status if available
                    if hasattr(trading_system, 'get_system_status'):
                        status = trading_system.get_system_status()
                        if "portfolio" in status:
                            portfolio = status["portfolio"]
                            logger.info(f"Portfolio: {portfolio}")
                    
                    last_status_time = current_time
                
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Test interrupted by user")
        
        # Stop components
        logger.info("Stopping system components...")
        trading_system.stop()
        market_data_hub.stop()
        
        # Print summary
        logger.info("=" * 50)
        logger.info("Virtual Trading System Test Summary")
        logger.info("=" * 50)
        logger.info(f"Test duration: {duration} seconds")
        logger.info(f"Signals detected: {tracker.signals}")
        logger.info(f"Trades executed: {tracker.trades}")
        logger.info(f"Portfolio updates: {tracker.portfolio_updates}")
        
        # Determine success
        success = (tracker.signals > 0)
        logger.info(f"Test result: {'SUCCESS' if success else 'FAILURE'}")
        
        return success
    
    except Exception as e:
        logger.error(f"Error testing virtual trading system: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def main():
    """Main entry point function"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Market Data Connection Test")
    
    # General arguments
    parser.add_argument("--config", type=str, default="config/warmachine_config.json", 
                        help="Path to configuration file")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    
    # Add subparsers for different test modes
    subparsers = parser.add_subparsers(dest="mode", help="Test mode")
    
    # Real market data test
    market_parser = subparsers.add_parser("market", help="Test market data connections")
    market_parser.add_argument("--symbols", type=str, default="AAPL,MSFT,GOOGL", 
                             help="Comma-separated list of symbols to test")
    market_parser.add_argument("--duration", type=int, default=60, 
                             help="Test duration in seconds")
    
    # Sample data test
    sample_parser = subparsers.add_parser("sample", help="Test with sample data")
    sample_parser.add_argument("--symbols", type=str, default="AAPL,MSFT,GOOGL", 
                             help="Comma-separated list of symbols to test")
    sample_parser.add_argument("--count", type=int, default=10, 
                             help="Number of sample updates to generate")
    
    # Virtual trading system test
    vt_parser = subparsers.add_parser("trading", help="Test virtual trading system")
    vt_parser.add_argument("--symbols", type=str, default="AAPL,MSFT,GOOGL", 
                         help="Comma-separated list of symbols to test")
    vt_parser.add_argument("--duration", type=int, default=60, 
                         help="Test duration in seconds")
    
    args = parser.parse_args()
    
    # Set debug logging if requested
    if args.debug:
        logger.setLevel(logging.DEBUG)
        for handler in logger.handlers:
            handler.setLevel(logging.DEBUG)
        
        # Set package-level debugging
        logging.getLogger("warmachine").setLevel(logging.DEBUG)
    
    # Ensure directories exist
    ensure_directories_exist()
    
    # Load configuration
    config = load_config(args.config)
    
    # Execute the selected test mode
    success = False
    
    if args.mode == "market" or args.mode is None:
        # Split symbols
        symbols = [s.strip() for s in args.symbols.split(",")]
        logger.info(f"Testing market data connections for symbols: {symbols}")
        success = test_market_data_connections(config, symbols, args.duration)
    
    elif args.mode == "sample":
        # Split symbols
        symbols = [s.strip() for s in args.symbols.split(",")]
        logger.info(f"Testing with sample data for symbols: {symbols}")
        success = feed_sample_data(config, symbols, args.count)
    
    elif args.mode == "trading":
        # Split symbols
        symbols = [s.strip() for s in args.symbols.split(",")]
        logger.info(f"Testing virtual trading system for symbols: {symbols}")
        success = test_virtual_trading_system(config, symbols, args.duration)
    
    else:
        logger.error(f"Unknown test mode: {args.mode}")
        return 1
    
    # Return success/failure code
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main()) 