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
    
    # Get user cache
    user_cache: TTLCache = context.bot_data['user_cache']
    
    # Ensure user exists in database
    user_ops = UserOperations(db_client, user_cache)
    try:
        user_data = await user_ops.ensure_user_exists(
            tg_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name
        )
    except Exception as e:
        logger.error(f"Failed to ensure user exists: {e}")
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
    
    logger.info("Command handlers registered successfully")