"""
Configuration management for Hour Watcher Bot.
"""
import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class Config:
    """Bot configuration class."""
    
    # Required fields (no defaults)
    bot_token: str
    supabase_url: str
    supabase_service_role_key: str
    admin_user_id: int
    
    # Optional fields (with defaults)
    question_text: str = "Чё делаешь? 🤔"
    
    # Cache Configuration
    cache_ttl_seconds: int = 300  # 5 minutes
    
    # Broadcast Configuration
    broadcast_batch_size: int = 10
    broadcast_delay_between_batches: float = 2.0
    broadcast_delay_between_messages: float = 0.1
    
    # Monitoring Configuration
    sentry_dsn: Optional[str] = None
    environment: str = "development"
    release_version: str = "unknown"
    
    # Web App Configuration
    webapp_url: str = "https://doyobi-diary.vercel.app"
    
    @classmethod
    def from_env(cls) -> "Config":
        """Create configuration from environment variables."""
        
        # Parse admin user ID safely
        try:
            admin_user_id = int(os.getenv("ADMIN_USER_ID", "0"))
        except (ValueError, TypeError):
            admin_user_id = 0
        
        return cls(
            # Required
            bot_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
            supabase_url=os.getenv("SUPABASE_URL", ""),
            supabase_service_role_key=os.getenv("SUPABASE_SERVICE_ROLE_KEY", ""),
            
            # Admin
            admin_user_id=admin_user_id,
            
            # Optional with defaults
            cache_ttl_seconds=int(os.getenv("CACHE_TTL_SECONDS", "300")),
            broadcast_batch_size=int(os.getenv("BROADCAST_BATCH_SIZE", "10")),
            broadcast_delay_between_batches=float(os.getenv("BROADCAST_DELAY_BATCHES", "2.0")),
            broadcast_delay_between_messages=float(os.getenv("BROADCAST_DELAY_MESSAGES", "0.1")),
            
            # Monitoring
            sentry_dsn=os.getenv("SENTRY_DSN"),
            environment=os.getenv("ENVIRONMENT", "development"),
            release_version=os.getenv("RELEASE_VERSION", "unknown"),
            
            # Web app
            webapp_url=os.getenv("WEBAPP_URL", "https://doyobi-diary.vercel.app"),
        )
    
    def validate(self) -> None:
        """Validate required configuration."""
        if not self.bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN is required")
        if not self.supabase_url:
            raise ValueError("SUPABASE_URL is required")
        if not self.supabase_service_role_key:
            raise ValueError("SUPABASE_SERVICE_ROLE_KEY is required")
    
    def is_admin_configured(self) -> bool:
        """Check if admin user is configured."""
        return self.admin_user_id != 0
    
    def is_monitoring_enabled(self) -> bool:
        """Check if monitoring is enabled."""
        return self.sentry_dsn is not None