#!/usr/bin/env python
"""
WarMachine AI Option Trader - 安装修复工具
解决常见的安装问题，尤其是AI/ML库相关的问题
"""

import os
import sys
import platform
import subprocess
import shutil


def print_banner():
    """打印Banner"""
    banner = """
╔══════════════════════════════════════════════════════════╗
║                                                          ║
║   🔧 WarMachine AI Option Trader - 安装修复工具          ║
║                                                          ║
║   解决常见的依赖安装问题                                  ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝
"""
    print(banner)


def get_python_info():
    """获取Python环境信息"""
    print("系统信息:")
    print(f"- 操作系统: {platform.system()} {platform.release()}")
    print(f"- Python版本: {platform.python_version()}")
    print(f"- 解释器路径: {sys.executable}")
    print("")


def install_minimal_requirements():
    """安装最小依赖集"""
    print("开始安装基础依赖...")
    
    # 基础依赖，这些包应该在任何环境下都能成功安装
    basic_reqs = [
        "numpy",
        "pandas",
        "matplotlib",
        "requests",
        "tqdm",
        "python-dotenv",
        "streamlit"
    ]
    
    pip_cmd = [sys.executable, "-m", "pip", "install", "--upgrade"]
    
    for req in basic_reqs:
        try:
            print(f"安装 {req}...")
            subprocess.run(pip_cmd + [req], check=True)
            print(f"✓ {req} 安装成功")
        except subprocess.CalledProcessError:
            print(f"✗ {req} 安装失败")
    
    print("基础依赖安装完成\n")


def create_ai_fallback():
    """创建AI服务的替代实现"""
    print("创建AI服务的替代实现...")
    
    # 确保utils/ai目录存在
    os.makedirs("utils/ai", exist_ok=True)
    
    # 创建__init__.py
    with open("utils/ai/__init__.py", "w") as f:
        f.write("# AI utilities package\n")
    
    # 创建deepseek_client.py
    with open("utils/ai/deepseek_client.py", "w") as f:
        f.write("""# DeepSeek API Client
import os
import json
import time
import requests

class DeepSeekClient:
    \"\"\"简化的DeepSeek客户端实现\"\"\"
    
    def __init__(self, api_key=None):
        self.api_key = api_key or os.environ.get('DEEPSEEK_API_KEY')
        self.api_base = "https://api.deepseek.com/v1"
        
    def completion(self, prompt, model="deepseek-chat", temperature=0.7, max_tokens=2000):
        \"\"\"生成文本补全\"\"\"
        if not self.api_key:
            return {"error": "API密钥未设置，请在.env文件中设置DEEPSEEK_API_KEY"}
            
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        try:
            response = requests.post(
                f"{self.api_base}/chat/completions", 
                headers=headers, 
                json=data,
                timeout=60
            )
            return response.json()
        except Exception as e:
            return {"error": f"API调用失败: {str(e)}"}

# 便捷函数
def create_client(api_key=None):
    \"\"\"创建客户端\"\"\"
    return DeepSeekClient(api_key)
""")
    
    # 创建openai_client.py 作为替代方案
    with open("utils/ai/openai_client.py", "w") as f:
        f.write("""# OpenAI API Client
import os
import json
import time
import requests

class OpenAIClient:
    \"\"\"简化的OpenAI客户端实现\"\"\"
    
    def __init__(self, api_key=None):
        self.api_key = api_key or os.environ.get('OPENAI_API_KEY')
        self.api_base = "https://api.openai.com/v1"
        
    def completion(self, prompt, model="gpt-3.5-turbo", temperature=0.7, max_tokens=2000):
        \"\"\"生成文本补全\"\"\"
        if not self.api_key:
            return {"error": "API密钥未设置，请在.env文件中设置OPENAI_API_KEY"}
            
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        try:
            response = requests.post(
                f"{self.api_base}/chat/completions", 
                headers=headers, 
                json=data,
                timeout=60
            )
            return response.json()
        except Exception as e:
            return {"error": f"API调用失败: {str(e)}"}

# 便捷函数
def create_client(api_key=None):
    \"\"\"创建客户端\"\"\"
    return OpenAIClient(api_key)
""")
    
    print("✓ AI替代服务创建完成\n")


def update_env_template():
    """更新.env模板，添加OpenAI选项"""
    if not os.path.exists(".env"):
        print("创建.env模板文件...")
        with open(".env", "w") as f:
            f.write("""# DeepSeek API密钥 (推荐)
DEEPSEEK_API_KEY=

# OpenAI API密钥 (替代选项)
OPENAI_API_KEY=

# Telegram Bot Token (用于通知)
TELEGRAM_BOT_TOKEN=

# Discord Bot Token (用于通知)
DISCORD_BOT_TOKEN=

# MongoDB配置
MONGO_USERNAME=admin
MONGO_PASSWORD=password

# 时区设置 (默认美东时间)
TZ=America/New_York
""")
        print("✓ .env模板创建完成")
    else:
        print(".env文件已存在，未修改")
    print("")


