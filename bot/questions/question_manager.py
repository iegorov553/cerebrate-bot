"""
Question Manager for handling custom user questions.

This module provides high-level business logic for managing user questions,
including versioning, validation, and reply tracking.
"""

from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

from bot.database.question_operations import QuestionOperations
from monitoring import get_logger, track_errors_async

logger = get_logger(__name__)


def safe_parse_datetime(datetime_str: str) -> Optional[datetime]:
    """
    Safely parse datetime string with various formats and timezone handling.

    Args:
        datetime_str: DateTime string in various formats

    Returns:
        Parsed datetime object or None if parsing fails
    """
    if not datetime_str:
        return None

    try:
        # Handle different timezone formats
        if datetime_str.endswith('Z'):
            # Convert Z to +00:00 for ISO format compatibility
            datetime_str = datetime_str[:-1] + '+00:00'
        elif datetime_str.endswith('+00:00') or datetime_str.endswith('-00:00'):
            # Already has timezone info
            pass
        elif '+' not in datetime_str and '-' not in datetime_str[-6:]:
            # No timezone info, assume UTC
            datetime_str += '+00:00'

        # Try parsing with timezone info
        return datetime.fromisoformat(datetime_str)

    except ValueError:
        try:
            # Fallback: try parsing without timezone, then make it UTC
            parsed = datetime.fromisoformat(datetime_str.replace('Z', ''))
            return parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            logger.warning(f"Failed to parse datetime string: {datetime_str}")
            return None


