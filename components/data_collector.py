"""
Data Collector Module
"""

import os
import sys
import time
import logging
import asyncio
import aiohttp
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import pandas as pd
import numpy as np

from core.exceptions import DataCollectionError, ValidationError
from core.config import get_config

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join('logs', 'data_collector.log')),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger('DataCollector')


class DataSource(Enum):
    """数据源枚举"""
    POLYGON = "polygon"
    BINANCE = "binance"
    TRADIER = "tradier"
    IBKR = "ibkr"
    GOOGLE_FINANCE = "google_finance"
    ALPHA_VANTAGE = "alpha_vantage"
    FINNHUB = "finnhub"
    YAHOO_FINANCE = "yahoo_finance"


class DataType(Enum):
    """数据类型枚举"""
    STOCK = "stock"
    CRYPTO = "crypto"
    FOREX = "forex"
    OPTIONS = "options"
    FUTURES = "futures"


@dataclass
class MarketData:
    """市场数据类"""
    symbol: str
    timestamp: datetime
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    volume: float
    source: DataSource
    data_type: DataType
    vwap: Optional[float] = None
    additional_data: Optional[Dict[str, Any]] = None


@dataclass
class DataRequest:
    """数据请求类"""
    symbol: str
    data_type: DataType
    source: DataSource
    timeframe: str  # 1m, 5m, 15m, 1h, 1d
    limit: int = 100
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None


class DataCache:
    """数据缓存管理器"""
    
    def __init__(self, max_size: int = 10000):
        self.max_size = max_size
        self.cache: Dict[str, List[MarketData]] = {}
        self.cache_timestamps: Dict[str, datetime] = {}
        self.cache_duration = timedelta(minutes=5)  # 5分钟缓存
    
    def get(self, key: str) -> Optional[List[MarketData]]:
        """获取缓存数据"""
        if key not in self.cache:
            return None
        
        # 检查缓存是否过期
        if datetime.now() - self.cache_timestamps[key] > self.cache_duration:
            del self.cache[key]
            del self.cache_timestamps[key]
            return None
        
        return self.cache[key]
    
    def set(self, key: str, data: List[MarketData]):
        """设置缓存数据"""
        # 如果缓存已满，删除最旧的数据
        if len(self.cache) >= self.max_size:
            oldest_key = min(self.cache_timestamps.keys(), 
                           key=lambda k: self.cache_timestamps[k])
            del self.cache[oldest_key]
            del self.cache_timestamps[oldest_key]
        
        self.cache[key] = data
        self.cache_timestamps[key] = datetime.now()
    
    def clear(self):
        """清空缓存"""
        self.cache.clear()
        self.cache_timestamps.clear()
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        return {
            "cache_size": len(self.cache),
            "max_size": self.max_size,
            "cache_duration_minutes": self.cache_duration.total_seconds() / 60,
            "keys": list(self.cache.keys())
        }


