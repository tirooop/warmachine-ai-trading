"""
训练监控组件
实现训练过程的可视化和控制功能
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
from typing import Dict, List, Any
from datetime import datetime, timedelta

class TrainingMonitor:
    """训练监控组件"""
    
    def __init__(self):
        """初始化训练监控器"""
        self.training_data = {
            "fitness": [],
            "generation": [],
            "timestamp": [],
            "metrics": {
                "sharpe_ratio": [],
                "sortino_ratio": [],
                "max_drawdown": [],
                "win_rate": [],
                "profit_factor": []
            }
        }
        self.is_training = False
        self.current_generation = 0
        
    def render(self):
        """渲染训练监控界面"""
        st.title("训练监控")
        
        # 创建控制面板
        self._render_controls()
        
        # 创建训练状态面板
        self._render_status()
        
        # 创建性能指标面板
        self._render_metrics()
        
        # 创建训练进度面板
        self._render_progress()
        
    def _render_controls(self):
        """渲染控制面板"""
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("开始训练", disabled=self.is_training):
                self._start_training()
                
        with col2:
            if st.button("暂停训练", disabled=not self.is_training):
                self._pause_training()
                
        with col3:
            if st.button("重置训练", disabled=self.is_training):
                self._reset_training()
                
    def _render_status(self):
        """渲染训练状态面板"""
        st.subheader("训练状态")
        
        # 创建状态卡片
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                "当前代数",
                self.current_generation,
                delta=None
            )
            
        with col2:
            status = "训练中" if self.is_training else "已暂停"
            st.metric(
                "训练状态",
                status,
                delta=None
            )
            
        with col3:
            if self.training_data["fitness"]:
                best_fitness = max(self.training_data["fitness"])
                st.metric(
                    "最佳适应度",
                    f"{best_fitness:.2f}",
                    delta=None
                )
                
    def _render_metrics(self):
        """渲染性能指标面板"""
        st.subheader("性能指标")
        
        # 创建性能指标图表
        metrics = self.training_data["metrics"]
        
        # 创建折线图
        fig = go.Figure()
        
        for metric_name, values in metrics.items():
            fig.add_trace(go.Scatter(
                x=self.training_data["generation"],
                y=values,
                name=metric_name,
                mode="lines+markers"
            ))
            
        fig.update_layout(
            title="性能指标趋势",
            xaxis_title="代数",
            yaxis_title="指标值",
            showlegend=True
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
    def _render_progress(self):
        """渲染训练进度面板"""
        st.subheader("训练进度")
        
        # 创建适应度分布图
        if self.training_data["fitness"]:
            fig = px.histogram(
                self.training_data["fitness"],
                title="适应度分布",
                labels={"value": "适应度", "count": "频次"}
            )
            st.plotly_chart(fig, use_container_width=True)
            
        # 创建适应度趋势图
        if len(self.training_data["fitness"]) > 1:
            fig = go.Figure()
            
            fig.add_trace(go.Scatter(
                x=self.training_data["generation"],
                y=self.training_data["fitness"],
                mode="lines+markers",
                name="适应度"
            ))
            
            # 添加移动平均线
            window = min(5, len(self.training_data["fitness"]))
            if window > 1:
                moving_avg = pd.Series(self.training_data["fitness"]).rolling(window=window).mean()
                fig.add_trace(go.Scatter(
                    x=self.training_data["generation"],
                    y=moving_avg,
                    mode="lines",
                    name=f"{window}代移动平均"
                ))
                
            fig.update_layout(
                title="适应度趋势",
                xaxis_title="代数",
                yaxis_title="适应度",
                showlegend=True
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
    def _start_training(self):
        """开始训练"""
        self.is_training = True
        st.success("训练已开始")
        
    def _pause_training(self):
        """暂停训练"""
        self.is_training = False
        st.warning("训练已暂停")
        
    def _reset_training(self):
        """重置训练"""
        self.training_data = {
            "fitness": [],
            "generation": [],
            "timestamp": [],
            "metrics": {
                "sharpe_ratio": [],
                "sortino_ratio": [],
                "max_drawdown": [],
                "win_rate": [],
                "profit_factor": []
            }
        }
        self.current_generation = 0
        st.info("训练已重置")
        
    def update_training_data(self, generation: int, fitness: float, metrics: Dict[str, float]):
        """更新训练数据"""
        self.current_generation = generation
        self.training_data["generation"].append(generation)
        self.training_data["fitness"].append(fitness)
        self.training_data["timestamp"].append(datetime.now())
        
        for metric_name, value in metrics.items():
            self.training_data["metrics"][metric_name].append(value)
            
    def get_training_data(self) -> Dict[str, Any]:
        """获取训练数据"""
        return self.training_data.copy() 