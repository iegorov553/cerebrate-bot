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
    CallbackQueryHandler,
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

# Безопасная обработка ADMIN_USER_ID
try:
    ADMIN_USER_ID: int = int(os.getenv("ADMIN_USER_ID", "0"))
except (ValueError, TypeError):
    ADMIN_USER_ID: int = 0
    logger.warning("ADMIN_USER_ID не задан или некорректен, админ функции отключены")

QUESTION: str = "Чё делаешь? 🤔"

if not (BOT_TOKEN and SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY):
    logger.error("Не заданы обязательные переменные среды. Завершаюсь.")
    raise SystemExit(1)

# --- Supabase ---
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

# --- Cache Manager ---
class CacheManager:
    """Простой менеджер кеша с поддержкой TTL."""
    
    def __init__(self):
        self._cache = {}
        self._cache_timeout = {}
    
    def get(self, key: str, default=None):
        """Получить значение из кеша."""
        if key in self._cache:
            if datetime.now() < self._cache_timeout[key]:
                return self._cache[key]
            else:
                # Кеш истек, удаляем
                del self._cache[key]
                del self._cache_timeout[key]
        return default
    
    def set(self, key: str, value, timeout_seconds: int = 300):
        """Сохранить значение в кеш с TTL."""
        from datetime import timedelta
        self._cache[key] = value
        self._cache_timeout[key] = datetime.now() + timedelta(seconds=timeout_seconds)
    
    def invalidate(self, key: str):
        """Принудительно удалить значение из кеша."""
        if key in self._cache:
            del self._cache[key]
        if key in self._cache_timeout:
            del self._cache_timeout[key]
    
    def clear(self):
        """Очистить весь кеш."""
        self._cache.clear()
        self._cache_timeout.clear()

# Глобальный экземпляр кеша
cache = CacheManager()

# --- Utility functions ---
def safe_parse_datetime(dt_string: str) -> datetime:
    """Безопасный парсинг datetime строки."""
    try:
        if dt_string:
            return datetime.fromisoformat(dt_string.replace('Z', '+00:00'))
        return None
    except (ValueError, AttributeError, TypeError):
        logger.warning("Не удалось распарсить дату: %s", dt_string)
        return None

def validate_time_window(time_range: str) -> tuple[bool, str, time, time]:
    """Улучшенная валидация временного окна."""
    pattern = r'^([0-2][0-9]):([0-5][0-9])-([0-2][0-9]):([0-5][0-9])$'
    match = re.match(pattern, time_range)
    
    if not match:
        return False, "Неправильный формат! Используйте HH:MM-HH:MM", None, None
    
    start_hour, start_min, end_hour, end_min = map(int, match.groups())
    
    if start_hour > 23 or end_hour > 23:
        return False, "Часы должны быть от 00 до 23!", None, None
    
    start_time = time(start_hour, start_min)
    end_time = time(end_hour, end_min)
    
    # Обработка перехода через полночь (не поддерживается в текущей версии)
    if start_time >= end_time:
        return False, "Время окончания должно быть позже времени начала!", None, None
    
    # Минимум 1 час
    start_minutes = start_hour * 60 + start_min  
    end_minutes = end_hour * 60 + end_min
    
    if end_minutes - start_minutes < 60:
        return False, "Минимальная продолжительность - 1 час!", None, None
    
    return True, "OK", start_time, end_time

async def get_user_settings_cached(user_id: int, force_refresh: bool = False) -> dict:
    """Получить настройки пользователя с кешированием."""
    cache_key = f"user_settings_{user_id}"
    
    if not force_refresh:
        settings = cache.get(cache_key)
        if settings is not None:
            return settings
    
    # Загружаем из базы данных
    try:
        result = supabase.table("users").select("*").eq("tg_id", user_id).execute()
        settings = result.data[0] if result.data else None
        
        if settings:
            # Кешируем на 5 минут
            cache.set(cache_key, settings, 300)
            logger.debug("Настройки пользователя %s загружены и закешированы", user_id)
        
        return settings
        
    except Exception as exc:
        logger.error("Ошибка получения настроек пользователя %s: %s", user_id, exc)
        return None

def invalidate_user_cache(user_id: int):
    """Очистить кеш настроек пользователя."""
    cache_key = f"user_settings_{user_id}"
    cache.invalidate(cache_key)
    logger.debug("Кеш пользователя %s очищен", user_id)

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
        # Incoming requests (simple query)
        incoming_result = supabase.table("friendships").select(
            "friendship_id, requester_id, addressee_id, status, created_at"
        ).eq("addressee_id", user_id).eq("status", "pending").execute()
        
        # Outgoing requests (simple query)
        outgoing_result = supabase.table("friendships").select(
            "friendship_id, requester_id, addressee_id, status, created_at"
        ).eq("requester_id", user_id).eq("status", "pending").execute()
        
        # Get user info for incoming requests
        incoming = []
        for req in incoming_result.data or []:
            user_info = supabase.table("users").select(
                "tg_username, tg_first_name"
            ).eq("tg_id", req['requester_id']).execute()
            
            if user_info.data:
                req['requester'] = user_info.data[0]
            else:
                req['requester'] = {'tg_username': None, 'tg_first_name': 'Unknown'}
            incoming.append(req)
        
        # Get user info for outgoing requests
        outgoing = []
        for req in outgoing_result.data or []:
            user_info = supabase.table("users").select(
                "tg_username, tg_first_name"
            ).eq("tg_id", req['addressee_id']).execute()
            
            if user_info.data:
                req['addressee'] = user_info.data[0]
            else:
                req['addressee'] = {'tg_username': None, 'tg_first_name': 'Unknown'}
            outgoing.append(req)
        
        return {
            "incoming": incoming,
            "outgoing": outgoing
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
            "requester_id, addressee_id"
        ).eq("status", "accepted").eq("requester_id", user_id).execute()

        result_addressee = supabase.table("friendships").select(
            "requester_id, addressee_id"
        ).eq("status", "accepted").eq("addressee_id", user_id).execute()

        # Collect friend IDs
        friend_ids = []
        for friendship in result_requester.data or []:
            friend_ids.append(friendship['addressee_id'])
        
        for friendship in result_addressee.data or []:
            friend_ids.append(friendship['requester_id'])

        # Get user info for each friend
        friends = []
        for friend_id in friend_ids:
            user_info = supabase.table("users").select(
                "tg_id, tg_username, tg_first_name"
            ).eq("tg_id", friend_id).execute()
            
            if user_info.data:
                friends.append(user_info.data[0])
        
        return friends
    except Exception as exc:
        logger.error("Ошибка получения списка друзей: %s", exc)
        return []

