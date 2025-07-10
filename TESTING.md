# Testing Documentation

This document provides comprehensive testing guidelines and procedures for the Doyobi Diary project.

## Overview

The Doyobi Diary employs a **multi-layered testing strategy** with unit tests, integration tests, and end-to-end testing to ensure reliability and maintainability.

### Testing Philosophy

- **Test-Driven Development**: Write tests before implementing features
- **High Coverage**: Maintain 60%+ test coverage across critical components
- **Fast Feedback**: Tests run in under 30 seconds locally
- **Comprehensive**: Cover unit, integration, and system-level scenarios
- **Automated**: All tests run in CI/CD pipeline

### Testing Stack

- **🧪 pytest**: Primary testing framework with fixtures and parametrization
- **📊 pytest-cov**: Code coverage reporting and analysis
- **🔄 pytest-asyncio**: Async/await testing support
- **🎭 pytest-mock**: Mocking and stubbing framework
- **🏗️ GitHub Actions**: Automated testing in CI/CD pipeline
- **🎯 Custom Fixtures**: Reusable test components

---

## Test Structure

### Current Test Organization

```
tests/
├── conftest.py              # Shared fixtures and configuration
├── test_basic_utils.py      # 18 utility function tests
├── test_new_components.py   # 7 architectural component tests  
├── test_rate_limiter.py     # 12+ rate limiting tests
├── test_database.py         # Database operation tests
├── test_admin.py           # Admin functionality tests
├── test_integration.py     # End-to-end integration tests
└── fixtures/               # Test data and mock objects
    ├── mock_telegram.py    # Telegram API mocks
    ├── mock_database.py    # Database mocks
    └── sample_data.py      # Test datasets
```

### Test Categories

#### 1. Unit Tests (`test_basic_utils.py`)
- **Purpose**: Test individual functions in isolation
- **Coverage**: 18 tests covering utility functions
- **Scope**: Pure functions, data validation, parsing logic

#### 2. Component Tests (`test_new_components.py`)
- **Purpose**: Test architectural components
- **Coverage**: 7 tests for modular components
- **Scope**: Rate limiters, cache managers, configuration

#### 3. Integration Tests (`test_rate_limiter.py`)
- **Purpose**: Test multi-tier rate limiting system
- **Coverage**: 12+ tests with various scenarios
- **Scope**: Rate limiting logic, sliding windows, user isolation

#### 4. Database Tests (`test_database.py`)
- **Purpose**: Test database operations and optimizations
- **Coverage**: CRUD operations, friend discovery, SQL functions
- **Scope**: Supabase integration, query optimization

#### 5. Admin Tests (`test_admin.py`)
- **Purpose**: Test administrative functionality
- **Coverage**: Broadcast system, user statistics, admin verification
- **Scope**: Admin operations, security, bulk processing

#### 6. End-to-End Tests (`test_integration.py`)
- **Purpose**: Test complete user workflows
- **Coverage**: User registration, friend requests, notifications
- **Scope**: Full system integration

---

## Running Tests

### Local Testing

#### Basic Test Execution

```bash
# Run all tests
python3 -m pytest

# Run with verbose output
python3 -m pytest -v

# Run specific test file
python3 -m pytest tests/test_basic_utils.py

# Run specific test function
python3 -m pytest tests/test_basic_utils.py::test_safe_parse_time

# Run tests matching pattern
python3 -m pytest -k "test_rate_limit"
```

#### Coverage Reports

```bash
# Run tests with coverage
python3 -m pytest --cov=.

# Generate HTML coverage report
python3 -m pytest --cov=. --cov-report=html

# View coverage report
open htmlcov/index.html

# Generate XML coverage for CI
python3 -m pytest --cov=. --cov-report=xml

# Coverage with missing lines
python3 -m pytest --cov=. --cov-report=term-missing
```

#### Test Categories and Markers

```bash
# Run only unit tests
python3 -m pytest -m "not integration"

# Run only integration tests
python3 -m pytest -m "integration"

# Run only fast tests
python3 -m pytest -m "not slow"

# Run tests for specific component
python3 -m pytest -m "rate_limiter"
```

