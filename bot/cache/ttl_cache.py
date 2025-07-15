"""
TTL Cache implementation for Doyobi Diary.

This module provides time-to-live caching functionality with automatic cleanup
and configurable expiration times.
"""

import asyncio
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

from bot.utils.cache_manager import get_logger

logger = get_logger(__name__)


@dataclass
class CacheEntry:
    """Cache entry with TTL support."""

    value: Any
    expires_at: float
    created_at: float

    def is_expired(self) -> bool:
        """Check if cache entry has expired."""
        return time.time() > self.expires_at


class TTLCache:
    """Time-to-live cache with automatic cleanup."""

    def __init__(self, ttl_seconds: int = 300):
        """
        Initialize TTL cache.

        Args:
            ttl_seconds: Time to live in seconds (default: 5 minutes)
        """
        self.ttl_seconds = ttl_seconds
        self._cache: Dict[str, CacheEntry] = {}
        self._cleanup_task = None
        self._running = False

    async def get(self, key: str, default: Any = None) -> Any:
        """
        Get value from cache.

        Args:
            key: Cache key
            default: Default value if key not found or expired

        Returns:
            Cached value or default
        """
        entry = self._cache.get(key)

        if entry is None:
            logger.debug(f"Cache miss for key: {key}")
            return default

        if entry.is_expired():
            logger.debug(f"Cache expired for key: {key}")
            await self.invalidate(key)
            return default

        logger.debug(f"Cache hit for key: {key}")
        return entry.value

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Custom TTL in seconds (overrides default)
        """
        ttl_to_use = ttl if ttl is not None else self.ttl_seconds
        now = time.time()

        entry = CacheEntry(value=value, expires_at=now + ttl_to_use, created_at=now)

        self._cache[key] = entry
        logger.debug(f"Cache set for key: {key}, TTL: {ttl_to_use}s")

        # Start cleanup task if not already running
        if not self._running:
            await self._start_cleanup_task()

    async def invalidate(self, key: str) -> bool:
        """
        Remove key from cache.

        Args:
            key: Cache key to remove

        Returns:
            True if key was removed, False if not found
        """
        if key in self._cache:
            del self._cache[key]
            logger.debug(f"Cache invalidated for key: {key}")
            return True
        return False

    async def clear(self) -> None:
        """Clear all cache entries."""
        self._cache.clear()
        logger.info("Cache cleared")

    async def cleanup_expired(self) -> int:
        """
        Remove expired entries.

        Returns:
            Number of entries removed
        """
        now = time.time()
        expired_keys = [key for key, entry in self._cache.items() if entry.expires_at <= now]

        for key in expired_keys:
            del self._cache[key]

        if expired_keys:
            logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")

        return len(expired_keys)

    async def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        now = time.time()
        total_entries = len(self._cache)
        expired_entries = sum(1 for entry in self._cache.values() if entry.expires_at <= now)
        active_entries = total_entries - expired_entries

        return {
            "total_entries": total_entries,
            "active_entries": active_entries,
            "expired_entries": expired_entries,
            "hit_rate": getattr(self, "_hit_rate", 0.0),
            "memory_usage_bytes": self._estimate_memory_usage(),
        }

    def _estimate_memory_usage(self) -> int:
        """Estimate memory usage of cache entries."""
        # Simple estimation - in production you might want more accurate calculation
        import sys

        total_size = 0
        for key, entry in self._cache.items():
            total_size += sys.getsizeof(key)
            total_size += sys.getsizeof(entry.value)
            total_size += sys.getsizeof(entry)
        return total_size

    async def _start_cleanup_task(self) -> None:
        """Start background cleanup task."""
        if self._running:
            return

        self._running = True
        self._cleanup_task = asyncio.create_task(self._cleanup_worker())
        logger.info("Started cache cleanup worker")

    async def _cleanup_worker(self) -> None:
        """Background worker for cleaning up expired entries."""
        while self._running and self._cache:
            try:
                await asyncio.sleep(60)  # Run cleanup every minute
                await self.cleanup_expired()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cache cleanup worker: {e}")

        self._running = False
        logger.info("Cache cleanup worker stopped")

    async def stop(self) -> None:
        """Stop the cache and cleanup worker."""
        self._running = False
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        await self.clear()
        logger.info("Cache stopped")


# Global cache instance
_global_cache: Optional[TTLCache] = None


def get_cache(ttl_seconds: int = 300) -> TTLCache:
    """
    Get global cache instance.

    Args:
        ttl_seconds: TTL for cache entries

    Returns:
        Global TTLCache instance
    """
    global _global_cache
    if _global_cache is None:
        _global_cache = TTLCache(ttl_seconds)
    return _global_cache


async def cache_user_settings(user_id: int, settings: Dict[str, Any]) -> None:
    """Cache user settings."""
    cache = get_cache()
    await cache.set(f"user_settings:{user_id}", settings)


async def get_cached_user_settings(user_id: int) -> Optional[Dict[str, Any]]:
    """Get cached user settings."""
    cache = get_cache()
    return await cache.get(f"user_settings:{user_id}")


async def invalidate_user_cache(user_id: int) -> None:
    """Invalidate all cache entries for a user."""
    cache = get_cache()
    patterns = [
        f"user_settings:{user_id}",
        f"user_friends:{user_id}",
        f"friend_activities:{user_id}",
    ]

    for pattern in patterns:
        await cache.invalidate(pattern)

    logger.info(f"Invalidated cache for user {user_id}")
