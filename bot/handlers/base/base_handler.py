"""
Base callback handler class with common functionality.

This module provides the foundational BaseCallbackHandler class that all
specialized callback handlers inherit from. It contains shared utilities,
error handling, and dependency management.
"""

from typing import Any, Dict
from abc import ABC, abstractmethod

from telegram import CallbackQuery, User
from telegram.ext import ContextTypes

from bot.cache.ttl_cache import TTLCache
from bot.config import Config
from bot.database.client import DatabaseClient
from bot.i18n.translator import Translator
from monitoring import get_logger, set_user_context, track_errors_async


logger = get_logger(__name__)


class BaseCallbackHandler(ABC):
    """
    Base class for all callback handlers.

    Provides common functionality like user language detection,
    translator setup, dependency injection, and error handling.
    """

    def __init__(self, 
                 db_client: DatabaseClient, 
                 config: Config, 
                 user_cache: TTLCache):
        """Initialize base handler with dependencies."""
        self.db_client = db_client
        self.config = config
        self.user_cache = user_cache
        self.logger = get_logger(self.__class__.__name__)

    async def get_user_language(self, 
                              user_id: int, 
                              force_refresh: bool = False) -> str:
        """
        Get user language from database with fallback.

        Args:
            user_id: Telegram user ID
            force_refresh: Whether to bypass cache

        Returns:
            User's preferred language code (ru/en/es)
        """
        try:
            from bot.database.user_operations import UserOperations
            user_ops = UserOperations(self.db_client, self.user_cache)
            user_data = await user_ops.get_user_settings(
                user_id, 
                force_refresh=force_refresh
            )

            if user_data and 'language' in user_data:
                language = user_data['language']
                self.logger.debug("Retrieved user language", 
                                user_id=user_id, 
                                language=language,
                                from_cache=not force_refresh)
                return language

        except Exception as e:
            self.logger.warning("Failed to get user language", 
                              user_id=user_id, 
                              error=str(e))

        # Fallback to default
        self.logger.debug("Using default language fallback", user_id=user_id)
        return 'ru'

    async def get_user_translator(self, 
                                user_id: int, 
                                force_refresh: bool = False) -> Translator:
        """
        Get translator configured for user's language.

        Args:
            user_id: Telegram user ID
            force_refresh: Whether to bypass cache

        Returns:
            Configured Translator instance
        """
        user_language = await self.get_user_language(user_id, force_refresh)

        # Create a fresh translator instance to avoid modifying global state
        translator = Translator()
        translator.set_language(user_language)

        self.logger.debug("Created user translator", 
                         user_id=user_id, 
                         language=user_language)
        return translator

    def setup_user_context(self, user: User) -> None:
        """Set up monitoring context for the user."""
        set_user_context(user.id, user.username, user.first_name)
        self.logger.debug("User context set up", 
                         user_id=user.id, 
                         username=user.username)

    async def ensure_user_exists(self, user: User) -> Dict[str, Any]:
        """
        Ensure user exists in database, create if needed.

        Args:
            user: Telegram user object

        Returns:
            User data from database
        """
        try:
            from bot.database.user_operations import UserOperations
            user_ops = UserOperations(self.db_client, self.user_cache)

            user_data = await user_ops.ensure_user_exists(
                tg_id=user.id,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name
            )

            self.logger.debug("User ensured in database", user_id=user.id)
            return user_data

        except Exception as e:
            self.logger.error("Failed to ensure user exists", 
                            user_id=user.id, 
                            error=str(e))
            raise

    @track_errors_async("callback_handler_execute")
    async def execute(self, 
                     query: CallbackQuery, 
                     data: str, 
                     context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Main execution method for callback handling.

        Args:
            query: Telegram callback query
            data: Callback data string
            context: Bot context
        """
        user = query.from_user
        if not user:
            self.logger.warning("No user in callback query")
            return

        # Set up monitoring context
        self.setup_user_context(user)

        # Ensure user exists in database
        await self.ensure_user_exists(user)

        # Get translator for user's language
        force_refresh = self.should_force_language_refresh(data)
        translator = await self.get_user_translator(user.id, force_refresh)

        try:
            # Call the specific handler implementation
            await self.handle_callback(query, data, translator, context)

        except Exception as e:
            self.logger.error("Error in callback handler", 
                            user_id=user.id, 
                            callback_data=data, 
                            error=str(e))

            # Try to send error message to user
            try:
                error_text = translator.translate('errors.general_error')
                await query.edit_message_text(
                    text=error_text,
                    parse_mode='HTML'
                )
            except Exception as edit_error:
                self.logger.error("Failed to send error message", 
                                error=str(edit_error))

            raise

    def should_force_language_refresh(self, data: str) -> bool:
        """
        Determine if language cache should be refreshed.

        Args:
            data: Callback data string

        Returns:
            True if cache should be bypassed
        """
        return (data.startswith("language_") 
                or data == "menu_language")

    @abstractmethod
    async def handle_callback(self, 
                            query: CallbackQuery, 
                            data: str, 
                            translator: Translator, 
                            context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handle the specific callback query.

        This method must be implemented by each specialized handler.

        Args:
            query: Telegram callback query
            data: Callback data string
            translator: Configured translator for user's language
            context: Bot context
        """
        pass

    def can_handle(self, data: str) -> bool:
        """
        Check if this handler can process the given callback data.

        Args:
            data: Callback data string

        Returns:
            True if this handler can process the callback
        """
        # Default implementation - override in subclasses
        return False