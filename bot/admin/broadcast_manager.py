"""
Broadcast manager for Doyobi Diary admin functionality.

This module provides efficient mass messaging capabilities with progress tracking,
batching, and error handling.
"""

import asyncio
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from telegram import Bot
from telegram.error import TelegramError

from bot.database.user_operations import UserOperations
from bot.utils.cache_manager import get_logger

logger = get_logger(__name__)


@dataclass
class BroadcastProgress:
    """Progress tracking for broadcast operations."""
    total_users: int
    sent_count: int
    failed_count: int
    current_batch: int
    total_batches: int
    start_time: float
    estimated_remaining: Optional[float] = None

    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage."""
        if self.sent_count + self.failed_count == 0:
            return 0.0
        return (self.sent_count / (self.sent_count + self.failed_count)) * 100

    @property
    def completion_percentage(self) -> float:
        """Calculate completion percentage."""
        if self.total_users == 0:
            return 100.0
        return ((self.sent_count + self.failed_count) / self.total_users) * 100

    @property
    def elapsed_time(self) -> float:
        """Get elapsed time in seconds."""
        return time.time() - self.start_time


@dataclass
class BroadcastResult:
    """Result of broadcast operation."""
    total_users: int
    sent_count: int
    failed_count: int
    duration_seconds: float
    success_rate: float
    failed_user_ids: List[int]
    error_messages: List[str]


class BroadcastManager:
    """Efficient mass messaging with progress tracking."""

    def __init__(
        self,
        bot: Bot,
        user_operations: UserOperations,
        batch_size: int = 10,
        delay_between_messages: float = 0.1,
        delay_between_batches: float = 2.0,
        max_retries: int = 2
    ):
        """
        Initialize broadcast manager.

        Args:
            bot: Telegram bot instance
            user_operations: User database operations
            batch_size: Number of messages per batch
            delay_between_messages: Delay between individual messages (seconds)
            delay_between_batches: Delay between batches (seconds)
            max_retries: Maximum retry attempts for failed messages
        """
        self.bot = bot
        self.user_operations = user_operations
        self.batch_size = batch_size
        self.delay_between_messages = delay_between_messages
        self.delay_between_batches = delay_between_batches
        self.max_retries = max_retries

    async def send_broadcast(
        self,
        message: str,
        progress_callback: Optional[Callable[[BroadcastProgress], None]] = None,
        target_user_ids: Optional[List[int]] = None
    ) -> BroadcastResult:
        """
        Send broadcast message to users.

        Args:
            message: Message to broadcast
            progress_callback: Optional callback for progress updates
            target_user_ids: Optional list of specific user IDs (default: all users)

        Returns:
            BroadcastResult with operation statistics
        """
        start_time = time.time()

        # Get target users
        if target_user_ids:
            user_ids = target_user_ids
        else:
            user_ids = await self.user_operations.get_all_user_ids()

        total_users = len(user_ids)
        logger.info(f"Starting broadcast to {total_users} users")

        # Split into batches
        batches = [
            user_ids[i:i + self.batch_size]
            for i in range(0, len(user_ids), self.batch_size)
        ]
        total_batches = len(batches)

        # Initialize tracking
        sent_count = 0
        failed_count = 0
        failed_user_ids = []
        error_messages = []

        # Process batches
        for batch_index, batch_user_ids in enumerate(batches):
            logger.debug(f"Processing batch {batch_index + 1}/{total_batches}")

            # Send messages in current batch concurrently
            batch_results = await asyncio.gather(
                *[
                    self._send_message_with_retry(user_id, message)
                    for user_id in batch_user_ids
                ],
                return_exceptions=True
            )

            # Process batch results
            for user_id, result in zip(batch_user_ids, batch_results):
                if isinstance(result, Exception):
                    failed_count += 1
                    failed_user_ids.append(user_id)
                    error_messages.append(f"User {user_id}: {str(result)}")
                    logger.warning(f"Failed to send to user {user_id}: {result}")
                elif result:
                    sent_count += 1
                else:
                    failed_count += 1
                    failed_user_ids.append(user_id)
                    error_messages.append(f"User {user_id}: Unknown error")

            # Update progress
            if progress_callback:
                progress = BroadcastProgress(
                    total_users=total_users,
                    sent_count=sent_count,
                    failed_count=failed_count,
                    current_batch=batch_index + 1,
                    total_batches=total_batches,
                    start_time=start_time,
                    estimated_remaining=self._estimate_remaining_time(
                        batch_index + 1, total_batches, start_time
                    )
                )
                try:
                    progress_callback(progress)
                except Exception as e:
                    logger.error(f"Error in progress callback: {e}")

            # Delay between batches (except for last batch)
            if batch_index < total_batches - 1:
                await asyncio.sleep(self.delay_between_batches)

        duration_seconds = time.time() - start_time
        success_rate = (sent_count / total_users * 100) if total_users > 0 else 0

        result = BroadcastResult(
            total_users=total_users,
            sent_count=sent_count,
            failed_count=failed_count,
            duration_seconds=duration_seconds,
            success_rate=success_rate,
            failed_user_ids=failed_user_ids,
            error_messages=error_messages[:50]  # Limit error messages
        )

        logger.info(
            f"Broadcast completed: {sent_count}/{total_users} sent "
            f"({success_rate:.1f}% success rate) in {duration_seconds:.1f}s"
        )

        return result

    async def _send_message_with_retry(
        self,
        user_id: int,
        message: str,
        retry_count: int = 0
    ) -> bool:
        """
        Send message to user with retry logic.

        Args:
            user_id: Target user ID
            message: Message text
            retry_count: Current retry attempt

        Returns:
            True if message sent successfully, False otherwise
        """
        try:
            await self.bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode='Markdown'
            )

            # Small delay between messages to avoid rate limits
            if self.delay_between_messages > 0:
                await asyncio.sleep(self.delay_between_messages)

            return True

        except TelegramError as e:
            error_msg = str(e).lower()

            # Don't retry for certain permanent errors
            if any(permanent_error in error_msg for permanent_error in [
                'forbidden', 'blocked', 'chat not found', 'user deactivated'
            ]):
                logger.debug(f"Permanent error for user {user_id}: {e}")
                return False

            # Retry for temporary errors
            if retry_count < self.max_retries:
                logger.debug(f"Retrying message to user {user_id} (attempt {retry_count + 1})")
                await asyncio.sleep(1.0 * (retry_count + 1))  # Exponential backoff
                return await self._send_message_with_retry(user_id, message, retry_count + 1)

            logger.warning(f"Failed to send message to user {user_id} after {retry_count + 1} attempts: {e}")
            return False

        except Exception as e:
            logger.error(f"Unexpected error sending message to user {user_id}: {e}")
            return False

    def _estimate_remaining_time(
        self,
        current_batch: int,
        total_batches: int,
        start_time: float
    ) -> Optional[float]:
        """
        Estimate remaining time for broadcast completion.

        Args:
            current_batch: Current batch number (1-based)
            total_batches: Total number of batches
            start_time: Broadcast start time

        Returns:
            Estimated remaining time in seconds, or None if can't estimate
        """
        if current_batch == 0:
            return None

        elapsed_time = time.time() - start_time
        time_per_batch = elapsed_time / current_batch
        remaining_batches = total_batches - current_batch

        return remaining_batches * time_per_batch

    async def preview_broadcast(self, message: str) -> str:
        """
        Generate broadcast preview with formatting.

        Args:
            message: Raw message text

        Returns:
            Formatted preview message
        """
        # Get user count for preview
        user_count = await self.user_operations.get_total_user_count()

        preview = "📢 **Broadcast Preview**\n\n"
        preview += f"**Recipients:** {user_count} users\n"
        preview += f"**Message:**\n{message}\n\n"
        preview += f"**Estimated time:** {self._estimate_broadcast_time(user_count)} minutes"

        return preview

    def _estimate_broadcast_time(self, user_count: int) -> float:
        """
        Estimate broadcast completion time.

        Args:
            user_count: Number of users to message

        Returns:
            Estimated time in minutes
        """
        if user_count == 0:
            return 0.0

        batches = (user_count + self.batch_size - 1) // self.batch_size

        # Time = (messages * delay) + (batches * batch_delay)
        message_time = user_count * self.delay_between_messages
        batch_time = batches * self.delay_between_batches

        total_seconds = message_time + batch_time
        return total_seconds / 60  # Convert to minutes

    async def get_broadcast_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get broadcast history (placeholder - implement based on your logging needs).

        Args:
            limit: Maximum number of records to return

        Returns:
            List of broadcast records
        """
        # This would typically query a broadcast_logs table
        # For now, return empty list as this is not implemented in current schema
        logger.info("Broadcast history requested - not implemented yet")
        return []

    async def send_test_broadcast(self, admin_user_id: int, message: str) -> bool:
        """
        Send test broadcast to admin only.

        Args:
            admin_user_id: Admin user ID
            message: Test message

        Returns:
            True if sent successfully
        """
        logger.info(f"Sending test broadcast to admin {admin_user_id}")

        try:
            await self.bot.send_message(
                chat_id=admin_user_id,
                text=f"🧪 **Test Broadcast**\n\n{message}",
                parse_mode='Markdown'
            )
            return True
        except Exception as e:
            logger.error(f"Failed to send test broadcast: {e}")
            return False


