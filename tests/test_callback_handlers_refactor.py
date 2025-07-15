"""
Tests for refactored callback handlers.

Tests the new modular callback handler architecture including:
- BaseCallbackHandler functionality
- CallbackRouter routing logic
- NavigationCallbackHandler specifics
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from telegram import CallbackQuery, Update, User
from telegram.ext import ContextTypes

from bot.cache.ttl_cache import TTLCache
from bot.config import Config
from bot.database.client import DatabaseClient
from bot.handlers.base.base_handler import BaseCallbackHandler
from bot.handlers.base.callback_router import CallbackRouter
from bot.handlers.callbacks.admin_callbacks import AdminCallbackHandler
from bot.handlers.callbacks.feedback_callbacks import FeedbackCallbackHandler
from bot.handlers.callbacks.friends_callbacks import FriendsCallbackHandler
from bot.handlers.callbacks.navigation_callbacks import NavigationCallbackHandler
from bot.handlers.callbacks.questions_callbacks import QuestionsCallbackHandler
from bot.i18n.translator import Translator


class TestBaseCallbackHandler:
    """Test BaseCallbackHandler common functionality."""

    @pytest.fixture
    def mock_dependencies(self):
        """Create mock dependencies."""
        db_client = MagicMock(spec=DatabaseClient)
        config = MagicMock(spec=Config)
        user_cache = MagicMock(spec=TTLCache)
        return db_client, config, user_cache

    @pytest.fixture
    def concrete_handler(self, mock_dependencies):
        """Create a concrete handler for testing."""
        db_client, config, user_cache = mock_dependencies

        class TestHandler(BaseCallbackHandler):
            async def handle_callback(self, query, data, translator, context):
                pass

            def can_handle(self, data):
                return data.startswith("test_")

        return TestHandler(db_client, config, user_cache)

    @pytest.mark.asyncio
    async def test_get_user_language_success(self, concrete_handler):
        """Test successful user language retrieval."""
        with patch("bot.database.user_operations.UserOperations") as mock_user_ops:
            # Mock successful language retrieval
            mock_instance = mock_user_ops.return_value
            mock_instance.get_user_settings = AsyncMock(return_value={"language": "en"})

            language = await concrete_handler.get_user_language(123456789)

            assert language == "en"
            mock_instance.get_user_settings.assert_called_once_with(123456789, force_refresh=False)

    @pytest.mark.asyncio
    async def test_get_user_language_fallback(self, concrete_handler):
        """Test fallback to default language when retrieval fails."""
        with patch("bot.database.user_operations.UserOperations") as mock_user_ops:
            # Mock failed language retrieval
            mock_instance = mock_user_ops.return_value
            mock_instance.get_user_settings = AsyncMock(side_effect=Exception("DB error"))

            language = await concrete_handler.get_user_language(123456789)

            assert language == "ru"  # Default fallback

    @pytest.mark.asyncio
    async def test_get_user_translator(self, concrete_handler):
        """Test translator creation with user's language."""
        with patch.object(concrete_handler, "get_user_language", return_value="es"):
            translator = await concrete_handler.get_user_translator(123456789)

            assert isinstance(translator, Translator)
            assert translator.current_language == "es"

    def test_setup_user_context(self, concrete_handler):
        """Test user context setup for monitoring."""
        user = MagicMock(spec=User)
        user.id = 123456789
        user.username = "testuser"
        user.first_name = "Test"

        with patch("bot.handlers.base.base_handler.set_user_context") as mock_set_context:
            concrete_handler.setup_user_context(user)

            mock_set_context.assert_called_once_with(123456789, "testuser", "Test")

    @pytest.mark.asyncio
    async def test_ensure_user_exists(self, concrete_handler):
        """Test user existence check and creation."""
        user = MagicMock(spec=User)
        user.id = 123456789
        user.username = "testuser"
        user.first_name = "Test"
        user.last_name = "User"

        with patch("bot.database.user_operations.UserOperations") as mock_user_ops:
            mock_instance = mock_user_ops.return_value
            mock_instance.ensure_user_exists = AsyncMock(return_value={"tg_id": 123456789, "tg_username": "testuser"})

            user_data = await concrete_handler.ensure_user_exists(user)

            assert user_data["tg_id"] == 123456789
            mock_instance.ensure_user_exists.assert_called_once_with(
                tg_id=123456789, username="testuser", first_name="Test", last_name="User"
            )

    def test_should_force_language_refresh(self, concrete_handler):
        """Test language refresh detection."""
        assert concrete_handler.should_force_language_refresh("language_en")
        assert concrete_handler.should_force_language_refresh("menu_language")
        assert concrete_handler.should_force_language_refresh("settings_enable") is False


