"""
AI Processor Module
=================

This module provides the main processor for AI operations.
"""

from typing import Dict, Any, List, Optional
import logging
from .ai_analyzer import AIAnalyzer
from .ai_alert_factory import AIAlertFactory

logger = logging.getLogger(__name__)

class AIProcessor:
    """
    Main processor for AI operations.
    
    This class coordinates the AI analysis and alert generation process.
    """
    
    def __init__(self):
        """Initialize the AI Processor."""
        self.logger = logging.getLogger(__name__)
        self.analyzer = AIAnalyzer()
        self.alert_factory = AIAlertFactory()
        
    def process_market_data(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Process market data through the AI pipeline.
        
        Args:
            data: Market data to process
            
        Returns:
            List of generated alerts
        """
        try:
            # Analyze market data
            analysis = self.analyzer.analyze_market_data(data)
            
            # Generate signals
            signals = self.analyzer.generate_signals(analysis)
            
            # Create alerts from signals
            alerts = []
            for signal in signals:
                alert = self.alert_factory.create_alert(
                    alert_type="ai_signal",
                    data=signal,
                    priority=signal.get("priority", 1)
                )
                alerts.append(alert)
                
            return alerts
            
        except Exception as e:
            self.logger.error(f"Error processing market data: {str(e)}")
            return [] 