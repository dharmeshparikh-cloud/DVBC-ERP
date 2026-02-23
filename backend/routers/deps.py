"""
Shared dependencies for all routers.
Contains database connection, authentication, and common utilities.

RBAC MIGRATION NOTE (Phase 4):
Role constants are now loaded from the database via rbac_service.
The hardcoded lists below are FALLBACKS for startup/testing only.
All role checks should use rbac_service.get_role_group() or rbac_service.has_role().
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

def get_role_group(group_name: str) -> List[str]:
    """
    Get role group from RBAC service (database-driven).
    Falls back to hardcoded values during startup/testing.
    """
    return _get_role_group(group_name)

# ==================== ROLE CONSTANTS (DB-BACKED) ====================
# These are now lazy-loaded from the database via rbac_service
# The hardcoded values serve as fallbacks during startup only

def _get_roles(group_name: str, fallback: List[str]) -> List[str]:
    """Get roles from DB or fallback."""
    try:
        roles = get_role_group(group_name)
        if roles:
            return roles
    except Exception as e:
        logger.debug(f"RBAC fallback for {group_name}: {e}")
    return fallback

# Admin-level roles (full system access)
ADMIN_ROLES = ["admin"]

# HR department roles
HR_ROLES = ["admin", "hr_manager", "hr_executive"]
HR_ADMIN_ROLES = ["admin", "hr_manager"]

# Sales department roles  
SALES_ROLES = ["admin", "sales_manager", "manager", "sr_manager", "principal_consultant", "executive", "sales_executive"]
SALES_MANAGER_ROLES = ["admin", "sales_manager", "manager", "sr_manager", "principal_consultant"]
SALES_EXECUTIVE_ROLES = ["admin", "executive", "sales_executive", "sales_manager"]

# Project/Consulting management roles (principal_consultant is the senior-most consulting role)
PROJECT_ROLES = ["admin", "principal_consultant", "senior_consultant", "manager", "project_manager"]
SENIOR_CONSULTING_ROLES = ["admin", "principal_consultant", "senior_consultant"]

# Principal Consultant ONLY - for kickoff internal approval
PRINCIPAL_CONSULTANT_ROLES = ["admin", "principal_consultant"]

# All consulting roles (delivery team)
CONSULTING_ROLES = ["admin", "consultant", "lean_consultant", "lead_consultant", "senior_consultant", "principal_consultant", "subject_matter_expert"]

# Finance roles
FINANCE_ROLES = ["admin", "finance_manager"]

# All manager-level roles
MANAGER_ROLES = ["admin", "manager", "sr_manager", "sales_manager", "hr_manager", "principal_consultant"]

# Approval roles (can approve various requests)
APPROVAL_ROLES = ["admin", "manager", "hr_manager", "principal_consultant"]

# HR + Senior Consulting (for attendance, resource management)
HR_PM_ROLES = ["admin", "hr_manager", "hr_executive", "principal_consultant"]

# Agreement approval roles
AGREEMENT_APPROVE_ROLES = ["admin", "principal_consultant"]

# ==================== EMPLOYEE ID LOGIC ====================
# Roles that REQUIRE employee_id (internal employees)
EMPLOYEE_ROLES = [
    "admin", "hr_manager", "hr_executive", 
    "sales_manager", "manager", "sr_manager", "executive", "sales_executive",
    "consultant", "lean_consultant", "lead_consultant", "senior_consultant", "principal_consultant", "subject_matter_expert",
    "finance_manager", "project_manager"
]

# Roles that must NOT have employee_id (external/system)
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