class TestCallbackRouter:
    """Test CallbackRouter functionality."""

    @pytest.fixture
    def mock_dependencies(self):
        """Create mock dependencies."""
        db_client = MagicMock(spec=DatabaseClient)
        config = MagicMock(spec=Config)
        user_cache = MagicMock(spec=TTLCache)
        return db_client, config, user_cache

    @pytest.fixture
    def router(self, mock_dependencies):
        """Create router instance."""
        db_client, config, user_cache = mock_dependencies
        return CallbackRouter(db_client, config, user_cache)

    @pytest.fixture
    def mock_handler(self, mock_dependencies):
        """Create mock handler."""
        db_client, config, user_cache = mock_dependencies

        class MockHandler(BaseCallbackHandler):
            async def handle_callback(self, query, data, translator, context):
                pass

            def can_handle(self, data):
                return data.startswith("test_")

        return MockHandler(db_client, config, user_cache)

    def test_register_handler(self, router, mock_handler):
        """Test handler registration."""
        router.register_handler(mock_handler)

        assert len(router.handlers) == 1
        assert router.handlers[0] == mock_handler

    def test_find_handler_success(self, router, mock_handler):
        """Test successful handler finding."""
        router.register_handler(mock_handler)

        found_handler = router.find_handler("test_callback")

        assert found_handler == mock_handler

    def test_find_handler_not_found(self, router, mock_handler):
        """Test handler not found scenario."""
        router.register_handler(mock_handler)

        found_handler = router.find_handler("unknown_callback")

        assert found_handler is None

    @pytest.mark.asyncio
    async def test_route_callback_success(self, router, mock_handler):
        """Test successful callback routing."""
        # Setup mocks
        query = MagicMock(spec=CallbackQuery)
        query.data = "test_callback"
        query.answer = AsyncMock()
        query.from_user = MagicMock(spec=User)
        query.from_user.id = 123456789

        user = MagicMock(spec=User)
        user.id = 123456789

        update = MagicMock(spec=Update)
        update.callback_query = query
        update.effective_user = user

        context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)

        # Register handler and mock execute
        router.register_handler(mock_handler)
        mock_handler.execute = AsyncMock()

        await router.route_callback(update, context)

        # Verify
        query.answer.assert_called_once()
        mock_handler.execute.assert_called_once_with(query, "test_callback", context)

    @pytest.mark.asyncio
    async def test_route_callback_no_handler(self, router):
        """Test callback routing when no handler is found."""
        # Setup mocks
        query = MagicMock(spec=CallbackQuery)
        query.data = "unknown_callback"
        query.answer = AsyncMock()
        query.edit_message_text = AsyncMock()
        query.from_user = MagicMock(spec=User)
        query.from_user.id = 123456789

        user = MagicMock(spec=User)
        user.id = 123456789

        update = MagicMock(spec=Update)
        update.callback_query = query
        update.effective_user = user

        context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)

        await router.route_callback(update, context)

        # Verify fallback behavior
        query.answer.assert_called_once()
        query.edit_message_text.assert_called_once()

    def test_get_handler_stats(self, router, mock_handler):
        """Test handler statistics."""
        router.register_handler(mock_handler)

        stats = router.get_handler_stats()

        assert stats["total_handlers"] == 1
        assert "MockHandler" in stats["handler_classes"]


