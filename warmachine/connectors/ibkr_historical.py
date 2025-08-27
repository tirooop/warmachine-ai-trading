#!/usr/bin/env python
"""
Standalone IBKR Historical Data Retriever

Utility to fetch and analyze historical data from Interactive Brokers.
This is a standalone version that doesn't depend on the WarMachine project.
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

# Import ibapi modules
try:
    from ibapi.client import EClient
    from ibapi.wrapper import EWrapper
    from ibapi.contract import Contract
    from ibapi.common import BarData, ListOfHistoricalTickBidAsk, TickAttribBidAsk, ListOfHistoricalTickLast, TickAttribLast
except ImportError as e:
    print(f"Error importing IBKR API modules: {str(e)}")
    print("Please install the IBKR API: pip install ibapi")
    sys.exit(1)

# Ensure required directories exist
os.makedirs('logs', exist_ok=True)
os.makedirs('data/historical', exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(f"logs/ibkr_standalone_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    ]
)
logger = logging.getLogger(__name__)

def load_config(config_path="config/warmachine_config.json"):
    """Load the system configuration from file"""
    try:
        if not os.path.exists(config_path):
            # If config file not found, use default settings
            logger.warning(f"Configuration file not found: {config_path}")
            logger.warning("Using default configuration")
            return {
                "market_data": {
                    "providers": {
                        "ibkr": {
                            "host": "127.0.0.1",
                            "port": 7496,  # TWS: 7496, IB Gateway: 4001
                            "client_id": 1
                        }
                    }
                }
            }
            
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        logger.info(f"Configuration loaded from {config_path}")
        return config
    except Exception as e:
        logger.error(f"Error loading configuration: {str(e)}")
        logger.warning("Using default configuration")
        return {
            "market_data": {
                "providers": {
                    "ibkr": {
                        "host": "127.0.0.1",
                        "port": 7496,
                        "client_id": 1
                    }
                }
            }
        }

class IBHistoricalDataApp(EWrapper, EClient):
    """IBKR Historical Data Application"""
    
    def __init__(self, host="127.0.0.1", port=7496, client_id=1):
        """
        Initialize the application
        
        Args:
            host: IB Gateway / TWS hostname or IP address
            port: IB Gateway / TWS port
            client_id: Client ID for API connection
        """
        EClient.__init__(self, self)
        
        self.host = host
        self.port = port
        self.client_id = client_id
        self.req_id = 0
        self.connected = False
        self.data = {}
        self.errors = []
        self.event = threading.Event()
        self.results_path = Path("data/historical")
        
        # Connect to the API
        logger.info(f"Connecting to IBKR at {host}:{port} (client ID: {client_id})...")
    
    def connect_to_ibkr(self):
        """Connect to IBKR API"""
        try:
            self.connect(self.host, self.port, self.client_id)
            
            # Start the client thread
            thread = threading.Thread(target=self.run)
            thread.daemon = True
            thread.start()
            
            # Wait for connection
            logger.info("Waiting for connection...")
            start_time = time.time()
            while not self.connected and time.time() - start_time < 10:
                time.sleep(0.1)
            
            if self.connected:
                logger.info("Connected to IBKR successfully")
                return True
            else:
                logger.error("Failed to connect to IBKR in 10 seconds")
                return False
                
        except Exception as e:
            logger.error(f"Error connecting to IBKR: {str(e)}")
            return False
    
    def nextValidId(self, orderId: int):
        """Callback for next valid ID"""
        super().nextValidId(orderId)
        self.req_id = orderId
        self.connected = True
    
    def error(self, reqId: int, errorCode: int, errorString: str, advancedOrderRejectJson=""):
        """Callback for errors"""
        error_msg = f"Error {errorCode}: {errorString}"
        
        if errorCode == 2104 or errorCode == 2106:  # Market data farm connection is OK
            return
        
        if errorCode == 2158:  # Sec-def data farm connection is OK
            return
            
        if reqId != -1:  # Error not related to connection
            self.errors.append({"req_id": reqId, "code": errorCode, "message": errorString})
            logger.error(f"Request {reqId}: {error_msg}")
        else:
            logger.error(error_msg)
            
        # Connection failures
        if errorCode == 502:
            logger.error("Could not connect. TWS/IB Gateway is not running.")
        elif errorCode == 501:
            logger.error("Could not connect. TWS/IB Gateway rejected connection request.")
        elif errorCode == 1100:
            logger.error("Connectivity between IB and TWS/IB Gateway has been lost.")
        elif errorCode == 504:
            logger.error("Not connected - API connection is inactive/broken.")
    
    def connectionClosed(self):
        """Callback for connection closed"""
        self.connected = False
        logger.info("Connection to IBKR closed")
    
    def get_next_req_id(self):
        """Get a unique request ID"""
        self.req_id += 1
        return self.req_id
    
    def historicalData(self, reqId: int, bar: BarData):
        """Callback for historical data"""
        # Initialize the data structure if it's the first bar
        if reqId not in self.data:
            self.data[reqId] = []
        
        # Append the bar to the data list
        self.data[reqId].append({
            "date": bar.date,
            "open": bar.open,
            "high": bar.high,
            "low": bar.low,
            "close": bar.close,
            "volume": bar.volume,
            "wap": bar.wap,
            "count": bar.barCount
        })
    
    def historicalDataEnd(self, reqId: int, start: str, end: str):
        """Callback when historical data is complete"""
        logger.info(f"Historical data complete for request {reqId}")
        self.event.set()
    
    def historicalDataUpdate(self, reqId: int, bar: BarData):
        """Callback for historical data updates - for real-time bars"""
        # Only used if keepUpToDate=True in reqHistoricalData
        self.historicalData(reqId, bar)
    
    def get_historical_data(self, symbol, security_type="STK", exchange="SMART", currency="USD",
                           timeframe="1d", duration_days=30, end_datetime="", what_to_show="TRADES",
                           use_rth=True, save=True):
        """
        Get historical data for a symbol
        
        Args:
            symbol: Instrument symbol
            security_type: Security type (STK, OPT, FUT, CASH, etc.)
            exchange: Exchange (SMART, CBOE, etc.)
            currency: Currency (USD, EUR, etc.)
            timeframe: Bar size (1 min, 5 mins, 1 hour, 1 day, etc.)
            duration_days: Number of days of historical data
            end_datetime: End date/time for the data
            what_to_show: Type of data (TRADES, MIDPOINT, BID, ASK, etc.)
            use_rth: Use regular trading hours only
            save: Whether to save the data to file
            
        Returns:
            DataFrame with historical data
        """
        # Reset data and event
        req_id = self.get_next_req_id()
        self.data[req_id] = []
        self.event.clear()
        
        # Map timeframe to IB format
        timeframe_map = {
            "1s": "1 secs",
            "5s": "5 secs",
            "10s": "10 secs",
            "15s": "15 secs",
            "30s": "30 secs",
            "1m": "1 min",
            "2m": "2 mins",
            "3m": "3 mins",
            "5m": "5 mins",
            "10m": "10 mins",
            "15m": "15 mins",
            "20m": "20 mins",
            "30m": "30 mins",
            "1h": "1 hour",
            "2h": "2 hours",
            "3h": "3 hours",
            "4h": "4 hours",
            "8h": "8 hours",
            "1d": "1 day",
            "1w": "1 week",
            "1m": "1 month"
        }
        
        bar_size = timeframe_map.get(timeframe, timeframe)
        
        # Calculate duration string
        duration_str = f"{duration_days} D"
        
        # Create contract
        contract = Contract()
        contract.symbol = symbol
        contract.secType = security_type
        contract.exchange = exchange
        contract.currency = currency
        
        # Request historical data
        logger.info(f"Requesting {duration_str} of {bar_size} data for {symbol}...")
        
        self.reqHistoricalData(
            reqId=req_id,
            contract=contract,
            endDateTime=end_datetime,
            durationStr=duration_str,
            barSizeSetting=bar_size,
            whatToShow=what_to_show,
            useRTH=1 if use_rth else 0,
            formatDate=1,
            keepUpToDate=False,
            chartOptions=[]
        )
        
        # Wait for data
        self.event.wait(timeout=30)
        
        # Check if we have data
        if not self.data[req_id]:
            logger.warning(f"No data returned for {symbol}")
            return pd.DataFrame()
        
        # Convert to dataframe
        df = pd.DataFrame(self.data[req_id])
        
        # Convert date to datetime and set as index
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'], format='%Y%m%d %H:%M:%S' if ' ' in df['date'].iloc[0] else '%Y%m%d')
            df.set_index('date', inplace=True)
        
        logger.info(f"Received {len(df)} bars for {symbol}")
        
        # Save to file if requested
        if save:
            filename = f"{symbol}_{timeframe}_{duration_days}d_{datetime.now().strftime('%Y%m%d')}.csv"
            file_path = self.results_path / filename
            df.to_csv(file_path)
            logger.info(f"Data saved to {file_path}")
        
        return df
    
    def contractDetails(self, reqId: int, contractDetails):
        """Callback for contract details"""
        if reqId not in self.data:
            self.data[reqId] = []
        
        self.data[reqId].append(contractDetails)
    
    def contractDetailsEnd(self, reqId: int):
        """Callback when contract details are complete"""
        logger.info(f"Contract details complete for request {reqId}")
        self.event.set()
    
    def get_option_chain(self, symbol, exchange="SMART", currency="USD"):
        """
        Get option chain for a symbol
        
        Args:
            symbol: Underlying symbol
            exchange: Exchange
            currency: Currency
            
        Returns:
            Dictionary with option chain data
        """
        # Reset data and event
        req_id = self.get_next_req_id()
        self.data[req_id] = []
        self.event.clear()
        
        # Create contract for the underlying
        contract = Contract()
        contract.symbol = symbol
        contract.secType = "STK"
        contract.exchange = exchange
        contract.currency = currency
        
        # Request contract details to get contract ID
        logger.info(f"Requesting contract details for {symbol}...")
        self.reqContractDetails(req_id, contract)
        
        # Wait for data
        self.event.wait(timeout=10)
        
        # Check if we have data
        if not self.data[req_id]:
            logger.warning(f"No contract details returned for {symbol}")
            return {}
        
        # Get contract ID
        contract_details = self.data[req_id][0]
        underlying_id = contract_details.contract.conId
        
        # Reset for option chain
        req_id = self.get_next_req_id()
        self.data[req_id] = []
        self.event.clear()
        
        # Request option chain
        logger.info(f"Requesting option chain for {symbol}...")
        self.reqSecDefOptParams(
            reqId=req_id,
            underlyingSymbol=symbol,
            futFopExchange="",
            underlyingSecType="STK",
            underlyingConId=underlying_id
        )
        
        # Wait for data
        self.event.wait(timeout=10)
        
        # Check if we have data
        if not self.data[req_id]:
            logger.warning(f"No option chain data returned for {symbol}")
            return {}
        
        # Process data
        chain_data = self.data[req_id]
        
        result = {
            "symbol": symbol,
            "expirations": [],
            "strikes": []
        }
        
        # Extract expirations and strikes
        for chain in chain_data:
            # Add expirations
            for expiry in chain.expirations:
                if expiry not in result["expirations"]:
                    result["expirations"].append(expiry)
            
            # Add strikes
            for strike in chain.strikes:
                if strike not in result["strikes"]:
                    result["strikes"].append(strike)
        
        # Sort data
        result["expirations"].sort()
        result["strikes"].sort()
        
        # Save to file
        filename = f"{symbol}_option_chain_{datetime.now().strftime('%Y%m%d')}.json"
        file_path = self.results_path / filename
        
        with open(file_path, 'w') as f:
            json.dump(result, f, indent=2)
            
        logger.info(f"Option chain saved to {file_path}")
        
        return result
    
    def securityDefinitionOptionParameter(self, reqId: int, exchange: str, underlyingConId: int, 
                                         tradingClass: str, multiplier: str, expirations, strikes):
        """Callback for option chain data"""
        if reqId not in self.data:
            self.data[reqId] = []
        
        # Append chain data
        self.data[reqId].append({
            "exchange": exchange,
            "underlyingId": underlyingConId,
            "tradingClass": tradingClass,
            "multiplier": multiplier,
            "expirations": list(expirations),
            "strikes": list(strikes)
        })
    
    def securityDefinitionOptionParameterEnd(self, reqId: int):
        """Callback when option chain data is complete"""
        logger.info(f"Option chain data complete for request {reqId}")
        self.event.set()
    
    def get_option_data(self, symbol, expiry, strike, option_type, exchange="SMART", currency="USD"):
        """
        Get data for a specific option contract
        
        Args:
            symbol: Underlying symbol
            expiry: Expiry date (YYYYMMDD format)
            strike: Strike price
            option_type: Option type (C=Call, P=Put)
            exchange: Exchange
            currency: Currency
            
        Returns:
            Dictionary with option data
        """
        # Create option contract
        contract = Contract()
        contract.symbol = symbol
        contract.secType = "OPT"
        contract.exchange = exchange
        contract.currency = currency
        contract.lastTradeDateOrContractMonth = expiry
        contract.strike = strike
        contract.right = "C" if option_type == "C" else "P"
        contract.multiplier = "100"
        
        # Request market data
        req_id = self.get_next_req_id()
        self.data[req_id] = []
        self.event.clear()
        
        logger.info(f"Requesting {option_type} option data for {symbol} {expiry} {strike}...")
        
        # Request market data
        self.reqMktData(req_id, contract, "", False, False, [])
        
        # Wait briefly for data
        time.sleep(2)
        
        # Cancel request
        self.cancelMktData(req_id)
        
        # Get option data from tickers
        if hasattr(self, "tickers") and req_id in self.tickers:
            ticker = self.tickers[req_id]
            
            option_data = {
                "symbol": symbol,
                "expiry": expiry,
                "strike": strike,
                "option_type": option_type,
                "bid": ticker.bid,
                "ask": ticker.ask,
                "last": ticker.last,
                "volume": ticker.volume,
                "open_interest": ticker.openInterest if hasattr(ticker, "openInterest") else 0,
                "timestamp": datetime.now().isoformat()
            }
            
            return option_data
        
        # Fallback - request historical data for the option
        return self.get_historical_data(
            symbol=symbol,
            security_type="OPT",
            exchange=exchange,
            currency=currency,
            timeframe="1d",
            duration_days=1,
            what_to_show="MIDPOINT",
            save=False
        )
    
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
    parser = argparse.ArgumentParser(description="Standalone IBKR Historical Data Retriever")
    
    parser.add_argument("--host", type=str, default="127.0.0.1", 
                        help="IB Gateway / TWS hostname or IP address")
    parser.add_argument("--port", type=int, default=7496, 
                        help="IB Gateway / TWS port (7496 for TWS, 4001 for Gateway)")
    parser.add_argument("--client-id", type=int, default=1, 
                        help="Client ID for API connection")
    parser.add_argument("--symbol", "-s", type=str, required=True, 
                        help="Symbol to fetch data for")
    parser.add_argument("--security-type", type=str, default="STK", 
                        choices=["STK", "OPT", "FUT", "CASH", "IND"], 
                        help="Security type")
    parser.add_argument("--exchange", type=str, default="SMART", 
                        help="Exchange")
    parser.add_argument("--currency", type=str, default="USD", 
                        help="Currency")
    parser.add_argument("--timeframe", "-t", type=str, default="1d", 
                        help="Timeframe (1m, 5m, 15m, 1h, 1d, etc.)")
    parser.add_argument("--days", "-d", type=int, default=30, 
                        help="Number of days of historical data")
    parser.add_argument("--plot", "-p", action="store_true", 
                        help="Plot the data")
    parser.add_argument("--options", "-o", action="store_true", 
                        help="Get option chain data")
    parser.add_argument("--expiry", "-e", type=str, 
                        help="Option expiry date (YYYYMMDD)")
    parser.add_argument("--strike", type=float, 
                        help="Option strike price")
    parser.add_argument("--type", choices=["C", "P"], 
                        help="Option type (C=call, P=put)")
    parser.add_argument("--what-to-show", type=str, default="TRADES", 
                        choices=["TRADES", "MIDPOINT", "BID", "ASK", "BID_ASK", 
                                 "HISTORICAL_VOLATILITY", "OPTION_IMPLIED_VOLATILITY"],
                        help="Type of data to retrieve")
    parser.add_argument("--use-rth", action="store_true", 
                        help="Use regular trading hours only")
    
    return parser.parse_args()

def main():
    """Main function"""
    args = parse_args()
    
    # Load configuration but override with command line arguments
    config = load_config()
    ibkr_config = config.get("market_data", {}).get("providers", {}).get("ibkr", {})
    
    # Create app and connect
    app = IBHistoricalDataApp(
        host=args.host or ibkr_config.get("host", "127.0.0.1"),
        port=args.port or ibkr_config.get("port", 7496),
        client_id=args.client_id or ibkr_config.get("client_id", 1)
    )
    
    try:
        # Connect to IBKR
        if not app.connect_to_ibkr():
            logger.error("Failed to connect to IBKR")
            logger.info("Possible reasons:")
            logger.info("1. TWS or IB Gateway is not running")
            logger.info("2. API connection not enabled in TWS/Gateway settings")
            logger.info("3. Port number mismatch in configuration")
            return
        
        # Get historical data if not options or if options with no specific contract
        if not args.options or (args.options and not args.expiry):
            # Get price history
            df = app.get_historical_data(
                symbol=args.symbol,
                security_type=args.security_type,
                exchange=args.exchange,
                currency=args.currency,
                timeframe=args.timeframe,
                duration_days=args.days,
                what_to_show=args.what_to_show,
                use_rth=args.use_rth
            )
            
            # Plot if requested
            if args.plot and not df.empty:
                title = f"{args.symbol} - {args.timeframe} - {args.days} days"
                save_path = f"data/historical/{args.symbol}_{args.timeframe}_{datetime.now().strftime('%Y%m%d')}.png"
                app.plot_data(df, title, save_path)
        
        # Get option data if requested
        if args.options:
            if args.expiry and args.strike and args.type:
                # Get specific option
                option_data = app.get_option_data(
                    symbol=args.symbol,
                    expiry=args.expiry,
                    strike=args.strike,
                    option_type=args.type,
                    exchange=args.exchange,
                    currency=args.currency
                )
                logger.info(f"Option data: {json.dumps(option_data, indent=2)}")
            else:
                # Get full chain
                chain = app.get_option_chain(
                    symbol=args.symbol,
                    exchange=args.exchange,
                    currency=args.currency
                )
                
                if chain:
                    logger.info(f"Option chain data:")
                    logger.info(f"Symbol: {chain['symbol']}")
                    logger.info(f"Expirations: {len(chain['expirations'])}")
                    logger.info(f"Strikes: {len(chain['strikes'])}")
    
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
    
    finally:
        # Disconnect
        if app.connected:
            app.disconnect()
            logger.info("Disconnected from IBKR")

if __name__ == "__main__":
    main() 