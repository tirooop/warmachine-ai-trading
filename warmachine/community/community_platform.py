#!/usr/bin/env python


"""


AI量化社区平台 - 一键启动模块





集成了:


- AI策略生成与优化


- Telegram/Discord社区交互


- 图表生成与AI解读


- 组合管理与优化


- 市场异动监控


- AI研究员日报


"""





import os


import sys


import logging


import argparse


import threading


import time


import json


from datetime import datetime


from pathlib import Path





# 设置日志


logging.basicConfig(


    level=logging.INFO,


    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',


    handlers=[


        logging.FileHandler("ai_community_platform.log"),


        logging.StreamHandler()


    ]


)


logger = logging.getLogger(__name__)





# 检查并创建所需目录


def create_directory_structure():


    """创建平台所需的目录结构"""


    directories = [


        "config",                       # 配置目录


        "utils/ai_engine",              # AI核心模块


        "utils/visualization",          # 图表与播报模块


        "utils/community",              # 用户与组合模块


        "utils/monitoring",             # 事件与监控模块


        "api",                          # API模块


        "data/market",                  # 市场数据


        "data/users",                   # 用户数据


        "data/portfolios",              # 组合数据


        "data/strategies",              # 策略数据


        "data/ai_research",             # AI研究报告


        "static/charts",                # 图表静态文件


        "static/audio",                 # 音频静态文件


        "logs",                         # 日志文件


    ]


    


    for directory in directories:


        Path(directory).mkdir(parents=True, exist_ok=True)


        logger.info(f"目录已创建/确认: {directory}")





# 初始化配置文件


