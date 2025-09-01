"""
WarMachine AI Trading System - Main Entry Point
"""

import logging
import json
import os
import sys
import traceback
import asyncio
import signal
from pathlib import Path
from typing import Dict, Any

from tg_bot.super_commander import SuperCommander
from core.config import Config
from utils.logging import setup_logging

def load_config(config_path: str = "config.json") -> Dict[str, Any]:
    """Load configuration from file
    
    Args:
        config_path: Path to configuration file
        
    Returns:
        Dict containing configuration
    """
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found at: {config_path}")
        
    with open(config_path, "r", encoding='utf-8') as f:
        return json.load(f)

async def async_main():
    """Async main entry point for WarMachine AI Trading System"""
    # Setup logging
    logger = setup_logging()
    commander = None
    
    try:
        # Load configuration
        logger.info("Loading configuration...")
        config_dict = load_config()
        config = Config.from_dict(config_dict)
        
        # Initialize and start Super Commander
        logger.info("Initializing Super Commander...")
        commander = SuperCommander(config_dict)
        
        # Start system
        logger.info("Starting WarMachine AI Trading System...")
        
        # Create a task for the commander
        commander_task = asyncio.create_task(commander.start())
        
        # Wait for the task to complete
        await commander_task
        
    except KeyboardInterrupt:
        logger.info("System shutdown by user")
    except Exception as e:
        logger.error(f"System error: {str(e)}")
        logger.error("Full traceback:")
        logger.error(traceback.format_exc())
        raise
    finally:
        # Ensure proper cleanup
        if commander is not None:
            try:
                await commander.stop()
            except Exception as e:
                logger.error(f"Error during cleanup: {str(e)}")

def main():
    """Main entry point for WarMachine AI Trading System"""
    try:
        # Run the async main function
        asyncio.run(async_main())
    except KeyboardInterrupt:
        print("\nSystem shutdown by user")
    except Exception as e:
        print(f"System error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 