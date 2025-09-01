"""
Signal Generator Module
"""

import os
import sys
import time
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import numpy as np
import pandas as pd
import talib

from core.exceptions import SignalGenerationError, ValidationError
from core.config import get_config

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join('logs', 'signal_generator.log')),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger('SignalGenerator')


class SignalType(Enum):
    """信号类型枚举"""
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    STRONG_BUY = "strong_buy"
    STRONG_SELL = "strong_sell"


class SignalStrength(Enum):
    """信号强度枚举"""
    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"
    VERY_STRONG = "very_strong"


@dataclass
class TradingSignal:
    """交易信号数据类"""
    symbol: str
    signal_type: SignalType
    strength: SignalStrength
    confidence: float
    price: float
    timestamp: datetime
    indicators: Dict[str, Any]
    reasoning: str
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None


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
    vwap: Optional[float] = None


class TechnicalIndicators:
    """技术指标计算器"""
    
    def __init__(self):
        self.config = get_config()
    
    def calculate_rsi(self, prices: List[float], period: int = 14) -> float:
        """计算RSI指标"""
        try:
            if len(prices) < period + 1:
                return 50.0  # 默认中性值
            
            prices_array = np.array(prices)
            rsi = talib.RSI(prices_array, timeperiod=period)
            return float(rsi[-1]) if not np.isnan(rsi[-1]) else 50.0
        
        except Exception as e:
            logger.error(f"计算RSI失败: {e}")
            return 50.0
    
    def calculate_macd(self, prices: List[float], fast_period: int = 12, slow_period: int = 26, signal_period: int = 9) -> Dict[str, float]:
        """计算MACD指标"""
        try:
            if len(prices) < slow_period + signal_period:
                return {"macd": 0.0, "signal": 0.0, "histogram": 0.0}
            
            prices_array = np.array(prices)
            macd, signal, histogram = talib.MACD(prices_array, fastperiod=fast_period, slowperiod=slow_period, signalperiod=signal_period)
            
            return {
                "macd": float(macd[-1]) if not np.isnan(macd[-1]) else 0.0,
                "signal": float(signal[-1]) if not np.isnan(signal[-1]) else 0.0,
                "histogram": float(histogram[-1]) if not np.isnan(histogram[-1]) else 0.0
            }
        
        except Exception as e:
            logger.error(f"计算MACD失败: {e}")
            return {"macd": 0.0, "signal": 0.0, "histogram": 0.0}
    
    def calculate_bollinger_bands(self, prices: List[float], period: int = 20, std_dev: float = 2.0) -> Dict[str, float]:
        """计算布林带"""
        try:
            if len(prices) < period:
                return {"upper": 0.0, "middle": 0.0, "lower": 0.0}
            
            prices_array = np.array(prices)
            upper, middle, lower = talib.BBANDS(prices_array, timeperiod=period, nbdevup=std_dev, nbdevdn=std_dev)
            
            return {
                "upper": float(upper[-1]) if not np.isnan(upper[-1]) else 0.0,
                "middle": float(middle[-1]) if not np.isnan(middle[-1]) else 0.0,
                "lower": float(lower[-1]) if not np.isnan(lower[-1]) else 0.0
            }
        
        except Exception as e:
            logger.error(f"计算布林带失败: {e}")
            return {"upper": 0.0, "middle": 0.0, "lower": 0.0}
    
    def calculate_moving_averages(self, prices: List[float], periods: List[int] = [5, 10, 20, 50]) -> Dict[str, float]:
        """计算移动平均线"""
        try:
            result = {}
            prices_array = np.array(prices)
            
            for period in periods:
                if len(prices) >= period:
                    ma = talib.SMA(prices_array, timeperiod=period)
                    result[f"sma_{period}"] = float(ma[-1]) if not np.isnan(ma[-1]) else 0.0
                else:
                    result[f"sma_{period}"] = 0.0
            
            return result
        
        except Exception as e:
            logger.error(f"计算移动平均线失败: {e}")
            return {f"sma_{period}": 0.0 for period in periods}
    
    def calculate_stochastic(self, high_prices: List[float], low_prices: List[float], close_prices: List[float], 
                           k_period: int = 14, d_period: int = 3) -> Dict[str, float]:
        """计算随机指标"""
        try:
            if len(close_prices) < k_period:
                return {"k": 50.0, "d": 50.0}
            
            high_array = np.array(high_prices)
            low_array = np.array(low_prices)
            close_array = np.array(close_prices)
            
            slowk, slowd = talib.STOCH(high_array, low_array, close_array, fastk_period=k_period, slowk_period=d_period, slowd_period=d_period)
            
            return {
                "k": float(slowk[-1]) if not np.isnan(slowk[-1]) else 50.0,
                "d": float(slowd[-1]) if not np.isnan(slowd[-1]) else 50.0
            }
        
        except Exception as e:
            logger.error(f"计算随机指标失败: {e}")
            return {"k": 50.0, "d": 50.0}
    
    def calculate_atr(self, high_prices: List[float], low_prices: List[float], close_prices: List[float], period: int = 14) -> float:
        """计算ATR指标"""
        try:
            if len(close_prices) < period:
                return 0.0
            
            high_array = np.array(high_prices)
            low_array = np.array(low_prices)
            close_array = np.array(close_prices)
            
            atr = talib.ATR(high_array, low_array, close_array, timeperiod=period)
            return float(atr[-1]) if not np.isnan(atr[-1]) else 0.0
        
        except Exception as e:
            logger.error(f"计算ATR失败: {e}")
            return 0.0


