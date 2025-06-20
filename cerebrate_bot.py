"""
Compatibility module for legacy tests.

This module provides backwards compatibility for tests that still import
from the old cerebrate_bot module.
"""

# Legacy imports for test compatibility
from bot.utils.datetime_utils import safe_parse_datetime
from bot.utils.cache_manager import CacheManager as LegacyCacheManager


class CacheManager:
    """Legacy cache manager for test compatibility."""
    
    def __init__(self):
        self._cache = {}
        self._expiry = {}
    
    def get(self, key: str, default=None):
        if key in self._cache:
            import time
            if key in self._expiry and time.time() > self._expiry[key]:
                # Expired
                del self._cache[key]
                del self._expiry[key]
                return default
            return self._cache[key]
        return default
    
    def set(self, key: str, value, timeout_seconds: int = 300):
        import time
        self._cache[key] = value
        if timeout_seconds > 0:
            self._expiry[key] = time.time() + timeout_seconds
        else:
            # timeout_seconds = 0 means expire immediately
            self._expiry[key] = time.time() - 1
    
    def invalidate(self, key: str):
        if key in self._cache:
            del self._cache[key]
        if key in self._expiry:
            del self._expiry[key]
    
    def clear(self):
        self._cache.clear()
        self._expiry.clear()


def validate_time_window(window_str: str) -> bool:
    """Validate time window format."""
    import re
    pattern = r'^([01]?[0-9]|2[0-3]):[0-5][0-9]-([01]?[0-9]|2[0-3]):[0-5][0-9]$'
    return bool(re.match(pattern, window_str))


def is_admin(user_id: int) -> bool:
    """Check if user is admin."""
    import os
    try:
        admin_id = int(os.getenv("ADMIN_USER_ID", "0"))
        return admin_id != 0 and user_id == admin_id
    except (ValueError, TypeError):
        return False


# Mock functions for admin tests
async def get_user_stats():
    """Mock user stats for tests."""
    return {
        "total_users": 100,
        "active_users": 80,
        "new_users_week": 10
    }


async def send_single_message(bot, chat_id: int, message: str):
    """Mock send single message for tests."""
    return True


async def send_broadcast_message(application, message: str):
    """Mock broadcast for tests."""
    return {"success": 100, "failed": 0}


# Export for legacy compatibility
__all__ = [
    'CacheManager',
    'safe_parse_datetime', 
    'validate_time_window',
    'is_admin',
    'get_user_stats',
    'send_single_message', 
    'send_broadcast_message'
]