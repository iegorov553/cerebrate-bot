"""
Feedback manager for handling user feedback and GitHub integration.
"""

from typing import Dict, Optional

from bot.cache.ttl_cache import TTLCache
from bot.config import Config
from bot.utils.rate_limiter import MultiTierRateLimiter
from monitoring import get_logger, track_errors_async

from .github_client import GitHubFeedbackClient

logger = get_logger(__name__)


class FeedbackManager:
    """Manages user feedback and GitHub integration."""

    def __init__(
        self,
        config: Config,
        rate_limiter: MultiTierRateLimiter,
        user_cache: TTLCache
    ):
        """
        Initialize feedback manager.

        Args:
            config: Bot configuration
            rate_limiter: Rate limiter instance
            user_cache: User cache for storing feedback sessions
        """
        self.config = config
        self.rate_limiter = rate_limiter
        self.user_cache = user_cache

        # Initialize GitHub client if token is available
        if config.is_feedback_enabled():
            self.github_client = GitHubFeedbackClient(
                token=config.github_feedback_token,
                repo=config.github_repo
            )
        else:
            self.github_client = None
            logger.warning("GitHub feedback not configured - feedback will be logged only")

    def is_enabled(self) -> bool:
        """Check if feedback system is enabled."""
        return self.config.is_feedback_enabled() and self.github_client is not None

    async def check_rate_limit(self, user_id: int) -> bool:
        """
        Check if user can send feedback.

        Args:
            user_id: Telegram user ID

        Returns:
            True if user can send feedback, False if rate limited
        """
        is_allowed, retry_after = await self.rate_limiter.check_limit(user_id, "feedback")
        return is_allowed

    @track_errors_async("feedback_session")
    async def start_feedback_session(
        self,
        user_id: int,
        feedback_type: str,
        user_language: str = "ru"
    ) -> bool:
        """
        Start a feedback session for user.

        Args:
            user_id: Telegram user ID
            feedback_type: Type of feedback (bug_report, feature_request, general)
            user_language: User's language preference

        Returns:
            True if session started, False if rate limited
        """
        # Check rate limit
        if not await self.check_rate_limit(user_id):
            logger.warning(f"User {user_id} rate limited for feedback")
            return False

        # Store feedback session in cache
        session_data = {
            "feedback_type": feedback_type,
            "user_language": user_language,
            "status": "awaiting_description"
        }

        await self.user_cache.set(
            f"feedback_session_{user_id}",
            session_data,
            ttl=3600  # 1 hour timeout for feedback session
        )

        logger.info(
            f"Started feedback session for user {user_id}",
            extra={
                "user_id": user_id,
                "feedback_type": feedback_type,
                "user_language": user_language
            }
        )

        return True

    async def get_feedback_session(self, user_id: int) -> Optional[Dict]:
        """Get active feedback session for user."""
        return await self.user_cache.get(f"feedback_session_{user_id}")

    async def clear_feedback_session(self, user_id: int) -> None:
        """Clear feedback session for user."""
        await self.user_cache.invalidate(f"feedback_session_{user_id}")

    @track_errors_async("submit_feedback")
    async def submit_feedback(
        self,
        user_id: int,
        username: Optional[str],
        description: str
    ) -> Optional[str]:
        """
        Submit user feedback to GitHub.

        Args:
            user_id: Telegram user ID
            username: Telegram username
            description: User's feedback description

        Returns:
            GitHub issue URL if successful, None if failed
        """
        # Get feedback session
        session = await self.get_feedback_session(user_id)
        if not session:
            logger.warning(f"No active feedback session for user {user_id}")
            return None

        feedback_type = session.get("feedback_type")
        user_language = session.get("user_language", "ru")

        # Clear session
        await self.clear_feedback_session(user_id)

        if not self.is_enabled():
            logger.info(
                f"Feedback submitted (GitHub disabled): {feedback_type}",
                extra={
                    "user_id": user_id,
                    "username": username,
                    "feedback_type": feedback_type,
                    "description": description[:100] + "..." if len(description) > 100 else description
                }
            )
            return None

        # Format issue based on feedback type
        if feedback_type == "bug_report":
            issue_data = self.github_client.format_bug_report(
                description, user_id, username, user_language
            )
        elif feedback_type == "feature_request":
            issue_data = self.github_client.format_feature_request(
                description, user_id, username, user_language
            )
        elif feedback_type == "general":
            issue_data = self.github_client.format_general_feedback(
                description, user_id, username, user_language
            )
        else:
            logger.error(f"Unknown feedback type: {feedback_type}")
            return None

        # Create GitHub issue
        issue_url = await self.github_client.create_issue(
            title=issue_data["title"],
            body=issue_data["body"],
            labels=issue_data["labels"],
            user_id=user_id,
            username=username
        )

        if issue_url:
            logger.info(
                f"Successfully submitted feedback to GitHub: {issue_url}",
                extra={
                    "user_id": user_id,
                    "username": username,
                    "feedback_type": feedback_type,
                    "issue_url": issue_url
                }
            )
        else:
            logger.error(
                f"Failed to submit feedback to GitHub",
                extra={
                    "user_id": user_id,
                    "username": username,
                    "feedback_type": feedback_type
                }
            )

        return issue_url