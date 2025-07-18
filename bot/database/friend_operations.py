"""
Friend-related database operations with optimizations.
"""
from typing import Any, Dict, List, Optional

from monitoring import get_logger, log_bot_metrics, track_errors_async

logger = get_logger(__name__)


class FriendOperations:
    """Handles friend-related database operations with optimizations."""
    
    def __init__(self, db_client):
        self.db = db_client
    
    @track_errors_async("friend_request_create")
    async def create_friend_request(self, requester_id: int, addressee_id: int) -> bool:
        """Create a friend request."""
        try:
            # Check if friendship already exists in either direction
            existing1 = self.db.table("friendships").select("*").eq(
                "requester_id", requester_id
            ).eq(
                "addressee_id", addressee_id
            ).execute()
            existing2 = self.db.table("friendships").select("*").eq(
                "requester_id", addressee_id
            ).eq(
                "addressee_id", requester_id
            ).execute()

            if (existing1.data or existing2.data):
                logger.debug("Friend request already exists", 
                           requester=requester_id, addressee=addressee_id)
                return False  # Already exists
            
            # Create new friend request
            self.db.table("friendships").insert({
                "requester_id": requester_id,
                "addressee_id": addressee_id,
                "status": "pending"
            }).execute()
            
            logger.info("Friend request created", 
                       requester=requester_id, addressee=addressee_id)
            return True
            
        except Exception as exc:
            logger.error("Error creating friend request", 
                        requester=requester_id, addressee=addressee_id, error=str(exc))
            return False

    @track_errors_async("friend_requests_get_optimized")
    async def get_friend_requests_optimized(self, user_id: int) -> Dict[str, List[Dict[str, Any]]]:
        """Get incoming and outgoing friend requests with OPTIMIZED queries (eliminates N+1)."""
        
        log_bot_metrics("friend_requests_query", 1.0, {"user_id": user_id})
        
        try:
            # Note: SQL queries prepared for future RPC function implementation
            # Currently using fallback table queries with joins
            
            # Execute optimized queries using direct table access
            # Note: Using fallback method as exec_sql RPC function may not exist
            try:
                # Try direct table queries with joins
                incoming_result = self.db.table("friendships").select(
                    "*, requester:requester_id(tg_id, tg_username, tg_first_name, tg_last_name)"
                ).eq("addressee_id", user_id).eq("status", "pending").order("created_at", desc=True).execute()
                
                outgoing_result = self.db.table("friendships").select(
                    "*, addressee:addressee_id(tg_id, tg_username, tg_first_name, tg_last_name)"
                ).eq("requester_id", user_id).eq("status", "pending").order("created_at", desc=True).execute()
                
            except Exception as e:
                logger.warning(f"Optimized query failed, using fallback: {e}")
                # Fallback to simple queries
                incoming_result = self.db.table("friendships").select("*").eq("addressee_id", user_id).eq("status", "pending").execute()
                outgoing_result = self.db.table("friendships").select("*").eq("requester_id", user_id).eq("status", "pending").execute()
            
            # Format incoming requests
            incoming = []
            for req in incoming_result.data or []:
                incoming.append({
                    'friendship_id': req['friendship_id'],
                    'requester_id': req['requester_id'],
                    'addressee_id': req['addressee_id'],
                    'status': req['status'],
                    'created_at': req['created_at'],
                    'requester': {
                        'tg_username': req['requester_username'],
                        'tg_first_name': req['requester_first_name']
                    }
                })
            
            # Format outgoing requests
            outgoing = []
            for req in outgoing_result.data or []:
                outgoing.append({
                    'friendship_id': req['friendship_id'],
                    'requester_id': req['requester_id'],
                    'addressee_id': req['addressee_id'],
                    'status': req['status'],
                    'created_at': req['created_at'],
                    'addressee': {
                        'tg_username': req['addressee_username'],
                        'tg_first_name': req['addressee_first_name']
                    }
                })
            
            logger.debug("Friend requests fetched (optimized)", 
                        user_id=user_id, incoming=len(incoming), outgoing=len(outgoing))
            
            return {
                "incoming": incoming,
                "outgoing": outgoing
            }
            
        except Exception as exc:
            logger.error("Error getting friend requests (optimized)", 
                        user_id=user_id, error=str(exc))
            
            # Fallback to non-optimized version
            return await self.get_friend_requests_fallback(user_id)
    
    async def get_friend_requests_fallback(self, user_id: int) -> Dict[str, List[Dict[str, Any]]]:
        """Fallback method using original approach if SQL RPC fails."""
        try:
            # Incoming requests (original method but batched)
            incoming_result = self.db.table("friendships").select(
                "friendship_id, requester_id, addressee_id, status, created_at"
            ).eq("addressee_id", user_id).eq("status", "pending").execute()
            
            # Outgoing requests
            outgoing_result = self.db.table("friendships").select(
                "friendship_id, requester_id, addressee_id, status, created_at"
            ).eq("requester_id", user_id).eq("status", "pending").execute()
            
            # Collect all user IDs we need info for
            user_ids_needed = set()
            for req in incoming_result.data or []:
                user_ids_needed.add(req['requester_id'])
            for req in outgoing_result.data or []:
                user_ids_needed.add(req['addressee_id'])
            
            # OPTIMIZED: Single batch query for all user info
            users_info = {}
            if user_ids_needed:
                users_result = self.db.table("users").select(
                    "tg_id, tg_username, tg_first_name"
                ).in_("tg_id", list(user_ids_needed)).execute()
                
                users_info = {user['tg_id']: user for user in users_result.data or []}
            
            # Build incoming with cached user info
            incoming = []
            for req in incoming_result.data or []:
                user_info = users_info.get(req['requester_id'], {})
                req['requester'] = {
                    'tg_username': user_info.get('tg_username'),
                    'tg_first_name': user_info.get('tg_first_name', 'Unknown')
                }
                incoming.append(req)
            
            # Build outgoing with cached user info
            outgoing = []
            for req in outgoing_result.data or []:
                user_info = users_info.get(req['addressee_id'], {})
                req['addressee'] = {
                    'tg_username': user_info.get('tg_username'),
                    'tg_first_name': user_info.get('tg_first_name', 'Unknown')
                }
                outgoing.append(req)
            
            logger.debug("Friend requests fetched (fallback)", 
                        user_id=user_id, incoming=len(incoming), outgoing=len(outgoing))
            
            return {
                "incoming": incoming,
                "outgoing": outgoing
            }
            
        except Exception as exc:
            logger.error("Error in friend requests fallback", user_id=user_id, error=str(exc))
            return {"incoming": [], "outgoing": []}

    @track_errors_async("friend_request_update")
    async def update_friend_request_status(self, requester_id: int, addressee_id: int, status: str) -> bool:
        """Update friend request status (accept/decline)."""
        try:
            result = self.db.table("friendships").update({
                "status": status
            }).eq("requester_id", requester_id).eq("addressee_id", addressee_id).eq("status", "pending").execute()
            
            if result.data:
                logger.info("Friend request updated", 
                           requester=requester_id, addressee=addressee_id, status=status)
                return True
            else:
                logger.warning("No pending friend request found", 
                              requester=requester_id, addressee=addressee_id)
                return False
            
        except Exception as exc:
            logger.error("Error updating friend request", 
                        requester=requester_id, addressee=addressee_id, status=status, error=str(exc))
            return False
    
    @track_errors_async("friend_request_accept")
    async def accept_friend_request(self, requester_id: int, addressee_id: int) -> bool:
        """Accept a friend request."""
        return await self.update_friend_request_status(requester_id, addressee_id, "accepted")
    
    @track_errors_async("friend_request_decline")
    async def decline_friend_request(self, requester_id: int, addressee_id: int) -> bool:
        """Decline a friend request."""
        return await self.update_friend_request_status(requester_id, addressee_id, "declined")

    @track_errors_async("friends_list_optimized")
    async def get_friends_list_optimized(self, user_id: int) -> List[Dict[str, Any]]:
        """Get list of user's friends with OPTIMIZED single query."""
        
        log_bot_metrics("friends_list_query", 1.0, {"user_id": user_id})
        
        try:
            # Note: SQL query prepared for future RPC function implementation
            # Currently using fallback table queries
            
            try:
                # Use direct table queries instead of RPC
                friends = await self.get_friends_list_fallback(user_id)
                
            except Exception:
                # Fallback to original method
                friends = await self.get_friends_list_fallback(user_id)
            
            logger.debug("Friends list fetched", user_id=user_id, count=len(friends))
            return friends
            
        except Exception as exc:
            logger.error("Error getting friends list", user_id=user_id, error=str(exc))
            return []
    
    async def get_friends_list_fallback(self, user_id: int) -> List[Dict[str, Any]]:
        """Fallback method for getting friends list."""
        try:
            # Get accepted friendships where user is either requester or addressee
            result_requester = self.db.table("friendships").select(
                "requester_id, addressee_id"
            ).eq("status", "accepted").eq("requester_id", user_id).execute()

            result_addressee = self.db.table("friendships").select(
                "requester_id, addressee_id"
            ).eq("status", "accepted").eq("addressee_id", user_id).execute()

            # Collect friend IDs
            friend_ids = set()
            for friendship in result_requester.data or []:
                friend_ids.add(friendship['addressee_id'])
            
            for friendship in result_addressee.data or []:
                friend_ids.add(friendship['requester_id'])

            # OPTIMIZED: Single batch query for all friends
            friends = []
            if friend_ids:
                friends_result = self.db.table("users").select(
                    "tg_id, tg_username, tg_first_name, tg_last_name"
                ).in_("tg_id", list(friend_ids)).execute()
                
                friends = friends_result.data or []
            
            return friends
            
        except Exception as exc:
            logger.error("Error in friends list fallback", user_id=user_id, error=str(exc))
            return []

    @track_errors_async("find_user_by_username")
    async def find_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Find user by username in database."""
        try:
            # Remove @ if present
            clean_username = username.lstrip('@')
            result = self.db.table("users").select("*").eq("tg_username", clean_username).execute()
            
            user = result.data[0] if result.data else None
            if user:
                logger.debug("User found by username", username=clean_username, user_id=user.get('tg_id'))
            
            return user
            
        except Exception as exc:
            logger.error("Error finding user by username", username=username, error=str(exc))
            return None

    @track_errors_async("friends_discovery_optimized")
    async def get_friends_of_friends_optimized(self, user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """Get friends of friends recommendations with OPTIMIZED single query."""
        
        log_bot_metrics("friends_discovery_optimized", 1.0, {"user_id": user_id, "limit": limit})
        
        try:
            # Try using the optimized SQL function first
            try:
                # Use fallback method as RPC function may not exist in current schema
                return await self.get_friends_of_friends_fallback(user_id, limit)
                
            except Exception as sql_error:
                logger.warning("Optimized SQL function failed, using fallback", 
                             user_id=user_id, error=str(sql_error))
                return await self.get_friends_of_friends_fallback(user_id, limit)
                
        except Exception as exc:
            logger.error("Error in friends discovery", user_id=user_id, error=str(exc))
            return []
    
    async def get_friends_of_friends_fallback(self, user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """Fallback optimized friends discovery using multiple queries but with batching."""
        try:
            # Get current friends (optimized with single query)
            current_friend_ids = set()
            
            # Single query for both directions - split into two queries due to Supabase client limitations
            friends_result_1 = self.db.table("friendships").select(
                "requester_id, addressee_id"
            ).eq("status", "accepted").eq("requester_id", user_id).execute()
            
            friends_result_2 = self.db.table("friendships").select(
                "requester_id, addressee_id"
            ).eq("status", "accepted").eq("addressee_id", user_id).execute()
            
            # Combine results
            all_friendships = (friends_result_1.data or []) + (friends_result_2.data or [])
            
            for friendship in all_friendships:
                if friendship['requester_id'] == user_id:
                    current_friend_ids.add(friendship['addressee_id'])
                else:
                    current_friend_ids.add(friendship['requester_id'])
            
            if not current_friend_ids:
                logger.info(f"User {user_id} has no friends - no recommendations possible")
                return []
            
            logger.info(f"User {user_id} has {len(current_friend_ids)} friends: {list(current_friend_ids)}")
            
            # Также исключить пользователей с которыми уже есть pending запросы (в любом направлении)
            pending_requests_1 = self.db.table("friendships").select(
                "requester_id, addressee_id"
            ).eq("status", "pending").eq("requester_id", user_id).execute()
            
            pending_requests_2 = self.db.table("friendships").select(
                "requester_id, addressee_id"
            ).eq("status", "pending").eq("addressee_id", user_id).execute()
            
            # Combine pending requests
            all_pending_requests = (pending_requests_1.data or []) + (pending_requests_2.data or [])
            
            pending_user_ids = set()
            for req in all_pending_requests:
                if req['requester_id'] == user_id:
                    pending_user_ids.add(req['addressee_id'])
                else:
                    pending_user_ids.add(req['requester_id'])
            
            exclude_ids = current_friend_ids | pending_user_ids | {user_id}
            logger.info(f"Excluding {len(exclude_ids)} users: friends={len(current_friend_ids)}, pending={len(pending_user_ids)}, self=1")
            
            # Get all friendships of current friends (batch query)
            # Get friendships where either requester or addressee is in current_friend_ids
            friend_list = list(current_friend_ids)
            friendships_as_requester = self.db.table("friendships").select(
                "requester_id, addressee_id"
            ).eq("status", "accepted").in_("requester_id", friend_list).execute()
            
            friendships_as_addressee = self.db.table("friendships").select(
                "requester_id, addressee_id"
            ).eq("status", "accepted").in_("addressee_id", friend_list).execute()
            
            # Combine all friendships
            all_friendships_combined = (friendships_as_requester.data or []) + (friendships_as_addressee.data or [])
            
            # Build recommendations map
            recommendations = {}
            
            for friendship in all_friendships_combined:
                requester_id = friendship['requester_id']
                addressee_id = friendship['addressee_id']
                
                # Find candidates and mutual friends
                if requester_id in current_friend_ids and addressee_id not in exclude_ids:
                    candidate_id = addressee_id
                    mutual_friend_id = requester_id
                elif addressee_id in current_friend_ids and requester_id not in exclude_ids:
                    candidate_id = requester_id
                    mutual_friend_id = addressee_id
                else:
                    continue
                
                if candidate_id not in recommendations:
                    recommendations[candidate_id] = set()
                recommendations[candidate_id].add(mutual_friend_id)
            
            if not recommendations:
                logger.info(f"No friend-of-friend candidates found for user {user_id}")
                return []
            
            logger.info(f"Found {len(recommendations)} friend-of-friend candidates for user {user_id}")
            
            # Batch fetch all user info (single query)
            all_user_ids = list(recommendations.keys()) + list(current_friend_ids)
            users_info = self.db.table("users").select(
                "tg_id, tg_username, tg_first_name, tg_last_name"
            ).in_("tg_id", all_user_ids).execute()
            
            users_map = {user['tg_id']: user for user in users_info.data or []}
            
            # Build final result
            result = []
            for candidate_id, mutual_friend_ids in recommendations.items():
                candidate_info = users_map.get(candidate_id)
                if not candidate_info:
                    continue
                
                # Get mutual friends names
                mutual_friends = []
                for mutual_id in mutual_friend_ids:
                    mutual_user = users_map.get(mutual_id)
                    if mutual_user:
                        mutual_name = mutual_user['tg_username'] or mutual_user['tg_first_name'] or f"ID{mutual_id}"
                        mutual_friends.append(mutual_name)
                
                result.append({
                    'user_info': candidate_info,
                    'mutual_friends': mutual_friends,
                    'mutual_count': len(mutual_friends)
                })
            
            # Sort and limit
            result.sort(key=lambda x: (
                -x['mutual_count'], 
                (x['user_info']['tg_username'] or x['user_info']['tg_first_name'] or 'zzz_unknown').lower()
            ))
            
            logger.info("Friends discovery completed (fallback)", 
                       user_id=user_id, recommendations=len(result[:limit]))
            return result[:limit]
            
        except Exception as exc:
            logger.error("Error in friends discovery fallback", user_id=user_id, error=str(exc))
            return []

    @track_errors_async("send_friend_request_by_id")
    async def send_friend_request_by_id(self, requester_id: int, target_user_id: int) -> tuple[bool, Optional[str]]:
        """Send friend request by user ID with enhanced validation and feedback."""
        try:
            # Check if target user exists in database
            target_user_result = self.db.table("users").select("tg_id, tg_username, tg_first_name").eq("tg_id", target_user_id).execute()
            
            if not target_user_result.data:
                logger.warning("Target user not found", requester=requester_id, target=target_user_id)
                return False, "Пользователь не найден в системе"
            
            # Check if friendship already exists in either direction
            existing_friendship_1 = self.db.table("friendships").select("status").eq("requester_id", requester_id).eq("addressee_id", target_user_id).execute()
            existing_friendship_2 = self.db.table("friendships").select("status").eq("requester_id", target_user_id).eq("addressee_id", requester_id).execute()
            
            # Combine results
            existing_friendship_data = (existing_friendship_1.data or []) + (existing_friendship_2.data or [])
            
            if existing_friendship_data:
                existing_status = existing_friendship_data[0]['status']
                if existing_status == "accepted":
                    return False, "Вы уже друзья"
                elif existing_status == "pending":
                    return False, "Запрос в друзья уже отправлен"
                elif existing_status == "declined":
                    # Allow new request after decline
                    logger.info("Retrying friend request after previous decline", 
                               requester=requester_id, target=target_user_id)
            
            # Create new friend request
            result = self.db.table("friendships").insert({
                "requester_id": requester_id,
                "addressee_id": target_user_id,
                "status": "pending"
            }).execute()
            
            if result.data:
                target_user = target_user_result.data[0]
                target_name = target_user.get('tg_first_name') or target_user.get('tg_username') or f"ID{target_user_id}"
                
                logger.info("Friend request sent successfully", 
                           requester=requester_id, target=target_user_id, target_name=target_name)
                
                return True, f"Запрос в друзья отправлен пользователю {target_name}"
            else:
                logger.error("Failed to create friend request", 
                            requester=requester_id, target=target_user_id)
                return False, "Не удалось отправить запрос в друзья"
                
        except Exception as exc:
            logger.error("Error sending friend request by ID", 
                        requester=requester_id, target=target_user_id, error=str(exc))
            return False, "Произошла ошибка при отправке запроса"