async def get_friends_of_friends(user_id: int) -> list:
    """Оптимизированная функция поиска друзей друзей."""
    try:
        # Получаем всех друзей пользователя одним запросом
        current_friend_ids = []
        
        # Друзья где user_id - requester
        result1 = supabase.table("friendships").select(
            "addressee_id"
        ).eq("requester_id", user_id).eq("status", "accepted").execute()
        
        # Друзья где user_id - addressee  
        result2 = supabase.table("friendships").select(
            "requester_id"
        ).eq("addressee_id", user_id).eq("status", "accepted").execute()
        
        for friendship in result1.data or []:
            current_friend_ids.append(friendship['addressee_id'])
        for friendship in result2.data or []:
            current_friend_ids.append(friendship['requester_id'])
        
        if not current_friend_ids:
            return []
        
        exclude_ids = current_friend_ids + [user_id]
        
        # Получаем всех друзей всех друзей одним большим запросом
        # Используем .in_() для эффективного запроса
        all_friendships = supabase.table("friendships").select(
            "requester_id, addressee_id"
        ).eq("status", "accepted").or_(
            f"requester_id.in.({','.join(map(str, current_friend_ids))}),addressee_id.in.({','.join(map(str, current_friend_ids))})"
        ).execute()
        
        # Собираем рекомендации и взаимных друзей
        recommendations = {}
        
        for friendship in all_friendships.data or []:
            requester_id = friendship['requester_id']
            addressee_id = friendship['addressee_id']
            
            # Определяем кто из них друг пользователя, а кто потенциальная рекомендация
            if requester_id in current_friend_ids and addressee_id not in exclude_ids:
                # addressee_id - рекомендация, requester_id - взаимный друг
                candidate_id = addressee_id
                mutual_friend_id = requester_id
            elif addressee_id in current_friend_ids and requester_id not in exclude_ids:
                # requester_id - рекомендация, addressee_id - взаимный друг
                candidate_id = requester_id
                mutual_friend_id = addressee_id
            else:
                continue
            
            # Добавляем в рекомендации
            if candidate_id not in recommendations:
                recommendations[candidate_id] = set()
            recommendations[candidate_id].add(mutual_friend_id)
        
        if not recommendations:
            return []
        
        # Получаем информацию о пользователях одним запросом
        all_user_ids = list(recommendations.keys()) + current_friend_ids
        users_info = supabase.table("users").select(
            "tg_id, tg_username, tg_first_name"
        ).in_("tg_id", all_user_ids).execute()
        
        # Создаем карту пользователей для быстрого доступа
        users_map = {user['tg_id']: user for user in users_info.data or []}
        
        # Формируем финальный результат
        result = []
        for candidate_id, mutual_friend_ids in recommendations.items():
            candidate_info = users_map.get(candidate_id)
            if not candidate_info:
                continue
            
            # Получаем имена взаимных друзей
            mutual_friends = []
            for mutual_id in mutual_friend_ids:
                mutual_user = users_map.get(mutual_id)
                if mutual_user:
                    mutual_name = mutual_user['tg_username'] or mutual_user['tg_first_name'] or f"ID{mutual_id}"
                    mutual_friends.append(mutual_name)
            
            result.append({
                'user_info': candidate_info,
                'mutual_friends': mutual_friends,
                'mutual_count': len(mutual_friends)
            })
        
        # Сортируем по количеству взаимных друзей (убывание), затем по имени
        result.sort(key=lambda x: (
            -x['mutual_count'], 
            (x['user_info']['tg_username'] or x['user_info']['tg_first_name'] or 'zzz_unknown').lower()
        ))
        
        # Ограничиваем до 10 рекомендаций
        return result[:10]
        
    except Exception as exc:
        logger.error("Ошибка получения рекомендаций друзей: %s", exc)
        return []

# --- Admin functions ---
def is_admin(user_id: int) -> bool:
    """Check if user is admin."""
    return ADMIN_USER_ID != 0 and user_id == ADMIN_USER_ID

async def get_user_stats() -> dict:
    """Get user statistics for admin panel."""
    try:
        # Total users
        total_result = supabase.table("users").select("tg_id", count="exact").execute()
        total_users = total_result.count
        
        # Active users (enabled=true)
        active_result = supabase.table("users").select("tg_id", count="exact").eq("enabled", True).execute()
        active_users = active_result.count
        
        # New users in last 7 days
        from datetime import datetime, timedelta
        week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        new_result = supabase.table("users").select("tg_id", count="exact").gte("created_at", week_ago).execute()
        new_users = new_result.count
        
        return {
            "total": total_users,
            "active": active_users,
            "new_week": new_users
        }
    except Exception as exc:
        logger.error("Ошибка получения статистики пользователей: %s", exc)
        return {"total": 0, "active": 0, "new_week": 0}

async def send_single_message(app: Application, user_id: int, message_text: str) -> bool:
    """Отправка одного сообщения пользователю."""
    try:
        await app.bot.send_message(
            chat_id=user_id,
            text=f"📢 **Обновление от администрации**\n\n{message_text}",
            parse_mode='Markdown'
        )
        return True
    except Exception as exc:
        logger.warning("Не удалось отправить сообщение пользователю %s: %s", user_id, exc)
        return False

async def send_broadcast_message(app: Application, message_text: str, admin_id: int) -> dict:
    """Улучшенная рассылка сообщений с батчами и прогрессом."""
    BATCH_SIZE = 10
    DELAY_BETWEEN_BATCHES = 2.0
    DELAY_BETWEEN_MESSAGES = 0.1
    
    try:
        # Получаем всех пользователей
        result = supabase.table("users").select("tg_id").execute()
        user_ids = [user['tg_id'] for user in result.data or []]
        
        total_users = len(user_ids)
        if total_users == 0:
            await app.bot.send_message(
                chat_id=admin_id,
                text="❌ Нет пользователей для рассылки."
            )
            return {"success": 0, "failed": 0, "total": 0}
        
        logger.info("Начало рассылки сообщения для %s пользователей", total_users)
        
        # Отправляем сообщение о начале рассылки
        progress_message = await app.bot.send_message(
            chat_id=admin_id,
            text=f"📡 **Рассылка началась...**\n\n📊 Прогресс: 0/{total_users} (0 успешно)"
        )
        
        processed = 0
        success_count = 0
        failed_count = 0
        failed_users = []
        
        # Отправка батчами
        for i in range(0, total_users, BATCH_SIZE):
            batch = user_ids[i:i+BATCH_SIZE]
            
            # Параллельная отправка в батче
            tasks = []
            for user_id in batch:
                task = asyncio.create_task(
                    send_single_message(app, user_id, message_text)
                )
                tasks.append((task, user_id))
            
            # Ожидаем результатов батча
            for task, user_id in tasks:
                try:
                    result = await task
                    if result:
                        success_count += 1
                    else:
                        failed_count += 1
                        failed_users.append({"user_id": user_id, "error": "Send failed"})
                    
                    processed += 1
                    
                    # Небольшая задержка между сообщениями
                    await asyncio.sleep(DELAY_BETWEEN_MESSAGES)
                    
                except Exception as exc:
                    failed_count += 1
                    failed_users.append({"user_id": user_id, "error": str(exc)})
                    processed += 1
            
            # Обновляем прогресс каждый батч
            try:
                progress_text = f"📡 **Рассылка в процессе...**\n\n📊 Прогресс: {processed}/{total_users} ({success_count} успешно, {failed_count} ошибок)"
                await app.bot.edit_message_text(
                    chat_id=admin_id,
                    message_id=progress_message.message_id,
                    text=progress_text,
                    parse_mode='Markdown'
                )
            except Exception:
                pass  # Игнорируем ошибки обновления прогресса
            
            # Задержка между батчами (кроме последнего)
            if i + BATCH_SIZE < total_users:
                await asyncio.sleep(DELAY_BETWEEN_BATCHES)
        
        # Финальное сообщение с результатами
        summary = f"""📊 **Результат рассылки:**

✅ Успешно доставлено: {success_count}
❌ Ошибки доставки: {failed_count}
📨 Всего пользователей: {total_users}
📈 Успешность: {success_count/max(total_users, 1)*100:.1f}%

Рассылка завершена!"""
        
        try:
            await app.bot.edit_message_text(
                chat_id=admin_id,
                message_id=progress_message.message_id,
                text=summary,
                parse_mode='Markdown'
            )
        except Exception:
            # Если редактирование не удалось, отправляем новое сообщение
            try:
                await app.bot.send_message(
                    chat_id=admin_id,
                    text=summary,
                    parse_mode='Markdown'
                )
            except Exception:
                pass
        
        logger.info("Рассылка завершена: %s успешных, %s ошибок из %s", success_count, failed_count, total_users)
        
        return {
            "success": success_count,
            "failed": failed_count,
            "total": total_users,
            "failed_users": failed_users
        }
        
    except Exception as exc:
        logger.error("Ошибка при рассылке: %s", exc)
        try:
            await app.bot.send_message(
                chat_id=admin_id,
                text=f"❌ **Ошибка рассылки:** {str(exc)}"
            )
        except Exception:
            pass
        return {"success": 0, "failed": 0, "total": 0, "failed_users": []}

