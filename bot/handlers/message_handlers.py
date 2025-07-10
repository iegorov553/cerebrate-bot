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


async def send_response_by_status(message, status: str, translator):
    """Send response to user based on message processing status."""
    try:
        if status == "reply_success":
            # Successful reply to notification
            await message.reply_text("✅ Записано!")
            
        elif status == "old_notification_active_question":
            # Old notification but question still active
            await message.reply_text(
                "😅 Вот это ты вспомнил! Уведомление старое, но записал как обычную активность."
            )
            
        elif status == "old_notification_inactive_question":
            # Both notification and question are outdated
            await message.reply_text(
                "🕰️ Этот вопрос уже неактуальный! Записал как обычную активность. "
                "Отвечай на что-то посвежее! 😄"
            )
            
        elif status == "default_question":
            # Regular message to default question
            await message.reply_text("✅ Записано!")
            
        else:
            # Error or unknown status
            await message.reply_text("✅ Записано!")
            
    except Exception as e:
        logger.error(f"Error sending status response: {e}")
        # Fallback response
        await message.reply_text("✅ Записано!")


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
        # Check if user has active feedback session first
        config: Config = context.bot_data['config']
        
        if config.is_feedback_enabled():
            from bot.handlers.feedback_handlers import handle_feedback_message
            # Try to handle as feedback message first
            await handle_feedback_message(update, context)
            
            # Check if message was consumed by feedback handler
            from bot.feedback import FeedbackManager
            from bot.utils.rate_limiter import MultiTierRateLimiter
            
            rate_limiter = MultiTierRateLimiter(feedback_rate_limit=config.feedback_rate_limit)
            feedback_manager = FeedbackManager(config, rate_limiter, user_cache)
            session = await feedback_manager.get_feedback_session(user.id)
            
            if session:
                # Message was handled by feedback system
                return
        
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
        
        # Initialize question manager and ensure user has default question
        from bot.questions import QuestionManager
        question_manager = QuestionManager(db_client, user_cache)
        await question_manager.ensure_user_has_default_question(user.id)
        
        # Determine which question this message responds to
        reply_to_message_id = None
        if message.reply_to_message:
            reply_to_message_id = message.reply_to_message.message_id
        
        question_id, status = await question_manager.determine_question_for_message(
            user.id, reply_to_message_id
        )
        
        if question_id:
            # Log the activity with question linkage
            success = await user_ops.log_activity(user.id, message.text, question_id=question_id)
            
            if success:
                logger.info("Activity logged successfully", 
                           user_id=user.id, 
                           question_id=question_id,
                           message_length=len(message.text))
                
                # Get user translator for response
                from bot.handlers.callback_handlers import get_user_translator
                translator = await get_user_translator(user.id, db_client, user_cache)
                
                # Send status-specific response
                await send_response_by_status(message, status, translator)
                
            else:
                logger.warning("Failed to log activity", user_id=user.id)
                await message.reply_text(
                    "❌ Не удалось записать активность. Попробуйте ещё раз."
                )
        else:
            logger.error("No question found for user", user_id=user.id)
            await message.reply_text(
                "❌ Ошибка системы вопросов. Попробуйте команду /start"
            )
            
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
    application.add_handler(text_handler, group=1)  # Lower priority than conversations
    
    logger.info("Message handlers registered successfully")