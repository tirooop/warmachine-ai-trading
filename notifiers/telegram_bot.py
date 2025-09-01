#!/usr/bin/env python



"""



WarMachine Telegram Bot







This module implements a Telegram bot for the WarMachine trading platform.



"""







import os



import sys



import json



import logging



import asyncio



import threading



from typing import Dict, Any, List, Optional







import telebot



from telebot.async_telebot import AsyncTeleBot



from telebot import types



from datetime import datetime



from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton



from telegram.ext import (



    Application,



    CommandHandler,



    MessageHandler,



    CallbackQueryHandler,



    filters



)







# Set up logging



logging.basicConfig(



    level=logging.INFO,



    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',



    handlers=[



        logging.FileHandler("logs/telegram_bot.log"),



        logging.StreamHandler()



    ]



)



logger = logging.getLogger(__name__)







# Ensure logs directory exists



os.makedirs("logs", exist_ok=True)







class OptionBot:



    def __init__(self, token: str, websocket_manager, risk_controller):



        self.app = Application.builder().token(token).build()



        self.ws_manager = websocket_manager



        self.risk_controller = risk_controller



        self.logger = logging.getLogger(__name__)



        self._register_handlers()



        



    def _register_handlers(self):



        """注册消息处理器"""



        self.app.add_handler(CommandHandler("start", self._handle_start))



        self.app.add_handler(CommandHandler("help", self._handle_help))



        self.app.add_handler(MessageHandler(



            filters.TEXT & ~filters.COMMAND,



            self._handle_message



        ))



        self.app.add_handler(CallbackQueryHandler(self._handle_callback))



        



    async def _handle_start(self, update: Update, context):



        """处理/start命令"""



        welcome_text = (



            "欢迎使用期权分析机器人！\n\n"



            "使用方法：\n"



            "1. 输入股票代码和到期日，例如：AAPL 2024-06-21\n"



            "2. 使用/help查看所有可用命令\n"



            "3. 点击按钮查看详细分析"



        )



        await update.message.reply_text(



            welcome_text,



            reply_markup=self._build_main_keyboard()



        )



        



    async def _handle_help(self, update: Update, context):



        """处理/help命令"""



        help_text = (



            "可用命令：\n"



            "/start - 开始使用\n"



            "/help - 显示帮助信息\n"



            "/risk - 查看当前风险指标\n"



            "/positions - 查看当前持仓\n"



            "/alerts - 管理价格提醒"



        )



        await update.message.reply_text(help_text)



        



    async def _handle_message(self, update: Update, context):



        """处理用户消息"""



        try:



            text = update.message.text



            symbol, expiry = text.split()



            



            # 显示分析中状态



            msg = await update.message.reply_text(



                f"正在分析 {symbol} {expiry}...",



                reply_markup=self._build_loading_keyboard()



            )



            



            # 获取期权数据



            await self.ws_manager.connect("polygon", symbol, self._handle_option_data)



            



            # 更新消息为分析结果



            analysis = await self._analyze_options(symbol, expiry)



            await msg.edit_text(



                self._format_analysis(analysis),



                reply_markup=self._build_analysis_keyboard(symbol, expiry)



            )



            



        except Exception as e:



            self.logger.error(f"Error handling message: {str(e)}")



            await update.message.reply_text(f"错误：{str(e)}")



            



    async def _handle_callback(self, update: Update, context):



        """处理按钮回调"""



        query = update.callback_query



        await query.answer()



        



        try:



            action, symbol, expiry = query.data.split("|")



            



            if action == "greeks":



                await self._show_greeks(query, symbol, expiry)



            elif action == "risk":



                await self._show_risk_metrics(query)



            elif action == "alert":



                await self._show_alert_options(query, symbol, expiry)



                



        except Exception as e:



            self.logger.error(f"Error handling callback: {str(e)}")



            await query.edit_message_text(f"错误：{str(e)}")



            



    def _build_main_keyboard(self) -> InlineKeyboardMarkup:



        """构建主菜单键盘"""



        return InlineKeyboardMarkup([



            [InlineKeyboardButton("查看风险指标", callback_data="risk|none|none")],



            [InlineKeyboardButton("管理提醒", callback_data="alerts|none|none")]



        ])



        



    def _build_analysis_keyboard(self, symbol: str, expiry: str) -> InlineKeyboardMarkup:



        """构建分析结果键盘"""



        return InlineKeyboardMarkup([



            [InlineKeyboardButton("Greeks分析", callback_data=f"greeks|{symbol}|{expiry}")],



            [InlineKeyboardButton("设置提醒", callback_data=f"alert|{symbol}|{expiry}")],



            [InlineKeyboardButton("查看风险", callback_data=f"risk|{symbol}|{expiry}")]



        ])



        



    async def _format_analysis(self, analysis: Dict) -> str:



        """格式化分析结果"""



        return (



            f"期权分析报告\n\n"



            f"标的：{analysis['symbol']}\n"



            f"到期日：{analysis['expiry']}\n"



            f"当前价格：${analysis['price']:.2f}\n"



            f"隐含波动率：{analysis['iv']:.1%}\n"



            f"Delta：{analysis['delta']:.2f}\n"



            f"Gamma：{analysis['gamma']:.4f}\n"



            f"Theta：{analysis['theta']:.2f}\n"



            f"Vega：{analysis['vega']:.2f}\n"



        )



        



    async def run(self):



        """启动机器人"""



        await self.app.run_polling()







def run_telegram_bot(config: Dict[str, Any]):



    """Start the Telegram bot (for use in a separate thread)"""



    bot = OptionBot(config.get("telegram", {}).get("token", ""), config.get("websocket_manager", None), config.get("risk_controller", None))



    



    if not bot.app:



        logger.error("Could not create Telegram bot instance, exiting")



        return



    



    loop = asyncio.new_event_loop()



    asyncio.set_event_loop(loop)



    



    try:



        loop.run_until_complete(bot.run())



        # Keep the event loop running to maintain the bot



        loop.run_forever()



    except KeyboardInterrupt:



        loop.run_until_complete(bot.app.stop())



    finally:



        loop.close() 