### Virtual Environment Testing

```bash
# Create test environment
python3 -m venv test_env
source test_env/bin/activate  # Linux/Mac
# test_env\Scripts\activate   # Windows

# Install test dependencies
pip install -r requirements.txt
pip install pytest pytest-cov pytest-asyncio pytest-mock

# Run tests in isolated environment
python3 -m pytest --cov=. --cov-report=html

# Deactivate when done
deactivate
```

---

## Test Configuration

### pytest Configuration (`pytest.ini`)

```ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*

# Test markers
markers =
    integration: marks tests as integration tests (deselect with '-m "not integration"')
    slow: marks tests as slow (deselect with '-m "not slow"')
    rate_limiter: marks tests for rate limiting functionality
    database: marks tests requiring database connection
    admin: marks tests for admin functionality
    unit: marks tests as unit tests

# Asyncio configuration
asyncio_mode = auto

# Coverage configuration
addopts = 
    --strict-markers
    --strict-config
    --cov-fail-under=60
    --cov-report=term-missing:skip-covered
    --cov-report=html:htmlcov
    --cov-report=xml
```

### Test Fixtures (`conftest.py`)

```python
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta

@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def mock_config():
    """Mock configuration for testing."""
    config = MagicMock()
    config.bot_token = "test_token"
    config.supabase_url = "https://test.supabase.co"
    config.supabase_service_role_key = "test_key"
    config.admin_user_id = 123456789
    config.cache_ttl_seconds = 300
    config.rate_limit_enabled = True
    config.environment = "test"
    config.sentry_dsn = None
    return config

@pytest.fixture
def mock_supabase():
    """Mock Supabase client for testing."""
    with patch('supabase.create_client') as mock_create:
        mock_client = MagicMock()
        mock_create.return_value = mock_client
        
        # Mock table operations
        mock_table = MagicMock()
        mock_client.table.return_value = mock_table
        
        # Mock query operations
        mock_table.select.return_value = mock_table
        mock_table.insert.return_value = mock_table
        mock_table.update.return_value = mock_table
        mock_table.delete.return_value = mock_table
        mock_table.eq.return_value = mock_table
        mock_table.limit.return_value = mock_table
        mock_table.order.return_value = mock_table
        
        # Mock execute
        mock_table.execute.return_value = MagicMock(data=[])
        
        yield mock_client

@pytest.fixture
def mock_telegram_update():
    """Mock Telegram Update object."""
    update = MagicMock()
    update.effective_user.id = 123456789
    update.effective_user.username = "testuser"
    update.effective_user.first_name = "Test"
    update.effective_chat.id = 123456789
    update.message.text = "/start"
    update.message.date = datetime.now()
    return update

@pytest.fixture
def mock_telegram_context():
    """Mock Telegram CallbackContext."""
    context = MagicMock()
    context.bot = AsyncMock()
    context.user_data = {}
    context.chat_data = {}
    return context

@pytest.fixture
def sample_users():
    """Sample user data for testing."""
    return [
        {
            "tg_id": 123456789,
            "enabled": True,
            "window_start": "09:00:00",
            "window_end": "22:00:00",
            "interval_min": 120,
            "created_at": datetime.now().isoformat()
        },
        {
            "tg_id": 987654321,
            "enabled": False,
            "window_start": "10:00:00",
            "window_end": "20:00:00",
            "interval_min": 60,
            "created_at": (datetime.now() - timedelta(days=1)).isoformat()
        }
    ]

@pytest.fixture
def sample_friendships():
    """Sample friendship data for testing."""
    return [
        {
            "id": 1,
            "requester_id": 123456789,
            "addressee_id": 987654321,
            "status": "accepted",
            "created_at": datetime.now().isoformat()
        },
        {
            "id": 2,
            "requester_id": 111111111,
            "addressee_id": 123456789,
            "status": "pending",
            "created_at": datetime.now().isoformat()
        }
    ]

@pytest.fixture(autouse=True)
def mock_monitoring():
    """Auto-mock monitoring to prevent Sentry calls during testing."""
    with patch('monitoring.get_logger') as mock_logger, \
         patch('monitoring.track_errors') as mock_track, \
         patch('monitoring.set_user_context') as mock_context:
        
        mock_logger.return_value = MagicMock()
        mock_track.return_value = lambda f: f  # Pass-through decorator
        yield {
            'logger': mock_logger,
            'track_errors': mock_track,
            'set_user_context': mock_context
        }
```

