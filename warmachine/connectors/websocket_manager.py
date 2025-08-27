import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Callable, Optional
import websockets
import aiohttp

class WebSocketManager:
    def __init__(self):
        self.connections: Dict[str, Dict] = {}
        self.callbacks: Dict[str, Callable] = {}
        self.logger = logging.getLogger(__name__)
        
    async def connect(self, provider: str, symbol: str, callback: Callable) -> None:
        """建立WebSocket连接"""
        key = f"{provider}:{symbol}"
        if key in self.connections:
            return
            
        try:
            if provider == "polygon":
                await self._connect_polygon(symbol, callback)
            elif provider == "tradier":
                await self._connect_tradier(symbol, callback)
            else:
                raise ValueError(f"Unsupported provider: {provider}")
                
            self.callbacks[key] = callback
            self.logger.info(f"Connected to {provider} for {symbol}")
            
        except Exception as e:
            self.logger.error(f"Connection failed: {str(e)}")
            raise
            
    async def _connect_polygon(self, symbol: str, callback: Callable) -> None:
        """连接Polygon WebSocket"""
        uri = f"wss://socket.polygon.io/options"
        async with websockets.connect(uri) as websocket:
            # 认证
            await websocket.send(json.dumps({
                "action": "auth",
                "params": "YOUR_POLYGON_API_KEY"
            }))
            
            # 订阅期权数据
            await websocket.send(json.dumps({
                "action": "subscribe",
                "params": f"O.{symbol}"
            }))
            
            while True:
                try:
                    data = await websocket.recv()
                    processed_data = self._process_polygon_data(json.loads(data))
                    await callback(processed_data)
                except Exception as e:
                    self.logger.error(f"Error processing Polygon data: {str(e)}")
                    break
                    
    def _process_polygon_data(self, data: Dict) -> Dict:
        """处理Polygon数据格式"""
        return {
            "symbol": data.get("sym"),
            "strike": data.get("strike"),
            "type": data.get("type"),
            "bid": data.get("bid"),
            "ask": data.get("ask"),
            "volume": data.get("vol"),
            "timestamp": datetime.fromtimestamp(data.get("t", 0) / 1000)
        }
        
    async def disconnect(self, provider: str, symbol: str) -> None:
        """断开WebSocket连接"""
        key = f"{provider}:{symbol}"
        if key in self.connections:
            await self.connections[key]["websocket"].close()
            del self.connections[key]
            del self.callbacks[key]
            
    async def health_check(self) -> None:
        """检查所有连接的健康状态"""
        for key, conn in list(self.connections.items()):
            try:
                if not conn["websocket"].open:
                    provider, symbol = key.split(":")
                    await self.connect(provider, symbol, self.callbacks[key])
            except Exception as e:
                self.logger.error(f"Health check failed for {key}: {str(e)}")
                
    async def start(self) -> None:
        """启动WebSocket管理器"""
        while True:
            await self.health_check()
            await asyncio.sleep(30)  # 每30秒检查一次 