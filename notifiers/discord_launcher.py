#!/usr/bin/env python
"""
WarMachine Discord Bot Launcher - Standalone launcher for Discord bot

This script allows running the Discord bot component separately from the main WarMachine platform.
It also supports Discord webhook events.
"""

import os
import sys
import json
import logging
import discord
from discord.ext import commands, tasks
import asyncio
from datetime import datetime
import aiohttp
from quart import Quart, request, Response
import nacl.signing
from nacl.exceptions import BadSignatureError
import threading
import multiprocessing
import subprocess

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/discord_bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Ensure logs directory exists
os.makedirs("logs", exist_ok=True)

def load_config():
    """Load configuration from file"""
    try:
        config_path = os.path.join("config", "warmachine_config.json")
        with open(config_path, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load configuration: {str(e)}")
        return {}

# Quart app for webhook handling
app = Quart(__name__)

# Global configuration for webhook handler
webhook_config = {
    "public_key": "",
    "application_id": ""
}

@app.route('/discord-webhooks', methods=['POST'])
async def handle_discord_webhook():
    """
    Handle Discord webhook events
    """
    # Validate the request signature
    signature = request.headers.get('X-Signature-Ed25519')
    timestamp = request.headers.get('X-Signature-Timestamp')
    
    if not signature or not timestamp:
        logger.warning("Missing signature headers")
        return Response('Invalid request signature', status=401)
    
    try:
        # Get request body
        body = await request.get_data()
        
        # Verify signature
        verify_key = nacl.signing.VerifyKey(bytes.fromhex(webhook_config["public_key"]))
        verify_key.verify(timestamp.encode() + body, bytes.fromhex(signature))
        
        # Parse the request
        data = await request.get_json()
        logger.info(f"Received webhook event: {data.get('type')}")
        
        # Check if it's a ping
        if data.get('type') == 0:  # PING
            logger.info("Received PING event")
            return Response('', status=204)
        
        # Process event based on type
        if data.get('type') == 1:  # Event
            event = data.get('event', {})
            event_type = event.get('type')
            event_data = event.get('data', {})
            
            logger.info(f"Processing event type: {event_type}")
            
            # Handle different event types
            if event_type == 'APPLICATION_AUTHORIZED':
                integration_type = event_data.get('integration_type')
                user = event_data.get('user', {})
                scopes = event_data.get('scopes', [])
                guild = event_data.get('guild')
                
                context = "user account" if integration_type == 1 else "server"
                logger.info(f"Bot authorized for {context} by user {user.get('username')}")
                
            elif event_type == 'ENTITLEMENT_CREATE':
                logger.info(f"New entitlement created: {event_data.get('id')}")
                
            return Response('', status=204)
        
        return Response('', status=204)
        
    except BadSignatureError:
        logger.warning("Invalid signature")
        return Response('Invalid request signature', status=401)
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        return Response('Internal server error', status=500)

def run_webhook_server(port, public_key, application_id):
    """Run the webhook server in a separate process"""
    try:
        # Set global webhook configuration
        webhook_config["public_key"] = public_key
        webhook_config["application_id"] = application_id
        
        logger.info(f"Starting webhook server on port {port}...")
        app.run(host='0.0.0.0', port=port)
    except Exception as e:
        logger.error(f"Error in webhook server: {str(e)}")

class StandaloneDiscordBot:
    """Standalone Discord Bot for WarMachine Platform"""
    
    def __init__(self, config):
        """
        Initialize the Discord bot
        
        Args:
            config: Platform configuration dictionary
        """
        self.config = config
        self.discord_config = config.get("discord", {})
        self.token = self.discord_config.get("token", "")
        self.public_key = self.discord_config.get("public_key", "")
        self.application_id = self.discord_config.get("application_id", "")
        self.webhook_port = self.discord_config.get("webhook_port", 8080)
        self.webhook_process = None
        
        if not self.token or self.token == "YOUR_DISCORD_BOT_TOKEN_HERE":
            logger.warning("Discord token not set or is a placeholder. Please update your configuration.")
            print("\nTo use the Discord bot, you need to create a bot on the Discord Developer Portal")
            print("1. Go to https://discord.com/developers/applications")
            print("2. Create a new application")
            print("3. Go to the Bot tab and add a bot")
            print("4. Copy the token and add it to config/warmachine_config.json")
            print("5. Enable the Message Content Intent in the Bot tab (or uncomment the line in the code)")
            print("6. Use the OAuth2 URL Generator to invite the bot to your server")
            sys.exit(1)
            
        # Initialize the Discord client
        intents = discord.Intents.default()
        # Only enable message_content if you've enabled it in the Developer Portal
        # intents.message_content = True  # This is a privileged intent
        
        self.bot = commands.Bot(command_prefix=self.discord_config.get("command_prefix", "/"), intents=intents)
        
        # Register event handlers
        self._register_events()
        
        # Register commands
        self._register_commands()
        
        logger.info("Discord bot initialized")
        
    def _register_events(self):
        """Register Discord event handlers"""
        
        @self.bot.event
        async def on_ready():
            """Event fired when bot is ready"""
            logger.info(f"Discord bot is ready: {self.bot.user.name}")
            logger.info(f"Bot ID: {self.bot.user.id}")
            logger.info(f"Command prefix: {self.bot.command_prefix}")
            print(f"\nBot is running as {self.bot.user.name}")
            print(f"Use {self.bot.command_prefix}commands to see available commands")
            
        @self.bot.event
        async def on_command_error(ctx, error):
            """Event fired when a command raises an error"""
            if isinstance(error, commands.CommandNotFound):
                await ctx.send(f"‚ùå Command not found. Use `{self.bot.command_prefix}commands` to see available commands.")
            elif isinstance(error, commands.MissingRequiredArgument):
                await ctx.send(f"‚ùå Missing required argument: {error.param.name}")
            elif isinstance(error, commands.BadArgument):
                await ctx.send(f"‚ùå Bad argument: {error}")
            else:
                logger.error(f"Command error: {error}")
                await ctx.send(f"‚ùå An error occurred: {error}")

    def _register_commands(self):
        """Register Discord bot commands"""
        
        @self.bot.command(name="commands", help="Show available commands")
        async def show_commands(ctx):
            """Show available commands"""
            command_list = [f"`{self.bot.command_prefix}{cmd.name}` - {cmd.help}" for cmd in self.bot.commands]
            
            embed = discord.Embed(
                title="üìã Available Commands",
                description="\n".join(command_list),
                color=discord.Color.blue()
            )
            
            await ctx.send(embed=embed)
        
        @self.bot.command(name="status", help="Check the status of the trading system")
        async def status(ctx):
            """Check the status of the trading system"""
            # Here we would normally check the actual status of the system
            # For demonstration purposes, we'll return a static status
            
            embed = discord.Embed(
                title="ü§ñ WarMachine Status",
                description="Current system status",
                color=discord.Color.green()
            )
            
            embed.add_field(name="AI Commander", value="‚úÖ Running", inline=True)
            embed.add_field(name="Market Watcher", value="‚úÖ Running", inline=True)
            embed.add_field(name="Liquidity Sniper", value="‚úÖ Running", inline=True)
            embed.add_field(name="Web Dashboard", value="‚úÖ Running", inline=True)
            
            embed.add_field(name="Last Updated", value=datetime.now().strftime('%Y-%m-%d %H:%M:%S'), inline=False)
            
            await ctx.send(embed=embed)
            
        @self.bot.command(name="portfolio", help="View current portfolio")
        async def portfolio(ctx):
            """View current portfolio"""
            
            embed = discord.Embed(
                title="üíº Portfolio",
                description="Current portfolio holdings",
                color=discord.Color.gold()
            )
            
            # In a real implementation, this would fetch actual portfolio data
            # For now, return simulated data
            embed.add_field(name="Total Value", value="$125,742.36", inline=False)
            embed.add_field(name="Daily P/L", value="+$1,243.87 (+0.99%)", inline=True)
            embed.add_field(name="Weekly P/L", value="+$3,867.21 (+3.17%)", inline=True)
            
            embed.add_field(name="SPY", value="100 shares @ $457.32", inline=True)
            embed.add_field(name="AAPL", value="50 shares @ $178.54", inline=True)
            embed.add_field(name="TSLA", value="20 shares @ $238.93", inline=True)
            
            embed.set_footer(text=f"Data as of {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            await ctx.send(embed=embed)
            
        @self.bot.command(name="market", help="Get market data for a symbol")
        async def market(ctx, symbol=None):
            """Get market data for a symbol"""
            if not symbol:
                await ctx.send(f"‚ùå Please specify symbol: `{self.bot.command_prefix}market <symbol>`")
                return
                
            symbol = symbol.upper()
            
            # Create embed message
            embed = discord.Embed(
                title=f"üìä {symbol} Market Data",
                description=f"Current market data for {symbol}",
                color=discord.Color.blue()
            )
            
            # In a real implementation, this would fetch actual market data
            # For now, return simulated data
            embed.add_field(name="Price", value="$157.34", inline=True)
            embed.add_field(name="Change", value="+1.2%", inline=True)
            embed.add_field(name="Volume", value="1.2M", inline=True)
            
            embed.set_footer(text=f"Data as of {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            await ctx.send(embed=embed)
            
        @self.bot.command(name="webhook_status", help="Check webhook configuration status")
        async def webhook_status(ctx):
            """Check webhook configuration status"""
            embed = discord.Embed(
                title="üîå Webhook Status",
                description="Discord webhook configuration",
                color=discord.Color.purple()
            )
            
            # Check if webhook server is running
            webhook_status = "‚úÖ Running" if self.webhook_process and self.webhook_process.is_alive() else "‚ùå Not running"
            
            embed.add_field(name="Webhook Server", value=webhook_status, inline=False)
            embed.add_field(name="Webhook URL", value=f"http://your-public-url/discord-webhooks", inline=False)
            embed.add_field(name="Public Key", value=f"{self.public_key[:10]}...{self.public_key[-10:]}" if self.public_key else "Not configured", inline=True)
            embed.add_field(name="Application ID", value=self.application_id if self.application_id else "Not configured", inline=True)
            embed.add_field(name="Local Port", value=str(self.webhook_port), inline=True)
            
            instructions = (
                "To configure webhook events:\n"
                "1. Make sure your webhook URL is publicly accessible\n"
                "2. Go to Discord Developer Portal ‚Üí Your App ‚Üí Webhooks\n"
                "3. Add your public URL under 'Endpoint URL'\n"
                "4. Enable the events you want to receive\n"
                "5. Save changes"
            )
            embed.add_field(name="Setup Instructions", value=instructions, inline=False)
            
            await ctx.send(embed=embed)
    
    def start_webhook_server(self):
        """Start the webhook server in a separate process"""
        if self.webhook_process and self.webhook_process.is_alive():
            logger.info("Webhook server already running")
            return
            
        try:
            # Create a new process for the webhook server
            self.webhook_process = multiprocessing.Process(
                target=run_webhook_server,
                args=(self.webhook_port, self.public_key, self.application_id)
            )
            self.webhook_process.daemon = True
            self.webhook_process.start()
            
            logger.info(f"Webhook server process started with PID {self.webhook_process.pid}")
        except Exception as e:
            logger.error(f"Failed to start webhook server: {str(e)}")
    
    def run(self):
        """Run the Discord bot and webhook server"""
        # Start webhook server if we have required configuration
        if self.public_key and self.application_id:
            self.start_webhook_server()
        else:
            logger.warning("Missing public_key or application_id for webhook server")
        
        # Run Discord bot
        try:
            logger.info("Starting Discord bot...")
            self.bot.run(self.token)
        except discord.errors.LoginFailure:
            logger.error("Failed to login - Invalid Discord token. Please check your configuration.")
            print("\nInvalid Discord bot token! Please update the token in config/warmachine_config.json")
        except Exception as e:
            logger.error(f"Failed to run Discord bot: {str(e)}")

def main():
    """Main function"""
    # Load configuration
    config = load_config()
    
    # Create bot
    bot = StandaloneDiscordBot(config)
    
    # Run bot
    bot.run()

if __name__ == "__main__":
    main() 