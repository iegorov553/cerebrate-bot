"""
Callback query handlers for inline keyboards.

This module handles all callback queries from inline keyboard buttons.
"""

from telegram import Update
from telegram.ext import Application, CallbackQueryHandler, ContextTypes

from bot.cache.ttl_cache import TTLCache
from bot.config import Config
from bot.database.client import DatabaseClient
from bot.i18n import get_translator
from bot.keyboards.keyboard_generators import KeyboardGenerator, create_friends_menu, create_language_menu, create_main_menu, create_settings_menu
from bot.utils.rate_limiter import MultiTierRateLimiter, rate_limit
from monitoring import get_logger, set_user_context, track_errors_async

logger = get_logger(__name__)


async def get_user_language(user_id: int, db_client: DatabaseClient, user_cache: TTLCache) -> str:
    """Get user language from database with fallback."""
    try:
        from bot.database.user_operations import UserOperations
        user_ops = UserOperations(db_client, user_cache)
        user_data = await user_ops.get_user_settings(user_id)
        
        if user_data and 'language' in user_data:
            return user_data['language']
    except Exception as e:
        logger.warning(f"Failed to get user language: {e}")
    
    return 'ru'  # Default fallback


async def get_user_translator(user_id: int, db_client: DatabaseClient, user_cache: TTLCache):
    """Get translator configured for user's language."""
    user_language = await get_user_language(user_id, db_client, user_cache)
    translator = get_translator()
    # Create a copy to avoid modifying global translator
    from bot.i18n.translator import Translator
    user_translator = Translator()
    user_translator.set_language(user_language)
    return user_translator


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
    
    # Setup translator with user's language
    user_language = await get_user_language(user.id, db_client, user_cache)
    translator = get_translator()
    translator.set_language(user_language)
    
    data = query.data
    
    try:
        if data == "main_menu":
            await handle_main_menu(query, config, user, None, db_client, user_cache)
        elif data == "menu_settings" or data == "settings":
            await handle_settings_menu(query, db_client, user_cache, user)
        elif data == "menu_friends" or data == "friends":
            await handle_friends_menu(query, db_client, user_cache, user)
        elif data == "menu_history" or data == "history":
            await handle_history(query, config, db_client, user_cache, user)
        elif data == "menu_admin" or data == "admin_panel":
            await handle_admin_panel(query, config, user, db_client, user_cache)
        elif data == "menu_language":
            await handle_language_menu(query, user_language, translator)
        elif data.startswith("language_"):
            await handle_language_change(query, data, db_client, user_cache, user, config)
        elif data == "menu_help":
            await handle_help(query, db_client, user_cache, user)
        elif data.startswith("settings_"):
            await handle_settings_action(query, data, db_client, user_cache, user, config, translator)
        elif data.startswith("friends_"):
            await handle_friends_action(query, data, db_client, user, config, translator)
        elif data.startswith("admin_"):
            await handle_admin_action(query, data, db_client, user, config, translator, user_cache)
        elif data == "back_main":
            await handle_main_menu(query, config, user, None, db_client, user_cache)
        else:
            logger.warning(f"Unknown callback data: {data}")
            
    except Exception as e:
        logger.error(f"Error handling callback {data}: {e}")
        await query.edit_message_text(
            "❌ Произошла ошибка. Попробуйте ещё раз.",
            reply_markup=create_main_menu(config.is_admin_configured() and user.id == config.admin_user_id)
        )


async def handle_main_menu(query, config: Config, user, translator=None, db_client=None, user_cache=None):
    """Handle main menu navigation."""
    if translator is None and db_client and user_cache:
        translator = await get_user_translator(user.id, db_client, user_cache)
    elif translator is None:
        from bot.i18n import get_translator
        translator = get_translator()
    
    keyboard = KeyboardGenerator.main_menu(config.is_admin_configured() and user.id == config.admin_user_id, translator)
    
    welcome_text = f"👋 {translator.translate('welcome.greeting', name=user.first_name)}\n\n"
    welcome_text += f"🤖 **Hour Watcher Bot**\n"
    welcome_text += translator.translate('welcome.choose_action')
    
    await query.edit_message_text(
        welcome_text,
        reply_markup=keyboard,
        parse_mode='Markdown'
    )


