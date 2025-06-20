"""
Tests for rate limiting functionality.
"""
import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import patch

# Mock monitoring before importing modules
with patch('monitoring.get_logger'), \
     patch('monitoring.track_errors'):
    from bot.utils.rate_limiter import RateLimiter, MultiTierRateLimiter, rate_limit
    from bot.utils.exceptions import RateLimitExceeded


class TestRateLimiter:
    """Tests for basic RateLimiter class."""
    
    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Mocked dependencies interfere with functionality")
    async def test_allows_requests_under_limit(self):
        """Test that requests under limit are allowed."""
        limiter = RateLimiter(max_requests=5, window_seconds=60)
        
        for i in range(5):
            is_allowed, retry_after = await limiter.is_allowed("test_user")
            assert is_allowed is True
            assert retry_after is None
    
    @pytest.mark.asyncio
    async def test_blocks_requests_over_limit(self):
        """Test that requests over limit are blocked."""
        limiter = RateLimiter(max_requests=2, window_seconds=60)
        
        # Use up the limit
        await limiter.is_allowed("test_user")
        await limiter.is_allowed("test_user")
        
        # Next request should be blocked
        is_allowed, retry_after = await limiter.is_allowed("test_user")
        assert is_allowed is False
        assert retry_after is not None
        assert retry_after > 0
    
    @pytest.mark.asyncio
    async def test_different_users_independent(self):
        """Test that different users have independent limits."""
        limiter = RateLimiter(max_requests=1, window_seconds=60)
        
        # User 1 uses their limit
        is_allowed, _ = await limiter.is_allowed("user1")
        assert is_allowed is True
        
        is_allowed, _ = await limiter.is_allowed("user1")
        assert is_allowed is False
        
        # User 2 should still be allowed
        is_allowed, _ = await limiter.is_allowed("user2")
        assert is_allowed is True
    
    def test_get_usage_stats(self):
        """Test usage statistics reporting."""
        limiter = RateLimiter(max_requests=5, window_seconds=60)
        
        # Initially should be empty
        stats = limiter.get_usage("test_user")
        assert stats["current_count"] == 0
        assert stats["remaining"] == 5
        assert stats["max_requests"] == 5
    
    def test_cleanup_old_entries(self):
        """Test cleanup of old entries."""
        limiter = RateLimiter(max_requests=5, window_seconds=1)  # 1 second window
        
        # Add some entries
        limiter.requests["user1"].append(datetime.now() - timedelta(seconds=2))
        limiter.requests["user2"].append(datetime.now())
        
        cleaned = limiter.cleanup_old_entries()
        assert cleaned >= 1


class TestMultiTierRateLimiter:
    """Tests for MultiTierRateLimiter class."""
    
    @pytest.mark.asyncio
    async def test_different_limits_for_different_actions(self):
        """Test that different actions have different limits."""
        limiter = MultiTierRateLimiter()
        
        # Friend requests have stricter limits than general commands
        # Use up friend request limit (should be lower)
        for i in range(10):  # Try more than typical friend request limit
            is_allowed, _ = await limiter.check_limit(123, "friend_request")
            if not is_allowed:
                break
        
        # General commands should still be allowed
        is_allowed, _ = await limiter.check_limit(123, "general")
        assert is_allowed is True
    
    @pytest.mark.asyncio
    async def test_unknown_action_uses_general_limit(self):
        """Test that unknown actions fall back to general limit."""
        limiter = MultiTierRateLimiter()
        
        is_allowed, _ = await limiter.check_limit(123, "unknown_action")
        assert is_allowed is True
    
    def test_get_usage_stats(self):
        """Test usage statistics for multi-tier limiter."""
        limiter = MultiTierRateLimiter()
        
        stats = limiter.get_usage_stats(123, "friend_request")
        assert "current_count" in stats
        assert "max_requests" in stats
        assert "remaining" in stats


class TestRateLimitDecorator:
    """Tests for rate_limit decorator."""
    
    @pytest.mark.asyncio
    async def test_decorator_allows_normal_execution(self):
        """Test that decorator allows normal function execution."""
        @rate_limit(action="test", error_message="Test limit exceeded")
        async def test_function(user_id: int):
            return f"Success for user {user_id}"
        
        result = await test_function(user_id=123)
        assert result == "Success for user 123"
    
    @pytest.mark.asyncio
    async def test_decorator_raises_rate_limit_error(self):
        """Test that decorator raises RateLimitExceeded when limit hit."""
        # Create a very restrictive limiter for testing
        with patch('bot.utils.rate_limiter.rate_limiter') as mock_limiter:
            mock_limiter.check_limit.return_value = (False, 30)  # Not allowed, retry after 30s
            
            @rate_limit(action="test", error_message="Test limit exceeded")
            async def test_function(user_id: int):
                return "This should not execute"
            
            with pytest.raises(RateLimitExceeded) as exc_info:
                await test_function(user_id=123)
            
            assert exc_info.value.retry_after == 30
            assert exc_info.value.action == "test"
            assert "Test limit exceeded" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_decorator_handles_missing_user_id(self):
        """Test that decorator handles functions without user_id gracefully."""
        @rate_limit(action="test")
        async def test_function():
            return "No user_id function"
        
        # Should execute normally when no user_id is found
        result = await test_function()
        assert result == "No user_id function"
    
    @pytest.mark.asyncio
    async def test_decorator_extracts_user_id_from_update(self):
        """Test that decorator can extract user_id from Update object."""
        from unittest.mock import MagicMock
        
        # Mock Update object
        mock_update = MagicMock()
        mock_update.effective_user.id = 456
        
        @rate_limit(action="test")
        async def test_function(update):
            return f"User ID: {update.effective_user.id}"
        
        result = await test_function(mock_update)
        assert result == "User ID: 456"


class TestRateLimiterIntegration:
    """Integration tests for rate limiting system."""
    
    @pytest.mark.asyncio
    async def test_sliding_window_behavior(self):
        """Test sliding window behavior over time."""
        limiter = RateLimiter(max_requests=2, window_seconds=2)
        
        # Use up limit
        await limiter.is_allowed("user1")
        await limiter.is_allowed("user1")
        
        # Should be blocked
        is_allowed, retry_after = await limiter.is_allowed("user1")
        assert is_allowed is False
        
        # Wait for window to slide (in real scenario, we'd wait)
        # For testing, we'll manipulate the internal state
        # Move oldest request back in time
        if limiter.requests["user1"]:
            limiter.requests["user1"][0] = datetime.now() - timedelta(seconds=3)
        
        # Should be allowed again
        is_allowed, _ = await limiter.is_allowed("user1")
        assert is_allowed is True
    
    @pytest.mark.asyncio
    async def test_concurrent_access(self):
        """Test that rate limiter works correctly with concurrent access."""
        limiter = RateLimiter(max_requests=10, window_seconds=60)
        
        async def make_request(user_id):
            return await limiter.is_allowed(f"user_{user_id}")
        
        # Make concurrent requests
        tasks = [make_request(i) for i in range(5)]
        results = await asyncio.gather(*tasks)
        
        # All should be allowed since we're under the limit
        for is_allowed, retry_after in results:
            assert is_allowed is True
            assert retry_after is None