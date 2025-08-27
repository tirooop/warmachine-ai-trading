"""
WarMachine Core Components

This package contains the core system components for the WarMachine trading platform.
"""

# Controller components
from .controller import MainController, RoutineScheduler, WarMachine

# Data components
from .data.market_data_hub import MarketDataHub

# Execution components
from .execution.hf_executor import HighFrequencyExecutor
from .execution.virtual_trading_manager import VirtualTradingManager
from .execution.trading_system_integrator import TradingSystemIntegrator

# Analysis components
from .analysis.ai_analyzer import AIAnalyzer
from .analysis.market_watcher import MarketWatcher
from .analysis.order_flow_monitor import OrderFlowMonitor

# Notification components
from .notification.ai_alert_factory import AIAlertFactory
from .notification.ai_alert_generator import AIAlertGenerator
from .notification.ai_intelligence_dispatcher import AIIntelligenceDispatcher

# AI components
from ai_engine.ai_model_router import AIModelRouter
from ai_engine.ai_event_pool import AIEventPool
from ai_engine.ai_feedback_learner import AIFeedbackLearner

# Bot components
from core.tg_bot.super_commander import SuperCommander

# New components
from .ai_scheduler import AIScheduler

__version__ = "1.0.0"
__all__ = [
    # Controller
    'MainController',
    'RoutineScheduler',
    'WarMachine',
    
    # Data
    'MarketDataHub',
    
    # Execution
    'HighFrequencyExecutor',
    'VirtualTradingManager',
    'TradingSystemIntegrator',
    
    # Analysis
    'AIAnalyzer',
    'MarketWatcher',
    'OrderFlowMonitor',
    
    # Notification
    'AIAlertFactory',
    'AIAlertGenerator',
    'AIIntelligenceDispatcher',
    
    # AI
    'AIModelRouter',
    'AIEventPool',
    'AIFeedbackLearner',
    
    # Bot
    'SuperCommander',

    # New components
    'AIScheduler',
] 