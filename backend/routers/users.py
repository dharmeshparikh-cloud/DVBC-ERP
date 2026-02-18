"""
Users Router - User Management, Roles, Team Management
"""

from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone
from typing import List, Optional
from pydantic import BaseModel

from .models import User, UserRole, DEFAULT_ROLES
from .deps import get_db, sanitize_text
from .auth import get_current_user, get_password_hash

router = APIRouter(tags=["Users"])


class ReportingManagerUpdate(BaseModel):
    reporting_manager_id: str


@router.get("/users")
async def get_users(
    role: Optional[str] = None,
    department: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get all users with optional filters."""
    db = get_db()
    
    query = {}
    if role:
        query["role"] = role
    if department:
        query["department"] = department
    
    users = await db.users.find(query, {"_id": 0, "hashed_password": 0}).to_list(1000)
    
    for user in users:
        if isinstance(user.get('created_at'), str):
            user['created_at'] = datetime.fromisoformat(user['created_at'])
    
    return users


@router.get("/users/{user_id}")
async def get_user(user_id: str, current_user: User = Depends(get_current_user)):
    """Get a single user by ID."""
    db = get_db()
    
    user = await db.users.find_one({"id": user_id}, {"_id": 0, "hashed_password": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if isinstance(user.get('created_at'), str):
        user['created_at'] = datetime.fromisoformat(user['created_at'])
    
    return user


@router.patch("/users/{user_id}/reporting-manager")
async def set_reporting_manager(
    user_id: str,
    data: ReportingManagerUpdate,
    current_user: User = Depends(get_current_user)
):
    """Set reporting manager for a user."""
    db = get_db()
    
    if current_user.role not in ["admin", "hr_manager"]:
        raise HTTPException(status_code=403, detail="Only admin or HR manager can set reporting managers")
    
    # Verify the user exists
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Verify the reporting manager exists
    manager = await db.users.find_one({"id": data.reporting_manager_id}, {"_id": 0})
    if not manager:
        raise HTTPException(status_code=404, detail="Reporting manager not found")
    
    # Prevent circular reporting
    if data.reporting_manager_id == user_id:
        raise HTTPException(status_code=400, detail="User cannot report to themselves")
    
    await db.users.update_one(
        {"id": user_id},
        {"$set": {"reporting_manager_id": data.reporting_manager_id}}
    )
    
    return {"message": "Reporting manager updated"}


@router.get("/my-team")
async def get_my_team(current_user: User = Depends(get_current_user)):
    """Get team members who report to the current user."""
    db = get_db()
    
    team_members = await db.users.find(
        {"reporting_manager_id": current_user.id},
        {"_id": 0, "hashed_password": 0}
    ).to_list(1000)
    
    for member in team_members:
        if isinstance(member.get('created_at'), str):
            member['created_at'] = datetime.fromisoformat(member['created_at'])
        
        # Get employee info if exists
        employee = await db.employees.find_one(
            {"user_id": member["id"]},
            {"_id": 0, "designation": 1, "department": 1, "date_of_joining": 1}
        )
        if employee:
            member["employee_info"] = employee
    
    return team_members


@router.get("/roles")
async def get_roles(current_user: User = Depends(get_current_user)):
    """Get all available roles."""
    db = get_db()
    
    # Get roles from database
    roles = await db.roles.find({}, {"_id": 0}).to_list(100)
    
    if not roles:
        # Return default roles if none in DB
        return DEFAULT_ROLES
    
    return roles


@router.post("/roles")
async def create_role(data: dict, current_user: User = Depends(get_current_user)):
    """Create a new role (admin only)."""
    db = get_db()
    
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can create roles")
    
    # Check if role already exists
    existing = await db.roles.find_one({"id": data.get("id")})
    if existing:
        raise HTTPException(status_code=400, detail="Role already exists")
    
    role_doc = {
        "id": data.get("id"),
        "name": sanitize_text(data.get("name", "")),
        "description": sanitize_text(data.get("description", "")),
        "is_system_role": False,
        "can_delete": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by": current_user.id
    }
    
    await db.roles.insert_one(role_doc)
    return role_doc


@router.delete("/roles/{role_id}")
async def delete_role(role_id: str, current_user: User = Depends(get_current_user)):
    """Delete a role (admin only, non-system roles)."""
    db = get_db()
    
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can delete roles")
    
    role = await db.roles.find_one({"id": role_id}, {"_id": 0})
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    
    if role.get("is_system_role") or not role.get("can_delete", True):
        raise HTTPException(status_code=400, detail="Cannot delete system role")
    
    # Check if any users have this role
    users_with_role = await db.users.count_documents({"role": role_id})
    if users_with_role > 0:
        raise HTTPException(status_code=400, detail=f"Cannot delete role. {users_with_role} users have this role.")
    
    await db.roles.delete_one({"id": role_id})
    return {"message": "Role deleted"}
