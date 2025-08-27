#!/usr/bin/env python


"""


AI交易助手系统启动器


启动全套AI交易员工作流、市场监听和推送系统


支持语音摘要、图表报告和市场事件监控


"""





import os


import sys


import time


import logging


import argparse


from datetime import datetime, timedelta


import threading





# 设置正确的环境变量


def setup_environment():


    """设置必要的环境变量"""


    # 加载PIL兼容层替代imghdr


    try:


        # 尝试导入PIL


        import PIL


        


        # 加载PIL_image_check模块替代imghdr


        try:


            import PIL_image_check  # 这会自动替代imghdr


            # PIL_image_check已经将自身注册为imghdr模块的替代品


        except ImportError:


            # 如果PIL_image_check不存在，手动创建兼容层


            from PIL import Image


            


            # 创建自定义兼容模块


            class ImghdrCompatModule:


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


                


                tests = {


                    'jpeg': lambda f: ImghdrCompatModule.what(f) == 'jpeg',


                    'png': lambda f: ImghdrCompatModule.what(f) == 'png',


                    'gif': lambda f: ImghdrCompatModule.what(f) == 'gif',


                    'bmp': lambda f: ImghdrCompatModule.what(f) == 'bmp',


                }


            


            # 创建兼容模块并安装到sys.modules


            sys.modules['imghdr'] = ImghdrCompatModule()


            


    except ImportError:


        print("⚠️ 警告: PIL库未安装，请运行: pip install pillow")


        


    # Telegram配置


    os.environ["TELEGRAM_BOT_TOKEN"] = os.environ.get("TELEGRAM_BOT_TOKEN", "7840040841AAG5Yj8-wgOU4eICkA5ba0e17EIzyPWP088")


    os.environ["TELEGRAM_CHAT_ID"] = os.environ.get("TELEGRAM_CHAT_ID", "YOUR_CHAT_ID_HERE")


    


    # DeepSeek API配置


    os.environ["DEEPSEEK_API_KEY"] = os.environ.get("DEEPSEEK_API_KEY", "sk-uvbjgxuaigsbjpebfthckspmnpfjixhwuwapwsrrqprfvarl")


    os.environ["DEEPSEEK_API_URL"] = os.environ.get("DEEPSEEK_API_URL", "https://api.siliconflow.cn/v1")


    os.environ["DEEPSEEK_MODEL"] = os.environ.get("DEEPSEEK_MODEL", "deepseek-ai/DeepSeek-V3")


    


    # Polygon API配置


    os.environ["POLYGON_API_KEY"] = os.environ.get("POLYGON_API_KEY", "LvSC19aRC_RnsZaVTplUAn_FFHH3pLYM")


    


    # Feishu Webhook配置


    os.environ["FEISHU_WEBHOOK"] = os.environ.get("FEISHU_WEBHOOK", "https://www.feishu.cn/flow/api/trigger-webhook/aed5a7c805669fe61a605fe0b93912eb")


    


    # 其他数据源配置


    os.environ["DATABENTO_API_KEY"] = os.environ.get("DATABENTO_API_KEY", "db-CkEmFXHNXd3XXS6F5qLYRPxR9jaTy")





# 配置日志


def setup_logging(log_level=logging.INFO):


    """设置日志配置"""


    # 创建日志目录


    os.makedirs("logs", exist_ok=True)


    


    # 配置根日志记录器


    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'


    logging.basicConfig(


        level=log_level,


        format=log_format,


        handlers=[


            logging.StreamHandler(),  # 控制台输出


            logging.FileHandler(f"logs/ai_trader_{datetime.now().strftime('%Y%m%d')}.log")  # 文件输出


        ]


    )


    


    # 设置第三方库的日志级别


    logging.getLogger("urllib3").setLevel(logging.WARNING)


    logging.getLogger("telegram").setLevel(logging.WARNING)


    logging.getLogger("matplotlib").setLevel(logging.WARNING)





# 打印欢迎信息


