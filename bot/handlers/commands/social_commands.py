"""Social commands: add_friend, friends, friend_requests, accept, decline."""

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from bot.cache.ttl_cache import TTLCache
from bot.database.client import DatabaseClient
from bot.database.user_operations import UserOperations
from bot.i18n import detect_user_language, get_translator
from bot.keyboards.keyboard_generators import create_friends_menu
from bot.utils.rate_limiter import rate_limit
from monitoring import get_logger, set_user_context, track_errors_async

logger = get_logger(__name__)


@rate_limit("friend_request")
@track_errors_async("add_friend_command")
async def add_friend_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /add_friend command."""
    user = update.effective_user
    if user is None:
        return

    set_user_context(user.id, user.username, user.first_name)

    # Get user language and translator
    user_language = detect_user_language(user)
    translator = get_translator()
    translator.set_language(user_language)

    if not context.args:
        await update.message.reply_text(
            f"{translator.translate('friends.add_friend_title')}\n\n"
            f"{translator.translate('friends.add_friend_usage')}\n\n"
            f"{translator.translate('friends.add_friend_example')}",
            parse_mode="Markdown",
        )
        return

    # Extract and validate username
    target_username_raw = context.args[0]

    from bot.utils.datetime_utils import validate_username

    is_valid, error_msg = validate_username(target_username_raw)
    if not is_valid:
        await update.message.reply_text(
            f"❌ {error_msg}\n\n" f"{translator.translate('friends.add_friend_example')}", parse_mode="Markdown"
        )
        return

    target_username = target_username_raw.lstrip("@")

    # Get dependencies
    db_client: DatabaseClient = context.bot_data["db_client"]
    user_cache: TTLCache = context.bot_data["user_cache"]

    # Implement friend request logic
    from bot.database.friend_operations import FriendOperations

    friend_ops = FriendOperations(db_client)
    user_ops = UserOperations(db_client, user_cache)

    # Find target user by username
    target_user = await user_ops.find_user_by_username(target_username)
    if not target_user:
        await update.message.reply_text(
            f"{translator.translate('friends.user_not_found', username=target_username)}\n\n"
            f"{translator.translate('friends.add_friend_note')}"
        )
        return

    target_id = target_user["tg_id"]

    # Send friend request (will check for existing friendship internally)
    success = await friend_ops.create_friend_request(user.id, target_id)
    if success:
        await update.message.reply_text(
            f"{translator.translate('friends.request_sent', username=target_username)}\n\n"
            f"{translator.translate('friends.add_friend_waiting')}"
        )

        # Notify target user if possible
        try:
            await context.bot.send_message(
                chat_id=target_id,
                text=f"{translator.translate('friends.add_friend_notification', username=user.username or user.first_name)}\n\n"
                f"{translator.translate('friends.add_friend_help')}",
            )
        except Exception as e:
            logger.warning(f"Could not notify user {target_id}: {e}")

    else:
        await update.message.reply_text(translator.translate("friends.request_failed"))


@rate_limit("general")
@track_errors_async("friends_command")
async def friends_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show friends menu."""
    user = update.effective_user
    if user is None:
        return

    set_user_context(user.id, user.username, user.first_name)

    # Get user language and translator
    user_language = detect_user_language(user)
    translator = get_translator()
    translator.set_language(user_language)

    # Create friends menu
    keyboard = create_friends_menu(0, 0, translator)

    await update.message.reply_text(
        f"{translator.translate('friends.title')}\n\n" f"{translator.translate('friends.choose_action')}",
        reply_markup=keyboard,
        parse_mode="Markdown",
    )


