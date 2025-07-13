"""Configuration commands: window, freq."""

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from bot.cache.ttl_cache import TTLCache
from bot.database.client import DatabaseClient
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


def setup_config_commands(application: Application) -> None:
    """Регистрация команд настройки."""
    application.add_handler(CommandHandler("window", window_command))
    application.add_handler(CommandHandler("freq", freq_command))
    
    logger.info("Config commands registered successfully")