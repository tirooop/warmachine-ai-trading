#!/usr/bin/env python
"""
WarMachine AI Option Quant Desk 安装脚本
自动安装依赖、配置环境并准备系统启动
"""

import os
import sys
import json
import shutil
import subprocess
import platform
import time
from pathlib import Path


def print_banner():
    """打印安装Banner"""
    banner = """
    ╔══════════════════════════════════════════════════════════╗
    ║                                                          ║
    ║   🚀 WarMachine AI Option Quant Desk - 安装程序         ║
    ║                                                          ║
    ║   无人值守AI期权量化交易系统                              ║
    ║                                                          ║
    ╚══════════════════════════════════════════════════════════╝
    """
    print(banner)


def check_python_version():
    """检查Python版本，需要3.8+"""
    print("📋 检查Python版本...")
    major, minor = sys.version_info.major, sys.version_info.minor
    if major < 3 or (major == 3 and minor < 8):
        print("❌ Python版本不符合要求！")
        print(f"当前版本: Python {major}.{minor}")
        print("需要版本: Python 3.8+")
        sys.exit(1)
    
    print(f"✅ 检测到 Python {major}.{minor}")
    return True


def check_os():
    """检查操作系统类型"""
    print("📋 检查操作系统...")
    system = platform.system()
    if system == "Windows":
        print("✅ 检测到 Windows 系统")
        return "Windows"
    elif system == "Linux":
        print("✅ 检测到 Linux 系统")
        return "Linux"
    elif system == "Darwin":
        print("✅ 检测到 macOS 系统")
        return "Darwin"
    else:
        print(f"⚠️ 检测到未知系统: {system}，将尝试继续安装...")
        return system


def check_docker():
    """检查Docker是否已安装"""
    print("📋 检查Docker环境...")
    try:
        subprocess.run(
            ["docker", "--version"], 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            check=True
        )
        print("✅ Docker已安装")
        
        # 检查Docker Compose
        try:
            subprocess.run(
                ["docker-compose", "--version"], 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                check=True
            )
            print("✅ Docker Compose已安装")
            return True
        except (subprocess.SubprocessError, FileNotFoundError):
            print("⚠️ Docker Compose未安装，将尝试仅使用Python环境")
            return False
    except (subprocess.SubprocessError, FileNotFoundError):
        print("⚠️ Docker未安装，将尝试仅使用Python环境")
        return False


def create_directories():
    """创建必要的目录结构"""
    print("📋 创建必要目录...")
    dirs = [
        'logs', 
        'data', 
        'config', 
        'strategies', 
        'production_strategies',
        'results',
        'results/backtests',
        'results/evaluations',
        'temp_charts',
        'temp_audio'
    ]
    
    for d in dirs:
        os.makedirs(d, exist_ok=True)
        print(f"  ✓ 已创建: {d}")


