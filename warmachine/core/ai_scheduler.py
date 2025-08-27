"""
AI Scheduler - Unified Management of AI Components

This module provides centralized scheduling and management of all AI-related
components in the WarMachine system, including:
- Analysis engines
- Prediction models
- Signal generation
- Strategy evolution
- Performance monitoring
- Self-improvement
"""

import logging
import asyncio
from typing import Dict, Any, Optional, List, Set
from datetime import datetime
from enum import Enum

from .analysis.ai_analyzer import AIAnalyzer
from .notification.ai_alert_generator import AIAlertGenerator
from .notification.ai_alert_factory import AIAlertFactory
from .execution.virtual_trading_manager import VirtualTradingManager
from ai_engine.ai_model_router import AIModelRouter
from trading.ai_feedback_learner import AIFeedbackLearner
from core.tg_bot.super_commander import SuperCommander

logger = logging.getLogger(__name__)

class ComponentState(Enum):
    """Component operational states"""
    INITIALIZING = "initializing"
    ACTIVE = "active"
    DEGRADED = "degraded"
    FAILED = "failed"
    UPDATING = "updating"

class AIScheduler:
    """Centralized scheduler for managing all AI components"""
    
    def __init__(self, config: Dict[str, Any], commander: Optional[SuperCommander] = None):
        """Initialize the AI scheduler
        
        Args:
            config: System configuration dictionary
            commander: SuperCommander instance for command integration
        """
        self.config = config
        self.commander = commander
        self.components = {}
        self.component_states = {}
        self.feedback_loops = {}
        self._initialize_components()
        
        # Register commands with SuperCommander if available
        if self.commander:
            self._register_commands()
            
    def _register_commands(self):
        """Register scheduler commands with SuperCommander"""
        if not self.commander:
            return
            
        # Register component management commands
        self.commander.register_command(
            "start_component",
            self.start_component,
            "Start an AI component",
            ["component_name"]
        )
        
        self.commander.register_command(
            "stop_component",
            self.stop_component,
            "Stop an AI component",
            ["component_name"]
        )
        
        self.commander.register_command(
            "get_component_status",
            self.get_component_status,
            "Get status of an AI component",
            ["component_name"]
        )
        
        self.commander.register_command(
            "get_system_status",
            self.generate_report,
            "Get overall system status",
            []
        )
        
        logger.info("Scheduler commands registered with SuperCommander")
        
    def _initialize_components(self):
        """Initialize all AI components"""
        try:
            # Initialize core components
            self.components["model_router"] = AIModelRouter(self.config)
            self.components["analyzer"] = AIAnalyzer(self.config)
            self.components["alert_generator"] = AIAlertGenerator(
                self.config,
                self.components["model_router"]
            )
            self.components["alert_factory"] = AIAlertFactory(self.config)
            
            # Initialize trading components
            self.components["trading_manager"] = VirtualTradingManager(
                self.config,
                self.components["model_router"]
            )
            self.components["feedback_learner"] = AIFeedbackLearner(
                self.config,
                self.components["model_router"]
            )
            
            # Initialize component states
            for name in self.components:
                self.component_states[name] = ComponentState.INITIALIZING
                
            # Initialize feedback loops
            self._setup_feedback_loops()
            
            logger.info("AI components initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize AI components: {str(e)}")
            raise
            
    def _setup_feedback_loops(self):
        """Set up feedback loops for component optimization"""
        try:
            # Global feedback loop
            self.feedback_loops["global"] = {
                "analyzer": self.components["analyzer"],
                "trading_manager": self.components["trading_manager"],
                "feedback_learner": self.components["feedback_learner"]
            }
            
            # Local feedback loops
            self.feedback_loops["local"] = {
                "signal_quality": {
                    "analyzer": self.components["analyzer"],
                    "alert_generator": self.components["alert_generator"]
                },
                "execution_quality": {
                    "trading_manager": self.components["trading_manager"],
                    "feedback_learner": self.components["feedback_learner"]
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to setup feedback loops: {str(e)}")
            raise
            
    async def start(self):
        """Start all AI components"""
        try:
            # Start core analysis
            await self.components["analyzer"].start()
            self.component_states["analyzer"] = ComponentState.ACTIVE
            
            # Start trading components
            await self.components["trading_manager"].start()
            self.component_states["trading_manager"] = ComponentState.ACTIVE
            
            await self.components["feedback_learner"].start()
            self.component_states["feedback_learner"] = ComponentState.ACTIVE
            
            # Start alert generation
            await self.components["alert_generator"].start()
            self.component_states["alert_generator"] = ComponentState.ACTIVE
            
            # Start feedback loops
            await self._start_feedback_loops()
            
            logger.info("AI scheduler started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start AI scheduler: {str(e)}")
            raise
            
    async def _start_feedback_loops(self):
        """Start all feedback loops"""
        try:
            # Start global feedback loop
            asyncio.create_task(self._run_global_feedback_loop())
            
            # Start local feedback loops
            for name, components in self.feedback_loops["local"].items():
                asyncio.create_task(self._run_local_feedback_loop(name, components))
                
        except Exception as e:
            logger.error(f"Failed to start feedback loops: {str(e)}")
            raise
            
    async def _run_global_feedback_loop(self):
        """Run the global feedback loop"""
        while True:
            try:
                # Get current model version
                current_model = await self.components["model_router"].get_current_model()
                
                # Update components
                await self._update_components(current_model)
                
                # Check component health
                await self._check_component_health()
                
                # Wait for next iteration
                await asyncio.sleep(
                    self.config.get("feedback_loop", {}).get(
                        "global_interval_seconds", 3600
                    )
                )
                
            except Exception as e:
                logger.error(f"Global feedback loop error: {str(e)}")
                await asyncio.sleep(60)  # Retry after 1 minute
                
    async def _run_local_feedback_loop(self, name: str, components: Dict[str, Any]):
        """Run a local feedback loop
        
        Args:
            name: Loop name
            components: Components in the loop
        """
        while True:
            try:
                # Run local optimization
                await self._optimize_local_components(name, components)
                
                # Wait for next iteration
                await asyncio.sleep(
                    self.config.get("feedback_loop", {}).get(
                        "local_interval_seconds", 300
                    )
                )
                
            except Exception as e:
                logger.error(f"Local feedback loop error ({name}): {str(e)}")
                await asyncio.sleep(30)  # Retry after 30 seconds
                
    async def _update_components(self, model_version: str):
        """Update components to use new model version
        
        Args:
            model_version: New model version
        """
        try:
            # Update analyzer
            if hasattr(self.components["analyzer"], "update_model"):
                await self.components["analyzer"].update_model(model_version)
                
            # Update trading manager
            if hasattr(self.components["trading_manager"], "update_model"):
                await self.components["trading_manager"].update_model(model_version)
                
            # Update feedback learner
            if hasattr(self.components["feedback_learner"], "update_model"):
                await self.components["feedback_learner"].update_model(model_version)
                
        except Exception as e:
            logger.error(f"Failed to update components: {str(e)}")
            raise
            
    async def _check_component_health(self):
        """Check health of all components"""
        try:
            for name, component in self.components.items():
                if hasattr(component, "get_health"):
                    health = await component.get_health()
                    if health["status"] != "healthy":
                        self.component_states[name] = ComponentState.DEGRADED
                        await self._handle_component_degradation(name, health)
                    else:
                        self.component_states[name] = ComponentState.ACTIVE
                        
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            
    async def _handle_component_degradation(self, name: str, health: Dict[str, Any]):
        """Handle component degradation
        
        Args:
            name: Component name
            health: Health status
        """
        try:
            # Log degradation
            logger.warning(f"Component {name} degraded: {health}")
            
            # Attempt recovery
            if hasattr(self.components[name], "recover"):
                await self.components[name].recover()
                
            # Generate alert
            await self.components["alert_generator"].process_analysis({
                "type": "component_degradation",
                "component": name,
                "details": health
            })
            
        except Exception as e:
            logger.error(f"Failed to handle component degradation: {str(e)}")
            
    async def _optimize_local_components(self, name: str, components: Dict[str, Any]):
        """Optimize local components
        
        Args:
            name: Optimization name
            components: Components to optimize
        """
        try:
            # Run optimization based on name
            if name == "signal_quality":
                await self._optimize_signal_quality(components)
            elif name == "execution_quality":
                await self._optimize_execution_quality(components)
                
        except Exception as e:
            logger.error(f"Local optimization failed ({name}): {str(e)}")
            
    async def _optimize_signal_quality(self, components: Dict[str, Any]):
        """Optimize signal quality
        
        Args:
            components: Components to optimize
        """
        try:
            # Get signal quality metrics
            metrics = await components["analyzer"].get_signal_metrics()
            
            # Update alert thresholds if needed
            if metrics["quality_score"] < 0.8:
                await components["alert_generator"].update_thresholds(
                    metrics["suggested_thresholds"]
                )
                
        except Exception as e:
            logger.error(f"Signal quality optimization failed: {str(e)}")
            
    async def _optimize_execution_quality(self, components: Dict[str, Any]):
        """Optimize execution quality
        
        Args:
            components: Components to optimize
        """
        try:
            # Get execution metrics
            metrics = await components["trading_manager"].get_execution_metrics()
            
            # Update feedback learner if needed
            if metrics["success_rate"] < 0.9:
                await components["feedback_learner"].update_learning_params(
                    metrics["suggested_params"]
                )
                
        except Exception as e:
            logger.error(f"Execution quality optimization failed: {str(e)}")
            
    async def stop(self):
        """Stop all AI components"""
        try:
            # Stop all components
            for name, component in self.components.items():
                if hasattr(component, "stop"):
                    await component.stop()
                    self.component_states[name] = ComponentState.FAILED
                    
            logger.info("AI scheduler stopped successfully")
            
        except Exception as e:
            logger.error(f"Error stopping AI scheduler: {str(e)}")
            
    async def analyze_market(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Perform market analysis using AI components
        
        Args:
            market_data: Market data dictionary
            
        Returns:
            Analysis results dictionary
        """
        try:
            # Get market analysis
            analysis = await self.components["analyzer"].analyze_market_data(market_data)
            
            # Check signal quality
            if not await self._validate_signal_quality(analysis):
                analysis["requires_review"] = True
                
            # Generate alerts if needed
            if analysis.get("alert_triggers", []):
                await self.components["alert_generator"].process_analysis(analysis)
                
            return analysis
            
        except Exception as e:
            logger.error(f"Market analysis failed: {str(e)}")
            return {"error": str(e)}
            
    async def _validate_signal_quality(self, analysis: Dict[str, Any]) -> bool:
        """Validate signal quality
        
        Args:
            analysis: Analysis results
            
        Returns:
            True if signal quality is acceptable
        """
        try:
            # Get quality metrics
            metrics = await self.components["analyzer"].get_signal_metrics()
            
            # Check against thresholds
            return (
                metrics["quality_score"] >= 0.8 and
                metrics["confidence"] >= 0.7 and
                metrics["reliability"] >= 0.6
            )
            
        except Exception as e:
            logger.error(f"Signal quality validation failed: {str(e)}")
            return False
            
    async def execute_trades(self, signals: List[Dict[str, Any]]):
        """Execute trades based on AI signals
        
        Args:
            signals: List of trading signal dictionaries
        """
        try:
            for signal in signals:
                # Validate signal
                if not await self._validate_signal_quality(signal):
                    logger.warning(f"Skipping low quality signal: {signal}")
                    continue
                    
                # Execute trade
                await self.components["trading_manager"].handle_signal(signal)
                
        except Exception as e:
            logger.error(f"Trade execution failed: {str(e)}")
            
    async def process_feedback(self, trading_results: Dict[str, Any]):
        """Process trading results for AI learning
        
        Args:
            trading_results: Trading results dictionary
        """
        try:
            # Process results
            await self.components["feedback_learner"].process_results(trading_results)
            
            # Update local optimizations
            await self._optimize_local_components("execution_quality", {
                "trading_manager": self.components["trading_manager"],
                "feedback_learner": self.components["feedback_learner"]
            })
            
        except Exception as e:
            logger.error(f"Feedback processing failed: {str(e)}")
            
    async def generate_report(self) -> Dict[str, Any]:
        """Generate AI system status report
        
        Returns:
            Report dictionary
        """
        try:
            report = {
                "timestamp": datetime.now().isoformat(),
                "components": {},
                "status": "healthy"
            }
            
            # Collect component status
            for name, component in self.components.items():
                if hasattr(component, "get_status"):
                    report["components"][name] = {
                        "status": await component.get_status(),
                        "state": self.component_states[name].value
                    }
                    
            # Check overall health
            if any(state == ComponentState.FAILED for state in self.component_states.values()):
                report["status"] = "failed"
            elif any(state == ComponentState.DEGRADED for state in self.component_states.values()):
                report["status"] = "degraded"
                
            return report
            
        except Exception as e:
            logger.error(f"Report generation failed: {str(e)}")
            return {
                "timestamp": datetime.now().isoformat(),
                "error": str(e),
                "status": "error"
            }
            
    def get_component(self, name: str) -> Optional[Any]:
        """Get an AI component by name
        
        Args:
            name: Component name
            
        Returns:
            Component instance or None if not found
        """
        return self.components.get(name) 