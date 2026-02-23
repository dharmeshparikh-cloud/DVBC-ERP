"""
RBAC Admin Router
=================
API endpoints for managing roles, permissions, and departments.
Only accessible by admin users.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone

from .deps import get_db, get_current_user
from .models import User
from .rbac_service import rbac

router = APIRouter(prefix="/rbac", tags=["RBAC Administration"])


# ==================== REQUEST/RESPONSE MODELS ====================

class RoleCreate(BaseModel):
    code: str = Field(..., min_length=2, max_length=50, pattern="^[a-z_]+$")
    name: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = ""
    level: int = Field(default=50, ge=1, le=100)
    department: str
    can_approve: bool = False
    can_manage_users: bool = False
    inherits_from: List[str] = []
    permissions: List[str] = []
    stage_access: Optional[Dict] = None


class RoleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    level: Optional[int] = None
    department: Optional[str] = None
    can_approve: Optional[bool] = None
    can_manage_users: Optional[bool] = None
    inherits_from: Optional[List[str]] = None
    permissions: Optional[List[str]] = None
    stage_access: Optional[Dict] = None
    is_active: Optional[bool] = None


class DepartmentCreate(BaseModel):
    code: str = Field(..., min_length=2, max_length=50)
    name: str = Field(..., min_length=2, max_length=100)
    color: str = Field(default="#6B7280", pattern="^#[0-9A-Fa-f]{6}$")


class DepartmentUpdate(BaseModel):
    name: Optional[str] = None
    color: Optional[str] = None
    is_active: Optional[bool] = None


class RoleGroupUpdate(BaseModel):
    roles: List[str]


class BulkPermissionUpdate(BaseModel):
    role_code: str
    permissions: List[str]


# ==================== ROLE ENDPOINTS ====================

@router.get("/roles")
async def get_all_roles(
    current_user: User = Depends(get_current_user),
    include_inactive: bool = False
):
    """Get all roles (Admin/HR only)"""
    if current_user.role not in ["admin", "hr_manager"]:
        raise HTTPException(status_code=403, detail="Admin or HR Manager access required")
    
    db = get_db()
    query = {} if include_inactive else {"is_active": True}
    roles = await db.rbac_roles.find(query, {"_id": 0}).sort("level", -1).to_list(1000)
    
    return {
        "roles": roles,
        "total": len(roles)
    }


@router.get("/roles/{role_code}")
async def get_role(
    role_code: str,
    current_user: User = Depends(get_current_user)
):
    """Get a specific role"""
    if current_user.role not in ["admin", "hr_manager"]:
        raise HTTPException(status_code=403, detail="Admin or HR Manager access required")
    
    role = rbac.get_role(role_code)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    
    # Remove MongoDB _id if present
    role_copy = {k: v for k, v in role.items() if k != "_id"}
    return role_copy


@router.post("/roles")
async def create_role(
    role_data: RoleCreate,
    current_user: User = Depends(get_current_user)
):
    """Create a new role (Admin only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Check if role code already exists
    existing = rbac.get_role(role_data.code)
    if existing:
        raise HTTPException(status_code=400, detail="Role code already exists")
    
    # Validate department
    dept = rbac.get_department(role_data.department)
    if not dept:
        raise HTTPException(status_code=400, detail="Invalid department")
    
    # Validate inherited roles exist
    for parent in role_data.inherits_from:
        if not rbac.get_role(parent):
            raise HTTPException(status_code=400, detail=f"Parent role '{parent}' not found")
    
    try:
        new_role = await rbac.create_role(role_data.dict(), current_user.id)
        return {
            "message": "Role created successfully",
            "role": {k: v for k, v in new_role.items() if k != "_id"}
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/roles/{role_code}")
async def update_role(
    role_code: str,
    updates: RoleUpdate,
    current_user: User = Depends(get_current_user)
):
    """Update a role (Admin only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Prevent modification of admin role's core properties
    if role_code == "admin" and updates.level is not None and updates.level < 100:
        raise HTTPException(status_code=400, detail="Cannot reduce admin role level")
    
    update_dict = {k: v for k, v in updates.dict().items() if v is not None}
    
    if not update_dict:
        raise HTTPException(status_code=400, detail="No updates provided")
    
    success = await rbac.update_role(role_code, update_dict, current_user.id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Role not found")
    
    return {"message": "Role updated successfully"}


@router.delete("/roles/{role_code}")
async def delete_role(
    role_code: str,
    current_user: User = Depends(get_current_user)
):
    """Delete a role (soft delete, Admin only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Check if any users have this role
    db = get_db()
    users_with_role = await db.users.count_documents({"role": role_code})
    if users_with_role > 0:
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot delete role: {users_with_role} users currently have this role"
        )
    
    try:
        success = await rbac.delete_role(role_code, current_user.id)
        if not success:
            raise HTTPException(status_code=404, detail="Role not found")
        return {"message": "Role deleted successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==================== DEPARTMENT ENDPOINTS ====================

@router.get("/departments")
async def get_all_departments(
    current_user: User = Depends(get_current_user),
    include_inactive: bool = False
):
    """Get all departments"""
    if current_user.role not in ["admin", "hr_manager"]:
        raise HTTPException(status_code=403, detail="Admin or HR Manager access required")
    
    db = get_db()
    query = {} if include_inactive else {"is_active": True}
    departments = await db.rbac_departments.find(query, {"_id": 0}).to_list(100)
    
    return {
        "departments": departments,
        "total": len(departments)
    }


@router.post("/departments")
async def create_department(
    dept_data: DepartmentCreate,
    current_user: User = Depends(get_current_user)
):
    """Create a new department (Admin only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    existing = rbac.get_department(dept_data.code)
    if existing:
        raise HTTPException(status_code=400, detail="Department code already exists")
    
    new_dept = await rbac.create_department(dept_data.dict(), current_user.id)
    return {
        "message": "Department created successfully",
        "department": {k: v for k, v in new_dept.items() if k != "_id"}
    }


@router.put("/departments/{dept_code}")
async def update_department(
    dept_code: str,
    updates: DepartmentUpdate,
    current_user: User = Depends(get_current_user)
):
    """Update a department (Admin only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    db = get_db()
    update_dict = {k: v for k, v in updates.dict().items() if v is not None}
    update_dict["updated_at"] = datetime.now(timezone.utc).isoformat()
    update_dict["updated_by"] = current_user.id
    
    result = await db.rbac_departments.update_one(
        {"code": dept_code},
        {"$set": update_dict}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Department not found")
    
    await rbac.refresh_cache()
    return {"message": "Department updated successfully"}


# ==================== ROLE GROUP ENDPOINTS ====================

@router.get("/role-groups")
async def get_all_role_groups(
    current_user: User = Depends(get_current_user)
):
    """Get all role groups"""
    if current_user.role not in ["admin", "hr_manager"]:
        raise HTTPException(status_code=403, detail="Admin or HR Manager access required")
    
    db = get_db()
    groups = await db.rbac_role_groups.find({}, {"_id": 0}).to_list(100)
    
    return {
        "groups": groups,
        "total": len(groups)
    }


@router.put("/role-groups/{group_name}")
async def update_role_group(
    group_name: str,
    update: RoleGroupUpdate,
    current_user: User = Depends(get_current_user)
):
    """Update roles in a group (Admin only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Validate all roles exist
    for role_code in update.roles:
        if not rbac.get_role(role_code):
            raise HTTPException(status_code=400, detail=f"Role '{role_code}' not found")
    
    await rbac.update_role_group(group_name, update.roles, current_user.id)
    return {"message": "Role group updated successfully"}


# ==================== UTILITY ENDPOINTS ====================

@router.post("/refresh-cache")
async def refresh_cache(
    current_user: User = Depends(get_current_user)
):
    """Manually refresh RBAC cache (Admin only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    await rbac.refresh_cache()
    return {
        "message": "Cache refreshed successfully",
        "roles_count": len(rbac.get_all_roles()),
        "departments_count": len(rbac.get_all_departments())
    }


@router.get("/check-permission")
async def check_permission(
    role: str,
    permission: str,
    current_user: User = Depends(get_current_user)
):
    """Check if a role has a specific permission"""
    has_perm = rbac.has_permission(role, permission)
    return {
        "role": role,
        "permission": permission,
        "has_permission": has_perm
    }


@router.get("/role-hierarchy")
async def get_role_hierarchy(
    current_user: User = Depends(get_current_user)
):
    """Get role hierarchy visualization data"""
    if current_user.role not in ["admin", "hr_manager"]:
        raise HTTPException(status_code=403, detail="Admin or HR Manager access required")
    
    roles = rbac.get_all_roles()
    
    # Group by department
    by_dept = {}
    for role in roles:
        dept = role.get("department", "Other")
        if dept not in by_dept:
            by_dept[dept] = []
        by_dept[dept].append({
            "code": role["code"],
            "name": role["name"],
            "level": role.get("level", 0),
            "can_approve": role.get("can_approve", False),
            "inherits_from": role.get("inherits_from", [])
        })
    
    # Sort by level within each department
    for dept in by_dept:
        by_dept[dept].sort(key=lambda x: x["level"], reverse=True)
    
    return {
        "hierarchy": by_dept,
        "departments": list(by_dept.keys())
    }


@router.get("/my-permissions")
async def get_my_permissions(
    current_user: User = Depends(get_current_user)
):
    """Get current user's role and permissions"""
    role = rbac.get_role(current_user.role)
    
    if not role:
        return {
            "role": current_user.role,
            "permissions": [],
            "stage_access": rbac.get_stage_access(current_user.role)
        }
    
    return {
        "role": current_user.role,
        "role_name": role.get("name"),
        "level": role.get("level", 0),
        "department": role.get("department"),
        "permissions": role.get("permissions", []),
        "can_approve": role.get("can_approve", False),
        "can_manage_users": role.get("can_manage_users", False),
        "stage_access": rbac.get_stage_access(current_user.role)
    }
