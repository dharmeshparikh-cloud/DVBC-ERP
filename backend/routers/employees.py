"""
Employees Router - Employee Management, Documents, Org Structure

PERFORMANCE OPTIMIZATION: December 2025
- Added pagination support
- Added caching for list endpoints
- Added WebSocket notifications for real-time updates
- Added profile photo upload support
"""

from fastapi import APIRouter, HTTPException, Depends, Query, UploadFile, File
from datetime import datetime, timezone
from typing import Optional, List
import uuid
import base64
import os

from .models import User, UserRole
from .deps import (
    get_db, HR_ROLES, HR_ADMIN_ROLES, ADMIN_ROLES, sanitize_text, 
    get_role_group, has_role, PaginationParams, paginate_response,
    DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
)
from .auth import get_current_user, get_password_hash

# Performance caching
import sys
sys.path.insert(0, '/app/backend')
from services.cache_service import cache, list_key, PerformanceCache
from services.redis_cache import redis_cache, CacheInvalidation
from services.websocket_manager import ws_manager, notify_employee_update, notify_dashboard_refresh
from services.employee_user_sync import sync_employee_to_user

router = APIRouter(prefix="/employees", tags=["Employees"])

# Profile photo settings
ALLOWED_PHOTO_TYPES = ["image/jpeg", "image/png", "image/webp"]
MAX_PHOTO_SIZE = 5 * 1024 * 1024  # 5MB for print quality passport photos


@router.get("")
async def get_employees(
    department: Optional[str] = None,
    status: Optional[str] = None,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE, description="Items per page"),
    current_user: User = Depends(get_current_user)
):
    """
    Get all employees with optional filters. HR and Admin only.
    
    Supports pagination:
    - page: Page number (default: 1)
    - page_size: Items per page (default: 100, max: 1000)
    """
    db = get_db()
    
    # RBAC Migration: Using database-driven role check
    hr_roles = get_role_group("HR_ROLES", fail_closed=True)
    if not hr_roles or not has_role(current_user.role, hr_roles):
        raise HTTPException(
            status_code=403, 
            detail="Access denied. HR or Admin role required."
        )
    
    query = {}
    if department:
        query["department"] = department
    if status:
        query["status"] = status
    
    # Create pagination params
    params = PaginationParams(page=page, page_size=page_size, sort_by="created_at")
    
    # Check cache for this query
    cache_key = list_key("employees", {"dept": department, "status": status, "page": page})
    cached = await cache.get(cache_key)
    if cached is not None:
        return cached
    
    # Get total count and paginated results
    total = await db.employees.count_documents(query)
    employees = await db.employees.find(
        query, 
        {"_id": 0}
    ).sort("created_at", -1).skip(params.skip).limit(params.page_size).to_list(params.page_size)
    
    result = paginate_response(employees, total, params)
    
    # Cache for 5 minutes
    await cache.set(cache_key, result, PerformanceCache.TTL_EMPLOYEE_LIST)
    
    return result


