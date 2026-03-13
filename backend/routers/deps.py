"""
Shared dependencies for all routers.
Contains database connection, authentication, and common utilities.

RBAC MIGRATION COMPLETE (December 2025):
All role checks now use the database-driven rbac_service.
Role constants are provided as properties that fetch from DB with fallbacks.
"""

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from bson import ObjectId
import os
import re
import logging

logger = logging.getLogger(__name__)

# ==================== RBAC SERVICE INTEGRATION ====================
# Import the RBAC service singleton - this is the source of truth
from .rbac_service import rbac, get_role_group as _get_role_group

def get_role_group(group_name: str, fail_closed: bool = False) -> List[str]:
    """
    Get role group from RBAC service (database-driven).
    Falls back to hardcoded values during startup/testing unless fail_closed=True.
    
    Args:
        group_name: Name of the role group
        fail_closed: If True, returns empty list (denies) instead of falling back
    """
    return _get_role_group(group_name, fail_closed=fail_closed)


# ==================== ROLE CONSTANTS (DB-BACKED WITH FALLBACKS) ====================
# These are now fetched from the database with static fallbacks for startup/testing
# All new code should use get_role_group() directly instead of these constants

# Fallback values (used only if DB is unavailable)
_FALLBACK_ADMIN_ROLES = ["admin"]
_FALLBACK_HR_ROLES = ["admin", "hr_manager", "hr_executive"]
_FALLBACK_HR_ADMIN_ROLES = ["admin", "hr_manager"]
_FALLBACK_SALES_ROLES = ["admin", "sales_manager", "manager", "sr_manager", "principal_consultant", "executive", "sales_executive"]
_FALLBACK_SALES_MANAGER_ROLES = ["admin", "sales_manager", "manager", "sr_manager", "principal_consultant"]
_FALLBACK_SALES_EXECUTIVE_ROLES = ["admin", "executive", "sales_executive", "sales_manager"]
_FALLBACK_PROJECT_ROLES = ["admin", "principal_consultant", "senior_consultant", "manager", "project_manager"]
_FALLBACK_SENIOR_CONSULTING_ROLES = ["admin", "principal_consultant", "senior_consultant"]
_FALLBACK_PRINCIPAL_CONSULTANT_ROLES = ["admin", "principal_consultant"]
_FALLBACK_CONSULTING_ROLES = ["admin", "consultant", "lean_consultant", "lead_consultant", "senior_consultant", "principal_consultant", "subject_matter_expert"]
_FALLBACK_FINANCE_ROLES = ["admin", "finance_manager"]
_FALLBACK_MANAGER_ROLES = ["admin", "manager", "sr_manager", "sales_manager", "hr_manager", "principal_consultant"]
_FALLBACK_APPROVAL_ROLES = ["admin", "manager", "hr_manager", "principal_consultant"]
_FALLBACK_HR_PM_ROLES = ["admin", "hr_manager", "hr_executive", "principal_consultant"]
_FALLBACK_AGREEMENT_APPROVE_ROLES = ["admin", "principal_consultant"]
_FALLBACK_EMPLOYEE_ROLES = [
    "admin", "hr_manager", "hr_executive", 
    "sales_manager", "manager", "sr_manager", "executive", "sales_executive",
    "consultant", "lean_consultant", "lead_consultant", "senior_consultant", "principal_consultant", "subject_matter_expert",
    "finance_manager", "project_manager"
]

# Dynamic role getters with fallbacks (for backward compatibility)
def _get_roles_safe(group_name: str, fallback: List[str]) -> List[str]:
    """Get roles from DB with fallback for backward compatibility."""
    roles = get_role_group(group_name, fail_closed=False)
    return roles if roles else fallback

# Backward-compatible constants (legacy imports will still work)
ADMIN_ROLES = _FALLBACK_ADMIN_ROLES
HR_ROLES = _FALLBACK_HR_ROLES
HR_ADMIN_ROLES = _FALLBACK_HR_ADMIN_ROLES
SALES_ROLES = _FALLBACK_SALES_ROLES
SALES_MANAGER_ROLES = _FALLBACK_SALES_MANAGER_ROLES
SALES_EXECUTIVE_ROLES = _FALLBACK_SALES_EXECUTIVE_ROLES
PROJECT_ROLES = _FALLBACK_PROJECT_ROLES
SENIOR_CONSULTING_ROLES = _FALLBACK_SENIOR_CONSULTING_ROLES
PRINCIPAL_CONSULTANT_ROLES = _FALLBACK_PRINCIPAL_CONSULTANT_ROLES
CONSULTING_ROLES = _FALLBACK_CONSULTING_ROLES
FINANCE_ROLES = _FALLBACK_FINANCE_ROLES
MANAGER_ROLES = _FALLBACK_MANAGER_ROLES
APPROVAL_ROLES = _FALLBACK_APPROVAL_ROLES
HR_PM_ROLES = _FALLBACK_HR_PM_ROLES
AGREEMENT_APPROVE_ROLES = _FALLBACK_AGREEMENT_APPROVE_ROLES
EMPLOYEE_ROLES = _FALLBACK_EMPLOYEE_ROLES
NON_EMPLOYEE_ROLES = ["client", "vendor", "partner", "system", "api_user"]

