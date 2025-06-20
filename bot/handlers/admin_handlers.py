"""
Admin command handlers for the Hour Watcher Bot.

This module contains all admin-only command handlers.
"""

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from bot.config import Config
from bot.database.client import DatabaseClient
from bot.utils.rate_limiter import MultiTierRateLimiter, rate_limit
from bot.utils.exceptions import AdminRequired
from bot.admin.admin_operations import is_admin, get_user_stats
from bot.admin.broadcast_manager import BroadcastManager

from monitoring import get_logger, set_user_context, track_errors_async

logger = get_logger(__name__)


def require_admin(func):
    """Decorator to require admin privileges."""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if not user:
            return
            
        config: Config = context.bot_data['config']
        if not is_admin(user.id, config):
            raise AdminRequired("This command requires admin privileges")
            
        return await func(update, context)
    return wrapper


@rate_limit("admin")
@track_errors_async("broadcast_command")
@require_admin
async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /broadcast command - send message to all users."""
    user = update.effective_user
    set_user_context(user.id, user.username, user.first_name)
    
    if not context.args:
        await update.message.reply_text(
            "📢 **Рассылка сообщений**\n\n"
            "Использование: `/broadcast <сообщение>`\n\n"
            "Пример:\n"
            "`/broadcast Обновление бота! Новые функции доступны.`\n\n"
            "Поддерживается форматирование Markdown.",
            parse_mode='Markdown'
        )
        return
    
    # Get message text
    message_text = ' '.join(context.args)
    
    # Get dependencies
    db_client: DatabaseClient = context.bot_data['db_client']
    config: Config = context.bot_data['config']
    
    # Create broadcast manager
    broadcast_manager = BroadcastManager(db_client, config)
    
    # Show preview and ask for confirmation
    preview_text = f"📢 **Предпросмотр рассылки:**\n\n{message_text}\n\n" \
                   "Отправить всем пользователям? Ответьте 'да' для подтверждения."
    
    await update.message.reply_text(preview_text, parse_mode='Markdown')
    
    # Store broadcast data for confirmation
    context.user_data['pending_broadcast'] = {
        'message': message_text,
        'broadcast_manager': broadcast_manager
    }


@rate_limit("admin")
@track_errors_async("broadcast_info_command")
@require_admin
async def broadcast_info_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show user statistics for admin."""
    user = update.effective_user
    set_user_context(user.id, user.username, user.first_name)
    
    # Get dependencies
    db_client: DatabaseClient = context.bot_data['db_client']
    
    # Get user statistics
    stats = await get_user_stats(db_client)
    
    if not stats:
        await update.message.reply_text(
            "❌ Не удалось получить статистику пользователей."
        )
        return
    
    # Calculate percentages
    active_percentage = (stats['active_users'] / stats['total_users'] * 100) if stats['total_users'] > 0 else 0
    
    stats_text = f"📊 **Статистика пользователей**\n\n" \
                f"👥 Всего пользователей: {stats['total_users']}\n" \
                f"✅ Активных: {stats['active_users']} ({active_percentage:.1f}%)\n" \
                f"🆕 Новых за неделю: {stats['new_users_week']}\n\n" \
                f"📈 Активность: {'Высокая' if active_percentage > 50 else 'Средняя' if active_percentage > 25 else 'Низкая'}"

    await update.message.reply_text(stats_text, parse_mode='Markdown')


def setup_admin_handlers(
    application: Application,
    db_client: DatabaseClient,
    rate_limiter: MultiTierRateLimiter,
    config: Config
) -> None:
    """Setup all admin command handlers."""
    
    if not config.is_admin_configured():
        logger.warning("Admin not configured, skipping admin handlers")
        return
    
    # Register admin command handlers
    application.add_handler(CommandHandler("broadcast", broadcast_command))
    application.add_handler(CommandHandler("broadcast_info", broadcast_info_command))
    
    logger.info("Admin handlers registered successfully")