@router.get("/all")
async def get_all_employees(
    department: Optional[str] = None,
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """
    Get all employees without pagination (for dropdowns, etc).
    Limited to 1000 results. HR and Admin only.
    """
    db = get_db()
    
    hr_roles = get_role_group("HR_ROLES", fail_closed=True)
    if not hr_roles or not has_role(current_user.role, hr_roles):
        raise HTTPException(status_code=403, detail="Access denied. HR or Admin role required.")
    
    query = {}
    if department:
        query["department"] = department
    if status:
        query["status"] = status
    
    employees = await db.employees.find(query, {"_id": 0}).to_list(1000)
    return employees


@router.get("/consultants")
async def get_consultant_employees(current_user: User = Depends(get_current_user)):
    """Get employees with consultant roles."""
    db = get_db()
    
    consultant_roles = ["consultant", "lean_consultant", "lead_consultant", "senior_consultant", "principal_consultant"]
    
    consultants = await db.employees.find(
        {"role": {"$in": consultant_roles}},
        {"_id": 0}
    ).to_list(500)
    
    return consultants



@router.get("/reportees/{user_id}")
async def get_reportees(user_id: str, current_user: User = Depends(get_current_user)):
    """
    Get all employees who report to a given user (direct and indirect reportees).
    Used for hierarchical data access in My Projects, Leads, etc.
    """
    db = get_db()
    
    # Get direct reportees
    direct_reportees = await db.employees.find(
        {"reporting_to": user_id},
        {"_id": 0, "id": 1, "user_id": 1, "employee_id": 1, "full_name": 1, "role": 1}
    ).to_list(500)
    
    # For a more complete hierarchy, get indirect reportees too
    all_reportees = list(direct_reportees)
    reportee_ids = [r.get("user_id") or r.get("id") for r in direct_reportees]
    
    # Get second level reportees (employees reporting to direct reportees)
    if reportee_ids:
        indirect_reportees = await db.employees.find(
            {"reporting_to": {"$in": reportee_ids}},
            {"_id": 0, "id": 1, "user_id": 1, "employee_id": 1, "full_name": 1, "role": 1}
        ).to_list(500)
        all_reportees.extend(indirect_reportees)
    
    return all_reportees



@router.post("")
async def create_employee(data: dict, current_user: User = Depends(get_current_user)):
    """Create a new employee."""
    db = get_db()
    
    # RBAC Migration
    hr_roles = get_role_group("HR_ROLES", fail_closed=True)
    if not hr_roles or not has_role(current_user.role, hr_roles):
        raise HTTPException(status_code=403, detail="Only HR can create employees")
    
    # Validate email format
    import re
    email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if data.get("email") and not re.match(email_regex, data["email"]):
        raise HTTPException(status_code=422, detail="Invalid email format")
    
    # Check for duplicate email in both employees and users collections
    if data.get("email"):
        existing_emp = await db.employees.find_one({"email": data["email"]})
        existing_user = await db.users.find_one({"email": data["email"]})
        if existing_emp or existing_user:
            raise HTTPException(status_code=400, detail="Employee with this email already exists")
    
    # Check for duplicate phone number
    if data.get("phone"):
        phone = data["phone"].replace(" ", "").replace("-", "")
        if len(phone) >= 10:
            existing_phone = await db.employees.find_one({"phone": {"$regex": phone[-10:]}})
            if existing_phone:
                raise HTTPException(status_code=400, detail="Employee with this phone number already exists")
    
    # Generate employee ID if not provided
    employee_id = data.get("employee_id")
    if not employee_id:
        # Find highest existing employee ID number
        all_employees = await db.employees.find(
            {"employee_id": {"$regex": "^EMP\\d+$"}},
            {"employee_id": 1}
        ).to_list(length=1000)
        
        max_num = 0
        for emp in all_employees:
            emp_id = emp.get("employee_id", "")
            try:
                num = int(emp_id.replace("EMP", ""))
                if num > max_num:
                    max_num = num
            except (ValueError, AttributeError):
                continue
        
        next_num = max_num + 1
        employee_id = f"EMP{next_num:04d}" if next_num > 999 else f"EMP{next_num:03d}"
        data["employee_id"] = employee_id
    
    # Handle SELF reporting manager (for first employee or admin)
    reporting_manager_id = data.get("reporting_manager_id")
    is_self_reporting = reporting_manager_id == "SELF"
    
    # Set up departments array - department determines page access
    primary_department = data.get("department")
    departments = data.get("departments", [primary_department] if primary_department else [])
    
    # Create employee ID first
    new_employee_id = str(uuid.uuid4())
    
    # If SELF, reporting manager will be set to own ID after creation
    if is_self_reporting:
        reporting_manager_id = new_employee_id
    
    employee = {
        "id": new_employee_id,
        "employee_id": data.get("employee_id"),
        "first_name": sanitize_text(data.get("first_name", "")),
        "last_name": sanitize_text(data.get("last_name", "")),
        "email": data.get("email"),
        "phone": data.get("phone"),
        "department": primary_department,  # Legacy field - kept for compatibility
        "departments": departments,  # NEW: Array of departments for multi-department access
        "primary_department": primary_department,  # NEW: Primary department for access
        "designation": data.get("designation"),
        "role": data.get("role", "consultant"),
        "level": data.get("level", "executive"),  # Employee hierarchy level
        "reporting_manager_id": reporting_manager_id,
        "is_self_reporting": is_self_reporting,  # Flag for first employee
        "date_of_joining": data.get("date_of_joining"),
        "date_of_birth": data.get("date_of_birth"),
        "gender": data.get("gender"),
        "address": data.get("address"),
        "city": data.get("city"),
        "state": data.get("state"),
        "pincode": data.get("pincode"),
        "emergency_contact": data.get("emergency_contact"),
        "bank_details": data.get("bank_details", {}),
        "salary": data.get("salary", 0),
        "status": "active",
        "user_id": None,
        "custom_page_access": [],  # NEW: Custom page exceptions
        "restricted_pages": [],  # NEW: Restricted pages
        "created_by": current_user.id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.employees.insert_one(employee)
    
    # Remove _id added by MongoDB before returning
    employee.pop("_id", None)
    
    # Send notifications to Admin, HR, and Reporting Manager
    emp_name = f"{employee.get('first_name', '')} {employee.get('last_name', '')}".strip()
    emp_code = employee.get('employee_id')
    department = employee.get('department', 'Unknown')
    
    # Notification for all HR users
    hr_users = await db.users.find(
        {"role": {"$in": ["hr_manager", "hr_executive"]}},
        {"_id": 0, "id": 1}
    ).to_list(50)
    
    for hr_user in hr_users:
        await db.notifications.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": hr_user["id"],
            "type": "employee_onboarded",
            "title": "New Employee Onboarded",
            "message": f"{emp_name} ({emp_code}) has joined {department} department.",
            "link": "/employees",
            "reference_id": employee["id"],
            "is_read": False,
            "status": "info",
            "created_at": datetime.now(timezone.utc).isoformat()
        })
    
    # Notification for all Admin users
    admin_users = await db.users.find(
        {"role": "admin"},
        {"_id": 0, "id": 1}
    ).to_list(20)
    
    for admin_user in admin_users:
        await db.notifications.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": admin_user["id"],
            "type": "employee_onboarded",
            "title": "New Employee Onboarded",
            "message": f"{emp_name} ({emp_code}) has joined {department} department. Review Go-Live readiness.",
            "link": "/go-live",
            "reference_id": employee["id"],
            "is_read": False,
            "status": "info",
            "created_at": datetime.now(timezone.utc).isoformat()
        })
    
    # Notification for Reporting Manager
    if employee.get("reporting_manager_id"):
        rm_employee = await db.employees.find_one(
            {"id": employee["reporting_manager_id"]},
            {"_id": 0, "user_id": 1, "first_name": 1, "last_name": 1}
        )
        if rm_employee and rm_employee.get("user_id"):
            await db.notifications.insert_one({
                "id": str(uuid.uuid4()),
                "user_id": rm_employee["user_id"],
                "type": "employee_onboarded",
                "title": "New Team Member",
                "message": f"{emp_name} ({emp_code}) has been assigned to your team in {department}.",
                "link": "/employees",
                "reference_id": employee["id"],
                "is_read": False,
                "status": "info",
                "created_at": datetime.now(timezone.utc).isoformat()
            })
    
    # Real-time WebSocket notification
    await notify_employee_update(employee["id"], "create", current_user.id)
    await notify_dashboard_refresh(current_user.id)
    
    # Invalidate Redis cache
    await CacheInvalidation.employees()
    
    return {"message": "Employee created", "employee": employee}


@router.post("/{employee_id}/grant-access")
async def grant_employee_access(
    employee_id: str, 
    data: dict = None,
    current_user: User = Depends(get_current_user)
):
    """Grant portal access to an employee by creating a user account.
    
    Args:
        employee_id: Can be either internal UUID (id) or Employee ID (EMP001)
        data: Optional dict with password override
    
    The user.employee_id will always store the human-readable Employee ID (EMP001 format).
    """
    db = get_db()
    
    # RBAC Migration
    hr_admin_roles = get_role_group("HR_ADMIN_ROLES", fail_closed=True)
    if not hr_admin_roles or not has_role(current_user.role, hr_admin_roles):
        raise HTTPException(status_code=403, detail="Only Admin/HR Manager can grant access")
    
    # Find employee by either id (UUID) or employee_id (EMP001)
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        # Try finding by employee_id (EMP001 format)
        employee = await db.employees.find_one({"employee_id": employee_id.upper()}, {"_id": 0})
    
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    if not employee.get("email"):
        raise HTTPException(status_code=400, detail="Employee must have an email to grant access")
    
    # IMPORTANT: Always use the human-readable employee_id (EMP001 format)
    emp_code = employee.get("employee_id")  # This is EMP001, EMP002 etc.
    emp_internal_id = employee.get("id")  # This is the UUID
    
    # Get departments - use departments array or fallback to single department
    departments = employee.get("departments", [])
    if not departments and employee.get("department"):
        departments = [employee.get("department")]
    primary_department = employee.get("primary_department") or employee.get("department")
    
    # Check if user already exists by email
    existing_user = await db.users.find_one({"email": employee["email"]})
    if existing_user:
        # Update existing user with proper employee_id and link
        await db.users.update_one(
            {"id": existing_user["id"]},
            {"$set": {
                "employee_id": emp_code,  # Store EMP001 format, NOT UUID
                "departments": departments,
                "primary_department": primary_department,
                "department": primary_department
            }}
        )
        # Link employee to user
        await db.employees.update_one(
            {"id": emp_internal_id},
            {"$set": {"user_id": existing_user["id"], "has_portal_access": True}}
        )
        return {
            "message": "Linked to existing user account", 
            "user_id": existing_user["id"],
            "employee_id": emp_code,
            "login_id": emp_code  # For clarity - this is what user logs in with
        }
    
    # Create new user with department-based access
    user_id = str(uuid.uuid4())
    
    # Password: Use provided or generate pattern-based
    if data and data.get("password"):
        temp_password = data.get("password")
    else:
        temp_password = f"Welcome@{emp_code}"  # Welcome@EMP001
    
    user = {
        "id": user_id,
        "email": employee["email"],
        "full_name": f"{employee.get('first_name', '')} {employee.get('last_name', '')}".strip(),
        "role": employee.get("role", "consultant"),
        "department": primary_department,  # Legacy field
        "departments": departments,  # Array for multi-department access
        "primary_department": primary_department,
        "level": employee.get("level", "executive"),
        "designation": employee.get("designation"),
        "reporting_manager_id": employee.get("reporting_manager_id"),
        "is_active": True,
        "is_view_only": employee.get("is_view_only", False),
        "hashed_password": get_password_hash(temp_password),
        "requires_password_change": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "employee_id": emp_code  # CRITICAL: Store EMP001 format, NOT UUID
    }
    
    await db.users.insert_one(user)
    
    # Update employee with user link
    await db.employees.update_one(
        {"id": emp_internal_id},
        {"$set": {"user_id": user_id, "has_portal_access": True}}
    )
    
    return {
        "message": "Portal access granted",
        "user_id": user_id,
        "employee_id": emp_code,
        "login_id": emp_code,  # User logs in with this
        "temp_password": temp_password,
        "departments": departments,
        "note": f"Login ID: {emp_code}, Password: {temp_password}. Password should be changed on first login."
    }


