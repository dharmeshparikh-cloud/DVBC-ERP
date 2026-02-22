"""
Role Management Router - Employee Levels, Role Creation/Assignment Approval Workflow
"""

from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
import uuid

from .models import User, UserRole
from .deps import get_db, sanitize_text, HR_ADMIN_ROLES
from .auth import get_current_user

router = APIRouter(prefix="/role-management", tags=["Role Management"])


# ============== Employee Levels ==============

class EmployeeLevel:
    """Employee hierarchy levels with predefined permission sets."""
    EXECUTIVE = "executive"     # Entry level - basic permissions
    MANAGER = "manager"         # Mid level - team management permissions  
    LEADER = "leader"           # Senior level - strategic permissions


# Default permission sets for each level (customizable by admin)
DEFAULT_LEVEL_PERMISSIONS = {
    "executive": {
        "can_view_own_data": True,
        "can_edit_own_profile": True,
        "can_submit_requests": True,
        "can_view_team_data": False,
        "can_approve_requests": False,
        "can_manage_team": False,
        "can_access_reports": False,
        "can_access_financials": False,
        "can_create_projects": False,
        "can_assign_tasks": False,
    },
    "manager": {
        "can_view_own_data": True,
        "can_edit_own_profile": True,
        "can_submit_requests": True,
        "can_view_team_data": True,
        "can_approve_requests": True,
        "can_manage_team": True,
        "can_access_reports": True,
        "can_access_financials": False,
        "can_create_projects": True,
        "can_assign_tasks": True,
    },
    "leader": {
        "can_view_own_data": True,
        "can_edit_own_profile": True,
        "can_submit_requests": True,
        "can_view_team_data": True,
        "can_approve_requests": True,
        "can_manage_team": True,
        "can_access_reports": True,
        "can_access_financials": True,
        "can_create_projects": True,
        "can_assign_tasks": True,
    }
}


# ============== Pydantic Models ==============

class LevelPermissionsUpdate(BaseModel):
    """Model for updating level permissions."""
    level: str
    permissions: Dict[str, bool]


class RoleCreationRequest(BaseModel):
    """Model for creating a new role request."""
    role_id: str
    role_name: str
    role_description: Optional[str] = None
    permissions: Optional[Dict[str, bool]] = None
    reason: Optional[str] = None


class RoleAssignmentRequest(BaseModel):
    """Model for requesting role assignment to an employee."""
    employee_id: str
    role_id: str
    level: str
    reason: Optional[str] = None


class RequestApproval(BaseModel):
    """Model for approving/rejecting a request."""
    approved: bool
    comments: Optional[str] = None


# ============== Level Management Endpoints ==============

@router.get("/levels")
async def get_employee_levels(current_user: User = Depends(get_current_user)):
    """Get available employee levels."""
    return {
        "levels": [
            {"id": "executive", "name": "Executive", "description": "Entry level - basic permissions"},
            {"id": "manager", "name": "Manager", "description": "Mid level - team management permissions"},
            {"id": "leader", "name": "Leader", "description": "Senior level - strategic permissions"},
        ]
    }


@router.get("/level-permissions")
async def get_level_permissions(current_user: User = Depends(get_current_user)):
    """Get permission configurations for all levels."""
    db = get_db()
    
    # Try to get custom configurations from DB
    config = await db.level_permissions_config.find_one({"id": "main"}, {"_id": 0})
    
    if config:
        return config.get("permissions", DEFAULT_LEVEL_PERMISSIONS)
    
    return DEFAULT_LEVEL_PERMISSIONS


@router.get("/level-permissions/{level}")
async def get_level_permission(level: str, current_user: User = Depends(get_current_user)):
    """Get permission configuration for a specific level."""
    db = get_db()
    
    if level not in ["executive", "manager", "leader"]:
        raise HTTPException(status_code=400, detail="Invalid level")
    
    config = await db.level_permissions_config.find_one({"id": "main"}, {"_id": 0})
    
    if config and level in config.get("permissions", {}):
        return {"level": level, "permissions": config["permissions"][level]}
    
    return {"level": level, "permissions": DEFAULT_LEVEL_PERMISSIONS.get(level, {})}