class TestNavigationCallbackHandler:
    """Test NavigationCallbackHandler specifics."""

    @pytest.fixture
    def mock_dependencies(self):
        """Create mock dependencies."""
        db_client = MagicMock(spec=DatabaseClient)
        config = MagicMock(spec=Config)
        config.is_admin_configured.return_value = True
        config.admin_user_id = 987654321
        config.webapp_url = "https://test-webapp.com"
        user_cache = MagicMock(spec=TTLCache)
        return db_client, config, user_cache

    @pytest.fixture
    def handler(self, mock_dependencies):
        """Create NavigationCallbackHandler instance."""
        db_client, config, user_cache = mock_dependencies
        return NavigationCallbackHandler(db_client, config, user_cache)

    def test_can_handle_navigation_callbacks(self, handler):
        """Test callback data recognition."""
        assert handler.can_handle("back_main")
        assert handler.can_handle("menu_language")
        assert handler.can_handle("language_en")
        assert handler.can_handle("menu_history") is False  # Now handled by WebApp directly
        assert handler.can_handle("history") is False  # Now handled by WebApp directly
        assert handler.can_handle("settings_enable") is False

    @pytest.mark.asyncio
    async def test_handle_main_menu(self, handler):
        """Test main menu handling."""
        query = MagicMock(spec=CallbackQuery)
        query.from_user = MagicMock(spec=User)
        query.from_user.id = 123456789
        query.from_user.first_name = "Test"
        query.edit_message_text = AsyncMock()

        translator = MagicMock(spec=Translator)
        translator.translate.side_effect = lambda key, **kwargs: f"translated_{key}"

        context = MagicMock()

        with patch("bot.handlers.callbacks.navigation_callbacks.KeyboardGenerator") as mock_keyboard:
            mock_keyboard.main_menu.return_value = "mock_keyboard"

            await handler.handle_callback(query, "back_main", translator, context)

            query.edit_message_text.assert_called_once()
            mock_keyboard.main_menu.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_language_change(self, handler):
        """Test language change handling."""
        query = MagicMock(spec=CallbackQuery)
        query.from_user = MagicMock(spec=User)
        query.from_user.id = 123456789
        query.edit_message_text = AsyncMock()

        translator = MagicMock(spec=Translator)
        translator.current_language = "ru"

        context = MagicMock()

        with patch("bot.database.user_operations.UserOperations") as mock_user_ops, patch(
            "bot.i18n.translator.Translator"
        ) as mock_translator_class, patch("bot.handlers.callbacks.navigation_callbacks.KeyboardGenerator") as mock_keyboard:
            # Mock user operations
            mock_instance = mock_user_ops.return_value
            mock_instance.update_user_settings = AsyncMock(return_value=True)

            # Mock new translator
            mock_new_translator = MagicMock()
            mock_new_translator.get_language_info.return_value = {"native": "English", "flag": "🇺🇸"}
            mock_new_translator.translate.return_value = "Language changed"
            mock_translator_class.return_value = mock_new_translator

            # Mock keyboard
            mock_keyboard.main_menu.return_value = "mock_keyboard"

            await handler.handle_callback(query, "language_en", translator, context)

            # Verify language update
            mock_instance.update_user_settings.assert_called_once_with(123456789, {"language": "en"})
            query.edit_message_text.assert_called_once()