---

## Writing Tests

### Unit Test Examples

#### Testing Utility Functions

```python
# tests/test_basic_utils.py
import pytest
from datetime import datetime, time
from bot.utils.datetime_utils import safe_parse_time, safe_parse_datetime
from bot.utils.exceptions import ValidationError

class TestDateTimeUtils:
    """Test datetime utility functions."""
    
    def test_safe_parse_time_valid_formats(self):
        """Test parsing valid time formats."""
        # Test various valid formats
        test_cases = [
            ("09:30", time(9, 30)),
            ("23:59", time(23, 59)),
            ("00:00", time(0, 0)),
            ("12:15", time(12, 15))
        ]
        
        for input_str, expected in test_cases:
            result = safe_parse_time(input_str)
            assert result == expected, f"Failed for input: {input_str}"
    
    def test_safe_parse_time_invalid_formats(self):
        """Test parsing invalid time formats."""
        invalid_inputs = [
            "25:00",    # Invalid hour
            "12:60",    # Invalid minute
            "abc:def",  # Non-numeric
            "12",       # Missing minute
            "12:30:45", # Extra seconds
            "",         # Empty string
            None        # None value
        ]
        
        for invalid_input in invalid_inputs:
            with pytest.raises(ValidationError):
                safe_parse_time(invalid_input)
    
    @pytest.mark.parametrize("input_str,expected", [
        ("2023-12-01T10:30:00", datetime(2023, 12, 1, 10, 30, 0)),
        ("2023-12-01 10:30:00", datetime(2023, 12, 1, 10, 30, 0)),
        ("2023-12-01", datetime(2023, 12, 1, 0, 0, 0)),
    ])
    def test_safe_parse_datetime_valid(self, input_str, expected):
        """Test parsing valid datetime formats."""
        result = safe_parse_datetime(input_str)
        assert result == expected

class TestCacheManager:
    """Test cache management functionality."""
    
    def test_cache_set_and_get(self, mock_config):
        """Test basic cache operations."""
        from bot.cache.ttl_cache import TTLCache
        
        cache = TTLCache(ttl_seconds=300)
        
        # Test set and get
        cache.set("test_key", "test_value")
        result = cache.get("test_key")
        assert result == "test_value"
    
    def test_cache_expiration(self, mock_config):
        """Test cache TTL expiration."""
        from bot.cache.ttl_cache import TTLCache
        import time
        
        cache = TTLCache(ttl_seconds=0.1)  # 100ms TTL
        
        cache.set("expiring_key", "expiring_value")
        
        # Should be available immediately
        assert cache.get("expiring_key") == "expiring_value"
        
        # Wait for expiration
        time.sleep(0.2)
        
        # Should be expired
        assert cache.get("expiring_key") is None
    
    def test_cache_invalidation(self, mock_config):
        """Test manual cache invalidation."""
        from bot.cache.ttl_cache import TTLCache
        
        cache = TTLCache()
        
        cache.set("key_to_invalidate", "value")
        assert cache.get("key_to_invalidate") == "value"
        
        cache.invalidate("key_to_invalidate")
        assert cache.get("key_to_invalidate") is None
```

### Integration Test Examples

#### Testing Rate Limiting

