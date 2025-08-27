#!/usr/bin/env python
"""
依赖安装脚本

安装AI策略演进模块所需的依赖项
"""

import subprocess
import sys
import os
import logging
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 要安装的依赖项
REQUIREMENTS = [
    "pandas",
    "numpy",
    "matplotlib",
    "yfinance",
    "requests",
    "openai",
    "python-dotenv"
]

def install_requirements():
    """安装所有依赖项"""
    logger.info("开始安装依赖项...")
    
    for package in REQUIREMENTS:
        try:
            logger.info(f"安装 {package}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
            logger.info(f"{package} 安装成功")
        except subprocess.CalledProcessError as e:
            logger.error(f"安装 {package} 失败: {str(e)}")
            return False
            
    logger.info("所有依赖项安装完成")
    return True

def verify_installation():
    """验证安装是否成功"""
    logger.info("验证安装...")
    
    for package in REQUIREMENTS:
        try:
            __import__(package)
            logger.info(f"{package} 已成功导入")
        except ImportError as e:
            logger.error(f"导入 {package} 失败: {str(e)}")
            return False
            
    logger.info("所有依赖项验证成功")
    return True

def create_required_directories():
    """创建所需的目录结构"""
    dirs = [
        "strategies",
        "strategies/generated",
        "strategies/deepseek_test",
        "data",
        "data/backtest"
    ]
    
    for d in dirs:
        Path(d).mkdir(parents=True, exist_ok=True)
        logger.info(f"创建目录: {d}")

def check_python_version():
    """检查Python版本是否满足要求"""
    major = sys.version_info.major
    minor = sys.version_info.minor
    
    if major < 3 or (major == 3 and minor < 7):
        logger.error(f"Python版本必须大于等于3.7.0，当前版本: {major}.{minor}")
        return False
        
    logger.info(f"Python版本检查通过: {major}.{minor}")
    return True

def main():
    """主函数"""
    logger.info("=== AI策略演进模块依赖安装 ===")
    
    # 检查Python版本
    if not check_python_version():
        return
    
    # 安装依赖项
    if not install_requirements():
        logger.error("依赖项安装失败")
        return
    
    # 验证安装
    if not verify_installation():
        logger.error("依赖项验证失败")
        return
    
    # 创建目录
    create_required_directories()
    
    # 安装完成
    logger.info("=== 安装完成 ===")
    logger.info("您可以运行 'python test_deepseek_connection.py' 来测试API连接")
    logger.info("或运行 'python test_evolution_with_deepseek.py' 来测试策略演进")

if __name__ == "__main__":
    main() 