# --- Keyboard generation functions ---
def get_main_menu_keyboard(user_id: int = None) -> InlineKeyboardMarkup:
    """Generate main menu keyboard."""
    keyboard = [
        [InlineKeyboardButton("⚙️ Настройки", callback_data="menu_settings")],
        [InlineKeyboardButton("👥 Друзья", callback_data="menu_friends")],
        [InlineKeyboardButton("📊 История", callback_data="menu_history")]
    ]
    
    # Add admin panel for admin users
    if user_id and is_admin(user_id):
        keyboard.insert(3, [InlineKeyboardButton("📢 Админ панель", callback_data="admin_panel")])
    
    keyboard.append([InlineKeyboardButton("❓ Помощь", callback_data="menu_help")])
    return InlineKeyboardMarkup(keyboard)

async def get_settings_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Generate settings menu keyboard with current user data (cached)."""
    try:
        # Get user data from cache
        user_data = await get_user_settings_cached(user_id)
        
        if not user_data:
            return InlineKeyboardMarkup([[InlineKeyboardButton("← Назад", callback_data="menu_main")]])
        
        # Format current settings
        status = "ВКЛ" if user_data['enabled'] else "ВЫКЛ"
        time_window = f"{user_data['window_start'][:5]}-{user_data['window_end'][:5]}"
        frequency = f"{user_data['interval_min']} мин"
        
        keyboard = [
            [InlineKeyboardButton(f"🔔 Уведомления: {status}", callback_data="set_notifications")],
            [InlineKeyboardButton(f"⏰ Время: {time_window}", callback_data="set_time_window")],
            [InlineKeyboardButton(f"📊 Частота: {frequency}", callback_data="set_frequency")],
            [InlineKeyboardButton("📝 Мои настройки", callback_data="set_view_settings")],
            [InlineKeyboardButton("← Назад", callback_data="menu_main")]
        ]
        return InlineKeyboardMarkup(keyboard)
    except Exception as exc:
        logger.error("Ошибка генерации клавиатуры настроек: %s", exc)
        return InlineKeyboardMarkup([[InlineKeyboardButton("← Назад", callback_data="menu_main")]])

async def get_friends_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Generate friends menu keyboard."""
    try:
        # Get friend requests count
        requests = await get_friend_requests(user_id)
        incoming_count = len(requests['incoming'])
        
        # Get friends count
        friends = await get_friends_list(user_id)
        friends_count = len(friends)
        
        keyboard = [
            [InlineKeyboardButton("➕ Добавить друга", callback_data="friend_add")],
            [InlineKeyboardButton(f"📥 Запросы ({incoming_count})", callback_data="friend_requests")],
            [InlineKeyboardButton(f"👥 Мои друзья ({friends_count})", callback_data="friend_list")],
            [InlineKeyboardButton("🔍 Найти друзей", callback_data="friends_discover")],
            [InlineKeyboardButton("📊 Активности друзей", callback_data="friend_activities")],
            [InlineKeyboardButton("← Назад", callback_data="menu_main")]
        ]
        return InlineKeyboardMarkup(keyboard)
    except Exception as exc:
        logger.error("Ошибка генерации клавиатуры друзей: %s", exc)
        return InlineKeyboardMarkup([[InlineKeyboardButton("← Назад", callback_data="menu_main")]])

