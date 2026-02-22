"""
Enhanced Permission System - Employee-Level Granular Permissions
Supports:
- Feature flags per employee
- API endpoint access control
- Sidebar visibility control
- Dual approval workflows
- Custom permission overrides
"""

from fastapi import APIRouter, HTTPException, Depends, status
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Set
from pydantic import BaseModel, Field
from enum import Enum
import uuid

from .deps import get_db, ADMIN_ROLES, HR_ADMIN_ROLES
from .auth import get_current_user
from .models import User

router = APIRouter(prefix="/permissions", tags=["Permissions"])


# ============== Permission Constants ==============

class PermissionCategory(str, Enum):
    SALES = "sales"
    HR = "hr"
    CONSULTING = "consulting"
    FINANCE = "finance"
    ADMIN = "admin"
    PERSONAL = "personal"


# Master list of all controllable features
FEATURE_FLAGS = {
    # Sales Features
    "sales.view_leads": {"category": "sales", "label": "View Leads", "default_roles": ["admin", "sales_manager", "executive", "sales_executive", "manager"]},
    "sales.create_leads": {"category": "sales", "label": "Create Leads", "default_roles": ["admin", "sales_manager", "executive", "sales_executive"]},
    "sales.delete_leads": {"category": "sales", "label": "Delete Leads", "default_roles": ["admin"]},
    "sales.reassign_leads": {"category": "sales", "label": "Reassign Leads", "default_roles": ["admin", "sales_manager", "manager"]},
    "sales.view_agreements": {"category": "sales", "label": "View Agreements", "default_roles": ["admin", "sales_manager", "principal_consultant", "executive", "sales_executive"]},
    "sales.create_agreements": {"category": "sales", "label": "Create Agreements", "default_roles": ["admin", "sales_manager"]},
    "sales.view_pricing": {"category": "sales", "label": "View Pricing Plans", "default_roles": ["admin", "sales_manager", "executive", "sales_executive"]},
    "sales.approve_pricing": {"category": "sales", "label": "Approve Pricing", "default_roles": ["admin", "sales_manager", "principal_consultant"]},
    "sales.view_sow": {"category": "sales", "label": "View SOW", "default_roles": ["admin", "sales_manager", "executive", "sales_executive", "consultant", "principal_consultant"]},
    "sales.approve_sow": {"category": "sales", "label": "Approve SOW", "default_roles": ["admin", "sales_manager", "manager"]},
    "sales.view_quotations": {"category": "sales", "label": "View Quotations", "default_roles": ["admin", "sales_manager", "executive", "sales_executive"]},
    "sales.view_pipeline": {"category": "sales", "label": "View Sales Pipeline", "default_roles": ["admin", "sales_manager", "manager"]},
    "sales.view_team_leads": {"category": "sales", "label": "View Team Leads", "default_roles": ["admin", "sales_manager", "manager"]},
    "sales.manage_targets": {"category": "sales", "label": "Manage Targets", "default_roles": ["admin", "sales_manager", "manager"]},
    
    # HR Features
    "hr.view_employees": {"category": "hr", "label": "View All Employees", "default_roles": ["admin", "hr_manager", "hr_executive"]},
    "hr.edit_employees": {"category": "hr", "label": "Edit Employee Data", "default_roles": ["admin", "hr_manager"]},
    "hr.view_attendance": {"category": "hr", "label": "View All Attendance", "default_roles": ["admin", "hr_manager", "hr_executive"]},
    "hr.manage_attendance": {"category": "hr", "label": "Manage Attendance", "default_roles": ["admin", "hr_manager"]},
    "hr.view_payroll": {"category": "hr", "label": "View Payroll", "default_roles": ["admin", "hr_manager"]},
    "hr.manage_payroll": {"category": "hr", "label": "Manage Payroll", "default_roles": ["admin", "hr_manager"]},
    "hr.approve_leaves": {"category": "hr", "label": "Approve Leaves", "default_roles": ["admin", "hr_manager", "manager"]},
    "hr.manage_onboarding": {"category": "hr", "label": "Manage Onboarding", "default_roles": ["admin", "hr_manager", "hr_executive"]},
    "hr.view_ctc": {"category": "hr", "label": "View CTC Details", "default_roles": ["admin", "hr_manager"]},
    "hr.design_ctc": {"category": "hr", "label": "Design CTC Packages", "default_roles": ["admin", "hr_manager"]},
    "hr.manage_leave_policies": {"category": "hr", "label": "Manage Leave Policies", "default_roles": ["admin", "hr_manager"]},
    
    # Consulting Features
    "consulting.view_projects": {"category": "consulting", "label": "View Projects", "default_roles": ["admin", "principal_consultant", "senior_consultant", "consultant"]},
    "consulting.manage_projects": {"category": "consulting", "label": "Manage Projects", "default_roles": ["admin", "principal_consultant"]},
    "consulting.view_timesheets": {"category": "consulting", "label": "View All Timesheets", "default_roles": ["admin", "hr_manager", "principal_consultant", "manager"]},
    "consulting.approve_timesheets": {"category": "consulting", "label": "Approve Timesheets", "default_roles": ["admin", "principal_consultant", "manager"]},
    "consulting.view_project_financials": {"category": "consulting", "label": "View Project Financials", "default_roles": ["admin", "principal_consultant"]},
    "consulting.assign_team": {"category": "consulting", "label": "Assign Team Members", "default_roles": ["admin", "principal_consultant"]},
    "consulting.record_payments": {"category": "consulting", "label": "Record Payments", "default_roles": ["admin", "principal_consultant", "consultant"]},
    
    # Finance Features
    "finance.view_invoices": {"category": "finance", "label": "View Invoices", "default_roles": ["admin", "finance_manager", "principal_consultant"]},
    "finance.create_invoices": {"category": "finance", "label": "Create Invoices", "default_roles": ["admin", "finance_manager"]},
    "finance.view_payments": {"category": "finance", "label": "View All Payments", "default_roles": ["admin", "finance_manager", "principal_consultant"]},
    "finance.approve_expenses": {"category": "finance", "label": "Approve Expenses", "default_roles": ["admin", "finance_manager", "manager"]},
    "finance.view_reports": {"category": "finance", "label": "View Financial Reports", "default_roles": ["admin", "finance_manager", "principal_consultant"]},
    
    # Admin Features
    "admin.manage_users": {"category": "admin", "label": "Manage Users", "default_roles": ["admin"]},
    "admin.manage_roles": {"category": "admin", "label": "Manage Roles", "default_roles": ["admin"]},
    "admin.manage_permissions": {"category": "admin", "label": "Manage Permissions", "default_roles": ["admin"]},
    "admin.view_audit_logs": {"category": "admin", "label": "View Audit Logs", "default_roles": ["admin"]},
    "admin.manage_masters": {"category": "admin", "label": "Manage Master Data", "default_roles": ["admin"]},
    "admin.view_all_data": {"category": "admin", "label": "View All Data", "default_roles": ["admin"]},
    
    # Personal/Self-Service (always enabled for self)
    "personal.view_own_attendance": {"category": "personal", "label": "View Own Attendance", "default_roles": ["*"]},
    "personal.view_own_leaves": {"category": "personal", "label": "View Own Leaves", "default_roles": ["*"]},
    "personal.view_own_salary": {"category": "personal", "label": "View Own Salary", "default_roles": ["*"]},
    "personal.view_own_expenses": {"category": "personal", "label": "View Own Expenses", "default_roles": ["*"]},
    "personal.submit_leave_request": {"category": "personal", "label": "Submit Leave Request", "default_roles": ["*"]},
    "personal.submit_expense_claim": {"category": "personal", "label": "Submit Expense Claim", "default_roles": ["*"]},
    "personal.view_own_scorecard": {"category": "personal", "label": "View Own Scorecard", "default_roles": ["*"]},
}

