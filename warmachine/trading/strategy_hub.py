#!/usr/bin/env python3
"""
Main Strategy Hub - Command-line interface for running predefined strategies

This module provides a command-line interface for executing various trading strategies
with different parameters and presets. It serves as the main entry point for manual
strategy execution and testing.

Example usage:
    # Run a single strategy for AAPL with default parameters
    python main_strategy_hub.py --symbol AAPL
    
    # Run a specific preset strategy for multiple symbols
    python main_strategy_hub.py --symbols AAPL MSFT GOOGL --preset trend_following
    
    # Run with custom timeframe
    python main_strategy_hub.py --symbol TSLA --interval 5m --days 30
"""

import argparse
import json
import logging
import os
import sys
import time
import schedule
import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
import yaml
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Add project root to path
project_root = str(Path(__file__).parent.absolute())
if project_root not in sys.path:
    sys.path.append(project_root)

from utils.strategy_executor import StrategyExecutor
from utils.unified_notifier import NotificationConfig
from utils.preset_strategy_prompt import get_strategy_preset
from utils.notifier_dispatcher import NotifierDispatcher
from utils.feishu_notifier import FeishuNotifier
from utils.telegram_notifier import TelegramNotifier
from utils.deepseek_client import DeepSeekClient
from utils.ai_judger import AIJudger
from utils.ai_daily_reporter import AIDailyReporter
from utils.ai_knowledge_base import AIKnowledgeBase

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("strategy_hub.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("StrategyHub")

class MainStrategyHub:
    """
    主策略调度中心
    负责根据市场时间调度不同功能:
    - 市场开盘时执行交易策略并发送信号
    - 市场收盘后生成AI日报总结
    """
    
    def __init__(self, symbols=None, use_ai_judger=True, knowledge_base_dir="data/knowledge_base"):
        """
        初始化主策略调度中心
        
        Args:
            symbols: 监控的股票代码列表
            use_ai_judger: 是否使用AI交易决策
            knowledge_base_dir: 知识库数据目录
        """
        self.symbols = symbols or ["SPY", "QQQ", "AAPL", "MSFT", "META", "NVDA", "GOOGL", "AMZN", "TSLA"]
        self.use_ai_judger = use_ai_judger
        self.knowledge_base_dir = knowledge_base_dir
        
        # 加载API密钥
        self.deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")
        if not self.deepseek_api_key:
            logger.warning("DeepSeek API密钥未设置，AI功能将不可用")
        
        # 初始化组件
        self._init_components()
        
        # 当日信号历史
        self.daily_signals = []
        
        # 标记市场状态
        self.market_open = False
        
        # 设置调度器
        self._setup_scheduler()
    
    def _init_components(self):
        """初始化各组件"""
        try:
            # Initialize notification systems
            self.feishu_notifier = None
            self.telegram_notifier = None
            
            # 初始化飞书通知器 (if webhook is available)
            feishu_webhook = os.getenv("FEISHU_WEBHOOK")
            if feishu_webhook:
                try:
                    self.feishu_notifier = FeishuNotifier()
                    logger.info("飞书通知器初始化成功")
                except Exception as e:
                    logger.warning(f"初始化飞书通知器失败: {str(e)}")
            
            # 初始化Telegram通知器
            telegram_token = os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("TELEGRAM_TOKEN")
            telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")
            telegram_enabled = os.getenv("TELEGRAM_ENABLED", "false").lower() == "true"
            
            if telegram_enabled and telegram_token and telegram_chat_id:
                try:
                    self.telegram_notifier = TelegramNotifier(token=telegram_token)
                    logger.info("Telegram通知器初始化成功")
                except Exception as e:
                    logger.error(f"初始化Telegram通知器失败: {str(e)}")
            
            # 确保至少有一个通知系统可用
            if not self.feishu_notifier and not self.telegram_notifier:
                logger.warning("没有可用的通知系统! 请设置FEISHU_WEBHOOK或TELEGRAM_BOT_TOKEN环境变量")
            
            # 初始化通知调度器
            self.notifier_dispatcher = NotifierDispatcher(
                feishu_notifier=self.feishu_notifier,
                telegram_notifier=self.telegram_notifier
            )
            
            # 初始化知识库
            self.knowledge_base = AIKnowledgeBase(data_dir=self.knowledge_base_dir)
            logger.info("已初始化AI知识库")
            
            # 初始化DeepSeek客户端(如果有API密钥)
            if self.deepseek_api_key:
                self.deepseek_client = DeepSeekClient(api_key=self.deepseek_api_key)
                
                # 初始化AI判断器
                if self.use_ai_judger:
                    self.ai_judger = AIJudger(deepseek_client=self.deepseek_client)
                
                # 初始化每日报告生成器
                self.daily_reporter = AIDailyReporter(
                    deepseek_client=self.deepseek_client,
                    notifier_dispatcher=self.notifier_dispatcher,
                    knowledge_base=self.knowledge_base
                )
            
            # 初始化策略执行器
            self.strategy_executor = StrategyExecutor(
                symbols=self.symbols,
                use_ai_judger=self.use_ai_judger,
                deepseek_api_key=self.deepseek_api_key
            )
            
            logger.info("所有组件初始化完成")
            
        except Exception as e:
            logger.error(f"组件初始化失败: {str(e)}")
            raise
    
    def _setup_scheduler(self):
        """设置定时任务"""
        # 美东时间9:30 (市场开盘)
        schedule.every().monday.at("09:30").do(self.market_open_handler)
        schedule.every().tuesday.at("09:30").do(self.market_open_handler)
        schedule.every().wednesday.at("09:30").do(self.market_open_handler)
        schedule.every().thursday.at("09:30").do(self.market_open_handler)
        schedule.every().friday.at("09:30").do(self.market_open_handler)
        
        # 美东时间16:00 (市场收盘)
        schedule.every().monday.at("16:00").do(self.market_close_handler)
        schedule.every().tuesday.at("16:00").do(self.market_close_handler)
        schedule.every().wednesday.at("16:00").do(self.market_close_handler)
        schedule.every().thursday.at("16:00").do(self.market_close_handler)
        schedule.every().friday.at("16:00").do(self.market_close_handler)
        
        # 每5分钟执行一次策略
        schedule.every(5).minutes.do(self.execute_strategies)
        
        logger.info("调度任务设置完成")
    
    def market_open_handler(self):
        """市场开盘处理程序"""
        logger.info("市场开盘，开始执行交易策略")
        self.market_open = True
        
        # 清空当日信号记录
        self.daily_signals = []
        
        # 发送市场开盘通知
        self.notifier_dispatcher._send_notification(
            title="🔔 市场开盘",
            content=f"市场已开盘，开始监控 {len(self.symbols)} 个交易标的",
            fig=None
        )
        
        # 启动策略执行器
        self.strategy_executor.start()
    
    def market_close_handler(self):
        """市场收盘处理程序"""
        logger.info("市场收盘，停止执行交易策略")
        self.market_open = False
        
        # 停止策略执行器
        self.strategy_executor.stop()
        
        # 获取市场数据
        market_data = self.daily_reporter.get_market_data()
        
        # 发送每日报告
        if hasattr(self, 'daily_reporter'):
            try:
                logger.info("生成并发送每日报告")
                self.daily_reporter.send_daily_report(self.daily_signals, market_data)
            except Exception as e:
                logger.error(f"发送每日报告失败: {str(e)}")
    
    def execute_strategies(self):
        """执行交易策略"""
        if not self.market_open:
            return
        
        try:
            # 执行所有标的的策略
            results = self.strategy_executor.batch_execute(self.symbols)
            
            # 记录信号
            for symbol, result in results.items():
                if result.get("status") == "success" and "signal" in result:
                    signal = result["signal"]
                    
                    # 只添加推荐通知的信号
                    if signal.get("notify", "否") == "是":
                        self.daily_signals.append(signal)
                        
                        # 智能通知过滤器：只推送高置信度高评级信号
                        should_notify = (
                            (signal.get("action") == "Call" and float(signal.get("confidence", 0)) > 0.7 and 
                             signal.get("ai_rating") in ["A", "B"]) or
                            (signal.get("action") == "Put" and float(signal.get("confidence", 0)) > 0.8 and 
                             signal.get("ai_rating") in ["A", "B"])
                        )
                        
                        if should_notify:
                            # 保存到知识库
                            self.knowledge_base.save_signals([signal])
            
            logger.info(f"执行了 {len(self.symbols)} 个标的的策略, 生成 {len(self.daily_signals)} 个信号")
            
        except Exception as e:
            logger.error(f"执行策略失败: {str(e)}")
    
    def is_market_open(self):
        """检查当前是否是市场交易时间"""
        now = datetime.datetime.now()
        current_time = now.time()
        current_day = now.weekday()
        
        # 周一至周五
        if current_day < 5:
            # 9:30 - 16:00 (美东时间)
            market_open_time = datetime.time(9, 30)
            market_close_time = datetime.time(16, 0)
            
            return market_open_time <= current_time <= market_close_time
        
        return False
    
    def run(self):
        """运行主策略调度中心"""
        logger.info("启动主策略调度中心")
        
        # 检查当前市场状态
        if self.is_market_open():
            logger.info("当前是市场交易时间，自动启动策略执行")
            self.market_open_handler()
        else:
            logger.info("当前是非交易时间，等待市场开盘")
        
        # 主循环
        try:
            while True:
                schedule.run_pending()
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("接收到中断信号，正在关闭...")
            if self.market_open:
                self.strategy_executor.stop()
            logger.info("已关闭策略执行器")

def main():
    """主函数"""
    try:
        # 初始化主调度中心
        hub = MainStrategyHub(use_ai_judger=True)
        
        # 启动运行
        hub.run()
        
    except Exception as e:
        logger.error(f"主程序异常: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 