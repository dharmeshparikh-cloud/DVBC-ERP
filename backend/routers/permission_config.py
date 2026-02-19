"""
Department & Employee Permission Configuration
- Configurable departments via Admin Masters
- Employee-level special permissions
- Temporary cross-functional access
"""

from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
import uuid

from .deps import get_db
from .auth import get_current_user
from .models import User

router = APIRouter(prefix="/permission-config", tags=["Permission Configuration"])


# ============== Pydantic Models ==============

class DepartmentCreate(BaseModel):
    """Create a new department"""
    name: str = Field(..., description="Department name (e.g., Marketing)")
    code: str = Field(..., description="Short code (e.g., MKT)")
    description: Optional[str] = None
    pages: List[str] = Field(default=[], description="List of page routes this dept can access")
    icon: str = Field(default="Building2", description="Lucide icon name")
    color: str = Field(default="#6B7280", description="Hex color code")
    is_active: bool = True


class DepartmentUpdate(BaseModel):
    """Update department"""
    name: Optional[str] = None
    description: Optional[str] = None
    pages: Optional[List[str]] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    is_active: Optional[bool] = None


class SpecialPermission(BaseModel):
    """Employee special permission entry"""
    permission_type: str = Field(..., description="Type: department_access, page_access, role_override")
    value: str = Field(..., description="Department name, page route, or role name")
    reason: str = Field(..., description="Why this permission was granted")
    is_temporary: bool = False
    expiry_date: Optional[str] = None  # ISO date string
    granted_by: Optional[str] = None
    granted_at: Optional[str] = None


class EmployeeSpecialPermissions(BaseModel):
    """Update employee special permissions"""
    additional_departments: List[str] = Field(default=[], description="Extra departments beyond primary")
    additional_pages: List[str] = Field(default=[], description="Specific pages to grant")
    restricted_pages: List[str] = Field(default=[], description="Pages to block")
    temporary_role: Optional[str] = Field(None, description="Temporary role override")
    temporary_role_expiry: Optional[str] = None
    can_approve_for_departments: List[str] = Field(default=[], description="Departments this person can approve for")
    special_permissions: List[SpecialPermission] = Field(default=[], description="Detailed permission entries")
    notes: Optional[str] = None


# ============== Department Configuration APIs ==============

@router.get("/departments")
async def get_configurable_departments(
    include_inactive: bool = False,
    current_user: User = Depends(get_current_user)
):
    """Get all configurable departments from database"""
    db = get_db()
    
    query = {} if include_inactive else {"is_active": True}
    departments = await db.department_config.find(query, {"_id": 0}).sort("order", 1).to_list(100)
    
    # If no departments configured, return defaults
    if not departments:
        departments = [
            {"id": "sales", "name": "Sales", "code": "SALES", "description": "Sales and business development", 
             "pages": ["/leads", "/meetings", "/sales", "/pricing", "/sow", "/quotations", "/proforma", "/agreements", "/kickoff-requests", "/payment-verification", "/clients"],
             "icon": "TrendingUp", "color": "#F97316", "is_active": True, "order": 1},
            {"id": "hr", "name": "HR", "code": "HR", "description": "Human resources management",
             "pages": ["/employees", "/attendance", "/leave-management", "/payroll", "/ctc-designer", "/onboarding", "/letter-management", "/hr", "/attendance-approvals", "/performance-dashboard", "/travel-reimbursement"],
             "icon": "Users", "color": "#10B981", "is_active": True, "order": 2},
            {"id": "consulting", "name": "Consulting", "code": "CONSULT", "description": "Project delivery and consulting",
             "pages": ["/projects", "/consulting", "/consultant", "/timesheets", "/payments", "/gantt-chart", "/project-roadmap"],
             "icon": "Briefcase", "color": "#8B5CF6", "is_active": True, "order": 3},
            {"id": "finance", "name": "Finance", "code": "FIN", "description": "Financial management",
             "pages": ["/payments", "/expenses", "/reports", "/finance"],
             "icon": "DollarSign", "color": "#3B82F6", "is_active": True, "order": 4},
            {"id": "admin", "name": "Admin", "code": "ADMIN", "description": "System administration - full access",
             "pages": ["*"],
             "icon": "Shield", "color": "#EF4444", "is_active": True, "order": 5},
        ]
    
    return {"departments": departments, "total": len(departments)}


