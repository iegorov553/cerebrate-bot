"""
Integration tests for the Hour Watcher Bot.
"""
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

@pytest.mark.integration
class TestBotIntegration:
    """Integration tests for bot functionality."""
    
    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Complex integration test with multiple async dependencies")
    async def test_user_registration_flow(self, mock_supabase, mock_telegram_update, mock_telegram_context):
        """Test complete user registration flow."""
        # Mock user doesn't exist initially
        mock_empty_response = MagicMock()
        mock_empty_response.data = []
        
        # Mock successful user creation
        mock_create_response = MagicMock()
        mock_create_response.data = [{"user_id": "new-user-id"}]
        
        mock_table = mock_supabase.table()
        mock_table.select().eq().execute.side_effect = [
            mock_empty_response,  # User doesn't exist
            mock_create_response  # User created
        ]
        mock_table.insert().execute.return_value = mock_create_response
        
        with patch('cerebrate_bot.supabase', mock_supabase):
            from cerebrate_bot import ensure_user_exists
            
            await ensure_user_exists(
                tg_id=123456789,
                username="testuser",
                first_name="Test",
                last_name="User"
            )
        
        # Verify user was created
        mock_table.insert.assert_called_once()
        create_call_args = mock_table.insert.call_args[0][0]
        assert create_call_args["tg_id"] == 123456789
        assert create_call_args["tg_username"] == "testuser"
    
    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Complex integration test with multiple async dependencies")
    async def test_friend_request_workflow(self, mock_supabase):
        """Test complete friend request workflow."""
        with patch('cerebrate_bot.supabase', mock_supabase):
            from cerebrate_bot import create_friend_request, update_friend_request

            # Mock no existing friendship
            mock_empty_response = MagicMock()
            mock_empty_response.data = []
            
            # Mock successful operations
            mock_success_response = MagicMock()
            
            mock_table = mock_supabase.table()
            mock_table.select().eq().eq().execute.return_value = mock_empty_response
            mock_table.insert().execute.return_value = mock_success_response
            mock_table.update().eq().execute.return_value = mock_success_response
            
            # Create friend request
            result1 = await create_friend_request(123456789, 987654321)
            assert result1 is True
            
            # Accept friend request
            result2 = await update_friend_request("test-friendship-id", "accepted")
            assert result2 is True
    
    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Complex integration test with multiple async dependencies")
    async def test_notification_scheduling_integration(self, mock_supabase):
        """Test notification scheduling with user settings."""
        # Mock user with specific settings
        mock_user_response = MagicMock()
        mock_user_response.data = [{
            "tg_id": 123456789,
            "enabled": True,
            "window_start": "09:00:00",
            "window_end": "17:00:00",
            "interval_min": 60,
            "last_notification_sent": None
        }]
        
        mock_supabase.table().select().eq().execute.return_value = mock_user_response
        
        with patch('cerebrate_bot.supabase', mock_supabase):
            from cerebrate_bot import get_user_settings_cached
            
            settings = await get_user_settings_cached(123456789)
            
            assert settings is not None
            assert settings["enabled"] is True
            assert settings["interval_min"] == 60
    
    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Complex integration test with multiple async dependencies")
    async def test_cache_integration(self):
        """Test cache integration with database functions."""
        from cerebrate_bot import CacheManager, get_user_settings_cached

        # Create cache instance
        cache = CacheManager()
        
        # Mock database response
        mock_user_data = {
            "tg_id": 123456789,
            "enabled": True,
            "window_start": "09:00:00",
            "window_end": "17:00:00",
            "interval_min": 60
        }
        
        with patch('cerebrate_bot.supabase') as mock_supabase:
            mock_response = MagicMock()
            mock_response.data = [mock_user_data]
            mock_supabase.table().select().eq().execute.return_value = mock_response
            
            with patch('cerebrate_bot.cache', cache):
                # First call should hit database
                result1 = await get_user_settings_cached(123456789)
                
                # Second call should hit cache
                result2 = await get_user_settings_cached(123456789)
                
                assert result1 == mock_user_data
                assert result2 == mock_user_data
                
                # Database should only be called once
                assert mock_supabase.table().select().eq().execute.call_count == 1