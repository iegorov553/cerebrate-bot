"""
Command handlers for the Doyobi Diary.

This module contains all user command handlers (non-admin).
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, WebAppInfo
from telegram.ext import Application, CommandHandler, ContextTypes

from bot.cache.ttl_cache import TTLCache
from bot.config import Config
from bot.database.client import DatabaseClient
from bot.database.user_operations import UserOperations
from bot.i18n import detect_user_language, get_translator
from bot.keyboards.keyboard_generators import create_friends_menu, create_main_menu, create_settings_menu
from bot.utils.rate_limiter import MultiTierRateLimiter, rate_limit
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
    
    # Get user cache
    user_cache: TTLCache = context.bot_data['user_cache']
    
    # Detect user language
    user_language = detect_user_language(user)
    translator = get_translator()
    translator.set_language(user_language)
    
    # Ensure user exists in database
    user_ops = UserOperations(db_client, user_cache)
    try:
        await user_ops.ensure_user_exists(
            tg_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            language=user_language
        )
    except Exception as e:
        logger.error(f"Failed to ensure user exists: {e}")
        await update.message.reply_text(
            translator.translate("errors.registration")
        )
        return

    # Create main menu
    keyboard = create_main_menu(config.is_admin_configured() and user.id == config.admin_user_id)
    
    welcome_text = f"{translator.translate('welcome.greeting', name=user.first_name)}\n\n" \
                   f"{translator.translate('welcome.description')}"

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
    
    # Get user settings from database
    user_ops = UserOperations(db_client, user_cache)
    user_data = await user_ops.get_user_settings(user.id)
    
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
    db_client: DatabaseClient = context.bot_data['db_client']
    user_cache: TTLCache = context.bot_data['user_cache']
    
    # Get user translator
    from bot.handlers.callback_handlers import get_user_translator
    translator = await get_user_translator(user.id, db_client, user_cache)
    
    # Create web app button for main webapp page
    web_app = WebAppInfo(url=config.webapp_url)
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("🌐 " + translator.translate('menu.history'), web_app=web_app)
    ]])
    
    await update.message.reply_text(
        f"🌐 **{translator.translate('menu.history')}**\n\n"
        f"{translator.translate('history.webapp_description')}",
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
    
    # Extract and validate username
    target_username_raw = context.args[0]
    
    from bot.utils.datetime_utils import validate_username
    is_valid, error_msg = validate_username(target_username_raw)
    if not is_valid:
        await update.message.reply_text(
            f"❌ {error_msg}\n\n"
            "Пример: `/add_friend @username`",
            parse_mode='Markdown'
        )
        return
    
    target_username = target_username_raw.lstrip('@')
    
    # Get dependencies
    db_client: DatabaseClient = context.bot_data['db_client']
    user_cache: TTLCache = context.bot_data['user_cache']
    
    # Implement friend request logic
    from bot.database.friend_operations import FriendOperations
    friend_ops = FriendOperations(db_client)
    user_ops = UserOperations(db_client, user_cache)
    
    # Find target user by username
    target_user = await user_ops.find_user_by_username(target_username)
    if not target_user:
        await update.message.reply_text(
            f"❌ Пользователь @{target_username} не найден.\n\n"
            "Убедитесь, что пользователь зарегистрирован в боте."
        )
        return
    
    target_id = target_user['tg_id']
    
    # Send friend request (will check for existing friendship internally)
    success = await friend_ops.create_friend_request(user.id, target_id)
    if success:
        await update.message.reply_text(
            f"📤 Запрос в друзья отправлен пользователю @{target_username}!\n\n"
            "Ожидайте подтверждения."
        )
        
        # Notify target user if possible
        try:
            await context.bot.send_message(
                chat_id=target_id,
                text=f"👤 Пользователь @{user.username or user.first_name} хочет добавить вас в друзья!\n\n"
                     f"Используйте /friend_requests для управления запросами."
            )
        except Exception as e:
            logger.warning(f"Could not notify user {target_id}: {e}")
            
    else:
        await update.message.reply_text(
            "❌ Ошибка при отправке запроса в друзья. Попробуйте позже."
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


@rate_limit("general")
@track_errors_async("friend_requests_command")
async def friend_requests_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show friend requests management."""
    user = update.effective_user
    if user is None:
        return

    set_user_context(user.id, user.username, user.first_name)
    
    # Get dependencies
    db_client: DatabaseClient = context.bot_data['db_client']
    
    from bot.database.friend_operations import FriendOperations
    friend_ops = FriendOperations(db_client)
    
    # Get friend requests
    requests_data = await friend_ops.get_friend_requests_optimized(user.id)
    
    incoming = requests_data.get('incoming', [])
    outgoing = requests_data.get('outgoing', [])
    
    text = "📥 **Запросы в друзья**\n\n"
    
    if incoming:
        text += "**Входящие запросы:**\n"
        for req in incoming[:5]:  # Показываем только первые 5
            username = req.get('tg_username', 'Неизвестно')
            name = req.get('tg_first_name', '')
            text += f"• @{username} ({name})\n"
            text += f"  `/accept @{username}` | `/decline @{username}`\n\n"
    else:
        text += "**Входящие запросы:** нет\n\n"
    
    if outgoing:
        text += "**Исходящие запросы:**\n"
        for req in outgoing[:5]:  # Показываем только первые 5
            username = req.get('tg_username', 'Неизвестно')
            name = req.get('tg_first_name', '')
            text += f"• @{username} ({name}) - ожидает ответа\n"
    else:
        text += "**Исходящие запросы:** нет"
    
    await update.message.reply_text(text, parse_mode='Markdown')


