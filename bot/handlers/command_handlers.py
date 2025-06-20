"""
Command handlers for the Hour Watcher Bot.

This module contains all user command handlers (non-admin).
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, ContextTypes

from bot.config import Config
from bot.database.client import DatabaseClient
from bot.cache.ttl_cache import TTLCache
from bot.utils.rate_limiter import MultiTierRateLimiter, rate_limit
from bot.database.user_operations import UserOperations
from bot.keyboards.keyboard_generators import create_main_menu, create_settings_menu, create_friends_menu

from monitoring import get_logger, set_user_context, track_errors_async

logger = get_logger(__name__)


@rate_limit("general")
@track_errors_async("start_command")
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command - register user and show main menu."""
    user = update.effective_user
    if user is None:
        return

    set_user_context(user.id, user.username, user.first_name)
    
    # Get dependencies from context
    db_client: DatabaseClient = context.bot_data['db_client']
    config: Config = context.bot_data['config']
    
    # Ensure user exists in database
    user_data = await ensure_user_exists(
        db_client=db_client,
        tg_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name
    )

    if not user_data:
        await update.message.reply_text(
            "❌ Ошибка регистрации. Попробуйте позже."
        )
        return

    # Create main menu
    keyboard = create_main_menu(config.is_admin_configured() and user.id == config.admin_user_id)
    
    welcome_text = f"👋 Привет, {user.first_name}!\n\n" \
                   f"🤖 **Hour Watcher Bot** поможет отслеживать твою активность.\n\n" \
                   f"Выбери действие:"

    await update.message.reply_text(
        welcome_text,
        reply_markup=keyboard,
        parse_mode='Markdown'
    )
    
    logger.info(f"User {user.id} opened main menu")


@rate_limit("settings")
@track_errors_async("settings_command")
async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show user settings from database."""
    user = update.effective_user
    if user is None:
        return

    set_user_context(user.id, user.username, user.first_name)
    
    # Get dependencies
    db_client: DatabaseClient = context.bot_data['db_client']
    user_cache: TTLCache = context.bot_data['user_cache']
    
    # Get user settings (with caching)
    user_data = await get_user_settings(db_client, user_cache, user.id)
    
    if not user_data:
        await update.message.reply_text(
            "❌ Не удалось получить настройки. Попробуйте /start"
        )
        return
    
    # Create settings menu
    keyboard = create_settings_menu()
    
    settings_text = f"⚙️ **Твои настройки:**\n\n" \
                   f"🔔 Уведомления: {'✅ Включены' if user_data['enabled'] else '❌ Отключены'}\n" \
                   f"⏰ Время: {user_data['window_start']} - {user_data['window_end']}\n" \
                   f"📊 Частота: каждые {user_data['interval_min']} минут"

    await update.message.reply_text(
        settings_text,
        reply_markup=keyboard,
        parse_mode='Markdown'
    )


@rate_limit("general")
@track_errors_async("history_command")
async def history_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Open web interface for activity history."""
    user = update.effective_user
    if user is None:
        return

    set_user_context(user.id, user.username, user.first_name)
    
    config: Config = context.bot_data['config']
    
    # Create web app button
    web_app = WebAppInfo(url=f"{config.webapp_url}/history")
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("📊 Открыть историю", web_app=web_app)
    ]])
    
    await update.message.reply_text(
        "📊 **История активности**\n\n"
        "Нажми кнопку ниже, чтобы открыть веб-интерфейс с твоей историей активности:",
        reply_markup=keyboard,
        parse_mode='Markdown'
    )


@rate_limit("friend_request")
@track_errors_async("add_friend_command")
async def add_friend_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /add_friend command."""
    user = update.effective_user
    if user is None:
        return

    set_user_context(user.id, user.username, user.first_name)
    
    if not context.args:
        await update.message.reply_text(
            "👥 **Добавить друга**\n\n"
            "Использование: `/add_friend @username`\n\n"
            "Пример: `/add_friend @john_doe`",
            parse_mode='Markdown'
        )
        return
    
    # Extract username and send friend request
    target_username = context.args[0].lstrip('@')
    
    # Get dependencies
    db_client: DatabaseClient = context.bot_data['db_client']
    
    # TODO: Implement friend request logic
    await update.message.reply_text(
        f"📤 Запрос в друзья отправлен пользователю @{target_username}\n\n"
        "Ожидайте подтверждения!"
    )


@rate_limit("general")
@track_errors_async("friends_command")
async def friends_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show friends menu."""
    user = update.effective_user
    if user is None:
        return

    set_user_context(user.id, user.username, user.first_name)
    
    # Create friends menu
    keyboard = create_friends_menu()
    
    await update.message.reply_text(
        "👥 **Друзья**\n\n"
        "Выбери действие:",
        reply_markup=keyboard,
        parse_mode='Markdown'
    )


def setup_command_handlers(
    application: Application,
    db_client: DatabaseClient,
    user_cache: TTLCache,
    rate_limiter: MultiTierRateLimiter,
    config: Config
) -> None:
    """Setup all command handlers."""
    
    # Store dependencies in bot_data for access in handlers
    application.bot_data.update({
        'db_client': db_client,
        'user_cache': user_cache,
        'rate_limiter': rate_limiter,
        'config': config
    })
    
    # Register command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("settings", settings_command))
    application.add_handler(CommandHandler("history", history_command))
    application.add_handler(CommandHandler("add_friend", add_friend_command))
    application.add_handler(CommandHandler("friends", friends_command))
    
    logger.info("Command handlers registered successfully")