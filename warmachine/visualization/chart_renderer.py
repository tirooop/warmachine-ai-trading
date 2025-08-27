"""
Standalone Chart Renderer - Generates technical analysis charts with indicators.
Doesn't depend on other project modules to avoid import issues.
"""

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import pandas as pd
import yfinance as yf
import os
from datetime import datetime, timedelta

class StandaloneChartRenderer:
    """
    Standalone chart generator that includes data fetching and indicator calculation
    """
    
    def __init__(self, output_dir='./temp_charts'):
        self.output_dir = output_dir
        
        # Create output directory if it doesn't exist
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
    
    def render(self, symbol, days=30, include_volume=True):
        """
        Generate a technical analysis chart for the given symbol
        
        Args:
            symbol: Stock ticker symbol
            days: Number of trading days to include
            include_volume: Whether to include volume bars
            
        Returns:
            Path to the generated chart image
        """
        # Fetch market data
        df = self._fetch_data(symbol, days)
        
        # Calculate technical indicators
        df = self._add_indicators(df)
        
        # Create figure with subplots
        if include_volume:
            fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 10), 
                                                gridspec_kw={'height_ratios': [3, 1, 1]})
        else:
            fig, (ax1, ax3) = plt.subplots(2, 1, figsize=(12, 8), 
                                          gridspec_kw={'height_ratios': [3, 1]})
        
        # Format date axis
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
        ax1.xaxis.set_major_locator(mdates.WeekdayLocator(interval=1))
        
        # Plot price data
        ax1.plot(df.index, df['close'], label='Close Price', color='black', linewidth=1)
        
        # Plot EMA lines
        ax1.plot(df.index, df['ema20'], label='EMA 20', color='blue', linewidth=1)
        ax1.plot(df.index, df['ema50'], label='EMA 50', color='red', linewidth=1)
        
        # Plot Bollinger Bands
        ax1.plot(df.index, df['upper_band'], 'k--', label='Upper BB', alpha=0.5)
        ax1.plot(df.index, df['lower_band'], 'k--', label='Lower BB', alpha=0.5)
        ax1.fill_between(df.index, df['upper_band'], df['lower_band'], color='gray', alpha=0.1)
        
        # Set title and labels
        current_price = df['close'].iloc[-1]
        change_pct = (df['close'].iloc[-1] / df['close'].iloc[-2] - 1) * 100
        title = f"{symbol}: ${current_price:.2f} ({'+' if change_pct >= 0 else ''}{change_pct:.2f}%)"
        ax1.set_title(title, fontsize=14)
        ax1.set_ylabel('Price ($)', fontsize=12)
        ax1.grid(True, alpha=0.3)
        ax1.legend(loc='upper left')
        
        # Volume subplot
        if include_volume:
            # Plot volume bars
            pos_idx = df['close'] >= df['open']
            neg_idx = df['close'] < df['open']
            
            ax2.bar(df.index[pos_idx], df['volume'][pos_idx], color='green', alpha=0.5, width=0.8)
            ax2.bar(df.index[neg_idx], df['volume'][neg_idx], color='red', alpha=0.5, width=0.8)
            
            # Format volume axis
            ax2.set_ylabel('Volume', fontsize=12)
            ax2.grid(True, alpha=0.3)
            ax2.set_xticklabels([])  # Hide x-axis labels
        
        # MACD subplot
        ax3.plot(df.index, df['macd'], label='MACD', color='blue', linewidth=1)
        ax3.plot(df.index, df['macd_signal'], label='Signal', color='red', linewidth=1)
        ax3.bar(df.index, df['macd_hist'], color=['green' if x >= 0 else 'red' for x in df['macd_hist']], 
                width=0.8, alpha=0.5)
        
        # Fisher Transform as dashed line on the same subplot
        fisher_line = ax3.plot(df.index, df['fisher'], label='Fisher', color='purple', 
                              linestyle='--', linewidth=1)
        
        # Format MACD axis
        ax3.set_ylabel('MACD / Fisher', fontsize=12)
        ax3.grid(True, alpha=0.3)
        ax3.axhline(y=0, color='black', linestyle='-', alpha=0.3)
        ax3.legend(loc='upper left')
        
        # Adjust layout and save
        plt.tight_layout()
        
        # Save to file
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        save_path = os.path.join(self.output_dir, f"{symbol}_{timestamp}.png")
        plt.savefig(save_path, dpi=150)
        plt.close(fig)
        
        return save_path
    
    def _fetch_data(self, symbol, days=30, interval="1d"):
        """Fetch market data for a symbol"""
        # Calculate start and end dates
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days * 1.5)  # Add buffer for weekends/holidays
        
        try:
            # Fetch data from yfinance
            df = yf.download(
                symbol, 
                start=start_date.strftime('%Y-%m-%d'),
                end=end_date.strftime('%Y-%m-%d'),
                interval=interval,
                progress=False,
                show_errors=False
            )
            
            # Ensure we have the expected columns
            required_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
            for col in required_columns:
                if col not in df.columns:
                    raise ValueError(f"Missing required column: {col}")
            
            # Standardize column names to lowercase
            df.columns = [col.lower() for col in df.columns]
            
            # Filter to get the requested number of days
            if len(df) > days:
                df = df.iloc[-days:]
                
            return df
            
        except Exception as e:
            # If yfinance fails, try to create a mock dataset for demo purposes
            if symbol.upper() in ['AAPL', 'MSFT', 'TSLA', 'NVDA', 'AMZN', 'GOOGL']:
                return self._generate_mock_data(symbol, days)
            else:
                raise ValueError(f"Failed to fetch data for {symbol}: {str(e)}")
    
    def _generate_mock_data(self, symbol, days):
        """Generate mock data for demo purposes"""
        # Create date range
        end_date = datetime.now()
        dates = [end_date - timedelta(days=i) for i in range(days)]
        dates.reverse()
        
        # Generate random price data with a trend
        seed_value = sum([ord(c) for c in symbol.upper()]) % 100  # Use symbol for seed
        np.random.seed(seed_value)
        
        base_price = 100 + (seed_value % 400)  # Different base price per symbol
        trend = np.random.choice([-1, 1]) * np.random.uniform(0.1, 0.3)  # Random trend
        
        # Generate price data
        noise = np.random.normal(0, 1, days) * base_price * 0.01
        trend_component = np.arange(days) * trend
        close_prices = base_price + trend_component + noise.cumsum()
        
        # Ensure no negative prices
        close_prices = np.maximum(close_prices, base_price * 0.7)
        
        # Create DataFrame
        data = {
            'open': close_prices * np.random.uniform(0.99, 1.01, days),
            'high': close_prices * np.random.uniform(1.01, 1.03, days),
            'low': close_prices * np.random.uniform(0.97, 0.99, days),
            'close': close_prices,
            'volume': np.random.randint(1000000, 10000000, days)
        }
        
        df = pd.DataFrame(data, index=dates)
        return df
    
    def _add_indicators(self, df):
        """Add technical indicators to a DataFrame"""
        # Copy to avoid modifying original
        df = df.copy()
        
        # Simple moving averages
        df['sma20'] = df['close'].rolling(window=20).mean()
        df['sma50'] = df['close'].rolling(window=50).mean()
        
        # Exponential moving averages
        df['ema20'] = df['close'].ewm(span=20, adjust=False).mean()
        df['ema50'] = df['close'].ewm(span=50, adjust=False).mean()
        
        # Bollinger Bands
        df['middle_band'] = df['close'].rolling(window=20).mean()
        std_dev = df['close'].rolling(window=20).std()
        df['upper_band'] = df['middle_band'] + (std_dev * 2)
        df['lower_band'] = df['middle_band'] - (std_dev * 2)
        
        # MACD (Moving Average Convergence Divergence)
        df['ema12'] = df['close'].ewm(span=12, adjust=False).mean()
        df['ema26'] = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = df['ema12'] - df['ema26']
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        df['macd_hist'] = df['macd'] - df['macd_signal']
        
        # Fisher Transform
        df = self._add_fisher_transform(df)
        
        # RSI (Relative Strength Index)
        df = self._add_rsi(df)
        
        return df
    
    def _add_fisher_transform(self, df, period=10):
        """Add Fisher Transform indicator"""
        # Get min and max of price
        df['fisher_high'] = df['close'].rolling(window=period).max()
        df['fisher_low'] = df['close'].rolling(window=period).min()
        
        # Normalize price between -1 and 1
        df['fisher_norm'] = (2 * ((df['close'] - df['fisher_low']) / 
                              (df['fisher_high'] - df['fisher_low'])) - 1)
        
        # Apply boundary constraints
        df['fisher_norm'] = df['fisher_norm'].clip(-0.999, 0.999)
        
        # Apply Fisher Transform
        df['fisher'] = 0.5 * np.log((1 + df['fisher_norm']) / (1 - df['fisher_norm']))
        
        # Clean up temporary columns
        df.drop(['fisher_high', 'fisher_low', 'fisher_norm'], axis=1, inplace=True)
        
        return df
    
    def _add_rsi(self, df, period=14):
        """Add Relative Strength Index"""
        # Calculate price changes
        delta = df['close'].diff()
        
        # Separate gains and losses
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        
        # Calculate average gain and loss
        avg_gain = gain.rolling(window=period).mean()
        avg_loss = loss.rolling(window=period).mean()
        
        # Calculate RS and RSI
        rs = avg_gain / avg_loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        return df


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python standalone_chart_renderer.py SYMBOL [DAYS]")
        sys.exit(1)
    
    symbol = sys.argv[1].upper()
    days = int(sys.argv[2]) if len(sys.argv) > 2 else 30
    
    renderer = StandaloneChartRenderer()
    chart_path = renderer.render(symbol, days)
    
    print(f"Chart saved to: {chart_path}") 