async def handle_settings_menu(query, db_client: DatabaseClient, user_cache: TTLCache, user):
    """Handle settings menu display."""
    from bot.database.user_operations import UserOperations

    # Get user translator
    translator = await get_user_translator(user.id, db_client, user_cache)
    
    # Get user settings
    user_ops = UserOperations(db_client, user_cache)
    user_data = await user_ops.get_user_settings(user.id)
    
    if not user_data:
        await query.edit_message_text(
            translator.translate('errors.database'),
            reply_markup=KeyboardGenerator.main_menu(False, translator)
        )
        return
    
    keyboard = create_settings_menu()
    
    # Localized settings display
    enabled_status = translator.translate('settings.notifications_enabled') if user_data['enabled'] else translator.translate('settings.notifications_disabled')
    
    settings_text = f"{translator.translate('settings.current_title')}\n\n"
    settings_text += f"{translator.translate('settings.notifications', status=enabled_status)}\n"
    settings_text += f"⏰ {translator.translate('settings.time_window')}: {user_data['window_start']} - {user_data['window_end']}\n"
    settings_text += f"📊 {translator.translate('settings.frequency')}: {translator.translate('settings.every_minutes', minutes=user_data['interval_min'])}"

    await query.edit_message_text(
        settings_text,
        reply_markup=keyboard,
        parse_mode='Markdown'
    )


async def handle_friends_menu(query, db_client: DatabaseClient, user_cache: TTLCache, user):
    """Handle friends menu display."""
    # Get user translator
    translator = await get_user_translator(user.id, db_client, user_cache)
    
    keyboard = create_friends_menu()
    
    await query.edit_message_text(
        f"👥 **{translator.translate('menu.friends')}**\n\n"
        f"{translator.translate('friends.description', default='Управление друзьями и социальными связями:')}",
        reply_markup=keyboard,
        parse_mode='Markdown'
    )


async def handle_history(query, config: Config, db_client: DatabaseClient, user_cache: TTLCache, user):
    """Handle history web app opening."""
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
    
    # Get user translator
    translator = await get_user_translator(user.id, db_client, user_cache)
    
    web_app = WebAppInfo(url=f"{config.webapp_url}/history")
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"📊 {translator.translate('history.open_button', default='Открыть историю')}", web_app=web_app)],
        [InlineKeyboardButton(translator.translate('menu.back'), callback_data="main_menu")]
    ])
    
    await query.edit_message_text(
        f"📊 **{translator.translate('menu.history')}**\n\n"
        f"{translator.translate('history.description', default='Откройте веб-интерфейс для просмотра детальной истории:')}",
        reply_markup=keyboard,
        parse_mode='Markdown'
    )


async def handle_admin_panel(query, config: Config, user, db_client: DatabaseClient, user_cache: TTLCache):
    """Handle admin panel access."""
    from bot.admin.admin_operations import AdminOperations

    # Get user translator
    translator = await get_user_translator(user.id, db_client, user_cache)
    
    # Create a temporary admin_ops instance for this check
    admin_ops = AdminOperations(None, config)  # db_client not needed for is_admin check
    
    if not admin_ops.is_admin(user.id):
        await query.edit_message_text(
            f"🔒 **{translator.translate('admin.access_denied', default='Доступ запрещён')}**\n\n"
            f"{translator.translate('admin.admin_only', default='Эта функция доступна только администраторам.')}",
            reply_markup=KeyboardGenerator.main_menu(False, translator)
        )
        return
    
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"📢 {translator.translate('admin.broadcast', default='Рассылка')}", callback_data="admin_broadcast")],
        [InlineKeyboardButton(f"📊 {translator.translate('admin.stats', default='Статистика')}", callback_data="admin_stats")],
        [InlineKeyboardButton(translator.translate('menu.back'), callback_data="main_menu")]
    ])
    
    await query.edit_message_text(
        f"👨‍💼 **{translator.translate('admin.panel', default='Админ-панель')}**\n\n"
        f"{translator.translate('admin.choose_action', default='Выберите действие:')}",
        reply_markup=keyboard,
        parse_mode='Markdown'
    )


async def handle_language_menu(query, current_language: str, translator):
    """Handle language menu display."""
    keyboard = KeyboardGenerator.language_menu(current_language, translator)
    
    help_text = f"{translator.translate('language.title')}\n\n{translator.translate('language.subtitle')}"
    
    await query.edit_message_text(
        help_text,
        reply_markup=keyboard,
        parse_mode='Markdown'
    )