class PolygonDataCollector:
    """Polygon数据收集器"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.polygon.io"
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def get_stock_data(self, symbol: str, timeframe: str, limit: int = 100) -> List[MarketData]:
        """获取股票数据"""
        try:
            url = f"{self.base_url}/v2/aggs/ticker/{symbol}/range/1/{timeframe}/2024-01-01/2024-12-31"
            params = {
                "apiKey": self.api_key,
                "limit": limit,
                "adjusted": "true"
            }
            
            async with self.session.get(url, params=params) as response:
                if response.status != 200:
                    raise DataCollectionError(f"Polygon API错误: {response.status}")
                
                data = await response.json()
                
                if data.get("status") != "OK":
                    raise DataCollectionError(f"Polygon API返回错误: {data.get('error')}")
                
                results = data.get("results", [])
                market_data = []
                
                for result in results:
                    market_data.append(MarketData(
                        symbol=symbol,
                        timestamp=datetime.fromtimestamp(result["t"] / 1000),
                        open_price=result["o"],
                        high_price=result["h"],
                        low_price=result["l"],
                        close_price=result["c"],
                        volume=result["v"],
                        source=DataSource.POLYGON,
                        data_type=DataType.STOCK,
                        vwap=result.get("vw")
                    ))
                
                return market_data
        
        except Exception as e:
            logger.error(f"获取Polygon股票数据失败: {e}")
            raise DataCollectionError(f"获取Polygon股票数据失败: {e}")


class BinanceDataCollector:
    """Binance数据收集器"""
    
    def __init__(self):
        self.base_url = "https://api.binance.com"
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def get_crypto_data(self, symbol: str, interval: str, limit: int = 100) -> List[MarketData]:
        """获取加密货币数据"""
        try:
            url = f"{self.base_url}/api/v3/klines"
            params = {
                "symbol": symbol,
                "interval": interval,
                "limit": limit
            }
            
            async with self.session.get(url, params=params) as response:
                if response.status != 200:
                    raise DataCollectionError(f"Binance API错误: {response.status}")
                
                data = await response.json()
                market_data = []
                
                for kline in data:
                    market_data.append(MarketData(
                        symbol=symbol,
                        timestamp=datetime.fromtimestamp(kline[0] / 1000),
                        open_price=float(kline[1]),
                        high_price=float(kline[2]),
                        low_price=float(kline[3]),
                        close_price=float(kline[4]),
                        volume=float(kline[5]),
                        source=DataSource.BINANCE,
                        data_type=DataType.CRYPTO
                    ))
                
                return market_data
        
        except Exception as e:
            logger.error(f"获取Binance加密货币数据失败: {e}")
            raise DataCollectionError(f"获取Binance加密货币数据失败: {e}")


class YahooFinanceDataCollector:
    """Yahoo Finance数据收集器"""
    
    def __init__(self):
        self.base_url = "https://query1.finance.yahoo.com"
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def get_stock_data(self, symbol: str, period: str = "1y", interval: str = "1d") -> List[MarketData]:
        """获取股票数据"""
        try:
            url = f"{self.base_url}/v8/finance/chart/{symbol}"
            params = {
                "period1": int((datetime.now() - timedelta(days=365)).timestamp()),
                "period2": int(datetime.now().timestamp()),
                "interval": interval,
                "includePrePost": "false"
            }
            
            async with self.session.get(url, params=params) as response:
                if response.status != 200:
                    raise DataCollectionError(f"Yahoo Finance API错误: {response.status}")
                
                data = await response.json()
                chart = data.get("chart", {})
                result = chart.get("result", [{}])[0]
                
                if "timestamp" not in result:
                    raise DataCollectionError("Yahoo Finance数据格式错误")
                
                timestamps = result["timestamp"]
                quote = result["indicators"]["quote"][0]
                
                market_data = []
                for i, timestamp in enumerate(timestamps):
                    market_data.append(MarketData(
                        symbol=symbol,
                        timestamp=datetime.fromtimestamp(timestamp),
                        open_price=quote["open"][i] if quote["open"][i] else 0,
                        high_price=quote["high"][i] if quote["high"][i] else 0,
                        low_price=quote["low"][i] if quote["low"][i] else 0,
                        close_price=quote["close"][i] if quote["close"][i] else 0,
                        volume=quote["volume"][i] if quote["volume"][i] else 0,
                        source=DataSource.YAHOO_FINANCE,
                        data_type=DataType.STOCK
                    ))
                
                return market_data
        
        except Exception as e:
            logger.error(f"获取Yahoo Finance股票数据失败: {e}")
            raise DataCollectionError(f"获取Yahoo Finance股票数据失败: {e}")


class DataCollectorManager:
    """数据收集管理器"""
    
    def __init__(self):
        self.config = get_config()
        self.cache = DataCache()
        self.collectors: Dict[DataSource, Any] = {}
        self.running = False
        self.collection_tasks: List[asyncio.Task] = []
        
        # 初始化数据收集器
        self._initialize_collectors()
    
    def _initialize_collectors(self):
        """初始化数据收集器"""
        try:
            # 初始化Polygon收集器
            if hasattr(self.config, 'polygon_api_key') and self.config.polygon_api_key:
                self.collectors[DataSource.POLYGON] = PolygonDataCollector(self.config.polygon_api_key)
            
            # 初始化Binance收集器
            self.collectors[DataSource.BINANCE] = BinanceDataCollector()
            
            # 初始化Yahoo Finance收集器
            self.collectors[DataSource.YAHOO_FINANCE] = YahooFinanceDataCollector()
            
            logger.info(f"初始化了 {len(self.collectors)} 个数据收集器")
        
        except Exception as e:
            logger.error(f"初始化数据收集器失败: {e}")
            raise DataCollectionError(f"初始化数据收集器失败: {e}")
    
    async def collect_data(self, request: DataRequest) -> List[MarketData]:
        """收集数据"""
        try:
            # 检查缓存
            cache_key = f"{request.symbol}_{request.source.value}_{request.timeframe}"
            cached_data = self.cache.get(cache_key)
            
            if cached_data:
                logger.info(f"从缓存获取数据: {cache_key}")
                return cached_data
            
            # 从数据源收集数据
            collector = self.collectors.get(request.source)
            if not collector:
                raise DataCollectionError(f"未找到数据源: {request.source.value}")
            
            async with collector as col:
                if request.data_type == DataType.STOCK:
                    if request.source == DataSource.POLYGON:
                        data = await col.get_stock_data(request.symbol, request.timeframe, request.limit)
                    elif request.source == DataSource.YAHOO_FINANCE:
                        data = await col.get_stock_data(request.symbol)
                    else:
                        raise DataCollectionError(f"不支持的数据源: {request.source.value}")
                
                elif request.data_type == DataType.CRYPTO:
                    if request.source == DataSource.BINANCE:
                        data = await col.get_crypto_data(request.symbol, request.timeframe, request.limit)
                    else:
                        raise DataCollectionError(f"不支持的数据源: {request.source.value}")
                
                else:
                    raise DataCollectionError(f"不支持的数据类型: {request.data_type.value}")
            
            # 缓存数据
            self.cache.set(cache_key, data)
            
            logger.info(f"成功收集数据: {request.symbol} ({len(data)} 条记录)")
            return data
        
        except Exception as e:
            logger.error(f"收集数据失败: {e}")
            raise DataCollectionError(f"收集数据失败: {e}")
    
    async def collect_multiple_symbols(self, requests: List[DataRequest]) -> Dict[str, List[MarketData]]:
        """收集多个股票的数据"""
        try:
            tasks = []
            for request in requests:
                task = asyncio.create_task(self.collect_data(request))
                tasks.append((request.symbol, task))
            
            results = {}
            for symbol, task in tasks:
                try:
                    data = await task
                    results[symbol] = data
                except Exception as e:
                    logger.error(f"收集 {symbol} 数据失败: {e}")
                    results[symbol] = []
            
            return results
        
        except Exception as e:
            logger.error(f"批量收集数据失败: {e}")
            raise DataCollectionError(f"批量收集数据失败: {e}")
    
    async def start_real_time_collection(self, symbols: List[str], interval: int = 60):
        """启动实时数据收集"""
        self.running = True
        logger.info(f"启动实时数据收集: {symbols}")
        
        try:
            while self.running:
                requests = []
                for symbol in symbols:
                    # 创建数据请求
                    request = DataRequest(
                        symbol=symbol,
                        data_type=DataType.STOCK,
                        source=DataSource.YAHOO_FINANCE,  # 使用免费数据源
                        timeframe="1d",
                        limit=100
                    )
                    requests.append(request)
                
                # 收集数据
                await self.collect_multiple_symbols(requests)
                
                # 等待下次收集
                await asyncio.sleep(interval)
        
        except Exception as e:
            logger.error(f"实时数据收集失败: {e}")
            self.running = False
    
    async def stop_real_time_collection(self):
        """停止实时数据收集"""
        self.running = False
        logger.info("停止实时数据收集")
        
        # 取消所有任务
        for task in self.collection_tasks:
            task.cancel()
        
        self.collection_tasks.clear()
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """获取收集统计信息"""
        cache_stats = self.cache.get_cache_stats()
        
        return {
            "running": self.running,
            "active_collectors": len(self.collectors),
            "cache_stats": cache_stats,
            "collection_tasks": len(self.collection_tasks)
        }


class DataCollector:
    """数据收集器主类"""
    
    def __init__(self):
        self.manager = DataCollectorManager()
        self.running = False
        logger.info("数据收集器初始化完成")
    
    async def start(self):
        """启动数据收集"""
        self.running = True
        logger.info("数据收集器启动")
        
        try:
            # 启动实时数据收集
            symbols = ["AAPL", "TSLA", "MSFT", "GOOGL", "AMZN"]
            await self.manager.start_real_time_collection(symbols, interval=300)  # 5分钟间隔
        
        except Exception as e:
            logger.error(f"数据收集出错: {e}")
            self.running = False
    
    async def stop(self):
        """停止数据收集"""
        self.running = False
        await self.manager.stop_real_time_collection()
        logger.info("数据收集器停止")
    
    async def collect_data(self, symbol: str, data_type: DataType = DataType.STOCK, 
                          source: DataSource = DataSource.YAHOO_FINANCE) -> List[MarketData]:
        """收集指定股票的数据"""
        request = DataRequest(
            symbol=symbol,
            data_type=data_type,
            source=source,
            timeframe="1d",
            limit=100
        )
        
        return await self.manager.collect_data(request)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return self.manager.get_collection_stats()


if __name__ == "__main__":
    async def main():
        collector = DataCollector()
        try:
            await collector.start()
        except KeyboardInterrupt:
            await collector.stop()
            logger.info("数据收集器已停止")
    
    asyncio.run(main()) 