@rate_limit("friend_request")
@track_errors_async("accept_friend_command")  
async def accept_friend_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Accept friend request."""
    user = update.effective_user
    if user is None:
        return

    set_user_context(user.id, user.username, user.first_name)
    
    if not context.args:
        await update.message.reply_text(
            "👥 **Принять в друзья**\n\n"
            "Использование: `/accept @username`",
            parse_mode='Markdown'
        )
        return
    
    target_username = context.args[0].lstrip('@')
    
    # Get dependencies
    db_client: DatabaseClient = context.bot_data['db_client']
    user_cache: TTLCache = context.bot_data['user_cache']
    
    from bot.database.friend_operations import FriendOperations
    from bot.database.user_operations import UserOperations
    
    friend_ops = FriendOperations(db_client)
    user_ops = UserOperations(db_client, user_cache)
    
    # Find requester by username
    requester = await user_ops.find_user_by_username(target_username)
    if not requester:
        await update.message.reply_text(
            f"❌ Пользователь @{target_username} не найден."
        )
        return
    
    # Accept friend request
    success = await friend_ops.accept_friend_request(requester['tg_id'], user.id)
    if success:
        await update.message.reply_text(
            f"✅ Заявка в друзья от @{target_username} принята!\n\n"
            "Теперь вы друзья! 🎉"
        )
        
        # Notify requester if possible
        try:
            await context.bot.send_message(
                chat_id=requester['tg_id'],
                text=f"🎉 @{user.username or user.first_name} принял вашу заявку в друзья!"
            )
        except Exception as e:
            logger.warning(f"Could not notify user {requester['tg_id']}: {e}")
    else:
        await update.message.reply_text(
            f"❌ Заявки в друзья от @{target_username} не найдено или она уже обработана."
        )


@rate_limit("friend_request")
@track_errors_async("decline_friend_command")
async def decline_friend_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Decline friend request."""
    user = update.effective_user
    if user is None:
        return

    set_user_context(user.id, user.username, user.first_name)
    
    if not context.args:
        await update.message.reply_text(
            "👥 **Отклонить заявку**\n\n"
            "Использование: `/decline @username`",
            parse_mode='Markdown'
        )
        return
    
    target_username = context.args[0].lstrip('@')
    
    # Get dependencies
    db_client: DatabaseClient = context.bot_data['db_client']
    user_cache: TTLCache = context.bot_data['user_cache']
    
    from bot.database.friend_operations import FriendOperations
    from bot.database.user_operations import UserOperations
    
    friend_ops = FriendOperations(db_client)
    user_ops = UserOperations(db_client, user_cache)
    
    # Find requester by username
    requester = await user_ops.find_user_by_username(target_username)
    if not requester:
        await update.message.reply_text(
            f"❌ Пользователь @{target_username} не найден."
        )
        return
    
    # Decline friend request
    success = await friend_ops.decline_friend_request(requester['tg_id'], user.id)
    if success:
        await update.message.reply_text(
            f"❌ Заявка в друзья от @{target_username} отклонена."
        )
        
        # Notify requester if possible
        try:
            await context.bot.send_message(
                chat_id=requester['tg_id'],
                text=f"❌ @{user.username or user.first_name} отклонил вашу заявку в друзья."
            )
        except Exception as e:
            logger.warning(f"Could not notify user {requester['tg_id']}: {e}")
    else:
        await update.message.reply_text(
            f"❌ Заявки в друзья от @{target_username} не найдено или она уже обработана."
        )


