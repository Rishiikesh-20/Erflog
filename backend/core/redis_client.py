"""
Redis Client with lazy initialization and connection pooling.

Provides a singleton RedisManager for efficient Redis connections.
Falls back gracefully when Redis is unavailable.
"""

import os
import logging
from typing import Optional

try:
    import redis
    from redis.exceptions import RedisError
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None
    RedisError = Exception

logger = logging.getLogger("RedisClient")


class RedisManager:
    """
    Singleton Redis connection manager with lazy initialization.
    
    Features:
    - Lazy connection (only connects when first used)
    - Connection pooling (handled by redis-py)
    - Graceful fallback when Redis unavailable
    - Auto-reconnection on failure
    """
    
    def __init__(self):
        self._client: Optional["redis.Redis"] = None
        self._connected: bool = False
        self._connection_attempted: bool = False
    
    def get_client(self) -> Optional["redis.Redis"]:
        """
        Get or create Redis client.
        
        Returns:
            Redis client if connected, None if unavailable.
        """
        if not REDIS_AVAILABLE:
            if not self._connection_attempted:
                logger.warning("⚠️ redis package not installed, caching disabled")
                self._connection_attempted = True
            return None
        
        if self._client is not None and self._connected:
            return self._client
        
        redis_url = os.getenv("REDIS_URL")
        if not redis_url:
            if not self._connection_attempted:
                logger.warning("⚠️ REDIS_URL not set, caching disabled")
                self._connection_attempted = True
            return None
        
        try:
            self._client = redis.from_url(
                redis_url,
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30
            )
            # Test connection
            self._client.ping()
            self._connected = True
            self._connection_attempted = True
            logger.info("✅ Redis connected successfully")
            return self._client
            
        except RedisError as e:
            logger.error(f"❌ Redis connection failed: {e}")
            self._client = None
            self._connected = False
            self._connection_attempted = True
            return None
        except Exception as e:
            logger.error(f"❌ Unexpected Redis error: {e}")
            self._client = None
            self._connected = False
            self._connection_attempted = True
            return None
    
    @property
    def is_connected(self) -> bool:
        """Check if Redis is currently connected."""
        return self._connected and self._client is not None
    
    def reconnect(self) -> bool:
        """
        Force a reconnection attempt.
        
        Returns:
            True if reconnection successful, False otherwise.
        """
        self._client = None
        self._connected = False
        self._connection_attempted = False
        return self.get_client() is not None
    
    def health_check(self) -> dict:
        """
        Perform health check on Redis connection.
        
        Returns:
            Dict with status information.
        """
        client = self.get_client()
        if client is None:
            return {
                "status": "disconnected",
                "available": False,
                "message": "Redis client not available"
            }
        
        try:
            info = client.info("server")
            return {
                "status": "connected",
                "available": True,
                "redis_version": info.get("redis_version", "unknown"),
                "connected_clients": info.get("connected_clients", 0)
            }
        except Exception as e:
            return {
                "status": "error",
                "available": False,
                "message": str(e)
            }


# Global singleton instance
redis_manager = RedisManager()