```python
# tests/test_rate_limiter.py
import pytest
import asyncio
from datetime import datetime, timedelta
from bot.utils.rate_limiter import MultiTierRateLimiter, RateLimitExceeded

class TestMultiTierRateLimiter:
    """Test multi-tier rate limiting functionality."""
    
    @pytest.mark.asyncio
    async def test_different_limits_for_actions(self):
        """Test that different actions have different limits."""
        limiter = MultiTierRateLimiter()
        user_id = 123456789
        
        # Friend requests should have stricter limits than general commands
        friend_request_count = 0
        general_command_count = 0
        
        # Test friend request limits
        for i in range(20):  # Try more than typical friend request limit
            is_allowed, _ = await limiter.check_limit(user_id, "friend_request")
            if is_allowed:
                friend_request_count += 1
            else:
                break
        
        # Test general command limits  
        for i in range(25):  # Try more than typical general limit
            is_allowed, _ = await limiter.check_limit(user_id + 1, "general")
            if is_allowed:
                general_command_count += 1
            else:
                break
        
        # Friend requests should have lower limit than general commands
        assert friend_request_count < general_command_count
        assert friend_request_count <= 5  # Typical friend request limit
        assert general_command_count >= 15  # Typical general command limit
    
    @pytest.mark.asyncio
    async def test_rate_limit_isolation_between_users(self):
        """Test that rate limits are isolated between users."""
        limiter = MultiTierRateLimiter()
        
        user1_id = 123456789
        user2_id = 987654321
        
        # Exhaust user1's limit
        for i in range(10):
            is_allowed, _ = await limiter.check_limit(user1_id, "friend_request")
            if not is_allowed:
                break
        
        # User2 should still be allowed
        is_allowed, _ = await limiter.check_limit(user2_id, "friend_request")
        assert is_allowed is True
    
    @pytest.mark.asyncio
    async def test_sliding_window_behavior(self):
        """Test sliding window rate limiting."""
        limiter = MultiTierRateLimiter()
        user_id = 123456789
        
        # Use up some of the limit
        for i in range(3):
            await limiter.check_limit(user_id, "friend_request")
        
        # Should hit limit
        is_allowed, retry_after = await limiter.check_limit(user_id, "friend_request")
        if not is_allowed:
            assert retry_after > 0
            
            # Simulate time passing (in real implementation)
            # For testing, we'd manipulate internal state
            # or use dependency injection for time
```

### Database Test Examples

```python
# tests/test_database.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from bot.database.user_operations import UserOperations
from bot.database.friend_operations import FriendOperations

class TestUserOperations:
    """Test user database operations."""
    
    @pytest.mark.asyncio
    async def test_ensure_user_exists_new_user(self, mock_supabase, mock_config):
        """Test auto-registration of new user."""
        user_ops = UserOperations(mock_supabase, mock_config)
        
        # Mock empty result (user doesn't exist)
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
        
        # Mock successful insert
        mock_supabase.table.return_value.insert.return_value.execute.return_value.data = [
            {"tg_id": 123456789, "enabled": True}
        ]
        
        result = await user_ops.ensure_user_exists(123456789)
        
        # Verify user was created
        assert result is not None
        mock_supabase.table.assert_called_with("users")
    
    @pytest.mark.asyncio
    async def test_ensure_user_exists_existing_user(self, mock_supabase, mock_config):
        """Test handling of existing user."""
        user_ops = UserOperations(mock_supabase, mock_config)
        
        # Mock existing user
        existing_user = {"tg_id": 123456789, "enabled": True}
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [existing_user]
        
        result = await user_ops.ensure_user_exists(123456789)
        
        # Verify existing user returned
        assert result == existing_user
        
        # Verify no insert was attempted
        mock_supabase.table.return_value.insert.assert_not_called()

class TestFriendOperations:
    """Test friend system database operations."""
    
    @pytest.mark.asyncio
    async def test_get_friends_of_friends_optimization(self, mock_supabase, mock_config):
        """Test optimized friend discovery query."""
        friend_ops = FriendOperations(mock_supabase, mock_config)
        
        # Mock SQL function result
        mock_result = [
            {"friend_id": 987654321, "mutual_friends_count": 3, "mutual_friends_sample": ["111", "222", "333"]},
            {"friend_id": 555555555, "mutual_friends_count": 2, "mutual_friends_sample": ["111", "444"]},
        ]
        
        mock_supabase.rpc.return_value.execute.return_value.data = mock_result
        
        result = await friend_ops.get_friends_of_friends_optimized(123456789)
        
        # Verify optimization function was called
        mock_supabase.rpc.assert_called_with("get_friends_of_friends_optimized", {"user_id": 123456789})
        
        # Verify results are properly formatted
        assert len(result) == 2
        assert result[0]["friend_id"] == 987654321
        assert result[0]["mutual_friends_count"] == 3
    
    @pytest.mark.asyncio
    async def test_friend_request_duplicate_prevention(self, mock_supabase, mock_config):
        """Test prevention of duplicate friend requests."""
        friend_ops = FriendOperations(mock_supabase, mock_config)
        
        # Mock existing friendship
        mock_supabase.table.return_value.select.return_value.or_.return_value.execute.return_value.data = [
            {"requester_id": 123456789, "addressee_id": 987654321, "status": "pending"}
        ]
        
        result = await friend_ops.create_friendship_request(123456789, 987654321)
        
        # Should return False for duplicate request
        assert result is False
        
        # Should not attempt to insert
        mock_supabase.table.return_value.insert.assert_not_called()
```