def check_install_deps():
    """检查并安装依赖包"""
    print("📋 安装依赖包...")
    
    # 基础依赖，几乎所有环境都能安装的包
    core_requirements = [
        # 核心依赖
        "numpy>=1.20.0",
        "pandas>=1.3.0",
        "matplotlib>=3.4.0",
        "scipy>=1.7.0",
        "scikit-learn>=1.0.0",
        
        # API访问
        "requests>=2.25.0",
        "websocket-client>=1.2.0",
        "aiohttp>=3.8.0",
        
        # 数据处理
        "yfinance>=0.1.70",
        "pandas-datareader>=0.10.0",
        
        # Web服务
        "fastapi>=0.75.0",
        "uvicorn>=0.17.0",
        "streamlit>=1.10.0",
        
        # 消息传递
        "python-telegram-bot>=13.11",
        "discord.py>=2.0.0",
        
        # 其他工具
        "tqdm>=4.62.0",
        "python-dotenv>=0.19.0",
        "pytz>=2022.1",
        "pymongo>=4.1.0"
    ]
    
    # 可选依赖，安装失败不影响核心功能
    optional_requirements = [
        "alpha_vantage>=2.3.1",
        "ibapi>=9.81.1.post1"
    ]
    
    # 复杂AI依赖，可能需要特殊处理的包
    ai_requirements = [
        # 尝试安装简化版本的包
        "torch",  # 不指定版本，让pip选择兼容版本
        "tensorflow",  # 不指定版本，让pip选择兼容版本
        "transformers",  # 作为deepseek-ai的替代方案
        "openai",  # 作为可能的AI后端
    ]
    
    pip_command = [sys.executable, "-m", "pip", "install"]
    
    # 安装核心依赖
    print("安装核心依赖...")
    for req in core_requirements:
        try:
            print(f"  正在安装: {req}")
            subprocess.run(
                pip_command + [req], 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                check=True
            )
        except subprocess.SubprocessError as e:
            print(f"⚠️ 安装 {req} 时出错: {e}")
            print("⚠️ 这是核心依赖，可能会影响系统功能")
    
    # 安装可选依赖
    print("\n安装可选依赖...")
    for req in optional_requirements:
        try:
            print(f"  正在安装: {req}")
            subprocess.run(
                pip_command + [req], 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                check=True
            )
        except subprocess.SubprocessError as e:
            print(f"⚠️ 安装 {req} 时出错: {e}")
            print("  这是可选依赖，系统仍可运行核心功能")
    
    # 安装AI依赖
    print("\n安装AI依赖 (可能需要一些时间)...")
    print("注意: 如果AI依赖安装失败，系统仍可使用外部API进行AI推理")
    
    for req in ai_requirements:
        try:
            print(f"  尝试安装: {req}")
            # 增加超时时间，AI包通常较大
            subprocess.run(
                pip_command + [req], 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                timeout=300,  # 5分钟超时
                check=False  # 不检查退出状态，即使失败也继续
            )
        except (subprocess.SubprocessError, subprocess.TimeoutExpired) as e:
            print(f"⚠️ 安装 {req} 时出错或超时: {e}")
            print("  系统将使用替代方法进行AI功能")
    
    # 特殊处理deepseek-ai
    print("\n配置DeepSeek API访问...")
    try:
        # 创建mock deepseek模块，使用openai或其他API作为后端
        os.makedirs("utils/ai", exist_ok=True)
        with open("utils/ai/__init__.py", "w") as f:
            f.write("# AI utilities module\n")
        
        with open("utils/ai/deepseek_client.py", "w") as f:
            f.write("""# DeepSeek API Client Mock
import os
import json
import requests

class DeepSeekClient:
    \"\"\"简化的DeepSeek客户端实现，使用HTTP API\"\"\"
    
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
                json=data
            )
            return response.json()
        except Exception as e:
            return {"error": f"API调用失败: {str(e)}"}

# 便捷函数
def create_client(api_key=None):
    return DeepSeekClient(api_key)
""")
        print("  ✓ 已创建DeepSeek API客户端替代实现")
    except Exception as e:
        print(f"⚠️ 创建DeepSeek客户端替代实现失败: {e}")
    
    print("✅ 依赖包安装完成")


def create_config():
    """创建默认配置文件"""
    print("📋 创建配置文件...")
    
    config_path = os.path.join("config", "warmachine_config.json")
    if os.path.exists(config_path):
        print(f"  ✓ 配置文件已存在: {config_path}")
        return
    
    config = {
        "symbols": ["SPY", "QQQ", "TSLA", "ETH-USD"],
        "evolution_params": {
            "strategies_per_symbol": 3,
            "evaluation_cycle": 1,
            "deploy_top_n": 2,
            "auto_deploy": True
        },
        "notification": {
            "telegram_enabled": True,
            "discord_enabled": True,
            "feishu_enabled": False,
            "voice_enabled": False
        },
        "market_hours": {
            "pre_market_open": "04:00",
            "market_open": "09:30",
            "market_close": "16:00",
            "post_market_close": "20:00"
        },
        "ai_settings": {
            "llm_provider": "deepseek",
            "temperature": 0.7,
            "strategy_generation_prompt_template": "创建一个针对{{symbol}}的期权交易策略，考虑当前市场环境和技术指标..."
        },
        "risk_management": {
            "max_position_size_pct": 5,
            "max_loss_per_trade_pct": 2,
            "max_total_loss_pct": 10
        },
        "trading_settings": {
            "environment": "paper",  # 或 "live"
            "base_currency": "USD"
        }
    }
    
    os.makedirs("config", exist_ok=True)
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    
    print(f"  ✓ 已创建默认配置文件: {config_path}")


