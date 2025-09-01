#!/usr/bin/env python
"""
IBKR Historical Data Retriever

Utility to fetch and analyze historical data from Interactive Brokers.
Uses the existing WarMachine AI Option Trader infrastructure.
"""

import os
import sys
import json
import time
import logging
import threading
import argparse
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
from pathlib import Path
from connectors.ibkr_connector import IBKRConnector

# Ensure required directories exist
os.makedirs('logs', exist_ok=True)
os.makedirs('data/historical', exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(f"logs/ibkr_historical_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    ]
)
logger = logging.getLogger(__name__)

def load_config(config_path="config/warmachine_config.json"):
    """Load the system configuration from file"""
    try:
        if not os.path.exists(config_path):
            logger.error(f"Configuration file not found: {config_path}")
            sys.exit(1)
            
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        logger.info(f"Configuration loaded from {config_path}")
        return config
    except Exception as e:
        logger.error(f"Error loading configuration: {str(e)}")
        sys.exit(1)

class IBKRHistoricalDataApp:
    """Application to fetch historical data from IBKR"""
    
    def __init__(self, config=None):
        """
        Initialize the application
        
        Args:
            config: Configuration dictionary (optional)
        """
        self.config = config or load_config()
        self.ibkr_config = self.config.get("market_data", {}).get("providers", {}).get("ibkr", {})
        
        if not self.ibkr_config:
            logger.error("IBKR configuration not found in config file")
            sys.exit(1)
            
        logger.info(f"IBKR Configuration: {self.ibkr_config}")
        
        try:
            # Import IBKRConnector from the WarMachine project
            logger.info("Importing IBKRConnector...")
            self.connector_class = IBKRConnector
        except ImportError as e:
            logger.error(f"Failed to import IBKRConnector: {str(e)}")
            logger.error("Make sure you're running this script from the project root directory")
            sys.exit(1)
            
        self.connector = None
        self.results_path = Path("data/historical")
        
    def connect(self):
        """Connect to IBKR"""
        logger.info("Creating IBKR connector...")
        self.connector = self.connector_class(self.ibkr_config)
        
        logger.info(f"Connection status: {self.connector.connected}")
        return self.connector.connected
    
    def disconnect(self):
        """Disconnect from IBKR"""
        if self.connector:
            self.connector.disconnect()
            logger.info("Disconnected from IBKR")
            
    def get_historical_data(self, symbol, timeframe="1d", duration_days=30, save=True):
        """
        Get historical data for a symbol
        
        Args:
            symbol: Instrument symbol
            timeframe: Timeframe (1m, 5m, 15m, 1h, 1d, etc.)
            duration_days: Number of days of historical data to fetch
            save: Whether to save the data to file
            
        Returns:
            DataFrame with historical data
        """
        if not self.connector:
            logger.error("Not connected to IBKR")
            return pd.DataFrame()
            
        # Calculate limit based on timeframe and duration
        limit_map = {
            "1s": 24 * 60 * 60,
            "5s": 24 * 60 * 12,
            "15s": 24 * 60 * 4,
            "30s": 24 * 60 * 2,
            "1m": 24 * 60,
            "3m": 24 * 20,
            "5m": 24 * 12,
            "15m": 24 * 4,
            "30m": 24 * 2,
            "1h": 24,
            "4h": 6,
            "1d": 1,
            "1w": 1/7
        }
        
        bars_per_day = limit_map.get(timeframe, 24 * 60)
        limit = int(bars_per_day * duration_days)
        
        # Get the data
        logger.info(f"Fetching {limit} {timeframe} bars for {symbol}...")
        df = self.connector.get_bars(symbol, timeframe, limit)
        
        if df.empty:
            logger.warning(f"No data returned for {symbol}")
            return df
            
        logger.info(f"Received {len(df)} bars for {symbol}")
        
        # Save to file if requested
        if save:
            filename = f"{symbol}_{timeframe}_{duration_days}d_{datetime.now().strftime('%Y%m%d')}.csv"
            file_path = self.results_path / filename
            df.to_csv(file_path)
            logger.info(f"Data saved to {file_path}")
            
        return df
        
    def get_option_data(self, symbol, expiry=None, strike=None, option_type=None):
        """
        Get option data
        
        Args:
            symbol: Underlying symbol
            expiry: Expiry date (optional, if None, returns full chain)
            strike: Strike price (optional)
            option_type: 'C' for call, 'P' for put (optional)
            
        Returns:
            Dictionary with option data
        """
        if not self.connector:
            logger.error("Not connected to IBKR")
            return {}
            
        # If only symbol provided, get full option chain
        if not expiry:
            logger.info(f"Fetching option chain for {symbol}...")
            chain = self.connector.get_option_chain(symbol)
            
            if not chain:
                logger.warning(f"No option chain data returned for {symbol}")
                return {}
                
            # Save to file
            filename = f"{symbol}_option_chain_{datetime.now().strftime('%Y%m%d')}.json"
            file_path = self.results_path / filename
            
            with open(file_path, 'w') as f:
                json.dump(chain, f, indent=2)
                
            logger.info(f"Option chain saved to {file_path}")
            return chain
            
        # If expiry, strike, and option_type provided, get specific option data
        if expiry and strike and option_type:
            logger.info(f"Fetching {option_type} option data for {symbol} {expiry} {strike}...")
            
            # Call private method directly
            option_data = self.connector._get_option_data(symbol, expiry, strike, option_type)
            
            if not option_data:
                logger.warning(f"No option data returned")
                return {}
                
            # Add metadata
            option_data["symbol"] = symbol
            option_data["expiry"] = expiry
            option_data["strike"] = strike
            option_data["option_type"] = option_type
            option_data["timestamp"] = datetime.now().isoformat()
            
            return option_data
            
        logger.error("Incomplete option specifications")
        return {}
        
    def plot_data(self, df, title=None, save_path=None):
        """
        Plot historical data
        
        Args:
            df: DataFrame with historical data
            title: Plot title
            save_path: Path to save the plot
        """
        if df.empty:
            logger.warning("No data to plot")
            return
            
        # Create figure
        plt.figure(figsize=(12, 8))
        
        # Plot OHLC as a line
        plt.subplot(2, 1, 1)
        plt.plot(df.index, df['close'], label='Close')
        plt.fill_between(df.index, df['low'], df['high'], alpha=0.3)
        plt.title(title or "Price History")
        plt.legend()
        plt.grid(True)
        
        # Plot volume
        if 'volume' in df.columns and not df['volume'].isna().all() and not (df['volume'] == 0).all():
            plt.subplot(2, 1, 2)
            plt.bar(df.index, df['volume'], width=0.6, alpha=0.5)
            plt.title("Volume")
            plt.grid(True)
        
        plt.tight_layout()
        
        # Save or show
        if save_path:
            plt.savefig(save_path)
            logger.info(f"Plot saved to {save_path}")
        else:
            plt.show()
            
def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="IBKR Historical Data Retriever")
    
    parser.add_argument("--symbol", "-s", type=str, required=True, help="Symbol to fetch data for")
    parser.add_argument("--timeframe", "-t", type=str, default="1d", 
                        help="Timeframe (1m, 5m, 15m, 1h, 1d, etc.)")
    parser.add_argument("--days", "-d", type=int, default=30, 
                        help="Number of days of historical data")
    parser.add_argument("--plot", "-p", action="store_true", help="Plot the data")
    parser.add_argument("--options", "-o", action="store_true", help="Get option chain data")
    parser.add_argument("--expiry", "-e", type=str, help="Option expiry date (YYYYMMDD)")
    parser.add_argument("--strike", type=float, help="Option strike price")
    parser.add_argument("--type", choices=["C", "P"], help="Option type (C=call, P=put)")
    
    return parser.parse_args()