# Utility functions for progress formatting

def format_progress_message(progress: BroadcastProgress) -> str:
    """
    Format progress update message.

    Args:
        progress: BroadcastProgress object

    Returns:
        Formatted progress message
    """
    message = "📢 **Broadcast Progress**\n\n"
    message += f"Progress: {progress.completion_percentage:.1f}%\n"
    message += f"Sent: {progress.sent_count}/{progress.total_users}\n"
    message += f"Failed: {progress.failed_count}\n"
    message += f"Success Rate: {progress.success_rate:.1f}%\n"
    message += f"Batch: {progress.current_batch}/{progress.total_batches}\n"
    message += f"Elapsed: {progress.elapsed_time:.1f}s\n"

    if progress.estimated_remaining:
        message += f"Remaining: ~{progress.estimated_remaining:.1f}s"

    return message


def format_broadcast_result(result: BroadcastResult) -> str:
    """
    Format broadcast completion message.

    Args:
        result: BroadcastResult object

    Returns:
        Formatted result message
    """
    message = "✅ **Broadcast Completed**\n\n"
    message += f"Total Users: {result.total_users}\n"
    message += f"Successfully Sent: {result.sent_count}\n"
    message += f"Failed: {result.failed_count}\n"
    message += f"Success Rate: {result.success_rate:.1f}%\n"
    message += f"Duration: {result.duration_seconds:.1f} seconds\n"

    if result.failed_count > 0:
        message += f"\n⚠️ {result.failed_count} messages failed to send"
        if len(result.failed_user_ids) <= 10:
            message += f"\nFailed user IDs: {', '.join(map(str, result.failed_user_ids))}"
        else:
            message += f"\nFirst 10 failed IDs: {', '.join(map(str, result.failed_user_ids[:10]))}"

    return message
