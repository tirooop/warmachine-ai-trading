import yfinance as yf
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
import logging
import aiohttp
import json

logger = logging.getLogger(__name__)

class DataProcessor:
    """数据处理类，负责获取和处理各种市场数据"""
    
    def __init__(self, config: Dict[str, Any]):
        """初始化数据处理器"""
        self.config = config
        self.data_providers = config["data_providers"]
        self.yf = yf
        self.sessions = {}
        
    async def _ensure_session(self, provider: str) -> aiohttp.ClientSession:
        """确保HTTP会话已初始化"""
        if provider not in self.sessions:
            provider_config = self.data_providers[provider]
            self.sessions[provider] = aiohttp.ClientSession(
                base_url=provider_config["base_url"],
                headers={
                    "Authorization": f"Bearer {provider_config['api_key']}",
                    "Content-Type": "application/json"
                }
            )
        return self.sessions[provider]
        
    async def get_price_data(self, symbol: str) -> Dict[str, Any]:
        """获取价格数据"""
        try:
            # 首先尝试使用Polygon
            if self.data_providers["polygon"]["enabled"]:
                try:
                    session = await self._ensure_session("polygon")
                    async with session.get(f"/v2/aggs/ticker/{symbol}/prev") as response:
                        if response.status == 200:
                            data = await response.json()
                            if data["results"]:
                                result = data["results"][0]
                                return {
                                    "current_price": round(result["c"], 2),
                                    "daily_change": round(((result["c"] - result["o"]) / result["o"]) * 100, 2),
                                    "52w_high": round(result["h"], 2),
                                    "52w_low": round(result["l"], 2)
                                }
                except Exception as e:
                    logger.warning(f"Polygon API failed, falling back to Yahoo Finance: {str(e)}")
            
            # 如果Polygon失败，使用Yahoo Finance
            ticker = self.yf.Ticker(symbol)
            hist = ticker.history(period="1y")
            
            if hist.empty:
                return {}
                
            current_price = hist['Close'].iloc[-1]
            daily_change = ((current_price - hist['Close'].iloc[-2]) / hist['Close'].iloc[-2]) * 100
            high_52w = hist['High'].max()
            low_52w = hist['Low'].min()
            
            return {
                "current_price": round(current_price, 2),
                "daily_change": round(daily_change, 2),
                "52w_high": round(high_52w, 2),
                "52w_low": round(low_52w, 2)
            }
        except Exception as e:
            logger.error(f"获取价格数据失败: {str(e)}")
            return {}
            
    async def get_technical_indicators(self, symbol: str) -> Dict[str, Any]:
        """获取技术指标数据"""
        try:
            # 首先尝试使用Tradier
            if self.data_providers["tradier"]["enabled"]:
                try:
                    session = await self._ensure_session("tradier")
                    async with session.get(f"/v1/markets/quotes?symbols={symbol}") as response:
                        if response.status == 200:
                            data = await response.json()
                            if data["quotes"]["quote"]:
                                quote = data["quotes"]["quote"]
                                return {
                                    "rsi": round(quote.get("rsi", 0), 2),
                                    "macd": round(quote.get("macd", 0), 2),
                                    "macd_signal": round(quote.get("macd_signal", 0), 2),
                                    "bollinger": {
                                        "upper": round(quote.get("bb_upper", 0), 2),
                                        "middle": round(quote.get("bb_middle", 0), 2),
                                        "lower": round(quote.get("bb_lower", 0), 2)
                                    }
                                }
                except Exception as e:
                    logger.warning(f"Tradier API failed, falling back to Yahoo Finance: {str(e)}")
            
            # 如果Tradier失败，使用Yahoo Finance
            ticker = self.yf.Ticker(symbol)
            hist = ticker.history(period="1y")
            
            if hist.empty:
                return {}
                
            # 计算RSI
            delta = hist['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            
            # 计算MACD
            exp1 = hist['Close'].ewm(span=12, adjust=False).mean()
            exp2 = hist['Close'].ewm(span=26, adjust=False).mean()
            macd = exp1 - exp2
            signal = macd.ewm(span=9, adjust=False).mean()
            
            # 计算布林带
            sma = hist['Close'].rolling(window=20).mean()
            std = hist['Close'].rolling(window=20).std()
            upper_band = sma + (std * 2)
            lower_band = sma - (std * 2)
            
            return {
                "rsi": round(rsi.iloc[-1], 2),
                "macd": round(macd.iloc[-1], 2),
                "macd_signal": round(signal.iloc[-1], 2),
                "bollinger": {
                    "upper": round(upper_band.iloc[-1], 2),
                    "middle": round(sma.iloc[-1], 2),
                    "lower": round(lower_band.iloc[-1], 2)
                }
            }
        except Exception as e:
            logger.error(f"获取技术指标失败: {str(e)}")
            return {}
            
    async def get_sentiment_data(self, symbol: str) -> Dict[str, Any]:
        """获取市场情绪数据"""
        try:
            # 这里可以接入实际的情绪分析API
            # 目前使用模拟数据
            return {
                "score": round(np.random.uniform(-1, 1), 2),
                "trend": np.random.choice(["上升", "下降", "稳定"]),
                "social_sentiment": round(np.random.uniform(-1, 1), 2)
            }
        except Exception as e:
            logger.error(f"获取市场情绪数据失败: {str(e)}")
            return {}
            
    async def get_fundamentals(self, symbol: str) -> Dict[str, Any]:
        """获取基本面数据"""
        try:
            # 首先尝试使用Polygon
            if self.data_providers["polygon"]["enabled"]:
                try:
                    session = await self._ensure_session("polygon")
                    async with session.get(f"/v3/reference/tickers/{symbol}") as response:
                        if response.status == 200:
                            data = await response.json()
                            if data["results"]:
                                result = data["results"]
                                return {
                                    "pe_ratio": round(result.get("pe_ratio", 0), 2),
                                    "eps": round(result.get("eps", 0), 2),
                                    "market_cap": round(result.get("market_cap", 0) / 1e9, 2),
                                    "dividend_yield": round(result.get("dividend_yield", 0) * 100, 2),
                                    "beta": round(result.get("beta", 0), 2)
                                }
                except Exception as e:
                    logger.warning(f"Polygon API failed, falling back to Yahoo Finance: {str(e)}")
            
            # 如果Polygon失败，使用Yahoo Finance
            ticker = self.yf.Ticker(symbol)
            info = ticker.info
            
            return {
                "pe_ratio": round(info.get('forwardPE', 0), 2),
                "eps": round(info.get('trailingEps', 0), 2),
                "market_cap": round(info.get('marketCap', 0) / 1e9, 2),
                "dividend_yield": round(info.get('dividendYield', 0) * 100, 2),
                "beta": round(info.get('beta', 0), 2)
            }
        except Exception as e:
            logger.error(f"获取基本面数据失败: {str(e)}")
            return {}
            
    async def get_money_flow(self, symbol: str) -> Dict[str, Any]:
        """获取资金流向数据"""
        try:
            # 这里可以接入实际的资金流向API
            # 目前使用模拟数据
            inflow = round(np.random.uniform(0, 100), 2)
            outflow = round(np.random.uniform(0, 100), 2)
            net_flow = round(inflow - outflow, 2)
            
            return {
                "inflow": inflow,
                "outflow": outflow,
                "net_flow": net_flow,
                "institutional_flow": round(np.random.uniform(-50, 50), 2),
                "retail_flow": round(np.random.uniform(-50, 50), 2)
            }
        except Exception as e:
            logger.error(f"获取资金流向数据失败: {str(e)}")
            return {}
            
    async def get_options_data(self, symbol: str) -> Dict[str, Any]:
        """获取期权数据"""
        try:
            # 首先尝试使用Tradier
            if self.data_providers["tradier"]["enabled"]:
                try:
                    session = await self._ensure_session("tradier")
                    async with session.get(f"/v1/markets/options/chains?symbol={symbol}") as response:
                        if response.status == 200:
                            data = await response.json()
                            if data["options"]:
                                options = data["options"]["option"]
                                puts = [o for o in options if o["option_type"] == "put"]
                                calls = [o for o in options if o["option_type"] == "call"]
                                
                                put_volume = sum(p.get("volume", 0) for p in puts)
                                call_volume = sum(c.get("volume", 0) for c in calls)
                                put_call_ratio = put_volume / call_volume if call_volume > 0 else 0
                                
                                return {
                                    "put_call_ratio": round(put_call_ratio, 2),
                                    "implied_volatility": round(np.random.uniform(0.1, 0.5), 2),
                                    "open_interest": round(np.random.uniform(1000, 10000), 0),
                                    "volume": round(put_volume + call_volume, 0)
                                }
                except Exception as e:
                    logger.warning(f"Tradier API failed, falling back to Yahoo Finance: {str(e)}")
            
            # 如果Tradier失败，使用Yahoo Finance
            ticker = self.yf.Ticker(symbol)
            options = ticker.option_chain()
            
            if options:
                puts = options.puts
                calls = options.calls
                
                put_volume = puts['volume'].sum() if 'volume' in puts else 0
                call_volume = calls['volume'].sum() if 'volume' in calls else 0
                put_call_ratio = put_volume / call_volume if call_volume > 0 else 0
                
                return {
                    "put_call_ratio": round(put_call_ratio, 2),
                    "implied_volatility": round(np.random.uniform(0.1, 0.5), 2),
                    "open_interest": round(np.random.uniform(1000, 10000), 0),
                    "volume": round(put_volume + call_volume, 0)
                }
            return {}
        except Exception as e:
            logger.error(f"获取期权数据失败: {str(e)}")
            return {} 