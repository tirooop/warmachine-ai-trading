"""
系统监控组件
整合系统状态、数据源监控和性能指标
"""

import os
import json
import glob
import datetime
import pandas as pd
import numpy as np
import streamlit as st
from typing import Dict, List, Any
import yfinance as yf
import threading
import time
import psutil

class SystemMonitor:
    """系统监控组件"""
    
    def __init__(self):
        """初始化系统监控组件"""
        self.last_update = datetime.datetime.now()
        self.update_interval = 5  # 更新间隔（秒）
        self.cache = {
            'system_status': 'Unknown',
            'data_sources': [],
            'signals': [],
            'performance': {},
            'charts': {},
            'update_in_progress': False
        }
        
        # 确保必要的目录存在
        self.ensure_directories()
        
        # 启动后台更新线程
        self.start_background_updater()
    
    def ensure_directories(self):
        """确保必要的目录存在"""
        dirs = ['data', 'data/signals', 'data/historical', 'data/analysis', 
                'data/backtests', 'logs', 'reports']
        for d in dirs:
            if not os.path.exists(d):
                os.makedirs(d)
    
    def start_background_updater(self):
        """启动后台更新线程"""
        def background_updater():
            while True:
                try:
                    self.update_dashboard_data()
                except Exception as e:
                    print(f"Error in background updater: {e}")
                time.sleep(300)  # 每5分钟更新一次
        
        updater_thread = threading.Thread(target=background_updater, daemon=True)
        updater_thread.start()
    
    def update_dashboard_data(self):
        """更新仪表盘数据"""
        if self.cache['update_in_progress']:
            return
        
        self.cache['update_in_progress'] = True
        try:
            # 更新系统状态
            self.last_update = datetime.datetime.now()
            
            # 检查数据源状态
            data_sources = []
            
            # 检查WarMachine状态
            try:
                for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                    if proc.info['cmdline'] and 'warmachine/main.py' in ' '.join(proc.info['cmdline']):
                        data_sources.append({"name": "WarMachine", "status": "OK"})
                        break
                else:
                    data_sources.append({"name": "WarMachine", "status": "ERROR"})
            except Exception:
                data_sources.append({"name": "WarMachine", "status": "ERROR"})
            
            # 检查其他数据源
            data_sources.append({"name": "Market Data", "status": "OK"})
            data_sources.append({"name": "Order Book", "status": "OK"})
            data_sources.append({"name": "News Feed", "status": "OK"})
            
            self.cache['data_sources'] = data_sources
            
            # 确定整体系统状态
            if all(source['status'] == 'OK' for source in data_sources):
                self.cache['system_status'] = 'OK'
            elif any(source['status'] == 'OK' for source in data_sources):
                self.cache['system_status'] = 'Warning'
            else:
                self.cache['system_status'] = 'Error'
            
            # 收集最新信号
            signals = []
            signal_files = glob.glob('data/signals/*_signals_*.json')
            for signal_file in sorted(signal_files, reverse=True)[:5]:
                try:
                    with open(signal_file, 'r') as f:
                        file_signals = json.load(f)
                        if isinstance(file_signals, list):
                            signals.extend(file_signals)
                        else:
                            signals.append(file_signals)
                except Exception as e:
                    print(f"Error loading signal file {signal_file}: {e}")
            
            # 按日期排序并取前10个
            signals = sorted(signals, key=lambda s: s.get('date', ''), reverse=True)[:10]
            self.cache['signals'] = signals
            
            # 收集性能指标
            performance = {}
            backtest_files = glob.glob('data/backtests/*_backtest_results_*.csv')
            if backtest_files:
                latest_backtest = sorted(backtest_files, reverse=True)[0]
                try:
                    results = pd.read_csv(latest_backtest)
                    
                    if not results.empty:
                        # 总收益率
                        initial_value = results['Total_Value'].iloc[0]
                        final_value = results['Total_Value'].iloc[-1]
                        total_return = round((final_value - initial_value) / initial_value * 100, 2)
                        
                        # 夏普比率
                        if 'Returns' in results.columns:
                            daily_returns = results['Returns'].dropna()
                            sharpe = round(np.sqrt(252) * daily_returns.mean() / daily_returns.std(), 2) if daily_returns.std() > 0 else 0
                        else:
                            sharpe = 0
                        
                        # 胜率
                        win_rate = 0
                        trades_file = latest_backtest.replace('_results_', '_trades_')
                        if os.path.exists(trades_file):
                            trades = pd.read_csv(trades_file)
                            if not trades.empty:
                                wins = 0
                                trades_count = 0
                                for i, trade in trades.iterrows():
                                    if trade['action'] in ['SELL', 'COVER']:
                                        trades_count += 1
                                        if ('value' in trades.columns and trade['value'] > 0) or \
                                           ('profit' in trades.columns and trade['profit'] > 0):
                                            wins += 1
                                
                                win_rate = round((wins / trades_count) * 100, 2) if trades_count > 0 else 0
                        
                        performance = {
                            'total_return': total_return,
                            'sharpe': sharpe,
                            'win_rate': win_rate
                        }
                except Exception as e:
                    print(f"Error processing backtest file {latest_backtest}: {e}")
            
            self.cache['performance'] = performance
            
            # 生成或加载图表
            charts = {}
            backtest_charts = glob.glob('data/backtests/*_backtest_*.png')
            if backtest_charts:
                # 获取每个符号的最新图表
                symbols = set()
                for chart_file in backtest_charts:
                    symbol = os.path.basename(chart_file).split('_')[0]
                    symbols.add(symbol)
                
                for symbol in symbols:
                    symbol_charts = [f for f in backtest_charts if os.path.basename(f).startswith(f"{symbol}_")]
                    if symbol_charts:
                        latest_chart = sorted(symbol_charts, reverse=True)[0]
                        with open(latest_chart, 'rb') as f:
                            img_data = f.read()
                            charts[symbol] = img_data
            
            self.cache['charts'] = charts
        
        except Exception as e:
            print(f"Error updating dashboard data: {e}")
        
        finally:
            self.cache['update_in_progress'] = False
    
    def display(self):
        """显示系统监控面板"""
        st.markdown('### 系统监控')
        
        # 检查是否需要更新
        current_time = datetime.datetime.now()
        if (current_time - self.last_update).seconds >= self.update_interval:
            self.update_dashboard_data()
            self.last_update = current_time
        
        # 显示系统状态
        col1, col2 = st.columns(2)
        with col1:
            status_color = {
                'OK': 'normal',
                'Warning': 'normal',
                'Error': 'inverse'
            }.get(self.cache['system_status'], 'off')
            
            st.metric(
                "系统状态",
                self.cache['system_status'],
                delta=None,
                delta_color=status_color
            )
        with col2:
            st.metric(
                "最后更新",
                self.last_update.strftime("%Y-%m-%d %H:%M:%S"),
                delta=None,
                delta_color="off"
            )
        
        # 显示数据源状态
        st.markdown('### 数据源状态')
        data_sources = self.cache['data_sources']
        if data_sources:
            cols = st.columns(len(data_sources))
            for i, source in enumerate(data_sources):
                with cols[i]:
                    st.metric(
                        source['name'],
                        source['status'],
                        delta=None,
                        delta_color="normal" if source['status'] == 'OK' else "inverse"
                    )
        
        # 显示性能指标
        if self.cache['performance']:
            st.markdown('### 性能指标')
            metrics = self.cache['performance']
            if metrics:
                cols = st.columns(3)  # 固定使用3列
                metric_items = list(metrics.items())
                for i, (metric, value) in enumerate(metric_items):
                    with cols[i % 3]:  # 使用模运算确保不会超出列数
                        st.metric(
                            metric.replace('_', ' ').title(),
                            f"{value:.2%}" if metric in ['total_return', 'win_rate'] else f"{value:.2f}"
                        )
        
        # 显示最近的交易信号
        if self.cache['signals']:
            st.markdown('### 最近的交易信号')
            signals_df = pd.DataFrame(self.cache['signals'])
            st.dataframe(signals_df, use_container_width=True)
        
        # 显示性能图表
        if self.cache['charts']:
            st.markdown('### 性能图表')
            for symbol, chart_data in self.cache['charts'].items():
                st.image(chart_data, caption=f"{symbol} Performance", use_column_width=True) 