def print_welcome_message():


    """打印欢迎信息"""


    welcome_text = """


    ╔═══════════════════════════════════════════════════╗


    ║                                                   ║


    ║   🤖 AI交易助手系统 - 高级量化交易版               ║


    ║                                                   ║


    ╠═══════════════════════════════════════════════════╣


    ║                                                   ║


    ║   🔹 语音摘要 + 图表报告 + 全球市场监控            ║


    ║   🔹 盘前/盘中/盘后 全周期跟踪                     ║


    ║   🔹 DeepSeek AI 驱动的策略分析                   ║


    ║   🔹 跨平台 Telegram 推送                         ║


    ║                                                   ║


    ╚═══════════════════════════════════════════════════╝


    """


    print(welcome_text)





# 创建临时目录


def create_temp_directories():


    """创建必要的临时目录"""


    os.makedirs("temp_charts", exist_ok=True)


    os.makedirs("temp_audio", exist_ok=True)


    os.makedirs("trade_reports", exist_ok=True)





# 检查系统依赖


def check_dependencies():


    """检查系统依赖是否已安装"""


    try:


        import telegram


        import pandas as pd


        import numpy as np


        import matplotlib


        import fastapi


        import uvicorn


        import seaborn


        import edge_tts


        


        return True


    except ImportError as e:


        print(f"❌ 依赖检查失败: {str(e)}")


        print("请确保已安装所有必要的Python包。运行: pip install -r requirements.txt")


        return False





# 启动助手


def start_assistant(args):


    """启动AI交易助手"""


    try:


        # 导入助手组件


        from utils.ai_trader_workflow import trader_workflow


        from utils.telegram_ai_assistant import telegram_assistant


        


        # 启动交易工作流


        trader_workflow.start_workflow(webhook_port=args.port)


        


        # 启动Telegram助手


        telegram_thread = telegram_assistant.start_background()


        


        # 发送启动通知


        trader_workflow._send_startup_notification()


        


        return telegram_thread


    except Exception as e:


        print(f"❌ 启动助手失败: {str(e)}")


        if args.debug:


            import traceback


            traceback.print_exc()


        sys.exit(1)





# 设置定时报告


def setup_scheduled_reports():


    """设置定时报告"""


    try:


        import schedule


        from utils.ai_daily_reporter import daily_reporter


        


        # 示例策略数据提供函数


        def get_strategy_data():


            # 实际应用中应从数据库或交易系统获取


            return [


                {


                    "name": "Mean Reversion",


                    "pnl": 340.50,


                    "win_rate": 0.65,


                    "trades": 20,


                    "max_drawdown": 120.30,


                    "pnl_series": [50, -30, 80, 120, -20, 70, 150, -80]


                },


                {


                    "name": "Gamma Scalping",


                    "pnl": 520.75,


                    "win_rate": 0.72,


                    "trades": 25,


                    "max_drawdown": 90.50,


                    "pnl_series": [80, 120, -50, 90, 130, 150, -40, 40]


                },


                {


                    "name": "Breakout V2",


                    "pnl": -120.25,


                    "win_rate": 0.40,


                    "trades": 15,


                    "max_drawdown": 200.10,


                    "pnl_series": [-40, -60, 30, -50, 70, -70, -10, 10]


                }


            ]


        


        # 示例市场数据提供函数


        def get_market_data():


            # 实际应用中应从市场数据源获取


            return {


                "spy_change": "+0.5%",


                "vix": "14.3",


                "market_sentiment": "中性偏多",


                "sector_performance": "科技+1.2%, 金融-0.3%",


                "notable_events": "无重大事件"


            }


        


        # 设置每日报告 - 市场收盘后 (16:10)


        schedule.every().day.at("16:10").do(


            daily_reporter.generate_report_on_schedule,


            strategies_data_provider=get_strategy_data,


            market_data_provider=get_market_data,


            report_type="daily"


        )


        


        # 设置每周报告 - 每周五收盘后 (16:30)


        schedule.every().friday.at("16:30").do(


            daily_reporter.generate_report_on_schedule,


            strategies_data_provider=get_strategy_data,


            market_data_provider=get_market_data,


            report_type="weekly"


        )


        


        # 设置每月报告 - 每月最后一个交易日 (这里简化为每月最后一天)


        # 实际应用中应判断是否为交易日


        def monthly_report_check():


            now = datetime.now()


            # 简化判断，检查是否为月末


            next_day = now.replace(day=28) + timedelta(days=4)


            end_of_month = next_day - timedelta(days=next_day.day)


            return now.day == end_of_month.day


        


        schedule.every().day.at("17:00").do(


            lambda: monthly_report_check() and daily_reporter.generate_report_on_schedule(


                strategies_data_provider=get_strategy_data,


                market_data_provider=get_market_data,


                report_type="monthly"


            )


        )


        


        # 启动定时器线程


        def run_scheduler():


            while True:


                schedule.run_pending()


                time.sleep(60)  # 每分钟检查一次


        


        scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)


        scheduler_thread.start()


        


        return scheduler_thread


    except Exception as e:


        logging.error(f"设置定时报告时出错: {str(e)}")


        return None





