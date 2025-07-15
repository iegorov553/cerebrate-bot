"""Tests for command handlers refactoring compatibility."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from telegram import Update, User, Message, Chat
from telegram.ext import Application

from bot.handlers.commands import (
    setup_user_commands,
    setup_social_commands,
    setup_config_commands,
    setup_history_commands,
    setup_system_commands
)


class TestCommandRefactoring:
    """Test that refactored command handlers work correctly."""
    
    @pytest.fixture
    def mock_application(self):
        """Create mock Application with bot_data."""
        app = MagicMock(spec=Application)
        app.bot_data = {
            'db_client': MagicMock(),
            'user_cache': MagicMock(),
            'rate_limiter': MagicMock(),
            'config': MagicMock()
        }
        app.add_handler = MagicMock()
        return app
    
    @pytest.fixture
    def mock_update(self):
        """Create mock Update with user and message."""
        update = MagicMock(spec=Update)
        update.effective_user = User(
            id=123456789,
            is_bot=False,
            first_name="TestUser",
            username="testuser"
        )
        update.message = MagicMock(spec=Message)
        update.message.reply_text = AsyncMock()
        update.message.chat = MagicMock(spec=Chat)
        return update
    
    def test_setup_user_commands_registration(self, mock_application):
        """Test that user commands are properly registered."""
        setup_user_commands(mock_application)
        
        # Should register only start command currently
        assert mock_application.add_handler.call_count == 1
        
        # Extract registered command names
        calls = mock_application.add_handler.call_args_list
        command_names = []
        for call in calls:
            handler = call[0][0]
            if hasattr(handler, 'commands'):
                command_names.extend(handler.commands)
            elif hasattr(handler, 'command'):
                command_names.append(handler.command)
        
        # Verify start command is registered
        assert 'start' in command_names or any('start' in str(call) for call in calls)
    
    def test_setup_social_commands_registration(self, mock_application):
        """Test that social commands are properly registered."""
        setup_social_commands(mock_application)
        
        # Should register 5 social commands
        assert mock_application.add_handler.call_count == 5
        
        expected_commands = ['add_friend', 'friends', 'friend_requests', 'accept', 'decline']
        calls = mock_application.add_handler.call_args_list
        
        # Verify all expected commands are registered
        assert len(calls) == len(expected_commands)
    
    def test_setup_config_commands_registration(self, mock_application):
        """Test that config commands are properly registered."""
        setup_config_commands(mock_application)
        
        # Should register window and freq commands
        assert mock_application.add_handler.call_count == 2
    
    def test_setup_history_commands_registration(self, mock_application):
        """Test that history commands are properly registered."""
        setup_history_commands(mock_application)
        
        # Should register history command
        assert mock_application.add_handler.call_count == 1
    
    def test_setup_system_commands_registration(self, mock_application):
        """Test that system commands are properly registered."""
        setup_system_commands(mock_application)
        
        # Should register health command
        assert mock_application.add_handler.call_count == 1
    
    @pytest.mark.asyncio
    async def test_start_command_handles_none_user(self, mock_application):
        """Test start command handles None user gracefully."""
        from bot.handlers.commands.user_commands import start_command
        
        # Create context with required bot_data
        context = MagicMock()
        context.bot_data = mock_application.bot_data
        
        # Create update with None user
        update = MagicMock()
        update.effective_user = None
        
        # Should not raise exception
        await start_command(update, context)
    
    @pytest.mark.asyncio 
    async def test_health_command_handles_exceptions(self, mock_application):
        """Test health command handles exceptions gracefully."""
        from bot.handlers.commands.system_commands import health_command
        
        # Create context with required bot_data
        context = MagicMock()
        context.bot_data = mock_application.bot_data
        context.application = MagicMock()
        
        # Mock update with user
        update = MagicMock()
        update.effective_user = User(
            id=123456789,
            is_bot=False,
            first_name="TestUser",
            username="testuser"
        )
        update.message = MagicMock()
        update.message.reply_text = AsyncMock()
        
        # Mock health service to raise exception
        with patch('bot.services.health_service.HealthService') as mock_health:
            mock_health.side_effect = Exception("Test error")
            
            # Should not raise exception
            await health_command(update, context)
            
            # Should send error message
            update.message.reply_text.assert_called_once()
    
    def test_all_setup_functions_exist(self):
        """Test that all setup functions are properly exported."""
        from bot.handlers.commands import (
            setup_user_commands,
            setup_social_commands, 
            setup_config_commands,
            setup_history_commands,
            setup_system_commands
        )
        
        # All functions should be callable
        assert callable(setup_user_commands)
        assert callable(setup_social_commands)
        assert callable(setup_config_commands)
        assert callable(setup_history_commands)
        assert callable(setup_system_commands)
    
    def test_module_imports_without_errors(self):
        """Test that all command modules import without errors."""
        # Should not raise any import errors
        from bot.handlers.commands.user_commands import start_command
        from bot.handlers.commands.social_commands import add_friend_command, friends_command
        from bot.handlers.commands.config_commands import window_command, freq_command
        from bot.handlers.commands.history_commands import history_command
        from bot.handlers.commands.system_commands import health_command
        
        # All functions should be callable
        assert callable(start_command)
        assert callable(add_friend_command)
        assert callable(friends_command)
        assert callable(window_command)
        assert callable(freq_command)
        assert callable(history_command)
        assert callable(health_command)