class TestFeedbackCallbackHandler:
    """Test FeedbackCallbackHandler specifics."""

    @pytest.fixture
    def mock_dependencies(self):
        """Create mock dependencies."""
        db_client = MagicMock(spec=DatabaseClient)
        config = MagicMock(spec=Config)
        config.is_feedback_enabled.return_value = True
        config.feedback_rate_limit = 3600  # 1 hour
        user_cache = MagicMock(spec=TTLCache)
        return db_client, config, user_cache

    @pytest.fixture
    def handler(self, mock_dependencies):
        """Create FeedbackCallbackHandler instance."""
        db_client, config, user_cache = mock_dependencies
        return FeedbackCallbackHandler(db_client, config, user_cache)

    def test_can_handle_feedback_callbacks(self, handler):
        """Test callback data recognition."""
        assert handler.can_handle("menu_feedback")
        assert handler.can_handle("feedback_menu")
        assert handler.can_handle("feedback_bug_report")
        assert handler.can_handle("feedback_feature_request")
        assert handler.can_handle("feedback_general")
        assert handler.can_handle("settings_view") is False
        assert handler.can_handle("friends_list") is False

    @pytest.mark.asyncio
    async def test_handle_feedback_menu_enabled(self, handler):
        """Test feedback menu when feedback is enabled."""
        query = MagicMock(spec=CallbackQuery)
        query.from_user = MagicMock(spec=User)
        query.from_user.id = 123456789
        query.edit_message_text = AsyncMock()

        translator = MagicMock(spec=Translator)
        translator.translate.side_effect = lambda key, **kwargs: f"translated_{key}"

        context = MagicMock()

        await handler.handle_callback(query, "feedback_menu", translator, context)

        # Verify menu is displayed
        query.edit_message_text.assert_called_once()

        # Check that translator was called for feedback texts
        translator.translate.assert_called()

    @pytest.mark.asyncio
    async def test_handle_feedback_menu_disabled(self, handler):
        """Test feedback menu when feedback is disabled."""
        # Override config to disable feedback
        handler.config.is_feedback_enabled.return_value = False

        query = MagicMock(spec=CallbackQuery)
        query.from_user = MagicMock(spec=User)
        query.from_user.id = 123456789
        query.edit_message_text = AsyncMock()

        translator = MagicMock(spec=Translator)
        translator.translate.return_value = "Feedback disabled"

        context = MagicMock()

        await handler.handle_callback(query, "feedback_menu", translator, context)

        # Verify disabled message is shown
        query.edit_message_text.assert_called_once()
        translator.translate.assert_called_with("feedback.disabled")

    @pytest.mark.asyncio
    async def test_start_feedback_session(self, handler):
        """Test starting a feedback session."""
        query = MagicMock(spec=CallbackQuery)
        query.from_user = MagicMock(spec=User)
        query.from_user.id = 123456789
        query.edit_message_text = AsyncMock()

        translator = MagicMock(spec=Translator)
        translator.translate.side_effect = lambda key, **kwargs: f"translated_{key}"

        context = MagicMock()

        with patch("bot.feedback.FeedbackManager") as mock_feedback_manager, patch(
            "bot.utils.rate_limiter.MultiTierRateLimiter"
        ):
            # Mock feedback manager
            mock_manager_instance = mock_feedback_manager.return_value
            mock_manager_instance.check_rate_limit = AsyncMock(return_value=True)
            mock_manager_instance.start_feedback_session = AsyncMock(return_value=True)

            await handler.handle_callback(query, "feedback_bug_report", translator, context)

            # Verify session started
            mock_manager_instance.start_feedback_session.assert_called_once()
            query.edit_message_text.assert_called_once()


