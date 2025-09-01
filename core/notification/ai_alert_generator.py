"""


AI Alert Generator - Market Event Analysis and Notification





This module processes market alerts from the Market Watcher and uses AI to:


- Analyze the significance and potential impact of events


- Generate detailed explanations and trading recommendations


- Create notifications for multiple platforms (Telegram, Discord, etc.)


- Prioritize alerts based on importance and user preferences


"""





import os


import logging


import time


import json


import requests


import threading


from datetime import datetime, timedelta


from typing import Dict, List, Any, Optional, Tuple, Set


from ..ai_event_pool import AIEventPool, AIEvent, EventCategory, EventPriority


from ..shared_interfaces import NotificationProtocol


from ..abstractions.notifications import IAlertGenerator, IAlertFactory, AlertLevel





# Set up logging


logger = logging.getLogger(__name__)





class NotificationPriority:


    CRITICAL = 0


    HIGH = 1


    MEDIUM = 2


    LOW = 3


    INFO = 4





class NotificationChannel:


    EMAIL = "email"


    TELEGRAM = "telegram"


    DISCORD = "discord"


    WEBSOCKET = "websocket"


    WEBHOOK = "webhook"


    SMS = "sms"


    PUSH = "push"





class AIAlertGenerator(IAlertGenerator):


    """AI Alert Generator for processing market alerts and generating notifications"""


    


    def __init__(self, alert_factory: IAlertFactory):


        """


        Initialize the AI Alert Generator


        


        Args:


            alert_factory: Alert factory instance


        """


        self.alert_factory = alert_factory


        


        logger.info("AI Alert Generator initialized")


        


    def generate_alert(self, alert_type: str, data: Dict[str, Any], level: AlertLevel = AlertLevel.INFO) -> Optional[Dict[str, Any]]:


        """


        Generate an alert


        


        Args:


            alert_type: Alert type


            data: Alert data


            level: Alert level


            


        Returns:


            Alert data or None


        """


        try:


            alert = self.alert_factory.create_alert(alert_type, data, level)




            
            if alert:


                logger.info(f"Generated alert: {alert.get('type', alert_type)}")


                return alert


            else:


                logger.error(f"Failed to generate alert of type: {alert_type}")


                return None


            


        except Exception as e:


            logger.error(f"Error generating alert: {str(e)}")


            return None


            


    def generate_price_alert(self, symbol: str, price: float, change: float, threshold: float) -> Optional[Dict[str, Any]]:


        """Generate a price alert"""


        data = {'symbol': symbol, 'price': price, 'change': change, 'threshold': threshold}


        return self.generate_alert('price', data)
        




    def generate_volume_alert(self, symbol: str, volume: float, avg_volume: float, threshold: float) -> Optional[Dict[str, Any]]:


        """Generate a volume alert"""
            

        data = {'symbol': symbol, 'volume': volume, 'avg_volume': avg_volume, 'threshold': threshold}


        return self.generate_alert('volume', data)


        


    def generate_pattern_alert(self, symbol: str, pattern: str, confidence: float, timeframe: str) -> Optional[Dict[str, Any]]:


        """Generate a pattern alert"""


        data = {'symbol': symbol, 'pattern': pattern, 'confidence': confidence, 'timeframe': timeframe}


        return self.generate_alert('pattern', data)


        


    def generate_sentiment_alert(self, symbol: str, sentiment: str, score: float, sources: list) -> Optional[Dict[str, Any]]:


        """Generate a sentiment alert"""


        data = {'symbol': symbol, 'sentiment': sentiment, 'score': score, 'sources': sources}


        return self.generate_alert('sentiment', data)


            


# For testing


if __name__ == "__main__":


    # Load config


    with open("config/warmachine_config.json", "r") as f:


        config = json.load(f)


    


    # Create alert generator


    alert_generator = AIAlertGenerator(config)


    


    # Test alert


    async def test_alert():


        await alert_generator.generate_alert(


            title="Test Alert",


            message="This is a test alert",


            priority=NotificationPriority.HIGH,


            metadata={"symbol": "SPY", "price": 450.25}


        )


    


    # Run test


    asyncio.run(test_alert()) 