#!/usr/bin/env python
"""
WarMachine 社区指挥版 - 主战术调度中心
集成所有AI组件和社区功能，支持Telegram和Discord多端实时控制
"""

import os
import sys
import json
import time
import logging
import argparse
import threading
import asyncio
import signal
from typing import Dict, List, Optional, Any, Union

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/warmachine_community.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 确保logs目录存在
os.makedirs("logs", exist_ok=True)

# 导入WarMachine相关模块
try:
    # AI路由器
    from utils.ai_router import AIRouterSync
    
    # 社区组合池
    from utils.community_portfolio import CommunityPortfolioSync
    
    # 社区调度器
    from utils.community_scheduler import CommunityScheduler
    
    # 语音广播
    from utils.voice_broadcaster import VoiceBroadcasterSync
    
    # Telegram机器人启动器
    from telegram_bot_launcher import StandaloneTelegramLauncher
    
    # Discord机器人启动器
    from discord_bot_launcher import StandaloneDiscordBot
    
except ImportError as e:
    logger.error(f"导入模块失败: {e}")
    print(f"错误: 导入模块失败 - {e}")
    print("请确保已安装所有必要的依赖项")
    print("运行: pip install -r requirements.txt")
    sys.exit(1)

class UnifiedNotifier:
    """
    统一通知器
    用于向所有平台发送消息
    """
    
    def __init__(self, telegram_bot=None, discord_bot=None, voice_broadcaster=None):
        """
        初始化统一通知器
        
        Args:
            telegram_bot: Telegram机器人实例
            discord_bot: Discord机器人实例
            voice_broadcaster: 语音广播器实例
        """
        self.telegram_bot = telegram_bot
        self.discord_bot = discord_bot
        self.voice_broadcaster = voice_broadcaster
        
        # 默认消息目标
        self.default_telegram_targets = []
        self.default_discord_targets = []
        
        logger.info("统一通知器初始化完成")
    
    def set_default_targets(self, telegram_targets=None, discord_targets=None):
        """设置默认消息目标"""
        if telegram_targets:
            self.default_telegram_targets = telegram_targets
        if discord_targets:
            self.default_discord_targets = discord_targets
    
    def send_message(self, message: str, image_path: str = None, telegram_targets: List[str] = None, discord_targets: List[str] = None):
        """
        发送文本消息到所有平台
        
        Args:
            message: 消息内容
            image_path: 可选的图片路径
            telegram_targets: Telegram目标列表
            discord_targets: Discord目标列表
        """
        # 使用默认目标或指定目标
        telegram_targets = telegram_targets or self.default_telegram_targets
        discord_targets = discord_targets or self.default_discord_targets
        
        # 发送到Telegram
        if self.telegram_bot and telegram_targets:
            for target in telegram_targets:
                try:
                    if image_path and os.path.exists(image_path):
                        # 发送图片消息
                        if hasattr(self.telegram_bot, 'send_photo'):
                            asyncio.run(self.telegram_bot.send_photo(target, image_path, message))
                        else:
                            logger.warning(f"Telegram机器人不支持send_photo方法")
                    else:
                        # 发送文本消息
                        if hasattr(self.telegram_bot, 'send_message'):
                            asyncio.run(self.telegram_bot.send_message(target, message))
                        else:
                            logger.warning(f"Telegram机器人不支持send_message方法")
                except Exception as e:
                    logger.error(f"向Telegram发送消息失败: {e}")
        
        # 发送到Discord
        if self.discord_bot and discord_targets:
            for target in discord_targets:
                try:
                    if image_path and os.path.exists(image_path):
                        # 发送图片消息
                        if hasattr(self.discord_bot, 'send_photo'):
                            asyncio.run(self.discord_bot.send_photo(target, image_path, message))
                        else:
                            logger.warning(f"Discord机器人不支持send_photo方法")
                    else:
                        # 发送文本消息
                        if hasattr(self.discord_bot, 'send_message'):
                            asyncio.run(self.discord_bot.send_message(target, message))
                        else:
                            logger.warning(f"Discord机器人不支持send_message方法")
                except Exception as e:
                    logger.error(f"向Discord发送消息失败: {e}")
    
    def broadcast(self, message: str, image_path: str = None, with_voice: bool = False, voice_type: str = "default"):
        """
        广播消息到所有平台
        
        Args:
            message: 消息内容
            image_path: 可选的图片路径
            with_voice: 是否包含语音
            voice_type: 语音类型
        """
        # 发送文本/图片消息
        self.send_message(message, image_path)
        
        # 如果启用语音，生成并发送语音
        if with_voice and self.voice_broadcaster:
            try:
                self.voice_broadcaster.quick_broadcast(message, voice_type)
            except Exception as e:
                logger.error(f"发送语音消息失败: {e}")