class TestFriendsCallbackHandler:
    """Test FriendsCallbackHandler specifics."""

    @pytest.fixture
    def mock_dependencies(self):
        """Create mock dependencies."""
        db_client = MagicMock(spec=DatabaseClient)
        config = MagicMock(spec=Config)
        config.is_admin_configured.return_value = False
        user_cache = MagicMock(spec=TTLCache)
        return db_client, config, user_cache

    @pytest.fixture
    def handler(self, mock_dependencies):
        """Create FriendsCallbackHandler instance."""
        db_client, config, user_cache = mock_dependencies
        return FriendsCallbackHandler(db_client, config, user_cache)

    def test_can_handle_friends_callbacks(self, handler):
        """Test callback data recognition."""
        assert handler.can_handle("menu_friends")
        assert handler.can_handle("friends")
        assert handler.can_handle("friends_list")
        assert handler.can_handle("friends_add")
        assert handler.can_handle("friends_discover")
        assert handler.can_handle("add_friend:123456")
        assert handler.can_handle("settings_view") is False
        assert handler.can_handle("feedback_menu") is False

    @pytest.mark.asyncio
    async def test_handle_friends_menu(self, handler):
        """Test friends menu display."""
        query = MagicMock(spec=CallbackQuery)
        query.from_user = MagicMock(spec=User)
        query.from_user.id = 123456789
        query.edit_message_text = AsyncMock()

        translator = MagicMock(spec=Translator)
        translator.translate.side_effect = lambda key, **kwargs: f"translated_{key}"

        context = MagicMock()

        with patch("bot.handlers.callbacks.friends_callbacks.create_friends_menu") as mock_menu:
            mock_menu.return_value = "mock_friends_menu"

            await handler.handle_callback(query, "friends", translator, context)

            # Verify menu is displayed
            query.edit_message_text.assert_called_once()
            mock_menu.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_friends_list_empty(self, handler):
        """Test friends list when user has no friends."""
        query = MagicMock(spec=CallbackQuery)
        query.from_user = MagicMock(spec=User)
        query.from_user.id = 123456789
        query.edit_message_text = AsyncMock()

        translator = MagicMock(spec=Translator)
        translator.translate.return_value = "No friends found"

        context = MagicMock()

        with patch("bot.database.friend_operations.FriendOperations") as mock_friend_ops, patch(
            "bot.handlers.callbacks.friends_callbacks.create_friends_menu"
        ) as mock_menu:
            # Mock empty friends list
            mock_instance = mock_friend_ops.return_value
            mock_instance.get_friends_list_optimized = AsyncMock(return_value=[])

            mock_menu.return_value = "mock_friends_menu"

            await handler.handle_callback(query, "friends_list", translator, context)

            # Verify empty message is shown
            query.edit_message_text.assert_called_once()
            translator.translate.assert_called_with("friends.list_empty")

    @pytest.mark.asyncio
    async def test_handle_friends_list_with_friends(self, handler):
        """Test friends list when user has friends."""
        query = MagicMock(spec=CallbackQuery)
        query.from_user = MagicMock(spec=User)
        query.from_user.id = 123456789
        query.edit_message_text = AsyncMock()

        translator = MagicMock(spec=Translator)
        translator.translate.side_effect = lambda key, **kwargs: f"translated_{key}"

        context = MagicMock()

        with patch("bot.database.friend_operations.FriendOperations") as mock_friend_ops, patch(
            "bot.handlers.callbacks.friends_callbacks.create_friends_menu"
        ) as mock_menu:
            # Mock friends list
            mock_instance = mock_friend_ops.return_value
            mock_instance.get_friends_list_optimized = AsyncMock(
                return_value=[
                    {"tg_username": "friend1", "tg_first_name": "Friend One"},
                    {"tg_username": "friend2", "tg_first_name": "Friend Two"},
                ]
            )

            mock_menu.return_value = "mock_friends_menu"

            await handler.handle_callback(query, "friends_list", translator, context)

            # Verify friends list is shown
            query.edit_message_text.assert_called_once()

            # Check that friends are included in the message
            call_args = query.edit_message_text.call_args
            message_text = call_args[0][0]
            assert "Friend One" in message_text
            assert "Friend Two" in message_text

    @pytest.mark.asyncio
    async def test_handle_add_friend_callback(self, handler):
        """Test add friend callback functionality."""
        query = MagicMock(spec=CallbackQuery)
        query.from_user = MagicMock(spec=User)
        query.from_user.id = 123456789
        query.answer = AsyncMock()
        query.edit_message_text = AsyncMock()

        translator = MagicMock(spec=Translator)
        translator.translate.return_value = "Friend request sent"

        context = MagicMock()
        context.bot_data = {}  # No rate limiter for simplicity

        with patch("bot.database.friend_operations.FriendOperations") as mock_friend_ops:
            # Mock successful friend request
            mock_instance = mock_friend_ops.return_value
            mock_instance.send_friend_request_by_id = AsyncMock(return_value=(True, "Success"))
            mock_instance.get_friends_of_friends_optimized = AsyncMock(return_value=[])

            await handler.handle_callback(query, "add_friend:987654321", translator, context)

            # Verify friend request was sent
            mock_instance.send_friend_request_by_id.assert_called_once_with(123456789, 987654321)
            query.answer.assert_called_once()


