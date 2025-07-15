"""User management commands: start, settings."""

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from bot.cache.ttl_cache import TTLCache
from bot.config import Config
from bot.database.client import DatabaseClient
from bot.database.user_operations import UserOperations
from bot.i18n import detect_user_language, get_translator
from bot.keyboards.keyboard_generators import create_main_menu
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
    db_client: DatabaseClient = context.bot_data["db_client"]
    config: Config = context.bot_data["config"]

    # Get user cache
    user_cache: TTLCache = context.bot_data["user_cache"]

    # Check if user exists and get their preferred language
    user_ops = UserOperations(db_client, user_cache)
    user_data = await user_ops.get_user_settings(user.id)

    if user_data:
        # User exists, use their saved language preference
        user_language = user_data.get("language", "ru")
    else:
        # New user, detect language from Telegram settings
        user_language = detect_user_language(user)

        # Ensure user exists in database
        try:
            await user_ops.ensure_user_exists(
                tg_id=user.id,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name,
                language=user_language,
            )
        except Exception as e:
            logger.error(f"Failed to ensure user exists: {e}")
            # Use fallback translator for error message
            translator = get_translator()
            translator.set_language(user_language)
            await update.message.reply_text(translator.translate("errors.registration"))
            return

    # Set up translator with user's language
    translator = get_translator()
    translator.set_language(user_language)

    # Create main menu
    keyboard = create_main_menu(config.is_admin_configured() and user.id == config.admin_user_id, translator)

    welcome_text = (
        f"{translator.translate('welcome.greeting', name=user.first_name)}\n\n"
        f"{translator.translate('welcome.description')}"
    )

    await update.message.reply_text(welcome_text, reply_markup=keyboard, parse_mode="Markdown")

    logger.info(f"User {user.id} opened main menu")


def setup_user_commands(application: Application) -> None:
    """Регистрация команд управления пользователем."""
    application.add_handler(CommandHandler("start", start_command))

    logger.info("User commands registered successfully")
