"""History and web interface commands."""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, WebAppInfo
from telegram.ext import Application, CommandHandler, ContextTypes

from bot.cache.ttl_cache import TTLCache
from bot.config import Config
from bot.database.client import DatabaseClient
from bot.utils.rate_limiter import rate_limit
from monitoring import get_logger, set_user_context, track_errors_async

logger = get_logger(__name__)


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
    from bot.utils.translation_helpers import get_user_translator
    translator = await get_user_translator(user.id, db_client, user_cache)

    # Create web app button for main webapp page
    web_app = WebAppInfo(url=config.webapp_url)
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton(translator.translate('menu.history'), web_app=web_app)
    ]])

    # Use formatter for combined text
    message_text = translator.format_title(translator.translate('menu.history'))
    message_text += translator.translate('history.webapp_description')
    
    await update.message.reply_text(
        message_text,
        reply_markup=keyboard,
        parse_mode='Markdown'
    )

    logger.info(f"User {user.id} opened history webapp")


def setup_history_commands(application: Application) -> None:
    """Регистрация команд истории."""
    application.add_handler(CommandHandler("history", history_command))
    
    logger.info("History commands registered successfully")