@rate_limit("settings")
@track_errors_async("window_command")
async def window_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Set time window for default question notifications."""
    user = update.effective_user
    if user is None:
        return

    set_user_context(user.id, user.username, user.first_name)
    
    if not context.args:
        await update.message.reply_text(
            "⏰ **Установить временное окно**\n\n"
            "Использование: `/window HH:MM-HH:MM`\n\n"
            "Примеры:\n"
            "• `/window 09:00-18:00` - с 9 утра до 6 вечера\n"
            "• `/window 22:00-06:00` - с 10 вечера до 6 утра",
            parse_mode='Markdown'
        )
        return
    
    time_range = context.args[0]
    
    # Validate time format
    from bot.utils.datetime_utils import validate_time_window
    is_valid, error_msg, start_time, end_time = validate_time_window(time_range)
    if not is_valid:
        await update.message.reply_text(
            f"❌ {error_msg}\n\n"
            "Формат: `HH:MM-HH:MM`\n"
            "Пример: `/window 09:00-22:00`",
            parse_mode='Markdown'
        )
        return
    
    # Get dependencies
    db_client: DatabaseClient = context.bot_data['db_client']
    user_cache: TTLCache = context.bot_data['user_cache']
    
    # Initialize question manager and ensure user has default question
    from bot.questions import QuestionManager
    question_manager = QuestionManager(db_client, user_cache)
    
    try:
        # Ensure user has default question
        await question_manager.ensure_user_has_default_question(user.id)
        
        # Get default question
        default_question = await question_manager.get_user_default_question(user.id)
        if not default_question:
            await update.message.reply_text(
                "❌ Ошибка получения дефолтного вопроса. Попробуйте /start"
            )
            return
        
        # Update time window for default question
        success = await question_manager.question_ops.update_question_schedule(
            default_question['id'], 
            window_start=start_time.strftime('%H:%M:%S'),
            window_end=end_time.strftime('%H:%M:%S')
        )
        
        if success:
            await update.message.reply_text(
                f"✅ **Временное окно обновлено!**\n\n"
                f"⏰ Новое время: {start_time.strftime('%H:%M')} - {end_time.strftime('%H:%M')}\n\n"
                f"Теперь уведомления будут приходить только в это время.",
                parse_mode='Markdown'
            )
            logger.info(f"Time window updated for user {user.id}: {time_range}")
        else:
            await update.message.reply_text(
                "❌ Ошибка при обновлении временного окна. Попробуйте позже."
            )
    except Exception as e:
        logger.error(f"Error updating time window for user {user.id}: {e}")
        await update.message.reply_text(
            "❌ Ошибка при обновлении настроек. Попробуйте позже."
        )


@rate_limit("settings")
@track_errors_async("freq_command")
async def freq_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Set notification frequency for default question."""
    user = update.effective_user
    if user is None:
        return

    set_user_context(user.id, user.username, user.first_name)
    
    if not context.args:
        await update.message.reply_text(
            "📊 **Установить частоту уведомлений**\n\n"
            "Использование: `/freq N`\n\n"
            "Где N - интервал в минутах между уведомлениями.\n\n"
            "Примеры:\n"
            "• `/freq 60` - каждый час\n"
            "• `/freq 120` - каждые 2 часа\n"
            "• `/freq 30` - каждые 30 минут",
            parse_mode='Markdown'
        )
        return
    
    try:
        interval_min = int(context.args[0])
        if interval_min < 5:
            await update.message.reply_text(
                "❌ Минимальный интервал: 5 минут\n\n"
                "Пример: `/freq 30`"
            )
            return
        elif interval_min > 1440:  # 24 hours
            await update.message.reply_text(
                "❌ Максимальный интервал: 1440 минут (24 часа)\n\n"
                "Пример: `/freq 120`"
            )
            return
    except ValueError:
        await update.message.reply_text(
            "❌ Неверный формат числа\n\n"
            "Использование: `/freq N`\n"
            "Пример: `/freq 60`"
        )
        return
    
    # Get dependencies
    db_client: DatabaseClient = context.bot_data['db_client']
    user_cache: TTLCache = context.bot_data['user_cache']
    
    # Initialize question manager and ensure user has default question
    from bot.questions import QuestionManager
    question_manager = QuestionManager(db_client, user_cache)
    
    try:
        # Ensure user has default question
        await question_manager.ensure_user_has_default_question(user.id)
        
        # Get default question
        default_question = await question_manager.get_user_default_question(user.id)
        if not default_question:
            await update.message.reply_text(
                "❌ Ошибка получения дефолтного вопроса. Попробуйте /start"
            )
            return
        
        # Update frequency for default question
        success = await question_manager.question_ops.update_question_schedule(
            default_question['id'], 
            interval_minutes=interval_min
        )
        
        if success:
            # Calculate human-readable frequency
            if interval_min < 60:
                freq_text = f"{interval_min} минут"
            elif interval_min == 60:
                freq_text = "1 час"
            elif interval_min < 1440:
                hours = interval_min // 60
                minutes = interval_min % 60
                if minutes == 0:
                    freq_text = f"{hours} час{'а' if hours < 5 else 'ов'}"
                else:
                    freq_text = f"{hours} час{'а' if hours < 5 else 'ов'} {minutes} минут"
            else:
                freq_text = f"{interval_min // 60} часов"
            
            await update.message.reply_text(
                f"✅ **Частота уведомлений обновлена!**\n\n"
                f"📊 Новая частота: каждые {freq_text}\n\n"
                f"Следующее уведомление придёт через {freq_text}.",
                parse_mode='Markdown'
            )
            logger.info(f"Frequency updated for user {user.id}: {interval_min} minutes")
        else:
            await update.message.reply_text(
                "❌ Ошибка при обновлении частоты. Попробуйте позже."
            )
    except Exception as e:
        logger.error(f"Error updating frequency for user {user.id}: {e}")
        await update.message.reply_text(
            "❌ Ошибка при обновлении настроек. Попробуйте позже."
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
    application.add_handler(CommandHandler("friend_requests", friend_requests_command))
    application.add_handler(CommandHandler("accept", accept_friend_command))
    application.add_handler(CommandHandler("decline", decline_friend_command))
    application.add_handler(CommandHandler("window", window_command))
    application.add_handler(CommandHandler("freq", freq_command))
    
    logger.info("Command handlers registered successfully")