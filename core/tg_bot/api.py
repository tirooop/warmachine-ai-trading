"""
Telegram API Handler

Handles all interactions with the Telegram Bot API.
"""

import logging
import aiohttp
import asyncio
from typing import Dict, Any, Optional, List, Union
from datetime import datetime

logger = logging.getLogger(__name__)

class TelegramAPI:
    """Handler for Telegram Bot API interactions"""
    
    def __init__(self, token: str, config: Optional[Dict[str, Any]] = None):
        """
        Initialize Telegram API handler
        
        Args:
            token: Telegram bot token
            config: Optional configuration dictionary
        """
        self.token = token
        self.config = config or {}
        self.base_url = f"https://api.telegram.org/bot{token}"
        self.session = None
        self.rate_limit = self.config.get("rate_limit", 1.0)  # seconds between messages
        self.last_send_time = 0
        self.max_retries = self.config.get("max_retries", 3)
        self.retry_delay = self.config.get("retry_delay", 1.0)
        
        logger.info("Telegram API handler initialized")
    
    async def __aenter__(self):
        """Create aiohttp session when entering context"""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Close aiohttp session when exiting context"""
        if self.session:
            await self.session.close()
    
    async def _make_request(self, method: str, data: Dict[str, Any], 
                           retry_count: int = 0) -> Optional[Dict[str, Any]]:
        """
        Make a request to the Telegram API
        
        Args:
            method: API method name
            data: Request data
            retry_count: Current retry attempt
            
        Returns:
            API response as dictionary or None if failed
        """
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        try:
            # Rate limiting
            current_time = datetime.now().timestamp()
            time_since_last = current_time - self.last_send_time
            if time_since_last < self.rate_limit:
                await asyncio.sleep(self.rate_limit - time_since_last)
            
            url = f"{self.base_url}/{method}"
            async with self.session.post(url, json=data) as response:
                if response.status == 200:
                    result = await response.json()
                    if result.get("ok"):
                        self.last_send_time = datetime.now().timestamp()
                        return result.get("result")
                    else:
                        error_msg = result.get("description", "Unknown error")
                        logger.error(f"Telegram API error: {error_msg}")
                        return None
                else:
                    logger.error(f"HTTP error {response.status}: {await response.text()}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error making Telegram API request: {str(e)}")
            if retry_count < self.max_retries:
                await asyncio.sleep(self.retry_delay * (retry_count + 1))
                return await self._make_request(method, data, retry_count + 1)
            return None
    
    async def send_message(self, chat_id: Union[str, int], text: str, 
                          parse_mode: str = "Markdown", 
                          disable_web_page_preview: bool = True) -> bool:
        """
        Send a message to a chat
        
        Args:
            chat_id: Target chat ID
            text: Message text
            parse_mode: Message format (Markdown, HTML)
            disable_web_page_preview: Whether to disable link previews
            
        Returns:
            True if message was sent successfully
        """
        # Ensure message isn't too long
        if len(text) > 4096:
            text = text[:4093] + "..."
        
        data = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": disable_web_page_preview
        }
        
        result = await self._make_request("sendMessage", data)
        return result is not None
    
    async def send_photo(self, chat_id: Union[str, int], photo: str,
                        caption: Optional[str] = None,
                        parse_mode: str = "Markdown") -> bool:
        """
        Send a photo to a chat
        
        Args:
            chat_id: Target chat ID
            photo: Photo file ID or URL
            caption: Optional photo caption
            parse_mode: Caption format (Markdown, HTML)
            
        Returns:
            True if photo was sent successfully
        """
        data = {
            "chat_id": chat_id,
            "photo": photo,
            "parse_mode": parse_mode
        }
        
        if caption:
            data["caption"] = caption
        
        result = await self._make_request("sendPhoto", data)
        return result is not None
    
    async def send_document(self, chat_id: Union[str, int], document: str,
                          caption: Optional[str] = None,
                          parse_mode: str = "Markdown") -> bool:
        """
        Send a document to a chat
        
        Args:
            chat_id: Target chat ID
            document: Document file ID or URL
            caption: Optional document caption
            parse_mode: Caption format (Markdown, HTML)
            
        Returns:
            True if document was sent successfully
        """
        data = {
            "chat_id": chat_id,
            "document": document,
            "parse_mode": parse_mode
        }
        
        if caption:
            data["caption"] = caption
        
        result = await self._make_request("sendDocument", data)
        return result is not None
    
    async def send_media_group(self, chat_id: Union[str, int],
                             media: List[Dict[str, Any]]) -> bool:
        """
        Send a group of media items to a chat
        
        Args:
            chat_id: Target chat ID
            media: List of media items to send
            
        Returns:
            True if media group was sent successfully
        """
        data = {
            "chat_id": chat_id,
            "media": media
        }
        
        result = await self._make_request("sendMediaGroup", data)
        return result is not None
    
    async def edit_message(self, chat_id: Union[str, int], message_id: int,
                          text: str, parse_mode: str = "Markdown") -> bool:
        """
        Edit an existing message
        
        Args:
            chat_id: Chat ID containing the message
            message_id: ID of message to edit
            text: New message text
            parse_mode: Message format (Markdown, HTML)
            
        Returns:
            True if message was edited successfully
        """
        data = {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text,
            "parse_mode": parse_mode
        }
        
        result = await self._make_request("editMessageText", data)
        return result is not None
    
    async def delete_message(self, chat_id: Union[str, int], message_id: int) -> bool:
        """
        Delete a message
        
        Args:
            chat_id: Chat ID containing the message
            message_id: ID of message to delete
            
        Returns:
            True if message was deleted successfully
        """
        data = {
            "chat_id": chat_id,
            "message_id": message_id
        }
        
        result = await self._make_request("deleteMessage", data)
        return result is not None
    
    async def get_chat(self, chat_id: Union[str, int]) -> Optional[Dict[str, Any]]:
        """
        Get information about a chat
        
        Args:
            chat_id: Chat ID to get information for
            
        Returns:
            Chat information dictionary or None if failed
        """
        data = {"chat_id": chat_id}
        return await self._make_request("getChat", data)
    
    async def get_chat_member(self, chat_id: Union[str, int], user_id: Union[str, int]) -> Optional[Dict[str, Any]]:
        """
        Get information about a chat member
        
        Args:
            chat_id: Chat ID
            user_id: User ID to get information for
            
        Returns:
            Chat member information dictionary or None if failed
        """
        data = {
            "chat_id": chat_id,
            "user_id": user_id
        }
        return await self._make_request("getChatMember", data) 