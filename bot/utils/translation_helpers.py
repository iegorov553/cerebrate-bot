"""
Translation helper utilities.

Provides utility functions for getting user-specific translators.
These are commonly used across multiple handlers.
"""

from bot.cache.ttl_cache import TTLCache
from bot.database.client import DatabaseClient
from bot.i18n.translator import Translator
from monitoring import get_logger


logger = get_logger(__name__)


async def get_user_language(user_id: int, 
                          db_client: DatabaseClient, 
                          user_cache: TTLCache, 
                          force_refresh: bool = False) -> str:
    """
    Get user language from database with fallback.
    
    Args:
        user_id: Telegram user ID
        db_client: Database client instance
        user_cache: TTL cache instance
        force_refresh: Whether to bypass cache
        
    Returns:
        User's preferred language code (ru/en/es)
    """
    try:
        from bot.database.user_operations import UserOperations
        user_ops = UserOperations(db_client, user_cache)
        user_data = await user_ops.get_user_settings(
            user_id, 
            force_refresh=force_refresh
        )
        
        if user_data and 'language' in user_data:
            language = user_data['language']
            logger.debug("Retrieved user language", 
                        user_id=user_id, 
                        language=language,
                        from_cache=not force_refresh)
            return language
            
    except Exception as e:
        logger.warning("Failed to get user language", 
                      user_id=user_id, 
                      error=str(e))
    
    # Fallback to default
    logger.debug("Using default language fallback", user_id=user_id)
    return 'ru'


async def get_user_translator(user_id: int, 
                            db_client: DatabaseClient, 
                            user_cache: TTLCache, 
                            force_refresh: bool = False) -> Translator:
    """
    Get translator configured for user's language.
    
    Args:
        user_id: Telegram user ID
        db_client: Database client instance
        user_cache: TTL cache instance
        force_refresh: Whether to bypass cache
        
    Returns:
        Configured Translator instance
    """
    user_language = await get_user_language(user_id, db_client, user_cache, force_refresh)
    
    # Create a fresh translator instance to avoid modifying global state
    translator = Translator()
    translator.set_language(user_language)
    
    logger.debug("Created user translator", 
                 user_id=user_id, 
                 language=user_language)
    return translator