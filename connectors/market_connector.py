"""
真实市场数据连接器

连接并统一多个交易所和数据提供商的API，提供标准化的市场数据接口。
支持股票、期权、加密货币和外汇等多个市场。
"""

import os
import sys
import logging
import time
import json
import traceback
import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Union, Callable
from concurrent.futures import ThreadPoolExecutor
import asyncio
import aiohttp
import websockets

# 导入Tradier期权适配器
from .tradier_options import TradierOptionsAdapter

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MarketDataConnector:
    """统一的市场数据连接器，整合多个数据源"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化市场数据连接器
        
        Args:
            config: 配置字典，包含各数据源的API密钥和设置
        """
        self.config = config
        self.api_keys = self._load_api_keys()
        self.connectors = {}
        self.cache_dir = "data/market/cache"
        
        # 确保缓存目录存在
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # 初始化所有可用的连接器
        self._initialize_connectors()
        
        logger.info(f"市场数据连接器初始化完成，已加载 {len(self.connectors)} 个数据源")
    
    def _load_api_keys(self) -> Dict[str, str]:
        """加载API密钥"""
        return {
            "alpha_vantage": os.environ.get("ALPHA_VANTAGE_API_KEY", self.config.get("alpha_vantage_key", "")),
            "finnhub": os.environ.get("FINNHUB_API_KEY", self.config.get("finnhub_key", "")),
            "binance": os.environ.get("BINANCE_API_KEY", self.config.get("binance_key", "")),
            "binance_secret": os.environ.get("BINANCE_SECRET_KEY", self.config.get("binance_secret", "")),
            "coinbase": os.environ.get("COINBASE_API_KEY", self.config.get("coinbase_key", "")),
            "coinbase_secret": os.environ.get("COINBASE_SECRET_KEY", self.config.get("coinbase_secret", "")),
            "tradier": os.environ.get("TRADIER_API_KEY", self.config.get("tradier_key", "")),
            "iex": os.environ.get("IEX_API_KEY", self.config.get("iex_key", "")),
            "polygon": os.environ.get("POLYGON_API_KEY", self.config.get("polygon_key", "")),
        }
    
    def _initialize_connectors(self):
        """初始化所有数据源连接器"""
        # 加载不同类型的市场数据连接器
        self._init_stock_connectors()
        self._init_crypto_connectors()
        self._init_options_connectors()
        self._init_forex_connectors()
    
    def _init_stock_connectors(self):
        """初始化股票市场数据连接器"""
        # Alpha Vantage
        if self.api_keys.get("alpha_vantage"):
            try:
                self.connectors["alpha_vantage"] = AlphaVantageConnector(self.api_keys["alpha_vantage"])
                logger.info("Alpha Vantage 连接器初始化成功")
            except Exception as e:
                logger.error(f"Alpha Vantage 连接器初始化失败: {str(e)}")
        
        # Finnhub
        if self.api_keys.get("finnhub"):
            try:
                self.connectors["finnhub"] = FinnhubConnector(self.api_keys["finnhub"])
                logger.info("Finnhub 连接器初始化成功")
            except Exception as e:
                logger.error(f"Finnhub 连接器初始化失败: {str(e)}")
        
        # Polygon.io
        if self.api_keys.get("polygon"):
            try:
                self.connectors["polygon"] = PolygonConnector(self.api_keys["polygon"])
                logger.info("Polygon 连接器初始化成功")
            except Exception as e:
                logger.error(f"Polygon 连接器初始化失败: {str(e)}")
    
    def _init_crypto_connectors(self):
        """初始化加密货币市场数据连接器"""
        # Binance
        if self.api_keys.get("binance") and self.api_keys.get("binance_secret"):
            try:
                self.connectors["binance"] = BinanceConnector(
                    api_key=self.api_keys["binance"],
                    api_secret=self.api_keys["binance_secret"]
                )
                logger.info("Binance 连接器初始化成功")
            except Exception as e:
                logger.error(f"Binance 连接器初始化失败: {str(e)}")
        
        # Coinbase Pro
        if self.api_keys.get("coinbase") and self.api_keys.get("coinbase_secret"):
            try:
                self.connectors["coinbase"] = CoinbaseConnector(
                    api_key=self.api_keys["coinbase"], 
                    api_secret=self.api_keys["coinbase_secret"]
                )
                logger.info("Coinbase 连接器初始化成功")
            except Exception as e:
                logger.error(f"Coinbase 连接器初始化失败: {str(e)}")
    
    def _init_options_connectors(self):
        """初始化期权市场数据连接器"""
        # Tradier
        if self.api_keys.get("tradier"):
            try:
                self.connectors["tradier"] = TradierOptionsAdapter(
                    api_key=self.api_keys["tradier"],
                    cache_dir=os.path.join(self.cache_dir, "options")
                )
                logger.info("Tradier期权数据适配器初始化成功")
            except Exception as e:
                logger.error(f"Tradier期权数据适配器初始化失败: {str(e)}")
    
    def _init_forex_connectors(self):
        """初始化外汇市场数据连接器"""
        # 可以添加外汇数据源如OANDA等
        pass
    
    def get_best_connector(self, market_type: str, data_type: str) -> Optional[Any]:
        """
        根据市场和数据类型获取最合适的数据连接器
        
        Args:
            market_type: 市场类型 (stock, crypto, option, forex)
            data_type: 数据类型 (price, orderbook, trades, etc.)
            
        Returns:
            适合的连接器对象
        """
        if market_type == "stock":
            if data_type in ["price", "ohlc"]:
                for name in ["polygon", "alpha_vantage", "finnhub"]:
                    if name in self.connectors:
                        return self.connectors[name]
            
            elif data_type in ["orderbook", "level2"]:
                for name in ["iex", "polygon"]:
                    if name in self.connectors:
                        return self.connectors[name]
        
        elif market_type == "crypto":
            if data_type in ["price", "ohlc", "orderbook", "trades"]:
                for name in ["binance", "coinbase"]:
                    if name in self.connectors:
                        return self.connectors[name]
        
        elif market_type == "option":
            if data_type in ["chain", "prices"]:
                if "tradier" in self.connectors:
                    return self.connectors["tradier"]
        
        return None
    
    def get_orderbook(self, symbol: str, market_type: str = "stock", depth: int = 10) -> Dict[str, Any]:
        """
        获取指定交易对的订单簿数据
        
        Args:
            symbol: 交易对符号
            market_type: 市场类型 (stock, crypto)
            depth: 订单簿深度
            
        Returns:
            订单簿数据，包含买单和卖单
        """
        connector = self.get_best_connector(market_type, "orderbook")
        if connector:
            try:
                return connector.get_orderbook(symbol, depth)
            except Exception as e:
                logger.error(f"获取 {symbol} 订单簿失败: {str(e)}")
        
        # 没有可用连接器或获取失败时返回空数据
        return {
            "timestamp": datetime.now().isoformat(),
            "symbol": symbol,
            "bids": [],
            "asks": []
        }
    
    def get_large_trades(self, symbol: str, market_type: str = "stock", min_value: float = 100000) -> List[Dict[str, Any]]:
        """
        获取大额交易数据
        
        Args:
            symbol: 交易对符号
            market_type: 市场类型 (stock, crypto)
            min_value: 最小交易价值（美元）
            
        Returns:
            大额交易列表
        """
        connector = self.get_best_connector(market_type, "trades")
        if connector:
            try:
                return connector.get_large_trades(symbol, min_value)
            except Exception as e:
                logger.error(f"获取 {symbol} 大额交易失败: {str(e)}")
        
        # 没有可用连接器或获取失败时返回空列表
        return []
    
    def calculate_order_imbalance(self, symbol: str, market_type: str = "stock") -> float:
        """
        计算订单簿不平衡指标
        
        Args:
            symbol: 交易对符号
            market_type: 市场类型 (stock, crypto)
            
        Returns:
            不平衡指标值，范围 [-1, 1]
        """
        orderbook = self.get_orderbook(symbol, market_type)
        
        bid_volume = sum(bid[1] for bid in orderbook.get("bids", []))
        ask_volume = sum(ask[1] for ask in orderbook.get("asks", []))
        
        total_volume = bid_volume + ask_volume
        if total_volume > 0:
            imbalance = (bid_volume - ask_volume) / total_volume
        else:
            imbalance = 0
        
        return imbalance
    
    def get_whale_activity(self, symbol: str, market_type: str = "stock", lookback: int = 24) -> Dict[str, Any]:
        """
        分析近期大户活动
        
        Args:
            symbol: 交易对符号
            market_type: 市场类型 (stock, crypto)
            lookback: 回溯时间（小时）
            
        Returns:
            大户活动分析结果
        """
        large_trades = self.get_large_trades(symbol, market_type)
        
        # 过滤最近时间段内的交易
        cutoff_time = (datetime.now() - timedelta(hours=lookback)).isoformat()
        recent_trades = [trade for trade in large_trades if trade["timestamp"] >= cutoff_time]
        
        # 计算买入和卖出数量
        buys = [trade for trade in recent_trades if trade["side"] == "buy"]
        sells = [trade for trade in recent_trades if trade["side"] == "sell"]
        
        buy_volume = sum(trade["volume"] for trade in buys)
        sell_volume = sum(trade["volume"] for trade in sells)
        
        # 计算平均价格
        buy_value = sum(trade["price"] * trade["volume"] for trade in buys)
        sell_value = sum(trade["price"] * trade["volume"] for trade in sells)
        
        avg_buy_price = buy_value / buy_volume if buy_volume > 0 else 0
        avg_sell_price = sell_value / sell_volume if sell_volume > 0 else 0
        
        # 确定主导方向
        if len(buys) >= 3 and buy_volume > 2 * sell_volume:
            direction = "accumulation"
        elif len(sells) >= 3 and sell_volume > 2 * buy_volume:
            direction = "distribution"
        else:
            direction = "neutral"
        
        return {
            "symbol": symbol,
            "buys": len(buys),
            "sells": len(sells),
            "buy_volume": buy_volume,
            "sell_volume": sell_volume,
            "avg_buy_price": avg_buy_price,
            "avg_sell_price": avg_sell_price,
            "direction": direction,
            "lookback_hours": lookback
        }

    def get_options_chain(self, symbol: str, expiration: str, **filters) -> Dict[str, Any]:
        """
        获取期权链数据
        
        Args:
            symbol: 标的代码
            expiration: 到期日 (YYYY-MM-DD)
            **filters: 筛选条件
                - moneyness_range: 实值/虚值范围 (默认0.1)
                - max_strikes: 每侧最大行权价数量 (默认20)
                - min_volume: 最小成交量
                - min_open_interest: 最小持仓量
                
        Returns:
            期权链数据，包含看涨和看跌期权
        """
        connector = self.get_best_connector("option", "chain")
        if connector:
            try:
                return connector.get_chain(symbol, expiration, **filters)
            except Exception as e:
                logger.error(f"获取 {symbol} 期权链失败: {str(e)}")
        
        # 没有可用连接器或获取失败时返回空数据
        return {
            "calls": [],
            "puts": [],
            "timestamp": datetime.now().isoformat(),
            "underlying_price": 0.0
        }


