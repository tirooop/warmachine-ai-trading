"""
Telegram Chart Bot - Uses Pillow instead of imghdr for image processing
"""

import os
import logging
import sys
from PIL import Image
from dotenv import load_dotenv
from telegram import Update, ParseMode
from telegram.ext import Updater, CommandHandler, CallbackContext, Dispatcher

# Standalone modules
from standalone_chart_renderer import StandaloneChartRenderer
from standalone_ai_analyzer import StandaloneAIAnalyzer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("telegram_chart_bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("telegram_chart_bot")

class TelegramChartBot:
    """Telegram bot for generating and sending technical analysis charts"""
    
    def __init__(self, token=None):
        """Initialize bot with token"""
        load_dotenv()
        self.token = token or os.getenv("TELEGRAM_BOT_TOKEN")
        
        if not self.token:
            logger.warning("No Telegram bot token provided. Set TELEGRAM_BOT_TOKEN environment variable.")
            raise ValueError("Telegram bot token is required")
        
        # Initialize components
        self.chart_renderer = StandaloneChartRenderer()
        self.ai_analyzer = StandaloneAIAnalyzer()
        
        # Initialize updater and dispatcher
        self.updater = Updater(token=self.token, use_context=True)
        self.dispatcher = self.updater.dispatcher
        
        # Register handlers
        self._register_handlers()
        
        logger.info("TelegramChartBot initialized")
    
    def _register_handlers(self):
        """Register command handlers"""
        # Basic commands
        self.dispatcher.add_handler(CommandHandler("start", self.cmd_start))
        self.dispatcher.add_handler(CommandHandler("help", self.cmd_help))
        
        # Chart commands
        self.dispatcher.add_handler(CommandHandler("chart", self.cmd_chart))
        self.dispatcher.add_handler(CommandHandler("portfolio", self.cmd_portfolio))
    
    def cmd_start(self, update: Update, context: CallbackContext):
        """Handler for /start command"""
        user = update.effective_user
        message = (
            f"ðŸ‘‹ Hello {user.first_name}!\n\n"
            f"Welcome to the AI Chart Analysis Bot. "
            f"This bot generates technical analysis charts with AI commentary.\n\n"
            f"Type /help to see available commands."
        )
        update.message.reply_text(message)
    
    def cmd_help(self, update: Update, context: CallbackContext):
        """Handler for /help command"""
        help_text = (
            "ðŸ¤– *AI Chart Analysis Bot Commands*\n\n"
            "/chart <symbol1> [symbol2] ... - Generate charts for symbols\n"
            "Example: `/chart AAPL MSFT TSLA`\n\n"
            "/portfolio - Generate charts for your portfolio\n"
        )
        update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)
    
    def cmd_chart(self, update: Update, context: CallbackContext):
        """Handler for /chart command"""
        args = context.args
        
        if not args:
            update.message.reply_text("Please provide stock symbols, e.g., /chart AAPL MSFT TSLA")
            return
        
        # Send processing message
        processing_msg = update.message.reply_text("Generating charts, please wait...")
        
        try:
            for symbol in args:
                symbol = symbol.upper()
                # Generate chart
                chart_path = self.chart_renderer.render(symbol)
                
                # Verify image with Pillow
                try:
                    with Image.open(chart_path) as img:
                        width, height = img.size
                        logger.info(f"Generated image dimensions: {width}x{height}")
                except Exception as e:
                    logger.error(f"Error validating image: {str(e)}")
                    update.message.reply_text(f"Error generating chart for {symbol}: {str(e)}")
                    continue
                
                # Get data for AI analysis
                df = self.chart_renderer._fetch_data(symbol)
                df = self.chart_renderer._add_indicators(df)
                
                # Get AI analysis
                analysis = self.ai_analyzer.analyze(symbol, df)
                
                # Send chart with analysis
                with open(chart_path, 'rb') as photo:
                    update.message.reply_photo(
                        photo=photo,
                        caption=f"ðŸ“Š *{symbol} Technical Analysis*\n\n{analysis}",
                        parse_mode=ParseMode.MARKDOWN
                    )
                
                # Clean up file
                try:
                    os.remove(chart_path)
                except:
                    pass
            
            # Delete processing message
            context.bot.delete_message(
                chat_id=update.effective_chat.id,
                message_id=processing_msg.message_id
            )
                
        except Exception as e:
            logger.error(f"Error in chart command: {str(e)}")
            update.message.reply_text(f"Error generating charts: {str(e)}")
    
    def cmd_portfolio(self, update: Update, context: CallbackContext):
        """Handler for /portfolio command"""
        # Default portfolio - in a real app, this would be user-specific
        portfolio = ["AAPL", "MSFT", "TSLA", "NVDA", "GOOGL"]
        
        # Send processing message
        processing_msg = update.message.reply_text("Generating portfolio overview, please wait...")
        
        try:
            # Generate portfolio summary
            summary = "ðŸ“ˆ *Portfolio Overview*\n\n"
            
            for symbol in portfolio:
                # Generate chart
                chart_path = self.chart_renderer.render(symbol)
                
                # Get data for AI analysis
                df = self.chart_renderer._fetch_data(symbol)
                df = self.chart_renderer._add_indicators(df)
                
                # Get brief AI analysis
                analysis = self.ai_analyzer.analyze(symbol, df, brief=True)
                
                # Add to summary
                summary += f"*{symbol}*: {analysis}\n\n"
                
                # Send chart
                with open(chart_path, 'rb') as photo:
                    update.message.reply_photo(
                        photo=photo,
                        caption=f"{symbol}",
                        parse_mode=ParseMode.MARKDOWN
                    )
                
                # Clean up file
                try:
                    os.remove(chart_path)
                except:
                    pass
            
            # Send summary
            update.message.reply_text(summary, parse_mode=ParseMode.MARKDOWN)
            
            # Delete processing message
            context.bot.delete_message(
                chat_id=update.effective_chat.id,
                message_id=processing_msg.message_id
            )
                
        except Exception as e:
            logger.error(f"Error in portfolio command: {str(e)}")
            update.message.reply_text(f"Error generating portfolio: {str(e)}")
    
    def run(self):
        """Start the bot"""
        self.updater.start_polling()
        logger.info("Bot started polling")
        self.updater.idle()


if __name__ == "__main__":
    try:
        bot = TelegramChartBot()
        logger.info("Starting bot...")
        bot.run()
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        sys.exit(1) 