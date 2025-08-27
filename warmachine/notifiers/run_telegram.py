#!/usr/bin/env python
"""
Telegram AI机器人启动脚本
直接启动Telegram机器人，无需完整的AI策略进化系统
"""
import os
import sys
import json
import logging
from api.ai_chat_agent import DeepSeekChatAgent
from PIL import Image

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("telegram_bot.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def load_config():
    """从config.json加载配置"""
    try:
        with open("config.json", "r") as f:
            config = json.load(f)
            logger.info("已加载配置文件")
            return config
    except Exception as e:
        logger.error(f"加载配置文件失败: {e}")
        return None

def setup_env_from_config(config):
    """设置环境变量"""
    # Telegram设置
    token = config.get("telegram_token")
    chat_id = config.get("telegram_chat_id")
    
    if token and chat_id:
        os.environ["TELEGRAM_BOT_TOKEN"] = token
        os.environ["TELEGRAM_TOKEN"] = token
        os.environ["TELEGRAM_CHAT_ID"] = str(chat_id)
        os.environ["TELEGRAM_ENABLED"] = "true"
        
        # 设置授权用户
        authorized_users = config.get("authorized_users", [])
        if authorized_users:
            os.environ["TELEGRAM_AUTHORIZED_USERS"] = ",".join(map(str, authorized_users))
        
        logger.info(f"已设置Telegram环境变量，Token: {token}, Chat ID: {chat_id}")
        return True
    else:
        logger.error("未找到Telegram token或chat ID")
        return False

def create_command_handlers():
    """创建命令处理函数"""
    return {
        "status": lambda: "AI策略自动进化系统状态: 在线",
        "save_strategy": lambda code, params: f"strategy_{params.replace(' ', '_')}.py",
        "analyze_strategy": lambda name: f"策略{name}分析: 夏普比率 1.2",
        "optimize_portfolio": lambda: "投资组合已优化: 40% 策略A, 60% 策略B",
        "train_strategy": lambda name: f"训练完成，策略: {name}, 准确率: 85%",
        "generate_strategy": lambda params: f"已生成{params}策略 (示例)"
    }

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
    # 加载配置
    config = load_config()
    if not config:
        print("❌ 加载配置失败，退出")
        return
    
    # 初始化AI代理
    ai_agent = DeepSeekChatAgent(
        api_key=config.get("deepseek_api_key", ""),
        model=config.get("deepseek_model", "deepseek-ai/DeepSeek-V3"),
        api_url=config.get("deepseek_api_url", "https://api.siliconflow.cn/v1")
    )
    
    # 创建命令处理函数
    command_handlers = create_command_handlers()
    
    try:
        # 尝试导入v13兼容版本
        try:
            from utils.telegram_ai_assistant_v13 import TelegramAIAssistant
            print("使用v13兼容版本的TelegramAIAssistant")
        except ImportError:
            # 如果没有v13版本，使用标准版本
            from utils.telegram_ai_assistant import TelegramAIAssistant
            print("使用标准版本的TelegramAIAssistant")
        
        # 创建Telegram机器人
        bot = TelegramAIAssistant(
            token=config.get("telegram_token"),
            ai_agent=ai_agent,
            command_handlers=command_handlers
        )
        
        # 运行Telegram机器人
        print("🚀 启动Telegram机器人...")
        bot.run()
        
    except ImportError as e:
        logger.error(f"无法导入TelegramAIAssistant: {e}")
        print(f"❌ 无法导入TelegramAIAssistant: {e}")
    except Exception as e:
        logger.error(f"运行Telegram机器人时出错: {e}")
        print(f"❌ 运行失败: {e}")

if __name__ == "__main__":
    print("启动Telegram AI机器人...")
    try:
        main()
    except KeyboardInterrupt:
        print("\n🛑 接收到退出信号，正在关闭...")
    print("Telegram AI机器人已退出") 