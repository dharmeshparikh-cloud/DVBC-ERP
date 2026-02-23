"""
Performance Optimizations Module
================================
Contains caching, indexing, and query optimization utilities.
"""

from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timezone
from functools import wraps
from cachetools import TTLCache
import logging
import asyncio

logger = logging.getLogger(__name__)

# ==================== USER SESSION CACHE ====================
# LRU cache with TTL for authenticated users
# Prevents DB hit on every request

_user_cache: TTLCache = TTLCache(maxsize=1000, ttl=300)  # 5 min TTL
_cache_hits = 0
_cache_misses = 0


def get_cached_user(user_id: str) -> Optional[Dict]:
    """Get user from cache (sync)"""
    global _cache_hits
    user = _user_cache.get(user_id)
    if user:
        _cache_hits += 1
    return user


def set_cached_user(user_id: str, user: Dict):
    """Set user in cache"""
    _user_cache[user_id] = user


def invalidate_user_cache(user_id: str):
    """Invalidate specific user cache entry"""
    if user_id in _user_cache:
        del _user_cache[user_id]
        logger.debug(f"User cache invalidated: {user_id}")


def clear_user_cache():
    """Clear entire user cache"""
    _user_cache.clear()
    logger.info("User cache cleared")


def get_cache_stats() -> Dict:
    """Get cache statistics"""
    global _cache_hits, _cache_misses
    total = _cache_hits + _cache_misses
    return {
        "hits": _cache_hits,
        "misses": _cache_misses,
        "hit_rate": f"{(_cache_hits / total * 100):.1f}%" if total > 0 else "0%",
        "size": len(_user_cache),
        "max_size": _user_cache.maxsize
    }


# ==================== QUERY RESULT CACHE ====================
# For expensive aggregations and reports

_query_cache: TTLCache = TTLCache(maxsize=500, ttl=60)  # 1 min TTL for queries


def cache_key(*args, **kwargs) -> str:
    """Generate cache key from function arguments"""
    key_parts = [str(a) for a in args]
    key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
    return ":".join(key_parts)


