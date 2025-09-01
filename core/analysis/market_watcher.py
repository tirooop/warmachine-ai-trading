"""


Market Watcher - Market Event and News Monitoring System





This module monitors market events, news, and economic data across multiple sources


to detect significant market events and generate trading signals.





Features:


- Multi-source market data monitoring


- Real-time news and social media analysis


- Economic data and earnings calendar tracking


- Pattern recognition and anomaly detection


"""





import os


import logging


import time


import json


import threading


import requests


from datetime import datetime, timedelta


from typing import Dict, List, Any, Optional, Tuple





# Set up logging


logger = logging.getLogger(__name__)





class MarketWatcher:


    """Market Watcher for monitoring market events and news"""


    


    def __init__(self, config: Dict[str, Any]):


        """


        Initialize the Market Watcher


        


        Args:


            config: Platform configuration dictionary


        """


        self.config = config


        self.market_config = config.get("market_data", {})


        self.running = False


        self.thread = None


        


        # Initialize monitoring targets


        self.symbols = self.market_config.get("symbols", [])


        self.news_sources = self.market_config.get("news_sources", ["reuters", "bloomberg", "wsj"])


        self.economic_calendars = self.market_config.get("economic_calendars", ["fomc", "earnings", "gdp"])


        


        # Event storage


        self.events = []


        self.news_items = []


        self.economic_data = []


        self.detected_patterns = []


        


        # Data storage paths


        self.data_path = "data/market/events"


        os.makedirs(self.data_path, exist_ok=True)


        


        # Alert signal path


        self.alert_path = "data/alerts"


        os.makedirs(self.alert_path, exist_ok=True)


        


        # Last check timestamps


        self.last_price_check = datetime.now()


        self.last_news_check = datetime.now()


        self.last_economic_check = datetime.now()


        self.last_pattern_check = datetime.now()


        


        logger.info("Market Watcher initialized")


        


    async def start(self):


        """Start market watching in non-blocking mode"""


        if not self.running:


            self.running = True


            self.thread = threading.Thread(


                target=self.run,


                daemon=True,


                name="MarketWatcherThread"


            )


            self.thread.start()


            logger.info("Market watcher started in background thread")


            return True


        return False


        


    def stop_thread(self):


        """Stop the background thread"""


        if self.thread and self.thread.is_alive():


            self.running = False


            self.thread.join(timeout=5.0)


            logger.info("Market watcher thread stopped")


            return True


        return False


        


    async def shutdown(self):


        """Gracefully shutdown the Market Watcher"""


        logger.info("Shutting down Market Watcher...")


        self.running = False


        if self.thread and self.thread.is_alive():


            self.thread.join(timeout=5.0)


        logger.info("Market Watcher shutdown complete")


        


    def run(self):


        """Start the Market Watcher's main processing loop"""


        self.running = True


        logger.info("Market Watcher started")


        


        try:


            while self.running:


                # Check prices and volume


                self._check_price_movements()


                


                # Check news and social media


                self._check_news()


                


                # Check economic data


                self._check_economic_data()


                


                # Check for technical patterns


                self._check_patterns()


                


                # Sleep to prevent excessive CPU usage


                time.sleep(60)  # Check every minute


                


        except Exception as e:


            logger.error(f"Market Watcher encountered an error: {str(e)}")


            self.running = False


            


        logger.info("Market Watcher stopped")


        


    def _check_price_movements(self):


        """Check for significant price movements"""


        try:


            # Only check every 5 minutes


            if (datetime.now() - self.last_price_check).total_seconds() < 300:


                return


                


            self.last_price_check = datetime.now()


            logger.debug("Checking price movements...")


            


            # In a real implementation, this would query market data APIs


            # For now, generate synthetic data for demonstration


            


            for symbol in self.symbols:


                # Randomly generate some price movement events (10% chance per symbol)


                import random


                if random.random() > 0.9:


                    # Generate a price event


                    change_percent = random.uniform(-8.0, 8.0)


                    


                    # Only report significant movements (>2%)


                    if abs(change_percent) > 2.0:


                        event = {


                            "timestamp": datetime.now().isoformat(),


                            "symbol": symbol,


                            "event_type": "price_movement",


                            "change_percent": change_percent,


                            "direction": "up" if change_percent > 0 else "down",


                            "volume_change": random.uniform(-50.0, 200.0),


                            "significance": min(1.0, abs(change_percent) / 10.0),


                            "description": f"{symbol} moved {change_percent:.2f}% on {random.randint(100, 500)}% normal volume"


                        }


                        


                        # Add to events list


                        self.events.append(event)


                        


                        # Keep list at reasonable size


                        if len(self.events) > 100:


                            self.events = self.events[-100:]


                            


                        # Write to disk


                        self._save_events()


                        


                        # Log the event


                        logger.info(f"Price movement detected: {symbol} {change_percent:.2f}%")


                        


                        # Check if we need to generate a signal


                        if abs(change_percent) > 5.0:


                            self._generate_alert(event)


            


        except Exception as e:


            logger.error(f"Price movement check failed: {str(e)}")


            


    def _check_news(self):


        """Check for market news and social media sentiment"""


        try:


            # Only check every 15 minutes


            if (datetime.now() - self.last_news_check).total_seconds() < 900:


                return


                


            self.last_news_check = datetime.now()


            logger.debug("Checking market news...")


            


            # In a real implementation, this would query news APIs


            # For now, generate synthetic data for demonstration


            


            # Randomly generate some news events (20% chance)


            import random


            if random.random() > 0.8:


                # Pick a random symbol and news source


                symbol = random.choice(self.symbols)


                source = random.choice(self.news_sources)


                


                # Generate a news item


                sentiment_value = random.uniform(-1.0, 1.0)


                sentiment = "positive" if sentiment_value > 0.3 else "negative" if sentiment_value < -0.3 else "neutral"


                


                # Generate headline and summary


                headlines = [


                    f"{symbol} Reports Quarterly Earnings",


                    f"{symbol} Announces New Product Line",


                    f"{symbol} CEO Steps Down",


                    f"{symbol} Faces Regulatory Investigation",


                    f"{symbol} Expands to New Markets",


                    f"Analysts Upgrade {symbol} Rating",


                    f"Analysts Downgrade {symbol} Rating",


                    f"{symbol} Announces Layoffs",


                    f"{symbol} Receives Acquisition Offer",


                    f"{symbol} Stock Splits Announced"


                ]


                


                headline = random.choice(headlines)


                


                news_item = {


                    "timestamp": datetime.now().isoformat(),


                    "symbol": symbol,


                    "headline": headline,


                    "source": source,


                    "sentiment": sentiment,


                    "sentiment_value": sentiment_value,


                    "importance": random.uniform(0.1, 1.0),


                    "url": f"https://example.com/news/{symbol.lower()}"


                }


                


                # Add to news list


                self.news_items.append(news_item)


                


                # Keep list at reasonable size


                if len(self.news_items) > 100:


                    self.news_items = self.news_items[-100:]


                    


                # Write to disk


                self._save_news()


                


                # Log the news


                logger.info(f"News detected: {headline} ({sentiment})")


                


                # Check if we need to generate a signal


                if abs(sentiment_value) > 0.7 and news_item["importance"] > 0.7:


                    event = {


                        "timestamp": datetime.now().isoformat(),


                        "symbol": symbol,


                        "event_type": "news",


                        "headline": headline,


                        "sentiment": sentiment,


                        "significance": news_item["importance"],


                        "description": f"{headline} ({source}) with {sentiment} sentiment"


                    }


                    self._generate_alert(event)


            


        except Exception as e:


            logger.error(f"News check failed: {str(e)}")


            


    def _check_economic_data(self):


        """Check for economic data releases and events"""


        try:


            # Only check every 30 minutes


            if (datetime.now() - self.last_economic_check).total_seconds() < 1800:


                return


                


            self.last_economic_check = datetime.now()


            logger.debug("Checking economic data...")


            


            # In a real implementation, this would query economic calendars


            # For now, generate synthetic data for demonstration


            


            # Randomly generate some economic events (10% chance)


            import random


            if random.random() > 0.9:


                # Pick a random economic event type


                event_types = [


                    "FOMC Meeting",


                    "Interest Rate Decision",


                    "GDP Release",


                    "NFP Report",


                    "CPI Data",


                    "PPI Data",


                    "Retail Sales",


                    "Unemployment Claims",


                    "Housing Starts",


                    "Consumer Confidence"


                ]


                


                event_type = random.choice(event_types)


                


                # Determine impacted markets


                impacted_markets = random.sample(self.symbols, min(3, len(self.symbols)))


                


                # Determine if it was a surprise


                surprise = random.choice([True, False])


                surprise_direction = random.choice(["above", "below"]) if surprise else "in-line"


                


                # Create economic event


                econ_event = {


                    "timestamp": datetime.now().isoformat(),


                    "event_type": event_type,


                    "impacted_markets": impacted_markets,


                    "surprise": surprise,


                    "surprise_direction": surprise_direction,


                    "importance": random.uniform(0.1, 1.0),


                    "description": f"{event_type} came in {surprise_direction} expectations"


                }


                


                # Add to economic data list


                self.economic_data.append(econ_event)


                


                # Keep list at reasonable size


                if len(self.economic_data) > 100:


                    self.economic_data = self.economic_data[-100:]


                    


                # Write to disk


                self._save_economic_data()


                


                # Log the event


                logger.info(f"Economic event: {event_type} ({surprise_direction} expectations)")


                


                # Check if we need to generate a signal


                if surprise and econ_event["importance"] > 0.7:


                    for symbol in impacted_markets:


                        event = {


                            "timestamp": datetime.now().isoformat(),


                            "symbol": symbol,


                            "event_type": "economic",


                            "economic_event": event_type,


                            "surprise_direction": surprise_direction,


                            "significance": econ_event["importance"],


                            "description": f"{event_type} {surprise_direction} expectations, impacting {symbol}"


                        }


                        self._generate_alert(event)


            


        except Exception as e:


            logger.error(f"Economic data check failed: {str(e)}")


            


    def _check_patterns(self):


        """Check for technical patterns in price data"""


        try:


            # Only check every 15 minutes


            if (datetime.now() - self.last_pattern_check).total_seconds() < 900:


                return


                


            self.last_pattern_check = datetime.now()


            logger.debug("Checking technical patterns...")


            


            # In a real implementation, this would analyze price data


            # For now, generate synthetic data for demonstration


            


            # Randomly generate some pattern detections (15% chance)


            import random


            if random.random() > 0.85:


                # Pick a random symbol


                symbol = random.choice(self.symbols)


                


                # Pick a random pattern


                patterns = [


                    "Double Top",


                    "Double Bottom",


                    "Head and Shoulders",


                    "Inverse Head and Shoulders",


                    "Bull Flag",


                    "Bear Flag",


                    "Triangle Breakout",


                    "Cup and Handle",


                    "Island Reversal",


                    "Gap Up",


                    "Gap Down"


                ]


                


                pattern = random.choice(patterns)


                


                # Determine if pattern is bullish or bearish


                bullish_patterns = ["Double Bottom", "Inverse Head and Shoulders", "Bull Flag", "Triangle Breakout", "Cup and Handle", "Gap Up"]


                bearish_patterns = ["Double Top", "Head and Shoulders", "Bear Flag", "Island Reversal", "Gap Down"]


                


                direction = "bullish" if pattern in bullish_patterns else "bearish"


                


                # Create pattern event


                pattern_event = {


                    "timestamp": datetime.now().isoformat(),


                    "symbol": symbol,


                    "pattern": pattern,


                    "direction": direction,


                    "confidence": random.uniform(0.5, 1.0),


                    "significance": random.uniform(0.1, 1.0),


                    "description": f"{pattern} pattern detected in {symbol}, suggesting {direction} movement"


                }


                


                # Add to patterns list


                self.detected_patterns.append(pattern_event)


                


                # Keep list at reasonable size


                if len(self.detected_patterns) > 100:


                    self.detected_patterns = self.detected_patterns[-100:]


                    


                # Write to disk


                self._save_patterns()


                


                # Log the pattern


                logger.info(f"Pattern detected: {pattern} in {symbol} ({direction})")


                


                # Check if we need to generate a signal


                if pattern_event["confidence"] > 0.7 and pattern_event["significance"] > 0.7:


                    event = {


                        "timestamp": datetime.now().isoformat(),


                        "symbol": symbol,


                        "event_type": "pattern",


                        "pattern": pattern,


                        "direction": direction,


                        "significance": pattern_event["significance"],


                        "description": pattern_event["description"]


                    }


                    self._generate_alert(event)


            


        except Exception as e:


            logger.error(f"Pattern check failed: {str(e)}")


            


    def _generate_alert(self, event: Dict[str, Any]):


        """Generate an alert for a significant market event"""


        try:


            # Create alert


            alert = {


                "timestamp": datetime.now().isoformat(),


                "event": event,


                "processed": False


            }


            


            # Write to alerts file


            alerts_file = os.path.join(self.alert_path, "market_alerts.json")


            


            alerts = []


            if os.path.exists(alerts_file):


                try:


                    with open(alerts_file, "r") as f:


                        alerts = json.load(f)


                except:


                    pass


                    


            alerts.append(alert)


            


            # Keep only the last 50 alerts


            if len(alerts) > 50:


                alerts = alerts[-50:]


                


            with open(alerts_file, "w") as f:


                json.dump(alerts, f, indent=2)


                


            logger.info(f"Generated alert: {event['event_type']} for {event['symbol']} - {event['description']}")


            


        except Exception as e:


            logger.error(f"Alert generation failed: {str(e)}")


            


    def _save_events(self):


        """Save market events to disk"""


        try:


            events_file = os.path.join(self.data_path, "price_events.json")


            


            with open(events_file, "w") as f:


                json.dump(self.events, f, indent=2)


                


        except Exception as e:


            logger.error(f"Failed to save events: {str(e)}")


            


    def _save_news(self):


        """Save news items to disk"""


        try:


            news_file = os.path.join(self.data_path, "news_items.json")


            


            with open(news_file, "w") as f:


                json.dump(self.news_items, f, indent=2)


                


        except Exception as e:


            logger.error(f"Failed to save news: {str(e)}")


            


    def _save_economic_data(self):


        """Save economic data to disk"""


        try:


            econ_file = os.path.join(self.data_path, "economic_events.json")


            


            with open(econ_file, "w") as f:


                json.dump(self.economic_data, f, indent=2)


                


        except Exception as e:


            logger.error(f"Failed to save economic data: {str(e)}")


            


    def _save_patterns(self):


        """Save technical patterns to disk"""


        try:


            patterns_file = os.path.join(self.data_path, "technical_patterns.json")


            


            with open(patterns_file, "w") as f:


                json.dump(self.detected_patterns, f, indent=2)


                


        except Exception as e:


            logger.error(f"Failed to save patterns: {str(e)}")


            


    def get_recent_events(self, event_type: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:


        """


        Get recent market events


        


        Args:


            event_type: Optional filter for event type


            limit: Maximum number of events to return


            


        Returns:


            List of event dictionaries


        """


        try:


            if event_type == "price":


                events = self.events


            elif event_type == "news":


                events = self.news_items


            elif event_type == "economic":


                events = self.economic_data


            elif event_type == "pattern":


                events = self.detected_patterns


            else:


                # Combine all events


                events = (


                    [dict(e, **{"category": "price"}) for e in self.events] +


                    [dict(e, **{"category": "news"}) for e in self.news_items] +


                    [dict(e, **{"category": "economic"}) for e in self.economic_data] +


                    [dict(e, **{"category": "pattern"}) for e in self.detected_patterns]


                )


                


                # Sort by timestamp (most recent first)


                events.sort(key=lambda x: x["timestamp"], reverse=True)


                


            # Return the most recent events


            return events[:limit]


            


        except Exception as e:


            logger.error(f"Failed to retrieve events: {str(e)}")


            return []


            


    def get_alerts(self, processed: bool = False, limit: int = 10) -> List[Dict[str, Any]]:


        """


        Get market alerts


        


        Args:


            processed: If True, return processed alerts; otherwise, unprocessed


            limit: Maximum number of alerts to return


            


        Returns:


            List of alert dictionaries


        """


        try:


            alerts_file = os.path.join(self.alert_path, "market_alerts.json")


            


            if not os.path.exists(alerts_file):


                return []


                


            with open(alerts_file, "r") as f:


                alerts = json.load(f)


                


            # Filter by processed status


            filtered_alerts = [a for a in alerts if a.get("processed", False) == processed]


            


            # Return the most recent alerts


            return filtered_alerts[:limit]


            


        except Exception as e:


            logger.error(f"Failed to retrieve alerts: {str(e)}")


            return []


            


    def mark_alert_processed(self, alert_timestamp: str):


        """


        Mark an alert as processed


        


        Args:


            alert_timestamp: Timestamp of the alert to mark as processed


        """


        try:


            alerts_file = os.path.join(self.alert_path, "market_alerts.json")


            


            if not os.path.exists(alerts_file):


                return


                


            with open(alerts_file, "r") as f:


                alerts = json.load(f)


                


            # Find the alert and mark it as processed


            for alert in alerts:


                if alert["timestamp"] == alert_timestamp:


                    alert["processed"] = True


                    


            # Write back to disk


            with open(alerts_file, "w") as f:


                json.dump(alerts, f, indent=2)


                


            logger.info(f"Marked alert as processed: {alert_timestamp}")


            


        except Exception as e:


            logger.error(f"Failed to mark alert as processed: {str(e)}") 