# Sidebar sections mapping to features
SIDEBAR_FEATURE_MAPPING = {
    "hr_section": ["hr.view_employees", "hr.view_attendance", "hr.view_payroll"],
    "sales_section": ["sales.view_leads", "sales.view_agreements", "sales.view_pipeline"],
    "consulting_section": ["consulting.view_projects", "consulting.view_timesheets"],
    "admin_section": ["admin.manage_users", "admin.manage_roles", "admin.manage_permissions"],
}


# ============== Pydantic Models ==============

class EmployeePermissionOverride(BaseModel):
    """Override permissions for a specific employee"""
    employee_id: str
    granted_features: List[str] = Field(default=[], description="Features to grant beyond role defaults")
    revoked_features: List[str] = Field(default=[], description="Features to revoke from role defaults")
    custom_sidebar_sections: List[str] = Field(default=[], description="Additional sidebar sections")
    hidden_sidebar_sections: List[str] = Field(default=[], description="Sidebar sections to hide")
    can_approve_for: List[str] = Field(default=[], description="Employee IDs this person can approve for")
    approval_authority: Dict[str, List[str]] = Field(default={}, description="Map of approval type to allowed stages")
    data_scope: str = Field(default="self", description="self, team, department, all")
    notes: Optional[str] = None
    effective_from: Optional[str] = None
    effective_until: Optional[str] = None
    granted_by: Optional[str] = None