async def handle_language_change(query, data: str, db_client: DatabaseClient, user_cache: TTLCache, user, config: Config):
    """Handle language change."""
    new_language = data.replace("language_", "")
    
    if new_language not in ['ru', 'en', 'es']:
        return
    
    # Update user language in database
    try:
        from bot.database.user_operations import UserOperations
        user_ops = UserOperations(db_client, user_cache)
        success = await user_ops.update_user_settings(user.id, {'language': new_language})
        
        if success:
            # Create new translator with new language (don't modify global one)
            from bot.i18n.translator import Translator
            new_translator = Translator()
            new_translator.set_language(new_language)
            
            # Get language info
            lang_info = new_translator.get_language_info(new_language)
            
            await query.edit_message_text(
                new_translator.translate('language.changed', 
                                       language_name=lang_info['native'], 
                                       flag=lang_info['flag']),
                reply_markup=KeyboardGenerator.main_menu(config.is_admin_configured() and user.id == config.admin_user_id, new_translator),
                parse_mode='Markdown'
            )
        else:
            # If language column doesn't exist, just show success message anyway
            from bot.i18n.translator import Translator
            fallback_translator = Translator()
            fallback_translator.set_language(new_language)  # Set temporarily for this response
            
            # Get language info
            lang_info = fallback_translator.get_language_info(new_language)
            
            await query.edit_message_text(
                fallback_translator.translate('language.changed', 
                                           language_name=lang_info['native'], 
                                           flag=lang_info['flag']) + "\n\n"
                "📝 *Примечание: изменения будут применены после добавления поддержки в базу данных*",
                reply_markup=KeyboardGenerator.main_menu(config.is_admin_configured() and user.id == config.admin_user_id, fallback_translator),
                parse_mode='Markdown'
            )
    except Exception as e:
        logger.error(f"Error changing language: {e}")
        from bot.i18n.translator import Translator
        translator = Translator()
        await query.edit_message_text(
            translator.translate('errors.general'),
            reply_markup=create_main_menu(config.is_admin_configured() and user.id == config.admin_user_id, translator),
            parse_mode='Markdown'
        )


async def handle_help(query, db_client: DatabaseClient, user_cache: TTLCache, user):
    """Handle help menu display."""
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    
    # Get user translator
    translator = await get_user_translator(user.id, db_client, user_cache)
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(translator.translate("menu.back"), callback_data="main_menu")]
    ])
    
    # Build help text from translations
    commands = "\n".join(translator.translate(f"help.commands.{i}") for i in range(5))
    how_it_works = "\n".join(translator.translate(f"help.how_it_works.{i}") for i in range(4))
    friends_info = "\n".join(translator.translate(f"help.friends_info.{i}") for i in range(3))
    
    help_text = (
        f"{translator.translate('help.title')}\n\n"
        f"{translator.translate('help.description')}\n\n"
        f"{translator.translate('help.commands_title')}\n"
        f"{commands}\n\n"
        f"{translator.translate('help.how_it_works_title')}\n"
        f"{how_it_works}\n\n"
        f"{translator.translate('help.friends_title')}\n"
        f"{friends_info}"
    )
    
    await query.edit_message_text(
        help_text,
        reply_markup=keyboard,
        parse_mode='Markdown'
    )


async def handle_settings_action(query, data: str, db_client: DatabaseClient, user_cache: TTLCache, user, config: Config, translator=None):
    """Handle settings-related actions."""
    if translator is None:
        from bot.i18n import get_translator
        translator = get_translator()
    
    action = data.replace("settings_", "")
    
    if action == "toggle_notifications":
        # Toggle user notifications
        from bot.database.user_operations import UserOperations
        user_ops = UserOperations(db_client, user_cache)
        
        # Get current settings
        user_settings = await user_ops.get_user_settings(user.id)
        if not user_settings:
            await query.edit_message_text(
                "❌ Не удалось получить настройки.",
                reply_markup=KeyboardGenerator.main_menu(config.is_admin_configured() and user.id == config.admin_user_id, translator)
            )
            return
            
        # Toggle enabled status
        new_enabled = not user_settings.get('enabled', True)
        success = await user_ops.update_user_settings(user.id, {'enabled': new_enabled})
        
        if success:
            status_text = "включены" if new_enabled else "отключены"
            emoji = "✅" if new_enabled else "❌"
            await query.edit_message_text(
                f"🔔 Уведомления {emoji} {status_text}!\n\n"
                "Возвращаемся к настройкам...",
                reply_markup=create_settings_menu()
            )
        else:
            await query.edit_message_text(
                "❌ Ошибка при изменении настроек.",
                reply_markup=create_settings_menu()
            )
    elif action == "back":
        # Use config passed as parameter
        await handle_main_menu(query, config, user, translator, db_client, user_cache)
    elif action == "time_window":
        await query.edit_message_text(
            "⏰ **Настройка времени уведомлений**\n\n"
            "Отправьте команду:\n"
            "`/window HH:MM-HH:MM`\n\n"
            "Например: `/window 09:00-22:00`",
            reply_markup=create_settings_menu(),
            parse_mode='Markdown'
        )
    elif action == "frequency":
        await query.edit_message_text(
            "📊 **Настройка частоты уведомлений**\n\n"
            "Отправьте команду:\n"
            "`/freq N`\n\n"
            "Где N - количество минут между уведомлениями\n"
            "Например: `/freq 120` (каждые 2 часа)",
            reply_markup=create_settings_menu(),
            parse_mode='Markdown'
        )
    elif action == "view":
        await handle_settings_menu(query, db_client, user_cache, user)


