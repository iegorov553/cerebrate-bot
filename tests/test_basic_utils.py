"""
Basic utility tests that don't require imports from the main module.
"""
import pytest
from datetime import datetime, time, timedelta
import sys
import os
from unittest.mock import MagicMock, patch

# Mock the supabase client before importing main module
with patch('supabase.create_client'):
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    # Mock environment variables for safe import
    os.environ.update({
        "TELEGRAM_BOT_TOKEN": "test_token",
        "SUPABASE_URL": "https://test.supabase.co",
        "SUPABASE_SERVICE_ROLE_KEY": "test_key",
        "ADMIN_USER_ID": "123456789"
    })
    
    from cerebrate_bot import (
        safe_parse_datetime,
        validate_time_window,
        CacheManager,
        is_admin
    )

class TestSafeParseDatetime:
    """Tests for safe_parse_datetime function."""
    
    def test_valid_iso_datetime(self):
        """Test parsing valid ISO datetime string."""
        dt_string = "2023-12-01T10:30:00+00:00"
        result = safe_parse_datetime(dt_string)
        
        assert result is not None
        assert result.year == 2023
        assert result.month == 12
        assert result.day == 1
        assert result.hour == 10
        assert result.minute == 30
    
    def test_valid_iso_datetime_with_z(self):
        """Test parsing ISO datetime with Z suffix."""
        dt_string = "2023-12-01T10:30:00Z"
        result = safe_parse_datetime(dt_string)
        
        assert result is not None
        assert result.year == 2023
    
    def test_invalid_datetime_string(self):
        """Test parsing invalid datetime string."""
        dt_string = "invalid-datetime"
        result = safe_parse_datetime(dt_string)
        
        assert result is None
    
    def test_empty_string(self):
        """Test parsing empty string."""
        result = safe_parse_datetime("")
        assert result is None
    
    def test_none_input(self):
        """Test parsing None input."""
        result = safe_parse_datetime(None)
        assert result is None

class TestValidateTimeWindow:
    """Tests for validate_time_window function."""
    
    def test_valid_time_window(self):
        """Test valid time window format."""
        time_range = "09:00-17:00"
        is_valid, message, start_time, end_time = validate_time_window(time_range)
        
        assert is_valid is True
        assert message == "OK"
        assert start_time == time(9, 0)
        assert end_time == time(17, 0)
    
    def test_invalid_format(self):
        """Test invalid time window format."""
        time_range = "9:00-17:00"  # Missing leading zero
        is_valid, message, start_time, end_time = validate_time_window(time_range)
        
        assert is_valid is False
        assert "Неправильный формат" in message
        assert start_time is None
        assert end_time is None
    
    def test_invalid_hours(self):
        """Test time window with invalid hours."""
        time_range = "25:00-17:00"  # Hour > 23
        is_valid, message, start_time, end_time = validate_time_window(time_range)
        
        assert is_valid is False
        assert "Часы должны быть от 00 до 23" in message
    
    def test_end_before_start(self):
        """Test time window where end is before start."""
        time_range = "17:00-09:00"
        is_valid, message, start_time, end_time = validate_time_window(time_range)
        
        assert is_valid is False
        assert "позже времени начала" in message
    
    def test_too_short_window(self):
        """Test time window shorter than 1 hour."""
        time_range = "09:00-09:30"
        is_valid, message, start_time, end_time = validate_time_window(time_range)
        
        assert is_valid is False
        assert "Минимальная продолжительность - 1 час" in message

class TestCacheManager:
    """Tests for CacheManager class."""
    
    def test_set_and_get(self):
        """Test setting and getting values from cache."""
        cache = CacheManager()
        cache.set("test_key", "test_value", 300)
        
        result = cache.get("test_key")
        assert result == "test_value"
    
    def test_get_nonexistent_key(self):
        """Test getting non-existent key returns default."""
        cache = CacheManager()
        result = cache.get("nonexistent", "default")
        
        assert result == "default"
    
    def test_cache_expiration(self):
        """Test cache expiration functionality."""
        cache = CacheManager()
        
        # Set a value with a very short TTL
        cache.set("test_key", "test_value", 0)  # Expires immediately
        
        # Value should be expired when we try to get it
        result = cache.get("test_key")
        assert result is None
    
    def test_invalidate(self):
        """Test manual cache invalidation."""
        cache = CacheManager()
        cache.set("test_key", "test_value", 300)
        
        # Verify value is there
        assert cache.get("test_key") == "test_value"
        
        # Invalidate
        cache.invalidate("test_key")
        
        # Value should be gone
        assert cache.get("test_key") is None
    
    def test_clear(self):
        """Test clearing entire cache."""
        cache = CacheManager()
        cache.set("key1", "value1", 300)
        cache.set("key2", "value2", 300)
        
        # Verify values are there
        assert cache.get("key1") == "value1"
        assert cache.get("key2") == "value2"
        
        # Clear cache
        cache.clear()
        
        # All values should be gone
        assert cache.get("key1") is None
        assert cache.get("key2") is None

class TestAdminFunctions:
    """Tests for admin functions."""
    
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