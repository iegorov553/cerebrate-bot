"""
Feedback message handlers for user feedback submissions.
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from bot.cache.ttl_cache import TTLCache
from bot.config import Config
from bot.database.client import DatabaseClient
from bot.feedback import FeedbackManager
from bot.utils.translation_helpers import get_user_translator
from bot.keyboards.keyboard_generators import create_main_menu
from bot.utils.rate_limiter import MultiTierRateLimiter, rate_limit
from monitoring import get_logger, set_user_context, track_errors_async

logger = get_logger(__name__)


@rate_limit("general")
@track_errors_async("handle_feedback_message")
async def handle_feedback_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle feedback message from user."""
    if not update.message or not update.effective_user:
        return

    user = update.effective_user
    message_text = update.message.text

    if not message_text or len(message_text.strip()) == 0:
        return

    # Skip commands
    if message_text.startswith('/'):
        return

    set_user_context(user.id, user.username, user.first_name)

    # Get dependencies
    config: Config = context.bot_data['config']
    db_client: DatabaseClient = context.bot_data['db_client']
    user_cache: TTLCache = context.bot_data['user_cache']

    # Check if feedback is enabled
    if not config.is_feedback_enabled():
        return

    # Initialize feedback manager
    rate_limiter = MultiTierRateLimiter(feedback_rate_limit=config.feedback_rate_limit)
    feedback_manager = FeedbackManager(config, rate_limiter, user_cache)

    # Check if user has active feedback session
    session = await feedback_manager.get_feedback_session(user.id)
    if not session:
        return  # No active feedback session, handle as regular message

    # Get user translator
    translator = await get_user_translator(user.id, db_client, user_cache)

    try:
        if session.get("status") == "awaiting_description":
            # User is providing feedback description
            await handle_feedback_description(
                update, context, feedback_manager, translator, message_text
            )

    except Exception as e:
        logger.error(f"Error handling feedback message: {e}")
        await feedback_manager.clear_feedback_session(user.id)

        await update.message.reply_text(
            translator.translate('feedback.error'),
            reply_markup=create_main_menu(
                config.is_admin_configured() and user.id == config.admin_user_id,
                translator
            ),
            parse_mode='Markdown'
        )


async def handle_feedback_description(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    feedback_manager: FeedbackManager,
    translator,
    description: str
) -> None:
    """Handle feedback description submission."""
    user = update.effective_user

    # Store description in session
    session = await feedback_manager.get_feedback_session(user.id)
    if not session:
        await update.message.reply_text(
            translator.translate('feedback.session_expired'),
            parse_mode='Markdown'
        )
        return

    session["description"] = description
    session["status"] = "awaiting_confirmation"

    # Store updated session
    await feedback_manager.user_cache.set(
        f"feedback_session_{user.id}",
        session,
        ttl=3600
    )

    # Show confirmation
    feedback_type = session.get("feedback_type", "general")

    # Preview message
    preview_text = (
        f"{translator.translate('feedback.confirm_title')}\n\n"
        f"**{translator.translate(f'feedback.{feedback_type}')}**\n\n"
        f"*{description[:500]}{'...' if len(description) > 500 else ''}*"
    )

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                translator.translate("feedback.confirm_send"),
                callback_data=f"feedback_confirm_{user.id}"
            ),
            InlineKeyboardButton(
                translator.translate("feedback.confirm_cancel"),
                callback_data=f"feedback_cancel_{user.id}"
            )
        ]
    ])

    await update.message.reply_text(
        preview_text,
        reply_markup=keyboard,
        parse_mode='Markdown'
    )


@track_errors_async("handle_feedback_confirmation")
async def handle_feedback_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE, action: str, user_id: int) -> None:
    """Handle feedback confirmation/cancellation."""
    query = update.callback_query
    user = update.effective_user

    if not query or not user or user.id != user_id:
        return

    await query.answer()

    # Get dependencies
    config: Config = context.bot_data['config']
    db_client: DatabaseClient = context.bot_data['db_client']
    user_cache: TTLCache = context.bot_data['user_cache']

    # Get user translator
    translator = await get_user_translator(user.id, db_client, user_cache)

    # Initialize feedback manager
    rate_limiter = MultiTierRateLimiter(feedback_rate_limit=config.feedback_rate_limit)
    feedback_manager = FeedbackManager(config, rate_limiter, user_cache)

    if action == "confirm":
        # Submit feedback
        session = await feedback_manager.get_feedback_session(user.id)
        if not session or "description" not in session:
            await query.edit_message_text(
                translator.translate('feedback.session_expired'),
                parse_mode='Markdown'
            )
            return

        description = session["description"]

        # Submit to GitHub
        issue_url = await feedback_manager.submit_feedback(
            user.id,
            user.username,
            description
        )

        if issue_url:
            # Success with GitHub link
            success_text = translator.translate('feedback.success', issue_url=issue_url)
        else:
            # Success without GitHub link (disabled or failed)
            success_text = translator.translate('feedback.success_no_link')

        await query.edit_message_text(
            success_text,
            reply_markup=create_main_menu(
                config.is_admin_configured() and user.id == config.admin_user_id,
                translator
            ),
            parse_mode='Markdown'
        )

    elif action == "cancel":
        # Cancel feedback
        await feedback_manager.clear_feedback_session(user.id)

        await query.edit_message_text(
            translator.translate('feedback.cancelled'),
            reply_markup=create_main_menu(
                config.is_admin_configured() and user.id == config.admin_user_id,
                translator
            ),
            parse_mode='Markdown'
        )
