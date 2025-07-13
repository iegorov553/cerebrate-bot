"""
Admin operations with optimized database queries.
"""
from typing import Any, Dict

from bot.config import Config
from monitoring import get_logger, track_errors_async

logger = get_logger(__name__)


class AdminOperations:
    """Handles admin-related database operations."""

    def __init__(self, db_client, config: Config):
        self.db = db_client
        self.config = config

    def is_admin(self, user_id: int) -> bool:
        """Check if user is admin."""
        return self.config.is_admin_configured() and user_id == self.config.admin_user_id

    @track_errors_async("admin_stats_optimized")
    async def get_user_stats_optimized(self) -> Dict[str, Any]:
        """Get user statistics using optimized SQL function."""
        try:
            # Try using the optimized SQL function first
            try:
                result = self.db.client.rpc('get_user_stats').execute()

                if result.data and len(result.data) > 0:
                    stats = result.data[0]
                    return {
                        "total": stats['total_users'],
                        "active": stats['active_users'],
                        "new_week": stats['new_users_week'],
                        "active_percentage": float(stats['active_percentage'])
                    }

            except Exception as sql_error:
                logger.warning("Optimized stats function failed, using fallback", error=str(sql_error))
                return await self.get_user_stats_fallback()

        except Exception as exc:
            logger.error("Error getting user statistics", error=str(exc))
            return {"total": 0, "active": 0, "new_week": 0, "active_percentage": 0.0}

    async def get_user_stats_fallback(self) -> Dict[str, Any]:
        """Fallback method for getting user statistics."""
        try:
            # Total users
            total_result = self.db.table("users").select("tg_id", count="exact").execute()
            total_users = total_result.count or 0

            # Active users (enabled=true)
            active_result = self.db.table("users").select("tg_id", count="exact").eq("enabled", True).execute()
            active_users = active_result.count or 0

            # New users in last 7 days
            from datetime import datetime, timedelta
            week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
            new_result = self.db.table("users").select("tg_id", count="exact").gte("created_at", week_ago).execute()
            new_users = new_result.count or 0

            # Calculate percentage
            active_percentage = (active_users / max(total_users, 1)) * 100 if total_users > 0 else 0

            return {
                "total": total_users,
                "active": active_users,
                "new_week": new_users,
                "active_percentage": round(active_percentage, 2)
            }

        except Exception as exc:
            logger.error("Error in user stats fallback", error=str(exc))
            return {"total": 0, "active": 0, "new_week": 0, "active_percentage": 0.0}

    @track_errors_async("admin_get_all_users")
    async def get_all_user_ids(self) -> list:
        """Get all user IDs for broadcasting."""
        try:
            result = self.db.table("users").select("tg_id").execute()
            user_ids = [user['tg_id'] for user in result.data or []]

            logger.info("Retrieved user IDs for broadcasting", count=len(user_ids))
            return user_ids

        except Exception as exc:
            logger.error("Error getting all user IDs", error=str(exc))
            return []
