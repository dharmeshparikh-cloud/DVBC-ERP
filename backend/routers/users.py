"""
Users Router - User Management, Roles, Team Management
"""

from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone
from typing import List, Optional
from pydantic import BaseModel

from .models import User, UserRole, DEFAULT_ROLES
from .deps import get_db, sanitize_text, HR_ADMIN_ROLES
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
    """Set reporting manager for a user.
    
    Note: reporting_manager_id is stored as employee_id code (e.g., "EMP110") for consistency.
    """
    db = get_db()
    
    if current_user.role not in HR_ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Only admin or HR manager can set reporting managers")
    
    # Get the employee record for this user
    employee = await db.employees.find_one({"user_id": user_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found for this user")
    
    # Prevent circular reporting
    if data.reporting_manager_id == user_id or data.reporting_manager_id == employee.get('employee_id'):
        raise HTTPException(status_code=400, detail="User cannot report to themselves")
    
    # Find the manager - could be passed as employee_id code or UUID
    manager_employee = await db.employees.find_one(
        {"$or": [
            {"employee_id": data.reporting_manager_id}, 
            {"id": data.reporting_manager_id}, 
            {"user_id": data.reporting_manager_id}
        ]},
        {"_id": 0, "employee_id": 1, "first_name": 1, "last_name": 1}
    )
    if not manager_employee:
        raise HTTPException(status_code=404, detail="Manager employee not found")
    
    # Always store as employee_id code for consistency
    manager_emp_code = manager_employee.get("employee_id")
    if not manager_emp_code:
        raise HTTPException(status_code=400, detail="Manager has no employee_id code")
    
    # Update the employee's reporting_manager_id with employee code
    await db.employees.update_one(
        {"user_id": user_id},
        {"$set": {"reporting_manager_id": manager_emp_code}}
    )
    
    return {
        "message": "Reporting manager updated",
        "reporting_manager_id": manager_emp_code,
        "reporting_manager_name": f"{manager_employee.get('first_name', '')} {manager_employee.get('last_name', '')}".strip()
    }


@router.get("/my-team")
async def get_my_team(current_user: User = Depends(get_current_user)):
    """Get team members who report to the current user.
    
    Uses employees collection with reporting_manager_id matching current user's employee_id code.
    """
    db = get_db()
    
    # Get current user's employee record to find their employee_id code
    current_employee = await db.employees.find_one({"user_id": current_user.id}, {"_id": 0, "id": 1, "employee_id": 1})
    if not current_employee:
        return []
    
    # Query employees who report to this user (by employee_id code or internal id)
    emp_id = current_employee.get("employee_id")
    emp_internal_id = current_employee.get("id")
    
    query = {"$or": []}
    if emp_id:
        query["$or"].append({"reporting_manager_id": emp_id})
    if emp_internal_id:
        query["$or"].append({"reporting_manager_id": emp_internal_id})
    
    if not query["$or"]:
        return []
    
    team_employees = await db.employees.find(query, {"_id": 0}).to_list(1000)
    
    # Enrich with user info
    team_members = []
    for emp in team_employees:
        member = {
            "employee_id": emp.get("employee_id"),
            "id": emp.get("id"),
            "user_id": emp.get("user_id"),
            "first_name": emp.get("first_name"),
            "last_name": emp.get("last_name"),
            "email": emp.get("email"),
            "department": emp.get("department"),
            "designation": emp.get("designation"),
            "role": emp.get("role"),
            "is_active": emp.get("is_active", True)
        }
        
        # Get user info if linked
        if emp.get("user_id"):
            user = await db.users.find_one({"id": emp["user_id"]}, {"_id": 0, "hashed_password": 0})
            if user:
                member["full_name"] = user.get("full_name")
                if isinstance(user.get('created_at'), str):
                    member['created_at'] = datetime.fromisoformat(user['created_at'])
        
        team_members.append(member)
    
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
