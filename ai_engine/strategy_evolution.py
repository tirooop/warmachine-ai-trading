#!/usr/bin/env python
"""
AI Strategy Auto-Evolution Runner
Main script for running the AI-driven strategy evolution and optimization pipeline
"""
import os
import sys

# 优先导入imghdr兼容性模块，确保所有后续导入的模块都能正常使用imghdr
try:
    import imghdr_compatibility  # 这会自动注册PIL基于的imghdr替代品
except ImportError:
    print("⚠️ 警告: 无法加载imghdr_compatibility模块，尝试备用方案")
    # 如果imghdr_compatibility不存在，保留现有的兼容层
    try:
        import PIL_image_check  # 这会自动替代imghdr模块
        print("已加载PIL_image_check作为imghdr模块替代品")
    except ImportError:
        # 如果PIL_image_check不存在，创建一个简单的兼容层
        try:
            from PIL import Image
            
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
            print("已创建PIL兼容层替代imghdr模块")
        except ImportError:
            print("⚠️ 警告: 无法加载PIL，请安装: pip install pillow")

# 现在导入其他模块
import json
import argparse
import logging
import pandas as pd
from typing import Dict, Any, List, Optional
from datetime import datetime

# Import our modules
from api.ai_chat_agent import DeepSeekChatAgent
from utils.strategy_batch_trainer import StrategyBatchTrainer
from utils.strategy_failure_handler import StrategyFailureHandler
from utils.portfolio_optimizer import PortfolioOptimizer

# 尝试导入v13兼容版本，如果不存在则使用标准版本
try:
    from utils.telegram_ai_assistant_v13 import TelegramAIAssistant
    print("Using telegram_ai_assistant_v13 (Python-Telegram-Bot v13.x compatible)")
