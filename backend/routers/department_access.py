"""
Department Access Management Router
Controls department-based page access with multi-department support and exceptions
"""

from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
import uuid

from .deps import get_db, sanitize_text
from .auth import get_current_user
from .models import User

router = APIRouter(prefix="/department-access", tags=["Department Access"])


# ============== Department Definitions ==============

DEPARTMENTS = {
    "Sales": {
        "id": "sales",
        "name": "Sales",
        "description": "Lead management, pricing, SOW, agreements, kickoff",
        "pages": [
            "/leads", "/meetings", "/sales", "/pricing", "/sow", 
            "/quotations", "/proforma", "/agreements", "/kickoff-requests",
            "/payment-verification", "/clients"
        ],
        "icon": "TrendingUp",
        "color": "#F97316"
    },
    "HR": {
        "id": "hr",
        "name": "HR",
        "description": "Employees, attendance, leaves, payroll, CTC, staffing",
        "pages": [
            "/employees", "/attendance", "/leave-management", "/payroll",
            "/ctc-designer", "/onboarding", "/letter-management", "/hr",
            "/attendance-approvals", "/performance-dashboard", "/travel-reimbursement"
        ],
        "icon": "Users",
        "color": "#10B981"
    },
    "Consulting": {
        "id": "consulting",
        "name": "Consulting",
        "description": "Projects, tasks, SOW execution, timesheets, payments",
        "pages": [
            "/projects", "/consulting", "/consultant", "/timesheets",
            "/payments", "/gantt-chart", "/project-roadmap"
        ],
        "icon": "Briefcase",
        "color": "#8B5CF6"
    },
    "Finance": {
        "id": "finance",
        "name": "Finance",
        "description": "Payments, expenses, P&L, financial reports",
        "pages": [
            "/payments", "/expenses", "/reports", "/finance"
        ],
        "icon": "DollarSign",
        "color": "#3B82F6"
    },
    "Admin": {
        "id": "admin",
        "name": "Admin",
        "description": "Full system access, user management, settings",
        "pages": ["*"],  # Access to all pages
        "icon": "Shield",
        "color": "#EF4444"
    }
}

# Pages accessible to all authenticated users (My Workspace)
UNIVERSAL_PAGES = [
    "/", "/dashboard", "/my-attendance", "/my-leaves", "/my-expenses",
    "/my-salary-slips", "/my-bank-details", "/user-profile", "/notifications",
    "/workflow", "/tutorials", "/mobile-app"
]


# ============== Pydantic Models ==============

class DepartmentAccessGrant(BaseModel):
    """Grant department access to an employee"""
    employee_id: str
    department: str
    is_primary: bool = False
    granted_pages: Optional[List[str]] = None  # Specific pages, or None for all dept pages
    restricted_pages: Optional[List[str]] = None  # Pages to exclude
    reason: Optional[str] = None


class DepartmentAccessUpdate(BaseModel):
    """Update department access"""
    departments: List[str]
    primary_department: str
    custom_page_access: Optional[List[str]] = None
    restricted_pages: Optional[List[str]] = None


class BulkDepartmentUpdate(BaseModel):
    """Bulk update department access for multiple employees"""
    employee_ids: List[str]
    add_departments: Optional[List[str]] = None
    remove_departments: Optional[List[str]] = None


# ============== API Endpoints ==============

@router.get("/departments")
async def get_all_departments(current_user: User = Depends(get_current_user)):
    """Get list of all departments with their configurations"""
    return {
        "departments": DEPARTMENTS,
        "universal_pages": UNIVERSAL_PAGES
    }


