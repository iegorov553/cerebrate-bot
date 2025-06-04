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
QUESTION: str = "Чё делаешь? 🤔"

if not (BOT_TOKEN and SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY):
    logger.error("Не заданы обязательные переменные среды. Завершаюсь.")
    raise SystemExit(1)

# --- Supabase ---
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

# --- Database functions ---
async def find_user_by_username(username: str) -> dict:
    """Find user by username in database."""
    try:
        # Remove @ if present
        clean_username = username.lstrip('@')
        result = supabase.table("users").select("*").eq("tg_username", clean_username).execute()
        return result.data[0] if result.data else None
    except Exception as exc:
        logger.error("Ошибка поиска пользователя %s: %s", username, exc)
        return None

async def create_friend_request(requester_id: int, addressee_id: int) -> bool:
    """Create a friend request."""
    try:
        # Check if friendship already exists in either direction
        existing1 = supabase.table("friendships").select("*").eq(
            "requester_id", requester_id
        ).eq(
            "addressee_id", addressee_id
        ).execute()
        existing2 = supabase.table("friendships").select("*").eq(
            "requester_id", addressee_id
        ).eq(
            "addressee_id", requester_id
        ).execute()

        if (existing1.data or existing2.data):
            return False  # Already exists
        
        # Create new friend request
        supabase.table("friendships").insert({
            "requester_id": requester_id,
            "addressee_id": addressee_id,
            "status": "pending"
        }).execute()
        
        return True
    except Exception as exc:
        logger.error("Ошибка создания запроса в друзья: %s", exc)
        return False

async def get_friend_requests(user_id: int) -> dict:
    """Get incoming and outgoing friend requests."""
    try:
        # Incoming requests
        incoming = supabase.table("friendships").select(
            "*, requester:users!friendships_requester_id_fkey(tg_username, tg_first_name)"
        ).eq("addressee_id", user_id).eq("status", "pending").execute()
        
        # Outgoing requests
        outgoing = supabase.table("friendships").select(
            "*, addressee:users!friendships_addressee_id_fkey(tg_username, tg_first_name)"
        ).eq("requester_id", user_id).eq("status", "pending").execute()
        
        return {
            "incoming": incoming.data or [],
            "outgoing": outgoing.data or []
        }
    except Exception as exc:
        logger.error("Ошибка получения запросов в друзья: %s", exc)
        return {"incoming": [], "outgoing": []}

async def update_friend_request(friendship_id: str, status: str) -> bool:
    """Accept or decline a friend request."""
    try:
        supabase.table("friendships").update({
            "status": status
        }).eq("friendship_id", friendship_id).execute()
        return True
    except Exception as exc:
        logger.error("Ошибка обновления запроса в друзья: %s", exc)
        return False

async def get_friends_list(user_id: int) -> list:
    """Get list of user's friends."""
    try:
        # Get accepted friendships where user is either requester or addressee
        result_requester = supabase.table("friendships").select(
            "*, requester:users!friendships_requester_id_fkey(tg_id, tg_username, tg_first_name), "
            "addressee:users!friendships_addressee_id_fkey(tg_id, tg_username, tg_first_name)"
        ).eq("status", "accepted").eq("requester_id", user_id).execute()

        result_addressee = supabase.table("friendships").select(
            "*, requester:users!friendships_requester_id_fkey(tg_id, tg_username, tg_first_name), "
            "addressee:users!friendships_addressee_id_fkey(tg_id, tg_username, tg_first_name)"
        ).eq("status", "accepted").eq("addressee_id", user_id).execute()

        result_data = (result_requester.data or []) + (result_addressee.data or [])

        friends = []
        for friendship in result_data:
            # Add the friend (not the current user)
            if friendship['requester_id'] == user_id:
                friends.append(friendship['addressee'])
            else:
                friends.append(friendship['requester'])
        
        return friends
    except Exception as exc:
        logger.error("Ошибка получения списка друзей: %s", exc)
        return []
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

    message = update.effective_message
    if message is None:
        return

    message = update.effective_message
    if message is None:
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
            "tg_id": user.id,
            "jobs_timestamp": timestamp,
            "job_text": text
        }
        supabase.table("tg_jobs").insert(data).execute()
        logger.info("Записан ответ от %s", user.id)
        
        # Send confirmation message
        await message.reply_text("Понял, принял! 👍")
        
    except Exception as exc:
        logger.error("Ошибка записи в Supabase: %s", exc)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command - register user and send first question."""
    user = update.effective_user
    if user is None:
        return

    message = update.effective_message
    if message is None:
        return

    # Ensure user exists in database
    user_data = await ensure_user_exists(
        tg_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name
    )

    if not user_data:
        await message.reply_text("❌ Ошибка регистрации пользователя.")
        return

    # Welcome message
    welcome_text = f"""🤖 **Привет, {user.first_name or user.username or 'друг'}!**

