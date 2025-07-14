"""
Admin command handlers for the Doyobi Diary.

This module contains all admin-only command handlers.
"""

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from bot.admin.admin_operations import AdminOperations
from bot.config import Config
from bot.database.client import DatabaseClient
from bot.i18n.translator import Translator
from bot.utils.exceptions import AdminRequired
from bot.utils.rate_limiter import MultiTierRateLimiter, rate_limit
from monitoring import get_logger, set_user_context, track_errors_async

logger = get_logger(__name__)
translator = Translator()


def require_admin(func):
    """Decorator to require admin privileges."""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if not user:
            return

        admin_ops: AdminOperations = context.bot_data['admin_ops']
        if not admin_ops.is_admin(user.id):
            raise AdminRequired("This command requires admin privileges")

        return await func(update, context)
    return wrapper


# Broadcast command moved to admin_conversations.py with ConversationHandler


@rate_limit("admin")
@track_errors_async("broadcast_info_command")
@require_admin
async def broadcast_info_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show user statistics for admin."""
    user = update.effective_user
    set_user_context(user.id, user.username, user.first_name)

    # Get user statistics
    admin_ops: AdminOperations = context.bot_data['admin_ops']
    stats = await admin_ops.get_user_stats_optimized()

    if not stats:
        await update.message.reply_text(
            translator.translate("errors.stats_failed")
        )
        return

    # Use percentage from stats (already calculated)
    active_percentage = stats.get('active_percentage', 0)

    stats_text = f"{translator.translate('admin.stats_title')}" \
        f"{translator.translate('admin.total_users', total=stats['total'])}\n" \
        f"{translator.translate('admin.active_users', active=stats['active'], percentage=active_percentage)}\n" \
        f"{translator.translate('admin.new_users_week', count=stats['new_week'])}\n" \
        f"{translator.translate('admin.activity_level', level=translator.translate('common.high' if active_percentage > 50 else 'common.medium' if active_percentage > 25 else 'common.low'))}"

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

    # Create admin operations instance
    admin_ops = AdminOperations(db_client, config)

    # Store in bot data for handlers
    application.bot_data['db_client'] = db_client
    application.bot_data['config'] = config
    application.bot_data['admin_ops'] = admin_ops

    # Register admin command handlers
    # Note: broadcast moved to admin_conversations.py
    application.add_handler(CommandHandler("broadcast_info", broadcast_info_command))

    logger.info("Admin handlers registered successfully")
