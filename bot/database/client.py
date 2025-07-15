"""
Database client setup and configuration.
"""
from supabase import Client, create_client

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
            self._client = create_client(self.config.supabase_url, self.config.supabase_service_role_key)
            logger.info("Database client initialized successfully")

            # Test connection
            if not self.health_check():
                logger.warning("Database health check failed on initialization")

        except Exception as e:
            logger.error("Failed to initialize database client", error=str(e))
            # Don't raise here - allow graceful degradation
            self._client = None

    @property
    def client(self) -> Client:
        """Get the Supabase client."""
        if self._client is None:
            self._initialize_client()

        if self._client is None:
            raise ConnectionError("Database client not available. Check your Supabase configuration.")

        return self._client

    def table(self, table_name: str):
        """Get a table reference."""
        try:
            return self.client.table(table_name)
        except ConnectionError:
            logger.error(f"Cannot access table '{table_name}' - database not connected")
            raise

    def is_connected(self) -> bool:
        """Check if database is connected."""
        return self._client is not None

    def health_check(self) -> bool:
        """Check if database connection is healthy."""
        try:
            # Simple query to check connectivity
            self.table("users").select("tg_id").limit(1).execute()
            return True
        except Exception as e:
            logger.error("Database health check failed", error=str(e))
            return False
