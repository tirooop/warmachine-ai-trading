"""
Custom exceptions for WarMachine
"""

from typing import Optional, Dict, Any


class WarMachineException(Exception):
    """Base exception for WarMachine"""
    
    def __init__(self, message: str, error_code: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}


class ConfigurationError(WarMachineException):
    """Configuration related errors"""
    pass


class DataProviderError(WarMachineException):
    """Data provider related errors"""
    pass


class TradingError(WarMachineException):
    """Trading related errors"""
    pass


class AIError(WarMachineException):
    """AI related errors"""
    pass


class ValidationError(WarMachineException):
    """Data validation errors"""
    pass


class ConnectionError(WarMachineException):
    """Connection related errors"""
    pass


class AuthenticationError(WarMachineException):
    """Authentication related errors"""
    pass


class RateLimitError(WarMachineException):
    """Rate limiting errors"""
    pass


class InsufficientFundsError(TradingError):
    """Insufficient funds for trading"""
    pass


class OrderNotFoundError(TradingError):
    """Order not found error"""
    pass


class InvalidOrderError(TradingError):
    """Invalid order parameters"""
    pass


class MarketDataError(DataProviderError):
    """Market data related errors"""
    pass


class DataNormalizationError(DataProviderError):
    """Data normalization errors"""
    pass


class StrategyError(WarMachineException):
    """Strategy related errors"""
    pass


class RiskManagementError(WarMachineException):
    """Risk management errors"""
    pass


class NotificationError(WarMachineException):
    """Notification related errors"""
    pass


class DatabaseError(WarMachineException):
    """Database related errors"""
    pass


class CacheError(WarMachineException):
    """Cache related errors"""
    pass


class WebhookError(WarMachineException):
    """Webhook related errors"""
    pass


class TelegramError(NotificationError):
    """Telegram specific errors"""
    pass


class DiscordError(NotificationError):
    """Discord specific errors"""
    pass


class EmailError(NotificationError):
    """Email specific errors"""
    pass


class FileError(WarMachineException):
    """File operation errors"""
    pass


class SerializationError(WarMachineException):
    """Data serialization errors"""
    pass


class TimeoutError(WarMachineException):
    """Timeout errors"""
    pass


class RetryableError(WarMachineException):
    """Errors that can be retried"""
    pass


class NonRetryableError(WarMachineException):
    """Errors that should not be retried"""
    pass


# Error code constants
class ErrorCodes:
    """Error code constants"""
    
    # Configuration errors
    CONFIG_MISSING = "CONFIG_MISSING"
    CONFIG_INVALID = "CONFIG_INVALID"
    CONFIG_NOT_FOUND = "CONFIG_NOT_FOUND"
    
    # Data provider errors
    PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"
    PROVIDER_TIMEOUT = "PROVIDER_TIMEOUT"
    PROVIDER_AUTH_FAILED = "PROVIDER_AUTH_FAILED"
    PROVIDER_RATE_LIMITED = "PROVIDER_RATE_LIMITED"
    PROVIDER_INVALID_RESPONSE = "PROVIDER_INVALID_RESPONSE"
    
    # Trading errors
    INSUFFICIENT_FUNDS = "INSUFFICIENT_FUNDS"
    ORDER_NOT_FOUND = "ORDER_NOT_FOUND"
    INVALID_ORDER = "INVALID_ORDER"
    ORDER_REJECTED = "ORDER_REJECTED"
    ORDER_CANCELLED = "ORDER_CANCELLED"
    POSITION_NOT_FOUND = "POSITION_NOT_FOUND"
    
    # AI errors
    AI_MODEL_UNAVAILABLE = "AI_MODEL_UNAVAILABLE"
    AI_INVALID_INPUT = "AI_INVALID_INPUT"
    AI_RESPONSE_ERROR = "AI_RESPONSE_ERROR"
    AI_TIMEOUT = "AI_TIMEOUT"
    
    # Validation errors
    VALIDATION_FAILED = "VALIDATION_FAILED"
    INVALID_DATA_TYPE = "INVALID_DATA_TYPE"
    MISSING_REQUIRED_FIELD = "MISSING_REQUIRED_FIELD"
    INVALID_VALUE = "INVALID_VALUE"
    
    # Connection errors
    CONNECTION_FAILED = "CONNECTION_FAILED"
    CONNECTION_TIMEOUT = "CONNECTION_TIMEOUT"
    CONNECTION_LOST = "CONNECTION_LOST"
    WEBSOCKET_ERROR = "WEBSOCKET_ERROR"
    
    # Authentication errors
    AUTH_FAILED = "AUTH_FAILED"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    INVALID_TOKEN = "INVALID_TOKEN"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    
    # Rate limiting errors
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    TOO_MANY_REQUESTS = "TOO_MANY_REQUESTS"
    
    # Database errors
    DB_CONNECTION_FAILED = "DB_CONNECTION_FAILED"
    DB_QUERY_FAILED = "DB_QUERY_FAILED"
    DB_TRANSACTION_FAILED = "DB_TRANSACTION_FAILED"
    DB_CONSTRAINT_VIOLATION = "DB_CONSTRAINT_VIOLATION"
    
    # Cache errors
    CACHE_MISS = "CACHE_MISS"
    CACHE_SET_FAILED = "CACHE_SET_FAILED"
    CACHE_DELETE_FAILED = "CACHE_DELETE_FAILED"
    
    # File errors
    FILE_NOT_FOUND = "FILE_NOT_FOUND"
    FILE_READ_ERROR = "FILE_READ_ERROR"
    FILE_WRITE_ERROR = "FILE_WRITE_ERROR"
    FILE_PERMISSION_DENIED = "FILE_PERMISSION_DENIED"
    
    # Serialization errors
    SERIALIZATION_FAILED = "SERIALIZATION_FAILED"
    DESERIALIZATION_FAILED = "DESERIALIZATION_FAILED"
    INVALID_JSON = "INVALID_JSON"
    
    # Strategy errors
    STRATEGY_NOT_FOUND = "STRATEGY_NOT_FOUND"
    STRATEGY_EXECUTION_FAILED = "STRATEGY_EXECUTION_FAILED"
    STRATEGY_VALIDATION_FAILED = "STRATEGY_VALIDATION_FAILED"
    
    # Risk management errors
    RISK_LIMIT_EXCEEDED = "RISK_LIMIT_EXCEEDED"
    POSITION_LIMIT_EXCEEDED = "POSITION_LIMIT_EXCEEDED"
    LOSS_LIMIT_EXCEEDED = "LOSS_LIMIT_EXCEEDED"
    
    # Notification errors
    NOTIFICATION_FAILED = "NOTIFICATION_FAILED"
    TELEGRAM_ERROR = "TELEGRAM_ERROR"
    DISCORD_ERROR = "DISCORD_ERROR"
    EMAIL_ERROR = "EMAIL_ERROR"
    
    # Webhook errors
    WEBHOOK_INVALID_SIGNATURE = "WEBHOOK_INVALID_SIGNATURE"
    WEBHOOK_TIMEOUT = "WEBHOOK_TIMEOUT"
    WEBHOOK_PROCESSING_FAILED = "WEBHOOK_PROCESSING_FAILED"


