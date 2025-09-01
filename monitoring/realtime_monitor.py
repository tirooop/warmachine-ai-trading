#!/usr/bin/env python
"""
WarMachine AI - Real-time Monitoring System

Real-time market data monitoring with DeepSeek AI-powered analysis:
- High-frequency data ingestion from multiple exchanges
- Order book analysis and liquidity monitoring
- AI-powered signal generation and alerting
- Real-time visualization dashboard

Usage:
  python run_realtime_monitor.py --symbols BTC,ETH,SPY,QQQ --mode ULTRA
"""

import os
import sys
import json
import time
import logging
import argparse
import asyncio
from datetime import datetime
from typing import Dict, List, Any, Optional
import pandas as pd
import numpy as np

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(f"logs/realtime_monitor_{int(time.time())}.log")
    ]
)
logger = logging.getLogger("realtime_monitor")

# Make sure the required directories exist
os.makedirs("logs", exist_ok=True)
os.makedirs("data", exist_ok=True)
os.makedirs("cache", exist_ok=True)

# Parse command line arguments
def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="WarMachine AI - Real-time Monitoring System")
    parser.add_argument("--symbols", type=str, default="BTC,ETH,SPY,QQQ,NVDA",
                        help="Comma-separated list of symbols to monitor")
    parser.add_argument("--mode", type=str, default="STANDARD", 
                        choices=["STANDARD", "ADVANCED", "ULTRA"],
                        help="Monitoring mode (STANDARD, ADVANCED, ULTRA)")
    parser.add_argument("--config", type=str, default="config/realtime_config.json",
                        help="Path to configuration file")
    parser.add_argument("--no-dashboard", action="store_true",
                        help="Disable web dashboard")
    return parser.parse_args()

# Load configuration
def load_config(args):
    """Load configuration from file and command line arguments"""
    # Default configuration
    config = {
        "mode": "STANDARD",
        "buffer_size": 10000,
        "update_interval_ms": 100,
        "enable_all_alerts": True,
        "enable_voice_alerts": False,
        "symbols": args.symbols.split(","),
        "web_dashboard": {
            "enabled": not args.no_dashboard,
            "host": "localhost",
            "port": 8501
        },
        "market_data": {
            "providers": {
                "binance": {
                    "enabled": True,
                    "api_key": os.environ.get("BINANCE_API_KEY", ""),
                    "api_secret": os.environ.get("BINANCE_API_SECRET", ""),
                    "reconnect_interval": 30
                },
                "ibkr": {
                    "enabled": True,
                    "host": "127.0.0.1",
                    "port": 7496,
                    "client_id": 1,
                    "timeout": 20
                },
                "polygon": {
                    "enabled": True,
                    "api_key": os.environ.get("POLYGON_API_KEY", ""),
                    "enable_websocket": True
                }
            }
        },
        "ai_config": {
            "api_base": "https://api.siliconflow.cn/v1",
            "api_key": os.environ.get("DEEPSEEK_API_KEY", ""),
            "model": "deepseek-ai/DeepSeek-V3",
            "temperature": 0.3,
            "max_tokens": 1500
        },
        "order_flow_monitor": {
            "entropy_threshold": 0.5,
            "imbalance_threshold": 0.3,
            "volume_spike_threshold": 1.5,
            "vwap_deviation_threshold": 0.002,
            "min_alert_interval": 60
        },
        "ai_alert_factory": {
            "min_confidence": 0.75,
            "alert_throttle_seconds": 300
        },
        "notifiers": {
            "console": {
                "enabled": True,
                "min_priority": "LOW"
            },
            "telegram": {
                "enabled": False,
                "bot_token": os.environ.get("TELEGRAM_BOT_TOKEN", ""),
                "chat_ids": []
            },
            "voice": {
                "enabled": False
            }
        }
    }
    
    # Override with configuration file if it exists
    if os.path.exists(args.config):
        try:
            with open(args.config, "r") as f:
                file_config = json.load(f)
                
            # Recursive update function for nested dictionaries
            def update_dict(d, u):
                for k, v in u.items():
                    if isinstance(v, dict) and k in d and isinstance(d[k], dict):
                        d[k] = update_dict(d[k], v)
                    else:
                        d[k] = v
                return d
            
            config = update_dict(config, file_config)
            logger.info(f"Loaded configuration from {args.config}")
            
        except Exception as e:
            logger.error(f"Error loading configuration: {str(e)}")
    
    # Override with command line arguments
    config["mode"] = args.mode
    config["symbols"] = args.symbols.split(",")
    
    # Update mode-specific settings
    if args.mode == "ULTRA":
        config["buffer_size"] = 100000
        config["update_interval_ms"] = 10
        config["enable_voice_alerts"] = True
    elif args.mode == "ADVANCED":
        config["buffer_size"] = 50000
        config["update_interval_ms"] = 50
        config["enable_voice_alerts"] = True
    
    return config

