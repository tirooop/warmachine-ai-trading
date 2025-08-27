"""
AI告警工厂模块
"""
import logging
from typing import Dict, Any, Optional
from ..abstractions.notifications import IAlertFactory, IAlertSender, AlertLevel

logger = logging.getLogger(__name__)

class AIAlertFactory(IAlertFactory):
    """AI告警工厂类"""
    
    def __init__(self, notification_system: Optional[IAlertSender] = None):
        """初始化告警工厂
        
        Args:
            notification_system: 通知系统实例
        """
        self.notification_system = notification_system
        self._alert_templates = {
            'price': self._price_alert_template,
            'volume': self._volume_alert_template,
            'pattern': self._pattern_alert_template,
            'sentiment': self._sentiment_alert_template
        }
    
    def create_alert(self, alert_type: str, data: Dict[str, Any], level: AlertLevel = AlertLevel.INFO) -> Optional[Dict[str, Any]]:
        """创建告警
        
        Args:
            alert_type: 告警类型
            data: 告警数据
            level: 告警级别
            
        Returns:
            创建的告警数据
        """
        try:
            if alert_type not in self._alert_templates:
                logger.error(f"未知的告警类型: {alert_type}")
                return None
                
            template = self._alert_templates[alert_type]
            alert_data = template(data)
            
            if self.notification_system:
                message = self._format_alert_message(alert_data)
                self.notification_system.send_alert(message, level)
                
            return alert_data
            
        except Exception as e:
            logger.error(f"创建告警失败: {str(e)}")
            return None
    
    def _price_alert_template(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """价格告警模板"""
        return {
            'type': 'price',
            'symbol': data.get('symbol'),
            'price': data.get('price'),
            'change': data.get('change'),
            'threshold': data.get('threshold')
        }
    
    def _volume_alert_template(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """成交量告警模板"""
        return {
            'type': 'volume',
            'symbol': data.get('symbol'),
            'volume': data.get('volume'),
            'avg_volume': data.get('avg_volume'),
            'threshold': data.get('threshold')
        }
    
    def _pattern_alert_template(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """形态告警模板"""
        return {
            'type': 'pattern',
            'symbol': data.get('symbol'),
            'pattern': data.get('pattern'),
            'confidence': data.get('confidence'),
            'timeframe': data.get('timeframe')
        }
    
    def _sentiment_alert_template(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """情绪告警模板"""
        return {
            'type': 'sentiment',
            'symbol': data.get('symbol'),
            'sentiment': data.get('sentiment'),
            'score': data.get('score'),
            'sources': data.get('sources', [])
        }
    
    def _format_alert_message(self, alert_data: Dict[str, Any]) -> str:
        """格式化告警消息"""
        alert_type = alert_data['type']
        symbol = alert_data.get('symbol', 'Unknown')
        
        if alert_type == 'price':
            return f"价格告警: {symbol} 当前价格 {alert_data['price']}, 变化 {alert_data['change']}%"
        elif alert_type == 'volume':
            return f"成交量告警: {symbol} 当前成交量 {alert_data['volume']}, 平均成交量 {alert_data['avg_volume']}"
        elif alert_type == 'pattern':
            return f"形态告警: {symbol} 检测到 {alert_data['pattern']} 形态, 置信度 {alert_data['confidence']}%"
        elif alert_type == 'sentiment':
            return f"情绪告警: {symbol} 市场情绪 {alert_data['sentiment']}, 得分 {alert_data['score']}"
        else:
            return f"未知告警类型: {alert_type}" 