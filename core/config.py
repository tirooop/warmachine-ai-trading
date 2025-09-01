"""
Configuration management for WarMachine
"""

import os
import json
import logging
from typing import Dict, Any, Optional
from pathlib import Path
from pydantic import BaseModel, Field, validator
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class DatabaseConfig(BaseModel):
    """Database configuration"""
    host: str = Field(default="localhost")
    port: int = Field(default=5432)
    database: str = Field(default="warmachine")
    username: str = Field(default="postgres")
    password: str = Field(default="")
    pool_size: int = Field(default=10, ge=1, le=100)
    max_overflow: int = Field(default=20, ge=0, le=100)
    
    @validator('password', pre=True)
    def get_password_from_env(cls, v):
        return os.getenv('DB_PASSWORD', v)


class APIConfig(BaseModel):
    """API configuration"""
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000, ge=1024, le=65535)
    debug: bool = Field(default=False)
    workers: int = Field(default=1, ge=1, le=10)
    timeout: int = Field(default=30, ge=1, le=300)


class LoggingConfig(BaseModel):
    """Logging configuration"""
    level: str = Field(default="INFO")
    format: str = Field(default="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    file: str = Field(default="warmachine.log")
    max_size: int = Field(default=10485760, ge=1024*1024)  # 10MB
    backup_count: int = Field(default=5, ge=0, le=10)
    console_output: bool = Field(default=True)


class SecurityConfig(BaseModel):
    """Security configuration"""
    secret_key: str = Field(default="")
    algorithm: str = Field(default="HS256")
    access_token_expire_minutes: int = Field(default=30, ge=1, le=1440)
    refresh_token_expire_days: int = Field(default=7, ge=1, le=30)
    
    @validator('secret_key', pre=True)
    def get_secret_key_from_env(cls, v):
        return os.getenv('SECRET_KEY', v) or "your-secret-key-change-in-production"


class TelegramConfig(BaseModel):
    """Telegram bot configuration"""
    enabled: bool = Field(default=True)
    token: str = Field(default="")
    admin_chat_id: str = Field(default="")
    allowed_users: list = Field(default_factory=list)
    allowed_groups: list = Field(default_factory=list)
    admin_users: list = Field(default_factory=list)
    use_webhook: bool = Field(default=False)
    webhook_url: str = Field(default="")
    webhook_port: int = Field(default=8081, ge=1024, le=65535)
    debug: bool = Field(default=False)
    log_level: str = Field(default="INFO")
    rate_limit: Dict[str, Any] = Field(default_factory=dict)
    max_retries: int = Field(default=3, ge=1, le=10)
    retry_delay: float = Field(default=1.0, ge=0.1, le=60.0)
    command_prefix: str = Field(default="/")
    max_message_length: int = Field(default=4096, ge=1, le=4096)
    
    @validator('token', pre=True)
    def get_token_from_env(cls, v):
        return os.getenv('TELEGRAM_TOKEN', v)
    
    @validator('admin_chat_id', pre=True)
    def get_admin_chat_id_from_env(cls, v):
        return os.getenv('TELEGRAM_ADMIN_CHAT_ID', v)


class TradingConfig(BaseModel):
    """Trading configuration"""
    default_exchange: str = Field(default="UVX")
    symbols: Dict[str, Any] = Field(default_factory=dict)
    timeframes: list = Field(default_factory=list)
    indicators: Dict[str, list] = Field(default_factory=dict)
    default_timeframe: str = Field(default="1d")
    max_position_size: float = Field(default=0.1, ge=0.01, le=1.0)
    max_total_risk: float = Field(default=0.2, ge=0.01, le=1.0)
    stop_loss: float = Field(default=0.02, ge=0.001, le=0.5)
    take_profit: float = Field(default=0.05, ge=0.001, le=1.0)
    max_daily_trades: int = Field(default=50, ge=1, le=1000)
    max_open_positions: int = Field(default=10, ge=1, le=100)


class DataProviderConfig(BaseModel):
    """Data provider configuration"""
    polygon: Dict[str, Any] = Field(default_factory=dict)
    tradier: Dict[str, Any] = Field(default_factory=dict)
    binance: Dict[str, Any] = Field(default_factory=dict)
    ibkr: Dict[str, Any] = Field(default_factory=dict)
    databento: Dict[str, Any] = Field(default_factory=dict)
    google_finance: Dict[str, Any] = Field(default_factory=dict)
    alpha_vantage: Dict[str, Any] = Field(default_factory=dict)
    finnhub: Dict[str, Any] = Field(default_factory=dict)
    yahoo_finance: Dict[str, Any] = Field(default_factory=dict)


class AIConfig(BaseModel):
    """AI configuration"""
    provider: str = Field(default="deepseek")
    provider_priority: list = Field(default_factory=list)
    fallback_provider: str = Field(default="openai")
    api_key: str = Field(default="")
    base_url: str = Field(default="")
    model: str = Field(default="deepseek-ai/DeepSeek-V3")
    system_prompt: str = Field(default="")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=4000, ge=1, le=32000)
    retry_settings: Dict[str, Any] = Field(default_factory=dict)
    model_path: str = Field(default="models/deepseek-chat")
    device: str = Field(default="cuda")
    top_p: float = Field(default=0.9, ge=0.0, le=1.0)
    frequency_penalty: float = Field(default=0.0, ge=-2.0, le=2.0)
    presence_penalty: float = Field(default=0.0, ge=-2.0, le=2.0)
    
    @validator('api_key', pre=True)
    def get_api_key_from_env(cls, v):
        return os.getenv('AI_API_KEY', v)


