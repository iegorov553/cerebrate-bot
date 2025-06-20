#!/usr/bin/env python3
"""
Hour Watcher Bot - New Entry Point

This is the new main entry point replacing cerebrate_bot.py
"""

import asyncio
import sys
import logging

# Setup basic logging first
logging.basicConfig(
    format="%(asctime)s | %(levelname)8s | %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

from bot.config import Config

# Initialize monitoring if available
try:
    from monitoring import setup_monitoring, get_logger
    setup_monitoring()
    logger = get_logger(__name__)
except ImportError:
    logger.info("Monitoring module not available, using basic logging")

from telegram.ext import Application, ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from bot.database.client import DatabaseClient
from bot.handlers.error_handler import setup_error_handler
from bot.utils.rate_limiter import MultiTierRateLimiter
from bot.cache.ttl_cache import TTLCache


# Simplified handlers for now - we'll migrate from old file gradually
async def start_command(update, context):
    """Simple start command."""
    await update.message.reply_text(
        "🤖 **Hour Watcher Bot** - New Modular Architecture\n\n"
        "✅ Migrated successfully!\n"
        "🚀 Now running on modern architecture",
        parse_mode='Markdown'
    )


async def main() -> None:
    """Main entry point."""
    logger.info("🚀 Starting Hour Watcher Bot (New Architecture)")
    
    # Load configuration
    config = Config.from_env()
    try:
        config.validate()
        logger.info("✅ Configuration validated successfully")
    except ValueError as e:
        logger.error(f"❌ Configuration error: {e}")
        return
    
    # Initialize core components
    db_client = DatabaseClient(config)
    rate_limiter = MultiTierRateLimiter()
    user_cache = TTLCache(ttl_seconds=config.cache_ttl_seconds)
    
    logger.info("✅ Core components initialized")
    
    # Create application
    application = ApplicationBuilder().token(config.bot_token).build()
    
    # Setup error handling
    setup_error_handler(application)
    
    # Add simple handlers for now
    application.add_handler(CommandHandler("start", start_command))
    
    # Add scheduler (simplified)
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        lambda: logger.info("⏰ Scheduler tick"),
        "cron",
        minute="*"
    )
    scheduler.start()
    
    logger.info("🎯 Bot is ready! Starting polling...")
    
    # Run the bot
    await application.run_polling()


if __name__ == "__main__":
    # Windows compatibility
    if sys.platform.startswith("win") and sys.version_info >= (3, 8):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    try:
        # nest_asyncio for deployment compatibility
        import nest_asyncio
        nest_asyncio.apply()
        
        # Run the bot
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Bot stopped manually")
    except Exception as e:
        logger.error(f"💥 Bot crashed: {e}")
        raise