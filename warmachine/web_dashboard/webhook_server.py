"""
Webhook Server

A server that receives webhook calls from external platforms like TradingView,
processes them, and converts them into AI events for the system.
"""

import os
import logging
import json
import hmac
import hashlib
import threading
import time
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable
from http.server import HTTPServer, BaseHTTPRequestHandler

# Import system components
from ai_event_pool import AIEventPool, EventCategory, EventPriority, AIEvent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class WebhookHandler(BaseHTTPRequestHandler):
    """HTTP request handler for webhooks"""
    
    def __init__(self, *args, **kwargs):
        # BaseHTTPRequestHandler initializes itself with these args
        self.server_instance = args[2]
        super().__init__(*args, **kwargs)
    
    def _send_response(self, status_code: int, message: str = ""):
        """Send an HTTP response"""
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        
        if message:
            response = {"status": "error" if status_code >= 400 else "success", "message": message}
            self.wfile.write(json.dumps(response).encode('utf-8'))
    
    def _verify_signature(self, payload: bytes, signature_header: str, secret: str) -> bool:
        """Verify the request signature"""
        if not signature_header or not secret:
            return False
        
        # Calculate expected signature
        expected_signature = hmac.new(
            secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        # Constant-time comparison to prevent timing attacks
        return hmac.compare_digest(signature_header, expected_signature)
    
    def _read_payload(self) -> bytes:
        """Read and return the request payload"""
        content_length = int(self.headers.get('Content-Length', 0))
        return self.rfile.read(content_length)
    
    def _get_source_info(self) -> Dict[str, str]:
        """Extract source information from request"""
        return {
            "ip": self.client_address[0],
            "user_agent": self.headers.get('User-Agent', 'Unknown'),
            "content_type": self.headers.get('Content-Type', 'Unknown'),
            "x_forwarded_for": self.headers.get('X-Forwarded-For', '')
        }
    
    def do_POST(self):
        """Handle POST requests"""
        try:
            # Get payload
            payload_bytes = self._read_payload()
            source_info = self._get_source_info()
            
            # Get endpoint key from path
            path = self.path.strip('/')
            
            # Process based on endpoint
            if path.startswith('webhook/'):
                # Extract the webhook key from the path
                webhook_key = path.split('/')[-1]
                handler = self.server_instance.get_webhook_handler(webhook_key)
                
                if not handler:
                    logger.warning(f"No handler registered for webhook key: {webhook_key}")
                    self._send_response(404, f"Unknown webhook key: {webhook_key}")
                    return
                
                # Check for authentication if required
                auth_secret = self.server_instance.get_webhook_secret(webhook_key)
                if auth_secret:
                    signature = self.headers.get('X-Signature')
                    if not self._verify_signature(payload_bytes, signature, auth_secret):
                        logger.warning(f"Invalid signature for webhook key: {webhook_key}")
                        self._send_response(401, "Invalid signature")
                        return
                
                # Parse payload
                try:
                    payload_json = json.loads(payload_bytes.decode('utf-8'))
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON received for webhook key: {webhook_key}")
                    self._send_response(400, "Invalid JSON payload")
                    return
                
                # Process the webhook
                try:
                    result = handler(payload_json, source_info)
                    self._send_response(200, "Webhook processed successfully")
                    logger.info(f"Processed webhook for key: {webhook_key}")
                except Exception as e:
                    logger.error(f"Error processing webhook {webhook_key}: {str(e)}")
                    self._send_response(500, f"Error processing webhook: {str(e)}")
                
            elif path == 'tradingview':
                # Special handler for TradingView alerts
                try:
                    payload_json = json.loads(payload_bytes.decode('utf-8'))
                except json.JSONDecodeError:
                    logger.warning("Invalid JSON received from TradingView")
                    self._send_response(400, "Invalid JSON payload")
                    return
                
                # Process TradingView alert
                self.server_instance.process_tradingview_alert(payload_json, source_info)
                self._send_response(200, "TradingView alert processed")
                logger.info("Processed TradingView alert")
                
            else:
                logger.warning(f"Unknown webhook path: {path}")
                self._send_response(404, "Unknown endpoint")
                
        except Exception as e:
            logger.error(f"Error handling webhook request: {str(e)}")
            self._send_response(500, f"Server error: {str(e)}")
    
    def do_GET(self):
        """Handle GET requests - just for health checks"""
        if self.path == '/health':
            self._send_response(200, "Webhook server running")
        else:
            self._send_response(404, "Not found")
    
    def log_message(self, format, *args):
        """Override to use our logger instead of stderr"""
        logger.info(f"{self.client_address[0]} - {format % args}")


class WebhookServer:
    """Webhook server for receiving external signals"""
    
    def __init__(self, config: Dict[str, Any], event_pool: AIEventPool):
        """
        Initialize webhook server
        
        Args:
            config: Configuration dictionary
            event_pool: AI event pool to add events to
        """
        self.config = config
        self.event_pool = event_pool
        self.host = config.get("host", "0.0.0.0")
        self.port = config.get("port", 8502)
        self.webhook_handlers: Dict[str, Callable] = {}
        self.webhook_secrets: Dict[str, str] = {}
        self.tradingview_symbols = config.get("tradingview_symbols", [])
        
        self.server = None
        self.server_thread = None
        self.running = False
        
        # Register default handlers
        self._register_default_handlers()
        
        logger.info(f"Webhook server initialized on {self.host}:{self.port}")
    
    def _register_default_handlers(self):
        """Register default webhook handlers"""
        # TradingView handler
        tv_key = self.config.get("tradingview_key", "tv")
        tv_secret = self.config.get("tradingview_secret", "")
        self.register_webhook_handler(tv_key, self.process_tradingview_alert, tv_secret)
    
    def register_webhook_handler(self, webhook_key: str, handler: Callable, secret: str = None):
        """
        Register a handler for a specific webhook endpoint
        
        Args:
            webhook_key: Webhook endpoint key
            handler: Function to handle webhook data
            secret: Secret for HMAC authentication (optional)
        """
        self.webhook_handlers[webhook_key] = handler
        if secret:
            self.webhook_secrets[webhook_key] = secret
        logger.info(f"Registered webhook handler for key: {webhook_key}")
    
    def get_webhook_handler(self, webhook_key: str) -> Optional[Callable]:
        """Get the handler for a webhook key"""
        return self.webhook_handlers.get(webhook_key)
    
    def get_webhook_secret(self, webhook_key: str) -> Optional[str]:
        """Get the secret for a webhook key"""
        return self.webhook_secrets.get(webhook_key)
    
    def process_tradingview_alert(self, data: Dict[str, Any], source_info: Dict[str, str] = None) -> bool:
        """
        Process a TradingView alert webhook
        
        Args:
            data: Alert data from TradingView
            source_info: Information about the request source
            
        Returns:
            True if processed successfully, False otherwise
        """
        try:
            # Extract key fields
            symbol = data.get("symbol", "").upper()
            strategy = data.get("strategy", {})
            alert_message = data.get("alert_message", "")
            close = float(data.get("close", 0))
            
            # Determine the alert type
            alert_type = strategy.get("order_action", "").lower()
            position_size = float(strategy.get("position_size", 0))
            
            # Validate symbol - if not in our monitored list, log but still process
            if symbol and self.tradingview_symbols and symbol not in self.tradingview_symbols:
                logger.warning(f"TradingView alert for non-monitored symbol: {symbol}")
            
            # Determine alert category and priority
            category = EventCategory.TECHNICAL_SIGNAL
            
            # Set priority based on position size or other factors
            priority = EventPriority.MEDIUM
            if abs(position_size) > 1.0:
                priority = EventPriority.HIGH
            if "URGENT" in alert_message.upper():
                priority = EventPriority.URGENT
            
            # Create a descriptive title
            if alert_type in ["buy", "sell"]:
                title = f"TradingView {alert_type.upper()} Signal: {symbol}"
            else:
                title = f"TradingView Alert: {symbol}"
            
            # Create event
            event_id = self.event_pool.generate_event_id()
            
            event = AIEvent(
                event_id=event_id,
                timestamp=datetime.now().isoformat(),
                category=category,
                symbol=symbol,
                title=title,
                content=alert_message,
                priority=priority,
                source="tradingview",
                metadata={
                    "alert_type": alert_type,
                    "position_size": position_size,
                    "price": close,
                    "strategy_name": strategy.get("strategy_name", ""),
                    "raw_data": data
                }
            )
            
            # Add to event pool
            self.event_pool.add_event(event)
            
            logger.info(f"Created TradingView alert event: {title}")
            return True
            
        except Exception as e:
            logger.error(f"Error processing TradingView alert: {str(e)}")
            return False
    
    def start(self):
        """Start the webhook server"""
        if self.running:
            logger.warning("Webhook server already running")
            return
        
        def run_server():
            try:
                self.server = HTTPServer((self.host, self.port), 
                                        lambda *args: WebhookHandler(*args, self))
                self.running = True
                logger.info(f"Webhook server started on {self.host}:{self.port}")
                self.server.serve_forever()
            except Exception as e:
                logger.error(f"Error in webhook server: {str(e)}")
                self.running = False
        
        self.server_thread = threading.Thread(target=run_server, daemon=True)
        self.server_thread.start()
    
    def stop(self):
        """Stop the webhook server"""
        if not self.running:
            logger.warning("Webhook server not running")
            return
        
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            self.running = False
            logger.info("Webhook server stopped")
    
    def wait_for_termination(self):
        """Wait for the server to terminate"""
        if self.server_thread and self.server_thread.is_alive():
            self.server_thread.join()


# Example usage
if __name__ == "__main__":
    # Load config for testing
    test_config = {
        "host": "0.0.0.0",
        "port": 8502,
        "tradingview_symbols": ["BTCUSD", "ETHUSD", "AAPL", "SPY"],
        "tradingview_key": "tv123",
        "tradingview_secret": "secret123"
    }
    
    # Create components
    from ai_event_pool import AIEventPool
    event_pool = AIEventPool({"storage": {"event_pool_path": "data/ai/events"}})
    
    # Start server
    server = WebhookServer(test_config, event_pool)
    server.start()
    
    print(f"Webhook server running on {test_config['host']}:{test_config['port']}")
    print("Press Ctrl+C to stop")
    
    try:
        # Keep the main thread alive
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Shutting down...")
        server.stop() 