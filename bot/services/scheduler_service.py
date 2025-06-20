"""
Scheduler service for Hour Watcher Bot.

This module handles the scheduling of notifications and periodic tasks.
"""

import asyncio
from datetime import datetime, time, timezone
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram.ext import Application

from bot.config import Config
from bot.database.client import DatabaseClient
from bot.database.user_operations import UserOperations
from bot.utils.cache_manager import CacheManager
from monitoring import get_logger, track_errors_async

logger = get_logger(__name__)


class SchedulerService:
    """Manages scheduled tasks for the bot."""
    
    def __init__(self, application: Application, db_client: DatabaseClient, config: Config):
        self.application = application
        self.db_client = db_client
        self.config = config
        self.scheduler = AsyncIOScheduler()
        # Initialize cache manager for user operations
        self.cache_manager = CacheManager()
        self.user_ops = UserOperations(db_client, self.cache_manager)
        
    def start(self) -> None:
        """Start the scheduler service."""
        try:
            # Schedule notification checks every minute
            self.scheduler.add_job(
                self._check_and_send_notifications,
                "cron",
                minute="*",  # Every minute
                id="notification_check"
            )
            
            # Schedule daily cleanup at 3 AM
            self.scheduler.add_job(
                self._daily_cleanup,
                "cron",
                hour=3,
                minute=0,
                id="daily_cleanup"
            )
            
            self.scheduler.start()
            logger.info("Scheduler service started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start scheduler service: {e}")
            raise
    
    def stop(self) -> None:
        """Stop the scheduler service."""
        try:
            if self.scheduler.running:
                self.scheduler.shutdown()
                logger.info("Scheduler service stopped")
        except Exception as e:
            logger.error(f"Error stopping scheduler service: {e}")
    
    @track_errors_async("notification_check")
    async def _check_and_send_notifications(self) -> None:
        """Check which users need notifications and send them."""
        try:
            # Get all active users
            active_users = await self.user_ops.get_all_active_users()
            
            if not active_users:
                logger.debug("No active users found")
                return
            
            current_time = datetime.now()
            
            for user in active_users:
                try:
                    if await self._should_send_notification(user, current_time):
                        await self._send_notification_to_user(user)
                        
                except Exception as e:
                    logger.error(f"Error processing user {user.get('tg_id')}: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error in notification check: {e}")
    
    async def _should_send_notification(self, user: dict, current_time: datetime) -> bool:
        """Determine if a user should receive a notification."""
        try:
            tg_id = user.get('tg_id')
            
            # Check if notifications are enabled
            if not user.get('enabled', False):
                return False
            
            # Check time window
            window_start = user.get('window_start', '09:00:00')
            window_end = user.get('window_end', '22:00:00')
            
            current_time_str = current_time.time().strftime('%H:%M:%S')
            
            if not (window_start <= current_time_str <= window_end):
                logger.debug(f"User {tg_id} outside time window")
                return False
            
            # Check interval
            interval_min = user.get('interval_min', 120)
            last_notification = user.get('last_notification_sent')
            
            if last_notification:
                try:
                    last_notification_dt = datetime.fromisoformat(last_notification.replace('Z', '+00:00'))
                    time_since_last = (current_time - last_notification_dt).total_seconds() / 60
                    
                    if time_since_last < interval_min:
                        logger.debug(f"User {tg_id} too soon since last notification")
                        return False
                        
                except Exception as e:
                    logger.warning(f"Error parsing last notification time for user {tg_id}: {e}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking notification conditions for user {user.get('tg_id')}: {e}")
            return False
    
    @track_errors_async("send_notification")
    async def _send_notification_to_user(self, user: dict) -> None:
        """Send notification to a specific user."""
        try:
            tg_id = user.get('tg_id')
            
            if not tg_id:
                logger.error("User missing tg_id")
                return
            
            # Send the notification
            await self.application.bot.send_message(
                chat_id=tg_id,
                text=self.config.question_text
            )
            
            # Update last notification timestamp
            await self.user_ops.update_last_notification(tg_id)
            
            logger.info(f"Notification sent to user {tg_id}")
            
        except Exception as e:
            logger.error(f"Error sending notification to user {user.get('tg_id')}: {e}")
    
    @track_errors_async("daily_cleanup")
    async def _daily_cleanup(self) -> None:
        """Perform daily cleanup tasks."""
        try:
            logger.info("Starting daily cleanup")
            
            # Add cleanup tasks here:
            # - Clean old cache entries
            # - Archive old activities
            # - Update statistics
            
            logger.info("Daily cleanup completed")
            
        except Exception as e:
            logger.error(f"Error in daily cleanup: {e}")


# Utility function for creating asyncio tasks
def run_coro_in_loop(coro):
    """Run coroutine in current event loop or create task."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # No running loop, run in new loop
        return asyncio.run(coro)
    else:
        # Running loop exists, create task
        loop.create_task(coro)