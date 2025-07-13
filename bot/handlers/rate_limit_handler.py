"""
Rate limiting handler utilities.
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from bot.utils.exceptions import RateLimitExceeded
from bot.utils.rate_limiter import rate_limiter
from monitoring import get_logger

logger = get_logger(__name__)


async def handle_rate_limit_error(update: Update, context: ContextTypes.DEFAULT_TYPE, error: RateLimitExceeded):
    """Handle rate limit exceeded with user-friendly message."""

    if not update.effective_chat:
        return

    try:
        # Get current usage stats
        user_id = update.effective_user.id if update.effective_user else 0
        stats = rate_limiter.get_usage_stats(user_id, error.action)

        # Format time message
        if error.retry_after < 60:
            time_msg = f"{error.retry_after} сек."
        elif error.retry_after < 3600:
            minutes = error.retry_after // 60
            time_msg = f"{minutes} мин."
        else:
            hours = error.retry_after // 3600
            time_msg = f"{hours} ч."

        # Create user-friendly action names
        action_names = {
            "general": "общих команд",
            "friend_request": "запросов в друзья",
            "settings": "изменений настроек", 
            "discovery": "поиска друзей",
            "admin": "админских команд",
            "callback": "нажатий кнопок"
        }

        action_display = action_names.get(error.action, error.action)

        # Create message with emoji and formatting
        message = f"🚫 **Превышен лимит {action_display}**\n\n" \
            f"📊 Использовано: {stats['current_count']}/{stats['max_requests']}\n" \
            f"⏰ Попробуйте через: {time_msg}\n" \
            f"🔄 Окно сброса: {stats['window_seconds']} сек.\n\n" \
            f"_Лимиты защищают бот от перегрузки._"

        # Add helpful keyboard
        keyboard = [
            [InlineKeyboardButton("🏠 Главное меню", callback_data="menu_main")],
            [InlineKeyboardButton("❓ Помощь", callback_data="menu_help")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Send message (try edit first, then send new)
        if update.callback_query:
            try:
                await update.callback_query.edit_message_text(
                    text=message,
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
            except Exception:
                # If edit fails, answer callback and send new message
                await update.callback_query.answer("Превышен лимит запросов!")
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=message,
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
        else:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=message,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )

        logger.info(
            "Rate limit notification sent",
            user_id=user_id,
            action=error.action,
            retry_after=error.retry_after,
            current_usage=stats['current_count'],
            max_requests=stats['max_requests']
        )

    except Exception as exc:
        logger.error("Failed to handle rate limit error", error=str(exc))

        # Fallback simple message
        try:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"🚫 Слишком много запросов. Попробуйте через {error.retry_after} сек."
            )
        except Exception:
            pass  # Give up if even simple message fails