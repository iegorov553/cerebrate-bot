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
from telegram import ForceReply, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram import WebAppInfo
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
    """Ask the question to all active users based on their individual intervals."""
    try:
        # Get all enabled users
        result = supabase.table("users").select("*").eq("enabled", True).execute()
        current_time = datetime.now()
        
        for user in result.data:
            # Check if user is within their time window
            user_start = datetime.strptime(user['window_start'], '%H:%M:%S').time()
            user_end = datetime.strptime(user['window_end'], '%H:%M:%S').time()
            current_time_only = current_time.time()
            
            if not (user_start <= current_time_only <= user_end):
                continue
            
            # Check if enough time has passed since last notification
            last_sent = user.get('last_notification_sent')
            interval_minutes = user.get('interval_min', 60)
            
            should_send = False
            if last_sent is None:
                # First time sending to this user
                should_send = True
            else:
                # Parse last sent time and check interval
                try:
                    last_sent_dt = datetime.fromisoformat(last_sent.replace('Z', '+00:00'))
                    time_diff = current_time - last_sent_dt.replace(tzinfo=None)
                    if time_diff.total_seconds() >= (interval_minutes * 60):
                        should_send = True
                except (ValueError, AttributeError) as exc:
                    logger.warning("Ошибка парсинга времени для %s: %s", user['tg_id'], exc)
                    should_send = True
            
            if should_send:
                try:
                    await app.bot.send_message(
                        chat_id=user['tg_id'], 
                        text=QUESTION, 
                        reply_markup=ForceReply()
                    )
                    
                    # Update last notification time
                    supabase.table("users").update({
                        "last_notification_sent": current_time.isoformat()
                    }).eq("tg_id", user['tg_id']).execute()
                    
                    logger.info("Отправлен вопрос пользователю %s (интервал: %s мин)", 
                              user['tg_id'], interval_minutes)
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

async def window_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Set user time window for notifications. Format: /window HH:MM-HH:MM"""
    user = update.effective_user
    if user is None:
        return

    if not context.args or len(context.args) != 1:
        await update.message.reply_text(
            "❌ Неправильный формат!\n"
            "Пример: `/window 09:00-23:00`", 
            parse_mode='Markdown'
        )
        return

    time_range = context.args[0]
    
    # Validate format HH:MM-HH:MM
    pattern = r'^([0-2][0-9]):([0-5][0-9])-([0-2][0-9]):([0-5][0-9])$'
    match = re.match(pattern, time_range)
    
    if not match:
        await update.message.reply_text(
            "❌ Неправильный формат времени!\n"
            "Пример: `/window 09:00-23:00`",
            parse_mode='Markdown'
        )
        return
    
    start_hour, start_min, end_hour, end_min = map(int, match.groups())
    
    # Validate time values
    if start_hour > 23 or end_hour > 23:
        await update.message.reply_text("❌ Часы должны быть от 00 до 23!")
        return
    
    start_time = time(start_hour, start_min)
    end_time = time(end_hour, end_min)
    
    # Calculate duration in minutes
    start_minutes = start_hour * 60 + start_min
    end_minutes = end_hour * 60 + end_min
    
    # Handle day boundary crossing
    if end_minutes <= start_minutes:
        end_minutes += 24 * 60  # Add 24 hours
    
    duration_minutes = end_minutes - start_minutes
    
    # Validate minimum 1 hour interval
    if duration_minutes < 60:
        await update.message.reply_text("❌ Минимальный интервал - 1 час!")
        return
    
    try:
        # Ensure user exists and update time window
        await ensure_user_exists(
            tg_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name
        )
        
        supabase.table("users").update({
            "window_start": start_time.strftime('%H:%M:%S'),
            "window_end": end_time.strftime('%H:%M:%S')
        }).eq("tg_id", user.id).execute()
        
        await update.message.reply_text(
            f"✅ Время оповещений обновлено!\n"
            f"⏰ {start_time.strftime('%H:%M')} - {end_time.strftime('%H:%M')}"
        )
        logger.info("Пользователь %s установил время: %s-%s", user.id, start_time, end_time)
    
    except Exception as exc:
        logger.error("Ошибка обновления времени для %s: %s", user.id, exc)
        await update.message.reply_text("❌ Ошибка при обновлении времени.")

async def freq_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Set user notification frequency in minutes. Format: /freq N"""
    user = update.effective_user
    if user is None:
        return

    if not context.args or len(context.args) != 1:
        await update.message.reply_text(
            "❌ Неправильный формат!\n"
            "Пример: `/freq 60` (для 60 минут)",
            parse_mode='Markdown'
        )
        return

    try:
        interval_min = int(context.args[0])
        
        # Validate interval (minimum 5 minutes, maximum 24 hours)
        if interval_min < 5:
            await update.message.reply_text("❌ Минимальный интервал - 5 минут!")
            return
        
        if interval_min > 1440:  # 24 hours
            await update.message.reply_text("❌ Максимальный интервал - 1440 минут (24 часа)!")
            return
        
        # Ensure user exists and update interval
        await ensure_user_exists(
            tg_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name
        )
        
        supabase.table("users").update({
            "interval_min": interval_min
        }).eq("tg_id", user.id).execute()
        
        # Convert to human readable format
        if interval_min >= 60:
            hours = interval_min // 60
            minutes = interval_min % 60
            if minutes == 0:
                interval_text = f"{hours} час(ов)"
            else:
                interval_text = f"{hours} час(ов) {minutes} минут"
        else:
            interval_text = f"{interval_min} минут"
        
        await update.message.reply_text(
            f"✅ Интервал оповещений обновлён!\n"
            f"📊 Каждые {interval_text}"
        )
        logger.info("Пользователь %s установил интервал: %s минут", user.id, interval_min)
        
    except ValueError:
        await update.message.reply_text("❌ Нужно указать число!")
    except Exception as exc:
        logger.error("Ошибка обновления интервала для %s: %s", user.id, exc)
        await update.message.reply_text("❌ Ошибка при обновлении интервала.")

async def history_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Open history page in Telegram Web App."""
    user = update.effective_user
    if user is None:
        return
    
    # Ensure user exists
    await ensure_user_exists(
        tg_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name
    )
    
    # Web App URL for Vercel deployment
    web_app_url = "https://doyobi-diary.vercel.app/history"
    
    keyboard = [[InlineKeyboardButton(
        "📊 Открыть историю активностей", 
        web_app=WebAppInfo(url=web_app_url)
    )]]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🔍 **Просмотр истории активностей**\n\n"
        "Нажмите кнопку ниже, чтобы открыть веб-интерфейс с вашей полной историей ответов. "
        "Вы сможете:\n"
        "• 📅 Фильтровать по датам\n"
        "• 🔍 Искать по тексту\n"
        "• 📊 Просматривать статистику\n"
        "• 📈 Анализировать активность",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    
    logger.info("Пользователь %s открыл историю активностей", user.id)

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
    application.add_handler(CommandHandler("notify_on", notify_on_command))
    application.add_handler(CommandHandler("notify_off", notify_off_command))
    application.add_handler(CommandHandler("window", window_command))
    application.add_handler(CommandHandler("freq", freq_command))
    application.add_handler(CommandHandler("history", history_command))
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
