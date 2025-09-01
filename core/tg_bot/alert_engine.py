"""
Alert Engine for managing trading alerts
"""

import logging
import time
from typing import Dict, Any, List, Optional, Set, Deque
from datetime import datetime, timedelta
from collections import defaultdict, deque
from ai_event_pool import AIEvent, EventCategory, EventPriority
import asyncio
from .api import TelegramAPI
from .alert_templates import AlertTemplateManager
from .alert_subscription import AlertSubscriptionManager
from .alert_feedback import AlertFeedbackManager
from .alert_priority import PriorityManager

logger = logging.getLogger(__name__)

class NotificationPriority:
    """Notification priority levels"""
    CRITICAL = 0
    HIGH = 1
    MEDIUM = 2
    LOW = 3
    INFO = 4

class AlertEngine:
    """Engine for managing and processing trading alerts"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize the alert engine
        
        Args:
            config: Configuration dictionary
        """
        self.config = config or {}
        self.alerts = {
            "price": {},  # symbol -> {threshold: float, direction: str, chat_id: str}
            "volume": {},  # symbol -> {threshold: float, chat_id: str}
            "risk": {}  # strategy -> {threshold: float, chat_id: str}
        }
        
        # Initialize Telegram API
        self.telegram_token = self.config.get("telegram", {}).get("token")
        if not self.telegram_token:
            logger.warning("No Telegram token provided, notifications will be logged only")
            self.telegram_api = None
        else:
            logger.info("Initializing Telegram API with token")
            self.telegram_api = TelegramAPI(self.telegram_token, self.config.get("telegram", {}))
        
        # Initialize template manager
        self.template_manager = AlertTemplateManager()
        
        # Initialize subscription manager
        self.subscription_manager = AlertSubscriptionManager()
        
        # Initialize feedback manager
        self.feedback_manager = AlertFeedbackManager()
        
        # Initialize priority manager
        self.priority_manager = PriorityManager()
        
        # Load default priority rules
        self._load_default_rules()
        
        # Notification settings
        self.rate_limit = self.config.get("rate_limit", 1.0)  # seconds between messages
        self.last_send_time = 0
        self.max_notifications_per_minute = self.config.get("max_notifications_per_minute", 60)
        self.notification_counts = defaultdict(int)
        self.notification_reset_time = time.time()
        
        # Cooldown periods for different priority levels
        self.cooldown_periods = self.config.get("cooldown_periods", {
            "CRITICAL": 60,  # seconds
            "HIGH": 300,
            "MEDIUM": 900,
            "LOW": 1800,
            "INFO": 3600
        })
        self.last_notification_time = {}
        
        # Alert history with improved tracking
        self.alert_history: Deque[Dict[str, Any]] = deque(maxlen=1000)
        
        # Performance metrics
        self.metrics = {
            "total_notifications": 0,
            "notifications_by_priority": defaultdict(int),
            "notifications_by_type": defaultdict(int),
            "delivery_times": [],
            "errors": defaultdict(int),
            "feedback": {
                "total": 0,
                "by_type": {}
            },
            "priority_adjustments": {
                "total": 0,
                "by_rule": {}
            }
        }
        
        logger.info("Alert Engine initialized with enhanced notification capabilities")
    
    def _load_default_rules(self) -> None:
        """Load default priority rules"""
        # High volume rule
        self.priority_manager.add_rule(
            name="high_volume",
            condition="volume > 1000",
            adjustment=1,
            cooldown=300
        )
        
        # Price change rule
        self.priority_manager.add_rule(
            name="price_change",
            condition="price_change > 0.05",
            adjustment=1,
            cooldown=300
        )
        
        # Risk level rule
        self.priority_manager.add_rule(
            name="high_risk",
            condition="risk_level > 0.8",
            adjustment=2,
            cooldown=60
        )
        
        # Strategy confidence rule
        self.priority_manager.add_rule(
            name="high_confidence",
            condition="confidence > 0.9",
            adjustment=1,
            cooldown=300
        )
        
        logger.info("Loaded default priority rules")
    
    def _get_priority_emoji(self, priority: EventPriority) -> str:
        """Get emoji for priority level"""
        if priority == EventPriority.CRITICAL:
            return "🔴"
        elif priority == EventPriority.URGENT:
            return "🟠"
        elif priority == EventPriority.HIGH:
            return "🟡"
        elif priority == EventPriority.MEDIUM:
            return "🟢"
        else:
            return "🔵"
    
    def _format_alert_message(self, event: AIEvent, format_type: str = "default") -> str:
        """
        Format an alert message
        
        Args:
            event: The event to format
            format_type: Message format type (default, compact, markdown)
            
        Returns:
            Formatted message string
        """
        priority_emoji = self._get_priority_emoji(event.priority)
        
        if format_type == "compact":
            return (
                f"{priority_emoji} *{event.title}*\n"
                f"_{event.symbol} | {event.category.value}_\n\n"
                f"{event.content[:200]}{'...' if len(event.content) > 200 else ''}"
            )
        
        elif format_type == "markdown":
            message = (
                f"{priority_emoji} *{event.title}*\n\n"
                f"*Symbol:* `{event.symbol}`\n"
                f"*Category:* `{event.category.value}`\n"
                f"*Priority:* `{event.priority.name}`\n"
                f"*Time:* `{event.timestamp}`\n\n"
                f"*Analysis:*\n{event.content}\n\n"
            )
            
            if event.metadata:
                message += "*Details:*\n"
                for key, value in event.metadata.items():
                    if key in ["imbalance_value", "trade_value", "trade_side", "direction"]:
                        message += f"• `{key}`: `{value}`\n"
                message += "\n"
            
            if event.actions:
                message += "*Recommended Actions:*\n"
                for i, action in enumerate(event.actions, 1):
                    message += f"{i}. {action.get('description', '')}\n"
            
            return message
        
        else:  # default format
            return (
                f"{priority_emoji} *{event.title}*\n\n"
                f"*Symbol:* {event.symbol}\n"
                f"*Category:* {event.category.value}\n\n"
                f"{event.content}\n"
            )
    
    def _should_send_notification(self, event: AIEvent, chat_id: str) -> bool:
        """
        Check if notification should be sent based on rate limits and cooldowns
        
        Args:
            event: The event to check
            chat_id: Target chat ID
            
        Returns:
            True if notification should be sent
        """
        current_time = time.time()
        
        # Check rate limit
        time_since_last = current_time - self.last_send_time
        if time_since_last < self.rate_limit:
            return False
        
        # Check notifications per minute limit
        if current_time - self.notification_reset_time >= 60:
            self.notification_counts.clear()
            self.notification_reset_time = current_time
        
        if self.notification_counts[chat_id] >= self.max_notifications_per_minute:
            return False
        
        # Check cooldown period
        cooldown_key = f"{chat_id}:{event.symbol}:{event.category.value}"
        last_time = self.last_notification_time.get(cooldown_key, 0)
        cooldown = self.cooldown_periods.get(event.priority.name, 3600)
        
        if current_time - last_time < cooldown:
            return False
        
        return True
    
    async def process_event(self, event: AIEvent) -> bool:
        """
        Process an AI event and trigger appropriate alerts
        
        Args:
            event: The AI event to process
            
        Returns:
            True if alert was triggered, False otherwise
        """
        try:
            start_time = time.time()
            
            # Adjust priority based on rules
            original_priority = event.priority
            event.priority = self.priority_manager.adjust_priority(event)
            
            # Update statistics if priority was adjusted
            if event.priority != original_priority:
                self.metrics["priority_adjustments"]["total"] += 1
                for rule in self.priority_manager.rules:
                    if rule.evaluate(event):
                        self.metrics["priority_adjustments"]["by_rule"][rule.name] = (
                            self.metrics["priority_adjustments"]["by_rule"].get(rule.name, 0) + 1
                        )
            
            if event.category == EventCategory.MARKET_ALERT:
                await self._handle_market_alert(event)
            elif event.category == EventCategory.RISK_ALERT:
                await self._handle_risk_alert(event)
            elif event.category == EventCategory.TRADE_SIGNAL:
                await self._handle_trade_signal(event)
            
            # Update metrics
            self.metrics["total_notifications"] += 1
            self.metrics["notifications_by_priority"][event.priority.name] += 1
            self.metrics["notifications_by_type"][event.category.value] += 1
            self.metrics["delivery_times"].append(time.time() - start_time)
            
            # Add to history with enhanced tracking
            self.alert_history.append({
                "timestamp": datetime.now().isoformat(),
                "event": event,
                "processed": True,
                "delivery_time": time.time() - start_time,
                "original_priority": original_priority.name
            })
            
            # Trim history if needed
            if len(self.alert_history) > self.alert_history.maxlen:
                self.alert_history.pop()
            
            return True
            
        except Exception as e:
            logger.error(f"Error processing event: {str(e)}")
            self.metrics["errors"]["process_event"] += 1
            return False
    
    async def _handle_market_alert(self, event: AIEvent):
        """Handle market-related alerts"""
        symbol = event.symbol
        metadata = event.metadata
        
        # Check price alerts
        if symbol in self.alerts["price"]:
            for alert in self.alerts["price"][symbol]:
                if self._check_price_alert(symbol, alert, metadata):
                    await self._trigger_alert(event, alert["chat_id"])
        
        # Check volume alerts
        if symbol in self.alerts["volume"]:
            for alert in self.alerts["volume"][symbol]:
                if self._check_volume_alert(symbol, alert, metadata):
                    await self._trigger_alert(event, alert["chat_id"])
    
    async def _handle_risk_alert(self, event: AIEvent):
        """Handle risk-related alerts"""
        strategy = event.metadata.get("strategy", "default")
        
        if strategy in self.alerts["risk"]:
            for alert in self.alerts["risk"][strategy]:
                if self._check_risk_alert(strategy, alert, event.metadata):
                    await self._trigger_alert(event, alert["chat_id"])
    
    async def _handle_trade_signal(self, event: AIEvent):
        """Handle trade signal alerts"""
        # Trade signals are always important, so we'll notify all relevant users
        for alert_type in self.alerts.values():
            for symbol_alerts in alert_type.values():
                for alert in symbol_alerts:
                    if event.symbol in alert.get("symbols", [event.symbol]):
                        await self._trigger_alert(event, alert["chat_id"])
    
    def _check_price_alert(self, symbol: str, alert: Dict[str, Any], 
                          metadata: Dict[str, Any]) -> bool:
        """Check if price alert conditions are met"""
        current_price = metadata.get("price", 0)
        threshold = alert["threshold"]
        direction = alert["direction"]
        
        if direction == "above" and current_price > threshold:
            return True
        elif direction == "below" and current_price < threshold:
            return True
        return False
    
    def _check_volume_alert(self, symbol: str, alert: Dict[str, Any],
                           metadata: Dict[str, Any]) -> bool:
        """Check if volume alert conditions are met"""
        current_volume = metadata.get("volume", 0)
        threshold = alert["threshold"]
        
        return current_volume > threshold
    
    def _check_risk_alert(self, strategy: str, alert: Dict[str, Any],
                         metadata: Dict[str, Any]) -> bool:
        """Check if risk alert conditions are met"""
        risk_level = metadata.get("risk_level", 0)
        threshold = alert["threshold"]
        
        return risk_level > threshold
    
    async def _trigger_alert(self, event: AIEvent, chat_id: str):
        """
        Trigger an alert to a specific chat
        
        Args:
            event: The event to send
            chat_id: Target chat ID
        """
        try:
            if not self._should_send_notification(event, chat_id):
                logger.debug(f"Skipping notification due to rate limit or cooldown: {event.title}")
                return
            
            # Format message
            message = self._format_alert_message(event, "markdown")
            
            # TODO: Implement actual alert sending using Telegram API
            # For now, just log it
            logger.info(f"Alert triggered for {event.symbol}: {event.title}")
            
            # Update tracking
            self.last_send_time = time.time()
            self.notification_counts[chat_id] += 1
            cooldown_key = f"{chat_id}:{event.symbol}:{event.category.value}"
            self.last_notification_time[cooldown_key] = time.time()
            
        except Exception as e:
            logger.error(f"Error triggering alert: {str(e)}")
            self.metrics["errors"]["trigger_alert"] += 1
    
    async def add_price_alert(self, symbol: str, threshold: float,
                            direction: str, chat_id: str) -> bool:
        """
        Add a price alert
        
        Args:
            symbol: Symbol to monitor
            threshold: Price threshold
            direction: "above" or "below"
            chat_id: Chat ID to notify
            
        Returns:
            True if alert was added successfully
        """
        try:
            if symbol not in self.alerts["price"]:
                self.alerts["price"][symbol] = []
            
            self.alerts["price"][symbol].append({
                "threshold": threshold,
                "direction": direction,
                "chat_id": chat_id,
                "created_at": datetime.now().isoformat()
            })
            
            return True
            
        except Exception as e:
            logger.error(f"Error adding price alert: {str(e)}")
            return False
    
    async def add_volume_alert(self, symbol: str, threshold: float,
                             chat_id: str) -> bool:
        """
        Add a volume alert
        
        Args:
            symbol: Symbol to monitor
            threshold: Volume threshold
            chat_id: Chat ID to notify
            
        Returns:
            True if alert was added successfully
        """
        try:
            if symbol not in self.alerts["volume"]:
                self.alerts["volume"][symbol] = []
            
            self.alerts["volume"][symbol].append({
                "threshold": threshold,
                "chat_id": chat_id,
                "created_at": datetime.now().isoformat()
            })
            
            return True
            
        except Exception as e:
            logger.error(f"Error adding volume alert: {str(e)}")
            return False
    
    async def add_risk_alert(self, strategy: str, threshold: float,
                           chat_id: str) -> bool:
        """
        Add a risk alert
        
        Args:
            strategy: Strategy to monitor
            threshold: Risk threshold
            chat_id: Chat ID to notify
            
        Returns:
            True if alert was added successfully
        """
        try:
            if strategy not in self.alerts["risk"]:
                self.alerts["risk"][strategy] = []
            
            self.alerts["risk"][strategy].append({
                "threshold": threshold,
                "chat_id": chat_id,
                "created_at": datetime.now().isoformat()
            })
            
            return True
            
        except Exception as e:
            logger.error(f"Error adding risk alert: {str(e)}")
            return False
    
    async def list_alerts(self) -> str:
        """List all active alerts"""
        response = "Active Alerts:\n\n"
        
        # Price alerts
        response += "*Price Alerts:*\n"
        for symbol, alerts in self.alerts["price"].items():
            for alert in alerts:
                response += (
                    f"- {symbol}: {alert['direction']} {alert['threshold']}\n"
                    f"  Created: {alert['created_at']}\n"
                )
        
        # Volume alerts
        response += "\n*Volume Alerts:*\n"
        for symbol, alerts in self.alerts["volume"].items():
            for alert in alerts:
                response += (
                    f"- {symbol}: > {alert['threshold']}\n"
                    f"  Created: {alert['created_at']}\n"
                )
        
        # Risk alerts
        response += "\n*Risk Alerts:*\n"
        for strategy, alerts in self.alerts["risk"].items():
            for alert in alerts:
                response += (
                    f"- {strategy}: > {alert['threshold']}\n"
                    f"  Created: {alert['created_at']}\n"
                )
        
        return response
    
    async def send_batch_notifications(self, events: List[AIEvent], chat_id: str) -> bool:
        """
        Send multiple events as a batch notification
        
        Args:
            events: List of events to send
            chat_id: Target chat ID
            
        Returns:
            True if all notifications sent successfully
        """
        if not events:
            return True
            
        try:
            # For small batches, send individually
            if len(events) <= 3:
                all_success = True
                for event in events:
                    success = await self._trigger_alert(event, chat_id)
                    if not success:
                        all_success = False
                return all_success
            
            # For larger batches, send a summary and the most important events
            summary = (
                f"*🔔 New Intelligence Update*\n\n"
                f"You have {len(events)} new market intelligence notifications:\n"
            )
            
            # Group events by category
            categories = defaultdict(list)
            for event in events:
                categories[event.category.value].append(event)
            
            # Add category summaries
            for category, cat_events in categories.items():
                summary += f"\n• {category}: {len(cat_events)} events"
            
            # Send summary
            await self._send_telegram_message(chat_id, summary)
            
            # Send the 3 highest priority events
            sorted_events = sorted(events, key=lambda e: (e.priority.value, e.timestamp), reverse=True)
            for event in sorted_events[:3]:
                await self._trigger_alert(event, chat_id)
            
            return True
            
        except Exception as e:
            logger.error(f"Error sending batch notifications: {str(e)}")
            self.metrics["errors"]["batch_notification"] += 1
            return False
    
    async def _send_telegram_message(self, chat_id: str, message: str, parse_mode: str = "Markdown") -> bool:
        """
        Send a message to Telegram
        
        Args:
            chat_id: Telegram chat ID
            message: Message text
            parse_mode: Message format (Markdown, HTML)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.telegram_api:
                logger.info(f"[MOCK] Sending message to {chat_id}: {message[:100]}...")
                return True
            
            # Rate limiting
            current_time = time.time()
            time_since_last = current_time - self.last_send_time
            if time_since_last < self.rate_limit:
                await asyncio.sleep(self.rate_limit - time_since_last)
            
            # Ensure message isn't too long
            if len(message) > 4096:
                message = message[:4093] + "..."
            
            # Send message via Telegram API
            success = await self.telegram_api.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode=parse_mode,
                disable_web_page_preview=True
            )
            
            if success:
                self.last_send_time = time.time()
                return True
            else:
                logger.error(f"Failed to send message to {chat_id}")
                self.metrics["errors"]["send_message"] += 1
                return False
            
        except Exception as e:
            logger.error(f"Error sending Telegram message: {str(e)}")
            self.metrics["errors"]["send_message"] += 1
            return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get notification statistics
        
        Returns:
            Dictionary containing statistics
        """
        stats = {
            "total_notifications": self.metrics["total_notifications"],
            "notifications_by_priority": dict(self.metrics["notifications_by_priority"]),
            "notifications_by_type": dict(self.metrics["notifications_by_type"]),
            "error_counts": dict(self.metrics["errors"]),
            "active_alerts": {
                "price": sum(len(alerts) for alerts in self.alerts["price"].values()),
                "volume": sum(len(alerts) for alerts in self.alerts["volume"].values()),
                "risk": sum(len(alerts) for alerts in self.alerts["risk"].values())
            },
            "feedback": dict(self.metrics["feedback"]),
            "priority_adjustments": dict(self.metrics["priority_adjustments"]),
            "rate_limit": self.rate_limit,
            "cooldown_periods": {k: v for k, v in self.cooldown_periods.items()},
            "subscription_count": len(self.subscription_manager.subscriptions)
        }
        
        # Calculate average delivery time
        if self.metrics["delivery_times"]:
            stats["average_delivery_time"] = sum(self.metrics["delivery_times"]) / len(self.metrics["delivery_times"])
        
        return stats
    
    def get_alert_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent alert history
        
        Args:
            limit: Maximum number of alerts to return
            
        Returns:
            List of recent alerts
        """
        return list(self.alert_history)[-limit:]
    
    def clear_alert_history(self):
        """Clear alert history"""
        self.alert_history.clear()
        logger.info("Alert history cleared")
    
    def reset_statistics(self):
        """Reset all statistics"""
        self.metrics = {
            "total_notifications": 0,
            "notifications_by_priority": defaultdict(int),
            "notifications_by_type": defaultdict(int),
            "delivery_times": [],
            "errors": defaultdict(int),
            "feedback": {
                "total": 0,
                "by_type": {}
            },
            "priority_adjustments": {
                "total": 0,
                "by_rule": {}
            }
        }
        logger.info("Statistics reset")
    
    async def remove_alert(self, alert_type: str, identifier: str, chat_id: str) -> bool:
        """
        Remove an alert
        
        Args:
            alert_type: Type of alert (price, volume, risk)
            identifier: Symbol or strategy name
            chat_id: Chat ID that created the alert
            
        Returns:
            True if alert was removed successfully
        """
        try:
            if alert_type not in self.alerts:
                logger.error(f"Invalid alert type: {alert_type}")
                return False
            
            if identifier not in self.alerts[alert_type]:
                logger.error(f"No alerts found for {identifier}")
                return False
            
            # Find and remove alerts for this chat_id
            alerts = self.alerts[alert_type][identifier]
            original_count = len(alerts)
            self.alerts[alert_type][identifier] = [
                alert for alert in alerts if alert["chat_id"] != chat_id
            ]
            
            # Remove empty lists
            if not self.alerts[alert_type][identifier]:
                del self.alerts[alert_type][identifier]
            
            removed_count = original_count - len(self.alerts[alert_type].get(identifier, []))
            logger.info(f"Removed {removed_count} alerts for {identifier}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error removing alert: {str(e)}")
            return False
    
    def add_subscription(self, user_id: str, chat_id: str) -> Any:
        """
        Add a new subscription
        
        Args:
            user_id: Telegram user ID
            chat_id: Telegram chat ID
            
        Returns:
            New subscription object
        """
        return self.subscription_manager.add_subscription(user_id, chat_id)
    
    def remove_subscription(self, user_id: str) -> bool:
        """
        Remove a subscription
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            True if subscription was removed successfully
        """
        return self.subscription_manager.remove_subscription(user_id)
    
    def update_subscription(self, user_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update subscription settings
        
        Args:
            user_id: Telegram user ID
            updates: Dictionary of settings to update
            
        Returns:
            True if subscription was updated successfully
        """
        return self.subscription_manager.update_subscription(user_id, updates)
    
    def list_subscriptions(self) -> List[Dict[str, Any]]:
        """
        List all subscriptions
        
        Returns:
            List of subscription information dictionaries
        """
        return self.subscription_manager.list_subscriptions()
    
    def process_feedback(self, event_id: str, user_id: str, feedback_type: str, comment: Optional[str] = None) -> bool:
        """
        Handle feedback for an event
        
        Args:
            event_id: ID of the event
            user_id: Telegram user ID
            feedback_type: Type of feedback
            comment: Optional comment
            
        Returns:
            True if feedback was handled successfully
        """
        try:
            # Add feedback
            feedback = self.feedback_manager.add_feedback(event_id, user_id, feedback_type, comment)
            
            # Update statistics
            self.metrics["feedback"]["total"] += 1
            self.metrics["feedback"]["by_type"][feedback_type] = (
                self.metrics["feedback"]["by_type"].get(feedback_type, 0) + 1
            )
            
            # Get feedback summary
            summary = self.feedback_manager.get_feedback_summary(event_id)
            
            # Notify subscribers about feedback
            subscribers = self.subscription_manager.list_subscriptions()
            for sub in subscribers:
                if sub["user_id"] != user_id:  # Don't notify the user who gave feedback
                    message = (
                        f"Feedback received for event {event_id}:\n"
                        f"Type: {feedback_type}\n"
                        f"Total feedback: {summary['total']}\n"
                    )
                    if comment:
                        message += f"Comment: {comment}\n"
                    
                    self._send_telegram_message(
                        sub["chat_id"],
                        message,
                        sub["enable_web_preview"]
                    )
            
            return True
            
        except Exception as e:
            logger.error(f"Error handling feedback for event {event_id}: {str(e)}")
            return False
    
    def get_feedback_summary(self, event_id: str) -> Dict[str, Any]:
        """
        Get feedback summary for an event
        
        Args:
            event_id: ID of the event
            
        Returns:
            Dictionary with feedback summary
        """
        return self.feedback_manager.get_feedback_summary(event_id)
    
    def clear_feedback(self, event_id: str) -> bool:
        """
        Clear feedback for an event
        
        Args:
            event_id: ID of the event
            
        Returns:
            True if feedback was cleared successfully
        """
        return self.feedback_manager.clear_event_feedback(event_id)
    
    def clear_user_feedback(self, user_id: str) -> bool:
        """
        Clear feedback from a user
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            True if feedback was cleared successfully
        """
        return self.feedback_manager.clear_user_feedback(user_id)
    
    def add_priority_rule(self, name: str, condition: str, adjustment: int, cooldown: int = 0) -> Any:
        """
        Add a priority rule
        
        Args:
            name: Rule name
            condition: Condition string
            adjustment: Priority adjustment
            cooldown: Cooldown period in seconds
            
        Returns:
            New rule object
        """
        return self.priority_manager.add_rule(name, condition, adjustment, cooldown)
    
    def remove_priority_rule(self, name: str) -> bool:
        """
        Remove a priority rule
        
        Args:
            name: Rule name
            
        Returns:
            True if rule was removed successfully
        """
        return self.priority_manager.remove_rule(name)
    
    def list_priority_rules(self) -> List[Dict[str, Any]]:
        """
        List all priority rules
        
        Returns:
            List of rule information dictionaries
        """
        return self.priority_manager.list_rules()
    
    def get_priority_history(self, event_id: str) -> List[Dict[str, Any]]:
        """
        Get priority adjustment history for an event
        
        Args:
            event_id: ID of the event
            
        Returns:
            List of adjustment records
        """
        return self.priority_manager.get_adjustment_history(event_id)
    
    def clear_priority_history(self, event_id: Optional[str] = None) -> None:
        """
        Clear priority adjustment history
        
        Args:
            event_id: Optional event ID to clear history for
        """
        self.priority_manager.clear_history(event_id) 