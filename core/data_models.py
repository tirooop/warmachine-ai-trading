from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Union, Any
from enum import Enum
from pydantic import BaseModel, Field, validator
import logging

logger = logging.getLogger(__name__)

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
    GOOGLE_FINANCE = "google_finance"
    ALPHA_VANTAGE = "alpha_vantage"
    FINNHUB = "finnhub"
    YAHOO_FINANCE = "yahoo_finance"

class OrderSide(Enum):
    BUY = "buy"
    SELL = "sell"

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
    raw_data: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        """数据验证"""
        if self.price <= 0:
            raise ValueError(f"Price must be positive: {self.price}")
        if self.volume < 0:
            raise ValueError(f"Volume cannot be negative: {self.volume}")

@dataclass
class OrderBook:
    """统一的订单簿数据模型"""
    symbol: str
    market_type: MarketType
    source: DataSource
    timestamp: datetime
    bids: List[List[float]]  # [[price, quantity], ...]
    asks: List[List[float]]  # [[price, quantity], ...]
    raw_data: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        """数据验证"""
        if not self.bids or not self.asks:
            raise ValueError("Order book must have both bids and asks")
        
        # 验证价格顺序
        for i in range(len(self.bids) - 1):
            if self.bids[i][0] < self.bids[i + 1][0]:
                raise ValueError("Bids must be in descending order")
        
        for i in range(len(self.asks) - 1):
            if self.asks[i][0] > self.asks[i + 1][0]:
                raise ValueError("Asks must be in ascending order")

@dataclass
class Trade:
    """统一的交易数据模型"""
    symbol: str
    market_type: MarketType
    source: DataSource
    timestamp: datetime
    price: float
    quantity: float
    side: OrderSide
    trade_id: Optional[str] = None
    raw_data: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        """数据验证"""
        if self.price <= 0:
            raise ValueError(f"Trade price must be positive: {self.price}")
        if self.quantity <= 0:
            raise ValueError(f"Trade quantity must be positive: {self.quantity}")

@dataclass
class OptionChain:
    """统一的期权链数据模型"""
    symbol: str
    source: DataSource
    timestamp: datetime
    expiration: datetime
    calls: List[Dict[str, Any]]
    puts: List[Dict[str, Any]]
    underlying_price: float
    raw_data: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        """数据验证"""
        if self.underlying_price <= 0:
            raise ValueError(f"Underlying price must be positive: {self.underlying_price}")
        if self.expiration <= self.timestamp:
            raise ValueError("Expiration must be after current timestamp")

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
    raw_data: Optional[Dict[str, Any]] = None

# Pydantic模型用于API接口
class MarketDataRequest(BaseModel):
    """市场数据请求模型"""
    symbol: str = Field(..., min_length=1, max_length=20)
    market_type: MarketType
    source: DataSource
    timeframe: str = Field(..., regex=r"^\d+[mhd]$")  # 1m, 5m, 1h, 1d等
    limit: int = Field(default=100, ge=1, le=10000)
    
    @validator('symbol')
    def validate_symbol(cls, v):
        if not v.isalnum():
            raise ValueError('Symbol must be alphanumeric')
        return v.upper()

class TradeRequest(BaseModel):
    """交易请求模型"""
    symbol: str = Field(..., min_length=1, max_length=20)
    side: OrderSide
    quantity: float = Field(..., gt=0)
    price: Optional[float] = Field(None, gt=0)
    order_type: str = Field(..., regex=r"^(market|limit|stop)$")
    
    @validator('symbol')
    def validate_symbol(cls, v):
        return v.upper()

