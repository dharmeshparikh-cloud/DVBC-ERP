"""
Enhanced Redis Distributed Cache Service
=========================================

Provides distributed caching with automatic fallback to in-memory cache.
Includes lifecycle-aware cache invalidation to prevent stale data.

Features:
- Redis-based distributed caching
- Automatic fallback to in-memory cache
- Lifecycle-aware invalidation
- TTL management
- Cache statistics
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set
from functools import wraps

logger = logging.getLogger(__name__)

# Try to import redis
try:
    import redis.asyncio as aioredis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("Redis not installed. Using in-memory cache only.")


class DistributedCache:
    """
    Production-ready distributed caching with Redis support.
    Automatically falls back to in-memory caching if Redis is unavailable.
    """
    
    # Cache TTL Configuration (in seconds)
    class TTL:
        EMPLOYEE_LIST = 300          # 5 minutes - frequently accessed
        EMPLOYEE_DETAIL = 180        # 3 minutes - may change often
        DASHBOARD_STATS = 300        # 5 minutes
        USER_PERMISSIONS = 600       # 10 minutes - rarely changes
        GO_LIVE_DATA = 120           # 2 minutes - lifecycle critical
        ANALYTICS = 180              # 3 minutes
        MASTER_DATA = 900            # 15 minutes - rarely changes
        SHORT = 60                   # 1 minute - volatile data
        NOTIFICATIONS = 30           # 30 seconds - needs freshness
    
    # Lifecycle-critical keys that need immediate invalidation
    LIFECYCLE_KEYS = {
        "list:employees",
        "stats:employees",
        "stats:go-live",
        "list:go-live",
        "stats:dashboard",
        "list:onboarding"
    }
    
    def __init__(self, redis_url: Optional[str] = None):
        self.redis_url = redis_url or os.environ.get("REDIS_URL", "redis://localhost:6379")
        self.redis: Optional[aioredis.Redis] = None
        self._memory_cache: Dict[str, tuple] = {}  # (value, expiry_time)
        self._connected = False
        self._stats = {
            "hits": 0,
            "misses": 0,
            "redis_errors": 0,
            "invalidations": 0
        }
    
    async def connect(self) -> bool:
        """Attempt to connect to Redis."""
        if not REDIS_AVAILABLE:
            logger.info("Redis not available, using in-memory cache")
            return False
        
        try:
            self.redis = await aioredis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            await self.redis.ping()
            self._connected = True
            logger.info(f"Connected to Redis at {self.redis_url}")
            return True
        except Exception as e:
            logger.warning(f"Failed to connect to Redis: {e}. Using in-memory fallback.")
            self._connected = False
            return False
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        # Try Redis first
        if self._connected and self.redis:
            try:
                value = await self.redis.get(key)
                if value:
                    self._stats["hits"] += 1
                    return json.loads(value)
                self._stats["misses"] += 1
                return None
            except Exception as e:
                self._stats["redis_errors"] += 1
                logger.warning(f"Redis GET error: {e}")
        
        # Fallback to memory cache
        if key in self._memory_cache:
            value, expiry = self._memory_cache[key]
            if datetime.now(timezone.utc).timestamp() < expiry:
                self._stats["hits"] += 1
                return value
            else:
                del self._memory_cache[key]
        
        self._stats["misses"] += 1
        return None
    
    async def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        """Set value in cache with TTL."""
        # Try Redis first
        if self._connected and self.redis:
            try:
                await self.redis.setex(key, ttl, json.dumps(value, default=str))
                return True
            except Exception as e:
                self._stats["redis_errors"] += 1
                logger.warning(f"Redis SET error: {e}")
        
        # Fallback to memory cache
        expiry = datetime.now(timezone.utc).timestamp() + ttl
        self._memory_cache[key] = (value, expiry)
        return True
    
    async def delete(self, key: str) -> bool:
        """Delete a specific key."""
        self._stats["invalidations"] += 1
        
        # Delete from Redis
        if self._connected and self.redis:
            try:
                await self.redis.delete(key)
            except Exception as e:
                logger.warning(f"Redis DELETE error: {e}")
        
        # Delete from memory cache
        if key in self._memory_cache:
            del self._memory_cache[key]
        
        return True
    
    async def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching pattern."""
        count = 0
        self._stats["invalidations"] += 1
        
        # Handle pattern (convert glob to regex-like matching)
        prefix = pattern.rstrip("*")
        
        # Delete from Redis
        if self._connected and self.redis:
            try:
                keys = await self.redis.keys(pattern)
                if keys:
                    count = await self.redis.delete(*keys)
            except Exception as e:
                logger.warning(f"Redis DELETE pattern error: {e}")
        
        # Delete from memory cache
        keys_to_delete = [k for k in self._memory_cache.keys() if k.startswith(prefix)]
        for key in keys_to_delete:
            del self._memory_cache[key]
            count += 1
        
        return count
    
    def invalidate_lifecycle_caches(self):
        """
        Invalidate all lifecycle-critical caches.
        Call this after any employee lifecycle state change.
        """
        for key in self.LIFECYCLE_KEYS:
            asyncio.create_task(self.delete_pattern(f"{key}*"))
        logger.debug("Lifecycle caches invalidated")
    
    async def invalidate_employee(self, employee_id: str):
        """Invalidate all caches related to a specific employee."""
        patterns = [
            f"employee:{employee_id}*",
            f"checklist:{employee_id}*",
            "list:employees*",
            "stats:employees*"
        ]
        for pattern in patterns:
            await self.delete_pattern(pattern)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total = self._stats["hits"] + self._stats["misses"]
        hit_rate = (self._stats["hits"] / total * 100) if total > 0 else 0
        
        return {
            "hits": self._stats["hits"],
            "misses": self._stats["misses"],
            "hit_rate": f"{hit_rate:.1f}%",
            "redis_errors": self._stats["redis_errors"],
            "invalidations": self._stats["invalidations"],
            "redis_connected": self._connected,
            "memory_cache_size": len(self._memory_cache)
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Check cache health status."""
        result = {
            "redis_available": REDIS_AVAILABLE,
            "redis_connected": self._connected,
            "memory_cache_entries": len(self._memory_cache),
            "status": "healthy"
        }
        
        if self._connected and self.redis:
            try:
                await self.redis.ping()
                result["redis_ping"] = "ok"
            except Exception as e:
                result["redis_ping"] = f"failed: {e}"
                result["status"] = "degraded"
        
        return result


# Lifecycle-aware cache invalidation decorator
def invalidate_cache_on_lifecycle_change(cache_patterns: List[str]):
    """
    Decorator to automatically invalidate cache after lifecycle-changing operations.
    
    Usage:
        @invalidate_cache_on_lifecycle_change(["list:employees", "stats:go-live"])
        async def approve_go_live(...):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)
            
            # Invalidate caches after successful operation
            for pattern in cache_patterns:
                distributed_cache.invalidate_pattern(pattern)
            
            return result
        return wrapper
    return decorator


