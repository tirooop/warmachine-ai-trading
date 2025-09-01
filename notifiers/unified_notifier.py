"""


Unified Notifier - Centralized notification system for multiple platforms





This module provides a unified interface for sending notifications across multiple


platforms (Telegram, Discord, Feishu) with consistent formatting and tracking.


"""





import os


import logging


import json


import time


import requests


from typing import Dict, Any, Optional, List, Union, Callable


from pathlib import Path


import asyncio


from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton


from telegram.ext import (


    Application,


    CommandHandler,


    MessageHandler,


    CallbackQueryHandler,


    filters


)


import discord


from discord.ext import commands





# Set up logging


logger = logging.getLogger(__name__)





class BaseNotifier:


    """Base class for platform notifiers"""


    


    def __init__(self, config: Dict[str, Any]):


        self.config = config


        self.enabled = False


        self.max_retries = 3


        self.retry_delay = 1  # 秒


        self.error_count = 0


        self.last_error_time = 0


        


    async def _retry_with_backoff(self, func: Callable, *args, **kwargs) -> bool:


        """带退避的重试机制"""


        for attempt in range(self.max_retries):


            try:


                return await func(*args, **kwargs)


            except Exception as e:


                self.error_count += 1


                self.last_error_time = time.time()


                


                if attempt < self.max_retries - 1:


                    delay = self.retry_delay * (2 ** attempt)  # 指数退避


                    logger.warning(f"Retry {attempt + 1}/{self.max_retries} after {delay}s: {str(e)}")


                    await asyncio.sleep(delay)


                else:


                    logger.error(f"All retries failed: {str(e)}")


                    return False


                    


    def _should_throttle(self) -> bool:


        """检查是否需要限流"""


        if self.error_count >= 10 and time.time() - self.last_error_time < 300:  # 5分钟内错误超过10次


            return True


        return False


        


    def _reset_error_count(self) -> None:


        """重置错误计数"""


        if time.time() - self.last_error_time > 300:  # 5分钟后重置


            self.error_count = 0


            self.last_error_time = 0


            


    async def send(self, message: str, title: str = "", group_id: str = None) -> bool:


        """发送消息（带重试）"""


        if self._should_throttle():


            logger.warning("Message sending throttled due to high error rate")


            return False


            


        success = await self._retry_with_backoff(self._send_impl, message, title, group_id)


        if success:


            self._reset_error_count()


        return success


        


    async def _send_impl(self, message: str, title: str = "", group_id: str = None) -> bool:


        """实际发送消息的实现"""


        raise NotImplementedError("Subclasses must implement _send_impl()")


        


    def send_image(self, image_path: str, caption: str = "", group_id: str = None) -> bool:


        """


        Send an image to the platform


        


        Args:


            image_path: Path to image file


            caption: Optional image caption


            group_id: Optional group/channel ID


            


        Returns:


            Success status


        """


        raise NotImplementedError("Subclasses must implement send_image()")


        


    def send_file(self, file_path: str, caption: str = "", group_id: str = None) -> bool:


        """


        Send a file to the platform


        


        Args:


            file_path: Path to file


            caption: Optional file caption


            group_id: Optional group/channel ID


            


        Returns:


            Success status


        """


        raise NotImplementedError("Subclasses must implement send_file()")


        


    def send_audio(self, audio_path: str, title: str = "", group_id: str = None) -> bool:


        """


        Send an audio file to the platform


        


        Args:


            audio_path: Path to audio file


            title: Optional audio title


            group_id: Optional group/channel ID


            


        Returns:


            Success status


        """


        raise NotImplementedError("Subclasses must implement send_audio()")





