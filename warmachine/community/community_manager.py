"""


Community Manager - User subscription and group management system





This module manages user subscriptions, group memberships, and permissions for


the WarMachine trading platform. It enables subscription-based access to


strategies and reports across multiple platforms.


"""





import os


import logging


import json


import time


import uuid


import sqlite3


from datetime import datetime, timedelta


from typing import Dict, Any, Optional, List, Union


from pathlib import Path


import threading


from telegram import Update


from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes





# Set up logging


logger = logging.getLogger(__name__)





# User plan levels


USER_LEVELS = {


    "free": {


        "name": "Free",


        "max_strategies": 2,


        "features": ["public_reports", "basic_alerts"],


        "channels": ["public"]


    },


    "trader": {


        "name": "Trader",


        "max_strategies": 5,


        "features": ["public_reports", "basic_alerts", "strategy_subscription", "portfolio_tracking"],


        "channels": ["public", "traders"]


    },


    "pro_trader": {


        "name": "Pro Trader",


        "max_strategies": 10,


        "features": ["public_reports", "advanced_alerts", "strategy_subscription", "portfolio_tracking", "ai_backtests"],


        "channels": ["public", "traders", "pro_traders"]


    },


    "vip": {


        "name": "VIP Trader",


        "max_strategies": 0,  # unlimited


        "features": ["public_reports", "advanced_alerts", "strategy_subscription", "portfolio_tracking", "ai_backtests", "custom_strategies", "voice_reports"],


        "channels": ["public", "traders", "pro_traders", "vip"]


    }


}