@router.get("/my-access")
async def get_my_department_access(current_user: User = Depends(get_current_user)):
    """Get current user's department access configuration"""
    db = get_db()
    
    # First check user record for departments (most authoritative)
    user = await db.users.find_one({"id": current_user.id}, {"_id": 0})
    user_departments = user.get("departments", []) if user else []
    user_primary = user.get("primary_department") if user else None
    
    # Get employee record for additional info
    employee = await db.employees.find_one(
        {"user_id": current_user.id},
        {"_id": 0}
    )
    
    # Use user departments if available, otherwise fall back to employee or role-based
    if user_departments:
        departments = user_departments
        primary_dept = user_primary or user_departments[0]
    elif employee:
        departments = employee.get("departments", [])
        primary_dept = employee.get("primary_department") or employee.get("department")
        if not departments and primary_dept:
            departments = [primary_dept]
    else:
        # Fall back to role-based access for users without employee record
        if current_user.role == "admin":
            departments = ["Admin"]
            primary_dept = "Admin"
        else:
            departments = []
            primary_dept = None
    
    # Admin role always has full access
    if current_user.role == "admin":
        departments = ["Admin"]
        primary_dept = "Admin"
    
    # Build accessible pages list
    accessible_pages = list(UNIVERSAL_PAGES)
    
    for dept in departments:
        if dept in DEPARTMENTS:
            dept_pages = DEPARTMENTS[dept]["pages"]
            if dept_pages == ["*"]:
                accessible_pages = ["*"]
                break
            accessible_pages.extend(dept_pages)
    
    # Add custom access pages if any (from employee record)
    custom_access = employee.get("custom_page_access", []) if employee else []
    if custom_access:
        accessible_pages.extend(custom_access)
    
    # Remove restricted pages
    restricted = employee.get("restricted_pages", []) if employee else []
    if restricted and accessible_pages != ["*"]:
        accessible_pages = [p for p in accessible_pages if p not in restricted]
    
    # Remove duplicates
    if accessible_pages != ["*"]:
        accessible_pages = list(set(accessible_pages))
    
    # Get level - user level takes precedence
    level = user.get("level") if user else None
    if not level and employee:
        level = employee.get("level", "executive")
    if not level:
        level = "leader" if current_user.role == "admin" else "executive"
    
    return {
        "employee_id": employee.get("id") if employee else None,
        "employee_code": employee.get("employee_id") if employee else None,
        "departments": departments,
        "primary_department": primary_dept,
        "accessible_pages": accessible_pages,
        "level": level,
        "custom_access": custom_access,
        "restricted_pages": restricted
    }


