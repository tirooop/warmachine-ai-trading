"""
Tradier期权数据适配器

提供Tradier API的期权数据访问接口，包括期权链、价格和希腊值等数据。
支持数据缓存和实时更新。
"""

import os
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union
import aiohttp
import asyncio
from diskcache import Cache

# 配置日志
logger = logging.getLogger(__name__)

class TradierOptionsAdapter:
    """Tradier期权数据适配器"""
    
    def __init__(self, api_key: str, cache_dir: str = "data/options/cache"):
        """
        初始化Tradier期权数据适配器
        
        Args:
            api_key: Tradier API密钥
            cache_dir: 缓存目录路径
        """
        self.api_key = api_key
        self.base_url = "https://sandbox.tradier.com/v1"
        self.session = None
        self.cache = Cache(cache_dir)
        
        # 确保缓存目录存在
        os.makedirs(cache_dir, exist_ok=True)
        
        logger.info("Tradier期权数据适配器初始化完成")
    
    async def _ensure_session(self):
        """确保aiohttp会话存在"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Accept": "application/json"
                },
                timeout=aiohttp.ClientTimeout(total=5.0)
            )
    
    async def _request(self, endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        发送API请求
        
        Args:
            endpoint: API端点
            params: 请求参数
            
        Returns:
            API响应数据
        """
        await self._ensure_session()
        
        try:
            async with self.session.get(f"{self.base_url}/{endpoint}", params=params) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    # 尝试提取faultstring
                    try:
                        error_json = json.loads(error_text) if isinstance(error_text, str) else error_text
                        faultstring = error_json.get('fault', {}).get('faultstring')
                        if faultstring:
                            raise ValueError(f"Tradier API错误: {faultstring}")
                    except json.JSONDecodeError:
                        pass
                    raise ValueError(f"Tradier API错误: {error_text}")
                return await resp.json()
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Tradier API请求失败: {str(e)}")
            raise
    
    def _get_cache_key(self, symbol: str, expiration: str, **filters) -> str:
        """生成缓存键"""
        filter_str = json.dumps(filters, sort_keys=True)
        return f"{symbol}|{expiration}|{filter_str}"
    
    async def get_chain(self, symbol: str, expiration: str, **filters) -> Dict[str, Any]:
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
        # 参数校验
        if not symbol or not isinstance(symbol, str):
            raise ValueError("无效的股票代码")
        try:
            datetime.strptime(expiration, "%Y-%m-%d")
        except Exception:
            raise ValueError("无效的到期日")
        
        cache_key = self._get_cache_key(symbol, expiration, **filters)
        
        # 检查缓存
        if cached_data := self.cache.get(cache_key):
            if time.time() - cached_data['timestamp'] < 60:  # 1分钟内的缓存有效
                return cached_data['data']
        
        # 获取原始数据
        raw_data = await self._request(
            "markets/options/chains",
            params={
                "symbol": symbol,
                "expiration": expiration,
                "greeks": "true"
            }
        )
        
        # 处理数据
        processed_data = self._process_chain_data(raw_data, filters)
        
        # 更新缓存
        self.cache.set(cache_key, {
            'timestamp': time.time(),
            'data': processed_data
        })
        
        return processed_data
    
    def _process_chain_data(self, raw_data: Dict[str, Any], filters: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理原始期权链数据
        
        Args:
            raw_data: 原始API响应数据
            filters: 筛选条件
            
        Returns:
            处理后的期权链数据
        """
        options = raw_data.get('options', {}).get('option', [])
        if not options:
            return {"calls": [], "puts": []}
        
        # 分离看涨和看跌期权
        calls = []
        puts = []
        
        for opt in options:
            option_data = {
                'strike': float(opt['strike']),
                'expiration': opt['expiration_date'],
                'type': opt['option_type'],
                'last': float(opt['last']),
                'bid': float(opt['bid']),
                'ask': float(opt['ask']),
                'volume': int(opt['volume']),
                'open_interest': int(opt['open_interest']),
                'implied_volatility': float(opt['greeks']['smv_vol']),
                'delta': float(opt['greeks']['delta']),
                'gamma': float(opt['greeks']['gamma']),
                'theta': float(opt['greeks']['theta']),
                'vega': float(opt['greeks']['vega'])
            }
            
            # 应用筛选条件
            if self._apply_filters(option_data, filters):
                if opt['option_type'] == 'call':
                    calls.append(option_data)
                else:
                    puts.append(option_data)
        
        # 按行权价排序
        calls.sort(key=lambda x: x['strike'])
        puts.sort(key=lambda x: x['strike'])
        
        # 限制每侧数量
        max_strikes = filters.get('max_strikes', 20)
        calls = calls[:max_strikes]
        puts = puts[:max_strikes]
        
        return {
            "calls": calls,
            "puts": puts,
            "timestamp": datetime.now().isoformat(),
            "underlying_price": float(raw_data.get('underlying', {}).get('last', 0))
        }
    
    def _apply_filters(self, option: Dict[str, Any], filters: Dict[str, Any]) -> bool:
        """
        应用筛选条件
        
        Args:
            option: 期权数据
            filters: 筛选条件
            
        Returns:
            是否通过筛选
        """
        # 成交量筛选
        if min_volume := filters.get('min_volume'):
            if option['volume'] < min_volume:
                return False
        
        # 持仓量筛选
        if min_oi := filters.get('min_open_interest'):
            if option['open_interest'] < min_oi:
                return False
        
        return True
    
    async def close(self):
        """关闭连接"""
        if self.session and not self.session.closed:
            await self.session.close()
        self.cache.close() 