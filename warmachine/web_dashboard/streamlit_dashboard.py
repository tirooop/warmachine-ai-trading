import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import json
from datetime import datetime, timedelta
import yfinance as yf
from utils.strategy_executor import StrategyExecutor
from utils.preset_strategy_prompt import StrategyPromptContext
import os
from io import StringIO
import base64

# 设置页面标题和布局
st.set_page_config(
    page_title="AI 期权交易策略系统",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义 CSS 样式
st.markdown("""
<style>
    .main-header {
        font-size: 42px;
        font-weight: bold;
        color: #1E88E5;
        margin-bottom: 20px;
    }
    .sub-header {
        font-size: 24px;
        font-weight: bold;
        color: #424242;
        margin-top: 30px;
        margin-bottom: 10px;
    }
    .info-box {
        background-color: #F5F5F5;
        padding: 15px;
        border-radius: 5px;
        margin-bottom: 20px;
    }
    .bullish {
        color: #4CAF50;
        font-weight: bold;
    }
    .bearish {
        color: #F44336;
        font-weight: bold;
    }
    .neutral {
        color: #FF9800;
        font-weight: bold;
    }
    .signal-card {
        background-color: #F9F9F9;
        padding: 15px;
        border-radius: 5px;
        margin-bottom: 10px;
        border-left: 5px solid #1E88E5;
    }
    .backtest-metrics {
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
    }
    .metric-box {
        background-color: #E1F5FE;
        padding: 10px;
        border-radius: 5px;
        flex: 1 1 120px;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# 初始化 Session State
if 'executor' not in st.session_state:
    st.session_state.executor = StrategyExecutor()
if 'signals_history' not in st.session_state:
    st.session_state.signals_history = []
if 'current_signal' not in st.session_state:
    st.session_state.current_signal = None

# 主标题
st.markdown('<div class="main-header">AI 期权交易策略系统</div>', unsafe_allow_html=True)

# 侧边栏 - 配置
st.sidebar.markdown("## 配置")

# 股票选择
symbol = st.sidebar.text_input("股票代码", "AAPL")

# 时间范围选择
timeframe_options = ["1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"]
timeframe = st.sidebar.selectbox("时间范围", timeframe_options, index=3)

# 策略选择
strategy_options = ["ema_rsi", "macd_cross", "breakout_volume"]
selected_strategy = st.sidebar.selectbox("回测策略", strategy_options)

# 执行按钮
if st.sidebar.button("分析并生成策略"):
    with st.spinner("正在分析市场数据..."):
        # 执行策略
        result = st.session_state.executor.execute(symbol)
        st.session_state.current_signal = result
        if result.get("status") == "success":
            st.session_state.signals_history.append(result)
            st.success(f"成功生成 {symbol} 的交易策略")
        elif result.get("status") == "no_signal":
            st.info(f"未生成 {symbol} 的交易信号，市场条件不满足")
        else:
            st.error(f"分析 {symbol} 时发生错误: {result.get('error', '未知错误')}")

# 创建主页面布局
col1, col2 = st.columns([2, 1])

# 左侧面板 - 图表区域
with col1:
    st.markdown('<div class="sub-header">价格走势与技术指标</div>', unsafe_allow_html=True)
    
    # 加载股票数据
    data = yf.download(symbol, period=timeframe)
    
    if not data.empty:
        # 准备绘图数据
        # 添加技术指标
        data['EMA20'] = data['Close'].ewm(span=20).mean()
        data['EMA50'] = data['Close'].ewm(span=50).mean()
        
        # RSI
        delta = data['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        data['RSI'] = 100 - (100 / (1 + rs))
        
        # MACD
        data['EMA12'] = data['Close'].ewm(span=12).mean()
        data['EMA26'] = data['Close'].ewm(span=26).mean()
        data['MACD'] = data['EMA12'] - data['EMA26']
        data['Signal'] = data['MACD'].ewm(span=9).mean()
        data['MACD_Hist'] = data['MACD'] - data['Signal']
        
        # 创建子图
        fig = make_subplots(rows=3, cols=1, shared_xaxes=True, 
                            vertical_spacing=0.05, 
                            subplot_titles=("价格", "RSI", "MACD"),
                            row_heights=[0.6, 0.2, 0.2])
        
        # 绘制 K 线图
        fig.add_trace(go.Candlestick(
            x=data.index,
            open=data['Open'],
            high=data['High'],
            low=data['Low'],
            close=data['Close'],
            name="K线"
        ), row=1, col=1)
        
        # 添加移动平均线
        fig.add_trace(go.Scatter(
            x=data.index,
            y=data['EMA20'],
            name="EMA20",
            line=dict(color='rgba(240, 128, 128, 0.8)')
        ), row=1, col=1)
        
        fig.add_trace(go.Scatter(
            x=data.index,
            y=data['EMA50'],
            name="EMA50",
            line=dict(color='rgba(50, 171, 96, 0.8)')
        ), row=1, col=1)
        
        # 添加 RSI
        fig.add_trace(go.Scatter(
            x=data.index,
            y=data['RSI'],
            name="RSI",
            line=dict(color='rgba(91, 155, 213, 1.0)')
        ), row=2, col=1)
        
        # 添加 RSI 参考线
        fig.add_trace(go.Scatter(
            x=data.index,
            y=[70] * len(data.index),
            name="超买线",
            line=dict(color='rgba(255, 0, 0, 0.5)', dash='dash')
        ), row=2, col=1)
        
        fig.add_trace(go.Scatter(
            x=data.index,
            y=[30] * len(data.index),
            name="超卖线",
            line=dict(color='rgba(0, 255, 0, 0.5)', dash='dash')
        ), row=2, col=1)
        
        # 添加 MACD
        fig.add_trace(go.Scatter(
            x=data.index,
            y=data['MACD'],
            name="MACD",
            line=dict(color='rgba(91, 155, 213, 1.0)')
        ), row=3, col=1)
        
        fig.add_trace(go.Scatter(
            x=data.index,
            y=data['Signal'],
            name="Signal",
            line=dict(color='rgba(255, 102, 0, 1.0)')
        ), row=3, col=1)
        
        # 添加 MACD 柱状图
        colors = ['rgba(0, 255, 0, 0.5)' if val >= 0 else 'rgba(255, 0, 0, 0.5)' for val in data['MACD_Hist']]
        fig.add_trace(go.Bar(
            x=data.index,
            y=data['MACD_Hist'],
            name="MACD Histogram",
            marker=dict(color=colors)
        ), row=3, col=1)
        
        # 更新布局
        fig.update_layout(
            height=600,
            title=f"{symbol} 技术分析图表",
            xaxis_rangeslider_visible=False,
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )
        
        # 显示图表
        st.plotly_chart(fig, use_container_width=True)
        
        # 显示最新数据
        latest = data.iloc[-1]
        
        st.markdown('<div class="sub-header">最新市场数据</div>', unsafe_allow_html=True)
        
        market_metrics = {
            "收盘价": f"${latest['Close']:.2f}",
            "当日变动": f"{(latest['Close'] - latest['Open']) / latest['Open']:.2%}",
            "成交量": f"{latest['Volume']:,}",
            "RSI (14)": f"{latest['RSI']:.2f}",
            "MACD": f"{latest['MACD']:.2f}",
            "EMA20": f"{latest['EMA20']:.2f}",
            "EMA50": f"{latest['EMA50']:.2f}"
        }
        
        # 显示最新市场数据
        cols = st.columns(4)
        for i, (metric, value) in enumerate(market_metrics.items()):
            with cols[i % 4]:
                st.metric(metric, value)

# 右侧面板 - 信号和回测结果
with col2:
    st.markdown('<div class="sub-header">AI 策略分析</div>', unsafe_allow_html=True)
    
    if st.session_state.current_signal and st.session_state.current_signal.get("status") == "success":
        signal = st.session_state.current_signal.get("signal", {})
        
        # 显示信号卡片
        bias = signal.get("bias", "NEUTRAL")
        bias_class = "bullish" if bias == "BULLISH" else "bearish" if bias == "BEARISH" else "neutral"
        
        signal_card = f"""
        <div class="signal-card">
            <h3>{symbol} 交易信号</h3>
            <p>方向: <span class="{bias_class}">{bias}</span></p>
            <p>信号强度: {signal.get('signal_strength', 0):.2f}</p>
            <p>信号类型: {signal.get('signal_type', 'UNKNOWN')}</p>
            <p>生成时间: {signal.get('timestamp', datetime.now().isoformat())[0:16].replace('T', ' ')}</p>
        </div>
        """
        st.markdown(signal_card, unsafe_allow_html=True)
        
        # 显示建议策略
        suggested_strategy = signal.get('suggested_strategy', {})
        if suggested_strategy:
            st.markdown('<div class="sub-header">建议策略</div>', unsafe_allow_html=True)
            
            strategy_type = suggested_strategy.get('type', 'Unknown')
            strike = suggested_strategy.get('strike', 0)
            expiration_days = suggested_strategy.get('expiration_days', 0)
            reason = suggested_strategy.get('reason', '')
            
            st.info(f"""
            **策略类型**: {strategy_type}  
            **执行价**: ${strike:.2f}  
            **到期日**: {expiration_days} 天  
            **理由**: {reason}
            """)
        
        # 显示 AI 分析逻辑
        logic_chain = signal.get('logic_chain', [])
        if logic_chain:
            st.markdown('<div class="sub-header">AI 分析逻辑</div>', unsafe_allow_html=True)
            for i, logic in enumerate(logic_chain, 1):
                st.write(f"{i}. {logic}")
        
        # 显示风险因素
        risk_factors = signal.get('risk_factors', [])
        if risk_factors:
            st.markdown('<div class="sub-header">风险因素</div>', unsafe_allow_html=True)
            for i, risk in enumerate(risk_factors, 1):
                st.write(f"{i}. {risk}")
        
        # 显示回测结果
        backtest_results = signal.get('backtest_results', {})
        if backtest_results:
            st.markdown('<div class="sub-header">回测结果</div>', unsafe_allow_html=True)
            
            # 显示回测指标
            col1, col2 = st.columns(2)
            with col1:
                st.metric("总收益", f"{backtest_results.get('total_return', 0):.2%}")
                st.metric("夏普比率", f"{backtest_results.get('sharpe_ratio', 0):.2f}")
            with col2:
                st.metric("最大回撤", f"{backtest_results.get('max_drawdown', 0):.2%}")
                st.metric("胜率", f"{backtest_results.get('win_rate', 0):.2%}")
            
            # 显示回测交易次数
            st.write(f"交易次数: {backtest_results.get('trades_count', 0)}")
    else:
        st.info("请使用左侧边栏分析并生成交易策略")

# 信号历史
st.markdown('<div class="sub-header">信号历史</div>', unsafe_allow_html=True)

if st.session_state.signals_history:
    # 显示信号历史表格
    signals_df = pd.DataFrame([
        {
            "时间": s.get("timestamp", "")[:16].replace('T', ' '),
            "股票": s.get("symbol", ""),
            "方向": s.get("signal", {}).get("bias", ""),
            "信号强度": s.get("signal", {}).get("signal_strength", 0),
            "建议策略": s.get("signal", {}).get("suggested_strategy", {}).get("type", ""),
            "执行价": s.get("signal", {}).get("suggested_strategy", {}).get("strike", 0),
            "状态": "有效" if s.get("validation", {}).get("valid", False) else "无效"
        }
        for s in st.session_state.signals_history
    ])
    
    st.dataframe(signals_df, use_container_width=True)
    
    # 导出按钮
    if st.button("导出信号历史"):
        # 将信号历史转换为 CSV
        csv = signals_df.to_csv(index=False)
        b64 = base64.b64encode(csv.encode()).decode()
        href = f'<a href="data:file/csv;base64,{b64}" download="signals_history.csv">下载 CSV 文件</a>'
        st.markdown(href, unsafe_allow_html=True)
else:
    st.info("暂无信号历史记录")

# 页脚
st.markdown("---")
st.markdown("© 2023 AI 期权交易策略系统 | 免责声明：这不是投资建议，请自行承担风险") 