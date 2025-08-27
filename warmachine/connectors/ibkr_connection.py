#!/usr/bin/env python
"""
Quick IBKR Connection Test
"""

import os
import sys
import json
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def main():
    """Test connection to IBKR"""
    try:
        # Load configuration
        config_path = "config/warmachine_config.json"
        if not os.path.exists(config_path):
            logger.error(f"Configuration file not found: {config_path}")
            return False
        
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        # Get IBKR configuration
        ibkr_config = config.get("market_data", {}).get("providers", {}).get("ibkr", {})
        
        if not ibkr_config:
            logger.error("IBKR configuration not found in config file")
            return False
        
        logger.info(f"IBKR Configuration: {ibkr_config}")
        
        # Import IBKR connector
        try:
            from connectors.ibkr_connector import IBKRConnector
        except ImportError as e:
            logger.error(f"Failed to import IBKRConnector: {str(e)}")
            return False
        
        # Create connector
        logger.info("Creating IBKR connector...")
        connector = IBKRConnector(ibkr_config)
        
        # Connect to IBKR
        logger.info(f"Connecting to IBKR at {ibkr_config.get('host')}:{ibkr_config.get('port')}...")
        success = connector.connect()
        
        # Get connection status
        logger.info(f"Connection attempt result: {success}")
        logger.info(f"Connected: {connector.connected}")
        
        if connector.connected:
            logger.info("Successfully connected to IBKR!")
            
            # Get some basic market data to confirm connection works
            try:
                logger.info("Testing market data request...")
                test_symbol = "SPY"
                
                if hasattr(connector, "get_ticker_info"):
                    ticker_info = connector.get_ticker_info(test_symbol)
                    logger.info(f"Ticker info for {test_symbol}: {ticker_info}")
                
                if hasattr(connector, "get_market_price"):
                    market_price = connector.get_market_price(test_symbol)
                    logger.info(f"Market price for {test_symbol}: {market_price}")
                    
            except Exception as e:
                logger.error(f"Error getting market data: {str(e)}")
            
            # Disconnect
            logger.info("Disconnecting from IBKR...")
            connector.disconnect()
            logger.info(f"Disconnected: {not connector.connected}")
            
        else:
            logger.error("Failed to connect to IBKR")
            logger.info("Possible reasons:")
            logger.info("1. TWS or IB Gateway is not running")
            logger.info("2. API connection not enabled in TWS/Gateway settings")
            logger.info("3. Port number mismatch in configuration")
            logger.info("4. Socket permission issues")
            logger.info("5. Authentication/authorization issue")
            
        return connector.connected
        
    except Exception as e:
        logger.error(f"Error testing IBKR connection: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 