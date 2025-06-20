"""
Message handlers for activity logging.

This module handles all text messages from users and logs them as activities.
"""

from telegram import Update
from telegram.ext import Application, ContextTypes, MessageHandler, filters

from bot.cache.ttl_cache import TTLCache
from bot.config import Config
from bot.database.client import DatabaseClient
from bot.utils.rate_limiter import MultiTierRateLimiter, rate_limit
from monitoring import get_logger, set_user_context, track_errors_async

logger = get_logger(__name__)


@rate_limit("general")
@track_errors_async("handle_text_message")
async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle text messages and log them as user activities."""
    user = update.effective_user
    message = update.message
    
    if not user or not message or not message.text:
        return
    
    # Skip if message is a command (starts with /)
    if message.text.startswith('/'):
        return
        
    set_user_context(user.id, user.username, user.first_name)
    
    # Get dependencies
    db_client: DatabaseClient = context.bot_data['db_client']
    user_cache: TTLCache = context.bot_data['user_cache']
    
    try:
        # Ensure user exists in database first
        from bot.database.user_operations import UserOperations
        user_ops = UserOperations(db_client, user_cache)
        
        # Register/update user
        await user_ops.ensure_user_exists(
            tg_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name
        )
        
        # Log the activity
        success = await user_ops.log_activity(user.id, message.text)
        
        if success:
            logger.info("Activity logged successfully", 
                       user_id=user.id, 
                       message_length=len(message.text))
        else:
            logger.warning("Failed to log activity", user_id=user.id)
            
    except Exception as e:
        logger.error(f"Error handling text message: {e}", user_id=user.id)


def setup_message_handlers(
    application: Application,
    db_client: DatabaseClient,
    user_cache: TTLCache,
    rate_limiter: MultiTierRateLimiter,
    config: Config
) -> None:
    """Setup message handlers."""
    
    # Ensure bot_data is populated (may be redundant but safe)
    application.bot_data.update({
        'db_client': db_client,
        'user_cache': user_cache,
        'rate_limiter': rate_limiter,
        'config': config
    })
    
    # Register text message handler (excluding commands)
    text_handler = MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle_text_message
    )
    application.add_handler(text_handler)
    
    logger.info("Message handlers registered successfully")