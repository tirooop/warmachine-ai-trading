"""
Event Pool - Central event management system for WarMachine

This module manages the event pool that coordinates communication between
different components of the WarMachine system.
"""

import logging
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime

# Set up logging
logger = logging.getLogger(__name__)

class EventPool:
    """Central event management system"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the Event Pool

        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.events = {}
        self.subscribers = {}
        self.running = False
        logger.info("Event Pool initialized")
    
    async def start(self):
        """Start the Event Pool service"""
        try:
            logger.info("Starting Event Pool...")
            self.running = True
            return True
        except Exception as e:
            logger.error(f"Failed to start Event Pool: {str(e)}")
            return False
    
    async def shutdown(self):
        """Shutdown the Event Pool service"""
        try:
            logger.info("Shutting down Event Pool...")
            self.running = False
            return True
        except Exception as e:
            logger.error(f"Failed to shutdown Event Pool: {str(e)}")
            return False
    
    def publish_event(self, event_type: str, data: Any):
        """Publish an event to the pool"""
        if not self.running:
            return
        
        try:
            event = {
                "type": event_type,
                "data": data,
                "timestamp": datetime.now().isoformat()
            }
            
            self.events[event_type] = event
            
            # Notify subscribers
            if event_type in self.subscribers:
                for callback in self.subscribers[event_type]:
                    try:
                        callback(event)
                    except Exception as e:
                        logger.error(f"Error in event subscriber: {str(e)}")
        except Exception as e:
            logger.error(f"Error publishing event: {str(e)}")
    
    def subscribe(self, event_type: str, callback):
        """Subscribe to an event type"""
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        self.subscribers[event_type].append(callback)
    
    def unsubscribe(self, event_type: str, callback):
        """Unsubscribe from an event type"""
        if event_type in self.subscribers:
            self.subscribers[event_type].remove(callback)
    
    def get_latest_event(self, event_type: str) -> Optional[Dict[str, Any]]:
        """Get the latest event of a specific type"""
        return self.events.get(event_type)
    
    def get_all_events(self) -> Dict[str, Dict[str, Any]]:
        """Get all events"""
        return self.events.copy() 