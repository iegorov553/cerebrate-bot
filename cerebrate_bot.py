"""
Telegram-bot 'Hour Watcher': asks two accounts every hour and writes replies to Supabase.

Для Railway, Render, VPS, любой среды где переменные окружения задаются через UI:
- TELEGRAM_BOT_TOKEN
- TARGET_USER_IDS
- SUPABASE_URL
- SUPABASE_SERVICE_ROLE_KEY
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
from datetime import datetime, timezone, time

from supabase import create_client, Client
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram import ForceReply, Update
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)


# --- Logging ---
logging.basicConfig(
    format="%(asctime)s | %(levelname)8s | %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# --- Config ---
BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_ROLE_KEY: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
QUESTION: str = "Что ты сейчас делаешь?"

if not (BOT_TOKEN and SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY):
    logger.error("Не заданы обязательные переменные среды. Завершаюсь.")
    raise SystemExit(1)

# --- Supabase ---
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

# --- Database functions ---
async def ensure_user_exists(tg_id: int, username: str = None, first_name: str = None, last_name: str = None) -> dict:
    """Ensure user exists in database, create if not."""
    try:
        # Check if user exists
        result = supabase.table("users").select("*").eq("tg_id", tg_id).execute()
        
        if result.data:
            return result.data[0]
        
        # Create new user with default settings
        new_user = {
            "tg_id": tg_id,
            "tg_username": username,
            "tg_first_name": first_name,
            "tg_last_name": last_name,
            "enabled": True,
            "window_start": "09:00:00",
            "window_end": "23:00:00",
            "interval_min": 60
        }
        
        result = supabase.table("users").insert(new_user).execute()
        logger.info("Создан новый пользователь: %s", tg_id)
        return result.data[0]
    
    except Exception as exc:
        logger.error("Ошибка работы с пользователем %s: %s", tg_id, exc)
        return None

# --- Telegram callbacks ---
async def ask_question(app: Application) -> None:
    """Ask the question to all active users."""
    try:
        # Get all enabled users within their time window
        current_time = datetime.now().time()
        
        result = supabase.table("users").select("*").eq("enabled", True).execute()
        
        for user in result.data:
            user_start = datetime.strptime(user['window_start'], '%H:%M:%S').time()
            user_end = datetime.strptime(user['window_end'], '%H:%M:%S').time()
            
            if user_start <= current_time <= user_end:
                try:
                    await app.bot.send_message(
                        chat_id=user['tg_id'], 
                        text=QUESTION, 
                        reply_markup=ForceReply()
                    )
                    logger.info("Отправлен вопрос пользователю %s", user['tg_id'])
                except Exception as exc:
                    logger.warning("Не удалось отправить сообщение %s: %s", user['tg_id'], exc)
    
    except Exception as exc:
        logger.error("Ошибка при отправке вопросов: %s", exc)

async def handle_reply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if user is None:
        return

    # Ensure user exists in database
    await ensure_user_exists(
        tg_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name
    )

    text = update.effective_message.text or "<без текста>"
    timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')

    try:
        data = {
            "tg_name": user.username or user.full_name,
            "jobs_timestamp": timestamp,
            "job_text": text
        }
        supabase.table("tg_jobs").insert(data).execute()
        logger.info("Записан ответ от %s", user.id)
    except Exception as exc:
        logger.error("Ошибка записи в Supabase: %s", exc)

async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show user settings from database."""
    user = update.effective_user
    if user is None:
        return

    # Ensure user exists
    user_data = await ensure_user_exists(
        tg_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name
    )

    if not user_data:
        await update.message.reply_text("Ошибка получения настроек.")
        return

    settings_text = f"""🔧 **Ваши настройки:**

✅ Статус: {'Включен' if user_data['enabled'] else 'Отключен'}
⏰ Время работы: {user_data['window_start'][:5]} - {user_data['window_end'][:5]}
📊 Интервал: {user_data['interval_min']} минут
👤 Telegram ID: {user_data['tg_id']}
📅 Регистрация: {user_data['created_at'][:10]}"""

    await update.message.reply_text(settings_text, parse_mode='Markdown')