def is_retryable_error(error: Exception) -> bool:
    """Check if an error is retryable"""
    if isinstance(error, RetryableError):
        return True
    
    if isinstance(error, NonRetryableError):
        return False
    
    # Default retryable errors
    retryable_types = (
        ConnectionError,
        TimeoutError,
        RateLimitError,
        DataProviderError,
        AIError,
        NotificationError,
        WebhookError
    )
    
    return isinstance(error, retryable_types)


def get_error_code(error: Exception) -> str:
    """Get error code from exception"""
    if hasattr(error, 'error_code') and error.error_code:
        return error.error_code
    
    # Map exception types to error codes
    error_code_map = {
        ConfigurationError: ErrorCodes.CONFIG_INVALID,
        DataProviderError: ErrorCodes.PROVIDER_UNAVAILABLE,
        TradingError: ErrorCodes.ORDER_REJECTED,
        AIError: ErrorCodes.AI_RESPONSE_ERROR,
        ValidationError: ErrorCodes.VALIDATION_FAILED,
        ConnectionError: ErrorCodes.CONNECTION_FAILED,
        AuthenticationError: ErrorCodes.AUTH_FAILED,
        RateLimitError: ErrorCodes.RATE_LIMIT_EXCEEDED,
        InsufficientFundsError: ErrorCodes.INSUFFICIENT_FUNDS,
        OrderNotFoundError: ErrorCodes.ORDER_NOT_FOUND,
        InvalidOrderError: ErrorCodes.INVALID_ORDER,
        MarketDataError: ErrorCodes.PROVIDER_INVALID_RESPONSE,
        DataNormalizationError: ErrorCodes.VALIDATION_FAILED,
        StrategyError: ErrorCodes.STRATEGY_EXECUTION_FAILED,
        RiskManagementError: ErrorCodes.RISK_LIMIT_EXCEEDED,
        NotificationError: ErrorCodes.NOTIFICATION_FAILED,
        DatabaseError: ErrorCodes.DB_CONNECTION_FAILED,
        CacheError: ErrorCodes.CACHE_MISS,
        WebhookError: ErrorCodes.WEBHOOK_PROCESSING_FAILED,
        TelegramError: ErrorCodes.TELEGRAM_ERROR,
        DiscordError: ErrorCodes.DISCORD_ERROR,
        EmailError: ErrorCodes.EMAIL_ERROR,
        FileError: ErrorCodes.FILE_NOT_FOUND,
        SerializationError: ErrorCodes.SERIALIZATION_FAILED,
        TimeoutError: ErrorCodes.CONNECTION_TIMEOUT,
    }
    
    return error_code_map.get(type(error), "UNKNOWN_ERROR")


def format_error_message(error: Exception) -> str:
    """Format error message for logging"""
    error_code = get_error_code(error)
    error_type = type(error).__name__
    message = str(error)
    
    return f"[{error_code}] {error_type}: {message}"


def create_error_response(error: Exception) -> Dict[str, Any]:
    """Create standardized error response"""
    return {
        "error": True,
        "error_code": get_error_code(error),
        "error_type": type(error).__name__,
        "message": str(error),
        "details": getattr(error, 'details', {}),
        "retryable": is_retryable_error(error)
    } 