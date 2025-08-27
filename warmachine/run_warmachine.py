"""
WarMachine - Unified Trading System Controller

This is the main entry point for the WarMachine trading system.
It coordinates all components and provides a unified interface for:
- Market data feeds
- Trading strategies
- AI analysis
- Signal generation
- Risk management
- Reporting and notifications
"""

import os
import sys
import logging
import json
import asyncio
import signal
import threading
from typing import Dict, Any, Optional, List
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

# Add project root to Python path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.append(PROJECT_ROOT)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('warmachine.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('WarMachine')

# Import core components
from core.ai_event_pool import AIEventPool
from core.market_data_hub import MarketDataHub
from community.community_manager import CommunityManager
from notifiers.unified_notifier import UnifiedNotifier

class AsyncManager:
    """Manages all asynchronous components in the system"""
    
    def __init__(self):
        self.components = {}
        self.running = False
        self.loop = None
        self.executor = ThreadPoolExecutor(max_workers=4)
        self._shutdown_event = threading.Event()
        
    async def add_component(self, name: str, component: Any, start_method: str = "start"):
        """Add a component to be managed"""
        self.components[name] = {
            "instance": component,
            "start_method": start_method,
            "running": False
        }
        
    async def start_component(self, name: str) -> bool:
        """Start a specific component"""
        if name not in self.components:
            logger.error(f"Component {name} not found")
            return False
            
        component = self.components[name]
        if component["running"]:
            logger.warning(f"Component {name} is already running")
            return True
            
        try:
            start_method = getattr(component["instance"], component["start_method"])
            if asyncio.iscoroutinefunction(start_method):
                await start_method()
            else:
                self.executor.submit(start_method)
            component["running"] = True
            logger.info(f"Started component {name}")
            return True
        except Exception as e:
            logger.error(f"Failed to start component {name}: {e}")
            return False
            
    async def stop_component(self, name: str) -> bool:
        """Stop a specific component"""
        if name not in self.components:
            logger.error(f"Component {name} not found")
            return False
            
        component = self.components[name]
        if not component["running"]:
            logger.warning(f"Component {name} is not running")
            return True
            
        try:
            if hasattr(component["instance"], "shutdown"):
                shutdown_method = getattr(component["instance"], "shutdown")
                if asyncio.iscoroutinefunction(shutdown_method):
                    await shutdown_method()
                else:
                    self.executor.submit(shutdown_method)
            component["running"] = False
            logger.info(f"Stopped component {name}")
            return True
        except Exception as e:
            logger.error(f"Failed to stop component {name}: {e}")
            return False
            
    async def start_all(self):
        """Start all components"""
        self.running = True
        self._shutdown_event.clear()
        
        for name in self.components:
            await self.start_component(name)
            
    async def stop_all(self):
        """Stop all components"""
        self.running = False
        self._shutdown_event.set()
        
        for name in reversed(list(self.components.keys())):
            await self.stop_component(name)
            
        self.executor.shutdown(wait=True)
        
    def is_running(self) -> bool:
        """Check if the manager is running"""
        return self.running
        
    def get_component(self, name: str) -> Optional[Any]:
        """Get a component instance by name"""
        return self.components.get(name, {}).get("instance")

