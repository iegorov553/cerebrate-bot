"""
Date and time utility functions.
"""
import re
from datetime import datetime, time
from typing import Tuple, Optional

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