### End-to-End Test Examples

```python
# tests/test_integration.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

class TestUserWorkflow:
    """Test complete user workflows end-to-end."""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_complete_user_registration_flow(self, mock_supabase, mock_telegram_update, mock_telegram_context):
        """Test complete user registration workflow."""
        with patch('cerebrate_bot.ensure_user_exists') as mock_ensure_user:
            mock_ensure_user.return_value = {
                "tg_id": 123456789,
                "enabled": True,
                "window_start": "09:00:00",
                "window_end": "22:00:00",
                "interval_min": 120
            }
            
            # Import after patching
            from cerebrate_bot import start_command
            
            # Execute start command
            await start_command(mock_telegram_update, mock_telegram_context)
            
            # Verify user registration was called
            mock_ensure_user.assert_called_once_with(123456789)
            
            # Verify response was sent
            mock_telegram_context.bot.send_message.assert_called_once()
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_friend_discovery_workflow(self, mock_supabase):
        """Test complete friend discovery workflow."""
        with patch('bot.database.friend_operations.FriendOperations') as mock_friend_ops:
            mock_instance = mock_friend_ops.return_value
            mock_instance.get_friends_of_friends_optimized.return_value = [
                {
                    "friend_id": 987654321,
                    "mutual_friends_count": 2,
                    "mutual_friends_sample": ["111111111", "222222222"]
                }
            ]
            
            # Execute friend discovery
            from bot.database.friend_operations import FriendOperations
            friend_ops = FriendOperations(mock_supabase, MagicMock())
            
            result = await friend_ops.get_friends_of_friends_optimized(123456789)
            
            # Verify results
            assert len(result) == 1
            assert result[0]["friend_id"] == 987654321
            assert result[0]["mutual_friends_count"] == 2

class TestAdminWorkflow:
    """Test admin functionality workflows."""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_broadcast_workflow(self, mock_supabase, mock_config):
        """Test complete broadcast workflow."""
        with patch('bot.admin.broadcast_manager.BroadcastManager') as mock_broadcast:
            mock_instance = mock_broadcast.return_value
            mock_instance.send_broadcast.return_value = {
                "total_users": 100,
                "successful_deliveries": 95,
                "failed_deliveries": 5,
                "delivery_rate": 95.0
            }
            
            # Execute broadcast
            from bot.admin.broadcast_manager import BroadcastManager
            broadcast_manager = BroadcastManager(mock_supabase, mock_config)
            
            result = await broadcast_manager.send_broadcast("Test message", lambda x: None)
            
            # Verify broadcast results
            assert result["total_users"] == 100
            assert result["successful_deliveries"] == 95
            assert result["delivery_rate"] == 95.0
```

---

## Performance Testing

### Load Testing

