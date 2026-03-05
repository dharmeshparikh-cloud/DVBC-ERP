"""
Redis Cache Service for Cross-Server Caching
=============================================

Provides distributed caching for multi-instance deployments.
Falls back to in-memory cache if Redis is unavailable.

Environment Variables:
- REDIS_URL: Redis connection URL (e.g., redis://localhost:6379)

Usage:
    from services.redis_cache import redis_cache
    
    # Get or set cached value
    value = await redis_cache.get("key")
    await redis_cache.set("key", value, ttl=300)
    
    # Invalidate cache
    await redis_cache.delete("key")
    await redis_cache.delete_pattern("prefix:*")
"""

import os
import json
import logging
from typing import Any, Optional, Dict
from datetime import datetime, timezone
import asyncio

logger = logging.getLogger(__name__)

# Try to import redis
try:
    import redis.asyncio as aioredis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("Redis library not installed. Using in-memory cache only.")


class RedisCache:
    """
    Distributed Redis cache with automatic fallback to in-memory cache.
    Thread-safe and optimized for async operations.
    """
    
    # Default TTL values (in seconds)
    TTL_SHORT = 60          # 1 minute
    TTL_MEDIUM = 300        # 5 minutes
    TTL_LONG = 600          # 10 minutes
    TTL_VERY_LONG = 3600    # 1 hour
    
    def __init__(self):
        self._redis: Optional[aioredis.Redis] = None
        self._connected = False
        self._fallback_cache: Dict[str, tuple] = {}  # key -> (value, expires_at)
        self._stats = {
            "hits": 0,
            "misses": 0,
            "redis_errors": 0,
            "fallback_hits": 0
        }
    
    async def connect(self, redis_url: Optional[str] = None) -> bool:
        """
        Connect to Redis server.
        Returns True if connected, False otherwise.
        """
        if not REDIS_AVAILABLE:
            logger.info("Redis not available. Using in-memory fallback cache.")
            return False
        
        url = redis_url or os.environ.get("REDIS_URL")
        if not url:
            logger.info("REDIS_URL not configured. Using in-memory fallback cache.")
            return False
        
        try:
            self._redis = aioredis.from_url(
                url,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            # Test connection
            await self._redis.ping()
            self._connected = True
            logger.info(f"Connected to Redis: {url.split('@')[-1] if '@' in url else url}")
            return True
        except Exception as e:
            logger.warning(f"Failed to connect to Redis: {e}. Using in-memory fallback.")
            self._connected = False
            return False
    
    async def disconnect(self):
        """Close Redis connection."""
        if self._redis:
            await self._redis.close()
            self._connected = False
            logger.info("Redis connection closed")
    
    def _serialize(self, value: Any) -> str:
        """Serialize value to JSON string."""
        try:
            return json.dumps(value, default=str)
        except (TypeError, ValueError) as e:
            logger.error(f"Serialization error: {e}")
            return json.dumps(str(value))
    
    def _deserialize(self, data: str) -> Any:
        """Deserialize JSON string to value."""
        try:
            return json.loads(data)
        except (TypeError, ValueError, json.JSONDecodeError):
            return data
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.
        Returns None if not found or expired.
        """
        # Try Redis first
        if self._connected and self._redis:
            try:
                data = await self._redis.get(key)
                if data is not None:
                    self._stats["hits"] += 1
                    return self._deserialize(data)
            except Exception as e:
                self._stats["redis_errors"] += 1
                logger.warning(f"Redis get error: {e}")
        
        # Fallback to in-memory cache
        if key in self._fallback_cache:
            value, expires_at = self._fallback_cache[key]
            if datetime.now(timezone.utc).timestamp() < expires_at:
                self._stats["fallback_hits"] += 1
                return value
            else:
                del self._fallback_cache[key]
        
        self._stats["misses"] += 1
        return None
    
    async def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        """
        Set value in cache with TTL.
        Returns True if successful.
        """
        # Try Redis first
        if self._connected and self._redis:
            try:
                serialized = self._serialize(value)
                await self._redis.setex(key, ttl, serialized)
                return True
            except Exception as e:
                self._stats["redis_errors"] += 1
                logger.warning(f"Redis set error: {e}")
        
        # Fallback to in-memory cache
        expires_at = datetime.now(timezone.utc).timestamp() + ttl
        self._fallback_cache[key] = (value, expires_at)
        
        # Cleanup old entries if cache is too large
        if len(self._fallback_cache) > 1000:
            await self._cleanup_fallback()
        
        return True
    
    async def delete(self, key: str) -> bool:
        """Delete a key from cache."""
        deleted = False
        
        if self._connected and self._redis:
            try:
                await self._redis.delete(key)
                deleted = True
            except Exception as e:
                logger.warning(f"Redis delete error: {e}")
        
        if key in self._fallback_cache:
            del self._fallback_cache[key]
            deleted = True
        
        return deleted
    
    async def delete_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching pattern.
        Pattern uses * as wildcard (e.g., "user:*")
        Returns count of deleted keys.
        """
        count = 0
        
        if self._connected and self._redis:
            try:
                keys = []
                async for key in self._redis.scan_iter(match=pattern, count=100):
                    keys.append(key)
                
                if keys:
                    count = await self._redis.delete(*keys)
            except Exception as e:
                logger.warning(f"Redis delete pattern error: {e}")
        
        # Also clean fallback cache
        prefix = pattern.rstrip("*")
        keys_to_delete = [k for k in self._fallback_cache if k.startswith(prefix)]
        for key in keys_to_delete:
            del self._fallback_cache[key]
            count += 1
        
        return count
    
    async def get_or_set(
        self, 
        key: str, 
        factory, 
        ttl: int = 300
    ) -> Any:
        """
        Get cached value or compute and cache it.
        Factory can be sync or async function.
        """
        value = await self.get(key)
        if value is not None:
            return value
        
        # Compute value
        if asyncio.iscoroutinefunction(factory):
            value = await factory()
        else:
            value = factory()
        
        await self.set(key, value, ttl)
        return value
    
    async def _cleanup_fallback(self):
        """Remove expired entries from fallback cache."""
        now = datetime.now(timezone.utc).timestamp()
        keys_to_delete = [
            k for k, (_, expires_at) in self._fallback_cache.items()
            if now >= expires_at
        ]
        for key in keys_to_delete:
            del self._fallback_cache[key]
        
        # If still too large, remove oldest 10%
        if len(self._fallback_cache) > 1000:
            sorted_keys = sorted(
                self._fallback_cache.keys(),
                key=lambda k: self._fallback_cache[k][1]
            )
            for key in sorted_keys[:100]:
                del self._fallback_cache[key]
    
    def get_stats(self) -> Dict:
        """Get cache statistics."""
        total = self._stats["hits"] + self._stats["misses"]
        hit_rate = (self._stats["hits"] / total * 100) if total > 0 else 0
        
        return {
            "connected": self._connected,
            "hits": self._stats["hits"],
            "misses": self._stats["misses"],
            "hit_rate": f"{hit_rate:.1f}%",
            "redis_errors": self._stats["redis_errors"],
            "fallback_hits": self._stats["fallback_hits"],
            "fallback_size": len(self._fallback_cache)
        }
    
    async def health_check(self) -> Dict:
        """Check Redis health and return status."""
        status = {
            "redis_available": REDIS_AVAILABLE,
            "connected": self._connected,
            "stats": self.get_stats()
        }
        
        if self._connected and self._redis:
            try:
                await self._redis.ping()
                status["ping"] = "OK"
            except Exception as e:
                status["ping"] = f"FAILED: {e}"
        
        return status


# Global Redis cache instance
redis_cache = RedisCache()


# ===========================================
# CACHE KEY BUILDERS
# ===========================================

def cache_key(prefix: str, *args, **kwargs) -> str:
    """Build a cache key from prefix and arguments."""
    parts = [prefix]
    parts.extend(str(a) for a in args if a is not None)
    parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()) if v is not None)
    return ":".join(parts)


