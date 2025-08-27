#!/usr/bin/env python
"""
WarMachine AI Option Trader - Main Entry Point

This script initializes and starts the WarMachine AI Option Trader system,
setting up all components and maintaining the system's operation.
"""

import os
import sys
import json
import time
import signal
import logging
import threading
from datetime import datetime
import argparse
import asyncio
from typing import Dict, Any, Optional, List
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from ..ai_scheduler import AIScheduler
from ..execution.trading_system_integrator import TradingSystemIntegrator
from ..execution.virtual_trading_manager import VirtualTradingManager
from notifiers.unified_notifier import UnifiedNotifier
from ..market_data_hub import MarketDataHub
from ..ai_intelligence_dispatcher import AIIntelligenceDispatcher
from ai_engine.ai_reporter import AIReporter
from ..ai_event_pool import EventPriority, AIEventPool
from core.tg_bot.super_commander import SuperCommander
from .routine_scheduler import RoutineScheduler
from web_dashboard.webhook_server import WebhookServer
# from trading.hf_executor import HighFrequencyExecutor  # Module not found

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(f"logs/warmachine_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    ]
)
logger = logging.getLogger(__name__)

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
                                                           
                AI Option Trader v1.0.0                    
    """
    print(banner)
    print("=" * 60)
    print(f"Starting WarMachine AI at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

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

# Initialize system components
def initialize_system(config, args):
    """Initialize all system components"""
    components = {}
    
    try:
        # Initialize system directories
        ensure_directories_exist(config)
        
        # Import components here to avoid circular imports
        from ..market_data_hub import MarketDataHub
        from ..ai_event_pool import AIEventPool
        from ..ai_intelligence_dispatcher import AIIntelligenceDispatcher
        # from trading.enhanced_liquidity_sniper import EnhancedLiquiditySniper  # Module not found
        from .routine_scheduler import RoutineScheduler
        from web_dashboard.webhook_server import WebhookServer
        # from trading.hf_executor import HighFrequencyExecutor  # Module not found
        
        # Set up Market Data Hub
        logger.info("Initializing Market Data Hub...")
        data_hub = MarketDataHub(config.get("market_data", {}))
        components["data_hub"] = data_hub
        
        # Set up AI Event Pool
        logger.info("Initializing AI Event Pool...")
        event_pool = AIEventPool(config.get("event_pool", {}))
        components["event_pool"] = event_pool
        
        # Set up AI Intelligence Dispatcher
        logger.info("Initializing AI Intelligence Dispatcher...")
        intelligence_dispatcher = AIIntelligenceDispatcher(
            config.get("intelligence_dispatcher", {}),
            event_pool
        )
        components["intelligence_dispatcher"] = intelligence_dispatcher
        
        # Set up Routine Scheduler
        logger.info("Initializing Routine Scheduler...")
        scheduler = RoutineScheduler(
            config.get("scheduler", {}),
            components
        )
        components["scheduler"] = scheduler
        
        # Optional: Add AI Reporter if enabled
        if config.get("ai_reporter", {}).get("enabled", False):
            try:
                logger.info("Initializing AI Reporter...")
                ai_reporter = AIReporter(
                    config.get("ai_reporter", {}),
                    data_hub,
                    event_pool
                )
                components["ai_reporter"] = ai_reporter
            except ImportError:
                logger.warning("AI Reporter module not found or dependencies missing.")
        
        # Initialize AI Scheduler
        logger.info("Initializing AI Scheduler...")
        ai_scheduler = AIScheduler(config)
        components["ai_scheduler"] = ai_scheduler
        
        # Initialize Trading System Integrator
        logger.info("Initializing Trading System Integrator...")
        trading_system = TradingSystemIntegrator(
            config,
            ai_scheduler.get_component("model_router")
        )
        components["trading_system"] = trading_system
        
        # Initialize Unified Notifier
        logger.info("Initializing Unified Notifier...")
        notifier = UnifiedNotifier(config)
        components["notifier"] = notifier
        
        logger.info("All components initialized successfully")
        
        # Create initial system status event
        create_system_status_event(components, config)
        
        return components
        
    except Exception as e:
        logger.error(f"Error initializing system: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)

def ensure_directories_exist(config):
    """Ensure all required directories exist"""
    directories = [
        "logs",
        "data",
        "data/market_data",
        "data/ai_models",
        "data/reports",
        "data/backups",
        "config"
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        
    logger.info("Required directories created")

def create_system_status_event(components, config):
    """Create initial system status event"""
    if "event_pool" not in components:
        return
        
    event_pool = components["event_pool"]
    
    status = {
        "timestamp": datetime.now().isoformat(),
        "system_status": "initializing",
        "components": {
            name: "initialized" for name in components.keys()
        },
        "config": {
            key: value for key, value in config.items()
            if key not in ["api_keys", "secrets", "credentials"]
        }
    }
    
    event_pool.publish_event(
        "SYSTEM_STATUS",
        status,
        priority=EventPriority.LOW
    )

def setup_signal_handlers(components):
    """Set up signal handlers for graceful shutdown"""
    def signal_handler(sig, frame):
        logger.info("Received shutdown signal")
        stop_system(components)
        sys.exit(0)
        
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

def stop_system(components):
    """Stop all system components"""
    logger.info("Stopping system components...")
    
    for name, component in components.items():
        try:
            if hasattr(component, "stop"):
                component.stop()
            logger.info(f"Stopped {name}")
        except Exception as e:
            logger.error(f"Error stopping {name}: {str(e)}")

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="WarMachine AI Option Trader")
    parser.add_argument("--config", type=str, default="config/warmachine_config.json",
                      help="Path to configuration file")
    parser.add_argument("--no-webhook", action="store_true",
                      help="Disable webhook server")
    parser.add_argument("--debug", action="store_true",
                      help="Enable debug logging")
    args = parser.parse_args()
    
    # Set debug logging if requested
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Display startup banner
    display_banner()
    
    # Load configuration
    config = load_config(args.config)
    
    # Initialize system
    components = initialize_system(config, args)
    
    # Set up signal handlers
    setup_signal_handlers(components)
    
    try:
        # Start asyncio event loop
        loop = asyncio.get_event_loop()
        
        # Start trading system
        loop.run_until_complete(start_trading_system(components))
        
        # Start system monitoring
        monitor_task = loop.create_task(monitor_system(components))
        
        # Run event loop
        loop.run_forever()
        
    except Exception as e:
        logger.error(f"Error in main loop: {str(e)}")
        stop_system(components)
        sys.exit(1)
        
    finally:
        loop.close()

async def start_trading_system(components):
    """Start the trading system"""
    logger.info("Starting trading system...")
    
    try:
        # Start components in order
        for name, component in components.items():
            if hasattr(component, "start"):
                await component.start()
            logger.info(f"Started {name}")
            
        logger.info("Trading system started successfully")
        
    except Exception as e:
        logger.error(f"Error starting trading system: {str(e)}")
        stop_system(components)
        sys.exit(1)

async def monitor_system(components):
    """Monitor system health and performance"""
    while True:
        try:
            # Collect system metrics
            status = await collect_system_metrics(components)
            
            # Check for warnings
            if status.get("warnings"):
                await handle_system_warning(components, status)
            
            # Publish status update
            if "event_pool" in components:
                components["event_pool"].publish_event(
                    "SYSTEM_STATUS",
                    status,
                    priority=EventPriority.LOW
                )
            
        except Exception as e:
            logger.error(f"Error in system monitor: {str(e)}")
            
        await asyncio.sleep(60)  # Check every minute

async def handle_system_warning(components, status: Dict[str, Any]):
    """Handle system warnings"""
    for warning in status["warnings"]:
        logger.warning(f"System warning: {warning['message']}")
        
        # Notify through unified notifier
        if "notifier" in components:
            await components["notifier"].send_alert(
                title="System Warning",
                message=warning["message"],
                level="warning",
                data=warning
            )

async def collect_system_metrics(components) -> Dict[str, Any]:
    """Collect system metrics from all components"""
    metrics = {
        "timestamp": datetime.now().isoformat(),
        "system_status": "running",
        "components": {},
        "warnings": []
    }
    
    for name, component in components.items():
        try:
            if hasattr(component, "get_metrics"):
                component_metrics = await component.get_metrics()
                metrics["components"][name] = component_metrics
            else:
                metrics["components"][name] = "running"
                
        except Exception as e:
            logger.error(f"Error collecting metrics from {name}: {str(e)}")
            metrics["components"][name] = "error"
            metrics["warnings"].append({
                "component": name,
                "message": f"Failed to collect metrics: {str(e)}",
                "timestamp": datetime.now().isoformat()
            })
    
    return metrics

class MainController:
    """Main controller class for the WarMachine system"""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize main controller"""
        self.config = config
        self.components = None
        self.running = False
        
        # Set up logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    async def start(self):
        """Start the system"""
        self.logger.info("Starting WarMachine system...")
        
        try:
            # Initialize components
            self.components = initialize_system(self.config, None)
            
            # Start trading system
            await start_trading_system(self.components)
            
            self.running = True
            self.logger.info("WarMachine system started successfully")
            
        except Exception as e:
            self.logger.error(f"Error starting system: {str(e)}")
            await self.stop()
            raise
    
    async def stop(self):
        """Stop the system"""
        self.logger.info("Stopping WarMachine system...")
        self.running = False
        
        if self.components:
            stop_system(self.components)
        
        self.logger.info("WarMachine system stopped")

if __name__ == "__main__":
    main() 