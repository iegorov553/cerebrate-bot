"""Configuration commands: window, freq."""

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from bot.cache.ttl_cache import TTLCache
from bot.database.client import DatabaseClient
from bot.i18n import get_translator
from bot.utils.rate_limiter import rate_limit
from monitoring import get_logger, set_user_context, track_errors_async

logger = get_logger(__name__)


@rate_limit("settings")
@track_errors_async("window_command")
async def window_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Set time window for default question notifications."""
    user = update.effective_user
    if user is None:
        return

    set_user_context(user.id, user.username, user.first_name)
    translator = get_translator()

    if not context.args:
        await update.message.reply_text(
            translator.translate("config.window_title")
            + translator.translate("config.window_usage")
            + translator.translate("config.examples_title")
            + translator.translate("config.window_example1")
            + translator.translate("config.window_example2"),
            parse_mode="Markdown",
        )
        return

    time_range = context.args[0]

    # Validate time format
    from bot.utils.datetime_utils import validate_time_window

    is_valid, error_msg, start_time, end_time = validate_time_window(time_range)
    if not is_valid:
        await update.message.reply_text(
            f"❌ {error_msg}\n\n"
            + translator.translate("config.window_format")
            + translator.translate("config.window_format_example"),
            parse_mode="Markdown",
        )
        return

    # Get dependencies
    db_client: DatabaseClient = context.bot_data["db_client"]
    user_cache: TTLCache = context.bot_data["user_cache"]

    # Initialize question manager and ensure user has default question
    from bot.questions import QuestionManager

    question_manager = QuestionManager(db_client, user_cache)

    try:
        # Ensure user has default question
        await question_manager.ensure_user_has_default_question(user.id)

        # Get default question
        default_question = await question_manager.get_user_default_question(user.id)
        if not default_question:
            await update.message.reply_text(translator.translate("errors.default_question_error"))
            return

        # Update time window for default question
        success = await question_manager.question_ops.update_question_schedule(
            default_question["id"], window_start=start_time.strftime("%H:%M:%S"), window_end=end_time.strftime("%H:%M:%S")
        )

        if success:
            await update.message.reply_text(
                f"{translator.translate('config.window_updated')}"
                f"{translator.translate('config.window_new_time')}{start_time.strftime('%H:%M')} - {end_time.strftime('%H:%M')}\n\n"
                f"{translator.translate('config.window_updated_note')}",
                parse_mode="Markdown",
            )
            logger.info(f"Time window updated for user {user.id}: {time_range}")
        else:
            await update.message.reply_text(translator.translate("errors.time_window_update_error"))
    except Exception as e:
        logger.error(f"Error updating time window for user {user.id}: {e}")
        await update.message.reply_text(translator.translate("errors.settings_update_error"))


@rate_limit("settings")
@track_errors_async("freq_command")
async def freq_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Set notification frequency for default question."""
    user = update.effective_user
    if user is None:
        return

    set_user_context(user.id, user.username, user.first_name)
    translator = get_translator()

    if not context.args:
        await update.message.reply_text(
            translator.translate("config.frequency_title")
            + translator.translate("config.freq_usage")
            + translator.translate("config.frequency_description")
            + translator.translate("config.examples_title")
            + translator.translate("config.freq_example_60")
            + translator.translate("config.freq_example_120_long")
            + translator.translate("config.freq_example_30"),
            parse_mode="Markdown",
        )
        return

    try:
        interval_min = int(context.args[0])
        if interval_min < 5:
            await update.message.reply_text(
                translator.translate("config.freq_min_error") + translator.translate("config.freq_min_example")
            )
            return
        elif interval_min > 1440:  # 24 hours
            await update.message.reply_text(
                translator.translate("config.freq_max_error") + translator.translate("config.freq_example_120")
            )
            return
    except ValueError:
        await update.message.reply_text(
            translator.translate("errors.invalid_number_format")
            + translator.translate("config.freq_usage")
            + translator.translate("config.freq_example")
        )
        return

    # Get dependencies
    db_client: DatabaseClient = context.bot_data["db_client"]
    user_cache: TTLCache = context.bot_data["user_cache"]

    # Initialize question manager and ensure user has default question
    from bot.questions import QuestionManager

    question_manager = QuestionManager(db_client, user_cache)

    try:
        # Ensure user has default question
        await question_manager.ensure_user_has_default_question(user.id)

        # Get default question
        default_question = await question_manager.get_user_default_question(user.id)
        if not default_question:
            await update.message.reply_text(translator.translate("errors.default_question_error"))
            return

        # Update frequency for default question
        success = await question_manager.question_ops.update_question_schedule(
            default_question["id"], interval_minutes=interval_min
        )

        if success:
            # Calculate human-readable frequency
            if interval_min < 60:
                freq_text = f"{interval_min} минут"
            elif interval_min == 60:
                freq_text = translator.translate("common.one_hour")
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
                translator.translate("config.frequency_updated")
                + f"📊 Новая частота: каждые {freq_text}\n\n"
                + f"Следующее уведомление придёт через {freq_text}.",
                parse_mode="Markdown",
            )
            logger.info(f"Frequency updated for user {user.id}: {interval_min} minutes")
        else:
            await update.message.reply_text(translator.translate("errors.frequency_update_error"))
    except Exception as e:
        logger.error(f"Error updating frequency for user {user.id}: {e}")
        await update.message.reply_text(translator.translate("errors.settings_update_error"))


def setup_config_commands(application: Application) -> None:
    """Регистрация команд настройки."""
    application.add_handler(CommandHandler("window", window_command))
    application.add_handler(CommandHandler("freq", freq_command))

    logger.info("Config commands registered successfully")
