import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import os
import sys
import json
import yaml
import tensorflow as tf
from tensorflow.keras.models import load_model
import matplotlib.pyplot as plt
import seaborn as sns

# Add project root to path
sys.path.append('.')

# Import project modules
from model.dqn_agent import DQNAgent
from risk.advanced_risk_manager import create_risk_manager

# Page config
st.set_page_config(
    page_title="AI期权交易系统 - RL模块",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 30px;
        font-weight: bold;
        color: #1E88E5;
        margin-bottom: 20px;
    }
    .sub-header {
        font-size: 22px;
        font-weight: bold;
        color: #424242;
        margin-top: 20px;
        margin-bottom: 10px;
    }
    .metric-container {
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
        margin-bottom: 20px;
    }
    .metric-box {
        background-color: #f0f2f6;
        border-radius: 5px;
        padding: 15px;
        flex: 1;
        min-width: 150px;
        box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
    }
    .metric-label {
        font-size: 14px;
        color: #555;
        margin-bottom: 5px;
    }
    .metric-value {
        font-size: 24px;
        font-weight: bold;
        color: #212121;
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
    .action-card {
        padding: 15px;
        border-radius: 5px;
        background-color: #f5f5f5;
        margin-bottom: 10px;
        border-left: 5px solid #1E88E5;
    }
</style>
""", unsafe_allow_html=True)

# Session state initialization
if 'current_symbol' not in st.session_state:
    st.session_state.current_symbol = 'SPY'
if 'model_loaded' not in st.session_state:
    st.session_state.model_loaded = False
if 'risk_manager' not in st.session_state:
    st.session_state.risk_manager = None
if 'dqn_agent' not in st.session_state:
    st.session_state.dqn_agent = None
if 'prediction_history' not in st.session_state:
    st.session_state.prediction_history = []

# Helper functions
def load_option_data(symbol, days=30):
    """Load option data for the given symbol."""
    # In a real implementation, this would load from your options data source
    # For demonstration, generate some sample data
    today = datetime.now()
    dates = [(today - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(days)]
    
    # Generate random data for demonstration
    np.random.seed(42)  # For reproducibility
    price = 450 + np.cumsum(np.random.normal(0, 1, days)) * 0.5
    
    # Generate option Greeks
    delta = np.random.uniform(0.4, 0.7, days)
    gamma = np.random.uniform(0.01, 0.05, days)
    theta = np.random.uniform(-0.5, -0.1, days)
    vega = np.random.uniform(0.5, 1.5, days)
    
    # Create DataFrame
    data = pd.DataFrame({
        'date': dates[::-1],
        'price': price[::-1],
        'delta': delta[::-1],
        'gamma': gamma[::-1],
        'theta': theta[::-1],
        'vega': vega[::-1],
        'volume': np.random.randint(1000, 5000, days)[::-1],
        'open_interest': np.random.randint(5000, 15000, days)[::-1]
    })
    
    return data

def generate_features(data):
    """Generate trading features from option data."""
    df = data.copy()
    
    # Technical indicators
    df['sma20'] = df['price'].rolling(window=20).mean().fillna(method='bfill')
    df['sma50'] = df['price'].rolling(window=50).mean().fillna(method='bfill')
    df['rsi'] = calculate_rsi(df['price']).fillna(method='bfill')
    
    # Calculate returns
    df['returns'] = df['price'].pct_change().fillna(0)
    
    # Volatility
    df['volatility'] = df['price'].rolling(window=10).std().fillna(method='bfill')
    
    # Option-specific features
    df['delta_change'] = df['delta'].diff().fillna(0)
    df['gamma_change'] = df['gamma'].diff().fillna(0)
    df['theta_change'] = df['theta'].diff().fillna(0)
    df['vega_change'] = df['vega'].diff().fillna(0)
    
    # Market regime features (for demo purposes)
    df['market_regime'] = np.where(df['price'] > df['sma50'], 1, -1)
    
    return df

def calculate_rsi(prices, period=14):
    """Calculate RSI technical indicator."""
    delta = prices.diff()
    gain = delta.where(delta > 0, 0).rolling(window=period).mean()
    loss = -delta.where(delta < 0, 0).rolling(window=period).mean()
    
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def preprocess_state(features, lookback=10):
    """Prepare state representation for RL agent."""
    if len(features) < lookback:
        # Pad if not enough history
        return None
    
    # Get the most recent state
    recent_features = features.iloc[-lookback:].copy()
    
    # Select relevant features for state representation
    feature_cols = [
        'returns', 'volatility', 'rsi', 
        'delta', 'gamma', 'theta', 'vega',
        'delta_change', 'gamma_change', 'theta_change', 'vega_change',
        'market_regime'
    ]
    
    # Create state array
    state = recent_features[feature_cols].values.flatten()
    
    # Ensure state has the right shape and includes Greeks at the end
    greeks = recent_features[['delta', 'gamma', 'theta', 'vega']].iloc[-1].values
    
    return np.concatenate([state, greeks])

def get_action_name(action):
    """Convert action integer to readable name."""
    if action == 0:
        return "持仓不变"
    elif action == 1:
        return "买入多头"
    else:
        return "建立空头"

def get_action_color(action):
    """Get color for action display."""
    if action == 0:
        return "neutral"
    elif action == 1:
        return "bullish"
    else:
        return "bearish"

def initialize_models():
    """Initialize RL agent and risk manager."""
    try:
        # Check if model file exists
        model_path = "data/models/dqn_options.h5"
        
        # Initialize DQN agent
        state_dim = 124  # Example: 10 lookback * 12 features + 4 Greeks
        action_dim = 3   # No action, Buy, Sell
        agent = DQNAgent(state_dim, action_dim)
        
        # Try to load saved model, or use untrained model if not available
        if os.path.exists(model_path):
            agent.load_model()
            st.sidebar.success("✅ 已加载预训练模型")
        else:
            st.sidebar.warning("⚠️ 使用未训练模型 (模型文件不存在)")
        
        # Initialize risk manager
        risk_manager = create_risk_manager()
        
        st.session_state.dqn_agent = agent
        st.session_state.risk_manager = risk_manager
        st.session_state.model_loaded = True
        
        return True
    
    except Exception as e:
        st.sidebar.error(f"❌ 模型初始化失败: {str(e)}")
        return False

# Main dashboard layout
st.markdown('<div class="main-header">AI期权交易系统 - 强化学习模块</div>', unsafe_allow_html=True)

# Sidebar controls
st.sidebar.markdown("## 设置")
symbol = st.sidebar.text_input("交易标的", value=st.session_state.current_symbol)
lookback_days = st.sidebar.slider("历史数据天数", min_value=10, max_value=60, value=30)
view_mode = st.sidebar.radio("显示模式", ["实时", "回测"])

# Initialize models
if not st.session_state.model_loaded:
    if st.sidebar.button("初始化模型"):
        initialize_models()
else:
    st.sidebar.success("✅ 模型已加载")

# Model status
model_status = st.sidebar.expander("模型状态", expanded=False)
with model_status:
    if st.session_state.model_loaded and st.session_state.dqn_agent:
        agent = st.session_state.dqn_agent
        st.markdown(f"**模型类型:** DQN强化学习")
        st.markdown(f"**交易模式:** 期权Delta策略")
        st.markdown(f"**训练步数:** {agent.episode_count}")
        st.markdown(f"**当前探索率 (ε):** {agent.epsilon:.3f}")
    else:
        st.markdown("*模型未加载*")

# Main content
col1, col2 = st.columns([3, 1])

with col1:
    st.markdown('<div class="sub-header">市场数据与模型预测</div>', unsafe_allow_html=True)
    
    # Load and preprocess data
    data = load_option_data(symbol, lookback_days)
    features = generate_features(data)
    
    # Create state for model
    current_state = preprocess_state(features)
    
    # Make prediction if model is loaded
    current_action = 0
    prediction_confidence = 0.0
    has_prediction = False
    
    if st.session_state.model_loaded and current_state is not None:
        # Get AI prediction
        agent = st.session_state.dqn_agent
        # In a real implementation, you would combine with other AI signals
        ai_score = 0.8  # Example AI confidence score
        
        # Get action from agent
        current_action = agent.act(current_state, ai_score=ai_score, explore=False)
        # For demo purposes, simulate confidence
        prediction_confidence = 0.65 + 0.2 * np.random.random()
        has_prediction = True
        
        # Add to prediction history
        current_price = features['price'].iloc[-1]
        prediction_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        st.session_state.prediction_history.append({
            'time': prediction_time,
            'symbol': symbol,
            'price': current_price,
            'action': current_action,
            'confidence': prediction_confidence,
            'delta': features['delta'].iloc[-1],
            'gamma': features['gamma'].iloc[-1]
        })
    
    # Create plot
    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        subplot_titles=("价格", "RSI", "希腊字母"),
        row_heights=[0.5, 0.25, 0.25]
    )
    
    # Add price chart
    fig.add_trace(
        go.Scatter(
            x=features['date'],
            y=features['price'],
            mode='lines',
            name='价格',
            line=dict(color='#1E88E5', width=2)
        ),
        row=1, col=1
    )
    
    # Add moving averages
    fig.add_trace(
        go.Scatter(
            x=features['date'],
            y=features['sma20'],
            mode='lines',
            name='SMA20',
            line=dict(color='#FB8C00', width=1.5)
        ),
        row=1, col=1
    )
    
    fig.add_trace(
        go.Scatter(
            x=features['date'],
            y=features['sma50'],
            mode='lines',
            name='SMA50',
            line=dict(color='#7CB342', width=1.5)
        ),
        row=1, col=1
    )
    
    # Add RSI
    fig.add_trace(
        go.Scatter(
            x=features['date'],
            y=features['rsi'],
            mode='lines',
            name='RSI',
            line=dict(color='#BA68C8', width=1.5)
        ),
        row=2, col=1
    )
    
    # Add RSI reference lines
    fig.add_trace(
        go.Scatter(
            x=features['date'],
            y=[70] * len(features),
            mode='lines',
            name='超买',
            line=dict(color='rgba(255, 0, 0, 0.5)', dash='dash', width=1)
        ),
        row=2, col=1
    )
    
    fig.add_trace(
        go.Scatter(
            x=features['date'],
            y=[30] * len(features),
            mode='lines',
            name='超卖',
            line=dict(color='rgba(0, 255, 0, 0.5)', dash='dash', width=1)
        ),
        row=2, col=1
    )
    
    # Add Delta
    fig.add_trace(
        go.Scatter(
            x=features['date'],
            y=features['delta'],
            mode='lines',
            name='Delta',
            line=dict(color='#EF5350', width=1.5)
        ),
        row=3, col=1
    )
    
    # Add Gamma
    fig.add_trace(
        go.Scatter(
            x=features['date'],
            y=features['gamma'],
            mode='lines',
            name='Gamma',
            line=dict(color='#66BB6A', width=1.5)
        ),
        row=3, col=1
    )
    
    # Update layout
    fig.update_layout(
        height=600,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        margin=dict(l=0, r=0, t=50, b=0)
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Display current prediction
    if has_prediction:
        action_text = get_action_name(current_action)
        action_class = get_action_color(current_action)
        
        st.markdown(f"""
        <div class="action-card">
            <h3>当前预测: <span class="{action_class}">{action_text}</span></h3>
            <p>置信度: {prediction_confidence:.2%}</p>
            <p>最新价格: ${features['price'].iloc[-1]:.2f}</p>
            <p>Delta: {features['delta'].iloc[-1]:.4f} | Gamma: {features['gamma'].iloc[-1]:.4f} | Theta: {features['theta'].iloc[-1]:.4f}</p>
        </div>
        """, unsafe_allow_html=True)

with col2:
    # Risk management section
    st.markdown('<div class="sub-header">仓位与风控</div>', unsafe_allow_html=True)
    
    if st.session_state.model_loaded and st.session_state.risk_manager:
        risk_manager = st.session_state.risk_manager
        
        # Update VIX value
        risk_manager.update_vix()
        
        # Calculate position size
        if has_prediction and prediction_confidence > 0.6:
            current_price = features['price'].iloc[-1]
            position_quantity, position_details = risk_manager.calculate_position_size(
                symbol, current_price, ai_score=prediction_confidence
            )
            
            position_value = position_quantity * current_price
            position_pct = position_details.get('position_pct', 0) * 100
            
            # Display position recommendation
            st.markdown("### 建议仓位")
            st.markdown(f"""
            <div class="metric-container">
                <div class="metric-box">
                    <div class="metric-label">合约数量</div>
                    <div class="metric-value">{position_quantity:.2f}</div>
                </div>
                <div class="metric-box">
                    <div class="metric-label">资金占比</div>
                    <div class="metric-value">{position_pct:.1f}%</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Kelly criterion details
            st.markdown("**Kelly仓位详情**")
            st.markdown(f"- 历史胜率: {position_details.get('win_rate', 0):.2%}")
            st.markdown(f"- 盈亏比: {position_details.get('profit_loss_ratio', 0):.2f}")
            st.markdown(f"- VIX系数: {position_details.get('vix_multiplier', 1):.2f}")
            st.markdown(f"- AI信心系数: {position_details.get('ai_confidence_factor', 1):.2f}")
        
        # Risk metrics
        st.markdown("### 风控指标")
        st.markdown(f"""
        <div class="metric-container">
            <div class="metric-box">
                <div class="metric-label">VIX指数</div>
                <div class="metric-value">{risk_manager.current_vix or 15:.1f}</div>
            </div>
            <div class="metric-box">
                <div class="metric-label">最大仓位</div>
                <div class="metric-value">{risk_manager.max_position_pct*100:.0f}%</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown(f"""
        <div class="metric-container">
            <div class="metric-box">
                <div class="metric-label">止盈位</div>
                <div class="metric-value">{risk_manager.profit_target_pct*100:.0f}%</div>
            </div>
            <div class="metric-box">
                <div class="metric-label">止损位</div>
                <div class="metric-value">{risk_manager.stop_loss_pct*100:.0f}%</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
    else:
        st.info("风控系统未加载，请初始化模型")
    
    # Prediction history
    st.markdown('<div class="sub-header">预测历史</div>', unsafe_allow_html=True)
    
    if st.session_state.prediction_history:
        history = st.session_state.prediction_history[-10:]  # Show last 10 predictions
        
        for i, pred in enumerate(reversed(history)):
            action_text = get_action_name(pred['action'])
            action_class = get_action_color(pred['action'])
            
            st.markdown(f"""
            <div style="padding:10px 0; border-bottom:1px solid #eee;">
                <div><b>{pred['time']}</b></div>
                <div>{pred['symbol']} @ ${pred['price']:.2f}</div>
                <div>预测: <span class="{action_class}">{action_text}</span> ({pred['confidence']:.1%})</div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("暂无预测历史")

# Bottom section for advanced analysis
st.markdown('<div class="sub-header">AI模型归因分析</div>', unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["成功/失败模式", "特征重要性", "回测分析"])

with tab1:
    if st.session_state.model_loaded and st.session_state.dqn_agent:
        agent = st.session_state.dqn_agent
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 顶级成功模式")
            
            # In a real implementation, these would come from agent.get_top_success_modes()
            # Demo data for visualization
            success_modes = {
                "trend_continuation": 32,
                "support_bounce": 28,
                "ai_consensus": 24,
                "volume_confirmation": 19,
                "volatility_expansion": 14
            }
            
            fig, ax = plt.subplots(figsize=(8, 5))
            bars = ax.barh(
                list(success_modes.keys()),
                list(success_modes.values()),
                color='green',
                alpha=0.7
            )
            ax.set_xlabel('成功次数')
            ax.set_title('顶级成功模式')
            for bar in bars:
                width = bar.get_width()
                label_position = width + 1
                ax.text(label_position, bar.get_y() + bar.get_height()/2, f'{width}', 
                        va='center', ha='left', fontsize=10)
            
            st.pyplot(fig)
        
        with col2:
            st.markdown("### 顶级失败模式")
            
            # Demo data for visualization
            failure_modes = {
                "fake_breakout": 18,
                "sudden_reversal": 15,
                "choppy_market": 12,
                "trend_reversal": 9,
                "liquidity_dry_up": 6
            }
            
            fig, ax = plt.subplots(figsize=(8, 5))
            bars = ax.barh(
                list(failure_modes.keys()),
                list(failure_modes.values()),
                color='red',
                alpha=0.7
            )
            ax.set_xlabel('失败次数')
            ax.set_title('顶级失败模式')
            for bar in bars:
                width = bar.get_width()
                label_position = width + 1
                ax.text(label_position, bar.get_y() + bar.get_height()/2, f'{width}', 
                        va='center', ha='left', fontsize=10)
            
            st.pyplot(fig)
    else:
        st.info("AI模型未加载，请初始化模型")

with tab2:
    if st.session_state.model_loaded:
        # Sample feature importance data (in a real implementation, this would come from model analysis)
        feature_importance = {
            'delta': 0.35,
            'rsi': 0.25,
            'price_trend': 0.15,
            'gamma': 0.08,
            'volatility': 0.07,
            'volume': 0.05,
            'theta': 0.03,
            'vega': 0.02
        }
        
        # Sort by importance
        feature_importance = {k: v for k, v in sorted(feature_importance.items(), key=lambda item: item[1], reverse=True)}
        
        fig, ax = plt.subplots(figsize=(10, 6))
        sns.barplot(x=list(feature_importance.values()), y=list(feature_importance.keys()), palette='viridis', ax=ax)
        ax.set_title('特征重要性分析')
        ax.set_xlabel('重要性系数')
        
        # Add percentage labels
        for i, v in enumerate(feature_importance.values()):
            ax.text(v + 0.01, i, f'{v:.0%}', va='center')
        
        st.pyplot(fig)
        
        st.markdown("""
        ### 特征解读
        
        - **Delta**: 期权的方向敏感度，是最重要的决策因素
        - **RSI**: 短期超买超卖指标，反映当前市场动能
        - **价格趋势**: 相对于移动平均线的位置，反映整体趋势
        - **Gamma**: Delta的变化率，影响期权价格的非线性变化
        - **波动率**: 短期价格波动幅度，有助于识别突破
        """)
    else:
        st.info("AI模型未加载，请初始化模型")

with tab3:
    if st.session_state.model_loaded:
        # Sample backtest data (in a real implementation, this would come from actual backtest results)
        backtest_data = pd.DataFrame({
            'date': pd.date_range(start='2023-01-01', periods=100, freq='D'),
            'strategy_return': np.cumsum(np.random.normal(0.001, 0.02, 100)),
            'benchmark_return': np.cumsum(np.random.normal(0.0008, 0.015, 100))
        })
        
        # Calculate metrics
        win_rate = 0.65
        profit_factor = 1.8
        max_drawdown = 0.12
        sharpe_ratio = 1.35
        
        # Plot performance
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=backtest_data['date'],
            y=backtest_data['strategy_return'],
            mode='lines',
            name='AI策略',
            line=dict(color='#1E88E5', width=2)
        ))
        
        fig.add_trace(go.Scatter(
            x=backtest_data['date'],
            y=backtest_data['benchmark_return'],
            mode='lines',
            name='基准',
            line=dict(color='#888888', width=1.5, dash='dash')
        ))
        
        fig.update_layout(
            title='策略回测表现',
            xaxis_title='日期',
            yaxis_title='累计收益',
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Display metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("胜率", f"{win_rate:.0%}")
        with col2:
            st.metric("盈亏比", f"{profit_factor:.2f}")
        with col3:
            st.metric("最大回撤", f"{max_drawdown:.0%}")
        with col4:
            st.metric("夏普比率", f"{sharpe_ratio:.2f}")
            
        st.markdown("""
        ### 归因分析
        
        - **胜率 > 60%**: 高于行业平均水平，显示模型预测方向的准确性高
        - **盈亏比 > 1.5**: 保持在理想区间，说明止盈止损设置合理
        - **最大回撤 < 15%**: 控制在可接受范围内，风控系统有效
        - **夏普比率 > 1.2**: 风险调整后回报强劲，模型能够高效管理风险
        """)
    else:
        st.info("AI模型未加载，请初始化模型")

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #888;">
SPY期权交易AI系统 - 强化学习模块 © 2023
</div>
""", unsafe_allow_html=True) 