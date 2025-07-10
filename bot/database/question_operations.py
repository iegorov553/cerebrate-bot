"""
Database operations for user questions system.

This module handles CRUD operations for custom user questions with versioning support.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from monitoring import get_logger, track_errors_async

logger = get_logger(__name__)


class QuestionOperations:
    """Handles database operations for user questions."""
    
    def __init__(self, db_client, cache=None):
        """
        Initialize question operations.
        
        Args:
            db_client: Database client instance
            cache: Optional cache instance
        """
        self.db_client = db_client
        self.cache = cache
    
    @track_errors_async("get_active_user_questions")
    async def get_active_user_questions(self, user_id: int) -> List[Dict]:
        """
        Get all active questions for a user.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            List of active question dictionaries
        """
        try:
            result = self.db_client.table('user_questions')\
                .select('*')\
                .eq('user_id', user_id)\
                .eq('active', True)\
                .order('is_default', desc=True)\
                .order('created_at')\
                .execute()
            
            return result.data if result.data else []
            
        except Exception as e:
            logger.error(f"Error getting active questions for user {user_id}: {e}")
            return []
    
    @track_errors_async("get_active_default_question")
    async def get_active_default_question(self, user_id: int) -> Optional[Dict]:
        """
        Get the active default question for a user.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            Default question dictionary or None
        """
        try:
            result = self.db_client.table('user_questions')\
                .select('*')\
                .eq('user_id', user_id)\
                .eq('is_default', True)\
                .eq('active', True)\
                .single()\
                .execute()
            
            return result.data if result.data else None
            
        except Exception as e:
            logger.error(f"Error getting default question for user {user_id}: {e}")
            return None
    
    @track_errors_async("get_question_by_id")
    async def get_question_by_id(self, question_id: int) -> Optional[Dict]:
        """
        Get question by ID.
        
        Args:
            question_id: Question ID
            
        Returns:
            Question dictionary or None
        """
        try:
            result = self.db_client.table('user_questions')\
                .select('*')\
                .eq('id', question_id)\
                .single()\
                .execute()
            
            return result.data if result.data else None
            
        except Exception as e:
            logger.error(f"Error getting question {question_id}: {e}")
            return None
    
    @track_errors_async("create_question")
    async def create_question(self, question_data: Dict) -> Optional[Dict]:
        """
        Create a new question.
        
        Args:
            question_data: Question data dictionary
            
        Returns:
            Created question dictionary or None
        """
        try:
            result = self.db_client.table('user_questions')\
                .insert(question_data)\
                .execute()
            
            if result.data and len(result.data) > 0:
                logger.info(f"Created question for user {question_data.get('user_id')}: {question_data.get('question_name')}")
                return result.data[0]
            
            return None
            
        except Exception as e:
            logger.error(f"Error creating question: {e}")
            return None
    
    @track_errors_async("update_question")
    async def update_question(self, question_id: int, updates: Dict) -> bool:
        """
        Update question data.
        
        Args:
            question_id: Question ID
            updates: Dictionary of fields to update
            
        Returns:
            True if successful
        """
        try:
            result = self.db_client.table('user_questions')\
                .update(updates)\
                .eq('id', question_id)\
                .execute()
            
            success = result.data is not None
            if success:
                logger.info(f"Updated question {question_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error updating question {question_id}: {e}")
            return False
    
    @track_errors_async("update_question_text")
    async def update_question_text(self, question_id: int, new_text: str) -> Optional[int]:
        """
        Update question text by creating new version and deactivating old.
        
        Args:
            question_id: Current question ID
            new_text: New question text
            
        Returns:
            New question ID or None if failed
        """
        try:
            # Get current question
            old_question = await self.get_question_by_id(question_id)
            if not old_question:
                logger.error(f"Question {question_id} not found")
                return None
            
            # Check if text actually changed
            if old_question['question_text'] == new_text:
                return question_id  # No change needed
            
            # Deactivate old question
            await self.update_question(question_id, {
                'active': False,
                'is_default': False if old_question['is_default'] else old_question['is_default']
            })
            
            # Create new version
            new_question_data = {
                'user_id': old_question['user_id'],
                'question_name': old_question['question_name'],
                'question_text': new_text,
                'window_start': old_question['window_start'],
                'window_end': old_question['window_end'],
                'interval_minutes': old_question['interval_minutes'],
                'is_default': old_question['is_default'],
                'active': True,
                'parent_question_id': question_id
            }
            
            new_question = await self.create_question(new_question_data)
            
            if new_question:
                logger.info(f"Created new version of question {question_id} -> {new_question['id']}")
                return new_question['id']
            
            return None
            
        except Exception as e:
            logger.error(f"Error updating question text {question_id}: {e}")
            return None
    
    @track_errors_async("delete_question")
    async def delete_question(self, question_id: int) -> bool:
        """
        Delete (deactivate) a question.
        
        Args:
            question_id: Question ID
            
        Returns:
            True if successful
        """
        try:
            # Just deactivate, don't actually delete for history preservation
            success = await self.update_question(question_id, {'active': False})
            
            if success:
                logger.info(f"Deactivated question {question_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error deleting question {question_id}: {e}")
            return False
    
    @track_errors_async("save_notification")
    async def save_notification(
        self, 
        user_id: int, 
        question_id: int, 
        telegram_message_id: int
    ) -> bool:
        """
        Save notification record for reply tracking.
        
        Args:
            user_id: Telegram user ID
            question_id: Question ID
            telegram_message_id: Telegram message ID
            
        Returns:
            True if successful
        """
        try:
            notification_data = {
                'user_id': user_id,
                'question_id': question_id,
                'telegram_message_id': telegram_message_id,
                'sent_at': datetime.now().isoformat(),
                'expires_at': (datetime.now() + timedelta(days=90)).isoformat()  # 3 months
            }
            
            result = self.db_client.table('question_notifications')\
                .insert(notification_data)\
                .execute()
            
            success = result.data is not None
            if success:
                logger.debug(f"Saved notification for user {user_id}, message {telegram_message_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error saving notification: {e}")
            return False
    
    @track_errors_async("get_notification_by_message_id")
    async def get_notification_by_message_id(
        self, 
        user_id: int, 
        telegram_message_id: int
    ) -> Optional[Dict]:
        """
        Get notification by telegram message ID.
        
        Args:
            user_id: Telegram user ID
            telegram_message_id: Telegram message ID
            
        Returns:
            Notification dictionary or None
        """
        try:
            result = self.db_client.table('question_notifications')\
                .select('*, user_questions(*)')\
                .eq('user_id', user_id)\
                .eq('telegram_message_id', telegram_message_id)\
                .gt('expires_at', datetime.now().isoformat())\
                .order('sent_at', desc=True)\
                .limit(1)\
                .execute()
            
            if result.data and len(result.data) > 0:
                return result.data[0]
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting notification for message {telegram_message_id}: {e}")
            return None
    
    @track_errors_async("cleanup_expired_notifications")
    async def cleanup_expired_notifications(self) -> int:
        """
        Clean up expired notifications.
        
        Returns:
            Number of deleted notifications
        """
        try:
            # Get count before deletion
            count_result = self.db_client.table('question_notifications')\
                .select('id', count='exact')\
                .lt('expires_at', datetime.now().isoformat())\
                .execute()
            
            count_before = count_result.count if count_result.count else 0
            
            # Delete expired notifications
            self.db_client.table('question_notifications')\
                .delete()\
                .lt('expires_at', datetime.now().isoformat())\
                .execute()
            
            logger.info(f"Cleaned up {count_before} expired notifications")
            return count_before
            
        except Exception as e:
            logger.error(f"Error cleaning up notifications: {e}")
            return 0
    
    @track_errors_async("get_user_questions_stats")
    async def get_user_questions_stats(self, user_id: int) -> Dict:
        """
        Get statistics about user's questions.
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            Statistics dictionary
        """
        try:
            # Get active questions count
            active_result = self.db_client.table('user_questions')\
                .select('id', count='exact')\
                .eq('user_id', user_id)\
                .eq('active', True)\
                .execute()
            
            # Get total activities for active questions
            activities_result = self.db_client.table('tg_jobs')\
                .select('id', count='exact')\
                .eq('tg_id', user_id)\
                .not_.is_('question_id', 'null')\
                .execute()
            
            return {
                'active_questions': active_result.count if active_result.count else 0,
                'total_activities': activities_result.count if activities_result.count else 0,
                'max_questions': 5  # 1 default + 4 custom
            }
            
        except Exception as e:
            logger.error(f"Error getting question stats for user {user_id}: {e}")
            return {
                'active_questions': 0,
                'total_activities': 0,
                'max_questions': 5
            }