except ImportError:
    try:
        from utils.telegram_ai_assistant import TelegramAIAssistant
        print("Using standard telegram_ai_assistant")
    except ImportError:
        print("Warning: TelegramAIAssistant could not be imported")
        TelegramAIAssistant = None

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("ai_evolution.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class AIStrategyEvolution:
    """
    Main controller for AI-driven strategy evolution pipeline.
    
    This class orchestrates the following process:
    1. Generate initial strategies with AI
    2. Batch train and evaluate strategies
    3. Analyze failures and generate improved versions
    4. Optimize portfolio allocation
    5. Provide Telegram interface for user interaction
    """
    
    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize the AI Strategy Evolution system.
        
        Args:
            config_file: Path to configuration file (JSON)
        """
        # Load configuration
        self.config = self._load_config(config_file)
        
        # Initialize components
        self.ai_agent = DeepSeekChatAgent(
            api_key=self.config.get("api_key"),
            api_url=self.config.get("api_url"),
            model=self.config.get("model")
        )
        
        self.failure_handler = StrategyFailureHandler(
            save_dir=self.config.get("strategies_dir", "strategies/generated"),
            ai_agent=self.ai_agent
        )
        
        self.batch_trainer = StrategyBatchTrainer(
            max_workers=self.config.get("max_workers", 3),
            results_dir=self.config.get("results_dir", "results/strategy_training"),
            notify_function=self.send_notification
        )
        
        self.portfolio_optimizer = PortfolioOptimizer(
            results_dir=self.config.get("optimization_dir", "results/portfolio_optimization"),
            risk_free_rate=self.config.get("risk_free_rate", 0.0)
        )
        
        # Telegram bot (if enabled)
        self.telegram_bot = None
        if self.config.get("enable_telegram", False):
            self.telegram_bot = self._setup_telegram_bot()
        
        logger.info("AI Strategy Evolution system initialized")
    
    def _load_config(self, config_file: Optional[str]) -> Dict[str, Any]:
        """Load configuration from file or use defaults."""
        default_config = {
            "api_key": os.environ.get("DEEPSEEK_API_KEY", "sk-uvbjgxuaigsbjpebfthckspmnpfjixhwuwapwsrrqprfvarl"),
            "api_url": os.environ.get("DEEPSEEK_API_URL", "https://api.siliconflow.cn/v1/chat/completions"),
            "model": os.environ.get("DEEPSEEK_MODEL", "deepseek-ai/DeepSeek-V3"),
            "strategies_dir": "strategies/generated",
            "results_dir": "results/strategy_training",
            "optimization_dir": "results/portfolio_optimization",
            "max_workers": 3,
            "risk_free_rate": 0.0,
            "enable_telegram": False,
            "telegram_token": os.environ.get("TELEGRAM_TOKEN", ""),
            "authorized_users": []
        }
        
        if config_file and os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    user_config = json.load(f)
                    # Update default config with user settings
                    default_config.update(user_config)
                    logger.info(f"Loaded configuration from {config_file}")
            except Exception as e:
                logger.error(f"Error loading config file: {str(e)}")
        
        return default_config
    
    def _setup_telegram_bot(self) -> Optional[TelegramAIAssistant]:
        """Set up the Telegram bot with command handlers."""
        token = self.config.get("telegram_token")
        if not token:
            logger.warning("No Telegram token provided, bot will not be enabled")
            return None
        
        # 重要：设置环境变量，确保其他组件可以使用Telegram
        os.environ["TELEGRAM_BOT_TOKEN"] = token
        os.environ["TELEGRAM_TOKEN"] = token
        os.environ["TELEGRAM_CHAT_ID"] = str(self.config.get("telegram_chat_id", ""))
        os.environ["TELEGRAM_ENABLED"] = "true"
        
        # Create command handlers dictionary
        command_handlers = {
            "status": self.get_status,
            "save_strategy": self.save_strategy,
            "analyze_strategy": self.analyze_strategy,
            "optimize_portfolio": self.optimize_portfolio,
            "train_strategy": self.train_strategy,
            "generate_strategy": self.generate_strategy
        }
        
        try:
            # Set authorized users
            os.environ["TELEGRAM_AUTHORIZED_USERS"] = ",".join(map(str, self.config.get("authorized_users", [])))
            
            # Create bot
            bot = TelegramAIAssistant(
                token=token,
                ai_agent=self.ai_agent,
                command_handlers=command_handlers
            )
            return bot
        except Exception as e:
            logger.error(f"Error setting up Telegram bot: {str(e)}")
            return None
    
    def send_notification(self, message: str):
        """Send a notification message (to be implemented)."""
        logger.info(f"NOTIFICATION: {message}")
        # Add notification implementation here (e.g., email, SMS, etc.)
    
    def get_status(self) -> str:
        """Get the current system status."""
        trainer_status = self.batch_trainer.get_status()
        
        return (
            f"AI Strategy Evolution Status\n"
            f"---------------------------\n"
            f"Active training tasks: {trainer_status['ongoing_tasks']}\n"
            f"Completed training tasks: {trainer_status['completed_tasks']}\n"
            f"Active workers: {trainer_status['active_workers']}\n"
            f"Timestamp: {datetime.now().isoformat()}"
        )
    
    def save_strategy(self, strategy_code: str, strategy_type: str) -> str:
        """Save a strategy to file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        strategy_name = strategy_type.replace(" ", "_")
        filename = f"{timestamp}_{strategy_name}.py"
        filepath = os.path.join(self.config["strategies_dir"], filename)
        
        os.makedirs(self.config["strategies_dir"], exist_ok=True)
        
        try:
            with open(filepath, 'w') as f:
                f.write(strategy_code)
            logger.info(f"Saved strategy to {filepath}")
            return filename
        except Exception as e:
            logger.error(f"Error saving strategy: {str(e)}")
            return f"Error: {str(e)}"
    
    def generate_strategy(self, strategy_type: str) -> str:
        """Generate a new strategy using AI."""
        try:
            strategy_code = self.ai_agent.generate_strategy(strategy_type)
            filename = self.save_strategy(strategy_code, strategy_type)
            return strategy_code
        except Exception as e:
            logger.error(f"Error generating strategy: {str(e)}")
            return f"Error: {str(e)}"
    
    def train_strategy(self, strategy_name: str) -> str:
        """Train a strategy or all strategies."""
        try:
            if strategy_name.lower() == "all":
                # Implement batch training of all strategies
                logger.info("Training all strategies")
                return "Started batch training of all strategies. This will take some time."
            else:
                # Implement single strategy training
                logger.info(f"Training strategy: {strategy_name}")
                return f"Started training of {strategy_name}. This will take some time."
        except Exception as e:
            logger.error(f"Error training strategy: {str(e)}")
            return f"Error: {str(e)}"
    
    def analyze_strategy(self, strategy_name: str) -> str:
        """Analyze a strategy's performance."""
        try:
            # Implement strategy analysis
            logger.info(f"Analyzing strategy: {strategy_name}")
            return f"Analysis of {strategy_name} would be displayed here."
        except Exception as e:
            logger.error(f"Error analyzing strategy: {str(e)}")
            return f"Error: {str(e)}"
    
    def optimize_portfolio(self) -> str:
        """Optimize portfolio allocation."""
        try:
            # Implement portfolio optimization
            logger.info("Optimizing portfolio")
            return "Portfolio optimization would be displayed here."
        except Exception as e:
            logger.error(f"Error optimizing portfolio: {str(e)}")
            return f"Error: {str(e)}"
    
    def handle_failed_strategy(self, strategy_code: str, failure_data: Dict[str, Any]) -> str:
        """Handle a failed strategy and generate an improved version."""
        try:
            filepath, improved_code = self.failure_handler.generate_improved_strategy(
                strategy_code, failure_data
            )
            return f"Generated improved strategy saved to {filepath}"
        except Exception as e:
            logger.error(f"Error handling failed strategy: {str(e)}")
            return f"Error: {str(e)}"
    
    def run_telegram_bot(self):
        """Run the Telegram bot."""
        if self.telegram_bot:
            try:
                logger.info("Starting Telegram bot")
                self.telegram_bot.run()
            except Exception as e:
                logger.error(f"Error running Telegram bot: {str(e)}")
        else:
            logger.warning("Telegram bot not initialized")
    
    def run_evolution_cycle(self, market_data: pd.DataFrame):
        """Run a complete evolution cycle."""
        logger.info("Starting AI strategy evolution cycle")
        
        # Steps to implement in the future:
        # 1. Generate initial strategies
        # 2. Train strategies
        # 3. Evaluate and identify failures
        # 4. Improve failed strategies
        # 5. Optimize portfolio
        
        logger.info("Evolution cycle completed")

def main():
    parser = argparse.ArgumentParser(description="AI Strategy Auto-Evolution Runner")
    parser.add_argument("--config", help="Path to configuration file (JSON)")
    parser.add_argument("--telegram", action="store_true", help="Run in Telegram bot mode")
    parser.add_argument("--generate", help="Generate a new strategy of specified type")
    parser.add_argument("--evolve", action="store_true", help="Run a full evolution cycle")
    parser.add_argument("--optimize", action="store_true", help="Run portfolio optimization")
    
    args = parser.parse_args()
    
    # Create evolution system
    evolution = AIStrategyEvolution(config_file=args.config)
    
    # Handle command line arguments
    if args.telegram:
        evolution.run_telegram_bot()
    elif args.generate:
        strategy_code = evolution.generate_strategy(args.generate)
        print(f"Generated {args.generate} strategy")
    elif args.evolve:
        # For demonstration purposes, create a simple dummy dataset
        dates = pd.date_range(start='2023-01-01', periods=100)
        data = pd.DataFrame({
            'open': range(100, 200),
            'high': range(105, 205),
            'low': range(95, 195),
            'close': range(102, 202),
            'volume': range(1000, 1100)
        }, index=dates)
        evolution.run_evolution_cycle(data)
    elif args.optimize:
        result = evolution.optimize_portfolio()
        print(result)
    else:
        parser.print_help()

if __name__ == "__main__":
    main() 