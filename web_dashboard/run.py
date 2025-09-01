"""
运行Web应用的入口文件
"""

import streamlit as st
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web_dashboard.app import WebApp

if __name__ == "__main__":
    app = WebApp()
    app.run() 