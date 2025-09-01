"""
Telegram Notifier

Sends AI intelligence events to Telegram users and channels.
"""

import logging
import requests
import time
from typing import Dict, List, Any, Optional
from ai_event_pool import AIEvent, EventPriority

logger = logging.getLogger(__name__)

class TelegramNotifier:
    """Telegram-based notification service"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Telegram notifier
        
        Args:
            config: Configuration dictionary with Telegram settings
        """
        self.config = config
        self.token = config.get("token", "")
        self.base_url = f"https://api.telegram.org/bot{self.token}"
        self.admin_chat_id = config.get("admin_chat_id", "")
        self.report_channel_id = config.get("report_channel_id", "")
        self.rate_limit = config.get("rate_limit", 1.0)  # seconds between messages
        self.last_send_time = 0
        
        # Validate configuration
        if not self.token:
            logger.error("Telegram token not provided")
            raise ValueError("Telegram token is required")
        
        logger.info("Telegram notifier initialized")
    
    def _format_event_message(self, event: AIEvent, format_type: str = "default") -> str:
        """
        Format an event as a Telegram message
        
        Args:
            event: The event to format
            format_type: Message format type (default, compact, markdown)
            
        Returns:
            Formatted message string
        """
        if format_type == "compact":
            # Compact format
            priority_emoji = self._get_priority_emoji(event.priority)
            return (
                f"{priority_emoji} *{event.title}*\n"
                f"_{event.symbol} | {event.category.value}_\n\n"
                f"{event.content[:200]}{'...' if len(event.content) > 200 else ''}"
            )
        
        elif format_type == "markdown":
            # Markdown format with details
            priority_emoji = self._get_priority_emoji(event.priority)
            
            message = (
                f"{priority_emoji} *{event.title}*\n\n"
                f"*Symbol:* `{event.symbol}`\n"
                f"*Category:* `{event.category.value}`\n"
                f"*Priority:* `{event.priority.name}`\n"
                f"*Time:* `{event.timestamp}`\n\n"
                f"*Analysis:*\n{event.content}\n\n"
            )
            
            # Add metadata if available (only important fields)
            if event.metadata:
                message += "*Details:*\n"
                for key, value in event.metadata.items():
                    if key in ["imbalance_value", "trade_value", "trade_side", "direction"]:
                        message += f"• `{key}`: `{value}`\n"
                message += "\n"
            
            # Add actions if available
            if event.actions:
                message += "*Recommended Actions:*\n"
                for i, action in enumerate(event.actions, 1):
                    message += f"{i}. {action.get('description', '')}\n"
            
            return message
        
        else:
            # Default format
            priority_emoji = self._get_priority_emoji(event.priority)
            
            message = (
                f"{priority_emoji} *{event.title}*\n\n"
                f"*Symbol:* {event.symbol}\n"
                f"*Category:* {event.category.value}\n\n"
                f"{event.content}\n"
            )
            
            return message
    
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
    
    def _send_telegram_message(self, chat_id: str, message: str, parse_mode: str = "Markdown") -> bool:
        """
        Send a message to Telegram
        
        Args:
            chat_id: Telegram chat ID
            message: Message text
            parse_mode: Message format (Markdown, HTML)
            
        Returns:
            True if successful, False otherwise
        """
        # Rate limiting
        current_time = time.time()
        time_since_last = current_time - self.last_send_time
        if time_since_last < self.rate_limit:
            time.sleep(self.rate_limit - time_since_last)
        
        # Send message
        try:
            url = f"{self.base_url}/sendMessage"
            
            # Ensure message isn't too long
            if len(message) > 4096:
                message = message[:4093] + "..."
            
            data = {
                "chat_id": chat_id,
                "text": message,
                "parse_mode": parse_mode,
                "disable_web_page_preview": True
            }
            
            response = requests.post(url, data=data)
            self.last_send_time = time.time()
            
            if response.status_code == 200:
                return True
            else:
                logger.error(f"Telegram API error: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending Telegram message: {str(e)}")
            return False
    
    def send_event(self, event: AIEvent, subscription: Any) -> bool:
        """
        Send an event to Telegram
        
        Args:
            event: The event to send
            subscription: Subscription details
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get destination details
            destination = subscription.destination
            chat_id = destination.get("chat_id")
            format_type = destination.get("format", "default")
            
            # Format message
            message = self._format_event_message(event, format_type)
            
            # Send message
            return self._send_telegram_message(chat_id, message)
            
        except Exception as e:
            logger.error(f"Error sending event to Telegram: {str(e)}")
            return False
    
    def send_batch(self, events: List[AIEvent], subscription: Any) -> bool:
        """
        Send multiple events to Telegram
        
        Args:
            events: List of events to send
            subscription: Subscription details
            
        Returns:
            True if all events sent successfully, False otherwise
        """
        if not events:
            return True
        
        try:
            # For batches of 3 or fewer events, send them individually
            if len(events) <= 3:
                all_success = True
                for event in events:
                    success = self.send_event(event, subscription)
                    if not success:
                        all_success = False
                return all_success
            
            # For larger batches, send a summary and the most important events
            destination = subscription.destination
            chat_id = destination.get("chat_id")
            
            # Create a summary message
            summary = (
                f"*🔔 New Intelligence Update*\n\n"
                f"You have {len(events)} new market intelligence notifications:\n"
            )
            
            # Group events by category
            categories = {}
            for event in events:
                category = event.category.value
                if category not in categories:
                    categories[category] = []
                categories[category].append(event)
            
            # Add category summaries
            for category, cat_events in categories.items():
                summary += f"\n• {category}: {len(cat_events)} events"
            
            # Send summary
            self._send_telegram_message(chat_id, summary)
            
            # Send the 3 highest priority events
            sorted_events = sorted(events, key=lambda e: (e.priority.value, e.timestamp), reverse=True)
            for event in sorted_events[:3]:
                self.send_event(event, subscription)
            
            return True
            
        except Exception as e:
            logger.error(f"Error sending batch events to Telegram: {str(e)}")
            return False 