class TestAdminCallbackHandler:
    """Test AdminCallbackHandler specifics."""

    @pytest.fixture
    def mock_dependencies(self):
        """Create mock dependencies."""
        db_client = MagicMock(spec=DatabaseClient)
        config = MagicMock(spec=Config)
        config.is_admin_configured.return_value = True
        config.admin_user_id = 987654321
        user_cache = MagicMock(spec=TTLCache)
        return db_client, config, user_cache

    @pytest.fixture
    def handler(self, mock_dependencies):
        """Create AdminCallbackHandler instance."""
        db_client, config, user_cache = mock_dependencies
        return AdminCallbackHandler(db_client, config, user_cache)

    def test_can_handle_admin_callbacks(self, handler):
        """Test callback data recognition."""
        assert handler.can_handle("menu_admin")
        assert handler.can_handle("admin_panel")
        assert handler.can_handle("admin_broadcast")
        assert handler.can_handle("admin_stats")
        assert handler.can_handle("admin_health")
        assert handler.can_handle("settings_view") is False
        assert handler.can_handle("friends_list") is False

    @pytest.mark.asyncio
    async def test_handle_admin_panel_access_granted(self, handler):
        """Test admin panel access for admin user."""
        query = MagicMock(spec=CallbackQuery)
        query.from_user = MagicMock(spec=User)
        query.from_user.id = 987654321  # Admin user
        query.edit_message_text = AsyncMock()

        translator = MagicMock(spec=Translator)
        translator.translate.side_effect = lambda key, **kwargs: f"translated_{key}"

        context = MagicMock()

        with patch("bot.admin.admin_operations.AdminOperations") as mock_admin_ops, patch(
            "bot.utils.version.format_version_string"
        ) as mock_version, patch("bot.utils.version.get_version_info") as mock_version_info, patch(
            "bot.handlers.callbacks.admin_callbacks.KeyboardGenerator"
        ) as mock_keyboard:
            # Mock admin operations
            mock_admin_instance = mock_admin_ops.return_value
            mock_admin_instance.is_admin.return_value = True

            # Mock version info
            mock_version.return_value = "2.1.19"
            mock_version_info.return_value = {"environment": "test"}

            # Mock keyboard
            mock_keyboard.admin_menu.return_value = "mock_admin_menu"

            await handler.handle_callback(query, "admin_panel", translator, context)

            # Verify admin panel is displayed
            query.edit_message_text.assert_called_once()
            mock_keyboard.admin_menu.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_admin_panel_access_denied(self, handler):
        """Test admin panel access for non-admin user."""
        query = MagicMock(spec=CallbackQuery)
        query.from_user = MagicMock(spec=User)
        query.from_user.id = 123456789  # Non-admin user
        query.edit_message_text = AsyncMock()

        translator = MagicMock(spec=Translator)
        translator.translate.side_effect = lambda key, **kwargs: f"translated_{key}"

        context = MagicMock()

        with patch("bot.admin.admin_operations.AdminOperations") as mock_admin_ops, patch(
            "bot.handlers.callbacks.admin_callbacks.KeyboardGenerator"
        ) as mock_keyboard:
            # Mock admin operations - access denied
            mock_admin_instance = mock_admin_ops.return_value
            mock_admin_instance.is_admin.return_value = False

            # Mock keyboard
            mock_keyboard.main_menu.return_value = "mock_main_menu"

            await handler.handle_callback(query, "admin_panel", translator, context)

            # Verify access denied message
            query.edit_message_text.assert_called_once()
            mock_keyboard.main_menu.assert_called_once_with(False, translator)

    @pytest.mark.asyncio
    async def test_handle_health_check(self, handler):
        """Test admin health check functionality."""
        query = MagicMock(spec=CallbackQuery)
        query.from_user = MagicMock(spec=User)
        query.from_user.id = 987654321  # Admin user
        query.edit_message_text = AsyncMock()

        translator = MagicMock(spec=Translator)
        translator.translate.side_effect = lambda key, **kwargs: f"translated_{key}"

        context = MagicMock()
        context.application = MagicMock()

        with patch("bot.admin.admin_operations.AdminOperations") as mock_admin_ops, patch(
            "bot.services.health_service.HealthService"
        ) as mock_health_service, patch("bot.utils.version.get_bot_version") as mock_get_version, patch(
            "bot.handlers.callbacks.admin_callbacks.KeyboardGenerator"
        ) as mock_keyboard:
            # Mock admin access
            mock_admin_instance = mock_admin_ops.return_value
            mock_admin_instance.is_admin.return_value = True

            # Mock health service
            mock_health_instance = mock_health_service.return_value
            mock_health_status = MagicMock()
            mock_health_status.status = "healthy"
            mock_health_status.timestamp = "2025-07-12T10:00:00Z"
            mock_health_status.version = "2.1.19"
            mock_health_status.uptime_seconds = 3600.0
            mock_health_status.components = {}
            mock_health_instance.get_system_health = AsyncMock(return_value=mock_health_status)

            # Mock version and keyboard
            mock_get_version.return_value = "2.1.19"
            mock_keyboard.admin_menu.return_value = "mock_admin_menu"

            await handler.handle_callback(query, "admin_health", translator, context)

            # Verify health check was performed
            mock_health_instance.get_system_health.assert_called_once()
            assert query.edit_message_text.call_count >= 2  # Loading message + result