@router.put("/level-permissions")
async def update_level_permissions(
    data: LevelPermissionsUpdate,
    current_user: User = Depends(get_current_user)
):
    """Update permission configuration for a level (Admin only)."""
    db = get_db()
    
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can update level permissions")
    
    if data.level not in ["executive", "manager", "leader"]:
        raise HTTPException(status_code=400, detail="Invalid level")
    
    # Get or create config
    config = await db.level_permissions_config.find_one({"id": "main"}, {"_id": 0})
    
    if not config:
        config = {
            "id": "main",
            "permissions": DEFAULT_LEVEL_PERMISSIONS.copy(),
            "created_at": datetime.now(timezone.utc).isoformat()
        }
    
    # Update the specific level
    config["permissions"][data.level] = data.permissions
    config["updated_at"] = datetime.now(timezone.utc).isoformat()
    config["updated_by"] = current_user.id
    
    await db.level_permissions_config.update_one(
        {"id": "main"},
        {"$set": config},
        upsert=True
    )
    
    return {"message": "Level permissions updated", "level": data.level}


@router.get("/my-permissions")
async def get_my_permissions(current_user: User = Depends(get_current_user)):
    """Get the current user's permissions based on their employee level."""
    db = get_db()
    
    # Get user's employee record to find their level
    employee = await db.employees.find_one({"user_id": current_user.id}, {"_id": 0, "level": 1})
    
    if not employee:
        # Fallback to user role-based permissions for non-employees (admin, hr_manager, etc.)
        if current_user.role in HR_ADMIN_ROLES:
            return {
                "level": "leader",
                "role": current_user.role,
                "permissions": {
                    "can_view_own_data": True,
                    "can_edit_own_profile": True,
                    "can_submit_requests": True,
                    "can_view_team_data": True,
                    "can_approve_requests": True,
                    "can_view_reports": True,
                    "can_manage_team": True
                }
            }
        return {
            "level": "executive",
            "role": current_user.role,
            "permissions": DEFAULT_LEVEL_PERMISSIONS.get("executive", {})
        }
    
    level = employee.get("level", "executive")
    
    # Get custom permissions if they exist
    config = await db.level_permissions_config.find_one({"id": "main"}, {"_id": 0})
    
    if config and level in config.get("permissions", {}):
        permissions = config["permissions"][level]
    else:
        permissions = DEFAULT_LEVEL_PERMISSIONS.get(level, {})
    
    return {
        "level": level,
        "role": current_user.role,
        "permissions": permissions
    }


# ============== Role Creation Request Endpoints ==============

@router.post("/role-requests")
async def create_role_request(
    request: RoleCreationRequest,
    current_user: User = Depends(get_current_user)
):
    """HR creates a request to add a new role (requires Admin approval)."""
    db = get_db()
    
    if current_user.role not in ["hr_manager", "hr_executive"]:
        raise HTTPException(status_code=403, detail="Only HR can create role requests")
    
    # Check if role already exists
    existing_role = await db.roles.find_one({"id": request.role_id})
    if existing_role:
        raise HTTPException(status_code=400, detail="Role with this ID already exists")
    
    # Check for pending request with same role_id
    pending = await db.role_requests.find_one({
        "role_id": request.role_id,
        "request_type": "create_role",
        "status": "pending"
    })
    if pending:
        raise HTTPException(status_code=400, detail="A pending request for this role already exists")
    
    role_request = {
        "id": str(uuid.uuid4()),
        "request_type": "create_role",
        "role_id": request.role_id,
        "role_name": sanitize_text(request.role_name),
        "role_description": sanitize_text(request.role_description) if request.role_description else "",
        "permissions": request.permissions or {},
        "reason": sanitize_text(request.reason) if request.reason else "",
        "status": "pending",
        "submitted_by": current_user.id,
        "submitted_by_name": current_user.full_name,
        "submitted_at": datetime.now(timezone.utc).isoformat(),
        "reviewed_by": None,
        "reviewed_at": None,
        "review_comments": None
    }
    
    await db.role_requests.insert_one(role_request)
    
    # Create notification for admins
    admins = await db.users.find({"role": "admin"}, {"_id": 0, "id": 1, "email": 1}).to_list(100)
    for admin in admins:
        notification = {
            "id": str(uuid.uuid4()),
            "type": "role_request_pending",
            "recipient_id": admin["id"],
            "title": "New Role Creation Request",
            "message": f"{current_user.full_name} has requested to create a new role: {request.role_name}",
            "request_id": role_request["id"],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "read": False
        }
        await db.notifications.insert_one(notification)
    
    return {"message": "Role creation request submitted", "request_id": role_request["id"]}


