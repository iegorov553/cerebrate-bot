"""
Custom exceptions for Doyobi Diary.
"""


class BotError(Exception):
    """Base exception for bot-related errors."""

    pass


class DatabaseError(BotError):
    """Exception raised for database-related errors."""

    pass


class ValidationError(BotError):
    """Exception raised for validation errors."""

    pass


class RateLimitExceeded(BotError):
    """Exception raised when rate limit is exceeded."""

    def __init__(self, message: str, retry_after: int, action: str):
        self.message = message
        self.retry_after = retry_after
        self.action = action
        super().__init__(self.message)


class AdminRequired(BotError):
    """Exception raised when admin access is required."""

    pass


class UserNotFound(BotError):
    """Exception raised when user is not found."""

    pass


class FriendshipError(BotError):
    """Exception raised for friendship-related errors."""

    pass
