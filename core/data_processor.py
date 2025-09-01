import asyncio
import logging
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime
from .data_models import (
    MarketData, OrderBook, Trade, OptionChain, MarketSnapshot,
    DataSource, MarketType, DataNormalizer
)

logger = logging.getLogger(__name__)

class DataProcessor:
    """统一的数据处理器"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.normalizer = DataNormalizer()
        self.callbacks: Dict[str, List[Callable]] = {
            "market_data": [],
            "orderbook": [],
            "trade": [],
            "option_chain": [],
            "snapshot": []
        }
        self.cache: Dict[str, Any] = {}
        self.cache_ttl = config.get("cache_ttl", 300)  # 默认5分钟缓存
        
    def register_callback(self, data_type: str, callback: Callable) -> None:
        """注册数据回调函数"""
        if data_type in self.callbacks:
            self.callbacks[data_type].append(callback)
        else:
            raise ValueError(f"Unsupported data type: {data_type}")
            
    async def process_market_data(self, data: Dict, source: DataSource) -> None:
        """处理市场数据"""
        try:
            normalized_data = self.normalizer.normalize_market_data(data, source)
            self._update_cache(f"market_data:{normalized_data.symbol}", normalized_data)
            
            # 触发回调
            for callback in self.callbacks["market_data"]:
                await callback(normalized_data)
                
        except Exception as e:
            logger.error(f"Error processing market data: {str(e)}")
            
    async def process_orderbook(self, data: Dict, source: DataSource) -> None:
        """处理订单簿数据"""
        try:
            normalized_data = self.normalizer.normalize_orderbook(data, source)
            self._update_cache(f"orderbook:{normalized_data.symbol}", normalized_data)
            
            # 触发回调
            for callback in self.callbacks["orderbook"]:
                await callback(normalized_data)
                
        except Exception as e:
            logger.error(f"Error processing orderbook: {str(e)}")
            
    async def process_trade(self, data: Dict, source: DataSource) -> None:
        """处理交易数据"""
        try:
            # 标准化交易数据
            trade = Trade(
                symbol=data.get("symbol", ""),
                market_type=MarketType.STOCK if source != DataSource.BINANCE else MarketType.CRYPTO,
                source=source,
                timestamp=datetime.fromtimestamp(data.get("timestamp", 0) / 1000),
                price=float(data.get("price", 0)),
                quantity=float(data.get("quantity", 0)),
                side=data.get("side", ""),
                trade_id=data.get("trade_id"),
                raw_data=data
            )
            
            # 更新缓存
            cache_key = f"trades:{trade.symbol}"
            if cache_key not in self.cache:
                self.cache[cache_key] = []
            self.cache[cache_key].append(trade)
            
            # 保持最近1000笔交易
            if len(self.cache[cache_key]) > 1000:
                self.cache[cache_key] = self.cache[cache_key][-1000:]
                
            # 触发回调
            for callback in self.callbacks["trade"]:
                await callback(trade)
                
        except Exception as e:
            logger.error(f"Error processing trade: {str(e)}")
            
    async def process_option_chain(self, data: Dict, source: DataSource) -> None:
        """处理期权链数据"""
        try:
            # 标准化期权链数据
            option_chain = OptionChain(
                symbol=data.get("symbol", ""),
                source=source,
                timestamp=datetime.now(),
                expiration=datetime.fromtimestamp(data.get("expiration", 0)),
                calls=data.get("calls", []),
                puts=data.get("puts", []),
                underlying_price=float(data.get("underlying_price", 0)),
                raw_data=data
            )
            
            # 更新缓存
            self._update_cache(f"option_chain:{option_chain.symbol}", option_chain)
            
            # 触发回调
            for callback in self.callbacks["option_chain"]:
                await callback(option_chain)
                
        except Exception as e:
            logger.error(f"Error processing option chain: {str(e)}")
            
    async def create_market_snapshot(self, symbol: str) -> Optional[MarketSnapshot]:
        """创建市场快照"""
        try:
            # 获取最新数据
            market_data = self._get_cached_data(f"market_data:{symbol}")
            orderbook = self._get_cached_data(f"orderbook:{symbol}")
            trades = self._get_cached_data(f"trades:{symbol}")
            option_chain = self._get_cached_data(f"option_chain:{symbol}")
            
            if not market_data:
                return None
                
            # 创建快照
            snapshot = MarketSnapshot(
                symbol=symbol,
                market_type=market_data.market_type,
                source=market_data.source,
                timestamp=datetime.now(),
                price_data=market_data,
                order_book=orderbook,
                recent_trades=trades[-10:] if trades else None,  # 最近10笔交易
                option_chain=option_chain
            )
            
            # 触发回调
            for callback in self.callbacks["snapshot"]:
                await callback(snapshot)
                
            return snapshot
            
        except Exception as e:
            logger.error(f"Error creating market snapshot: {str(e)}")
            return None
            
    def _update_cache(self, key: str, data: Any) -> None:
        """更新缓存"""
        self.cache[key] = (datetime.now(), data)
        
    def _get_cached_data(self, key: str) -> Optional[Any]:
        """获取缓存数据"""
        if key in self.cache:
            timestamp, data = self.cache[key]
            if (datetime.now() - timestamp).total_seconds() < self.cache_ttl:
                return data
            del self.cache[key]
        return None
        
    def clear_cache(self) -> None:
        """清除所有缓存"""
        self.cache.clear()
        
    def get_cache_stats(self) -> Dict:
        """获取缓存统计信息"""
        return {
            "total_items": len(self.cache),
            "cache_ttl": self.cache_ttl,
            "keys": list(self.cache.keys())
        } 