# 下面是各个特定数据源连接器的实现

class AlphaVantageConnector:
    """Alpha Vantage API连接器"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://www.alphavantage.co/query"
    
    def get_price(self, symbol: str) -> Dict[str, Any]:
        """获取实时价格"""
        params = {
            "function": "GLOBAL_QUOTE",
            "symbol": symbol,
            "apikey": self.api_key
        }
        
        response = requests.get(self.base_url, params=params)
        data = response.json()
        
        if "Global Quote" in data:
            quote = data["Global Quote"]
            return {
                "symbol": symbol,
                "price": float(quote.get("05. price", 0)),
                "change": float(quote.get("09. change", 0)),
                "change_percent": quote.get("10. change percent", "0%"),
                "volume": int(quote.get("06. volume", 0)),
                "timestamp": datetime.now().isoformat()
            }
        
        return {
            "symbol": symbol,
            "error": "No data available",
            "timestamp": datetime.now().isoformat()
        }
    
    def get_intraday(self, symbol: str, interval: str = "1min") -> List[Dict[str, Any]]:
        """获取日内K线数据"""
        params = {
            "function": "TIME_SERIES_INTRADAY",
            "symbol": symbol,
            "interval": interval,
            "apikey": self.api_key,
            "outputsize": "compact"
        }
        
        response = requests.get(self.base_url, params=params)
        data = response.json()
        
        key = f"Time Series ({interval})"
        if key in data:
            time_series = data[key]
            return [
                {
                    "timestamp": timestamp,
                    "open": float(values["1. open"]),
                    "high": float(values["2. high"]),
                    "low": float(values["3. low"]),
                    "close": float(values["4. close"]),
                    "volume": int(values["5. volume"])
                }
                for timestamp, values in time_series.items()
            ]
        
        return []


class BinanceConnector:
    """币安API连接器"""
    
    def __init__(self, api_key: str, api_secret: str):
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = "https://api.binance.com/api/v3"
    
    def get_orderbook(self, symbol: str, depth: int = 10) -> Dict[str, Any]:
        """获取订单簿"""
        url = f"{self.base_url}/depth"
        params = {
            "symbol": symbol.replace("-", ""),
            "limit": depth
        }
        
        response = requests.get(url, params=params)
        data = response.json()
        
        return {
            "timestamp": datetime.now().isoformat(),
            "symbol": symbol,
            "bids": [[float(price), float(qty)] for price, qty in data.get("bids", [])],
            "asks": [[float(price), float(qty)] for price, qty in data.get("asks", [])]
        }
    
    def get_recent_trades(self, symbol: str, limit: int = 1000) -> List[Dict[str, Any]]:
        """获取最近成交"""
        url = f"{self.base_url}/trades"
        params = {
            "symbol": symbol.replace("-", ""),
            "limit": limit
        }
        
        response = requests.get(url, params=params)
        data = response.json()
        
        return [
            {
                "id": trade["id"],
                "price": float(trade["price"]),
                "volume": float(trade["qty"]),
                "timestamp": datetime.fromtimestamp(trade["time"]/1000).isoformat(),
                "side": "buy" if trade["isBuyerMaker"] else "sell"
            }
            for trade in data
        ]
    
    def get_large_trades(self, symbol: str, min_value: float = 100000) -> List[Dict[str, Any]]:
        """获取大额交易"""
        trades = self.get_recent_trades(symbol)
        
        return [
            trade for trade in trades
            if trade["price"] * trade["volume"] >= min_value
        ]


class PolygonConnector:
    """Polygon.io API连接器"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.polygon.io"
    
    def get_last_quote(self, symbol: str) -> Dict[str, Any]:
        """获取最新报价"""
        url = f"{self.base_url}/v2/last/nbbo/{symbol}"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        
        response = requests.get(url, headers=headers)
        data = response.json()
        
        if data.get("status") == "success":
            quote = data.get("results", {})
            return {
                "symbol": symbol,
                "bid_price": quote.get("p", 0),
                "bid_size": quote.get("s", 0),
                "ask_price": quote.get("P", 0),
                "ask_size": quote.get("S", 0),
                "timestamp": datetime.fromtimestamp(quote.get("t", 0)/1000).isoformat()
            }
        
        return {
            "symbol": symbol,
            "error": data.get("error", "Unknown error"),
            "timestamp": datetime.now().isoformat()
        }
    
    def get_trades(self, symbol: str, date: str = None) -> List[Dict[str, Any]]:
        """获取交易记录"""
        if not date:
            date = datetime.now().strftime("%Y-%m-%d")
            
        url = f"{self.base_url}/v2/ticks/stocks/trades/{symbol}/{date}"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        
        response = requests.get(url, headers=headers)
        data = response.json()
        
        if data.get("status") == "success":
            return [
                {
                    "price": trade.get("p", 0),
                    "volume": trade.get("s", 0),
                    "timestamp": datetime.fromtimestamp(trade.get("t", 0)/1000).isoformat(),
                    "exchange": trade.get("x", ""),
                    "id": trade.get("i", ""),
                    "side": "buy" if trade.get("z", 0) > 0 else "sell"
                }
                for trade in data.get("results", [])
            ]
        
        return []
    
    def get_large_trades(self, symbol: str, min_value: float = 100000) -> List[Dict[str, Any]]:
        """获取大额交易"""
        trades = self.get_trades(symbol)
        
        return [
            trade for trade in trades
            if trade["price"] * trade["volume"] >= min_value
        ]