@router.get("/role-requests")
async def get_role_requests(
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get role requests (Admin sees all, HR sees own requests)."""
    db = get_db()
    
    query = {}
    
    if current_user.role == "admin":
        # Admin sees all
        if status:
            query["status"] = status
    elif current_user.role in ["hr_manager", "hr_executive"]:
        # HR sees their own requests
        query["submitted_by"] = current_user.id
        if status:
            query["status"] = status
    else:
        raise HTTPException(status_code=403, detail="Not authorized to view role requests")
    
    requests = await db.role_requests.find(query, {"_id": 0}).sort("submitted_at", -1).to_list(500)
    return requests


@router.get("/role-requests/pending")
async def get_pending_role_requests(current_user: User = Depends(get_current_user)):
    """Get pending role requests for admin approval."""
    db = get_db()
    
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can view pending requests")
    
    requests = await db.role_requests.find(
        {"status": "pending"},
        {"_id": 0}
    ).sort("submitted_at", -1).to_list(100)
    
    return requests


@router.post("/role-requests/{request_id}/approve")
async def approve_role_request(
    request_id: str,
    approval: RequestApproval,
    current_user: User = Depends(get_current_user)
):
    """Admin approves or rejects a role creation request."""
    db = get_db()
    
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can approve role requests")
    
    request = await db.role_requests.find_one({"id": request_id}, {"_id": 0})
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")
    
    if request["status"] != "pending":
        raise HTTPException(status_code=400, detail="Request already processed")
    
    new_status = "approved" if approval.approved else "rejected"
    
    # Update request status
    await db.role_requests.update_one(
        {"id": request_id},
        {"$set": {
            "status": new_status,
            "reviewed_by": current_user.id,
            "reviewed_by_name": current_user.full_name,
            "reviewed_at": datetime.now(timezone.utc).isoformat(),
            "review_comments": approval.comments
        }}
    )
    
    if approval.approved and request["request_type"] == "create_role":
        # Create the role
        new_role = {
            "id": request["role_id"],
            "name": request["role_name"],
            "description": request["role_description"],
            "permissions": request.get("permissions", {}),
            "is_system_role": False,
            "can_delete": True,
            "created_by": request["submitted_by"],
            "approved_by": current_user.id,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.roles.insert_one(new_role)
    
    elif approval.approved and request["request_type"] == "assign_role":
        # Update employee role and level
        await db.employees.update_one(
            {"id": request["employee_id"]},
            {"$set": {
                "role": request["role_id"],
                "level": request.get("level", "executive"),
                "role_updated_at": datetime.now(timezone.utc).isoformat(),
                "role_updated_by": current_user.id
            }}
        )
        
        # Also update user if linked
        employee = await db.employees.find_one({"id": request["employee_id"]}, {"_id": 0})
        if employee and employee.get("user_id"):
            await db.users.update_one(
                {"id": employee["user_id"]},
                {"$set": {"role": request["role_id"]}}
            )
    
    # Notify the requester
    notification = {
        "id": str(uuid.uuid4()),
        "type": "role_request_" + new_status,
        "recipient_id": request["submitted_by"],
        "title": f"Role Request {new_status.title()}",
        "message": f"Your role request has been {new_status}" + (f": {approval.comments}" if approval.comments else ""),
        "request_id": request_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "read": False
    }
    await db.notifications.insert_one(notification)
    
    return {"message": f"Request {new_status}", "request_id": request_id}


# ============== Role Assignment Request Endpoints ==============

@router.post("/assignment-requests")
async def create_role_assignment_request(
    request: RoleAssignmentRequest,
    current_user: User = Depends(get_current_user)
):
    """HR requests to assign a role and level to an employee (requires Admin approval)."""
    db = get_db()
    
    if current_user.role not in ["hr_manager", "hr_executive"]:
        raise HTTPException(status_code=403, detail="Only HR can create assignment requests")
    
    # Validate employee exists
    employee = await db.employees.find_one({"id": request.employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Validate role exists
    role = await db.roles.find_one({"id": request.role_id}, {"_id": 0})
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    
    # Validate level
    if request.level not in ["executive", "manager", "leader"]:
        raise HTTPException(status_code=400, detail="Invalid level")
    
    # Check for pending request for same employee
    pending = await db.role_requests.find_one({
        "employee_id": request.employee_id,
        "request_type": "assign_role",
        "status": "pending"
    })
    if pending:
        raise HTTPException(status_code=400, detail="A pending assignment request for this employee already exists")
    
    assignment_request = {
        "id": str(uuid.uuid4()),
        "request_type": "assign_role",
        "employee_id": request.employee_id,
        "employee_name": f"{employee.get('first_name', '')} {employee.get('last_name', '')}".strip(),
        "employee_code": employee.get("employee_id", ""),
        "current_role": employee.get("role"),
        "current_level": employee.get("level"),
        "new_role_id": request.role_id,
        "new_role_name": role.get("name", request.role_id),
        "level": request.level,
        "reason": sanitize_text(request.reason) if request.reason else "",
        "status": "pending",
        "submitted_by": current_user.id,
        "submitted_by_name": current_user.full_name,
        "submitted_at": datetime.now(timezone.utc).isoformat(),
        "reviewed_by": None,
        "reviewed_at": None,
        "review_comments": None
    }
    
    await db.role_requests.insert_one(assignment_request)
    
    # Notify admins
    admins = await db.users.find({"role": "admin"}, {"_id": 0, "id": 1}).to_list(100)
    for admin in admins:
        notification = {
            "id": str(uuid.uuid4()),
            "type": "role_assignment_pending",
            "recipient_id": admin["id"],
            "title": "New Role Assignment Request",
            "message": f"{current_user.full_name} has requested to assign {role.get('name')} ({request.level}) to {assignment_request['employee_name']}",
            "request_id": assignment_request["id"],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "read": False
        }
        await db.notifications.insert_one(notification)
    
    return {"message": "Role assignment request submitted", "request_id": assignment_request["id"]}


# ============== Stats & Summary ==============

@router.get("/stats")
async def get_role_management_stats(current_user: User = Depends(get_current_user)):
    """Get statistics for role management dashboard."""
    db = get_db()
    
    if current_user.role not in HR_ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Count requests by status
    pending_count = await db.role_requests.count_documents({"status": "pending"})
    approved_count = await db.role_requests.count_documents({"status": "approved"})
    rejected_count = await db.role_requests.count_documents({"status": "rejected"})
    
    # Count employees by level
    level_counts = {
        "executive": await db.employees.count_documents({"level": "executive"}),
        "manager": await db.employees.count_documents({"level": "manager"}),
        "leader": await db.employees.count_documents({"level": "leader"}),
        "unassigned": await db.employees.count_documents({"$or": [{"level": None}, {"level": {"$exists": False}}]})
    }
    
    # Count custom roles
    total_roles = await db.roles.count_documents({})
    custom_roles = await db.roles.count_documents({"is_system_role": False})
    
    return {
        "requests": {
            "pending": pending_count,
            "approved": approved_count,
            "rejected": rejected_count
        },
        "employees_by_level": level_counts,
        "roles": {
            "total": total_roles,
            "custom": custom_roles
        }
    }
