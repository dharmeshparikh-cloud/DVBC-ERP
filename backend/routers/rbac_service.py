"""
RBAC (Role-Based Access Control) Service
=========================================
Single source of truth for roles, permissions, and departments.
Uses MongoDB with in-memory caching for performance.

This module replaces all hardcoded role arrays across the application.

CRITICAL: This is the ONLY source of truth for roles/permissions.
DO NOT create role arrays anywhere else in the codebase.
"""

from typing import Dict, List, Optional, Any, Set
from datetime import datetime, timezone
from functools import lru_cache
import asyncio
import logging
import os

from .rbac_migration import (
    log_fallback_event, 
    compare_permission_results,
    CURRENT_PHASE, 
    MigrationPhase,
    with_rbac_lock
)

logger = logging.getLogger(__name__)

# ==================== IN-MEMORY CACHE ====================
# Cache with TTL for role/permission data
_role_cache: Dict[str, Any] = {}
_permission_cache: Dict[str, Any] = {}
_department_cache: Dict[str, Any] = {}
_cache_timestamp: float = 0
_cache_version: int = 0  # Incremented on each update for cache invalidation
CACHE_TTL_SECONDS = 300  # 5 minutes

# ==================== DEFAULT SEED DATA ====================
# These are migrated to DB on first run, then DB becomes source of truth