# 可以继续添加其他连接器，如FinnhubConnector, TradierConnector, CoinbaseConnector等

if __name__ == "__main__":
    # 测试代码
    config = {
        "alpha_vantage_key": os.environ.get("ALPHA_VANTAGE_API_KEY", ""),
        "polygon_key": os.environ.get("POLYGON_API_KEY", ""),
        "binance_key": os.environ.get("BINANCE_API_KEY", ""),
        "binance_secret": os.environ.get("BINANCE_SECRET_KEY", "")
    }
    
    connector = MarketDataConnector(config)
    
    # 测试获取订单簿
    if config["binance_key"]:
        orderbook = connector.get_orderbook("BTC-USDT", market_type="crypto")
        print("订单簿数据示例:")
        print(f"Symbol: {orderbook['symbol']}")
        print(f"时间戳: {orderbook['timestamp']}")
        print(f"买盘前5: {orderbook['bids'][:5]}")
        print(f"卖盘前5: {orderbook['asks'][:5]}")
        
        # 计算订单不平衡
        imbalance = connector.calculate_order_imbalance("BTC-USDT", market_type="crypto")
        print(f"订单不平衡指标: {imbalance:.4f}")
    else:
        print("未配置Binance API密钥，跳过测试")

from core.data_models import (
    MarketData, OrderBook, Trade, OptionChain, MarketSnapshot,
    DataSource, MarketType, DataNormalizer
)
from core.data_processor import DataProcessor