# Global distributed cache instance
distributed_cache = DistributedCache()


# Cache key builders
class CacheKeys:
    """Centralized cache key generation for consistency."""
    
    @staticmethod
    def employee_list(filters: Dict = None, page: int = 1) -> str:
        """Generate cache key for employee list."""
        base = "list:employees"
        if filters:
            filter_str = ":".join(f"{k}={v}" for k, v in sorted(filters.items()) if v)
            return f"{base}:{filter_str}:page={page}"
        return f"{base}:page={page}"
    
    @staticmethod
    def employee_detail(employee_id: str) -> str:
        return f"employee:{employee_id}"
    
    @staticmethod
    def employee_checklist(employee_id: str) -> str:
        return f"checklist:{employee_id}"
    
    @staticmethod
    def dashboard_stats(user_id: str = None) -> str:
        if user_id:
            return f"stats:dashboard:user:{user_id}"
        return "stats:dashboard:global"
    
    @staticmethod
    def go_live_pending() -> str:
        return "list:go-live:pending"
    
    @staticmethod
    def go_live_stats() -> str:
        return "stats:go-live"
    
    @staticmethod
    def user_permissions(user_id: str) -> str:
        return f"user:{user_id}:permissions"
    
    @staticmethod
    def notifications(user_id: str) -> str:
        return f"notifications:{user_id}"
