"""
Connectors Package

Contains various connectors for market data sources like IBKR, Polygon, Binance, etc.
"""

# Import connectors if available
try:
    from connectors.ibkr_connector import IBKRConnector
except ImportError:
    pass

try:
    from connectors.polygon_connector import PolygonConnector
except ImportError:
    pass

try:
    from connectors.binance_connector import BinanceConnector
except ImportError:
    pass

try:
    from connectors.alphavantage_connector import AlphaVantageConnector
except ImportError:
    pass

# Export ConnectorManager
from connectors.connector_manager import ConnectorManager

__all__ = [
    'IBKRConnector',
    'PolygonConnector',
    'BinanceConnector',
    'AlphaVantageConnector',
    'ConnectorManager'
] 