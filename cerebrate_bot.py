"""
Telegram-bot 'Hour Watcher': asks two accounts every hour and writes replies to Google Sheets.

Для Railway, Render, VPS, любой среды где переменные окружения задаются через UI:
- TELEGRAM_BOT_TOKEN
- TARGET_USER_IDS
- SPREADSHEET_ID
- CREDS_B64 (Google service account creds.json, base64-encoded)
"""

from __future__ import annotations

import asyncio
import logging
import os
import base64
import tempfile
from datetime import datetime, timezone

import gspread
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from gspread import Client as GspreadClient
from oauth2client.service_account import ServiceAccountCredentials
from telegram import ForceReply, Update
from telegram.ext import (
    Application,
    ApplicationBuilder,
    ContextTypes,
    MessageHandler,
    filters,
)

# --- Google credentials from base64 env variable ---
if "CREDS_B64" in os.environ:
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
    tmp.write(base64.b64decode(os.environ["CREDS_B64"]))
    tmp.close()
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = tmp.name

# --- Logging ---
logging.basicConfig(
    format="%(asctime)s | %(levelname)8s | %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# --- Config ---
BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
SPREADSHEET_ID: str = os.getenv("SPREADSHEET_ID", "")
QUESTION: str = "Что ты сейчас делаешь?"

raw_ids = os.getenv("TARGET_USER_IDS", "").split(",")
TARGET_USER_IDS: list[int] = [int(x.strip()) for x in raw_ids if x.strip()]

if not (BOT_TOKEN and SPREADSHEET_ID and TARGET_USER_IDS):
    logger.error("Не заданы обязательные переменные среды. Завершаюсь.")
    raise SystemExit(1)

# --- Google Sheets ---
_SCOPE = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
]

def _get_gspread_client() -> GspreadClient:
    creds = ServiceAccountCredentials.from_json_keyfile_name(
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"], _SCOPE
    )
    return gspread.authorize(creds)

gs_client = _get_gspread_client()
worksheet = gs_client.open_by_key(SPREADSHEET_ID).sheet1

# --- Telegram callbacks ---
async def ask_question(app: Application) -> None:
    """Ask the question to all target users."""
    for chat_id in TARGET_USER_IDS:
        try:
            await app.bot.send_message(chat_id=chat_id, text=QUESTION, reply_markup=ForceReply())
            logger.info("Отправлен вопрос пользователю %s", chat_id)
        except Exception as exc:
            logger.warning("Не удалось отправить сообщение %s: %s", chat_id, exc)

async def handle_reply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if user is None or update.effective_chat.id not in TARGET_USER_IDS:
        return

    text = update.effective_message.text or "<без текста>"
    timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')  # <--- исправлен формат!

    try:
        worksheet.append_row([user.username or user.full_name, timestamp, text])
        logger.info("Записан ответ от %s", user.id)
    except Exception as exc:
        logger.error("Ошибка записи в Google Sheets: %s", exc)

def run_coro_in_loop(coro):
    loop = asyncio.get_event_loop()
    if loop.is_running():
        loop.create_task(coro)
    else:
        loop.run_until_complete(coro)

async def main() -> None:
    application: Application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_reply))
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        lambda: run_coro_in_loop(ask_question(application)),
        "cron",
        hour="10-23"
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