async def get_friend_requests_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Generate friend requests keyboard with accept/decline buttons."""
    try:
        requests = await get_friend_requests(user_id)
        keyboard = []
        
        # Add buttons for each incoming request
        for req in requests['incoming']:
            requester_username = req['requester']['tg_username']
            requester_name = req['requester']['tg_first_name']
            
            if requester_username:
                display_name = f"@{requester_username}"
                user_identifier = requester_username
            else:
                display_name = requester_name or "Unknown"
                user_identifier = str(req['requester_id'])
            
            # Add row with user name
            keyboard.append([InlineKeyboardButton(f"👤 {display_name}", callback_data="noop")])
            
            # Add row with accept/decline buttons
            keyboard.append([
                InlineKeyboardButton("✅ Принять", callback_data=f"req_accept_{user_identifier}"),
                InlineKeyboardButton("❌ Отклонить", callback_data=f"req_decline_{user_identifier}")
            ])
        
        if not requests['incoming']:
            keyboard.append([InlineKeyboardButton("📭 Нет новых запросов", callback_data="noop")])
        
        keyboard.append([InlineKeyboardButton("← Назад", callback_data="menu_friends")])
        return InlineKeyboardMarkup(keyboard)
    except Exception as exc:
        logger.error("Ошибка генерации клавиатуры запросов: %s", exc)
        return InlineKeyboardMarkup([[InlineKeyboardButton("← Назад", callback_data="menu_friends")]])

async def get_admin_panel_keyboard() -> InlineKeyboardMarkup:
    """Generate admin panel keyboard."""
    try:
        stats = await get_user_stats()
        
        keyboard = [
            [InlineKeyboardButton("📢 Рассылка обновления", callback_data="admin_broadcast")],
            [InlineKeyboardButton(f"📊 Статистика ({stats['total']} польз.)", callback_data="admin_stats")],
            [InlineKeyboardButton("📝 Тест рассылки", callback_data="admin_test")],
            [InlineKeyboardButton("← Назад", callback_data="menu_main")]
        ]
        return InlineKeyboardMarkup(keyboard)
    except Exception as exc:
        logger.error("Ошибка генерации админ клавиатуры: %s", exc)
        return InlineKeyboardMarkup([[InlineKeyboardButton("← Назад", callback_data="menu_main")]])

def get_broadcast_confirm_keyboard() -> InlineKeyboardMarkup:
    """Generate broadcast confirmation keyboard."""
    keyboard = [
        [InlineKeyboardButton("✅ Подтвердить рассылку", callback_data="broadcast_confirm")],
        [InlineKeyboardButton("❌ Отменить", callback_data="broadcast_cancel")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def get_friends_discovery_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Generate friends discovery keyboard with recommendations."""
    try:
        recommendations = await get_friends_of_friends(user_id)
        keyboard = []
        
        if not recommendations:
            keyboard.append([InlineKeyboardButton("😔 Рекомендаций пока нет", callback_data="noop")])
            keyboard.append([InlineKeyboardButton("💡 Добавьте друзей, чтобы найти больше людей!", callback_data="noop")])
        else:
            # Add each recommendation as a separate row
            for i, rec in enumerate(recommendations):
                user_info = rec['user_info']
                mutual_friends = rec['mutual_friends']
                
                # Format display name
                display_name = user_info['tg_username'] or user_info['tg_first_name'] or "Unknown"
                if user_info['tg_username']:
                    display_name = f"@{display_name}"
                
                # Format mutual friends list
                if len(mutual_friends) == 1:
                    mutual_text = f"Общий друг: @{mutual_friends[0]}"
                elif len(mutual_friends) <= 3:
                    mutual_names = [f"@{name}" for name in mutual_friends]
                    mutual_text = f"Общие друзья: {', '.join(mutual_names)}"
                else:
                    shown = [f"@{name}" for name in mutual_friends[:2]]
                    mutual_text = f"Общие друзья: {', '.join(shown)} и ещё {len(mutual_friends)-2}"
                
                # Add user info row
                keyboard.append([InlineKeyboardButton(f"👤 {display_name}", callback_data="noop")])
                
                # Add mutual friends info row
                keyboard.append([InlineKeyboardButton(f"   {mutual_text}", callback_data="noop")])
                
                # Add action row
                keyboard.append([InlineKeyboardButton(f"➕ Добавить в друзья", callback_data=f"discover_add_{user_info['tg_id']}")])
                
                # Add separator for better readability (except for last item)
                if i < len(recommendations) - 1:
                    keyboard.append([InlineKeyboardButton("─────────────", callback_data="noop")])
        
        # Add summary and back button
        keyboard.append([InlineKeyboardButton("← Назад", callback_data="menu_friends")])
        
        return InlineKeyboardMarkup(keyboard)
        
    except Exception as exc:
        logger.error("Ошибка генерации клавиатуры рекомендаций: %s", exc)
        return InlineKeyboardMarkup([[InlineKeyboardButton("← Назад", callback_data="menu_friends")]])

# --- Callback Query Handler ---
async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle inline keyboard button callbacks."""
    query = update.callback_query
    user = update.effective_user
    
    if not user or not query:
        return
    
    await query.answer()  # Answer the callback query
    
    # Ensure user exists
    await ensure_user_exists(
        tg_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name
    )
    
    callback_data = query.data
    
    try:
        # Main menu navigation
        if callback_data == "menu_main":
            keyboard = get_main_menu_keyboard(user.id)
            await query.edit_message_text(
                "🤖 **Hour Watcher Бот**\n\nВыберите действие:",
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
        
        elif callback_data == "menu_settings":
            keyboard = await get_settings_keyboard(user.id)
            await query.edit_message_text(
                "⚙️ **Настройки**\n\nВыберите параметр для изменения:",
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
        
        elif callback_data == "menu_friends":
            keyboard = await get_friends_keyboard(user.id)
            await query.edit_message_text(
                "👥 **Друзья**\n\nУправление друзьями и запросами:",
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
        
        elif callback_data == "menu_history":
            # Open history web app
            web_app_url = "https://doyobi-diary.vercel.app/history"
            keyboard = [[InlineKeyboardButton(
                "📊 Открыть историю активностей", 
                web_app=WebAppInfo(url=web_app_url)
            )], [InlineKeyboardButton("← Назад", callback_data="menu_main")]]
            
            await query.edit_message_text(
                "🔍 **Просмотр истории активностей**\n\n"
                "Нажмите кнопку ниже, чтобы открыть веб-интерфейс с вашей полной историей ответов.",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
        
        elif callback_data == "menu_help":
            help_text = """❓ **Справка по боту**

🤖 **Hour Watcher** - бот для отслеживания активности

**Как это работает:**
• Бот будет спрашивать "Чё делаешь? 🤔" в указанное время
• Вы отвечаете, и ответ сохраняется в базу данных
• Можете просматривать историю и анализировать активность

**Настройки:**
• ⏰ Время работы - когда бот активен (например 09:00-23:00)
• 📊 Частота - как часто спрашивать (например каждые 60 минут)
• 🔔 Включить/выключить уведомления

**Друзья:**
• Добавляйте друзей и смотрите их активности
• Отправляйте и принимайте запросы в друзья
• Просматривайте активности через веб-интерфейс"""
            
            keyboard = [[InlineKeyboardButton("← Назад", callback_data="menu_main")]]
            await query.edit_message_text(
                help_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
        
        # Settings callbacks
        elif callback_data == "set_notifications":
            # Toggle notifications
            try:
                user_data = await get_user_settings_cached(user.id)
                current_status = user_data['enabled'] if user_data else True
                new_status = not current_status
                
                supabase.table("users").update({"enabled": new_status}).eq("tg_id", user.id).execute()
                
                # Инвалидируем кеш после обновления
                invalidate_user_cache(user.id)
                
                status_text = "включены" if new_status else "отключены"
                await query.edit_message_text(
                    f"✅ Уведомления {status_text}!",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("← К настройкам", callback_data="menu_settings")]])
                )
                logger.info("Пользователь %s изменил статус уведомлений: %s", user.id, new_status)
            except Exception as exc:
                logger.error("Ошибка изменения статуса уведомлений: %s", exc)
                await query.edit_message_text(
                    "❌ Ошибка при изменении настроек.",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("← К настройкам", callback_data="menu_settings")]])
                )
        
        elif callback_data == "set_time_window":
            await query.edit_message_text(
                "⏰ **Настройка времени**\n\n"
                "Отправьте новое время в формате: `HH:MM-HH:MM`\n"
                "Например: `09:00-23:00`",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("← Назад", callback_data="menu_settings")]]),
                parse_mode='Markdown'
            )
        
        elif callback_data == "set_frequency":
            await query.edit_message_text(
                "📊 **Настройка частоты**\n\n"
                "Отправьте новую частоту в минутах.\n"
                "Например: `60` (для 60 минут)\n"
                "Минимум: 5 минут, максимум: 1440 минут (24 часа)",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("← Назад", callback_data="menu_settings")]]),
                parse_mode='Markdown'
            )
        
        elif callback_data == "set_view_settings":
            # Show current settings (same as /settings command)
            try:
                user_data = await get_user_settings_cached(user.id)
                
                if user_data:
                    settings_text = f"""🔧 **Ваши настройки:**

