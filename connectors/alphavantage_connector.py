"""
Alpha Vantage Connector

Connects to Alpha Vantage for stock, forex, and crypto market data.
Provides a fallback data source for when primary sources are unavailable.
"""

import os
import logging
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union, Callable
import pandas as pd
import numpy as np
import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AlphaVantageConnector:
    """Connector for Alpha Vantage market data"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Alpha Vantage connector
        
        Args:
            config: Configuration dictionary with Alpha Vantage settings
        """
        self.config = config
        self.api_key = config.get("api_key", "")
        self.base_url = "https://www.alphavantage.co/query"
        
        # Validate API key
        if not self.api_key:
            logger.error("Alpha Vantage API key is required")
            raise ValueError("Alpha Vantage API key is required")
        
        # Cache to avoid redundant API calls
        self.market_data_cache = {}
        self.cache_duration = config.get("cache_duration", 300)  # seconds
        self.cache_lock = threading.RLock()
        
        # Rate limiting (Alpha Vantage has a limit of 5 calls per minute for free tier)
        self.calls_per_minute = config.get("calls_per_minute", 5)
        self.api_call_times = []
        self.api_call_lock = threading.RLock()
        
        logger.info("Alpha Vantage connector initialized")
    
    def _make_api_request(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make an API request to Alpha Vantage with rate limiting
        
        Args:
            params: Query parameters
            
        Returns:
            Response data
        """
        # Apply rate limiting
        with self.api_call_lock:
            current_time = time.time()
            
            # Remove old call timestamps
            self.api_call_times = [t for t in self.api_call_times if current_time - t < 60]
            
            # Check if we've hit the rate limit
            if len(self.api_call_times) >= self.calls_per_minute:
                # Calculate wait time
                oldest_call = min(self.api_call_times)
                wait_time = 60 - (current_time - oldest_call) + 0.1  # Add a small buffer
                
                logger.warning(f"Rate limit hit, waiting {wait_time:.2f} seconds")
                time.sleep(wait_time)
                
                # Reset the timer after waiting
                current_time = time.time()
                self.api_call_times = [t for t in self.api_call_times if current_time - t < 60]
            
            # Add current call timestamp
            self.api_call_times.append(current_time)
        
        # Add API key to parameters
        params["apikey"] = self.api_key
        
        try:
            response = requests.get(self.base_url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                
                # Check for API error messages
                if "Error Message" in data:
                    logger.error(f"Alpha Vantage API error: {data['Error Message']}")
                    return {}
                
                # Check for usage limit messages
                if "Note" in data and "API call frequency" in data["Note"]:
                    logger.warning(f"Alpha Vantage API limit warning: {data['Note']}")
                
                return data
            else:
                logger.error(f"Alpha Vantage API error: {response.status_code} - {response.text}")
                return {}
        
        except Exception as e:
            logger.error(f"Error making API request: {str(e)}")
            return {}
    
    def _get_from_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """
        Get data from cache if available and not expired
        
        Args:
            cache_key: Cache key
            
        Returns:
            Cached data or None
        """
        with self.cache_lock:
            if cache_key in self.market_data_cache:
                cached_data = self.market_data_cache[cache_key]
                cache_time = cached_data.get("cache_time", 0)
                current_time = time.time()
                
                # Check if cache is still valid
                if current_time - cache_time < self.cache_duration:
                    return cached_data.get("data")
        
        return None
    
    def _store_in_cache(self, cache_key: str, data: Dict[str, Any]):
        """
        Store data in cache
        
        Args:
            cache_key: Cache key
            data: Data to store
        """
        with self.cache_lock:
            self.market_data_cache[cache_key] = {
                "data": data,
                "cache_time": time.time()
            }
    
    def get_stock_data(self, symbol: str, function: str = "TIME_SERIES_DAILY", 
                     outputsize: str = "compact") -> Dict[str, Any]:
        """
        Get stock time series data
        
        Args:
            symbol: Stock symbol
            function: Time series function (TIME_SERIES_INTRADAY, TIME_SERIES_DAILY, etc.)
            outputsize: Output size (compact or full)
            
        Returns:
            Stock time series data
        """
        cache_key = f"stock_{symbol}_{function}_{outputsize}"
        
        # Check cache first
        cached_data = self._get_from_cache(cache_key)
        if cached_data:
            return cached_data
        
        # Prepare parameters
        params = {
            "function": function,
            "symbol": symbol,
            "outputsize": outputsize
        }
        
        # Add interval for intraday data
        if function == "TIME_SERIES_INTRADAY":
            params["interval"] = "5min"
        
        # Make API request
        data = self._make_api_request(params)
        
        # Store in cache
        if data:
            self._store_in_cache(cache_key, data)
        
        return data
    
    def get_forex_data(self, from_currency: str, to_currency: str, 
                      function: str = "FX_DAILY") -> Dict[str, Any]:
        """
        Get forex exchange rate data
        
        Args:
            from_currency: From currency code
            to_currency: To currency code
            function: Time series function (FX_INTRADAY, FX_DAILY, etc.)
            
        Returns:
            Forex exchange rate data
        """
        cache_key = f"forex_{from_currency}_{to_currency}_{function}"
        
        # Check cache first
        cached_data = self._get_from_cache(cache_key)
        if cached_data:
            return cached_data
        
        # Prepare parameters
        params = {
            "function": function,
            "from_symbol": from_currency,
            "to_symbol": to_currency,
            "outputsize": "compact"
        }
        
        # Add interval for intraday data
        if function == "FX_INTRADAY":
            params["interval"] = "5min"
        
        # Make API request
        data = self._make_api_request(params)
        
        # Store in cache
        if data:
            self._store_in_cache(cache_key, data)
        
        return data
    
    def get_crypto_data(self, symbol: str, market: str = "USD",
                       function: str = "DIGITAL_CURRENCY_DAILY") -> Dict[str, Any]:
        """
        Get cryptocurrency data
        
        Args:
            symbol: Cryptocurrency symbol
            market: Market (USD, EUR, etc.)
            function: Time series function (DIGITAL_CURRENCY_DAILY, etc.)
            
        Returns:
            Cryptocurrency data
        """
        cache_key = f"crypto_{symbol}_{market}_{function}"
        
        # Check cache first
        cached_data = self._get_from_cache(cache_key)
        if cached_data:
            return cached_data
        
        # Prepare parameters
        params = {
            "function": function,
            "symbol": symbol,
            "market": market
        }
        
        # Make API request
        data = self._make_api_request(params)
        
        # Store in cache
        if data:
            self._store_in_cache(cache_key, data)
        
        return data
    
    def get_technical_indicator(self, symbol: str, indicator: str, 
                               interval: str = "daily", time_period: int = 14) -> Dict[str, Any]:
        """
        Get technical indicator data
        
        Args:
            symbol: Stock symbol
            indicator: Technical indicator (SMA, EMA, RSI, etc.)
            interval: Time interval (1min, 5min, 15min, 30min, 60min, daily, weekly, monthly)
            time_period: Time period
            
        Returns:
            Technical indicator data
        """
        cache_key = f"indicator_{symbol}_{indicator}_{interval}_{time_period}"
        
        # Check cache first
        cached_data = self._get_from_cache(cache_key)
        if cached_data:
            return cached_data
        
        # Prepare parameters
        params = {
            "function": indicator,
            "symbol": symbol,
            "interval": interval,
            "time_period": time_period,
            "series_type": "close"
        }
        
        # Make API request
        data = self._make_api_request(params)
        
        # Store in cache
        if data:
            self._store_in_cache(cache_key, data)
        
        return data
    
    def search_symbols(self, keywords: str) -> List[Dict[str, Any]]:
        """
        Search for symbols
        
        Args:
            keywords: Search keywords
            
        Returns:
            List of matching symbols
        """
        cache_key = f"search_{keywords}"
        
        # Check cache first
        cached_data = self._get_from_cache(cache_key)
        if cached_data:
            return cached_data
        
        # Prepare parameters
        params = {
            "function": "SYMBOL_SEARCH",
            "keywords": keywords
        }
        
        # Make API request
        data = self._make_api_request(params)
        
        # Extract matches
        matches = []
        if data and "bestMatches" in data:
            matches = data["bestMatches"]
        
        # Store in cache
        if matches:
            self._store_in_cache(cache_key, matches)
        
        return matches
    
    def get_quote(self, symbol: str) -> Dict[str, Any]:
        """
        Get global quote for a symbol
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Quote data
        """
        cache_key = f"quote_{symbol}"
        
        # Check cache first with shorter cache duration for quotes
        cached_data = self._get_from_cache(cache_key)
        if cached_data:
            return cached_data
        
        # Prepare parameters
        params = {
            "function": "GLOBAL_QUOTE",
            "symbol": symbol
        }
        
        # Make API request
        data = self._make_api_request(params)
        
        # Extract quote
        quote = {}
        if data and "Global Quote" in data:
            quote = data["Global Quote"]
        
        # Store in cache
        if quote:
            self._store_in_cache(cache_key, quote)
        
        return quote
    
    def get_bars(self, symbol: str, timeframe: str, limit: int = 100) -> pd.DataFrame:
        """
        Get price bars as DataFrame
        
        Args:
            symbol: Stock symbol
            timeframe: Time frame (1m, 5m, 15m, 30m, 1h, 1d, 1w, 1M)
            limit: Maximum number of bars to return
            
        Returns:
            DataFrame with price data
        """
        # Map timeframe to Alpha Vantage function and interval
        function = "TIME_SERIES_DAILY"
        interval = None
        
        if timeframe == "1d":
            function = "TIME_SERIES_DAILY"
        elif timeframe == "1w":
            function = "TIME_SERIES_WEEKLY"
        elif timeframe == "1M":
            function = "TIME_SERIES_MONTHLY"
        elif timeframe in ["1m", "5m", "15m", "30m", "60m"]:
            function = "TIME_SERIES_INTRADAY"
            interval = timeframe.replace("m", "min")
            if timeframe == "60m":
                interval = "60min"
        else:
            logger.warning(f"Unsupported timeframe: {timeframe}, using daily")
        
        # Prepare parameters
        params = {
            "function": function,
            "symbol": symbol,
            "outputsize": "compact"
        }
        
        if interval:
            params["interval"] = interval
        
        # Make API request
        data = self._make_api_request(params)
        if not data:
            return pd.DataFrame()
        
        # Extract time series data
        time_series_key = None
        for key in data.keys():
            if "Time Series" in key:
                time_series_key = key
                break
        
        if not time_series_key or time_series_key not in data:
            logger.warning(f"No time series data found for {symbol}")
            return pd.DataFrame()
        
        # Convert to DataFrame
        time_series = data[time_series_key]
        df = pd.DataFrame.from_dict(time_series, orient="index")
        
        # Parse column names
        df.columns = [col.split(". ")[1] if ". " in col else col for col in df.columns]
        
        # Convert types
        for col in df.columns:
            df[col] = pd.to_numeric(df[col])
        
        # Convert index to datetime
        df.index = pd.to_datetime(df.index)
        
        # Sort by date (newest first)
        df.sort_index(ascending=False, inplace=True)
        
        # Rename columns
        if "open" not in df.columns and "1. open" in df.columns:
            df.rename(columns={
                "1. open": "open",
                "2. high": "high",
                "3. low": "low",
                "4. close": "close",
                "5. volume": "volume"
            }, inplace=True)
        
        # Limit to requested number of bars
        return df.head(limit)
    
    def get_crypto_bars(self, symbol: str, timeframe: str, limit: int = 100) -> pd.DataFrame:
        """
        Get cryptocurrency bars as DataFrame
        
        Args:
            symbol: Cryptocurrency symbol (e.g., BTC)
            timeframe: Time frame (1d, 1w, 1M)
            limit: Maximum number of bars to return
            
        Returns:
            DataFrame with price data
        """
        # Extract currency from symbol format (e.g., BTC-USD)
        currency = symbol
        if "-" in symbol:
            currency = symbol.split("-")[0]
        
        # Map timeframe to Alpha Vantage function
        function = "DIGITAL_CURRENCY_DAILY"
        
        if timeframe == "1d":
            function = "DIGITAL_CURRENCY_DAILY"
        elif timeframe == "1w":
            function = "DIGITAL_CURRENCY_WEEKLY"
        elif timeframe == "1M":
            function = "DIGITAL_CURRENCY_MONTHLY"
        else:
            logger.warning(f"Unsupported timeframe for crypto: {timeframe}, using daily")
        
        # Get cryptocurrency data
        data = self.get_crypto_data(currency, "USD", function)
        if not data:
            return pd.DataFrame()
        
        # Extract time series data
        time_series_key = None
        for key in data.keys():
            if "Time Series" in key:
                time_series_key = key
                break
        
        if not time_series_key or time_series_key not in data:
            logger.warning(f"No time series data found for {symbol}")
            return pd.DataFrame()
        
        # Convert to DataFrame
        time_series = data[time_series_key]
        df = pd.DataFrame.from_dict(time_series, orient="index")
        
        # Extract USD columns
        usd_columns = [col for col in df.columns if "(USD)" in col]
        if not usd_columns:
            logger.warning(f"No USD data found for {symbol}")
            return pd.DataFrame()
        
        # Rename columns
        col_map = {}
        for col in usd_columns:
            if "open" in col.lower():
                col_map[col] = "open"
            elif "high" in col.lower():
                col_map[col] = "high"
            elif "low" in col.lower():
                col_map[col] = "low"
            elif "close" in col.lower():
                col_map[col] = "close"
            elif "volume" in col.lower():
                col_map[col] = "volume"
        
        # Select and rename columns
        df = df[list(col_map.keys())]
        df.rename(columns=col_map, inplace=True)
        
        # Convert types
        for col in df.columns:
            df[col] = pd.to_numeric(df[col])
        
        # Convert index to datetime
        df.index = pd.to_datetime(df.index)
        
        # Sort by date (newest first)
        df.sort_index(ascending=False, inplace=True)
        
        # Limit to requested number of bars
        return df.head(limit)
    
    def get_indicators(self, symbol: str, indicators: List[str], 
                      timeframe: str = "daily", periods: List[int] = [14]) -> pd.DataFrame:
        """
        Get multiple technical indicators for a symbol
        
        Args:
            symbol: Stock symbol
            indicators: List of indicators to fetch
            timeframe: Time interval
            periods: List of time periods to use
            
        Returns:
            DataFrame with indicator data
        """
        all_data = {}
        
        for indicator in indicators:
            for period in periods:
                # Get indicator data
                indicator_data = self.get_technical_indicator(symbol, indicator, timeframe, period)
                
                if not indicator_data or "Technical Analysis" not in indicator_data:
                    logger.warning(f"No data for {indicator} with period {period}")
                    continue
                
                # Extract the indicator data
                tech_data = indicator_data["Technical Analysis: " + indicator]
                
                # Convert to DataFrame
                df = pd.DataFrame.from_dict(tech_data, orient="index")
                
                # Rename columns to include period
                for col in df.columns:
                    df.rename(columns={col: f"{indicator.lower()}_{period}"}, inplace=True)
                
                # Convert index to datetime
                df.index = pd.to_datetime(df.index)
                
                # Store DataFrame
                all_data[f"{indicator}_{period}"] = df
        
        if not all_data:
            return pd.DataFrame()
        
        # Merge all DataFrames
        result = pd.DataFrame()
        for name, df in all_data.items():
            if result.empty:
                result = df
            else:
                result = result.join(df, how="outer")
        
        # Sort by date
        result.sort_index(ascending=False, inplace=True)
        
        return result

# For testing
if __name__ == "__main__":
    # Test configuration
    test_config = {
        "api_key": "YOUR_ALPHA_VANTAGE_API_KEY",
        "cache_duration": 300,
        "calls_per_minute": 5
    }
    
    # Create connector
    connector = AlphaVantageConnector(test_config)
    
    # Test stock data
    stock_data = connector.get_stock_data("AAPL", "TIME_SERIES_DAILY")
    if stock_data:
        print("Got stock data for AAPL")
    
    # Test forex data
    forex_data = connector.get_forex_data("EUR", "USD", "FX_DAILY")
    if forex_data:
        print("Got forex data for EUR/USD")
    
    # Test crypto data
    crypto_data = connector.get_crypto_data("BTC", "USD", "DIGITAL_CURRENCY_DAILY")
    if crypto_data:
        print("Got crypto data for BTC/USD")
    
    # Test indicator
    indicator_data = connector.get_technical_indicator("AAPL", "RSI", "daily", 14)
    if indicator_data:
        print("Got RSI indicator for AAPL")
    
    # Test search
    search_results = connector.search_symbols("MICROSOFT")
    if search_results:
        print(f"Found {len(search_results)} matches for 'MICROSOFT'")
    
    # Test quote
    quote = connector.get_quote("AAPL")
    if quote:
        print(f"AAPL quote: {quote}")
    
    # Test bars
    bars = connector.get_bars("AAPL", "1d", 10)
    print(f"Retrieved {len(bars)} bars for AAPL")
    print(bars) 