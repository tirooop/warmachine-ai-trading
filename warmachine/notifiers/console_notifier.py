"""
Console Notifier

Simple console-based notifier for testing AI event delivery.
"""

import logging
from typing import Dict, List, Any
from ai_event_pool import AIEvent

logger = logging.getLogger(__name__)

class ConsoleNotifier:
    """Console-based notification service for testing"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize console notifier
        
        Args:
            config: Configuration dictionary (optional)
        """
        self.config = config or {}
        logger.info("Console notifier initialized")
    
    def send_event(self, event: AIEvent, subscription: Any) -> bool:
        """
        Send a single event to the console
        
        Args:
            event: The event to send
            subscription: Subscription details
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Print a formatted message to the console
            print(f"\n{'=' * 60}")
            print(f"EVENT: {event.title}")
            print(f"{'=' * 60}")
            print(f"PRIORITY: {event.priority.name}")
            print(f"CATEGORY: {event.category.value}")
            print(f"SYMBOL: {event.symbol}")
            print(f"TIMESTAMP: {event.timestamp}")
            print(f"{'=' * 60}")
            print(f"{event.content}")
            print(f"{'=' * 60}")
            
            # Add metadata if available
            if event.metadata:
                print("METADATA:")
                for key, value in event.metadata.items():
                    print(f"  {key}: {value}")
                print(f"{'=' * 60}")
            
            # Add recommended actions if available
            if event.actions:
                print("RECOMMENDED ACTIONS:")
                for i, action in enumerate(event.actions, 1):
                    print(f"  {i}. {action.get('description', 'No description')}")
                print(f"{'=' * 60}")
            
            print(f"Delivered to: {subscription.subscriber_id} ({subscription.name})\n")
            
            return True
        except Exception as e:
            logger.error(f"Error sending event to console: {str(e)}")
            return False
    
    def send_batch(self, events: List[AIEvent], subscription: Any) -> bool:
        """
        Send multiple events to the console
        
        Args:
            events: List of events to send
            subscription: Subscription details
        
        Returns:
            True if successful, False otherwise
        """
        try:
            print(f"\n{'#' * 80}")
            print(f"BATCH NOTIFICATION FOR: {subscription.subscriber_id} ({subscription.name})")
            print(f"{'#' * 80}")
            print(f"EVENTS COUNT: {len(events)}")
            print(f"{'#' * 80}\n")
            
            for event in events:
                self.send_event(event, subscription)
            
            return True
        except Exception as e:
            logger.error(f"Error sending batch events to console: {str(e)}")
            return False 