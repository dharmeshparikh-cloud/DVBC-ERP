"""
Roles Router - Role management and permissions.
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Optional, List
from datetime import datetime, timezone
import uuid
from .deps import get_db, ADMIN_ROLES
from .models import User
from .auth import get_current_user

router = APIRouter(prefix="/roles", tags=["Roles"])


@router.get("")
async def get_roles(current_user: User = Depends(get_current_user)):
    """Get all roles"""
    db = get_db()
    
    roles = await db.roles.find({}, {"_id": 0}).to_list(100)
    
    if not roles:
        # Return default roles
        return [
            {"id": "admin", "name": "Admin", "description": "Full system access"},
            {"id": "manager", "name": "Manager", "description": "Team management"},
            {"id": "sales_manager", "name": "Sales Manager", "description": "Sales team management"},
            {"id": "hr_manager", "name": "HR Manager", "description": "HR operations"},
            {"id": "principal_consultant", "name": "Principal Consultant", "description": "Senior consulting & project authority"},
            {"id": "senior_consultant", "name": "Senior Consultant", "description": "Senior consulting services"},
            {"id": "consultant", "name": "Consultant", "description": "Consulting services"},
            {"id": "employee", "name": "Employee", "description": "Regular employee"}
        ]
    
    return roles


@router.post("")
async def create_role(data: dict, current_user: User = Depends(get_current_user)):
    """Create a new role (admin only)"""
    db = get_db()
    
    if current_user.role not in ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Only admin can create roles")
    
    role_id = data.get("id") or str(uuid.uuid4())
    name = data.get("name")
    
    if not name:
        raise HTTPException(status_code=400, detail="name is required")
    
    existing = await db.roles.find_one({"$or": [{"id": role_id}, {"name": name}]}, {"_id": 0})
    if existing:
        raise HTTPException(status_code=400, detail="Role with this ID or name already exists")
    
    role_doc = {
        "id": role_id,
        "name": name,
        "description": data.get("description", ""),
        "permissions": data.get("permissions", []),
        "created_by": current_user.id,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.roles.insert_one(role_doc)
    role_doc.pop("_id", None)
    return role_doc


@router.get("/{role_id}")
async def get_role(role_id: str, current_user: User = Depends(get_current_user)):
    """Get role by ID"""
    db = get_db()
    
    role = await db.roles.find_one({"id": role_id}, {"_id": 0})
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    
    return role


@router.patch("/{role_id}")
async def update_role(role_id: str, data: dict, current_user: User = Depends(get_current_user)):
    """Update a role (admin only)"""
    db = get_db()
    
    if current_user.role not in ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Only admin can update roles")
    
    role = await db.roles.find_one({"id": role_id}, {"_id": 0})
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    
    update_fields = {}
    for field in ["name", "description", "permissions"]:
        if field in data:
            update_fields[field] = data[field]
    
    update_fields["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.roles.update_one({"id": role_id}, {"$set": update_fields})
    
    return {"message": "Role updated"}


@router.delete("/{role_id}")
async def delete_role(role_id: str, current_user: User = Depends(get_current_user)):
    """Delete a role (admin only)"""
    db = get_db()
    
    if current_user.role not in ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Only admin can delete roles")
    
    # Check if role is in use
    users_with_role = await db.users.count_documents({"role": role_id})
    if users_with_role > 0:
        raise HTTPException(status_code=400, detail=f"Cannot delete role - {users_with_role} users have this role")
    
    result = await db.roles.delete_one({"id": role_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Role not found")
    
    return {"message": "Role deleted"}


@router.get("/categories/sow")
async def get_sow_role_categories(current_user: User = Depends(get_current_user)):
    """Get SOW role categories"""
    return ["discovery", "implementation", "training", "support", "management"]


# Role Permissions endpoints
@router.get("-permissions")
async def get_role_permissions(current_user: User = Depends(get_current_user)):
    """Get role permissions matrix"""
    db = get_db()
    
    permissions = await db.role_permissions.find({}, {"_id": 0}).to_list(100)
    return permissions


@router.get("-permissions/{role}")
async def get_permissions_for_role(role: str, current_user: User = Depends(get_current_user)):
    """Get permissions for a specific role"""
    db = get_db()
    
    permissions = await db.role_permissions.find_one({"role": role}, {"_id": 0})
    if not permissions:
        return {"role": role, "permissions": []}
    
    return permissions


@router.patch("-permissions/{role}")
async def update_role_permissions(role: str, data: dict, current_user: User = Depends(get_current_user)):
    """Update permissions for a role (admin only)"""
    db = get_db()
    
    if current_user.role not in ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Only admin can update role permissions")
    
    permissions = data.get("permissions", [])
    
    await db.role_permissions.update_one(
        {"role": role},
        {
            "$set": {
                "role": role,
                "permissions": permissions,
                "updated_by": current_user.id,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        },
        upsert=True
    )
    
    return {"message": "Role permissions updated"}
