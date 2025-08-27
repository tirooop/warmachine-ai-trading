"""
前端配置文件
定义了前端相关的常量和配置项
"""

from enum import Enum
from typing import Dict, List, Any
from dataclasses import dataclass

class AlertType(Enum):
    """警报类型枚举"""
    RISK = "risk"
    TRAINING = "training"
    SYSTEM = "system"

class AlertUrgency(Enum):
    """警报紧急程度枚举"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3

@dataclass
class AlertConfig:
    """警报配置"""
    type: AlertType
    urgency: AlertUrgency
    channels: List[str]
    template: str
    cooldown: int  # 冷却时间（秒）

@dataclass
class WebAppConfig:
    """Web应用配置"""
    title: str
    theme: Dict[str, Any]
    features: List[str]
    api_endpoints: Dict[str, str]

# 警报配置
ALERT_CONFIGS = {
    AlertType.RISK: AlertConfig(
        type=AlertType.RISK,
        urgency=AlertUrgency.HIGH,
        channels=["telegram", "web", "email"],
        template="🚨 风险预警: {message}",
        cooldown=300
    ),
    AlertType.TRAINING: AlertConfig(
        type=AlertType.TRAINING,
        urgency=AlertUrgency.MEDIUM,
        channels=["telegram", "web"],
        template="🤖 训练状态: {message}",
        cooldown=60
    ),
    AlertType.SYSTEM: AlertConfig(
        type=AlertType.SYSTEM,
        urgency=AlertUrgency.LOW,
        channels=["web"],
        template="🛠 系统通知: {message}",
        cooldown=0
    )
}

# Web应用配置
WEB_APP_CONFIG = WebAppConfig(
    title="策略进化系统控制台",
    theme={
        "primary": "#1976d2",
        "secondary": "#dc004e",
        "background": "#f5f5f5",
        "text": "#333333"
    },
    features=[
        "gene_editor",
        "training_monitor",
        "risk_dashboard",
        "performance_visualization",
        "report_generator"
    ],
    api_endpoints={
        "gene_editor": "/api/v1/genes",
        "training": "/api/v1/training",
        "risk": "/api/v1/risk",
        "performance": "/api/v1/performance",
        "reports": "/api/v1/reports"
    }
)

# 权限配置
PERMISSIONS = {
    "trader": {
        "access": ["view", "execute"],
        "commands": ["status", "pause"]
    },
    "quant": {
        "access": ["edit_genes", "backtest"],
        "commands": ["adjust", "analyze"]
    },
    "admin": {
        "access": ["all"],
        "commands": ["all"]
    }
}

# 移动端配置
MOBILE_CONFIG = {
    "pwa": {
        "name": "策略进化系统",
        "short_name": "策略系统",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#ffffff",
        "theme_color": "#1976d2",
        "icons": [
            {
                "src": "/icons/icon-192x192.png",
                "sizes": "192x192",
                "type": "image/png"
            },
            {
                "src": "/icons/icon-512x512.png",
                "sizes": "512x512",
                "type": "image/png"
            }
        ]
    },
    "offline_cache": [
        "/gene-editor",
        "/alerts",
        "/static/js/main.js",
        "/static/css/main.css"
    ]
}

# 可视化配置
VISUALIZATION_CONFIG = {
    "gene_editor": {
        "radar_chart": {
            "max_value": 100,
            "width": 600,
            "height": 400
        },
        "heatmap": {
            "colors": "Viridis",
            "cell_size": 50
        }
    },
    "performance": {
        "3d_view": {
            "width": 800,
            "height": 600,
            "camera_position": [0, 0, 5],
            "light_position": [1, 1, 1]
        }
    }
} 