class BulkPermissionUpdate(BaseModel):
    """Update permissions for multiple employees"""
    employee_ids: List[str]
    grant_features: List[str] = []
    revoke_features: List[str] = []


class ApprovalConfig(BaseModel):
    """Configure dual/multi approval requirements"""
    feature: str
    min_approvers: int = 1
    required_roles: List[str] = []
    any_of_roles: List[str] = []  # Any one of these roles can approve
    requires_sequence: bool = False  # Must approve in order


# ============== Permission Check Utilities ==============

async def get_employee_permissions(employee_id: str, role: str) -> Dict[str, Any]:
    """
    Get effective permissions for an employee.
    Combines role defaults + employee overrides.
    """
    db = get_db()
    
    # Start with role-based defaults
    effective_permissions = {}
    for feature_key, feature_config in FEATURE_FLAGS.items():
        default_roles = feature_config.get("default_roles", [])
        if "*" in default_roles or role in default_roles:
            effective_permissions[feature_key] = True
        else:
            effective_permissions[feature_key] = False
    
    # Apply employee-specific overrides
    override = await db.employee_permissions.find_one(
        {"employee_id": employee_id},
        {"_id": 0}
    )
    
    if override:
        # Check if override is still valid
        now = datetime.now(timezone.utc).isoformat()
        effective_from = override.get("effective_from")
        effective_until = override.get("effective_until")
        
        is_valid = True
        if effective_from and effective_from > now:
            is_valid = False
        if effective_until and effective_until < now:
            is_valid = False
        
        if is_valid:
            # Grant additional features
            for feature in override.get("granted_features", []):
                if feature in effective_permissions:
                    effective_permissions[feature] = True
            
            # Revoke features
            for feature in override.get("revoked_features", []):
                if feature in effective_permissions:
                    effective_permissions[feature] = False
    
    return {
        "employee_id": employee_id,
        "role": role,
        "permissions": effective_permissions,
        "has_overrides": override is not None,
        "override_details": override
    }


async def check_permission(employee_id: str, role: str, feature: str) -> bool:
    """Check if employee has a specific permission"""
    perms = await get_employee_permissions(employee_id, role)
    return perms["permissions"].get(feature, False)


async def get_sidebar_visibility(employee_id: str, role: str) -> Dict[str, bool]:
    """Get which sidebar sections should be visible for employee"""
    perms = await get_employee_permissions(employee_id, role)
    
    visibility = {}
    for section, required_features in SIDEBAR_FEATURE_MAPPING.items():
        # Section visible if employee has ANY of the required features
        visibility[section] = any(
            perms["permissions"].get(f, False) for f in required_features
        )
    
    # Apply custom overrides
    override = perms.get("override_details")
    if override:
        for section in override.get("custom_sidebar_sections", []):
            visibility[section] = True
        for section in override.get("hidden_sidebar_sections", []):
            visibility[section] = False
    
    return visibility


# ============== API Endpoints ==============

@router.get("/features")
async def get_all_features(current_user: User = Depends(get_current_user)):
    """Get list of all controllable features with their defaults"""
    if current_user.role not in ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Admin only")
    
    return {
        "features": FEATURE_FLAGS,
        "categories": [c.value for c in PermissionCategory],
        "sidebar_mapping": SIDEBAR_FEATURE_MAPPING
    }


@router.get("/my-permissions")
async def get_my_permissions(current_user: User = Depends(get_current_user)):
    """Get current user's effective permissions"""
    perms = await get_employee_permissions(current_user.id, current_user.role)
    sidebar = await get_sidebar_visibility(current_user.id, current_user.role)
    
    return {
        **perms,
        "sidebar_visibility": sidebar
    }