DEFAULT_ROLES = [
    {
        "code": "admin",
        "name": "Administrator",
        "description": "Full system access",
        "level": 100,
        "department": "Operations",
        "is_active": True,
        "can_approve": True,
        "can_manage_users": True,
        "inherits_from": [],
        "permissions": ["*"],  # Wildcard = all permissions
    },
    {
        "code": "hr_manager",
        "name": "HR Manager",
        "description": "HR department head",
        "level": 80,
        "department": "HR",
        "is_active": True,
        "can_approve": True,
        "can_manage_users": True,
        "inherits_from": ["hr_executive"],
        "permissions": ["hr.*", "employees.*", "attendance.*", "leaves.*", "payroll.view"],
    },
    {
        "code": "hr_executive",
        "name": "HR Executive",
        "description": "HR team member",
        "level": 40,
        "department": "HR",
        "is_active": True,
        "can_approve": False,
        "can_manage_users": False,
        "inherits_from": [],
        "permissions": ["hr.view", "employees.view", "attendance.*", "leaves.view"],
    },
    {
        "code": "sales_manager",
        "name": "Sales Manager",
        "description": "Sales department head",
        "level": 80,
        "department": "Sales",
        "is_active": True,
        "can_approve": True,
        "can_manage_users": False,
        "inherits_from": ["sales_executive"],
        "permissions": ["sales.*", "leads.*", "agreements.view", "quotations.*", "reports.sales"],
    },
    {
        "code": "sales_executive",
        "name": "Sales Executive",
        "description": "Sales team member",
        "level": 40,
        "department": "Sales",
        "is_active": True,
        "can_approve": False,
        "can_manage_users": False,
        "inherits_from": [],
        "permissions": ["leads.own", "meetings.own", "quotations.create", "agreements.create"],
        "stage_access": {
            "mode": "guided",
            "visible_stages": ["LEAD", "MEETING", "PRICING"],
            "can_skip_stages": False
        }
    },
    {
        "code": "executive",
        "name": "Executive",
        "description": "Sales Executive (legacy code)",
        "level": 40,
        "department": "Sales",
        "is_active": True,
        "can_approve": False,
        "can_manage_users": False,
        "inherits_from": [],
        "permissions": ["leads.own", "meetings.own", "quotations.create", "agreements.create"],
        "stage_access": {
            "mode": "guided",
            "visible_stages": ["LEAD", "MEETING", "PRICING"],
            "can_skip_stages": False
        }
    },
    {
        "code": "principal_consultant",
        "name": "Principal Consultant",
        "description": "Senior-most consulting role, can approve kickoffs",
        "level": 90,
        "department": "Consulting",
        "is_active": True,
        "can_approve": True,
        "can_manage_users": False,
        "inherits_from": ["senior_consultant"],
        "permissions": ["consulting.*", "projects.*", "kickoff.approve", "agreements.approve", "sow.*"],
        "stage_access": {
            "mode": "monitoring",
            "visible_stages": ["LEAD", "MEETING", "PRICING", "SOW", "QUOTATION", "AGREEMENT", "PAYMENT", "KICKOFF", "CLOSED"],
            "can_skip_stages": False,
            "has_reportees_view": True
        }
    },
    {
        "code": "senior_consultant",
        "name": "Senior Consultant",
        "description": "Senior consulting role",
        "level": 70,
        "department": "Consulting",
        "is_active": True,
        "can_approve": True,
        "can_manage_users": False,
        "inherits_from": ["lead_consultant"],
        "permissions": ["consulting.*", "projects.manage", "sow.*", "meetings.*"],
    },
    {
        "code": "lead_consultant",
        "name": "Lead Consultant",
        "description": "Lead consulting role",
        "level": 60,
        "department": "Consulting",
        "is_active": True,
        "can_approve": False,
        "can_manage_users": False,
        "inherits_from": ["consultant"],
        "permissions": ["consulting.*", "projects.view", "sow.create", "meetings.*"],
    },
    {
        "code": "consultant",
        "name": "Consultant",
        "description": "Standard consulting role",
        "level": 50,
        "department": "Consulting",
        "is_active": True,
        "can_approve": False,
        "can_manage_users": False,
        "inherits_from": [],
        "permissions": ["consulting.own", "projects.view", "meetings.own", "attendance.own"],
    },
    {
        "code": "lean_consultant",
        "name": "Lean Consultant",
        "description": "Lean/efficiency focused consultant",
        "level": 50,
        "department": "Consulting",
        "is_active": True,
        "can_approve": False,
        "can_manage_users": False,
        "inherits_from": [],
        "permissions": ["consulting.own", "projects.view", "meetings.own"],
    },
    {
        "code": "subject_matter_expert",
        "name": "Subject Matter Expert",
        "description": "Domain expert consultant",
        "level": 55,
        "department": "Consulting",
        "is_active": True,
        "can_approve": False,
        "can_manage_users": False,
        "inherits_from": ["consultant"],
        "permissions": ["consulting.*", "projects.view", "sow.review"],
    },
    {
        "code": "manager",
        "name": "Manager",
        "description": "General manager role",
        "level": 75,
        "department": "Operations",
        "is_active": True,
        "can_approve": True,
        "can_manage_users": False,
        "inherits_from": [],
        "permissions": ["team.*", "reports.*", "approvals.*"],
    },
    {
        "code": "sr_manager",
        "name": "Senior Manager",
        "description": "Senior manager role",
        "level": 85,
        "department": "Operations",
        "is_active": True,
        "can_approve": True,
        "can_manage_users": True,
        "inherits_from": ["manager"],
        "permissions": ["team.*", "reports.*", "approvals.*", "budget.*"],
    },
    {
        "code": "finance_manager",
        "name": "Finance Manager",
        "description": "Finance department head",
        "level": 80,
        "department": "Finance",
        "is_active": True,
        "can_approve": True,
        "can_manage_users": False,
        "inherits_from": [],
        "permissions": ["finance.*", "payments.*", "invoices.*", "reports.finance"],
    },
    {
        "code": "client",
        "name": "Client",
        "description": "External client user",
        "level": 10,
        "department": "External",
        "is_active": True,
        "can_approve": False,
        "can_manage_users": False,
        "is_external": True,
        "inherits_from": [],
        "permissions": ["client_portal.*"],
    },
]

DEFAULT_DEPARTMENTS = [
    {"code": "HR", "name": "Human Resources", "is_active": True, "color": "#8B5CF6"},
    {"code": "Sales", "name": "Sales & Business Development", "is_active": True, "color": "#F59E0B"},
    {"code": "Consulting", "name": "Consulting & Delivery", "is_active": True, "color": "#10B981"},
    {"code": "Finance", "name": "Finance & Accounts", "is_active": True, "color": "#3B82F6"},
    {"code": "Operations", "name": "Operations & Admin", "is_active": True, "color": "#6B7280"},
    {"code": "External", "name": "External Users", "is_active": True, "color": "#EC4899"},
]

