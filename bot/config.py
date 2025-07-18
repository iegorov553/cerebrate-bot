"""
Configuration management for Doyobi Diary.
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
    
    # Web App Configuration (should be set via environment variable)
    webapp_url: str = ""
    
    # GitHub Feedback Configuration
    github_feedback_token: Optional[str] = None
    github_repo: str = "iegorov553/cerebrate-bot"
    feedback_rate_limit: int = 3  # messages per hour
    
    # Whisper Voice Recognition Configuration
    openai_api_key: Optional[str] = None
    whisper_model: str = "whisper-1"
    max_voice_file_size_mb: int = 25
    max_voice_duration_seconds: int = 120
    
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
            
            # GitHub Feedback
            github_feedback_token=os.getenv("GITHUB_FEEDBACK_TOKEN"),
            github_repo=os.getenv("GITHUB_REPO", "iegorov553/cerebrate-bot"),
            feedback_rate_limit=int(os.getenv("FEEDBACK_RATE_LIMIT", "3")),
            
            # Whisper Voice Recognition
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            whisper_model=os.getenv("WHISPER_MODEL", "whisper-1"),
            max_voice_file_size_mb=int(os.getenv("MAX_VOICE_FILE_SIZE_MB", "25")),
            max_voice_duration_seconds=int(os.getenv("MAX_VOICE_DURATION_SECONDS", "120")),
        )
    
    def validate(self) -> None:
        """Validate required configuration."""
        if not self.bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN is required")
        if not self.supabase_url:
            raise ValueError("SUPABASE_URL is required")
        if not self.supabase_service_role_key:
            raise ValueError("SUPABASE_SERVICE_ROLE_KEY is required")
        if not self.webapp_url:
            raise ValueError("WEBAPP_URL is required")
    
    def is_admin_configured(self) -> bool:
        """Check if admin user is configured."""
        return self.admin_user_id != 0
    
    def is_monitoring_enabled(self) -> bool:
        """Check if monitoring is enabled."""
        return self.sentry_dsn is not None
    
    def is_feedback_enabled(self) -> bool:
        """Check if GitHub feedback is enabled."""
        return self.github_feedback_token is not None
    
    def is_whisper_enabled(self) -> bool:
        """Check if Whisper voice recognition is enabled."""
        return self.openai_api_key is not None