class SignalAnalyzer:
    """信号分析器"""
    
    def __init__(self):
        self.indicators = TechnicalIndicators()
        self.config = get_config()
    
    def analyze_technical_signals(self, market_data: List[MarketData]) -> Dict[str, Any]:
        """分析技术信号"""
        try:
            if len(market_data) < 50:
                return {"status": "insufficient_data"}
            
            # 提取价格数据
            close_prices = [data.close_price for data in market_data]
            high_prices = [data.high_price for data in market_data]
            low_prices = [data.low_price for data in market_data]
            volumes = [data.volume for data in market_data]
            
            # 计算技术指标
            rsi = self.indicators.calculate_rsi(close_prices)
            macd = self.indicators.calculate_macd(close_prices)
            bb = self.indicators.calculate_bollinger_bands(close_prices)
            ma = self.indicators.calculate_moving_averages(close_prices)
            stoch = self.indicators.calculate_stochastic(high_prices, low_prices, close_prices)
            atr = self.indicators.calculate_atr(high_prices, low_prices, close_prices)
            
            # 分析信号
            signal_analysis = self._analyze_signals(rsi, macd, bb, ma, stoch, close_prices[-1])
            
            return {
                "status": "success",
                "indicators": {
                    "rsi": rsi,
                    "macd": macd,
                    "bollinger_bands": bb,
                    "moving_averages": ma,
                    "stochastic": stoch,
                    "atr": atr
                },
                "signal_analysis": signal_analysis,
                "current_price": close_prices[-1],
                "volume": volumes[-1] if volumes else 0
            }
        
        except Exception as e:
            logger.error(f"分析技术信号失败: {e}")
            raise SignalGenerationError(f"分析技术信号失败: {e}")
    
    def _analyze_signals(self, rsi: float, macd: Dict[str, float], bb: Dict[str, float], 
                        ma: Dict[str, float], stoch: Dict[str, float], current_price: float) -> Dict[str, Any]:
        """分析各种信号"""
        signals = []
        reasoning = []
        
        # RSI分析
        if rsi < 30:
            signals.append(("rsi", SignalType.STRONG_BUY, SignalStrength.STRONG))
            reasoning.append(f"RSI超卖 ({rsi:.2f})")
        elif rsi < 40:
            signals.append(("rsi", SignalType.BUY, SignalStrength.MODERATE))
            reasoning.append(f"RSI偏低 ({rsi:.2f})")
        elif rsi > 70:
            signals.append(("rsi", SignalType.STRONG_SELL, SignalStrength.STRONG))
            reasoning.append(f"RSI超买 ({rsi:.2f})")
        elif rsi > 60:
            signals.append(("rsi", SignalType.SELL, SignalStrength.MODERATE))
            reasoning.append(f"RSI偏高 ({rsi:.2f})")
        
        # MACD分析
        if macd["histogram"] > 0 and macd["macd"] > macd["signal"]:
            signals.append(("macd", SignalType.BUY, SignalStrength.MODERATE))
            reasoning.append("MACD金叉")
        elif macd["histogram"] < 0 and macd["macd"] < macd["signal"]:
            signals.append(("macd", SignalType.SELL, SignalStrength.MODERATE))
            reasoning.append("MACD死叉")
        
        # 布林带分析
        if current_price < bb["lower"]:
            signals.append(("bb", SignalType.BUY, SignalStrength.STRONG))
            reasoning.append("价格触及布林带下轨")
        elif current_price > bb["upper"]:
            signals.append(("bb", SignalType.SELL, SignalStrength.STRONG))
            reasoning.append("价格触及布林带上轨")
        
        # 移动平均线分析
        if "sma_5" in ma and "sma_20" in ma:
            if ma["sma_5"] > ma["sma_20"]:
                signals.append(("ma", SignalType.BUY, SignalStrength.MODERATE))
                reasoning.append("短期均线上穿长期均线")
            elif ma["sma_5"] < ma["sma_20"]:
                signals.append(("ma", SignalType.SELL, SignalStrength.MODERATE))
                reasoning.append("短期均线下穿长期均线")
        
        # 随机指标分析
        if stoch["k"] < 20:
            signals.append(("stoch", SignalType.BUY, SignalStrength.STRONG))
            reasoning.append(f"随机指标超卖 ({stoch['k']:.2f})")
        elif stoch["k"] > 80:
            signals.append(("stoch", SignalType.SELL, SignalStrength.STRONG))
            reasoning.append(f"随机指标超买 ({stoch['k']:.2f})")
        
        # 综合信号分析
        return self._combine_signals(signals, reasoning)
    
    def _combine_signals(self, signals: List[Tuple[str, SignalType, SignalStrength]], 
                        reasoning: List[str]) -> Dict[str, Any]:
        """综合信号分析"""
        if not signals:
            return {
                "signal_type": SignalType.HOLD,
                "strength": SignalStrength.WEAK,
                "confidence": 0.5,
                "reasoning": "无明显信号"
            }
        
        # 统计信号
        buy_signals = [s for s in signals if s[1] in [SignalType.BUY, SignalType.STRONG_BUY]]
        sell_signals = [s for s in signals if s[1] in [SignalType.SELL, SignalType.STRONG_SELL]]
        
        # 计算信号强度
        buy_strength = sum(self._strength_to_value(s[2]) for s in buy_signals)
        sell_strength = sum(self._strength_to_value(s[2]) for s in sell_signals)
        
        # 确定信号类型
        if buy_strength > sell_strength and buy_strength > 0:
            if buy_strength >= 3:
                signal_type = SignalType.STRONG_BUY
            else:
                signal_type = SignalType.BUY
            strength_value = buy_strength
        elif sell_strength > buy_strength and sell_strength > 0:
            if sell_strength >= 3:
                signal_type = SignalType.STRONG_SELL
            else:
                signal_type = SignalType.SELL
            strength_value = sell_strength
        else:
            signal_type = SignalType.HOLD
            strength_value = 0
        
        # 计算置信度
        total_signals = len(signals)
        confidence = min(0.95, 0.5 + (strength_value / total_signals) * 0.4) if total_signals > 0 else 0.5
        
        # 确定信号强度
        if strength_value >= 4:
            strength = SignalStrength.VERY_STRONG
        elif strength_value >= 3:
            strength = SignalStrength.STRONG
        elif strength_value >= 2:
            strength = SignalStrength.MODERATE
        else:
            strength = SignalStrength.WEAK
        
        return {
            "signal_type": signal_type,
            "strength": strength,
            "confidence": confidence,
            "reasoning": "; ".join(reasoning),
            "buy_signals": len(buy_signals),
            "sell_signals": len(sell_signals),
            "total_signals": total_signals
        }
    
    def _strength_to_value(self, strength: SignalStrength) -> int:
        """将信号强度转换为数值"""
        strength_map = {
            SignalStrength.WEAK: 1,
            SignalStrength.MODERATE: 2,
            SignalStrength.STRONG: 3,
            SignalStrength.VERY_STRONG: 4
        }
        return strength_map.get(strength, 1)


