"""System commands: health check."""

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from bot.database.client import DatabaseClient
from bot.utils.rate_limiter import rate_limit
from monitoring import get_logger, set_user_context, track_errors_async

logger = get_logger(__name__)


@rate_limit("general")
@track_errors_async("health_command")
async def health_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /health command - show system health status."""
    user = update.effective_user
    if user is None:
        return

    set_user_context(user.id, user.username, user.first_name)

    # Get dependencies from context
    db_client: DatabaseClient = context.bot_data['db_client']

    # Импортируем HealthService
    from bot.services.health_service import HealthService
    from bot.utils.version import get_bot_version

    try:
        # Создаем health service
        version = get_bot_version()
        health_service = HealthService(db_client, version)

        # Получаем статус здоровья системы
        health_status = await health_service.get_system_health(context.application)

        # Формируем сообщение
        status_emoji = {
            "healthy": "✅",
            "degraded": "⚠️",
            "unhealthy": "❌"
        }

        # Безопасное экранирование для Markdown
        def escape_markdown_safe(text):
            if not text:
                return ""
            return (str(text).replace('_', '\\_').replace('*', '\\*')
                    .replace('`', '\\`').replace('[', '\\[').replace(']', '\\]'))

        message = "🏥 **System Health Check**\n\n"
        message += f"{status_emoji.get(health_status.status, '❓')} **Overall Status:** {health_status.status}\n"

        # Безопасное время
        timestamp_safe = health_status.timestamp.split('T')[0] + ' ' + health_status.timestamp.split('T')[1][:8]
        message += f"📅 **Timestamp:** `{timestamp_safe}`\n"
        message += f"🔢 **Version:** {health_status.version}\n"
        message += f"⏱️ **Uptime:** {health_status.uptime_seconds:.1f}s\n\n"

        message += "**Components:**\n"
        for name, component in health_status.components.items():
            emoji = status_emoji.get(component.status, '❓')
            message += f"{emoji} **{name.title()}:** {component.status}"

            if component.latency_ms:
                message += f" ({component.latency_ms:.0f}ms)"

            if component.error:
                safe_error = escape_markdown_safe(component.error)
                message += f"\n   ⚠️ Error: `{safe_error}`"

            message += "\n"

        await update.message.reply_text(
            message,
            parse_mode='Markdown'
        )

        logger.info(f"Health check command executed for user {user.id}, status: {health_status.status}")

    except Exception as e:
        logger.error(f"Health command failed for user {user.id}: {e}")
        await update.message.reply_text(
            "❌ Failed to check system health. Please try again later.",
            parse_mode='Markdown'
        )


def setup_system_commands(application: Application) -> None:
    """Регистрация системных команд."""
    application.add_handler(CommandHandler("health", health_command))
    
    logger.info("System commands registered successfully")