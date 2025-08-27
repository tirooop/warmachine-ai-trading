"""
AI Engine Module
===============

This module provides the core AI functionality for the trading system.
It includes components for market analysis, signal generation, strategy execution,
and various AI-powered trading tools.

Components:
----------
Core Components:
- AIAnalyzer: Core analysis engine for market data
- AIAlertFactory: Factory for creating AI-generated alerts
- AIStrategy: Base class for AI trading strategies
- AIProcessor: Main processor for AI operations

Advanced Components:
- AICommander: AI-powered command and control system
- AIModelRouter: Intelligent routing of AI model requests
- AIReporter: AI-powered reporting and analysis system
- AISelfImprovement: Self-improving AI system
- TradingSystem: Core trading system implementation
- TraderAssistant: AI-powered trading assistant
- StrategyEvolution: Evolutionary strategy optimization
- StrategyTelegram: Telegram integration for strategies
"""

from .ai_analyzer import AIAnalyzer
from .ai_alert_factory import AIAlertFactory
from .ai_strategy import AIStrategy
from .ai_processor import AIProcessor
from .ai_commander import AICommander
from .ai_model_router import AIModelRouter
from .ai_reporter import AIReporter
from .ai_self_improvement import AISelfImprovement

__version__ = '1.0.0'
__author__ = 'Warmachine Team'

__all__ = [
    # Core Components
    'AIAnalyzer',
    'AIAlertFactory',
    'AIStrategy',
    'AIProcessor',
    
    # Advanced Components
    'AICommander',
    'AIModelRouter',
    'AIReporter',
    'AISelfImprovement',
] 