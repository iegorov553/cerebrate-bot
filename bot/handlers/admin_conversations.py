"""
Admin conversation handlers using ConversationHandler.

This module contains admin-only conversation flows with states and confirmations.
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from bot.admin.admin_operations import AdminOperations
from bot.admin.broadcast_manager import BroadcastManager
from bot.config import Config
from bot.database.client import DatabaseClient
from bot.i18n.translator import Translator
from bot.utils.rate_limiter import MultiTierRateLimiter, rate_limit
from monitoring import get_logger, set_user_context, track_errors_async

logger = get_logger(__name__)
translator = Translator()

# Conversation states
WAITING_BROADCAST_TEXT = 1
WAITING_BROADCAST_CONFIRMATION = 2


def require_admin(func):
    """Decorator to require admin privileges."""

    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if not user:
            return ConversationHandler.END

        admin_ops: AdminOperations = context.bot_data["admin_ops"]
        if not admin_ops.is_admin(user.id):
            await update.message.reply_text(translator.translate("admin.access_denied"))
            return ConversationHandler.END

        return await func(update, context)

    return wrapper


@rate_limit("admin")
@track_errors_async("start_broadcast")
@require_admin
async def start_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start broadcast conversation - entry point."""
    user = update.effective_user
    set_user_context(user.id, user.username, user.first_name)

    await update.message.reply_text(
        translator.translate("broadcast.create_title")
        + translator.translate("broadcast.enter_message")
        + translator.translate("broadcast.markdown_support")
        + translator.translate("broadcast.cancel_info"),
        parse_mode="Markdown",
    )

    return WAITING_BROADCAST_TEXT


@track_errors_async("start_broadcast_from_callback")
@require_admin
async def start_broadcast_from_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start broadcast conversation - entry point from callback button."""
    query = update.callback_query
    user = query.from_user

    await query.answer()  # Acknowledge the callback
    set_user_context(user.id, user.username, user.first_name)

    await query.edit_message_text(
        translator.translate("broadcast.create_title")
        + translator.translate("broadcast.enter_message")
        + translator.translate("broadcast.markdown_support")
        + translator.translate("broadcast.cancel_info"),
        parse_mode="Markdown",
    )

    return WAITING_BROADCAST_TEXT


@track_errors_async("handle_broadcast_text")
async def handle_broadcast_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle broadcast text input and show confirmation."""
    message_text = update.message.text

    # Store broadcast text in user_data
    context.user_data["broadcast_text"] = message_text

    # Create confirmation keyboard
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(translator.translate("broadcast.confirm_yes"), callback_data="broadcast_confirm_yes"),
                InlineKeyboardButton(translator.translate("broadcast.confirm_no"), callback_data="broadcast_confirm_no"),
            ]
        ]
    )

    # Show preview with buttons
    preview_text = (
        f"{translator.translate('broadcast.preview_title')}"
        f"{message_text}\n\n"
        f"{translator.translate('broadcast.confirm_question')}"
    )

    await update.message.reply_text(preview_text, reply_markup=keyboard, parse_mode="Markdown")

    return WAITING_BROADCAST_CONFIRMATION


@track_errors_async("handle_broadcast_confirmation")
async def handle_broadcast_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle broadcast confirmation via callback buttons."""
    query = update.callback_query
    await query.answer()

    user = update.effective_user
    set_user_context(user.id, user.username, user.first_name)

    if query.data == "broadcast_confirm_yes":
        # Get broadcast text
        broadcast_text = context.user_data.get("broadcast_text")
        if not broadcast_text:
            await query.edit_message_text(translator.translate("errors.broadcast_not_found"))
            return ConversationHandler.END

        # Get dependencies
        db_client: DatabaseClient = context.bot_data["db_client"]

        # Create broadcast manager and send
        from bot.database.user_operations import UserOperations
        from bot.utils.cache_manager import CacheManager

        cache_manager = CacheManager()
        user_ops = UserOperations(db_client, cache_manager)
        broadcast_manager = BroadcastManager(bot=context.bot, user_operations=user_ops)

        await query.edit_message_text(translator.translate("broadcast.sending_message"))

        try:
            # Send broadcast
            result = await broadcast_manager.send_broadcast(message=broadcast_text)

            # Show results
            success_text = (
                f"{translator.translate('broadcast.completed_title')}"
                f"{translator.translate('broadcast.results_title')}"
                f"• Успешно отправлено: {result.sent_count}\n"
                f"• Ошибок: {result.failed_count}\n"
                f"• Всего пользователей: {result.total_users}\n"
                f"• Успешность: {result.success_rate:.1f}%\n\n"
                f"⏱️ Время выполнения: {result.duration_seconds:.1f} сек"
            )

            await query.edit_message_text(success_text, parse_mode="Markdown")

        except Exception as e:
            logger.error(f"Error sending broadcast: {e}")
            error_message = (
                translator.translate("errors.broadcast_send_error")
                + ":\n\n"
                + str(e)
                + "\n\n"
                + translator.translate("errors.general_error")
            )
            await query.edit_message_text(error_message)

    elif query.data == "broadcast_confirm_no":
        await query.edit_message_text(translator.translate("broadcast.cancelled_message"))

    # Clear user data and end conversation
    context.user_data.clear()
    return ConversationHandler.END


@track_errors_async("cancel_broadcast")
async def cancel_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel broadcast conversation."""
    context.user_data.clear()

    await update.message.reply_text(translator.translate("broadcast.creation_cancelled"))

    return ConversationHandler.END


@track_errors_async("broadcast_timeout")
async def broadcast_timeout(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle conversation timeout."""
    if update.effective_user:
        await context.bot.send_message(
            chat_id=update.effective_user.id, text=translator.translate("broadcast.timeout_message")
        )


def create_broadcast_conversation() -> ConversationHandler:
    """Create and configure broadcast conversation handler."""

    return ConversationHandler(
        entry_points=[
            CommandHandler("broadcast", start_broadcast),
            CallbackQueryHandler(start_broadcast_from_callback, pattern="^admin_broadcast$"),
        ],
        states={
            WAITING_BROADCAST_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_broadcast_text)],
            WAITING_BROADCAST_CONFIRMATION: [
                CallbackQueryHandler(handle_broadcast_confirmation, pattern="^broadcast_confirm_(yes|no)$")
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel_broadcast),
            MessageHandler(filters.COMMAND, cancel_broadcast),  # любая команда отменяет
        ],
        per_user=True,  # отдельный диалог для каждого пользователя
        per_message=True,  # отслеживать для каждого сообщения
        conversation_timeout=300,  # 5 минут
        name="broadcast_conversation",
        persistent=False,  # не сохраняем между перезапусками
    )


def setup_admin_conversations(
    application: Application, db_client: DatabaseClient, rate_limiter: MultiTierRateLimiter, config: Config
) -> None:
    """Setup all admin conversation handlers."""

    if not config.is_admin_configured():
        logger.warning("Admin not configured, skipping admin conversations")
        return

    # Create admin operations instance
    admin_ops = AdminOperations(db_client, config)

    # Store in bot data for handlers
    application.bot_data.update(
        {"db_client": db_client, "config": config, "admin_ops": admin_ops, "rate_limiter": rate_limiter}
    )

    # Add broadcast conversation with HIGH PRIORITY
    broadcast_conv = create_broadcast_conversation()
    application.add_handler(broadcast_conv, group=-1)  # Negative group = high priority

    logger.info("Admin conversation handlers registered successfully")
