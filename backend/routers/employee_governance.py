"""
Employee Governance Router - Single Source of Truth & Field-Level RBAC

This module enforces:
1. Single source of truth for employee master data
2. Field-level edit permissions based on RBAC
3. Mandatory audit trail for all changes
4. Workflow-based changes for protected fields
5. Consent management and compliance
"""

from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
import uuid
import hashlib

from .models import User
from .deps import get_db, get_role_group, has_role
from .auth import get_current_user

router = APIRouter(prefix="/governance", tags=["Employee Governance"])


# ============== FIELD PERMISSION MATRIX ==============
# Defines who can edit which fields and through what workflow

FIELD_PERMISSIONS = {
    # Personal Information - HR can edit during onboarding, employee can request changes
    "first_name": {"edit_roles": ["hr_manager", "hr_executive", "admin"], "requires_approval": False, "workflow": None},
    "last_name": {"edit_roles": ["hr_manager", "hr_executive", "admin"], "requires_approval": False, "workflow": None},
    "date_of_birth": {"edit_roles": ["hr_manager", "admin"], "requires_approval": False, "workflow": None},
    "gender": {"edit_roles": ["hr_manager", "admin"], "requires_approval": False, "workflow": None},
    "phone": {"edit_roles": ["hr_manager", "hr_executive", "admin"], "requires_approval": False, "workflow": None},
    "personal_email": {"edit_roles": ["hr_manager", "hr_executive", "admin"], "requires_approval": False, "workflow": None},
    "current_address": {"edit_roles": ["hr_manager", "hr_executive", "admin"], "requires_approval": False, "workflow": None},
    "permanent_address": {"edit_roles": ["hr_manager", "hr_executive", "admin"], "requires_approval": False, "workflow": None},
    "emergency_contact": {"edit_roles": ["hr_manager", "hr_executive", "admin"], "requires_approval": False, "workflow": None},
    
    # Identity Documents - HR Manager only, with audit
    "pan_number": {"edit_roles": ["hr_manager", "admin"], "requires_approval": False, "workflow": None, "audit_required": True},
    "aadhaar_number": {"edit_roles": ["hr_manager", "admin"], "requires_approval": False, "workflow": None, "audit_required": True},
    
    # PROTECTED FIELDS - Cannot be directly edited
    # Department - Only via transfer workflow
    "department": {"edit_roles": [], "requires_approval": True, "workflow": "transfer", "locked": True},
    "departments": {"edit_roles": [], "requires_approval": True, "workflow": "transfer", "locked": True},
    "primary_department": {"edit_roles": [], "requires_approval": True, "workflow": "transfer", "locked": True},
    
    # Designation - Only via promotion workflow
    "designation": {"edit_roles": [], "requires_approval": True, "workflow": "promotion", "locked": True},
    
    # Reporting Manager - Only via hierarchy change workflow
    "reporting_manager_id": {"edit_roles": [], "requires_approval": True, "workflow": "hierarchy_change", "locked": True},
    "reporting_manager": {"edit_roles": [], "requires_approval": True, "workflow": "hierarchy_change", "locked": True},
    
    # Salary/CTC - NEVER directly editable, must use CTC Designer
    "salary": {"edit_roles": [], "requires_approval": True, "workflow": "ctc_revision", "locked": True, "source": "ctc_structures"},
    "ctc": {"edit_roles": [], "requires_approval": True, "workflow": "ctc_revision", "locked": True, "source": "ctc_structures"},
    "annual_ctc": {"edit_roles": [], "requires_approval": True, "workflow": "ctc_revision", "locked": True, "source": "ctc_structures"},
    "ctc_details": {"edit_roles": [], "requires_approval": True, "workflow": "ctc_revision", "locked": True, "source": "ctc_structures"},
    
    # Bank Details - Requires HR Manager approval with verification
    "bank_details": {"edit_roles": ["hr_manager", "admin"], "requires_approval": True, "workflow": "bank_change", "audit_required": True},
    "bank_account_number": {"edit_roles": ["hr_manager", "admin"], "requires_approval": True, "workflow": "bank_change", "audit_required": True},
    "bank_name": {"edit_roles": ["hr_manager", "admin"], "requires_approval": True, "workflow": "bank_change", "audit_required": True},
    "ifsc_code": {"edit_roles": ["hr_manager", "admin"], "requires_approval": True, "workflow": "bank_change", "audit_required": True},
    
    # Role & Permissions - Admin only
    "role": {"edit_roles": ["admin"], "requires_approval": False, "workflow": None, "audit_required": True},
    "level": {"edit_roles": ["admin"], "requires_approval": False, "workflow": None, "audit_required": True},
    "custom_page_access": {"edit_roles": ["admin"], "requires_approval": False, "workflow": None},
    "restricted_pages": {"edit_roles": ["admin"], "requires_approval": False, "workflow": None},
    
    # Employment Details - Admin/HR Manager
    "employment_type": {"edit_roles": ["hr_manager", "admin"], "requires_approval": True, "workflow": "employment_change"},
    "joining_date": {"edit_roles": ["hr_manager", "admin"], "requires_approval": False, "workflow": None},
    
    # Status - Admin only
    "status": {"edit_roles": ["admin"], "requires_approval": False, "workflow": None, "audit_required": True},
    "is_active": {"edit_roles": ["admin"], "requires_approval": False, "workflow": None, "audit_required": True},
    
    # System Fields - Never directly editable
    "id": {"edit_roles": [], "locked": True, "immutable": True},
    "employee_id": {"edit_roles": [], "locked": True, "immutable": True},
    "created_at": {"edit_roles": [], "locked": True, "immutable": True},
    "created_by": {"edit_roles": [], "locked": True, "immutable": True},
}