class SignalQualityAnalyzer:
    """信号质量分析器"""
    
    def __init__(self):
        self.config = get_config()
        self.signal_history: List[TradingSignal] = []
    
    def analyze_signal_quality(self, signal: TradingSignal, market_data: List[MarketData]) -> Dict[str, Any]:
        """分析信号质量"""
        try:
            # 基础质量检查
            quality_score = self._calculate_quality_score(signal, market_data)
            
            # 历史信号对比
            historical_accuracy = self._calculate_historical_accuracy(signal.symbol)
            
            # 市场条件分析
            market_conditions = self._analyze_market_conditions(market_data)
            
            # 风险评估
            risk_assessment = self._assess_risk(signal, market_data)
            
            return {
                "quality_score": quality_score,
                "historical_accuracy": historical_accuracy,
                "market_conditions": market_conditions,
                "risk_assessment": risk_assessment,
                "overall_rating": self._calculate_overall_rating(quality_score, historical_accuracy, market_conditions, risk_assessment)
            }
        
        except Exception as e:
            logger.error(f"分析信号质量失败: {e}")
            raise SignalGenerationError(f"分析信号质量失败: {e}")
    
    def _calculate_quality_score(self, signal: TradingSignal, market_data: List[MarketData]) -> float:
        """计算质量分数"""
        score = 0.0
        
        # 基于置信度
        score += signal.confidence * 0.3
        
        # 基于信号强度
        strength_scores = {
            SignalStrength.WEAK: 0.2,
            SignalStrength.MODERATE: 0.5,
            SignalStrength.STRONG: 0.8,
            SignalStrength.VERY_STRONG: 1.0
        }
        score += strength_scores.get(signal.strength, 0.5) * 0.3
        
        # 基于技术指标数量
        indicator_count = len(signal.indicators)
        score += min(indicator_count / 10.0, 1.0) * 0.2
        
        # 基于价格趋势一致性
        trend_consistency = self._calculate_trend_consistency(market_data)
        score += trend_consistency * 0.2
        
        return min(score, 1.0)
    
    def _calculate_historical_accuracy(self, symbol: str) -> float:
        """计算历史准确率"""
        if not self.signal_history:
            return 0.5
        
        # 获取该股票的历史信号
        symbol_signals = [s for s in self.signal_history if s.symbol == symbol]
        if len(symbol_signals) < 10:
            return 0.5
        
        # 计算准确率 (简化实现)
        correct_signals = 0
        for signal in symbol_signals[-20:]:  # 最近20个信号
            # 这里需要实际的盈亏数据来计算准确率
            # 简化实现，假设50%准确率
            correct_signals += 1
        
        return correct_signals / len(symbol_signals[-20:])
    
    def _analyze_market_conditions(self, market_data: List[MarketData]) -> Dict[str, Any]:
        """分析市场条件"""
        if len(market_data) < 20:
            return {"volatility": "unknown", "trend": "unknown", "volume": "unknown"}
        
        # 计算波动率
        returns = []
        for i in range(1, len(market_data)):
            ret = (market_data[i].close_price - market_data[i-1].close_price) / market_data[i-1].close_price
            returns.append(ret)
        
        volatility = np.std(returns) * np.sqrt(252)  # 年化波动率
        
        # 计算趋势
        recent_prices = [data.close_price for data in market_data[-20:]]
        trend = "up" if recent_prices[-1] > recent_prices[0] else "down"
        
        # 计算成交量
        avg_volume = np.mean([data.volume for data in market_data[-20:]])
        current_volume = market_data[-1].volume
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0
        
        return {
            "volatility": "high" if volatility > 0.3 else "medium" if volatility > 0.15 else "low",
            "trend": trend,
            "volume": "high" if volume_ratio > 1.5 else "medium" if volume_ratio > 0.8 else "low",
            "volatility_value": volatility,
            "volume_ratio": volume_ratio
        }
    
    def _assess_risk(self, signal: TradingSignal, market_data: List[MarketData]) -> Dict[str, Any]:
        """风险评估"""
        if len(market_data) < 20:
            return {"risk_level": "unknown", "stop_loss": None, "take_profit": None}
        
        current_price = market_data[-1].close_price
        
        # 计算ATR用于止损止盈
        high_prices = [data.high_price for data in market_data]
        low_prices = [data.low_price for data in market_data]
        close_prices = [data.close_price for data in market_data]
        
        atr = self._calculate_atr(high_prices, low_prices, close_prices)
        
        # 设置止损止盈
        if signal.signal_type in [SignalType.BUY, SignalType.STRONG_BUY]:
            stop_loss = current_price - (atr * 2)
            take_profit = current_price + (atr * 3)
            risk_level = "low" if atr < current_price * 0.02 else "medium"
        elif signal.signal_type in [SignalType.SELL, SignalType.STRONG_SELL]:
            stop_loss = current_price + (atr * 2)
            take_profit = current_price - (atr * 3)
            risk_level = "low" if atr < current_price * 0.02 else "medium"
        else:
            stop_loss = None
            take_profit = None
            risk_level = "low"
        
        return {
            "risk_level": risk_level,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "atr": atr
        }
    
    def _calculate_trend_consistency(self, market_data: List[MarketData]) -> float:
        """计算趋势一致性"""
        if len(market_data) < 10:
            return 0.5
        
        prices = [data.close_price for data in market_data[-10:]]
        up_count = sum(1 for i in range(1, len(prices)) if prices[i] > prices[i-1])
        down_count = sum(1 for i in range(1, len(prices)) if prices[i] < prices[i-1])
        
        if up_count > down_count:
            return up_count / (len(prices) - 1)
        else:
            return down_count / (len(prices) - 1)
    
    def _calculate_atr(self, high_prices: List[float], low_prices: List[float], close_prices: List[float]) -> float:
        """计算ATR"""
        try:
            if len(close_prices) < 14:
                return close_prices[-1] * 0.02  # 默认2%
            
            high_array = np.array(high_prices)
            low_array = np.array(low_prices)
            close_array = np.array(close_prices)
            
            atr = talib.ATR(high_array, low_array, close_array, timeperiod=14)
            return float(atr[-1]) if not np.isnan(atr[-1]) else close_prices[-1] * 0.02
        except:
            return close_prices[-1] * 0.02
    
    def _calculate_overall_rating(self, quality_score: float, historical_accuracy: float, 
                                 market_conditions: Dict[str, Any], risk_assessment: Dict[str, Any]) -> str:
        """计算总体评级"""
        # 综合评分
        score = quality_score * 0.4 + historical_accuracy * 0.3 + 0.3  # 简化计算
        
        if score >= 0.8:
            return "excellent"
        elif score >= 0.6:
            return "good"
        elif score >= 0.4:
            return "fair"
        else:
            return "poor"