def main():
    """Main function"""
    args = parse_args()
    
    app = IBKRHistoricalDataApp()
    
    try:
        # Connect to IBKR
        logger.info("Connecting to IBKR...")
        if not app.connect():
            logger.error("Failed to connect to IBKR")
            logger.info("Possible reasons:")
            logger.info("1. TWS or IB Gateway is not running")
            logger.info("2. API connection not enabled in TWS/Gateway settings")
            logger.info("3. Port number mismatch in configuration")
            return
            
        # Get historical data
        if not args.options or (args.options and not args.expiry):
            # Get price history
            df = app.get_historical_data(args.symbol, args.timeframe, args.days)
            
            # Plot if requested
            if args.plot and not df.empty:
                title = f"{args.symbol} - {args.timeframe} - {args.days} days"
                save_path = f"data/historical/{args.symbol}_{args.timeframe}_{datetime.now().strftime('%Y%m%d')}.png"
                app.plot_data(df, title, save_path)
        
        # Get option data if requested
        if args.options:
            if args.expiry and args.strike and args.type:
                # Get specific option
                option_data = app.get_option_data(args.symbol, args.expiry, args.strike, args.type)
                logger.info(f"Option data: {json.dumps(option_data, indent=2)}")
            else:
                # Get full chain
                chain = app.get_option_data(args.symbol)
                logger.info(f"Retrieved option chain with {len(chain.get('expirations', []))} expirations")
                
                # Print summary
                if chain and 'expirations' in chain:
                    logger.info(f"Available expirations:")
                    for exp in chain['expirations']:
                        logger.info(f"  {exp['date']} - {len(exp['options'])} strikes")
    
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
    
    finally:
        # Disconnect
        app.disconnect()

if __name__ == "__main__":
    main() 