class NotificationConfig(BaseModel):
    """Notification configuration"""
    discord: Dict[str, Any] = Field(default_factory=dict)
    feishu: Dict[str, Any] = Field(default_factory=dict)
    email: Dict[str, Any] = Field(default_factory=dict)


class PerformanceConfig(BaseModel):
    """Performance configuration"""
    connection_pool_size: int = Field(default=10, ge=1, le=100)
    cache_size: int = Field(default=1000, ge=100, le=10000)
    cache_ttl: int = Field(default=300, ge=60, le=3600)
    max_workers: int = Field(default=4, ge=1, le=20)
    queue_size: int = Field(default=1000, ge=100, le=10000)


class Config(BaseModel):
    """Main configuration class"""
    system: Dict[str, Any] = Field(default_factory=dict)
    telegram: TelegramConfig = Field(default_factory=TelegramConfig)
    trading: TradingConfig = Field(default_factory=TradingConfig)
    data_providers: DataProviderConfig = Field(default_factory=DataProviderConfig)
    ai: AIConfig = Field(default_factory=AIConfig)
    notifications: NotificationConfig = Field(default_factory=NotificationConfig)
    performance: PerformanceConfig = Field(default_factory=PerformanceConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    api: APIConfig = Field(default_factory=APIConfig)
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> "Config":
        """Create config from dictionary"""
        return cls(**config_dict)
    
    @classmethod
    def from_file(cls, config_path: str) -> "Config":
        """Load configuration from file"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_dict = json.load(f)
            return cls.from_dict(config_dict)
        except Exception as e:
            logger.error(f"Failed to load config from {config_path}: {e}")
            return cls()  # Return default config
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary"""
        return self.dict()
    
    def save_to_file(self, config_path: str) -> None:
        """Save configuration to file"""
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(self.to_dict(), f, indent=4, ensure_ascii=False)
            logger.info(f"Configuration saved to {config_path}")
        except Exception as e:
            logger.error(f"Failed to save config to {config_path}: {e}")
    
    def validate(self) -> bool:
        """Validate configuration"""
        try:
            # Validate required fields
            if not self.telegram.token and self.telegram.enabled:
                logger.warning("Telegram token not provided but Telegram is enabled")
            
            if not self.ai.api_key and self.ai.provider in ["deepseek", "openai"]:
                logger.warning("AI API key not provided")
            
            # Validate trading configuration
            if self.trading.max_position_size > self.trading.max_total_risk:
                logger.warning("Max position size should not exceed max total risk")
            
            return True
        except Exception as e:
            logger.error(f"Configuration validation failed: {e}")
            return False
    
    def get_api_key(self, provider: str) -> Optional[str]:
        """Get API key for specific provider"""
        env_key = f"{provider.upper()}_API_KEY"
        return os.getenv(env_key) or self.data_providers.dict().get(provider, {}).get("api_key", "")
    
    def is_provider_enabled(self, provider: str) -> bool:
        """Check if data provider is enabled"""
        provider_config = self.data_providers.dict().get(provider, {})
        return provider_config.get("enabled", False)


# Global configuration instance
_config: Optional[Config] = None


def get_config() -> Config:
    """Get global configuration instance"""
    global _config
    if _config is None:
        _config = Config.from_file("config.json")
        _config.validate()
    return _config


def set_config(config: Config) -> None:
    """Set global configuration instance"""
    global _config
    _config = config


def reload_config() -> Config:
    """Reload configuration from file"""
    global _config
    _config = Config.from_file("config.json")
    _config.validate()
    return _config 