class TelegramNotifier(BaseNotifier):


    """Notifier for Telegram platform"""


    


    def __init__(self, config: Dict[str, Any]):


        super().__init__(config)


        self.telegram_config = config.get("telegram", {})


        self.token = self.telegram_config.get("token", "")


        self.enabled = self.telegram_config.get("enabled", False) and bool(self.token)


        self.admin_chat_id = self.telegram_config.get("admin_chat_id", "")


        self.report_channel_id = self.telegram_config.get("report_channel_id", "")


        


        if self.enabled:


            logger.info("Telegram notifier initialized")


        else:


            logger.warning("Telegram notifier disabled or missing token")


            


    async def _send_impl(self, message: str, title: str = "", group_id: str = None) -> bool:


        """


        Send a message to Telegram


        


        Args:


            message: Message content


            title: Optional message title


            group_id: Optional chat/channel ID


            


        Returns:


            Success status


        """


        if not self.enabled:


            logger.warning("Telegram notifier is disabled")


            return False


            


        try:


            chat_id = group_id or self.admin_chat_id


            


            if not chat_id:


                logger.error("No chat ID specified for Telegram message")


                return False


                


            # Format message with title if provided


            formatted_message = f"*{title}*\n\n{message}" if title else message


            


            # Send message via Telegram API


            url = f"https://api.telegram.org/bot{self.token}/sendMessage"


            data = {


                "chat_id": chat_id,


                "text": formatted_message,


                "parse_mode": "Markdown"


            }


            


            response = requests.post(url, json=data, timeout=10)


            


            if response.status_code == 200:


                logger.info(f"Message sent to Telegram chat {chat_id}")


                return True


            else:


                logger.error(f"Failed to send Telegram message: {response.status_code} - {response.text}")


                return False


                


        except Exception as e:


            logger.error(f"Error sending Telegram message: {str(e)}")


            return False


            


    def send_image(self, image_path: str, caption: str = "", group_id: str = None) -> bool:


        """


        Send an image to Telegram


        


        Args:


            image_path: Path to image file


            caption: Optional image caption


            group_id: Optional chat/channel ID


            


        Returns:


            Success status


        """


        if not self.enabled:


            logger.warning("Telegram notifier is disabled")


            return False


            


        try:


            chat_id = group_id or self.admin_chat_id


            


            if not chat_id:


                logger.error("No chat ID specified for Telegram image")


                return False


                


            if not os.path.exists(image_path):


                logger.error(f"Image file not found: {image_path}")


                return False


                


            # Send image via Telegram API


            url = f"https://api.telegram.org/bot{self.token}/sendPhoto"


            files = {"photo": open(image_path, "rb")}


            data = {


                "chat_id": chat_id,


                "caption": caption,


                "parse_mode": "Markdown"


            }


            


            response = requests.post(url, files=files, data=data, timeout=30)


            


            if response.status_code == 200:


                logger.info(f"Image sent to Telegram chat {chat_id}")


                return True


            else:


                logger.error(f"Failed to send Telegram image: {response.status_code} - {response.text}")


                return False


                


        except Exception as e:


            logger.error(f"Error sending Telegram image: {str(e)}")


            return False


            


    def send_file(self, file_path: str, caption: str = "", group_id: str = None) -> bool:


        """


        Send a file to Telegram


        


        Args:


            file_path: Path to file


            caption: Optional file caption


            group_id: Optional chat/channel ID


            


        Returns:


            Success status


        """


        if not self.enabled:


            logger.warning("Telegram notifier is disabled")


            return False


            


        try:


            chat_id = group_id or self.admin_chat_id


            


            if not chat_id:


                logger.error("No chat ID specified for Telegram file")


                return False


                


            if not os.path.exists(file_path):


                logger.error(f"File not found: {file_path}")


                return False


                


            # Send file via Telegram API


            url = f"https://api.telegram.org/bot{self.token}/sendDocument"


            files = {"document": open(file_path, "rb")}


            data = {


                "chat_id": chat_id,


                "caption": caption,


                "parse_mode": "Markdown"


            }


            


            response = requests.post(url, files=files, data=data, timeout=60)


            


            if response.status_code == 200:


                logger.info(f"File sent to Telegram chat {chat_id}")


                return True


            else:


                logger.error(f"Failed to send Telegram file: {response.status_code} - {response.text}")


                return False


                


        except Exception as e:


            logger.error(f"Error sending Telegram file: {str(e)}")


            return False


            


    def send_audio(self, audio_path: str, title: str = "", group_id: str = None) -> bool:


        """


        Send an audio file to Telegram


        


        Args:


            audio_path: Path to audio file


            title: Optional audio title


            group_id: Optional chat/channel ID


            


        Returns:


            Success status


        """


        if not self.enabled:


            logger.warning("Telegram notifier is disabled")


            return False


            


        try:


            chat_id = group_id or self.admin_chat_id


            


            if not chat_id:


                logger.error("No chat ID specified for Telegram audio")


                return False


                


            if not os.path.exists(audio_path):


                logger.error(f"Audio file not found: {audio_path}")


                return False


                


            # Send audio via Telegram API


            url = f"https://api.telegram.org/bot{self.token}/sendAudio"


            files = {"audio": open(audio_path, "rb")}


            data = {


                "chat_id": chat_id,


                "title": title,


                "parse_mode": "Markdown"


            }


            


            response = requests.post(url, files=files, data=data, timeout=60)


            


            if response.status_code == 200:


                logger.info(f"Audio sent to Telegram chat {chat_id}")


                return True


            else:


                logger.error(f"Failed to send Telegram audio: {response.status_code} - {response.text}")


                return False


                


        except Exception as e:


            logger.error(f"Error sending Telegram audio: {str(e)}")


            return False