# Pre-computed role groups (will be populated from DB)
DEFAULT_ROLE_GROUPS = {
    "ADMIN_ROLES": ["admin"],
    "HR_ROLES": ["admin", "hr_manager", "hr_executive"],
    "HR_ADMIN_ROLES": ["admin", "hr_manager"],
    "SALES_ROLES": ["admin", "sales_manager", "manager", "sr_manager", "principal_consultant", "executive", "sales_executive"],
    "SALES_MANAGER_ROLES": ["admin", "sales_manager", "manager", "sr_manager", "principal_consultant"],
    "SALES_EXECUTIVE_ROLES": ["admin", "executive", "sales_executive", "sales_manager"],
    "PROJECT_ROLES": ["admin", "principal_consultant", "senior_consultant", "manager"],
    "SENIOR_CONSULTING_ROLES": ["admin", "principal_consultant", "senior_consultant"],
    "PRINCIPAL_CONSULTANT_ROLES": ["admin", "principal_consultant"],
    "CONSULTING_ROLES": ["admin", "consultant", "lean_consultant", "lead_consultant", "senior_consultant", "principal_consultant", "subject_matter_expert"],
    "FINANCE_ROLES": ["admin", "finance_manager"],
    "MANAGER_ROLES": ["admin", "manager", "sr_manager", "sales_manager", "hr_manager", "principal_consultant"],
    "APPROVAL_ROLES": ["admin", "manager", "hr_manager", "principal_consultant"],
    "HR_PM_ROLES": ["admin", "hr_manager", "hr_executive", "principal_consultant"],
    "EMPLOYEE_ROLES": [
        "admin", "hr_manager", "hr_executive",
        "sales_manager", "manager", "sr_manager", "executive", "sales_executive",
        "consultant", "lean_consultant", "lead_consultant", "senior_consultant", "principal_consultant", "subject_matter_expert",
        "finance_manager"
    ],
    "AGREEMENT_APPROVE_ROLES": ["admin", "principal_consultant"],
}


