"""
Enhanced Liquidity Sniper

Analyzes real-time market data to detect liquidity imbalances and generate intelligence events.
This enhanced version uses real market data from IBKR, Polygon, and other sources via the DataHub.
"""

import os
import logging
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union, Callable
import pandas as pd
import numpy as np
import json

# Import system components
from datafeeds.market_data_hub import MarketDataHub
from core.data.market_data_hub import DataType, TimeFrame
from core.ai_event_pool import AIEventPool, AIEvent, EventCategory, EventPriority

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class EnhancedLiquiditySniper:
    """Enhanced liquidity sniper using real market data"""
    
    def __init__(self, config: Dict[str, Any], data_hub: MarketDataHub, event_pool: AIEventPool):
        """
        Initialize the enhanced liquidity sniper
        
        Args:
            config: Configuration dictionary
            data_hub: Market data hub for accessing market data
            event_pool: AI event pool for creating intelligence events
        """
        self.config = config
        self.data_hub = data_hub
        self.event_pool = event_pool
        
        # Monitoring settings
        self.watch_interval = config.get("watch_interval", 60)  # seconds
        self.symbols = config.get("symbols", ["SPY", "QQQ", "AAPL", "MSFT", "TSLA"])
        self.crypto_symbols = config.get("crypto_symbols", ["BTC-USD", "ETH-USD"])
        self.timeframes = config.get("timeframes", ["1m", "5m", "15m"])
        self.option_expiries = config.get("option_expiries", 3)  # Number of expiries to analyze
        self.imbalance_threshold = config.get("imbalance_threshold", 0.3)
        self.volume_threshold = config.get("volume_threshold", 1.5)  # Multiple of average volume
        self.option_iv_threshold = config.get("option_iv_threshold", 0.1)  # IV change threshold
        
        # Pools for data analysis
        self.order_book_cache = {}
        self.volume_history = {}
        self.price_history = {}
        self.option_chain_history = {}
        
        # Analysis results
        self.imbalance_history = {}
        self.whale_alerts = []
        self.option_alerts = []
        
        # Control flag
        self.running = True
        
        # Initialize data subscriptions
        self._initialize_data_subscriptions()
        
        # Start monitoring thread
        self.monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitor_thread.start()
        
        logger.info("Enhanced Liquidity Sniper initialized")
    
    def _initialize_data_subscriptions(self):
        """Set up data subscriptions for all watched symbols"""
        # Subscribe to order book data for equity symbols
        for symbol in self.symbols:
            self.data_hub.subscribe_market_data(
                symbol=symbol,
                data_type=DataType.ORDER_BOOK,
                callback=self._on_order_book_update
            )
            
            self.data_hub.subscribe_market_data(
                symbol=symbol,
                data_type=DataType.STOCK_TRADES,
                callback=self._on_trade_update
            )
            
            # Subscribe to option chain data
            self.data_hub.subscribe_market_data(
                symbol=symbol,
                data_type=DataType.OPTION_CHAIN,
                callback=self._on_option_chain_update
            )
        
        # Subscribe to order book data for crypto symbols
        for symbol in self.crypto_symbols:
            self.data_hub.subscribe_market_data(
                symbol=symbol,
                data_type=DataType.ORDER_BOOK,
                callback=self._on_order_book_update
            )
            
            self.data_hub.subscribe_market_data(
                symbol=symbol,
                data_type=DataType.CRYPTO_TRADES,
                callback=self._on_trade_update
            )
        
        logger.info(f"Subscribed to data for {len(self.symbols)} equity symbols and {len(self.crypto_symbols)} crypto symbols")
    
    def _on_order_book_update(self, data: Dict[str, Any]):
        """
        Handle order book updates
        
        Args:
            data: Order book data
        """
        if "symbol" not in data or "bids" not in data or "asks" not in data:
            return
        
        symbol = data["symbol"]
        bids = data.get("bids", [])
        asks = data.get("asks", [])
        timestamp = data.get("timestamp", datetime.now().isoformat())
        
        # Store in cache
        self.order_book_cache[symbol] = {
            "timestamp": timestamp,
            "bids": bids,
            "asks": asks
        }
        
        # Calculate imbalance in real-time
        imbalance = self._calculate_imbalance(bids, asks)
        
        # Store imbalance history
        if symbol not in self.imbalance_history:
            self.imbalance_history[symbol] = []
        
        self.imbalance_history[symbol].append({
            "timestamp": timestamp,
            "imbalance": imbalance
        })
        
        # Limit history size
        if len(self.imbalance_history[symbol]) > 100:
            self.imbalance_history[symbol] = self.imbalance_history[symbol][-100:]
        
        # Check for significant imbalance
        if abs(imbalance) > self.imbalance_threshold:
            self._check_significant_imbalance(symbol, imbalance, timestamp)
    
    def _on_trade_update(self, data: Dict[str, Any]):
        """
        Handle trade updates
        
        Args:
            data: Trade data
        """
        if "symbol" not in data or "price" not in data or "size" not in data:
            return
        
        symbol = data["symbol"]
        price = data.get("price", 0)
        size = data.get("size", 0)
        timestamp = data.get("timestamp", datetime.now().isoformat())
        
        # Initialize price history if needed
        if symbol not in self.price_history:
            self.price_history[symbol] = []
        
        # Initialize volume history if needed
        if symbol not in self.volume_history:
            self.volume_history[symbol] = []
        
        # Add to price history
        self.price_history[symbol].append({
            "timestamp": timestamp,
            "price": price
        })
        
        # Add to volume history
        self.volume_history[symbol].append({
            "timestamp": timestamp,
            "size": size
        })
        
        # Limit history size
        if len(self.price_history[symbol]) > 1000:
            self.price_history[symbol] = self.price_history[symbol][-1000:]
        
        if len(self.volume_history[symbol]) > 1000:
            self.volume_history[symbol] = self.volume_history[symbol][-1000:]
        
        # Check for whale trades
        self._check_whale_trade(symbol, price, size, timestamp)
    
    def _on_option_chain_update(self, data: Dict[str, Any]):
        """
        Handle option chain updates
        
        Args:
            data: Option chain data
        """
        if "symbol" not in data or "expirations" not in data:
            return
        
        symbol = data["symbol"]
        expirations = data.get("expirations", [])
        underlying_price = data.get("underlying_price", 0)
        timestamp = data.get("timestamp", datetime.now().isoformat())
        
        # Store in cache
        if symbol not in self.option_chain_history:
            self.option_chain_history[symbol] = []
        
        self.option_chain_history[symbol].append({
            "timestamp": timestamp,
            "underlying_price": underlying_price,
            "expirations": expirations
        })
        
        # Limit history size
        if len(self.option_chain_history[symbol]) > 10:
            self.option_chain_history[symbol] = self.option_chain_history[symbol][-10:]
        
        # Analyze option data if we have at least 2 data points
        if len(self.option_chain_history[symbol]) >= 2:
            self._analyze_option_chain(symbol)
    
    def _calculate_imbalance(self, bids: List[tuple], asks: List[tuple]) -> float:
        """
        Calculate order book imbalance
        
        Args:
            bids: List of (price, size) tuples for bids
            asks: List of (price, size) tuples for asks
            
        Returns:
            Imbalance score (-1 to 1, positive = buy pressure)
        """
        if not bids or not asks:
            return 0.0
        
        # Calculate bid and ask liquidity (price * size)
        bid_liquidity = sum(price * size for price, size in bids)
        ask_liquidity = sum(price * size for price, size in asks)
        
        # Calculate imbalance
        total_liquidity = bid_liquidity + ask_liquidity
        if total_liquidity == 0:
            return 0.0
        
        imbalance = (bid_liquidity - ask_liquidity) / total_liquidity
        return imbalance
    
    def _check_significant_imbalance(self, symbol: str, imbalance: float, timestamp: str):
        """
        Check if an imbalance is significant enough to generate an event
        
        Args:
            symbol: Trading symbol
            imbalance: Calculated imbalance
            timestamp: Event timestamp
        """
        # Get trend over recent history
        if symbol in self.imbalance_history and len(self.imbalance_history[symbol]) > 5:
            recent_imbalances = [entry["imbalance"] for entry in self.imbalance_history[symbol][-5:]]
            avg_imbalance = sum(recent_imbalances) / len(recent_imbalances)
            
            # Only report if imbalance is increasing in the same direction
            if (imbalance > 0 and avg_imbalance < imbalance) or (imbalance < 0 and avg_imbalance > imbalance):
                self._generate_imbalance_event(symbol, imbalance, timestamp)
    
    def _generate_imbalance_event(self, symbol: str, imbalance: float, timestamp: str):
        """
        Generate an intelligence event for a liquidity imbalance
        
        Args:
            symbol: Trading symbol
            imbalance: Calculated imbalance
            timestamp: Event timestamp
        """
        # Get relevant market data for analysis
        price_data = None
        try:
            # Get recent price data
            timeframe = "1m"
            if symbol in self.price_history and len(self.price_history[symbol]) > 0:
                recent_price = self.price_history[symbol][-1]["price"]
            else:
                # Try to get price from data hub
                price_df = self.data_hub.get_stock_data(symbol, TimeFrame.MINUTE_1, 1)
                if not price_df.empty:
                    recent_price = price_df.iloc[-1]["close"]
                else:
                    recent_price = 0
            
            # Direction and magnitude
            direction = "bullish" if imbalance > 0 else "bearish"
            magnitude = abs(imbalance)
            
            # Format content based on direction
            if imbalance > 0:
                title = f"{symbol} showing {magnitude:.2f} bullish liquidity imbalance"
                content = (
                    f"Significant buying pressure detected for {symbol}. Order book analysis reveals "
                    f"a {magnitude:.2f} bullish imbalance, indicating potential upward movement.\n\n"
                    f"Current price: ${recent_price:.2f}\n"
                    f"Order book: {len(self.order_book_cache.get(symbol, {}).get('bids', []))} bids vs "
                    f"{len(self.order_book_cache.get(symbol, {}).get('asks', []))} asks"
                )
            else:
                title = f"{symbol} showing {magnitude:.2f} bearish liquidity imbalance"
                content = (
                    f"Significant selling pressure detected for {symbol}. Order book analysis reveals "
                    f"a {magnitude:.2f} bearish imbalance, indicating potential downward movement.\n\n"
                    f"Current price: ${recent_price:.2f}\n"
                    f"Order book: {len(self.order_book_cache.get(symbol, {}).get('bids', []))} bids vs "
                    f"{len(self.order_book_cache.get(symbol, {}).get('asks', []))} asks"
                )
            
            # Determine priority based on magnitude
            priority = EventPriority.LOW
            if magnitude > 0.7:
                priority = EventPriority.HIGH
            elif magnitude > 0.4:
                priority = EventPriority.MEDIUM
            
            # Create event metadata
            metadata = {
                "imbalance_value": imbalance,
                "imbalance_direction": direction,
                "imbalance_magnitude": magnitude,
                "current_price": recent_price,
                "timestamp": timestamp
            }
            
            # Generate the event
            self.event_pool.create_liquidity_event(
                symbol=symbol,
                imbalance=imbalance,
                analysis=content,
                metadata=metadata
            )
            
            logger.info(f"Generated {direction} liquidity imbalance event for {symbol}: {magnitude:.2f}")
            
        except Exception as e:
            logger.error(f"Error generating imbalance event: {str(e)}")
    
    def _check_whale_trade(self, symbol: str, price: float, size: float, timestamp: str):
        """
        Check if a trade is a whale trade worth reporting
        
        Args:
            symbol: Trading symbol
            price: Trade price
            size: Trade size
            timestamp: Event timestamp
        """
        # Calculate trade value
        trade_value = price * size
        
        # Different thresholds for different assets
        is_crypto = symbol in self.crypto_symbols
        is_major_stock = symbol in ["SPY", "QQQ", "IWM", "DIA"]
        
        value_threshold = 500000  # Default $500k
        if is_crypto:
            value_threshold = 1000000  # $1M for crypto
        elif is_major_stock:
            value_threshold = 2000000  # $2M for major ETFs
        
        # Check average volume if we have history
        if symbol in self.volume_history and len(self.volume_history[symbol]) > 10:
            recent_volumes = [entry["size"] for entry in self.volume_history[symbol][-10:]]
            avg_volume = sum(recent_volumes) / len(recent_volumes)
            
            # If volume is significantly above average
            if size > avg_volume * self.volume_threshold and trade_value > value_threshold:
                self._generate_whale_alert(symbol, price, size, trade_value, timestamp)
        
        # Otherwise just use the value threshold
        elif trade_value > value_threshold * 2:  # Higher threshold if we don't have history
            self._generate_whale_alert(symbol, price, size, trade_value, timestamp)
    
    def _generate_whale_alert(self, symbol: str, price: float, size: float, value: float, timestamp: str):
        """
        Generate a whale alert intelligence event
        
        Args:
            symbol: Trading symbol
            price: Trade price
            size: Trade size
            value: Trade value
            timestamp: Event timestamp
        """
        try:
            # Determine if it's a buy or sell
            side = "unknown"
            if symbol in self.price_history and len(self.price_history[symbol]) > 1:
                prev_price = self.price_history[symbol][-2]["price"]
                if price > prev_price:
                    side = "buy"
                elif price < prev_price:
                    side = "sell"
            
            # If we still don't know, check order book
            if side == "unknown" and symbol in self.order_book_cache:
                book = self.order_book_cache[symbol]
                if book["bids"] and book["asks"]:
                    best_bid = book["bids"][0][0]
                    best_ask = book["asks"][0][0]
                    mid_price = (best_bid + best_ask) / 2
                    
                    if price >= mid_price:
                        side = "buy"
                    else:
                        side = "sell"
            
            # Format value for display
            formatted_value = f"${value:,.2f}"
            
            # Generate content based on side
            title = f"Whale Alert: {side.upper()} {symbol} {formatted_value}"
            content = (
                f"Large {side} detected for {symbol}. Transaction details:\n\n"
                f"Price: ${price:.2f}\n"
                f"Size: {size:,.0f}\n"
                f"Value: {formatted_value}\n\n"
            )
            
            # Add trend analysis if we have price history
            if symbol in self.price_history and len(self.price_history[symbol]) > 20:
                recent_prices = [entry["price"] for entry in self.price_history[symbol][-20:]]
                start_price = recent_prices[0]
                end_price = recent_prices[-1]
                price_change = (end_price - start_price) / start_price * 100
                
                content += f"Recent price trend: {price_change:.2f}% over the last 20 trades\n"
                
                if side == "buy" and price_change > 0:
                    content += "This whale is buying into strength, potentially accelerating the upward move."
                elif side == "buy" and price_change < 0:
                    content += "This whale is buying after a dip, potentially signaling a reversal."
                elif side == "sell" and price_change > 0:
                    content += "This whale is selling into strength, potentially taking profits."
                elif side == "sell" and price_change < 0:
                    content += "This whale is selling into weakness, potentially accelerating the downward move."
            
            # Determine priority based on value
            priority = EventPriority.MEDIUM
            if value > 5000000:
                priority = EventPriority.URGENT
            elif value > 1000000:
                priority = EventPriority.HIGH
            
            # Create metadata
            metadata = {
                "trade_side": side,
                "trade_value": value,
                "trade_size": size,
                "trade_price": price,
                "timestamp": timestamp
            }
            
            # Generate the event
            self.event_pool.create_whale_alert(
                symbol=symbol,
                side=side,
                value=value,
                analysis=content,
                exchange="real-time feed",
                metadata=metadata
            )
            
            # Add to local alert history
            self.whale_alerts.append({
                "symbol": symbol,
                "timestamp": timestamp,
                "side": side,
                "value": value
            })
            
            # Maintain history size
            if len(self.whale_alerts) > 100:
                self.whale_alerts = self.whale_alerts[-100:]
            
            logger.info(f"Generated whale alert for {symbol}: {side} {formatted_value}")
            
        except Exception as e:
            logger.error(f"Error generating whale alert: {str(e)}")
    
    def _analyze_option_chain(self, symbol: str):
        """
        Analyze option chain data for unusual activity
        
        Args:
            symbol: Underlying symbol
        """
        if symbol not in self.option_chain_history or len(self.option_chain_history[symbol]) < 2:
            return
        
        try:
            # Get current and previous chains
            current_chain = self.option_chain_history[symbol][-1]
            prev_chain = self.option_chain_history[symbol][-2]
            
            # Get underlying price
            current_price = current_chain["underlying_price"]
            prev_price = prev_chain["underlying_price"]
            price_change = ((current_price - prev_price) / prev_price) if prev_price else 0
            
            # Check each expiration (up to configured limit)
            expirations = current_chain["expirations"][:self.option_expiries]
            
            for exp_data in expirations:
                exp_date = exp_data["date"]
                
                # Find matching expiration in previous chain
                prev_exp_data = None
                for prev_exp in prev_chain["expirations"]:
                    if prev_exp["date"] == exp_date:
                        prev_exp_data = prev_exp
                        break
                
                if not prev_exp_data:
                    continue
                
                # Check each strike
                for opt_data in exp_data["options"]:
                    strike = opt_data["strike"]
                    
                    # Find matching strike in previous chain
                    prev_opt_data = None
                    for prev_opt in prev_exp_data["options"]:
                        if abs(prev_opt["strike"] - strike) < 0.01:
                            prev_opt_data = prev_opt
                            break
                    
                    if not prev_opt_data:
                        continue
                    
                    # Check for unusual volume or IV changes
                    call_data = opt_data["call"]
                    put_data = opt_data["put"]
                    prev_call_data = prev_opt_data["call"]
                    prev_put_data = prev_opt_data["put"]
                    
                    # Check call options
                    if call_data and prev_call_data:
                        call_volume = call_data.get("volume", 0)
                        prev_call_volume = prev_call_data.get("volume", 0)
                        call_oi = call_data.get("open_interest", 0)
                        
                        call_iv = call_data.get("iv", 0)
                        prev_call_iv = prev_call_data.get("iv", 0)
                        call_iv_change = call_iv - prev_call_iv
                        
                        # Unusual volume increase
                        if call_volume > 0 and prev_call_volume > 0:
                            vol_ratio = call_volume / prev_call_volume if prev_call_volume else 0
                            
                            if vol_ratio > 3 and call_volume > 100:
                                self._generate_option_alert(
                                    symbol=symbol,
                                    expiry=exp_date,
                                    strike=strike,
                                    option_type="call",
                                    alert_type="volume",
                                    values={
                                        "volume": call_volume,
                                        "prev_volume": prev_call_volume,
                                        "ratio": vol_ratio,
                                        "open_interest": call_oi
                                    }
                                )
                        
                        # Unusual IV change
                        if abs(call_iv_change) > self.option_iv_threshold:
                            self._generate_option_alert(
                                symbol=symbol,
                                expiry=exp_date,
                                strike=strike,
                                option_type="call",
                                alert_type="iv",
                                values={
                                    "iv": call_iv,
                                    "prev_iv": prev_call_iv,
                                    "change": call_iv_change
                                }
                            )
                    
                    # Check put options
                    if put_data and prev_put_data:
                        put_volume = put_data.get("volume", 0)
                        prev_put_volume = prev_put_data.get("volume", 0)
                        put_oi = put_data.get("open_interest", 0)
                        
                        put_iv = put_data.get("iv", 0)
                        prev_put_iv = prev_put_data.get("iv", 0)
                        put_iv_change = put_iv - prev_put_iv
                        
                        # Unusual volume increase
                        if put_volume > 0 and prev_put_volume > 0:
                            vol_ratio = put_volume / prev_put_volume if prev_put_volume else 0
                            
                            if vol_ratio > 3 and put_volume > 100:
                                self._generate_option_alert(
                                    symbol=symbol,
                                    expiry=exp_date,
                                    strike=strike,
                                    option_type="put",
                                    alert_type="volume",
                                    values={
                                        "volume": put_volume,
                                        "prev_volume": prev_put_volume,
                                        "ratio": vol_ratio,
                                        "open_interest": put_oi
                                    }
                                )
                        
                        # Unusual IV change
                        if abs(put_iv_change) > self.option_iv_threshold:
                            self._generate_option_alert(
                                symbol=symbol,
                                expiry=exp_date,
                                strike=strike,
                                option_type="put",
                                alert_type="iv",
                                values={
                                    "iv": put_iv,
                                    "prev_iv": prev_put_iv,
                                    "change": put_iv_change
                                }
                            )
            
        except Exception as e:
            logger.error(f"Error analyzing option chain for {symbol}: {str(e)}")
    
    def _generate_option_alert(self, symbol: str, expiry: str, strike: float, option_type: str, alert_type: str, values: Dict[str, Any]):
        """
        Generate an option alert intelligence event
        
        Args:
            symbol: Underlying symbol
            expiry: Option expiration date
            strike: Option strike price
            option_type: 'call' or 'put'
            alert_type: Type of alert ('volume', 'iv', etc.)
            values: Alert-specific values
        """
        try:
            current_chain = self.option_chain_history[symbol][-1]
            current_price = current_chain["underlying_price"]
            
            # Format the option contract for display
            option_contract = f"{symbol} {expiry} {strike} {option_type.upper()}"
            
            # Calculate moneyness
            moneyness = ""
            if option_type == "call":
                if strike < current_price * 0.95:
                    moneyness = "deep ITM"
                elif strike < current_price:
                    moneyness = "ITM"
                elif strike == current_price:
                    moneyness = "ATM"
                elif strike < current_price * 1.05:
                    moneyness = "near OTM"
                else:
                    moneyness = "OTM"
            else:  # put
                if strike > current_price * 1.05:
                    moneyness = "deep ITM"
                elif strike > current_price:
                    moneyness = "ITM"
                elif strike == current_price:
                    moneyness = "ATM"
                elif strike > current_price * 0.95:
                    moneyness = "near OTM"
                else:
                    moneyness = "OTM"
            
            # Generate title and content based on alert type
            if alert_type == "volume":
                volume = values.get("volume", 0)
                prev_volume = values.get("prev_volume", 0)
                ratio = values.get("ratio", 0)
                oi = values.get("open_interest", 0)
                
                title = f"Option Volume Alert: {option_contract}"
                content = (
                    f"Unusual volume detected in {option_contract} ({moneyness}).\n\n"
                    f"Volume: {volume:,.0f} (up {ratio:.1f}x)\n"
                    f"Previous Volume: {prev_volume:,.0f}\n"
                    f"Open Interest: {oi:,.0f}\n"
                    f"Underlying Price: ${current_price:.2f}\n\n"
                )
                
                # Add analysis
                if option_type == "call":
                    content += "Increased call volume may indicate bullish sentiment or hedging of short positions."
                else:
                    content += "Increased put volume may indicate bearish sentiment or protective hedging."
                
            elif alert_type == "iv":
                iv = values.get("iv", 0)
                prev_iv = values.get("prev_iv", 0)
                change = values.get("change", 0)
                
                title = f"Option IV Alert: {option_contract}"
                content = (
                    f"Unusual implied volatility change detected in {option_contract} ({moneyness}).\n\n"
                    f"Current IV: {iv:.2f}\n"
                    f"Previous IV: {prev_iv:.2f}\n"
                    f"Change: {change:+.2f} ({(change/prev_iv)*100 if prev_iv else 0:+.1f}%)\n"
                    f"Underlying Price: ${current_price:.2f}\n\n"
                )
                
                # Add analysis
                if change > 0:
                    content += "Rising IV suggests increasing uncertainty or anticipation of a move."
                else:
                    content += "Falling IV suggests decreasing uncertainty or post-event normalization."
            
            # Determine priority
            priority = EventPriority.MEDIUM
            if (alert_type == "volume" and values.get("ratio", 0) > 5) or (alert_type == "iv" and abs(values.get("change", 0)) > 0.2):
                priority = EventPriority.HIGH
            
            # Create metadata
            metadata = {
                "option_contract": option_contract,
                "expiry": expiry,
                "strike": strike,
                "option_type": option_type,
                "alert_type": alert_type,
                "moneyness": moneyness,
                "underlying_price": current_price,
                "values": values
            }
            
            # Generate event
            event_id = self.event_pool.create_ai_insight(
                symbol=symbol,
                title=title,
                analysis=content,
                priority=priority,
                metadata=metadata
            )
            
            # Add to local alert history
            self.option_alerts.append({
                "symbol": symbol,
                "timestamp": datetime.now().isoformat(),
                "option_contract": option_contract,
                "alert_type": alert_type,
                "event_id": event_id
            })
            
            # Maintain history size
            if len(self.option_alerts) > 100:
                self.option_alerts = self.option_alerts[-100:]
            
            logger.info(f"Generated option {alert_type} alert for {option_contract}")
            
        except Exception as e:
            logger.error(f"Error generating option alert: {str(e)}")
    
    def _monitoring_loop(self):
        """Background thread that performs periodic data analysis"""
        while self.running:
            try:
                # Analyze all tracked symbols
                for symbol in self.symbols + self.crypto_symbols:
                    # Perform any periodic analysis that isn't triggered by real-time events
                    self._perform_periodic_analysis(symbol)
                
                # Generate summary report every hour
                if datetime.now().minute == 0:
                    self._generate_market_summary()
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {str(e)}")
            
            # Sleep until next check
            time.sleep(self.watch_interval)
    
    def _perform_periodic_analysis(self, symbol: str):
        """
        Perform periodic analysis on a symbol
        
        Args:
            symbol: Trading symbol
        """
        # This method can be expanded to include additional periodic analyses
        pass
    
    def _generate_market_summary(self):
        """Generate a market summary intelligence event"""
        try:
            # Collect market data for major symbols
            market_data = {}
            for symbol in ["SPY", "QQQ", "DIA"]:
                if symbol in self.symbols:
                    # Get latest price
                    price_df = self.data_hub.get_stock_data(symbol, TimeFrame.MINUTE_1, 1)
                    if not price_df.empty:
                        current_price = price_df.iloc[-1]["close"]
                        
                        # Get daily change
                        daily_df = self.data_hub.get_stock_data(symbol, TimeFrame.DAY_1, 2)
                        if len(daily_df) >= 2:
                            prev_close = daily_df.iloc[-2]["close"]
                            daily_change = (current_price - prev_close) / prev_close * 100
                        else:
                            daily_change = 0
                        
                        market_data[symbol] = {
                            "price": current_price,
                            "daily_change": daily_change
                        }
            
            # Count alerts by type
            imbalance_count = sum(1 for s in self.imbalance_history.values() if len(s) > 0)
            whale_count = len(self.whale_alerts)
            option_count = len(self.option_alerts)
            
            # Generate summary
            title = "Market Intelligence Summary"
            content = f"Market Overview ({datetime.now().strftime('%Y-%m-%d %H:%M')}):\n\n"
            
            # Add market data
            for symbol, data in market_data.items():
                content += f"{symbol}: ${data['price']:.2f} ({data['daily_change']:+.2f}%)\n"
            
            content += f"\nRecent Activity:\n"
            content += f"• {imbalance_count} liquidity imbalance alerts\n"
            content += f"• {whale_count} whale transaction alerts\n"
            content += f"• {option_count} unusual option activity alerts\n\n"
            
            # Add recent significant events
            if self.whale_alerts:
                content += "Significant Whale Activity:\n"
                for alert in sorted(self.whale_alerts[-3:], key=lambda x: x.get("value", 0), reverse=True):
                    value = alert.get("value", 0)
                    content += f"• {alert.get('symbol')}: {alert.get('side').upper()} ${value:,.2f}\n"
            
            # Create metadata
            metadata = {
                "market_data": market_data,
                "alert_counts": {
                    "imbalance": imbalance_count,
                    "whale": whale_count,
                    "option": option_count
                }
            }
            
            # Generate event
            self.event_pool.create_ai_insight(
                symbol="MARKET",
                title=title,
                analysis=content,
                priority=EventPriority.MEDIUM,
                metadata=metadata
            )
            
            logger.info("Generated market intelligence summary")
            
        except Exception as e:
            logger.error(f"Error generating market summary: {str(e)}")
    
    def stop(self):
        """Stop the liquidity sniper monitoring"""
        self.running = False
        logger.info("Enhanced Liquidity Sniper stopped")

# For testing
if __name__ == "__main__":
    # Load config
    with open("config/warmachine_config.json", "r") as f:
        config = json.load(f)
    
    # Create components
    from datafeeds.market_data_hub import MarketDataHub
    from core.ai_event_pool import AIEventPool
    
    data_hub = MarketDataHub(config.get("market_data", {}))
    event_pool = AIEventPool(config.get("event_pool", {}))
    
    # Create enhanced liquidity sniper
    sniper_config = config.get("liquidity_sniper", {})
    sniper = EnhancedLiquiditySniper(sniper_config, data_hub, event_pool)
    
    # Run for a while
    try:
        print("Enhanced Liquidity Sniper running. Press Ctrl+C to stop.")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        sniper.stop()
        print("Stopped.") 