class DiscordNotifier(BaseNotifier):


    """Notifier for Discord platform"""


    


    def __init__(self, config: Dict[str, Any]):


        super().__init__(config)


        self.discord_config = config.get("discord", {})


        self.token = self.discord_config.get("token", "")


        self.enabled = self.discord_config.get("enabled", False) and bool(self.token)


        self.admin_channel_id = self.discord_config.get("admin_channel_id", "")


        self.report_channel_id = self.discord_config.get("report_channel_id", "")


        


        if self.enabled:


            logger.info("Discord notifier initialized")


        else:


            logger.warning("Discord notifier disabled or missing token")


            


    async def _send_impl(self, message: str, title: str = "", group_id: str = None) -> bool:


        """


        Send a message to Discord


        


        Args:


            message: Message content


            title: Optional message title


            group_id: Optional channel ID


            


        Returns:


            Success status


        """


        if not self.enabled:


            logger.warning("Discord notifier is disabled")


            return False


            


        try:


            channel_id = group_id or self.admin_channel_id


            


            if not channel_id:


                logger.error("No channel ID specified for Discord message")


                return False


                


            # Create an embed if title is provided


            payload = {


                "content": message if not title else None,


                "embeds": [


                    {


                        "title": title,


                        "description": message,


                        "color": 3447003  # Blue color


                    }


                ] if title else None


            }


            


            # Send message via Discord webhook API


            url = f"https://discord.com/api/v10/channels/{channel_id}/messages"


            headers = {


                "Authorization": f"Bot {self.token}",


                "Content-Type": "application/json"


            }


            


            response = requests.post(url, json=payload, headers=headers, timeout=10)


            


            if response.status_code in (200, 201, 204):


                logger.info(f"Message sent to Discord channel {channel_id}")


                return True


            else:


                logger.error(f"Failed to send Discord message: {response.status_code} - {response.text}")


                return False


                


        except Exception as e:


            logger.error(f"Error sending Discord message: {str(e)}")


            return False


            


    def send_image(self, image_path: str, caption: str = "", group_id: str = None) -> bool:


        """


        Send an image to Discord


        


        Args:


            image_path: Path to image file


            caption: Optional image caption


            group_id: Optional channel ID


            


        Returns:


            Success status


        """


        if not self.enabled:


            logger.warning("Discord notifier is disabled")


            return False


            


        try:


            channel_id = group_id or self.admin_channel_id


            


            if not channel_id:


                logger.error("No channel ID specified for Discord image")


                return False


                


            if not os.path.exists(image_path):


                logger.error(f"Image file not found: {image_path}")


                return False


                


            # Send image via Discord API


            url = f"https://discord.com/api/v10/channels/{channel_id}/messages"


            headers = {


                "Authorization": f"Bot {self.token}"


            }


            


            files = {


                "file": (os.path.basename(image_path), open(image_path, "rb"))


            }


            


            data = {


                "content": caption


            }


            


            response = requests.post(url, files=files, data=data, headers=headers, timeout=30)


            


            if response.status_code in (200, 201, 204):


                logger.info(f"Image sent to Discord channel {channel_id}")


                return True


            else:


                logger.error(f"Failed to send Discord image: {response.status_code} - {response.text}")


                return False


                


        except Exception as e:


            logger.error(f"Error sending Discord image: {str(e)}")


            return False


            


    def send_file(self, file_path: str, caption: str = "", group_id: str = None) -> bool:


        """


        Send a file to Discord


        


        Args:


            file_path: Path to file


            caption: Optional file caption


            group_id: Optional channel ID


            


        Returns:


            Success status


        """


        if not self.enabled:


            logger.warning("Discord notifier is disabled")


            return False


            


        try:


            channel_id = group_id or self.admin_channel_id


            


            if not channel_id:


                logger.error("No channel ID specified for Discord file")


                return False


                


            if not os.path.exists(file_path):


                logger.error(f"File not found: {file_path}")


                return False


                


            # Send file via Discord API


            url = f"https://discord.com/api/v10/channels/{channel_id}/messages"


            headers = {


                "Authorization": f"Bot {self.token}"


            }


            


            files = {


                "file": (os.path.basename(file_path), open(file_path, "rb"))


            }


            


            data = {


                "content": caption


            }


            


            response = requests.post(url, files=files, data=data, headers=headers, timeout=60)


            


            if response.status_code in (200, 201, 204):


                logger.info(f"File sent to Discord channel {channel_id}")


                return True


            else:


                logger.error(f"Failed to send Discord file: {response.status_code} - {response.text}")


                return False


                


        except Exception as e:


            logger.error(f"Error sending Discord file: {str(e)}")


            return False


            


    def send_audio(self, audio_path: str, title: str = "", group_id: str = None) -> bool:


        """


        Send an audio file to Discord


        


        Args:


            audio_path: Path to audio file


            title: Optional audio title


            group_id: Optional channel ID


            


        Returns:


            Success status


        """


        if not self.enabled:


            logger.warning("Discord notifier is disabled")


            return False


            


        try:


            channel_id = group_id or self.admin_channel_id


            


            if not channel_id:


                logger.error("No channel ID specified for Discord audio")


                return False


                


            if not os.path.exists(audio_path):


                logger.error(f"Audio file not found: {audio_path}")


                return False


                


            # Send audio file via Discord API


            url = f"https://discord.com/api/v10/channels/{channel_id}/messages"


            headers = {


                "Authorization": f"Bot {self.token}"


            }


            


            files = {


                "file": (os.path.basename(audio_path), open(audio_path, "rb"))


            }


            


            data = {


                "content": title


            }


            


            response = requests.post(url, files=files, data=data, headers=headers, timeout=60)


            


            if response.status_code in (200, 201, 204):


                logger.info(f"Audio sent to Discord channel {channel_id}")


                return True


            else:


                logger.error(f"Failed to send Discord audio: {response.status_code} - {response.text}")


                return False


                


        except Exception as e:


            logger.error(f"Error sending Discord audio: {str(e)}")


            return False





