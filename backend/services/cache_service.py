"""
Redis Cache Service for all user-scoped data.

Provides a unified caching layer with:
- Cache-first reads with DB fallback
- Write-through consistency 
- Graceful degradation when Redis unavailable
- TTL strategies per entity type

Key Schema:
- today_data:{user_id} -> JSON string (24h TTL)
- leetcode_progress:{user_id} -> JSON string (no expiry)
- saved_jobs:{user_id} -> JSON string (no expiry)
- saved_job:{user_id}:{job_id} -> JSON string (no expiry)
- github_activity_cache:{user_id} -> JSON string (1h TTL)
- profile:{user_id} -> JSON string (5min TTL)
"""

import json
import logging
from typing import Optional, Any, List, Dict
from datetime import timedelta

from core.redis_client import redis_manager

logger = logging.getLogger("CacheService")

# TTL Constants
TTL_TODAY_DATA = int(timedelta(hours=24).total_seconds())  # 24 hours
TTL_GITHUB_ACTIVITY = int(timedelta(hours=1).total_seconds())  # 1 hour (synced frequently)
TTL_PROFILE = int(timedelta(minutes=5).total_seconds())  # 5 minutes (can change often)
TTL_GLOBAL_ROADMAPS = int(timedelta(hours=1).total_seconds())  # 1 hour (shared data)
TTL_LEETCODE = None  # No expiry - user progress is critical
TTL_SAVED_JOBS = None  # No expiry - user data


