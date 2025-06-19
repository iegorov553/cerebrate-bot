"""
Database client setup and configuration.
"""
from supabase import create_client, Client

from bot.config import Config
from monitoring import get_logger

logger = get_logger(__name__)


class DatabaseClient:
    """Wrapper for Supabase client with additional functionality."""
    
    def __init__(self, config: Config):
        self.config = config
        self._client: Client = None
        self._initialize_client()
    
    def _initialize_client(self) -> None:
        """Initialize Supabase client."""
        try:
            self._client = create_client(
                self.config.supabase_url,
                self.config.supabase_service_role_key
            )
            logger.info("Database client initialized successfully")
        except Exception as e:
            logger.error("Failed to initialize database client", error=str(e))
            raise
    
    @property
    def client(self) -> Client:
        """Get the Supabase client."""
        if self._client is None:
            self._initialize_client()
        return self._client
    
    def table(self, table_name: str):
        """Get a table reference."""
        return self.client.table(table_name)
    
    def health_check(self) -> bool:
        """Check if database connection is healthy."""
        try:
            # Simple query to check connectivity
            result = self.table("users").select("tg_id").limit(1).execute()
            return True
        except Exception as e:
            logger.error("Database health check failed", error=str(e))
            return False