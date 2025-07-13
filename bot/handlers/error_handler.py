"""
Error handling for Telegram bot operations.
"""
import traceback

from telegram import Update
from telegram.ext import ContextTypes

from bot.utils.exceptions import AdminRequired, RateLimitExceeded, ValidationError
from monitoring import get_logger, set_user_context

logger = get_logger(__name__)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle errors that occur during bot operation."""

    # Set user context if available
    if isinstance(update, Update) and update.effective_user:
        set_user_context(
            update.effective_user.id,
            update.effective_user.username,
            update.effective_user.first_name
        )

    error = context.error

    # Handle specific error types
    if isinstance(error, RateLimitExceeded):
        await handle_rate_limit_error(update, context, error)
        return

    if isinstance(error, AdminRequired):
        await handle_admin_required_error(update, context, error)
        return

    if isinstance(error, ValidationError):
        await handle_validation_error(update, context, error)
        return

    # Log all other errors
    logger.error(
        "Unhandled error occurred",
        error_type=type(error).__name__,
        error_message=str(error),
        traceback=traceback.format_exc()
    )

    # Send generic error message to user
    if isinstance(update, Update) and update.effective_chat:
        try:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="❌ Произошла ошибка. Попробуйте позже или обратитесь к администратору."
            )
        except Exception:
            # If we can't even send an error message, just log it
            logger.error("Failed to send error message to user")


async def handle_rate_limit_error(update: Update, context: ContextTypes.DEFAULT_TYPE, error: RateLimitExceeded):
    """Handle rate limit exceeded errors."""
    if not update.effective_chat:
        return

    try:
        # Format retry time
        if error.retry_after < 60:
            time_msg = f"{error.retry_after} секунд"
        else:
            minutes = error.retry_after // 60
            time_msg = f"{minutes} минут"

        message = f"🚫 **Превышен лимит запросов**\n\n" \
            f"Вы отправляете команды слишком часто.\n" \
            f"Попробуйте снова через {time_msg}.\n\n" \
            f"Действие: {error.action}"

        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=message,
            parse_mode='Markdown'
        )

        logger.warning(
            "Rate limit message sent to user",
            user_id=update.effective_user.id if update.effective_user else None,
            action=error.action,
            retry_after=error.retry_after
        )

    except Exception as exc:
        logger.error("Failed to send rate limit message", error=str(exc))


async def handle_admin_required_error(update: Update, context: ContextTypes.DEFAULT_TYPE, error: AdminRequired):
    """Handle admin required errors."""
    if not update.effective_chat:
        return

    try:
        message = "🔒 **Доступ запрещен**\n\nЭта команда доступна только администраторам."

        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=message,
            parse_mode='Markdown'
        )

        logger.warning(
            "Admin access denied",
            user_id=update.effective_user.id if update.effective_user else None
        )

    except Exception as exc:
        logger.error("Failed to send admin required message", error=str(exc))


async def handle_validation_error(update: Update, context: ContextTypes.DEFAULT_TYPE, error: ValidationError):
    """Handle validation errors."""
    if not update.effective_chat:
        return

    try:
        message = f"❌ **Ошибка валидации**\n\n{str(error)}"

        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=message,
            parse_mode='Markdown'
        )

        logger.warning(
            "Validation error",
            user_id=update.effective_user.id if update.effective_user else None,
            error_message=str(error)
        )

    except Exception as exc:
        logger.error("Failed to send validation error message", error=str(exc))


def setup_error_handler(application):
    """Set up the error handler for the application."""
    application.add_error_handler(error_handler)
    logger.info("Error handler configured")