def create_env_file():
    """创建.env文件模板"""
    print("📋 创建环境变量文件...")
    
    if os.path.exists(".env"):
        print("  ✓ .env文件已存在")
        return
    
    env_template = """# DeepSeek API密钥 (用于AI策略生成)
DEEPSEEK_API_KEY=

# Telegram Bot Token (用于通知)
TELEGRAM_BOT_TOKEN=

# Discord Bot Token (用于通知)
DISCORD_BOT_TOKEN=

# Feishu App ID & Secret (用于通知)
FEISHU_APP_ID=
FEISHU_APP_SECRET=

# MongoDB配置
MONGO_USERNAME=admin
MONGO_PASSWORD=password

# IBKR配置 (用于实盘交易)
IBKR_ACCOUNT=
IBKR_PASSWORD=
IBKR_API_KEY=

# 时区设置 (默认美东时间)
TZ=America/New_York
"""

    with open(".env", "w", encoding="utf-8") as f:
        f.write(env_template)
    
    print("  ✓ 已创建.env文件，请编辑填入您的API密钥")


def check_startup_scripts():
    """检查启动脚本是否存在"""
    print("📋 检查启动脚本...")
    
    # 检查Linux/macOS启动脚本
    if not os.path.exists("start_warmachine_option.sh"):
        print("  ✗ 未找到Linux/macOS启动脚本")
        return False
    
    # 检查Windows启动脚本
    if not os.path.exists("start_warmachine_option.bat"):
        print("  ✗ 未找到Windows启动脚本")
        return False
    
    print("  ✓ 启动脚本已存在")
    return True


def make_scripts_executable():
    """使脚本可执行"""
    if platform.system() in ["Linux", "Darwin"]:
        try:
            os.chmod("start_warmachine_option.sh", 0o755)
            print("  ✓ 已将start_warmachine_option.sh设为可执行")
        except Exception as e:
            print(f"  ⚠️ 无法修改脚本权限: {e}")


def main():
    """主安装函数"""
    print_banner()
    
    # 检查环境
    check_python_version()
    os_type = check_os()
    has_docker = check_docker()
    
    # 创建目录结构
    create_directories()
    
    # 安装依赖
    check_install_deps()
    
    # 创建配置文件
    create_config()
    create_env_file()
    
    # 检查启动脚本
    scripts_exist = check_startup_scripts()
    if scripts_exist:
        make_scripts_executable()
    
    # 完成安装
    print("\n🎉 WarMachine AI Option Quant Desk 安装完成！\n")
    
    # 启动指南
    print("📋 启动指南:")
    if os_type in ["Linux", "Darwin"]:
        print("  执行: bash start_warmachine_option.sh")
    else:
        print("  执行: start_warmachine_option.bat")
    
    print("\n🔗 文档导航:")
    print("  • 使用指南: README_AI_OPTION_TRADER.md")
    print("  • 期权交易指南: OPTION_TRADING_GUIDE.md")
    
    # 询问是否立即启动
    try:
        start_now = input("\n是否立即启动系统? (y/n): ").strip().lower()
        if start_now == 'y':
            print("\n🚀 启动系统...\n")
            if os_type in ["Linux", "Darwin"]:
                os.system("bash start_warmachine_option.sh")
            else:
                os.system("start_warmachine_option.bat")
        else:
            print("\n👋 安装完成，您可以稍后手动启动系统。")
    except KeyboardInterrupt:
        print("\n\n👋 安装已完成，您可以稍后手动启动系统。")


if __name__ == "__main__":
    main() 