# Initialize components
async def initialize_system(config):
    """Initialize all system components"""
    try:
        # Import required modules
        from connectors.binance_websocket import EnhancedDataFeed
        from order_flow_monitor import OrderFlowMonitor
        from ai_alert_factory import AIAlertFactory
        from market_data_hub import MarketDataHub
        from ai_event_pool import AIEventPool
        
        logger.info("Initializing system components...")
        
        # Initialize event pool
        event_pool = AIEventPool({})
        
        # Initialize data feed
        data_feed_config = {
            "symbols": config["symbols"],
            "buffer_size": config["buffer_size"],
            "binance": config["market_data"]["providers"]["binance"]
        }
        data_feed = EnhancedDataFeed(data_feed_config)
        
        # Initialize order flow monitor
        order_flow_config = config["order_flow_monitor"]
        order_flow_config["symbols"] = config["symbols"]
        order_flow_monitor = OrderFlowMonitor(order_flow_config)
        
        # Initialize AI alert factory
        ai_alert_config = config["ai_alert_factory"]
        ai_alert_config["symbols"] = config["symbols"]
        ai_alert_config["ai_config"] = config["ai_config"]
        ai_alert_factory = AIAlertFactory(ai_alert_config)
        
        # Initialize market data hub
        market_data_hub = MarketDataHub(config["market_data"])
        
        # Setup alert handlers
        def handle_alert(alert):
            # Log alert
            level = alert.get("level", "medium")
            title = alert.get("title", "")
            content = alert.get("content", "")
            
            if level == "high":
                logger.warning(f"🚨 {title}")
                if content:
                    logger.warning(content)
            else:
                logger.info(f"🔔 {title}")
                if content:
                    logger.info(content)
            
            # Create AI event
            event_pool.create_ai_insight(
                symbol=alert.get("symbol", ""),
                title=title,
                analysis=content,
                priority=level.upper(),
                metadata=alert.get("data", {})
            )
            
            # Voice alert if enabled
            if config["enable_voice_alerts"] and level == "high":
                pass  # Voice alert implementation would go here
        
        # Register alert handlers
        order_flow_monitor.add_alert_handler(handle_alert)
        ai_alert_factory.add_alert_handler(handle_alert)
        
        # Setup data feed handlers
        async def handle_data(data):
            # Add to order flow monitor
            symbol = data.get("symbol", "")
            
            if "bids" in data and "asks" in data:
                # Order book data
                order_flow_monitor.add_orderbook(symbol, data)
            elif "price" in data and "quantity" in data:
                # Trade data
                order_flow_monitor.add_trade(symbol, data)
            
            # Collect data for AI analysis
            # In a real implementation, you would buffer data and periodically send for AI analysis
            
        data_feed.add_handler(handle_data)
        
        # Start data feed
        logger.info("Starting data feed...")
        await data_feed.start()
        
        # Initialize dashboard if enabled
        if config["web_dashboard"]["enabled"]:
            logger.info("Starting dashboard...")
            # Dashboard implementation would go here
            pass
        
        logger.info("System initialization complete")
        
        return {
            "data_feed": data_feed,
            "order_flow_monitor": order_flow_monitor,
            "ai_alert_factory": ai_alert_factory,
            "market_data_hub": market_data_hub,
            "event_pool": event_pool
        }
        
    except ImportError as e:
        logger.error(f"Failed to import required modules: {str(e)}")
        logger.error("Please make sure all dependencies are installed.")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error initializing system: {str(e)}")
        sys.exit(1)

