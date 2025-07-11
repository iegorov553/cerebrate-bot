"""
Multi-Question Scheduler service for Doyobi Diary.

This module handles the scheduling of notifications for multiple user questions
with individual schedules and reply tracking.
"""

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram.ext import Application

from bot.config import Config
from bot.database.client import DatabaseClient
from bot.database.user_operations import UserOperations
from bot.questions import QuestionManager
from bot.utils.cache_manager import CacheManager
from monitoring import get_logger, track_errors_async

logger = get_logger(__name__)


class MultiQuestionScheduler:
    """Manages scheduled notifications for multiple user questions."""
    
    def __init__(self, application: Application, db_client: DatabaseClient, config: Config):
        self.application = application
        self.db_client = db_client
        self.config = config
        self.scheduler = AsyncIOScheduler()
        
        # Initialize managers
        self.cache_manager = CacheManager()
        self.user_ops = UserOperations(db_client, self.cache_manager)
        self.question_manager = QuestionManager(db_client, self.cache_manager)
        
        # Track last notifications per question to avoid duplicates
        self.last_notifications: Dict[int, datetime] = {}
        
    def start(self) -> None:
        """Start the multi-question scheduler service."""
        try:
            # Schedule question notifications check every minute
            self.scheduler.add_job(
                self._check_and_send_question_notifications,
                "cron",
                minute="*",  # Every minute
                id="multi_question_check"
            )
            
            # Schedule cleanup of expired notifications at 4 AM daily
            self.scheduler.add_job(
                self._cleanup_expired_notifications,
                "cron",
                hour=4,
                minute=0,
                id="notification_cleanup"
            )
            
            # Schedule daily statistics update at 3 AM
            self.scheduler.add_job(
                self._daily_maintenance,
                "cron",
                hour=3,
                minute=0,
                id="daily_maintenance"
            )
            
            self.scheduler.start()
            logger.info("Multi-question scheduler service started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start multi-question scheduler: {e}")
            raise
    
    def stop(self) -> None:
        """Stop the scheduler service."""
        try:
            if self.scheduler.running:
                self.scheduler.shutdown()
                logger.info("Multi-question scheduler stopped")
        except Exception as e:
            logger.error(f"Error stopping scheduler: {e}")
    
    @track_errors_async("multi_question_notification_check")
    async def _check_and_send_question_notifications(self) -> None:
        """Check all active questions and send notifications as needed."""
        try:
            # Get all active users with notifications enabled
            active_users = await self.user_ops.get_all_active_users()
            
            if not active_users:
                logger.debug("No active users found")
                return
            
            current_time = datetime.now(timezone.utc)
            notifications_sent = 0
            
            for user in active_users:
                try:
                    user_id = user.get('tg_id')
                    if not user_id:
                        continue
                    
                    # Ensure user has default question
                    await self.question_manager.ensure_user_has_default_question(user_id, user)
                    
                    # Get all active questions for this user
                    user_questions = await self.question_manager.question_ops.get_active_user_questions(user_id)
                    
                    for question in user_questions:
                        if await self._should_send_question_notification(question, current_time):
                            success = await self._send_question_notification(user_id, question)
                            if success:
                                notifications_sent += 1
                                
                except Exception as e:
                    logger.error(f"Error processing user {user.get('tg_id')}: {e}")
                    continue
            
            if notifications_sent > 0:
                logger.info(f"Sent {notifications_sent} question notifications")
                    
        except Exception as e:
            logger.error(f"Error in multi-question notification check: {e}")
    
    async def _should_send_question_notification(self, question: Dict, current_time: datetime) -> bool:
        """Determine if a specific question should trigger a notification."""
        try:
            question_id = question.get('id')
            
            # Check if question is active
            if not question.get('active', False):
                return False
            
            # Check time window
            window_start_str = question.get('window_start', '09:00')
            window_end_str = question.get('window_end', '22:00')
            
            # Convert to time objects for comparison
            from datetime import time
            
            try:
                window_start = datetime.strptime(window_start_str, '%H:%M').time()
                window_end = datetime.strptime(window_end_str, '%H:%M').time()
            except ValueError:
                # Fallback for time with seconds
                try:
                    window_start = datetime.strptime(window_start_str, '%H:%M:%S').time()
                    window_end = datetime.strptime(window_end_str, '%H:%M:%S').time()
                except ValueError:
                    logger.warning(f"Invalid time format for question {question_id}")
                    return False
            
            current_time_only = current_time.time()
            
            # Handle cases where end time is next day (e.g., 22:00 - 06:00)
            if window_start <= window_end:
                # Normal case: 09:00 - 18:00
                if not (window_start <= current_time_only <= window_end):
                    return False
            else:
                # Overnight case: 22:00 - 06:00
                if not (current_time_only >= window_start or current_time_only <= window_end):
                    return False
            
            # Check interval since last notification for this specific question
            interval_minutes = question.get('interval_minutes', 120)
            
            # Check our local tracking
            last_notification = self.last_notifications.get(question_id)
            if last_notification:
                time_since_last = (current_time - last_notification).total_seconds() / 60
                if time_since_last < interval_minutes:
                    return False
            
            # Additional check: get actual last notification from database
            # This prevents duplicate notifications across bot restarts
            last_db_notification = await self._get_last_notification_for_question(question_id)
            if last_db_notification:
                # Function _get_last_notification_for_question now always returns timezone-aware datetime
                time_since_db = (current_time - last_db_notification).total_seconds() / 60
                if time_since_db < interval_minutes:
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking notification conditions for question {question.get('id')}: {e}")
            return False
    
    async def _get_last_notification_for_question(self, question_id: int) -> Optional[datetime]:
        """Get the last notification time for a specific question."""
        try:
            result = self.question_manager.question_ops.db_client.table('question_notifications')\
                .select('sent_at')\
                .eq('question_id', question_id)\
                .order('sent_at', desc=True)\
                .limit(1)\
                .execute()
            
            if result.data and len(result.data) > 0:
                sent_at_str = result.data[0]['sent_at']
                # Handle different datetime formats
                try:
                    return datetime.fromisoformat(sent_at_str.replace('Z', '+00:00'))
                except ValueError:
                    # Try parsing as ISO format without timezone, then add UTC
                    dt = datetime.fromisoformat(sent_at_str)
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    return dt
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting last notification for question {question_id}: {e}")
            return None
    
    @track_errors_async("send_question_notification")
    async def _send_question_notification(self, user_id: int, question: Dict) -> bool:
        """Send notification for a specific question."""
        try:
            question_id = question.get('id')
            question_text = question.get('question_text', 'Что делаешь?')
            
            # Apply template variables
            formatted_text = await self._format_question_text(question_text, user_id)
            
            # Send the notification
            message = await self.application.bot.send_message(
                chat_id=user_id,
                text=formatted_text
            )
            
            # Save notification for reply tracking
            await self.question_manager.save_notification_for_reply(
                user_id, question_id, message.message_id
            )
            
            # Update our local tracking
            self.last_notifications[question_id] = datetime.now()
            
            logger.info(f"Question notification sent", 
                       user_id=user_id, 
                       question_id=question_id,
                       message_id=message.message_id)
            
            return True
            
        except Exception as e:
            logger.error(f"Error sending question notification: {e}", 
                        user_id=user_id, 
                        question_id=question.get('id'))
            return False
    
    async def _format_question_text(self, question_text: str, user_id: int) -> str:
        """Format question text with template variables."""
        try:
            # Get user info for formatting
            user_result = self.user_ops.db.table('users')\
                .select('tg_first_name')\
                .eq('tg_id', user_id)\
                .single()\
                .execute()
            
            user_name = "друг"  # Default fallback
            if user_result.data:
                user_name = user_result.data.get('tg_first_name', 'друг')
            
            # Current time for {time} variable
            current_time = datetime.now().strftime('%H:%M')
            
            # Apply template variables
            formatted_text = question_text.replace('{name}', user_name)
            formatted_text = formatted_text.replace('{time}', current_time)
            
            return formatted_text
            
        except Exception as e:
            logger.error(f"Error formatting question text: {e}")
            # Return original text if formatting fails
            return question_text
    
    @track_errors_async("cleanup_expired_notifications")
    async def _cleanup_expired_notifications(self) -> None:
        """Clean up expired notification records."""
        try:
            logger.info("Starting cleanup of expired notifications")
            
            # Use the question manager's cleanup method
            deleted_count = await self.question_manager.question_ops.cleanup_expired_notifications()
            
            logger.info(f"Cleaned up {deleted_count} expired notifications")
            
        except Exception as e:
            logger.error(f"Error cleaning up expired notifications: {e}")
    
    @track_errors_async("daily_maintenance")
    async def _daily_maintenance(self) -> None:
        """Perform daily maintenance tasks."""
        try:
            logger.info("Starting daily maintenance")
            
            # Clear local notification tracking (reset daily)
            self.last_notifications.clear()
            
            # Add other maintenance tasks here:
            # - Clean old cache entries
            # - Archive old activities
            # - Update statistics
            # - Ensure all users have default questions
            
            # Ensure all active users have default questions
            active_users = await self.user_ops.get_all_active_users()
            default_questions_created = 0
            
            for user in active_users:
                user_id = user.get('tg_id')
                if user_id:
                    try:
                        # This will create default question if missing
                        await self.question_manager.ensure_user_has_default_question(user_id, user)
                        default_questions_created += 1
                    except Exception as e:
                        logger.error(f"Error ensuring default question for user {user_id}: {e}")
            
            logger.info(f"Daily maintenance completed. Processed {default_questions_created} users.")
            
        except Exception as e:
            logger.error(f"Error in daily maintenance: {e}")
    
    async def reschedule_user_questions(self, user_id: int) -> None:
        """Reschedule notifications for a specific user (useful after question changes)."""
        try:
            # Clear any cached tracking for this user's questions
            user_questions = await self.question_manager.question_ops.get_active_user_questions(user_id)
            
            for question in user_questions:
                question_id = question.get('id')
                if question_id in self.last_notifications:
                    del self.last_notifications[question_id]
            
            logger.info(f"Rescheduled notifications for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error rescheduling user questions: {e}")


# Factory function for creating the scheduler
def create_multi_question_scheduler(
    application: Application, 
    db_client: DatabaseClient, 
    config: Config
) -> MultiQuestionScheduler:
    """Create and configure the multi-question scheduler."""
    return MultiQuestionScheduler(application, db_client, config)