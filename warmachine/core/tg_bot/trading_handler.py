"""
Trading Query Handler with Enhanced AI Analysis Support
"""

import logging
import yfinance as yf
import pandas as pd
import numpy as np
import aiohttp
import ta
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import os
from typing import Dict, Any, Optional, List, Union
from datetime import datetime, timedelta
from dataclasses import dataclass
from collections import defaultdict

logger = logging.getLogger(__name__)

@dataclass
class TradingQuery:
    """Trading query parameters"""
    symbol: str
    query_type: str
    timeframe: str = "1d"
    indicators: Optional[List[str]] = None
    params: Optional[Dict[str, Any]] = None

class TradingHandler:
    """Handler for trading-related queries with enhanced AI analysis"""
    
    def __init__(self, mcp_connector, config: Dict[str, Any]):
        """
        Initialize trading handler
        
        Args:
            mcp_connector: MCP Server connector instance
            config: Configuration dictionary
        """
        self.mcp = mcp_connector
        self.config = config
        self.trading_config = config["trading"]
        self.supported_queries = {
            "price": self._handle_price_query,
            "volume": self._handle_volume_query,
            "technical": self._handle_technical_query,
            "fundamental": self._handle_fundamental_query,
            "ai_analysis": self._handle_ai_analysis_query,
            "prediction": self._handle_prediction_query,
            "sentiment": self._handle_sentiment_query,
            "risk_alert": self._handle_risk_alert_query,
            "chart": self._handle_chart_query  # 添加图表查询
        }
        
        # 初始化数据源
        self.yf = yf
        
        # 初始化AI配置
        self.ai_config = config["ai"]
        self.ai_session = None
        
        # 初始化预测历史记录
        self.prediction_history = defaultdict(list)
        
        # 创建图表输出目录
        self.chart_dir = "data/charts"
        if not os.path.exists(self.chart_dir):
            os.makedirs(self.chart_dir)
        
        # 扩展技术指标计算器
        self.technical_indicators = {
            "RSI": self._calculate_rsi,
            "MACD": self._calculate_macd,
            "BB": self._calculate_bollinger_bands,
            "MA": self._calculate_moving_averages,
            "ATR": self._calculate_atr,
            "KDJ": self._calculate_kdj,
            "OBV": self._calculate_obv,
            "CCI": self._calculate_cci,
            "DMI": self._calculate_dmi,
            "Ichimoku": self._calculate_ichimoku
        }
        
        # 风险预警阈值
        self.risk_thresholds = {
            "volatility": 0.02,  # 2% 日内波动
            "volume_spike": 3.0,  # 3倍平均成交量
            "price_gap": 0.05,   # 5% 价格跳空
            "rsi_extreme": 30,   # RSI 极值
            "macd_divergence": True,  # MACD 背离
            "bb_breakout": True,  # 布林带突破
            "ma_cross": True,    # 均线交叉
            "volume_trend": True  # 成交量趋势
        }
    
    async def _ensure_ai_session(self):
        """确保AI会话已初始化"""
        if self.ai_session is None:
            self.ai_session = aiohttp.ClientSession(
                base_url=self.ai_config["base_url"],
                headers={
                    "Authorization": f"Bearer {self.ai_config['api_key']}",
                    "Content-Type": "application/json"
                }
            )
    
    async def _call_ai_api(self, prompt: str) -> Dict[str, Any]:
        """调用AI API"""
        await self._ensure_ai_session()
        
        try:
            async with self.ai_session.post(
                "/v1/chat/completions",
                json={
                    "model": self.ai_config["model"],
                    "messages": [
                        {"role": "system", "content": self.ai_config["system_prompt"]},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": self.ai_config["temperature"],
                    "max_tokens": self.ai_config["max_tokens"],
                    "top_p": self.ai_config.get("top_p", 0.9),
                    "frequency_penalty": self.ai_config.get("frequency_penalty", 0.0),
                    "presence_penalty": self.ai_config.get("presence_penalty", 0.0)
                }
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return result["choices"][0]["message"]["content"]
                else:
                    error_text = await response.text()
                    logger.error(f"AI API error: {error_text}")
                    raise Exception(f"AI API error: {response.status}")
        except Exception as e:
            logger.error(f"Error calling AI API: {str(e)}")
            raise
    
    def _calculate_kdj(self, data: pd.DataFrame, n: int = 9, m1: int = 3, m2: int = 3) -> Dict[str, float]:
        """计算KDJ指标"""
        low_list = data['Low'].rolling(window=n, min_periods=1).min()
        high_list = data['High'].rolling(window=n, min_periods=1).max()
        rsv = (data['Close'] - low_list) / (high_list - low_list) * 100
        k = rsv.ewm(alpha=1/m1, adjust=False).mean()
        d = k.ewm(alpha=1/m2, adjust=False).mean()
        j = 3 * k - 2 * d
        return {
            "k": round(k.iloc[-1], 2),
            "d": round(d.iloc[-1], 2),
            "j": round(j.iloc[-1], 2)
        }
    
    def _calculate_obv(self, data: pd.DataFrame) -> Dict[str, float]:
        """计算OBV指标"""
        obv = (np.sign(data['Close'].diff()) * data['Volume']).fillna(0).cumsum()
        return {
            "current": round(obv.iloc[-1], 2),
            "change": round(obv.iloc[-1] - obv.iloc[-2], 2),
            "trend": "up" if obv.iloc[-1] > obv.iloc[-2] else "down"
        }
    
    def _calculate_cci(self, data: pd.DataFrame, period: int = 20) -> Dict[str, float]:
        """计算CCI指标"""
        tp = (data['High'] + data['Low'] + data['Close']) / 3
        tp_ma = tp.rolling(window=period).mean()
        tp_md = tp.rolling(window=period).apply(lambda x: np.abs(x - x.mean()).mean())
        cci = (tp - tp_ma) / (0.015 * tp_md)
        return {
            "current": round(cci.iloc[-1], 2),
            "previous": round(cci.iloc[-2], 2),
            "change": round(cci.iloc[-1] - cci.iloc[-2], 2)
        }
    
    def _calculate_dmi(self, data: pd.DataFrame, period: int = 14) -> Dict[str, float]:
        """计算DMI指标"""
        high = data['High']
        low = data['Low']
        close = data['Close']
        
        tr = pd.DataFrame()
        tr['h-l'] = high - low
        tr['h-pc'] = abs(high - close.shift(1))
        tr['l-pc'] = abs(low - close.shift(1))
        tr['tr'] = tr[['h-l', 'h-pc', 'l-pc']].max(axis=1)
        
        up_move = high - high.shift(1)
        down_move = low.shift(1) - low
        
        plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
        minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)
        
        plus_di = 100 * pd.Series(plus_dm).rolling(period).mean() / pd.Series(tr['tr']).rolling(period).mean()
        minus_di = 100 * pd.Series(minus_dm).rolling(period).mean() / pd.Series(tr['tr']).rolling(period).mean()
        
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = dx.rolling(period).mean()
        
        return {
            "plus_di": round(plus_di.iloc[-1], 2),
            "minus_di": round(minus_di.iloc[-1], 2),
            "adx": round(adx.iloc[-1], 2)
        }
    
    def _calculate_ichimoku(self, data: pd.DataFrame) -> Dict[str, float]:
        """计算一目均衡表"""
        high = data['High']
        low = data['Low']
        
        # 转换线
        conversion_line = (high.rolling(window=9).max() + low.rolling(window=9).min()) / 2
        # 基准线
        base_line = (high.rolling(window=26).max() + low.rolling(window=26).min()) / 2
        # 先行带A
        leading_span_a = (conversion_line + base_line) / 2
        # 先行带B
        leading_span_b = (high.rolling(window=52).max() + low.rolling(window=52).min()) / 2
        # 延迟线
        lagging_span = data['Close'].shift(-26)
        
        return {
            "conversion_line": round(conversion_line.iloc[-1], 2),
            "base_line": round(base_line.iloc[-1], 2),
            "leading_span_a": round(leading_span_a.iloc[-1], 2),
            "leading_span_b": round(leading_span_b.iloc[-1], 2),
            "lagging_span": round(lagging_span.iloc[-1], 2)
        }
    
    def _analyze_market_sentiment(self, data: pd.DataFrame) -> Dict[str, Any]:
        """分析市场情绪"""
        # 计算价格动量
        returns = data['Close'].pct_change()
        momentum = returns.rolling(window=20).mean()
        
        # 计算波动率
        volatility = returns.rolling(window=20).std()
        
        # 计算成交量趋势
        volume_ma = data['Volume'].rolling(window=20).mean()
        volume_trend = data['Volume'] / volume_ma
        
        # 计算市场情绪指标
        sentiment = {
            "momentum": "bullish" if momentum.iloc[-1] > 0 else "bearish",
            "volatility": "high" if volatility.iloc[-1] > self.risk_thresholds["volatility"] else "low",
            "volume_trend": "increasing" if volume_trend.iloc[-1] > 1 else "decreasing",
            "overall": "bullish" if (momentum.iloc[-1] > 0 and volume_trend.iloc[-1] > 1) else "bearish"
        }
        
        return sentiment
    
    def _check_risk_alerts(self, data: pd.DataFrame, indicators: Dict[str, Any]) -> List[Dict[str, Any]]:
        """检查风险预警"""
        alerts = []
        
        # 检查波动率
        returns = data['Close'].pct_change()
        if abs(returns.iloc[-1]) > self.risk_thresholds["volatility"]:
            alerts.append({
                "type": "volatility",
                "level": "warning",
                "message": f"价格波动超过{self.risk_thresholds['volatility']*100}%"
            })
        
        # 检查成交量异常
        volume_ma = data['Volume'].rolling(window=20).mean()
        if data['Volume'].iloc[-1] > volume_ma.iloc[-1] * self.risk_thresholds["volume_spike"]:
            alerts.append({
                "type": "volume",
                "level": "warning",
                "message": "成交量异常放大"
            })
        
        # 检查RSI极值
        if indicators["RSI"]["current"] < self.risk_thresholds["rsi_extreme"]:
            alerts.append({
                "type": "rsi",
                "level": "warning",
                "message": "RSI指标显示超卖"
            })
        elif indicators["RSI"]["current"] > 100 - self.risk_thresholds["rsi_extreme"]:
            alerts.append({
                "type": "rsi",
                "level": "warning",
                "message": "RSI指标显示超买"
            })
        
        # 检查布林带突破
        if data['Close'].iloc[-1] > indicators["BB"]["upper"]:
            alerts.append({
                "type": "bb",
                "level": "warning",
                "message": "价格突破布林带上轨"
            })
        elif data['Close'].iloc[-1] < indicators["BB"]["lower"]:
            alerts.append({
                "type": "bb",
                "level": "warning",
                "message": "价格突破布林带下轨"
            })
        
        return alerts
    
    def _prepare_ai_analysis_prompt(self, symbol: str, data: pd.DataFrame, indicators: Dict[str, Any]) -> str:
        """准备AI分析提示词"""
        current_price = data['Close'].iloc[-1]
        price_change = current_price - data['Close'].iloc[-2]
        price_change_pct = (price_change / data['Close'].iloc[-2]) * 100
        
        # 计算市场情绪
        sentiment = self._analyze_market_sentiment(data)
        
        prompt = f"""
        请对{symbol}进行全面的技术分析，包括以下数据：

        价格信息：
        - 当前价格: ${current_price:.2f}
        - 价格变化: ${price_change:.2f} ({price_change_pct:.2f}%)
        - 日内波动: {data['High'].iloc[-1]:.2f} - {data['Low'].iloc[-1]:.2f}

        技术指标：
        - RSI: {indicators['RSI']['current']} (前值: {indicators['RSI']['previous']})
        - MACD: {indicators['MACD']['macd']} (信号线: {indicators['MACD']['signal']})
        - 布林带: 上轨 ${indicators['BB']['upper']:.2f}, 中轨 ${indicators['BB']['middle']:.2f}, 下轨 ${indicators['BB']['lower']:.2f}
        - 移动平均线: MA20 ${indicators['MA']['MA20']:.2f}, MA50 ${indicators['MA']['MA50']:.2f}, MA200 ${indicators['MA']['MA200']:.2f}
        - KDJ: K={indicators['KDJ']['k']}, D={indicators['KDJ']['d']}, J={indicators['KDJ']['j']}
        - CCI: {indicators['CCI']['current']} (变化: {indicators['CCI']['change']})
        - DMI: +DI={indicators['DMI']['plus_di']}, -DI={indicators['DMI']['minus_di']}, ADX={indicators['DMI']['adx']}
        - 一目均衡表: 转换线={indicators['Ichimoku']['conversion_line']}, 基准线={indicators['Ichimoku']['base_line']}

        市场情绪：
        - 动量: {sentiment['momentum']}
        - 波动率: {sentiment['volatility']}
        - 成交量趋势: {sentiment['volume_trend']}
        - 整体情绪: {sentiment['overall']}

        请提供以下分析：
        1. 整体趋势分析（短期、中期、长期）
        2. 关键支撑和阻力位
        3. 交易信号和建议（包括入场点、止损位、目标位）
        4. 风险评估（包括技术面风险、市场风险、流动性风险）
        5. 成交量分析（包括成交量趋势、异常情况）
        6. 市场情绪分析（包括多空力量对比、市场情绪指标）
        7. 技术指标综合分析（包括指标背离、交叉信号）
        8. 交易策略建议（包括仓位管理、风险控制）

        请用专业的技术分析语言，给出详细的分析依据和逻辑推理过程。
        """
        return prompt
    
    def _prepare_prediction_prompt(self, symbol: str, data: pd.DataFrame, indicators: Dict[str, Any]) -> str:
        """准备预测提示词"""
        current_price = data['Close'].iloc[-1]
        price_change = current_price - data['Close'].iloc[-2]
        price_change_pct = (price_change / data['Close'].iloc[-2]) * 100
        
        # 计算市场情绪
        sentiment = self._analyze_market_sentiment(data)
        
        # 获取历史预测准确率
        accuracy = self._get_prediction_accuracy(symbol)
        
        prompt = f"""
        基于以下{symbol}的数据，预测未来5个交易日的价格走势：

        当前状态：
        - 当前价格: ${current_price:.2f}
        - 价格变化: ${price_change:.2f} ({price_change_pct:.2f}%)
        - 日内波动: {data['High'].iloc[-1]:.2f} - {data['Low'].iloc[-1]:.2f}

        技术指标：
        - RSI: {indicators['RSI']['current']} (前值: {indicators['RSI']['previous']})
        - MACD: {indicators['MACD']['macd']} (信号线: {indicators['MACD']['signal']})
        - 布林带: 上轨 ${indicators['BB']['upper']:.2f}, 中轨 ${indicators['BB']['middle']:.2f}, 下轨 ${indicators['BB']['lower']:.2f}
        - 移动平均线: MA20 ${indicators['MA']['MA20']:.2f}, MA50 ${indicators['MA']['MA50']:.2f}, MA200 ${indicators['MA']['MA200']:.2f}
        - KDJ: K={indicators['KDJ']['k']}, D={indicators['KDJ']['d']}, J={indicators['KDJ']['j']}
        - CCI: {indicators['CCI']['current']} (变化: {indicators['CCI']['change']})
        - DMI: +DI={indicators['DMI']['plus_di']}, -DI={indicators['DMI']['minus_di']}, ADX={indicators['DMI']['adx']}

        市场情绪：
        - 动量: {sentiment['momentum']}
        - 波动率: {sentiment['volatility']}
        - 成交量趋势: {sentiment['volume_trend']}
        - 整体情绪: {sentiment['overall']}

        历史预测准确率：{accuracy:.2f}%

        请提供：
        1. 未来5天的具体价格目标（包括最高价、最低价、收盘价）
        2. 预测的置信度（基于技术指标、市场情绪、历史准确率）
        3. 影响预测的关键因素（包括技术面、基本面、市场情绪）
        4. 需要考虑的风险因素（包括市场风险、技术风险、流动性风险）
        5. 预测的可靠性分析（包括历史准确率、当前市场环境、技术指标支持度）

        请用专业的技术分析语言，给出详细的分析依据和逻辑推理过程。
        """
        return prompt
    
    def _get_prediction_accuracy(self, symbol: str) -> float:
        """获取历史预测准确率"""
        predictions = self.prediction_history[symbol]
        if not predictions:
            return 0.0
        
        correct = sum(1 for p in predictions if p["accuracy"] > 0.7)
        return (correct / len(predictions)) * 100
    
    def _update_prediction_history(self, symbol: str, prediction: Dict[str, Any], actual_price: float):
        """更新预测历史记录"""
        if "targets" in prediction:
            target_price = float(prediction["targets"].split("$")[1].split()[0])
            accuracy = 1 - abs(target_price - actual_price) / actual_price
            self.prediction_history[symbol].append({
                "timestamp": datetime.now(),
                "predicted_price": target_price,
                "actual_price": actual_price,
                "accuracy": accuracy
            })
            
            # 只保留最近100条记录
            if len(self.prediction_history[symbol]) > 100:
                self.prediction_history[symbol] = self.prediction_history[symbol][-100:]
    
    async def _handle_sentiment_query(self, query: TradingQuery) -> Dict[str, Any]:
        """处理市场情绪查询"""
        try:
            # 获取历史数据
            ticker = self.yf.Ticker(query.symbol)
            hist = ticker.history(period="1mo")
            
            if hist.empty:
                return {
                    "success": False,
                    "error": f"No data available for {query.symbol}"
                }
            
            # 分析市场情绪
            sentiment = self._analyze_market_sentiment(hist)
            
            return {
                "success": True,
                "data": sentiment,
                "message": self._format_sentiment_message(sentiment, query.symbol)
            }
                
        except Exception as e:
            logger.error(f"Error handling sentiment query: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _handle_risk_alert_query(self, query: TradingQuery) -> Dict[str, Any]:
        """处理风险预警查询"""
        try:
            # 获取历史数据
            ticker = self.yf.Ticker(query.symbol)
            hist = ticker.history(period="1mo")
            
            if hist.empty:
                return {
                    "success": False,
                    "error": f"No data available for {query.symbol}"
                }
            
            # 计算技术指标
            indicators = {}
            for name, calculator in self.technical_indicators.items():
                indicators[name] = calculator(hist)
            
            # 检查风险预警
            alerts = self._check_risk_alerts(hist, indicators)
            
            return {
                "success": True,
                "data": alerts,
                "message": self._format_risk_alert_message(alerts, query.symbol)
            }
                
        except Exception as e:
            logger.error(f"Error handling risk alert query: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _format_sentiment_message(self, sentiment: Dict[str, Any], symbol: str) -> str:
        """格式化市场情绪消息"""
        message = f"📊 {symbol} 市场情绪分析:\n\n"
        
        # 添加情绪指标
        message += "情绪指标:\n"
        message += f"动量: {'🟢' if sentiment['momentum'] == 'bullish' else '🔴'} {sentiment['momentum']}\n"
        message += f"波动率: {'⚠️' if sentiment['volatility'] == 'high' else '✅'} {sentiment['volatility']}\n"
        message += f"成交量趋势: {'📈' if sentiment['volume_trend'] == 'increasing' else '📉'} {sentiment['volume_trend']}\n"
        message += f"整体情绪: {'🟢' if sentiment['overall'] == 'bullish' else '🔴'} {sentiment['overall']}\n\n"
        
        message += f"更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        return message
    
    def _format_risk_alert_message(self, alerts: List[Dict[str, Any]], symbol: str) -> str:
        """格式化风险预警消息"""
        if not alerts:
            return f"✅ {symbol} 当前无风险预警"
        
        message = f"⚠️ {symbol} 风险预警:\n\n"
        
        for alert in alerts:
            level_emoji = "🔴" if alert["level"] == "critical" else "🟡" if alert["level"] == "warning" else "🔵"
            message += f"{level_emoji} {alert['type'].upper()}: {alert['message']}\n"
        
        message += f"\n更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        return message
    
    async def process_query(self, symbol: str, query_type: str, **kwargs) -> Dict[str, Any]:
        """
        Process trading query
        
        Args:
            symbol: Trading symbol (any valid stock symbol)
            query_type: Type of query (price, volume, technical, fundamental, ai_analysis, prediction)
            **kwargs: Additional query parameters
            
        Returns:
            Dict containing query results
        """
        logger.info(f"Processing query - Symbol: {symbol}, Type: {query_type}, Params: {kwargs}")
        
        if query_type not in self.supported_queries:
            error_msg = f"Unsupported query type: {query_type}. Supported types are: {', '.join(self.supported_queries.keys())}"
            logger.warning(error_msg)
            return {
                "success": False,
                "error": error_msg
            }
        
        # Create query object
        query = TradingQuery(
            symbol=symbol,
            query_type=query_type,
            **kwargs
        )
        
        # Process query
        handler = self.supported_queries[query_type]
        logger.info(f"Executing {query_type} query handler for {symbol}")
        result = await handler(query)
        logger.info(f"Query result: {result}")
        return result
    
    async def _handle_price_query(self, query: TradingQuery) -> Dict[str, Any]:
        """Handle price-related queries"""
        try:
            # 尝试从配置中获取symbol信息，如果不存在则使用默认值
            symbol_info = self.trading_config["symbols"].get(query.symbol, {
                "name": query.symbol,
                "type": "stock",
                "description": f"{query.symbol} Stock",
                "data_providers": ["yahoo_finance"]
            })
            
            # 首先尝试使用MCP
            if self.mcp and self.mcp.enabled:
                try:
                    response = await self.mcp.send_command(
                        "get_price",
                        {
                            "symbol": query.symbol,
                            "timeframe": query.timeframe,
                            "type": symbol_info["type"],
                            "data_providers": symbol_info["data_providers"]
                        }
                    )
                    if response.success:
                        return {
                            "success": True,
                            "data": response.data,
                            "message": self._format_price_message(response.data, symbol_info)
                        }
                except Exception as e:
                    logger.warning(f"MCP price query failed, falling back to direct data source: {str(e)}")
            
            # 如果MCP不可用或失败，使用yfinance直接获取数据
            ticker = self.yf.Ticker(query.symbol)
            hist = ticker.history(period="1d")
            if hist.empty:
                return {
                    "success": False,
                    "error": f"No data available for {query.symbol}"
                }
            
            current_price = hist['Close'].iloc[-1]
            prev_close = hist['Open'].iloc[0]
            change = current_price - prev_close
            change_percent = (change / prev_close) * 100
            
            data = {
                "current": round(current_price, 2),
                "change": round(change, 2),
                "change_percent": round(change_percent, 2),
                "high": round(hist['High'].iloc[-1], 2),
                "low": round(hist['Low'].iloc[-1], 2),
                "open": round(hist['Open'].iloc[-1], 2),
                "prev_close": round(prev_close, 2)
            }
            
            return {
                "success": True,
                "data": data,
                "message": self._format_price_message(data, symbol_info)
            }
            
        except Exception as e:
            logger.error(f"Error handling price query: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _handle_volume_query(self, query: TradingQuery) -> Dict[str, Any]:
        """Handle volume-related queries"""
        try:
            # 尝试从配置中获取symbol信息，如果不存在则使用默认值
            symbol_info = self.trading_config["symbols"].get(query.symbol, {
                "name": query.symbol,
                "type": "stock",
                "description": f"{query.symbol} Stock",
                "data_providers": ["yahoo_finance"]
            })
            # 首先尝试使用MCP
            if self.mcp and self.mcp.enabled:
                try:
                    response = await self.mcp.send_command(
                        "get_volume",
                        {
                            "symbol": query.symbol,
                            "timeframe": query.timeframe,
                            "type": symbol_info["type"],
                            "data_providers": symbol_info["data_providers"]
                        }
                    )
                    if response.success:
                        return {
                            "success": True,
                            "data": response.data,
                            "message": self._format_volume_message(response.data, symbol_info)
                        }
                except Exception as e:
                    logger.warning(f"MCP volume query failed, falling back to direct data source: {str(e)}")
            # 如果MCP不可用或失败，使用yfinance直接获取数据
            ticker = self.yf.Ticker(query.symbol)
            hist = ticker.history(period="5d")  # 获取5天数据来计算平均值
            if hist.empty:
                return {
                    "success": False,
                    "error": f"No data available for {query.symbol}"
                }
            current_volume = hist['Volume'].iloc[-1]
            avg_volume = hist['Volume'].mean()
            prev_volume = hist['Volume'].iloc[-2]
            volume_change = current_volume - prev_volume
            volume_change_percent = (volume_change / prev_volume) * 100
            data = {
                "current": int(current_volume),
                "average": int(avg_volume),
                "change": int(volume_change),
                "change_percent": round(volume_change_percent, 2)
            }
            return {
                "success": True,
                "data": data,
                "message": self._format_volume_message(data, symbol_info)
            }
        except Exception as e:
            logger.error(f"Error handling volume query: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _handle_technical_query(self, query: TradingQuery) -> Dict[str, Any]:
        """Handle technical analysis queries"""
        try:
            # 尝试从配置中获取symbol信息，如果不存在则使用默认值
            symbol_info = self.trading_config["symbols"].get(query.symbol, {
                "name": query.symbol,
                "type": "stock",
                "description": f"{query.symbol} Stock",
                "data_providers": ["polygon", "tradier", "yahoo_finance"]
            })
            
            # Use default indicators if none specified
            indicators = query.indicators or self.trading_config["indicators"]["technical"]
            
            response = await self.mcp.send_command(
                "get_technical",
                {
                    "symbol": query.symbol,
                    "timeframe": query.timeframe,
                    "type": symbol_info["type"],
                    "data_providers": symbol_info["data_providers"],
                    "indicators": indicators
                }
            )
            
            if response.success:
                return {
                    "success": True,
                    "data": response.data,
                    "message": self._format_technical_message(response.data, symbol_info)
                }
            else:
                return {
                    "success": False,
                    "error": response.error
                }
                
        except Exception as e:
            logger.error(f"Error handling technical query: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _handle_fundamental_query(self, query: TradingQuery) -> Dict[str, Any]:
        """Handle fundamental analysis queries"""
        try:
            # 尝试从配置中获取symbol信息，如果不存在则使用默认值
            symbol_info = self.trading_config["symbols"].get(query.symbol, {
                "name": query.symbol,
                "type": "stock",
                "description": f"{query.symbol} Stock",
                "data_providers": ["polygon", "tradier", "yahoo_finance"]
            })
            
            response = await self.mcp.send_command(
                "get_fundamental",
                {
                    "symbol": query.symbol,
                    "type": symbol_info["type"],
                    "data_providers": symbol_info["data_providers"]
                }
            )
            
            if response.success:
                return {
                    "success": True,
                    "data": response.data,
                    "message": self._format_fundamental_message(response.data, symbol_info)
                }
            else:
                return {
                    "success": False,
                    "error": response.error
                }
                
        except Exception as e:
            logger.error(f"Error handling fundamental query: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _handle_ai_analysis_query(self, query: TradingQuery) -> Dict[str, Any]:
        """Handle AI analysis queries with enhanced alert recommendations"""
        try:
            ticker = self.yf.Ticker(query.symbol)
            hist = ticker.history(period="1mo")
            if hist.empty:
                return {"success": False, "error": f"No data available for {query.symbol}"}
            indicators = {}
            for name, calculator in self.technical_indicators.items():
                indicators[name] = calculator(hist)
            fundamentals = await self.data_processor.get_fundamentals(query.symbol)
            money_flow = await self.data_processor.get_money_flow(query.symbol)
            options_data = await self.data_processor.get_options_data(query.symbol)
            prompt = self._prepare_enhanced_ai_analysis_prompt(
                query.symbol, hist, indicators, fundamentals, money_flow, options_data)
            analysis_text = await self.ai_processor.generate_response(prompt)
            analysis = self._parse_ai_analysis(analysis_text)
            alert_recommendations = await self.ai_processor.generate_alert_recommendations(analysis_text)
            return {
                "success": True,
                "data": {
                    "analysis": analysis,
                    "indicators": indicators,
                    "fundamentals": fundamentals,
                    "money_flow": money_flow,
                    "options_data": options_data,
                    "alert_recommendations": alert_recommendations
                },
                "message": self._format_enhanced_ai_analysis_message(
                    analysis, indicators, fundamentals, money_flow, options_data, alert_recommendations, query.symbol)
            }
        except Exception as e:
            logger.error(f"Error handling AI analysis query: {str(e)}")
            return {"success": False, "error": str(e)}

    def _prepare_enhanced_ai_analysis_prompt(self, symbol: str, data: pd.DataFrame, 
                                           indicators: Dict[str, Any], fundamentals: Dict[str, Any],
                                           money_flow: Dict[str, Any], options_data: Dict[str, Any]) -> str:
        """准备增强版AI分析提示词"""
        try:
            current_price = data['Close'].iloc[-1]
            price_change = current_price - data['Close'].iloc[-2]
            price_change_pct = (price_change / data['Close'].iloc[-2]) * 100
            sentiment = self._analyze_market_sentiment(data)
            prompt = f"""
请对{symbol}进行全面的技术分析，包括以下数据：
价格信息：
- 当前价格: ${current_price:.2f}
- 价格变化: ${price_change:.2f} ({price_change_pct:.2f}%)
- 日内波动: {data['High'].iloc[-1]:.2f} - {data['Low'].iloc[-1]:.2f}
技术指标：
- RSI: {indicators['RSI']['current']} (前值: {indicators['RSI']['previous']})
- MACD: {indicators['MACD']['macd']} (信号线: {indicators['MACD']['signal']})
- 布林带: 上轨 ${indicators['BB']['upper']:.2f}, 中轨 ${indicators['BB']['middle']:.2f}, 下轨 ${indicators['BB']['lower']:.2f}
- 移动平均线: MA20 ${indicators['MA']['MA20']:.2f}, MA50 ${indicators['MA']['MA50']:.2f}, MA200 ${indicators['MA']['MA200']:.2f}
- KDJ: K={indicators['KDJ']['k']}, D={indicators['KDJ']['d']}, J={indicators['KDJ']['j']}
- CCI: {indicators['CCI']['current']} (变化: {indicators['CCI']['change']})
- DMI: +DI={indicators['DMI']['plus_di']}, -DI={indicators['DMI']['minus_di']}, ADX={indicators['DMI']['adx']}
- 一目均衡表: 转换线={indicators['Ichimoku']['conversion_line']}, 基准线={indicators['Ichimoku']['base_line']}
基本面数据：
- PE比率: {fundamentals.get('pe_ratio', 'N/A')}
- EPS: {fundamentals.get('eps', 'N/A')}
- 市值: {fundamentals.get('market_cap', 'N/A')}
- 股息率: {fundamentals.get('dividend_yield', 'N/A')}
- Beta系数: {fundamentals.get('beta', 'N/A')}
资金流数据：
- 资金净流入: {money_flow.get('net_flow', 'N/A')}
- 机构资金流向: {money_flow.get('institutional_flow', 'N/A')}
- 散户资金流向: {money_flow.get('retail_flow', 'N/A')}
期权数据：
- 看跌/看涨比率: {options_data.get('put_call_ratio', 'N/A')}
- 隐含波动率: {options_data.get('implied_volatility', 'N/A')}
- 未平仓合约: {options_data.get('open_interest', 'N/A')}
- 期权成交量: {options_data.get('volume', 'N/A')}
市场情绪：
- 动量: {sentiment['momentum']}
- 波动率: {sentiment['volatility']}
- 成交量趋势: {sentiment['volume_trend']}
- 整体情绪: {sentiment['overall']}
请提供以下分析：
1. 整体趋势分析（短期、中期、长期）
2. 关键支撑和阻力位
3. 交易信号和建议（包括入场点、止损位、目标位）
4. 风险评估（包括技术面风险、市场风险、流动性风险）
5. 成交量分析（包括成交量趋势、异常情况）
6. 市场情绪分析（包括多空力量对比、市场情绪指标）
7. 技术指标综合分析（包括指标背离、交叉信号）
8. 交易策略建议（包括仓位管理、风险控制）
9. 预警建议（基于当前市场状态，推荐4个最重要的监控点）
请用专业的技术分析语言，给出详细的分析依据和逻辑推理过程。
"""
            return prompt
        except Exception as e:
            logger.error(f"Error preparing AI analysis prompt: {str(e)}")
            return ""

    def _format_enhanced_ai_analysis_message(self, analysis: Dict[str, Any], indicators: Dict[str, Any],
                                           fundamentals: Dict[str, Any], money_flow: Dict[str, Any],
                                           options_data: Dict[str, Any], alert_recommendations: List[Dict[str, Any]],
                                           symbol: str) -> str:
        """格式化增强版AI分析消息"""
        try:
            message = f"🤖 {symbol} AI分析报告:\n\n"
            message += "📊 技术指标:\n"
            message += f"RSI: {indicators['RSI']['current']} ({'超买' if indicators['RSI']['current'] > 70 else '超卖' if indicators['RSI']['current'] < 30 else '中性'})\n"
            message += f"MACD: {indicators['MACD']['macd']} (信号线: {indicators['MACD']['signal']})\n"
            message += f"布林带: ${indicators['BB']['upper']:.2f} | ${indicators['BB']['middle']:.2f} | ${indicators['BB']['lower']:.2f}\n"
            message += f"移动平均线: 20日 ${indicators['MA']['MA20']:.2f}, 50日 ${indicators['MA']['MA50']:.2f}, 200日 ${indicators['MA']['MA200']:.2f}\n\n"
            message += "📈 基本面数据:\n"
            message += f"PE比率: {fundamentals.get('pe_ratio', 'N/A')}\n"
            message += f"EPS: {fundamentals.get('eps', 'N/A')}\n"
            message += f"市值: {fundamentals.get('market_cap', 'N/A')}\n"
            message += f"股息率: {fundamentals.get('dividend_yield', 'N/A')}\n"
            message += f"Beta系数: {fundamentals.get('beta', 'N/A')}\n\n"
            message += "💰 资金流数据:\n"
            message += f"资金净流入: {money_flow.get('net_flow', 'N/A')}\n"
            message += f"机构资金流向: {money_flow.get('institutional_flow', 'N/A')}\n"
            message += f"散户资金流向: {money_flow.get('retail_flow', 'N/A')}\n\n"
            message += "📊 期权数据:\n"
            message += f"看跌/看涨比率: {options_data.get('put_call_ratio', 'N/A')}\n"
            message += f"隐含波动率: {options_data.get('implied_volatility', 'N/A')}\n"
            message += f"未平仓合约: {options_data.get('open_interest', 'N/A')}\n"
            message += f"期权成交量: {options_data.get('volume', 'N/A')}\n\n"
            message += "🔍 趋势分析:\n"
            message += f"{analysis.get('trend', 'N/A')}\n\n"
            message += "🎯 支撑/阻力位:\n"
            message += f"{analysis.get('levels', 'N/A')}\n\n"
            message += "💡 交易信号:\n"
            message += f"{analysis.get('signals', 'N/A')}\n\n"
            message += "⚠️ 风险评估:\n"
            message += f"{analysis.get('risk', 'N/A')}\n\n"
            message += "📈 成交量分析:\n"
            message += f"{analysis.get('volume', 'N/A')}\n\n"
            message += "🔔 预警推荐:\n"
            for alert in alert_recommendations:
                level_emoji = "🔴" if alert["level"] == "critical" else "🟡" if alert["level"] == "warning" else "🔵"
                message += f"{level_emoji} {alert['message']}\n"
                message += f"   类型: {alert['type']}\n"
                message += f"   阈值: {alert['threshold']}\n"
                message += f"   方向: {alert['direction']}\n\n"
            message += f"更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            return message
        except Exception as e:
            logger.error(f"Error formatting AI analysis message: {str(e)}")
            return ""

    def _parse_ai_analysis(self, text: str) -> Dict[str, str]:
        """解析AI分析文本"""
        try:
            sections = {"trend": "", "levels": "", "signals": "", "risk": "", "volume": ""}
            current_section = None
            for line in text.split("\n"):
                line = line.strip()
                if not line:
                    continue
                if "趋势分析" in line:
                    current_section = "trend"
                elif "支撑/阻力位" in line:
                    current_section = "levels"
                elif "交易信号" in line:
                    current_section = "signals"
                elif "风险评估" in line:
                    current_section = "risk"
                elif "成交量分析" in line:
                    current_section = "volume"
                elif current_section:
                    sections[current_section] += line + "\n"
            return sections
        except Exception as e:
            logger.error(f"Error parsing AI analysis text: {str(e)}")
            return {"trend": "", "levels": "", "signals": "", "risk": "", "volume": ""}
    
    def _format_price_message(self, data: Dict[str, Any], symbol_info: Dict[str, Any]) -> str:
        """Format price data into message"""
        change_symbol = "🟢" if data.get("change", 0) >= 0 else "🔴"
        return (
            f"{symbol_info['name']} ({symbol_info['type'].upper()}) Price Information:\n"
            f"Current: ${data.get('current', 'N/A')} {change_symbol}\n"
            f"Change: ${data.get('change', 'N/A')} ({data.get('change_percent', 'N/A')}%)\n"
            f"High: ${data.get('high', 'N/A')}\n"
            f"Low: ${data.get('low', 'N/A')}\n"
            f"Open: ${data.get('open', 'N/A')}\n"
            f"Previous Close: ${data.get('prev_close', 'N/A')}\n"
            f"Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
    
    def _format_volume_message(self, data: Dict[str, Any], symbol_info: Dict[str, Any]) -> str:
        """Format volume data into message"""
        change_symbol = "🟢" if data.get("change", 0) >= 0 else "🔴"
        return (
            f"{symbol_info['name']} ({symbol_info['type'].upper()}) Volume Information:\n"
            f"Current: {data.get('current', 'N/A'):,} {change_symbol}\n"
            f"Average: {data.get('average', 'N/A'):,}\n"
            f"Change: {data.get('change', 'N/A'):,} ({data.get('change_percent', 'N/A')}%)\n"
            f"Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
    
    def _format_technical_message(self, data: Dict[str, Any], symbol_info: Dict[str, Any]) -> str:
        """Format technical analysis data into message"""
        message = f"{symbol_info['name']} ({symbol_info['type'].upper()}) Technical Analysis:\n"
        
        for indicator, values in data.items():
            message += f"\n{indicator}:\n"
            for key, value in values.items():
                message += f"{key}: {value}\n"
        
        message += f"\nLast Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        return message
    
    def _format_fundamental_message(self, data: Dict[str, Any], symbol_info: Dict[str, Any]) -> str:
        """Format fundamental data into message"""
        return (
            f"{symbol_info['name']} ({symbol_info['type'].upper()}) Fundamental Analysis:\n"
            f"Market Cap: {data.get('market_cap', 'N/A')}\n"
            f"P/E Ratio: {data.get('pe_ratio', 'N/A')}\n"
            f"EPS: {data.get('eps', 'N/A')}\n"
            f"Dividend Yield: {data.get('dividend_yield', 'N/A')}\n"
            f"52 Week High: {data.get('52w_high', 'N/A')}\n"
            f"52 Week Low: {data.get('52w_low', 'N/A')}\n"
            f"Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
    
    async def _handle_chart_query(self, query: TradingQuery) -> Dict[str, Any]:
        """处理图表查询"""
        try:
            # 获取历史数据
            data = self.yf.download(
                query.symbol,
                period=f"{query.params.get('days', 30)}d",
                interval=query.timeframe
            )
            
            if data.empty:
                return {
                    "success": False,
                    "error": f"无法获取 {query.symbol} 的历史数据"
                }
            
            # 创建图表
            fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 10), 
                                               gridspec_kw={'height_ratios': [3, 1, 1]})
            
            # 绘制价格和均线
            ax1.plot(data.index, data['Close'], label='收盘价', color='black', linewidth=1)
            ax1.plot(data.index, data['Close'].rolling(window=20).mean(), 
                    label='20日均线', color='blue', linewidth=1)
            ax1.plot(data.index, data['Close'].rolling(window=50).mean(), 
                    label='50日均线', color='red', linewidth=1)
            
            # 绘制布林带
            bb = self._calculate_bollinger_bands(data)
            ax1.plot(data.index, bb['upper'], 'k--', label='布林上轨', alpha=0.5)
            ax1.plot(data.index, bb['lower'], 'k--', label='布林下轨', alpha=0.5)
            ax1.fill_between(data.index, bb['upper'], bb['lower'], color='gray', alpha=0.1)
            
            # 设置标题和标签
            current_price = data['Close'].iloc[-1]
            change_pct = (data['Close'].iloc[-1] / data['Close'].iloc[-2] - 1) * 100
            title = f"{query.symbol}: ${current_price:.2f} ({'+' if change_pct >= 0 else ''}{change_pct:.2f}%)"
            ax1.set_title(title, fontsize=14)
            ax1.set_ylabel('价格 ($)', fontsize=12)
            ax1.grid(True, alpha=0.3)
            ax1.legend()
            
            # 绘制成交量
            pos_idx = data['Close'] >= data['Open']
            neg_idx = data['Close'] < data['Open']
            ax2.bar(data.index[pos_idx], data['Volume'][pos_idx], 
                   color='green', alpha=0.5, width=0.8)
            ax2.bar(data.index[neg_idx], data['Volume'][neg_idx], 
                   color='red', alpha=0.5, width=0.8)
            ax2.set_ylabel('成交量', fontsize=12)
            ax2.grid(True, alpha=0.3)
            
            # 绘制MACD
            macd = self._calculate_macd(data)
            ax3.plot(data.index, macd['macd'], label='MACD', color='blue', linewidth=1)
            ax3.plot(data.index, macd['signal'], label='信号线', color='red', linewidth=1)
            ax3.bar(data.index, macd['histogram'], label='柱状图', color='green', alpha=0.5)
            ax3.set_ylabel('MACD', fontsize=12)
            ax3.grid(True, alpha=0.3)
            ax3.legend()
            
            # 格式化日期
            ax1.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
            ax1.xaxis.set_major_locator(mdates.WeekdayLocator(interval=1))
            
            plt.tight_layout()
            
            # 保存图表
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            chart_path = f"{self.chart_dir}/{query.symbol}_{timestamp}.png"
            plt.savefig(chart_path)
            plt.close()
            
            return {
                "success": True,
                "chart_path": chart_path,
                "message": f"已生成 {query.symbol} 的技术分析图表"
            }
            
        except Exception as e:
            logger.error(f"生成图表时出错: {str(e)}")
            return {
                "success": False,
                "error": f"生成图表时出错: {str(e)}"
            } 