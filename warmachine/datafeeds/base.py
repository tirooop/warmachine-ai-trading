"""
基础数据源类
定义所有数据源必须实现的接口
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
import asyncio
import logging

logger = logging.getLogger(__name__)

class BaseDataFeed(ABC):
    """基础数据源类"""
    
    def __init__(self, config: Dict[str, Any]):
        """初始化数据源
        
        Args:
            config: 配置字典
        """
        self.config = config
        self.running = False
        self._tasks: List[asyncio.Task] = []
        
    @abstractmethod
    async def connect(self) -> bool:
        """连接到数据源
        
        Returns:
            bool: 连接是否成功
        """
        pass
        
    @abstractmethod
    async def disconnect(self) -> None:
        """断开与数据源的连接"""
        pass
        
    @abstractmethod
    async def subscribe(self, symbols: List[str]) -> bool:
        """订阅指定的交易对
        
        Args:
            symbols: 要订阅的交易对列表
            
        Returns:
            bool: 订阅是否成功
        """
        pass
        
    @abstractmethod
    async def unsubscribe(self, symbols: List[str]) -> bool:
        """取消订阅指定的交易对
        
        Args:
            symbols: 要取消订阅的交易对列表
            
        Returns:
            bool: 取消订阅是否成功
        """
        pass
        
    @abstractmethod
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
        pass
        
    async def start(self) -> None:
        """启动数据源"""
        if not self.running:
            self.running = True
            await self.connect()
            
    async def stop(self) -> None:
        """停止数据源"""
        if self.running:
            self.running = False
            await self.disconnect()
            for task in self._tasks:
                task.cancel()
            self._tasks.clear() 