class QuestionManager:
    """High-level manager for user questions."""

    def __init__(self, db_client, cache=None):
        """
        Initialize question manager.

        Args:
            db_client: Database client instance
            cache: Optional cache instance
        """
        self.question_ops = QuestionOperations(db_client, cache)
        self.cache = cache

    @track_errors_async("ensure_user_has_default_question")
    async def ensure_user_has_default_question(self, user_id: int, user_data: Dict = None) -> bool:
        """
        Ensure user has a default question, create if missing.

        Args:
            user_id: Telegram user ID
            user_data: Optional user data from users table

        Returns:
            True if default question exists or was created
        """
        try:
            # Check if user already has default question
            default_question = await self.question_ops.get_active_default_question(user_id)
            if default_question:
                return True

            # Create default question from user data or defaults
            default_data = {
                'user_id': user_id,
                'question_name': 'Основной',
                'question_text': '⏰ Время отчёта! Что делаешь?',
                'window_start': user_data.get('window_start', '09:00') if user_data else '09:00',
                'window_end': user_data.get('window_end', '22:00') if user_data else '22:00',
                'interval_minutes': user_data.get('interval_min', 120) if user_data else 120,
                'is_default': True,
                'active': True
            }

            created_question = await self.question_ops.create_question(default_data)

            if created_question:
                logger.info(f"Created default question for user {user_id}")
                return True

            return False

        except Exception as e:
            logger.error(f"Error ensuring default question for user {user_id}: {e}")
            return False

    @track_errors_async("determine_question_for_message")
    async def determine_question_for_message(
        self,
        user_id: int,
        reply_to_message_id: Optional[int] = None
    ) -> Tuple[Optional[int], str]:
        """
        Determine which question a message should be linked to.

        Args:
            user_id: Telegram user ID
            reply_to_message_id: Optional reply to message ID

        Returns:
            Tuple of (question_id, status_message)
        """
        try:
            # Check for reply to notification
            if reply_to_message_id:
                notification = await self.question_ops.get_notification_by_message_id(
                    user_id, reply_to_message_id
                )

                if notification:
                    # Check if notification is still valid
                    now = datetime.now(timezone.utc)
                    expires_at = safe_parse_datetime(notification['expires_at'])

                    if expires_at and expires_at > now:
                        # Valid notification
                        return notification['question_id'], "reply_success"
                    else:
                        # Expired notification, check if question is still active
                        question = notification.get('user_questions')
                        if question and question.get('active'):
                            # Question active but notification old
                            default_question = await self.question_ops.get_active_default_question(user_id)
                            return default_question['id'] if default_question else None, "old_notification_active_question"
                        else:
                            # Both notification and question are old
                            default_question = await self.question_ops.get_active_default_question(user_id)
                            return default_question['id'] if default_question else None, "old_notification_inactive_question"

            # No reply or notification not found - use default question
            default_question = await self.question_ops.get_active_default_question(user_id)
            if default_question:
                return default_question['id'], "default_question"

            # No default question - ensure user has one
            await self.ensure_user_has_default_question(user_id)
            default_question = await self.question_ops.get_active_default_question(user_id)

            return default_question['id'] if default_question else None, "default_question"

        except Exception as e:
            logger.error(f"Error determining question for message: {e}")
            return None, "error"

    @track_errors_async("create_custom_question")
    async def create_custom_question(
        self,
        user_id: int,
        question_data: Dict
    ) -> Optional[Dict]:
        """
        Create a new custom question with validation.

        Args:
            user_id: Telegram user ID
            question_data: Question data dictionary

        Returns:
            Created question or None if failed
        """
        try:
            # Validate user hasn't exceeded question limit
            user_questions = await self.question_ops.get_active_user_questions(user_id)
            active_count = len(user_questions)

            if active_count >= 5:  # 1 default + 4 custom
                logger.warning(f"User {user_id} has reached question limit ({active_count}/5)")
                return None

            # Validate question data
            if not self._validate_question_data(question_data):
                return None

            # Ensure question is not default (only one default allowed)
            question_data['is_default'] = False
            question_data['user_id'] = user_id
            question_data['active'] = True

            # Check for name conflicts
            for existing in user_questions:
                if existing['question_name'] == question_data['question_name']:
                    logger.warning(f"Question name '{question_data['question_name']}' already exists for user {user_id}")
                    return None

            return await self.question_ops.create_question(question_data)

        except Exception as e:
            logger.error(f"Error creating custom question: {e}")
            return None

    @track_errors_async("update_question_settings")
    async def update_question_settings(
        self,
        question_id: int,
        settings: Dict
    ) -> bool:
        """
        Update question settings (non-text fields).

        Args:
            question_id: Question ID
            settings: Settings to update

        Returns:
            True if successful
        """
        try:
            # Validate settings
            if not self._validate_question_settings(settings):
                return False

            # Remove text field if present (use update_question_text for that)
            settings = {k: v for k, v in settings.items() if k != 'question_text'}

            return await self.question_ops.update_question(question_id, settings)

        except Exception as e:
            logger.error(f"Error updating question settings: {e}")
            return False

    @track_errors_async("update_question_text_with_versioning")
    async def update_question_text_with_versioning(
        self,
        question_id: int,
        new_text: str
    ) -> Optional[int]:
        """
        Update question text, creating new version if needed.

        Args:
            question_id: Current question ID
            new_text: New question text

        Returns:
            New question ID or original if no change
        """
        try:
            if not new_text or len(new_text.strip()) == 0:
                logger.warning("Cannot update question with empty text")
                return None

            if len(new_text) > 500:
                logger.warning("Question text too long (max 500 characters)")
                return None

            return await self.question_ops.update_question_text(question_id, new_text.strip())

        except Exception as e:
            logger.error(f"Error updating question text: {e}")
            return None

    @track_errors_async("toggle_question_status")
    async def toggle_question_status(self, question_id: int) -> Tuple[bool, bool]:
        """
        Toggle question active/inactive status.

        Args:
            question_id: Question ID

        Returns:
            Tuple of (success, new_status)
        """
        try:
            question = await self.question_ops.get_question_by_id(question_id)
            if not question:
                return False, False

            # Cannot deactivate default questions
            if question['is_default']:
                logger.warning(f"Cannot deactivate default question {question_id}")
                return False, question['active']

            new_status = not question['active']
            success = await self.question_ops.update_question(question_id, {'active': new_status})

            return success, new_status

        except Exception as e:
            logger.error(f"Error toggling question status: {e}")
            return False, False

    @track_errors_async("save_notification_for_reply")
    async def save_notification_for_reply(
        self,
        user_id: int,
        question_id: int,
        telegram_message_id: int
    ) -> bool:
        """
        Save notification for later reply tracking.

        Args:
            user_id: Telegram user ID
            question_id: Question ID
            telegram_message_id: Telegram message ID

        Returns:
            True if successful
        """
        try:
            return await self.question_ops.save_notification(
                user_id, question_id, telegram_message_id
            )

        except Exception as e:
            logger.error(f"Error saving notification: {e}")
            return False

    @track_errors_async("get_user_questions_summary")
    async def get_user_questions_summary(self, user_id: int) -> Dict:
        """
        Get summary of user's questions and stats.

        Args:
            user_id: Telegram user ID

        Returns:
            Summary dictionary
        """
        try:
            questions = await self.question_ops.get_active_user_questions(user_id)
            stats = await self.question_ops.get_user_questions_stats(user_id)

            # Separate default and custom questions
            default_question = None
            custom_questions = []

            for q in questions:
                if q['is_default']:
                    default_question = q
                else:
                    custom_questions.append(q)

            return {
                'default_question': default_question,
                'custom_questions': custom_questions,
                'stats': stats,
                'can_add_more': len(questions) < 5
            }

        except Exception as e:
            logger.error(f"Error getting user questions summary: {e}")
            return {
                'default_question': None,
                'custom_questions': [],
                'stats': {'active_questions': 0, 'total_activities': 0, 'max_questions': 5},
                'can_add_more': True
            }

    def _validate_question_data(self, data: Dict) -> bool:
        """Validate question data."""
        required_fields = ['question_name', 'question_text', 'window_start', 'window_end', 'interval_minutes']

        for field in required_fields:
            if field not in data:
                logger.warning(f"Missing required field: {field}")
                return False

        # Validate text length
        if len(data['question_text'].strip()) == 0 or len(data['question_text']) > 500:
            logger.warning("Invalid question text length")
            return False

        # Validate name length
        if len(data['question_name'].strip()) == 0 or len(data['question_name']) > 100:
            logger.warning("Invalid question name length")
            return False

        # Validate interval
        if data['interval_minutes'] < 30:
            logger.warning("Interval too small (minimum 30 minutes)")
            return False

        return True

    def _validate_question_settings(self, settings: Dict) -> bool:
        """Validate question settings."""
        if 'interval_minutes' in settings and settings['interval_minutes'] < 30:
            logger.warning("Interval too small (minimum 30 minutes)")
            return False

        if 'question_name' in settings and (
            len(settings['question_name'].strip()) == 0
            or len(settings['question_name']) > 100
        ):
            logger.warning("Invalid question name length")
            return False

        return True
