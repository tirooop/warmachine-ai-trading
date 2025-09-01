"""
Alert Templates

Provides template system for formatting alert messages.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from ai_event_pool import AIEvent, EventCategory, EventPriority

logger = logging.getLogger(__name__)

class AlertTemplate:
    """Template for formatting alert messages"""
    
    def __init__(self, name: str, template: str, description: str = ""):
        """
        Initialize alert template
        
        Args:
            name: Template name
            template: Template string with placeholders
            description: Template description
        """
        self.name = name
        self.template = template
        self.description = description
        self.created_at = datetime.now().isoformat()
        self.updated_at = self.created_at
        self.usage_count = 0
    
    def format(self, event: AIEvent, **kwargs) -> str:
        """
        Format template with event data
        
        Args:
            event: The event to format
            **kwargs: Additional formatting parameters
            
        Returns:
            Formatted message string
        """
        try:
            # Basic event data
            data = {
                "title": event.title,
                "symbol": event.symbol,
                "category": event.category.value,
                "priority": event.priority.name,
                "timestamp": event.timestamp,
                "content": event.content
            }
            
            # Add metadata
            if event.metadata:
                data.update(event.metadata)
            
            # Add custom parameters
            data.update(kwargs)
            
            # Format template
            message = self.template.format(**data)
            self.usage_count += 1
            self.updated_at = datetime.now().isoformat()
            
            return message
            
        except Exception as e:
            logger.error(f"Error formatting template {self.name}: {str(e)}")
            return f"Error formatting alert: {str(e)}"

class AlertTemplateManager:
    """Manager for alert templates"""
    
    def __init__(self):
        """Initialize template manager"""
        self.templates: Dict[str, AlertTemplate] = {}
        self._load_default_templates()
    
    def _load_default_templates(self):
        """Load default templates"""
        # Price alert template
        self.add_template(
            "price_alert",
            (
                "🔔 *Price Alert*\n\n"
                "Symbol: {symbol}\n"
                "Current Price: {price}\n"
                "Direction: {direction}\n"
                "Threshold: {threshold}\n\n"
                "Analysis:\n{content}"
            ),
            "Default template for price alerts"
        )
        
        # Volume alert template
        self.add_template(
            "volume_alert",
            (
                "📊 *Volume Alert*\n\n"
                "Symbol: {symbol}\n"
                "Current Volume: {volume}\n"
                "Threshold: {threshold}\n\n"
                "Analysis:\n{content}"
            ),
            "Default template for volume alerts"
        )
        
        # Risk alert template
        self.add_template(
            "risk_alert",
            (
                "⚠️ *Risk Alert*\n\n"
                "Strategy: {strategy}\n"
                "Risk Level: {risk_level}\n"
                "Threshold: {threshold}\n\n"
                "Analysis:\n{content}"
            ),
            "Default template for risk alerts"
        )
        
        # Trade signal template
        self.add_template(
            "trade_signal",
            (
                "🎯 *Trade Signal*\n\n"
                "Symbol: {symbol}\n"
                "Signal Type: {signal_type}\n"
                "Direction: {direction}\n"
                "Confidence: {confidence}\n\n"
                "Analysis:\n{content}\n\n"
                "Recommended Actions:\n{actions}"
            ),
            "Default template for trade signals"
        )
    
    def add_template(self, name: str, template: str, description: str = "") -> bool:
        """
        Add a new template
        
        Args:
            name: Template name
            template: Template string
            description: Template description
            
        Returns:
            True if template was added successfully
        """
        try:
            if name in self.templates:
                logger.warning(f"Template {name} already exists, updating")
            
            self.templates[name] = AlertTemplate(name, template, description)
            return True
            
        except Exception as e:
            logger.error(f"Error adding template {name}: {str(e)}")
            return False
    
    def get_template(self, name: str) -> Optional[AlertTemplate]:
        """
        Get a template by name
        
        Args:
            name: Template name
            
        Returns:
            Template object or None if not found
        """
        return self.templates.get(name)
    
    def remove_template(self, name: str) -> bool:
        """
        Remove a template
        
        Args:
            name: Template name
            
        Returns:
            True if template was removed successfully
        """
        try:
            if name in self.templates:
                del self.templates[name]
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error removing template {name}: {str(e)}")
            return False
    
    def list_templates(self) -> List[Dict[str, Any]]:
        """
        List all templates
        
        Returns:
            List of template information dictionaries
        """
        return [
            {
                "name": template.name,
                "description": template.description,
                "created_at": template.created_at,
                "updated_at": template.updated_at,
                "usage_count": template.usage_count
            }
            for template in self.templates.values()
        ]
    
    def format_alert(self, event: AIEvent, template_name: str = None, **kwargs) -> str:
        """
        Format an alert using the specified template
        
        Args:
            event: The event to format
            template_name: Name of template to use (uses default if None)
            **kwargs: Additional formatting parameters
            
        Returns:
            Formatted message string
        """
        try:
            # Get template
            if template_name:
                template = self.get_template(template_name)
                if not template:
                    logger.warning(f"Template {template_name} not found, using default")
                    template_name = None
            
            # Use default template based on event category
            if not template_name:
                if event.category == EventCategory.MARKET_ALERT:
                    template_name = "price_alert"
                elif event.category == EventCategory.RISK_ALERT:
                    template_name = "risk_alert"
                elif event.category == EventCategory.TRADE_SIGNAL:
                    template_name = "trade_signal"
                else:
                    template_name = "price_alert"  # fallback
            
            template = self.get_template(template_name)
            if not template:
                logger.error(f"Default template {template_name} not found")
                return str(event)
            
            # Format message
            return template.format(event, **kwargs)
            
        except Exception as e:
            logger.error(f"Error formatting alert: {str(e)}")
            return str(event) 