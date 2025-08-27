"""
AI Event Intelligence Pool

A central hub that collects, categorizes, and manages all AI-generated market intelligence events.
These events can be subscribed to by various components of the system or by users.
"""

import os
import json
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union
from enum import Enum
import threading

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class EventPriority(Enum):
    """Event priority levels"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    URGENT = 4
    CRITICAL = 5

class EventCategory(Enum):
    """Event category types"""
    LIQUIDITY_SIGNAL = "liquidity_signal"
    WHALE_ALERT = "whale_alert"
    MARKET_IMBALANCE = "market_imbalance"
    TECHNICAL_SIGNAL = "technical_signal"
    OPTIONS_ALERT = "options_alert"
    AI_INSIGHT = "ai_insight"
    STRATEGY_UPDATE = "strategy_update"
    POSITION_CHANGE = "position_change"
    NEWS_IMPACT = "news_impact"
    RISK_WARNING = "risk_warning"

class AIEvent:
    """An AI-generated intelligence event"""
    
    def __init__(
        self,
        event_id: str,
        timestamp: str,
        category: EventCategory,
        symbol: str,
        title: str,
        content: str,
        priority: EventPriority = EventPriority.MEDIUM,
        source: str = "ai_commander",
        expiry: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        actions: Optional[List[Dict[str, Any]]] = None
    ):
        """
        Initialize an AI event
        
        Args:
            event_id: Unique identifier for the event
            timestamp: ISO format timestamp when the event was generated
            category: Event category
            symbol: Market symbol related to this event
            title: Short title/summary of the event
            content: Detailed event description/analysis
            priority: Event priority level
            source: Component that generated this event
            expiry: When this event should expire (ISO timestamp)
            metadata: Additional structured data
            actions: Recommended actions based on this event
        """
        self.event_id = event_id
        self.timestamp = timestamp
        self.category = category
        self.symbol = symbol
        self.title = title
        self.content = content
        self.priority = priority
        self.source = source
        self.expiry = expiry or (datetime.fromisoformat(timestamp) + timedelta(days=1)).isoformat()
        self.metadata = metadata or {}
        self.actions = actions or []
        self.delivered_to = set()  # Track which subscribers have received this
    
    def is_expired(self) -> bool:
        """Check if the event has expired"""
        if not self.expiry:
            return False
        return datetime.fromisoformat(self.expiry) < datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary representation"""
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp,
            "category": self.category.value,
            "symbol": self.symbol,
            "title": self.title,
            "content": self.content,
            "priority": self.priority.value,
            "source": self.source,
            "expiry": self.expiry,
            "metadata": self.metadata,
            "actions": self.actions,
            "delivered_to": list(self.delivered_to)
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AIEvent':
        """Create an event from dictionary representation"""
        # Convert string category to enum
        category = EventCategory(data["category"])
        # Convert priority value to enum
        priority = EventPriority(data["priority"])
        
        event = cls(
            event_id=data["event_id"],
            timestamp=data["timestamp"],
            category=category,
            symbol=data["symbol"],
            title=data["title"],
            content=data["content"],
            priority=priority,
            source=data["source"],
            expiry=data.get("expiry"),
            metadata=data.get("metadata", {}),
            actions=data.get("actions", [])
        )
        
        # Restore delivery tracking
        event.delivered_to = set(data.get("delivered_to", []))
        
        return event