Я бот, который поможет тебе отслеживать твою активность! 📊

🕐 Буду спрашивать что ты делаешь в рабочее время
⚙️ Можешь настроить время и частоту через /settings
📱 Смотри историю через /history

Давай начнём прямо сейчас! 🚀"""

    await message.reply_text(welcome_text, parse_mode='Markdown')
    
    # Send first question immediately
    await asyncio.sleep(1)  # Small delay for better UX
    await message.reply_text(QUESTION, reply_markup=ForceReply())
    
    logger.info("Новый пользователь зарегистрирован: %s", user.id)

async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show user settings from database."""
    user = update.effective_user
    if user is None:
        return

    message = update.effective_message
    if message is None:
        return

    # Ensure user exists
    user_data = await ensure_user_exists(
        tg_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name
    )

    if not user_data:
        await message.reply_text("Ошибка получения настроек.")
        return

    settings_text = f"""🔧 **Ваши настройки:**

✅ Статус: {'Включен' if user_data['enabled'] else 'Отключен'}
⏰ Время работы: {user_data['window_start'][:5]} - {user_data['window_end'][:5]}
📊 Интервал: {user_data['interval_min']} минут
👤 Telegram ID: {user_data['tg_id']}
📅 Регистрация: {user_data['created_at'][:10]}"""

    await message.reply_text(settings_text, parse_mode='Markdown')

async def notify_on_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Enable notifications for user."""
    user = update.effective_user
    if user is None:
        return

    message = update.effective_message
    if message is None:
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
        await message.reply_text("✅ Оповещения включены!")
        logger.info("Пользователь %s включил оповещения", user.id)
    except Exception as exc:
        logger.error("Ошибка включения оповещений для %s: %s", user.id, exc)
        await message.reply_text("❌ Ошибка при включении оповещений.")

async def notify_off_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Disable notifications for user."""
    user = update.effective_user
    if user is None:
        return

    message = update.effective_message
    if message is None:
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
        await message.reply_text("❌ Оповещения отключены.")
        logger.info("Пользователь %s отключил оповещения", user.id)
    except Exception as exc:
        logger.error("Ошибка отключения оповещений для %s: %s", user.id, exc)
        await message.reply_text("❌ Ошибка при отключении оповещений.")

