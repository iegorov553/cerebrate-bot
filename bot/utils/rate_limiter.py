"""
Rate limiting utilities to prevent spam and abuse.
"""
import asyncio
from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple

from monitoring import get_logger, track_errors

logger = get_logger(__name__)


class RateLimiter:
    """Rate limiter with sliding window algorithm."""

    def __init__(self, max_requests: int = 10, window_seconds: int = 60):
        """
        Initialize rate limiter.

        Args:
            max_requests: Maximum requests allowed in the window
            window_seconds: Time window in seconds
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: Dict[str, deque] = defaultdict(deque)
        self._lock = asyncio.Lock()

    @track_errors("rate_limit_check")
    async def is_allowed(self, key: str) -> Tuple[bool, Optional[int]]:
        """
        Check if request is allowed for the given key.

        Args:
            key: Unique identifier (e.g., user_id, IP address)

        Returns:
            Tuple of (is_allowed, retry_after_seconds)
        """
        async with self._lock:
            now = datetime.now()
            cutoff = now - timedelta(seconds=self.window_seconds)

            # Clean old requests
            user_requests = self.requests[key]
            while user_requests and user_requests[0] < cutoff:
                user_requests.popleft()

            # Check if under limit
            if len(user_requests) < self.max_requests:
                user_requests.append(now)
                logger.debug("Rate limit check passed", key=key, count=len(user_requests))
                return True, None
            else:
                # Calculate retry after (when oldest request expires)
                oldest_request = user_requests[0]
                retry_after = int((oldest_request + timedelta(seconds=self.window_seconds) - now).total_seconds())
                retry_after = max(1, retry_after)  # At least 1 second

                logger.warning("Rate limit exceeded", key=key, count=len(user_requests), retry_after=retry_after)
                return False, retry_after

    def get_usage(self, key: str) -> Dict[str, int]:
        """Get current usage stats for a key."""
        now = datetime.now()
        cutoff = now - timedelta(seconds=self.window_seconds)

        user_requests = self.requests[key]
        # Count recent requests
        recent_count = sum(1 for req_time in user_requests if req_time > cutoff)

        return {
            "current_count": recent_count,
            "max_requests": self.max_requests,
            "window_seconds": self.window_seconds,
            "remaining": max(0, self.max_requests - recent_count),
        }

    def cleanup_old_entries(self) -> int:
        """Clean up old entries to free memory."""
        now = datetime.now()
        cutoff = now - timedelta(seconds=self.window_seconds)

        cleaned = 0
        keys_to_remove = []

        for key, user_requests in self.requests.items():
            # Clean old requests
            while user_requests and user_requests[0] < cutoff:
                user_requests.popleft()
                cleaned += 1

            # Remove empty entries
            if not user_requests:
                keys_to_remove.append(key)

        for key in keys_to_remove:
            del self.requests[key]

        logger.debug("Rate limiter cleanup", cleaned_requests=cleaned, removed_keys=len(keys_to_remove))
        return cleaned


class MultiTierRateLimiter:
    """Multi-tier rate limiter with different limits for different actions."""

    def __init__(self, feedback_rate_limit: int = 3):
        """Initialize with default limits for different action types."""
        self.limiters = {
            # General commands - 20 per minute
            "general": RateLimiter(max_requests=20, window_seconds=60),
            # Friend requests - 5 per hour (prevent spam)
            "friend_request": RateLimiter(max_requests=5, window_seconds=3600),
            # Settings changes - 10 per minute
            "settings": RateLimiter(max_requests=10, window_seconds=60),
            # Friend discovery - 3 per minute (expensive operation)
            "discovery": RateLimiter(max_requests=3, window_seconds=60),
            # Admin commands - 50 per minute
            "admin": RateLimiter(max_requests=50, window_seconds=60),
            # Callback queries - 30 per minute
            "callback": RateLimiter(max_requests=30, window_seconds=60),
            # Feedback submissions - configurable rate limit per hour
            "feedback": RateLimiter(max_requests=feedback_rate_limit, window_seconds=3600),
            # Voice messages - 10 per hour (API costs money)
            "voice_message": RateLimiter(max_requests=10, window_seconds=3600),
        }

    async def check_limit(self, user_id: int, action: str) -> Tuple[bool, Optional[int]]:
        """
        Check rate limit for a specific action.

        Args:
            user_id: User identifier
            action: Action type (general, friend_request, settings, etc.)

        Returns:
            Tuple of (is_allowed, retry_after_seconds)
        """
        limiter = self.limiters.get(action, self.limiters["general"])
        key = f"{user_id}:{action}"

        return await limiter.is_allowed(key)

    def get_usage_stats(self, user_id: int, action: str) -> Dict[str, int]:
        """Get usage statistics for a user and action."""
        limiter = self.limiters.get(action, self.limiters["general"])
        key = f"{user_id}:{action}"

        return limiter.get_usage(key)

    def cleanup_all(self) -> int:
        """Clean up all rate limiters."""
        total_cleaned = 0
        for action, limiter in self.limiters.items():
            cleaned = limiter.cleanup_old_entries()
            total_cleaned += cleaned

        return total_cleaned


# Global rate limiter instance
rate_limiter = MultiTierRateLimiter()


def rate_limit(action: str = "general", error_message: str = None):
    """
    Decorator for rate limiting function calls.

    Args:
        action: Action type for rate limiting
        error_message: Custom error message when rate limited
    """

    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Try to extract user_id from args
            user_id = None

            # Look for user_id in common argument patterns
            if args:
                # Check each argument for Update object or user_id
                for arg in args:
                    if user_id is not None:
                        break

                    # Check if arg is Update object
                    if hasattr(arg, "effective_user") and arg.effective_user:
                        user_id = arg.effective_user.id
                    # Check if it's a callback query
                    elif hasattr(arg, "callback_query") and arg.callback_query and arg.callback_query.from_user:
                        user_id = arg.callback_query.from_user.id
                    # Check if it's a message
                    elif hasattr(arg, "message") and arg.message and arg.message.from_user:
                        user_id = arg.message.from_user.id
                    elif isinstance(arg, int):
                        user_id = arg

            # Look in kwargs
            if user_id is None:
                user_id = kwargs.get("user_id") or kwargs.get("tg_id")

            if user_id is None:
                logger.warning(
                    "Rate limiting skipped - no user_id found",
                    function=func.__name__,
                    args_types=[type(arg).__name__ for arg in args[:2]] if args else [],
                )
                return await func(*args, **kwargs)

            # Check rate limit
            is_allowed, retry_after = await rate_limiter.check_limit(user_id, action)

            if not is_allowed:
                logger.warning(
                    "Rate limit exceeded", user_id=user_id, action=action, retry_after=retry_after, function=func.__name__
                )

                # Raise custom exception or return error
                from bot.utils.exceptions import RateLimitExceeded

                raise RateLimitExceeded(
                    message=error_message or f"Too many {action} requests. Try again in {retry_after} seconds.",
                    retry_after=retry_after,
                    action=action,
                )

            # Execute function if allowed
            return await func(*args, **kwargs)

        return wrapper

    return decorator


# Convenience functions for common rate limiting patterns
async def check_command_rate_limit(user_id: int) -> Tuple[bool, Optional[int]]:
    """Check rate limit for general commands."""
    return await rate_limiter.check_limit(user_id, "general")


async def check_friend_request_rate_limit(user_id: int) -> Tuple[bool, Optional[int]]:
    """Check rate limit for friend requests."""
    return await rate_limiter.check_limit(user_id, "friend_request")


async def check_discovery_rate_limit(user_id: int) -> Tuple[bool, Optional[int]]:
    """Check rate limit for friend discovery."""
    return await rate_limiter.check_limit(user_id, "discovery")


async def check_admin_rate_limit(user_id: int) -> Tuple[bool, Optional[int]]:
    """Check rate limit for admin commands."""
    return await rate_limiter.check_limit(user_id, "admin")


async def check_feedback_rate_limit(user_id: int) -> Tuple[bool, Optional[int]]:
    """Check rate limit for feedback submissions."""
    return await rate_limiter.check_limit(user_id, "feedback")


# Background cleanup task
async def cleanup_rate_limiter_task():
    """Background task to clean up old rate limiter entries."""
    while True:
        try:
            await asyncio.sleep(300)  # Clean up every 5 minutes
            cleaned = rate_limiter.cleanup_all()
            if cleaned > 0:
                logger.debug("Rate limiter background cleanup", cleaned_entries=cleaned)
        except Exception as exc:
            logger.error("Error in rate limiter cleanup task", error=str(exc))