class CommunityManager:


    """Manager for user subscriptions and community features"""


    


    def __init__(self, config: Dict[str, Any]):


        """


        Initialize the Community Manager


        


        Args:


            config: Configuration dictionary


        """


        self.config = config


        self.community_config = config.get("community", {})


        self.thread = None


        self.running = False


        self._shutdown_event = threading.Event()


        


        # Initialize Telegram bot


        self.bot = None


        self._init_telegram_bot()


        


        # Database setup


        self.db_path = os.path.join("data", "database", "community.db")


        self.initialize_database()


        


        # Platform channels mapping


        self.platform_channels = {


            "telegram": {


                "public": self.community_config.get("telegram_public_group", ""),


                "traders": self.community_config.get("telegram_traders_group", ""),


                "pro_traders": self.community_config.get("telegram_pro_traders_group", ""),


                "vip": self.community_config.get("telegram_vip_group", "")


            },


            "discord": {


                "public": self.community_config.get("discord_public_channel", ""),


                "traders": self.community_config.get("discord_traders_channel", ""),


                "pro_traders": self.community_config.get("discord_pro_traders_channel", ""),


                "vip": self.community_config.get("discord_vip_channel", "")


            }


        }


        


        logger.info("Community Manager initialized")


        


    def initialize_database(self):


        """Initialize SQLite database for community management"""


        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)


        


        try:


            conn = sqlite3.connect(self.db_path)


            cursor = conn.cursor()


            


            # Users table


            cursor.execute('''


                CREATE TABLE IF NOT EXISTS users (


                    id TEXT PRIMARY KEY,


                    username TEXT,


                    email TEXT UNIQUE,


                    password_hash TEXT,


                    level TEXT DEFAULT 'free',


                    created_at TEXT,


                    last_login TEXT,


                    telegram_id TEXT,


                    discord_id TEXT


                )


            ''')


            


            # Subscriptions table


            cursor.execute('''


                CREATE TABLE IF NOT EXISTS subscriptions (


                    id TEXT PRIMARY KEY,


                    user_id TEXT,


                    plan TEXT,


                    start_date TEXT,


                    end_date TEXT,


                    payment_id TEXT,


                    is_active INTEGER DEFAULT 1,


                    FOREIGN KEY (user_id) REFERENCES users(id)


                )


            ''')


            


            # Strategy subscriptions table


            cursor.execute('''


                CREATE TABLE IF NOT EXISTS strategy_subscriptions (


                    id TEXT PRIMARY KEY,


                    user_id TEXT,


                    strategy_id TEXT,


                    subscribed_at TEXT,


                    is_active INTEGER DEFAULT 1,


                    FOREIGN KEY (user_id) REFERENCES users(id)


                )


            ''')


            


            # User tokens table


            cursor.execute('''


                CREATE TABLE IF NOT EXISTS user_tokens (


                    token TEXT PRIMARY KEY,


                    user_id TEXT,


                    created_at TEXT,


                    expires_at TEXT,


                    is_valid INTEGER DEFAULT 1,


                    FOREIGN KEY (user_id) REFERENCES users(id)


                )


            ''')


            


            conn.commit()


            conn.close()


            logger.info("Community database initialized")


            


        except Exception as e:


            logger.error(f"Failed to initialize community database: {str(e)}")


            


    def register_user(self, username: str, email: str, password_hash: str, level: str = "free") -> Optional[Dict[str, Any]]:


        """


        Register a new user


        


        Args:


            username: User's username


            email: User's email


            password_hash: Hashed password


            level: User access level (free, trader, pro_trader, vip)


            


        Returns:


            User data dictionary or None if failed


        """


        try:


            conn = sqlite3.connect(self.db_path)


            cursor = conn.cursor()


            


            # Check if user already exists


            cursor.execute("SELECT id FROM users WHERE email = ?", (email,))


            if cursor.fetchone():


                logger.warning(f"User with email {email} already exists")


                conn.close()


                return None


                


            # Create user


            user_id = str(uuid.uuid4())


            now = datetime.now().isoformat()


            


            cursor.execute(


                "INSERT INTO users (id, username, email, password_hash, level, created_at, last_login) VALUES (?, ?, ?, ?, ?, ?, ?)",


                (user_id, username, email, password_hash, level, now, now)


            )


            


            conn.commit()


            conn.close()


            


            logger.info(f"User registered: {username} ({user_id}) - {level}")


            


            return {


                "id": user_id,


                "username": username,


                "email": email,


                "level": level,


                "created_at": now


            }


            


        except Exception as e:


            logger.error(f"Failed to register user: {str(e)}")


            return None


            


    def authenticate_user(self, email: str, password_hash: str) -> Optional[Dict[str, Any]]:


        """


        Authenticate a user


        


        Args:


            email: User's email


            password_hash: Hashed password


            


        Returns:


            User data dictionary or None if authentication failed


        """


        try:


            conn = sqlite3.connect(self.db_path)


            cursor = conn.cursor()


            


            cursor.execute(


                "SELECT id, username, email, level, created_at FROM users WHERE email = ? AND password_hash = ?",


                (email, password_hash)


            )


            


            result = cursor.fetchone()


            


            if result:


                user_id, username, email, level, created_at = result


                


                # Update last login


                now = datetime.now().isoformat()


                cursor.execute(


                    "UPDATE users SET last_login = ? WHERE id = ?",


                    (now, user_id)


                )


                


                conn.commit()


                


                # Generate token


                token = self.generate_user_token(user_id)


                


                user_data = {


                    "id": user_id,


                    "username": username,


                    "email": email,


                    "level": level,


                    "created_at": created_at,


                    "token": token


                }


                


                conn.close()


                logger.info(f"User authenticated: {username} ({user_id})")


                return user_data


            else:


                conn.close()


                logger.warning(f"Authentication failed for email: {email}")


                return None


                


        except Exception as e:


            logger.error(f"Failed to authenticate user: {str(e)}")


            return None


            


    def generate_user_token(self, user_id: str) -> str:


        """


        Generate authentication token for user


        


        Args:


            user_id: User ID


            


        Returns:


            Authentication token


        """


        try:


            conn = sqlite3.connect(self.db_path)


            cursor = conn.cursor()


            


            # Invalidate any existing tokens


            cursor.execute(


                "UPDATE user_tokens SET is_valid = 0 WHERE user_id = ?",


                (user_id,)


            )


            


            # Generate new token


            token = str(uuid.uuid4())


            now = datetime.now().isoformat()


            expires_at = (datetime.now() + timedelta(days=7)).isoformat()


            


            cursor.execute(


                "INSERT INTO user_tokens (token, user_id, created_at, expires_at, is_valid) VALUES (?, ?, ?, ?, 1)",


                (token, user_id, now, expires_at)


            )


            


            conn.commit()


            conn.close()


            


            return token


            


        except Exception as e:


            logger.error(f"Failed to generate user token: {str(e)}")


            return ""


            


    def validate_token(self, token: str) -> Optional[Dict[str, Any]]:


        """


        Validate user token


        


        Args:


            token: Authentication token


            


        Returns:


            User data dictionary or None if token is invalid


        """


        try:


            conn = sqlite3.connect(self.db_path)


            cursor = conn.cursor()


            


            now = datetime.now().isoformat()


            


            # Check token


            cursor.execute(


                """


                SELECT ut.user_id, u.username, u.email, u.level 


                FROM user_tokens ut 


                JOIN users u ON ut.user_id = u.id 


                WHERE ut.token = ? AND ut.is_valid = 1 AND ut.expires_at > ?


                """,


                (token, now)


            )


            


            result = cursor.fetchone()


            


            if result:


                user_id, username, email, level = result


                conn.close()


                


                return {


                    "id": user_id,


                    "username": username,


                    "email": email,


                    "level": level


                }


            else:


                conn.close()


                logger.warning(f"Invalid token: {token}")


                return None


                


        except Exception as e:


            logger.error(f"Failed to validate token: {str(e)}")


            return None


            


    def update_user_level(self, user_id: str, level: str) -> bool:


        """


        Update user subscription level


        


        Args:


            user_id: User ID


            level: New subscription level


            


        Returns:


            Success status


        """


        if level not in USER_LEVELS:


            logger.error(f"Invalid user level: {level}")


            return False


            


        try:


            conn = sqlite3.connect(self.db_path)


            cursor = conn.cursor()


            


            cursor.execute(


                "UPDATE users SET level = ? WHERE id = ?",


                (level, user_id)


            )


            


            conn.commit()


            conn.close()


            


            logger.info(f"Updated user {user_id} to level: {level}")


            return True


            


        except Exception as e:


            logger.error(f"Failed to update user level: {str(e)}")


            return False


            


    def create_subscription(self, user_id: str, plan: str, duration_days: int = 30, payment_id: str = "") -> bool:


        """


        Create a new subscription


        


        Args:


            user_id: User ID


            plan: Subscription plan (trader, pro_trader, vip)


            duration_days: Subscription duration in days


            payment_id: Payment reference ID


            


        Returns:


            Success status


        """


        if plan not in USER_LEVELS or plan == "free":


            logger.error(f"Invalid subscription plan: {plan}")


            return False


            


        try:


            conn = sqlite3.connect(self.db_path)


            cursor = conn.cursor()


            


            # Check if user exists


            cursor.execute("SELECT id FROM users WHERE id = ?", (user_id,))


            if not cursor.fetchone():


                logger.error(f"User not found: {user_id}")


                conn.close()


                return False


                


            # Deactivate existing subscriptions


            cursor.execute(


                "UPDATE subscriptions SET is_active = 0 WHERE user_id = ? AND is_active = 1",


                (user_id,)


            )


            


            # Create new subscription


            subscription_id = str(uuid.uuid4())


            start_date = datetime.now().isoformat()


            end_date = (datetime.now() + timedelta(days=duration_days)).isoformat()


            


            cursor.execute(


                "INSERT INTO subscriptions (id, user_id, plan, start_date, end_date, payment_id, is_active) VALUES (?, ?, ?, ?, ?, ?, 1)",


                (subscription_id, user_id, plan, start_date, end_date, payment_id)


            )


            


            # Update user level


            cursor.execute(


                "UPDATE users SET level = ? WHERE id = ?",


                (plan, user_id)


            )


            


            conn.commit()


            conn.close()


            


            logger.info(f"Created subscription for user {user_id}: {plan} until {end_date}")


            return True


            


        except Exception as e:


            logger.error(f"Failed to create subscription: {str(e)}")


            return False


            


    def get_active_subscription(self, user_id: str) -> Optional[Dict[str, Any]]:


        """


        Get active subscription for user


        


        Args:


            user_id: User ID


            


        Returns:


            Subscription data dictionary or None if no active subscription


        """


        try:


            conn = sqlite3.connect(self.db_path)


            cursor = conn.cursor()


            


            cursor.execute(


                "SELECT id, plan, start_date, end_date, payment_id FROM subscriptions WHERE user_id = ? AND is_active = 1",


                (user_id,)


            )


            


            result = cursor.fetchone()


            


            if result:


                subscription_id, plan, start_date, end_date, payment_id = result


                


                subscription_data = {


                    "id": subscription_id,


                    "plan": plan,


                    "start_date": start_date,


                    "end_date": end_date,


                    "payment_id": payment_id


                }


                


                conn.close()


                return subscription_data


            else:


                conn.close()


                return None


                


        except Exception as e:


            logger.error(f"Failed to get active subscription: {str(e)}")


            return None


            


    def subscribe_to_strategy(self, user_id: str, strategy_id: str) -> bool:


        """


        Subscribe user to a strategy


        


        Args:


            user_id: User ID


            strategy_id: Strategy ID


            


        Returns:


            Success status


        """


        try:


            conn = sqlite3.connect(self.db_path)


            cursor = conn.cursor()


            


            # Check if user exists


            cursor.execute("SELECT level FROM users WHERE id = ?", (user_id,))


            result = cursor.fetchone()


            


            if not result:


                logger.error(f"User not found: {user_id}")


                conn.close()


                return False


                


            user_level = result[0]


            


            # Check strategy subscription limit


            cursor.execute(


                "SELECT COUNT(*) FROM strategy_subscriptions WHERE user_id = ? AND is_active = 1",


                (user_id,)


            )


            


            current_count = cursor.fetchone()[0]


            max_strategies = USER_LEVELS.get(user_level, {}).get("max_strategies", 0)


            


            # If max_strategies is 0, it means unlimited


            if max_strategies > 0 and current_count >= max_strategies:


                logger.warning(f"User {user_id} has reached strategy subscription limit: {max_strategies}")


                conn.close()


                return False


                


            # Check if already subscribed


            cursor.execute(


                "SELECT id FROM strategy_subscriptions WHERE user_id = ? AND strategy_id = ? AND is_active = 1",


                (user_id, strategy_id)


            )


            


            if cursor.fetchone():


                logger.info(f"User {user_id} is already subscribed to strategy {strategy_id}")


                conn.close()


                return True


                


            # Create subscription


            subscription_id = str(uuid.uuid4())


            now = datetime.now().isoformat()


            


            cursor.execute(


                "INSERT INTO strategy_subscriptions (id, user_id, strategy_id, subscribed_at, is_active) VALUES (?, ?, ?, ?, 1)",


                (subscription_id, user_id, strategy_id, now)


            )


            


            conn.commit()


            conn.close()


            


            logger.info(f"User {user_id} subscribed to strategy {strategy_id}")


            return True


            


        except Exception as e:


            logger.error(f"Failed to subscribe to strategy: {str(e)}")


            return False


            


    def unsubscribe_from_strategy(self, user_id: str, strategy_id: str) -> bool:


        """


        Unsubscribe user from a strategy


        


        Args:


            user_id: User ID


            strategy_id: Strategy ID


            


        Returns:


            Success status


        """


        try:


            conn = sqlite3.connect(self.db_path)


            cursor = conn.cursor()


            


            cursor.execute(


                "UPDATE strategy_subscriptions SET is_active = 0 WHERE user_id = ? AND strategy_id = ? AND is_active = 1",


                (user_id, strategy_id)


            )


            


            conn.commit()


            conn.close()


            


            logger.info(f"User {user_id} unsubscribed from strategy {strategy_id}")


            return True


            


        except Exception as e:


            logger.error(f"Failed to unsubscribe from strategy: {str(e)}")


            return False


            


    def get_user_subscribed_strategies(self, user_id: str) -> List[str]:


        """


        Get list of strategies the user is subscribed to


        


        Args:


            user_id: User ID


            


        Returns:


            List of strategy IDs


        """


        try:


            conn = sqlite3.connect(self.db_path)


            cursor = conn.cursor()


            


            cursor.execute(


                "SELECT strategy_id FROM strategy_subscriptions WHERE user_id = ? AND is_active = 1",


                (user_id,)


            )


            


            results = cursor.fetchall()


            conn.close()


            


            return [row[0] for row in results]


            


        except Exception as e:


            logger.error(f"Failed to get user subscribed strategies: {str(e)}")


            return []


            


    def get_strategy_subscribers(self, strategy_id: str) -> List[Dict[str, Any]]:


        """


        Get list of users subscribed to a strategy


        


        Args:


            strategy_id: Strategy ID


            


        Returns:


            List of user dictionaries


        """


        try:


            conn = sqlite3.connect(self.db_path)


            cursor = conn.cursor()


            


            cursor.execute(


                """


                SELECT u.id, u.username, u.email, u.level, u.telegram_id, u.discord_id 


                FROM users u 


                JOIN strategy_subscriptions ss ON u.id = ss.user_id 


                WHERE ss.strategy_id = ? AND ss.is_active = 1


                """,


                (strategy_id,)


            )


            


            results = cursor.fetchall()


            conn.close()


            


            subscribers = []


            for row in results:


                user_id, username, email, level, telegram_id, discord_id = row


                subscribers.append({


                    "id": user_id,


                    "username": username,


                    "email": email,


                    "level": level,


                    "telegram_id": telegram_id,


                    "discord_id": discord_id


                })


                


            return subscribers


            


        except Exception as e:


            logger.error(f"Failed to get strategy subscribers: {str(e)}")


            return []


            


    def link_platform_account(self, user_id: str, platform: str, platform_id: str) -> bool:


        """


        Link a platform account to user


        


        Args:


            user_id: User ID


            platform: Platform name (telegram, discord)


            platform_id: Platform-specific ID


            


        Returns:


            Success status


        """


        if platform not in ["telegram", "discord"]:


            logger.error(f"Unsupported platform: {platform}")


            return False


            


        try:


            conn = sqlite3.connect(self.db_path)


            cursor = conn.cursor()


            


            # Update user's platform ID


            if platform == "telegram":


                cursor.execute(


                    "UPDATE users SET telegram_id = ? WHERE id = ?",


                    (platform_id, user_id)


                )


            elif platform == "discord":


                cursor.execute(


                    "UPDATE users SET discord_id = ? WHERE id = ?",


                    (platform_id, user_id)


                )


                


            conn.commit()


            conn.close()


            


            logger.info(f"Linked {platform} account {platform_id} to user {user_id}")


            return True


            


        except Exception as e:


            logger.error(f"Failed to link platform account: {str(e)}")


            return False


            


    def get_user_channels(self, user_id: str) -> Dict[str, List[str]]:


        """


        Get channels the user has access to across platforms


        


        Args:


            user_id: User ID


            


        Returns:


            Dictionary of platform -> channel IDs


        """


        try:


            conn = sqlite3.connect(self.db_path)


            cursor = conn.cursor()


            


            cursor.execute("SELECT level FROM users WHERE id = ?", (user_id,))


            result = cursor.fetchone()


            


            if not result:


                logger.error(f"User not found: {user_id}")


                conn.close()


                return {}


                


            user_level = result[0]


            conn.close()


            


            # Get channels for user level


            channels_by_platform = {}


            user_channels = USER_LEVELS.get(user_level, {}).get("channels", [])


            


            for platform, channels in self.platform_channels.items():


                platform_channel_ids = []


                


                for channel_type in user_channels:


                    channel_id = channels.get(channel_type, "")


                    if channel_id:


                        platform_channel_ids.append(channel_id)


                        


                channels_by_platform[platform] = platform_channel_ids


                


            return channels_by_platform


            


        except Exception as e:


            logger.error(f"Failed to get user channels: {str(e)}")


            return {}


            


    def get_user_by_platform_id(self, platform: str, platform_id: str) -> Optional[Dict[str, Any]]:


        """


        Get user by platform-specific ID


        


        Args:


            platform: Platform name (telegram, discord)


            platform_id: Platform-specific ID


            


        Returns:


            User data dictionary or None if not found


        """


        if platform not in ["telegram", "discord"]:


            logger.error(f"Unsupported platform: {platform}")


            return None


            


        try:


            conn = sqlite3.connect(self.db_path)


            cursor = conn.cursor()


            


            if platform == "telegram":


                cursor.execute(


                    "SELECT id, username, email, level FROM users WHERE telegram_id = ?",


                    (platform_id,)


                )


            elif platform == "discord":


                cursor.execute(


                    "SELECT id, username, email, level FROM users WHERE discord_id = ?",


                    (platform_id,)


                )


                


            result = cursor.fetchone()


            


            if result:


                user_id, username, email, level = result


                


                user_data = {


                    "id": user_id,


                    "username": username,


                    "email": email,


                    "level": level


                }


                


                conn.close()


                return user_data


            else:


                conn.close()


                return None


                


        except Exception as e:


            logger.error(f"Failed to get user by platform ID: {str(e)}")


            return None


            


    def check_feature_access(self, user_id: str, feature: str) -> bool:


        """


        Check if user has access to a feature


        


        Args:


            user_id: User ID


            feature: Feature name


            


        Returns:


            True if user has access, False otherwise


        """


        try:


            conn = sqlite3.connect(self.db_path)


            cursor = conn.cursor()


            


            cursor.execute("SELECT level FROM users WHERE id = ?", (user_id,))


            result = cursor.fetchone()


            


            if not result:


                logger.error(f"User not found: {user_id}")


                conn.close()


                return False


                


            user_level = result[0]


            conn.close()


            


            # Check if feature is available for user level


            user_features = USER_LEVELS.get(user_level, {}).get("features", [])


            return feature in user_features


            


        except Exception as e:


            logger.error(f"Failed to check feature access: {str(e)}")


            return False


            


    def get_channel_subscribers(self, platform: str, channel_type: str) -> List[Dict[str, Any]]:


        """


        Get users with access to a specific channel


        


        Args:


            platform: Platform name (telegram, discord)


            channel_type: Channel type (public, traders, pro_traders, vip)


            


        Returns:


            List of user dictionaries


        """


        if platform not in ["telegram", "discord"] or channel_type not in ["public", "traders", "pro_traders", "vip"]:


            logger.error(f"Invalid platform or channel type: {platform} / {channel_type}")


            return []


            


        try:


            conn = sqlite3.connect(self.db_path)


            cursor = conn.cursor()


            


            # Find levels that have access to this channel


            eligible_levels = []


            for level, data in USER_LEVELS.items():


                if channel_type in data.get("channels", []):


                    eligible_levels.append(level)


                    


            if not eligible_levels:


                conn.close()


                return []


                


            # Get users with eligible levels


            placeholders = ",".join(["?"] * len(eligible_levels))


            


            if platform == "telegram":


                cursor.execute(


                    f"""


                    SELECT id, username, email, level, telegram_id 


                    FROM users 


                    WHERE level IN ({placeholders}) AND telegram_id IS NOT NULL


                    """,


                    eligible_levels


                )


            elif platform == "discord":


                cursor.execute(


                    f"""


                    SELECT id, username, email, level, discord_id 


                    FROM users 


                    WHERE level IN ({placeholders}) AND discord_id IS NOT NULL


                    """,


                    eligible_levels


                )


                


            results = cursor.fetchall()


            conn.close()


            


            subscribers = []


            for row in results:


                user_id, username, email, level, platform_id = row


                subscribers.append({


                    "id": user_id,


                    "username": username,


                    "email": email,


                    "level": level,


                    f"{platform}_id": platform_id


                })


                


            return subscribers


            


        except Exception as e:


            logger.error(f"Failed to get channel subscribers: {str(e)}")


            return []


            


    def _init_telegram_bot(self):


        """Initialize Telegram bot"""


        try:


            # Get bot token from config


            bot_token = self.community_config.get('telegram_bot_token')


            if not bot_token:


                logger.warning("No Telegram bot token found in config")


                return


                


            # Create bot application


            self.bot = Application.builder().token(bot_token).build()


            


            # Add command handlers


            self.bot.add_handler(CommandHandler("start", self._cmd_start))


            self.bot.add_handler(CommandHandler("help", self._cmd_help))


            self.bot.add_handler(CommandHandler("status", self._cmd_status))


            self.bot.add_handler(CommandHandler("start_component", self._cmd_start_component))


            self.bot.add_handler(CommandHandler("stop_component", self._cmd_stop_component))


            self.bot.add_handler(CommandHandler("component_status", self._cmd_component_status))


            


            logger.info("Telegram bot initialized")


            


        except ImportError as e:


            logger.warning(f"Failed to initialize Telegram bot: {e}")


            


    async def start(self):


        """Start the community manager"""


        if not self.thread and self.bot:


            self.running = True


            self._shutdown_event.clear()


            


            self.thread = threading.Thread(


                target=self._run_bot,


                daemon=True,


                name="TelegramBotThread"


            )


            self.thread.start()


            logger.info("Telegram bot started in background thread")


            return True


        return False


        


    async def shutdown(self):


        """Shutdown the community manager"""


        logger.info("Shutting down community manager...")


        self.running = False


        self._shutdown_event.set()


        


        if self.thread and self.thread.is_alive():


            self.thread.join(timeout=5.0)


            if self.thread.is_alive():


                logger.warning("Telegram bot thread did not stop gracefully")


                


        logger.info("Community manager shutdown complete")


        


    def _run_bot(self):


        """Run the Telegram bot"""


        try:


            if self.bot:


                self.bot.run_polling()


        except Exception as e:


            logger.error(f"Failed to run Telegram bot: {str(e)}")


            self.running = False


            


    async def _cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):


        """Handle /start command"""


        await update.message.reply_text(


            "Welcome to WarMachine Trading Platform!\n\n"


            "Available commands:\n"


            "/help - Show help message\n"


            "/status - Show system status\n"


            "/start_component <name> - Start a component\n"


            "/stop_component <name> - Stop a component\n"


            "/component_status <name> - Show component status"


        )


        


    async def _cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):


        """Handle /help command"""


        await update.message.reply_text(


            "WarMachine Trading Platform Help\n\n"


            "Component Control:\n"


            "- /start_component <name> - Start a component\n"


            "- /stop_component <name> - Stop a component\n"


            "- /component_status <name> - Show component status\n\n"


            "Available components:\n"


            "- market_data - Market data feed\n"


            "- web_dashboard - Web dashboard\n"


            "- web_api - Web API server\n"


            "- market_watcher - Market watcher\n"


            "- scheduler - Routine scheduler\n"


            "- ai_analyzer - AI analyzer\n"


            "- ai_commander - AI commander\n"


            "- ai_model_router - AI model router\n"


            "- ai_reporter - AI reporter\n"


            "- ai_self_improvement - AI self-improvement"


        )


        


    async def _cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):


        """Handle /status command"""


        try:


            from run_warmachine import WarMachine


            warmachine = WarMachine()


            


            status = {


                "market_data": await warmachine.get_component_status("market_data"),


                "web_dashboard": await warmachine.get_component_status("web_dashboard"),


                "web_api": await warmachine.get_component_status("web_api"),


                "market_watcher": await warmachine.get_component_status("market_watcher"),


                "scheduler": await warmachine.get_component_status("scheduler"),


                "ai_analyzer": await warmachine.get_component_status("ai_analyzer"),


                "ai_commander": await warmachine.get_component_status("ai_commander"),


                "ai_model_router": await warmachine.get_component_status("ai_model_router"),


                "ai_reporter": await warmachine.get_component_status("ai_reporter"),


                "ai_self_improvement": await warmachine.get_component_status("ai_self_improvement")


            }


            


            # Format status message


            message = "System Status:\n\n"


            for component, comp_status in status.items():


                if comp_status.get("status") == "running":


                    message += f"✅ {component}: Running\n"


                elif comp_status.get("status") == "stopped":


                    message += f"❌ {component}: Stopped\n"


                else:


                    message += f"⚠️ {component}: Unknown\n"


                    


            await update.message.reply_text(message)


            


        except Exception as e:


            await update.message.reply_text(f"Failed to get system status: {str(e)}")


            


    async def _cmd_start_component(self, update: Update, context: ContextTypes.DEFAULT_TYPE):


        """Handle /start_component command"""


        try:


            if not context.args:


                await update.message.reply_text("Please specify a component name")


                return


                


            component_name = context.args[0]


            from run_warmachine import WarMachine


            warmachine = WarMachine()


            


            if await warmachine.start_component(component_name):


                await update.message.reply_text(f"Started component: {component_name}")


            else:


                await update.message.reply_text(f"Failed to start component: {component_name}")


                


        except Exception as e:


            await update.message.reply_text(f"Failed to start component: {str(e)}")


            


    async def _cmd_stop_component(self, update: Update, context: ContextTypes.DEFAULT_TYPE):


        """Handle /stop_component command"""


        try:


            if not context.args:


                await update.message.reply_text("Please specify a component name")


                return


                


            component_name = context.args[0]


            from run_warmachine import WarMachine


            warmachine = WarMachine()


            


            if await warmachine.stop_component(component_name):


                await update.message.reply_text(f"Stopped component: {component_name}")


            else:


                await update.message.reply_text(f"Failed to stop component: {component_name}")


                


        except Exception as e:


            await update.message.reply_text(f"Failed to stop component: {str(e)}")


            


    async def _cmd_component_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):


        """Handle /component_status command"""


        try:


            if not context.args:


                await update.message.reply_text("Please specify a component name")


                return


                


            component_name = context.args[0]


            from run_warmachine import WarMachine


            warmachine = WarMachine()


            


            status = await warmachine.get_component_status(component_name)


            


            # Format status message


            if status.get("status") == "running":


                message = f"✅ {component_name}: Running\n"


            elif status.get("status") == "stopped":


                message = f"❌ {component_name}: Stopped\n"


            else:


                message = f"⚠️ {component_name}: Unknown\n"


                


            # Add additional status information if available


            for key, value in status.items():


                if key != "status":


                    message += f"{key}: {value}\n"


                    


            await update.message.reply_text(message)


            


        except Exception as e:


            await update.message.reply_text(f"Failed to get component status: {str(e)}") 