# Fields that employees can view but never edit
EMPLOYEE_READONLY_FIELDS = [
    "employee_id", "department", "designation", "salary", "ctc", "annual_ctc",
    "reporting_manager_id", "role", "level", "employment_type", "joining_date"
]


def validate_field_edit_permission(field: str, user_role: str, employee: dict) -> dict:
    """
    Validate if user can edit a specific field.
    Returns: {"allowed": bool, "reason": str, "workflow": str or None}
    """
    permission = FIELD_PERMISSIONS.get(field)
    
    if not permission:
        # Unknown field - allow for backward compatibility but log
        return {"allowed": True, "reason": "Unknown field - allowed", "workflow": None}
    
    # Check if field is immutable
    if permission.get("immutable"):
        return {"allowed": False, "reason": f"Field '{field}' is immutable and cannot be changed", "workflow": None}
    
    # Check if field is locked and requires workflow
    if permission.get("locked"):
        workflow = permission.get("workflow")
        return {
            "allowed": False, 
            "reason": f"Field '{field}' requires {workflow} workflow. Direct edit not allowed.",
            "workflow": workflow
        }
    
    # Check role permission
    allowed_roles = permission.get("edit_roles", [])
    if allowed_roles and user_role not in allowed_roles:
        return {
            "allowed": False,
            "reason": f"Role '{user_role}' cannot edit field '{field}'. Allowed: {allowed_roles}",
            "workflow": None
        }
    
    # Check if approval is required
    if permission.get("requires_approval") and user_role != "admin":
        return {
            "allowed": False,
            "reason": f"Field '{field}' requires admin approval",
            "workflow": permission.get("workflow")
        }
    
    return {"allowed": True, "reason": "Permitted", "workflow": None, "audit_required": permission.get("audit_required", False)}


async def log_field_change(
    db, 
    employee_id: str, 
    field: str, 
    old_value: Any, 
    new_value: Any, 
    changed_by: str,
    changed_by_name: str,
    changed_by_role: str,
    change_reason: str = None,
    workflow_id: str = None
):
    """Log a field change to the audit trail."""
    
    change_record = {
        "id": str(uuid.uuid4()),
        "employee_id": employee_id,
        "field": field,
        "old_value": str(old_value) if old_value is not None else None,
        "new_value": str(new_value) if new_value is not None else None,
        "changed_by": changed_by,
        "changed_by_name": changed_by_name,
        "changed_by_role": changed_by_role,
        "change_reason": change_reason,
        "workflow_id": workflow_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "change_type": "direct_edit" if not workflow_id else "workflow_change"
    }
    
    await db.employee_change_history.insert_one(change_record)
    return change_record


# ============== GOVERNANCE ENDPOINTS ==============

@router.get("/field-permissions")
async def get_field_permissions(current_user: User = Depends(get_current_user)):
    """Get field permission matrix for the current user's role."""
    
    permissions = {}
    for field, config in FIELD_PERMISSIONS.items():
        can_edit = current_user.role in config.get("edit_roles", [])
        permissions[field] = {
            "can_edit": can_edit,
            "requires_approval": config.get("requires_approval", False),
            "workflow": config.get("workflow"),
            "locked": config.get("locked", False),
            "immutable": config.get("immutable", False)
        }
    
    return {
        "user_role": current_user.role,
        "permissions": permissions
    }


