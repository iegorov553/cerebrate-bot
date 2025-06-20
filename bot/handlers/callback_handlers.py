"""
Callback query handlers for inline keyboards.

This module handles all callback queries from inline keyboard buttons.
"""

from telegram import Update
from telegram.ext import Application, CallbackQueryHandler, ContextTypes

from bot.config import Config
from bot.database.client import DatabaseClient
from bot.cache.ttl_cache import TTLCache
from bot.utils.rate_limiter import MultiTierRateLimiter, rate_limit
from bot.keyboards.keyboard_generators import (
    create_main_menu, create_settings_menu, create_friends_menu
)

from monitoring import get_logger, set_user_context, track_errors_async

logger = get_logger(__name__)


@rate_limit("callback")
@track_errors_async("handle_callback_query")
async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle callback queries from inline keyboards."""
    query = update.callback_query
    user = update.effective_user
    
    if not query or not user:
        return
        
    await query.answer()  # Answer the callback query
    set_user_context(user.id, user.username, user.first_name)
    
    # Get dependencies
    config: Config = context.bot_data['config']
    db_client: DatabaseClient = context.bot_data['db_client']
    user_cache: TTLCache = context.bot_data['user_cache']
    
    data = query.data
    
    try:
        if data == "main_menu":
            await handle_main_menu(query, config, user)
        elif data == "settings":
            await handle_settings_menu(query, db_client, user_cache, user)
        elif data == "friends":
            await handle_friends_menu(query)
        elif data == "history":
            await handle_history(query, config)
        elif data == "admin_panel":
            await handle_admin_panel(query, config, user)
        elif data.startswith("settings_"):
            await handle_settings_action(query, data, db_client, user_cache, user)
        elif data.startswith("friends_"):
            await handle_friends_action(query, data, db_client, user)
        else:
            logger.warning(f"Unknown callback data: {data}")
            
    except Exception as e:
        logger.error(f"Error handling callback {data}: {e}")
        await query.edit_message_text(
            "❌ Произошла ошибка. Попробуйте ещё раз.",
            reply_markup=create_main_menu(config.is_admin_configured() and user.id == config.admin_user_id)
        )


async def handle_main_menu(query, config: Config, user):
    """Handle main menu navigation."""
    keyboard = create_main_menu(config.is_admin_configured() and user.id == config.admin_user_id)
    
    await query.edit_message_text(
        f"👋 Главное меню\n\n"
        f"🤖 **Hour Watcher Bot**\n"
        f"Выбери действие:",
        reply_markup=keyboard,
        parse_mode='Markdown'
    )


async def handle_settings_menu(query, db_client: DatabaseClient, user_cache: TTLCache, user):
    """Handle settings menu display."""
    from bot.database.user_operations import get_user_settings
    
    # Get user settings
    user_data = await get_user_settings(db_client, user_cache, user.id)
    
    if not user_data:
        await query.edit_message_text(
            "❌ Не удалось получить настройки.",
            reply_markup=create_main_menu()
        )
        return
    
    keyboard = create_settings_menu()
    
    settings_text = f"⚙️ **Настройки**\n\n" \
                   f"🔔 Уведомления: {'✅ Включены' if user_data['enabled'] else '❌ Отключены'}\n" \
                   f"⏰ Время: {user_data['window_start']} - {user_data['window_end']}\n" \
                   f"📊 Частота: каждые {user_data['interval_min']} минут"

    await query.edit_message_text(
        settings_text,
        reply_markup=keyboard,
        parse_mode='Markdown'
    )


async def handle_friends_menu(query):
    """Handle friends menu display."""
    keyboard = create_friends_menu()
    
    await query.edit_message_text(
        "👥 **Друзья**\n\n"
        "Управление друзьями и социальными связями:",
        reply_markup=keyboard,
        parse_mode='Markdown'
    )


async def handle_history(query, config: Config):
    """Handle history web app opening."""
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
    
    web_app = WebAppInfo(url=f"{config.webapp_url}/history")
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Открыть историю", web_app=web_app)],
        [InlineKeyboardButton("🔙 Назад", callback_data="main_menu")]
    ])
    
    await query.edit_message_text(
        "📊 **История активности**\n\n"
        "Откройте веб-интерфейс для просмотра детальной истории:",
        reply_markup=keyboard,
        parse_mode='Markdown'
    )


async def handle_admin_panel(query, config: Config, user):
    """Handle admin panel access."""
    from bot.admin.admin_operations import is_admin
    
    if not is_admin(user.id, config):
        await query.edit_message_text(
            "🔒 **Доступ запрещён**\n\n"
            "Эта функция доступна только администраторам.",
            reply_markup=create_main_menu()
        )
        return
    
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Рассылка", callback_data="admin_broadcast")],
        [InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton("🔙 Назад", callback_data="main_menu")]
    ])
    
    await query.edit_message_text(
        "👨‍💼 **Админ-панель**\n\n"
        "Выберите действие:",
        reply_markup=keyboard,
        parse_mode='Markdown'
    )


async def handle_settings_action(query, data: str, db_client: DatabaseClient, user_cache: TTLCache, user):
    """Handle settings-related actions."""
    action = data.replace("settings_", "")
    
    if action == "toggle_notifications":
        # TODO: Implement notification toggle
        await query.edit_message_text(
            "🔔 Уведомления переключены!\n\n"
            "Возвращаемся к настройкам...",
            reply_markup=create_settings_menu()
        )
    elif action == "back":
        # Temporarily hardcode - will fix architecture later
        from bot.config import Config
        config = Config.from_env()
        await handle_main_menu(query, config, user)


async def handle_friends_action(query, data: str, db_client: DatabaseClient, user):
    """Handle friends-related actions."""
    action = data.replace("friends_", "")
    
    if action == "add":
        await query.edit_message_text(
            "➕ **Добавить друга**\n\n"
            "Отправьте команду:\n"
            "`/add_friend @username`",
            reply_markup=create_friends_menu(),
            parse_mode='Markdown'
        )
    elif action == "list":
        # TODO: Implement friends list
        await query.edit_message_text(
            "👥 **Список друзей**\n\n"
            "У вас пока нет друзей.",
            reply_markup=create_friends_menu()
        )
    elif action == "back":
        # Temporarily hardcode - will fix architecture later
        from bot.config import Config
        config = Config.from_env()
        await handle_main_menu(query, config, user)


def setup_callback_handlers(
    application: Application,
    db_client: DatabaseClient,
    user_cache: TTLCache,
    rate_limiter: MultiTierRateLimiter,
    config: Config
) -> None:
    """Setup callback query handlers."""
    
    # Register callback query handler
    application.add_handler(CallbackQueryHandler(handle_callback_query))
    
    logger.info("Callback handlers registered successfully")