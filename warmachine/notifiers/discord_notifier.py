"""
Discord Notifier

Sends AI intelligence events to Discord channels.
"""

import logging
import requests
import time
import json
from typing import Dict, List, Any, Optional
from ai_event_pool import AIEvent, EventPriority

logger = logging.getLogger(__name__)

class DiscordNotifier:
    """Discord-based notification service"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Discord notifier
        
        Args:
            config: Configuration dictionary with Discord settings
        """
        self.config = config
        self.token = config.get("token", "")
        self.admin_channel_id = config.get("admin_channel_id", "")
        self.report_channel_id = config.get("report_channel_id", "")
        self.webhook_url = config.get("webhook_url", "")
        self.rate_limit = config.get("rate_limit", 1.0)  # seconds between messages
        self.last_send_time = 0
        
        # Validate configuration
        if not self.token and not self.webhook_url:
            logger.error("Neither Discord token nor webhook URL provided")
            raise ValueError("Discord token or webhook URL is required")
        
        logger.info("Discord notifier initialized")
    
    def _create_embed(self, event: AIEvent) -> Dict[str, Any]:
        """
        Format an event as a Discord embed
        
        Args:
            event: The event to format
            
        Returns:
            Discord embed dictionary
        """
        # Set color based on priority
        colors = {
            EventPriority.CRITICAL: 0xFF0000,  # Red
            EventPriority.URGENT: 0xFF7700,    # Orange
            EventPriority.HIGH: 0xFFCC00,      # Yellow
            EventPriority.MEDIUM: 0x00CC00,    # Green
            EventPriority.LOW: 0x0099FF,       # Blue
        }
        color = colors.get(event.priority, 0x808080)  # Default gray
        
        # Create embed
        embed = {
            "title": event.title,
            "description": event.content,
            "color": color,
            "timestamp": event.timestamp,
            "footer": {
                "text": f"Category: {event.category.value} | Priority: {event.priority.name}"
            },
            "fields": [
                {
                    "name": "Symbol",
                    "value": event.symbol,
                    "inline": True
                }
            ]
        }
        
        # Add metadata fields
        if event.metadata:
            for key, value in event.metadata.items():
                if key in ["imbalance_value", "trade_value", "trade_side", "direction", "exchange"]:
                    embed["fields"].append({
                        "name": key.replace("_", " ").title(),
                        "value": str(value),
                        "inline": True
                    })
        
        # Add actions if available
        if event.actions:
            actions_text = ""
            for i, action in enumerate(event.actions, 1):
                actions_text += f"{i}. {action.get('description', '')}\n"
            
            if actions_text:
                embed["fields"].append({
                    "name": "Recommended Actions",
                    "value": actions_text,
                    "inline": False
                })
        
        return embed
    
    def _send_webhook_message(self, webhook_url: str, content: str = "", embeds: List[Dict[str, Any]] = None, username: str = None) -> bool:
        """
        Send a message via Discord webhook
        
        Args:
            webhook_url: Discord webhook URL
            content: Text content
            embeds: List of embeds
            username: Override username
            
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
            data = {
                "content": content
            }
            
            if embeds:
                data["embeds"] = embeds
            
            if username:
                data["username"] = username
            
            headers = {
                "Content-Type": "application/json"
            }
            
            response = requests.post(webhook_url, data=json.dumps(data), headers=headers)
            self.last_send_time = time.time()
            
            if response.status_code in [200, 201, 204]:
                return True
            else:
                logger.error(f"Discord API error: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending Discord webhook message: {str(e)}")
            return False
    
    def _get_webhook_url(self, destination: Dict[str, Any]) -> str:
        """Get webhook URL from destination or config"""
        # First check if destination has a channel-specific webhook
        if "webhook_url" in destination:
            return destination["webhook_url"]
        
        # Next check if destination specifies a channel ID that has a predefined webhook
        channel_id = destination.get("channel_id")
        if channel_id:
            if channel_id == self.admin_channel_id and "admin_webhook_url" in self.config:
                return self.config["admin_webhook_url"]
            if channel_id == self.report_channel_id and "report_webhook_url" in self.config:
                return self.config["report_webhook_url"]
        
        # Fall back to default webhook
        return self.webhook_url
    
    def send_event(self, event: AIEvent, subscription: Any) -> bool:
        """
        Send an event to Discord
        
        Args:
            event: The event to send
            subscription: Subscription details
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get destination details
            destination = subscription.destination
            webhook_url = self._get_webhook_url(destination)
            
            if not webhook_url:
                logger.error(f"No webhook URL available for {subscription.subscriber_id}")
                return False
            
            # Create embed
            embed = self._create_embed(event)
            
            # Get custom username if specified
            username = destination.get("username", "WarMachine AI")
            
            # Send message with embed
            return self._send_webhook_message(
                webhook_url=webhook_url,
                content="",  # No content, just the embed
                embeds=[embed],
                username=username
            )
            
        except Exception as e:
            logger.error(f"Error sending event to Discord: {str(e)}")
            return False
    
    def send_batch(self, events: List[AIEvent], subscription: Any) -> bool:
        """
        Send multiple events to Discord
        
        Args:
            events: List of events to send
            subscription: Subscription details
            
        Returns:
            True if all events sent successfully, False otherwise
        """
        if not events:
            return True
        
        try:
            # Get destination details
            destination = subscription.destination
            webhook_url = self._get_webhook_url(destination)
            
            if not webhook_url:
                logger.error(f"No webhook URL available for {subscription.subscriber_id}")
                return False
            
            username = destination.get("username", "WarMachine AI")
            
            # For batches of 5 or fewer events, send them as a group of embeds
            if len(events) <= 5:
                embeds = [self._create_embed(event) for event in events]
                return self._send_webhook_message(
                    webhook_url=webhook_url,
                    content="📊 **Market Intelligence Update**",
                    embeds=embeds,
                    username=username
                )
            
            # For larger batches, send a summary and the most important events
            high_priority_count = len([e for e in events if e.priority.value >= EventPriority.HIGH.value])
            
            # Create summary content
            content = (
                f"📊 **Market Intelligence Update**\n\n"
                f"You have {len(events)} new market intelligence notifications"
                f"{f' ({high_priority_count} high priority)' if high_priority_count > 0 else ''}."
            )
            
            # Create embeds for top 5 events by priority
            sorted_events = sorted(events, key=lambda e: (e.priority.value, e.timestamp), reverse=True)
            embeds = [self._create_embed(event) for event in sorted_events[:5]]
            
            # Send message
            return self._send_webhook_message(
                webhook_url=webhook_url,
                content=content,
                embeds=embeds,
                username=username
            )
            
        except Exception as e:
            logger.error(f"Error sending batch events to Discord: {str(e)}")
            return False 