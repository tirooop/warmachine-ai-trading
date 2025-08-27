from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Union
from enum import Enum

from core.tg_bot.super_commander import SuperCommander

class MarketType(Enum):
    STOCK = "stock"
    CRYPTO = "crypto"
    FOREX = "forex"
    OPTION = "option"
    FUTURE = "future"

class DataSource(Enum):
    POLYGON = "polygon"
    TRADIER = "tradier"
    BINANCE = "binance"
    IBKR = "ibkr"
    DATABENTO = "databento"

@dataclass
class MarketData:
    """统一的市场数据模型"""
    symbol: str
    market_type: MarketType
    source: DataSource
    timestamp: datetime
    price: float
    volume: float
    bid: Optional[float] = None
    ask: Optional[float] = None
    last_price: Optional[float] = None
    open_price: Optional[float] = None
    high_price: Optional[float] = None
    low_price: Optional[float] = None
    close_price: Optional[float] = None
    vwap: Optional[float] = None
    raw_data: Optional[Dict] = None

@dataclass
class OrderBook:
    """统一的订单簿数据模型"""
    symbol: str
    market_type: MarketType
    source: DataSource
    timestamp: datetime
    bids: List[List[float]]  # [[price, quantity], ...]
    asks: List[List[float]]  # [[price, quantity], ...]
    raw_data: Optional[Dict] = None

@dataclass
class Trade:
    """统一的交易数据模型"""
    symbol: str
    market_type: MarketType
    source: DataSource
    timestamp: datetime
    price: float
    quantity: float
    side: str  # "buy" or "sell"
    trade_id: Optional[str] = None
    raw_data: Optional[Dict] = None

@dataclass
class OptionChain:
    """统一的期权链数据模型"""
    symbol: str
    source: DataSource
    timestamp: datetime
    expiration: datetime
    calls: List[Dict]
    puts: List[Dict]
    underlying_price: float
    raw_data: Optional[Dict] = None

@dataclass
class MarketSnapshot:
    """统一的市场快照数据模型"""
    symbol: str
    market_type: MarketType
    source: DataSource
    timestamp: datetime
    price_data: MarketData
    order_book: Optional[OrderBook] = None
    recent_trades: Optional[List[Trade]] = None
    option_chain: Optional[OptionChain] = None
    raw_data: Optional[Dict] = None

class DataNormalizer:
    """数据标准化处理器"""
    
    @staticmethod
    def normalize_market_data(data: Dict, source: DataSource) -> MarketData:
        """标准化市场数据"""
        if source == DataSource.POLYGON:
            return DataNormalizer._normalize_polygon_data(data)
        elif source == DataSource.TRADIER:
            return DataNormalizer._normalize_tradier_data(data)
        elif source == DataSource.BINANCE:
            return DataNormalizer._normalize_binance_data(data)
        else:
            raise ValueError(f"Unsupported data source: {source}")

    @staticmethod
    def _normalize_polygon_data(data: Dict) -> MarketData:
        """标准化Polygon数据"""
        return MarketData(
            symbol=data.get("sym", ""),
            market_type=MarketType.STOCK,
            source=DataSource.POLYGON,
            timestamp=datetime.fromtimestamp(data.get("t", 0) / 1000),
            price=float(data.get("p", 0)),
            volume=float(data.get("s", 0)),
            bid=float(data.get("bp", 0)),
            ask=float(data.get("ap", 0)),
            raw_data=data
        )

    @staticmethod
    def _normalize_tradier_data(data: Dict) -> MarketData:
        """标准化Tradier数据"""
        return MarketData(
            symbol=data.get("symbol", ""),
            market_type=MarketType.STOCK,
            source=DataSource.TRADIER,
            timestamp=datetime.fromtimestamp(data.get("timestamp", 0)),
            price=float(data.get("last", 0)),
            volume=float(data.get("volume", 0)),
            bid=float(data.get("bid", 0)),
            ask=float(data.get("ask", 0)),
            raw_data=data
        )

    @staticmethod
    def _normalize_binance_data(data: Dict) -> MarketData:
        """标准化Binance数据"""
        return MarketData(
            symbol=data.get("s", ""),
            market_type=MarketType.CRYPTO,
            source=DataSource.BINANCE,
            timestamp=datetime.fromtimestamp(data.get("T", 0) / 1000),
            price=float(data.get("p", 0)),
            volume=float(data.get("q", 0)),
            raw_data=data
        )

    @staticmethod
    def normalize_orderbook(data: Dict, source: DataSource) -> OrderBook:
        """标准化订单簿数据"""
        if source == DataSource.POLYGON:
            return DataNormalizer._normalize_polygon_orderbook(data)
        elif source == DataSource.BINANCE:
            return DataNormalizer._normalize_binance_orderbook(data)
        else:
            raise ValueError(f"Unsupported data source for orderbook: {source}")

    @staticmethod
    def _normalize_polygon_orderbook(data: Dict) -> OrderBook:
        """标准化Polygon订单簿数据"""
        return OrderBook(
            symbol=data.get("sym", ""),
            market_type=MarketType.STOCK,
            source=DataSource.POLYGON,
            timestamp=datetime.fromtimestamp(data.get("t", 0) / 1000),
            bids=[[float(price), float(qty)] for price, qty in data.get("bids", [])],
            asks=[[float(price), float(qty)] for price, qty in data.get("asks", [])],
            raw_data=data
        )

    @staticmethod
    def _normalize_binance_orderbook(data: Dict) -> OrderBook:
        """标准化Binance订单簿数据"""
        return OrderBook(
            symbol=data.get("s", ""),
            market_type=MarketType.CRYPTO,
            source=DataSource.BINANCE,
            timestamp=datetime.fromtimestamp(data.get("T", 0) / 1000),
            bids=[[float(price), float(qty)] for price, qty in data.get("bids", [])],
            asks=[[float(price), float(qty)] for price, qty in data.get("asks", [])],
            raw_data=data
        ) 