#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
技术指标组合策略分析器 (BOLL + MACD + KDJ)

本文件实现了一种结合布林带（Bollinger Bands）、MACD 和 KDJ 三种技术指标的交易信号分析策略。
其核心思想源于您提供的图片分析，旨在提高信号的准确性。

策略逻辑:
1. 卖出信号 (三重确认):
    - 主要条件 (BOLL):      价格触及或突破布林带上轨，表明处于相对高位。
    - 首次确认 (MACD):      MACD的红色动能柱（柱状图）开始缩短，或快线（DIF）下穿慢线（DEA）形成“死叉”，表明上涨动能减弱。
    - 最终确认 (KDJ):      KDJ指标处于超买区（>80），并且K线从上向下穿过D线形成“死叉”。

2. 买入信号 (三重确认 - 卖出信号的逆向逻辑):
    - 主要条件 (BOLL):      价格触及或跌破布林带下轨，表明处于相对低位。
    - 首次确认 (MACD):      MACD的绿色动能柱开始缩短，或快线（DIF）上穿慢线（DEA）形成“金叉”，表明下跌动能减弱。
    - 最终确认 (KDJ):      KDJ指标处于超卖区（<20），并且K线从下向上穿过D线形成“金叉”。

如何使用:
1. 确保已安装所需库: pip install pandas pandas_ta
2. (可选) 准备一个名为 'my_stock_data.csv' 的CSV文件，其中需包含 'Open', 'High', 'Low', 'Close' 列。
3. 直接运行此文件: python trading_strategy_analyzer.py
"""

import pandas as pd
import pandas_ta as ta
import numpy as np
import os
import datetime
import sys

# --- 1. 可配置参数 ---
# 您可以在这里修改指标的参数
# 布林带参数
BOLL_LENGTH = 20
BOLL_STD_DEV = 2.0

# MACD 参数
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9

# KDJ (Stochastic) 参数
KDJ_K = 14
KDJ_D = 3
KDJ_SMOOTH_K = 3

# KDJ 超买/超卖阈值
KDJ_OVERBOUGHT_LEVEL = 80
KDJ_OVERSOLD_LEVEL = 20


def analyze_signals(df: pd.DataFrame) -> pd.DataFrame:
    """
    对给定的DataFrame进行BOLL+MACD+KDJ组合策略分析。

    参数:
        df (pd.DataFrame): 包含'Open', 'High', 'Low', 'Close'列的价格数据。

    返回:
        pd.DataFrame: 增加了指标和信号列的新DataFrame。
    """
    if df.empty:
        print("警告: 输入的DataFrame为空。")
        return pd.DataFrame()

    df_copy = df.copy()

    # --- 2. 计算所有技术指标 ---
    # 使用 pandas_ta 库可以非常方便地计算
    print("正在计算技术指标...")

    # 布林带
    df_copy.ta.bbands(length=BOLL_LENGTH, std=BOLL_STD_DEV, append=True)

    # MACD
    df_copy.ta.macd(fast=MACD_FAST, slow=MACD_SLOW, signal=MACD_SIGNAL, append=True)

    # KDJ (在pandas_ta中名为stoch)
    df_copy.ta.stoch(k=KDJ_K, d=KDJ_D, smooth_k=KDJ_SMOOTH_K, append=True)
    
    # 为了代码清晰，重命名KDJ列
    k_col = f'STOCHk_{KDJ_K}_{KDJ_D}_{KDJ_SMOOTH_K}'
    d_col = f'STOCHd_{KDJ_K}_{KDJ_D}_{KDJ_SMOOTH_K}'

    # --- 3. 定义并应用策略逻辑 ---
    print("正在应用交易策略逻辑...")

    # 卖出信号逻辑
    sell_cond_boll = df_copy['Close'] > df_copy[f'BBU_{BOLL_LENGTH}_{BOLL_STD_DEV}']
    sell_cond_macd = (df_copy[f'MACDh_{MACD_FAST}_{MACD_SLOW}_{MACD_SIGNAL}'] < df_copy[f'MACDh_{MACD_FAST}_{MACD_SLOW}_{MACD_SIGNAL}'].shift(1)) & \
                     (df_copy[f'MACDh_{MACD_FAST}_{MACD_SLOW}_{MACD_SIGNAL}'].shift(1) > 0)
    sell_cond_kdj = (df_copy[k_col] > KDJ_OVERBOUGHT_LEVEL) & \
                    (df_copy[d_col] > KDJ_OVERBOUGHT_LEVEL) & \
                    (df_copy[k_col] < df_copy[d_col]) & \
                    (df_copy[k_col].shift(1) > df_copy[d_col].shift(1))
    
    df_copy['SELL_SIGNAL'] = sell_cond_boll & sell_cond_macd & sell_cond_kdj

    # 买入信号逻辑 (与卖出逻辑相反)
    buy_cond_boll = df_copy['Close'] < df_copy[f'BBL_{BOLL_LENGTH}_{BOLL_STD_DEV}']
    buy_cond_macd = (df_copy[f'MACDh_{MACD_FAST}_{MACD_SLOW}_{MACD_SIGNAL}'] > df_copy[f'MACDh_{MACD_FAST}_{MACD_SLOW}_{MACD_SIGNAL}'].shift(1)) & \
                    (df_copy[f'MACDh_{MACD_FAST}_{MACD_SLOW}_{MACD_SIGNAL}'].shift(1) < 0)
    buy_cond_kdj = (df_copy[k_col] < KDJ_OVERSOLD_LEVEL) & \
                   (df_copy[d_col] < KDJ_OVERSOLD_LEVEL) & \
                   (df_copy[k_col] > df_copy[d_col]) & \
                   (df_copy[k_col].shift(1) < df_copy[d_col].shift(1))

    df_copy['BUY_SIGNAL'] = buy_cond_boll & buy_cond_macd & buy_cond_kdj
    
    print("分析完成。")
    return df_copy


def load_or_create_data(symbol="AAPL", start=None, end=None, filename="my_stock_data.csv"):
    """
    优先从Yahoo Finance下载数据，其次尝试CSV，最后生成模拟数据。
    参数:
        symbol: 股票代码（如AAPL、SPY等）
        start, end: 日期范围（datetime/date对象或YYYY-MM-DD字符串），默认近一年
        filename: 可选的本地CSV文件名
    返回:
        pd.DataFrame
    """
    try:
        import yfinance as yf
    except ImportError:
        print("未检测到yfinance库，正在尝试安装...")
        os.system(f"{sys.executable} -m pip install yfinance")
        import yfinance as yf

    if start is None:
        start = (datetime.date.today() - datetime.timedelta(days=365)).strftime("%Y-%m-%d")
    if end is None:
        end = datetime.date.today().strftime("%Y-%m-%d")

    print(f"正在从Yahoo Finance下载 {symbol} 数据 ({start} ~ {end}) ...")
    try:
        df = yf.download(symbol, start=start, end=end)
        if not df.empty:
            df = df.reset_index()
            df = df.rename(columns={"Adj Close": "Adj_Close"})
            return df
        else:
            print("Yahoo数据为空，尝试本地CSV...")
    except Exception as e:
        print(f"Yahoo下载失败: {e}，尝试本地CSV...")

    if os.path.exists(filename):
        print(f"从 '{filename}' 加载数据...")
        return pd.read_csv(filename)
    else:
        print(f"未找到 '{filename}'。正在生成模拟数据...")
        np.random.seed(42) # 保证每次生成的随机数一致
        data_points = 200
        close_prices = 100 + np.cumsum(np.random.randn(data_points))
        high_prices = close_prices + np.random.uniform(0, 5, data_points)
        low_prices = close_prices - np.random.uniform(0, 5, data_points)
        open_prices = (high_prices + low_prices) / 2
        volume = np.random.randint(100000, 5000000, data_points)
        df = pd.DataFrame({
            'Date': pd.to_datetime(pd.date_range(start='2024-01-01', periods=data_points)),
            'Open': open_prices,
            'High': high_prices,
            'Low': low_prices,
            'Close': close_prices,
            'Volume': volume
        })
        return df

# --- 4. 主程序入口 ---
if __name__ == "__main__":
    # 支持命令行参数指定股票代码
    import argparse
    parser = argparse.ArgumentParser(description="BOLL+MACD+KDJ三重确认策略分析器")
    parser.add_argument("--symbol", type=str, default="AAPL", help="股票代码, 如AAPL、SPY等")
    parser.add_argument("--start", type=str, default=None, help="起始日期, 如2023-01-01")
    parser.add_argument("--end", type=str, default=None, help="结束日期, 如2024-01-01")
    args = parser.parse_args()
    stock_data = load_or_create_data(symbol=args.symbol, start=args.start, end=args.end)

    # 执行策略分析
    analyzed_data = analyze_signals(stock_data)

    # 筛选出有信号的交易日
    buy_signals = analyzed_data[analyzed_data['BUY_SIGNAL']]
    sell_signals = analyzed_data[analyzed_data['SELL_SIGNAL']]

    print("\n" + "="*50)
    print("策略分析结果")
    print("="*50)

    if buy_signals.empty:
        print("\n未检测到明确的买入信号。")
    else:
        print(f"\n检测到 {len(buy_signals)} 个买入信号:")
        # 为了方便查看，只显示部分关键列
        print(buy_signals[['Date', 'Close', 'BUY_SIGNAL']])

    if sell_signals.empty:
        print("\n未检测到明确的卖出信号。")
    else:
        print(f"\n检测到 {len(sell_signals)} 个卖出信号:")
        # 为了方便查看，只显示部分关键列
        print(sell_signals[['Date', 'Close', 'SELL_SIGNAL']])
        
    # (可选) 如果需要，可以取消下面的注释，将完整结果保存到新的CSV文件中
    # output_filename = "analyzed_results.csv"
    # analyzed_data.to_csv(output_filename, index=False)
    # print(f"\n完整分析结果已保存到 '{output_filename}'") 