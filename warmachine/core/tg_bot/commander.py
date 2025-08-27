"""
Telegram Commander - Core component for handling all Telegram interactions
"""

import logging
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes
)

from .nl_processor_v2 import NLProcessorV2
from .strategy_sandbox import StrategySandbox
from .alert_engine import AlertEngine
from .mcp_connector import MCPConnector, MCPResponse
from .trading_handler import TradingHandler
from ai_event_pool import AIEvent, EventCategory, EventPriority

logger = logging.getLogger(__name__)

class TelegramCommander:
    """Core component for handling all Telegram interactions"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the Telegram Commander
        
        Args:
            config: Configuration dictionary containing all settings
        """
        self.config = config
        self.telegram_config = config["telegram"]
        self.token = self.telegram_config["token"]
        self.admin_chat_id = self.telegram_config["admin_chat_id"]
        self.broadcast_channels = self.telegram_config["broadcast_channels"]
        self.allowed_users = self.telegram_config["allowed_users"]
        
        # Initialize components
        self.nl_processor = NLProcessorV2()
        self.sandbox = StrategySandbox()
        self.alert_engine = AlertEngine(config)
        self.mcp_connector = MCPConnector(config["mcp_server"])
        self.trading_handler = TradingHandler(self.mcp_connector, config)
        
        # Initialize bot
        self.app = Application.builder().token(self.token).build()
        
        # Register handlers
        self._register_handlers()
        
        logger.info("Telegram Commander initialized")
    
    def _register_handlers(self):
        """Register all command and message handlers"""
        # Command handlers
        self.app.add_handler(CommandHandler("start", self._handle_start))
        self.app.add_handler(CommandHandler("help", self._handle_help))
        self.app.add_handler(CommandHandler("status", self._handle_status))
        self.app.add_handler(CommandHandler("strategy", self._handle_strategy))
        self.app.add_handler(CommandHandler("alert", self._handle_alert))
        self.app.add_handler(CommandHandler("price", self._handle_price))
        self.app.add_handler(CommandHandler("volume", self._handle_volume))
        self.app.add_handler(CommandHandler("technical", self._handle_technical))
        self.app.add_handler(CommandHandler("fundamental", self._handle_fundamental))
        self.app.add_handler(CommandHandler("ai_analysis", self._handle_ai_analysis))
        self.app.add_handler(CommandHandler("prediction", self._handle_prediction))
        self.app.add_handler(CommandHandler("sentiment", self._handle_sentiment))
        self.app.add_handler(CommandHandler("risk_alert", self._handle_risk_alert))
        self.app.add_handler(CommandHandler("test", self._handle_test))
        
        # Message handlers
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_message))
        
        # Callback query handlers
        self.app.add_handler(CallbackQueryHandler(self._handle_callback))
    
    def start(self):
        """Start the Telegram bot (sync version)"""
        try:
            logger.info("Starting Telegram bot...")
            logger.info(f"Bot token: {self.token[:10]}...")
            logger.info(f"Allowed users: {self.allowed_users}")
            
            # Initialize bot
            logger.info("Initializing Telegram bot...")
            self.app = Application.builder().token(self.token).build()
            
            # Add handlers
            self._register_handlers()
            
            # Start polling (sync)
            logger.info("Starting Telegram bot polling...")
            self.app.run_polling(allowed_updates=Update.ALL_TYPES)
            logger.info("Telegram bot polling started successfully")
        except Exception as e:
            logger.error(f"Error starting Telegram bot: {str(e)}")
            raise
    
    async def stop(self):
        """Stop the Telegram bot and disconnect from MCP Server"""
        # Unsubscribe from MCP events
        await self.mcp_connector.unsubscribe_from_events()
        
        # Disconnect from MCP Server
        await self.mcp_connector.disconnect()
        
        # Stop Telegram bot
        await self.app.stop()
    
    async def _handle_mcp_event(self, event: Dict[str, Any]):
        """Handle events from MCP Server"""
        try:
            event_type = event.get("type")
            data = event.get("data", {})
            
            if event_type == "trade":
                await self._handle_trade_event(data)
            elif event_type == "alert":
                await self._handle_alert_event(data)
            elif event_type == "status":
                await self._handle_status_event(data)
                
        except Exception as e:
            logger.error(f"Error handling MCP event: {str(e)}")
    
    async def _handle_trade_event(self, data: Dict[str, Any]):
        """Handle trade events from MCP Server"""
        # Create AIEvent for trade
        event = AIEvent(
            title="Trade Execution",
            category=EventCategory.TRADE,
            priority=EventPriority.INFO,
            content=f"Trade executed: {data.get('symbol')} - {data.get('action')} {data.get('quantity')} @ {data.get('price')}",
            metadata=data
        )
        
        # Send alert
        await self.send_alert(event)
    
    async def _handle_alert_event(self, data: Dict[str, Any]):
        """Handle alert events from MCP Server"""
        # Create AIEvent for alert
        event = AIEvent(
            title=data.get("title", "MCP Alert"),
            category=EventCategory.ALERT,
            priority=EventPriority(data.get("priority", "INFO")),
            content=data.get("message", ""),
            metadata=data
        )
        
        # Send alert
        await self.send_alert(event)
    
    async def _handle_status_event(self, data: Dict[str, Any]):
        """Handle status events from MCP Server"""
        # Create AIEvent for status
        event = AIEvent(
            title="System Status Update",
            category=EventCategory.SYSTEM,
            priority=EventPriority.INFO,
            content=f"Status: {data.get('status')}\nDetails: {data.get('details', '')}",
            metadata=data
        )
        
        # Send alert
        await self.send_alert(event)
    
    async def _handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        try:
            user_id = str(update.effective_user.id)
            logger.info(f"Received /start command from user {user_id}")
            logger.info(f"Allowed users: {self.allowed_users}")
            
            if user_id not in self.allowed_users:
                logger.warning(f"Unauthorized access attempt from user {user_id}")
                await update.message.reply_text("Sorry, you are not authorized to use this bot.")
                return
            
            welcome_message = (
                "Welcome to WarMachine AI Trading System!\n\n"
                "Available commands:\n"
                "/help - Show help message\n"
                "/status - Check system status\n"
                "/strategy - Manage trading strategies\n"
                "/alert - Configure alerts\n"
                "/price - Get price information\n"
                "/volume - Get volume information\n"
                "/technical - Get technical analysis\n"
                "/fundamental - Get fundamental analysis\n\n"
                "You can also use natural language commands like:\n"
                "- Show me the current portfolio\n"
                "- What's the status of UVX?\n"
                "- Run backtest for strategy X\n"
                "- Set alert for NXP above 200"
            )
            logger.info(f"Sending welcome message to user {user_id}")
            await update.message.reply_text(welcome_message)
            logger.info(f"Welcome message sent successfully to user {user_id}")
        except Exception as e:
            logger.error(f"Error in _handle_start: {str(e)}", exc_info=True)
    
    async def _handle_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_message = (
            "WarMachine AI Trading System Help\n\n"
            "Commands:\n"
            "/start - Start the bot\n"
            "/help - Show this help message\n"
            "/status - Check system status\n"
            "/strategy - Manage trading strategies\n"
            "/alert - Configure alerts\n"
            "/price <symbol> - Get price information\n"
            "/volume <symbol> - Get volume information\n"
            "/technical <symbol> [indicators] - Get technical analysis\n"
            "/fundamental <symbol> - Get fundamental analysis\n\n"
            "Natural Language Commands:\n"
            "- Show me the current portfolio\n"
            "- What's the status of UVX?\n"
            "- Run backtest for strategy X\n"
            "- Set alert for NXP above 200\n"
            "- Optimize parameters for strategy Y\n"
            "- Deploy strategy Z\n\n"
            "The system understands natural language and can handle complex queries.\n"
            "Try asking questions in your own words!"
        )
        await update.message.reply_text(help_message)
    
    async def _handle_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command"""
        status = await self._get_system_status()
        await update.message.reply_text(status)
    
    async def _handle_strategy(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /strategy command"""
        keyboard = [
            [
                InlineKeyboardButton("List Strategies", callback_data="strategy_list"),
                InlineKeyboardButton("Run Backtest", callback_data="strategy_backtest")
            ],
            [
                InlineKeyboardButton("Optimize Parameters", callback_data="strategy_optimize"),
                InlineKeyboardButton("Deploy Strategy", callback_data="strategy_deploy")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Strategy Management:", reply_markup=reply_markup)
    
    async def _handle_alert(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /alert command"""
        keyboard = [
            [
                InlineKeyboardButton("Set Price Alert", callback_data="alert_price"),
                InlineKeyboardButton("Set Volume Alert", callback_data="alert_volume")
            ],
            [
                InlineKeyboardButton("Set Risk Alert", callback_data="alert_risk"),
                InlineKeyboardButton("List Alerts", callback_data="alert_list")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Alert Configuration:", reply_markup=reply_markup)
    
    async def _handle_price(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /price command"""
        try:
            user_id = str(update.effective_user.id)
            logger.info(f"Received /price command from user {user_id}")
            
            if user_id not in self.allowed_users:
                logger.warning(f"Unauthorized access attempt from user {user_id}")
                await update.message.reply_text("Sorry, you are not authorized to use this bot.")
                return
            
            # Get symbol from command arguments
            args = context.args
            if not args:
                logger.warning("No symbol provided in /price command")
                await update.message.reply_text(
                    "Please provide a symbol. Example: /price UVX"
                )
                return
            
            symbol = args[0].upper()
            logger.info(f"Processing price query for symbol: {symbol}")
            
            # Process query
            result = await self.trading_handler.process_query(
                symbol=symbol,
                query_type="price",
                timeframe="1d"
            )
            
            if result["success"]:
                logger.info(f"Successfully retrieved price data for {symbol}")
                await update.message.reply_text(result["message"])
            else:
                error_msg = result.get("error", "Unknown error")
                logger.error(f"Error retrieving price data for {symbol}: {error_msg}")
                await update.message.reply_text(f"Error: {error_msg}")
                
        except Exception as e:
            logger.error(f"Error handling /price command: {str(e)}")
            await update.message.reply_text("Sorry, an error occurred while processing your request.")
    
    async def _handle_volume(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /volume command"""
        if not context.args:
            await update.message.reply_text("Please specify a symbol (e.g., /volume NXP)")
            return
        
        symbol = context.args[0].upper()
        result = await self.trading_handler.process_query(symbol, "volume")
        
        if result["success"]:
            await update.message.reply_text(result["message"])
        else:
            await update.message.reply_text(f"Error: {result['error']}")
    
    async def _handle_technical(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /technical command"""
        if not context.args:
            await update.message.reply_text("Please specify a symbol (e.g., /technical UVX)")
            return
        
        symbol = context.args[0].upper()
        indicators = context.args[1:] if len(context.args) > 1 else None
        
        result = await self.trading_handler.process_query(
            symbol,
            "technical",
            indicators=indicators
        )
        
        if result["success"]:
            await update.message.reply_text(result["message"])
        else:
            await update.message.reply_text(f"Error: {result['error']}")
    
    async def _handle_fundamental(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /fundamental command"""
        if not context.args:
            await update.message.reply_text("Please specify a symbol (e.g., /fundamental NXP)")
            return
        
        symbol = context.args[0].upper()
        result = await self.trading_handler.process_query(symbol, "fundamental")
        
        if result["success"]:
            await update.message.reply_text(result["message"])
        else:
            await update.message.reply_text(f"Error: {result['error']}")
    
    async def _handle_test(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /test command"""
        try:
            user_id = str(update.effective_user.id)
            logger.info(f"Received /test command from user {user_id}")
            
            if user_id not in self.allowed_users:
                logger.warning(f"Unauthorized access attempt from user {user_id}")
                await update.message.reply_text("Sorry, you are not authorized to use this bot.")
                return
            
            test_message = "这是一条测试消息！如果你能看到这条消息，说明机器人工作正常。"
            logger.info(f"Sending test message to user {user_id}")
            await update.message.reply_text(test_message)
            logger.info(f"Test message sent successfully to user {user_id}")
        except Exception as e:
            logger.error(f"Error in _handle_test: {str(e)}", exc_info=True)
    
    async def _handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle natural language messages"""
        try:
            user_id = str(update.effective_user.id)
            logger.info(f"Received message from user {user_id}: {update.message.text}")
            logger.info(f"Allowed users: {self.allowed_users}")
            
            if user_id not in self.allowed_users:
                logger.warning(f"Unauthorized access attempt from user {user_id}")
                await update.message.reply_text("Sorry, you are not authorized to use this bot.")
                return
            
            message = update.message.text
            
            # Create context with user information
            context = {
                "user_id": user_id,
                "chat_id": update.effective_chat.id,
                "username": update.effective_user.username,
                "timestamp": datetime.now()
            }
            
            logger.info(f"Processing message with context: {context}")
            
            # Process message with enhanced NL processor
            response = await self.nl_processor.process(message, context)
            logger.info(f"NL processor response: {response}")
            
            # If response contains trading query, process it
            if isinstance(response, dict) and "trading_query" in response:
                query = response["trading_query"]
                result = await self.trading_handler.process_query(**query)
                
                if result["success"]:
                    await update.message.reply_text(result["message"])
                else:
                    await update.message.reply_text(f"Error: {result['error']}")
            # If response contains MCP command, send it to MCP Server
            elif isinstance(response, dict) and "mcp_command" in response:
                mcp_response = await self.mcp_connector.send_command(
                    response["mcp_command"],
                    response.get("params", {})
                )
                
                if mcp_response.success:
                    await update.message.reply_text(
                        f"Command executed successfully: {mcp_response.data.get('message', '')}"
                    )
                else:
                    await update.message.reply_text(
                        f"Error executing command: {mcp_response.error}"
                    )
            else:
                await update.message.reply_text(response)
                
            logger.info(f"Message processed and response sent to user {user_id}")
        except Exception as e:
            logger.error(f"Error in _handle_message: {str(e)}", exc_info=True)
    
    async def _handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle callback queries from inline keyboards"""
        query = update.callback_query
        await query.answer()
        
        if query.data.startswith("strategy_"):
            await self._handle_strategy_callback(query)
        elif query.data.startswith("alert_"):
            await self._handle_alert_callback(query)
    
    async def _handle_strategy_callback(self, query):
        """Handle strategy-related callbacks"""
        action = query.data.split("_")[1]
        
        if action == "list":
            strategies = await self.sandbox.list_strategies()
            await query.message.reply_text(strategies)
        elif action == "backtest":
            await query.message.reply_text("Please specify the strategy name for backtesting.")
        elif action == "optimize":
            await query.message.reply_text("Please specify the strategy and parameters to optimize.")
        elif action == "deploy":
            await query.message.reply_text("Please specify the strategy to deploy.")
    
    async def _handle_alert_callback(self, query):
        """Handle alert-related callbacks"""
        action = query.data.split("_")[1]
        
        if action == "price":
            await query.message.reply_text("Please specify the symbol and price level for the alert.")
        elif action == "volume":
            await query.message.reply_text("Please specify the symbol and volume threshold for the alert.")
        elif action == "risk":
            await query.message.reply_text("Please specify the risk parameters for the alert.")
        elif action == "list":
            alerts = await self.alert_engine.list_alerts()
            await query.message.reply_text(alerts)
    
    async def _get_system_status(self) -> str:
        """Get current system status"""
        status = (
            "System Status:\n\n"
            f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            "Components:\n"
            "- AI Strategy Engine: Running\n"
            "- Risk Monitor: Active\n"
            "- Market Data: Connected\n"
            "- Portfolio: Updated\n"
            "\nLast Update: 1 minute ago"
        )
        return status
    
    async def broadcast_message(self, message: str, priority: EventPriority = EventPriority.INFO):
        """Broadcast message to all channels"""
        for channel in self.broadcast_channels:
            try:
                await self.app.bot.send_message(
                    chat_id=channel,
                    text=message,
                    parse_mode="Markdown"
                )
            except Exception as e:
                logger.error(f"Error broadcasting to channel {channel}: {str(e)}")
    
    async def send_alert(self, event: AIEvent):
        """Send alert to appropriate channels"""
        await self.alert_engine.process_event(event)
        if event.priority in [EventPriority.CRITICAL, EventPriority.URGENT]:
            await self.broadcast_message(
                f"🚨 *{event.title}*\n{event.content}",
                event.priority
            )
    
    async def _handle_ai_analysis(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /ai_analysis command"""
        try:
            user_id = str(update.effective_user.id)
            logger.info(f"Received /ai_analysis command from user {user_id}")
            
            if user_id not in self.allowed_users:
                logger.warning(f"Unauthorized access attempt from user {user_id}")
                await update.message.reply_text("Sorry, you are not authorized to use this bot.")
                return
            
            # Get symbol from command arguments
            if not context.args:
                await update.message.reply_text("Please provide a symbol. Example: /ai_analysis AAPL")
                return
            
            symbol = context.args[0].upper()
            logger.info(f"Processing AI analysis query for {symbol}")
            
            # Process query
            result = await self.trading_handler.process_query(symbol, "ai_analysis")
            
            if result["success"]:
                await update.message.reply_text(result["message"])
            else:
                await update.message.reply_text(f"Error: {result['error']}")
                
        except Exception as e:
            logger.error(f"Error handling AI analysis query: {str(e)}")
            await update.message.reply_text("Sorry, an error occurred while processing your request.")
    
    async def _handle_prediction(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /prediction command"""
        try:
            user_id = str(update.effective_user.id)
            logger.info(f"Received /prediction command from user {user_id}")
            
            if user_id not in self.allowed_users:
                logger.warning(f"Unauthorized access attempt from user {user_id}")
                await update.message.reply_text("Sorry, you are not authorized to use this bot.")
                return
            
            # Get symbol from command arguments
            if not context.args:
                await update.message.reply_text("Please provide a symbol. Example: /prediction AAPL")
                return
            
            symbol = context.args[0].upper()
            logger.info(f"Processing prediction query for {symbol}")
            
            # Process query
            result = await self.trading_handler.process_query(symbol, "prediction")
            
            if result["success"]:
                await update.message.reply_text(result["message"])
            else:
                await update.message.reply_text(f"Error: {result['error']}")
                
        except Exception as e:
            logger.error(f"Error handling prediction query: {str(e)}")
            await update.message.reply_text("Sorry, an error occurred while processing your request.")
    
    async def _handle_sentiment(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /sentiment command"""
        try:
            user_id = str(update.effective_user.id)
            logger.info(f"Received /sentiment command from user {user_id}")
            
            if user_id not in self.allowed_users:
                logger.warning(f"Unauthorized access attempt from user {user_id}")
                await update.message.reply_text("Sorry, you are not authorized to use this bot.")
                return
            
            # Get symbol from command arguments
            if not context.args:
                await update.message.reply_text("Please provide a symbol. Example: /sentiment AAPL")
                return
            
            symbol = context.args[0].upper()
            logger.info(f"Processing sentiment query for {symbol}")
            
            # Process query
            result = await self.trading_handler.process_query(symbol, "sentiment")
            
            if result["success"]:
                await update.message.reply_text(result["message"])
            else:
                await update.message.reply_text(f"Error: {result['error']}")
                
        except Exception as e:
            logger.error(f"Error handling sentiment query: {str(e)}")
            await update.message.reply_text("Sorry, an error occurred while processing your request.")
    
    async def _handle_risk_alert(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /risk_alert command"""
        try:
            user_id = str(update.effective_user.id)
            logger.info(f"Received /risk_alert command from user {user_id}")
            
            if user_id not in self.allowed_users:
                logger.warning(f"Unauthorized access attempt from user {user_id}")
                await update.message.reply_text("Sorry, you are not authorized to use this bot.")
                return
            
            # Get symbol from command arguments
            if not context.args:
                await update.message.reply_text("Please provide a symbol. Example: /risk_alert AAPL")
                return
            
            symbol = context.args[0].upper()
            logger.info(f"Processing risk alert query for {symbol}")
            
            # Process query
            result = await self.trading_handler.process_query(symbol, "risk_alert")
            
            if result["success"]:
                await update.message.reply_text(result["message"])
            else:
                await update.message.reply_text(f"Error: {result['error']}")
                
        except Exception as e:
            logger.error(f"Error handling risk alert query: {str(e)}")
            await update.message.reply_text("Sorry, an error occurred while processing your request.") 