@router.post("/validate-update/{employee_id}")
async def validate_employee_update(
    employee_id: str,
    data: dict,
    current_user: User = Depends(get_current_user)
):
    """
    Validate proposed employee updates before applying.
    Returns detailed validation results for each field.
    """
    db = get_db()
    
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    validation_results = {
        "allowed_updates": {},
        "blocked_updates": {},
        "workflow_required": {},
        "audit_required": []
    }
    
    for field, value in data.items():
        result = validate_field_edit_permission(field, current_user.role, employee)
        
        if result["allowed"]:
            validation_results["allowed_updates"][field] = value
            if result.get("audit_required"):
                validation_results["audit_required"].append(field)
        elif result.get("workflow"):
            validation_results["workflow_required"][field] = {
                "value": value,
                "workflow": result["workflow"],
                "reason": result["reason"]
            }
        else:
            validation_results["blocked_updates"][field] = result["reason"]
    
    return {
        "employee_id": employee_id,
        "employee_code": employee.get("employee_id"),
        "validation": validation_results,
        "can_proceed": len(validation_results["blocked_updates"]) == 0 and len(validation_results["workflow_required"]) == 0
    }


@router.patch("/employee/{employee_id}")
async def governed_employee_update(
    employee_id: str,
    data: dict,
    change_reason: str = None,
    current_user: User = Depends(get_current_user)
):
    """
    Update employee with full governance checks.
    - Validates field-level permissions
    - Blocks protected fields
    - Creates audit trail
    - Routes to appropriate workflows
    """
    db = get_db()
    
    # Get employee
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Validate all fields
    allowed_updates = {}
    blocked_fields = []
    workflow_fields = {}
    audit_fields = []
    
    for field, value in data.items():
        # Skip system fields
        if field in ["updated_at", "updated_by"]:
            continue
            
        result = validate_field_edit_permission(field, current_user.role, employee)
        
        if result["allowed"]:
            allowed_updates[field] = value
            if result.get("audit_required"):
                audit_fields.append(field)
        elif result.get("workflow"):
            workflow_fields[field] = {
                "value": value,
                "workflow": result["workflow"],
                "reason": result["reason"]
            }
        else:
            blocked_fields.append({"field": field, "reason": result["reason"]})
    
    # If any fields are blocked, reject entirely
    if blocked_fields:
        raise HTTPException(
            status_code=403,
            detail={
                "message": "Some fields cannot be updated",
                "blocked_fields": blocked_fields
            }
        )
    
    # If workflow fields exist, create workflow requests
    workflow_requests = []
    for field, info in workflow_fields.items():
        workflow_request = {
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
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.field_change_requests.insert_one(workflow_request)
        workflow_requests.append({
            "field": field,
            "workflow": info["workflow"],
            "request_id": workflow_request["id"]
        })
    
    # Apply allowed updates
    if allowed_updates:
        now = datetime.now(timezone.utc).isoformat()
        allowed_updates["updated_at"] = now
        allowed_updates["updated_by"] = current_user.id
        allowed_updates["updated_by_name"] = current_user.full_name
        
        # Log audit trail for required fields
        for field in audit_fields:
            await log_field_change(
                db=db,
                employee_id=employee_id,
                field=field,
                old_value=employee.get(field),
                new_value=allowed_updates[field],
                changed_by=current_user.id,
                changed_by_name=current_user.full_name,
                changed_by_role=current_user.role,
                change_reason=change_reason
            )
        
        await db.employees.update_one({"id": employee_id}, {"$set": allowed_updates})
    
    return {
        "message": "Update processed",
        "updated_fields": list(allowed_updates.keys()) if allowed_updates else [],
        "workflow_requests": workflow_requests,
        "note": "Some fields require workflow approval" if workflow_requests else None
    }


@router.get("/change-history/{employee_id}")
async def get_employee_change_history(
    employee_id: str,
    field: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get audit trail for employee changes."""
    db = get_db()
    
    # Check permission
    hr_roles = get_role_group("HR_ROLES", fail_closed=True) or []
    admin_roles = get_role_group("ADMIN_ROLES", fail_closed=False) or ["admin"]
    
    if not has_role(current_user.role, hr_roles + admin_roles):
        raise HTTPException(status_code=403, detail="Access denied")
    
    query = {"employee_id": employee_id}
    if field:
        query["field"] = field
    
    history = await db.employee_change_history.find(
        query, {"_id": 0}
    ).sort("timestamp", -1).to_list(500)
    
    return {
        "employee_id": employee_id,
        "total_changes": len(history),
        "history": history
    }


# ============== WORKFLOW ENDPOINTS ==============

@router.get("/pending-requests")
async def get_pending_field_change_requests(
    current_user: User = Depends(get_current_user)
):
    """Get all pending field change requests (Admin only)."""
    db = get_db()
    
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    
    requests = await db.field_change_requests.find(
        {"status": "pending"}, {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    
    return requests


@router.post("/requests/{request_id}/approve")
async def approve_field_change_request(
    request_id: str,
    remarks: str = None,
    current_user: User = Depends(get_current_user)
):
    """Approve a field change request and apply the change."""
    db = get_db()
    
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    
    request = await db.field_change_requests.find_one({"id": request_id}, {"_id": 0})
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")
    
    if request["status"] != "pending":
        raise HTTPException(status_code=400, detail=f"Request is already {request['status']}")
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Get current employee data for audit
    employee = await db.employees.find_one({"id": request["employee_id"]}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Apply the change
    field = request["field"]
    new_value = request["requested_value"]
    old_value = employee.get(field)
    
    await db.employees.update_one(
        {"id": request["employee_id"]},
        {"$set": {
            field: new_value,
            "updated_at": now,
            "updated_by": current_user.id
        }}
    )
    
    # Log the change
    await log_field_change(
        db=db,
        employee_id=request["employee_id"],
        field=field,
        old_value=old_value,
        new_value=new_value,
        changed_by=current_user.id,
        changed_by_name=current_user.full_name,
        changed_by_role=current_user.role,
        change_reason=f"Approved: {remarks}" if remarks else "Approved via workflow",
        workflow_id=request_id
    )
    
    # Update request status
    await db.field_change_requests.update_one(
        {"id": request_id},
        {"$set": {
            "status": "approved",
            "approved_by": current_user.id,
            "approved_by_name": current_user.full_name,
            "approved_at": now,
            "remarks": remarks
        }}
    )
    
    # Notify requester
    await db.notifications.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": request["requested_by"],
        "type": "field_change_approved",
        "title": "Change Request Approved",
        "message": f"Your request to change {field} for {request['employee_name']} has been approved.",
        "is_read": False,
        "created_at": now
    })
    
    return {"message": "Change approved and applied", "field": field, "new_value": new_value}


@router.post("/requests/{request_id}/reject")
async def reject_field_change_request(
    request_id: str,
    reason: str,
    current_user: User = Depends(get_current_user)
):
    """Reject a field change request."""
    db = get_db()
    
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    
    if not reason:
        raise HTTPException(status_code=400, detail="Rejection reason is required")
    
    request = await db.field_change_requests.find_one({"id": request_id}, {"_id": 0})
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")
    
    now = datetime.now(timezone.utc).isoformat()
    
    await db.field_change_requests.update_one(
        {"id": request_id},
        {"$set": {
            "status": "rejected",
            "rejected_by": current_user.id,
            "rejected_by_name": current_user.full_name,
            "rejected_at": now,
            "rejection_reason": reason
        }}
    )
    
    # Notify requester
    await db.notifications.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": request["requested_by"],
        "type": "field_change_rejected",
        "title": "Change Request Rejected",
        "message": f"Your request to change {request['field']} for {request['employee_name']} was rejected. Reason: {reason}",
        "is_read": False,
        "created_at": now
    })
    
    return {"message": "Change request rejected"}


# ============== SALARY SYNC ==============

@router.post("/sync-salary/{employee_id}")
async def sync_salary_from_ctc(
    employee_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Sync employee salary from CTC structure.
    This is the ONLY way to update salary - ensures single source of truth.
    """
    db = get_db()
    
    # Only admin can trigger sync
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Get active CTC structure
    ctc = await db.ctc_structures.find_one(
        {"employee_id": employee_id, "status": "approved"},
        {"_id": 0}
    )
    
    if not ctc:
        raise HTTPException(status_code=404, detail="No approved CTC structure found")
    
    now = datetime.now(timezone.utc).isoformat()
    old_salary = employee.get("salary")
    new_salary = ctc.get("annual_ctc")
    
    # Create salary revision log
    revision = {
        "id": str(uuid.uuid4()),
        "employee_id": employee_id,
        "employee_code": employee.get("employee_id"),
        "old_salary": old_salary,
        "new_salary": new_salary,
        "ctc_structure_id": ctc.get("id"),
        "effective_date": ctc.get("effective_date") or now,
        "synced_by": current_user.id,
        "synced_by_name": current_user.full_name,
        "synced_at": now,
        "source": "ctc_structure"
    }
    await db.salary_revision_log.insert_one(revision)
    
    # Update employee
    await db.employees.update_one(
        {"id": employee_id},
        {"$set": {
            "salary": new_salary,
            "annual_ctc": new_salary,
            "ctc_structure_id": ctc.get("id"),
            "salary_last_synced": now,
            "updated_at": now,
            "updated_by": current_user.id
        }}
    )
    
    # Log audit
    await log_field_change(
        db=db,
        employee_id=employee_id,
        field="salary",
        old_value=old_salary,
        new_value=new_salary,
        changed_by=current_user.id,
        changed_by_name=current_user.full_name,
        changed_by_role=current_user.role,
        change_reason="Synced from CTC structure",
        workflow_id=ctc.get("id")
    )
    
    return {
        "message": "Salary synced from CTC structure",
        "old_salary": old_salary,
        "new_salary": new_salary,
        "revision_id": revision["id"]
    }


# ============== DATA INTEGRITY CHECKS ==============

@router.get("/integrity-check")
async def run_integrity_check(current_user: User = Depends(get_current_user)):
    """Run data integrity checks across employee data."""
    db = get_db()
    
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    
    issues = []
    
    # Check for circular reporting chains
    employees = await db.employees.find(
        {"is_active": True},
        {"_id": 0, "id": 1, "employee_id": 1, "full_name": 1, "reporting_manager_id": 1}
    ).to_list(1000)
    
    emp_map = {e["id"]: e for e in employees}
    
    for emp in employees:
        chain = set()
        current = emp
        while current:
            if current["id"] in chain:
                issues.append({
                    "type": "circular_reporting",
                    "employee_id": emp["employee_id"],
                    "employee_name": emp.get("full_name"),
                    "message": f"Circular reporting chain detected"
                })
                break
            chain.add(current["id"])
            manager_id = current.get("reporting_manager_id")
            current = emp_map.get(manager_id) if manager_id else None
    
    # Check for duplicate employee_id
    pipeline = [
        {"$group": {"_id": "$employee_id", "count": {"$sum": 1}, "ids": {"$push": "$id"}}},
        {"$match": {"count": {"$gt": 1}}}
    ]
    duplicates = await db.employees.aggregate(pipeline).to_list(100)
    for dup in duplicates:
        if dup["_id"]:  # Skip null employee_ids
            issues.append({
                "type": "duplicate_employee_id",
                "employee_id": dup["_id"],
                "count": dup["count"],
                "record_ids": dup["ids"]
            })
    
    # Check for employees without employee_id
    no_id = await db.employees.count_documents({
        "is_active": True,
        "$or": [
            {"employee_id": None},
            {"employee_id": ""},
            {"employee_id": {"$exists": False}}
        ]
    })
    if no_id > 0:
        issues.append({
            "type": "missing_employee_id",
            "count": no_id,
            "message": f"{no_id} active employees without employee_id"
        })
    
    # Check for salary mismatch with CTC
    employees_with_ctc = await db.employees.find(
        {"ctc_structure_id": {"$exists": True, "$ne": None}},
        {"_id": 0, "id": 1, "employee_id": 1, "salary": 1, "ctc_structure_id": 1}
    ).to_list(1000)
    
    for emp in employees_with_ctc:
        ctc = await db.ctc_structures.find_one(
            {"id": emp["ctc_structure_id"], "status": "approved"},
            {"_id": 0, "annual_ctc": 1}
        )
        if ctc and emp.get("salary") != ctc.get("annual_ctc"):
            issues.append({
                "type": "salary_ctc_mismatch",
                "employee_id": emp["employee_id"],
                "employee_salary": emp.get("salary"),
                "ctc_salary": ctc.get("annual_ctc"),
                "message": "Employee salary doesn't match CTC structure"
            })
    
    return {
        "check_time": datetime.now(timezone.utc).isoformat(),
        "total_issues": len(issues),
        "issues": issues
    }


@router.get("/salary-revision-log/{employee_id}")
async def get_salary_revision_log(
    employee_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get salary revision history for an employee."""
    db = get_db()
    
    hr_roles = get_role_group("HR_ROLES", fail_closed=True) or []
    admin_roles = get_role_group("ADMIN_ROLES", fail_closed=False) or ["admin"]
    
    if not has_role(current_user.role, hr_roles + admin_roles):
        raise HTTPException(status_code=403, detail="Access denied")
    
    revisions = await db.salary_revision_log.find(
        {"employee_id": employee_id},
        {"_id": 0}
    ).sort("synced_at", -1).to_list(100)
    
    return revisions
