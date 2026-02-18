"""
Role Management Router - Role Creation, Assignment, and Level-based Permissions
"""

from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone
from typing import Optional, List
import uuid

from .models import User
from .deps import get_db, sanitize_text
from .auth import get_current_user

router = APIRouter(prefix="/role-management", tags=["Role Management"])


# ==================== EMPLOYEE LEVELS ====================
# Level Hierarchy: Executive < Manager < Leader
# - Executive: Stand-alone user (no reportees)
# - Manager: Has direct reportees
# - Leader: Manager's manager (has managers reporting to them)

EMPLOYEE_LEVELS = {
    "executive": {
        "name": "Executive",
        "description": "Stand-alone user from any department without reportees",
        "hierarchy": 1,
        "default_permissions": {
            "sales": ["leads.read", "leads.create", "meetings.create", "meetings.read"],
            "consulting": ["projects.read", "tasks.read", "tasks.update", "timesheets.create"],
            "hr": ["attendance.read", "leaves.create", "expenses.create"],
            "finance": [],
            "admin": []
        }
    },
    "manager": {
        "name": "Manager",
        "description": "Reporting manager with direct reportees under them",
        "hierarchy": 2,
        "default_permissions": {
            "sales": ["leads.read", "leads.create", "leads.update", "leads.assign", "meetings.create", "meetings.read", "meetings.update"],
            "consulting": ["projects.read", "projects.update", "tasks.read", "tasks.create", "tasks.assign", "timesheets.create", "timesheets.approve"],
            "hr": ["attendance.read", "attendance.approve", "leaves.create", "leaves.approve", "expenses.create", "expenses.approve"],
            "finance": ["reports.view"],
            "admin": []
        }
    },
    "leader": {
        "name": "Leader",
        "description": "Senior leader - reporting manager's reporting manager",
        "hierarchy": 3,
        "default_permissions": {
            "sales": ["leads.read", "leads.create", "leads.update", "leads.delete", "leads.assign", "leads.export", 
                     "meetings.create", "meetings.read", "meetings.update", "meetings.delete",
                     "sow.read", "sow.create", "sow.update", "agreements.read", "agreements.approve"],
            "consulting": ["projects.read", "projects.create", "projects.update", "projects.assign_team",
                          "tasks.read", "tasks.create", "tasks.update", "tasks.delete", "tasks.assign",
                          "timesheets.create", "timesheets.approve", "deliverables.read", "deliverables.approve"],
            "hr": ["employees.read", "attendance.read", "attendance.approve", "leaves.create", "leaves.approve", 
                   "expenses.create", "expenses.approve", "payroll.read"],
            "finance": ["reports.view", "reports.export"],
            "admin": ["audit_logs.read"]
        }
    }
}


@router.get("/levels")
async def get_employee_levels(current_user: User = Depends(get_current_user)):
    """Get all employee levels with their default permissions."""
    return EMPLOYEE_LEVELS


@router.get("/levels/{level_id}")
async def get_employee_level(level_id: str, current_user: User = Depends(get_current_user)):
    """Get a specific employee level details."""
    if level_id not in EMPLOYEE_LEVELS:
        raise HTTPException(status_code=404, detail="Level not found")
    return {level_id: EMPLOYEE_LEVELS[level_id]}


# ==================== ROLE CREATION WITH APPROVAL ====================

