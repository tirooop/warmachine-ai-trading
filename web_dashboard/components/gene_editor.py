"""
基因编辑器组件
用于编辑和优化交易策略的基因
"""

import streamlit as st
import pandas as pd
import numpy as np
from typing import Dict, List, Any
import json
import os
from datetime import datetime
import plotly.graph_objects as go

# 使用绝对导入
from web_dashboard.config.frontend_config import VISUALIZATION_CONFIG

class GeneEditor:
    """基因编辑器组件"""
    
    def __init__(self):
        """初始化基因编辑器"""
        self.config = VISUALIZATION_CONFIG["gene_editor"]
        self.genes = {}
        self.history = []
        
    def render(self):
        """渲染基因编辑器界面"""
        st.title("基因编辑器")
        
        # 创建两列布局
        col1, col2 = st.columns([2, 1])
        
        with col1:
            self._render_visualization()
            
        with col2:
            self._render_controls()
            
    def _render_visualization(self):
        """渲染可视化部分"""
        # 创建雷达图
        fig = self._create_radar_chart()
        st.plotly_chart(fig, use_container_width=True)
        
        # 创建热力图
        fig = self._create_heatmap()
        st.plotly_chart(fig, use_container_width=True)
        
    def _render_controls(self):
        """渲染控制面板"""
        st.subheader("基因参数")
        
        # 添加基因参数滑块
        for gene_name, gene_value in self.genes.items():
            self.genes[gene_name] = st.slider(
                gene_name,
                min_value=0.0,
                max_value=100.0,
                value=gene_value,
                step=0.1
            )
            
        # 添加操作按钮
        col1, col2 = st.columns(2)
        with col1:
            if st.button("保存"):
                self._save_genes()
        with col2:
            if st.button("重置"):
                self._reset_genes()
                
    def _create_radar_chart(self) -> go.Figure:
        """创建雷达图"""
        config = self.config["radar_chart"]
        
        fig = go.Figure()
        
        # 添加基因数据
        fig.add_trace(go.Scatterpolar(
            r=list(self.genes.values()),
            theta=list(self.genes.keys()),
            fill='toself',
            name='当前基因'
        ))
        
        # 设置布局
        fig.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, config["max_value"]]
                )
            ),
            showlegend=True,
            width=config["width"],
            height=config["height"]
        )
        
        return fig
        
    def _create_heatmap(self) -> go.Figure:
        """创建热力图"""
        config = self.config["heatmap"]
        
        # 创建基因相关性矩阵
        matrix = self._calculate_gene_correlation()
        
        fig = go.Figure(data=go.Heatmap(
            z=matrix,
            x=list(self.genes.keys()),
            y=list(self.genes.keys()),
            colorscale=config["colors"]
        ))
        
        fig.update_layout(
            title="基因相关性热力图",
            width=config["cell_size"] * len(self.genes),
            height=config["cell_size"] * len(self.genes)
        )
        
        return fig
        
    def _calculate_gene_correlation(self) -> np.ndarray:
        """计算基因相关性矩阵"""
        # 这里使用简单的示例数据，实际应用中应该使用真实的相关性计算
        n = len(self.genes)
        return np.random.rand(n, n)
        
    def _save_genes(self):
        """保存基因配置"""
        self.history.append(self.genes.copy())
        st.success("基因配置已保存")
        
    def _reset_genes(self):
        """重置基因配置"""
        if self.history:
            self.genes = self.history[-1].copy()
            st.info("已恢复到上次保存的配置")
        else:
            st.warning("没有可恢复的配置")
            
    def load_genes(self, genes: Dict[str, float]):
        """加载基因配置"""
        self.genes = genes.copy()
        self.history = [genes.copy()]
        
    def get_genes(self) -> Dict[str, float]:
        """获取当前基因配置"""
        return self.genes.copy() 