class TestQuestionsCallbackHandler:
    """Test QuestionsCallbackHandler specifics."""

    @pytest.fixture
    def mock_dependencies(self):
        """Create mock dependencies."""
        db_client = MagicMock(spec=DatabaseClient)
        config = MagicMock(spec=Config)
        config.is_admin_configured.return_value = False
        user_cache = MagicMock(spec=TTLCache)
        return db_client, config, user_cache

    @pytest.fixture
    def handler(self, mock_dependencies):
        """Create QuestionsCallbackHandler instance."""
        db_client, config, user_cache = mock_dependencies
        return QuestionsCallbackHandler(db_client, config, user_cache)

    def test_can_handle_questions_callbacks(self, handler):
        """Test callback data recognition."""
        assert handler.can_handle("menu_questions")
        assert handler.can_handle("questions")
        assert handler.can_handle("questions_noop")
        assert handler.can_handle("questions_create")
        assert handler.can_handle("questions_list")
        assert handler.can_handle("questions_edit:123")
        assert handler.can_handle("questions_delete:456")
        assert handler.can_handle("settings_view") is False
        assert handler.can_handle("admin_panel") is False

    @pytest.mark.asyncio
    async def test_handle_questions_menu(self, handler):
        """Test questions menu display."""
        query = MagicMock(spec=CallbackQuery)
        query.from_user = MagicMock(spec=User)
        query.from_user.id = 123456789
        query.edit_message_text = AsyncMock()

        translator = MagicMock(spec=Translator)
        translator.translate.side_effect = lambda key, **kwargs: f"translated_{key}"

        context = MagicMock()

        with patch("bot.questions.QuestionManager") as mock_question_manager, patch(
            "bot.database.user_operations.UserOperations"
        ) as mock_user_ops, patch("bot.handlers.callbacks.questions_callbacks.create_questions_menu") as mock_menu:
            # Mock question manager
            mock_manager_instance = mock_question_manager.return_value
            mock_manager_instance.get_user_questions_summary = AsyncMock(
                return_value={"questions": [{"id": 1, "text": "Test question"}]}
            )

            # Mock user operations
            mock_user_instance = mock_user_ops.return_value
            mock_user_instance.get_user_settings = AsyncMock(return_value={"enabled": True})

            # Mock menu creation
            mock_menu.return_value = "mock_questions_menu"

            await handler.handle_callback(query, "questions", translator, context)

            # Verify menu is displayed
            query.edit_message_text.assert_called_once()
            mock_menu.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_list_questions_empty(self, handler):
        """Test questions list when user has no questions."""
        query = MagicMock(spec=CallbackQuery)
        query.from_user = MagicMock(spec=User)
        query.from_user.id = 123456789
        query.edit_message_text = AsyncMock()

        translator = MagicMock(spec=Translator)
        translator.translate.return_value = "No questions found"

        context = MagicMock()

        with patch("bot.questions.QuestionManager") as mock_question_manager:
            # Mock empty questions list
            mock_manager_instance = mock_question_manager.return_value
            mock_manager_instance.question_ops.get_user_questions = AsyncMock(return_value=[])

            await handler.handle_callback(query, "questions_list", translator, context)

            # Verify empty message is shown
            query.edit_message_text.assert_called_once()
            translator.translate.assert_called_with("questions.list_empty")

    @pytest.mark.asyncio
    async def test_handle_question_toggle(self, handler):
        """Test question status toggle."""
        query = MagicMock(spec=CallbackQuery)
        query.from_user = MagicMock(spec=User)
        query.from_user.id = 123456789
        query.edit_message_text = AsyncMock()

        translator = MagicMock(spec=Translator)
        translator.translate.return_value = "Question toggled"

        context = MagicMock()

        with patch("bot.questions.QuestionManager") as mock_question_manager:
            # Mock successful toggle
            mock_manager_instance = mock_question_manager.return_value
            mock_manager_instance.question_ops.toggle_question_status = AsyncMock(return_value=True)

            await handler.handle_callback(query, "questions_toggle:123", translator, context)

            # Verify toggle was called
            mock_manager_instance.question_ops.toggle_question_status.assert_called_once_with(123)
            query.edit_message_text.assert_called_once()


@pytest.mark.asyncio
async def test_integration_router_with_navigation_handler():
    """Integration test: router with navigation handler."""
    # Setup
    db_client = MagicMock(spec=DatabaseClient)
    config = MagicMock(spec=Config)
    config.is_admin_configured.return_value = False
    user_cache = MagicMock(spec=TTLCache)

    router = CallbackRouter(db_client, config, user_cache)
    nav_handler = NavigationCallbackHandler(db_client, config, user_cache)
    router.register_handler(nav_handler)

    # Mock callback query
    query = MagicMock(spec=CallbackQuery)
    query.data = "back_main"
    query.answer = AsyncMock()
    query.from_user = MagicMock(spec=User)
    query.from_user.id = 123456789
    query.from_user.first_name = "Test"

    update = MagicMock(spec=Update)
    update.callback_query = query
    update.effective_user = query.from_user

    context = MagicMock()

    # Mock handler execute
    nav_handler.execute = AsyncMock()

    # Execute
    await router.route_callback(update, context)

    # Verify
    query.answer.assert_called_once()
    nav_handler.execute.assert_called_once_with(query, "back_main", context)
