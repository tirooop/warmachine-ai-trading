"""
AI Intelligence Dispatcher

This module is responsible for dispatching AI-generated intelligence events to
various subscribers (users, notification channels, and system components).
It handles subscription management, event filtering, and delivery tracking.
"""

import os
import json
import time
import logging
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union, Set, Callable
from enum import Enum

# Import the event pool
from ai_event_pool import AIEventPool, AIEvent, EventCategory, EventPriority

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SubscriberType(Enum):
    """Types of subscribers that can receive events"""
    USER = "user"
    CHANNEL = "channel"
    COMPONENT = "component"
    WEBHOOK = "webhook"

class SubscriptionFilter:
    """Filter criteria for event subscriptions"""
    
    def __init__(
        self,
        categories: Optional[List[EventCategory]] = None,
        symbols: Optional[List[str]] = None,
        min_priority: EventPriority = EventPriority.LOW,
        sources: Optional[List[str]] = None
    ):
        """
        Initialize a subscription filter
        
        Args:
            categories: Event categories to include (None = all)
            symbols: Market symbols to include (None = all)
            min_priority: Minimum event priority to include
            sources: Event sources to include (None = all)
        """
        self.categories = set(categories) if categories else None
        self.symbols = set(symbols) if symbols else None
        self.min_priority = min_priority
        self.sources = set(sources) if sources else None
    
    def matches(self, event: AIEvent) -> bool:
        """
        Check if an event matches this filter
        
        Args:
            event: The event to check
            
        Returns:
            True if the event matches the filter, False otherwise
        """
        # Check priority
        if event.priority.value < self.min_priority.value:
            return False
        
        # Check categories
        if self.categories and event.category not in self.categories:
            return False
        
        # Check symbols
        if self.symbols and event.symbol not in self.symbols:
            return False
        
        # Check sources
        if self.sources and event.source not in self.sources:
            return False
        
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert filter to dictionary representation"""
        return {
            "categories": [c.value for c in self.categories] if self.categories else None,
            "symbols": list(self.symbols) if self.symbols else None,
            "min_priority": self.min_priority.value,
            "sources": list(self.sources) if self.sources else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SubscriptionFilter':
        """Create a filter from dictionary representation"""
        # Convert category strings to enum values
        categories = None
        if data.get("categories"):
            categories = [EventCategory(c) for c in data["categories"]]
        
        # Convert priority value to enum
        min_priority = EventPriority(data.get("min_priority", EventPriority.LOW.value))
        
        return cls(
            categories=categories,
            symbols=data.get("symbols"),
            min_priority=min_priority,
            sources=data.get("sources")
        )

class Subscription:
    """A subscription to AI intelligence events"""
    
    def __init__(
        self,
        subscriber_id: str,
        subscriber_type: SubscriberType,
        name: str,
        filter: SubscriptionFilter,
        destination: Dict[str, Any],
        is_active: bool = True
    ):
        """
        Initialize a subscription
        
        Args:
            subscriber_id: Unique identifier for the subscriber
            subscriber_type: Type of subscriber
            name: Human-readable name for this subscription
            filter: Event filter for this subscription
            destination: Information needed to deliver events
            is_active: Whether this subscription is currently active
        """
        self.subscriber_id = subscriber_id
        self.subscriber_type = subscriber_type
        self.name = name
        self.filter = filter
        self.destination = destination
        self.is_active = is_active
        self.created_at = datetime.now().isoformat()
        self.last_delivery = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert subscription to dictionary representation"""
        return {
            "subscriber_id": self.subscriber_id,
            "subscriber_type": self.subscriber_type.value,
            "name": self.name,
            "filter": self.filter.to_dict(),
            "destination": self.destination,
            "is_active": self.is_active,
            "created_at": self.created_at,
            "last_delivery": self.last_delivery
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Subscription':
        """Create a subscription from dictionary representation"""
        # Convert subscription type string to enum
        subscriber_type = SubscriberType(data["subscriber_type"])
        
        # Convert filter dict to object
        filter_obj = SubscriptionFilter.from_dict(data["filter"])
        
        subscription = cls(
            subscriber_id=data["subscriber_id"],
            subscriber_type=subscriber_type,
            name=data["name"],
            filter=filter_obj,
            destination=data["destination"],
            is_active=data.get("is_active", True)
        )
        
        subscription.created_at = data.get("created_at", subscription.created_at)
        subscription.last_delivery = data.get("last_delivery")
        
        return subscription

class DeliveryProvider:
    """Base class for event delivery providers"""
    
    def send_event(self, event: AIEvent, subscription: Subscription) -> bool:
        """
        Send an event to a subscriber
        
        Args:
            event: The event to send
            subscription: The subscription to deliver to
            
        Returns:
            True if delivery was successful, False otherwise
        """
        raise NotImplementedError("Subclasses must implement send_event")
    
    def send_batch(self, events: List[AIEvent], subscription: Subscription) -> bool:
        """
        Send multiple events to a subscriber
        
        Args:
            events: The events to send
            subscription: The subscription to deliver to
            
        Returns:
            True if delivery was successful, False otherwise
        """
        raise NotImplementedError("Subclasses must implement send_batch")

class AIIntelligenceDispatcher:
    """整合所有高级功能的Telegram机器人指挥官"""
    
    def __init__(self, config: Dict[str, Any], event_pool: AIEventPool):
        """
        初始化AI智能分发器
        
        Args:
            config: 配置字典
            event_pool: AI事件池实例
        """
        self.config = config
        self.event_pool = event_pool
        self.subscriptions = {}
        self.delivery_providers = {}
        self.delivery_thread = None
        self.running = False
        
        # 加载订阅
        self._load_subscriptions()
        
        # 注册分发提供者
        self._register_delivery_providers()
        
        # 启动分发线程
        self.delivery_thread = threading.Thread(target=self._delivery_loop)
        self.delivery_thread.daemon = True
        self.running = True
        self.delivery_thread.start()
        
        logger.info("AI Intelligence Dispatcher initialized")
    
    def _load_subscriptions(self):
        """Load subscriptions from storage"""
        try:
            subscriptions_file = os.path.join("data/ai/subscriptions", "subscriptions.json")
            if os.path.exists(subscriptions_file):
                with open(subscriptions_file, 'r') as f:
                    subscriptions_data = json.load(f)
                
                for subscription_data in subscriptions_data:
                    try:
                        subscription = Subscription.from_dict(subscription_data)
                        self.subscriptions[subscription.subscriber_id] = subscription
                    except Exception as e:
                        logger.error(f"Failed to load subscription: {str(e)}")
                
                logger.info(f"Loaded {len(self.subscriptions)} subscriptions from storage")
        except Exception as e:
            logger.error(f"Error loading subscriptions: {str(e)}")
    
    def _save_subscriptions(self):
        """Save subscriptions to storage"""
        try:
            subscriptions_data = [subscription.to_dict() for subscription in self.subscriptions.values()]
            
            subscriptions_file = os.path.join("data/ai/subscriptions", "subscriptions.json")
            with open(subscriptions_file, 'w') as f:
                json.dump(subscriptions_data, f, indent=2)
            
            logger.debug(f"Saved {len(subscriptions_data)} subscriptions to storage")
        except Exception as e:
            logger.error(f"Error saving subscriptions: {str(e)}")
    
    def _register_delivery_providers(self):
        """Register event delivery providers"""
        # At minimum, register console provider for testing
        from notifiers.console_notifier import ConsoleNotifier
        self.delivery_providers[SubscriberType.USER] = ConsoleNotifier()
        self.delivery_providers[SubscriberType.CHANNEL] = ConsoleNotifier()
        
        # Try to register Telegram provider
        try:
            from notifiers.telegram_notifier import TelegramNotifier
            telegram_config = self.config.get("telegram", {})
            if telegram_config.get("enabled", False):
                self.delivery_providers[SubscriberType.USER] = TelegramNotifier(telegram_config)
                self.delivery_providers[SubscriberType.CHANNEL] = TelegramNotifier(telegram_config)
                logger.info("Registered Telegram delivery provider")
        except Exception as e:
            logger.warning(f"Failed to register Telegram provider: {str(e)}")
        
        # Try to register Discord provider
        try:
            from notifiers.discord_notifier import DiscordNotifier
            discord_config = self.config.get("discord", {})
            if discord_config.get("enabled", False):
                self.delivery_providers[SubscriberType.CHANNEL] = DiscordNotifier(discord_config)
                logger.info("Registered Discord delivery provider")
        except Exception as e:
            logger.warning(f"Failed to register Discord provider: {str(e)}")
        
        # Try to register webhook provider
        try:
            from notifiers.webhook_notifier import WebhookNotifier
            webhook_config = self.config.get("webhooks", {})
            if webhook_config.get("enabled", False):
                self.delivery_providers[SubscriberType.WEBHOOK] = WebhookNotifier(webhook_config)
                logger.info("Registered Webhook delivery provider")
        except Exception as e:
            logger.warning(f"Failed to register Webhook provider: {str(e)}")
        
        # Register component provider for internal system components
        from notifiers.component_notifier import ComponentNotifier
        self.delivery_providers[SubscriberType.COMPONENT] = ComponentNotifier()
    
    def add_subscription(self, subscription: Subscription) -> bool:
        """
        Add a new subscription
        
        Args:
            subscription: The subscription to add
            
        Returns:
            True if added successfully, False otherwise
        """
        with self.lock:
            # Check if subscription already exists
            if subscription.subscriber_id in self.subscriptions:
                logger.warning(f"Subscription for {subscription.subscriber_id} already exists, updating")
                self.subscriptions[subscription.subscriber_id] = subscription
            else:
                self.subscriptions[subscription.subscriber_id] = subscription
            
            # Save to storage
            self._save_subscriptions()
            
            logger.info(f"Added/updated subscription for {subscription.subscriber_id}")
            return True
    
    def remove_subscription(self, subscriber_id: str) -> bool:
        """
        Remove a subscription
        
        Args:
            subscriber_id: The subscriber ID to remove
            
        Returns:
            True if removed successfully, False otherwise
        """
        with self.lock:
            if subscriber_id not in self.subscriptions:
                logger.warning(f"Subscription for {subscriber_id} not found")
                return False
            
            del self.subscriptions[subscriber_id]
            
            # Save to storage
            self._save_subscriptions()
            
            logger.info(f"Removed subscription for {subscriber_id}")
            return True
    
    def update_subscription(self, subscriber_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update an existing subscription
        
        Args:
            subscriber_id: The subscriber ID to update
            updates: Dictionary of fields to update
            
        Returns:
            True if updated successfully, False otherwise
        """
        with self.lock:
            if subscriber_id not in self.subscriptions:
                logger.warning(f"Subscription for {subscriber_id} not found")
                return False
            
            subscription = self.subscriptions[subscriber_id]
            
            # Update fields
            if "name" in updates:
                subscription.name = updates["name"]
            
            if "filter" in updates:
                subscription.filter = SubscriptionFilter.from_dict(updates["filter"])
            
            if "destination" in updates:
                subscription.destination = updates["destination"]
            
            if "is_active" in updates:
                subscription.is_active = updates["is_active"]
            
            # Save to storage
            self._save_subscriptions()
            
            logger.info(f"Updated subscription for {subscriber_id}")
            return True
    
    def get_subscription(self, subscriber_id: str) -> Optional[Subscription]:
        """
        Get a subscription by ID
        
        Args:
            subscriber_id: The subscriber ID to retrieve
            
        Returns:
            The subscription if found, None otherwise
        """
        with self.lock:
            return self.subscriptions.get(subscriber_id)
    
    def get_all_subscriptions(self) -> List[Subscription]:
        """
        Get all subscriptions
        
        Returns:
            List of all subscriptions
        """
        with self.lock:
            return list(self.subscriptions.values())
    
    def dispatch_event(self, event: AIEvent) -> int:
        """
        Dispatch an event to all matching subscribers
        
        Args:
            event: The event to dispatch
            
        Returns:
            Number of subscribers the event was dispatched to
        """
        delivered_count = 0
        
        with self.lock:
            # Find matching subscriptions
            for subscriber_id, subscription in self.subscriptions.items():
                # Skip inactive subscriptions
                if not subscription.is_active:
                    continue
                
                # Check if event matches subscription filter
                if not subscription.filter.matches(event):
                    continue
                
                # Get appropriate delivery provider
                provider = self.delivery_providers.get(subscription.subscriber_type)
                if not provider:
                    logger.warning(f"No delivery provider for {subscription.subscriber_type}")
                    continue
                
                # Attempt delivery
                try:
                    if provider.send_event(event, subscription):
                        # Mark as delivered
                        self.event_pool.mark_delivered(event.event_id, subscriber_id)
                        subscription.last_delivery = datetime.now().isoformat()
                        delivered_count += 1
                        logger.debug(f"Delivered event {event.event_id} to {subscriber_id}")
                except Exception as e:
                    logger.error(f"Error delivering event to {subscriber_id}: {str(e)}")
            
            # Save subscription updates
            if delivered_count > 0:
                self._save_subscriptions()
            
            return delivered_count
    
    def dispatch_batch(self, events: List[AIEvent], subscriber_id: str) -> int:
        """
        Dispatch a batch of events to a specific subscriber
        
        Args:
            events: The events to dispatch
            subscriber_id: The subscriber to dispatch to
            
        Returns:
            Number of events successfully dispatched
        """
        with self.lock:
            subscription = self.get_subscription(subscriber_id)
            if not subscription or not subscription.is_active:
                return 0
            
            # Filter events based on subscription filter
            matching_events = [event for event in events if subscription.filter.matches(event)]
            if not matching_events:
                return 0
            
            # Get appropriate delivery provider
            provider = self.delivery_providers.get(subscription.subscriber_type)
            if not provider:
                logger.warning(f"No delivery provider for {subscription.subscriber_type}")
                return 0
            
            # Attempt batch delivery
            try:
                if provider.send_batch(matching_events, subscription):
                    # Mark all as delivered
                    for event in matching_events:
                        self.event_pool.mark_delivered(event.event_id, subscriber_id)
                    
                    subscription.last_delivery = datetime.now().isoformat()
                    self._save_subscriptions()
                    
                    logger.info(f"Delivered batch of {len(matching_events)} events to {subscriber_id}")
                    return len(matching_events)
                else:
                    logger.warning(f"Failed to deliver batch to {subscriber_id}")
                    return 0
            except Exception as e:
                logger.error(f"Error delivering batch to {subscriber_id}: {str(e)}")
                return 0
    
    def _delivery_loop(self):
        """Background thread that processes event deliveries"""
        while self.running:
            try:
                # Deliver any pending events
                delivered_total = 0
                
                # Process each active subscription
                for subscriber_id, subscription in self.subscriptions.items():
                    if not subscription.is_active:
                        continue
                    
                    # Get undelivered events for this subscriber
                    undelivered = self.event_pool.get_undelivered_events(subscriber_id, limit=20)
                    if not undelivered:
                        continue
                    
                    # Filter events based on subscription
                    matching_events = [event for event in undelivered if subscription.filter.matches(event)]
                    if not matching_events:
                        continue
                    
                    # Attempt batch delivery for efficiency
                    delivered = self.dispatch_batch(matching_events, subscriber_id)
                    delivered_total += delivered
                
                if delivered_total > 0:
                    logger.info(f"Delivered {delivered_total} events in background loop")
            except Exception as e:
                logger.error(f"Error in delivery loop: {str(e)}")
            
            # Sleep between delivery cycles (10 seconds)
            time.sleep(10)
    
    def stop(self):
        """Stop the dispatcher and its background threads"""
        self.running = False
        if self.delivery_thread.is_alive():
            self.delivery_thread.join(timeout=1.0)
        logger.info("AI Intelligence Dispatcher stopped")

    def create_user_subscription(
        self,
        user_id: str,
        name: str,
        symbols: List[str] = None,
        categories: List[EventCategory] = None,
        min_priority: EventPriority = EventPriority.MEDIUM,
        destination: Dict[str, Any] = None
    ) -> str:
        """
        Create a subscription for a user
        
        Args:
            user_id: User identifier
            name: Subscription name
            symbols: Symbols to subscribe to (None = all)
            categories: Event categories to include (None = all)
            min_priority: Minimum event priority
            destination: Delivery destination details
            
        Returns:
            Subscriber ID
        """
        subscriber_id = f"user_{user_id}"
        
        # Create filter
        filter = SubscriptionFilter(
            categories=categories,
            symbols=symbols,
            min_priority=min_priority
        )
        
        # Create default destination if none provided
        if not destination:
            destination = {
                "chat_id": user_id,
                "format": "default"
            }
        
        # Create subscription
        subscription = Subscription(
            subscriber_id=subscriber_id,
            subscriber_type=SubscriberType.USER,
            name=name,
            filter=filter,
            destination=destination
        )
        
        # Add to dispatcher
        self.add_subscription(subscription)
        
        return subscriber_id
    
    def create_channel_subscription(
        self,
        channel_id: str,
        name: str,
        symbols: List[str] = None,
        categories: List[EventCategory] = None,
        min_priority: EventPriority = EventPriority.HIGH,
        platform: str = "telegram",
        destination: Dict[str, Any] = None
    ) -> str:
        """
        Create a subscription for a channel
        
        Args:
            channel_id: Channel identifier
            name: Subscription name
            symbols: Symbols to subscribe to (None = all)
            categories: Event categories to include (None = all)
            min_priority: Minimum event priority
            platform: Platform (telegram, discord)
            destination: Delivery destination details
            
        Returns:
            Subscriber ID
        """
        subscriber_id = f"{platform}_channel_{channel_id}"
        
        # Create filter
        filter = SubscriptionFilter(
            categories=categories,
            symbols=symbols,
            min_priority=min_priority
        )
        
        # Create default destination if none provided
        if not destination:
            destination = {
                "channel_id": channel_id,
                "platform": platform,
                "format": "rich"
            }
        
        # Create subscription
        subscription = Subscription(
            subscriber_id=subscriber_id,
            subscriber_type=SubscriberType.CHANNEL,
            name=name,
            filter=filter,
            destination=destination
        )
        
        # Add to dispatcher
        self.add_subscription(subscription)
        
        return subscriber_id

    def create_webhook_subscription(
        self,
        webhook_id: str,
        name: str,
        url: str,
        symbols: List[str] = None,
        categories: List[EventCategory] = None,
        min_priority: EventPriority = EventPriority.MEDIUM,
        headers: Dict[str, str] = None,
        secret: str = None
    ) -> str:
        """
        Create a subscription for a webhook
        
        Args:
            webhook_id: Webhook identifier
            name: Subscription name
            url: Webhook URL
            symbols: Symbols to subscribe to (None = all)
            categories: Event categories to include (None = all)
            min_priority: Minimum event priority
            headers: HTTP headers to include
            secret: Shared secret for HMAC authentication
            
        Returns:
            Subscriber ID
        """
        subscriber_id = f"webhook_{webhook_id}"
        
        # Create filter
        filter = SubscriptionFilter(
            categories=categories,
            symbols=symbols,
            min_priority=min_priority
        )
        
        # Create destination
        destination = {
            "url": url,
            "headers": headers or {},
            "secret": secret,
            "format": "json"
        }
        
        # Create subscription
        subscription = Subscription(
            subscriber_id=subscriber_id,
            subscriber_type=SubscriberType.WEBHOOK,
            name=name,
            filter=filter,
            destination=destination
        )
        
        # Add to dispatcher
        self.add_subscription(subscription)
        
        return subscriber_id

# For testing
if __name__ == "__main__":
    # Initialize with test config
    test_config = {
        "telegram": {"enabled": False},
        "discord": {"enabled": False},
        "webhooks": {"enabled": False}
    }
    
    from ai_event_pool import AIEventPool
    
    # Create event pool
    event_pool = AIEventPool(test_config)
    
    # Create dispatcher
    dispatcher = AIIntelligenceDispatcher(test_config, event_pool)
    
    # Create test subscription
    dispatcher.create_user_subscription(
        user_id="test_user",
        name="Test Subscription",
        symbols=["AAPL", "BTC-USD"],
        categories=[EventCategory.MARKET_IMBALANCE, EventCategory.WHALE_ALERT]
    )
    
    # Create test events
    event_id = event_pool.create_liquidity_event(
        symbol="AAPL",
        imbalance=0.75,
        analysis="Strong buying pressure on AAPL, likely to break resistance."
    )
    
    whale_id = event_pool.create_whale_alert(
        symbol="BTC-USD",
        side="buy",
        value=8500000,
        analysis="Major whale accumulation detected. Significant buying power entering the market."
    )
    
    # Wait for events to be processed
    print("Waiting for events to be processed...")
    time.sleep(15)
    
    # Stop dispatcher
    dispatcher.stop()
    print("Dispatcher stopped") 