class CacheService:
    """
    Unified cache service for all cacheable entities.
    
    All methods are class methods for easy access without instantiation.
    All operations fail gracefully - returning None on cache miss/error.
    """
    
    # =========================================================================
    # TODAY_DATA Operations
    # =========================================================================
    
    @staticmethod
    def _today_key(user_id: str) -> str:
        """Generate Redis key for today_data."""
        return f"today_data:{user_id}"
    
    @classmethod
    def get_today_data(cls, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get today_data from cache.
        
        Args:
            user_id: User's UUID
            
        Returns:
            Dict with data and updated_at, or None on miss/error
        """
        client = redis_manager.get_client()
        if not client:
            return None
        
        try:
            data = client.get(cls._today_key(user_id))
            if data:
                logger.info(f"🎯 Cache HIT for today_data:{user_id}")
                return json.loads(data)
            logger.info(f"📭 Cache MISS for today_data:{user_id}")
        except Exception as e:
            logger.warning(f"Cache read failed for today_data:{user_id}: {e}")
        return None
    
    @classmethod
    def set_today_data(cls, user_id: str, data: Dict[str, Any]) -> bool:
        """
        Set today_data in cache with 24h TTL.
        
        Args:
            user_id: User's UUID
            data: Dict containing 'data' and 'updated_at' keys
            
        Returns:
            True if successful, False otherwise
        """
        client = redis_manager.get_client()
        if not client:
            return False
        
        try:
            client.setex(
                cls._today_key(user_id),
                TTL_TODAY_DATA,
                json.dumps(data, default=str)
            )
            logger.info(f"💾 Cache SET for today_data:{user_id}")
            return True
        except Exception as e:
            logger.warning(f"Cache write failed for today_data:{user_id}: {e}")
            return False
    
    @classmethod
    def delete_today_data(cls, user_id: str) -> bool:
        """
        Invalidate today_data cache.
        
        Args:
            user_id: User's UUID
            
        Returns:
            True if successful, False otherwise
        """
        client = redis_manager.get_client()
        if not client:
            return False
        
        try:
            client.delete(cls._today_key(user_id))
            logger.info(f"🗑️ Cache DELETE for today_data:{user_id}")
            return True
        except Exception as e:
            logger.warning(f"Cache delete failed for today_data:{user_id}: {e}")
            return False
    
    # =========================================================================
    # LEETCODE_PROGRESS Operations
    # =========================================================================
    
    @staticmethod
    def _leetcode_key(user_id: str) -> str:
        """Generate Redis key for leetcode_progress."""
        return f"leetcode_progress:{user_id}"
    
    @classmethod
    def get_leetcode_progress(cls, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get leetcode_progress from cache.
        
        Args:
            user_id: User's UUID
            
        Returns:
            Dict with solved_problem_ids, quiz_answers, total_solved, or None
        """
        client = redis_manager.get_client()
        if not client:
            return None
        
        try:
            data = client.get(cls._leetcode_key(user_id))
            if data:
                logger.info(f"🎯 Cache HIT for leetcode_progress:{user_id}")
                return json.loads(data)
            logger.info(f"📭 Cache MISS for leetcode_progress:{user_id}")
        except Exception as e:
            logger.warning(f"Cache read failed for leetcode_progress:{user_id}: {e}")
        return None
    
    @classmethod
    def set_leetcode_progress(cls, user_id: str, data: Dict[str, Any]) -> bool:
        """
        Set leetcode_progress in cache (no TTL - critical user data).
        
        Args:
            user_id: User's UUID
            data: Dict with solved_problem_ids, quiz_answers, total_solved
            
        Returns:
            True if successful, False otherwise
        """
        client = redis_manager.get_client()
        if not client:
            return False
        
        try:
            client.set(cls._leetcode_key(user_id), json.dumps(data, default=str))
            logger.info(f"💾 Cache SET for leetcode_progress:{user_id}")
            return True
        except Exception as e:
            logger.warning(f"Cache write failed for leetcode_progress:{user_id}: {e}")
            return False
    
    @classmethod
    def delete_leetcode_progress(cls, user_id: str) -> bool:
        """
        Invalidate leetcode_progress cache.
        
        Args:
            user_id: User's UUID
            
        Returns:
            True if successful, False otherwise
        """
        client = redis_manager.get_client()
        if not client:
            return False
        
        try:
            client.delete(cls._leetcode_key(user_id))
            logger.info(f"🗑️ Cache DELETE for leetcode_progress:{user_id}")
            return True
        except Exception as e:
            logger.warning(f"Cache delete failed for leetcode_progress:{user_id}: {e}")
            return False
    
    # =========================================================================
    # SAVED_JOBS Operations
    # =========================================================================
    
    @staticmethod
    def _saved_jobs_list_key(user_id: str) -> str:
        """Generate Redis key for user's saved jobs list."""
        return f"saved_jobs:{user_id}"
    
    @staticmethod
    def _saved_job_key(user_id: str, job_id: str) -> str:
        """Generate Redis key for individual saved job."""
        return f"saved_job:{user_id}:{job_id}"
    
    @classmethod
    def get_saved_jobs(cls, user_id: str) -> Optional[List[Dict[str, Any]]]:
        """
        Get all saved_jobs for user from cache.
        
        Args:
            user_id: User's UUID
            
        Returns:
            List of saved job dicts, or None on miss/error
        """
        client = redis_manager.get_client()
        if not client:
            return None
        
        try:
            data = client.get(cls._saved_jobs_list_key(user_id))
            if data:
                logger.info(f"🎯 Cache HIT for saved_jobs:{user_id}")
                return json.loads(data)
            logger.info(f"📭 Cache MISS for saved_jobs:{user_id}")
        except Exception as e:
            logger.warning(f"Cache read failed for saved_jobs:{user_id}: {e}")
        return None
    
    @classmethod
    def set_saved_jobs(cls, user_id: str, jobs: List[Dict[str, Any]]) -> bool:
        """
        Set saved_jobs list in cache (no TTL).
        
        Args:
            user_id: User's UUID
            jobs: List of saved job dicts
            
        Returns:
            True if successful, False otherwise
        """
        client = redis_manager.get_client()
        if not client:
            return False
        
        try:
            client.set(
                cls._saved_jobs_list_key(user_id),
                json.dumps(jobs, default=str)
            )
            logger.info(f"💾 Cache SET for saved_jobs:{user_id} ({len(jobs)} jobs)")
            return True
        except Exception as e:
            logger.warning(f"Cache write failed for saved_jobs:{user_id}: {e}")
            return False
    
    @classmethod
    def invalidate_saved_jobs(cls, user_id: str) -> bool:
        """
        Invalidate user's saved jobs cache (list + individual jobs).
        
        Args:
            user_id: User's UUID
            
        Returns:
            True if successful, False otherwise
        """
        client = redis_manager.get_client()
        if not client:
            return False
        
        try:
            keys_to_delete = [cls._saved_jobs_list_key(user_id)]
            
            # Find all individual job keys for this user using SCAN (non-blocking)
            pattern = f"saved_job:{user_id}:*"
            cursor = 0
            while True:
                cursor, keys = client.scan(cursor, match=pattern, count=100)
                keys_to_delete.extend(keys)
                if cursor == 0:
                    break
            
            if keys_to_delete:
                client.delete(*keys_to_delete)
                logger.info(f"🗑️ Cache INVALIDATE for saved_jobs:{user_id} ({len(keys_to_delete)} keys)")
            
            return True
        except Exception as e:
            logger.warning(f"Cache invalidate failed for saved_jobs:{user_id}: {e}")
            return False
    
    @classmethod
    def get_saved_job(cls, user_id: str, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get single saved job from cache.
        
        Args:
            user_id: User's UUID
            job_id: Job's UUID
            
        Returns:
            Job dict, or None on miss/error
        """
        client = redis_manager.get_client()
        if not client:
            return None
        
        try:
            data = client.get(cls._saved_job_key(user_id, job_id))
            if data:
                logger.info(f"🎯 Cache HIT for saved_job:{user_id}:{job_id}")
                return json.loads(data)
            logger.info(f"📭 Cache MISS for saved_job:{user_id}:{job_id}")
        except Exception as e:
            logger.warning(f"Cache read failed for saved_job:{user_id}:{job_id}: {e}")
        return None
    
    @classmethod
    def set_saved_job(cls, user_id: str, job_id: str, job: Dict[str, Any]) -> bool:
        """
        Set single saved job in cache (no TTL).
        
        Args:
            user_id: User's UUID
            job_id: Job's UUID
            job: Job data dict
            
        Returns:
            True if successful, False otherwise
        """
        client = redis_manager.get_client()
        if not client:
            return False
        
        try:
            client.set(
                cls._saved_job_key(user_id, job_id),
                json.dumps(job, default=str)
            )
            logger.info(f"💾 Cache SET for saved_job:{user_id}:{job_id}")
            return True
        except Exception as e:
            logger.warning(f"Cache write failed for saved_job:{user_id}:{job_id}: {e}")
            return False
    
    # =========================================================================
    # GITHUB_ACTIVITY_CACHE Operations
    # =========================================================================
    
    @staticmethod
    def _github_activity_key(user_id: str) -> str:
        """Generate Redis key for github_activity_cache."""
        return f"github_activity:{user_id}"
    
    @classmethod
    def get_github_activity(cls, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get github_activity_cache from Redis.
        
        Args:
            user_id: User's UUID
            
        Returns:
            Dict with detected_skills, repos_touched, tech_stack, insight_message, or None
        """
        client = redis_manager.get_client()
        if not client:
            return None
        
        try:
            data = client.get(cls._github_activity_key(user_id))
            if data:
                logger.info(f"🎯 Cache HIT for github_activity:{user_id}")
                return json.loads(data)
            logger.info(f"📭 Cache MISS for github_activity:{user_id}")
        except Exception as e:
            logger.warning(f"Cache read failed for github_activity:{user_id}: {e}")
        return None
    
    @classmethod
    def set_github_activity(cls, user_id: str, data: Dict[str, Any]) -> bool:
        """
        Set github_activity_cache in Redis with 1h TTL.
        
        Args:
            user_id: User's UUID
            data: Dict with github activity data
            
        Returns:
            True if successful, False otherwise
        """
        client = redis_manager.get_client()
        if not client:
            return False
        
        try:
            client.setex(
                cls._github_activity_key(user_id),
                TTL_GITHUB_ACTIVITY,
                json.dumps(data, default=str)
            )
            logger.info(f"💾 Cache SET for github_activity:{user_id}")
            return True
        except Exception as e:
            logger.warning(f"Cache write failed for github_activity:{user_id}: {e}")
            return False
    
    @classmethod
    def delete_github_activity(cls, user_id: str) -> bool:
        """Invalidate github_activity cache."""
        client = redis_manager.get_client()
        if not client:
            return False
        
        try:
            client.delete(cls._github_activity_key(user_id))
            logger.info(f"🗑️ Cache DELETE for github_activity:{user_id}")
            return True
        except Exception as e:
            logger.warning(f"Cache delete failed for github_activity:{user_id}: {e}")
            return False
    
    # =========================================================================
    # PROFILE Operations
    # =========================================================================
    
    @staticmethod
    def _profile_key(user_id: str) -> str:
        """Generate Redis key for profile."""
        return f"profile:{user_id}"
    
    @classmethod
    def get_profile(cls, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get profile from Redis.
        
        Args:
            user_id: User's UUID
            
        Returns:
            Profile dict, or None on miss/error
        """
        client = redis_manager.get_client()
        if not client:
            return None
        
        try:
            data = client.get(cls._profile_key(user_id))
            if data:
                logger.info(f"🎯 Cache HIT for profile:{user_id}")
                return json.loads(data)
            logger.info(f"📭 Cache MISS for profile:{user_id}")
        except Exception as e:
            logger.warning(f"Cache read failed for profile:{user_id}: {e}")
        return None
    
    @classmethod
    def set_profile(cls, user_id: str, profile: Dict[str, Any]) -> bool:
        """
        Set profile in Redis with 5min TTL.
        
        Args:
            user_id: User's UUID
            profile: Profile dict
            
        Returns:
            True if successful, False otherwise
        """
        client = redis_manager.get_client()
        if not client:
            return False
        
        try:
            client.setex(
                cls._profile_key(user_id),
                TTL_PROFILE,
                json.dumps(profile, default=str)
            )
            logger.info(f"💾 Cache SET for profile:{user_id}")
            return True
        except Exception as e:
            logger.warning(f"Cache write failed for profile:{user_id}: {e}")
            return False
    
    @classmethod
    def delete_profile(cls, user_id: str) -> bool:
        """Invalidate profile cache."""
        client = redis_manager.get_client()
        if not client:
            return False
        
        try:
            client.delete(cls._profile_key(user_id))
            logger.info(f"🗑️ Cache DELETE for profile:{user_id}")
            return True
        except Exception as e:
            logger.warning(f"Cache delete failed for profile:{user_id}: {e}")
            return False
    
    # =========================================================================
    # GLOBAL_ROADMAPS Operations (shared across users)
    # =========================================================================
    
    @staticmethod
    def _global_roadmaps_key() -> str:
        """Generate Redis key for global roadmaps list."""
        return "global_roadmaps:all"
    
    @staticmethod
    def _global_roadmap_key(roadmap_id: str) -> str:
        """Generate Redis key for individual roadmap."""
        return f"global_roadmap:{roadmap_id}"
    
    @classmethod
    def get_global_roadmaps(cls) -> Optional[List[Dict[str, Any]]]:
        """
        Get all global roadmaps from Redis.
        
        Returns:
            List of roadmap dicts, or None on miss/error
        """
        client = redis_manager.get_client()
        if not client:
            return None
        
        try:
            data = client.get(cls._global_roadmaps_key())
            if data:
                logger.info("🎯 Cache HIT for global_roadmaps:all")
                return json.loads(data)
            logger.info("📭 Cache MISS for global_roadmaps:all")
        except Exception as e:
            logger.warning(f"Cache read failed for global_roadmaps: {e}")
        return None
    
    @classmethod
    def set_global_roadmaps(cls, roadmaps: List[Dict[str, Any]]) -> bool:
        """
        Set global roadmaps list in Redis with 1h TTL.
        
        Args:
            roadmaps: List of roadmap dicts
            
        Returns:
            True if successful, False otherwise
        """
        client = redis_manager.get_client()
        if not client:
            return False
        
        try:
            client.setex(
                cls._global_roadmaps_key(),
                TTL_GLOBAL_ROADMAPS,
                json.dumps(roadmaps, default=str)
            )
            logger.info(f"💾 Cache SET for global_roadmaps ({len(roadmaps)} roadmaps)")
            return True
        except Exception as e:
            logger.warning(f"Cache write failed for global_roadmaps: {e}")
            return False
    
    @classmethod
    def invalidate_global_roadmaps(cls) -> bool:
        """Invalidate global roadmaps cache (call after create/delete)."""
        client = redis_manager.get_client()
        if not client:
            return False
        
        try:
            client.delete(cls._global_roadmaps_key())
            logger.info("🗑️ Cache INVALIDATE for global_roadmaps")
            return True
        except Exception as e:
            logger.warning(f"Cache invalidate failed for global_roadmaps: {e}")
            return False
    
    # =========================================================================
    # Utility Methods
    # =========================================================================
    
    @classmethod
    def flush_user_cache(cls, user_id: str) -> bool:
        """
        Flush all cached data for a user.
        
        Args:
            user_id: User's UUID
            
        Returns:
            True if successful, False otherwise
        """
        client = redis_manager.get_client()
        if not client:
            return False
        
        try:
            # Collect all keys for this user
            keys_to_delete = [
                cls._today_key(user_id),
                cls._leetcode_key(user_id),
                cls._saved_jobs_list_key(user_id),
                cls._github_activity_key(user_id),
                cls._profile_key(user_id)
            ]
            
            # Add individual saved job keys
            pattern = f"saved_job:{user_id}:*"
            cursor = 0
            while True:
                cursor, keys = client.scan(cursor, match=pattern, count=100)
                keys_to_delete.extend(keys)
                if cursor == 0:
                    break
            
            if keys_to_delete:
                client.delete(*keys_to_delete)
                logger.info(f"Flushed {len(keys_to_delete)} cache keys for user {user_id}")
            
            return True
        except Exception as e:
            logger.warning(f"Cache flush failed for user {user_id}: {e}")
            return False


# Singleton instance for easy imports
cache_service = CacheService()
