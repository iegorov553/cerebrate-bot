"""Base class for command handlers."""

from telegram import User

from bot.cache.ttl_cache import TTLCache
from bot.config import Config
from bot.database.client import DatabaseClient
from bot.database.user_operations import UserOperations
from bot.i18n import detect_user_language, get_translator
from monitoring import get_logger, set_user_context


class BaseCommandHandler:
    """Базовый класс для обработчиков команд."""
    
    def __init__(self, db_client: DatabaseClient, config: Config, user_cache: TTLCache):
        self.db_client = db_client
        self.config = config
        self.user_cache = user_cache
        self.logger = get_logger(self.__class__.__name__)
    
    def get_user_translator(self, user: User):
        """Получить переводчик для пользователя."""
        user_language = detect_user_language(user)
        translator = get_translator()
        translator.set_language(user_language)
        return translator
        
    async def ensure_user_exists(self, user: User) -> bool:
        """Убедиться что пользователь существует в БД."""
        if user is None:
            return False
            
        set_user_context(user.id, user.username, user.first_name)
        
        user_ops = UserOperations(self.db_client, self.user_cache)
        try:
            await user_ops.ensure_user_exists(
                tg_id=user.id,
                username=user.username,
                first_name=user.first_name,
                language=detect_user_language(user)
            )
            return True
        except Exception as e:
            self.logger.error(f"Failed to ensure user exists: {e}")
            return False
    
    def get_user_operations(self) -> UserOperations:
        """Получить объект для операций с пользователями."""
        return UserOperations(self.db_client, self.user_cache)