✅ Статус: {'Включен' if user_data['enabled'] else 'Отключен'}
⏰ Время работы: {user_data['window_start'][:5]} - {user_data['window_end'][:5]}
📊 Интервал: {user_data['interval_min']} минут
👤 Telegram ID: {user_data['tg_id']}
📅 Регистрация: {user_data['created_at'][:10]}"""
                else:
                    settings_text = "❌ Ошибка получения настроек."
                
                await query.edit_message_text(
                    settings_text,
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("← К настройкам", callback_data="menu_settings")]]),
                    parse_mode='Markdown'
                )
            except Exception as exc:
                logger.error("Ошибка получения настроек: %s", exc)
        
        # Friends callbacks
        elif callback_data == "friend_add":
            await query.edit_message_text(
                "➕ **Добавить друга**\n\n"
                "Отправьте username друга в формате: `@username`\n"
                "Например: `@john_doe`",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("← Назад", callback_data="menu_friends")]]),
                parse_mode='Markdown'
            )
        
        elif callback_data == "friend_requests":
            keyboard = await get_friend_requests_keyboard(user.id)
            await query.edit_message_text(
                "📥 **Запросы в друзья**\n\nВыберите действие:",
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
        
        elif callback_data == "friend_list":
            friends = await get_friends_list(user.id)
            
            if friends:
                message_parts = ["👥 **Ваши друзья:**\n"]
                for friend in friends:
                    friend_name = friend['tg_username'] or friend['tg_first_name']
                    message_parts.append(f"• @{friend_name}")
                message_parts.append(f"\nВсего друзей: {len(friends)}")
                friends_text = "\n".join(message_parts)
            else:
                friends_text = "📭 У вас пока нет друзей.\n\nИспользуйте кнопку \"Добавить друга\" чтобы добавить друзей!"
            
            await query.edit_message_text(
                friends_text,
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("← Назад", callback_data="menu_friends")]]),
                parse_mode='Markdown'
            )
        
        elif callback_data == "friend_activities":
            await query.edit_message_text(
                "📊 **Активности друзей**\n\n"
                "Отправьте username друга для просмотра активностей: `@username`\n"
                "Или используйте веб-интерфейс через кнопку \"История\"",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("← Назад", callback_data="menu_friends")]]),
                parse_mode='Markdown'
            )
        
        elif callback_data == "friends_discover":
            try:
                recommendations = await get_friends_of_friends(user.id)
                keyboard = await get_friends_discovery_keyboard(user.id)
                
                if not recommendations:
                    message_text = """🔍 **Поиск друзей**

😔 Рекомендаций пока нет.

💡 Чтобы найти новых друзей:
• Добавьте больше друзей
• Подождите, пока ваши друзья тоже найдут друзей
• Попробуйте снова через некоторое время

Рекомендации появятся, когда у ваших друзей будут общие знакомые!"""
                else:
                    message_text = f"""🔍 **Друзья друзей**

Найдено {len(recommendations)} пользователей через ваших друзей:"""
                
                await query.edit_message_text(
                    message_text,
                    reply_markup=keyboard,
                    parse_mode='Markdown'
                )
                logger.info("Пользователь %s открыл поиск друзей", user.id)
                
            except Exception as exc:
                logger.error("Ошибка поиска друзей для %s: %s", user.id, exc)
                await query.edit_message_text(
                    "❌ Ошибка при поиске друзей.",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("← Назад", callback_data="menu_friends")]])
                )
        
        # Friend request callbacks
        elif callback_data.startswith("req_accept_"):
            user_identifier = callback_data[11:]  # Remove "req_accept_" prefix
            
            # Same logic as accept_command
            try:
                if user_identifier.isdigit():
                    target_user_id = int(user_identifier)
                    target_user = supabase.table("users").select("*").eq("tg_id", target_user_id).execute()
                    target_user = target_user.data[0] if target_user.data else None
                else:
                    target_user = await find_user_by_username(user_identifier)
                
                if not target_user:
                    await query.edit_message_text(
                        "❌ Пользователь не найден!",
                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("← Назад", callback_data="friend_requests")]])
                    )
                    return
                
                # Find and accept request
                result = supabase.table("friendships").select("*").eq(
                    "addressee_id", user.id
                ).eq("requester_id", target_user['tg_id']).eq("status", "pending").execute()
                
                if result.data:
                    success = await update_friend_request(result.data[0]['friendship_id'], "accepted")
                    
                    if success:
                        # Notify requester
                        try:
                            await context.bot.send_message(
                                chat_id=target_user['tg_id'],
                                text=f"🎉 @{user.username or user.first_name} принял ваш запрос в друзья!"
                            )
                        except Exception:
                            pass
                        
                        await query.edit_message_text(
                            f"✅ Вы теперь друзья с @{target_user['tg_username'] or target_user['tg_first_name']}! 🎉",
                            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("← К запросам", callback_data="friend_requests")]])
                        )
                        logger.info("Пользователь %s принял запрос от %s", user.id, target_user['tg_id'])
                    else:
                        await query.edit_message_text(
                            "❌ Ошибка при принятии запроса.",
                            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("← Назад", callback_data="friend_requests")]])
                        )
                else:
                    await query.edit_message_text(
                        "❌ Запрос не найден!",
                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("← Назад", callback_data="friend_requests")]])
                    )
            except Exception as exc:
                logger.error("Ошибка принятия запроса: %s", exc)
                await query.edit_message_text(
                    "❌ Ошибка при принятии запроса.",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("← Назад", callback_data="friend_requests")]])
                )
        
        elif callback_data.startswith("req_decline_"):
            user_identifier = callback_data[12:]  # Remove "req_decline_" prefix
            
            # Same logic as decline_command
            try:
                if user_identifier.isdigit():
                    target_user_id = int(user_identifier)
                    target_user = supabase.table("users").select("*").eq("tg_id", target_user_id).execute()
                    target_user = target_user.data[0] if target_user.data else None
                else:
                    target_user = await find_user_by_username(user_identifier)
                
                if not target_user:
                    await query.edit_message_text(
                        "❌ Пользователь не найден!",
                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("← Назад", callback_data="friend_requests")]])
                    )
                    return
                
                # Find and delete request
                result = supabase.table("friendships").select("*").eq(
                    "addressee_id", user.id
                ).eq("requester_id", target_user['tg_id']).eq("status", "pending").execute()
                
                if result.data:
                    supabase.table("friendships").delete().eq(
                        "friendship_id", result.data[0]['friendship_id']
                    ).execute()
                    
                    await query.edit_message_text(
                        "❌ Запрос отклонён.",
                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("← К запросам", callback_data="friend_requests")]])
                    )
                    logger.info("Пользователь %s отклонил запрос от %s", user.id, target_user['tg_id'])
                else:
                    await query.edit_message_text(
                        "❌ Запрос не найден!",
                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("← Назад", callback_data="friend_requests")]])
                    )
            except Exception as exc:
                logger.error("Ошибка отклонения запроса: %s", exc)
                await query.edit_message_text(
                    "❌ Ошибка при отклонении запроса.",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("← Назад", callback_data="friend_requests")]])
                )
        
        # Friend discovery callbacks
        elif callback_data.startswith("discover_add_"):
            target_user_id = int(callback_data[13:])  # Remove "discover_add_" prefix
            
            try:
                # Get target user info
                target_user_result = supabase.table("users").select("*").eq("tg_id", target_user_id).execute()
                target_user = target_user_result.data[0] if target_user_result.data else None
                
                if not target_user:
                    await query.edit_message_text(
                        "❌ Пользователь не найден!",
                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("← К поиску", callback_data="friends_discover")]])
                    )
                    return
                
                # Create friend request
                success = await create_friend_request(user.id, target_user_id)
                
                if success:
                    # Try to notify the target user
                    try:
                        await context.bot.send_message(
                            chat_id=target_user_id,
                            text=f"🤝 У вас новый запрос в друзья от @{user.username or user.first_name}!\n\n"
                                 f"Быстрые действия (кликните для копирования):\n"
                                 f"✅ `/accept @{user.username or user.first_name}`\n"
                                 f"❌ `/decline @{user.username or user.first_name}`\n\n"
                                 f"Или используйте `/friend_requests` для полного списка.",
                            parse_mode='Markdown'
                        )
                    except Exception:
                        pass  # User might have blocked the bot
                    
                    target_name = target_user['tg_username'] or target_user['tg_first_name']
                    await query.edit_message_text(
                        f"✅ Запрос в друзья отправлен пользователю @{target_name}!\n\n"
                        f"Они получили уведомление и смогут принять или отклонить ваш запрос.",
                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("← К поиску", callback_data="friends_discover")]])
                    )
                    logger.info("Пользователь %s отправил запрос из рекомендаций пользователю %s", user.id, target_user_id)
                else:
                    await query.edit_message_text(
                        f"❌ Не удалось отправить запрос!\n"
                        f"Возможно, вы уже друзья или запрос уже существует.",
                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("← К поиску", callback_data="friends_discover")]])
                    )
                    
            except Exception as exc:
                logger.error("Ошибка добавления из рекомендаций: %s", exc)
                await query.edit_message_text(
                    "❌ Ошибка при отправке запроса.",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("← К поиску", callback_data="friends_discover")]])
                )
        
        # Admin panel callbacks (only for admin)
        elif callback_data == "admin_panel":
            if not is_admin(user.id):
                await query.edit_message_text("❌ У вас нет прав для доступа к админ панели.")
                return
            
            keyboard = await get_admin_panel_keyboard()
            await query.edit_message_text(
                "📢 **Админ панель**\n\nВыберите действие:",
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
            logger.info("Админ %s открыл админ панель", user.id)
        
        elif callback_data == "admin_broadcast":
            if not is_admin(user.id):
                await query.edit_message_text("❌ У вас нет прав для выполнения этой команды.")
                return
            
            await query.edit_message_text(
                "📢 **Рассылка обновления**\n\n"
                "Отправьте текст сообщения для рассылки всем пользователям.\n"
                "Используйте Markdown для форматирования.\n\n"
                "Пример: `Вышло новое обновление! 🎉`",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("← Назад", callback_data="admin_panel")]]),
                parse_mode='Markdown'
            )
        
        elif callback_data == "admin_stats":
            if not is_admin(user.id):
                await query.edit_message_text("❌ У вас нет прав для выполнения этой команды.")
                return
            
            try:
                stats = await get_user_stats()
                
                stats_text = f"""📊 **Статистика пользователей:**

