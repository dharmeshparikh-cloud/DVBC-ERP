"""
Performance Caching Service
In-memory cache with TTL for frequently accessed data like dashboard stats.

Usage:
    from .cache_service import cache
    
    # Get or compute cached value
    stats = await cache.get_or_set("dashboard_stats", compute_stats_fn, ttl=300)
    
    # Invalidate on data change
    cache.invalidate("dashboard_stats")
    cache.invalidate_pattern("stats_*")
"""

import asyncio
from datetime import datetime, timezone, timedelta
from typing import Any, Callable, Optional, Dict, List
import logging
import hashlib

logger = logging.getLogger(__name__)


class CacheEntry:
    """Single cache entry with metadata."""
    __slots__ = ['value', 'expires_at', 'hits', 'created_at']
    
    def __init__(self, value: Any, ttl: int):
        self.value = value
        self.expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl)
        self.hits = 0
        self.created_at = datetime.now(timezone.utc)
    
    def is_expired(self) -> bool:
        return datetime.now(timezone.utc) > self.expires_at


class PerformanceCache:
    """
    High-performance in-memory cache with TTL support.
    Thread-safe and optimized for async operations.
    """
    
    # Default TTL values for different cache types
    TTL_DASHBOARD_STATS = 300    # 5 minutes
    TTL_USER_PERMISSIONS = 600   # 10 minutes
    TTL_EMPLOYEE_LIST = 300      # 5 minutes
    TTL_PROJECT_LIST = 300       # 5 minutes
    TTL_ANALYTICS = 180          # 3 minutes
    TTL_SHORT = 60               # 1 minute
    
    def __init__(self, max_size: int = 1000):
        self._cache: Dict[str, CacheEntry] = {}
        self._max_size = max_size
        self._lock = asyncio.Lock()
        self._stats = {
            "hits": 0,
            "misses": 0,
            "invalidations": 0,
            "evictions": 0
        }
    
    def _make_key(self, prefix: str, *args, **kwargs) -> str:
        """Create a unique cache key from prefix and arguments."""
        key_parts = [prefix]
        key_parts.extend(str(a) for a in args)
        key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
        key_str = ":".join(key_parts)
        # Use hash for very long keys
        if len(key_str) > 200:
            return f"{prefix}:{hashlib.md5(key_str.encode()).hexdigest()}"
        return key_str
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache if exists and not expired."""
        entry = self._cache.get(key)
        if entry is None:
            self._stats["misses"] += 1
            return None
        
        if entry.is_expired():
            del self._cache[key]
            self._stats["misses"] += 1
            return None
        
        entry.hits += 1
        self._stats["hits"] += 1
        return entry.value
    
    async def set(self, key: str, value: Any, ttl: int = 300) -> None:
        """Set value in cache with TTL."""
        async with self._lock:
            # Evict if at capacity
            if len(self._cache) >= self._max_size:
                await self._evict_oldest()
            
            self._cache[key] = CacheEntry(value, ttl)
    
    async def get_or_set(
        self, 
        key: str, 
        factory: Callable, 
        ttl: int = 300,
        *args, 
        **kwargs
    ) -> Any:
        """
        Get cached value or compute and cache it.
        Factory can be sync or async function.
        """
        # Check cache first
        cached = await self.get(key)
        if cached is not None:
            return cached
        
        # Compute value
        if asyncio.iscoroutinefunction(factory):
            value = await factory(*args, **kwargs)
        else:
            value = factory(*args, **kwargs)
        
        # Cache and return
        await self.set(key, value, ttl)
        return value
    
    def invalidate(self, key: str) -> bool:
        """Invalidate a specific cache key."""
        if key in self._cache:
            del self._cache[key]
            self._stats["invalidations"] += 1
            logger.debug(f"Cache invalidated: {key}")
            return True
        return False
    
    def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate all keys matching pattern (prefix match)."""
        keys_to_delete = [k for k in self._cache.keys() if k.startswith(pattern.rstrip("*"))]
        for key in keys_to_delete:
            del self._cache[key]
        
        if keys_to_delete:
            self._stats["invalidations"] += len(keys_to_delete)
            logger.debug(f"Cache pattern invalidated: {pattern} ({len(keys_to_delete)} keys)")
        return len(keys_to_delete)
    
    def invalidate_all(self) -> int:
        """Clear entire cache."""
        count = len(self._cache)
        self._cache.clear()
        self._stats["invalidations"] += count
        logger.info(f"Cache cleared: {count} entries")
        return count
    
    async def _evict_oldest(self) -> None:
        """Evict oldest entries when cache is full."""
        if not self._cache:
            return
        
        # Sort by creation time and remove oldest 10%
        sorted_keys = sorted(
            self._cache.keys(),
            key=lambda k: self._cache[k].created_at
        )
        evict_count = max(1, len(sorted_keys) // 10)
        
        for key in sorted_keys[:evict_count]:
            del self._cache[key]
            self._stats["evictions"] += 1
    
    async def cleanup_expired(self) -> int:
        """Remove all expired entries."""
        expired_keys = [
            k for k, v in self._cache.items() 
            if v.is_expired()
        ]
        for key in expired_keys:
            del self._cache[key]
        return len(expired_keys)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = self._stats["hits"] + self._stats["misses"]
        hit_rate = (self._stats["hits"] / total_requests * 100) if total_requests > 0 else 0
        
        return {
            "size": len(self._cache),
            "max_size": self._max_size,
            "hits": self._stats["hits"],
            "misses": self._stats["misses"],
            "hit_rate": f"{hit_rate:.1f}%",
            "invalidations": self._stats["invalidations"],
            "evictions": self._stats["evictions"]
        }


# Global cache instance
cache = PerformanceCache()


# Cache key builders for consistency
def stats_key(stat_type: str, user_id: str = None) -> str:
    """Build cache key for stats endpoints."""
    if user_id:
        return f"stats:{stat_type}:user:{user_id}"
    return f"stats:{stat_type}:global"


def list_key(entity: str, filters: Dict = None) -> str:
    """Build cache key for list endpoints."""
    base = f"list:{entity}"
    if filters:
        filter_str = ":".join(f"{k}={v}" for k, v in sorted(filters.items()))
        return f"{base}:{filter_str}"
    return base


def user_key(user_id: str, data_type: str) -> str:
    """Build cache key for user-specific data."""
    return f"user:{user_id}:{data_type}"
