"""
Webhook Notifier

Sends AI intelligence events to external webhook endpoints.
"""

import logging
import requests
import time
import json
import hmac
import hashlib
from typing import Dict, List, Any, Optional
from ai_event_pool import AIEvent
from datetime import datetime

logger = logging.getLogger(__name__)

class WebhookNotifier:
    """Webhook-based notification service"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize webhook notifier
        
        Args:
            config: Configuration dictionary with webhook settings
        """
        self.config = config
        self.rate_limit = config.get("rate_limit", 1.0)  # seconds between webhook calls
        self.retry_count = config.get("retry_count", 3)
        self.last_send_time = 0
        
        logger.info("Webhook notifier initialized")
    
    def _sign_payload(self, payload: str, secret: str) -> str:
        """
        Create HMAC signature for the payload
        
        Args:
            payload: JSON payload as string
            secret: Shared secret for HMAC
            
        Returns:
            Hex digest of HMAC-SHA256 signature
        """
        return hmac.new(
            secret.encode() if isinstance(secret, str) else secret,
            payload.encode(),
            hashlib.sha256
        ).hexdigest()
    
    def _format_event_payload(self, event: AIEvent, format_type: str = "json") -> Dict[str, Any]:
        """
        Format an event as a webhook payload
        
        Args:
            event: The event to format
            format_type: Payload format type
            
        Returns:
            Formatted payload dictionary
        """
        # Standard JSON format
        payload = {
            "event_id": event.event_id,
            "timestamp": event.timestamp,
            "category": event.category.value,
            "priority": event.priority.value,
            "symbol": event.symbol,
            "title": event.title,
            "content": event.content,
            "source": event.source,
            "metadata": event.metadata,
            "actions": event.actions
        }
        
        return payload
    
    def _send_webhook(self, url: str, payload: Dict[str, Any], headers: Dict[str, str] = None, secret: str = None) -> bool:
        """
        Send a payload to a webhook URL
        
        Args:
            url: Webhook URL
            payload: Data payload
            headers: HTTP headers
            secret: Shared secret for HMAC authentication
            
        Returns:
            True if successful, False otherwise
        """
        # Rate limiting
        current_time = time.time()
        time_since_last = current_time - self.last_send_time
        if time_since_last < self.rate_limit:
            time.sleep(self.rate_limit - time_since_last)
        
        # Send webhook
        try:
            # Convert payload to JSON string
            payload_str = json.dumps(payload)
            
            # Prepare headers
            request_headers = headers or {}
            request_headers["Content-Type"] = "application/json"
            
            # Add signature if secret is provided
            if secret:
                signature = self._sign_payload(payload_str, secret)
                request_headers["X-Signature"] = signature
            
            # Add provider identifier
            request_headers["User-Agent"] = "WarMachine-AI/1.0"
            
            # Make the request with retries
            for attempt in range(self.retry_count):
                try:
                    response = requests.post(url, data=payload_str, headers=request_headers, timeout=10)
                    self.last_send_time = time.time()
                    
                    if response.status_code in [200, 201, 202, 204]:
                        return True
                    
                    logger.warning(f"Webhook failed (attempt {attempt+1}/{self.retry_count}): HTTP {response.status_code}")
                    
                    # Only retry for server errors or timeouts
                    if response.status_code < 500:
                        break
                    
                    # Wait before retrying
                    time.sleep(2 ** attempt)  # Exponential backoff
                    
                except (requests.exceptions.RequestException, requests.exceptions.Timeout) as e:
                    logger.warning(f"Webhook request error (attempt {attempt+1}/{self.retry_count}): {str(e)}")
                    time.sleep(2 ** attempt)  # Exponential backoff
            
            logger.error(f"Webhook failed after {self.retry_count} attempts")
            return False
                
        except Exception as e:
            logger.error(f"Error sending webhook: {str(e)}")
            return False
    
    def send_event(self, event: AIEvent, subscription: Any) -> bool:
        """
        Send an event to a webhook
        
        Args:
            event: The event to send
            subscription: Subscription details
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get destination details
            destination = subscription.destination
            url = destination.get("url")
            headers = destination.get("headers", {})
            secret = destination.get("secret")
            format_type = destination.get("format", "json")
            
            if not url:
                logger.error(f"No URL specified for webhook subscription {subscription.subscriber_id}")
                return False
            
            # Format payload
            payload = self._format_event_payload(event, format_type)
            
            # Add subscription ID and timestamp
            payload["subscription_id"] = subscription.subscriber_id
            payload["delivery_timestamp"] = datetime.now().isoformat()
            
            # Send webhook
            return self._send_webhook(url, payload, headers, secret)
            
        except Exception as e:
            logger.error(f"Error sending event to webhook: {str(e)}")
            return False
    
    def send_batch(self, events: List[AIEvent], subscription: Any) -> bool:
        """
        Send multiple events to a webhook
        
        Args:
            events: List of events to send
            subscription: Subscription details
            
        Returns:
            True if successful, False otherwise
        """
        if not events:
            return True
        
        try:
            # Get destination details
            destination = subscription.destination
            url = destination.get("url")
            headers = destination.get("headers", {})
            secret = destination.get("secret")
            format_type = destination.get("format", "json")
            
            if not url:
                logger.error(f"No URL specified for webhook subscription {subscription.subscriber_id}")
                return False
            
            # Format each event
            event_payloads = [self._format_event_payload(event, format_type) for event in events]
            
            # Create batch payload
            batch_payload = {
                "subscription_id": subscription.subscriber_id,
                "delivery_timestamp": datetime.now().isoformat(),
                "batch_size": len(events),
                "events": event_payloads
            }
            
            # Send webhook
            return self._send_webhook(url, batch_payload, headers, secret)
            
        except Exception as e:
            logger.error(f"Error sending batch events to webhook: {str(e)}")
            return False 