async def handle_friends_action(query, data: str, db_client: DatabaseClient, user, config: Config, translator=None):
    """Handle friends-related actions."""
    if translator is None:
        from bot.i18n import get_translator
        translator = get_translator()
    
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
        # Get friends list from database
        from bot.database.friend_operations import FriendOperations
        friend_ops = FriendOperations(db_client)
        
        friends = await friend_ops.get_friends_list_optimized(user.id)
        
        if not friends:
            await query.edit_message_text(
                "👥 **Список друзей**\n\n"
                "У вас пока нет друзей.\n"
                "Добавьте друзей через команду `/add_friend @username`",
                reply_markup=create_friends_menu(),
                parse_mode='Markdown'
            )
        else:
            friends_text = "👥 **Ваши друзья:**\n\n"
            for friend in friends[:10]:  # Показываем максимум 10 друзей
                username = friend.get('tg_username', '')
                name = friend.get('tg_first_name', 'Без имени')
                friends_text += f"• @{username} - {name}\n" if username else f"• {name}\n"
            
            if len(friends) > 10:
                friends_text += f"\n... и ещё {len(friends) - 10} друзей"
                
            await query.edit_message_text(
                friends_text,
                reply_markup=create_friends_menu(),
                parse_mode='Markdown'
            )
    elif action == "back":
        # Use config passed as parameter
        await handle_main_menu(query, config, user, translator, db_client, user_cache)
    elif action == "requests":
        await query.edit_message_text(
            "📥 **Запросы в друзья**\n\n"
            "Используйте команды:\n"
            "• `/friend_requests` - посмотреть запросы\n"
            "• `/accept @username` - принять запрос\n"
            "• `/decline @username` - отклонить запрос",
            reply_markup=create_friends_menu(),
            parse_mode='Markdown'
        )
    elif action == "discover":
        await query.edit_message_text(
            "🔍 **Поиск друзей**\n\n"
            "Эта функция находится в разработке.\n"
            "Пока используйте команду `/add_friend @username`",
            reply_markup=create_friends_menu(),
            parse_mode='Markdown'
        )
    elif action == "activities":
        await query.edit_message_text(
            "📊 **Активности друзей**\n\n"
            "Используйте команду:\n"
            "`/activities [@username]`\n\n"
            "Или откройте веб-интерфейс для детального просмотра",
            reply_markup=create_friends_menu(),
            parse_mode='Markdown'
        )


async def handle_admin_action(query, data: str, db_client: DatabaseClient, user, config: Config, translator=None, user_cache=None):
    """Handle admin-related actions."""
    if translator is None:
        if user_cache:
            translator = await get_user_translator(user.id, db_client, user_cache)
        else:
            from bot.i18n import get_translator
            translator = get_translator()
    
    from bot.admin.admin_operations import AdminOperations
    admin_ops = AdminOperations(db_client, config)
    
    if not admin_ops.is_admin(user.id):
        await query.edit_message_text(
            "🔒 **Доступ запрещён**\n\nЭта функция доступна только администраторам.",
            reply_markup=KeyboardGenerator.main_menu(False, translator),
            parse_mode='Markdown'
        )
        return
    
    action = data.replace("admin_", "")
    
    if action == "broadcast":
        await query.edit_message_text(
            "📢 **Массовая рассылка**\n\n"
            "Отправьте команду:\n"
            "`/broadcast <сообщение>`\n\n"
            "Например: `/broadcast Привет всем!`",
            reply_markup=KeyboardGenerator.main_menu(True, translator),
            parse_mode='Markdown'
        )
    elif action == "stats":
        await query.edit_message_text(
            "📊 **Статистика пользователей**\n\n"
            "Используйте команду:\n"
            "`/broadcast_info`",
            reply_markup=KeyboardGenerator.main_menu(True, translator),
            parse_mode='Markdown'
        )
    else:
        await handle_main_menu(query, config, user, translator)


def setup_callback_handlers(
    application: Application,
    db_client: DatabaseClient,
    user_cache: TTLCache,
    rate_limiter: MultiTierRateLimiter,
    config: Config
) -> None:
    """Setup callback query handlers."""
    
    # Store dependencies in bot_data for access in handlers
    application.bot_data['db_client'] = db_client
    application.bot_data['user_cache'] = user_cache
    application.bot_data['rate_limiter'] = rate_limiter
    application.bot_data['config'] = config
    
    # Register callback query handler
    application.add_handler(CallbackQueryHandler(handle_callback_query))
    
    logger.info("Callback handlers registered successfully")