@router.get("/employee/{employee_id}")
async def get_employee_permission_details(
    employee_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get permissions for a specific employee (Admin/HR only)"""
    if current_user.role not in HR_ADMIN_ROLES and current_user.id != employee_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    db = get_db()
    
    # Get employee info
    employee = await db.employees.find_one({"employee_id": employee_id}, {"_id": 0})
    if not employee:
        employee = await db.users.find_one({"employee_id": employee_id}, {"_id": 0})
    
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    user_id = employee.get("user_id") or employee.get("id")
    role = employee.get("role", "executive")
    
    perms = await get_employee_permissions(user_id, role)
    sidebar = await get_sidebar_visibility(user_id, role)
    
    return {
        "employee": {
            "employee_id": employee_id,
            "name": employee.get("full_name"),
            "role": role,
            "department": employee.get("department")
        },
        **perms,
        "sidebar_visibility": sidebar
    }


@router.put("/employee/{employee_id}")
async def update_employee_permissions(
    employee_id: str,
    override: EmployeePermissionOverride,
    current_user: User = Depends(get_current_user)
):
    """Update permissions for a specific employee (Admin only)"""
    if current_user.role not in ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Admin only")
    
    db = get_db()
    
    # Validate features exist
    for feature in override.granted_features + override.revoked_features:
        if feature not in FEATURE_FLAGS:
            raise HTTPException(status_code=400, detail=f"Invalid feature: {feature}")
    
    override_doc = {
        **override.dict(),
        "updated_by": current_user.id,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.employee_permissions.update_one(
        {"employee_id": employee_id},
        {"$set": override_doc},
        upsert=True
    )
    
    # Log the change
    await db.audit_logs.insert_one({
        "id": str(uuid.uuid4()),
        "action": "permission_update",
        "entity_type": "employee_permission",
        "entity_id": employee_id,
        "changes": override.dict(),
        "performed_by": current_user.id,
        "performed_at": datetime.now(timezone.utc).isoformat()
    })
    
    return {"status": "success", "message": f"Permissions updated for {employee_id}"}


@router.post("/bulk-update")
async def bulk_update_permissions(
    update: BulkPermissionUpdate,
    current_user: User = Depends(get_current_user)
):
    """Update permissions for multiple employees at once"""
    if current_user.role not in ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Admin only")
    
    db = get_db()
    updated_count = 0
    
    for emp_id in update.employee_ids:
        existing = await db.employee_permissions.find_one({"employee_id": emp_id})
        
        granted = set(existing.get("granted_features", []) if existing else [])
        revoked = set(existing.get("revoked_features", []) if existing else [])
        
        # Apply updates
        granted.update(update.grant_features)
        granted -= set(update.revoke_features)
        revoked.update(update.revoke_features)
        revoked -= set(update.grant_features)
        
        await db.employee_permissions.update_one(
            {"employee_id": emp_id},
            {"$set": {
                "granted_features": list(granted),
                "revoked_features": list(revoked),
                "updated_by": current_user.id,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }},
            upsert=True
        )
        updated_count += 1
    
    return {"status": "success", "updated_count": updated_count}


@router.delete("/employee/{employee_id}")
async def reset_employee_permissions(
    employee_id: str,
    current_user: User = Depends(get_current_user)
):
    """Reset employee permissions to role defaults"""
    if current_user.role not in ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Admin only")
    
    db = get_db()
    result = await db.employee_permissions.delete_one({"employee_id": employee_id})
    
    return {
        "status": "success",
        "message": f"Permissions reset for {employee_id}",
        "deleted": result.deleted_count > 0
    }


# ============== Approval Configuration ==============

@router.get("/approval-config")
async def get_approval_configs(current_user: User = Depends(get_current_user)):
    """Get all approval configurations"""
    if current_user.role not in ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Admin only")
    
    db = get_db()
    configs = await db.approval_configs.find({}, {"_id": 0}).to_list(100)
    
    # Return defaults if none configured
    if not configs:
        return {
            "configs": [
                {"feature": "sales.approve_pricing", "min_approvers": 2, "any_of_roles": ["sales_manager", "principal_consultant", "admin"]},
                {"feature": "sales.approve_sow", "min_approvers": 1, "required_roles": ["sales_manager", "manager"]},
                {"feature": "consulting.approve_timesheets", "min_approvers": 1, "any_of_roles": ["principal_consultant", "manager"]},
                {"feature": "hr.approve_leaves", "min_approvers": 1, "any_of_roles": ["hr_manager", "manager"]},
            ]
        }
    
    return {"configs": configs}


@router.put("/approval-config/{feature}")
async def update_approval_config(
    feature: str,
    config: ApprovalConfig,
    current_user: User = Depends(get_current_user)
):
    """Update approval configuration for a feature"""
    if current_user.role not in ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Admin only")
    
    db = get_db()
    await db.approval_configs.update_one(
        {"feature": feature},
        {"$set": config.dict()},
        upsert=True
    )
    
    return {"status": "success"}


# ============== Permission Check Endpoint ==============

@router.post("/check")
async def check_user_permission(
    feature: str,
    current_user: User = Depends(get_current_user)
):
    """Check if current user has a specific permission"""
    has_permission = await check_permission(current_user.id, current_user.role, feature)
    
    return {
        "feature": feature,
        "has_permission": has_permission,
        "user_role": current_user.role
    }
