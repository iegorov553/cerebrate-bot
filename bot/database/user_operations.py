"""
User-related database operations.
"""
from typing import Any, Dict, Optional

from bot.utils.cache_manager import CacheManager
from monitoring import get_logger, set_user_context, track_errors_async

logger = get_logger(__name__)


class UserOperations:
    """Handles user-related database operations."""
    
    def __init__(self, db_client, cache: CacheManager):
        self.db = db_client
        self.cache = cache
    
    @track_errors_async("user_registration")
    async def ensure_user_exists(self, tg_id: int, username: str = None, 
                                 first_name: str = None, last_name: str = None,
                                 language: str = 'ru') -> Dict[str, Any]:
        """Ensure user exists in database, create if not."""
        
        # Set user context for monitoring
        set_user_context(tg_id, username, first_name)
        
        try:
            # Check if user exists
            result = self.db.table("users").select("*").eq("tg_id", tg_id).execute()
            
            if result.data:
                user = result.data[0]
                # Cache the user data if cache is available
                if self.cache:
                    await self.cache.set(f"user_{tg_id}", user, 300)
                return user
            
            # Create new user with default settings
            new_user = {
                "tg_id": tg_id,
                "tg_username": username,
                "tg_first_name": first_name,
                "tg_last_name": last_name,
                "enabled": True,
                "window_start": "09:00:00",
                "window_end": "23:00:00",
                "interval_min": 60,
                "language": language
            }
            
            result = self.db.table("users").insert(new_user).execute()
            created_user = result.data[0] if result.data else new_user
            
            # Cache the new user if cache is available
            if self.cache:
                await self.cache.set(f"user_{tg_id}", created_user, 300)
            
            logger.info("Created new user", user_id=tg_id, username=username)
            return created_user
            
        except Exception as exc:
            logger.error("Error ensuring user exists", user_id=tg_id, error=str(exc))
            raise
    
    @track_errors_async("user_settings_get")
    async def get_user_settings(self, user_id: int, force_refresh: bool = False) -> Optional[Dict[str, Any]]:
        """Get user settings with caching."""
        cache_key = f"user_settings_{user_id}"
        
        if not force_refresh and self.cache:
            settings = await self.cache.get(cache_key)
            if settings is not None:
                logger.debug("User settings from cache", user_id=user_id)
                return settings
        
        try:
            result = self.db.table("users").select("*").eq("tg_id", user_id).execute()
            settings = result.data[0] if result.data else None
            
            if settings and self.cache:
                # Cache for 5 minutes
                await self.cache.set(cache_key, settings, 300)
                logger.debug("User settings cached", user_id=user_id)
            
            return settings
            
        except Exception as exc:
            logger.error("Error getting user settings", user_id=user_id, error=str(exc))
            return None
    
    @track_errors_async("user_settings_update")
    async def update_user_settings(self, user_id: int, updates: Dict[str, Any]) -> bool:
        """Update user settings and invalidate cache."""
        try:
            self.db.table("users").update(updates).eq("tg_id", user_id).execute()
            
            # Invalidate cache if available
            if self.cache:
                await self.cache.invalidate(f"user_settings_{user_id}")
                await self.cache.invalidate(f"user_{user_id}")
            
            logger.info("User settings updated", user_id=user_id, updates=list(updates.keys()))
            return True
            
        except Exception as exc:
            error_msg = str(exc)
            
            # Check if it's a missing column error (language column not yet added)
            if "Could not find the 'language' column" in error_msg and 'language' in updates:
                logger.warning("Language column not found, trying without language update", user_id=user_id)
                
                # Retry without language field
                updates_without_language = {k: v for k, v in updates.items() if k != 'language'}
                
                if updates_without_language:
                    try:
                        self.db.table("users").update(updates_without_language).eq("tg_id", user_id).execute()
                        
                        # Invalidate cache if available
                        if self.cache:
                            await self.cache.invalidate(f"user_settings_{user_id}")
                            await self.cache.invalidate(f"user_{user_id}")
                        
                        logger.info("User settings updated (without language)", user_id=user_id, updates=list(updates_without_language.keys()))
                        return True
                    except Exception as exc2:
                        logger.error("Error updating user settings (fallback)", user_id=user_id, error=str(exc2))
                        return False
                else:
                    logger.warning("Only language field to update, but column not found", user_id=user_id)
                    return False
            
            logger.error("Error updating user settings", user_id=user_id, error=error_msg)
            return False
    
    @track_errors_async("user_lookup")
    async def find_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Find user by username in database."""
        try:
            # Remove @ if present
            clean_username = username.lstrip('@')
            result = self.db.table("users").select("*").eq("tg_username", clean_username).execute()
            
            user = result.data[0] if result.data else None
            if user:
                logger.debug("User found by username", username=clean_username, user_id=user.get('tg_id'))
            else:
                logger.debug("User not found by username", username=clean_username)
            
            return user
            
        except Exception as exc:
            logger.error("Error finding user by username", username=username, error=str(exc))
            return None
    
    @track_errors_async("user_activity_log")
    async def log_activity(self, user_id: int, activity_text: str, question_id: Optional[int] = None) -> bool:
        """Log user activity to database with optional question linkage."""
        try:
            activity_data = {
                "tg_id": user_id,
                "job_text": activity_text,
                "jobs_timestamp": "now()"
            }
            
            # Add question_id if provided
            if question_id is not None:
                activity_data["question_id"] = question_id
            
            self.db.table("tg_jobs").insert(activity_data).execute()
            
            log_data = {"user_id": user_id, "text_length": len(activity_text)}
            if question_id:
                log_data["question_id"] = question_id
            
            logger.info("Activity logged", **log_data)
            return True
            
        except Exception as exc:
            logger.error("Error logging activity", user_id=user_id, error=str(exc))
            return False
    
    @track_errors_async("get_all_active_users")
    async def get_all_active_users(self) -> list:
        """Get all users with notifications enabled."""
        try:
            result = self.db.table("users").select("*").eq("enabled", True).execute()
            
            active_users = result.data if result.data else []
            logger.debug("Retrieved active users", count=len(active_users))
            
            return active_users
            
        except Exception as exc:
            logger.error("Error getting active users", error=str(exc))
            return []
    
    @track_errors_async("update_last_notification")
    async def update_last_notification(self, user_id: int) -> bool:
        """Update last notification timestamp for user."""
        try:
            # Use PostgreSQL's NOW() function to get current timestamp
            self.db.table("users").update({
                "last_notification_sent": "now()"
            }).eq("tg_id", user_id).execute()
            
            # Invalidate cache for this user (if cache is available)
            if self.cache:
                await self.cache.invalidate(f"user_settings_{user_id}")
                await self.cache.invalidate(f"user_{user_id}")
            
            logger.debug("Updated last notification timestamp", user_id=user_id)
            return True
            
        except Exception as exc:
            logger.error("Error updating last notification", user_id=user_id, error=str(exc))
            return False
    
    @track_errors_async("get_all_user_ids")
    async def get_all_user_ids(self) -> list:
        """Get all user IDs for broadcast."""
        try:
            result = self.db.table("users").select("tg_id").execute()
            
            user_ids = [user['tg_id'] for user in result.data] if result.data else []
            logger.debug("Retrieved user IDs for broadcast", count=len(user_ids))
            
            return user_ids
            
        except Exception as exc:
            logger.error("Error getting all user IDs", error=str(exc))
            return []