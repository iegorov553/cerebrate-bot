"""
Hour Watcher Bot - Modern Modular Entry Point

This is the new main entry point for the bot using proper modular architecture.
Replaces the old monolithic cerebrate_bot.py file.
"""

import asyncio
import sys

from telegram.ext import Application, ApplicationBuilder
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from bot.config import Config
from bot.database.client import DatabaseClient
from bot.handlers.error_handler import setup_error_handler
from bot.handlers.command_handlers import setup_command_handlers
from bot.handlers.admin_handlers import setup_admin_handlers
from bot.handlers.callback_handlers import setup_callback_handlers
from bot.utils.rate_limiter import MultiTierRateLimiter
from bot.cache.ttl_cache import TTLCache
from bot.services.scheduler_service import SchedulerService

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
    setup_callback_handlers(application, db_client, user_cache, rate_limiter, config)
    
    logger.info("All handlers configured")
    
    # Setup scheduler service
    scheduler_service = SchedulerService(application, db_client, config)
    scheduler_service.start()
    
    logger.info("Scheduler service started")
    
    return application


async def main() -> None:
    """Main entry point for the bot."""
    logger.info("Starting Hour Watcher Bot (Modular Architecture)")
    
    # Create application
    application = await create_application()
    
    # Run the bot
    logger.info("Bot is ready! Starting polling...")
    await application.run_polling()


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