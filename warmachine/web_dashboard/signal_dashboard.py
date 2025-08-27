import os
import time
import threading
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import yaml
from typing import Dict, List, Optional
from dotenv import load_dotenv

# Load environment variables from .env
if os.path.exists('.env'):
    load_dotenv()
else:
    st.error(".env file not found. Please create it with your API keys.")
    st.stop()

# Validate required environment variables
required_env_vars = [
    'DATABENTO_API_KEY',
    'DEEPSEEK_API_KEY',
    'POLYGON_API_KEY'
]

missing_vars = [var for var in required_env_vars if not os.getenv(var)]
if missing_vars:
    st.error(f"Missing required environment variables: {', '.join(missing_vars)}")
    st.stop()

# Then import other modules
from scheduler.signal_scheduler import SignalScheduler, SignalConfig
from analysis.market_context_builder import MarketContextBuilder
from analysis.technical_analysis import TechnicalAnalyzer
from analysis.signal_fusion_engine import SignalFusionEngine

# Constants
DEFAULT_SYMBOLS = ["AAPL", "TSLA", "NVDA", "MSFT", "GOOGL"]
INTERVAL_OPTIONS = [1, 3, 5, 15]
CONFIG_FILE = "config/signal_config.yaml"

class SignalDashboard:
    def __init__(self):
        self.scheduler = None
        self.scheduler_thread = None
        self.running = False
        self.signals = []
        
        # Initialize components
        try:
            self.config = self.load_config()
            self.market_context_builder = MarketContextBuilder()
            self.technical_analyzer = TechnicalAnalyzer(pd.DataFrame())  # Will be updated with data
            self.signal_fusion = SignalFusionEngine()
            
            # Load trading configuration from environment
            self.trading_enabled = os.getenv('TRADING_ENABLED', 'false').lower() == 'true'
            self.max_positions = int(os.getenv('MAX_POSITIONS', '5'))
            self.position_size = float(os.getenv('POSITION_SIZE', '0.1'))
            
        except Exception as e:
            st.error(f"Error initializing dashboard: {str(e)}")
            st.stop()
        
    def load_config(self):
        """Load configuration from YAML file"""
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r') as f:
                    return yaml.safe_load(f)
            else:
                return {
                    'symbols': DEFAULT_SYMBOLS,
                    'interval': '1h',
                    'signal_strength': 0.7,
                    'trading': {
                        'enabled': False,
                        'position_size': 0.1,
                        'max_positions': 5
                    }
                }
        except Exception as e:
            st.error(f"Error loading config: {str(e)}")
            return {
                'symbols': DEFAULT_SYMBOLS,
                'interval': '1h',
                'signal_strength': 0.7,
                'trading': {
                    'enabled': False,
                    'position_size': 0.1,
                    'max_positions': 5
                }
            }
            
    def save_config(self):
        """Save configuration to YAML file"""
        try:
            os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
            with open(CONFIG_FILE, 'w') as f:
                yaml.dump(self.config, f)
        except Exception as e:
            st.error(f"Error saving config: {str(e)}")
            
    def start_scheduler(self):
        """Start the signal scheduler in a background thread"""
        if not self.running:
            self.running = True
            self.scheduler = SignalScheduler(
                symbols=self.config['symbols'],
                interval=self.config['interval'],
                signal_strength=self.config['signal_strength']
            )
            self.scheduler_thread = threading.Thread(target=self._run_scheduler)
            self.scheduler_thread.start()
    
    def stop_scheduler(self):
        """Stop the signal scheduler"""
        self.running = False
        if self.scheduler_thread:
            self.scheduler_thread.join()
    
    def _run_scheduler(self):
        """Run the scheduler loop"""
        while self.running:
            try:
                # Generate mock signals for demo
                for symbol in self.config['symbols']:
                    market_context = self.market_context_builder.build_context(symbol)
                    technical_signals = self.technical_analyzer.analyze(market_context)
                    fusion_result = self.signal_fusion.fuse_signals(
                        technical_signals=technical_signals,
                        market_context=market_context
                    )
                    
                    if fusion_result.action != "HOLD":
                        self.signals.append({
                            'timestamp': datetime.now(),
                            'symbol': symbol,
                            'action': fusion_result.action,
                            'confidence': fusion_result.confidence,
                            'reasoning': fusion_result.reasoning
                        })
                
                time.sleep(60)  # Check every minute
            except Exception as e:
                st.error(f"Error in scheduler: {str(e)}")
                time.sleep(5)
    
    def render_dashboard(self):
        """Render the Streamlit dashboard"""
        st.title("Trading Signal Dashboard")
        
        # Configuration Section
        st.header("Configuration")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            symbols = st.text_input(
                "Trading Symbols",
                value=",".join(self.config['symbols']),
                help="Comma-separated list of symbols"
            )
            self.config['symbols'] = [s.strip() for s in symbols.split(",")]
        
        with col2:
            self.config['interval'] = st.selectbox(
                "Signal Interval",
                options=['1m', '5m', '15m', '1h', '4h', '1d'],
                index=['1m', '5m', '15m', '1h', '4h', '1d'].index(self.config['interval'])
            )
        
        with col3:
            self.config['signal_strength'] = st.slider(
                "Signal Strength Threshold",
                min_value=0.0,
                max_value=1.0,
                value=self.config['signal_strength'],
                step=0.1
            )
            
        # Trading Configuration Section
        st.header("Trading Configuration")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.info(f"Trading Enabled: {'Yes' if self.trading_enabled else 'No'}")
        
        with col2:
            st.info(f"Max Positions: {self.max_positions}")
        
        with col3:
            st.info(f"Position Size: {self.position_size:.1%}")
        
        # Control Panel
        st.header("Control Panel")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("Start Scheduler"):
                self.start_scheduler()
                st.success("Scheduler started")
        
        with col2:
            if st.button("Stop Scheduler"):
                self.stop_scheduler()
                st.warning("Scheduler stopped")
        
        with col3:
            st.info(f"Status: {'Running' if self.running else 'Stopped'}")
        
        # Signal Display
        st.header("Recent Signals")
        if self.signals:
            signals_df = pd.DataFrame(self.signals)
            signals_df['timestamp'] = pd.to_datetime(signals_df['timestamp'])
            signals_df = signals_df.sort_values('timestamp', ascending=False)
            
            # Display signals table
            st.dataframe(signals_df)
            
            # Plot signals
            fig = go.Figure()
            for symbol in self.config['symbols']:
                symbol_signals = signals_df[signals_df['symbol'] == symbol]
                if not symbol_signals.empty:
                    fig.add_trace(go.Scatter(
                        x=symbol_signals['timestamp'],
                        y=symbol_signals['confidence'],
                        mode='lines+markers',
                        name=symbol,
                        text=symbol_signals['reasoning']
                    ))
            
            fig.update_layout(
                title="Signal Confidence Over Time",
                xaxis_title="Time",
                yaxis_title="Confidence",
                hovermode='x unified'
            )
            st.plotly_chart(fig)
        else:
            st.info("No signals generated yet")
        
        # Save configuration
        if st.button("Save Configuration"):
            self.save_config()
            st.success("Configuration saved")

if __name__ == "__main__":
    dashboard = SignalDashboard()
    dashboard.render_dashboard() 