class WarMachineCommunity:
    """
    WarMachine 社区指挥版主控制器
    """
    
    def __init__(self, config_path: str = None):
        """
        初始化WarMachine社区版
        
        Args:
            config_path: 配置文件路径
        """
        # 加载配置
        self.config_path = config_path or os.path.join("config", "warmachine_community_config.json")
        self.config = self._load_config()
        
        # 处理信号
        self._setup_signal_handlers()
        
        # 创建组件
        self._init_components()
        
        # 组件状态
        self.running = False
        self.components_status = {}
        
        logger.info("WarMachine社区指挥版初始化完成")
    
    def _load_config(self) -> Dict:
        """
        加载配置文件
        
        Returns:
            配置字典
        """
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                logger.info(f"已加载配置文件: {self.config_path}")
                return config
            else:
                # 尝试加载标准配置
                standard_config_path = os.path.join("config", "warmachine_config.json")
                if os.path.exists(standard_config_path):
                    with open(standard_config_path, "r", encoding="utf-8") as f:
                        config = json.load(f)
                    logger.info(f"已加载标准配置文件: {standard_config_path}")
                    return config
                else:
                    logger.warning("找不到配置文件，使用默认配置")
                    return {}
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            return {}
    
    def _setup_signal_handlers(self):
        """设置信号处理器"""
        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)
    
    def _handle_signal(self, signum, frame):
        """处理信号"""
        logger.info(f"接收到信号: {signum}")
        self.stop()
        sys.exit(0)
    
    def _init_components(self):
        """初始化各个组件"""
        # 初始化AI路由器
        self.ai_router = AIRouterSync(self.config.get("ai", {}))
        
        # 初始化社区组合池
        self.portfolio_manager = CommunityPortfolioSync(self.config.get("community_portfolio", {}))
        
        # 初始化Telegram机器人
        self.telegram_bot = None
        if self.config.get("telegram", {}).get("enabled", True):
            try:
                self.telegram_bot = StandaloneTelegramLauncher(self.config)
                logger.info("Telegram机器人初始化完成")
            except Exception as e:
                logger.error(f"初始化Telegram机器人失败: {e}")
        
        # 初始化Discord机器人
        self.discord_bot = None
        if self.config.get("discord", {}).get("enabled", True):
            try:
                self.discord_bot = StandaloneDiscordBot(self.config)
                logger.info("Discord机器人初始化完成")
            except Exception as e:
                logger.error(f"初始化Discord机器人失败: {e}")
        
        # 初始化统一通知器
        self.notifier = UnifiedNotifier(
            telegram_bot=self.telegram_bot,
            discord_bot=self.discord_bot
        )
        
        # 设置默认目标
        self.notifier.set_default_targets(
            telegram_targets=self.config.get("telegram", {}).get("broadcast_channels", []),
            discord_targets=self.config.get("discord", {}).get("broadcast_channels", [])
        )
        
        # 初始化语音广播器
        self.voice_broadcaster = VoiceBroadcasterSync(
            config=self.config.get("voice_broadcaster", {}),
            telegram_bot=self.telegram_bot,
            discord_bot=self.discord_bot
        )
        
        # 设置通知器的语音广播器
        self.notifier.voice_broadcaster = self.voice_broadcaster
        
        # 初始化社区调度器
        self.scheduler = CommunityScheduler(
            config=self.config.get("community_scheduler", {}),
            notifier=self.notifier
        )
    
    def start(self):
        """启动所有组件"""
        if self.running:
            logger.warning("WarMachine社区指挥版已在运行中")
            return
        
        logger.info("正在启动WarMachine社区指挥版...")
        
        try:
            # 启动Telegram机器人
            if self.telegram_bot:
                asyncio.run(self.telegram_bot.start())
                self.components_status["telegram_bot"] = "running"
                logger.info("Telegram机器人已启动")
            
            # 启动Discord机器人
            if self.discord_bot:
                self.discord_bot.run()
                self.components_status["discord_bot"] = "running"
                logger.info("Discord机器人已启动")
            
            # 启动社区调度器
            self.scheduler.start()
            self.components_status["scheduler"] = "running"
            logger.info("社区调度器已启动")
            
            # 发送启动通知
            self.notifier.broadcast(
                "🚀 **WarMachine社区指挥版已启动**\n\n"
                "• AI多模型路由: ✅\n"
                "• 社区组合池: ✅\n"
                "• 自动调度: ✅\n"
                "• 语音广播: ✅\n\n"
                "系统已准备就绪，随时为您提供市场分析和交易信号。",
                with_voice=True
            )
            
            self.running = True
            logger.info("WarMachine社区指挥版已成功启动")
            
            # 保持程序运行
            while self.running:
                time.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("接收到中断信号，正在关闭...")
            self.stop()
        except Exception as e:
            logger.error(f"启动失败: {e}")
            self.stop()
    
    def stop(self):
        """停止所有组件"""
        if not self.running:
            return
        
        logger.info("正在停止WarMachine社区指挥版...")
        
        # 停止社区调度器
        if self.scheduler:
            self.scheduler.stop()
            self.components_status["scheduler"] = "stopped"
            logger.info("社区调度器已停止")
        
        # 停止Telegram机器人
        if self.telegram_bot:
            asyncio.run(self.telegram_bot.stop())
            self.components_status["telegram_bot"] = "stopped"
            logger.info("Telegram机器人已停止")
        
        # 停止Discord机器人在StandaloneDiscordBot类中已有实现，不需要额外调用
        
        # 发送关闭通知
        try:
            self.notifier.broadcast("⚠️ WarMachine社区指挥版正在关闭...")
        except:
            pass
        
        self.running = False
        logger.info("WarMachine社区指挥版已成功停止")
    
    def restart(self):
        """重启所有组件"""
        logger.info("正在重启WarMachine社区指挥版...")
        self.stop()
        time.sleep(2)
        self.start()

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="WarMachine社区指挥版")
    parser.add_argument("--config", "-c", type=str, help="配置文件路径")
    args = parser.parse_args()
    
    # 创建并启动WarMachine社区指挥版
    warmachine = WarMachineCommunity(config_path=args.config)
    warmachine.start()

if __name__ == "__main__":
    main() 