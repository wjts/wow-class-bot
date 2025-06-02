import discord
from discord.ext import commands
import asyncio
import logging
from src.config import DISCORD_TOKEN, GUILD_ID, CHANNEL_ID
from src.sheets_handler import SheetsHandler
from src.commands import Commands
from src.logging_config import setup_logging, log_startup_info, log_shutdown_info

# Set up enhanced logging
logger = setup_logging()

class ClassSpecBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.guilds = True
        
        super().__init__(
            command_prefix='!',
            intents=intents,
            help_command=None
        )
        
        self.sheets_handler = SheetsHandler()
        self.commands_handler = None
        
    async def setup_hook(self):
        """Called when the bot is starting up"""
        log_startup_info()
        
        # Setup Google Sheets
        logger.info("Setting up Google Sheets connection...")
        sheets_success = await self.sheets_handler.setup()
        if not sheets_success:
            logger.error("Failed to setup Google Sheets!")
            return
        
        # Setup commands
        logger.info("Setting up Discord commands...")
        self.commands_handler = Commands(self, self.sheets_handler)
        
        # Sync commands
        if GUILD_ID:
            guild = discord.Object(id=GUILD_ID)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            logger.info(f"Synced commands to guild {GUILD_ID}")
        else:
            await self.tree.sync()
            logger.info("Synced commands globally")
        
        logger.info("Bot setup completed successfully")
    
    async def on_ready(self):
        """Called when the bot is ready"""
        logger.info(f'Bot user: {self.user} (ID: {self.user.id})')
        logger.info(f'Connected to {len(self.guilds)} guild(s)')
        
        if CHANNEL_ID:
            channel = self.get_channel(CHANNEL_ID)
            if channel:
                logger.info(f"Bot will listen on channel: {channel.name} (ID: {CHANNEL_ID})")
            else:
                logger.warning(f"Could not find channel with ID: {CHANNEL_ID}")
        else:
            logger.info("Bot will listen on all channels (no channel restriction)")
        
        logger.info("Discord WoW Class Management Bot is ready!")
    
    async def close(self):
        """Called when the bot is shutting down"""
        log_shutdown_info()
        await super().close()

# Create and run the bot
bot = ClassSpecBot()

if __name__ == "__main__":
    if not DISCORD_TOKEN:
        logger.error("DISCORD_TOKEN environment variable not set!")
        exit(1)
    
    try:
        logger.info("Starting Discord bot...")
        bot.run(DISCORD_TOKEN)
    except KeyboardInterrupt:
        logger.info("Bot stopped by user (Ctrl+C)")
    except Exception as e:
        logger.error(f"Bot crashed with error: {e}")
        raise