class MarketConnector:
    def __init__(self, config: Dict):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.connections: Dict[str, Dict] = {}
        self.callbacks: Dict[str, Callable] = {}
        self.data_processor = DataProcessor(config)
        self.connection_pool = {}
        self.cache = {}
        self.cache_ttl = 300  # 5分钟缓存
        
    async def connect(self, provider: str, symbol: str, callback: Callable) -> None:
        """连接到指定数据源"""
        key = f"{provider}:{symbol}"
        if key in self.connections:
            return
            
        try:
            if provider == "polygon":
                await self._connect_polygon(symbol, callback)
            elif provider == "tradier":
                await self._connect_tradier(symbol, callback)
            elif provider == "binance":
                await self._connect_binance(symbol, callback)
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
            await websocket.send({
                "action": "auth",
                "params": self.config["polygon"]["api_key"]
            })
            
            # 订阅期权数据
            await websocket.send({
                "action": "subscribe",
                "params": f"O.{symbol}"
            })
            
            while True:
                try:
                    data = await websocket.recv()
                    # 使用数据处理器处理数据
                    await self.data_processor.process_market_data(
                        data, DataSource.POLYGON
                    )
                except Exception as e:
                    self.logger.error(f"Error processing Polygon data: {str(e)}")
                    break
                    
    async def _connect_tradier(self, symbol: str, callback: Callable) -> None:
        """连接Tradier WebSocket"""
        uri = "wss://ws.tradier.com/v1/markets/events"
        headers = {
            "Authorization": f"Bearer {self.config['tradier']['api_key']}",
            "Accept": "application/json"
        }
        
        async with websockets.connect(uri, extra_headers=headers) as websocket:
            # 订阅期权数据
            await websocket.send({
                "symbols": [symbol],
                "sessionid": "session1",
                "linebreak": True
            })
            
            while True:
                try:
                    data = await websocket.recv()
                    # 使用数据处理器处理数据
                    await self.data_processor.process_market_data(
                        data, DataSource.TRADIER
                    )
                except Exception as e:
                    self.logger.error(f"Error processing Tradier data: {str(e)}")
                    break
                    
    async def _connect_binance(self, symbol: str, callback: Callable) -> None:
        """连接Binance WebSocket"""
        uri = f"wss://fstream.binance.com/ws/{symbol.lower()}@aggTrade"
        
        async with websockets.connect(uri) as websocket:
            while True:
                try:
                    data = await websocket.recv()
                    # 使用数据处理器处理数据
                    await self.data_processor.process_market_data(
                        data, DataSource.BINANCE
                    )
                except Exception as e:
                    self.logger.error(f"Error processing Binance data: {str(e)}")
                    break
                    
    async def get_historical_data(self, provider: str, symbol: str, 
                                start_date: str, end_date: str) -> List[Dict]:
        """获取历史数据"""
        try:
            if provider == "polygon":
                data = await self._get_polygon_historical(symbol, start_date, end_date)
                return [self.data_processor.normalizer.normalize_market_data(
                    item, DataSource.POLYGON
                ) for item in data]
            elif provider == "tradier":
                data = await self._get_tradier_historical(symbol, start_date, end_date)
                return [self.data_processor.normalizer.normalize_market_data(
                    item, DataSource.TRADIER
                ) for item in data]
            else:
                raise ValueError(f"Unsupported provider: {provider}")
        except Exception as e:
            self.logger.error(f"Error fetching historical data: {str(e)}")
            return []
            
    async def get_market_snapshot(self, symbol: str) -> Optional[MarketSnapshot]:
        """获取市场快照"""
        return await self.data_processor.create_market_snapshot(symbol)
        
    def register_data_callback(self, data_type: str, callback: Callable) -> None:
        """注册数据回调"""
        self.data_processor.register_callback(data_type, callback)
        
    async def disconnect(self, provider: str, symbol: str) -> None:
        """断开连接"""
        key = f"{provider}:{symbol}"
        if key in self.connections:
            await self.connections[key]["websocket"].close()
            del self.connections[key]
            del self.callbacks[key]
            
    async def health_check(self) -> None:
        """检查连接健康状态"""
        for key, conn in list(self.connections.items()):
            try:
                if not conn["websocket"].open:
                    provider, symbol = key.split(":")
                    await self.connect(provider, symbol, self.callbacks[key])
            except Exception as e:
                self.logger.error(f"Health check failed for {key}: {str(e)}")
                
    async def start(self) -> None:
        """启动连接管理器"""
        while True:
            await self.health_check()
            await asyncio.sleep(30)  # 每30秒检查一次 