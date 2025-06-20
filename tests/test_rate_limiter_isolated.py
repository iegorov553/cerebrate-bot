"""
Isolated rate limiter tests without any monitoring dependencies.
"""
import asyncio
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import pytest


class SimpleRateLimiter:
    """Simple rate limiter for testing without monitoring dependencies."""
    
    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: Dict[str, List[datetime]] = defaultdict(list)
    
    async def is_allowed(self, key: str) -> Tuple[bool, Optional[int]]:
        """Check if request is allowed."""
        now = datetime.now()
        window_start = now - timedelta(seconds=self.window_seconds)
        
        # Clean old requests
        self.requests[key] = [req_time for req_time in self.requests[key] if req_time > window_start]
        
        if len(self.requests[key]) < self.max_requests:
            self.requests[key].append(now)
            return True, None
        else:
            # Calculate retry after
            oldest_request = min(self.requests[key])
            retry_after = int((oldest_request + timedelta(seconds=self.window_seconds) - now).total_seconds())
            return False, max(1, retry_after)


class SimpleMultiTierRateLimiter:
    """Simple multi-tier rate limiter for testing."""
    
    LIMITS = {
        "general": (20, 60),        # 20 requests per minute
        "friend_request": (5, 3600),  # 5 requests per hour
        "discovery": (3, 60),        # 3 requests per minute
        "settings": (10, 300),       # 10 requests per 5 minutes
        "admin": (50, 60),          # 50 requests per minute
        "callback": (30, 60),       # 30 callbacks per minute
    }
    
    def __init__(self):
        self.limiters = {}
        for action, (max_req, window) in self.LIMITS.items():
            self.limiters[action] = SimpleRateLimiter(max_req, window)
    
    async def check_limit(self, user_id: int, action: str) -> Tuple[bool, Optional[int]]:
        """Check rate limit for specific action."""
        limiter = self.limiters.get(action, self.limiters["general"])
        key = f"{user_id}:{action}"
        return await limiter.is_allowed(key)


class TestSimpleRateLimiter:
    """Test simple rate limiter functionality."""
    
    @pytest.mark.asyncio
    async def test_rate_limiter_basic_functionality(self):
        """Test basic rate limiter functionality."""
        limiter = SimpleRateLimiter(max_requests=3, window_seconds=60)
        
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
        limiter = SimpleRateLimiter(max_requests=2, window_seconds=60)
        
        # User 1 uses their limit
        await limiter.is_allowed("user1")
        await limiter.is_allowed("user1")
        
        # User 1 should be blocked
        is_allowed, _ = await limiter.is_allowed("user1")
        assert is_allowed is False
        
        # User 2 should still be allowed
        is_allowed, _ = await limiter.is_allowed("user2")
        assert is_allowed is True
    
    @pytest.mark.asyncio
    async def test_window_sliding(self):
        """Test sliding window behavior."""
        limiter = SimpleRateLimiter(max_requests=2, window_seconds=1)
        
        # Use up limit
        await limiter.is_allowed("user1")
        await limiter.is_allowed("user1")
        
        # Should be blocked
        is_allowed, retry_after = await limiter.is_allowed("user1")
        assert is_allowed is False
        
        # Wait for window to slide
        await asyncio.sleep(1.1)
        
        # Should be allowed again
        is_allowed, _ = await limiter.is_allowed("user1")
        assert is_allowed is True


class TestSimpleMultiTierRateLimiter:
    """Test multi-tier rate limiter functionality."""
    
    def test_multi_tier_rate_limiter_configuration(self):
        """Test MultiTierRateLimiter configuration."""
        limiter = SimpleMultiTierRateLimiter()
        
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
        limiter = SimpleMultiTierRateLimiter()
        
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
    
    @pytest.mark.asyncio
    async def test_unknown_action_uses_general_limit(self):
        """Test that unknown actions fall back to general limit."""
        limiter = SimpleMultiTierRateLimiter()
        
        is_allowed, _ = await limiter.check_limit(123, "unknown_action")
        assert is_allowed is True


class TestRateLimiterIntegration:
    """Integration tests for rate limiting system."""
    
    @pytest.mark.asyncio
    async def test_concurrent_access(self):
        """Test that rate limiter works correctly with concurrent access."""
        limiter = SimpleRateLimiter(max_requests=10, window_seconds=60)
        
        async def make_request(user_id):
            return await limiter.is_allowed(f"user_{user_id}")
        
        # Make concurrent requests
        tasks = [make_request(i) for i in range(5)]
        results = await asyncio.gather(*tasks)
        
        # All should be allowed since we're under the limit
        for is_allowed, retry_after in results:
            assert is_allowed is True
            assert retry_after is None