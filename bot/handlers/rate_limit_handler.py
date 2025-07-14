"""
Rate limiting handler utilities.
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from bot.utils.exceptions import RateLimitExceeded
from bot.utils.rate_limiter import rate_limiter
from bot.i18n.translator import get_translator
from monitoring import get_logger

logger = get_logger(__name__)
translator = get_translator()


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
            "general": translator.translate("rate_limit.general_commands"),
            "friend_request": translator.translate("rate_limit.friend_requests"),
            "settings": translator.translate("rate_limit.settings_changes"),
            "discovery": translator.translate("rate_limit.friend_discovery"),
            "admin": translator.translate("rate_limit.admin_commands"),
            "callback": translator.translate("rate_limit.button_clicks")
        }

        action_display = action_names.get(error.action, error.action)

        # Create message with emoji and formatting
        message = f"🚫 **Превышен лимит {action_display}**\n\n" \
            f"{translator.translate('rate_limit.usage_count', current=stats['current_count'], max=stats['max_requests'])}\n" \
            f"⏰ Попробуйте через: {time_msg}\n" \
            f"{translator.translate('rate_limit.reset_window', seconds=stats['window_seconds'])}\n\n" \
            f"{translator.translate('rate_limit.protection_note')}"

        # Add helpful keyboard
        keyboard = [
            [InlineKeyboardButton(translator.translate("menu.back_main"), callback_data="menu_main")],
            [InlineKeyboardButton(translator.translate("menu.help"), callback_data="menu_help")]
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
                await update.callback_query.answer(translator.translate("rate_limit.exceeded_alert"))
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