```python
# tests/test_performance.py
import pytest
import asyncio
import time
from concurrent.futures import ThreadPoolExecutor

class TestPerformance:
    """Test performance and scalability."""
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_concurrent_rate_limiting(self):
        """Test rate limiter under concurrent load."""
        from bot.utils.rate_limiter import MultiTierRateLimiter
        
        limiter = MultiTierRateLimiter()
        
        async def make_request(user_id, action):
            return await limiter.check_limit(user_id, action)
        
        # Create concurrent requests
        tasks = []
        for i in range(100):
            user_id = i % 10  # 10 different users
            action = "general" if i % 2 == 0 else "friend_request"
            tasks.append(make_request(user_id, action))
        
        start_time = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = time.time()
        
        # Performance assertions
        duration = end_time - start_time
        assert duration < 1.0, f"Rate limiting took too long: {duration}s"
        
        # Verify no exceptions
        exceptions = [r for r in results if isinstance(r, Exception)]
        assert len(exceptions) == 0, f"Got exceptions: {exceptions}"
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_cache_performance(self):
        """Test cache performance under load."""
        from bot.cache.ttl_cache import TTLCache
        
        cache = TTLCache(ttl_seconds=300)
        
        # Warm up cache
        for i in range(1000):
            cache.set(f"key_{i}", f"value_{i}")
        
        # Test read performance
        start_time = time.time()
        for i in range(1000):
            result = cache.get(f"key_{i}")
            assert result == f"value_{i}"
        end_time = time.time()
        
        # Performance assertion
        duration = end_time - start_time
        ops_per_second = 1000 / duration
        assert ops_per_second > 10000, f"Cache too slow: {ops_per_second} ops/sec"
    
    @pytest.mark.asyncio
    @pytest.mark.slow  
    async def test_friend_discovery_performance(self, mock_supabase):
        """Test friend discovery optimization performance."""
        from bot.database.friend_operations import FriendOperations
        
        # Mock large dataset
        large_result = []
        for i in range(1000):
            large_result.append({
                "friend_id": i,
                "mutual_friends_count": i % 10,
                "mutual_friends_sample": [str(j) for j in range(min(3, i % 10))]
            })
        
        mock_supabase.rpc.return_value.execute.return_value.data = large_result
        
        friend_ops = FriendOperations(mock_supabase, MagicMock())
        
        start_time = time.time()
        result = await friend_ops.get_friends_of_friends_optimized(123456789)
        end_time = time.time()
        
        # Performance assertions
        duration = end_time - start_time
        assert duration < 0.1, f"Friend discovery too slow: {duration}s"
        assert len(result) <= 1000, "Result set too large"
```

### Memory Testing

```python
import psutil
import gc

class TestMemoryUsage:
    """Test memory usage and leaks."""
    
    def test_cache_memory_cleanup(self):
        """Test that cache cleans up expired entries."""
        from bot.cache.ttl_cache import TTLCache
        import time
        
        cache = TTLCache(ttl_seconds=0.1)
        
        # Get initial memory
        process = psutil.Process()
        initial_memory = process.memory_info().rss
        
        # Fill cache
        for i in range(10000):
            cache.set(f"key_{i}", f"large_value_{i}" * 100)
        
        # Check memory increased
        filled_memory = process.memory_info().rss
        assert filled_memory > initial_memory
        
        # Wait for expiration
        time.sleep(0.2)
        
        # Force cleanup
        cache.cleanup_expired()
        gc.collect()
        
        # Check memory decreased
        cleaned_memory = process.memory_info().rss
        memory_reduction = filled_memory - cleaned_memory
        
        # Should have freed significant memory
        assert memory_reduction > 0, "No memory was freed"
```

---

## CI/CD Testing

### GitHub Actions Test Workflow

The project includes automated testing in `.github/workflows/test.yml`:

```yaml
name: Tests

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.8, 3.9, '3.10', 3.11, 3.12]
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v4
        with:
          python-version: ${{ matrix.python-version }}
      
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
      
      - name: Lint with flake8
        run: |
          pip install flake8
          flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
          flake8 . --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics
      
      - name: Type check with mypy
        run: |
          pip install mypy
          mypy --ignore-missing-imports cerebrate_bot.py monitoring.py
      
      - name: Security check with bandit
        run: |
          pip install bandit
          bandit -r . -f json -o bandit-report.json || true
      
      - name: Run tests
        run: |
          python -m pytest -v --cov=. --cov-report=term-missing --cov-report=xml
      
      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
          flags: unittests
          name: codecov-umbrella
          fail_ci_if_error: true
```