class WarMachine:
    """Main controller class for the WarMachine trading system"""
    
    def __init__(self, config_path: str = "config/warmachine_config.json"):
        """Initialize the WarMachine system"""
        self.config = self._load_config(config_path)
        self.running = False
        
        # Initialize core components
        self._init_components()
        
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from JSON file"""
        try:
            if not os.path.isfile(config_path):
                config_path = os.path.join(PROJECT_ROOT, config_path)
            with open(config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load config from {config_path}: {e}")
            return {}
            
    def _init_components(self):
        """Initialize all system components"""
        # First initialize event pool
        try:
            self.event_pool = AIEventPool(self.config.get('event_pool', {}))
        except ImportError as e:
            logger.warning(f"Failed to initialize event pool: {e}")
            self.event_pool = None
        
        # Market Data Components
        self.market_data = self._init_market_data()
        
        # Strategy Components
        self.strategies = self._init_strategies()
        
        # AI Components
        self.ai_components = self._init_ai_components()
        
        # Notification Components
        self.notifiers = self._init_notifiers()
        
        # Risk Management
        self.risk_management = self._init_risk_management()
        
        # Community Components
        self.community = self._init_community()
        
        # Web Components
        self.web_components = self._init_web()
        
        # Monitoring Components
        self.monitoring = self._init_monitoring()
        
        logger.info("All components initialized")
        
    def _init_market_data(self):
        """Initialize market data components"""
        try:
            return MarketDataHub(self.config, self.event_pool)
        except ImportError as e:
            logger.warning(f"Failed to initialize market data hub: {e}")
            return None
        
    def _init_strategies(self):
        """Initialize trading strategies"""
        strategies = {}
        try:
            from core.analysis.order_flow_monitor import OrderFlowMonitor
            strategies['order_flow'] = OrderFlowMonitor(self.config)
        except ImportError as e:
            logger.warning(f"Failed to initialize order flow monitor: {e}")
        
        return strategies
        
    def _init_ai_components(self):
        """Initialize AI analysis components"""
        ai_components = {}
        
        try:
            # Initialize AI analyzer
            from ai_engine.ai_analyzer import AIAnalyzer
            ai_components['analyzer'] = AIAnalyzer()
            
            # Initialize AI commander
            from ai_engine.ai_commander import AICommander
            ai_components['commander'] = AICommander(self.config)
            
            # Initialize AI model router
            from ai_engine.ai_model_router import AIModelRouter
            ai_components['model_router'] = AIModelRouter(self.config)
            
            # Initialize AI reporter
            from ai_engine.ai_reporter import AIReporter
            ai_components['reporter'] = AIReporter(self.config.get('ai_reporter', {}))
            
            # Initialize AI self-improvement
            from ai_engine.ai_self_improvement import AISelfImprovement
            ai_components['self_improvement'] = AISelfImprovement(self.config)
        except ImportError as e:
            logger.warning(f"Failed to initialize AI components: {e}")
        
        return ai_components
        
    def _init_notifiers(self):
        """Initialize notification components"""
        try:
            return UnifiedNotifier(self.config.get('notifiers', {}))
        except ImportError as e:
            logger.warning(f"Failed to initialize notifiers: {e}")
            return None
        
    def _init_risk_management(self):
        """Initialize risk management components"""
        # TODO: Implement risk management
        return None
        
    def _init_community(self):
        """Initialize community components"""
        try:
            return CommunityManager(self.config.get('community', {}))
        except ImportError as e:
            logger.warning(f"Failed to initialize community components: {e}")
            return None
        
    def _init_web(self):
        """Initialize web components"""
        web_components = {}
        
        try:
            # Initialize web dashboard
            from web_dashboard.web_dashboard import WebDashboard
            web_components['dashboard'] = WebDashboard(self.config.get('web', {}))
            
            # Initialize web API
            from web_dashboard.web_api import WebAPI
            web_components['api'] = WebAPI(self.config.get('web', {}))
        except ImportError as e:
            logger.warning(f"Failed to initialize web components: {e}")
        
        return web_components
        
    def _init_monitoring(self):
        """Initialize monitoring components"""
        monitoring_components = {}
        
        try:
            # Initialize market watcher
            from core.analysis.market_watcher import MarketWatcher
            monitoring_components['market_watcher'] = MarketWatcher(self.config)
            
            # Initialize routine scheduler
            from core.controller.routine_scheduler import RoutineScheduler
            components = {
                "data_hub": self.market_data,
                "event_pool": self.event_pool
            }
            monitoring_components['scheduler'] = RoutineScheduler(self.config, components)
        except ImportError as e:
            logger.warning(f"Failed to initialize monitoring components: {e}")
        
        return monitoring_components
        
    async def start(self):
        """Start the WarMachine system"""
        try:
            logger.info("Starting WarMachine system...")
            
            # Setup signal handlers
            for sig in (signal.SIGTERM, signal.SIGINT):
                signal.signal(sig, self._signal_handler)
            
            # Start components in order
            if self.market_data:
                await self.market_data.start()
                logger.info("Market data component started")
            
            if self.web_components:
                if 'dashboard' in self.web_components:
                    await self.web_components['dashboard'].start()
                    logger.info("Web dashboard started")
                if 'api' in self.web_components:
                    await self.web_components['api'].start()
                    logger.info("Web API started")
            
            if self.monitoring:
                if 'market_watcher' in self.monitoring:
                    await self.monitoring['market_watcher'].start()
                    logger.info("Market watcher started")
                if 'scheduler' in self.monitoring:
                    await self.monitoring['scheduler'].start()
                    logger.info("Scheduler started")
            
            if self.ai_components:
                for name, component in self.ai_components.items():
                    if hasattr(component, 'start'):
                        await component.start()
                        logger.info(f"AI component {name} started")
            
            # Start Telegram bot last
            if self.community:
                await self.community.start()
                logger.info("Community manager started")
            
            # Keep the main thread alive
            self.running = True
            while self.running:
                await asyncio.sleep(1)
                
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
            await self.shutdown()
            raise
            
    async def shutdown(self):
        """Graceful shutdown with proper error handling"""
        logger.info("Initiating shutdown sequence...")
        self.running = False
        
        # Shutdown all components
        if self.community:
            await self.community.shutdown()
            
        if self.web_components:
            if 'dashboard' in self.web_components:
                await self.web_components['dashboard'].shutdown()
            if 'api' in self.web_components:
                await self.web_components['api'].shutdown()
                
        if self.monitoring:
            if 'market_watcher' in self.monitoring:
                await self.monitoring['market_watcher'].shutdown()
            if 'scheduler' in self.monitoring:
                await self.monitoring['scheduler'].shutdown()
                
        if self.ai_components:
            for component in self.ai_components.values():
                if hasattr(component, 'shutdown'):
                    await component.shutdown()
                    
        if self.market_data:
            await self.market_data.shutdown()
            
        if self.notifiers:
            await self.notifiers.shutdown()
            
        logger.info("WarMachine system shut down successfully")

    async def start_component(self, component_name: str) -> bool:
        """Start a specific component"""
        try:
            if component_name == 'market_data' and self.market_data:
                await self.market_data.start()
                return True
            elif component_name == 'web_dashboard' and self.web_components and 'dashboard' in self.web_components:
                await self.web_components['dashboard'].start()
                return True
            elif component_name == 'web_api' and self.web_components and 'api' in self.web_components:
                await self.web_components['api'].start()
                return True
            elif component_name == 'market_watcher' and self.monitoring and 'market_watcher' in self.monitoring:
                await self.monitoring['market_watcher'].start()
                return True
            elif component_name == 'scheduler' and self.monitoring and 'scheduler' in self.monitoring:
                await self.monitoring['scheduler'].start()
                return True
            elif component_name.startswith('ai_') and self.ai_components:
                ai_component = component_name[3:]  # Remove 'ai_' prefix
                if ai_component in self.ai_components:
                    await self.ai_components[ai_component].start()
                    return True
            return False
        except Exception as e:
            logger.error(f"Failed to start component {component_name}: {e}")
            return False

    async def stop_component(self, component_name: str) -> bool:
        """Stop a specific component"""
        try:
            if component_name == 'market_data' and self.market_data:
                await self.market_data.shutdown()
                return True
            elif component_name == 'web_dashboard' and self.web_components and 'dashboard' in self.web_components:
                await self.web_components['dashboard'].shutdown()
                return True
            elif component_name == 'web_api' and self.web_components and 'api' in self.web_components:
                await self.web_components['api'].shutdown()
                return True
            elif component_name == 'market_watcher' and self.monitoring and 'market_watcher' in self.monitoring:
                await self.monitoring['market_watcher'].shutdown()
                return True
            elif component_name == 'scheduler' and self.monitoring and 'scheduler' in self.monitoring:
                await self.monitoring['scheduler'].shutdown()
                return True
            elif component_name.startswith('ai_') and self.ai_components:
                ai_component = component_name[3:]  # Remove 'ai_' prefix
                if ai_component in self.ai_components:
                    await self.ai_components[ai_component].shutdown()
                    return True
            return False
        except Exception as e:
            logger.error(f"Failed to stop component {component_name}: {e}")
            return False

    async def get_component_status(self, component_name: str) -> Dict[str, Any]:
        """Get status of a specific component"""
        try:
            if component_name == 'market_data' and self.market_data:
                return await self.market_data.get_status()
            elif component_name == 'web_dashboard' and self.web_components and 'dashboard' in self.web_components:
                return await self.web_components['dashboard'].get_status()
            elif component_name == 'web_api' and self.web_components and 'api' in self.web_components:
                return await self.web_components['api'].get_status()
            elif component_name == 'market_watcher' and self.monitoring and 'market_watcher' in self.monitoring:
                return await self.monitoring['market_watcher'].get_status()
            elif component_name == 'scheduler' and self.monitoring and 'scheduler' in self.monitoring:
                return await self.monitoring['scheduler'].get_status()
            elif component_name.startswith('ai_') and self.ai_components:
                ai_component = component_name[3:]  # Remove 'ai_' prefix
                if ai_component in self.ai_components:
                    return await self.ai_components[ai_component].get_status()
            return {"status": "not_found"}
        except Exception as e:
            logger.error(f"Failed to get status for component {component_name}: {e}")
            return {"status": "error", "error": str(e)}

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}")
        asyncio.create_task(self.shutdown())

async def main():
    """Main entry point"""
    try:
        warmachine = WarMachine()
        logger.info("Starting WarMachine system...")
        await warmachine.start()
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
        await warmachine.shutdown()
    except Exception as e:
        logger.error(f"Error in main loop: {e}")
        if 'warmachine' in locals():
            await warmachine.shutdown()
        raise

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("System shutdown complete")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1) 