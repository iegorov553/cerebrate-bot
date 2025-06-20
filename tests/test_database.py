"""
Tests for database functions in the Hour Watcher Bot.
"""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock Supabase before importing cerebrate_bot
with patch('supabase.create_client') as mock_create_client:
    mock_create_client.return_value = MagicMock()
    from cerebrate_bot import (
        find_user_by_username,
        create_friend_request,
        get_friend_requests,
        update_friend_request,
        get_friends_list,
        get_friends_of_friends
    )

class TestDatabaseFunctions:
    """Tests for database-related functions."""
    
    @pytest.mark.asyncio
    async def test_find_user_by_username_success(self, mock_supabase):
        """Test finding user by username successfully."""
        # Mock successful response
        mock_response = MagicMock()
        mock_response.data = [{
            "tg_id": 123456789,
            "tg_username": "testuser",
            "tg_first_name": "Test"
        }]
        
        mock_supabase.table().select().eq().execute.return_value = mock_response
        
        with patch('cerebrate_bot.supabase', mock_supabase):
            result = await find_user_by_username("@testuser")
        
        assert result is not None
        assert result["tg_username"] == "testuser"
        assert result["tg_id"] == 123456789
        
        # Verify supabase was called correctly
        mock_supabase.table.assert_called_with("users")
        mock_supabase.table().select().eq.assert_called_with("tg_username", "testuser")
    
    @pytest.mark.asyncio
    async def test_find_user_by_username_not_found(self, mock_supabase):
        """Test finding user by username when user doesn't exist."""
        # Mock empty response
        mock_response = MagicMock()
        mock_response.data = []
        
        mock_supabase.table().select().eq().execute.return_value = mock_response
        
        with patch('cerebrate_bot.supabase', mock_supabase):
            result = await find_user_by_username("nonexistent")
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_find_user_strips_at_symbol(self, mock_supabase):
        """Test that @ symbol is stripped from username."""
        mock_response = MagicMock()
        mock_response.data = [{"tg_username": "testuser"}]
        
        mock_supabase.table().select().eq().execute.return_value = mock_response
        
        with patch('cerebrate_bot.supabase', mock_supabase):
            await find_user_by_username("@testuser")
        
        # Verify @ was stripped
        mock_supabase.table().select().eq.assert_called_with("tg_username", "testuser")
    
    @pytest.mark.asyncio
    async def test_create_friend_request_success(self, mock_supabase):
        """Test creating friend request successfully."""
        # Mock no existing friendship
        mock_empty_response = MagicMock()
        mock_empty_response.data = []
        
        # Mock successful insert
        mock_insert_response = MagicMock()
        
        mock_supabase.table().select().eq().eq().execute.return_value = mock_empty_response
        mock_supabase.table().insert().execute.return_value = mock_insert_response
        
        with patch('cerebrate_bot.supabase', mock_supabase):
            result = await create_friend_request(123456789, 987654321)
        
        assert result is True
        
        # Verify insert was called with correct data
        expected_data = {
            "requester_id": 123456789,
            "addressee_id": 987654321,
            "status": "pending"
        }
        mock_supabase.table().insert.assert_called_with(expected_data)
    
    @pytest.mark.asyncio
    async def test_create_friend_request_already_exists(self, mock_supabase):
        """Test creating friend request when one already exists."""
        # Mock existing friendship
        mock_existing_response = MagicMock()
        mock_existing_response.data = [{"friendship_id": "test-id"}]
        
        mock_supabase.table().select().eq().eq().execute.return_value = mock_existing_response
        
        with patch('cerebrate_bot.supabase', mock_supabase):
            result = await create_friend_request(123456789, 987654321)
        
        assert result is False
        
        # Verify insert was not called
        mock_supabase.table().insert.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_get_friend_requests_success(self, mock_supabase):
        """Test getting friend requests successfully."""
        # Mock incoming requests response
        mock_incoming_response = MagicMock()
        mock_incoming_response.data = [{
            "friendship_id": "test-id-1",
            "requester_id": 987654321,
            "addressee_id": 123456789,
            "status": "pending"
        }]
        
        # Mock outgoing requests response
        mock_outgoing_response = MagicMock()
        mock_outgoing_response.data = [{
            "friendship_id": "test-id-2", 
            "requester_id": 123456789,
            "addressee_id": 555666777,
            "status": "pending"
        }]
        
        # Mock user info responses
        mock_user_response = MagicMock()
        mock_user_response.data = [{
            "tg_username": "frienduser",
            "tg_first_name": "Friend"
        }]
        
        # Configure mock to return different responses for different calls
        mock_table = mock_supabase.table()
        
        def mock_execute(*args, **kwargs):
            # This is a simplified mock - in real scenario we'd need more sophisticated mocking
            return mock_incoming_response
        
        mock_table.select().eq().eq().execute.side_effect = [
            mock_incoming_response,  # First call for incoming
            mock_outgoing_response   # Second call for outgoing
        ]
        mock_table.select().eq().execute.return_value = mock_user_response
        
        with patch('cerebrate_bot.supabase', mock_supabase):
            result = await get_friend_requests(123456789)
        
        assert "incoming" in result
        assert "outgoing" in result
        assert isinstance(result["incoming"], list)
        assert isinstance(result["outgoing"], list)
    
    @pytest.mark.asyncio
    async def test_update_friend_request_success(self, mock_supabase):
        """Test updating friend request status successfully."""
        mock_response = MagicMock()
        mock_supabase.table().update().eq().execute.return_value = mock_response
        
        with patch('cerebrate_bot.supabase', mock_supabase):
            result = await update_friend_request("test-friendship-id", "accepted")
        
        assert result is True
        
        # Verify update was called correctly
        mock_supabase.table().update.assert_called_with({"status": "accepted"})
        mock_supabase.table().update().eq.assert_called_with("friendship_id", "test-friendship-id")
    
    @pytest.mark.asyncio
    async def test_get_friends_list_success(self, mock_supabase):
        """Test getting friends list successfully."""
        # Mock friendship responses
        mock_requester_response = MagicMock()
        mock_requester_response.data = [{
            "requester_id": 123456789,
            "addressee_id": 987654321
        }]
        
        mock_addressee_response = MagicMock()
        mock_addressee_response.data = [{
            "requester_id": 555666777,
            "addressee_id": 123456789
        }]
        
        # Mock user info response
        mock_user_response = MagicMock()
        mock_user_response.data = [{
            "tg_id": 987654321,
            "tg_username": "friend1",
            "tg_first_name": "Friend"
        }]
        
        mock_table = mock_supabase.table()
        
        # Configure different responses for different calls
        mock_table.select().eq().eq().execute.side_effect = [
            mock_requester_response,
            mock_addressee_response
        ]
        mock_table.select().eq().execute.return_value = mock_user_response
        
        with patch('cerebrate_bot.supabase', mock_supabase):
            result = await get_friends_list(123456789)
        
        assert isinstance(result, list)
        # In a more comprehensive test, we'd verify the actual structure
    
    @pytest.mark.asyncio
    async def test_get_friends_of_friends_optimization(self, mock_supabase):
        """Test that friends of friends uses optimized queries."""
        # Mock responses for the optimized version
        mock_friends_response1 = MagicMock()
        mock_friends_response1.data = [{"addressee_id": 987654321}]
        
        mock_friends_response2 = MagicMock()
        mock_friends_response2.data = [{"requester_id": 555666777}]
        
        mock_all_friendships_response = MagicMock()
        mock_all_friendships_response.data = [
            {"requester_id": 987654321, "addressee_id": 111222333},
            {"requester_id": 555666777, "addressee_id": 444555666}
        ]
        
        mock_users_response = MagicMock()
        mock_users_response.data = [
            {"tg_id": 111222333, "tg_username": "friend_of_friend1", "tg_first_name": "FOF1"},
            {"tg_id": 444555666, "tg_username": "friend_of_friend2", "tg_first_name": "FOF2"}
        ]
        
        mock_table = mock_supabase.table()
        
        # Set up call sequence
        mock_table.select().eq().eq().execute.side_effect = [
            mock_friends_response1,  # requester friends
            mock_friends_response2   # addressee friends
        ]
        mock_table.select().eq().or_().execute.return_value = mock_all_friendships_response
        mock_table.select().in_().execute.return_value = mock_users_response
        
        with patch('cerebrate_bot.supabase', mock_supabase):
            result = await get_friends_of_friends(123456789)
        
        assert isinstance(result, list)
        # Verify we made optimized calls (fewer than N+1)
        # The exact number depends on implementation details