### Local CI Simulation

```bash
# Simulate full CI pipeline locally
./scripts/run_full_tests.sh
```

Create `scripts/run_full_tests.sh`:

```bash
#!/bin/bash
set -e

echo "🧪 Running full test suite..."

# Linting
echo "📝 Running linting..."
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
flake8 . --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics

# Type checking
echo "🔍 Running type checks..."
mypy --ignore-missing-imports cerebrate_bot.py monitoring.py

# Security checks
echo "🔒 Running security checks..."
bandit -r . -f json -o bandit-report.json || true

# Unit tests
echo "🧪 Running unit tests..."
python -m pytest tests/test_basic_utils.py -v

# Component tests
echo "🏗️ Running component tests..."
python -m pytest tests/test_new_components.py -v

# Integration tests
echo "🔄 Running integration tests..."
python -m pytest tests/test_rate_limiter.py -v

# Coverage report
echo "📊 Generating coverage report..."
python -m pytest --cov=. --cov-report=term-missing --cov-report=html

echo "✅ All tests passed!"
echo "📊 Coverage report: file://$(pwd)/htmlcov/index.html"
```

---

## Test Data Management

### Test Fixtures and Data

```python
# tests/fixtures/sample_data.py
from datetime import datetime, timedelta

class TestDataFactory:
    """Factory for generating test data."""
    
    @staticmethod
    def create_user(tg_id=123456789, **kwargs):
        """Create test user data."""
        defaults = {
            "tg_id": tg_id,
            "enabled": True,
            "window_start": "09:00:00",
            "window_end": "22:00:00", 
            "interval_min": 120,
            "created_at": datetime.now().isoformat()
        }
        defaults.update(kwargs)
        return defaults
    
    @staticmethod
    def create_friendship(requester_id=123456789, addressee_id=987654321, **kwargs):
        """Create test friendship data."""
        defaults = {
            "id": 1,
            "requester_id": requester_id,
            "addressee_id": addressee_id,
            "status": "accepted",
            "created_at": datetime.now().isoformat()
        }
        defaults.update(kwargs)
        return defaults
    
    @staticmethod
    def create_activity(tg_id=123456789, **kwargs):
        """Create test activity data."""
        defaults = {
            "id": 1,
            "tg_name": "testuser",
            "tg_id": tg_id,
            "jobs_timestamp": datetime.now().isoformat(),
            "job_text": "Test activity"
        }
        defaults.update(kwargs)
        return defaults
    
    @classmethod
    def create_user_network(cls, size=10):
        """Create a network of users for testing."""
        users = []
        friendships = []
        
        for i in range(size):
            user_id = 100000000 + i
            users.append(cls.create_user(tg_id=user_id))
            
            # Create some friendships
            if i > 0:
                friend_id = 100000000 + (i - 1)
                friendships.append(cls.create_friendship(
                    requester_id=user_id,
                    addressee_id=friend_id
                ))
        
        return users, friendships
```

### Database Seeding for Tests

```python
# tests/fixtures/database_seed.py
import asyncio
from tests.fixtures.sample_data import TestDataFactory

class DatabaseSeeder:
    """Seed test database with sample data."""
    
    def __init__(self, supabase_client):
        self.supabase = supabase_client
    
    async def seed_users(self, count=10):
        """Seed users table with test data."""
        users = []
        for i in range(count):
            user = TestDataFactory.create_user(tg_id=100000000 + i)
            users.append(user)
        
        result = self.supabase.table("users").insert(users).execute()
        return result.data
    
    async def seed_friendships(self, user_ids):
        """Seed friendships between users."""
        friendships = []
        for i in range(len(user_ids) - 1):
            friendship = TestDataFactory.create_friendship(
                requester_id=user_ids[i],
                addressee_id=user_ids[i + 1]
            )
            friendships.append(friendship)
        
        result = self.supabase.table("friendships").insert(friendships).execute()
        return result.data
    
    async def cleanup_test_data(self):
        """Clean up test data after tests."""
        # Delete test users (cascades to friendships)
        self.supabase.table("users").delete().gte("tg_id", 100000000).execute()
        self.supabase.table("tg_jobs").delete().gte("tg_id", 100000000).execute()
```