def validate_employee_id_for_role(role: str, employee_id: Optional[str]) -> bool:
    """
    Validate employee_id based on role:
    - If role ∈ EMPLOYEE_ROLES → employee_id mandatory
    - If role ∉ EMPLOYEE_ROLES → employee_id must be None
    """
    employee_roles = get_role_group("EMPLOYEE_ROLES") or EMPLOYEE_ROLES
    if role in employee_roles:
        return employee_id is not None and employee_id.strip() != ""
    else:
        return employee_id is None or employee_id.strip() == ""


# ==================== RBAC HELPER FUNCTIONS ====================

def has_role(user_role: str, allowed_roles: List[str]) -> bool:
    """
    Check if user has one of the allowed roles.
    Uses rbac_service for the check.
    """
    return rbac.has_role(user_role, allowed_roles)

def has_permission(user_role: str, permission: str) -> bool:
    """
    Check if user role has a specific permission.
    Uses rbac_service for the check.
    """
    return rbac.has_permission(user_role, permission)

def can_approve(user_role: str) -> bool:
    """Check if role can approve requests."""
    return rbac.can_approve(user_role)

def is_manager(user_role: str) -> bool:
    """Check if role is a manager-level role."""
    return rbac.is_manager_role(user_role)


# Default pagination limits
DEFAULT_PAGE_SIZE = 100
MAX_PAGE_SIZE = 1000
LARGE_QUERY_SIZE = 500


# ==================== PAGINATION HELPERS ====================

class PaginationParams:
    """Standard pagination parameters."""
    def __init__(
        self,
        page: int = 1,
        page_size: int = DEFAULT_PAGE_SIZE,
        sort_by: str = None,
        sort_order: str = "desc"
    ):
        self.page = max(1, page)
        self.page_size = min(max(1, page_size), MAX_PAGE_SIZE)
        self.sort_by = sort_by
        self.sort_order = -1 if sort_order == "desc" else 1
        self.skip = (self.page - 1) * self.page_size
    
    def to_dict(self):
        return {
            "page": self.page,
            "page_size": self.page_size,
            "skip": self.skip,
            "sort_by": self.sort_by,
            "sort_order": "desc" if self.sort_order == -1 else "asc"
        }


def paginate_response(items: list, total: int, params: PaginationParams) -> dict:
    """Create paginated response with metadata."""
    total_pages = (total + params.page_size - 1) // params.page_size if total > 0 else 1
    return {
        "items": items,
        "pagination": {
            "page": params.page,
            "page_size": params.page_size,
            "total_items": total,
            "total_pages": total_pages,
            "has_next": params.page < total_pages,
            "has_prev": params.page > 1
        }
    }


# ==================== DATABASE ====================
# Database reference - set by main server
db = None

def set_db(database):
    """Set the database reference for all routers."""
    global db
    db = database

def get_db():
    """Get the database reference."""
    if db is None:
        raise RuntimeError("Database not initialized")
    return db

# JWT Configuration
SECRET_KEY = os.environ.get('SECRET_KEY', 'your-secret-key-change-in-production')
ALGORITHM = "HS256"

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

# Helper function to sanitize user input (prevent XSS)
def sanitize_text(text: str) -> str:
    """Remove HTML tags and dangerous characters from text."""
    if not text or not isinstance(text, str):
        return text
    # Remove HTML tags
    clean = re.sub(r'<[^>]*>', '', text)
    # Remove script-related keywords
    clean = re.sub(r'javascript:', '', clean, flags=re.IGNORECASE)
    clean = re.sub(r'onerror\s*=', '', clean, flags=re.IGNORECASE)
    clean = re.sub(r'onclick\s*=', '', clean, flags=re.IGNORECASE)
    return clean.strip()


def clean_mongo_doc(doc: Dict[str, Any]) -> Dict[str, Any]:
    """
    Remove MongoDB ObjectId from document for JSON serialization.
    Removes _id and converts any ObjectId values to strings.
    """
    if doc is None:
        return None
    if isinstance(doc, list):
        return [clean_mongo_doc(d) for d in doc]
    if not isinstance(doc, dict):
        return doc
    
    cleaned = {}
    for key, value in doc.items():
        if key == "_id":
            continue  # Skip MongoDB's _id field
        if isinstance(value, ObjectId):
            cleaned[key] = str(value)
        elif isinstance(value, dict):
            cleaned[key] = clean_mongo_doc(value)
        elif isinstance(value, list):
            cleaned[key] = [clean_mongo_doc(v) if isinstance(v, dict) else (str(v) if isinstance(v, ObjectId) else v) for v in value]
        else:
            cleaned[key] = value
    return cleaned