class FeishuNotifier(BaseNotifier):


    """Notifier for Feishu (Lark) platform"""


    


    def __init__(self, config: Dict[str, Any]):


        super().__init__(config)


        self.feishu_config = config.get("feishu", {})


        self.webhook_url = self.feishu_config.get("webhook_url", "")


        self.enabled = self.feishu_config.get("enabled", False) and bool(self.webhook_url)


        


        if self.enabled:


            logger.info("Feishu notifier initialized")


        else:


            logger.warning("Feishu notifier disabled or missing webhook URL")


            


    async def _send_impl(self, message: str, title: str = "", group_id: str = None) -> bool:


        """


        Send a message to Feishu


        


        Args:


            message: Message content


            title: Optional message title


            group_id: Optional group ID (ignored for webhook)


            


        Returns:


            Success status


        """


        if not self.enabled:


            logger.warning("Feishu notifier is disabled")


            return False


            


        try:


            # Format message with title if provided


            if title:


                payload = {


                    "msg_type": "interactive",


                    "card": {


                        "elements": [{


                            "tag": "div",


                            "text": {


                                "content": message,


                                "tag": "lark_md"


                            }


                        }],


                        "header": {


                            "title": {


                                "content": title,


                                "tag": "plain_text"


                            }


                        }


                    }


                }


            else:


                payload = {


                    "msg_type": "text",


                    "content": {


                        "text": message


                    }


                }


                


            # Send message via Feishu webhook


            response = requests.post(self.webhook_url, json=payload, timeout=10)


            


            if response.status_code == 200:


                result = response.json()


                if result.get("code") == 0:


                    logger.info("Message sent to Feishu")


                    return True


                else:


                    logger.error(f"Failed to send Feishu message: {result.get('msg')}")


                    return False


            else:


                logger.error(f"Failed to send Feishu message: {response.status_code} - {response.text}")


                return False


                


        except Exception as e:


            logger.error(f"Error sending Feishu message: {str(e)}")


            return False


            


    def send_image(self, image_path: str, caption: str = "", group_id: str = None) -> bool:


        """


        Send an image to Feishu


        


        Note: For webhook, image needs to be publicly accessible URL


        This implementation uses a simple text message with the caption


        


        Args:


            image_path: Path to image file (ignored for webhook)


            caption: Optional image caption


            group_id: Optional group ID (ignored for webhook)


            


        Returns:


            Success status


        """


        if not self.enabled:


            logger.warning("Feishu notifier is disabled")


            return False


            


        message = f"Image: {os.path.basename(image_path)}"


        if caption:


            message += f"\n{caption}"


            


        return self.send(message)


        


    def send_file(self, file_path: str, caption: str = "", group_id: str = None) -> bool:


        """


        Send a file to Feishu


        


        Note: For webhook, file needs to be publicly accessible URL


        This implementation uses a simple text message with the caption


        


        Args:


            file_path: Path to file (ignored for webhook)


            caption: Optional file caption


            group_id: Optional group ID (ignored for webhook)


            


        Returns:


            Success status


        """


        if not self.enabled:


            logger.warning("Feishu notifier is disabled")


            return False


            


        message = f"File: {os.path.basename(file_path)}"


        if caption:


            message += f"\n{caption}"


            


        return self.send(message)


        


    def send_audio(self, audio_path: str, title: str = "", group_id: str = None) -> bool:


        """


        Send an audio file to Feishu


        


        Note: For webhook, audio needs to be publicly accessible URL


        This implementation uses a simple text message with the title


        


        Args:


            audio_path: Path to audio file (ignored for webhook)


            title: Optional audio title


            group_id: Optional group ID (ignored for webhook)


            


        Returns:


            Success status


        """


        if not self.enabled:


            logger.warning("Feishu notifier is disabled")


            return False


            


        message = f"Audio: {os.path.basename(audio_path)}"


        if title:


            message += f"\n{title}"


            


        return self.send(message)