class SignalGenerator:
    """信号生成器主类"""
    
    def __init__(self):
        self.analyzer = SignalAnalyzer()
        self.quality_analyzer = SignalQualityAnalyzer()
        self.running = False
        self.signals_history: List[TradingSignal] = []
        logger.info("信号生成器初始化完成")
    
    async def start(self):
        """启动信号生成"""
        self.running = True
        logger.info("信号生成器启动")
        
        try:
            while self.running:
                # 这里应该从实际的数据源获取数据
                # 目前使用模拟数据
                symbols = ["AAPL", "TSLA", "MSFT", "GOOGL"]
                
                for symbol in symbols:
                    try:
                        # 获取市场数据
                        market_data = self._get_mock_market_data(symbol)
                        
                        # 生成信号
                        signal = await self.generate_signal(symbol, market_data)
                        
                        if signal:
                            self.signals_history.append(signal)
                            logger.info(f"生成信号: {symbol} {signal.signal_type.value} {signal.strength.value}")
                    
                    except Exception as e:
                        logger.error(f"为 {symbol} 生成信号失败: {e}")
                
                await asyncio.sleep(30)  # 每30秒生成一次信号
        
        except Exception as e:
            logger.error(f"信号生成出错: {e}")
            self.running = False
    
    async def stop(self):
        """停止信号生成"""
        self.running = False
        logger.info("信号生成器停止")
    
    async def generate_signal(self, symbol: str, market_data: List[MarketData]) -> Optional[TradingSignal]:
        """生成交易信号"""
        try:
            # 分析技术信号
            analysis = self.analyzer.analyze_technical_signals(market_data)
            
            if analysis["status"] != "success":
                return None
            
            signal_analysis = analysis["signal_analysis"]
            current_price = analysis["current_price"]
            
            # 创建交易信号
            signal = TradingSignal(
                symbol=symbol,
                signal_type=signal_analysis["signal_type"],
                strength=signal_analysis["strength"],
                confidence=signal_analysis["confidence"],
                price=current_price,
                timestamp=datetime.now(),
                indicators=analysis["indicators"],
                reasoning=signal_analysis["reasoning"]
            )
            
            # 分析信号质量
            quality_analysis = self.quality_analyzer.analyze_signal_quality(signal, market_data)
            
            # 设置止损止盈
            risk_assessment = quality_analysis["risk_assessment"]
            signal.stop_loss = risk_assessment.get("stop_loss")
            signal.take_profit = risk_assessment.get("take_profit")
            
            return signal
        
        except Exception as e:
            logger.error(f"生成信号失败: {e}")
            raise SignalGenerationError(f"生成信号失败: {e}")
    
    def _get_mock_market_data(self, symbol: str) -> List[MarketData]:
        """获取模拟市场数据"""
        # 生成模拟的OHLCV数据
        base_price = 150.0 if symbol == "AAPL" else 200.0 if symbol == "TSLA" else 300.0
        
        market_data = []
        for i in range(100):  # 100个数据点
            # 模拟价格波动
            price_change = np.random.normal(0, 0.02) * base_price
            current_price = base_price + price_change
            
            # 生成OHLCV数据
            high_price = current_price * (1 + abs(np.random.normal(0, 0.01)))
            low_price = current_price * (1 - abs(np.random.normal(0, 0.01)))
            open_price = current_price * (1 + np.random.normal(0, 0.005))
            volume = np.random.randint(1000000, 10000000)
            
            market_data.append(MarketData(
                symbol=symbol,
                timestamp=datetime.now() - timedelta(days=100-i),
                open_price=open_price,
                high_price=high_price,
                low_price=low_price,
                close_price=current_price,
                volume=volume
            ))
            
            base_price = current_price
        
        return market_data
    
    def get_signals_summary(self) -> Dict[str, Any]:
        """获取信号摘要"""
        if not self.signals_history:
            return {"status": "no_signals"}
        
        recent_signals = self.signals_history[-50:]  # 最近50个信号
        
        # 统计信号类型
        signal_types = {}
        for signal in recent_signals:
            signal_type = signal.signal_type.value
            signal_types[signal_type] = signal_types.get(signal_type, 0) + 1
        
        # 统计信号强度
        signal_strengths = {}
        for signal in recent_signals:
            strength = signal.strength.value
            signal_strengths[strength] = signal_strengths.get(strength, 0) + 1
        
        return {
            "total_signals": len(self.signals_history),
            "recent_signals": len(recent_signals),
            "signal_types": signal_types,
            "signal_strengths": signal_strengths,
            "avg_confidence": np.mean([s.confidence for s in recent_signals]),
            "latest_signals": [
                {
                    "symbol": s.symbol,
                    "signal_type": s.signal_type.value,
                    "strength": s.strength.value,
                    "confidence": s.confidence,
                    "price": s.price,
                    "timestamp": s.timestamp.isoformat()
                }
                for s in recent_signals[-5:]  # 最近5个信号
            ]
        }


if __name__ == "__main__":
    async def main():
        generator = SignalGenerator()
        try:
            await generator.start()
        except KeyboardInterrupt:
            await generator.stop()
            logger.info("信号生成器已停止")
    
    asyncio.run(main()) 