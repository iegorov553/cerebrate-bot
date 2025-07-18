#!/usr/bin/env python3
"""
Doyobi Diary - Modern Modular Entry Point

This is the main entry point for the bot using proper modular architecture.
Replaces the old monolithic cerebrate_bot.py file.
"""

import asyncio
import sys

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram.ext import Application, ApplicationBuilder

from bot.cache.ttl_cache import TTLCache
from bot.config import Config
from bot.database.client import DatabaseClient
from bot.handlers.admin_conversations import setup_admin_conversations
from bot.handlers.admin_handlers import setup_admin_handlers
from bot.handlers.callback_handlers import setup_callback_handlers
from bot.handlers.command_handlers import setup_command_handlers
from bot.handlers.error_handler import setup_error_handler
from bot.handlers.message_handlers import setup_message_handlers
from bot.handlers.voice_handlers import setup_voice_handlers
from bot.services.multi_question_scheduler import create_multi_question_scheduler
from bot.utils.rate_limiter import MultiTierRateLimiter

# Monitoring setup
try:
    from monitoring import get_logger, setup_monitoring
    setup_monitoring()
    logger = get_logger(__name__)
except ImportError:
    import logging
    logging.basicConfig(
        format="%(asctime)s | %(levelname)8s | %(name)s: %(message)s",
        level=logging.INFO,
    )
    logger = logging.getLogger(__name__)


async def create_application() -> Application:
    """Create and configure the Telegram application."""
    
    # Load and validate configuration
    config = Config.from_env()
    config.validate()
    logger.info("Configuration loaded and validated successfully")
    
    # Initialize core components
    db_client = DatabaseClient(config)
    
    # Check database connection
    if not db_client.is_connected():
        logger.error("❌ Database connection failed - bot will not function properly")
        logger.error("Check your SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY")
        # Continue anyway for debugging, but warn user
    else:
        logger.info("✅ Database connection established")
    
    rate_limiter = MultiTierRateLimiter()
    user_cache = TTLCache(ttl_seconds=config.cache_ttl_seconds)
    
    logger.info("Core components initialized")
    
    # Create Telegram application
    application = ApplicationBuilder().token(config.bot_token).build()
    
    # Setup error handling first
    setup_error_handler(application)
    logger.info("Error handling configured")
    
    # Setup all handlers
    setup_command_handlers(application, db_client, user_cache, rate_limiter, config)
    setup_admin_handlers(application, db_client, rate_limiter, config)
    setup_admin_conversations(application, db_client, rate_limiter, config)  # NEW: Admin conversations
    setup_callback_handlers(application, db_client, user_cache, rate_limiter, config)
    setup_message_handlers(application, db_client, user_cache, rate_limiter, config)
    setup_voice_handlers(application, db_client, user_cache, rate_limiter, config)
    
    logger.info("All handlers configured")
    
    # Setup multi-question scheduler service
    multi_question_scheduler = create_multi_question_scheduler(application, db_client, config)
    multi_question_scheduler.start()
    
    logger.info("Multi-question scheduler service started")
    
    # Store scheduler in application for proper shutdown
    application.bot_data['multi_question_scheduler'] = multi_question_scheduler
    
    return application


async def main() -> None:
    """Main entry point for the bot."""
    logger.info("Starting Doyobi Diary (Modular Architecture)")
    
    # Create application
    application = await create_application()
    
    try:
        # Run the bot
        logger.info("Bot is ready! Starting polling...")
        await application.run_polling()
    finally:
        # Cleanup scheduler on shutdown
        if 'multi_question_scheduler' in application.bot_data:
            scheduler = application.bot_data['multi_question_scheduler']
            scheduler.stop()
            logger.info("Multi-question scheduler stopped")


if __name__ == "__main__":
    # Handle Windows event loop policy
    if sys.platform.startswith("win") and sys.version_info >= (3, 8):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    try:
        # Setup nest_asyncio for cloud deployment
        import nest_asyncio
        nest_asyncio.apply()
        loop = asyncio.get_event_loop()
        loop.run_until_complete(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped manually")
    except Exception as e:
        logger.error(f"Bot crashed: {e}")
        raise