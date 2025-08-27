"""
测试导入
"""

def test_imports():
    """测试所有必要的导入"""
    try:
        from web_dashboard.app import WebApp
        from web_dashboard.components import GeneEditor, TrainingMonitor, RiskMonitor
        from web_dashboard.config import (
            AlertType,
            AlertUrgency,
            WebAppConfig,
            ALERT_CONFIGS,
            WEB_APP_CONFIG
        )
        print("✅ 所有导入成功！")
        return True
    except Exception as e:
        print(f"❌ 导入失败: {str(e)}")
        return False

if __name__ == "__main__":
    test_imports() 