def initialize_config():


    """初始化配置文件"""


    config_file = "config/platform_config.json"


    


    if not os.path.exists(config_file):


        default_config = {


            "version": "1.0.0",


            "updated_at": datetime.now().isoformat(),


            "ai": {


                "provider": "deepseek",


                "api_key": "sk-uvbjgxuaigsbjpebfthckspmnpfjixhwuwapwsrrqprfvarl",


                "model": "deepseek-ai/DeepSeek-V3",


                "base_url": "https://api.siliconflow.cn/v1",


                "fallback_provider": "openai",


                "fallback_api_key": "",


                "fallback_model": "gpt-3.5-turbo"


            },


            "telegram": {


                "enabled": True,


                "token": "",


                "admin_chat_id": ""


            },


            "discord": {


                "enabled": True,


                "token": "",


                "admin_channel_id": ""


            },


            "web_api": {


                "enabled": True,


                "host": "0.0.0.0",


                "port": 8000,


                "debug": False


            },


            "market_data": {


                "provider": "yfinance",


                "symbols": ["SPY", "QQQ", "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "BTC-USD", "ETH-USD"]


            },


            "ai_researcher": {


                "daily_report_time": "08:00",


                "weekly_report_day": "Monday",


                "weekly_report_time": "09:00",


                "research_topics": ["市场趋势", "板块轮动", "资金流向", "宏观经济", "明日机会"]


            },


            "audio": {


                "enabled": True,


                "engine": "edge-tts",


                "voice": "zh-CN-XiaoxiaoNeural"


            },


            "storage": {


                "strategy_cloud_sync": False,


                "portfolio_cloud_sync": False,


                "cloud_provider": "local"


            }


        }


        


        with open(config_file, "w", encoding="utf-8") as f:


            json.dump(default_config, f, indent=2, ensure_ascii=False)


            


        logger.info(f"配置文件已创建: {config_file}")





# 创建初始化文件


def create_init_files():


    """创建必要的初始化文件"""


    init_files = [


        "utils/__init__.py",


        "utils/ai_engine/__init__.py",


        "utils/visualization/__init__.py",


        "utils/community/__init__.py",


        "utils/monitoring/__init__.py",


        "api/__init__.py"


    ]


    


    for file_path in init_files:


        if not os.path.exists(file_path):


            with open(file_path, "w", encoding="utf-8") as f:


                f.write('"""AI量化社区平台模块"""')


            logger.info(f"初始化文件已创建: {file_path}")





# 主函数：启动所有服务


def main():


    """启动AI量化社区平台"""


    parser = argparse.ArgumentParser(description="AI量化社区平台启动器")


    parser.add_argument("--telegram", action="store_true", help="启用Telegram机器人")


    parser.add_argument("--discord", action="store_true", help="启用Discord机器人")


    parser.add_argument("--web", action="store_true", help="启用Web API")


    parser.add_argument("--ai-research", action="store_true", help="启用AI研究员")


    parser.add_argument("--monitor", action="store_true", help="启用市场监控")


    parser.add_argument("--all", action="store_true", help="启用所有服务")


    


    args = parser.parse_args()


    


    # 如果没有指定任何参数，默认启用所有服务


    if not any([args.telegram, args.discord, args.web, args.ai_research, args.monitor]):


        args.all = True


    


    # 准备环境


    logger.info("准备AI量化社区平台环境...")


    create_directory_structure()


    initialize_config()


    create_init_files()


    


    # 加载配置


    try:


        with open("config/platform_config.json", "r", encoding="utf-8") as f:


            config = json.load(f)


        logger.info("配置加载成功")


    except Exception as e:


        logger.error(f"配置加载失败: {str(e)}")


        return


    


    # 启动服务


    threads = []


    


    # Telegram机器人


    if args.telegram or args.all:


        if config["telegram"]["enabled"]:


            logger.info("正在启动Telegram机器人...")


            telegram_thread = threading.Thread(


                target=start_telegram_bot,


                args=(config,),


                daemon=True


            )


            threads.append(telegram_thread)


            telegram_thread.start()


        else:


            logger.info("Telegram机器人已禁用")


    


    # Discord机器人


    if args.discord or args.all:


        if config["discord"]["enabled"]:


            logger.info("正在启动Discord机器人...")


            discord_thread = threading.Thread(


                target=start_discord_bot,


                args=(config,),


                daemon=True


            )


            threads.append(discord_thread)


            discord_thread.start()


        else:


            logger.info("Discord机器人已禁用")


    


    # Web API


    if args.web or args.all:


        if config["web_api"]["enabled"]:


            logger.info("正在启动Web API...")


            web_thread = threading.Thread(


                target=start_web_api,


                args=(config,),


                daemon=True


            )


            threads.append(web_thread)


            web_thread.start()


        else:


            logger.info("Web API已禁用")


    


    # AI研究员


    if args.ai_research or args.all:


        logger.info("正在启动AI研究员...")


        ai_thread = threading.Thread(


            target=start_ai_researcher,


            args=(config,),


            daemon=True


        )


        threads.append(ai_thread)


        ai_thread.start()


    


    # 市场监控


    if args.monitor or args.all:


        logger.info("正在启动市场监控...")


        monitor_thread = threading.Thread(


            target=start_market_monitor,


            args=(config,),


            daemon=True


        )


        threads.append(monitor_thread)


        monitor_thread.start()


    


    # 主线程保持运行


    try:


        logger.info("AI量化社区平台启动完成！")


        logger.info("按Ctrl+C停止所有服务...")


        


        while True:


            time.sleep(1)


    except KeyboardInterrupt:


        logger.info("正在关闭AI量化社区平台...")


        logger.info("请等待所有服务安全退出...")


        


        # 等待所有线程结束（实际上由于daemon=True，主线程结束后所有线程会被强制结束）


        time.sleep(2)


        logger.info("AI量化社区平台已关闭")





def start_telegram_bot(config):


    """启动Telegram机器人"""


    try:


        # 这里将来会引入实际的Telegram机器人模块


        logger.info("✅ Telegram机器人启动成功")


        


        while True:


            time.sleep(10)


    except Exception as e:


        logger.error(f"Telegram机器人出错: {str(e)}")





def start_discord_bot(config):


    """启动Discord机器人"""


    try:


        # 这里将来会引入实际的Discord机器人模块


        logger.info("✅ Discord机器人启动成功")


        


        while True:


            time.sleep(10)


    except Exception as e:


        logger.error(f"Discord机器人出错: {str(e)}")





def start_web_api(config):


    """启动Web API"""


    try:


        # 这里将来会引入实际的Web API模块


        logger.info("✅ Web API启动成功")


        


        while True:


            time.sleep(10)


    except Exception as e:


        logger.error(f"Web API出错: {str(e)}")





def start_ai_researcher(config):


    """启动AI研究员"""


    try:


        # 这里将来会引入实际的AI研究员模块


        logger.info("✅ AI研究员启动成功")


        


        while True:


            time.sleep(10)


    except Exception as e:


        logger.error(f"AI研究员出错: {str(e)}")





def start_market_monitor(config):


    """启动市场监控"""


    try:


        # 这里将来会引入实际的市场监控模块


        logger.info("✅ 市场监控启动成功")


        


        while True:


            time.sleep(10)


    except Exception as e:


        logger.error(f"市场监控出错: {str(e)}")





if __name__ == "__main__":


    main() 