#!/usr/bin/env python
"""
Run Discord Bot - Standalone script to run only the Discord bot component
"""

import os
import sys
import json
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/discord_bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def load_config():
    """Load configuration from file"""
    try:
        config_path = os.path.join("config", "warmachine_config.json")
        with open(config_path, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load configuration: {str(e)}")
        return {}

def main():
    """Main function"""
    # Ensure logs directory exists
    os.makedirs("logs", exist_ok=True)
    
    # Load configuration
    config = load_config()
    
    # Import the DiscordBot class
    try:
        from utils.discord_bot import DiscordBot
        
        # Create and run the bot
        bot = DiscordBot(config)
        bot.run()
        
    except Exception as e:
        logger.error(f"Failed to run Discord bot: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 