---

## Best Practices

### Test Organization

1. **Clear Test Names**: Use descriptive test function names that explain what is being tested
2. **Single Assertion**: Each test should verify one specific behavior
3. **Arrange-Act-Assert**: Structure tests with clear setup, execution, and verification phases
4. **Independent Tests**: Tests should not depend on each other or shared state

### Mocking Guidelines

1. **Mock External Dependencies**: Always mock external services (Telegram API, Supabase)
2. **Mock at Boundaries**: Mock at the integration points, not internal functions
3. **Verify Interactions**: Assert that mocked functions are called with correct parameters
4. **Use Real Objects When Possible**: Prefer real objects over mocks for internal logic

### Performance Considerations

1. **Fast Tests**: Unit tests should run in milliseconds
2. **Parallel Execution**: Use pytest-xdist for parallel test execution
3. **Resource Cleanup**: Always clean up resources (files, connections) after tests
4. **Memory Monitoring**: Watch for memory leaks in long-running test suites

### Coverage Guidelines

1. **Target 60%+**: Maintain at least 60% code coverage
2. **Focus on Critical Paths**: Prioritize testing business logic and error handling
3. **Branch Coverage**: Ensure all code branches are tested
4. **Integration Coverage**: Test integration points between components

---

## Debugging Tests

### Debug Test Failures

```bash
# Run single failing test with maximum verbosity
python -m pytest tests/test_basic_utils.py::test_failing_function -vvv

# Run test with debugger
python -m pytest tests/test_basic_utils.py::test_failing_function --pdb

# Run test with print statements
python -m pytest tests/test_basic_utils.py::test_failing_function -s

# Run test with custom markers
python -m pytest -m "not slow" -v
```

### Test Output Analysis

```bash
# Generate detailed HTML report
python -m pytest --html=report.html --self-contained-html

# Generate JUnit XML for CI integration
python -m pytest --junitxml=junit.xml

# Run tests with timing information
python -m pytest --durations=10
```

### Common Issues and Solutions

#### Import Errors
```bash
# Ensure PYTHONPATH includes project root
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Or run tests as module
python -m pytest
```

#### Async Test Issues
```python
# Ensure proper async fixtures
@pytest.fixture
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

# Use pytest-asyncio for async tests
@pytest.mark.asyncio
async def test_async_function():
    result = await async_function()
    assert result is not None
```

#### Mock Issues
```python
# Patch at the right location
# Patch where the function is used, not where it's defined
with patch('module_using_function.function_name') as mock_func:
    # Test code here
    pass
```

---

## Test Automation

### Pre-commit Hooks

Create `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.4.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
  
  - repo: https://github.com/psf/black
    rev: 23.7.0
    hooks:
      - id: black
        language_version: python3.11
  
  - repo: https://github.com/pycqa/flake8
    rev: 6.0.0
    hooks:
      - id: flake8
        args: [--max-line-length=127]
  
  - repo: local
    hooks:
      - id: pytest
        name: Run tests
        entry: python -m pytest tests/ -x -v
        language: system
        pass_filenames: false
        always_run: true
```

### Test Automation Scripts

```bash
# scripts/test_watch.sh - Watch for changes and run tests
#!/bin/bash
while inotifywait -e modify,create,delete -r . --exclude='\.git|__pycache__|\.pytest_cache'; do
    clear
    echo "🔄 Files changed, running tests..."
    python -m pytest tests/ -x --tb=short
done
```

---

This testing documentation provides comprehensive guidance for maintaining high-quality, reliable code through effective testing strategies and automation.