# Pre-defined key builders for common patterns
class CacheKeys:
    """Cache key builders for common data types."""
    
    @staticmethod
    def dashboard_stats(user_id: str = None) -> str:
        return cache_key("stats", "dashboard", user_id)
    
    @staticmethod
    def hr_stats() -> str:
        return cache_key("stats", "hr")
    
    @staticmethod
    def sales_stats() -> str:
        return cache_key("stats", "sales")
    
    @staticmethod
    def employee_list(department: str = None, status: str = None, page: int = 1) -> str:
        return cache_key("employees", "list", department=department, status=status, page=page)
    
    @staticmethod
    def employee(employee_id: str) -> str:
        return cache_key("employees", "detail", employee_id)
    
    @staticmethod
    def lead_list(status: str = None, assigned_to: str = None, page: int = 1) -> str:
        return cache_key("leads", "list", status=status, assigned_to=assigned_to, page=page)
    
    @staticmethod
    def lead(lead_id: str) -> str:
        return cache_key("leads", "detail", lead_id)
    
    @staticmethod
    def user_permissions(user_id: str) -> str:
        return cache_key("permissions", user_id)
    
    @staticmethod
    def onboarding_submissions(status: str = None) -> str:
        return cache_key("onboarding", "submissions", status=status)
    
    @staticmethod
    def attendance(employee_id: str, month: str) -> str:
        return cache_key("attendance", employee_id, month)


# ===========================================
# CACHE INVALIDATION HELPERS
# ===========================================

class CacheInvalidation:
    """Helpers for invalidating related cache keys."""
    
    @staticmethod
    async def employees():
        """Invalidate all employee-related caches."""
        await redis_cache.delete_pattern("employees:*")
        await redis_cache.delete_pattern("stats:hr*")
    
    @staticmethod
    async def employee(employee_id: str):
        """Invalidate specific employee cache."""
        await redis_cache.delete(CacheKeys.employee(employee_id))
        await redis_cache.delete_pattern("employees:list:*")
    
    @staticmethod
    async def leads():
        """Invalidate all lead-related caches."""
        await redis_cache.delete_pattern("leads:*")
        await redis_cache.delete_pattern("stats:sales*")
    
    @staticmethod
    async def lead(lead_id: str):
        """Invalidate specific lead cache."""
        await redis_cache.delete(CacheKeys.lead(lead_id))
        await redis_cache.delete_pattern("leads:list:*")
    
    @staticmethod
    async def onboarding():
        """Invalidate onboarding caches."""
        await redis_cache.delete_pattern("onboarding:*")
        await redis_cache.delete_pattern("employees:*")
        await redis_cache.delete_pattern("stats:hr*")
    
    @staticmethod
    async def dashboard():
        """Invalidate dashboard stats."""
        await redis_cache.delete_pattern("stats:*")
    
    @staticmethod
    async def all():
        """Invalidate entire cache."""
        await redis_cache.delete_pattern("*")