async def window_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Set user time window for notifications. Format: /window HH:MM-HH:MM"""
    user = update.effective_user
    if user is None:
        return
    message = update.effective_message
    if message is None:
        return

    if not context.args or len(context.args) != 1:
        await message.reply_text(
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
        await message.reply_text(
            "❌ Неправильный формат времени!\n"
            "Пример: `/window 09:00-23:00`",
            parse_mode='Markdown'
        )
        return
    
    start_hour, start_min, end_hour, end_min = map(int, match.groups())
    
    # Validate time values
    if start_hour > 23 or end_hour > 23:
        await message.reply_text("❌ Часы должны быть от 00 до 23!")
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
        await message.reply_text("❌ Минимальный интервал - 1 час!")
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
        
        await message.reply_text(
            f"✅ Время оповещений обновлено!\n"
            f"⏰ {start_time.strftime('%H:%M')} - {end_time.strftime('%H:%M')}"
        )
        logger.info("Пользователь %s установил время: %s-%s", user.id, start_time, end_time)
    
    except Exception as exc:
        logger.error("Ошибка обновления времени для %s: %s", user.id, exc)
        await message.reply_text("❌ Ошибка при обновлении времени.")

async def freq_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Set user notification frequency in minutes. Format: /freq N"""
    user = update.effective_user
    if user is None:
        return

    if not context.args or len(context.args) != 1:
        await message.reply_text(
            "❌ Неправильный формат!\n"
            "Пример: `/freq 60` (для 60 минут)",
            parse_mode='Markdown'
        )
        return

    try:
        interval_min = int(context.args[0])
        
        # Validate interval (minimum 5 minutes, maximum 24 hours)
        if interval_min < 5:
            await message.reply_text("❌ Минимальный интервал - 5 минут!")
            return
        
        if interval_min > 1440:  # 24 hours
            await message.reply_text("❌ Максимальный интервал - 1440 минут (24 часа)!")
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
        
        await message.reply_text(
            f"✅ Интервал оповещений обновлён!\n"
            f"📊 Каждые {interval_text}"
        )
        logger.info("Пользователь %s установил интервал: %s минут", user.id, interval_min)
        
    except ValueError:
        await message.reply_text("❌ Нужно указать число!")
    except Exception as exc:
        logger.error("Ошибка обновления интервала для %s: %s", user.id, exc)
        await message.reply_text("❌ Ошибка при обновлении интервала.")

async def history_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Open history page in Telegram Web App."""
    user = update.effective_user
    if user is None:
        return
    message = update.effective_message
    if message is None:
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
    
    await message.reply_text(
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

async def add_friend_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Add a friend by username. Format: /add_friend @username"""
    user = update.effective_user
    if user is None:
        return
    message = update.effective_message
    if message is None:
        return

    if not context.args or len(context.args) != 1:
        await message.reply_text(
            "❌ Неправильный формат!\n"
            "Пример: `/add_friend @username`",
            parse_mode='Markdown'
        )
        return
    
    username = context.args[0]
    
    # Ensure current user exists
    await ensure_user_exists(
        tg_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name
    )
    
    # Find the target user
    target_user = await find_user_by_username(username)
    if not target_user:
        await message.reply_text(
            f"❌ Пользователь {username} не найден!\n"
            "Убедитесь, что он уже использовал бота."
        )
        return
    
    # Check if trying to add themselves
    if target_user['tg_id'] == user.id:
        await message.reply_text("❌ Нельзя добавить себя в друзья! 😄")
        return
    
    # Create friend request
    success = await create_friend_request(user.id, target_user['tg_id'])
    
    if success:
        # Try to notify the target user
        try:
            await context.bot.send_message(
                chat_id=target_user['tg_id'],
                text=f"🤝 У вас новый запрос в друзья от @{user.username or user.first_name}!\n"
                     f"Используйте /friend_requests чтобы принять или отклонить."
            )
        except Exception:
            pass  # User might have blocked the bot
        
        await message.reply_text(
            f"✅ Запрос в друзья отправлен пользователю {username}!"
        )
        logger.info("Пользователь %s отправил запрос в друзья %s", user.id, target_user['tg_id'])
    else:
        await message.reply_text(
            f"❌ Не удалось отправить запрос!\n"
            f"Возможно, вы уже друзья или запрос уже существует."
        )

