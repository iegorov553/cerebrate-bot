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
from datetime import datetime, timezone

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

def run_coro_in_loop(coro):
    loop = asyncio.get_event_loop()
    if loop.is_running():
        loop.create_task(coro)
    else:
        loop.run_until_complete(coro)

async def main() -> None:
    application: Application = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("settings", settings_command))
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
