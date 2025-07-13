"""
Telegram bot handlers for Doyobi Diary.
"""

from .error_handler import setup_error_handler
from .rate_limit_handler import handle_rate_limit_error

__all__ = [
    "setup_error_handler",
    "handle_rate_limit_error"
]