async def friend_requests_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show incoming and outgoing friend requests."""
    user = update.effective_user
    if user is None:
        return
    message = update.effective_message
    if message is None:
        return
    
    # Ensure user exists
    await ensure_user_exists(
        tg_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name
    )
    
    requests = await get_friend_requests(user.id)
    
    # Build response message
    message_parts = ["🤝 **Запросы в друзья:**\n"]
    
    # Incoming requests
    if requests['incoming']:
        message_parts.append("📥 **Входящие запросы:**")
        for req in requests['incoming']:
            requester_name = req['requester']['tg_username'] or req['requester']['tg_first_name']
            message_parts.append(f"• @{requester_name} - `/accept {req['friendship_id'][:8]}` | `/decline {req['friendship_id'][:8]}`")
        message_parts.append("")
    
    # Outgoing requests
    if requests['outgoing']:
        message_parts.append("📤 **Исходящие запросы:**")
        for req in requests['outgoing']:
            addressee_name = req['addressee']['tg_username'] or req['addressee']['tg_first_name']
            message_parts.append(f"• @{addressee_name} (ожидает ответа)")
        message_parts.append("")
    
    if not requests['incoming'] and not requests['outgoing']:
        message_parts.append("📭 Нет активных запросов в друзья.")
    
    await message.reply_text(
        "\n".join(message_parts),
        parse_mode='Markdown'
    )

async def accept_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Accept a friend request. Format: /accept [request_id]"""
    user = update.effective_user
    if user is None:
        return
    message = update.effective_message
    if message is None:
        return

    if not context.args or len(context.args) != 1:
        await message.reply_text(
            "❌ Неправильный формат!\n"
            "Пример: `/accept 12345678`"
        )
        return
    
    request_id_short = context.args[0]
    
    # Find full friendship_id by partial match
    try:
        result = supabase.table("friendships").select("*").eq(
            "addressee_id", user.id
        ).eq("status", "pending").execute()
        
        matching_request = None
        for req in result.data or []:
            if req['friendship_id'].startswith(request_id_short):
                matching_request = req
                break
        
        if not matching_request:
            await message.reply_text("❌ Запрос не найден!")
            return
        
        # Accept the request
        success = await update_friend_request(matching_request['friendship_id'], "accepted")
        
        if success:
            # Get requester info
            requester = supabase.table("users").select("*").eq(
                "tg_id", matching_request['requester_id']
            ).execute()
            
            if requester.data:
                requester_name = requester.data[0]['tg_username'] or requester.data[0]['tg_first_name']
                
                # Notify the requester
                try:
                    await context.bot.send_message(
                        chat_id=matching_request['requester_id'],
                        text=f"🎉 @{user.username or user.first_name} принял ваш запрос в друзья!\n"
                             f"Теперь вы можете смотреть активности друг друга через /activities"
                    )
                except Exception:
                    pass
                
                await message.reply_text(
                    f"✅ Вы теперь друзья с @{requester_name}! 🎉"
                )
                logger.info("Пользователь %s принял запрос от %s", user.id, matching_request['requester_id'])
            else:
                await message.reply_text("✅ Запрос принят!")
        else:
            await message.reply_text("❌ Ошибка при принятии запроса.")
            
    except Exception as exc:
        logger.error("Ошибка при принятии запроса: %s", exc)
        await message.reply_text("❌ Ошибка при принятии запроса.")

async def decline_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Decline a friend request. Format: /decline [request_id]"""
    user = update.effective_user
    if user is None:
        return
    message = update.effective_message
    if message is None:
        return

    if not context.args or len(context.args) != 1:
        await message.reply_text(
            "❌ Неправильный формат!\n"
            "Пример: `/decline 12345678`"
        )
        return
    
    request_id_short = context.args[0]
    
    # Find and delete the request
    try:
        result = supabase.table("friendships").select("*").eq(
            "addressee_id", user.id
        ).eq("status", "pending").execute()
        
        matching_request = None
        for req in result.data or []:
            if req['friendship_id'].startswith(request_id_short):
                matching_request = req
                break
        
        if not matching_request:
            await message.reply_text("❌ Запрос не найден!")
            return
        
        # Delete the request
        supabase.table("friendships").delete().eq(
            "friendship_id", matching_request['friendship_id']
        ).execute()
        
        await message.reply_text("❌ Запрос отклонён.")
        logger.info("Пользователь %s отклонил запрос от %s", user.id, matching_request['requester_id'])
            
    except Exception as exc:
        logger.error("Ошибка при отклонении запроса: %s", exc)
        await message.reply_text("❌ Ошибка при отклонении запроса.")

async def friends_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show list of friends."""
    user = update.effective_user
    if user is None:
        return
    message = update.effective_message
    if message is None:
        return
    
    # Ensure user exists
    await ensure_user_exists(
        tg_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name
    )
    
    friends = await get_friends_list(user.id)
    
    if not friends:
        await message.reply_text(
            "👥 У вас пока нет друзей.\n\n"
            "Используйте `/add_friend @username` чтобы добавить друзей!",
            parse_mode='Markdown'
        )
        return
    
    message_parts = ["👥 **Ваши друзья:**\n"]
    
    for friend in friends:
        friend_name = friend['tg_username'] or friend['tg_first_name']
        message_parts.append(f"• @{friend_name}")
    
    message_parts.extend([
        "",
        f"Всего друзей: {len(friends)}",
        "",
        "Используйте `/activities @username` чтобы посмотреть активности друга!"
    ])
    
    await message.reply_text(
        "\n".join(message_parts),
        parse_mode='Markdown'
    )

