"""
Web Dashboard Application
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import os
import sys
import subprocess
import time
import psutil
import asyncio
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import logging
from pathlib import Path
import json
import threading
from queue import Queue
import traceback

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from components.hybrid_aggregator import HybridAggregator
from components.signal_analytics import SignalAnalyticsEngine
from components.performance_optimizer import PerformanceOptimizer
from components.performance_metrics import PerformanceMetrics
from components.risk_manager import RiskManager
from components.backtest_engine import BacktestEngine
from components.execution_engine import ExecutionEngine
from components.data_collector import DataCollector
from components.performance_monitor import PerformanceMonitor

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(project_root, 'logs', 'web_dashboard.log')),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class WebApp:
    def __init__(self):
        """初始化Web应用"""
        self.setup_page()
        self.initialize_components()
        self.load_css()
        
    def setup_page(self):
        """设置页面配置"""
        st.set_page_config(
            page_title="Trading System Dashboard",
            page_icon="📈",
            layout="wide",
            initial_sidebar_state="expanded"
        )
        
    def load_css(self):
        """加载自定义CSS样式"""
        st.markdown("""
        <style>
        .main-header {
            font-size: 2.5rem;
            color: #1E88E5;
            text-align: center;
            margin-bottom: 2rem;
            font-weight: bold;
        }
        .sub-header {
            font-size: 1.8rem;
            color: #424242;
            margin: 1.5rem 0;
            font-weight: bold;
        }
        .metric-card {
            background-color: #f8f9fa;
            padding: 1.5rem;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .stButton>button {
            width: 100%;
            background-color: #1E88E5;
            color: white;
            border: none;
            padding: 0.5rem 1rem;
            border-radius: 5px;
            font-weight: bold;
        }
        .stButton>button:hover {
            background-color: #1565C0;
        }
        </style>
        """, unsafe_allow_html=True)
        
    def initialize_components(self):
        """初始化系统组件"""
        try:
            # 初始化信号聚合器
            self.signal_aggregator = HybridAggregator()
            
            # 初始化信号分析引擎
            self.signal_analytics = SignalAnalyticsEngine()
            
            # 初始化性能优化器
            self.performance_optimizer = PerformanceOptimizer()
            
            # 初始化风险管理器
            self.risk_manager = RiskManager()
            
            # 初始化回测引擎
            self.backtest_engine = BacktestEngine()
            
            # 初始化执行引擎
            self.execution_engine = ExecutionEngine()
            
            # 初始化数据收集器
            self.data_collector = DataCollector()
            
            # 初始化性能监控器
            self.performance_monitor = PerformanceMonitor()
            
            logger.info("All components initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing components: {str(e)}")
            st.error(f"Error initializing system components: {str(e)}")
            
    def run(self):
        """运行Web应用"""
        try:
            # 显示主标题
            st.markdown('<div class="main-header">Trading System Dashboard</div>', 
                       unsafe_allow_html=True)
            
            # 创建侧边栏
            self.display_sidebar()
            
            # 创建主内容区域
            self.display_main_content()
            
        except Exception as e:
            logger.error(f"Error running web app: {str(e)}")
            st.error(f"An error occurred: {str(e)}")
            
    def display_sidebar(self):
        """显示侧边栏"""
        with st.sidebar:
            st.markdown("### System Control")
            
            # 系统状态
            st.markdown("#### System Status")
            system_status = self.get_system_status()
            st.markdown(f"**Status**: {system_status['status']}")
            st.markdown(f"**Last Update**: {system_status['last_update']}")
            
            # 组件控制
            self.display_component_control()
            
            # 系统设置
            st.markdown("### System Settings")
            self.display_system_settings()
            
    def display_main_content(self):
        """显示主内容区域"""
        # 创建标签页
        tab1, tab2, tab3, tab4 = st.tabs([
            "Signal Analysis", 
            "Performance Monitor",
            "Risk Management",
            "Backtest Results"
        ])
        
        with tab1:
            self.display_signal_analysis()
            
        with tab2:
            self.display_performance_monitor()
            
        with tab3:
            self.display_risk_management()
            
        with tab4:
            self.display_backtest_results()
            
    def get_system_status(self) -> Dict[str, str]:
        """获取系统状态"""
        return {
            "status": "Running",
            "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
    def display_system_settings(self):
        """显示系统设置"""
        st.markdown("#### Signal Settings")
        
        # 信号聚合器设置
        confidence_threshold = st.slider(
            "Confidence Threshold",
            min_value=0.0,
            max_value=1.0,
            value=0.7,
            step=0.1
        )
        
        if st.button("Update Settings"):
            try:
                self.signal_aggregator.set_confidence_threshold(confidence_threshold)
                st.success("Settings updated successfully")
            except Exception as e:
                st.error(f"Error updating settings: {str(e)}")
                
    def display_signal_analysis(self):
        """显示信号分析"""
        st.markdown('<div class="sub-header">Signal Analysis</div>', 
                   unsafe_allow_html=True)
        
        # 获取当前信号
        signals_df = self.signal_aggregator.get_current_signals()
        
        if not signals_df.empty:
            # 显示信号统计信息
            stats = self.signal_aggregator.get_signal_statistics()
            
            if stats['status'] == 'success':
                # 创建指标卡片
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric(
                        "Total Signals",
                        stats['statistics']['total_signals']
                    )
                    
                with col2:
                    st.metric(
                        "Mean Score",
                        f"{stats['statistics']['mean_score']:.2f}"
                    )
                    
                with col3:
                    st.metric(
                        "Mean Confidence",
                        f"{stats['statistics']['mean_confidence']:.2f}"
                    )
                    
                with col4:
                    st.metric(
                        "Latest Score",
                        f"{stats['statistics']['latest_score']:.2f}"
                    )
                
                # 显示信号图表
                st.markdown("### Signal Trends")
                
                # 创建信号趋势图
                fig = go.Figure()
                
                # 添加最终得分线
                fig.add_trace(go.Scatter(
                    x=signals_df.index,
                    y=signals_df['final_score'],
                    name='Final Score',
                    line=dict(color='#1E88E5')
                ))
                
                # 添加置信度线
                fig.add_trace(go.Scatter(
                    x=signals_df.index,
                    y=signals_df['confidence'],
                    name='Confidence',
                    line=dict(color='#43A047')
                ))
                
                # 添加波动率线
                fig.add_trace(go.Scatter(
                    x=signals_df.index,
                    y=signals_df['volatility'],
                    name='Volatility',
                    line=dict(color='#E53935')
                ))
                
                # 更新布局
                fig.update_layout(
                    title='Signal Trends',
                    xaxis_title='Time',
                    yaxis_title='Value',
                    hovermode='x unified',
                    showlegend=True
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
                # 显示信号分析报告
                st.markdown("### Signal Analysis Report")
                
                # 计算信号指标
                metrics = self.signal_analytics.calculate_metrics(signals_df)
                
                if metrics['status'] == 'success':
                    # 创建指标卡片
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        st.metric(
                            "Cumulative Alpha",
                            f"{metrics['metrics']['cumulative_alpha']:.2f}"
                        )
                        
                    with col2:
                        st.metric(
                            "Sharpe Ratio",
                            f"{metrics['metrics']['sharpe_ratio']:.2f}"
                        )
                        
                    with col3:
                        st.metric(
                            "Signal Stability",
                            f"{metrics['metrics']['signal_stability']:.2f}"
                        )
                        
                    with col4:
                        st.metric(
                            "Anomaly Count",
                            metrics['metrics']['anomaly_count']
                        )
                    
                    # 显示异常信号
                    anomalies = self.signal_analytics.detect_abnormal_signals(signals_df)
                    
                    if not anomalies.empty:
                        st.markdown("### Abnormal Signals")
                        st.dataframe(anomalies)
                        
                else:
                    st.error(f"Error calculating metrics: {metrics['error']}")
                    
            else:
                st.error(f"Error getting signal statistics: {stats['error']}")
                
        else:
            st.warning("No signals available for analysis")
            
    def display_performance_monitor(self):
        """显示性能监控"""
        st.markdown('<div class="sub-header">Performance Monitor</div>', 
                   unsafe_allow_html=True)
        
        # 获取系统指标
        metrics = self.performance_monitor.get_system_metrics()
        
        if metrics['status'] == 'success':
            # 创建指标卡片
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric(
                    "CPU Usage",
                    f"{metrics['metrics']['cpu_usage']:.1f}%"
                )
                
            with col2:
                st.metric(
                    "Memory Usage",
                    f"{metrics['metrics']['memory_usage']:.1f}%"
                )
                
            with col3:
                st.metric(
                    "Disk Usage",
                    f"{metrics['metrics']['disk_usage']:.1f}%"
                )
                
            with col4:
                st.metric(
                    "Uptime",
                    f"{self.performance_monitor.get_uptime():.1f}s"
                )
            
            # 显示性能摘要
            summary = self.performance_monitor.get_performance_summary()
            
            if summary['status'] == 'success':
                st.markdown("### Performance Summary")
                
                # 创建性能摘要图表
                fig = go.Figure()
                
                # 添加CPU使用率线
                fig.add_trace(go.Scatter(
                    x=list(range(len(summary['summary']['averages']))),
                    y=[summary['summary']['averages']['cpu_usage']],
                    name='CPU Usage',
                    line=dict(color='#1E88E5')
                ))
                
                # 添加内存使用率线
                fig.add_trace(go.Scatter(
                    x=list(range(len(summary['summary']['averages']))),
                    y=[summary['summary']['averages']['memory_usage']],
                    name='Memory Usage',
                    line=dict(color='#43A047')
                ))
                
                # 添加磁盘使用率线
                fig.add_trace(go.Scatter(
                    x=list(range(len(summary['summary']['averages']))),
                    y=[summary['summary']['averages']['disk_usage']],
                    name='Disk Usage',
                    line=dict(color='#E53935')
                ))
                
                # 更新布局
                fig.update_layout(
                    title='Performance Summary',
                    xaxis_title='Time',
                    yaxis_title='Usage (%)',
                    hovermode='x unified',
                    showlegend=True
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
            else:
                st.error(f"Error getting performance summary: {summary['error']}")
                
        else:
            st.error(f"Error getting system metrics: {metrics['error']}")
            
    def display_risk_management(self):
        """显示风险管理"""
        st.markdown('<div class="sub-header">Risk Management</div>', 
                   unsafe_allow_html=True)
        
        # 获取风险指标
        metrics = self.risk_manager.get_risk_metrics()
        
        if metrics['status'] == 'success':
            # 创建指标卡片
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric(
                    "Portfolio Risk",
                    f"{metrics['metrics']['portfolio_risk']:.2f}"
                )
                
            with col2:
                st.metric(
                    "Position Risk",
                    f"{metrics['metrics']['position_risk']:.2f}"
                )
                
            with col3:
                st.metric(
                    "Market Risk",
                    f"{metrics['metrics']['market_risk']:.2f}"
                )
                
            with col4:
                st.metric(
                    "Liquidity Risk",
                    f"{metrics['metrics']['liquidity_risk']:.2f}"
                )
            
            # 显示风险限制
            st.markdown("### Risk Limits")
            
            limits = self.risk_manager.get_risk_limits()
            
            # 创建风险限制图表
            fig = go.Figure()
            
            # 添加风险指标柱状图
            fig.add_trace(go.Bar(
                x=list(metrics['metrics'].keys()),
                y=list(metrics['metrics'].values()),
                name='Current Risk',
                marker_color='#1E88E5'
            ))
            
            # 添加风险限制线
            fig.add_trace(go.Scatter(
                x=list(limits.keys()),
                y=list(limits.values()),
                name='Risk Limits',
                line=dict(color='#E53935', dash='dash')
            ))
            
            # 更新布局
            fig.update_layout(
                title='Risk Metrics vs Limits',
                xaxis_title='Risk Type',
                yaxis_title='Value',
                hovermode='x unified',
                showlegend=True
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
        else:
            st.error(f"Error getting risk metrics: {metrics['error']}")
            
    def display_backtest_results(self):
        """显示回测结果"""
        st.markdown('<div class="sub-header">Backtest Results</div>', 
                   unsafe_allow_html=True)
        
        # 获取回测结果
        results = self.backtest_engine.get_backtest_results()
        
        if results['status'] == 'success':
            # 创建指标卡片
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric(
                    "Total Return",
                    f"{results['results']['total_return']:.2%}"
                )
                
            with col2:
                st.metric(
                    "Sharpe Ratio",
                    f"{results['results']['sharpe_ratio']:.2f}"
                )
                
            with col3:
                st.metric(
                    "Max Drawdown",
                    f"{results['results']['max_drawdown']:.2%}"
                )
                
            with col4:
                st.metric(
                    "Win Rate",
                    f"{results['results']['win_rate']:.2%}"
                )
            
            # 显示回测图表
            st.markdown("### Backtest Performance")
            
            # 创建回测图表
            self.display_backtest_chart(results['results'])
            
            # 显示交易记录
            st.markdown("### Trade History")
            
            trades_df = pd.DataFrame(results['results']['trades'])
            st.dataframe(trades_df)
            
        else:
            st.error(f"Error getting backtest results: {results['error']}")
            
    def display_backtest_chart(self, backtest_results: Dict[str, Any]):
        """显示回测图表"""
        # 创建回测图表
        fig = go.Figure()
        
        # 添加收益率线
        fig.add_trace(go.Scatter(
            x=[t['timestamp'] for t in backtest_results['trades']],
            y=[t['price'] for t in backtest_results['trades']],
            name='Price',
            line=dict(color='#1E88E5')
        ))
        
        # 更新布局
        fig.update_layout(
            title='Backtest Performance',
            xaxis_title='Time',
            yaxis_title='Price',
            hovermode='x unified',
            showlegend=True
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
    def display_component_control(self):
        """显示组件控制"""
        st.markdown("#### Component Control")
        
        # 组件状态
        components = [
            "Signal Aggregator",
            "Performance Optimizer",
            "Risk Manager",
            "Backtest Engine",
            "Execution Engine",
            "Data Collector",
            "Performance Monitor"
        ]
        
        for component in components:
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.markdown(f"**{component}**")
                
            with col2:
                if self.is_component_running(component):
                    if st.button("Stop", key=f"stop_{component}"):
                        self.stop_component(component)
                else:
                    if st.button("Start", key=f"start_{component}"):
                        self.start_component(component)
                        
    def is_component_running(self, component_name: str) -> bool:
        """检查组件是否运行中"""
        try:
            # 示例：检查组件状态
            return True
        except Exception as e:
            logger.error(f"Error checking component status: {str(e)}")
            return False
            
    def start_component(self, component_name: str):
        """启动组件"""
        try:
            # 示例：启动组件
            st.success(f"{component_name} started successfully")
        except Exception as e:
            st.error(f"Error starting {component_name}: {str(e)}")
            
    def stop_component(self, component_name: str):
        """停止组件"""
        try:
            # 示例：停止组件
            st.success(f"{component_name} stopped successfully")
        except Exception as e:
            st.error(f"Error stopping {component_name}: {str(e)}")
            
def main():
    """主函数"""
    app = WebApp()
    app.run()
    
if __name__ == "__main__":
    main() 