class UnifiedNotifier:


    """Unified notifier for multiple platforms"""


    


    def __init__(self, config: Dict[str, Any]):


        """


        Initialize the unified notifier


        


        Args:


            config: Configuration dictionary


        """


        self.config = config


        


        # Initialize platform notifiers


        self.telegram = TelegramNotifier(config)


        self.discord = DiscordNotifier(config)


        self.feishu = FeishuNotifier(config)


        


        # Platform notifiers dictionary


        self.notifiers = {


            "telegram": self.telegram,


            "discord": self.discord,


            "feishu": self.feishu


        }


        


        # Count enabled notifiers


        enabled_count = sum(1 for n in self.notifiers.values() if n.enabled)


        logger.info(f"Unified notifier initialized with {enabled_count} enabled platforms")


        


    def send(self, message: str, title: str = "", platforms: List[str] = None, group_ids: Dict[str, str] = None) -> Dict[str, bool]:


        """


        Send a message to multiple platforms


        


        Args:


            message: Message content


            title: Optional message title


            platforms: List of platforms to send to (default: all enabled)


            group_ids: Dictionary of platform-specific group IDs


            


        Returns:


            Dictionary of platform: success status


        """


        results = {}


        group_ids = group_ids or {}


        


        # Determine which platforms to use


        if platforms:


            targets = [p for p in platforms if p in self.notifiers and self.notifiers[p].enabled]


        else:


            targets = [p for p, n in self.notifiers.items() if n.enabled]


            


        # Send to each platform


        for platform in targets:


            notifier = self.notifiers[platform]


            group_id = group_ids.get(platform)


            results[platform] = notifier.send(message, title, group_id)


            


        return results


        


    def send_image(self, image_path: str, caption: str = "", platforms: List[str] = None, group_ids: Dict[str, str] = None) -> Dict[str, bool]:


        """


        Send an image to multiple platforms


        


        Args:


            image_path: Path to image file


            caption: Optional image caption


            platforms: List of platforms to send to (default: all enabled)


            group_ids: Dictionary of platform-specific group IDs


            


        Returns:


            Dictionary of platform: success status


        """


        results = {}


        group_ids = group_ids or {}


        


        # Determine which platforms to use


        if platforms:


            targets = [p for p in platforms if p in self.notifiers and self.notifiers[p].enabled]


        else:


            targets = [p for p, n in self.notifiers.items() if n.enabled]


            


        # Send to each platform


        for platform in targets:


            notifier = self.notifiers[platform]


            group_id = group_ids.get(platform)


            results[platform] = notifier.send_image(image_path, caption, group_id)


            


        return results


        


    def send_file(self, file_path: str, caption: str = "", platforms: List[str] = None, group_ids: Dict[str, str] = None) -> Dict[str, bool]:


        """


        Send a file to multiple platforms


        


        Args:


            file_path: Path to file


            caption: Optional file caption


            platforms: List of platforms to send to (default: all enabled)


            group_ids: Dictionary of platform-specific group IDs


            


        Returns:


            Dictionary of platform: success status


        """


        results = {}


        group_ids = group_ids or {}


        


        # Determine which platforms to use


        if platforms:


            targets = [p for p in platforms if p in self.notifiers and self.notifiers[p].enabled]


        else:


            targets = [p for p, n in self.notifiers.items() if n.enabled]


            


        # Send to each platform


        for platform in targets:


            notifier = self.notifiers[platform]


            group_id = group_ids.get(platform)


            results[platform] = notifier.send_file(file_path, caption, group_id)


            


        return results


        


    def send_audio(self, audio_path: str, title: str = "", platforms: List[str] = None, group_ids: Dict[str, str] = None) -> Dict[str, bool]:


        """


        Send an audio file to multiple platforms


        


        Args:


            audio_path: Path to audio file


            title: Optional audio title


            platforms: List of platforms to send to (default: all enabled)


            group_ids: Dictionary of platform-specific group IDs


            


        Returns:


            Dictionary of platform: success status


        """


        results = {}


        group_ids = group_ids or {}


        


        # Determine which platforms to use


        if platforms:


            targets = [p for p in platforms if p in self.notifiers and self.notifiers[p].enabled]


        else:


            targets = [p for p, n in self.notifiers.items() if n.enabled]


            


        # Send to each platform


        for platform in targets:


            notifier = self.notifiers[platform]


            group_id = group_ids.get(platform)


            results[platform] = notifier.send_audio(audio_path, title, group_id)


            


        return results


        


    def send_report(self, report_text: str, report_type: str, audio_path: str = None, image_path: str = None) -> Dict[str, bool]:


        """


        Send a report to the appropriate channels on each platform


        


        Args:


            report_text: Report content


            report_type: Type of report (daily, weekly, performance, alert)


            audio_path: Optional path to audio version


            image_path: Optional path to image/chart


            


        Returns:


            Dictionary of platform: success status


        """


        results = {}


        title = f"{report_type.capitalize()} Report - {datetime.now().strftime('%Y-%m-%d')}"


        


        # Send text report to each platform


        for platform, notifier in self.notifiers.items():


            if not notifier.enabled:


                continue


                


            # Get appropriate channel for this platform and report type


            channel_id = None


            if platform == "telegram":


                channel_id = self.config.get("telegram", {}).get("report_channel_id")


            elif platform == "discord":


                channel_id = self.config.get("discord", {}).get("report_channel_id")


                


            # Send text report


            results[f"{platform}_text"] = notifier.send(report_text, title, channel_id)


            


            # Send audio if available and appropriate for platform


            if audio_path and os.path.exists(audio_path) and platform in ["telegram", "discord"]:


                results[f"{platform}_audio"] = notifier.send_audio(audio_path, title, channel_id)


                


            # Send image if available


            if image_path and os.path.exists(image_path):


                results[f"{platform}_image"] = notifier.send_image(image_path, title, channel_id)


                


        return results


    def _init_telegram_bot(self) -> Application:
        """初始化Telegram机器人"""
        bot = Application.builder().token(self.config["telegram"]["token"]).build()
        
        # 注册命令处理器
        bot.add_handler(CommandHandler("start", self._handle_telegram_start))
        bot.add_handler(CommandHandler("help", self._handle_telegram_help))
        bot.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            self._handle_telegram_message
        ))
        bot.add_handler(CallbackQueryHandler(self._handle_telegram_callback))
        
        return bot
        
    def _init_discord_bot(self) -> commands.Bot:
        """初始化Discord机器人"""
        intents = discord.Intents.default()
        intents.message_content = True
        bot = commands.Bot(command_prefix='!', intents=intents)
        
        # 注册命令
        @bot.event
        async def on_ready():
            logger.info(f'Discord bot logged in as {bot.user}')
            
        @bot.command(name='start')
        async def start(ctx):
            await self._handle_discord_start(ctx)
            
        @bot.command(name='help')
        async def help(ctx):
            await self._handle_discord_help(ctx)
            
        return bot
        
    async def _handle_telegram_start(self, update: Update, context):
        """处理Telegram /start命令"""
        welcome_text = (
            "欢迎使用期权分析机器人！\n\n"
            "使用方法：\n"
            "1. 输入股票代码和到期日，例如：AAPL 2024-06-21\n"
            "2. 使用/help查看所有可用命令\n"
            "3. 点击按钮查看详细分析"
        )
        await update.message.reply_text(
            welcome_text,
            reply_markup=self._build_telegram_keyboard()
        )
        
    async def _handle_discord_start(self, ctx):
        """处理Discord !start命令"""
        welcome_text = (
            "欢迎使用期权分析机器人！\n\n"
            "使用方法：\n"
            "1. 输入股票代码和到期日，例如：!analyze AAPL 2024-06-21\n"
            "2. 使用!help查看所有可用命令\n"
            "3. 使用!greeks查看Greeks分析"
        )
        await ctx.send(welcome_text)
        
    async def send_notification(self, message: str, platform: str = "all", **kwargs):
        """发送通知到指定平台"""
        try:
            if platform in ["all", "telegram"] and hasattr(self, "telegram_bot"):
                await self._send_telegram_notification(message, **kwargs)
                
            if platform in ["all", "discord"] and hasattr(self, "discord_bot"):
                await self._send_discord_notification(message, **kwargs)
                
        except Exception as e:
            logger.error(f"Error sending notification: {str(e)}")
            
    async def _send_telegram_notification(self, message: str, **kwargs):
        """发送Telegram通知"""
        chat_id = kwargs.get("chat_id")
        if not chat_id:
            logger.warning("No chat_id provided for Telegram notification")
            return
            
        try:
            await self.telegram_bot.bot.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Error sending Telegram notification: {str(e)}")
            
    async def _send_discord_notification(self, message: str, **kwargs):
        """发送Discord通知"""
        channel_id = kwargs.get("channel_id")
        if not channel_id:
            logger.warning("No channel_id provided for Discord notification")
            return
            
        try:
            channel = self.discord_bot.get_channel(channel_id)
            if channel:
                await channel.send(message)
        except Exception as e:
            logger.error(f"Error sending Discord notification: {str(e)}")
            
    async def start(self):
        """启动所有通知服务"""
        tasks = []
        
        if hasattr(self, "telegram_bot"):
            tasks.append(self.telegram_bot.run_polling())
            
        if hasattr(self, "discord_bot"):
            tasks.append(self.discord_bot.start(self.config["discord"]["token"]))
            
        if tasks:
            await asyncio.gather(*tasks)
            
    async def stop(self):
        """停止所有通知服务"""
        if hasattr(self, "telegram_bot"):
            await self.telegram_bot.stop()
            
        if hasattr(self, "discord_bot"):
            await self.discord_bot.close() 