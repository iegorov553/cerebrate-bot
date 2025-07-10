"""
Admin conversation handlers using ConversationHandler.

This module contains admin-only conversation flows with states and confirmations.
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application, CallbackQueryHandler, CommandHandler, 
    ConversationHandler, ContextTypes, MessageHandler, filters
)

from bot.admin.admin_operations import AdminOperations
from bot.admin.broadcast_manager import BroadcastManager
from bot.config import Config
from bot.database.client import DatabaseClient
from bot.utils.exceptions import AdminRequired
from bot.utils.rate_limiter import MultiTierRateLimiter, rate_limit
from monitoring import get_logger, set_user_context, track_errors_async

logger = get_logger(__name__)

# Conversation states
WAITING_BROADCAST_TEXT = 1
WAITING_BROADCAST_CONFIRMATION = 2


def require_admin(func):
    """Decorator to require admin privileges."""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if not user:
            return ConversationHandler.END
            
        config: Config = context.bot_data['config']
        admin_ops: AdminOperations = context.bot_data['admin_ops']
        if not admin_ops.is_admin(user.id):
            await update.message.reply_text(
                "🔒 Эта команда доступна только администраторам."
            )
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
        "📢 **Создание рассылки**\n\n"
        "Отправьте текст сообщения для рассылки всем пользователям.\n\n"
        "💡 Поддерживается форматирование Markdown.\n"
        "📝 Для отмены используйте /cancel",
        parse_mode='Markdown'
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
        "📢 **Создание рассылки**\n\n"
        "Отправьте текст сообщения для рассылки всем пользователям.\n\n"
        "💡 Поддерживается форматирование Markdown.\n"
        "📝 Для отмены используйте /cancel",
        parse_mode='Markdown'
    )
    
    return WAITING_BROADCAST_TEXT


@track_errors_async("handle_broadcast_text")
async def handle_broadcast_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle broadcast text input and show confirmation."""
    user = update.effective_user
    message_text = update.message.text
    
    # Store broadcast text in user_data
    context.user_data['broadcast_text'] = message_text
    
    # Create confirmation keyboard
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Да, отправить", callback_data="broadcast_confirm_yes"),
            InlineKeyboardButton("❌ Нет, отменить", callback_data="broadcast_confirm_no")
        ]
    ])
    
    # Show preview with buttons
    preview_text = (
        f"📢 **Предпросмотр рассылки:**\n\n"
        f"{message_text}\n\n"
        f"Отправить это сообщение всем пользователям?"
    )
    
    await update.message.reply_text(
        preview_text,
        reply_markup=keyboard,
        parse_mode='Markdown'
    )
    
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
        broadcast_text = context.user_data.get('broadcast_text')
        if not broadcast_text:
            await query.edit_message_text(
                "❌ Ошибка: текст рассылки не найден. Попробуйте заново с /broadcast"
            )
            return ConversationHandler.END
        
        # Get dependencies
        db_client: DatabaseClient = context.bot_data['db_client']
        config: Config = context.bot_data['config']
        
        # Create broadcast manager and send
        from bot.database.user_operations import UserOperations
        from bot.utils.cache_manager import CacheManager
        
        cache_manager = CacheManager()
        user_ops = UserOperations(db_client, cache_manager)
        broadcast_manager = BroadcastManager(
            bot=context.bot,
            user_operations=user_ops
        )
        
        await query.edit_message_text(
            "📤 **Отправка рассылки...**\n\nПожалуйста, подождите..."
        )
        
        try:
            # Send broadcast
            result = await broadcast_manager.send_broadcast(
                message=broadcast_text
            )
            
            # Show results
            success_text = (
                f"✅ **Рассылка завершена!**\n\n"
                f"📊 **Результаты:**\n"
                f"• Успешно отправлено: {result.sent_count}\n"
                f"• Ошибок: {result.failed_count}\n"
                f"• Всего пользователей: {result.total_users}\n"
                f"• Успешность: {result.success_rate:.1f}%\n\n"
                f"⏱️ Время выполнения: {result.duration_seconds:.1f} сек"
            )
            
            await query.edit_message_text(success_text, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error sending broadcast: {e}")
            await query.edit_message_text(
                f"❌ **Ошибка отправки рассылки:**\n\n{str(e)}\n\nПопробуйте позже."
            )
    
    elif query.data == "broadcast_confirm_no":
        await query.edit_message_text(
            "❌ **Рассылка отменена**\n\nНичего не было отправлено."
        )
    
    # Clear user data and end conversation
    context.user_data.clear()
    return ConversationHandler.END


@track_errors_async("cancel_broadcast")
async def cancel_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel broadcast conversation."""
    context.user_data.clear()
    
    await update.message.reply_text(
        "❌ **Создание рассылки отменено**\n\nВсе данные очищены."
    )
    
    return ConversationHandler.END


@track_errors_async("broadcast_timeout")
async def broadcast_timeout(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle conversation timeout."""
    if update.effective_user:
        await context.bot.send_message(
            chat_id=update.effective_user.id,
            text="⏰ **Время создания рассылки истекло**\n\nСессия завершена. Используйте /broadcast для начала заново."
        )


def create_broadcast_conversation() -> ConversationHandler:
    """Create and configure broadcast conversation handler."""
    
    return ConversationHandler(
        entry_points=[
            CommandHandler("broadcast", start_broadcast),
            CallbackQueryHandler(
                start_broadcast_from_callback,
                pattern="^admin_broadcast$"
            )
        ],
        states={
            WAITING_BROADCAST_TEXT: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, 
                    handle_broadcast_text
                )
            ],
            WAITING_BROADCAST_CONFIRMATION: [
                CallbackQueryHandler(
                    handle_broadcast_confirmation,
                    pattern="^broadcast_confirm_(yes|no)$"
                )
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel_broadcast),
            MessageHandler(filters.COMMAND, cancel_broadcast)  # любая команда отменяет
        ],
        per_user=True,  # отдельный диалог для каждого пользователя
        conversation_timeout=300,  # 5 минут
        name="broadcast_conversation",
        persistent=False  # не сохраняем между перезапусками
    )


def setup_admin_conversations(
    application: Application,
    db_client: DatabaseClient,
    rate_limiter: MultiTierRateLimiter,
    config: Config
) -> None:
    """Setup all admin conversation handlers."""
    
    if not config.is_admin_configured():
        logger.warning("Admin not configured, skipping admin conversations")
        return
    
    # Create admin operations instance
    admin_ops = AdminOperations(db_client, config)
    
    # Store in bot data for handlers
    application.bot_data.update({
        'db_client': db_client,
        'config': config,
        'admin_ops': admin_ops,
        'rate_limiter': rate_limiter
    })
    
    # Add broadcast conversation with HIGH PRIORITY
    broadcast_conv = create_broadcast_conversation()
    application.add_handler(broadcast_conv, group=-1)  # Negative group = high priority
    
    logger.info("Admin conversation handlers registered successfully")