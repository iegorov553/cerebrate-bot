"""
New modular callback handlers entry point.

This replaces the old monolithic callback_handlers.py with a clean router-based architecture.
All callback handling is now delegated to specialized handlers through the CallbackRouter.
"""

from telegram import Update
from telegram.ext import ContextTypes

from bot.cache.ttl_cache import TTLCache
from bot.config import Config
from bot.database.client import DatabaseClient
from bot.handlers.base.callback_router import CallbackRouter
from bot.handlers.callbacks import (
    NavigationCallbackHandler,
    SettingsCallbackHandler,
    FeedbackCallbackHandler,
    FriendsCallbackHandler,
    AdminCallbackHandler,
    QuestionsCallbackHandler,
)
from bot.utils.rate_limiter import rate_limit
from monitoring import get_logger, track_errors_async


logger = get_logger(__name__)


# Global router instance will be initialized in setup
_callback_router: CallbackRouter = None


def setup_callback_handlers(db_client: DatabaseClient, 
                           config: Config, 
                           user_cache: TTLCache) -> CallbackRouter:
    """
    Set up the callback router with all specialized handlers.
    
    Args:
        db_client: Database client instance
        config: Bot configuration
        user_cache: TTL cache instance
        
    Returns:
        Configured CallbackRouter instance
    """
    global _callback_router
    
    # Create router
    router = CallbackRouter(db_client, config, user_cache)
    
    # Register all specialized handlers
    router.register_handler(NavigationCallbackHandler(db_client, config, user_cache))
    router.register_handler(SettingsCallbackHandler(db_client, config, user_cache))
    router.register_handler(FeedbackCallbackHandler(db_client, config, user_cache))
    router.register_handler(FriendsCallbackHandler(db_client, config, user_cache))
    router.register_handler(AdminCallbackHandler(db_client, config, user_cache))
    router.register_handler(QuestionsCallbackHandler(db_client, config, user_cache))
    
    _callback_router = router
    
    logger.info("Callback handlers set up", 
               total_handlers=len(router.handlers),
               handler_classes=[h.__class__.__name__ for h in router.handlers])
    
    return router


@rate_limit("callback")
@track_errors_async("handle_callback_query")
async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Main callback query handler that routes to specialized handlers.
    
    This is the entry point for all callback queries. It uses the CallbackRouter
    to delegate handling to the appropriate specialized handler.
    
    Args:
        update: Telegram update containing callback query
        context: Bot context
    """
    if _callback_router is None:
        logger.error("Callback router not initialized")
        return
    
    # Route the callback to appropriate handler
    await _callback_router.route_callback(update, context)


# Legacy compatibility functions - these maintain the old interface
# for any code that might still import them directly

async def get_user_language(user_id: int, db_client: DatabaseClient, user_cache: TTLCache, force_refresh: bool = False) -> str:
    """Legacy compatibility function."""
    from bot.handlers.base.base_handler import BaseCallbackHandler
    
    # Create temporary handler instance
    temp_handler = type('TempHandler', (BaseCallbackHandler,), {
        'handle_callback': lambda *args: None,
        'can_handle': lambda *args: False
    })(db_client, None, user_cache)
    
    return await temp_handler.get_user_language(user_id, force_refresh)


async def get_user_translator(user_id: int, db_client: DatabaseClient, user_cache: TTLCache, force_refresh: bool = False):
    """Legacy compatibility function."""
    from bot.handlers.base.base_handler import BaseCallbackHandler
    
    # Create temporary handler instance  
    temp_handler = type('TempHandler', (BaseCallbackHandler,), {
        'handle_callback': lambda *args: None,
        'can_handle': lambda *args: False
    })(db_client, None, user_cache)
    
    return await temp_handler.get_user_translator(user_id, force_refresh)