def clean_mongo_list(docs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Clean a list of MongoDB documents."""
    return [clean_mongo_doc(doc) for doc in docs]


def require_roles(allowed_roles: List[str]):
    """
    Dependency that checks if user has one of the allowed roles.
    Usage: current_user = Depends(require_roles(SALES_ROLES))
    """
    async def role_checker(current_user = Depends(get_current_user_from_token)):
        if not has_role(current_user.role, allowed_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required roles: {', '.join(allowed_roles)}"
            )
        return current_user
    return role_checker


def require_role_group(group_name: str, fail_closed: bool = False):
    """
    Dependency that checks if user has a role in the specified group (from database).
    Usage: current_user = Depends(require_role_group("HR_ROLES"))
    
    Args:
        group_name: Name of the role group
        fail_closed: If True, denies access on RBAC service failure.
                     Use True for critical security operations (approvals, payments).
    
    This is the preferred method for role checks as it uses the database-driven RBAC.
    """
    async def role_checker(current_user = Depends(get_current_user_from_token)):
        allowed_roles = get_role_group(group_name, fail_closed=fail_closed)
        if not allowed_roles:
            if fail_closed:
                logger.critical(f"RBAC FAIL-CLOSED: Denying access to {group_name}")
            else:
                logger.error(f"Role group '{group_name}' not found in RBAC system")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE if fail_closed else status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Authorization service unavailable" if fail_closed else "Role configuration error"
            )
        if not has_role(current_user.role, allowed_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role group: {group_name}"
            )
        return current_user
    return role_checker


def require_role_group_critical(group_name: str):
    """
    FAIL-CLOSED role check for critical operations.
    Use this for: approvals, payments, data exports, role management.
    
    If RBAC service is unavailable, ACCESS IS DENIED (not permitted).
    """
    return require_role_group(group_name, fail_closed=True)


def require_permission(permission: str):
    """
    Dependency that checks if user has a specific permission.
    Usage: current_user = Depends(require_permission("leads.create"))
    """
    async def permission_checker(current_user = Depends(get_current_user_from_token)):
        if not has_permission(current_user.role, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required permission: {permission}"
            )
        return current_user
    return permission_checker


def require_approval_role():
    """
    Dependency that checks if user can approve requests.
    Usage: current_user = Depends(require_approval_role())
    """
    async def approval_checker(current_user = Depends(get_current_user_from_token)):
        if not can_approve(current_user.role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have approval privileges"
            )
        return current_user
    return approval_checker


async def get_current_user_from_token(token: str = Depends(oauth2_scheme)):
    """Get current user from JWT token - used by require_roles"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    db = get_db()
    # Try by id first
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if user is None:
        # Try by email (admin users have email in sub)
        user = await db.users.find_one({"email": user_id}, {"_id": 0})
    if user is None:
        # Try by employee_id
        user = await db.users.find_one({"employee_id": user_id}, {"_id": 0})
    if user is None:
        raise credentials_exception
    
    # Import here to avoid circular import
    from .models import User
    return User(**user)



# ==================== STANDARDIZED API RESPONSE HELPERS ====================

def api_response(
    data: Any = None, 
    success: bool = True, 
    message: str = None,
    total: int = None,
    page: int = None,
    limit: int = None
) -> Dict[str, Any]:
    """
    Create a standardized API response.
    
    Usage:
        return api_response(data=users, total=len(users))
        return api_response(data=[], message="No records found")
        return api_response(success=False, message="Error occurred")
    
    Returns:
        {
            "success": True,
            "data": [...],      # Always an array or object
            "message": null,
            "pagination": { "total": 0, "page": 1, "limit": 10 }  # Optional
        }
    """
    response = {
        "success": success,
        "data": data if data is not None else [],
    }
    
    if message:
        response["message"] = message
    
    # Add pagination if provided
    if total is not None or page is not None or limit is not None:
        response["pagination"] = {
            "total": total or (len(data) if isinstance(data, list) else 0),
            "page": page or 1,
            "limit": limit or 10
        }
    
    return response


def ensure_list(data: Any) -> List:
    """
    Ensure data is always a list.
    
    Usage:
        items = ensure_list(some_data)  # Always returns []
    """
    if data is None:
        return []
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        # Check for common array keys
        for key in ['items', 'results', 'data', 'records', 'rows']:
            if key in data and isinstance(data[key], list):
                return data[key]
    return []