async def activities_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show activities of self or a friend. Format: /activities [@username]"""
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
    
    # If no username provided, show own activities via web interface
    if not context.args:
        # Redirect to history command for own activities
        await history_command(update, context)
        return
    
    target_username = context.args[0]
    
    # Find target user
    target_user = await find_user_by_username(target_username)
    if not target_user:
        await message.reply_text(
            f"❌ Пользователь {target_username} не найден!\n"
            "Убедитесь, что он уже использовал бота."
        )
        return
    
    # Check if they are friends
    friends = await get_friends_list(user.id)
    is_friend = any(friend['tg_id'] == target_user['tg_id'] for friend in friends)
    
    if not is_friend and target_user['tg_id'] != user.id:
        await message.reply_text(
            f"🔒 Вы не можете просматривать активности @{target_username}.\n"
            f"Сначала добавьте в друзья: `/add_friend {target_username}`",
            parse_mode='Markdown'
        )
        return
    
    # Get recent activities
    try:
        # Get last 10 activities from the last week
        from datetime import datetime, timedelta
        week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d %H:%M:%S')
        
        result = supabase.table("tg_jobs").select("*").eq(
            "tg_id", target_user['tg_id']
        ).gte(
            "jobs_timestamp", week_ago
        ).order(
            "jobs_timestamp", desc=True
        ).limit(10).execute()
        
        activities = result.data or []
        
        if not activities:
            target_name = target_user['tg_username'] or target_user['tg_first_name']
            await message.reply_text(
                f"📝 У @{target_name} нет активностей за последнюю неделю."
            )
            return
        
        # Format response
        target_name = target_user['tg_username'] or target_user['tg_first_name']
        message_parts = [f"📊 **Активности @{target_name} (последние 10):**\n"]
        
        for activity in activities:
            # Format timestamp
            timestamp = datetime.fromisoformat(activity['jobs_timestamp'].replace('Z', '+00:00'))
            formatted_time = timestamp.strftime('%d.%m %H:%M')
            
            # Truncate long messages
            text = activity['job_text']
            if len(text) > 100:
                text = text[:97] + "..."
            
            message_parts.append(f"• {formatted_time}: {text}")
        
        message_parts.extend([
            "",
            f"Всего записей за неделю: {len(activities)}",
            "",
            "🌐 Полная история доступна через /history в веб-интерфейсе"
        ])
        
        await message.reply_text(
            "\n".join(message_parts),
            parse_mode='Markdown'
        )
        
        logger.info("Пользователь %s просмотрел активности %s", user.id, target_user['tg_id'])
        
    except Exception as exc:
        logger.error("Ошибка получения активностей: %s", exc)
        await message.reply_text("❌ Ошибка при получении активностей.")

def run_coro_in_loop(coro):
    loop = asyncio.get_event_loop()
    if loop.is_running():
        loop.create_task(coro)
    else:
        loop.run_until_complete(coro)

async def main() -> None:
    application: Application = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("settings", settings_command))
    application.add_handler(CommandHandler("notify_on", notify_on_command))
    application.add_handler(CommandHandler("notify_off", notify_off_command))
    application.add_handler(CommandHandler("window", window_command))
    application.add_handler(CommandHandler("freq", freq_command))
    application.add_handler(CommandHandler("history", history_command))
    application.add_handler(CommandHandler("add_friend", add_friend_command))
    application.add_handler(CommandHandler("friend_requests", friend_requests_command))
    application.add_handler(CommandHandler("accept", accept_command))
    application.add_handler(CommandHandler("decline", decline_command))
    application.add_handler(CommandHandler("friends", friends_command))
    application.add_handler(CommandHandler("activities", activities_command))
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