@router.post("/{employee_id}/reset-temp-password")
async def reset_employee_temp_password(employee_id: str, current_user: User = Depends(get_current_user)):
    """Reset the temporary password for an employee's portal access.
    This is useful when an employee forgets their password or HR needs to resend credentials.
    """
    db = get_db()
    
    # RBAC Migration
    hr_admin_roles = get_role_group("HR_ADMIN_ROLES", fail_closed=True)
    if not hr_admin_roles or not has_role(current_user.role, hr_admin_roles):
        raise HTTPException(status_code=403, detail="Only Admin/HR Manager can reset passwords")
    
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    if not employee.get("user_id"):
        raise HTTPException(status_code=400, detail="Employee does not have portal access. Grant access first.")
    
    # Find the user
    user = await db.users.find_one({"id": employee["user_id"]}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User account not found")
    
    # Generate new temp password
    temp_password = f"Welcome@{employee.get('employee_id', '123')}"
    new_hash = get_password_hash(temp_password)
    
    # Update user's password
    await db.users.update_one(
        {"id": employee["user_id"]},
        {"$set": {
            "hashed_password": new_hash,
            "is_active": True,  # Re-activate if deactivated
            "password_reset_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    return {
        "message": "Temporary password reset successfully",
        "user_id": employee["user_id"],
        "temp_password": temp_password,
        "note": "Old password is now invalid. User must use this new password."
    }


@router.delete("/{employee_id}/revoke-access")
async def revoke_employee_access(employee_id: str, current_user: User = Depends(get_current_user)):
    """Revoke portal access from an employee."""
    db = get_db()
    
    # RBAC Migration
    hr_admin_roles = get_role_group("HR_ADMIN_ROLES", fail_closed=True)
    if not hr_admin_roles or not has_role(current_user.role, hr_admin_roles):
        raise HTTPException(status_code=403, detail="Only Admin/HR Manager can revoke access")
    
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    if employee.get("user_id"):
        # Deactivate user account
        await db.users.update_one(
            {"id": employee["user_id"]},
            {"$set": {"is_active": False}}
        )
    
    await db.employees.update_one(
        {"id": employee_id},
        {"$set": {"has_portal_access": False}}
    )
    
    return {"message": "Portal access revoked"}


@router.post("/fix-missing-levels")
async def fix_missing_levels(current_user: User = Depends(get_current_user)):
    """Update all employees without a level to have 'executive' as default."""
    db = get_db()
    
    # RBAC Migration
    hr_admin_roles = get_role_group("HR_ADMIN_ROLES", fail_closed=True)
    if not hr_admin_roles or not has_role(current_user.role, hr_admin_roles):
        raise HTTPException(status_code=403, detail="Only Admin/HR Manager can fix levels")
    
    # Find employees without level or with null level
    result = await db.employees.update_many(
        {"$or": [{"level": {"$exists": False}}, {"level": None}, {"level": ""}]},
        {"$set": {"level": "executive"}}
    )
    
    return {
        "message": f"Updated {result.modified_count} employees to have 'executive' level",
        "modified_count": result.modified_count
    }


@router.get("/{employee_id}")
async def get_employee(employee_id: str, current_user: User = Depends(get_current_user)):
    """Get a single employee by ID."""
    db = get_db()
    
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    return employee


@router.patch("/{employee_id}")
async def update_employee(employee_id: str, data: dict, change_reason: str = None, current_user: User = Depends(get_current_user)):
    """
    Update an employee's details with GOVERNANCE ENFORCEMENT.
    
    BLOCKED FIELDS (require workflow):
    - salary, ctc, annual_ctc, ctc_details → Use CTC Designer
    - department, departments → Use Transfer workflow
    - designation → Use Promotion workflow
    - reporting_manager_id → Use Hierarchy Change workflow
    
    PROTECTED FIELDS (require admin approval):
    - bank_details, bank_account_number, ifsc_code
    - role, level, employment_type
    
    ALLOWED FIELDS (HR can edit):
    - Personal info: name, phone, address, emergency contact
    - Documents: pan_number, aadhaar_number (with audit)
    """
    db = get_db()
    
    # RBAC Migration
    hr_roles = get_role_group("HR_ROLES", fail_closed=True)
    if not hr_roles or not has_role(current_user.role, hr_roles):
        raise HTTPException(status_code=403, detail="Only HR can update employees")
    
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    is_onboarded = employee.get("onboarding_status") == "completed" or employee.get("has_portal_access", False)
    is_go_live = employee.get("go_live_status") == "active"
    now = datetime.now(timezone.utc).isoformat()
    
    # ========== GOVERNANCE: Field Classification ==========
    
    # IMMUTABLE - Never allow direct edit
    immutable_fields = ["id", "employee_id", "created_at", "created_by"]
    
    # LOCKED - Must use specific workflows, even admin cannot bypass
    locked_fields = {
        "salary": "ctc_revision",
        "ctc": "ctc_revision", 
        "annual_ctc": "ctc_revision",
        "ctc_details": "ctc_revision",
        "department": "transfer",
        "departments": "transfer",
        "primary_department": "transfer",
        "designation": "promotion",
        "reporting_manager_id": "hierarchy_change",
        "reporting_manager": "hierarchy_change"
    }
    
    # PROTECTED - Require admin approval after onboarding
    protected_fields = [
        "bank_details", "bank_account_number", "bank_name", "ifsc_code", "bank_ifsc",
        "role", "level", "employment_type"
    ]
    
    # AUDIT REQUIRED - Log changes even when allowed
    audit_fields = ["pan_number", "aadhaar_number", "role", "level", "is_active", "status"]
    
    # ========== Validate Each Field ==========
    
    blocked_updates = []
    workflow_required = {}
    approval_required = {}
    allowed_updates = {}
    audit_log = []
    
    for field, value in data.items():
        # Skip system fields
        if field in ["updated_at", "updated_by", "updated_by_name"]:
            continue
        
        # Check immutable
        if field in immutable_fields:
            blocked_updates.append({
                "field": field,
                "reason": f"Field '{field}' is immutable and cannot be changed"
            })
            continue
        
        # Check locked fields - EVEN ADMIN CANNOT BYPASS
        if field in locked_fields:
            workflow = locked_fields[field]
            workflow_required[field] = {
                "value": value,
                "workflow": workflow,
                "reason": f"Field '{field}' must be changed via {workflow.replace('_', ' ')} workflow. Direct edit not allowed."
            }
            continue
        
        # Check protected fields (require admin approval after onboarding)
        if field in protected_fields and (is_onboarded or is_go_live) and current_user.role != "admin":
            approval_required[field] = {
                "value": value,
                "current_value": employee.get(field)
            }
            continue
        
        # Field is allowed
        allowed_updates[field] = value
        
        # Check if audit is required
        if field in audit_fields:
            audit_log.append({
                "field": field,
                "old_value": employee.get(field),
                "new_value": value
            })
    
    # ========== Handle Blocked Updates ==========
    
    if blocked_updates:
        raise HTTPException(
            status_code=403,
            detail={
                "message": "Some fields cannot be updated directly",
                "blocked_fields": blocked_updates
            }
        )
    
    # ========== Handle Workflow Required ==========
    
    workflow_requests = []
    if workflow_required:
        for field, info in workflow_required.items():
            # Create workflow request
            request = {
                "id": str(uuid.uuid4()),
                "employee_id": employee_id,
                "employee_code": employee.get("employee_id"),
                "employee_name": employee.get("full_name") or f"{employee.get('first_name', '')} {employee.get('last_name', '')}",
                "field": field,
                "current_value": employee.get(field),
                "requested_value": info["value"],
                "workflow_type": info["workflow"],
                "requested_by": current_user.id,
                "requested_by_name": current_user.full_name,
                "requested_by_role": current_user.role,
                "change_reason": change_reason,
                "status": "pending",
                "created_at": now
            }
            await db.field_change_requests.insert_one(request)
            workflow_requests.append({
                "field": field,
                "workflow": info["workflow"],
                "request_id": request["id"],
                "message": info["reason"]
            })
    
    # ========== Handle Approval Required ==========
    
    if approval_required:
        modification_request = {
            "id": str(uuid.uuid4()),
            "employee_id": employee_id,
            "employee_code": employee.get("employee_id"),
            "employee_name": f"{employee.get('first_name', '')} {employee.get('last_name', '')}",
            "requested_by": current_user.id,
            "requested_by_email": current_user.email,
            "requested_by_name": current_user.full_name,
            "requested_by_role": current_user.role,
            "requested_changes": {k: v["value"] for k, v in approval_required.items()},
            "current_values": {k: v["current_value"] for k, v in approval_required.items()},
            "all_changes": data,
            "status": "pending",
            "request_type": "employee_modification",
            "is_go_live_employee": is_go_live,
            "change_reason": change_reason,
            "created_at": now
        }
        
        await db.modification_requests.insert_one(modification_request)
        
        # Notify admins
        admin_users = await db.users.find({"role": "admin"}, {"_id": 0, "id": 1}).to_list(20)
        for admin in admin_users:
            await db.notifications.insert_one({
                "id": str(uuid.uuid4()),
                "user_id": admin["id"],
                "type": "modification_approval_required",
                "title": "Employee Modification Request",
                "message": f"{current_user.full_name} requested changes to {employee.get('employee_id', '')}. Review and approve/reject.",
                "reference_type": "modification_request",
                "reference_id": modification_request["id"],
                "is_read": False,
                "action_required": True,
                "link": "/approvals",
                "created_at": now
            })
    
    # ========== Apply Allowed Updates ==========
    
    if allowed_updates:
        # Sanitize text fields
        if "first_name" in allowed_updates:
            allowed_updates["first_name"] = sanitize_text(allowed_updates["first_name"])
        if "last_name" in allowed_updates:
            allowed_updates["last_name"] = sanitize_text(allowed_updates["last_name"])
        
        allowed_updates["updated_at"] = now
        allowed_updates["updated_by"] = current_user.id
        allowed_updates["updated_by_name"] = current_user.full_name
        
        # Log audit entries
        for entry in audit_log:
            await db.employee_change_history.insert_one({
                "id": str(uuid.uuid4()),
                "employee_id": employee_id,
                "field": entry["field"],
                "old_value": str(entry["old_value"]) if entry["old_value"] is not None else None,
                "new_value": str(entry["new_value"]) if entry["new_value"] is not None else None,
                "changed_by": current_user.id,
                "changed_by_name": current_user.full_name,
                "changed_by_role": current_user.role,
                "change_reason": change_reason,
                "timestamp": now,
                "change_type": "direct_edit"
            })
        
        await db.employees.update_one({"id": employee_id}, {"$set": allowed_updates})
    
    # ========== Build Response ==========
    
    response = {"message": "Update processed"}
    
    if allowed_updates:
        response["updated_fields"] = [k for k in allowed_updates.keys() if k not in ["updated_at", "updated_by", "updated_by_name"]]
        # Real-time WebSocket notification for update
        await notify_employee_update(employee_id, "update", current_user.id)
        await CacheInvalidation.employee(employee_id)
        
        # P0 FIX: Sync employee data to user record for consistency
        # This ensures role, department, level etc stay in sync
        await sync_employee_to_user(db, employee_id, allowed_updates)
    
    if workflow_requests:
        response["workflow_requests"] = workflow_requests
        response["note"] = "Some fields require specific workflows. See workflow_requests for details."
    
    if approval_required:
        response["pending_approval"] = list(approval_required.keys())
        response["approval_request_id"] = modification_request["id"]
        response["approval_note"] = "Some fields require Admin approval. Request has been submitted."
        # Notify about pending approval
        await ws_manager.broadcast_update("approvals", "new_request", {"type": "employee_modification"}, current_user.id)
    
    return response



# ============== Modification Request Endpoints ==============

@router.get("/modification-requests/pending")
async def get_pending_modification_requests(current_user: User = Depends(get_current_user)):
    """Get all pending modification requests (Admin only)."""
    db = get_db()
    
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only Admin can view modification requests")
    
    requests = await db.modification_requests.find(
        {"status": "pending"},
        {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    
    return requests


@router.post("/modification-requests/{request_id}/approve")
async def approve_modification_request(request_id: str, current_user: User = Depends(get_current_user)):
    """Approve a modification request and apply changes (Admin only)."""
    db = get_db()
    
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only Admin can approve modification requests")
    
    mod_request = await db.modification_requests.find_one({"id": request_id}, {"_id": 0})
    if not mod_request:
        raise HTTPException(status_code=404, detail="Modification request not found")
    
    if mod_request.get("status") != "pending":
        raise HTTPException(status_code=400, detail=f"Request is already {mod_request.get('status')}")
    
    # Apply the changes to the employee
    employee_id = mod_request.get("employee_id")
    changes = mod_request.get("requested_changes", {})
    
    now = datetime.now(timezone.utc).isoformat()
    changes["updated_at"] = now
    changes["updated_by"] = current_user.id
    changes["last_modification_approved_at"] = now
    changes["last_modification_approved_by"] = current_user.id
    
    await db.employees.update_one({"id": employee_id}, {"$set": changes})
    
    # P0 FIX: Sync employee data to user record after approval
    await sync_employee_to_user(db, employee_id, changes)
    
    # Update the modification request status
    await db.modification_requests.update_one(
        {"id": request_id},
        {"$set": {
            "status": "approved",
            "approved_by": current_user.id,
            "approved_by_name": current_user.full_name,
            "approved_at": now
        }}
    )
    
    # Notify the requester
    if mod_request.get("requested_by"):
        await db.notifications.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": mod_request["requested_by"],
            "type": "modification_approved",
            "title": "Modification Approved",
            "message": f"Your modification request for {mod_request.get('employee_code', '')} ({mod_request.get('employee_name', '')}) has been approved by {current_user.full_name}.",
            "reference_type": "modification_request",
            "reference_id": request_id,
            "is_read": False,
            "created_at": now
        })
    
    return {
        "message": "Modification request approved and changes applied",
        "employee_id": employee_id,
        "employee_code": mod_request.get("employee_code"),
        "applied_changes": list(changes.keys())
    }


@router.post("/modification-requests/{request_id}/reject")
async def reject_modification_request(
    request_id: str, 
    data: dict,
    current_user: User = Depends(get_current_user)
):
    """Reject a modification request (Admin only)."""
    db = get_db()
    
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only Admin can reject modification requests")
    
    mod_request = await db.modification_requests.find_one({"id": request_id}, {"_id": 0})
    if not mod_request:
        raise HTTPException(status_code=404, detail="Modification request not found")
    
    if mod_request.get("status") != "pending":
        raise HTTPException(status_code=400, detail=f"Request is already {mod_request.get('status')}")
    
    now = datetime.now(timezone.utc).isoformat()
    reason = data.get("reason", "")
    
    # Update the modification request status
    await db.modification_requests.update_one(
        {"id": request_id},
        {"$set": {
            "status": "rejected",
            "rejected_by": current_user.id,
            "rejected_by_name": current_user.full_name,
            "rejected_at": now,
            "rejection_reason": reason
        }}
    )
    
    # Notify the requester
    if mod_request.get("requested_by"):
        await db.notifications.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": mod_request["requested_by"],
            "type": "modification_rejected",
            "title": "Modification Rejected",
            "message": f"Your modification request for {mod_request.get('employee_code', '')} was rejected. Reason: {reason or 'Not specified'}",
            "reference_type": "modification_request",
            "reference_id": request_id,
            "is_read": False,
            "created_at": now
        })
    
    return {
        "message": "Modification request rejected",
        "employee_code": mod_request.get("employee_code"),
        "reason": reason
    }



@router.delete("/{employee_id}")
async def delete_employee(employee_id: str, current_user: User = Depends(get_current_user)):
    """Delete (soft delete) an employee."""
    db = get_db()
    
    if current_user.role not in ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Only Admin can delete employees")
    
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Soft delete
    await db.employees.update_one(
        {"id": employee_id},
        {"$set": {"status": "terminated", "terminated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    return {"message": "Employee terminated"}


@router.post("/{employee_id}/photo")
async def upload_profile_photo(
    employee_id: str, 
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """
    Upload passport-size profile photo for an employee.
    
    Purpose:
    - Print forms (offer letters, ID cards, official documents)
    - UI avatar display (auto-generated thumbnail)
    
    Requirements:
    - Accepts JPEG, PNG, WebP images
    - Recommended: Passport size (35mm x 45mm ratio, ~413x531 pixels)
    - Max file size: 5MB (for print quality)
    - Stores original for print + generates avatar thumbnail
    """
    db = get_db()
    
    # Find employee - check both employees and users collections
    employee = await db.employees.find_one({"employee_id": employee_id}, {"_id": 0})
    user_record = None
    
    if not employee:
        # Try users collection as fallback for users without employee records
        user_record = await db.users.find_one({"employee_id": employee_id}, {"_id": 0})
        if not user_record:
            raise HTTPException(status_code=404, detail="Employee not found")
    
    # Check permissions: HR, Admin, or self
    target_user_id = employee.get("user_id") if employee else user_record.get("id")
    is_self = target_user_id == current_user.id or employee_id == current_user.employee_id
    hr_roles = get_role_group("HR_ROLES", fail_closed=True)
    if not is_self and not has_role(current_user.role, hr_roles):
        raise HTTPException(status_code=403, detail="Not authorized to update this profile photo")
    
    # Validate file type
    if file.content_type not in ALLOWED_PHOTO_TYPES:
        raise HTTPException(
            status_code=400, 
            detail="Invalid file type. Allowed: JPEG, PNG, WebP"
        )
    
    # Read and validate file size (5MB for print quality)
    contents = await file.read()
    if len(contents) > MAX_PHOTO_SIZE:
        raise HTTPException(
            status_code=400, 
            detail="File too large. Maximum size: 5MB"
        )
    
    # Convert to base64 data URL (original for print)
    base64_data = base64.b64encode(contents).decode('utf-8')
    profile_photo_url = f"data:{file.content_type};base64,{base64_data}"
    
    # Photo metadata
    photo_metadata = {
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
        "uploaded_by": current_user.id,
        "file_name": file.filename,
        "file_type": file.content_type,
        "file_size": len(contents),
        "purpose": "passport_photo"  # For print forms
    }
    
    # Update employee record if exists
    if employee:
        await db.employees.update_one(
            {"employee_id": employee_id},
            {"$set": {
                "profile_photo_url": profile_photo_url,  # Original for print
                "avatar_url": profile_photo_url,  # Same for avatar (UI will resize)
                "photo_metadata": photo_metadata,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }}
        )
        
        # Also update user record if linked
        if employee.get("user_id"):
            await db.users.update_one(
                {"id": employee.get("user_id")},
                {"$set": {
                    "profile_photo_url": profile_photo_url,
                    "avatar_url": profile_photo_url
                }}
            )
    elif user_record:
        # Update user record directly if no employee record exists
        await db.users.update_one(
            {"employee_id": employee_id},
            {"$set": {
                "profile_photo_url": profile_photo_url,
                "avatar_url": profile_photo_url,
                "photo_metadata": photo_metadata
            }}
        )
    
    return {
        "message": "Passport photo uploaded successfully",
        "profile_photo_url": profile_photo_url,
        "avatar_url": profile_photo_url,
        "metadata": photo_metadata,
        "usage": {
            "print_forms": "Use profile_photo_url for offer letters, ID cards",
            "ui_avatar": "Use avatar_url for dashboard display"
        }
    }


@router.delete("/{employee_id}/photo")
async def delete_profile_photo(
    employee_id: str,
    current_user: User = Depends(get_current_user)
):
    """Remove profile photo for an employee."""
    db = get_db()
    
    # Find employee - check both employees and users collections
    employee = await db.employees.find_one({"employee_id": employee_id}, {"_id": 0})
    user_record = None
    
    if not employee:
        user_record = await db.users.find_one({"employee_id": employee_id}, {"_id": 0})
        if not user_record:
            raise HTTPException(status_code=404, detail="Employee not found")
    
    # Check permissions
    target_user_id = employee.get("user_id") if employee else user_record.get("id")
    is_self = target_user_id == current_user.id or employee_id == current_user.employee_id
    hr_roles = get_role_group("HR_ROLES", fail_closed=True)
    if not is_self and not has_role(current_user.role, hr_roles):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Remove from employee if exists
    if employee:
        await db.employees.update_one(
            {"employee_id": employee_id},
            {"$unset": {
                "profile_photo_url": "",
                "avatar_url": "",
                "photo_metadata": ""
            }}
        )
        
        # Remove from user if linked
        if employee.get("user_id"):
            await db.users.update_one(
                {"id": employee.get("user_id")},
                {"$unset": {
                    "profile_photo_url": "",
                    "avatar_url": ""
                }}
            )
    elif user_record:
        # Remove from user record directly
        await db.users.update_one(
            {"employee_id": employee_id},
            {"$unset": {
                "profile_photo_url": "",
                "avatar_url": "",
                "photo_metadata": ""
            }}
        )
    
    return {"message": "Profile photo removed"}


@router.get("/{employee_id}/photo")
async def get_profile_photo(
    employee_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get employee's profile photo details.
    Returns URLs for both print (high-res) and avatar (display) usage.
    """
    db = get_db()
    
    # Try employees collection first
    employee = await db.employees.find_one(
        {"employee_id": employee_id}, 
        {"_id": 0, "profile_photo_url": 1, "avatar_url": 1, "photo_metadata": 1, "first_name": 1, "last_name": 1}
    )
    
    if not employee:
        # Try users collection as fallback
        employee = await db.users.find_one(
            {"employee_id": employee_id}, 
            {"_id": 0, "profile_photo_url": 1, "avatar_url": 1, "photo_metadata": 1, "full_name": 1}
        )
        if not employee:
            raise HTTPException(status_code=404, detail="Employee not found")
    
    has_photo = bool(employee.get("profile_photo_url"))
    
    return {
        "has_photo": has_photo,
        "profile_photo_url": employee.get("profile_photo_url"),  # For print
        "avatar_url": employee.get("avatar_url"),  # For UI
        "metadata": employee.get("photo_metadata"),
        "fallback_initials": f"{employee.get('first_name', '?')[0]}{employee.get('last_name', '?')[0]}".upper()
    }


@router.post("/{employee_id}/documents")
async def upload_employee_document(employee_id: str, data: dict, current_user: User = Depends(get_current_user)):
    """Upload a document for an employee."""
    db = get_db()
    
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    document = {
        "id": str(uuid.uuid4()),
        "employee_id": employee_id,
        "document_type": data.get("document_type", "other"),
        "document_name": sanitize_text(data.get("document_name", "")),
        "file_data": data.get("file_data"),  # Base64 encoded
        "file_name": data.get("file_name"),
        "file_type": data.get("file_type"),
        "uploaded_by": current_user.id,
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
        "verified": False
    }
    
    await db.employee_documents.insert_one(document)
    
    return {"message": "Document uploaded", "document_id": document["id"]}


@router.get("/{employee_id}/documents/{document_id}")
async def get_employee_document(employee_id: str, document_id: str, current_user: User = Depends(get_current_user)):
    """Get a specific document for an employee."""
    db = get_db()
    
    document = await db.employee_documents.find_one(
        {"id": document_id, "employee_id": employee_id},
        {"_id": 0}
    )
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return document


@router.delete("/{employee_id}/documents/{document_id}")
async def delete_employee_document(employee_id: str, document_id: str, current_user: User = Depends(get_current_user)):
    """Delete an employee document."""
    db = get_db()
    
    # RBAC Migration
    hr_admin_roles = get_role_group("HR_ADMIN_ROLES", fail_closed=True)
    if not hr_admin_roles or not has_role(current_user.role, hr_admin_roles):
        raise HTTPException(status_code=403, detail="Only Admin/HR can delete documents")
    
    result = await db.employee_documents.delete_one({"id": document_id, "employee_id": employee_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return {"message": "Document deleted"}


@router.get("/org-chart/hierarchy")
async def get_org_hierarchy(current_user: User = Depends(get_current_user)):
    """Get organization hierarchy for org chart."""
    db = get_db()
    
    employees = await db.employees.find(
        {"status": "active"},
        {"_id": 0, "id": 1, "first_name": 1, "last_name": 1, "designation": 1, "department": 1, "reporting_manager_id": 1, "role": 1}
    ).to_list(1000)
    
    # Build hierarchy tree
    def build_tree(manager_id=None):
        children = []
        for emp in employees:
            if emp.get("reporting_manager_id") == manager_id:
                node = {
                    "id": emp["id"],
                    "name": f"{emp.get('first_name', '')} {emp.get('last_name', '')}".strip(),
                    "designation": emp.get("designation", ""),
                    "department": emp.get("department", ""),
                    "role": emp.get("role", ""),
                    "children": build_tree(emp["id"])
                }
                children.append(node)
        return children
    
    # Find root nodes (no reporting manager)
    roots = []
    for emp in employees:
        if not emp.get("reporting_manager_id"):
            node = {
                "id": emp["id"],
                "name": f"{emp.get('first_name', '')} {emp.get('last_name', '')}".strip(),
                "designation": emp.get("designation", ""),
                "department": emp.get("department", ""),
                "role": emp.get("role", ""),
                "children": build_tree(emp["id"])
            }
            roots.append(node)
    
    return roots


@router.get("/{employee_id}/subordinates")
async def get_subordinates(employee_id: str, current_user: User = Depends(get_current_user)):
    """Get direct reports for an employee."""
    db = get_db()
    
    subordinates = await db.employees.find(
        {"reporting_manager_id": employee_id, "status": "active"},
        {"_id": 0}
    ).to_list(100)
    
    return subordinates


@router.get("/departments/list")
async def get_departments(current_user: User = Depends(get_current_user)):
    """Get list of unique departments."""
    db = get_db()
    
    departments = await db.employees.distinct("department")
    dept_list = [d for d in departments if d]
    return {"success": True, "data": dept_list}


@router.get("/stats/summary")
async def get_employee_stats(current_user: User = Depends(get_current_user)):
    """Get employee statistics summary."""
    db = get_db()
    
    # RBAC Migration
    hr_roles = get_role_group("HR_ROLES", fail_closed=True)
    if not hr_roles or not has_role(current_user.role, hr_roles):
        raise HTTPException(status_code=403, detail="Only HR can view employee stats")
    
    total = await db.employees.count_documents({})
    active = await db.employees.count_documents({"status": "active"})
    terminated = await db.employees.count_documents({"status": "terminated"})
    with_access = await db.employees.count_documents({"has_portal_access": True, "status": "active"})
    without_access = active - with_access
    
    # By department
    dept_stats = await db.employees.aggregate([
        {"$match": {"status": "active"}},
        {"$group": {"_id": "$department", "count": {"$sum": 1}}}
    ]).to_list(50)
    
    # By role
    role_stats = await db.employees.aggregate([
        {"$match": {"status": "active"}},
        {"$group": {"_id": "$role", "count": {"$sum": 1}}}
    ]).to_list(50)
    
    # By level
    level_stats = await db.employees.aggregate([
        {"$match": {"status": "active"}},
        {"$group": {"_id": "$level", "count": {"$sum": 1}}}
    ]).to_list(10)
    
    return {
        "total": total,
        "active": active,
        "terminated": terminated,
        "with_portal_access": with_access,
        "without_portal_access": without_access,
        "by_department": {d["_id"]: d["count"] for d in dept_stats if d["_id"]},
        "by_role": {r["_id"]: r["count"] for r in role_stats if r["_id"]},
        "by_level": {lvl["_id"]: lvl["count"] for lvl in level_stats if lvl["_id"]}
    }


@router.get("/integrity/audit")
async def run_integrity_audit(current_user: User = Depends(get_current_user)):
    """
    Run comprehensive integrity audit on employee data.
    
    ACCESS: Admin only.
    
    Returns audit report with:
    - Employee statistics
    - Lifecycle anomalies detected
    - Risk assessment
    - Recommendations
    """
    db = get_db()
    
    # Admin only
    admin_roles = get_role_group("ADMIN_ROLES", fail_closed=False) or ["admin"]
    if not has_role(current_user.role, admin_roles):
        raise HTTPException(status_code=403, detail="Only Admin can run integrity audits")
    
    from services.integrity_monitor import IntegrityMonitor
    
    report = await IntegrityMonitor.run_audit(db)
    return report


@router.get("/integrity/scheduler/status")
async def get_scheduler_status(current_user: User = Depends(get_current_user)):
    """
    Get integrity scheduler status.
    
    ACCESS: Admin only.
    """
    # Admin only
    admin_roles = get_role_group("ADMIN_ROLES", fail_closed=False) or ["admin"]
    if not has_role(current_user.role, admin_roles):
        raise HTTPException(status_code=403, detail="Only Admin can view scheduler status")
    
    from services.integrity_scheduler import get_integrity_scheduler
    scheduler = get_integrity_scheduler()
    
    if not scheduler:
        return {"status": "not_initialized", "message": "Scheduler not running"}
    
    return scheduler.get_status()


@router.post("/integrity/scheduler/run-now")
async def trigger_audit_now(current_user: User = Depends(get_current_user)):
    """
    Trigger an immediate integrity audit.
    
    ACCESS: Admin only.
    """
    db = get_db()
    
    # Admin only
    admin_roles = get_role_group("ADMIN_ROLES", fail_closed=False) or ["admin"]
    if not has_role(current_user.role, admin_roles):
        raise HTTPException(status_code=403, detail="Only Admin can trigger audits")
    
    from services.integrity_scheduler import get_integrity_scheduler
    scheduler = get_integrity_scheduler(db)
    
    if not scheduler:
        raise HTTPException(status_code=500, detail="Scheduler not initialized")
    
    report = await scheduler.run_audit_now()
    return report


@router.get("/integrity/reports")
async def get_audit_reports(
    limit: int = 10,
    current_user: User = Depends(get_current_user)
):
    """
    Get recent integrity audit reports.
    
    ACCESS: Admin only.
    """
    db = get_db()
    
    # Admin only
    admin_roles = get_role_group("ADMIN_ROLES", fail_closed=False) or ["admin"]
    if not has_role(current_user.role, admin_roles):
        raise HTTPException(status_code=403, detail="Only Admin can view audit reports")
    
    reports = await db.integrity_audit_reports.find(
        {},
        {"_id": 0}
    ).sort("timestamp", -1).limit(limit).to_list(limit)
    
    return {"reports": reports, "count": len(reports)}


@router.get("/lookup/by-code/{emp_code}")
async def lookup_employee_by_code(emp_code: str, current_user: User = Depends(get_current_user)):
    """Lookup employee by employee code (e.g., EMP001)."""
    db = get_db()
    
    employee = await db.employees.find_one(
        {"employee_id": {"$regex": emp_code, "$options": "i"}},
        {"_id": 0}
    )
    
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    return employee


@router.get("/{employee_id}/timeline")
async def get_employee_timeline(employee_id: str, current_user: User = Depends(get_current_user)):
    """Get complete timeline/journey of an employee from hiring to present."""
    db = get_db()
    
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    emp_code = employee.get("employee_id", "")
    timeline = []
    
    # 1. Hiring/Onboarding
    if employee.get("created_at"):
        timeline.append({
            "date": employee["created_at"],
            "event": "hired",
            "title": "Joined Company",
            "description": f"Joined as {employee.get('designation', 'Employee')} in {employee.get('department', 'N/A')}"
        })
    
    # 2. Portal Access Grant
    if employee.get("has_portal_access") and employee.get("user_id"):
        user = await db.users.find_one({"id": employee["user_id"]}, {"_id": 0, "created_at": 1})
        if user:
            timeline.append({
                "date": user.get("created_at"),
                "event": "access_granted",
                "title": "Portal Access Granted",
                "description": "Employee portal access enabled"
            })
    
    # 3. Offer Letters
    letters = await db.offer_letters.find(
        {"$or": [{"employee_id": employee_id}, {"employee_email": employee.get("email")}]},
        {"_id": 0}
    ).to_list(20)
    for letter in letters:
        timeline.append({
            "date": letter.get("created_at"),
            "event": "offer_letter",
            "title": f"{letter.get('letter_type', 'Offer').title()} Letter",
            "description": f"Status: {letter.get('status', 'pending')}"
        })
    
    # 4. Leave Requests
    leaves = await db.leave_requests.find({"employee_id": employee_id}, {"_id": 0}).to_list(50)
    for leave in leaves:
        timeline.append({
            "date": leave.get("created_at"),
            "event": "leave_request",
            "title": f"{leave.get('leave_type', '').replace('_', ' ').title()}",
            "description": f"{leave.get('days')} day(s) - {leave.get('status', 'pending')}"
        })
    
    # 5. Expenses - query by both employee_id (code) and user_id (UUID)
    user_id = employee.get("user_id")
    expense_query = {"$or": [{"employee_id": emp_code}]}
    if user_id:
        expense_query["$or"].append({"user_id": user_id})
        expense_query["$or"].append({"created_by": user_id})
    expenses = await db.expenses.find(expense_query, {"_id": 0}).to_list(50)
    for exp in expenses:
        timeline.append({
            "date": exp.get("created_at"),
            "event": "expense",
            "title": f"Expense: {exp.get('category', 'Other')}",
            "description": f"Amount: {exp.get('total_amount', 0)} - {exp.get('status', 'pending')}"
        })
    
    # 6. Attendance milestones
    att_count = await db.attendance.count_documents({"employee_id": employee_id})
    if att_count > 0:
        first_att = await db.attendance.find_one({"employee_id": employee_id}, {"_id": 0}, sort=[("date", 1)])
        if first_att:
            timeline.append({
                "date": first_att.get("created_at") or first_att.get("date"),
                "event": "first_attendance",
                "title": "First Attendance",
                "description": f"Started tracking attendance ({att_count} records total)"
            })
    
    # 7. Project Assignments
    project_assignments = await db.project_assignments.find(
        {"$or": [{"employee_id": employee_id}, {"consultant_id": employee_id}]},
        {"_id": 0}
    ).to_list(50)
    for pa in project_assignments:
        project = await db.projects.find_one({"id": pa.get("project_id")}, {"_id": 0, "name": 1})
        timeline.append({
            "date": pa.get("assigned_at") or pa.get("created_at"),
            "event": "project_assignment",
            "title": "Assigned to Project",
            "description": project.get("name", "Unknown Project") if project else "Unknown Project"
        })
    
    # 8. Salary Slips
    salary_slips = await db.salary_slips.find({"employee_id": employee_id}, {"_id": 0}).to_list(50)
    for slip in salary_slips:
        timeline.append({
            "date": slip.get("created_at") or f"{slip.get('month', '')}-01",
            "event": "salary_slip",
            "title": f"Salary Slip - {slip.get('month', 'N/A')}",
            "description": f"Net: {slip.get('net_salary', 0)}"
        })
    
    # 9. Termination
    if employee.get("status") == "terminated":
        timeline.append({
            "date": employee.get("terminated_at"),
            "event": "terminated",
            "title": "Employment Ended",
            "description": "Status changed to terminated"
        })
    
    # Sort by date
    timeline.sort(key=lambda x: x.get("date") or "", reverse=True)
    
    return {
        "employee_id": employee_id,
        "employee_code": emp_code,
        "employee_name": f"{employee.get('first_name', '')} {employee.get('last_name', '')}".strip(),
        "timeline": timeline,
        "total_events": len(timeline)
    }


@router.get("/{employee_id}/linked-records")
async def get_employee_linked_records(employee_id: str, current_user: User = Depends(get_current_user)):
    """Get all records linked to this employee across all modules."""
    db = get_db()
    
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    emp_code = employee.get("employee_id", "")
    user_id = employee.get("user_id")
    email = employee.get("email")
    
    # Count linked records - use $or for expenses to include user_id and created_by
    expense_query = {"$or": [{"employee_id": employee_id}]}
    if user_id:
        expense_query["$or"].append({"user_id": user_id})
        expense_query["$or"].append({"created_by": user_id})
    
    linked = {
        "attendance": await db.attendance.count_documents({"employee_id": employee_id}),
        "leave_requests": await db.leave_requests.count_documents({"employee_id": employee_id}),
        "expenses": await db.expenses.count_documents(expense_query),
        "salary_slips": await db.salary_slips.count_documents({"employee_id": employee_id}),
        "documents": await db.employee_documents.count_documents({"employee_id": employee_id}),
        "project_assignments": await db.project_assignments.count_documents(
            {"$or": [{"employee_id": employee_id}, {"consultant_id": employee_id}]}
        ),
        "offer_letters": await db.offer_letters.count_documents(
            {"$or": [{"employee_id": employee_id}, {"employee_email": email}]}
        ) if email else 0,
        "approval_requests": await db.approval_requests.count_documents({"requester_id": user_id}) if user_id else 0,
        "notifications": await db.notifications.count_documents({"user_id": user_id}) if user_id else 0,
        "staffing_requests": await db.staffing_requests.count_documents({"requester_id": user_id}) if user_id else 0
    }
    
    return {
        "employee_id": employee_id,
        "employee_code": emp_code,
        "user_id": user_id,
        "email": email,
        "linked_records": linked,
        "total_records": sum(linked.values())
    }



# ============== Data Sync Endpoints (P0 Architecture Fix) ==============

from services.employee_user_sync import sync_all_employees_to_users, verify_sync_consistency

@router.get("/sync/status/{employee_id}")
async def check_sync_status(employee_id: str, current_user: User = Depends(get_current_user)):
    """Check if employee and user data are in sync. Admin only."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    
    db = get_db()
    report = await verify_sync_consistency(db, employee_id)
    return report


@router.post("/sync/bulk")
async def trigger_bulk_sync(current_user: User = Depends(get_current_user)):
    """Trigger bulk sync of all employees to users. Admin only."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    
    db = get_db()
    stats = await sync_all_employees_to_users(db)
    return {
        "message": "Bulk sync completed",
        "stats": stats
    }


@router.post("/sync/{employee_id}")
async def trigger_single_sync(employee_id: str, current_user: User = Depends(get_current_user)):
    """Manually trigger sync for a single employee. Admin only."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    
    db = get_db()
    result = await sync_employee_to_user(db, employee_id)
    return {
        "message": "Sync completed" if result else "No sync needed or user not found",
        "synced": result
    }
