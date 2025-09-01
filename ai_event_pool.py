"""
AI Event Pool Module

Manages AI-generated events and their distribution to subscribers.
"""

import logging
from datetime import datetime
from enum import Enum
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class EventPriority(Enum):
    """Event priority levels"""
    CRITICAL = 0
    URGENT = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4
    INFO = 5

class EventCategory(Enum):
    """Event categories"""
    SYSTEM = "system"
    MARKET_ALERT = "market_alert"
    TRADE_SIGNAL = "trade_signal"
    RISK_ALERT = "risk_alert"
    PERFORMANCE = "performance"
    ANALYSIS = "analysis"

@dataclass
class AIEvent:
    """AI-generated event"""
    title: str
    symbol: str
    category: EventCategory
    priority: EventPriority
    content: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)
    actions: List[Dict[str, str]] = field(default_factory=list)

class AIEventPool:
    """Pool for managing AI events"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the event pool
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.events: List[AIEvent] = []
        self.handlers: Dict[str, List[callable]] = {}
        self.max_events = config.get("max_events", 1000)
        
        logger.info("AI Event Pool initialized")
    
    def add_event(self, event: AIEvent) -> None:
        """
        Add an event to the pool
        
        Args:
            event: The event to add
        """
        self.events.append(event)
        
        # Trim old events if needed
        if len(self.events) > self.max_events:
            self.events = self.events[-self.max_events:]
        
        # Notify handlers
        self._notify_handlers(event)
    
    def register_handler(self, event_type: str, handler: callable) -> None:
        """
        Register an event handler
        
        Args:
            event_type: Type of event to handle
            handler: Handler function
        """
        if event_type not in self.handlers:
            self.handlers[event_type] = []
        self.handlers[event_type].append(handler)
    
    def _notify_handlers(self, event: AIEvent) -> None:
        """
        Notify all handlers for an event
        
        Args:
            event: The event to notify about
        """
        event_type = event.category.value
        if event_type in self.handlers:
            for handler in self.handlers[event_type]:
                try:
                    handler(event)
                except Exception as e:
                    logger.error(f"Error in event handler: {str(e)}")
    
    def get_events(self, 
                  category: Optional[EventCategory] = None,
                  priority: Optional[EventPriority] = None,
                  symbol: Optional[str] = None,
                  limit: int = 100) -> List[AIEvent]:
        """
        Get events matching criteria
        
        Args:
            category: Filter by category
            priority: Filter by priority
            symbol: Filter by symbol
            limit: Maximum number of events to return
            
        Returns:
            List of matching events
        """
        events = self.events
        
        if category:
            events = [e for e in events if e.category == category]
        if priority:
            events = [e for e in events if e.priority == priority]
        if symbol:
            events = [e for e in events if e.symbol == symbol]
            
        return events[-limit:] 