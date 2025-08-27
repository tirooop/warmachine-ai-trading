"""
Signal Analytics Engine Module
"""

from web_dashboard.signal_processing.signal_analytics import SignalAnalyticsEngine as WebSignalAnalyticsEngine

class SignalAnalyticsEngine:
    def __init__(self):
        self.engine = WebSignalAnalyticsEngine()
        pass

    def calculate_metrics(self, signals_df):
        """计算信号指标"""
        return self.engine.calculate_metrics(signals_df)

    def detect_abnormal_signals(self, signals_df):
        """检测异常信号"""
        return self.engine.detect_abnormal_signals(signals_df) 