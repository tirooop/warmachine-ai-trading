"""
Alert Subscription Manager

Manages alert subscriptions and user preferences.
"""

import logging
from typing import Dict, Any, List, Optional, Set
from datetime import datetime
from ai_event_pool import EventCategory, EventPriority

logger = logging.getLogger(__name__)

class AlertSubscription:
    """Alert subscription settings for a user"""
    
    def __init__(self, user_id: str, chat_id: str):
        """
        Initialize alert subscription
        
        Args:
            user_id: Telegram user ID
            chat_id: Telegram chat ID
        """
        self.user_id = user_id
        self.chat_id = chat_id
        self.created_at = datetime.now().isoformat()
        self.updated_at = self.created_at
        
        # Subscription settings
        self.enabled_categories: Set[EventCategory] = set([
            EventCategory.MARKET_ALERT,
            EventCategory.RISK_ALERT,
            EventCategory.TRADE_SIGNAL
        ])
        
        self.min_priority = EventPriority.LOW
        self.max_notifications_per_minute = 60
        self.cooldown_periods = {
            EventPriority.CRITICAL: 60,  # seconds
            EventPriority.URGENT: 300,
            EventPriority.HIGH: 900,
            EventPriority.MEDIUM: 1800,
            EventPriority.LOW: 3600
        }
        
        # Notification preferences
        self.template_name = None  # Use default template
        self.format_type = "markdown"
        self.enable_web_preview = False
        self.enable_sound = True
        self.enable_vibration = True
        
        # Alert filters
        self.symbols: Set[str] = set()  # Empty means all symbols
        self.strategies: Set[str] = set()  # Empty means all strategies
        self.tags: Set[str] = set()
        
        # Statistics
        self.notification_count = 0
        self.last_notification_time = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert subscription to dictionary"""
        return {
            "user_id": self.user_id,
            "chat_id": self.chat_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "enabled_categories": [cat.value for cat in self.enabled_categories],
            "min_priority": self.min_priority.name,
            "max_notifications_per_minute": self.max_notifications_per_minute,
            "cooldown_periods": {k.name: v for k, v in self.cooldown_periods.items()},
            "template_name": self.template_name,
            "format_type": self.format_type,
            "enable_web_preview": self.enable_web_preview,
            "enable_sound": self.enable_sound,
            "enable_vibration": self.enable_vibration,
            "symbols": list(self.symbols),
            "strategies": list(self.strategies),
            "tags": list(self.tags),
            "notification_count": self.notification_count,
            "last_notification_time": self.last_notification_time
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AlertSubscription':
        """Create subscription from dictionary"""
        sub = cls(data["user_id"], data["chat_id"])
        sub.created_at = data["created_at"]
        sub.updated_at = data["updated_at"]
        
        # Convert category strings back to enums
        sub.enabled_categories = {
            EventCategory(cat) for cat in data["enabled_categories"]
        }
        
        sub.min_priority = EventPriority[data["min_priority"]]
        sub.max_notifications_per_minute = data["max_notifications_per_minute"]
        
        # Convert cooldown periods back to enums
        sub.cooldown_periods = {
            EventPriority[k]: v for k, v in data["cooldown_periods"].items()
        }
        
        sub.template_name = data["template_name"]
        sub.format_type = data["format_type"]
        sub.enable_web_preview = data["enable_web_preview"]
        sub.enable_sound = data["enable_sound"]
        sub.enable_vibration = data["enable_vibration"]
        
        sub.symbols = set(data["symbols"])
        sub.strategies = set(data["strategies"])
        sub.tags = set(data["tags"])
        
        sub.notification_count = data["notification_count"]
        sub.last_notification_time = data["last_notification_time"]
        
        return sub

class AlertSubscriptionManager:
    """Manager for alert subscriptions"""
    
    def __init__(self):
        """Initialize subscription manager"""
        self.subscriptions: Dict[str, AlertSubscription] = {}
    
    def add_subscription(self, user_id: str, chat_id: str) -> AlertSubscription:
        """
        Add a new subscription
        
        Args:
            user_id: Telegram user ID
            chat_id: Telegram chat ID
            
        Returns:
            New subscription object
        """
        subscription = AlertSubscription(user_id, chat_id)
        self.subscriptions[user_id] = subscription
        logger.info(f"Added subscription for user {user_id}")
        return subscription
    
    def get_subscription(self, user_id: str) -> Optional[AlertSubscription]:
        """
        Get subscription by user ID
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            Subscription object or None if not found
        """
        return self.subscriptions.get(user_id)
    
    def remove_subscription(self, user_id: str) -> bool:
        """
        Remove a subscription
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            True if subscription was removed successfully
        """
        try:
            if user_id in self.subscriptions:
                del self.subscriptions[user_id]
                logger.info(f"Removed subscription for user {user_id}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error removing subscription for user {user_id}: {str(e)}")
            return False
    
    def update_subscription(self, user_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update subscription settings
        
        Args:
            user_id: Telegram user ID
            updates: Dictionary of settings to update
            
        Returns:
            True if subscription was updated successfully
        """
        try:
            subscription = self.get_subscription(user_id)
            if not subscription:
                return False
            
            # Update enabled categories
            if "enabled_categories" in updates:
                subscription.enabled_categories = {
                    EventCategory(cat) for cat in updates["enabled_categories"]
                }
            
            # Update minimum priority
            if "min_priority" in updates:
                subscription.min_priority = EventPriority[updates["min_priority"]]
            
            # Update notification limits
            if "max_notifications_per_minute" in updates:
                subscription.max_notifications_per_minute = updates["max_notifications_per_minute"]
            
            # Update cooldown periods
            if "cooldown_periods" in updates:
                subscription.cooldown_periods = {
                    EventPriority[k]: v for k, v in updates["cooldown_periods"].items()
                }
            
            # Update notification preferences
            if "template_name" in updates:
                subscription.template_name = updates["template_name"]
            if "format_type" in updates:
                subscription.format_type = updates["format_type"]
            if "enable_web_preview" in updates:
                subscription.enable_web_preview = updates["enable_web_preview"]
            if "enable_sound" in updates:
                subscription.enable_sound = updates["enable_sound"]
            if "enable_vibration" in updates:
                subscription.enable_vibration = updates["enable_vibration"]
            
            # Update filters
            if "symbols" in updates:
                subscription.symbols = set(updates["symbols"])
            if "strategies" in updates:
                subscription.strategies = set(updates["strategies"])
            if "tags" in updates:
                subscription.tags = set(updates["tags"])
            
            subscription.updated_at = datetime.now().isoformat()
            logger.info(f"Updated subscription for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating subscription for user {user_id}: {str(e)}")
            return False
    
    def list_subscriptions(self) -> List[Dict[str, Any]]:
        """
        List all subscriptions
        
        Returns:
            List of subscription information dictionaries
        """
        return [sub.to_dict() for sub in self.subscriptions.values()]
    
    def get_subscribers_for_event(self, event: Any) -> List[AlertSubscription]:
        """
        Get subscribers that should receive an event
        
        Args:
            event: The event to check
            
        Returns:
            List of matching subscriptions
        """
        subscribers = []
        
        for subscription in self.subscriptions.values():
            # Check if category is enabled
            if event.category not in subscription.enabled_categories:
                continue
            
            # Check minimum priority
            if event.priority.value > subscription.min_priority.value:
                continue
            
            # Check symbol filter
            if subscription.symbols and event.symbol not in subscription.symbols:
                continue
            
            # Check strategy filter
            if subscription.strategies:
                strategy = event.metadata.get("strategy", "default")
                if strategy not in subscription.strategies:
                    continue
            
            # Check tag filter
            if subscription.tags:
                event_tags = set(event.metadata.get("tags", []))
                if not event_tags.intersection(subscription.tags):
                    continue
            
            subscribers.append(subscription)
        
        return subscribers 