"""
通知系统的抽象接口定义
"""
from typing import Protocol, Dict, Any, Optional
from enum import Enum
from abc import ABC, abstractmethod

class AlertLevel(Enum):
    """告警级别"""
    INFO = 0
    WARNING = 1
    ERROR = 2
    CRITICAL = 3

class IAlertGenerator(Protocol):
    """告警生成器接口"""
    def generate_alert(self, alert_type: str, data: Dict[str, Any], level: AlertLevel = AlertLevel.INFO) -> Dict[str, Any]:
        """生成告警"""
        ...

class IAlertSender(ABC):
    """Interface for sending alerts"""
    
    @abstractmethod
    def send_alert(self, message: str, metadata: Dict[str, Any] = None):
        """Send an alert message"""
        pass
    
    @abstractmethod
    def send_trade_alert(self, trade_data: Dict[str, Any]):
        """Send a trade-specific alert"""
        pass

class IAlertFactory(Protocol):
    """告警工厂接口"""
    def create_alert(self, alert_type: str, data: Dict[str, Any], level: AlertLevel = AlertLevel.INFO) -> Optional[Dict[str, Any]]:
        """创建告警"""
        ...

class INotificationSystem(Protocol):
    """通知系统接口"""
    def send_notification(self, message: str, level: AlertLevel = AlertLevel.INFO) -> bool:
        """发送通知"""
        ...
    
    def register_handler(self, handler: IAlertSender) -> None:
        """注册告警处理器"""
        ... 