def cached_query(ttl: int = 60):
    """
    Decorator for caching query results.
    Use for expensive aggregations.
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            key = f"{func.__name__}:{cache_key(*args[1:], **kwargs)}"  # Skip 'self' or 'db'
            
            cached = _query_cache.get(key)
            if cached is not None:
                logger.debug(f"Cache hit: {key}")
                return cached
            
            result = await func(*args, **kwargs)
            _query_cache[key] = result
            logger.debug(f"Cache set: {key}")
            return result
        return wrapper
    return decorator


# ==================== PAGINATION HELPER ====================

class PaginatedResponse:
    """Standard paginated response structure"""
    
    def __init__(
        self,
        items: List[Any],
        total: int,
        page: int,
        limit: int
    ):
        self.items = items
        self.total = total
        self.page = page
        self.limit = limit
        self.pages = (total + limit - 1) // limit if limit > 0 else 0
        self.has_next = page < self.pages
        self.has_prev = page > 1
    
    def to_dict(self) -> Dict:
        return {
            "items": self.items,
            "pagination": {
                "total": self.total,
                "page": self.page,
                "limit": self.limit,
                "pages": self.pages,
                "has_next": self.has_next,
                "has_prev": self.has_prev
            }
        }


async def paginate_query(
    collection,
    query: Dict,
    page: int = 1,
    limit: int = 20,
    sort_field: str = "created_at",
    sort_order: int = -1,
    projection: Dict = None
) -> PaginatedResponse:
    """
    Execute paginated query with optimal performance.
    
    Args:
        collection: MongoDB collection
        query: Filter query
        page: Page number (1-indexed)
        limit: Items per page
        sort_field: Field to sort by
        sort_order: 1 for ascending, -1 for descending
        projection: Fields to include/exclude
    
    Returns:
        PaginatedResponse with items and pagination metadata
    """
    # Validate pagination params
    page = max(1, page)
    limit = min(max(1, limit), 100)  # Cap at 100 items per page
    skip = (page - 1) * limit
    
    # Default projection excludes _id
    if projection is None:
        projection = {"_id": 0}
    elif "_id" not in projection:
        projection["_id"] = 0
    
    # Execute count and fetch in parallel for efficiency
    count_task = collection.count_documents(query)
    
    cursor = collection.find(query, projection)
    cursor = cursor.sort(sort_field, sort_order)
    cursor = cursor.skip(skip).limit(limit)
    items_task = cursor.to_list(limit)
    
    total, items = await asyncio.gather(count_task, items_task)
    
    return PaginatedResponse(items, total, page, limit)


# ==================== INDEX CREATION ====================

async def ensure_indexes(db):
    """
    Create all required indexes for optimal performance.
    Safe to run multiple times - only creates if not exists.
    """
    logger.info("Ensuring MongoDB indexes...")
    
    indexes_created = []
    
    try:
        # Users collection - Critical for auth (562 checks/session)
        await db.users.create_index("id", unique=True, background=True)
        await db.users.create_index("employee_id", unique=True, sparse=True, background=True)
        await db.users.create_index("email", background=True)
        indexes_created.append("users: id, employee_id, email")
        
        # Leads collection - Most queried for sales
        await db.leads.create_index("id", unique=True, background=True)
        await db.leads.create_index([("assigned_to", 1), ("status", 1)], background=True)
        await db.leads.create_index([("created_at", -1)], background=True)
        await db.leads.create_index("company", background=True)
        indexes_created.append("leads: id, assigned_to+status, created_at, company")
        
        # Employees collection
        await db.employees.create_index("id", unique=True, background=True)
        await db.employees.create_index("employee_id", unique=True, background=True)
        await db.employees.create_index("user_id", background=True)
        await db.employees.create_index("department", background=True)
        await db.employees.create_index("reporting_manager_id", background=True)
        indexes_created.append("employees: id, employee_id, user_id, department, reporting_manager_id")
        
        # Attendance collection - compound index for daily queries
        await db.attendance.create_index([("employee_id", 1), ("date", -1)], background=True)
        await db.attendance.create_index("date", background=True)
        indexes_created.append("attendance: employee_id+date, date")
        
        # Meetings collection
        await db.meetings.create_index("lead_id", background=True)
        await db.meetings.create_index([("lead_id", 1), ("meeting_date", -1)], background=True)
        indexes_created.append("meetings: lead_id, lead_id+meeting_date")
        
        # Pricing plans
        await db.pricing_plans.create_index("lead_id", background=True)
        indexes_created.append("pricing_plans: lead_id")
        
        # SOW collections
        await db.sows.create_index("lead_id", background=True)
        await db.enhanced_sows.create_index("lead_id", background=True)
        indexes_created.append("sows/enhanced_sows: lead_id")
        
        # Quotations
        await db.quotations.create_index("lead_id", background=True)
        await db.quotations.create_index("quotation_number", unique=True, sparse=True, background=True)
        indexes_created.append("quotations: lead_id, quotation_number")
        
        # Agreements
        await db.agreements.create_index([("lead_id", 1), ("status", 1)], background=True)
        await db.agreements.create_index("agreement_number", unique=True, sparse=True, background=True)
        indexes_created.append("agreements: lead_id+status, agreement_number")
        
        # Kickoff requests
        await db.kickoff_requests.create_index("lead_id", background=True)
        await db.kickoff_requests.create_index([("status", 1), ("created_at", -1)], background=True)
        indexes_created.append("kickoff_requests: lead_id, status+created_at")
        
        # Projects
        await db.projects.create_index("project_id", unique=True, sparse=True, background=True)
        await db.projects.create_index([("status", 1), ("created_at", -1)], background=True)
        await db.projects.create_index("client_id", background=True)
        indexes_created.append("projects: project_id, status+created_at, client_id")
        
        # Leave requests
        await db.leave_requests.create_index([("employee_id", 1), ("status", 1)], background=True)
        await db.leave_requests.create_index([("start_date", 1), ("end_date", 1)], background=True)
        indexes_created.append("leave_requests: employee_id+status, date range")
        
        # Expenses
        await db.expenses.create_index([("employee_id", 1), ("status", 1)], background=True)
        await db.expenses.create_index("created_at", background=True)
        indexes_created.append("expenses: employee_id+status, created_at")
        
        # RBAC collections
        await db.rbac_roles.create_index("code", unique=True, background=True)
        await db.rbac_departments.create_index("code", unique=True, background=True)
        await db.rbac_role_groups.create_index("code", unique=True, background=True)
        indexes_created.append("rbac_*: code")
        
        logger.info(f"Indexes ensured: {len(indexes_created)} collections")
        for idx in indexes_created:
            logger.info(f"  ✓ {idx}")
        
        return {"success": True, "indexes": indexes_created}
        
    except Exception as e:
        logger.error(f"Error creating indexes: {e}")
        return {"success": False, "error": str(e), "indexes": indexes_created}


# ==================== QUERY OPTIMIZATION HELPERS ====================

def slim_projection(*fields: str) -> Dict:
    """
    Create projection dict for specified fields only.
    Always excludes _id.
    
    Usage:
        projection = slim_projection("id", "name", "email", "status")
    """
    return {field: 1 for field in fields} | {"_id": 0}


async def batch_lookup(
    collection,
    ids: List[str],
    id_field: str = "id",
    projection: Dict = None
) -> Dict[str, Dict]:
    """
    Fetch multiple documents by ID in single query.
    Returns dict mapping ID -> document for O(1) lookup.
    
    Usage:
        users = await batch_lookup(db.users, user_ids, "id", slim_projection("id", "name"))
        user_name = users.get(some_id, {}).get("name")
    """
    if not ids:
        return {}
    
    if projection is None:
        projection = {"_id": 0}
    
    docs = await collection.find(
        {id_field: {"$in": list(set(ids))}},
        projection
    ).to_list(len(ids))
    
    return {doc[id_field]: doc for doc in docs if id_field in doc}


# ==================== RESPONSE SIZE HELPERS ====================

def truncate_response(data: Any, max_items: int = 100) -> Any:
    """
    Truncate large responses to prevent memory issues.
    Adds _truncated flag if data was cut.
    """
    if isinstance(data, list) and len(data) > max_items:
        return {
            "items": data[:max_items],
            "_truncated": True,
            "_total_available": len(data),
            "_showing": max_items
        }
    return data
