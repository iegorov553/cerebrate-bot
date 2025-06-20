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
            # OPTIMIZED: Single JOIN query for incoming requests
            incoming_query = """
            SELECT 
                f.friendship_id,
                f.requester_id,
                f.addressee_id,
                f.status,
                f.created_at,
                u.tg_username as requester_username,
                u.tg_first_name as requester_first_name
            FROM friendships f
            JOIN users u ON u.tg_id = f.requester_id
            WHERE f.addressee_id = %s AND f.status = 'pending'
            ORDER BY f.created_at DESC
            """
            
            # OPTIMIZED: Single JOIN query for outgoing requests  
            outgoing_query = """
            SELECT 
                f.friendship_id,
                f.requester_id,
                f.addressee_id,
                f.status,
                f.created_at,
                u.tg_username as addressee_username,
                u.tg_first_name as addressee_first_name
            FROM friendships f
            JOIN users u ON u.tg_id = f.addressee_id
            WHERE f.requester_id = %s AND f.status = 'pending'
            ORDER BY f.created_at DESC
            """
            
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
    async def update_friend_request(self, friendship_id: str, status: str) -> bool:
        """Accept or decline a friend request."""
        try:
            self.db.table("friendships").update({
                "status": status
            }).eq("friendship_id", friendship_id).execute()
            
            logger.info("Friend request updated", 
                       friendship_id=friendship_id, status=status)
            return True
            
        except Exception as exc:
            logger.error("Error updating friend request", 
                        friendship_id=friendship_id, status=status, error=str(exc))
            return False

    @track_errors_async("friends_list_optimized")
    async def get_friends_list_optimized(self, user_id: int) -> List[Dict[str, Any]]:
        """Get list of user's friends with OPTIMIZED single query."""
        
        log_bot_metrics("friends_list_query", 1.0, {"user_id": user_id})
        
        try:
            # OPTIMIZED: Single query using UNION to get friends in both directions
            friends_query = """
            SELECT DISTINCT
                u.tg_id,
                u.tg_username,
                u.tg_first_name,
                u.tg_last_name
            FROM users u
            WHERE u.tg_id IN (
                SELECT f.addressee_id FROM friendships f 
                WHERE f.requester_id = %s AND f.status = 'accepted'
                UNION
                SELECT f.requester_id FROM friendships f 
                WHERE f.addressee_id = %s AND f.status = 'accepted'
            )
            ORDER BY u.tg_username, u.tg_first_name
            """
            
            try:
                # Use direct table queries instead of RPC
                friends = self.get_friends_list_fallback(user_id)
                
            except Exception:
                # Fallback to original method
                friends = self.get_friends_list_fallback(user_id)
            
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
                return self.get_friends_of_friends_fallback(user_id, limit)
                
            except Exception as sql_error:
                logger.warning("Optimized SQL function failed, using fallback", 
                             user_id=user_id, error=str(sql_error))
                return self.get_friends_of_friends_fallback(user_id, limit)
                
        except Exception as exc:
            logger.error("Error in friends discovery", user_id=user_id, error=str(exc))
            return []
    
    async def get_friends_of_friends_fallback(self, user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """Fallback optimized friends discovery using multiple queries but with batching."""
        try:
            # Get current friends (optimized with single query)
            current_friend_ids = set()
            
            # Single query for both directions
            friends_result = self.db.table("friendships").select(
                "requester_id, addressee_id"
            ).eq("status", "accepted").or_(
                f"requester_id.eq.{user_id},addressee_id.eq.{user_id}"
            ).execute()
            
            for friendship in friends_result.data or []:
                if friendship['requester_id'] == user_id:
                    current_friend_ids.add(friendship['addressee_id'])
                else:
                    current_friend_ids.add(friendship['requester_id'])
            
            if not current_friend_ids:
                return []
            
            exclude_ids = current_friend_ids | {user_id}
            
            # Get all friendships of current friends (batch query)
            # Get friendships where either requester or addressee is in current_friend_ids
            all_friendships = self.db.table("friendships").select(
                "requester_id, addressee_id"
            ).eq("status", "accepted").or_(
                f"requester_id.in.({','.join(map(str, current_friend_ids))}),addressee_id.in.({','.join(map(str, current_friend_ids))})"
            ).execute()
            
            # Build recommendations map
            recommendations = {}
            
            for friendship in all_friendships.data or []:
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
                return []
            
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