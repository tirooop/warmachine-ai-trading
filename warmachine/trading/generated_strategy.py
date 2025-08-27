```python
import numpy as np
import pandas as pd

class MeanReversionStrategy:
    """
    均值回归交易策略，结合EMA和RSI指标
    当价格偏离均线且RSI显示超买/超卖时进行交易
    """
    
    def __init__(self, data, ema_period=20, rsi_period=14, 
                 overbought=70, oversold=30, stop_loss_pct=0.02, take_profit_pct=0.03):
        """
        初始化策略参数
        :param data: 包含OHLC数据的DataFrame
        :param ema_period: EMA周期 (默认20)
        :param rsi_period: RSI周期 (默认14)
        :param overbought: 超买阈值 (默认70)
        :param oversold: 超卖阈值 (默认30)
        :param stop_loss_pct: 止损比例 (默认2%)
        :param take_profit_pct: 止盈比例 (默认3%)
        """
        self.data = data.copy()
        self.ema_period = ema_period
        self.rsi_period = rsi_period
        self.overbought = overbought
        self.oversold = oversold
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        
        # 计算技术指标
        self._calculate_indicators()
        
        # 初始化仓位和交易记录
        self.position = 0  # 0表示空仓，1表示多头，-1表示空头
        self.trades = []
    
    def _calculate_indicators(self):
        """计算所需技术指标"""
        # 计算EMA
        self.data['ema'] = self.data['close'].ewm(span=self.ema_period, adjust=False).mean()
        
        # 计算RSI
        delta = self.data['close'].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        
        avg_gain = gain.rolling(self.rsi_period).mean()
        avg_loss = loss.rolling(self.rsi_period).mean()
        
        rs = avg_gain / avg_loss
        self.data['rsi'] = 100 - (100 / (1 + rs))
        
    def generate_signal(self, i):
        """
        生成交易信号
        :param i: 当前数据索引
        :return: 交易信号 (1=买入, -1=卖出, 0=无信号)
        """
        if i < max(self.ema_period, self.rsi_period):
            return 0  # 确保有足够数据计算指标
        
        close_price = self.data['close'].iloc[i]
        ema = self.data['ema'].iloc[i]
        rsi = self.data['rsi'].iloc[i]
        
        # 多头信号: 价格低于EMA且RSI超卖
        if close_price < ema and rsi < self.oversold:
            return 1
        
        # 空头信号: 价格高于EMA且RSI超买
        elif close_price > ema and rsi > self.overbought:
            return -1
        
        return 0
    
    def execute_trade(self, i, signal, capital=100000):
        """
        执行交易逻辑
        :param i: 当前数据索引
        :param signal: 交易信号
        :param capital: 初始资金
        """
        if self.position == signal:  # 已有相同方向的仓位
            return
            
        close_price = self.data['close'].