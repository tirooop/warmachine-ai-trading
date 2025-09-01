"""
Polygon.io数据源实现
"""

from typing import Dict, List, Optional, Any
import aiohttp
import asyncio
import logging
from .base import BaseDataFeed

logger = logging.getLogger(__name__)

class PolygonDataFeed(BaseDataFeed):
    """Polygon.io数据源实现"""
    
    def __init__(self, config: Dict[str, Any]):
        """初始化Polygon数据源
        
        Args:
            config: 配置字典
        """
        super().__init__(config)
        self.api_key = config.get('api_key', '')
        self.base_url = config.get('base_url', 'https://api.polygon.io')
        self.ws_url = config.get('websocket_url', 'wss://socket.polygon.io')
        self.session: Optional[aiohttp.ClientSession] = None
        self.ws: Optional[aiohttp.ClientWebSocketResponse] = None
        
    async def connect(self) -> bool:
        """连接到Polygon.io
        
        Returns:
            bool: 连接是否成功
        """
        try:
            self.session = aiohttp.ClientSession()
            self.ws = await self.session.ws_connect(
                f"{self.ws_url}/stocks",
                headers={"Authorization": f"Bearer {self.api_key}"}
            )
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Polygon.io: {str(e)}")
            return False
            
    async def disconnect(self) -> None:
        """断开与Polygon.io的连接"""
        if self.ws:
            await self.ws.close()
        if self.session:
            await self.session.close()
            
    async def subscribe(self, symbols: List[str]) -> bool:
        """订阅指定的交易对
        
        Args:
            symbols: 要订阅的交易对列表
            
        Returns:
            bool: 订阅是否成功
        """
        try:
            if not self.ws:
                return False
                
            for symbol in symbols:
                await self.ws.send_json({
                    "action": "subscribe",
                    "params": f"T.{symbol}"
                })
            return True
        except Exception as e:
            logger.error(f"Failed to subscribe to symbols: {str(e)}")
            return False
            
    async def unsubscribe(self, symbols: List[str]) -> bool:
        """取消订阅指定的交易对
        
        Args:
            symbols: 要取消订阅的交易对列表
            
        Returns:
            bool: 取消订阅是否成功
        """
        try:
            if not self.ws:
                return False
                
            for symbol in symbols:
                await self.ws.send_json({
                    "action": "unsubscribe",
                    "params": f"T.{symbol}"
                })
            return True
        except Exception as e:
            logger.error(f"Failed to unsubscribe from symbols: {str(e)}")
            return False
            
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
        try:
            if not self.session:
                return {}
                
            params = {
                "apiKey": self.api_key,
                "timespan": timeframe,
                "symbol": symbol
            }
            
            if start_time:
                params["from"] = start_time
            if end_time:
                params["to"] = end_time
                
            async with self.session.get(
                f"{self.base_url}/v2/aggs/ticker/{symbol}/range/1/{timeframe}",
                params=params
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error(f"Failed to get historical data: {response.status}")
                    return {}
        except Exception as e:
            logger.error(f"Error getting historical data: {str(e)}")
            return {} 