class AIEventPool:
    """Central repository for AI-generated events"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the AI Event Pool
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.events: Dict[str, AIEvent] = {}  # event_id -> event
        self.category_indexes: Dict[EventCategory, List[str]] = {
            category: [] for category in EventCategory
        }
        self.symbol_indexes: Dict[str, List[str]] = {}  # symbol -> [event_ids]
        self.priority_indexes: Dict[EventPriority, List[str]] = {
            priority: [] for priority in EventPriority
        }
        
        # Storage paths
        self.storage_path = "data/ai/events"
        os.makedirs(self.storage_path, exist_ok=True)
        
        # Lock for thread safety
        self.lock = threading.RLock()
        
        # Load existing events
        self._load_events()
        
        # Start cleanup thread for expired events
        self.cleanup_thread = threading.Thread(target=self._cleanup_expired_events, daemon=True)
        self.cleanup_thread.start()
        
        logger.info("AI Event Intelligence Pool initialized")
    
    def _load_events(self):
        """Load events from storage"""
        try:
            events_file = os.path.join(self.storage_path, "events.json")
            if os.path.exists(events_file):
                with open(events_file, 'r') as f:
                    events_data = json.load(f)
                
                for event_data in events_data:
                    try:
                        event = AIEvent.from_dict(event_data)
                        if not event.is_expired():
                            self.add_event(event)
                    except Exception as e:
                        logger.error(f"Failed to load event: {str(e)}")
                
                logger.info(f"Loaded {len(self.events)} events from storage")
        except Exception as e:
            logger.error(f"Error loading events: {str(e)}")
    
    def _save_events(self):
        """Save events to storage"""
        try:
            events_data = [event.to_dict() for event in self.events.values()]
            
            events_file = os.path.join(self.storage_path, "events.json")
            with open(events_file, 'w') as f:
                json.dump(events_data, f, indent=2)
            
            logger.debug(f"Saved {len(events_data)} events to storage")
        except Exception as e:
            logger.error(f"Error saving events: {str(e)}")
    
    def add_event(self, event: AIEvent) -> bool:
        """
        Add a new event to the pool
        
        Args:
            event: The event to add
            
        Returns:
            True if added successfully, False otherwise
        """
        with self.lock:
            # Check if event already exists
            if event.event_id in self.events:
                logger.warning(f"Event {event.event_id} already exists, skipping")
                return False
            
            # Add to main storage
            self.events[event.event_id] = event
            
            # Add to category index
            self.category_indexes[event.category].append(event.event_id)
            
            # Add to symbol index
            if event.symbol not in self.symbol_indexes:
                self.symbol_indexes[event.symbol] = []
            self.symbol_indexes[event.symbol].append(event.event_id)
            
            # Add to priority index
            self.priority_indexes[event.priority].append(event.event_id)
            
            # Save to storage
            self._save_events()
            
            logger.info(f"Added new event: {event.event_id} - {event.title}")
            return True
    
    def get_event(self, event_id: str) -> Optional[AIEvent]:
        """
        Get an event by ID
        
        Args:
            event_id: The event ID to retrieve
            
        Returns:
            The event if found, None otherwise
        """
        with self.lock:
            return self.events.get(event_id)
    
    def mark_delivered(self, event_id: str, subscriber_id: str) -> bool:
        """
        Mark an event as delivered to a subscriber
        
        Args:
            event_id: Event ID
            subscriber_id: Subscriber identifier
            
        Returns:
            True if marked successfully, False otherwise
        """
        with self.lock:
            event = self.get_event(event_id)
            if not event:
                return False
            
            event.delivered_to.add(subscriber_id)
            return True
    
    def get_events_by_category(self, category: EventCategory, limit: int = 100) -> List[AIEvent]:
        """
        Get events by category
        
        Args:
            category: Event category to filter by
            limit: Maximum number of events to return
            
        Returns:
            List of matching events
        """
        with self.lock:
            event_ids = self.category_indexes.get(category, [])
            # Get the events and sort by timestamp (newest first)
            events = [self.events[event_id] for event_id in event_ids if event_id in self.events]
            events.sort(key=lambda e: e.timestamp, reverse=True)
            return events[:limit]
    
    def get_events_by_symbol(self, symbol: str, limit: int = 100) -> List[AIEvent]:
        """
        Get events by symbol
        
        Args:
            symbol: Market symbol to filter by
            limit: Maximum number of events to return
            
        Returns:
            List of matching events
        """
        with self.lock:
            event_ids = self.symbol_indexes.get(symbol, [])
            # Get the events and sort by timestamp (newest first)
            events = [self.events[event_id] for event_id in event_ids if event_id in self.events]
            events.sort(key=lambda e: e.timestamp, reverse=True)
            return events[:limit]
    
    def get_events_by_priority(self, priority: EventPriority, limit: int = 100) -> List[AIEvent]:
        """
        Get events by priority level
        
        Args:
            priority: Priority level to filter by
            limit: Maximum number of events to return
            
        Returns:
            List of matching events
        """
        with self.lock:
            event_ids = self.priority_indexes.get(priority, [])
            # Get the events and sort by timestamp (newest first)
            events = [self.events[event_id] for event_id in event_ids if event_id in self.events]
            events.sort(key=lambda e: e.timestamp, reverse=True)
            return events[:limit]
    
    def get_undelivered_events(self, subscriber_id: str, limit: int = 100) -> List[AIEvent]:
        """
        Get events not yet delivered to a subscriber
        
        Args:
            subscriber_id: Subscriber identifier
            limit: Maximum number of events to return
            
        Returns:
            List of undelivered events
        """
        with self.lock:
            # Find events that haven't been delivered to this subscriber
            undelivered = [
                event for event in self.events.values()
                if subscriber_id not in event.delivered_to and not event.is_expired()
            ]
            
            # Sort by priority (highest first) and then by timestamp (newest first)
            undelivered.sort(key=lambda e: (e.priority.value, e.timestamp), reverse=True)
            
            return undelivered[:limit]
    
    def delete_event(self, event_id: str) -> bool:
        """
        Delete an event from the pool
        
        Args:
            event_id: The event ID to delete
            
        Returns:
            True if deleted successfully, False otherwise
        """
        with self.lock:
            if event_id not in self.events:
                return False
            
            event = self.events[event_id]
            
            # Remove from main storage
            del self.events[event_id]
            
            # Remove from category index
            if event.category in self.category_indexes:
                self.category_indexes[event.category] = [
                    eid for eid in self.category_indexes[event.category] if eid != event_id
                ]
            
            # Remove from symbol index
            if event.symbol in self.symbol_indexes:
                self.symbol_indexes[event.symbol] = [
                    eid for eid in self.symbol_indexes[event.symbol] if eid != event_id
                ]
            
            # Remove from priority index
            if event.priority in self.priority_indexes:
                self.priority_indexes[event.priority] = [
                    eid for eid in self.priority_indexes[event.priority] if eid != event_id
                ]
            
            # Save changes
            self._save_events()
            
            logger.debug(f"Deleted event: {event_id}")
            return True
    
    def _cleanup_expired_events(self):
        """Periodically clean up expired events"""
        while True:
            try:
                now = datetime.now()
                with self.lock:
                    # Find expired events
                    expired_ids = [
                        event_id for event_id, event in self.events.items()
                        if event.is_expired()
                    ]
                    
                    # Delete expired events
                    for event_id in expired_ids:
                        self.delete_event(event_id)
                    
                    if expired_ids:
                        logger.info(f"Cleaned up {len(expired_ids)} expired events")
            except Exception as e:
                logger.error(f"Error during event cleanup: {str(e)}")
            
            # Sleep for 1 hour
            time.sleep(3600)
    
    def generate_event_id(self) -> str:
        """Generate a unique event ID"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        return f"evt_{timestamp}_{len(self.events)}"
    
    def create_liquidity_event(
        self,
        symbol: str,
        imbalance: float,
        analysis: str,
        metadata: Dict[str, Any] = None
    ) -> str:
        """
        Create a liquidity imbalance event
        
        Args:
            symbol: Market symbol
            imbalance: Imbalance value (-1 to 1)
            analysis: AI analysis of the imbalance
            metadata: Additional data about the imbalance
            
        Returns:
            Event ID of the created event
        """
        # Determine priority based on imbalance magnitude
        priority = EventPriority.LOW
        if abs(imbalance) > 0.7:
            priority = EventPriority.HIGH
        elif abs(imbalance) > 0.4:
            priority = EventPriority.MEDIUM
        
        # Format title based on direction
        direction = "bullish" if imbalance > 0 else "bearish"
        magnitude = abs(imbalance)
        title = f"{symbol} shows {magnitude:.2f} {direction} order imbalance"
        
        # Create event
        event = AIEvent(
            event_id=self.generate_event_id(),
            timestamp=datetime.now().isoformat(),
            category=EventCategory.MARKET_IMBALANCE,
            symbol=symbol,
            title=title,
            content=analysis,
            priority=priority,
            source="liquidity_sniper",
            metadata=metadata or {
                "imbalance_value": imbalance,
                "imbalance_direction": direction,
                "imbalance_magnitude": magnitude
            }
        )
        
        # Add to pool
        self.add_event(event)
        return event.event_id
    
    def create_whale_alert(
        self,
        symbol: str,
        side: str,
        value: float,
        analysis: str,
        exchange: str = "unknown",
        metadata: Dict[str, Any] = None
    ) -> str:
        """
        Create a whale alert event
        
        Args:
            symbol: Market symbol
            side: Trade side (buy/sell)
            value: Trade value in USD
            analysis: AI analysis of the whale activity
            exchange: Exchange where the trade occurred
            metadata: Additional data about the whale activity
            
        Returns:
            Event ID of the created event
        """
        # Determine priority based on value
        priority = EventPriority.MEDIUM
        if value > 5000000:
            priority = EventPriority.URGENT
        elif value > 1000000:
            priority = EventPriority.HIGH
        
        # Format amounts for display
        formatted_value = f"${value:,.2f}"
        
        # Create title
        title = f"Whale Alert: {side.upper()} {symbol} {formatted_value}"
        
        # Create event
        event = AIEvent(
            event_id=self.generate_event_id(),
            timestamp=datetime.now().isoformat(),
            category=EventCategory.WHALE_ALERT,
            symbol=symbol,
            title=title,
            content=analysis,
            priority=priority,
            source="whale_monitor",
            metadata=metadata or {
                "trade_side": side,
                "trade_value": value,
                "exchange": exchange
            }
        )
        
        # Add to pool
        self.add_event(event)
        return event.event_id
    
    def create_ai_insight(
        self,
        symbol: str,
        title: str,
        analysis: str,
        priority: EventPriority = EventPriority.MEDIUM,
        metadata: Dict[str, Any] = None,
        actions: List[Dict[str, Any]] = None
    ) -> str:
        """
        Create an AI insight event
        
        Args:
            symbol: Market symbol
            title: Insight title
            analysis: Detailed AI analysis
            priority: Event priority
            metadata: Additional data
            actions: Recommended actions
            
        Returns:
            Event ID of the created event
        """
        # Create event
        event = AIEvent(
            event_id=self.generate_event_id(),
            timestamp=datetime.now().isoformat(),
            category=EventCategory.AI_INSIGHT,
            symbol=symbol,
            title=title,
            content=analysis,
            priority=priority,
            source="ai_commander",
            metadata=metadata or {},
            actions=actions or []
        )
        
        # Add to pool
        self.add_event(event)
        return event.event_id

# For testing
if __name__ == "__main__":
    # Initialize with test config
    test_config = {"storage": {"event_pool_path": "data/ai/events"}}
    pool = AIEventPool(test_config)
    
    # Create a test liquidity event
    event_id = pool.create_liquidity_event(
        symbol="AAPL",
        imbalance=0.65,
        analysis="Strong buying pressure detected on AAPL with significant order book imbalance."
    )
    
    # Create a test whale alert
    whale_id = pool.create_whale_alert(
        symbol="BTC-USD",
        side="buy",
        value=5235000,
        analysis="Large BTC purchase detected. This follows three similar buys in the past 24 hours."
    )
    
    # Retrieve events
    liquidity_events = pool.get_events_by_category(EventCategory.MARKET_IMBALANCE)
    whale_alerts = pool.get_events_by_category(EventCategory.WHALE_ALERT)
    
    print(f"Created {len(pool.events)} test events")
    print(f"Retrieved {len(liquidity_events)} liquidity events")
    print(f"Retrieved {len(whale_alerts)} whale alerts") 