@router.get("/employee/{employee_id}")
async def get_employee_department_access(
    employee_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get department access for a specific employee (Admin/HR only)"""
    if current_user.role not in ["admin", "hr_manager"]:
        raise HTTPException(status_code=403, detail="Admin or HR Manager access required")
    
    db = get_db()
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    departments = employee.get("departments", [])
    primary_dept = employee.get("primary_department") or employee.get("department")
    
    if not departments and primary_dept:
        departments = [primary_dept]
    
    return {
        "employee_id": employee.get("id"),
        "employee_code": employee.get("employee_id"),
        "full_name": f"{employee.get('first_name', '')} {employee.get('last_name', '')}".strip(),
        "departments": departments,
        "primary_department": primary_dept,
        "level": employee.get("level", "executive"),
        "custom_page_access": employee.get("custom_page_access", []),
        "restricted_pages": employee.get("restricted_pages", []),
        "has_portal_access": bool(employee.get("user_id"))
    }


@router.put("/employee/{employee_id}")
async def update_employee_department_access(
    employee_id: str,
    access_update: DepartmentAccessUpdate,
    current_user: User = Depends(get_current_user)
):
    """Update department access for an employee (Admin/HR only)"""
    if current_user.role not in ["admin", "hr_manager"]:
        raise HTTPException(status_code=403, detail="Admin or HR Manager access required")
    
    db = get_db()
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Validate departments
    for dept in access_update.departments:
        if dept not in DEPARTMENTS:
            raise HTTPException(status_code=400, detail=f"Invalid department: {dept}")
    
    if access_update.primary_department not in access_update.departments:
        raise HTTPException(status_code=400, detail="Primary department must be in departments list")
    
    # Update employee record
    update_data = {
        "departments": access_update.departments,
        "primary_department": access_update.primary_department,
        "department": access_update.primary_department,  # Keep legacy field in sync
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    if access_update.custom_page_access is not None:
        update_data["custom_page_access"] = access_update.custom_page_access
    
    if access_update.restricted_pages is not None:
        update_data["restricted_pages"] = access_update.restricted_pages
    
    await db.employees.update_one(
        {"id": employee_id},
        {"$set": update_data}
    )
    
    # If user has portal access, update user record too
    if employee.get("user_id"):
        await db.users.update_one(
            {"id": employee["user_id"]},
            {"$set": {
                "departments": access_update.departments,
                "primary_department": access_update.primary_department,
                "department": access_update.primary_department
            }}
        )
    
    # Log the change
    await db.department_access_logs.insert_one({
        "id": str(uuid.uuid4()),
        "employee_id": employee_id,
        "action": "update_access",
        "old_departments": employee.get("departments", []),
        "new_departments": access_update.departments,
        "changed_by": current_user.id,
        "changed_by_name": current_user.full_name,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    return {"message": "Department access updated successfully"}


@router.post("/employee/{employee_id}/add-department")
async def add_department_to_employee(
    employee_id: str,
    grant: DepartmentAccessGrant,
    current_user: User = Depends(get_current_user)
):
    """Add a department to an employee's access (Admin/HR only)"""
    if current_user.role not in ["admin", "hr_manager"]:
        raise HTTPException(status_code=403, detail="Admin or HR Manager access required")
    
    if grant.department not in DEPARTMENTS:
        raise HTTPException(status_code=400, detail=f"Invalid department: {grant.department}")
    
    db = get_db()
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    current_depts = employee.get("departments", [])
    primary_dept = employee.get("primary_department") or employee.get("department")
    
    # Initialize departments if not set
    if not current_depts and primary_dept:
        current_depts = [primary_dept]
    
    if grant.department in current_depts:
        raise HTTPException(status_code=400, detail=f"Employee already has {grant.department} access")
    
    # Add the new department
    new_depts = current_depts + [grant.department]
    
    update_data = {
        "departments": new_depts,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    # Set as primary if requested or if first department
    if grant.is_primary or not primary_dept:
        update_data["primary_department"] = grant.department
        update_data["department"] = grant.department
    
    # Handle custom page access
    if grant.granted_pages:
        current_custom = employee.get("custom_page_access", [])
        update_data["custom_page_access"] = list(set(current_custom + grant.granted_pages))
    
    if grant.restricted_pages:
        current_restricted = employee.get("restricted_pages", [])
        update_data["restricted_pages"] = list(set(current_restricted + grant.restricted_pages))
    
    await db.employees.update_one({"id": employee_id}, {"$set": update_data})
    
    # Update user record if exists
    if employee.get("user_id"):
        user_update = {"departments": new_depts}
        if grant.is_primary:
            user_update["primary_department"] = grant.department
            user_update["department"] = grant.department
        await db.users.update_one({"id": employee["user_id"]}, {"$set": user_update})
    
    # Create notification
    await db.notifications.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": employee.get("user_id"),
        "type": "department_access_granted",
        "title": "Department Access Granted",
        "message": f"You have been granted access to {grant.department} department",
        "read": False,
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    return {
        "message": f"{grant.department} access granted successfully",
        "departments": new_depts
    }


@router.delete("/employee/{employee_id}/remove-department/{department}")
async def remove_department_from_employee(
    employee_id: str,
    department: str,
    current_user: User = Depends(get_current_user)
):
    """Remove a department from an employee's access (Admin/HR only)"""
    if current_user.role not in ["admin", "hr_manager"]:
        raise HTTPException(status_code=403, detail="Admin or HR Manager access required")
    
    db = get_db()
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    current_depts = employee.get("departments", [])
    
    if department not in current_depts:
        raise HTTPException(status_code=400, detail=f"Employee doesn't have {department} access")
    
    if len(current_depts) <= 1:
        raise HTTPException(status_code=400, detail="Cannot remove last department. Employee must have at least one department.")
    
    new_depts = [d for d in current_depts if d != department]
    
    update_data = {
        "departments": new_depts,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    # Update primary if removed
    if employee.get("primary_department") == department:
        update_data["primary_department"] = new_depts[0]
        update_data["department"] = new_depts[0]
    
    await db.employees.update_one({"id": employee_id}, {"$set": update_data})
    
    # Update user record if exists
    if employee.get("user_id"):
        user_update = {"departments": new_depts}
        if employee.get("primary_department") == department:
            user_update["primary_department"] = new_depts[0]
            user_update["department"] = new_depts[0]
        await db.users.update_one({"id": employee["user_id"]}, {"$set": user_update})
    
    return {
        "message": f"{department} access removed successfully",
        "departments": new_depts
    }


@router.post("/bulk-update")
async def bulk_update_department_access(
    bulk_update: BulkDepartmentUpdate,
    current_user: User = Depends(get_current_user)
):
    """Bulk update department access for multiple employees (Admin only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    db = get_db()
    updated_count = 0
    errors = []
    
    for emp_id in bulk_update.employee_ids:
        try:
            employee = await db.employees.find_one({"id": emp_id}, {"_id": 0})
            if not employee:
                errors.append({"employee_id": emp_id, "error": "Not found"})
                continue
            
            current_depts = employee.get("departments", [])
            if not current_depts:
                current_depts = [employee.get("department")] if employee.get("department") else []
            
            # Add departments
            if bulk_update.add_departments:
                for dept in bulk_update.add_departments:
                    if dept in DEPARTMENTS and dept not in current_depts:
                        current_depts.append(dept)
            
            # Remove departments
            if bulk_update.remove_departments:
                current_depts = [d for d in current_depts if d not in bulk_update.remove_departments]
            
            if not current_depts:
                errors.append({"employee_id": emp_id, "error": "Cannot remove all departments"})
                continue
            
            # Update
            await db.employees.update_one(
                {"id": emp_id},
                {"$set": {
                    "departments": current_depts,
                    "primary_department": current_depts[0] if employee.get("primary_department") not in current_depts else employee.get("primary_department"),
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }}
            )
            updated_count += 1
            
        except Exception as e:
            errors.append({"employee_id": emp_id, "error": str(e)})
    
    return {
        "updated_count": updated_count,
        "errors": errors
    }


@router.get("/stats")
async def get_department_access_stats(current_user: User = Depends(get_current_user)):
    """Get department access statistics (Admin/HR only)"""
    if current_user.role not in ["admin", "hr_manager"]:
        raise HTTPException(status_code=403, detail="Admin or HR Manager access required")
    
    db = get_db()
    
    # Count by primary department
    dept_stats = await db.employees.aggregate([
        {"$match": {"status": {"$ne": "terminated"}}},
        {"$group": {"_id": "$primary_department", "count": {"$sum": 1}}}
    ]).to_list(100)
    
    # Count multi-department employees
    multi_dept_count = await db.employees.count_documents({
        "status": {"$ne": "terminated"},
        "departments.1": {"$exists": True}  # Has at least 2 departments
    })
    
    # Count by level
    level_stats = await db.employees.aggregate([
        {"$match": {"status": {"$ne": "terminated"}}},
        {"$group": {"_id": "$level", "count": {"$sum": 1}}}
    ]).to_list(100)
    
    # Count with portal access
    with_access = await db.employees.count_documents({
        "status": {"$ne": "terminated"},
        "user_id": {"$ne": None}
    })
    
    total = await db.employees.count_documents({"status": {"$ne": "terminated"}})
    
    return {
        "total_employees": total,
        "with_portal_access": with_access,
        "without_portal_access": total - with_access,
        "multi_department_employees": multi_dept_count,
        "by_department": {d["_id"]: d["count"] for d in dept_stats if d["_id"]},
        "by_level": {l["_id"]: l["count"] for l in level_stats if l["_id"]},
        "departments_available": list(DEPARTMENTS.keys())
    }


@router.get("/employees-by-department/{department}")
async def get_employees_by_department(
    department: str,
    current_user: User = Depends(get_current_user)
):
    """Get all employees with access to a specific department"""
    if current_user.role not in ["admin", "hr_manager"]:
        raise HTTPException(status_code=403, detail="Admin or HR Manager access required")
    
    if department not in DEPARTMENTS:
        raise HTTPException(status_code=400, detail=f"Invalid department: {department}")
    
    db = get_db()
    
    # Find employees with this department in their departments array or primary_department
    employees = await db.employees.find(
        {
            "status": {"$ne": "terminated"},
            "$or": [
                {"departments": department},
                {"primary_department": department},
                {"department": department}
            ]
        },
        {"_id": 0, "id": 1, "employee_id": 1, "first_name": 1, "last_name": 1,
         "designation": 1, "level": 1, "departments": 1, "primary_department": 1,
         "user_id": 1}
    ).to_list(500)
    
    return {
        "department": department,
        "department_info": DEPARTMENTS[department],
        "employee_count": len(employees),
        "employees": [
            {
                "id": e.get("id"),
                "employee_code": e.get("employee_id"),
                "name": f"{e.get('first_name', '')} {e.get('last_name', '')}".strip(),
                "designation": e.get("designation"),
                "level": e.get("level", "executive"),
                "is_primary": e.get("primary_department") == department or e.get("department") == department,
                "has_portal_access": bool(e.get("user_id")),
                "all_departments": e.get("departments", [e.get("department")] if e.get("department") else [])
            }
            for e in employees
        ]
    }
