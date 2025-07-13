"""
Date and time utility functions.
"""
import re
from datetime import datetime, time
from typing import Optional, Tuple

from monitoring import get_logger, track_errors

logger = get_logger(__name__)


@track_errors("datetime_parsing")
def safe_parse_datetime(dt_string: str) -> Optional[datetime]:
    """Безопасный парсинг datetime строки."""
    try:
        if dt_string:
            return datetime.fromisoformat(dt_string.replace('Z', '+00:00'))
        return None
    except (ValueError, AttributeError, TypeError):
        logger.warning("Не удалось распарсить дату: %s", dt_string)
        return None


@track_errors("time_validation")
def validate_time_window(time_range: str) -> Tuple[bool, str, Optional[time], Optional[time]]:
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


@track_errors("interval_validation")
def validate_interval(interval_str: str) -> Tuple[bool, str, int]:
    """
    Validate notification interval.

    Args:
        interval_str: Interval string (should be integer minutes)

    Returns:
        Tuple of (is_valid, error_message, interval_value)
    """
    try:
        interval = int(interval_str.strip())

        if interval < 5:
            return False, "Интервал не может быть меньше 5 минут", 0

        if interval > 1440:  # 24 hours
            return False, "Интервал не может быть больше 24 часов (1440 минут)", 0

        return True, "", interval

    except (ValueError, AttributeError):
        return False, f"Неверный формат интервала: {interval_str}. Введите число (минуты)", 0


@track_errors("username_validation")
def validate_username(username: str) -> Tuple[bool, str]:
    """
    Validate Telegram username.

    Args:
        username: Username to validate (with or without @)

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not username or not isinstance(username, str):
        return False, "Имя пользователя не может быть пустым"

    # Remove @ if present
    clean_username = username.lstrip('@').strip()

    if not clean_username:
        return False, "Имя пользователя не может быть пустым"

    if len(clean_username) < 5:
        return False, "Имя пользователя должно содержать минимум 5 символов"

    if len(clean_username) > 32:
        return False, "Имя пользователя не может быть длиннее 32 символов"

    # Check for valid characters (letters, numbers, underscores)
    if not clean_username.replace('_', '').replace('-', '').isalnum():
        return False, "Имя пользователя может содержать только буквы, цифры, _ и -"

    return True, ""
