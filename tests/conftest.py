"""
Pytest configuration and fixtures for the Doyobi Diary tests.
"""
import asyncio
import os
from typing import AsyncGenerator, Generator
from unittest.mock import MagicMock, Mock

import pytest

# Set test environment variables
os.environ.update({
    "TELEGRAM_BOT_TOKEN": "test_token",
    "SUPABASE_URL": "https://test.supabase.co",
    "SUPABASE_SERVICE_ROLE_KEY": "test_key",
    "ADMIN_USER_ID": "123456789",
    "WEBAPP_URL": "https://test.vercel.app"
})

@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def mock_supabase():
    """Mock Supabase client for testing."""
    mock_client = MagicMock()

    # Mock table operations
    mock_table = MagicMock()
    mock_client.table.return_value = mock_table

    # Mock query builder
    mock_query = MagicMock()
    mock_table.select.return_value = mock_query
    mock_table.insert.return_value = mock_query
    mock_table.update.return_value = mock_query
    mock_table.delete.return_value = mock_query

    # Chain methods
    mock_query.eq.return_value = mock_query
    mock_query.gte.return_value = mock_query
    mock_query.order.return_value = mock_query
    mock_query.in_.return_value = mock_query
    mock_query.or_.return_value = mock_query

    return mock_client

@pytest.fixture
def sample_user_data():
    """Sample user data for testing."""
    return {
        "tg_id": 123456789,
        "tg_username": "testuser",
        "tg_first_name": "Test",
        "tg_last_name": "User",
        "enabled": True,
        "window_start": "09:00:00",
        "window_end": "18:00:00",
        "interval_min": 60,
        "created_at": "2023-01-01T00:00:00+00:00",
        "updated_at": "2023-01-01T00:00:00+00:00",
        "last_notification_sent": None
    }

@pytest.fixture
def sample_friendship_data():
    """Sample friendship data for testing."""
    return {
        "friendship_id": "550e8400-e29b-41d4-a716-446655440000",
        "requester_id": 123456789,
        "addressee_id": 987654321,
        "status": "pending",
        "created_at": "2023-01-01T00:00:00+00:00"
    }

@pytest.fixture
def mock_telegram_update():
    """Mock Telegram update object."""
    update = MagicMock()
    update.effective_user.id = 123456789
    update.effective_user.username = "testuser"
    update.effective_user.first_name = "Test"
    update.effective_user.last_name = "User"

    # Mock callback query
    callback_query = MagicMock()
    callback_query.data = "test_callback"
    callback_query.answer = Mock(return_value=asyncio.Future())
    callback_query.answer.return_value.set_result(None)
    callback_query.edit_message_text = Mock(return_value=asyncio.Future())
    callback_query.edit_message_text.return_value.set_result(None)

    update.callback_query = callback_query

    return update

@pytest.fixture
def mock_telegram_context():
    """Mock Telegram context object."""
    context = MagicMock()
    context.bot.send_message = Mock(return_value=asyncio.Future())
    context.bot.send_message.return_value.set_result(MagicMock())
    return context