👥 Всего пользователей: {stats['total']}
✅ Активных пользователей: {stats['active']}
🆕 Новых за неделю: {stats['new_week']}

📈 Процент активных: {stats['active']/max(stats['total'], 1)*100:.1f}% (из {stats['total']})"""
                
                await query.edit_message_text(
                    stats_text,
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("← Назад", callback_data="admin_panel")]]),
                    parse_mode='Markdown'
                )
                logger.info("Админ %s просмотрел статистику", user.id)
                
            except Exception as exc:
                logger.error("Ошибка получения статистики: %s", exc)
                await query.edit_message_text(
                    "❌ Ошибка при получении статистики.",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("← Назад", callback_data="admin_panel")]])
                )
        
        elif callback_data == "admin_test":
            if not is_admin(user.id):
                await query.edit_message_text("❌ У вас нет прав для выполнения этой команды.")
                return
            
            # Send test message to admin
            test_message = """📢 **Тест рассылки**

Это тестовое сообщение показывает, как будет выглядеть рассылка для пользователей.

✨ Вы можете использовать **Markdown** для форматирования:
• Жирный текст
• *Курсив*
• `Код`

🎉 Всё работает отлично!"""
            
            try:
                await context.bot.send_message(
                    chat_id=user.id,
                    text=f"📢 **Обновление от администрации**\n\n{test_message}",
                    parse_mode='Markdown'
                )
                
                await query.edit_message_text(
                    "✅ Тестовое сообщение отправлено вам в чат!",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("← Назад", callback_data="admin_panel")]])
                )
                logger.info("Админ %s протестировал рассылку", user.id)
                
            except Exception as exc:
                logger.error("Ошибка отправки тест сообщения: %s", exc)
                await query.edit_message_text(
                    "❌ Ошибка при отправке тестового сообщения.",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("← Назад", callback_data="admin_panel")]])
                )
        
        elif callback_data == "broadcast_confirm":
            if not is_admin(user.id):
                await query.edit_message_text("❌ У вас нет прав для выполнения этой команды.")
                return
            
            message_text = context.user_data.get('broadcast_message')
            if not message_text:
                await query.edit_message_text(
                    "❌ Сообщение для рассылки не найдено. Попробуйте ещё раз.",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("← Назад", callback_data="admin_panel")]])
                )
                return
            
            await query.edit_message_text(
                "📡 **Рассылка началась...**\n\nПожалуйста, подождите. Это может занять несколько минут.",
                reply_markup=None
            )
            
            # Start broadcast in background
            import asyncio
            asyncio.create_task(send_broadcast_message(context.application, message_text, user.id))
            
            # Clear stored message
            context.user_data.pop('broadcast_message', None)
            logger.info("Админ %s подтвердил рассылку", user.id)
        
        elif callback_data == "broadcast_cancel":
            if not is_admin(user.id):
                await query.edit_message_text("❌ У вас нет прав для выполнения этой команды.")
                return
            
            # Clear stored message
            context.user_data.pop('broadcast_message', None)
            
            await query.edit_message_text(
                "❌ Рассылка отменена.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("← К админ панели", callback_data="admin_panel")]])
            )
            logger.info("Админ %s отменил рассылку", user.id)
        
        elif callback_data == "noop":
            # Do nothing for informational buttons
            pass
        
        else:
            # Unknown callback
            await query.edit_message_text(
                "❌ Неизвестная команда.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("← В главное меню", callback_data="menu_main")]])
            )
            
    except Exception as exc:
        logger.error("Ошибка обработки callback: %s", exc)
        try:
            await query.edit_message_text(
                "❌ Произошла ошибка. Попробуйте ещё раз.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("← В главное меню", callback_data="menu_main")]])
            )
        except Exception:
            pass

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
                # Parse last sent time and check interval using safe parser
                last_sent_dt = safe_parse_datetime(last_sent)
                if last_sent_dt is None:
                    # If parsing failed, assume we should send
                    should_send = True
                else:
                    time_diff = current_time - last_sent_dt.replace(tzinfo=None)
                    if time_diff.total_seconds() >= (interval_minutes * 60):
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
            "tg_id": user.id,
            "jobs_timestamp": timestamp,
            "job_text": text
        }
        supabase.table("tg_jobs").insert(data).execute()
        logger.info("Записан ответ от %s", user.id)
        
        # Send confirmation message
        await update.message.reply_text("Понял, принял! 👍")
        
    except Exception as exc:
        logger.error("Ошибка записи в Supabase: %s", exc)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command - register user and show main menu."""
    user = update.effective_user
    if user is None:
        return

    # Ensure user exists in database
    user_data = await ensure_user_exists(
        tg_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name
    )

    if not user_data:
        await update.message.reply_text("❌ Ошибка регистрации пользователя.")
        return

    # Welcome message with main menu
    welcome_text = f"""🤖 **Привет, {user.first_name or user.username or 'друг'}!**

Я бот, который поможет тебе отслеживать твою активность! 📊

🕐 Буду спрашивать что ты делаешь в рабочее время
⚙️ Настрой время и частоту в настройках
📱 Просматривай историю активностей
👥 Добавляй друзей и смотри их активности

Выберите действие из меню ниже:"""

    keyboard = get_main_menu_keyboard(user.id)
    await update.message.reply_text(
        welcome_text, 
        reply_markup=keyboard,
        parse_mode='Markdown'
    )
    
    logger.info("Пользователь %s открыл главное меню", user.id)