@rate_limit("general")
@track_errors_async("friend_requests_command")
async def friend_requests_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show friend requests management."""
    user = update.effective_user
    if user is None:
        return

    set_user_context(user.id, user.username, user.first_name)

    # Get user language and translator
    user_language = detect_user_language(user)
    translator = get_translator()
    translator.set_language(user_language)

    # Get dependencies
    db_client: DatabaseClient = context.bot_data["db_client"]

    from bot.database.friend_operations import FriendOperations

    friend_ops = FriendOperations(db_client)

    # Get friend requests
    requests_data = await friend_ops.get_friend_requests_optimized(user.id)

    incoming = requests_data.get("incoming", [])
    outgoing = requests_data.get("outgoing", [])

    text = translator.title("friends.requests", "📥")

    if incoming:
        text += f"{translator.translate('friends.requests_incoming')}\n"
        for req in incoming[:5]:  # Показываем только первые 5
            username = req.get("tg_username", translator.translate("common.unknown"))
            name = req.get("tg_first_name", "")
            text += f"• @{username} ({name})\n"

            def escape_markdown_safe(text):
                if not text:
                    return ""
                return (
                    str(text)
                    .replace("_", "\\_")
                    .replace("*", "\\*")
                    .replace("`", "\\`")
                    .replace("[", "\\[")
                    .replace("]", "\\]")
                )

            safe_username = escape_markdown_safe(username)
            accept_cmd = f"`/accept @{safe_username}`"
            decline_cmd = f"`/decline @{safe_username}`"
            text += f"  {accept_cmd} | {decline_cmd}\n\n"
    else:
        text += f"{translator.translate('friends.requests_none_incoming')}\n\n"

    if outgoing:
        text += f"{translator.translate('friends.requests_outgoing')}\n"
        for req in outgoing[:5]:  # Показываем только первые 5
            username = req.get("tg_username", translator.translate("common.unknown"))
            name = req.get("tg_first_name", "")
            text += f"• @{username} ({name}) {translator.translate('friends.request_waiting')}\n"
    else:
        text += translator.translate("friends.requests_none_outgoing")

    await update.message.reply_text(text, parse_mode="Markdown")


@rate_limit("friend_request")
@track_errors_async("accept_friend_command")
async def accept_friend_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Accept friend request."""
    user = update.effective_user
    if user is None:
        return

    set_user_context(user.id, user.username, user.first_name)

    # Get user language and translator
    user_language = detect_user_language(user)
    translator = get_translator()
    translator.set_language(user_language)

    if not context.args:
        await update.message.reply_text(
            f"{translator.title('friends.accept_title', '👥')}" f"{translator.translate('friends.accept_usage')}",
            parse_mode="Markdown",
        )
        return

    target_username = context.args[0].lstrip("@")

    # Get dependencies
    db_client: DatabaseClient = context.bot_data["db_client"]
    user_cache: TTLCache = context.bot_data["user_cache"]

    from bot.database.friend_operations import FriendOperations
    from bot.database.user_operations import UserOperations

    friend_ops = FriendOperations(db_client)
    user_ops = UserOperations(db_client, user_cache)

    # Find requester by username
    requester = await user_ops.find_user_by_username(target_username)
    if not requester:
        await update.message.reply_text(translator.translate("friends.user_not_found", username=target_username))
        return

    # Accept friend request
    success = await friend_ops.accept_friend_request(requester["tg_id"], user.id)
    if success:
        await update.message.reply_text(
            f"{translator.translate('friends.request_accepted', username=target_username)}\n\n"
            f"{translator.translate('friends.accept_success')}"
        )

        # Notify requester if possible
        try:
            await context.bot.send_message(
                chat_id=requester["tg_id"],
                text=translator.translate("friends.request_notification_sent", username=user.username or user.first_name),
            )
        except Exception as e:
            logger.warning(f"Could not notify user {requester['tg_id']}: {e}")
    else:
        await update.message.reply_text(translator.translate("friends.request_not_found", username=target_username))


@rate_limit("friend_request")
@track_errors_async("decline_friend_command")
async def decline_friend_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Decline friend request."""
    user = update.effective_user
    if user is None:
        return

    set_user_context(user.id, user.username, user.first_name)

    # Get user language and translator
    user_language = detect_user_language(user)
    translator = get_translator()
    translator.set_language(user_language)

    if not context.args:
        await update.message.reply_text(
            f"{translator.title('friends.decline_title', '👥')}" f"{translator.translate('friends.decline_usage')}",
            parse_mode="Markdown",
        )
        return

    target_username = context.args[0].lstrip("@")

    # Get dependencies
    db_client: DatabaseClient = context.bot_data["db_client"]
    user_cache: TTLCache = context.bot_data["user_cache"]

    from bot.database.friend_operations import FriendOperations
    from bot.database.user_operations import UserOperations

    friend_ops = FriendOperations(db_client)
    user_ops = UserOperations(db_client, user_cache)

    # Find requester by username
    requester = await user_ops.find_user_by_username(target_username)
    if not requester:
        await update.message.reply_text(translator.translate("friends.user_not_found", username=target_username))
        return

    # Decline friend request
    success = await friend_ops.decline_friend_request(requester["tg_id"], user.id)
    if success:
        await update.message.reply_text(translator.translate("friends.request_declined", username=target_username))

        # Notify requester if possible
        try:
            await context.bot.send_message(
                chat_id=requester["tg_id"],
                text=translator.translate("friends.request_notification_declined", username=user.username or user.first_name),
            )
        except Exception as e:
            logger.warning(f"Could not notify user {requester['tg_id']}: {e}")
    else:
        await update.message.reply_text(translator.translate("friends.request_not_found", username=target_username))


def setup_social_commands(application: Application) -> None:
    """Регистрация команд социальных функций."""
    application.add_handler(CommandHandler("add_friend", add_friend_command))
    application.add_handler(CommandHandler("friends", friends_command))
    application.add_handler(CommandHandler("friend_requests", friend_requests_command))
    application.add_handler(CommandHandler("accept", accept_friend_command))
    application.add_handler(CommandHandler("decline", decline_friend_command))

    logger.info("Social commands registered successfully")
