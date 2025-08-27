"""
Component Notifier

Delivers AI intelligence events to internal system components.
"""

import logging
import threading
from typing import Dict, List, Any, Optional, Callable
from ai_event_pool import AIEvent
from ai_event_pool import EventCategory, EventPriority

logger = logging.getLogger(__name__)

class ComponentNotifier:
    """Notification service for internal components"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize component notifier
        
        Args:
            config: Configuration dictionary (optional)
        """
        self.config = config or {}
        self.callbacks: Dict[str, Callable] = {}  # component_id -> callback function
        self.lock = threading.RLock()
        
        logger.info("Component notifier initialized")
    
    def register_callback(self, component_id: str, callback: Callable[[AIEvent], bool]) -> None:
        """
        Register a callback function for a component
        
        Args:
            component_id: Component identifier
            callback: Function to call with events
        """
        with self.lock:
            self.callbacks[component_id] = callback
            logger.info(f"Registered callback for component: {component_id}")
    
    def unregister_callback(self, component_id: str) -> None:
        """
        Unregister a component's callback
        
        Args:
            component_id: Component identifier
        """
        with self.lock:
            if component_id in self.callbacks:
                del self.callbacks[component_id]
                logger.info(f"Unregistered callback for component: {component_id}")
    
    def send_event(self, event: AIEvent, subscription: Any) -> bool:
        """
        Send an event to a component
        
        Args:
            event: The event to send
            subscription: Subscription details
            
        Returns:
            True if successfully delivered, False otherwise
        """
        try:
            # Get component ID from the subscription
            component_id = subscription.subscriber_id
            if component_id.startswith("component_"):
                component_id = component_id[10:]  # Remove "component_" prefix
            
            with self.lock:
                callback = self.callbacks.get(component_id)
                if not callback:
                    logger.warning(f"No callback registered for component: {component_id}")
                    return False
                
                # Call the component's callback function
                success = callback(event)
                
                if success:
                    logger.debug(f"Successfully delivered event to component: {component_id}")
                else:
                    logger.warning(f"Component {component_id} failed to process event")
                
                return success
                
        except Exception as e:
            logger.error(f"Error sending event to component: {str(e)}")
            return False
    
    def send_batch(self, events: List[AIEvent], subscription: Any) -> bool:
        """
        Send multiple events to a component
        
        Args:
            events: The events to send
            subscription: Subscription details
            
        Returns:
            True if all successfully delivered, False otherwise
        """
        if not events:
            return True
        
        # Process events individually
        success_count = 0
        for event in events:
            if self.send_event(event, subscription):
                success_count += 1
        
        # Return True only if all events were successfully delivered
        return success_count == len(events)

# Example usage (for demonstration purposes)
if __name__ == "__main__":
    from datetime import datetime
    
    # Create a test event
    test_event = AIEvent(
        event_id="test_event_1",
        timestamp=datetime.now().isoformat(),
        category=EventCategory.MARKET_IMBALANCE,
        symbol="BTC-USD",
        title="Test Event",
        content="This is a test event for component notification.",
        priority=EventPriority.HIGH
    )
    
    # Create a mock subscription
    class MockSubscription:
        def __init__(self, subscriber_id):
            self.subscriber_id = subscriber_id
    
    # Create notifier
    notifier = ComponentNotifier()
    
    # Define a callback function
    def test_callback(event):
        print(f"Received event: {event.title}")
        return True
    
    # Register the callback
    notifier.register_callback("test_component", test_callback)
    
    # Test sending an event
    subscription = MockSubscription("component_test_component")
    notifier.send_event(test_event, subscription) 