@router.post("/departments")
async def create_department(
    dept: DepartmentCreate,
    current_user: User = Depends(get_current_user)
):
    """Create a new department (Admin only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    db = get_db()
    
    # Check if department with same name/code exists
    existing = await db.department_config.find_one({
        "$or": [{"name": dept.name}, {"code": dept.code}]
    })
    if existing:
        raise HTTPException(status_code=400, detail="Department with this name or code already exists")
    
    # Get next order
    max_order = await db.department_config.find_one(sort=[("order", -1)])
    next_order = (max_order.get("order", 0) + 1) if max_order else 1
    
    department = {
        "id": str(uuid.uuid4()),
        "name": dept.name,
        "code": dept.code.upper(),
        "description": dept.description,
        "pages": dept.pages,
        "icon": dept.icon,
        "color": dept.color,
        "is_active": dept.is_active,
        "order": next_order,
        "created_by": current_user.id,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.department_config.insert_one(department)
    department.pop("_id", None)
    
    return {"message": "Department created", "department": department}


@router.put("/departments/{dept_id}")
async def update_department(
    dept_id: str,
    update: DepartmentUpdate,
    current_user: User = Depends(get_current_user)
):
    """Update a department (Admin only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    db = get_db()
    
    existing = await db.department_config.find_one({"id": dept_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Department not found")
    
    update_data = {k: v for k, v in update.dict().items() if v is not None}
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    update_data["updated_by"] = current_user.id
    
    await db.department_config.update_one({"id": dept_id}, {"$set": update_data})
    
    return {"message": "Department updated"}


@router.delete("/departments/{dept_id}")
async def delete_department(
    dept_id: str,
    current_user: User = Depends(get_current_user)
):
    """Soft delete a department (Admin only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    db = get_db()
    
    # Check if any employees are assigned to this department
    emp_count = await db.employees.count_documents({
        "$or": [
            {"departments": dept_id},
            {"primary_department": dept_id}
        ]
    })
    
    if emp_count > 0:
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot delete: {emp_count} employees are assigned to this department. Reassign them first."
        )
    
    await db.department_config.update_one(
        {"id": dept_id},
        {"$set": {"is_active": False, "deleted_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    return {"message": "Department deactivated"}


# ============== Employee Special Permissions APIs ==============

@router.get("/employee/{employee_id}/special-permissions")
async def get_employee_special_permissions(
    employee_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get special permissions for an employee"""
    if current_user.role not in ["admin", "hr_manager"]:
        raise HTTPException(status_code=403, detail="Admin or HR Manager access required")
    
    db = get_db()
    
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Get all special permissions fields
    return {
        "employee_id": employee_id,
        "employee_name": f"{employee.get('first_name', '')} {employee.get('last_name', '')}".strip(),
        "employee_code": employee.get("employee_id"),
        "primary_department": employee.get("primary_department"),
        "base_departments": employee.get("departments", []),
        "designation": employee.get("designation"),
        "level": employee.get("level", "executive"),
        "role": employee.get("role"),
        # Special permissions
        "additional_departments": employee.get("additional_departments", []),
        "additional_pages": employee.get("additional_pages", []),
        "restricted_pages": employee.get("restricted_pages", []),
        "temporary_role": employee.get("temporary_role"),
        "temporary_role_expiry": employee.get("temporary_role_expiry"),
        "can_approve_for_departments": employee.get("can_approve_for_departments", []),
        "special_permissions": employee.get("special_permissions", []),
        "permission_notes": employee.get("permission_notes"),
        # Computed effective access
        "effective_departments": list(set(
            employee.get("departments", []) + 
            employee.get("additional_departments", [])
        )),
    }


@router.put("/employee/{employee_id}/special-permissions")
async def update_employee_special_permissions(
    employee_id: str,
    permissions: EmployeeSpecialPermissions,
    current_user: User = Depends(get_current_user)
):
    """Update special permissions for an employee (Admin/HR Manager only)"""
    if current_user.role not in ["admin", "hr_manager"]:
        raise HTTPException(status_code=403, detail="Admin or HR Manager access required")
    
    db = get_db()
    
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Prepare special permissions with audit info
    special_perms = []
    for perm in permissions.special_permissions:
        perm_dict = perm.dict()
        perm_dict["granted_by"] = current_user.id
        perm_dict["granted_by_name"] = current_user.full_name
        perm_dict["granted_at"] = datetime.now(timezone.utc).isoformat()
        special_perms.append(perm_dict)
    
    update_data = {
        "additional_departments": permissions.additional_departments,
        "additional_pages": permissions.additional_pages,
        "restricted_pages": permissions.restricted_pages,
        "temporary_role": permissions.temporary_role,
        "temporary_role_expiry": permissions.temporary_role_expiry,
        "can_approve_for_departments": permissions.can_approve_for_departments,
        "special_permissions": special_perms,
        "permission_notes": permissions.notes,
        "permissions_updated_by": current_user.id,
        "permissions_updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.employees.update_one({"id": employee_id}, {"$set": update_data})
    
    # Update user record if exists
    if employee.get("user_id"):
        # Compute effective departments for quick access
        effective_depts = list(set(
            employee.get("departments", []) + 
            permissions.additional_departments
        ))
        await db.users.update_one(
            {"id": employee["user_id"]},
            {"$set": {
                "additional_departments": permissions.additional_departments,
                "additional_pages": permissions.additional_pages,
                "restricted_pages": permissions.restricted_pages,
                "temporary_role": permissions.temporary_role,
                "effective_departments": effective_depts
            }}
        )
    
    # Log the change
    await db.permission_audit_logs.insert_one({
        "id": str(uuid.uuid4()),
        "employee_id": employee_id,
        "action": "special_permissions_updated",
        "changes": update_data,
        "changed_by": current_user.id,
        "changed_by_name": current_user.full_name,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    return {"message": "Special permissions updated successfully"}


@router.post("/employee/{employee_id}/grant-temporary-access")
async def grant_temporary_department_access(
    employee_id: str,
    department: str,
    reason: str,
    expiry_days: int = 30,
    current_user: User = Depends(get_current_user)
):
    """Quick action: Grant temporary department access to an employee"""
    if current_user.role not in ["admin", "hr_manager"]:
        raise HTTPException(status_code=403, detail="Admin or HR Manager access required")
    
    db = get_db()
    
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    from datetime import timedelta
    expiry_date = (datetime.now(timezone.utc) + timedelta(days=expiry_days)).isoformat()
    
    # Add to additional_departments
    additional_depts = employee.get("additional_departments", [])
    if department not in additional_depts:
        additional_depts.append(department)
    
    # Add special permission entry
    special_perms = employee.get("special_permissions", [])
    special_perms.append({
        "permission_type": "temporary_department_access",
        "value": department,
        "reason": reason,
        "is_temporary": True,
        "expiry_date": expiry_date,
        "granted_by": current_user.id,
        "granted_by_name": current_user.full_name,
        "granted_at": datetime.now(timezone.utc).isoformat()
    })
    
    await db.employees.update_one(
        {"id": employee_id},
        {"$set": {
            "additional_departments": additional_depts,
            "special_permissions": special_perms
        }}
    )
    
    # Update user record if exists
    if employee.get("user_id"):
        effective_depts = list(set(employee.get("departments", []) + additional_depts))
        await db.users.update_one(
            {"id": employee["user_id"]},
            {"$set": {
                "additional_departments": additional_depts,
                "effective_departments": effective_depts
            }}
        )
    
    return {
        "message": f"Temporary {department} access granted until {expiry_date[:10]}",
        "expiry_date": expiry_date
    }


@router.delete("/employee/{employee_id}/revoke-access/{department}")
async def revoke_department_access(
    employee_id: str,
    department: str,
    current_user: User = Depends(get_current_user)
):
    """Revoke additional department access from an employee"""
    if current_user.role not in ["admin", "hr_manager"]:
        raise HTTPException(status_code=403, detail="Admin or HR Manager access required")
    
    db = get_db()
    
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Cannot revoke primary department
    if department == employee.get("primary_department"):
        raise HTTPException(status_code=400, detail="Cannot revoke primary department access")
    
    # Remove from additional_departments
    additional_depts = employee.get("additional_departments", [])
    if department in additional_depts:
        additional_depts.remove(department)
    
    # Also remove from base departments if it's not primary
    base_depts = employee.get("departments", [])
    if department in base_depts and department != employee.get("primary_department"):
        base_depts.remove(department)
    
    await db.employees.update_one(
        {"id": employee_id},
        {"$set": {
            "additional_departments": additional_depts,
            "departments": base_depts
        }}
    )
    
    # Update user record
    if employee.get("user_id"):
        effective_depts = list(set(base_depts + additional_depts))
        await db.users.update_one(
            {"id": employee["user_id"]},
            {"$set": {
                "additional_departments": additional_depts,
                "departments": base_depts,
                "effective_departments": effective_depts
            }}
        )
    
    return {"message": f"{department} access revoked"}


@router.get("/approval-matrix")
async def get_approval_matrix(current_user: User = Depends(get_current_user)):
    """Get approval matrix showing who can approve what"""
    if current_user.role not in ["admin", "hr_manager"]:
        raise HTTPException(status_code=403, detail="Admin or HR Manager access required")
    
    db = get_db()
    
    # Get all employees with approval rights
    approvers = await db.employees.find(
        {
            "$or": [
                {"level": {"$in": ["manager", "leader"]}},
                {"can_approve_for_departments": {"$exists": True, "$ne": []}}
            ],
            "status": {"$ne": "terminated"}
        },
        {"_id": 0, "id": 1, "employee_id": 1, "first_name": 1, "last_name": 1,
         "department": 1, "departments": 1, "level": 1, "can_approve_for_departments": 1}
    ).to_list(500)
    
    return {
        "approvers": [
            {
                "id": e.get("id"),
                "name": f"{e.get('first_name', '')} {e.get('last_name', '')}".strip(),
                "employee_code": e.get("employee_id"),
                "level": e.get("level"),
                "own_departments": e.get("departments", []),
                "can_approve_for": e.get("can_approve_for_departments", []) or e.get("departments", [])
            }
            for e in approvers
        ]
    }
