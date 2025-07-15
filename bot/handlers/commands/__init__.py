"""Command handlers module for Doyobi Diary bot."""

from .config_commands import setup_config_commands
from .history_commands import setup_history_commands
from .social_commands import setup_social_commands
from .system_commands import setup_system_commands
from .user_commands import setup_user_commands

__all__ = [
    "setup_user_commands",
    "setup_social_commands",
    "setup_config_commands",
    "setup_history_commands",
    "setup_system_commands",
]
