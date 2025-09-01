"""
MCP Server Connector for Cherry Studio Integration
"""

import logging
import asyncio
import aiohttp
from typing import Dict, Any, Optional, List, Union
from datetime import datetime
from dataclasses import dataclass
import json

logger = logging.getLogger(__name__)

@dataclass
class MCPResponse:
    """Response from MCP Server"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    timestamp: datetime = datetime.now()

class MCPConnector:
    """Connector for Cherry Studio MCP Server"""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize MCP Server connector"""
        self.config = config
        self.enabled = config.get("enabled", False)
        if not self.enabled:
            logger.info("MCP Server connector disabled")
            return
            
        # Get server configuration
        self.host = config.get("host", "cherry-studio.com")
        self.port = config.get("port", 443)
        self.api_key = config.get("api_key", "")
        self.use_ssl = config.get("use_ssl", True)
        
        # Build base URL with proper protocol
        protocol = "https" if self.use_ssl else "http"
        self.base_url = f"{protocol}://{self.host}:{self.port}"
        
        # Initialize retry settings
        retry_config = config.get("retry_settings", {})
        self.max_retries = retry_config.get("max_retries", 3)
        self.retry_delay = retry_config.get("retry_delay", 1)
        self.backoff_factor = retry_config.get("backoff_factor", 2)
        
        # Initialize session with SSL verification
        self.session = aiohttp.ClientSession(
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=aiohttp.ClientTimeout(total=30)
        )
        
        logger.info(f"MCP Server Connector initialized: {self.base_url}")
    
    async def connect(self) -> bool:
        """
        Connect to MCP Server
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            self.session = aiohttp.ClientSession(
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
            )
            
            # Test connection
            async with self.session.get(f"{self.base_url}/health") as response:
                if response.status == 200:
                    self.connected = True
                    logger.info("Successfully connected to MCP Server")
                    return True
                else:
                    logger.error(f"Failed to connect to MCP Server: {response.status}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error connecting to MCP Server: {str(e)}")
            return False
    
    async def disconnect(self):
        """Disconnect from MCP Server"""
        if self.session:
            await self.session.close()
            self.session = None
            self.connected = False
            logger.info("Disconnected from MCP Server")
    
    async def send_command(self, command: str, params: Dict[str, Any] = None) -> MCPResponse:
        """
        Send command to MCP Server
        
        Args:
            command: Command to execute
            params: Command parameters
            
        Returns:
            MCPResponse: Response from MCP Server
        """
        if not self.connected:
            return MCPResponse(
                success=False,
                error="Not connected to MCP Server"
            )
        
        try:
            async with self.session.post(
                f"{self.base_url}/command",
                json={
                    "command": command,
                    "params": params or {},
                    "timestamp": datetime.now().isoformat()
                }
            ) as response:
                data = await response.json()
                
                if response.status == 200:
                    return MCPResponse(
                        success=True,
                        data=data
                    )
                else:
                    return MCPResponse(
                        success=False,
                        error=data.get("error", "Unknown error")
                    )
                    
        except Exception as e:
            logger.error(f"Error sending command to MCP Server: {str(e)}")
            return MCPResponse(
                success=False,
                error=str(e)
            )
    
    async def get_status(self) -> MCPResponse:
        """
        Get MCP Server status
        
        Returns:
            MCPResponse: Server status information
        """
        if not self.connected:
            return MCPResponse(
                success=False,
                error="Not connected to MCP Server"
            )
        
        try:
            async with self.session.get(f"{self.base_url}/status") as response:
                data = await response.json()
                
                if response.status == 200:
                    return MCPResponse(
                        success=True,
                        data=data
                    )
                else:
                    return MCPResponse(
                        success=False,
                        error=data.get("error", "Unknown error")
                    )
                    
        except Exception as e:
            logger.error(f"Error getting MCP Server status: {str(e)}")
            return MCPResponse(
                success=False,
                error=str(e)
            )
    
    async def subscribe_to_events(self, event_types: List[str], callback) -> bool:
        """
        Subscribe to MCP Server events
        
        Args:
            event_types: List of event types to subscribe to
            callback: Async callback function to handle events
            
        Returns:
            bool: True if subscription successful, False otherwise
        """
        if not self.connected:
            logger.error("Cannot subscribe: Not connected to MCP Server")
            return False
        
        try:
            async with self.session.post(
                f"{self.base_url}/subscribe",
                json={
                    "event_types": event_types,
                    "timestamp": datetime.now().isoformat()
                }
            ) as response:
                if response.status == 200:
                    # Start event listener
                    asyncio.create_task(self._listen_for_events(callback))
                    return True
                else:
                    logger.error(f"Failed to subscribe to events: {response.status}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error subscribing to events: {str(e)}")
            return False
    
    async def _listen_for_events(self, callback):
        """Listen for events from MCP Server"""
        try:
            async with self.session.get(f"{self.base_url}/events") as response:
                async for line in response.content:
                    if line:
                        try:
                            event = json.loads(line)
                            await callback(event)
                        except json.JSONDecodeError:
                            logger.error(f"Invalid event data: {line}")
                            
        except Exception as e:
            logger.error(f"Error listening for events: {str(e)}")
    
    async def unsubscribe_from_events(self) -> bool:
        """
        Unsubscribe from MCP Server events
        
        Returns:
            bool: True if unsubscription successful, False otherwise
        """
        if not self.connected:
            return False
        
        try:
            async with self.session.post(f"{self.base_url}/unsubscribe") as response:
                return response.status == 200
                
        except Exception as e:
            logger.error(f"Error unsubscribing from events: {str(e)}")
            return False
    
    async def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make HTTP request to MCP Server with retry logic"""
        if not self.enabled:
            raise RuntimeError("MCP Server connector is disabled")
            
        url = f"{self.base_url}{endpoint}"
        retry_count = 0
        
        while retry_count < self.max_retries:
            try:
                async with self.session.request(method, url, **kwargs) as response:
                    if response.status == 200:
                        return await response.json()
                    elif response.status == 401:
                        raise RuntimeError("Invalid API key")
                    else:
                        error_msg = await response.text()
                        raise RuntimeError(f"Server error: {error_msg}")
                        
            except aiohttp.ClientError as e:
                retry_count += 1
                if retry_count == self.max_retries:
                    raise RuntimeError(f"Failed to connect to MCP Server: {str(e)}")
                    
                wait_time = self.retry_delay * (self.backoff_factor ** (retry_count - 1))
                logger.warning(f"Retry {retry_count}/{self.max_retries} after {wait_time}s")
                await asyncio.sleep(wait_time)
                
        raise RuntimeError("Max retries exceeded") 