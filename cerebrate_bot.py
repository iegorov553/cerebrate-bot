"""
Телеграм-бот «Часовой».
Каждый час задаёт вопрос двум указанным аккаунтам и заносит их ответы в Google-таблицу.

Перед запуском необходимо:
1. Создать сервисный аккаунт в Google Cloud, дать ему доступ «Редактор» к нужной Google-таблице,
   скачать credentials.json и указать путь к ней в переменной окружения GOOGLE_APPLICATION_CREDENTIALS.
2. Установить зависимости:
   pip install python-telegram-bot==20.3 gspread oauth2client APScheduler python-dotenv
3. Заполнить переменные среды TELEGRAM_BOT_TOKEN, TARGET_USER_IDS, SPREADSHEET_ID.
   TARGET_USER_IDS — запятая-разделённый список двух user_id.
   Пример: TARGET_USER_IDS="123456789,987654321"
4. (Опционально) Отредактировать текст QUESTION.
"""
from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone

import gspread
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from gspread import Client as GspreadClient
from oauth2client.service_account import ServiceAccountCredentials
from telegram import ForceReply, Update
from telegram.ext import (Application, ApplicationBuilder, ContextTypes,
                          MessageHandler, filters)
from dotenv import load_dotenv

# Загружаем переменные среды из .env
load_dotenv()

logging.basicConfig(
    format="%(asctime)s | %(levelname)8s | %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# === Конфигурация ===
BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
SPREADSHEET_ID: str = os.getenv("SPREADSHEET_ID", "")
QUESTION: str = "Что ты сейчас делаешь?"

# Список целевых chat_id (int). Берём из переменной среды, разделитель — запятая.
raw_ids = os.getenv("TARGET_USER_IDS", "").split(",")
TARGET_USER_IDS: list[int] = [int(x.strip()) for x in raw_ids if x.strip()]

if not (BOT_TOKEN and SPREADSHEET_ID and TARGET_USER_IDS):
    logger.error("Не заданы обязательные переменные среды. Завершаюсь.")
    raise SystemExit(1)

# === Google Sheets ===
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
worksheet = gs_client.open_by_key(SPREADSHEET_ID).sheet1  # первая вкладка

# === Telegram callbacks ===
async def ask_question(app: Application) -> None:
    """Послать вопрос всем целевым пользователям."""
    for chat_id in TARGET_USER_IDS:
        try:
            await app.bot.send_message(chat_id=chat_id, text=QUESTION, reply_markup=ForceReply())
            logger.info("Отправлен вопрос пользователю %s", chat_id)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Не удалось отправить сообщение %s: %s", chat_id, exc)

async def handle_reply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработать любой ответ от целевых пользователей."""
    user = update.effective_user
    if user is None or update.effective_chat.id not in TARGET_USER_IDS:
        return  # игнорируем чужие сообщения

    text = update.effective_message.text or "<без текста>"
    timestamp = datetime.now(timezone.utc).isoformat()

    # Добавляем строку в таблицу
    try:
        worksheet.append_row([user.username or user.full_name, timestamp, text])
        logger.info("Записан ответ от %s", user.id)
    except Exception as exc:  # noqa: BLE001
        logger.error("Ошибка записи в Google Sheets: %s", exc)

# Вспомогательный обработчик — для вывода chat_id (можешь удалить после использования)
async def debug(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"chat_id: {update.effective_user.id}")

async def main() -> None:
    application: Application = ApplicationBuilder().token(BOT_TOKEN).build()

    # Обработчики сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_reply))
    # Чтобы узнать chat_id пользователя — можешь временно подключить debug:
    # application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, debug))

    # Планировщик
    scheduler = AsyncIOScheduler()
    scheduler.add_job(lambda: asyncio.create_task(ask_question(application)), "interval", hours=1)
    scheduler.start()

    logger.info("Бот запущен. Жду сигнала...")
    await application.run_polling()

if __name__ == "__main__":
    import sys
    if sys.platform.startswith("win") and sys.version_info >= (3, 8):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Остановлено вручную.")
