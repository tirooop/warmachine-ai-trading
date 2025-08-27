"""
Standalone AI Chart Analyzer using DeepSeek API
"""

import os
import requests
import json
from typing import Dict, Any, Optional
import pandas as pd
import numpy as np
from dotenv import load_dotenv

class StandaloneAIAnalyzer:
    """
    Standalone AI analyzer that doesn't depend on other project modules
    """
    
    def __init__(self, api_key=None):
        """
        Initialize the AI analyzer
        
        Args:
            api_key: DeepSeek API key (if None, will try environment)
        """
        load_dotenv()
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY") or "sk-uvbjgxuaigsbjpebfthckspmnpfjixhwuwapwsrrqprfvarl"
        self.base_url = "https://api.siliconflow.cn/v1/chat/completions"
        self.model = "deepseek-ai/DeepSeek-V3"
        
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def analyze(self, symbol: str, data: pd.DataFrame, brief: bool = False) -> str:
        """
        Analyze stock data using DeepSeek AI
        
        Args:
            symbol: Stock ticker symbol
            data: DataFrame with OHLCV and technical indicators
            brief: Whether to generate brief or detailed analysis
            
        Returns:
            String with AI analysis
        """
        # Extract key metrics for the prompt
        try:
            current_price = data['close'].iloc[-1]
            price_change = (data['close'].iloc[-1] - data['close'].iloc[-5]) / data['close'].iloc[-5] * 100
            
            # Get indicators if available
            rsi = data['rsi'].iloc[-1] if 'rsi' in data.columns else None
            macd = data['macd'].iloc[-1] if 'macd' in data.columns else None
            macd_signal = data['macd_signal'].iloc[-1] if 'macd_signal' in data.columns else None
            fisher = data['fisher'].iloc[-1] if 'fisher' in data.columns else None
            
            # Determine trend direction
            if 'ema20' in data.columns and 'fisher' in data.columns:
                price = data['close'].iloc[-1]
                ema20 = data['ema20'].iloc[-1]
                fisher_value = data['fisher'].iloc[-1]
                
                if fisher_value > 0.5 and price > ema20:
                    trend_direction = "bullish"
                elif fisher_value < -0.5 and price < ema20:
                    trend_direction = "bearish"
                else:
                    trend_direction = "neutral"
                    
                # Calculate trend strength (0-100)
                trend_strength = min(100, abs(fisher_value) * 33)
            else:
                trend_direction = "unknown"
                trend_strength = 50
                
            # Calculate Bollinger Band position
            if 'upper_band' in data.columns and 'lower_band' in data.columns:
                upper_band = data['upper_band'].iloc[-1]
                lower_band = data['lower_band'].iloc[-1]
                band_position = (current_price - lower_band) / (upper_band - lower_band) * 100
            else:
                band_position = 50
            
            # Create prompt based on brief or detailed
            if brief:
                prompt = self._create_brief_prompt(symbol, current_price, price_change, 
                                                 rsi, trend_direction, band_position)
            else:
                prompt = self._create_detailed_prompt(symbol, current_price, price_change, 
                                                   rsi, fisher, macd, macd_signal, 
                                                   trend_direction, trend_strength, band_position)
                
            # Call DeepSeek API
            return self._ask_deepseek(prompt)
            
        except Exception as e:
            return f"分析错误: {str(e)}"
    
    def _create_brief_prompt(self, symbol, price, change, rsi, trend, band_position):
        """Create brief analysis prompt"""
        prompt = f"""
作为专业的量化交易技术分析师，请对{symbol}的技术指标做一个简短的分析。

数据:
- 当前价格: ${price:.2f}
- 5日涨跌幅: {'+' if change >= 0 else ''}{change:.2f}%
- RSI: {rsi:.2f if rsi is not None else 'N/A'}
- 趋势方向: {trend}
- 布林带位置: {band_position:.2f}%

请提供一个50字左右的简洁分析，包括：
1. 当前趋势状态
2. 可能的支撑/阻力位
3. 操作建议(买入/卖出/持有)
"""
        return prompt
    
    def _create_detailed_prompt(self, symbol, price, change, rsi, fisher, macd, signal, 
                               trend_direction, trend_strength, band_position):
        """Create detailed analysis prompt"""
        prompt = f"""
作为专业的量化交易技术分析师，请对{symbol}的技术指标做出全面分析。

技术指标数据:
- 当前价格: ${price:.2f}
- 5日涨跌幅: {'+' if change >= 0 else ''}{change:.2f}%
- RSI(14): {rsi:.2f if rsi is not None else 'N/A'}
- Fisher Transform: {fisher:.4f if fisher is not None else 'N/A'}
- MACD: {macd:.4f if macd is not None else 'N/A'}
- MACD Signal: {signal:.4f if signal is not None else 'N/A'}
- 趋势方向: {trend_direction}
- 趋势强度: {trend_strength:.2f}/100
- 布林带位置: {band_position:.2f}% (0%=下轨, 100%=上轨)

请提供详细分析，包括：
1. 当前趋势总结
2. 支撑位和阻力位分析
3. 超买/超卖状态判断
4. 短期（1-3日）价格预测
5. 操作建议（买入/卖出/持有）及理由
6. 潜在风险提示

注意：分析必须围绕技术指标，不要使用基本面因素。保持专业简洁的语言，回答控制在150字以内。
"""
        return prompt
        
    def _ask_deepseek(self, prompt: str) -> str:
        """Call DeepSeek API with system and user prompts"""
        system_prompt = "你是一位专业的金融分析师和量化交易专家，擅长分析市场数据并提供客观、准确的建议。"
        
        data = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ]
        }
        
        try:
            response = requests.post(
                self.base_url,
                headers=self.headers,
                json=data,
                timeout=30
            )
            response.raise_for_status()
            
            return response.json()["choices"][0]["message"]["content"]
            
        except Exception as e:
            return f"API调用错误: {str(e)[:100]}..."


if __name__ == "__main__":
    import sys
    from standalone_chart_renderer import StandaloneChartRenderer
    
    if len(sys.argv) < 2:
        print("Usage: python standalone_ai_analyzer.py SYMBOL [DAYS]")
        sys.exit(1)
    
    symbol = sys.argv[1].upper()
    days = int(sys.argv[2]) if len(sys.argv) > 2 else 30
    
    # Get chart data
    renderer = StandaloneChartRenderer()
    chart_path = renderer.render(symbol, days)
    print(f"Chart saved to: {chart_path}")
    
    # Get the data with indicators
    df = renderer._fetch_data(symbol, days)
    df = renderer._add_indicators(df)
    
    # Analyze the data
    analyzer = StandaloneAIAnalyzer()
    analysis = analyzer.analyze(symbol, df)
    
    print("\n" + "="*50)
    print(f"📊 {symbol} Technical Analysis")
    print("="*50)
    print(analysis)
    print("="*50) 