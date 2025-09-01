"""
市场数据中心
负责管理和协调多个数据源
"""

from typing import Dict, List, Optional, Any
import asyncio
import logging
from .base import BaseDataFeed
from .polygon import PolygonDataFeed
from .tradier import TradierDataFeed
from .binance import BinanceDataFeed

logger = logging.getLogger(__name__)

class MarketDataHub:
    """市场数据中心"""
    
    def __init__(self, config: Dict[str, Any]):
        """初始化市场数据中心
        
        Args:
            config: 配置字典
        """
        self.config = config
        self.feeds: Dict[str, BaseDataFeed] = {}
        self.running = False
        self._tasks: List[asyncio.Task] = []
        
    def _init_feeds(self) -> None:
        """初始化数据源"""
        # 初始化Polygon数据源
        if self.config.get('polygon', {}).get('enabled', False):
            self.feeds['polygon'] = PolygonDataFeed(self.config['polygon'])
            
        # 初始化Tradier数据源
        if self.config.get('tradier', {}).get('enabled', False):
            self.feeds['tradier'] = TradierDataFeed(self.config['tradier'])
            
        # 初始化Binance数据源
        if self.config.get('binance', {}).get('enabled', False):
            self.feeds['binance'] = BinanceDataFeed(self.config['binance'])
            
    async def start(self) -> None:
        """启动市场数据中心"""
        if not self.running:
            self.running = True
            self._init_feeds()
            
            # 启动所有数据源
            for feed in self.feeds.values():
                await feed.start()
                
    async def stop(self) -> None:
        """停止市场数据中心"""
        if self.running:
            self.running = False
            
            # 停止所有数据源
            for feed in self.feeds.values():
                await feed.stop()
                
            # 取消所有任务
            for task in self._tasks:
                task.cancel()
            self._tasks.clear()
            
    async def subscribe(self, symbols: List[str]) -> bool:
        """订阅指定的交易对
        
        Args:
            symbols: 要订阅的交易对列表
            
        Returns:
            bool: 订阅是否成功
        """
        success = True
        for feed in self.feeds.values():
            if not await feed.subscribe(symbols):
                success = False
        return success
        
    async def unsubscribe(self, symbols: List[str]) -> bool:
        """取消订阅指定的交易对
        
        Args:
            symbols: 要取消订阅的交易对列表
            
        Returns:
            bool: 取消订阅是否成功
        """
        success = True
        for feed in self.feeds.values():
            if not await feed.unsubscribe(symbols):
                success = False
        return success
        
    async def get_historical_data(self,
                                symbol: str,
                                timeframe: str,
                                start_time: Optional[str] = None,
                                end_time: Optional[str] = None) -> Dict[str, Any]:
        """获取历史数据
        
        Args:
            symbol: 交易对
            timeframe: 时间周期
            start_time: 开始时间
            end_time: 结束时间
            
        Returns:
            Dict[str, Any]: 历史数据
        """
        # 优先使用Polygon数据源
        if 'polygon' in self.feeds:
            data = await self.feeds['polygon'].get_historical_data(
                symbol, timeframe, start_time, end_time
            )
            if data:
                return data
                
        # 如果Polygon数据源失败，尝试使用Tradier数据源
        if 'tradier' in self.feeds:
            data = await self.feeds['tradier'].get_historical_data(
                symbol, timeframe, start_time, end_time
            )
            if data:
                return data
                
        # 如果Tradier数据源失败，尝试使用Binance数据源
        if 'binance' in self.feeds:
            data = await self.feeds['binance'].get_historical_data(
                symbol, timeframe, start_time, end_time
            )
            if data:
                return data
                
        return {} 