class DataNormalizer:
    """数据标准化处理器"""
    
    @staticmethod
    def normalize_market_data(data: Dict[str, Any], source: DataSource) -> MarketData:
        """标准化市场数据"""
        try:
            if source == DataSource.POLYGON:
                return DataNormalizer._normalize_polygon_data(data)
            elif source == DataSource.TRADIER:
                return DataNormalizer._normalize_tradier_data(data)
            elif source == DataSource.BINANCE:
                return DataNormalizer._normalize_binance_data(data)
            else:
                raise ValueError(f"Unsupported data source: {source}")
        except Exception as e:
            logger.error(f"Failed to normalize market data from {source}: {e}")
            raise

    @staticmethod
    def _normalize_polygon_data(data: Dict[str, Any]) -> MarketData:
        """标准化Polygon数据"""
        try:
            return MarketData(
                symbol=data.get("sym", ""),
                market_type=MarketType.STOCK,
                source=DataSource.POLYGON,
                timestamp=datetime.fromtimestamp(data.get("t", 0) / 1000),
                price=float(data.get("p", 0)),
                volume=float(data.get("s", 0)),
                bid=float(data.get("bp", 0)) if data.get("bp") else None,
                ask=float(data.get("ap", 0)) if data.get("ap") else None,
                raw_data=data
            )
        except (KeyError, ValueError, TypeError) as e:
            logger.error(f"Failed to normalize Polygon data: {e}")
            raise

    @staticmethod
    def _normalize_tradier_data(data: Dict[str, Any]) -> MarketData:
        """标准化Tradier数据"""
        try:
            return MarketData(
                symbol=data.get("symbol", ""),
                market_type=MarketType.STOCK,
                source=DataSource.TRADIER,
                timestamp=datetime.fromtimestamp(data.get("timestamp", 0)),
                price=float(data.get("last", 0)),
                volume=float(data.get("volume", 0)),
                bid=float(data.get("bid", 0)) if data.get("bid") else None,
                ask=float(data.get("ask", 0)) if data.get("ask") else None,
                raw_data=data
            )
        except (KeyError, ValueError, TypeError) as e:
            logger.error(f"Failed to normalize Tradier data: {e}")
            raise

    @staticmethod
    def _normalize_binance_data(data: Dict[str, Any]) -> MarketData:
        """标准化Binance数据"""
        try:
            return MarketData(
                symbol=data.get("s", ""),
                market_type=MarketType.CRYPTO,
                source=DataSource.BINANCE,
                timestamp=datetime.fromtimestamp(data.get("T", 0) / 1000),
                price=float(data.get("p", 0)),
                volume=float(data.get("q", 0)),
                raw_data=data
            )
        except (KeyError, ValueError, TypeError) as e:
            logger.error(f"Failed to normalize Binance data: {e}")
            raise

    @staticmethod
    def normalize_orderbook(data: Dict[str, Any], source: DataSource) -> OrderBook:
        """标准化订单簿数据"""
        try:
            if source == DataSource.POLYGON:
                return DataNormalizer._normalize_polygon_orderbook(data)
            elif source == DataSource.BINANCE:
                return DataNormalizer._normalize_binance_orderbook(data)
            else:
                raise ValueError(f"Unsupported data source for orderbook: {source}")
        except Exception as e:
            logger.error(f"Failed to normalize orderbook from {source}: {e}")
            raise

    @staticmethod
    def _normalize_polygon_orderbook(data: Dict[str, Any]) -> OrderBook:
        """标准化Polygon订单簿数据"""
        try:
            return OrderBook(
                symbol=data.get("sym", ""),
                market_type=MarketType.STOCK,
                source=DataSource.POLYGON,
                timestamp=datetime.fromtimestamp(data.get("t", 0) / 1000),
                bids=[[float(price), float(qty)] for price, qty in data.get("bids", [])],
                asks=[[float(price), float(qty)] for price, qty in data.get("asks", [])],
                raw_data=data
            )
        except (KeyError, ValueError, TypeError) as e:
            logger.error(f"Failed to normalize Polygon orderbook: {e}")
            raise

    @staticmethod
    def _normalize_binance_orderbook(data: Dict[str, Any]) -> OrderBook:
        """标准化Binance订单簿数据"""
        try:
            return OrderBook(
                symbol=data.get("s", ""),
                market_type=MarketType.CRYPTO,
                source=DataSource.BINANCE,
                timestamp=datetime.fromtimestamp(data.get("T", 0) / 1000),
                bids=[[float(price), float(qty)] for price, qty in data.get("bids", [])],
                asks=[[float(price), float(qty)] for price, qty in data.get("asks", [])],
                raw_data=data
            )
        except (KeyError, ValueError, TypeError) as e:
            logger.error(f"Failed to normalize Binance orderbook: {e}")
            raise 