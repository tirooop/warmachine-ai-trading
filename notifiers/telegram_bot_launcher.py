#!/usr/bin/env python


"""


WarMachine Telegram Bot Launcher - Standalone launcher for Telegram bot





This script allows running the Telegram bot component separately from the main WarMachine platform.


It also supports Telegram webhook integration.


"""





import os


import sys


import json


import logging


import asyncio


from quart import Quart, request, Response


import threading





# Ensure we can import from the warmachine module


sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))





# Import the TelegramBot class


from telegram_bot import TelegramBot





# Set up logging


logging.basicConfig(


    level=logging.INFO,


    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',


    handlers=[


        logging.FileHandler("logs/telegram_bot_launcher.log"),


        logging.StreamHandler()


    ]


)


logger = logging.getLogger(__name__)





# Ensure logs directory exists


os.makedirs("logs", exist_ok=True)





# Quart app for webhook handling


app = Quart(__name__)





def load_config():


    """Load configuration from file"""


    try:


        config_path = os.path.join("config", "warmachine_config.json")


        with open(config_path, "r") as f:


            return json.load(f)


    except Exception as e:


        logger.error(f"Failed to load configuration: {str(e)}")


        return {}





class StandaloneTelegramLauncher:


    """Standalone Launcher for Telegram Bot"""


    


    def __init__(self, config):


        """


        Initialize the Telegram bot launcher


        


        Args:


            config: Platform configuration dictionary


        """


        self.config = config


        self.telegram_config = config.get("telegram", {})


        self.token = self.telegram_config.get("token", "")


        self.webhook_port = self.telegram_config.get("webhook_port", 8081)


        self.webhook_url = self.telegram_config.get("webhook_url", "")


        self.use_webhook = self.telegram_config.get("use_webhook", False) and self.webhook_url


        


        # Initialize the Telegram bot


        self.bot = TelegramBot(config)


        


        # Set up webhook handler if enabled


        if self.use_webhook:


            self._setup_webhook_handler()


        


        logger.info("Telegram bot launcher initialized")


        


    def _setup_webhook_handler(self):


        """Set up webhook handler for Telegram"""


        


        @app.route('/telegram-webhook', methods=['POST'])


        async def telegram_webhook():


            """Handle Telegram webhook events"""


            try:


                # Get the update from Telegram


                update = await request.get_json()


                logger.info(f"Received Telegram update: {update.get('update_id')}")


                


                # Process the update


                # In a real implementation, this would be passed to the bot for processing


                


                return Response('', status=200)


            except Exception as e:


                logger.error(f"Error processing webhook: {str(e)}")


                return Response('Error processing webhook', status=500)





    async def set_webhook(self):


        """Set up the Telegram webhook"""


        if not self.use_webhook or not self.webhook_url:


            logger.warning("Webhook not configured, skipping webhook setup")


            return False


            


        import aiohttp


        


        webhook_setup_url = f"https://api.telegram.org/bot{self.token}/setWebhook?url={self.webhook_url}/telegram-webhook"


        


        try:


            async with aiohttp.ClientSession() as session:


                async with session.get(webhook_setup_url) as response:


                    result = await response.json()


                    


                    if result.get("ok"):


                        logger.info(f"Webhook setup successful: {self.webhook_url}/telegram-webhook")


                        return True


                    else:


                        logger.error(f"Webhook setup failed: {result}")


                        return False


        except Exception as e:


            logger.error(f"Error setting webhook: {str(e)}")


            return False


    


    async def delete_webhook(self):


        """Delete the Telegram webhook"""


        import aiohttp


        


        webhook_delete_url = f"https://api.telegram.org/bot{self.token}/deleteWebhook"


        


        try:


            async with aiohttp.ClientSession() as session:


                async with session.get(webhook_delete_url) as response:


                    result = await response.json()


                    


                    if result.get("ok"):


                        logger.info("Webhook deleted successfully")


                        return True


                    else:


                        logger.error(f"Webhook deletion failed: {result}")


                        return False


        except Exception as e:


            logger.error(f"Error deleting webhook: {str(e)}")


            return False


    


    async def start(self):


        """Start the Telegram bot"""


        # Set up webhook if enabled


        if self.use_webhook:


            await self.set_webhook()


            


            # Start webhook server


            def run_webhook_server():


                logger.info(f"Starting webhook server on port {self.webhook_port}...")


                app.run(host='0.0.0.0', port=self.webhook_port)


            


            webhook_thread = threading.Thread(target=run_webhook_server)


            webhook_thread.daemon = True


            webhook_thread.start()


        


        # Start the bot


        logger.info("Starting Telegram bot...")


        await self.bot.start()


    


    async def stop(self):


        """Stop the Telegram bot"""


        # Delete webhook if enabled


        if self.use_webhook:


            await self.delete_webhook()


        


        # Stop the bot


        logger.info("Stopping Telegram bot...")


        await self.bot.stop()





async def main():


    """Main function"""


    # Load configuration


    config = load_config()


    


    # Create launcher


    launcher = StandaloneTelegramLauncher(config)


    


    try:


        # Start launcher


        await launcher.start()


        


        # Keep the program running


        while True:


            await asyncio.sleep(1)


    except KeyboardInterrupt:


        logger.info("Keyboard interrupt received, shutting down...")


    finally:


        # Stop launcher


        await launcher.stop()





if __name__ == "__main__":


    # Run the main function


    asyncio.run(main()) 