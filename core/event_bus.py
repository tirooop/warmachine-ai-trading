"""
Event Bus for WarMachine Trading System

This module implements the event bus system for handling various types of events,
including market data, news, and sentiment analysis.
"""

import logging
from typing import Dict, Any, List, Callable, Optional
from datetime import datetime
import json
import asyncio
from collections import defaultdict

from .analysis.sentiment_adapter import SentimentAdapter

logger = logging.getLogger(__name__)

class EventType:
    """Event types enumeration"""
    MARKET_DATA = "market_data"
    NEWS = "news"
    SENTIMENT = "sentiment"
    SOCIAL_MEDIA = "social_media"
    TRADE = "trade"
    SYSTEM = "system"

class EventBus:
    """Event bus for handling system events"""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize event bus
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        
        # Initialize handlers
        self.handlers = defaultdict(list)
        
        # Initialize sentiment adapter
        self.sentiment_adapter = SentimentAdapter(config.get("sentiment", {}))
        
        # Initialize event queue
        self.event_queue = asyncio.Queue()
        
        # Initialize event history
        self.event_history = []
        self.max_history_size = config.get("max_history_size", 1000)
        
    async def publish(self, event_type: str, event_data: Dict[str, Any]):
        """Publish event to bus
        
        Args:
            event_type: Type of event
            event_data: Event data
        """
        try:
            # Add timestamp if not present
            if "timestamp" not in event_data:
                event_data["timestamp"] = datetime.now().isoformat()
                
            # Process event based on type
            if event_type == EventType.NEWS:
                processed_data = self.sentiment_adapter.process_news(event_data)
                event_data["sentiment"] = processed_data
                
            elif event_type == EventType.SOCIAL_MEDIA:
                processed_data = self.sentiment_adapter.process_social_media(event_data)
                event_data["sentiment"] = processed_data
                
            # Create event
            event = {
                "type": event_type,
                "data": event_data,
                "timestamp": datetime.now().isoformat()
            }
            
            # Add to queue
            await self.event_queue.put(event)
            
            # Add to history
            self.event_history.append(event)
            if len(self.event_history) > self.max_history_size:
                self.event_history.pop(0)
                
            # Notify handlers
            await self._notify_handlers(event)
            
        except Exception as e:
            logger.error(f"Error publishing event: {str(e)}")
            raise
            
    def subscribe(self, event_type: str, handler: Callable):
        """Subscribe to event type
        
        Args:
            event_type: Type of event to subscribe to
            handler: Handler function
        """
        self.handlers[event_type].append(handler)
        
    def unsubscribe(self, event_type: str, handler: Callable):
        """Unsubscribe from event type
        
        Args:
            event_type: Type of event to unsubscribe from
            handler: Handler function to remove
        """
        if handler in self.handlers[event_type]:
            self.handlers[event_type].remove(handler)
            
    async def _notify_handlers(self, event: Dict[str, Any]):
        """Notify handlers of event
        
        Args:
            event: Event to notify handlers of
        """
        try:
            event_type = event["type"]
            
            # Notify specific handlers
            for handler in self.handlers[event_type]:
                try:
                    await handler(event)
                except Exception as e:
                    logger.error(f"Error in event handler: {str(e)}")
                    
            # Notify wildcard handlers
            for handler in self.handlers["*"]:
                try:
                    await handler(event)
                except Exception as e:
                    logger.error(f"Error in wildcard handler: {str(e)}")
                    
        except Exception as e:
            logger.error(f"Error notifying handlers: {str(e)}")
            raise
            
    async def process_queue(self):
        """Process event queue"""
        while True:
            try:
                # Get event from queue
                event = await self.event_queue.get()
                
                # Process event
                await self._notify_handlers(event)
                
                # Mark task as done
                self.event_queue.task_done()
                
            except Exception as e:
                logger.error(f"Error processing queue: {str(e)}")
                
    def get_event_history(
        self,
        event_type: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get event history
        
        Args:
            event_type: Filter by event type
            start_time: Filter by start time
            end_time: Filter by end time
            
        Returns:
            List of events
        """
        try:
            # Filter events
            filtered_events = self.event_history
            
            if event_type:
                filtered_events = [e for e in filtered_events if e["type"] == event_type]
                
            if start_time:
                filtered_events = [
                    e for e in filtered_events
                    if e["timestamp"] >= start_time
                ]
                
            if end_time:
                filtered_events = [
                    e for e in filtered_events
                    if e["timestamp"] <= end_time
                ]
                
            return filtered_events
            
        except Exception as e:
            logger.error(f"Error getting event history: {str(e)}")
            raise
            
    def save_event_history(self, filepath: str):
        """Save event history to file
        
        Args:
            filepath: Path to save history
        """
        try:
            with open(filepath, "w") as f:
                json.dump(self.event_history, f, indent=2)
                
        except Exception as e:
            logger.error(f"Error saving event history: {str(e)}")
            raise
            
    def load_event_history(self, filepath: str):
        """Load event history from file
        
        Args:
            filepath: Path to load history from
        """
        try:
            with open(filepath, "r") as f:
                self.event_history = json.load(f)
                
        except Exception as e:
            logger.error(f"Error loading event history: {str(e)}")
            raise 