# Main system loop
async def main_loop(components, config):
    """Main system loop for periodic tasks"""
    data_feed = components["data_feed"]
    order_flow_monitor = components["order_flow_monitor"]
    ai_alert_factory = components["ai_alert_factory"]
    market_data_hub = components["market_data_hub"]
    
    # Create update intervals
    fast_interval = config["update_interval_ms"] / 1000  # Fast updates (order flow)
    medium_interval = 5  # Medium updates (5s)
    slow_interval = 60  # Slow updates (60s)
    
    # Track last update times
    last_medium_update = time.time()
    last_slow_update = time.time()
    
    logger.info(f"Starting main loop with update interval: {fast_interval:.3f}s")
    
    try:
        while True:
            current_time = time.time()
            
            # Fast updates (order flow processing happens in handlers)
            
            # Medium updates (every 5s)
            if current_time - last_medium_update >= medium_interval:
                # Process each symbol
                for symbol in config["symbols"]:
                    try:
                        # Get latest data
                        latest_data = await data_feed.get_latest_data(symbol, 100)
                        if latest_data:
                            # Process with AI alert factory to generate signals
                            market_data = {
                                "symbol": symbol,
                                "price_data": pd.DataFrame(latest_data),
                                "recent_trades": latest_data,
                                # Add more data as needed
                            }
                            
                            # Get any active alerts
                            # This would be implemented in a real system
                            
                            # Generate AI alert if data is sufficient
                            if len(latest_data) >= 20:  # Only if we have enough data
                                await ai_alert_factory.generate_ai_alert(symbol, market_data)
                    except Exception as e:
                        logger.error(f"Error processing {symbol}: {str(e)}")
                
                last_medium_update = current_time
            
            # Slow updates (every 60s)
            if current_time - last_slow_update >= slow_interval:
                # System status logging
                logger.info("System status: OK")
                
                # Memory usage report
                import psutil
                process = psutil.Process(os.getpid())
                memory_info = process.memory_info()
                logger.info(f"Memory usage: {memory_info.rss / 1024 / 1024:.2f} MB")
                
                last_slow_update = current_time
            
            # Sleep for the fast interval
            await asyncio.sleep(fast_interval)
            
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received. Shutting down...")
    except Exception as e:
        logger.error(f"Error in main loop: {str(e)}")
    finally:
        # Shutdown all components
        logger.info("Shutting down components...")
        
        await data_feed.stop()
        order_flow_monitor.stop()
        ai_alert_factory.stop()
        
        logger.info("Shutdown complete")

# Main function
async def main():
    """Main function"""
    # Parse command line arguments
    args = parse_arguments()
    
    # Load configuration
    config = load_config(args)
    
    # Display startup information
    logger.info("=" * 60)
    logger.info("WarMachine AI - Real-time Market Monitor with DeepSeek")
    logger.info("=" * 60)
    logger.info(f"Mode: {config['mode']}")
    logger.info(f"Symbols: {', '.join(config['symbols'])}")
    logger.info(f"Buffer size: {config['buffer_size']}")
    logger.info(f"Update interval: {config['update_interval_ms']}ms")
    logger.info("=" * 60)
    
    # Check DeepSeek API key
    if not config["ai_config"]["api_key"]:
        logger.warning("WARNING: DeepSeek API key not set!")
        logger.warning("AI-powered analysis will be disabled.")
        logger.warning("Set DEEPSEEK_API_KEY environment variable to enable AI features.")
    
    # Initialize system components
    components = await initialize_system(config)
    
    # Run main loop
    await main_loop(components, config)

# Entry point
if __name__ == "__main__":
    # Set up asyncio with proper handling of KeyboardInterrupt
    try:
        if sys.platform == 'win32':
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExiting on keyboard interrupt...")
    except Exception as e:
        logger.critical(f"Unhandled exception: {str(e)}", exc_info=True)
        sys.exit(1) 