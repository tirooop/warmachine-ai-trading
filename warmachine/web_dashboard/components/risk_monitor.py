"""
风险监控组件
实现风险指标的可视化和预警功能
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
from typing import Dict, List, Any
from datetime import datetime, timedelta

from ..config.frontend_config import AlertType, AlertUrgency, ALERT_CONFIGS

class RiskMonitor:
    """风险监控组件"""
    
    def __init__(self):
        """初始化风险监控器"""
        self.risk_data = {
            "timestamp": [],
            "metrics": {
                "var_95": [],  # 95% VaR
                "var_99": [],  # 99% VaR
                "expected_shortfall": [],
                "volatility": [],
                "beta": [],
                "correlation": []
            },
            "alerts": []
        }
        self.alert_thresholds = {
            "var_95": 0.02,  # 2%
            "var_99": 0.03,  # 3%
            "expected_shortfall": 0.025,  # 2.5%
            "volatility": 0.2,  # 20%
            "beta": 1.5,
            "correlation": 0.8
        }
        
    def render(self):
        """渲染风险监控界面"""
        st.title("风险监控")
        
        # 创建风险指标面板
        self._render_metrics()
        
        # 创建风险预警面板
        self._render_alerts()
        
        # 创建风险分析面板
        self._render_analysis()
        
    def _render_metrics(self):
        """渲染风险指标面板"""
        st.subheader("风险指标")
        
        # 创建风险指标图表
        metrics = self.risk_data["metrics"]
        
        # 创建折线图
        fig = go.Figure()
        
        for metric_name, values in metrics.items():
            fig.add_trace(go.Scatter(
                x=self.risk_data["timestamp"],
                y=values,
                name=metric_name,
                mode="lines+markers"
            ))
            
            # 添加阈值线
            if metric_name in self.alert_thresholds:
                threshold = self.alert_thresholds[metric_name]
                fig.add_hline(
                    y=threshold,
                    line_dash="dash",
                    line_color="red",
                    annotation_text=f"{metric_name} 阈值",
                    annotation_position="top right"
                )
                
        fig.update_layout(
            title="风险指标趋势",
            xaxis_title="时间",
            yaxis_title="指标值",
            showlegend=True
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
    def _render_alerts(self):
        """渲染风险预警面板"""
        st.subheader("风险预警")
        
        # 显示最近的预警
        if self.risk_data["alerts"]:
            for alert in self.risk_data["alerts"][-5:]:  # 显示最近5条预警
                st.warning(alert["message"])
                
        # 创建预警设置
        with st.expander("预警设置"):
            for metric_name, threshold in self.alert_thresholds.items():
                new_threshold = st.number_input(
                    f"{metric_name} 阈值",
                    value=threshold,
                    format="%.3f"
                )
                self.alert_thresholds[metric_name] = new_threshold
                
    def _render_analysis(self):
        """渲染风险分析面板"""
        st.subheader("风险分析")
        
        # 创建风险相关性热力图
        if len(self.risk_data["timestamp"]) > 1:
            metrics = self.risk_data["metrics"]
            correlation_matrix = pd.DataFrame(metrics).corr()
            
            fig = px.imshow(
                correlation_matrix,
                title="风险指标相关性",
                color_continuous_scale="RdBu"
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
        # 创建风险分布图
        if self.risk_data["metrics"]["var_95"]:
            fig = px.histogram(
                self.risk_data["metrics"]["var_95"],
                title="VaR分布",
                labels={"value": "VaR", "count": "频次"}
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
    def update_risk_data(self, metrics: Dict[str, float]):
        """更新风险数据"""
        timestamp = datetime.now()
        self.risk_data["timestamp"].append(timestamp)
        
        for metric_name, value in metrics.items():
            self.risk_data["metrics"][metric_name].append(value)
            
            # 检查是否需要触发预警
            if metric_name in self.alert_thresholds:
                threshold = self.alert_thresholds[metric_name]
                if value > threshold:
                    self._trigger_alert(metric_name, value, threshold)
                    
    def _trigger_alert(self, metric_name: str, value: float, threshold: float):
        """触发风险预警"""
        alert_config = ALERT_CONFIGS[AlertType.RISK]
        
        message = alert_config.template.format(
            message=f"{metric_name} 超过阈值: {value:.3f} > {threshold:.3f}"
        )
        
        self.risk_data["alerts"].append({
            "timestamp": datetime.now(),
            "type": AlertType.RISK,
            "urgency": AlertUrgency.HIGH,
            "message": message
        })
        
    def get_risk_data(self) -> Dict[str, Any]:
        """获取风险数据"""
        return self.risk_data.copy()
        
    def get_alert_thresholds(self) -> Dict[str, float]:
        """获取预警阈值"""
        return self.alert_thresholds.copy() 