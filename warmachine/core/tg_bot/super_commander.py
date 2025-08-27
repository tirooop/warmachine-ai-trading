"""
Super Commander for WarMachine - 整合所有高级功能的Telegram机器人
"""

import logging
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from ..shared_interfaces import (
    AIAnalyzerProtocol,
    MarketDataProtocol,
    TradingHandlerProtocol,
    NotificationProtocol
)
from ..ai_event_pool import AIEvent, EventCategory, EventPriority
from ..abstractions.notifications import IAlertGenerator
from ai_engine.ai_model_router import AIModelRouter
from trading.ai_feedback_learner import AIFeedbackLearner

logger = logging.getLogger(__name__)

class SuperCommander:
    """整合所有高级功能的Telegram机器人指挥官"""
    
    def __init__(self, config: Dict[str, Any],
                 ai_analyzer: Optional[AIAnalyzerProtocol] = None,
                 market_data: Optional[MarketDataProtocol] = None,
                 trading_handler: Optional[TradingHandlerProtocol] = None,
                 notification_system: Optional[NotificationProtocol] = None,
                 alert_generator: Optional[IAlertGenerator] = None):
        """
        初始化超级指挥官
        
        Args:
            config: 配置字典
            ai_analyzer: AI分析器实例
            market_data: 市场数据提供者实例
            trading_handler: 交易处理器实例
            notification_system: 通知系统实例
            alert_generator: 告警生成器实例
        """
        self.config = config
        self.telegram_config = config["telegram"]
        self.token = self.telegram_config["token"]
        self.admin_chat_id = self.telegram_config["admin_chat_id"]
        self.broadcast_channels = self.telegram_config["broadcast_channels"]
        self.allowed_users = self.telegram_config["allowed_users"]
        
        # 初始化所有组件
        
        # 初始化AI相关组件
        self.ai_analyzer = ai_analyzer
        self.ai_alert_generator = alert_generator
        self.ai_model_router = AIModelRouter(config)
        self.ai_feedback_learner = AIFeedbackLearner(config)
        
        # 初始化机器人
        self.app = Application.builder().token(self.token).build()
        
        # 注册所有处理器
        self._register_handlers()
        
        logger.info("Super Commander initialized with all advanced features")
        
        self.scheduler = AsyncIOScheduler()
        self.scheduler.add_job(self.push_daily_ai_report, 'cron', hour=9, minute=0)
        self.scheduler.start()
    
    def _register_handlers(self):
        """注册所有命令处理器"""
        # 基础命令
        self.app.add_handler(CommandHandler("start", self._handle_start))
        self.app.add_handler(CommandHandler("help", self._handle_help))
        self.app.add_handler(CommandHandler("status", self._handle_status))
        
        # 交易相关命令
        self.app.add_handler(CommandHandler("trade", self._handle_trade))
        self.app.add_handler(CommandHandler("position", self._handle_position))
        self.app.add_handler(CommandHandler("balance", self._handle_balance))
        
        # 策略相关命令
        self.app.add_handler(CommandHandler("strategy", self._handle_strategy))
        self.app.add_handler(CommandHandler("backtest", self._handle_backtest))
        self.app.add_handler(CommandHandler("optimize", self._handle_optimize))
        
        # 告警相关命令
        self.app.add_handler(CommandHandler("alert", self._handle_alert))
        self.app.add_handler(CommandHandler("subscribe", self._handle_subscribe))
        self.app.add_handler(CommandHandler("unsubscribe", self._handle_unsubscribe))
        self.app.add_handler(CommandHandler("alert_template", self._handle_alert_template))
        self.app.add_handler(CommandHandler("alert_priority", self._handle_alert_priority))
        self.app.add_handler(CommandHandler("alert_feedback", self._handle_alert_feedback))
        self.app.add_handler(CommandHandler("alert_group", self._handle_alert_group))
        
        # AI相关命令
        self.app.add_handler(CommandHandler("ai_analyze", self._handle_ai_analyze))
        self.app.add_handler(CommandHandler("ai_learn", self._handle_ai_learn))
        self.app.add_handler(CommandHandler("ai_model", self._handle_ai_model))
        self.app.add_handler(CommandHandler("ai_report", self._handle_ai_report))
        self.app.add_handler(CommandHandler("ai_signal", self._handle_ai_signal))
        self.app.add_handler(CommandHandler("ai_sentiment", self._handle_ai_sentiment))
        self.app.add_handler(CommandHandler("backtest", self._handle_backtest))
        self.app.add_handler(CommandHandler("backtest_detail", self._handle_backtest_detail))
        self.app.add_handler(CommandHandler("strategy_evolution", self._handle_strategy_evolution))
        self.app.add_handler(CommandHandler("quote", self._handle_quote))
        self.app.add_handler(CommandHandler("kline", self._handle_kline))
        self.app.add_handler(CommandHandler("position", self._handle_position))
        self.app.add_handler(CommandHandler("asset", self._handle_asset))
        self.app.add_handler(CommandHandler("order", self._handle_order))
        self.app.add_handler(CommandHandler("notify", self._handle_notify))
        self.app.add_handler(CommandHandler("subscribe", self._handle_subscribe))
        self.app.add_handler(CommandHandler("unsubscribe", self._handle_unsubscribe))
        self.app.add_handler(CommandHandler("report", self._handle_report))
        self.app.add_handler(CommandHandler("performance", self._handle_performance))
        self.app.add_handler(CommandHandler("dashboard", self._handle_dashboard))
        
        # 系统相关命令
        self.app.add_handler(CommandHandler("settings", self._handle_settings))
        self.app.add_handler(CommandHandler("language", self._handle_language))
        
        # 消息处理器
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_message))
        
        # 回调查询处理器
        self.app.add_handler(CallbackQueryHandler(self._handle_callback))
    
    async def start(self):
        """启动机器人"""
        try:
            # 初始化应用
            await self.app.initialize()
            await self.app.start()
            
            # 启动轮询
            logger.info("Starting bot polling...")
            await self.app.updater.start_polling()
            
            # 保持运行
            while True:
                await asyncio.sleep(1)
            
        except Exception as e:
            logger.error(f"Error running bot: {str(e)}")
            try:
                await self.stop()
            except Exception as cleanup_error:
                logger.error(f"Error during cleanup: {str(cleanup_error)}")
            raise
    
    async def stop(self):
        """停止机器人"""
        try:
            if self.app.running:
                await self.app.stop()
                await self.app.shutdown()
                logger.info("Bot stopped successfully")
            else:
                logger.info("Bot was not running")
        except Exception as e:
            logger.error(f"Error stopping bot: {str(e)}")
            raise
    
    async def _handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理 /start 命令"""
        try:
            user = update.effective_user
            keyboard = [
                ["/ai_report", "/backtest", "/quote AAPL"],
                ["/position", "/asset", "/performance"],
                ["/help"]
            ]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            await update.message.reply_text("欢迎使用WarMachine，请选择功能：", reply_markup=reply_markup)
            
            # 记录新用户
            logger.info(f"New user started the bot: {user.id} ({user.first_name})")
            
        except Exception as e:
            logger.error(f"Error in _handle_start: {str(e)}", exc_info=True)
            await update.message.reply_text("抱歉，启动时发生错误。请稍后重试。")
    
    async def _handle_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理帮助命令"""
        help_text = (
            "🤖 *WarMachine Trading Bot 帮助*\n\n"
            "*基础命令：*\n"
            "/start - 启动机器人\n"
            "/help - 显示此帮助信息\n"
            "/status - 显示系统状态\n\n"
            
            "*交易命令：*\n"
            "/trade - 执行交易操作\n"
            "/position - 查看当前持仓\n"
            "/balance - 查看账户余额\n\n"
            
            "*策略命令：*\n"
            "/strategy - 管理交易策略\n"
            "/backtest - 执行回测\n"
            "/optimize - 优化策略参数\n\n"
            
            "*告警命令：*\n"
            "/alert - 管理交易告警\n"
            "/subscribe - 订阅告警\n"
            "/unsubscribe - 取消订阅\n"
            "/alert_template - 管理告警模板\n"
            "/alert_priority - 设置告警优先级\n"
            "/alert_feedback - 管理告警反馈\n"
            "/alert_group - 管理告警分组\n\n"
            
            "*AI命令：*\n"
            "/ai_analyze - 执行AI市场分析\n"
            "/ai_learn - 管理AI学习\n"
            "/ai_model - 管理AI模型\n"
            "/ai_report - 查看AI分析报告\n"
            "/ai_signal - 查看AI智能信号\n"
            "/ai_sentiment - 查看市场情绪分析\n"
            "/backtest - 查看策略回测摘要\n"
            "/backtest_detail - 查看回测详细信号\n"
            "/strategy_evolution - 查看策略进化报告\n"
            "/quote - 查看股票实时行情\n"
            "/kline - 查看股票日K线\n"
            "/position - 查看当前持仓\n"
            "/asset - 查看账户资产\n"
            "/order - 查看订单状态\n"
            "/notify - 发送通知消息\n"
            "/subscribe - 订阅告警\n"
            "/unsubscribe - 取消订阅\n"
            "/report - 查看最新日报/周报\n"
            "/performance - 查看策略表现\n"
            "/dashboard - 访问可视化仪表盘\n\n"
            
            "*系统命令：*\n"
            "/settings - 管理系统设置\n"
            "/language - 设置语言\n\n"
            
            "使用 /help <命令> 获取特定命令的详细帮助"
        )
        
        if context.args:
            command = context.args[0].lower().lstrip('/')
            detailed_help = self._get_command_help(command)
            if detailed_help:
                await update.message.reply_text(detailed_help, parse_mode='Markdown')
            else:
                await update.message.reply_text(f"未找到命令 {command} 的详细帮助")
        else:
            await update.message.reply_text(help_text, parse_mode='Markdown')
    
    def _get_command_help(self, command: str) -> str:
        """获取特定命令的详细帮助"""
        help_texts = {
            'trade': (
                "*交易命令帮助*\n\n"
                "用法：/trade <操作> [参数]\n\n"
                "可用操作：\n"
                "- buy <交易对> <数量> - 买入\n"
                "- sell <交易对> <数量> - 卖出\n"
                "- cancel <订单ID> - 取消订单\n"
                "- list - 列出所有订单"
            ),
            'position': (
                "*持仓命令帮助*\n\n"
                "用法：/position [交易对]\n\n"
                "参数：\n"
                "- 交易对：可选，指定要查看的交易对\n"
                "不带参数时显示所有持仓"
            ),
            'balance': (
                "*余额命令帮助*\n\n"
                "用法：/balance [币种]\n\n"
                "参数：\n"
                "- 币种：可选，指定要查看的币种\n"
                "不带参数时显示所有余额"
            ),
            'strategy': (
                "*策略命令帮助*\n\n"
                "用法：/strategy <操作> [参数]\n\n"
                "可用操作：\n"
                "- list - 列出所有策略\n"
                "- info <策略ID> - 查看策略详情\n"
                "- create <名称> - 创建新策略\n"
                "- delete <策略ID> - 删除策略"
            ),
            'backtest': (
                "*回测命令帮助*\n\n"
                "用法：/backtest <策略ID> [参数]\n\n"
                "参数：\n"
                "- 开始时间：可选，格式 YYYY-MM-DD\n"
                "- 结束时间：可选，格式 YYYY-MM-DD\n"
                "- 初始资金：可选，默认 10000"
            ),
            'optimize': (
                "*优化命令帮助*\n\n"
                "用法：/optimize <策略ID> [参数]\n\n"
                "参数：\n"
                "- 参数范围：可选，指定要优化的参数范围\n"
                "- 优化目标：可选，指定优化目标"
            ),
            'alert': (
                "*告警命令帮助*\n\n"
                "用法：/alert <操作> [参数]\n\n"
                "可用操作：\n"
                "- create <条件> - 创建告警\n"
                "- list - 列出所有告警\n"
                "- delete <告警ID> - 删除告警"
            ),
            'subscribe': (
                "*订阅命令帮助*\n\n"
                "用法：/subscribe <告警ID>\n\n"
                "参数：\n"
                "- 告警ID：要订阅的告警ID"
            ),
            'unsubscribe': (
                "*取消订阅命令帮助*\n\n"
                "用法：/unsubscribe <告警ID>\n\n"
                "参数：\n"
                "- 告警ID：要取消订阅的告警ID"
            ),
            'alert_template': (
                "*告警模板命令帮助*\n\n"
                "用法：/alert_template <操作> [参数]\n\n"
                "可用操作：\n"
                "- create <名称> <内容> - 创建模板\n"
                "- delete <名称> - 删除模板\n"
                "- edit <名称> <新内容> - 编辑模板"
            ),
            'alert_priority': (
                "*告警优先级命令帮助*\n\n"
                "用法：/alert_priority <操作> [参数]\n\n"
                "可用操作：\n"
                "- set <告警ID> <优先级> - 设置优先级"
            ),
            'alert_feedback': (
                "*告警反馈命令帮助*\n\n"
                "用法：/alert_feedback <操作> [参数]\n\n"
                "可用操作：\n"
                "- add <告警ID> <反馈> - 添加反馈\n"
                "- list <告警ID> - 查看反馈"
            ),
            'alert_group': (
                "*告警分组命令帮助*\n\n"
                "用法：/alert_group <操作> [参数]\n\n"
                "可用操作：\n"
                "- create <名称> <描述> - 创建分组\n"
                "- add <分组> <告警ID> - 添加告警\n"
                "- remove <分组> <告警ID> - 移除告警"
            ),
            'ai_analyze': (
                "*AI分析命令帮助*\n\n"
                "用法：/ai_analyze <交易对>\n\n"
                "参数：\n"
                "- 交易对：要分析的交易对"
            ),
            'ai_learn': (
                "*AI学习命令帮助*\n\n"
                "用法：/ai_learn <操作>\n\n"
                "可用操作：\n"
                "- start - 启动学习\n"
                "- stop - 停止学习"
            ),
            'ai_model': (
                "*AI模型命令帮助*\n\n"
                "用法：/ai_model <操作> [参数]\n\n"
                "可用操作：\n"
                "- switch <模型名称> - 切换模型"
            ),
            'settings': (
                "*设置命令帮助*\n\n"
                "用法：/settings <操作> [参数]\n\n"
                "可用操作：\n"
                "- list - 显示所有设置\n"
                "- set <设置项> <值> - 修改设置"
            ),
            'language': (
                "*语言命令帮助*\n\n"
                "用法：/language <语言代码>\n\n"
                "参数：\n"
                "- 语言代码：要切换的语言代码（如 zh, en）"
            ),
            'ai_report': (
                "*AI分析报告命令帮助*\n\n"
                "用法：/ai_report\n\n"
                "参数：无"
            ),
            'ai_signal': (
                "*AI智能信号命令帮助*\n\n"
                "用法：/ai_signal\n\n"
                "参数：无"
            ),
            'ai_sentiment': (
                "*市场情绪分析命令帮助*\n\n"
                "用法：/ai_sentiment\n\n"
                "参数：无"
            ),
            'backtest': (
                "*策略回测摘要命令帮助*\n\n"
                "用法：/backtest\n\n"
                "参数：无"
            ),
            'backtest_detail': (
                "*回测详细信号命令帮助*\n\n"
                "用法：/backtest_detail\n\n"
                "参数：无"
            ),
            'strategy_evolution': (
                "*策略进化报告命令帮助*\n\n"
                "用法：/strategy_evolution\n\n"
                "参数：无"
            ),
            'quote': (
                "*股票实时行情命令帮助*\n\n"
                "用法：/quote <股票代码>\n\n"
                "参数：\n"
                "- 股票代码：要查询的股票代码"
            ),
            'kline': (
                "*股票日K线命令帮助*\n\n"
                "用法：/kline <股票代码>\n\n"
                "参数：\n"
                "- 股票代码：要查询的股票代码"
            ),
            'position': (
                "*当前持仓命令帮助*\n\n"
                "用法：/position\n\n"
                "参数：无"
            ),
            'asset': (
                "*账户资产命令帮助*\n\n"
                "用法：/asset\n\n"
                "参数：无"
            ),
            'order': (
                "*订单状态命令帮助*\n\n"
                "用法：/order <订单ID>\n\n"
                "参数：\n"
                "- 订单ID：要查询的订单ID"
            ),
            'notify': (
                "*发送通知消息命令帮助*\n\n"
                "用法：/notify <消息>\n\n"
                "参数：\n"
                "- 消息：要发送的消息"
            ),
            'report': (
                "*最新日报/周报命令帮助*\n\n"
                "用法：/report\n\n"
                "参数：无"
            ),
            'performance': (
                "*策略表现命令帮助*\n\n"
                "用法：/performance\n\n"
                "参数：无"
            ),
            'dashboard': (
                "*可视化仪表盘命令帮助*\n\n"
                "用法：/dashboard\n\n"
                "参数：无"
            )
        }
        return help_texts.get(command, None)
    
    def _is_user_allowed(self, user_id: int) -> bool:
        """检查用户是否有权限使用机器人"""
        return str(user_id) in self.allowed_users
    
    async def _handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理自然语言消息"""
        try:
            user_id = str(update.effective_user.id)
            if not self._is_user_allowed(user_id):
                await update.message.reply_text("抱歉，您没有权限使用此机器人。")
                return
            
            text = update.message.text
            logger.info(f"Received message from user {user_id}: {text}")
            
            # 使用自然语言处理器
            response = await self.nl_processor.process_message(text)
            
            # 如果响应包含交易查询，处理它
            if isinstance(response, dict) and "trading_query" in response:
                query = response["trading_query"]
                result = await self.trading_handler.process_query(**query)
                
                if result["success"]:
                    await update.message.reply_text(result["message"])
                else:
                    await update.message.reply_text(f"错误: {result['error']}")
            
            # 如果响应包含 MCP 命令，发送到 MCP 服务器
            elif isinstance(response, dict) and "mcp_command" in response:
                mcp_response = await self.mcp_connector.send_command(
                    response["mcp_command"],
                    response.get("params", {})
                )
                
                if mcp_response.success:
                    await update.message.reply_text(
                        f"命令执行成功: {mcp_response.data.get('message', '')}"
                    )
                else:
                    await update.message.reply_text(
                        f"执行命令时出错: {mcp_response.error}"
                    )
            else:
                await update.message.reply_text(response)
            
            logger.info(f"Message processed and response sent to user {user_id}")
            
        except Exception as e:
            logger.error(f"Error in _handle_message: {str(e)}", exc_info=True)
            await update.message.reply_text("抱歉，处理消息时发生错误。请稍后重试。")
    
    async def _handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理回调查询"""
        try:
            query = update.callback_query
            await query.answer()
            
            # 解析回调数据
            callback_data = query.data.split('_')
            action = callback_data[0]
            category = callback_data[1] if len(callback_data) > 1 else None
            
            if action == "menu":
                # 处理主菜单按钮
                if category == "market":
                    message = (
                        "📊 市场数据\n\n"
                        "可用命令：\n"
                        "- /price <交易对> - 查询价格\n"
                        "- /volume <交易对> - 分析交易量\n"
                        "- /technical <交易对> - 技术分析\n"
                        "- /fundamental <交易对> - 基本面分析\n"
                        "- /ai_analysis <交易对> - AI 智能分析\n"
                        "- /chart <交易对> - 生成图表\n\n"
                        "💡 提示：您可以直接输入自然语言来使用这些功能，例如：\n"
                        "- '显示 BTC 的价格'\n"
                        "- '分析 ETH 的技术面'\n"
                        "- '生成 BTC 的图表'"
                    )
                elif category == "trading":
                    message = (
                        "💼 交易管理\n\n"
                        "可用命令：\n"
                        "- /portfolio - 查看投资组合\n"
                        "- /strategy - 管理交易策略\n"
                        "- /backtest - 运行回测\n"
                        "- /optimize - 优化策略\n"
                        "- /deploy - 部署策略\n\n"
                        "💡 提示：您可以直接输入自然语言来使用这些功能，例如：\n"
                        "- '显示我的投资组合'\n"
                        "- '创建新的交易策略'\n"
                        "- '运行策略回测'"
                    )
                elif category == "alerts":
                    message = (
                        "🔔 告警系统\n\n"
                        "可用命令：\n"
                        "- /alert - 管理告警\n"
                        "- /subscribe - 管理订阅\n"
                        "- /unsubscribe - 取消订阅\n\n"
                        "💡 提示：您可以直接输入自然语言来使用这些功能，例如：\n"
                        "- '创建价格突破告警'\n"
                        "- '订阅 BTC 的价格通知'\n"
                        "- '取消所有告警'"
                    )
                elif category == "settings":
                    message = (
                        "⚙️ 系统设置\n\n"
                        "可用命令：\n"
                        "- /settings - 系统设置\n"
                        "- /voice - 语音设置\n"
                        "- /language - 语言设置\n\n"
                        "💡 提示：您可以直接输入自然语言来使用这些功能，例如：\n"
                        "- '更改系统语言'\n"
                        "- '设置语音通知'\n"
                        "- '导出系统设置'"
                    )
                elif category == "help":
                    message = (
                        "❓ 使用帮助\n\n"
                        "基本命令：\n"
                        "- /start - 启动机器人\n"
                        "- /help - 显示帮助信息\n"
                        "- /help <命令> - 显示特定命令的详细说明\n\n"
                        "💡 提示：\n"
                        "- 所有命令都支持自然语言输入\n"
                        "- 使用 /help <命令> 获取详细说明\n"
                        "- 设置中的参数可以通过 /settings 命令查看和修改"
                    )
                else:
                    message = "无效的菜单选项。请使用 /start 重新开始。"
                
                # 创建返回主菜单按钮
                keyboard = [[InlineKeyboardButton("🏠 返回主菜单", callback_data="menu_main")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(text=message, reply_markup=reply_markup)
            
            elif action == "help":
                # 处理帮助菜单按钮
                if category == "market":
                    message = (
                        "📊 市场数据命令帮助\n\n"
                        "1. 价格查询 (/price)\n"
                        "   - 显示实时价格\n"
                        "   - 24小时涨跌幅\n"
                        "   - 交易量信息\n"
                        "   - 价格趋势\n\n"
                        "2. 交易量分析 (/volume)\n"
                        "   - 24小时交易量\n"
                        "   - 交易量趋势\n"
                        "   - 大单分析\n"
                        "   - 流动性分析\n\n"
                        "3. 技术分析 (/technical)\n"
                        "   - 技术指标分析\n"
                        "   - 趋势分析\n"
                    f"📊 回测结果: {strategy_name}\n\n"
                    f"交易对: {symbol}\n"
                    f"时间范围: {start_date} 至 {end_date}\n\n"
                    f"总收益率: {backtest_data['total_return']}%\n"
                    f"年化收益率: {backtest_data['annual_return']}%\n"
                    f"最大回撤: {backtest_data['max_drawdown']}%\n"
                    f"夏普比率: {backtest_data['sharpe_ratio']}\n"
                    f"胜率: {backtest_data['win_rate']}%\n"
                    f"交易次数: {backtest_data['total_trades']}\n\n"
                    f"详细报告:\n{backtest_data['detailed_report']}"
                )
                
                # 更新状态消息
                await status_message.edit_text(message)
                
                # 如果有图表，发送图表
                if "chart_url" in backtest_data:
                    await update.message.reply_photo(
                        photo=backtest_data["chart_url"],
                        caption="回测结果图表"
                    )
            else:
                await status_message.edit_text(f"回测失败: {result['error']}")
        
        except Exception as e:
            logger.error(f"Error in _handle_backtest: {str(e)}", exc_info=True)
            await update.message.reply_text("抱歉，执行回测时发生错误。请稍后重试。")
    
    async def _handle_optimize(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理 /optimize 命令"""
        try:
            if not context.args:
                await update.message.reply_text(
                    "请提供策略名称和优化参数，例如：\n"
                    "/optimize MyStrategy BTCUSDT 2023-01-01 2023-12-31"
                )
                return
            
            if len(context.args) < 4:
                await update.message.reply_text(
                    "请提供完整的优化参数：\n"
                    "策略名称、交易对、开始日期、结束日期"
                )
                return
            
            strategy_name = context.args[0]
            symbol = context.args[1].upper()
            start_date = context.args[2]
            end_date = context.args[3]
            
            # 发送开始优化的消息
            status_message = await update.message.reply_text(
                f"⚡ 开始优化策略 {strategy_name}...\n"
                f"交易对: {symbol}\n"
                f"时间范围: {start_date} 至 {end_date}"
            )
            
            # 执行优化
            result = await self.sandbox.optimize_strategy(
                strategy_name,
                symbol,
                start_date,
                end_date
            )
            
            if result["success"]:
                optimize_data = result["data"]
                message = (
                    f"⚡ 优化结果: {strategy_name}\n\n"
                    f"交易对: {symbol}\n"
                    f"时间范围: {start_date} 至 {end_date}\n\n"
                    f"优化前性能:\n"
                    f"- 总收益率: {optimize_data['before']['total_return']}%\n"
                    f"- 年化收益率: {optimize_data['before']['annual_return']}%\n"
                    f"- 最大回撤: {optimize_data['before']['max_drawdown']}%\n"
                    f"- 夏普比率: {optimize_data['before']['sharpe_ratio']}\n\n"
                    f"优化后性能:\n"
                    f"- 总收益率: {optimize_data['after']['total_return']}%\n"
                    f"- 年化收益率: {optimize_data['after']['annual_return']}%\n"
                    f"- 最大回撤: {optimize_data['after']['max_drawdown']}%\n"
                    f"- 夏普比率: {optimize_data['after']['sharpe_ratio']}\n\n"
                    f"优化参数:\n"
                )
                
                for param, value in optimize_data["parameters"].items():
                    message += f"- {param}: {value}\n"
                
                message += f"\n详细报告:\n{optimize_data['detailed_report']}"
                
                # 更新状态消息
                await status_message.edit_text(message)
                
                # 如果有图表，发送图表
                if "chart_url" in optimize_data:
                    await update.message.reply_photo(
                        photo=optimize_data["chart_url"],
                        caption="优化结果对比图表"
                    )
            else:
                await status_message.edit_text(f"优化失败: {result['error']}")
        
        except Exception as e:
            logger.error(f"Error in _handle_optimize: {str(e)}", exc_info=True)
            await update.message.reply_text("抱歉，执行优化时发生错误。请稍后重试。")
    
    async def _handle_deploy(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理 /deploy 命令"""
        try:
            if not context.args:
                await update.message.reply_text(
                    "请提供策略名称和部署参数，例如：\n"
                    "/deploy MyStrategy BTCUSDT"
                )
                return
            
            if len(context.args) < 2:
                await update.message.reply_text(
                    "请提供策略名称和交易对"
                )
                return
            
            strategy_name = context.args[0]
            symbol = context.args[1].upper()
            
            # 发送开始部署的消息
            status_message = await update.message.reply_text(
                f"🚀 开始部署策略 {strategy_name}...\n"
                f"交易对: {symbol}"
            )
            
            # 执行部署
            result = await self.sandbox.deploy_strategy(strategy_name, symbol)
            
            if result["success"]:
                deploy_data = result["data"]
                message = (
                    f"🚀 策略部署成功！\n\n"
                    f"策略名称: {deploy_data['strategy_name']}\n"
                    f"交易对: {deploy_data['symbol']}\n"
                    f"部署时间: {deploy_data['deploy_time']}\n"
                    f"状态: {deploy_data['status']}\n\n"
                    f"配置信息:\n"
                )
                
                for key, value in deploy_data["config"].items():
                    message += f"- {key}: {value}\n"
                
                message += f"\n监控信息:\n"
                for key, value in deploy_data["monitoring"].items():
                    message += f"- {key}: {value}\n"
                
                # 更新状态消息
                await status_message.edit_text(message)
            else:
                await status_message.edit_text(f"部署失败: {result['error']}")
        
        except Exception as e:
            logger.error(f"Error in _handle_deploy: {str(e)}", exc_info=True)
            await update.message.reply_text("抱歉，部署策略时发生错误。请稍后重试。")
    
    async def _handle_alert(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理 /alert 命令"""
        try:
            if not context.args:
                # 显示当前告警列表
                result = await self.alert_engine.list_alerts()
                
                if result["success"]:
                    message = "🔔 当前告警列表\n\n"
                    
                    for alert in result["data"]["alerts"]:
                        message += (
                            f"ID: {alert['id']}\n"
                            f"类型: {alert['type']}\n"
                            f"条件: {alert['condition']}\n"
                            f"优先级: {alert['priority']}\n"
                            f"状态: {alert['status']}\n"
                            f"创建时间: {alert['created_at']}\n\n"
                        )
                    
                    await update.message.reply_text(message)
                else:
                    await update.message.reply_text(f"获取告警列表失败: {result['error']}")
                return
            
            # 处理子命令
            subcommand = context.args[0].lower()
            
            if subcommand == "create":
                if len(context.args) < 3:
                    await update.message.reply_text(
                        "请提供告警类型和条件，例如：\n"
                        "/alert create price BTCUSDT > 50000"
                    )
                    return
                
                alert_type = context.args[1]
                condition = " ".join(context.args[2:])
                
                result = await self.alert_engine.create_alert(alert_type, condition)
                
                if result["success"]:
                    await update.message.reply_text(
                        f"告警创建成功！\n"
                        f"ID: {result['data']['id']}\n"
                        f"类型: {result['data']['type']}\n"
                        f"条件: {result['data']['condition']}\n"
                        f"优先级: {result['data']['priority']}\n"
                        f"创建时间: {result['data']['created_at']}"
                    )
                else:
                    await update.message.reply_text(f"创建告警失败: {result['error']}")
            
            elif subcommand == "edit":
                if len(context.args) < 3:
                    await update.message.reply_text(
                        "请提供告警ID和新条件，例如：\n"
                        "/alert edit 123 BTCUSDT > 55000"
                    )
                    return
                
                alert_id = context.args[1]
                condition = " ".join(context.args[2:])
                
                result = await self.alert_engine.edit_alert(alert_id, condition)
                
                if result["success"]:
                    await update.message.reply_text(
                        f"告警更新成功！\n"
                        f"ID: {result['data']['id']}\n"
                        f"类型: {result['data']['type']}\n"
                        f"新条件: {result['data']['condition']}\n"
                        f"更新时间: {result['data']['updated_at']}"
                    )
                else:
                    await update.message.reply_text(f"更新告警失败: {result['error']}")
            
            elif subcommand == "delete":
                if len(context.args) < 2:
                    await update.message.reply_text(
                        "请提供告警ID，例如：\n"
                        "/alert delete 123"
                    )
                    return
                
                alert_id = context.args[1]
                
                result = await self.alert_engine.delete_alert(alert_id)
                
                if result["success"]:
                    await update.message.reply_text(f"告警 {alert_id} 已成功删除！")
                else:
                    await update.message.reply_text(f"删除告警失败: {result['error']}")
            
            elif subcommand == "info":
                if len(context.args) < 2:
                    await update.message.reply_text(
                        "请提供告警ID，例如：\n"
                        "/alert info 123"
                    )
                    return
                
                alert_id = context.args[1]
                
                result = await self.alert_engine.get_alert_info(alert_id)
                
                if result["success"]:
                    alert = result["data"]
                    message = (
                        f"🔔 告警信息: {alert['id']}\n\n"
                        f"类型: {alert['type']}\n"
                        f"条件: {alert['condition']}\n"
                        f"优先级: {alert['priority']}\n"
                        f"状态: {alert['status']}\n"
                        f"创建时间: {alert['created_at']}\n"
                        f"最后触发: {alert['last_triggered']}\n\n"
                        f"触发历史:\n"
                    )
                    
                    for trigger in alert["trigger_history"]:
                        message += (
                            f"- 时间: {trigger['time']}\n"
                            f"  值: {trigger['value']}\n"
                            f"  消息: {trigger['message']}\n"
                        )
                    
                    await update.message.reply_text(message)
                else:
                    await update.message.reply_text(f"获取告警信息失败: {result['error']}")
            
            else:
                await update.message.reply_text(
                    "无效的子命令。可用命令：\n"
                    "- create: 创建新告警\n"
                    "- edit: 编辑告警\n"
                    "- delete: 删除告警\n"
                    "- info: 查看告警信息"
                )
        
        except Exception as e:
            logger.error(f"Error in _handle_alert: {str(e)}", exc_info=True)
            await update.message.reply_text("抱歉，处理告警命令时发生错误。请稍后重试。")
    
    async def _handle_subscribe(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理 /subscribe 命令"""
        try:
            if not context.args:
                # 显示当前订阅列表
                result = await self.alert_engine.list_subscriptions()
                
                if result["success"]:
                    message = "📱 当前订阅列表\n\n"
                    
                    for sub in result["data"]["subscriptions"]:
                        message += (
                            f"ID: {sub['id']}\n"
                            f"类型: {sub['type']}\n"
                            f"条件: {sub['condition']}\n"
                            f"优先级: {sub['priority']}\n"
                            f"状态: {sub['status']}\n"
                            f"创建时间: {sub['created_at']}\n\n"
                        )
                    
                    await update.message.reply_text(message)
                else:
                    await update.message.reply_text(f"获取订阅列表失败: {result['error']}")
                return
            
            # 处理子命令
            subcommand = context.args[0].lower()
            
            if subcommand == "create":
                if len(context.args) < 3:
                    await update.message.reply_text(
                        "请提供订阅类型和条件，例如：\n"
                        "/subscribe create price BTCUSDT > 50000"
                    )
                    return
                
                sub_type = context.args[1]
                condition = " ".join(context.args[2:])
                
                result = await self.alert_engine.create_subscription(sub_type, condition)
                
                if result["success"]:
                    await update.message.reply_text(
                        f"订阅创建成功！\n"
                        f"ID: {result['data']['id']}\n"
                        f"类型: {result['data']['type']}\n"
                        f"条件: {result['data']['condition']}\n"
                        f"优先级: {result['data']['priority']}\n"
                        f"创建时间: {result['data']['created_at']}"
                    )
                else:
                    await update.message.reply_text(f"创建订阅失败: {result['error']}")
            
            elif subcommand == "edit":
                if len(context.args) < 3:
                    await update.message.reply_text(
                        "请提供订阅ID和新条件，例如：\n"
                        "/subscribe edit 123 BTCUSDT > 55000"
                    )
                    return
                
                sub_id = context.args[1]
                condition = " ".join(context.args[2:])
                
                result = await self.alert_engine.edit_subscription(sub_id, condition)
                
                if result["success"]:
                    await update.message.reply_text(
                        f"订阅更新成功！\n"
                        f"ID: {result['data']['id']}\n"
                        f"类型: {result['data']['type']}\n"
                        f"新条件: {result['data']['condition']}\n"
                        f"更新时间: {result['data']['updated_at']}"
                    )
                else:
                    await update.message.reply_text(f"更新订阅失败: {result['error']}")
            
            elif subcommand == "delete":
                if len(context.args) < 2:
                    await update.message.reply_text(
                        "请提供订阅ID，例如：\n"
                        "/subscribe delete 123"
                    )
                    return
                
                sub_id = context.args[1]
                
                result = await self.alert_engine.delete_subscription(sub_id)
                
                if result["success"]:
                    await update.message.reply_text(f"订阅 {sub_id} 已成功取消！")
                else:
                    await update.message.reply_text(f"删除订阅失败: {result['error']}")
            
            elif subcommand == "info":
                if len(context.args) < 2:
                    await update.message.reply_text(
                        "请提供订阅ID，例如：\n"
                        "/subscribe info 123"
                    )
                    return
                
                sub_id = context.args[1]
                
                result = await self.alert_engine.get_subscription_info(sub_id)
                
                if result["success"]:
                    sub = result["data"]
                    message = (
                        f"📱 订阅信息: {sub['id']}\n\n"
                        f"类型: {sub['type']}\n"
                        f"条件: {sub['condition']}\n"
                        f"优先级: {sub['priority']}\n"
                        f"状态: {sub['status']}\n"
                        f"创建时间: {sub['created_at']}\n"
                        f"最后通知: {sub['last_notified']}\n\n"
                        f"通知历史:\n"
                    )
                    
                    for notification in sub["notification_history"]:
                        message += (
                            f"- 时间: {notification['time']}\n"
                            f"  消息: {notification['message']}\n"
                        )
                    
                    await update.message.reply_text(message)
                else:
                    await update.message.reply_text(f"获取订阅信息失败: {result['error']}")
            
            else:
                await update.message.reply_text(
                    "无效的子命令。可用命令：\n"
                    "- create: 创建新订阅\n"
                    "- edit: 编辑订阅\n"
                    "- delete: 删除订阅\n"
                    "- info: 查看订阅信息"
                )
        
        except Exception as e:
            logger.error(f"Error in _handle_subscribe: {str(e)}", exc_info=True)
            await update.message.reply_text("抱歉，处理订阅命令时发生错误。请稍后重试。")
    
    async def _handle_unsubscribe(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理 /unsubscribe 命令"""
        try:
            if not context.args:
                await update.message.reply_text(
                    "请提供订阅ID，例如：\n"
                    "/unsubscribe 123"
                )
                return
            
            sub_id = context.args[0]
            
            result = await self.alert_engine.delete_subscription(sub_id)
            
            if result["success"]:
                await update.message.reply_text(f"订阅 {sub_id} 已成功取消！")
            else:
                await update.message.reply_text(f"取消订阅失败: {result['error']}")
        
        except Exception as e:
            logger.error(f"Error in _handle_unsubscribe: {str(e)}", exc_info=True)
            await update.message.reply_text("抱歉，取消订阅时发生错误。请稍后重试。")
    
    async def _handle_settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理 /settings 命令"""
        try:
            if not context.args:
                # 显示当前设置
                result = await self.data_processor.get_settings()
                
                if result["success"]:
                    settings = result["data"]
                    message = "⚙️ 系统设置\n\n"
                    
                    # 基本设置
                    message += "基本设置:\n"
                    message += f"- 语言: {settings['language']}\n"
                    message += f"- 时区: {settings['timezone']}\n"
                    message += f"- 通知方式: {settings['notification_method']}\n"
                    message += f"- 图表主题: {settings['chart_theme']}\n\n"
                    
                    # 交易设置
                    message += "交易设置:\n"
                    message += f"- 默认杠杆: {settings['default_leverage']}\n"
                    message += f"- 风险限制: {settings['risk_limit']}\n"
                    message += f"- 止损比例: {settings['stop_loss_ratio']}%\n"
                    message += f"- 止盈比例: {settings['take_profit_ratio']}%\n\n"
                    
                    # 告警设置
                    message += "告警设置:\n"
                    message += f"- 默认优先级: {settings['default_priority']}\n"
                    message += f"- 静默时间: {settings['quiet_hours']}\n"
                    message += f"- 最大告警数: {settings['max_alerts']}\n"
                    message += f"- 告警冷却时间: {settings['alert_cooldown']}秒\n\n"
                    
                    # AI 设置
                    message += "AI 设置:\n"
                    message += f"- 模型版本: {settings['ai_model_version']}\n"
                    message += f"- 分析深度: {settings['analysis_depth']}\n"
                    message += f"- 预测周期: {settings['prediction_period']}\n"
                    message += f"- 置信度阈值: {settings['confidence_threshold']}%\n"
                    
                    await update.message.reply_text(message)
                else:
                    await update.message.reply_text(f"获取设置失败: {result['error']}")
                return
            
            # 处理子命令
            subcommand = context.args[0].lower()
            
            if subcommand == "set":
                if len(context.args) < 3:
                    await update.message.reply_text(
                        "请提供设置项和值，例如：\n"
                        "/settings set language zh_CN"
                    )
                    return
                
                key = context.args[1]
                value = " ".join(context.args[2:])
                
                result = await self.data_processor.update_setting(key, value)
                
                if result["success"]:
                    await update.message.reply_text(
                        f"设置更新成功！\n"
                        f"项: {result['data']['key']}\n"
                        f"新值: {result['data']['value']}\n"
                        f"更新时间: {result['data']['updated_at']}"
                    )
                else:
                    await update.message.reply_text(f"更新设置失败: {result['error']}")
            
            elif subcommand == "reset":
                if len(context.args) < 2:
                    await update.message.reply_text(
                        "请提供要重置的设置项，例如：\n"
                        "/settings reset language"
                    )
                    return
                
                key = context.args[1]
                
                result = await self.data_processor.reset_setting(key)
                
                if result["success"]:
                    await update.message.reply_text(
                        f"设置已重置为默认值！\n"
                        f"项: {result['data']['key']}\n"
                        f"默认值: {result['data']['value']}"
                    )
                else:
                    await update.message.reply_text(f"重置设置失败: {result['error']}")
            
            elif subcommand == "export":
                result = await self.data_processor.export_settings()
                
                if result["success"]:
                    # 发送设置文件
                    await update.message.reply_document(
                        document=result["data"]["file_path"],
                        caption="系统设置导出文件"
                    )
                else:
                    await update.message.reply_text(f"导出设置失败: {result['error']}")
            
            elif subcommand == "import":
                if not update.message.reply_to_message or not update.message.reply_to_message.document:
                    await update.message.reply_text(
                        "请回复一个设置文件，例如：\n"
                        "回复设置文件并输入 /settings import"
                    )
                    return
                
                file = await update.message.reply_to_message.document.get_file()
                result = await self.data_processor.import_settings(file.file_path)
                
                if result["success"]:
                    await update.message.reply_text(
                        f"设置导入成功！\n"
                        f"导入项数: {result['data']['imported_items']}\n"
                        f"更新时间: {result['data']['updated_at']}"
                    )
                else:
                    await update.message.reply_text(f"导入设置失败: {result['error']}")
            
            else:
                await update.message.reply_text(
                    "无效的子命令。可用命令：\n"
                    "- set: 设置值\n"
                    "- reset: 重置为默认值\n"
                    "- export: 导出设置\n"
                    "- import: 导入设置"
                )
        
        except Exception as e:
            logger.error(f"Error in _handle_settings: {str(e)}", exc_info=True)
            await update.message.reply_text("抱歉，处理设置命令时发生错误。请稍后重试。")
    
    async def _handle_voice(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理 /voice 命令"""
        try:
            if not context.args:
                # 显示当前语音设置
                result = await self.data_processor.get_voice_settings()
                
                if result["success"]:
                    settings = result["data"]
                    message = "🔊 语音设置\n\n"
                    
                    message += f"语音状态: {'启用' if settings['enabled'] else '禁用'}\n"
                    message += f"语音类型: {settings['voice_type']}\n"
                    message += f"语速: {settings['speed']}\n"
                    message += f"音量: {settings['volume']}\n"
                    message += f"音调: {settings['pitch']}\n"
                    message += f"语言: {settings['language']}\n"
                    message += f"通知类型: {', '.join(settings['notification_types'])}\n"
                    
                    await update.message.reply_text(message)
                else:
                    await update.message.reply_text(f"获取语音设置失败: {result['error']}")
                return
            
            # 处理子命令
            subcommand = context.args[0].lower()
            
            if subcommand == "enable":
                result = await self.data_processor.update_voice_settings({"enabled": True})
                
                if result["success"]:
                    await update.message.reply_text("语音通知已启用！")
                else:
                    await update.message.reply_text(f"启用语音失败: {result['error']}")
            
            elif subcommand == "disable":
                result = await self.data_processor.update_voice_settings({"enabled": False})
                
                if result["success"]:
                    await update.message.reply_text("语音通知已禁用！")
                else:
                    await update.message.reply_text(f"禁用语音失败: {result['error']}")
            
            elif subcommand == "set":
                if len(context.args) < 3:
                    await update.message.reply_text(
                        "请提供设置项和值，例如：\n"
                        "/voice set speed 1.2"
                    )
                    return
                
                key = context.args[1]
                value = " ".join(context.args[2:])
                
                result = await self.data_processor.update_voice_settings({key: value})
                
                if result["success"]:
                    await update.message.reply_text(
                        f"语音设置更新成功！\n"
                        f"项: {result['data']['key']}\n"
                        f"新值: {result['data']['value']}"
                    )
                else:
                    await update.message.reply_text(f"更新语音设置失败: {result['error']}")
            
            elif subcommand == "test":
                result = await self.data_processor.test_voice()
                
                if result["success"]:
                    # 发送测试语音
                    await update.message.reply_voice(
                        voice=result["data"]["voice_file"],
                        caption="语音测试"
                    )
                else:
                    await update.message.reply_text(f"语音测试失败: {result['error']}")
            
            else:
                await update.message.reply_text(
                    "无效的子命令。可用命令：\n"
                    "- enable: 启用语音\n"
                    "- disable: 禁用语音\n"
                    "- set: 设置语音参数\n"
                    "- test: 测试语音"
                )
        
        except Exception as e:
            logger.error(f"Error in _handle_voice: {str(e)}", exc_info=True)
            await update.message.reply_text("抱歉，处理语音命令时发生错误。请稍后重试。")
    
    async def _handle_language(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理 /language 命令"""
        try:
            if not context.args:
                # 显示当前语言设置
                result = await self.data_processor.get_language_settings()
                
                if result["success"]:
                    settings = result["data"]
                    message = "🌐 语言设置\n\n"
                    
                    message += f"当前语言: {settings['current_language']}\n"
                    message += f"自动检测: {'是' if settings['auto_detect'] else '否'}\n"
                    message += f"翻译服务: {settings['translation_service']}\n"
                    message += f"可用语言:\n"
                    
                    for lang in settings["available_languages"]:
                        message += f"- {lang['code']}: {lang['name']}\n"
                    
                    await update.message.reply_text(message)
                else:
                    await update.message.reply_text(f"获取语言设置失败: {result['error']}")
                return
            
            # 处理子命令
            subcommand = context.args[0].lower()
            
            if subcommand == "set":
                if len(context.args) < 2:
                    await update.message.reply_text(
                        "请提供语言代码，例如：\n"
                        "/language set zh_CN"
                    )
                    return
                
                language = context.args[1]
                
                result = await self.data_processor.set_language(language)
                
                if result["success"]:
                    await update.message.reply_text(
                        f"语言设置已更新！\n"
                        f"新语言: {result['data']['language']}\n"
                        f"更新时间: {result['data']['updated_at']}"
                    )
                else:
                    await update.message.reply_text(f"更新语言失败: {result['error']}")
            
            elif subcommand == "auto":
                if len(context.args) < 2:
                    await update.message.reply_text(
                        "请提供是否启用自动检测，例如：\n"
                        "/language auto on"
                    )
                    return
                
                enabled = context.args[1].lower() in ["on", "true", "yes", "1"]
                
                result = await self.data_processor.set_auto_detect(enabled)
                
                if result["success"]:
                    status = "启用" if enabled else "禁用"
                    await update.message.reply_text(f"语言自动检测已{status}！")
                else:
                    await update.message.reply_text(f"设置自动检测失败: {result['error']}")
            
            elif subcommand == "list":
                result = await self.data_processor.get_available_languages()
                
                if result["success"]:
                    message = "🌐 可用语言列表\n\n"
                    
                    for lang in result["data"]["languages"]:
                        message += f"- {lang['code']}: {lang['name']}\n"
                        message += f"  本地化名称: {lang['native_name']}\n"
                        message += f"  支持程度: {lang['support_level']}\n\n"
                    
                    await update.message.reply_text(message)
                else:
                    await update.message.reply_text(f"获取语言列表失败: {result['error']}")
            
            else:
                await update.message.reply_text(
                    "无效的子命令。可用命令：\n"
                    "- set: 设置语言\n"
                    "- auto: 设置自动检测\n"
                    "- list: 显示可用语言"
                )
        
        except Exception as e:
            logger.error(f"Error in _handle_language: {str(e)}", exc_info=True)
            await update.message.reply_text("抱歉，处理语言命令时发生错误。请稍后重试。")
    
    async def _handle_alert_template(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理告警模板命令"""
        try:
            if not context.args:
                # 显示所有模板
                templates = self.alert_templates.get_all_templates()
                message = "📝 告警模板列表：\n\n"
                for template in templates:
                    message += f"- {template['name']}: {template['description']}\n"
                await update.message.reply_text(message)
                return
            
            subcommand = context.args[0].lower()
            if subcommand == "create":
                if len(context.args) < 3:
                    await update.message.reply_text("请提供模板名称和内容")
                    return
                name = context.args[1]
                content = " ".join(context.args[2:])
                result = self.alert_templates.create_template(name, content)
                if result["success"]:
                    await update.message.reply_text(f"模板 {name} 创建成功！")
                else:
                    await update.message.reply_text(f"创建模板失败: {result['error']}")
            
            elif subcommand == "delete":
                if len(context.args) < 2:
                    await update.message.reply_text("请提供要删除的模板名称")
                    return
                name = context.args[1]
                result = self.alert_templates.delete_template(name)
                if result["success"]:
                    await update.message.reply_text(f"模板 {name} 删除成功！")
                else:
                    await update.message.reply_text(f"删除模板失败: {result['error']}")
            
            elif subcommand == "edit":
                if len(context.args) < 3:
                    await update.message.reply_text("请提供模板名称和新内容")
                    return
                name = context.args[1]
                content = " ".join(context.args[2:])
                result = self.alert_templates.edit_template(name, content)
                if result["success"]:
                    await update.message.reply_text(f"模板 {name} 更新成功！")
                else:
                    await update.message.reply_text(f"更新模板失败: {result['error']}")
            
            else:
                await update.message.reply_text(
                    "无效的子命令。可用命令：\n"
                    "- create: 创建新模板\n"
                    "- delete: 删除模板\n"
                    "- edit: 编辑模板"
                )
        
        except Exception as e:
            logger.error(f"Error in _handle_alert_template: {str(e)}")
            await update.message.reply_text("处理告警模板命令时发生错误")
    
    async def _handle_alert_priority(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理告警优先级命令"""
        try:
            if not context.args:
                # 显示当前优先级设置
                priorities = self.alert_priority.get_all_priorities()
                message = "🔔 告警优先级设置：\n\n"
                for priority in priorities:
                    message += f"- {priority['name']}: {priority['description']}\n"
                await update.message.reply_text(message)
                return
            
            subcommand = context.args[0].lower()
            if subcommand == "set":
                if len(context.args) < 3:
                    await update.message.reply_text("请提供告警ID和优先级")
                    return
                alert_id = context.args[1]
                priority = context.args[2]
                result = self.alert_priority.set_priority(alert_id, priority)
                if result["success"]:
                    await update.message.reply_text(f"告警 {alert_id} 的优先级已更新！")
                else:
                    await update.message.reply_text(f"更新优先级失败: {result['error']}")
            
            else:
                await update.message.reply_text(
                    "无效的子命令。可用命令：\n"
                    "- set: 设置告警优先级"
                )
        
        except Exception as e:
            logger.error(f"Error in _handle_alert_priority: {str(e)}")
            await update.message.reply_text("处理告警优先级命令时发生错误")
    
    async def _handle_alert_feedback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理告警反馈命令"""
        try:
            if not context.args:
                # 显示反馈统计
                stats = self.alert_feedback.get_feedback_stats()
                message = "📊 告警反馈统计：\n\n"
                for stat in stats:
                    message += f"- {stat['category']}: {stat['count']} 条反馈\n"
                await update.message.reply_text(message)
                return
            
            subcommand = context.args[0].lower()
            if subcommand == "add":
                if len(context.args) < 3:
                    await update.message.reply_text("请提供告警ID和反馈内容")
                    return
                alert_id = context.args[1]
                feedback = " ".join(context.args[2:])
                result = self.alert_feedback.add_feedback(alert_id, feedback)
                if result["success"]:
                    await update.message.reply_text("反馈已记录！")
                else:
                    await update.message.reply_text(f"记录反馈失败: {result['error']}")
            
            elif subcommand == "list":
                if len(context.args) < 2:
                    await update.message.reply_text("请提供告警ID")
                    return
                alert_id = context.args[1]
                feedbacks = self.alert_feedback.get_feedbacks(alert_id)
                message = f"📝 告警 {alert_id} 的反馈：\n\n"
                for feedback in feedbacks:
                    message += f"- {feedback['content']}\n"
                await update.message.reply_text(message)
            
            else:
                await update.message.reply_text(
                    "无效的子命令。可用命令：\n"
                    "- add: 添加反馈\n"
                    "- list: 查看反馈"
                )
        
        except Exception as e:
            logger.error(f"Error in _handle_alert_feedback: {str(e)}")
            await update.message.reply_text("处理告警反馈命令时发生错误")
    
    async def _handle_alert_group(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理告警分组命令"""
        try:
            if not context.args:
                # 显示所有分组
                groups = self.alert_grouping.get_all_groups()
                message = "👥 告警分组：\n\n"
                for group in groups:
                    message += f"- {group['name']}: {group['description']}\n"
                await update.message.reply_text(message)
                return
            
            subcommand = context.args[0].lower()
            if subcommand == "create":
                if len(context.args) < 3:
                    await update.message.reply_text("请提供分组名称和描述")
                    return
                name = context.args[1]
                description = " ".join(context.args[2:])
                result = self.alert_grouping.create_group(name, description)
                if result["success"]:
                    await update.message.reply_text(f"分组 {name} 创建成功！")
                else:
                    await update.message.reply_text(f"创建分组失败: {result['error']}")
            
            elif subcommand == "add":
                if len(context.args) < 3:
                    await update.message.reply_text("请提供分组名称和告警ID")
                    return
                group_name = context.args[1]
                alert_id = context.args[2]
                result = self.alert_grouping.add_to_group(group_name, alert_id)
                if result["success"]:
                    await update.message.reply_text(f"告警已添加到分组 {group_name}！")
                else:
                    await update.message.reply_text(f"添加到分组失败: {result['error']}")
            
            elif subcommand == "remove":
                if len(context.args) < 3:
                    await update.message.reply_text("请提供分组名称和告警ID")
                    return
                group_name = context.args[1]
                alert_id = context.args[2]
                result = self.alert_grouping.remove_from_group(group_name, alert_id)
                if result["success"]:
                    await update.message.reply_text(f"告警已从分组 {group_name} 移除！")
                else:
                    await update.message.reply_text(f"从分组移除失败: {result['error']}")
            
            else:
                await update.message.reply_text(
                    "无效的子命令。可用命令：\n"
                    "- create: 创建新分组\n"
                    "- add: 添加告警到分组\n"
                    "- remove: 从分组移除告警"
                )
        
        except Exception as e:
            logger.error(f"Error in _handle_alert_group: {str(e)}")
            await update.message.reply_text("处理告警分组命令时发生错误")
    
    async def _handle_ai_analyze(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理AI分析命令"""
        try:
            if not context.args:
                await update.message.reply_text("请提供要分析的交易对")
                return
            
            symbol = context.args[0].upper()
            
            # 发送开始分析的消息
            status_message = await update.message.reply_text(
                f"🤖 开始AI分析 {symbol}..."
            )
            
            # 获取市场数据
            market_data = await self.trading_handler.get_market_data(symbol)
            
            # 执行AI分析
            analysis = await self.ai_analyzer.analyze_market_data(symbol, "1h", market_data)
            
            if analysis:
                # 格式化分析结果
                message = (
                    f"📊 {symbol} AI分析结果：\n\n"
                    f"市场趋势：{analysis.get('trend', '未知')}\n"
                    f"技术指标：\n"
                )
                
                for indicator, value in analysis.get('indicators', {}).items():
                    message += f"- {indicator}: {value}\n"
                
                message += f"\n预测：\n"
                for prediction in analysis.get('predictions', []):
                    message += f"- {prediction}\n"
                
                message += f"\n建议：\n"
                for suggestion in analysis.get('suggestions', []):
                    message += f"- {suggestion}\n"
                
                # 更新状态消息
                await status_message.edit_text(message)
            else:
                await status_message.edit_text("分析失败，请稍后重试")
        
        except Exception as e:
            logger.error(f"Error in _handle_ai_analyze: {str(e)}")
            await update.message.reply_text("执行AI分析时发生错误")
    
    async def _handle_ai_learn(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理AI学习命令"""
        try:
            if not context.args:
                # 显示学习状态
                stats = self.ai_feedback_learner.get_learning_stats()
                message = "📚 AI学习状态：\n\n"
                message += f"已处理交易数：{stats['processed_trades']}\n"
                message += f"学习周期：{stats['learning_cycles']}\n"
                message += f"最后学习时间：{stats['last_learning_time']}\n"
                await update.message.reply_text(message)
                return
            
            subcommand = context.args[0].lower()
            if subcommand == "start":
                result = await self.ai_feedback_learner.start_learning()
                if result["success"]:
                    await update.message.reply_text("AI学习已启动！")
                else:
                    await update.message.reply_text(f"启动学习失败: {result['error']}")
            
            elif subcommand == "stop":
                result = await self.ai_feedback_learner.stop_learning()
                if result["success"]:
                    await update.message.reply_text("AI学习已停止！")
                else:
                    await update.message.reply_text(f"停止学习失败: {result['error']}")
            
            else:
                await update.message.reply_text(
                    "无效的子命令。可用命令：\n"
                    "- start: 启动AI学习\n"
                    "- stop: 停止AI学习"
                )
        
        except Exception as e:
            logger.error(f"Error in _handle_ai_learn: {str(e)}")
            await update.message.reply_text("处理AI学习命令时发生错误")
    
    async def _handle_ai_model(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理AI模型命令"""
        try:
            if not context.args:
                # 显示可用模型
                models = self.ai_model_router.get_available_models()
                message = "🤖 可用AI模型：\n\n"
                for model in models:
                    message += f"- {model}\n"
                await update.message.reply_text(message)
                return
            
            subcommand = context.args[0].lower()
            if subcommand == "switch":
                if len(context.args) < 2:
                    await update.message.reply_text("请提供要切换的模型名称")
                    return
                model = context.args[1]
                result = self.ai_model_router.switch_default_model(model)
                if result:
                    await update.message.reply_text(f"已切换到模型 {model}！")
                else:
                    await update.message.reply_text("切换模型失败")
            
            else:
                await update.message.reply_text(
                    "无效的子命令。可用命令：\n"
                    "- switch: 切换AI模型"
                )
        
        except Exception as e:
            logger.error(f"Error in _handle_ai_model: {str(e)}")
            await update.message.reply_text("处理AI模型命令时发生错误")
    
    async def _handle_ai_report(self, update, context):
        from ai_engine.ai_reporter import get_latest_report
        report = get_latest_report()
        msg = f"📢 *AI分析报告*\n\n{report}"
        await update.message.reply_text(msg, parse_mode="Markdown")

    async def _handle_ai_signal(self, update, context):
        from core.ai_event_pool import get_latest_signal
        signal = get_latest_signal()
        await update.message.reply_text(f"*AI智能信号*\n\n{signal}", parse_mode="Markdown")

    async def _handle_ai_sentiment(self, update, context):
        from core.analysis.ai_analyzer import get_market_sentiment
        sentiment = get_market_sentiment()
        await update.message.reply_text(f"*市场情绪分析*\n\n{sentiment}", parse_mode="Markdown")

    async def _handle_backtest(self, update, context):
        from trading.backtest_strategy import get_last_backtest_summary
        summary = get_last_backtest_summary()  # 假设返回dict
        msg = (
            f"📈 *策略回测摘要*\n"
            f"----------------------\n"
            f"*总收益率*: `{summary['total_return']}%`\n"
            f"*最大回撤*: `{summary['max_drawdown']}%`\n"
            f"*夏普比率*: `{summary['sharpe_ratio']}`\n"
            f"*胜率*: `{summary['win_rate']}%`\n"
            f"*交易次数*: `{summary['total_trades']}`\n"
            f"----------------------\n"
            f"详情请用 /backtest_detail 查看"
        )
        await update.message.reply_text(msg, parse_mode="Markdown")

    async def _handle_backtest_detail(self, update, context):
        from trading.backtest_strategy import get_last_backtest_detail
        detail = get_last_backtest_detail()  # 假设返回dict，含图片路径
        msg = f"📊 *回测详细信号*\n\n{detail['summary']}"
        await update.message.reply_text(msg, parse_mode="Markdown")
        if 'chart_path' in detail:
            with open(detail['chart_path'], 'rb') as photo:
                await update.message.reply_photo(photo=photo, caption="回测收益曲线")

    async def _handle_strategy_evolution(self, update, context):
        from core.strategy.strategy_evolution import get_evolution_report
        report = get_evolution_report()
        await update.message.reply_text(f"*策略进化报告*\n\n{report}", parse_mode="Markdown")

    async def _handle_quote(self, update, context):
        if not context.args:
            await update.message.reply_text("请提供股票代码，例如 /quote AAPL")
            return
        symbol = context.args[0].upper()
        from core.data.market_data_hub import get_stock_quote
        quote = get_stock_quote(symbol)
        keyboard = [[InlineKeyboardButton("刷新", callback_data=f"refresh_quote_{symbol}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(f"*{symbol} 实时行情*\n\n{quote}", parse_mode="Markdown", reply_markup=reply_markup)

    async def _handle_kline(self, update, context):
        if not context.args:
            await update.message.reply_text("请提供股票代码，例如 /kline AAPL")
            return
        symbol = context.args[0].upper()
        from core.data.market_data_hub import get_kline
        kline = get_kline(symbol, period="1d")
        await update.message.reply_text(f"*{symbol} 日K线*\n\n{kline}", parse_mode="Markdown")

    async def _handle_position(self, update, context):
        from trading.position_manager import get_current_position
        pos = get_current_position()
        await update.message.reply_text(f"*当前持仓*\n\n{pos}", parse_mode="Markdown")

    async def _handle_asset(self, update, context):
        from trading.position_manager import get_account_asset
        asset = get_account_asset()
        await update.message.reply_text(f"*账户资产*\n\n{asset}", parse_mode="Markdown")

    async def _handle_order(self, update, context):
        if not context.args:
            await update.message.reply_text("请提供订单ID，例如 /order 123456")
            return
        order_id = context.args[0]
        from trading.order_manager import get_order_status
        status = get_order_status(order_id)
        await update.message.reply_text(f"*订单状态*\n\n{status}", parse_mode="Markdown")

    async def _handle_notify(self, update, context):
        msg = " ".join(context.args)
        from notifiers.telegram_notifier import send_admin_message
        send_admin_message(msg)
        await update.message.reply_text("消息已推送。")

    async def _handle_subscribe(self, update, context):
        await update.message.reply_text("已订阅。")

    async def _handle_unsubscribe(self, update, context):
        await update.message.reply_text("已取消订阅。")

    async def _handle_report(self, update, context):
        from reports import get_latest_report
        report = get_latest_report()
        await update.message.reply_text(f"*最新日报/周报*\n\n{report}", parse_mode="Markdown")

    async def _handle_performance(self, update, context):
        from web_dashboard.performance import get_performance
        perf = get_performance()
        await update.message.reply_text(f"*策略表现*\n\n{perf}", parse_mode="Markdown")

    async def _handle_dashboard(self, update, context):
        url = "http://your_dashboard_url"
        await update.message.reply_text(f"点击访问可视化仪表盘：{url}")

    async def push_daily_ai_report(self):
        from ai_engine.ai_reporter import get_latest_report
        report = get_latest_report()
        for chat_id in self.broadcast_channels:
            await self.app.bot.send_message(chat_id=chat_id, text=f"📢 *每日AI报告*\n\n{report}", parse_mode="Markdown")