class RBACService:
    """
    Centralized RBAC service with caching.
    All role/permission checks should go through this service.
    """
    
    def __init__(self, db=None):
        self.db = db
        self._initialized = False
    
    def set_db(self, db):
        """Set database connection (called after app startup)"""
        self.db = db
    
    async def initialize(self):
        """Initialize RBAC - seed default data if needed"""
        if self._initialized:
            return
        
        if not self.db:
            logger.warning("RBAC: No database connection, using defaults")
            return
        
        try:
            # Check if roles collection exists and has data
            roles_count = await self.db.rbac_roles.count_documents({})
            
            if roles_count == 0:
                logger.info("RBAC: Seeding default roles...")
                await self._seed_defaults()
            
            # Load into cache
            await self.refresh_cache()
            self._initialized = True
            logger.info(f"RBAC: Initialized with {len(_role_cache)} roles")
            
        except Exception as e:
            logger.error(f"RBAC initialization error: {e}")
            # Fall back to defaults
            self._load_defaults_to_cache()
    
    async def _seed_defaults(self):
        """Seed default roles and departments to database"""
        now = datetime.now(timezone.utc).isoformat()
        
        # Seed departments
        for dept in DEFAULT_DEPARTMENTS:
            dept_doc = {
                **dept,
                "created_at": now,
                "updated_at": now,
                "created_by": "system"
            }
            await self.db.rbac_departments.update_one(
                {"code": dept["code"]},
                {"$setOnInsert": dept_doc},
                upsert=True
            )
        
        # Seed roles
        for role in DEFAULT_ROLES:
            role_doc = {
                **role,
                "created_at": now,
                "updated_at": now,
                "created_by": "system"
            }
            await self.db.rbac_roles.update_one(
                {"code": role["code"]},
                {"$setOnInsert": role_doc},
                upsert=True
            )
        
        # Seed role groups
        for group_name, roles in DEFAULT_ROLE_GROUPS.items():
            group_doc = {
                "code": group_name,
                "name": group_name.replace("_", " ").title(),
                "roles": roles,
                "description": f"Auto-generated group: {group_name}",
                "is_system": True,
                "created_at": now,
                "updated_at": now
            }
            await self.db.rbac_role_groups.update_one(
                {"code": group_name},
                {"$setOnInsert": group_doc},
                upsert=True
            )
        
        # Create indexes
        await self.db.rbac_roles.create_index("code", unique=True)
        await self.db.rbac_departments.create_index("code", unique=True)
        await self.db.rbac_role_groups.create_index("code", unique=True)
    
    def _load_defaults_to_cache(self, reason: str = "unknown"):
        """
        Load default values to cache (fallback).
        FAIL-LOUD: Always logs when this happens.
        """
        global _role_cache, _department_cache, _permission_cache, _cache_timestamp, _cache_version
        
        # Log fallback event - this should trigger alerts in production
        log_fallback_event(
            location="RBACService._load_defaults_to_cache",
            reason=reason,
            fallback_value=f"{len(DEFAULT_ROLES)} default roles"
        )
        
        _role_cache = {r["code"]: r for r in DEFAULT_ROLES}
        _department_cache = {d["code"]: d for d in DEFAULT_DEPARTMENTS}
        _permission_cache = DEFAULT_ROLE_GROUPS.copy()
        _cache_timestamp = datetime.now(timezone.utc).timestamp()
        _cache_version += 1
    
    async def refresh_cache(self):
        """Refresh in-memory cache from database"""
        global _role_cache, _department_cache, _permission_cache, _cache_timestamp, _cache_version
        
        if not self.db:
            self._load_defaults_to_cache(reason="No database connection")
            return
        
        try:
            # Load roles
            roles = await self.db.rbac_roles.find({"is_active": True}).to_list(1000)
            
            if not roles:
                # No roles in DB - this is a problem, not normal
                logger.warning("RBAC: No roles found in database, seeding defaults...")
                await self._seed_defaults()
                roles = await self.db.rbac_roles.find({"is_active": True}).to_list(1000)
            
            _role_cache = {r["code"]: r for r in roles}
            
            # Load departments
            depts = await self.db.rbac_departments.find({"is_active": True}).to_list(100)
            _department_cache = {d["code"]: d for d in depts}
            
            # Load role groups
            groups = await self.db.rbac_role_groups.find({}).to_list(100)
            _permission_cache = {g["code"]: g["roles"] for g in groups}
            
            # Also include defaults for any missing groups
            for group_name, roles_list in DEFAULT_ROLE_GROUPS.items():
                if group_name not in _permission_cache:
                    _permission_cache[group_name] = roles_list
            
            _cache_timestamp = datetime.now(timezone.utc).timestamp()
            _cache_version += 1
            logger.info(f"RBAC cache refreshed: {len(_role_cache)} roles, {len(_department_cache)} depts, version={_cache_version}")
            
        except Exception as e:
            logger.error(f"RBAC cache refresh error: {e}")
            self._load_defaults_to_cache(reason=f"Database error: {str(e)}")
    
    def _is_cache_valid(self) -> bool:
        """Check if cache is still valid"""
        if not _cache_timestamp:
            return False
        age = datetime.now(timezone.utc).timestamp() - _cache_timestamp
        return age < CACHE_TTL_SECONDS
    
    async def _ensure_cache(self):
        """Ensure cache is loaded and valid"""
        if not self._is_cache_valid():
            await self.refresh_cache()
    
    # ==================== ROLE QUERIES ====================
    
    def get_role(self, role_code: str) -> Optional[Dict]:
        """Get role by code (sync, from cache)"""
        role = _role_cache.get(role_code)
        if not role and role_code:
            # Role not in cache - log this unusual situation
            logger.warning(f"RBAC: Role '{role_code}' not found in cache ({len(_role_cache)} roles loaded)")
        return role
    
    def get_all_roles(self) -> List[Dict]:
        """Get all active roles"""
        return list(_role_cache.values())
    
    def get_role_group(self, group_name: str) -> List[str]:
        """
        Get roles in a group (replaces hardcoded arrays).
        FAIL-LOUD: Logs if falling back to defaults.
        """
        # First check cache (from database)
        if group_name in _permission_cache:
            return _permission_cache[group_name]
        
        # Fallback to defaults - but LOG IT
        if group_name in DEFAULT_ROLE_GROUPS:
            log_fallback_event(
                location=f"RBACService.get_role_group({group_name})",
                reason="Group not in cache, using DEFAULT_ROLE_GROUPS",
                fallback_value=DEFAULT_ROLE_GROUPS[group_name]
            )
            return DEFAULT_ROLE_GROUPS[group_name]
        
        # Unknown group - this is an error
        logger.error(f"RBAC: Unknown role group '{group_name}' requested")
        return []
    
    def get_roles_by_department(self, department: str) -> List[str]:
        """Get all role codes for a department"""
        return [r["code"] for r in _role_cache.values() if r.get("department") == department]
    
    def get_role_level(self, role_code: str) -> int:
        """Get role hierarchy level (higher = more access)"""
        role = self.get_role(role_code)
        return role.get("level", 0) if role else 0
    
    # ==================== PERMISSION CHECKS ====================
    
    def has_role(self, user_role: str, required_roles: List[str]) -> bool:
        """Check if user role is in required roles list"""
        if not user_role:
            return False
        # Admin always has access
        if user_role == "admin":
            return True
        return user_role in required_roles
    
    def has_permission(self, user_role: str, permission: str) -> bool:
        """Check if role has a specific permission"""
        role = self.get_role(user_role)
        if not role:
            return False
        
        permissions = role.get("permissions", [])
        
        # Wildcard check
        if "*" in permissions:
            return True
        
        # Exact match
        if permission in permissions:
            return True
        
        # Wildcard pattern (e.g., "hr.*" matches "hr.view")
        for perm in permissions:
            if perm.endswith(".*"):
                prefix = perm[:-2]
                if permission.startswith(prefix):
                    return True
        
        # Check inherited roles
        for parent_role in role.get("inherits_from", []):
            if self.has_permission(parent_role, permission):
                return True
        
        return False
    
    def can_approve(self, user_role: str) -> bool:
        """Check if role can approve requests"""
        role = self.get_role(user_role)
        return role.get("can_approve", False) if role else False
    
    def can_manage_users(self, user_role: str) -> bool:
        """Check if role can manage users"""
        role = self.get_role(user_role)
        return role.get("can_manage_users", False) if role else False
    
    def is_manager_role(self, user_role: str) -> bool:
        """Check if role is a manager-level role"""
        return self.has_role(user_role, self.get_role_group("MANAGER_ROLES"))
    
    def is_hr_role(self, user_role: str) -> bool:
        """Check if role is HR"""
        return self.has_role(user_role, self.get_role_group("HR_ROLES"))
    
    def is_consulting_role(self, user_role: str) -> bool:
        """Check if role is consulting"""
        return self.has_role(user_role, self.get_role_group("CONSULTING_ROLES"))
    
    def is_sales_role(self, user_role: str) -> bool:
        """Check if role is sales"""
        return self.has_role(user_role, self.get_role_group("SALES_ROLES"))
    
    # ==================== STAGE ACCESS (Preserves existing logic) ====================
    
    def get_stage_access(self, user_role: str) -> Dict:
        """Get stage access configuration for role"""
        role = self.get_role(user_role)
        if not role:
            return {
                "mode": "guided",
                "visible_stages": ["LEAD"],
                "can_skip_stages": False
            }
        
        # Return stage access if defined, else full access for non-sales roles
        if "stage_access" in role:
            return role["stage_access"]
        
        # Default: full access for manager+ roles
        if role.get("level", 0) >= 70:
            return {
                "mode": "monitoring",
                "visible_stages": ["LEAD", "MEETING", "PRICING", "SOW", "QUOTATION", "AGREEMENT", "PAYMENT", "KICKOFF", "CLOSED"],
                "can_skip_stages": role["code"] == "admin"
            }
        
        return {
            "mode": "guided",
            "visible_stages": ["LEAD", "MEETING", "PRICING", "SOW", "QUOTATION", "AGREEMENT"],
            "can_skip_stages": False
        }
    
    # ==================== DEPARTMENT QUERIES ====================
    
    def get_department(self, dept_code: str) -> Optional[Dict]:
        """Get department by code"""
        return _department_cache.get(dept_code)
    
    def get_all_departments(self) -> List[Dict]:
        """Get all active departments"""
        return list(_department_cache.values())
    
    # ==================== ADMIN OPERATIONS ====================
    
    async def create_role(self, role_data: Dict, created_by: str) -> Dict:
        """Create a new role"""
        now = datetime.now(timezone.utc).isoformat()
        
        role_doc = {
            **role_data,
            "created_at": now,
            "updated_at": now,
            "created_by": created_by,
            "is_active": True
        }
        
        await self.db.rbac_roles.insert_one(role_doc)
        await self.refresh_cache()
        
        return role_doc
    
    async def update_role(self, role_code: str, updates: Dict, updated_by: str) -> bool:
        """Update an existing role"""
        now = datetime.now(timezone.utc).isoformat()
        
        updates["updated_at"] = now
        updates["updated_by"] = updated_by
        
        result = await self.db.rbac_roles.update_one(
            {"code": role_code},
            {"$set": updates}
        )
        
        if result.modified_count > 0:
            await self.refresh_cache()
            return True
        return False
    
    async def delete_role(self, role_code: str, deleted_by: str) -> bool:
        """Soft delete a role"""
        # Prevent deletion of system roles
        if role_code in ["admin", "client"]:
            raise ValueError("Cannot delete system roles")
        
        return await self.update_role(role_code, {"is_active": False}, deleted_by)
    
    async def create_department(self, dept_data: Dict, created_by: str) -> Dict:
        """Create a new department"""
        now = datetime.now(timezone.utc).isoformat()
        
        dept_doc = {
            **dept_data,
            "created_at": now,
            "updated_at": now,
            "created_by": created_by,
            "is_active": True
        }
        
        await self.db.rbac_departments.insert_one(dept_doc)
        await self.refresh_cache()
        
        return dept_doc
    
    async def update_role_group(self, group_name: str, roles: List[str], updated_by: str) -> bool:
        """Update a role group"""
        now = datetime.now(timezone.utc).isoformat()
        
        result = await self.db.rbac_role_groups.update_one(
            {"code": group_name},
            {
                "$set": {
                    "roles": roles,
                    "updated_at": now,
                    "updated_by": updated_by
                }
            },
            upsert=True
        )
        
        await self.refresh_cache()
        return True


# ==================== SINGLETON INSTANCE ====================
rbac = RBACService()


# ==================== COMPATIBILITY FUNCTIONS ====================
# These replace the hardcoded imports in deps.py

def get_role_group(group_name: str) -> List[str]:
    """Backward-compatible function to get role group"""
    return rbac.get_role_group(group_name)


def has_role_in_group(user_role: str, group_name: str) -> bool:
    """Check if user role is in a named group"""
    return rbac.has_role(user_role, rbac.get_role_group(group_name))


# ==================== PROPERTY ALIASES (for backward compatibility) ====================
# These can be imported like: from rbac_service import ADMIN_ROLES

@property
def ADMIN_ROLES() -> List[str]:
    return rbac.get_role_group("ADMIN_ROLES")

@property  
def HR_ROLES() -> List[str]:
    return rbac.get_role_group("HR_ROLES")

@property
def SALES_ROLES() -> List[str]:
    return rbac.get_role_group("SALES_ROLES")

@property
def MANAGER_ROLES() -> List[str]:
    return rbac.get_role_group("MANAGER_ROLES")

@property
def CONSULTING_ROLES() -> List[str]:
    return rbac.get_role_group("CONSULTING_ROLES")
