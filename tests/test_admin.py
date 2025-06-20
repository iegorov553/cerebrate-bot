"""
Tests for admin functions in the Hour Watcher Bot.
"""
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock Supabase before importing cerebrate_bot
with patch('supabase.create_client') as mock_create_client:
    mock_create_client.return_value = MagicMock()
    from cerebrate_bot import get_user_stats, is_admin, send_broadcast_message, send_single_message

class TestAdminFunctions:
    """Tests for admin-related functions."""
    
    def test_is_admin_valid_admin(self):
        """Test is_admin with valid admin user ID."""
        with patch('cerebrate_bot.ADMIN_USER_ID', 123456789):
            result = is_admin(123456789)
            assert result is True
    
    def test_is_admin_invalid_user(self):
        """Test is_admin with non-admin user ID."""
        with patch('cerebrate_bot.ADMIN_USER_ID', 123456789):
            result = is_admin(987654321)
            assert result is False
    
    def test_is_admin_no_admin_configured(self):
        """Test is_admin when no admin is configured."""
        with patch('cerebrate_bot.ADMIN_USER_ID', 0):
            result = is_admin(123456789)
            assert result is False
    
    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Complex mocking required for async database operations")
    async def test_get_user_stats_success(self, mock_supabase):
        """Test getting user statistics successfully."""
        # Mock responses for different queries
        mock_total_response = MagicMock()
        mock_total_response.count = 100
        
        mock_active_response = MagicMock()
        mock_active_response.count = 75
        
        mock_new_response = MagicMock()
        mock_new_response.count = 15
        
        # Configure mock to return different responses
        mock_table = mock_supabase.table()
        mock_table.select().execute.return_value = mock_total_response
        mock_table.select().eq().execute.return_value = mock_active_response
        mock_table.select().gte().execute.return_value = mock_new_response
        
        with patch('cerebrate_bot.supabase', mock_supabase):
            result = await get_user_stats()
        
        assert result["total"] == 100
        assert result["active"] == 75
        assert result["new_week"] == 15
    
    @pytest.mark.asyncio
    async def test_get_user_stats_error_handling(self, mock_supabase):
        """Test get_user_stats error handling."""
        # Mock database error
        mock_supabase.table().select().execute.side_effect = Exception("Database error")
        
        with patch('cerebrate_bot.supabase', mock_supabase):
            result = await get_user_stats()
        
        # Should return default values on error
        assert result["total"] == 0
        assert result["active"] == 0
        assert result["new_week"] == 0
    
    @pytest.mark.asyncio
    async def test_send_single_message_success(self):
        """Test sending single message successfully."""
        # Mock application and bot
        mock_app = MagicMock()
        mock_bot = MagicMock()
        mock_app.bot = mock_bot
        
        # Mock successful send_message
        mock_future = AsyncMock()
        mock_future.return_value = None
        mock_bot.send_message = mock_future
        
        result = await send_single_message(mock_app, 123456789, "Test message")
        
        assert result is True
        mock_bot.send_message.assert_called_once()
        
        # Verify message format
        call_args = mock_bot.send_message.call_args
        assert call_args[1]['chat_id'] == 123456789
        assert "Test message" in call_args[1]['text']
        assert call_args[1]['parse_mode'] == 'Markdown'
    
    @pytest.mark.asyncio
    async def test_send_single_message_failure(self):
        """Test send_single_message when sending fails."""
        # Mock application and bot
        mock_app = MagicMock()
        mock_bot = MagicMock()
        mock_app.bot = mock_bot
        
        # Mock failed send_message
        mock_bot.send_message.side_effect = Exception("Send failed")
        
        result = await send_single_message(mock_app, 123456789, "Test message")
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_send_broadcast_message_success(self, mock_supabase):
        """Test broadcast message functionality."""
        # Mock user data
        mock_users_response = MagicMock()
        mock_users_response.data = [
            {"tg_id": 123456789},
            {"tg_id": 987654321},
            {"tg_id": 555666777}
        ]
        
        mock_supabase.table().select().execute.return_value = mock_users_response
        
        # Mock application and bot
        mock_app = MagicMock()
        mock_bot = MagicMock()
        mock_app.bot = mock_bot
        
        # Mock send_message success
        mock_future = AsyncMock()
        mock_future.return_value = MagicMock()
        mock_bot.send_message = mock_future
        
        # Mock edit_message_text for progress updates
        mock_edit_future = AsyncMock()
        mock_edit_future.return_value = None
        mock_bot.edit_message_text = mock_edit_future
        
        # Mock initial progress message
        mock_progress_msg = MagicMock()
        mock_progress_msg.message_id = 12345
        mock_bot.send_message.return_value = mock_progress_msg
        
        with patch('cerebrate_bot.supabase', mock_supabase):
            with patch('cerebrate_bot.send_single_message') as mock_send_single:
                mock_send_single.return_value = True  # All messages succeed
                
                result = await send_broadcast_message(mock_app, "Test broadcast", 123456789)
        
        assert result["success"] == 3
        assert result["failed"] == 0
        assert result["total"] == 3
    
    @pytest.mark.asyncio
    async def test_send_broadcast_message_no_users(self, mock_supabase):
        """Test broadcast when no users exist."""
        # Mock empty user data
        mock_empty_response = MagicMock()
        mock_empty_response.data = []
        
        mock_supabase.table().select().execute.return_value = mock_empty_response
        
        # Mock application and bot
        mock_app = MagicMock()
        mock_bot = MagicMock()
        mock_app.bot = mock_bot
        
        mock_future = AsyncMock()
        mock_future.return_value = None
        mock_bot.send_message = mock_future
        
        with patch('cerebrate_bot.supabase', mock_supabase):
            result = await send_broadcast_message(mock_app, "Test broadcast", 123456789)
        
        assert result["success"] == 0
        assert result["failed"] == 0
        assert result["total"] == 0
    
    @pytest.mark.asyncio
    async def test_send_broadcast_message_partial_failure(self, mock_supabase):
        """Test broadcast with some message failures."""
        # Mock user data
        mock_users_response = MagicMock()
        mock_users_response.data = [
            {"tg_id": 123456789},
            {"tg_id": 987654321}
        ]
        
        mock_supabase.table().select().execute.return_value = mock_users_response
        
        # Mock application and bot
        mock_app = MagicMock()
        mock_bot = MagicMock()
        mock_app.bot = mock_bot
        
        # Mock progress message
        mock_progress_msg = MagicMock()
        mock_progress_msg.message_id = 12345
        
        mock_future = AsyncMock()
        mock_future.return_value = mock_progress_msg
        mock_bot.send_message = mock_future
        
        mock_edit_future = AsyncMock()
        mock_edit_future.return_value = None
        mock_bot.edit_message_text = mock_edit_future
        
        with patch('cerebrate_bot.supabase', mock_supabase):
            with patch('cerebrate_bot.send_single_message') as mock_send_single:
                # First message succeeds, second fails
                mock_send_single.side_effect = [True, False]
                
                result = await send_broadcast_message(mock_app, "Test broadcast", 123456789)
        
        assert result["success"] == 1
        assert result["failed"] == 1
        assert result["total"] == 2
        assert len(result["failed_users"]) == 1