# 主函数


def main():


    """主函数"""


    parser = argparse.ArgumentParser(description="AI交易助手系统启动器")


    parser.add_argument("--port", type=int, default=8000, help="Webhook服务器端口")


    parser.add_argument("--debug", action="store_true", help="启用调试模式")


    parser.add_argument("--demo", action="store_true", help="启用演示模式（使用模拟数据）")


    parser.add_argument("--test-message", action="store_true", help="发送测试消息到Telegram并退出")


    args = parser.parse_args()


    


    # 设置环境变量


    setup_environment()


    


    # 配置日志


    log_level = logging.DEBUG if args.debug else logging.INFO


    setup_logging(log_level)


    


    # 打印欢迎信息


    print_welcome_message()


    


    # 创建临时目录


    create_temp_directories()


    


    # 检查依赖


    if not check_dependencies():


        sys.exit(1)


    


    # 如果只需要发送测试消息


    if args.test_message:


        try:


            from utils.ai_trader_workflow import trader_workflow


            


            print("发送测试消息到Telegram...")


            success = trader_workflow._send_to_telegram("🧪 *AI交易助手测试消息*\n\n系统连接正常，消息推送功能测试成功。")


            


            if success:


                print("✅ 测试消息发送成功！")


            else:


                print("❌ 测试消息发送失败，请检查Telegram配置。")


                


            sys.exit(0 if success else 1)


        except Exception as e:


            print(f"❌ 发送测试消息时出错: {str(e)}")


            sys.exit(1)


    


    # 启动AI交易助手


    try:


        print(f"🚀 正在启动AI交易助手系统 (端口: {args.port})...")


        


        # 导入模块（在设置好环境变量之后）


        from utils.ai_trader_workflow import trader_workflow


        from utils.ai_voice_summarizer import voice_summarizer


        from utils.ai_chart_reporter import chart_reporter


        from utils.ai_daily_reporter import daily_reporter


        from api.market_event_watcher import event_watcher


        from utils.telegram_ai_assistant import telegram_assistant


        


        # 设置演示模式


        if args.demo:


            print("🎮 已启用演示模式，将使用模拟数据")


            # 这里可以添加演示模式的特殊配置


        


        # 启动工作流


        trader_workflow.start_workflow(webhook_port=args.port)


        


        # 启动Telegram助手


        telegram_thread = telegram_assistant.start_background()


        


        # 设置定时报告


        scheduler_thread = setup_scheduled_reports()


        


        print(f"""


        ✅ AI交易助手系统已成功启动!


        


        🌐 Webhook服务器运行在: http://localhost:{args.port}


        📊 支持以下Webhook端点:


          - TradingView: http://localhost:{args.port}/webhook/tradingview


          - Polygon.io: http://localhost:{args.port}/webhook/polygon


          - IBKR: http://localhost:{args.port}/webhook/ibkr


          - 通用: http://localhost:{args.port}/webhook


        


        📋 当前安排的工作流任务:


          - 盘前准备: 每日 07:00-08:30


          - 盘中高频状态: 交易时段内动态更新


          - 午盘重估: 12:00-12:30


          - 盘后总结: 16:00-18:00


          - 夜盘风险评估: 20:00-21:00


        


        📱 推送已配置到 Telegram


        


        按 Ctrl+C 停止服务


        """)


        


        # 保持主程序运行


        while True:


            time.sleep(1)


            


    except KeyboardInterrupt:


        print("\n⏹️ 用户中断，正在停止服务...")


        try:


            trader_workflow.stop_workflow()


            telegram_assistant.stop()


        except:


            pass


        print("✅ 服务已停止")


    except Exception as e:


        print(f"❌ 启动AI交易助手时出错: {str(e)}")


        if args.debug:


            import traceback


            traceback.print_exc()


        sys.exit(1)





if __name__ == "__main__":


    main() 