async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show user settings from database."""
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

    # Get settings from cache
    user_data = await get_user_settings_cached(user.id)
    
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
        
        # Инвалидируем кеш после обновления
        invalidate_user_cache(user.id)
        
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
        
        # Инвалидируем кеш после обновления
        invalidate_user_cache(user.id)
        
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
    
    # Use improved validation function
    is_valid, error_message, start_time, end_time = validate_time_window(time_range)
    
    if not is_valid:
        await update.message.reply_text(
            f"❌ {error_message}\n"
            "Пример: `/window 09:00-23:00`",
            parse_mode='Markdown'
        )
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
        
        # Инвалидируем кеш после обновления
        invalidate_user_cache(user.id)
        
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
        
        # Инвалидируем кеш после обновления
        invalidate_user_cache(user.id)
        
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

async def add_friend_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Add a friend by username. Format: /add_friend @username"""
    user = update.effective_user
    if user is None:
        return

    if not context.args or len(context.args) != 1:
        await update.message.reply_text(
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
        await update.message.reply_text(
            f"❌ Пользователь {username} не найден!\n"
            "Убедитесь, что он уже использовал бота."
        )
        return
    
    # Check if trying to add themselves
    if target_user['tg_id'] == user.id:
        await update.message.reply_text("❌ Нельзя добавить себя в друзья! 😄")
        return
    
    # Create friend request
    success = await create_friend_request(user.id, target_user['tg_id'])
    
    if success:
        # Try to notify the target user
        try:
            await context.bot.send_message(
                chat_id=target_user['tg_id'],
                text=f"🤝 У вас новый запрос в друзья от @{user.username or user.first_name}!\n\n"
                     f"Быстрые действия (кликните для копирования):\n"
                     f"✅ `/accept @{user.username or user.first_name}`\n"
                     f"❌ `/decline @{user.username or user.first_name}`\n\n"
                     f"Или используйте `/friend_requests` для полного списка.",
                parse_mode='Markdown'
            )
        except Exception:
            pass  # User might have blocked the bot
        
        await update.message.reply_text(
            f"✅ Запрос в друзья отправлен пользователю {username}!"
        )
        logger.info("Пользователь %s отправил запрос в друзья %s", user.id, target_user['tg_id'])
    else:
        await update.message.reply_text(
            f"❌ Не удалось отправить запрос!\n"
            f"Возможно, вы уже друзья или запрос уже существует."
        )

async def friend_requests_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show incoming and outgoing friend requests."""
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
    
    requests = await get_friend_requests(user.id)
    
    # Build response message
    message_parts = ["🤝 Запросы в друзья:\n"]
    
    # Incoming requests
    if requests['incoming']:
        message_parts.append("📥 Входящие запросы:")
        message_parts.append("Скопируйте команду целиком кликнув на неё: \n")
        for i, req in enumerate(requests['incoming'], 1):
            requester_username = req['requester']['tg_username']
            requester_name = req['requester']['tg_first_name']
            
            if requester_username:
                display_name = f"@{requester_username}"
                accept_cmd = f"`/accept @{requester_username}`"
                decline_cmd = f"`/decline @{requester_username}`"
            else:
                display_name = requester_name or "Unknown"
                # Fallback to ID if no username
                short_id = req['friendship_id'][:8]
                accept_cmd = f"`/accept {short_id}`"
                decline_cmd = f"`/decline {short_id}`"
            
            message_parts.append(f"{i}. {display_name}")
            message_parts.append(f"   ✅ {accept_cmd}")
            message_parts.append(f"   ❌ {decline_cmd}")
            message_parts.append("")
    
    # Outgoing requests
    if requests['outgoing']:
        message_parts.append("📤 Исходящие запросы:")
        for req in requests['outgoing']:
            addressee_name = req['addressee']['tg_username'] or req['addressee']['tg_first_name']
            message_parts.append(f"• @{addressee_name} (ожидает ответа)")
        message_parts.append("")
    
    if not requests['incoming'] and not requests['outgoing']:
        message_parts.append("📭 Нет активных запросов в друзья.")
    
    await update.message.reply_text(
        "\n".join(message_parts),
        parse_mode='Markdown'
    )

async def accept_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Accept a friend request. Format: /accept [request_id]"""
    user = update.effective_user
    if user is None:
        return

    if not context.args or len(context.args) != 1:
        await update.message.reply_text(
            "❌ Неправильный формат!\n\n"
            "Чтобы принять запрос в друзья:\n"
            "1. Используйте `/friend_requests` чтобы посмотреть запросы\n"
            "2. Скопируйте команду `/accept` из списка\n"
            "3. Отправьте скопированную команду\n\n"
            "Пример: `/accept @username` или `/accept username`",
            parse_mode='Markdown'
        )
        return
    
    identifier = context.args[0]
    
    try:
        # Check if it's a username (starts with @) or an ID
        if identifier.startswith('@') or not identifier.isdigit():
            # Find user by username (remove @ if present)
            username = identifier[1:] if identifier.startswith('@') else identifier
            target_user = await find_user_by_username(username)
            if not target_user:
                await update.message.reply_text(f"❌ Пользователь @{username} не найден!")
                return
            
            # Find friendship by requester_id
            result = supabase.table("friendships").select("*").eq(
                "addressee_id", user.id
            ).eq("requester_id", target_user['tg_id']).eq("status", "pending").execute()
            
            matching_request = result.data[0] if result.data else None
        else:
            # Old method with ID
            result = supabase.table("friendships").select("*").eq(
                "addressee_id", user.id
            ).eq("status", "pending").execute()
            
            matching_request = None
            for req in result.data or []:
                if req['friendship_id'].startswith(identifier):
                    matching_request = req
                    break
        
        if not matching_request:
            await update.message.reply_text("❌ Запрос не найден!")
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
                
                await update.message.reply_text(
                    f"✅ Вы теперь друзья с @{requester_name}! 🎉"
                )
                logger.info("Пользователь %s принял запрос от %s", user.id, matching_request['requester_id'])
            else:
                await update.message.reply_text("✅ Запрос принят!")
        else:
            await update.message.reply_text("❌ Ошибка при принятии запроса.")
            
    except Exception as exc:
        logger.error("Ошибка при принятии запроса: %s", exc)
        await update.message.reply_text("❌ Ошибка при принятии запроса.")

async def decline_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Decline a friend request. Format: /decline [request_id]"""
    user = update.effective_user
    if user is None:
        return

    if not context.args or len(context.args) != 1:
        await update.message.reply_text(
            "❌ Неправильный формат!\n\n"
            "Чтобы отклонить запрос в друзья:\n"
            "1. Используйте `/friend_requests` чтобы посмотреть запросы\n"
            "2. Скопируйте команду `/decline` из списка\n"
            "3. Отправьте скопированную команду\n\n"
            "Пример: `/decline @username`",
            parse_mode='Markdown'
        )
        return
    
    identifier = context.args[0]
    
    # Find and delete the request
    try:
        # Check if it's a username (starts with @) or an ID
        if identifier.startswith('@') or not identifier.isdigit():
            # Find user by username (remove @ if present)
            username = identifier[1:] if identifier.startswith('@') else identifier
            target_user = await find_user_by_username(username)
            if not target_user:
                await update.message.reply_text(f"❌ Пользователь @{username} не найден!")
                return
            
            # Find friendship by requester_id
            result = supabase.table("friendships").select("*").eq(
                "addressee_id", user.id
            ).eq("requester_id", target_user['tg_id']).eq("status", "pending").execute()
            
            matching_request = result.data[0] if result.data else None
        else:
            # Old method with ID
            result = supabase.table("friendships").select("*").eq(
                "addressee_id", user.id
            ).eq("status", "pending").execute()
            
            matching_request = None
            for req in result.data or []:
                if req['friendship_id'].startswith(identifier):
                    matching_request = req
                    break
        
        if not matching_request:
            await update.message.reply_text("❌ Запрос не найден!")
            return
        
        # Delete the request
        supabase.table("friendships").delete().eq(
            "friendship_id", matching_request['friendship_id']
        ).execute()
        
        await update.message.reply_text("❌ Запрос отклонён.")
        logger.info("Пользователь %s отклонил запрос от %s", user.id, matching_request['requester_id'])
            
    except Exception as exc:
        logger.error("Ошибка при отклонении запроса: %s", exc)
        await update.message.reply_text("❌ Ошибка при отклонении запроса.")

async def friends_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show list of friends."""
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
    
    friends = await get_friends_list(user.id)
    
    if not friends:
        await update.message.reply_text(
            "👥 У вас пока нет друзей.\n\n"
            "Используйте /add_friend @username чтобы добавить друзей!"
        )
        return
    
    message_parts = ["👥 Ваши друзья:\n"]
    
    for friend in friends:
        friend_name = friend['tg_username'] or friend['tg_first_name']
        message_parts.append(f"• @{friend_name}")
    
    message_parts.extend([
        "",
        f"Всего друзей: {len(friends)}",
        "",
        "Используйте /activities @username чтобы посмотреть активности друга!"
    ])
    
    await update.message.reply_text(
        "\n".join(message_parts)
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
        await update.message.reply_text(
            f"❌ Пользователь {target_username} не найден!\n"
            "Убедитесь, что он уже использовал бота."
        )
        return
    
    # Check if they are friends
    friends = await get_friends_list(user.id)
    is_friend = any(friend['tg_id'] == target_user['tg_id'] for friend in friends)
    
    if not is_friend and target_user['tg_id'] != user.id:
        await update.message.reply_text(
            f"🔒 Вы не можете просматривать активности @{target_username}.\n"
            f"Сначала добавьте в друзья: /add_friend {target_username}"
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
            await update.message.reply_text(
                f"📝 У @{target_name} нет активностей за последнюю неделю."
            )
            return
        
        # Format response
        target_name = target_user['tg_username'] or target_user['tg_first_name']
        message_parts = [f"📊 Активности @{target_name} (последние 10):\n"]
        
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
        
        await update.message.reply_text(
            "\n".join(message_parts)
        )
        
        logger.info("Пользователь %s просмотрел активности %s", user.id, target_user['tg_id'])
        
    except Exception as exc:
        logger.error("Ошибка получения активностей: %s", exc)
        await update.message.reply_text("❌ Ошибка при получении активностей.")

async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send broadcast message to all users (admin only)."""
    user = update.effective_user
    if not user or not is_admin(user.id):
        await update.message.reply_text("❌ У вас нет прав для выполнения этой команды.")
        return
    
    if not context.args:
        await update.message.reply_text(
            "📢 **Рассылка сообщения**\n\n"
            "Используйте: `/broadcast <текст сообщения>`\n"
            "Пример: `/broadcast Вышло новое обновление!`",
            parse_mode='Markdown'
        )
        return
    
    # Get full message text preserving line breaks
    full_text = update.message.text
    command_start = full_text.find('/broadcast') + len('/broadcast')
    message_text = full_text[command_start:].strip()
    
    # Show preview and confirmation
    preview_text = f"""📢 **Предварительный просмотр рассылки:**

{message_text}

⚠️ **Внимание!** Сообщение будет отправлено всем пользователям бота.
Вы уверены, что хотите продолжить?"""
    
    keyboard = get_broadcast_confirm_keyboard()
    await update.message.reply_text(
        preview_text,
        reply_markup=keyboard,
        parse_mode='Markdown'
    )
    
    # Store message text in context for later use
    context.user_data['broadcast_message'] = message_text
    logger.info("Админ %s подготовил рассылку: %s", user.id, message_text[:50])

async def broadcast_info_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show user statistics (admin only)."""
    user = update.effective_user
    if not user or not is_admin(user.id):
        await update.message.reply_text("❌ У вас нет прав для выполнения этой команды.")
        return
    
    try:
        stats = await get_user_stats()
        
        stats_text = f"""📊 **Статистика пользователей:**

👥 Всего пользователей: {stats['total']}
✅ Активных пользователей: {stats['active']}
🆕 Новых за неделю: {stats['new_week']}

📈 Процент активных: {stats['active']/max(stats['total'], 1)*100:.1f}% (из {stats['total']})"""
        
        await update.message.reply_text(stats_text, parse_mode='Markdown')
        logger.info("Админ %s запросил статистику", user.id)
        
    except Exception as exc:
        logger.error("Ошибка получения статистики: %s", exc)
        await update.message.reply_text("❌ Ошибка при получении статистики.")

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
    
    # Admin commands
    application.add_handler(CommandHandler("broadcast", broadcast_command))
    application.add_handler(CommandHandler("broadcast_info", broadcast_info_command))
    
    # Add callback query handler for inline keyboards
    application.add_handler(CallbackQueryHandler(handle_callback_query))
    
    # Add message handler (must be last)
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