@router.post("/roles/request")
async def request_role_creation(data: dict, current_user: User = Depends(get_current_user)):
    """
    HR requests creation of a new role - requires Admin approval.
    
    Flow:
    1. HR creates role request with name, description, base_level, permissions
    2. Request goes to pending state
    3. Admin reviews and approves/rejects
    4. If approved, role is created and available for assignment
    """
    db = get_db()
    
    if current_user.role not in ["admin", "hr_manager"]:
        raise HTTPException(status_code=403, detail="Only Admin/HR Manager can request role creation")
    
    role_id = data.get("id", "").lower().replace(" ", "_")
    role_name = sanitize_text(data.get("name", ""))
    description = sanitize_text(data.get("description", ""))
    base_level = data.get("base_level", "executive")
    custom_permissions = data.get("permissions", {})
    
    if not role_id or not role_name:
        raise HTTPException(status_code=400, detail="Role ID and name are required")
    
    # Check if role already exists
    existing_role = await db.roles.find_one({"id": role_id})
    if existing_role:
        raise HTTPException(status_code=400, detail="Role with this ID already exists")
    
    # Check if there's already a pending request for this role
    existing_request = await db.role_creation_requests.find_one({
        "role_id": role_id,
        "status": "pending"
    })
    if existing_request:
        raise HTTPException(status_code=400, detail="There's already a pending request for this role")
    
    # Get default permissions from base level
    base_permissions = EMPLOYEE_LEVELS.get(base_level, {}).get("default_permissions", {})
    
    # Merge base permissions with custom permissions
    final_permissions = {**base_permissions}
    for module, perms in custom_permissions.items():
        if module in final_permissions:
            final_permissions[module] = list(set(final_permissions[module] + perms))
        else:
            final_permissions[module] = perms
    
    request_doc = {
        "id": str(uuid.uuid4()),
        "role_id": role_id,
        "role_name": role_name,
        "description": description,
        "base_level": base_level,
        "permissions": final_permissions,
        "status": "pending",  # pending, approved, rejected
        "requested_by": current_user.id,
        "requested_by_name": current_user.full_name,
        "requested_at": datetime.now(timezone.utc).isoformat(),
        "reviewed_by": None,
        "reviewed_at": None,
        "review_comments": None
    }
    
    await db.role_creation_requests.insert_one(request_doc)
    
    # If admin is creating, auto-approve
    if current_user.role == "admin":
        return await approve_role_creation(request_doc["id"], {"comments": "Auto-approved by admin"}, current_user)
    
    # Notify admins
    admins = await db.users.find({"role": "admin"}, {"_id": 0, "id": 1}).to_list(50)
    for admin in admins:
        notification = {
            "id": str(uuid.uuid4()),
            "user_id": admin["id"],
            "type": "role_creation_request",
            "title": "New Role Creation Request",
            "message": f"{current_user.full_name} requested to create role: {role_name}",
            "reference_type": "role_creation_request",
            "reference_id": request_doc["id"],
            "is_read": False,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.notifications.insert_one(notification)
    
    return {
        "message": "Role creation request submitted for admin approval",
        "request_id": request_doc["id"],
        "status": "pending"
    }


@router.get("/roles/pending-requests")
async def get_pending_role_requests(current_user: User = Depends(get_current_user)):
    """Get all pending role creation requests (Admin only)."""
    db = get_db()
    
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only Admin can view pending role requests")
    
    requests = await db.role_creation_requests.find(
        {"status": "pending"},
        {"_id": 0}
    ).sort("requested_at", -1).to_list(100)
    
    return requests


@router.post("/roles/request/{request_id}/approve")
async def approve_role_creation(request_id: str, data: dict, current_user: User = Depends(get_current_user)):
    """Admin approves role creation request."""
    db = get_db()
    
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only Admin can approve role creation")
    
    request_doc = await db.role_creation_requests.find_one({"id": request_id}, {"_id": 0})
    if not request_doc:
        raise HTTPException(status_code=404, detail="Request not found")
    
    if request_doc["status"] != "pending":
        raise HTTPException(status_code=400, detail=f"Request is already {request_doc['status']}")
    
    # Create the role
    new_role = {
        "id": request_doc["role_id"],
        "name": request_doc["role_name"],
        "description": request_doc["description"],
        "base_level": request_doc["base_level"],
        "permissions": request_doc["permissions"],
        "is_system_role": False,
        "can_delete": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by": request_doc["requested_by"],
        "approved_by": current_user.id
    }
    
    await db.roles.insert_one(new_role)
    
    # Update request status
    await db.role_creation_requests.update_one(
        {"id": request_id},
        {"$set": {
            "status": "approved",
            "reviewed_by": current_user.id,
            "reviewed_by_name": current_user.full_name,
            "reviewed_at": datetime.now(timezone.utc).isoformat(),
            "review_comments": data.get("comments", "")
        }}
    )
    
    # Notify requester
    notification = {
        "id": str(uuid.uuid4()),
        "user_id": request_doc["requested_by"],
        "type": "role_creation_approved",
        "title": "Role Creation Approved",
        "message": f"Your role creation request for '{request_doc['role_name']}' has been approved",
        "reference_type": "role",
        "reference_id": request_doc["role_id"],
        "is_read": False,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.notifications.insert_one(notification)
    
    return {
        "message": "Role created successfully",
        "role_id": request_doc["role_id"]
    }


@router.post("/roles/request/{request_id}/reject")
async def reject_role_creation(request_id: str, data: dict, current_user: User = Depends(get_current_user)):
    """Admin rejects role creation request."""
    db = get_db()
    
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only Admin can reject role creation")
    
    request_doc = await db.role_creation_requests.find_one({"id": request_id}, {"_id": 0})
    if not request_doc:
        raise HTTPException(status_code=404, detail="Request not found")
    
    rejection_reason = data.get("reason", "")
    if not rejection_reason:
        raise HTTPException(status_code=400, detail="Rejection reason is required")
    
    await db.role_creation_requests.update_one(
        {"id": request_id},
        {"$set": {
            "status": "rejected",
            "reviewed_by": current_user.id,
            "reviewed_by_name": current_user.full_name,
            "reviewed_at": datetime.now(timezone.utc).isoformat(),
            "review_comments": rejection_reason
        }}
    )
    
    # Notify requester
    notification = {
        "id": str(uuid.uuid4()),
        "user_id": request_doc["requested_by"],
        "type": "role_creation_rejected",
        "title": "Role Creation Rejected",
        "message": f"Your role creation request for '{request_doc['role_name']}' was rejected. Reason: {rejection_reason}",
        "reference_type": "role_creation_request",
        "reference_id": request_id,
        "is_read": False,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.notifications.insert_one(notification)
    
    return {"message": "Role creation request rejected"}


# ==================== ROLE ASSIGNMENT WITH APPROVAL ====================

@router.post("/assign-role")
async def request_role_assignment(data: dict, current_user: User = Depends(get_current_user)):
    """
    HR assigns role to employee - requires Admin approval.
    
    Flow:
    1. HR selects employee, role, and level during onboarding or later
    2. Request goes to pending state
    3. Admin reviews and approves/rejects
    4. If approved:
       - Employee's role and level are updated
       - User account (if exists) is updated with new role
       - Pre-approved permissions based on level are applied
    """
    db = get_db()
    
    if current_user.role not in ["admin", "hr_manager", "hr_executive"]:
        raise HTTPException(status_code=403, detail="Only HR can assign roles")
    
    employee_id = data.get("employee_id")
    role_id = data.get("role_id")
    level = data.get("level", "executive")
    custom_permissions = data.get("custom_permissions", {})
    notes = sanitize_text(data.get("notes", ""))
    
    if not employee_id or not role_id:
        raise HTTPException(status_code=400, detail="Employee ID and Role ID are required")
    
    # Validate employee exists
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Validate role exists
    role = await db.roles.find_one({"id": role_id}, {"_id": 0})
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    
    # Validate level
    if level not in EMPLOYEE_LEVELS:
        raise HTTPException(status_code=400, detail="Invalid employee level")
    
    # Check for existing pending request
    existing_request = await db.role_assignment_requests.find_one({
        "employee_id": employee_id,
        "status": "pending"
    })
    if existing_request:
        raise HTTPException(status_code=400, detail="There's already a pending role assignment for this employee")
    
    # Get base permissions from level
    level_permissions = EMPLOYEE_LEVELS[level]["default_permissions"]
    
    # Merge with role permissions and custom permissions
    final_permissions = {**level_permissions}
    if role.get("permissions"):
        for module, perms in role["permissions"].items():
            if module in final_permissions:
                final_permissions[module] = list(set(final_permissions[module] + perms))
            else:
                final_permissions[module] = perms
    
    for module, perms in custom_permissions.items():
        if module in final_permissions:
            final_permissions[module] = list(set(final_permissions[module] + perms))
        else:
            final_permissions[module] = perms
    
    request_doc = {
        "id": str(uuid.uuid4()),
        "employee_id": employee_id,
        "employee_name": f"{employee.get('first_name', '')} {employee.get('last_name', '')}".strip(),
        "employee_email": employee.get("email") or employee.get("work_email"),
        "current_role": employee.get("role"),
        "current_level": employee.get("level"),
        "requested_role": role_id,
        "requested_role_name": role.get("name", role_id),
        "requested_level": level,
        "requested_level_name": EMPLOYEE_LEVELS[level]["name"],
        "permissions": final_permissions,
        "custom_permissions": custom_permissions,
        "notes": notes,
        "status": "pending",
        "requested_by": current_user.id,
        "requested_by_name": current_user.full_name,
        "requested_at": datetime.now(timezone.utc).isoformat(),
        "reviewed_by": None,
        "reviewed_at": None,
        "review_comments": None
    }
    
    await db.role_assignment_requests.insert_one(request_doc)
    
    # If admin is assigning, auto-approve
    if current_user.role == "admin":
        return await approve_role_assignment(request_doc["id"], {"comments": "Auto-approved by admin"}, current_user)
    
    # Notify admins
    admins = await db.users.find({"role": "admin"}, {"_id": 0, "id": 1}).to_list(50)
    for admin in admins:
        notification = {
            "id": str(uuid.uuid4()),
            "user_id": admin["id"],
            "type": "role_assignment_request",
            "title": "Role Assignment Request",
            "message": f"{current_user.full_name} requested to assign {role.get('name')} ({EMPLOYEE_LEVELS[level]['name']}) to {request_doc['employee_name']}",
            "reference_type": "role_assignment_request",
            "reference_id": request_doc["id"],
            "is_read": False,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.notifications.insert_one(notification)
    
    return {
        "message": "Role assignment request submitted for admin approval",
        "request_id": request_doc["id"],
        "status": "pending"
    }


@router.get("/assign-role/pending")
async def get_pending_role_assignments(current_user: User = Depends(get_current_user)):
    """Get all pending role assignment requests."""
    db = get_db()
    
    if current_user.role not in ["admin", "hr_manager"]:
        raise HTTPException(status_code=403, detail="Only Admin/HR Manager can view pending assignments")
    
    requests = await db.role_assignment_requests.find(
        {"status": "pending"},
        {"_id": 0}
    ).sort("requested_at", -1).to_list(100)
    
    return requests


@router.post("/assign-role/{request_id}/approve")
async def approve_role_assignment(request_id: str, data: dict, current_user: User = Depends(get_current_user)):
    """Admin approves role assignment request."""
    db = get_db()
    
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only Admin can approve role assignments")
    
    request_doc = await db.role_assignment_requests.find_one({"id": request_id}, {"_id": 0})
    if not request_doc:
        raise HTTPException(status_code=404, detail="Request not found")
    
    if request_doc["status"] != "pending":
        raise HTTPException(status_code=400, detail=f"Request is already {request_doc['status']}")
    
    # Update employee
    await db.employees.update_one(
        {"id": request_doc["employee_id"]},
        {"$set": {
            "role": request_doc["requested_role"],
            "level": request_doc["requested_level"],
            "permissions": request_doc["permissions"],
            "role_updated_at": datetime.now(timezone.utc).isoformat(),
            "role_updated_by": current_user.id
        }}
    )
    
    # Update user account if exists
    employee = await db.employees.find_one({"id": request_doc["employee_id"]}, {"_id": 0})
    if employee and employee.get("user_id"):
        await db.users.update_one(
            {"id": employee["user_id"]},
            {"$set": {
                "role": request_doc["requested_role"],
                "level": request_doc["requested_level"],
                "permissions": request_doc["permissions"]
            }}
        )
    
    # Update request status
    await db.role_assignment_requests.update_one(
        {"id": request_id},
        {"$set": {
            "status": "approved",
            "reviewed_by": current_user.id,
            "reviewed_by_name": current_user.full_name,
            "reviewed_at": datetime.now(timezone.utc).isoformat(),
            "review_comments": data.get("comments", "")
        }}
    )
    
    # Notify requester
    notification = {
        "id": str(uuid.uuid4()),
        "user_id": request_doc["requested_by"],
        "type": "role_assignment_approved",
        "title": "Role Assignment Approved",
        "message": f"Role assignment for {request_doc['employee_name']} has been approved",
        "reference_type": "employee",
        "reference_id": request_doc["employee_id"],
        "is_read": False,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.notifications.insert_one(notification)
    
    return {
        "message": "Role assignment approved and applied",
        "employee_id": request_doc["employee_id"]
    }


@router.post("/assign-role/{request_id}/reject")
async def reject_role_assignment(request_id: str, data: dict, current_user: User = Depends(get_current_user)):
    """Admin rejects role assignment request."""
    db = get_db()
    
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only Admin can reject role assignments")
    
    request_doc = await db.role_assignment_requests.find_one({"id": request_id}, {"_id": 0})
    if not request_doc:
        raise HTTPException(status_code=404, detail="Request not found")
    
    rejection_reason = data.get("reason", "")
    if not rejection_reason:
        raise HTTPException(status_code=400, detail="Rejection reason is required")
    
    await db.role_assignment_requests.update_one(
        {"id": request_id},
        {"$set": {
            "status": "rejected",
            "reviewed_by": current_user.id,
            "reviewed_by_name": current_user.full_name,
            "reviewed_at": datetime.now(timezone.utc).isoformat(),
            "review_comments": rejection_reason
        }}
    )
    
    # Notify requester
    notification = {
        "id": str(uuid.uuid4()),
        "user_id": request_doc["requested_by"],
        "type": "role_assignment_rejected",
        "title": "Role Assignment Rejected",
        "message": f"Role assignment for {request_doc['employee_name']} was rejected. Reason: {rejection_reason}",
        "reference_type": "role_assignment_request",
        "reference_id": request_id,
        "is_read": False,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.notifications.insert_one(notification)
    
    return {"message": "Role assignment request rejected"}


# ==================== EMPLOYEE LEVEL MANAGEMENT ====================

@router.patch("/employee/{employee_id}/level")
async def update_employee_level(employee_id: str, data: dict, current_user: User = Depends(get_current_user)):
    """Update employee's level (HR/Admin only)."""
    db = get_db()
    
    if current_user.role not in ["admin", "hr_manager"]:
        raise HTTPException(status_code=403, detail="Only Admin/HR Manager can update employee level")
    
    new_level = data.get("level")
    if new_level not in EMPLOYEE_LEVELS:
        raise HTTPException(status_code=400, detail="Invalid level")
    
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Get new level's default permissions
    level_permissions = EMPLOYEE_LEVELS[new_level]["default_permissions"]
    
    # Merge with existing custom permissions
    existing_permissions = employee.get("permissions", {})
    final_permissions = {**level_permissions}
    for module, perms in existing_permissions.items():
        if module in final_permissions:
            # Keep custom permissions that were added beyond level defaults
            custom_perms = [p for p in perms if p not in level_permissions.get(module, [])]
            final_permissions[module] = list(set(final_permissions[module] + custom_perms))
    
    await db.employees.update_one(
        {"id": employee_id},
        {"$set": {
            "level": new_level,
            "permissions": final_permissions,
            "level_updated_at": datetime.now(timezone.utc).isoformat(),
            "level_updated_by": current_user.id
        }}
    )
    
    # Update user if exists
    if employee.get("user_id"):
        await db.users.update_one(
            {"id": employee["user_id"]},
            {"$set": {"level": new_level, "permissions": final_permissions}}
        )
    
    return {
        "message": "Employee level updated",
        "new_level": new_level,
        "permissions": final_permissions
    }


@router.get("/employee/{employee_id}/permissions")
async def get_employee_permissions(employee_id: str, current_user: User = Depends(get_current_user)):
    """Get employee's current permissions."""
    db = get_db()
    
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    level = employee.get("level", "executive")
    level_info = EMPLOYEE_LEVELS.get(level, EMPLOYEE_LEVELS["executive"])
    
    return {
        "employee_id": employee_id,
        "employee_name": f"{employee.get('first_name', '')} {employee.get('last_name', '')}".strip(),
        "role": employee.get("role"),
        "level": level,
        "level_name": level_info["name"],
        "level_description": level_info["description"],
        "permissions": employee.get("permissions", level_info["default_permissions"])
    }


@router.patch("/employee/{employee_id}/permissions")
async def update_employee_permissions(employee_id: str, data: dict, current_user: User = Depends(get_current_user)):
    """Update employee's permissions (HR/Admin can customize)."""
    db = get_db()
    
    if current_user.role not in ["admin", "hr_manager"]:
        raise HTTPException(status_code=403, detail="Only Admin/HR Manager can update permissions")
    
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    new_permissions = data.get("permissions", {})
    
    await db.employees.update_one(
        {"id": employee_id},
        {"$set": {
            "permissions": new_permissions,
            "permissions_updated_at": datetime.now(timezone.utc).isoformat(),
            "permissions_updated_by": current_user.id
        }}
    )
    
    # Update user if exists
    if employee.get("user_id"):
        await db.users.update_one(
            {"id": employee["user_id"]},
            {"$set": {"permissions": new_permissions}}
        )
    
    return {"message": "Employee permissions updated", "permissions": new_permissions}


# ==================== AUTO-DETECT LEVEL ====================

@router.get("/employee/{employee_id}/detect-level")
async def detect_employee_level(employee_id: str, current_user: User = Depends(get_current_user)):
    """
    Auto-detect employee level based on reporting structure.
    
    Logic:
    - If employee has no reportees → Executive
    - If employee has direct reportees who are NOT managers → Manager  
    - If employee has direct reportees who ARE managers → Leader
    """
    db = get_db()
    
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Get direct reportees
    direct_reportees = await db.employees.find(
        {"reporting_manager_id": employee_id},
        {"_id": 0, "id": 1, "first_name": 1, "last_name": 1}
    ).to_list(100)
    
    if not direct_reportees:
        detected_level = "executive"
        reason = "No direct reportees found"
    else:
        # Check if any reportee has their own reportees (making them a manager)
        has_manager_reportees = False
        for reportee in direct_reportees:
            sub_reportees = await db.employees.count_documents({"reporting_manager_id": reportee["id"]})
            if sub_reportees > 0:
                has_manager_reportees = True
                break
        
        if has_manager_reportees:
            detected_level = "leader"
            reason = f"Has {len(direct_reportees)} direct reportees, some of whom have their own teams"
        else:
            detected_level = "manager"
            reason = f"Has {len(direct_reportees)} direct reportees (individual contributors)"
    
    return {
        "employee_id": employee_id,
        "employee_name": f"{employee.get('first_name', '')} {employee.get('last_name', '')}".strip(),
        "current_level": employee.get("level"),
        "detected_level": detected_level,
        "detection_reason": reason,
        "direct_reportee_count": len(direct_reportees)
    }