async def notify_on_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Enable notifications for user."""
    user = update.effective_user
    if user is None:
        return

    try:
        # Ensure user exists and update enabled status
        await ensure_user_exists(
            tg_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name
        )
        
        supabase.table("users").update({"enabled": True}).eq("tg_id", user.id).execute()
        await update.message.reply_text("✅ Оповещения включены!")
        logger.info("Пользователь %s включил оповещения", user.id)
    except Exception as exc:
        logger.error("Ошибка включения оповещений для %s: %s", user.id, exc)
        await update.message.reply_text("❌ Ошибка при включении оповещений.")

async def notify_off_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Disable notifications for user."""
    user = update.effective_user
    if user is None:
        return

    try:
        # Ensure user exists and update enabled status
        await ensure_user_exists(
            tg_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name
        )
        
        supabase.table("users").update({"enabled": False}).eq("tg_id", user.id).execute()
        await update.message.reply_text("❌ Оповещения отключены.")
        logger.info("Пользователь %s отключил оповещения", user.id)
    except Exception as exc:
        logger.error("Ошибка отключения оповещений для %s: %s", user.id, exc)
        await update.message.reply_text("❌ Ошибка при отключении оповещений.")

async def window_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:\n    \"\"\"Set user time window for notifications. Format: /window HH:MM-HH:MM\"\"\"\n    user = update.effective_user\n    if user is None:\n        return\n\n    if not context.args or len(context.args) != 1:\n        await update.message.reply_text(\n            \"\u274c \u041d\u0435\u043f\u0440\u0430\u0432\u0438\u043b\u044c\u043d\u044b\u0439 \u0444\u043e\u0440\u043c\u0430\u0442!\\n\"\n            \"\u041f\u0440\u0438\u043c\u0435\u0440: `/window 09:00-23:00`\", \n            parse_mode='Markdown'\n        )\n        return\n\n    time_range = context.args[0]\n    \n    # Validate format HH:MM-HH:MM\n    pattern = r'^([0-2][0-9]):([0-5][0-9])-([0-2][0-9]):([0-5][0-9])$'\n    match = re.match(pattern, time_range)\n    \n    if not match:\n        await update.message.reply_text(\n            \"\u274c \u041d\u0435\u043f\u0440\u0430\u0432\u0438\u043b\u044c\u043d\u044b\u0439 \u0444\u043e\u0440\u043c\u0430\u0442 \u0432\u0440\u0435\u043c\u0435\u043d\u0438!\\n\"\n            \"\u041f\u0440\u0438\u043c\u0435\u0440: `/window 09:00-23:00`\",\n            parse_mode='Markdown'\n        )\n        return\n    \n    start_hour, start_min, end_hour, end_min = map(int, match.groups())\n    \n    # Validate time values\n    if start_hour > 23 or end_hour > 23:\n        await update.message.reply_text(\"\u274c \u0427\u0430\u0441\u044b \u0434\u043e\u043b\u0436\u043d\u044b \u0431\u044b\u0442\u044c \u043e\u0442 00 \u0434\u043e 23!\")\n        return\n    \n    start_time = time(start_hour, start_min)\n    end_time = time(end_hour, end_min)\n    \n    # Calculate duration in minutes\n    start_minutes = start_hour * 60 + start_min\n    end_minutes = end_hour * 60 + end_min\n    \n    # Handle day boundary crossing\n    if end_minutes <= start_minutes:\n        end_minutes += 24 * 60  # Add 24 hours\n    \n    duration_minutes = end_minutes - start_minutes\n    \n    # Validate minimum 1 hour interval\n    if duration_minutes < 60:\n        await update.message.reply_text(\"\u274c \u041c\u0438\u043d\u0438\u043c\u0430\u043b\u044c\u043d\u044b\u0439 \u0438\u043d\u0442\u0435\u0440\u0432\u0430\u043b - 1 \u0447\u0430\u0441!\")\n        return\n    \n    try:\n        # Ensure user exists and update time window\n        await ensure_user_exists(\n            tg_id=user.id,\n            username=user.username,\n            first_name=user.first_name,\n            last_name=user.last_name\n        )\n        \n        supabase.table(\"users\").update({\n            \"window_start\": start_time.strftime('%H:%M:%S'),\n            \"window_end\": end_time.strftime('%H:%M:%S')\n        }).eq(\"tg_id\", user.id).execute()\n        \n        await update.message.reply_text(\n            f\"\u2705 \u0412\u0440\u0435\u043c\u044f \u043e\u043f\u043e\u0432\u0435\u0449\u0435\u043d\u0438\u0439 \u043e\u0431\u043d\u043e\u0432\u043b\u0435\u043d\u043e!\\n\"\n            f\"\u23f0 {start_time.strftime('%H:%M')} - {end_time.strftime('%H:%M')}\"\n        )\n        logger.info(\"\u041f\u043e\u043b\u044c\u0437\u043e\u0432\u0430\u0442\u0435\u043b\u044c %s \u0443\u0441\u0442\u0430\u043d\u043e\u0432\u0438\u043b \u0432\u0440\u0435\u043c\u044f: %s-%s\", user.id, start_time, end_time)\n    \n    except Exception as exc:\n        logger.error(\"\u041e\u0448\u0438\u0431\u043a\u0430 \u043e\u0431\u043d\u043e\u0432\u043b\u0435\u043d\u0438\u044f \u0432\u0440\u0435\u043c\u0435\u043d\u0438 \u0434\u043b\u044f %s: %s\", user.id, exc)\n        await update.message.reply_text(\"\u274c \u041e\u0448\u0438\u0431\u043a\u0430 \u043f\u0440\u0438 \u043e\u0431\u043d\u043e\u0432\u043b\u0435\u043d\u0438\u0438 \u0432\u0440\u0435\u043c\u0435\u043d\u0438.\")\n\nasync def freq_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:\n    \"\"\"Set user notification frequency in minutes. Format: /freq N\"\"\"\n    user = update.effective_user\n    if user is None:\n        return\n\n    if not context.args or len(context.args) != 1:\n        await update.message.reply_text(\n            \"\u274c \u041d\u0435\u043f\u0440\u0430\u0432\u0438\u043b\u044c\u043d\u044b\u0439 \u0444\u043e\u0440\u043c\u0430\u0442!\\n\"\n            \"\u041f\u0440\u0438\u043c\u0435\u0440: `/freq 60` (\u0434\u043b\u044f 60 \u043c\u0438\u043d\u0443\u0442)\",\n            parse_mode='Markdown'\n        )\n        return\n\n    try:\n        interval_min = int(context.args[0])\n        \n        # Validate interval (minimum 5 minutes, maximum 24 hours)\n        if interval_min < 5:\n            await update.message.reply_text(\"\u274c \u041c\u0438\u043d\u0438\u043c\u0430\u043b\u044c\u043d\u044b\u0439 \u0438\u043d\u0442\u0435\u0440\u0432\u0430\u043b - 5 \u043c\u0438\u043d\u0443\u0442!\")\n            return\n        \n        if interval_min > 1440:  # 24 hours\n            await update.message.reply_text(\"\u274c \u041c\u0430\u043a\u0441\u0438\u043c\u0430\u043b\u044c\u043d\u044b\u0439 \u0438\u043d\u0442\u0435\u0440\u0432\u0430\u043b - 1440 \u043c\u0438\u043d\u0443\u0442 (24 \u0447\u0430\u0441\u0430)!\")\n            return\n        \n        # Ensure user exists and update interval\n        await ensure_user_exists(\n            tg_id=user.id,\n            username=user.username,\n            first_name=user.first_name,\n            last_name=user.last_name\n        )\n        \n        supabase.table(\"users\").update({\n            \"interval_min\": interval_min\n        }).eq(\"tg_id\", user.id).execute()\n        \n        # Convert to human readable format\n        if interval_min >= 60:\n            hours = interval_min // 60\n            minutes = interval_min % 60\n            if minutes == 0:\n                interval_text = f\"{hours} \u0447\u0430\u0441(\u043e\u0432)\"\n            else:\n                interval_text = f\"{hours} \u0447\u0430\u0441(\u043e\u0432) {minutes} \u043c\u0438\u043d\u0443\u0442\"\n        else:\n            interval_text = f\"{interval_min} \u043c\u0438\u043d\u0443\u0442\"\n        \n        await update.message.reply_text(\n            f\"\u2705 \u0418\u043d\u0442\u0435\u0440\u0432\u0430\u043b \u043e\u043f\u043e\u0432\u0435\u0449\u0435\u043d\u0438\u0439 \u043e\u0431\u043d\u043e\u0432\u043b\u0451\u043d!\\n\"\n            f\"\ud83d\udcca \u041a\u0430\u0436\u0434\u044b\u0435 {interval_text}\"\n        )\n        logger.info(\"\u041f\u043e\u043b\u044c\u0437\u043e\u0432\u0430\u0442\u0435\u043b\u044c %s \u0443\u0441\u0442\u0430\u043d\u043e\u0432\u0438\u043b \u0438\u043d\u0442\u0435\u0440\u0432\u0430\u043b: %s \u043c\u0438\u043d\u0443\u0442\", user.id, interval_min)\n        \n    except ValueError:\n        await update.message.reply_text(\"\u274c \u041d\u0443\u0436\u043d\u043e \u0443\u043a\u0430\u0437\u0430\u0442\u044c \u0447\u0438\u0441\u043b\u043e!\")\n    except Exception as exc:\n        logger.error(\"\u041e\u0448\u0438\u0431\u043a\u0430 \u043e\u0431\u043d\u043e\u0432\u043b\u0435\u043d\u0438\u044f \u0438\u043d\u0442\u0435\u0440\u0432\u0430\u043b\u0430 \u0434\u043b\u044f %s: %s\", user.id, exc)\n        await update.message.reply_text(\"\u274c \u041e\u0448\u0438\u0431\u043a\u0430 \u043f\u0440\u0438 \u043e\u0431\u043d\u043e\u0432\u043b\u0435\u043d\u0438\u0438 \u0438\u043d\u0442\u0435\u0440\u0432\u0430\u043b\u0430.\")\n\ndef run_coro_in_loop(coro):"
    loop = asyncio.get_event_loop()
    if loop.is_running():
        loop.create_task(coro)
    else:
        loop.run_until_complete(coro)

async def main() -> None:
    application: Application = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("settings", settings_command))
    application.add_handler(CommandHandler("notify_on", notify_on_command))
    application.add_handler(CommandHandler("notify_off", notify_off_command))
    application.add_handler(CommandHandler("window", window_command))
    application.add_handler(CommandHandler("freq", freq_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_reply))
    
    # Scheduler for asking questions
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        lambda: run_coro_in_loop(ask_question(application)),
        "cron",
        minute="*"  # Every minute - we'll check user settings inside ask_question
    )
    scheduler.start()
    logger.info("Бот запущен. Жду сигнала...")
    await application.run_polling()

if __name__ == "__main__":
    import sys

    if sys.platform.startswith("win") and sys.version_info >= (3, 8):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    try:
        import nest_asyncio
        nest_asyncio.apply()
        loop = asyncio.get_event_loop()
        loop.run_until_complete(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Остановлено вручную.")
