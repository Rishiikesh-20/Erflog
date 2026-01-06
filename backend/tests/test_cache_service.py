"""
Unit tests for Redis Cache Service.

Tests cover:
- Cache operations for today_data, leetcode_progress, saved_jobs
- Cache hits and misses
- Graceful fallback when Redis unavailable
- TTL behavior
"""

import pytest
from unittest.mock import patch, MagicMock
import json


class TestCacheService:
    """Test suite for CacheService operations."""
    
    # =========================================================================
    # TODAY_DATA Tests
    # =========================================================================
    
    def test_get_today_data_cache_hit(self):
        """Test cache returns data when present."""
        with patch('services.cache_service.redis_manager') as mock_redis:
            mock_client = MagicMock()
            mock_client.get.return_value = json.dumps({
                "data": {"jobs": [], "hackathons": []},
                "updated_at": "2024-01-01T00:00:00Z"
            })
            mock_redis.get_client.return_value = mock_client
            
            from services.cache_service import CacheService
            result = CacheService.get_today_data("user123")
            
            assert result is not None
            assert "data" in result
            assert "updated_at" in result
            mock_client.get.assert_called_once_with("today_data:user123")
    
    def test_get_today_data_cache_miss(self):
        """Test cache returns None on miss."""
        with patch('services.cache_service.redis_manager') as mock_redis:
            mock_client = MagicMock()
            mock_client.get.return_value = None
            mock_redis.get_client.return_value = mock_client
            
            from services.cache_service import CacheService
            result = CacheService.get_today_data("user123")
            
            assert result is None
    
    def test_set_today_data_with_ttl(self):
        """Test setting today_data with 24h TTL."""
        with patch('services.cache_service.redis_manager') as mock_redis:
            mock_client = MagicMock()
            mock_redis.get_client.return_value = mock_client
            
            from services.cache_service import CacheService, TTL_TODAY_DATA
            data = {"data": {"jobs": []}, "updated_at": "2024-01-01"}
            
            result = CacheService.set_today_data("user123", data)
            
            assert result is True
            mock_client.setex.assert_called_once()
            args = mock_client.setex.call_args[0]
            assert args[0] == "today_data:user123"
            assert args[1] == TTL_TODAY_DATA
    
    # =========================================================================
    # LEETCODE_PROGRESS Tests
    # =========================================================================
    
    def test_get_leetcode_progress_cache_hit(self):
        """Test leetcode_progress cache hit."""
        with patch('services.cache_service.redis_manager') as mock_redis:
            mock_client = MagicMock()
            mock_client.get.return_value = json.dumps({
                "solved_problem_ids": [1, 2, 3],
                "quiz_answers": {"Arrays": "strong"},
                "total_solved": 3
            })
            mock_redis.get_client.return_value = mock_client
            
            from services.cache_service import CacheService
            result = CacheService.get_leetcode_progress("user123")
            
            assert result is not None
            assert result["solved_problem_ids"] == [1, 2, 3]
            assert result["total_solved"] == 3
    
    def test_set_leetcode_progress_no_ttl(self):
        """Test leetcode_progress is set WITHOUT TTL (critical data)."""
        with patch('services.cache_service.redis_manager') as mock_redis:
            mock_client = MagicMock()
            mock_redis.get_client.return_value = mock_client
            
            from services.cache_service import CacheService
            data = {"solved_problem_ids": [1, 2], "quiz_answers": {}, "total_solved": 2}
            
            result = CacheService.set_leetcode_progress("user123", data)
            
            assert result is True
            # Should use set() not setex() - no TTL
            mock_client.set.assert_called_once()
            mock_client.setex.assert_not_called()
    
    # =========================================================================
    # SAVED_JOBS Tests
    # =========================================================================
    
    def test_get_saved_jobs_cache_hit(self):
        """Test saved_jobs cache hit returns list."""
        with patch('services.cache_service.redis_manager') as mock_redis:
            mock_client = MagicMock()
            mock_client.get.return_value = json.dumps([
                {"id": "job1", "title": "SWE", "company": "Google"},
                {"id": "job2", "title": "PM", "company": "Meta"}
            ])
            mock_redis.get_client.return_value = mock_client
            
            from services.cache_service import CacheService
            result = CacheService.get_saved_jobs("user123")
            
            assert result is not None
            assert len(result) == 2
            assert result[0]["title"] == "SWE"
    
    def test_invalidate_saved_jobs(self):
        """Test cache invalidation deletes all related keys."""
        with patch('services.cache_service.redis_manager') as mock_redis:
            mock_client = MagicMock()
            mock_client.scan.return_value = (0, ["saved_job:user123:job1", "saved_job:user123:job2"])
            mock_redis.get_client.return_value = mock_client
            
            from services.cache_service import CacheService
            result = CacheService.invalidate_saved_jobs("user123")
            
            assert result is True
            mock_client.delete.assert_called_once()
            # Should delete list key + individual job keys
            args = mock_client.delete.call_args[0]
            assert "saved_jobs:user123" in args
    
    # =========================================================================
    # FALLBACK Tests
    # =========================================================================
    
    def test_redis_unavailable_graceful_fallback(self):
        """Test graceful fallback when Redis unavailable."""
        with patch('services.cache_service.redis_manager') as mock_redis:
            mock_redis.get_client.return_value = None
            
            from services.cache_service import CacheService
            
            # All get operations should return None
            assert CacheService.get_today_data("user123") is None
            assert CacheService.get_leetcode_progress("user123") is None
            assert CacheService.get_saved_jobs("user123") is None
            
            # All set operations should return False
            assert CacheService.set_today_data("user123", {}) is False
            assert CacheService.set_leetcode_progress("user123", {}) is False
    
    def test_redis_error_graceful_handling(self):
        """Test graceful error handling on Redis exceptions."""
        with patch('services.cache_service.redis_manager') as mock_redis:
            mock_client = MagicMock()
            mock_client.get.side_effect = Exception("Connection lost")
            mock_redis.get_client.return_value = mock_client
            
            from services.cache_service import CacheService
            
            # Should not raise, just return None
            result = CacheService.get_today_data("user123")
            assert result is None
    
    # =========================================================================
    # UTILITY Tests
    # =========================================================================
    
    def test_flush_user_cache(self):
        """Test flushing all cache for a user."""
        with patch('services.cache_service.redis_manager') as mock_redis:
            mock_client = MagicMock()
            mock_client.scan.return_value = (0, [])
            mock_redis.get_client.return_value = mock_client
            
            from services.cache_service import CacheService
            result = CacheService.flush_user_cache("user123")
            
            assert result is True
            mock_client.delete.assert_called_once()


class TestRedisManager:
    """Test suite for RedisManager connection handling."""
    
    def test_lazy_initialization(self):
        """Test Redis client is not created until first use."""
        with patch.dict('os.environ', {'REDIS_URL': ''}):
            from core.redis_client import RedisManager
            manager = RedisManager()
            
            # Client should be None until get_client() is called
            assert manager._client is None
            assert manager._connected is False
    
    def test_missing_redis_url(self):
        """Test graceful handling when REDIS_URL not set."""
        with patch.dict('os.environ', {'REDIS_URL': ''}):
            from core.redis_client import RedisManager
            manager = RedisManager()
            
            client = manager.get_client()
            
            assert client is None
            assert manager.is_connected is False
    
    def test_health_check_disconnected(self):
        """Test health check when not connected."""
        with patch.dict('os.environ', {'REDIS_URL': ''}):
            from core.redis_client import RedisManager
            manager = RedisManager()
            
            health = manager.health_check()
            
            assert health["status"] == "disconnected"
            assert health["available"] is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
