import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import os
import json
from pathlib import Path
import logging
import sys

# Add project root to path
sys.path.append('.')

# Import custom modules
from utils.virtual_trader import virtual_trader
from utils.trading_integration import trading_integration
from utils.telegram_notifier import TelegramNotifier

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("streamlit_dashboard")

# Page config
st.set_page_config(
    page_title="RL Options Trader Dashboard",
    page_icon="ðŸ“ˆ",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2rem;
        font-weight: bold;
        color: #1E88E5;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.5rem;
        font-weight: bold;
        color: #424242;
        margin-top: 1rem;
        margin-bottom: 0.5rem;
    }
    .info-card {
        background-color: #f8f9fa;
        border-radius: 0.5rem;
        padding: 1rem;
        margin-bottom: 1rem;
    }
    .success-text {
        color: #4CAF50;
        font-weight: bold;
    }
    .danger-text {
        color: #F44336;
        font-weight: bold;
    }
    .warning-text {
        color: #FFC107;
        font-weight: bold;
    }
    .footer {
        text-align: center;
        margin-top: 3rem;
        color: #9e9e9e;
        font-size: 0.8rem;
    }
</style>
""", unsafe_allow_html=True)

# Helper functions
@st.cache_data(ttl=300)  # Cache for 5 minutes
def fetch_market_data(symbol):
    """Fetch market data for a symbol"""
    return trading_integration.get_market_data(symbol)

@st.cache_data(ttl=300)  # Cache for 5 minutes
def fetch_option_data(symbol):
    """Fetch option data for a symbol"""
    return trading_integration.get_option_data(symbol)

def format_currency(value):
    """Format a value as currency"""
    return f"${value:,.2f}"

def color_pnl(val):
    """Color positive/negative for pandas styler"""
    color = 'green' if val > 0 else 'red' if val < 0 else 'black'
    return f'color: {color}'

def plot_portfolio_history():
    """Plot portfolio value over time"""
    history = virtual_trader.portfolio.history
    
    if not history:
        st.info("No portfolio history data available yet.")
        return
    
    # Extract timestamps and values
    data = []
    for entry in history:
        try:
            data.append({
                'timestamp': datetime.fromisoformat(entry['timestamp']),
                'total_value': entry['total_value'],
                'cash': entry['cash'],
                'positions_value': entry['positions_value']
            })
        except (KeyError, ValueError) as e:
            continue
    
    if not data:
        st.info("Portfolio history data is not in the expected format.")
        return
    
    # Convert to DataFrame
    df = pd.DataFrame(data)
    
    # Create plot
    fig = go.Figure()
    
    # Add total value line
    fig.add_trace(go.Scatter(
        x=df['timestamp'], 
        y=df['total_value'],
        mode='lines',
        name='Total Value',
        line=dict(color='#1E88E5', width=2)
    ))
    
    # Add cash line
    fig.add_trace(go.Scatter(
        x=df['timestamp'], 
        y=df['cash'],
        mode='lines',
        name='Cash',
        line=dict(color='#7CB342', width=1.5, dash='dash')
    ))
    
    # Add positions value line
    fig.add_trace(go.Scatter(
        x=df['timestamp'], 
        y=df['positions_value'],
        mode='lines',
        name='Positions Value',
        line=dict(color='#F44336', width=1.5, dash='dash')
    ))
    
    # Update layout
    fig.update_layout(
        title='Portfolio Value Over Time',
        xaxis_title='Date',
        yaxis_title='Value ($)',
        height=400,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    st.plotly_chart(fig, use_container_width=True)

def plot_trades_history():
    """Plot trades history"""
    trades = virtual_trader.get_completed_trades()
    
    if not trades:
        st.info("No completed trades available yet.")
        return
    
    # Convert trades to DataFrame
    data = []
    for trade in trades:
        if trade.exit_time and trade.pnl is not None:
            data.append({
                'symbol': trade.symbol,
                'entry_time': trade.entry_time,
                'exit_time': trade.exit_time,
                'entry_price': trade.entry_price,
                'exit_price': trade.exit_price,
                'pnl': trade.pnl,
                'pnl_pct': trade.pnl_pct,
                'action': trade.action
            })
    
    if not data:
        st.info("No completed trades with P&L data available yet.")
        return
    
    df = pd.DataFrame(data)
    
    # Create plot
    fig = go.Figure()
    
    # Add bars for P&L
    colors = ['#4CAF50' if pnl >= 0 else '#F44336' for pnl in df['pnl']]
    
    fig.add_trace(go.Bar(
        x=df['exit_time'],
        y=df['pnl'],
        name='P&L',
        marker_color=colors
    ))
    
    # Add line for cumulative P&L
    fig.add_trace(go.Scatter(
        x=df['exit_time'],
        y=df['pnl'].cumsum(),
        mode='lines',
        name='Cumulative P&L',
        line=dict(color='#1E88E5', width=2)
    ))
    
    # Update layout
    fig.update_layout(
        title='Trade P&L History',
        xaxis_title='Exit Time',
        yaxis_title='P&L ($)',
        height=400,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    st.plotly_chart(fig, use_container_width=True)

def display_positions():
    """Display current positions"""
    positions = virtual_trader.portfolio.get_all_positions()
    
    if not positions:
        st.info("No active positions.")
        return
    
    # Convert to DataFrame
    data = []
    for symbol, pos in positions.items():
        current = pos["current_price"]
        avg_price = pos["avg_price"]
        pnl = (current - avg_price) * pos["quantity"]
        pnl_pct = (current / avg_price - 1) * 100
        
        data.append({
            'Symbol': symbol,
            'Quantity': pos["quantity"],
            'Avg Price': avg_price,
            'Current Price': current,
            'P&L': pnl,
            'P&L %': pnl_pct
        })
    
    df = pd.DataFrame(data)
    
    # Format DataFrame
    formatted_df = df.copy()
    formatted_df['Avg Price'] = formatted_df['Avg Price'].apply(lambda x: f"${x:.2f}")
    formatted_df['Current Price'] = formatted_df['Current Price'].apply(lambda x: f"${x:.2f}")
    formatted_df['P&L'] = formatted_df['P&L'].apply(lambda x: f"${x:.2f}")
    formatted_df['P&L %'] = formatted_df['P&L %'].apply(lambda x: f"{x:.2f}%")
    
    # Display DataFrame
    st.dataframe(formatted_df, use_container_width=True)

def display_recent_trades():
    """Display recent trades"""
    trades = virtual_trader.get_completed_trades()
    
    if not trades:
        st.info("No completed trades.")
        return
    
    # Convert to DataFrame
    data = []
    for trade in trades[-10:]:  # Get last 10 trades
        data.append({
            'Symbol': trade.symbol,
            'Action': trade.action,
            'Quantity': trade.quantity,
            'Entry Price': trade.entry_price,
            'Exit Price': trade.exit_price if trade.exit_price else 0,
            'Entry Time': trade.entry_time,
            'Exit Time': trade.exit_time if trade.exit_time else None,
            'P&L': trade.pnl if trade.pnl else 0,
            'P&L %': trade.pnl_pct if trade.pnl_pct else 0
        })
    
    df = pd.DataFrame(data)
    
    # Format DataFrame
    formatted_df = df.copy()
    formatted_df['Entry Price'] = formatted_df['Entry Price'].apply(lambda x: f"${x:.2f}")
    formatted_df['Exit Price'] = formatted_df['Exit Price'].apply(lambda x: f"${x:.2f}")
    formatted_df['P&L'] = formatted_df['P&L'].apply(lambda x: f"${x:.2f}")
    formatted_df['P&L %'] = formatted_df['P&L %'].apply(lambda x: f"{x:.2f}%")
    
    # Display DataFrame
    st.dataframe(formatted_df, use_container_width=True)

def display_performance_metrics():
    """Display performance metrics"""
    metrics = virtual_trader.get_performance_metrics()
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Trades", metrics["total_trades"])
    
    with col2:
        win_rate = metrics["win_rate"] * 100 if "win_rate" in metrics else 0
        st.metric("Win Rate", f"{win_rate:.1f}%")
    
    with col3:
        profit_factor = metrics["profit_factor"] if "profit_factor" in metrics else 0
        st.metric("Profit Factor", f"{profit_factor:.2f}")
    
    with col4:
        total_pnl = metrics["total_pnl"] if "total_pnl" in metrics else 0
        st.metric("Total P&L", f"${total_pnl:.2f}")

def display_predictions(symbol):
    """Display predictions for a symbol"""
    # Get prediction
    with st.spinner(f"Getting prediction for {symbol}..."):
        prediction = trading_integration.get_prediction(symbol)
    
    if prediction['action'] == 'ERROR':
        st.error(f"Error getting prediction: {prediction.get('error', 'Unknown error')}")
        return
    
    # Display prediction
    action = prediction['action']
    confidence = prediction['confidence']
    price = prediction['current_price']
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        action_color = (
            "success-text" if action == "BUY" else 
            "danger-text" if action == "SELL" else 
            "warning-text"
        )
        st.markdown(f"<div class='info-card'><h3>Action</h3><p class='{action_color}'>{action}</p></div>", unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"<div class='info-card'><h3>Confidence</h3><p>{confidence:.1%}</p></div>", unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"<div class='info-card'><h3>Current Price</h3><p>${price:.2f}</p></div>", unsafe_allow_html=True)
    
    # Option data
    option_data = prediction.get('option_data', {})
    if option_data:
        st.markdown("<div class='sub-header'>Option Data</div>", unsafe_allow_html=True)
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown(f"<div class='info-card'><h3>Strike</h3><p>${option_data['strike']:.2f}</p></div>", unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"<div class='info-card'><h3>Expiry</h3><p>{option_data['expiry']}</p></div>", unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"<div class='info-card'><h3>Option Price</h3><p>${option_data['price']:.2f}</p></div>", unsafe_allow_html=True)
        
        with col4:
            st.markdown(f"<div class='info-card'><h3>Type</h3><p>{option_data['option_type'].upper()}</p></div>", unsafe_allow_html=True)
        
        # Greeks
        st.markdown("<div class='sub-header'>Option Greeks</div>", unsafe_allow_html=True)
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown(f"<div class='info-card'><h3>Delta</h3><p>{option_data['delta']:.4f}</p></div>", unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"<div class='info-card'><h3>Gamma</h3><p>{option_data['gamma']:.4f}</p></div>", unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"<div class='info-card'><h3>Theta</h3><p>{option_data['theta']:.4f}</p></div>", unsafe_allow_html=True)
        
        with col4:
            st.markdown(f"<div class='info-card'><h3>Vega</h3><p>{option_data['vega']:.4f}</p></div>", unsafe_allow_html=True)
    
    # Position recommendation
    if action != "NO_ACTION":
        st.markdown("<div class='sub-header'>Position Recommendation</div>", unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            position_size = prediction.get('position_size', 0)
            st.markdown(f"<div class='info-card'><h3>Quantity</h3><p>{position_size:.2f}</p></div>", unsafe_allow_html=True)
        
        with col2:
            position_value = prediction.get('position_value', 0)
            st.markdown(f"<div class='info-card'><h3>Position Value</h3><p>${position_value:.2f}</p></div>", unsafe_allow_html=True)
        
        # Trade execution buttons
        st.markdown("<div class='sub-header'>Execute Trade</div>", unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("Buy", use_container_width=True, type="primary"):
                with st.spinner("Executing buy order..."):
                    result = trading_integration.execute_virtual_trade(prediction)
                    if result["success"]:
                        st.success(result["message"])
                    else:
                        st.error(result["message"])
        
        with col2:
            if st.button("Sell", use_container_width=True, key="sell_button"):
                # Create a sell prediction from the buy prediction
                sell_prediction = prediction.copy()
                sell_prediction["action"] = "SELL"
                
                with st.spinner("Executing sell order..."):
                    result = trading_integration.execute_virtual_trade(sell_prediction)
                    if result["success"]:
                        st.success(result["message"])
                    else:
                        st.error(result["message"])

def display_market_data(symbol):
    """Display market data for a symbol"""
    try:
        # Get market data
        market_data = trading_integration.get_market_data(symbol)
        
        # Create candlestick chart
        fig = go.Figure(data=[go.Candlestick(
            x=market_data['date'],
            open=market_data['open'],
            high=market_data['high'],
            low=market_data['low'],
            close=market_data['close'],
            name='Price'
        )])
        
        # Add SMA20
        if 'sma20' in market_data.columns:
            fig.add_trace(go.Scatter(
                x=market_data['date'],
                y=market_data['sma20'],
                mode='lines',
                name='SMA20',
                line=dict(color='orange', width=1)
            ))
        
        # Add RSI if available
        if 'rsi' in market_data.columns:
            fig2 = go.Figure(data=[go.Scatter(
                x=market_data['date'],
                y=market_data['rsi'],
                mode='lines',
                name='RSI',
                line=dict(color='purple', width=1)
            )])
            
            # Add RSI reference lines
            fig2.add_trace(go.Scatter(
                x=market_data['date'],
                y=[70] * len(market_data),
                mode='lines',
                name='Overbought',
                line=dict(color='red', width=1, dash='dash')
            ))
            
            fig2.add_trace(go.Scatter(
                x=market_data['date'],
                y=[30] * len(market_data),
                mode='lines',
                name='Oversold',
                line=dict(color='green', width=1, dash='dash')
            ))
            
            fig2.update_layout(
                title='RSI Indicator',
                height=300,
                yaxis=dict(range=[0, 100])
            )
            
            # Display RSI chart
            st.plotly_chart(fig2, use_container_width=True)
        
        # Update candlestick layout
        fig.update_layout(
            title=f'Price Chart for {symbol}',
            xaxis_title='Date',
            yaxis_title='Price',
            height=500
        )
        
        # Display price chart
        st.plotly_chart(fig, use_container_width=True)
        
    except Exception as e:
        st.error(f"Error loading market data: {str(e)}")

def main():
    """Main Streamlit app"""
    st.markdown("<div class='main-header'>RL Options Trader Dashboard</div>", unsafe_allow_html=True)
    
    # Sidebar
    st.sidebar.title("Navigation")
    page = st.sidebar.radio("Select Page", ["Overview", "Portfolio", "Trades", "Predictions", "Market Data"])
    
    # Symbol selection
    symbols = ["SPY", "AAPL", "GOOGL", "TSLA", "MSFT", "AMZN", "NVDA", "META"]
    selected_symbol = st.sidebar.selectbox("Select Symbol", symbols)
    
    # Update prices button
    if st.sidebar.button("Update Prices"):
        with st.sidebar.spinner("Updating prices..."):
            trading_integration.auto_update_prices()
            st.sidebar.success("Prices updated successfully!")
    
    # Run predictions button
    if st.sidebar.button("Run Predictions"):
        with st.sidebar.spinner("Running predictions..."):
            results = trading_integration.run_predictions([selected_symbol])
            if results and selected_symbol in results:
                st.sidebar.success(f"Prediction: {results[selected_symbol]['action']}")
            else:
                st.sidebar.error("Failed to get prediction")
    
    # Auto-trade button
    auto_trade_expanded = st.sidebar.expander("Auto Trade Settings")
    with auto_trade_expanded:
        auto_trade_symbols = st.multiselect("Symbols to Trade", symbols, default=[selected_symbol])
        min_confidence = st.slider("Minimum Confidence", 0.0, 1.0, 0.7, 0.05)
        
        if st.button("Execute Auto Trade"):
            with st.spinner("Executing auto trades..."):
                results = trading_integration.auto_trade(auto_trade_symbols, min_confidence)
                for symbol, result in results.items():
                    if result.get("success", False):
                        st.success(f"{symbol}: {result['message']}")
                    else:
                        st.warning(f"{symbol}: {result.get('message', 'Failed')}")
    
    # Display portfolio summary in sidebar
    st.sidebar.markdown("---")
    st.sidebar.markdown("### Portfolio Summary")
    
    summary = virtual_trader.get_portfolio_summary()
    
    st.sidebar.metric("Total Value", f"${summary['total_value']:.2f}")
    st.sidebar.metric("Cash", f"${summary['cash']:.2f}")
    st.sidebar.metric("Return", f"{summary['total_return']:.2f}%")
    
    # Display page content
    if page == "Overview":
        # Portfolio value
        st.markdown("<div class='sub-header'>Portfolio Value</div>", unsafe_allow_html=True)
        plot_portfolio_history()
        
        # Performance metrics
        st.markdown("<div class='sub-header'>Performance Metrics</div>", unsafe_allow_html=True)
        display_performance_metrics()
        
        # Active positions
        st.markdown("<div class='sub-header'>Active Positions</div>", unsafe_allow_html=True)
        display_positions()
        
        # Recent trades
        st.markdown("<div class='sub-header'>Recent Trades</div>", unsafe_allow_html=True)
        display_recent_trades()
    
    elif page == "Portfolio":
        st.markdown("<div class='sub-header'>Portfolio Value</div>", unsafe_allow_html=True)
        plot_portfolio_history()
        
        st.markdown("<div class='sub-header'>Active Positions</div>", unsafe_allow_html=True)
        display_positions()
        
        st.markdown("<div class='sub-header'>Asset Allocation</div>", unsafe_allow_html=True)
        
        # Create asset allocation pie chart
        positions = virtual_trader.portfolio.get_all_positions()
        if positions:
            position_values = {symbol: pos["quantity"] * pos["current_price"] for symbol, pos in positions.items()}
            position_values["Cash"] = summary["cash"]
            
            fig = px.pie(
                values=list(position_values.values()),
                names=list(position_values.keys()),
                title="Portfolio Allocation"
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No positions to display")
    
    elif page == "Trades":
        st.markdown("<div class='sub-header'>Trade P&L History</div>", unsafe_allow_html=True)
        plot_trades_history()
        
        st.markdown("<div class='sub-header'>Completed Trades</div>", unsafe_allow_html=True)
        display_recent_trades()
        
        st.markdown("<div class='sub-header'>Trade Statistics</div>", unsafe_allow_html=True)
        
        metrics = virtual_trader.get_performance_metrics()
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("<div class='info-card'>", unsafe_allow_html=True)
            st.markdown("#### Trade Counts")
            st.markdown(f"Total Trades: **{metrics['total_trades']}**")
            st.markdown(f"Winning Trades: **{metrics['winning_trades']}**")
            st.markdown(f"Losing Trades: **{metrics['losing_trades']}**")
            st.markdown("</div>", unsafe_allow_html=True)
        
        with col2:
            st.markdown("<div class='info-card'>", unsafe_allow_html=True)
            st.markdown("#### Trade Metrics")
            st.markdown(f"Win Rate: **{metrics['win_rate']*100:.1f}%**")
            st.markdown(f"Profit Factor: **{metrics['profit_factor']:.2f}**")
            st.markdown(f"Average Profit: **${metrics['avg_profit']:.2f}**")
            st.markdown(f"Average Loss: **${metrics['avg_loss']:.2f}**")
            st.markdown("</div>", unsafe_allow_html=True)
    
    elif page == "Predictions":
        st.markdown(f"<div class='sub-header'>RL Model Prediction for {selected_symbol}</div>", unsafe_allow_html=True)
        display_predictions(selected_symbol)
    
    elif page == "Market Data":
        st.markdown(f"<div class='sub-header'>Market Data for {selected_symbol}</div>", unsafe_allow_html=True)
        display_market_data(selected_symbol)
        
        # Option data
        st.markdown(f"<div class='sub-header'>Option Data for {selected_symbol}</div>", unsafe_allow_html=True)
        
        try:
            option_data = trading_integration.get_option_data(selected_symbol)
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.markdown(f"<div class='info-card'><h3>Option Symbol</h3><p>{option_data['symbol']}</p></div>", unsafe_allow_html=True)
            
            with col2:
                st.markdown(f"<div class='info-card'><h3>Strike</h3><p>${option_data['strike']:.2f}</p></div>", unsafe_allow_html=True)
            
            with col3:
                st.markdown(f"<div class='info-card'><h3>Expiry</h3><p>{option_data['expiry']}</p></div>", unsafe_allow_html=True)
            
            with col4:
                st.markdown(f"<div class='info-card'><h3>Price</h3><p>${option_data['price']:.2f}</p></div>", unsafe_allow_html=True)
            
            # Greeks
            st.markdown("<div class='sub-header'>Option Greeks</div>", unsafe_allow_html=True)
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.markdown(f"<div class='info-card'><h3>Delta</h3><p>{option_data['delta']:.4f}</p></div>", unsafe_allow_html=True)
            
            with col2:
                st.markdown(f"<div class='info-card'><h3>Gamma</h3><p>{option_data['gamma']:.4f}</p></div>", unsafe_allow_html=True)
            
            with col3:
                st.markdown(f"<div class='info-card'><h3>Theta</h3><p>{option_data['theta']:.4f}</p></div>", unsafe_allow_html=True)
            
            with col4:
                st.markdown(f"<div class='info-card'><h3>Vega</h3><p>{option_data['vega']:.4f}</p></div>", unsafe_allow_html=True)
        
        except Exception as e:
            st.error(f"Error loading option data: {str(e)}")
    
    # Footer
    st.markdown("<div class='footer'>RL Options Trader Dashboard - Powered by Streamlit</div>", unsafe_allow_html=True)

if __name__ == "__main__":
    main() 