"""
Trading System Integrator - 交易系统集成器
负责集成和管理交易系统的各个组件
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

# Import necessary modules
from ..market_data_hub import MarketDataHub
from ..ai_intelligence_dispatcher import AIIntelligenceDispatcher
from trading.virtual_trading import VirtualTrader
from ..ai_event_pool import AIEventPool
from core.tg_bot.super_commander import SuperCommander

logger = logging.getLogger(__name__)

class TradingSystemIntegrator:
    """交易系统集成器类"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化交易系统集成器
        
        Args:
            config: 配置字典
        """
        self.config = config
        self.market_data_hub = MarketDataHub(config)
        self.intelligence_dispatcher = AIIntelligenceDispatcher(config)
        self.virtual_trader = VirtualTrader(config)
        self.event_pool = AIEventPool()
        logger.info("Trading System Integrator initialized")
    
    async def start(self):
        """启动交易系统"""
        try:
            # 初始化各个组件
            await self.market_data_hub.initialize()
            await self.intelligence_dispatcher.initialize()
            await self.virtual_trader.initialize()
            
            # 注册事件处理器
            self._register_event_handlers()
            
            logger.info("Trading system started successfully")
            
        except Exception as e:
            logger.error(f"Error starting trading system: {str(e)}")
            raise
    
    def _register_event_handlers(self):
        """注册事件处理器"""
        # TODO: 实现事件处理器注册逻辑
        pass
    
    async def stop(self):
        """停止交易系统"""
        try:
            # 停止各个组件
            await self.market_data_hub.stop()
            await self.intelligence_dispatcher.stop()
            await self.virtual_trader.stop()
            
            logger.info("Trading system stopped successfully")
            
        except Exception as e:
            logger.error(f"Error stopping trading system: {str(e)}")
            raise 