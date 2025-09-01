"""
AI Analyzer

Advanced market analysis system with:
- Real-time technical analysis
- Machine learning predictions
- Pattern recognition
- Market sentiment analysis
- Integration with notification system
"""

import os
import logging
import time
import json
import threading
import asyncio
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union, Tuple
from collections import defaultdict, deque
import requests
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestRegressor
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout

# Import system components
from ..shared_interfaces import (
    DataType, TimeFrame, AIAnalyzerProtocol,
    MarketDataProtocol, TradingHandlerProtocol,
    NotificationProtocol
)
from ..ai_event_pool import AIEventPool, AIEvent, EventCategory, EventPriority

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AnalysisPriority:
    CRITICAL = 0  # Immediate action required
    HIGH = 1      # Important signal
    MEDIUM = 2    # Normal signal
    LOW = 3       # Minor signal
    INFO = 4      # Informational only

class AIAnalyzer(AIAnalyzerProtocol):
    """Advanced AI-powered market analysis system"""
    
    def __init__(self, config: Dict[str, Any], 
                 notification_system: NotificationProtocol,
                 market_data: Optional[MarketDataProtocol] = None,
                 trading_handler: Optional[TradingHandlerProtocol] = None):
        """Initialize the analyzer
        
        Args:
            config: Configuration dictionary
            notification_system: Notification system instance
            market_data: Market data provider instance
            trading_handler: Trading handler instance
        """
        self.config = config.get("analysis", {})
        self.notification_system = notification_system
        self.market_data = market_data
        self.trading_handler = trading_handler
        
        # Register commands with trading handler if available
        if self.trading_handler:
            self._register_commands()
        
        # Analysis settings
        self.timeframes = self.config.get("timeframes", ["1m", "5m", "15m", "1h", "4h", "1d"])
        self.symbols = self.config.get("symbols", [])
        self.indicators = self.config.get("indicators", {
            "RSI": {"period": 14, "overbought": 70, "oversold": 30},
            "MACD": {"fast": 12, "slow": 26, "signal": 9},
            "BB": {"period": 20, "std": 2},
            "ATR": {"period": 14},
            "VWAP": {"period": 14}
        })
        
        # Machine learning models
        self.models = {}
        self.model_configs = self.config.get("models", {
            "price_prediction": {
                "type": "lstm",
                "features": ["close", "volume", "rsi", "macd"],
                "target": "close",
                "lookback": 60
            },
            "volatility_prediction": {
                "type": "xgboost",
                "features": ["atr", "bb_width", "volume"],
                "target": "volatility",
                "lookback": 20
            }
        })
        
        # Pattern recognition
        self.patterns = self.config.get("patterns", {
            "candlestick": ["doji", "hammer", "engulfing", "morning_star"],
            "chart": ["head_shoulders", "double_top", "triangle", "channel"],
            "volume": ["volume_spike", "volume_trend", "volume_divergence"]
        })
        
        # Market sentiment
        self.sentiment_sources = self.config.get("sentiment_sources", {
            "news": {"weight": 0.3, "update_interval": 300},
            "social": {"weight": 0.2, "update_interval": 60},
            "options": {"weight": 0.3, "update_interval": 300},
            "technical": {"weight": 0.2, "update_interval": 60}
        })
        
        # Analysis tracking
        self.analysis_history = defaultdict(deque)
        self.last_analysis_time = {}
        self.analysis_counts = defaultdict(int)
        
        # Performance metrics
        self.metrics = {
            "total_analyses": 0,
            "analyses_by_priority": defaultdict(int),
            "analyses_by_symbol": defaultdict(int),
            "prediction_accuracy": defaultdict(list),
            "processing_times": []
        }
        
        # Initialize components
        self._initialize_components()
        
        logger.info("AI Analyzer initialized")
    
    def _initialize_components(self):
        """Initialize analysis components"""
        try:
            # Initialize machine learning models
            self._init_ml_models()
            
            # Initialize pattern recognition
            self._init_pattern_recognition()
            
            # Initialize sentiment analysis
            self._init_sentiment_analysis()
            
            # Initialize technical indicators
            self._init_technical_indicators()
            
        except Exception as e:
            logger.error(f"Error initializing components: {str(e)}")
    
    async def analyze_market_data(self, 
                                symbol: str,
                                timeframe: str,
                                data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze market data and generate insights
        
        Args:
            symbol: Trading symbol
            timeframe: Analysis timeframe
            data: Market data to analyze
            
        Returns:
            Analysis results
        """
        try:
            start_time = time.time()
            
            # Convert data to DataFrame
            df = pd.DataFrame(data)
            
            # Calculate technical indicators
            indicators = self._calculate_indicators(df)
            
            # Detect patterns
            patterns = self._detect_patterns(df)
            
            # Analyze sentiment
            sentiment = await self._analyze_sentiment(symbol)
            
            # Generate predictions
            predictions = self._generate_predictions(df)
            
            # Combine results
            analysis = {
                "symbol": symbol,
                "timeframe": timeframe,
                "timestamp": datetime.now().isoformat(),
                "indicators": indicators,
                "patterns": patterns,
                "sentiment": sentiment,
                "predictions": predictions
            }
            
            # Determine priority
            priority = self._determine_priority(analysis)
            analysis["priority"] = priority
            
            # Generate signals
            signals = self._generate_signals(analysis)
            analysis["signals"] = signals
            
            # Update metrics
            self._update_metrics(symbol, priority, time.time() - start_time)
            
            # Store analysis
            self._store_analysis(analysis)
            
            # Send notifications if needed
            await self._send_notifications(analysis)
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing market data: {str(e)}")
            return {}
    
    def _calculate_indicators(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Calculate technical indicators"""
        try:
            indicators = {}
            
            # RSI
            if "RSI" in self.indicators:
                rsi_config = self.indicators["RSI"]
                indicators["RSI"] = self._calculate_rsi(
                    df["close"],
                    rsi_config["period"]
                )
            
            # MACD
            if "MACD" in self.indicators:
                macd_config = self.indicators["MACD"]
                indicators["MACD"] = self._calculate_macd(
                    df["close"],
                    macd_config["fast"],
                    macd_config["slow"],
                    macd_config["signal"]
                )
            
            # Bollinger Bands
            if "BB" in self.indicators:
                bb_config = self.indicators["BB"]
                indicators["BB"] = self._calculate_bollinger_bands(
                    df["close"],
                    bb_config["period"],
                    bb_config["std"]
                )
            
            # ATR
            if "ATR" in self.indicators:
                atr_config = self.indicators["ATR"]
                indicators["ATR"] = self._calculate_atr(
                    df,
                    atr_config["period"]
                )
            
            # VWAP
            if "VWAP" in self.indicators:
                vwap_config = self.indicators["VWAP"]
                indicators["VWAP"] = self._calculate_vwap(
                    df,
                    vwap_config["period"]
                )
            
            return indicators
            
        except Exception as e:
            logger.error(f"Error calculating indicators: {str(e)}")
            return {}
    
    def _detect_patterns(self, df: pd.DataFrame) -> Dict[str, List[Dict[str, Any]]]:
        """Detect chart patterns"""
        try:
            patterns = {
                "candlestick": [],
                "chart": [],
                "volume": []
            }
            
            # Detect candlestick patterns
            if "candlestick" in self.patterns:
                for pattern in self.patterns["candlestick"]:
                    if pattern == "doji":
                        patterns["candlestick"].extend(self._detect_doji(df))
                    elif pattern == "hammer":
                        patterns["candlestick"].extend(self._detect_hammer(df))
                    elif pattern == "engulfing":
                        patterns["candlestick"].extend(self._detect_engulfing(df))
                    elif pattern == "morning_star":
                        patterns["candlestick"].extend(self._detect_morning_star(df))
            
            # Detect chart patterns
            if "chart" in self.patterns:
                for pattern in self.patterns["chart"]:
                    if pattern == "head_shoulders":
                        patterns["chart"].extend(self._detect_head_shoulders(df))
                    elif pattern == "double_top":
                        patterns["chart"].extend(self._detect_double_top(df))
                    elif pattern == "triangle":
                        patterns["chart"].extend(self._detect_triangle(df))
                    elif pattern == "channel":
                        patterns["chart"].extend(self._detect_channel(df))
            
            # Detect volume patterns
            if "volume" in self.patterns:
                for pattern in self.patterns["volume"]:
                    if pattern == "volume_spike":
                        patterns["volume"].extend(self._detect_volume_spike(df))
                    elif pattern == "volume_trend":
                        patterns["volume"].extend(self._detect_volume_trend(df))
                    elif pattern == "volume_divergence":
                        patterns["volume"].extend(self._detect_volume_divergence(df))
            
            return patterns
            
        except Exception as e:
            logger.error(f"Error detecting patterns: {str(e)}")
            return {"candlestick": [], "chart": [], "volume": []}
    
    async def _analyze_sentiment(self, symbol: str) -> Dict[str, Any]:
        """Analyze market sentiment"""
        try:
            sentiment = {
                "overall": 0.0,
                "components": {}
            }
            
            # Analyze news sentiment
            if "news" in self.sentiment_sources:
                news_sentiment = await self._analyze_news_sentiment(symbol)
                sentiment["components"]["news"] = news_sentiment
                sentiment["overall"] += news_sentiment * self.sentiment_sources["news"]["weight"]
            
            # Analyze social sentiment
            if "social" in self.sentiment_sources:
                social_sentiment = await self._analyze_social_sentiment(symbol)
                sentiment["components"]["social"] = social_sentiment
                sentiment["overall"] += social_sentiment * self.sentiment_sources["social"]["weight"]
            
            # Analyze options sentiment
            if "options" in self.sentiment_sources:
                options_sentiment = await self._analyze_options_sentiment(symbol)
                sentiment["components"]["options"] = options_sentiment
                sentiment["overall"] += options_sentiment * self.sentiment_sources["options"]["weight"]
            
            # Analyze technical sentiment
            if "technical" in self.sentiment_sources:
                technical_sentiment = self._analyze_technical_sentiment(symbol)
                sentiment["components"]["technical"] = technical_sentiment
                sentiment["overall"] += technical_sentiment * self.sentiment_sources["technical"]["weight"]
            
            return sentiment
            
        except Exception as e:
            logger.error(f"Error analyzing sentiment: {str(e)}")
            return {"overall": 0.0, "components": {}}
    
    def _generate_predictions(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Generate price and volatility predictions"""
        try:
            predictions = {}
            
            # Price prediction
            if "price_prediction" in self.model_configs:
                price_model = self.models.get("price_prediction")
                if price_model:
                    predictions["price"] = self._predict_price(df, price_model)
            
            # Volatility prediction
            if "volatility_prediction" in self.model_configs:
                vol_model = self.models.get("volatility_prediction")
                if vol_model:
                    predictions["volatility"] = self._predict_volatility(df, vol_model)
            
            return predictions
            
        except Exception as e:
            logger.error(f"Error generating predictions: {str(e)}")
            return {}
    
    def _determine_priority(self, analysis: Dict[str, Any]) -> int:
        """Determine analysis priority"""
        try:
            priority = AnalysisPriority.INFO
            
            # Check for critical patterns
            if any(p["type"] in ["head_shoulders", "double_top"] for p in analysis["patterns"]["chart"]):
                priority = AnalysisPriority.CRITICAL
            
            # Check for high-priority signals
            elif any(s["type"] in ["breakout", "breakdown"] for s in analysis["signals"]):
                priority = AnalysisPriority.HIGH
            
            # Check for medium-priority signals
            elif any(s["type"] in ["trend_change", "support_resistance"] for s in analysis["signals"]):
                priority = AnalysisPriority.MEDIUM
            
            # Check for low-priority signals
            elif any(s["type"] in ["indicator_cross", "pattern_completion"] for s in analysis["signals"]):
                priority = AnalysisPriority.LOW
            
            return priority
            
        except Exception as e:
            logger.error(f"Error determining priority: {str(e)}")
            return AnalysisPriority.INFO
    
    def _generate_signals(self, analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate trading signals from analysis"""
        try:
            signals = []
            
            # Check indicator signals
            signals.extend(self._check_indicator_signals(analysis["indicators"]))
            
            # Check pattern signals
            signals.extend(self._check_pattern_signals(analysis["patterns"]))
            
            # Check sentiment signals
            signals.extend(self._check_sentiment_signals(analysis["sentiment"]))
            
            # Check prediction signals
            signals.extend(self._check_prediction_signals(analysis["predictions"]))
            
            return signals
            
        except Exception as e:
            logger.error(f"Error generating signals: {str(e)}")
            return []
    
    async def _send_notifications(self, analysis: Dict[str, Any]):
        """Send notifications based on analysis"""
        try:
            # Skip if no notification system
            if not self.notification_system:
                return
            
            # Prepare notification data
            notification_data = {
                "title": f"Market Analysis: {analysis['symbol']}",
                "message": self._format_analysis_message(analysis),
                "priority": analysis["priority"],
                "metadata": {
                    "symbol": analysis["symbol"],
                    "timeframe": analysis["timeframe"],
                    "signals": analysis["signals"]
                }
            }
            
            # Send notification
            await self.notification_system.generate_alert(**notification_data)
            
        except Exception as e:
            logger.error(f"Error sending notifications: {str(e)}")
    
    def _format_analysis_message(self, analysis: Dict[str, Any]) -> str:
        """Format analysis results as a message"""
        try:
            message = []
            
            # Add symbol and timeframe
            message.append(f"Symbol: {analysis['symbol']}")
            message.append(f"Timeframe: {analysis['timeframe']}")
            message.append("")
            
            # Add signals
            if analysis["signals"]:
                message.append("Signals:")
                for signal in analysis["signals"]:
                    message.append(f"- {signal['type']}: {signal['description']}")
                message.append("")
            
            # Add patterns
            if any(analysis["patterns"].values()):
                message.append("Patterns:")
                for pattern_type, patterns in analysis["patterns"].items():
                    if patterns:
                        message.append(f"{pattern_type.title()}:")
                        for pattern in patterns:
                            message.append(f"- {pattern['type']}: {pattern['description']}")
                message.append("")
            
            # Add sentiment
            if analysis["sentiment"]["overall"] != 0:
                message.append("Sentiment:")
                message.append(f"Overall: {analysis['sentiment']['overall']:.2f}")
                for component, value in analysis["sentiment"]["components"].items():
                    message.append(f"{component.title()}: {value:.2f}")
                message.append("")
            
            # Add predictions
            if analysis["predictions"]:
                message.append("Predictions:")
                for pred_type, pred in analysis["predictions"].items():
                    message.append(f"{pred_type.title()}: {pred['value']:.2f}")
            
            return "\n".join(message)
            
        except Exception as e:
            logger.error(f"Error formatting analysis message: {str(e)}")
            return "Error formatting analysis message"
    
    def _update_metrics(self, symbol: str, priority: int, processing_time: float):
        """Update analysis metrics"""
        self.metrics["total_analyses"] += 1
        self.metrics["analyses_by_priority"][priority] += 1
        self.metrics["analyses_by_symbol"][symbol] += 1
        self.metrics["processing_times"].append(processing_time)
    
    def _store_analysis(self, analysis: Dict[str, Any]):
        """Store analysis results"""
        try:
            # Add to history
            self.analysis_history[analysis["symbol"]].append(analysis)
            
            # Update last analysis time
            self.last_analysis_time[analysis["symbol"]] = time.time()
            
            # Update analysis count
            current_minute = int(time.time() / 60)
            self.analysis_counts[current_minute] += 1
            
        except Exception as e:
            logger.error(f"Error storing analysis: {str(e)}")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get analysis metrics"""
        return {
            "total_analyses": self.metrics["total_analyses"],
            "analyses_by_priority": dict(self.metrics["analyses_by_priority"]),
            "analyses_by_symbol": dict(self.metrics["analyses_by_symbol"]),
            "average_processing_time": np.mean(self.metrics["processing_times"]) if self.metrics["processing_times"] else 0,
            "prediction_accuracy": {k: np.mean(v) for k, v in self.metrics["prediction_accuracy"].items()}
        }
    
    def get_analysis_history(self, 
                           symbol: Optional[str] = None,
                           limit: int = 100) -> List[Dict[str, Any]]:
        """Get analysis history"""
        if symbol is not None:
            return list(self.analysis_history[symbol])[-limit:]
        
        # Combine all symbols
        all_analyses = []
        for symbol in self.symbols:
            all_analyses.extend(self.analysis_history[symbol])
        
        # Sort by timestamp
        all_analyses.sort(key=lambda x: x["timestamp"], reverse=True)
        return all_analyses[:limit]

    def _register_commands(self):
        """Register analyzer commands with trading handler"""
        if not self.trading_handler:
            return
            
        # Register analysis commands
        self.trading_handler.register_command(
            "analyze",
            self.analyze_market_data,
            "Analyze market data for a symbol",
            ["symbol", "timeframe"]
        )
        
        self.trading_handler.register_command(
            "get_metrics",
            self.get_metrics,
            "Get analysis metrics",
            []
        )
        
        self.trading_handler.register_command(
            "get_history",
            self.get_analysis_history,
            "Get analysis history",
            ["symbol", "limit"]
        )
        
        logger.info("Analyzer commands registered with trading handler")

# For testing
if __name__ == "__main__":
    # Load config
    with open("config/warmachine_config.json", "r") as f:
        config = json.load(f)
    
    # Create analyzer
    analyzer = AIAnalyzer(config, None)
    
    # Test analysis
    async def test_analysis():
        result = await analyzer.analyze_market_data(
            symbol="SPY",
            timeframe="1h",
            data={
                "timestamp": [datetime.now().isoformat()],
                "open": [450.0],
                "high": [451.0],
                "low": [449.0],
                "close": [450.5],
                "volume": [1000000]
            }
        )
        print(json.dumps(result, indent=2))
    
    # Run test
    asyncio.run(test_analysis()) 