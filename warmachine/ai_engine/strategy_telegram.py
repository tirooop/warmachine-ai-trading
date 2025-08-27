#!/usr/bin/env python
"""
AI策略进化启动器 - 使用Telegram集成
从config.json读取配置，无需.env文件
"""
import os
import sys

print("开始加载 - 首先检查imghdr替代品")

# 优先导入imghdr兼容性模块，确保所有后续导入的模块都能正常使用imghdr
try:
    import imghdr_compatibility  # 这会自动注册PIL基于的imghdr替代品
    print("成功导入 imghdr_compatibility")
except ImportError as e:
    print(f"⚠️ 警告: 无法加载imghdr_compatibility模块: {e}")
    print("尝试备用方案")
    # 如果imghdr_compatibility不存在，保留现有的兼容层
    try:
        import PIL_image_check  # 这会自动替代imghdr模块
        print("已加载PIL_image_check作为imghdr模块替代品")
    except ImportError as e:
        print(f"⚠️ 警告: 无法加载PIL_image_check: {e}")
        # 如果PIL_image_check不存在，创建一个简单的兼容层
        try:
            from PIL import Image
            print("已导入PIL.Image，创建兼容层")
            
            # 创建imghdr兼容模块
            class ImghdrModule:
                @staticmethod
                def what(file, h=None):
                    try:
                        if isinstance(file, str):
                            with Image.open(file) as img:
                                return img.format.lower() if img.format else None
                        else:
                            pos = file.tell()
                            file.seek(0)
                            with Image.open(file) as img:
                                format = img.format
                            file.seek(pos)
                            return format.lower() if format else None
                    except Exception:
                        return None
                
                # 添加测试函数兼容性
                tests = {
                    'jpeg': lambda f: ImghdrModule.what(f) == 'jpeg',
                    'png': lambda f: ImghdrModule.what(f) == 'png',
                    'gif': lambda f: ImghdrModule.what(f) == 'gif',
                    'bmp': lambda f: ImghdrModule.what(f) == 'bmp',
                }
            
            # 注册到系统模块
            sys.modules['imghdr'] = ImghdrModule()
            print("已创建PIL兼容层并注册为imghdr替代品")
            
            # 验证注册是否成功
            print(f"验证: 'imghdr' 在 sys.modules 中: {'imghdr' in sys.modules}")
            
            # 测试导入
            try:
                import imghdr
                print(f"测试导入 imghdr 成功: {imghdr}")
            except ImportError as e:
                print(f"测试导入 imghdr 失败: {e}")
        except ImportError as e:
            print(f"⚠️ 警告: 无法加载PIL: {e}，请安装: pip install pillow")

# 现在导入其他模块
print("开始导入其他模块")
import json
import logging
import argparse
from typing import Dict, Any
from PIL import Image

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("strategy_evolution.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def load_config(config_file: str) -> Dict[str, Any]:
    """加载配置文件"""
    try:
        with open(config_file, "r") as f:
            config = json.load(f)
            logger.info(f"已从{config_file}加载配置")
            return config
    except Exception as e:
        logger.error(f"加载配置文件失败: {e}")
        return {}

def setup_env_from_config(config: Dict[str, Any]) -> bool:
    """从配置设置环境变量"""
    # 设置API密钥环境变量
    os.environ["DEEPSEEK_API_KEY"] = config.get("api_key", "")
    os.environ["DEEPSEEK_API_URL"] = config.get("api_url", "")
    os.environ["DEEPSEEK_MODEL"] = config.get("model", "")
    
    # 设置Telegram环境变量(如果启用)
    if config.get("enable_telegram", False):
        token = config.get("telegram_token")
        chat_id = config.get("telegram_chat_id")
        
        if token and chat_id:
            os.environ["TELEGRAM_BOT_TOKEN"] = token
            os.environ["TELEGRAM_CHAT_ID"] = str(chat_id)
            os.environ["TELEGRAM_TOKEN"] = token
            os.environ["TELEGRAM_ENABLED"] = "true"
            
            # 设置授权用户
            authorized_users = config.get("authorized_users", [])
            if authorized_users:
                os.environ["TELEGRAM_AUTHORIZED_USERS"] = ",".join(map(str, authorized_users))
            
            logger.info("Telegram环境变量已设置")
            return True
        else:
            logger.error("config.json中缺少telegram_token或telegram_chat_id")
            return False
    
    return True

def get_image_format(path):
    """
    Use PIL to determine image format
    
    Args:
        path: Path to the image file
        
    Returns:
        Image format or None if not a valid image
    """
    try:
        with Image.open(path) as img:
            return img.format
    except Exception:
        return None

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="AI策略进化启动器")
    parser.add_argument("--config", type=str, default="config.json", help="配置文件路径")
    args = parser.parse_args()
    
    # 加载配置
    config = load_config(args.config)
    if not config:
        print("❌ 加载配置失败，退出")
        return
    
    # 设置环境变量
    if not setup_env_from_config(config):
        print("❌ 设置环境变量失败，退出")
        return
    
    # 导入并运行AI策略进化
    try:
        from run_ai_strategy_evolution import AIStrategyEvolution
        
        # 测试Telegram通知
        if config.get("enable_telegram", False):
            try:
                from utils.telegram_notifier import TelegramNotifier
                notifier = TelegramNotifier()
                notifier.send_message("🚀 AI策略进化系统正在启动...")
                logger.info("Telegram通知测试成功")
            except Exception as e:
                logger.error(f"Telegram通知测试失败: {e}")
        
        # 运行AI策略进化
        evolution = AIStrategyEvolution(config_file=args.config)
        
        # 如果Telegram启用，则运行Telegram机器人
        if evolution.telegram_bot:
            logger.info("启动Telegram机器人...")
            evolution.run_telegram_bot()
        else:
            logger.warning("Telegram机器人未启用或初始化失败")
        
        # 运行进化循环(这里根据实际情况调用API获取市场数据)
        # 示例: evolution.run_evolution_cycle(market_data)
        
        logger.info("AI策略进化系统已启动，按Ctrl+C退出")
        
        # 保持主进程运行
        try:
            while True:
                import time
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("收到退出信号，正在关闭...")
    
    except ImportError as e:
        logger.error(f"导入错误: {e}")
        print(f"❌ 缺少必要的模块，请确保已安装所有依赖: {e}")
    except Exception as e:
        logger.error(f"运行AI策略进化时出错: {e}")
        print(f"❌ 运行失败: {e}")

if __name__ == "__main__":
    print("AI策略进化系统启动中...")
    main()
    print("AI策略进化系统已退出") 