"""
Fixed rate limiter tests without mock conflicts.
"""
import pytest
import asyncio
from bot.utils.rate_limiter import RateLimiter, MultiTierRateLimiter


class TestRateLimiterFixed:
    """Tests for RateLimiter without mocking issues."""
    
    @pytest.mark.asyncio
    async def test_rate_limiter_basic_functionality(self):
        """Test basic rate limiter functionality."""
        limiter = RateLimiter(max_requests=3, window_seconds=60)
        
        # Should allow requests under limit
        for i in range(3):
            is_allowed, retry_after = await limiter.is_allowed("test_user")
            assert is_allowed is True
            assert retry_after is None
        
        # Should block when over limit
        is_allowed, retry_after = await limiter.is_allowed("test_user")
        assert is_allowed is False
        assert retry_after > 0
    
    @pytest.mark.asyncio
    async def test_different_users_independent(self):
        """Test that different users have independent rate limits."""
        limiter = RateLimiter(max_requests=2, window_seconds=60)
        
        # User 1 uses their limit
        await limiter.is_allowed("user1")
        await limiter.is_allowed("user1")
        
        # User 1 should be blocked
        is_allowed, _ = await limiter.is_allowed("user1")
        assert is_allowed is False
        
        # User 2 should still be allowed
        is_allowed, _ = await limiter.is_allowed("user2")
        assert is_allowed is True
    
    def test_multi_tier_rate_limiter_configuration(self):
        """Test MultiTierRateLimiter configuration."""
        limiter = MultiTierRateLimiter()
        
        # Check that limiters are configured
        assert "general" in limiter.limiters
        assert "friend_request" in limiter.limiters
        assert "admin" in limiter.limiters
        
        # Check that limits are reasonable
        assert limiter.limiters["general"].max_requests == 20
        assert limiter.limiters["friend_request"].max_requests == 5
        assert limiter.limiters["admin"].max_requests == 50
    
    @pytest.mark.asyncio
    async def test_multi_tier_different_limits(self):
        """Test that different actions have different limits."""
        limiter = MultiTierRateLimiter()
        
        # General should have higher limit than friend_request
        # Use up friend_request limit (5 per hour)
        user_id = 999999
        for i in range(5):
            is_allowed, _ = await limiter.check_limit(user_id, "friend_request")
            assert is_allowed is True
        
        # Next friend_request should be blocked
        is_allowed, _ = await limiter.check_limit(user_id, "friend_request")
        assert is_allowed is False
        
        # But general should still be allowed
        is_allowed, _ = await limiter.check_limit(user_id, "general")
        assert is_allowed is True
    
    def test_usage_stats(self):
        """Test usage statistics functionality."""
        limiter = RateLimiter(max_requests=10, window_seconds=60)
        
        stats = limiter.get_usage("test_user")
        assert "current_count" in stats
        assert "max_requests" in stats
        assert "window_seconds" in stats
        assert "remaining" in stats
        
        assert stats["max_requests"] == 10
        assert stats["window_seconds"] == 60
        assert stats["current_count"] == 0
        assert stats["remaining"] == 10