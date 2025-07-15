"""
Cache management utilities.
"""
from datetime import datetime, timedelta
from typing import Any

from monitoring import get_logger, track_errors

logger = get_logger(__name__)


class CacheManager:
    """Простой менеджер кеша с поддержкой TTL."""

    def __init__(self):
        self._cache = {}
        self._cache_timeout = {}

    @track_errors("cache_get")
    def get(self, key: str, default=None) -> Any:
        """Получить значение из кеша."""
        if key in self._cache:
            if datetime.now() < self._cache_timeout[key]:
                logger.debug("Cache hit", key=key)
                return self._cache[key]
            else:
                # Кеш истек, удаляем
                logger.debug("Cache expired", key=key)
                del self._cache[key]
                del self._cache_timeout[key]

        logger.debug("Cache miss", key=key)
        return default

    @track_errors("cache_set")
    def set(self, key: str, value: Any, timeout_seconds: int = 300) -> None:
        """Сохранить значение в кеш с TTL."""
        self._cache[key] = value
        self._cache_timeout[key] = datetime.now() + timedelta(seconds=timeout_seconds)
        logger.debug("Cache set", key=key, timeout=timeout_seconds)

    @track_errors("cache_invalidate")
    def invalidate(self, key: str) -> None:
        """Принудительно удалить значение из кеша."""
        if key in self._cache:
            del self._cache[key]
            logger.debug("Cache invalidated", key=key)
        if key in self._cache_timeout:
            del self._cache_timeout[key]

    def clear(self) -> None:
        """Очистить весь кеш."""
        cache_size = len(self._cache)
        self._cache.clear()
        self._cache_timeout.clear()
        logger.info("Cache cleared", previous_size=cache_size)

    def size(self) -> int:
        """Получить размер кеша."""
        return len(self._cache)

    def cleanup_expired(self) -> int:
        """Очистить истекшие записи и вернуть количество удаленных."""
        now = datetime.now()
        expired_keys = [key for key, timeout in self._cache_timeout.items() if now >= timeout]

        for key in expired_keys:
            self.invalidate(key)

        if expired_keys:
            logger.debug("Expired cache entries cleaned", count=len(expired_keys))

        return len(expired_keys)
