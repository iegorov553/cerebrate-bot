"""User management commands: start, settings."""

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from bot.cache.ttl_cache import TTLCache
from bot.config import Config
from bot.database.client import DatabaseClient
from bot.database.user_operations import UserOperations
from bot.i18n import detect_user_language, get_translator
from bot.keyboards.keyboard_generators import create_main_menu, create_settings_menu
from bot.utils.rate_limiter import rate_limit
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

    welcome_text = (f"{translator.translate('welcome.greeting', name=user.first_name)}\n\n"
                   f"{translator.translate('welcome.description')}")

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
        # Get user language and translator
        user_language = detect_user_language(user)
        translator = get_translator()
        translator.set_language(user_language)
        
        await update.message.reply_text(
            translator.translate('settings.error_missing')
        )
        return

    # Get user language and translator
    user_language = user_data.get('language', 'ru')
    translator = get_translator()
    translator.set_language(user_language)

    # Create settings keyboard
    keyboard = create_settings_menu()

    # Format settings message
    enabled_status = translator.translate("common.enabled") if user_data['enabled'] else translator.translate("common.disabled")
    
    settings_text = (
        f"{translator.translate('settings.title')}\n\n"
        f"{translator.translate('settings.notifications')}: {enabled_status}\n"
        f"{translator.translate('settings.time_window')}: {user_data['window_start']} - {user_data['window_end']}\n"
        f"{translator.translate('settings.frequency')}: {translator.translate('settings.every_n_minutes', minutes=user_data['interval_min'])}\n"
        f"{translator.translate('settings.language')}: {translator.translate(f'languages.{user_language}')}"
    )

    await update.message.reply_text(
        settings_text,
        reply_markup=keyboard,
        parse_mode='Markdown'
    )

    logger.info(f"User {user.id} viewed settings")


def setup_user_commands(application: Application) -> None:
    """Регистрация команд управления пользователем."""
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("settings", settings_command))
    
    logger.info("User commands registered successfully")