def create_minimal_run_script():
    """创建简化版启动脚本"""
    print("创建简化版启动脚本...")
    
    if os.name == 'nt':  # Windows
        with open("run_option_trader_simple.bat", "w") as f:
            f.write("""@echo off
echo ===== WarMachine AI Option Trader - 简化版 =====
echo.

set PYTHONPATH=%CD%
echo 设置Python路径: %PYTHONPATH%

echo.
echo [1] 启动期权策略生成
echo [2] 启动多标的监控
echo [3] 启动调度器
echo [0] 退出
echo.

set /p choice="请选择要启动的组件 (0-3): "

if "%choice%"=="1" (
    python ai_strategy_generator\run_option_evolution.py
) else if "%choice%"=="2" (
    python option_manager\multi_symbol_watcher.py
) else if "%choice%"=="3" (
    python scheduler\routine_scheduler.py
) else if "%choice%"=="0" (
    exit /b 0
) else (
    echo 无效选择
    pause
    exit /b 1
)

pause
""")
        print("✓ 已创建 run_option_trader_simple.bat")
    else:  # Linux/macOS
        with open("run_option_trader_simple.sh", "w") as f:
            f.write("""#!/bin/bash
echo "===== WarMachine AI Option Trader - 简化版 ====="
echo ""

export PYTHONPATH=$(pwd)
echo "设置Python路径: $PYTHONPATH"

echo ""
echo "[1] 启动期权策略生成"
echo "[2] 启动多标的监控"
echo "[3] 启动调度器"
echo "[0] 退出"
echo ""

read -p "请选择要启动的组件 (0-3): " choice

case $choice in
    1)
        python3 ai_strategy_generator/run_option_evolution.py
        ;;
    2)
        python3 option_manager/multi_symbol_watcher.py
        ;;
    3)
        python3 scheduler/routine_scheduler.py
        ;;
    0)
        exit 0
        ;;
    *)
        echo "无效选择"
        exit 1
        ;;
esac
""")
        # 设置为可执行
        os.chmod("run_option_trader_simple.sh", 0o755)
        print("✓ 已创建 run_option_trader_simple.sh")
    
    print("")


def check_missing_dirs():
    """检查是否缺少必要的目录"""
    print("检查必要目录...")
    
    dirs = [
        'logs', 
        'data', 
        'config', 
        'strategies', 
        'production_strategies',
        'results',
        'utils',
        'utils/ai'
    ]
    
    for d in dirs:
        if not os.path.exists(d):
            print(f"创建目录: {d}")
            os.makedirs(d, exist_ok=True)
    
    print("✓ 所有必要目录已创建\n")


def create_basic_config():
    """创建基本配置文件"""
    config_dir = "config"
    config_file = os.path.join(config_dir, "warmachine_config.json")
    
    if not os.path.exists(config_file):
        print("创建默认配置文件...")
        os.makedirs(config_dir, exist_ok=True)
        
        config = {
            "symbols": ["SPY", "QQQ", "TSLA", "ETH-USD"],
            "evolution_params": {
                "strategies_per_symbol": 3,
                "deploy_top_n": 2,
                "auto_deploy": True
            },
            "notification": {
                "telegram_enabled": False,
                "discord_enabled": False
            },
            "ai_settings": {
                "llm_provider": "deepseek",
                "temperature": 0.7
            },
            "risk_management": {
                "max_position_size_pct": 5,
                "max_loss_per_trade_pct": 2,
                "max_total_loss_pct": 10
            }
        }
        
        with open(config_file, "w") as f:
            import json
            json.dump(config, f, indent=2)
        
        print(f"✓ 已创建配置文件: {config_file}")
    else:
        print(f"配置文件已存在: {config_file}")
    
    print("")


def main():
    """主函数"""
    print_banner()
    
    get_python_info()
    
    print("此工具将修复安装问题并配置一个简化版的AI期权交易系统。")
    print("注意: 这将创建替代实现，而不依赖于难以安装的AI/ML库。")
    print("")
    
    proceed = input("是否继续? (y/n): ").lower().strip()
    if proceed != "y":
        print("已取消操作")
        return
    
    print("\n开始修复安装...\n")
    
    # 步骤1: 检查必要目录
    check_missing_dirs()
    
    # 步骤2: 安装最小依赖集
    install_minimal_requirements()
    
    # 步骤3: 创建AI替代服务
    create_ai_fallback()
    
    # 步骤4: 更新.env模板
    update_env_template()
    
    # 步骤5: 创建基本配置文件
    create_basic_config()
    
    # 步骤6: 创建简化版启动脚本
    create_minimal_run_script()
    
    print("==================================================")
    print("🎉 修复完成! 系统已配置为使用HTTP API代替本地AI库。")
    print("==================================================")
    print("")
    print("后续步骤:")
    print("1. 编辑.env文件，添加您的API密钥 (DeepSeek或OpenAI)")
    print("2. 使用简化版启动脚本运行系统:")
    if os.name == 'nt':
        print("   run_option_trader_simple.bat")
    else:
        print("   ./run_option_trader_simple.sh")
    print("")
    print("注意: 此简化版本使用HTTP API而不是本地AI库，确保您有可用的API密钥。")


if __name__ == "__main__":
    main() 