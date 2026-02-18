"""
Employees Router - Employee Management, Documents, Org Structure
"""

from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone
from typing import Optional, List
import uuid
import base64

from .models import User, UserRole
from .deps import get_db, sanitize_text
from .auth import get_current_user, get_password_hash

router = APIRouter(prefix="/employees", tags=["Employees"])


@router.get("")
async def get_employees(
    department: Optional[str] = None,
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get all employees with optional filters."""
    db = get_db()
    
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


@router.post("")
async def create_employee(data: dict, current_user: User = Depends(get_current_user)):
    """Create a new employee."""
    db = get_db()
    
    if current_user.role not in ["admin", "hr_manager", "hr_executive"]:
        raise HTTPException(status_code=403, detail="Only HR can create employees")
    
    # Check for duplicate email
    if data.get("email"):
        existing = await db.employees.find_one({"email": data["email"]})
        if existing:
            raise HTTPException(status_code=400, detail="Employee with this email already exists")
    
    # Check for duplicate phone number
    if data.get("phone"):
        phone = data["phone"].replace(" ", "").replace("-", "")
        if len(phone) >= 10:
            existing_phone = await db.employees.find_one({"phone": {"$regex": phone[-10:]}})
            if existing_phone:
                raise HTTPException(status_code=400, detail="Employee with this phone number already exists")
    
    # Generate employee ID if not provided
    if not data.get("employee_id"):
        count = await db.employees.count_documents({})
        data["employee_id"] = f"EMP{str(count + 1).zfill(3)}"
    
    employee = {
        "id": str(uuid.uuid4()),
        "employee_id": data.get("employee_id"),
        "first_name": sanitize_text(data.get("first_name", "")),
        "last_name": sanitize_text(data.get("last_name", "")),
        "email": data.get("email"),
        "phone": data.get("phone"),
        "department": data.get("department"),
        "designation": data.get("designation"),
        "role": data.get("role", "consultant"),
        "level": data.get("level", "executive"),  # Employee hierarchy level
        "reporting_manager_id": data.get("reporting_manager_id"),
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
        "created_by": current_user.id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.employees.insert_one(employee)
    
    # Remove _id added by MongoDB before returning
    employee.pop("_id", None)
    
    return {"message": "Employee created", "employee": employee}


@router.post("/{employee_id}/grant-access")
async def grant_employee_access(employee_id: str, current_user: User = Depends(get_current_user)):
    """Grant portal access to an employee by creating a user account."""
    db = get_db()
    
    if current_user.role not in ["admin", "hr_manager"]:
        raise HTTPException(status_code=403, detail="Only Admin/HR Manager can grant access")
    
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    if not employee.get("email"):
        raise HTTPException(status_code=400, detail="Employee must have an email to grant access")
    
    # Check if user already exists
    existing_user = await db.users.find_one({"email": employee["email"]})
    if existing_user:
        # Link existing user
        await db.employees.update_one(
            {"id": employee_id},
            {"$set": {"user_id": existing_user["id"], "has_portal_access": True}}
        )
        return {"message": "Linked to existing user account", "user_id": existing_user["id"]}
    
    # Create new user
    user_id = str(uuid.uuid4())
    temp_password = f"Welcome@{employee.get('employee_id', '123')}"
    
    user = {
        "id": user_id,
        "email": employee["email"],
        "full_name": f"{employee.get('first_name', '')} {employee.get('last_name', '')}".strip(),
        "role": employee.get("role", "consultant"),
        "department": employee.get("department"),
        "designation": employee.get("designation"),
        "reporting_manager_id": employee.get("reporting_manager_id"),
        "is_active": True,
        "hashed_password": get_password_hash(temp_password),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "employee_id": employee_id
    }
    
    await db.users.insert_one(user)
    
    # Update employee with user link
    await db.employees.update_one(
        {"id": employee_id},
        {"$set": {"user_id": user_id, "has_portal_access": True}}
    )
    
    return {
        "message": "Portal access granted",
        "user_id": user_id,
        "temp_password": temp_password,
        "note": "User should change password on first login"
    }


@router.post("/{employee_id}/reset-temp-password")
async def reset_employee_temp_password(employee_id: str, current_user: User = Depends(get_current_user)):
    """Reset the temporary password for an employee's portal access.
    This is useful when an employee forgets their password or HR needs to resend credentials.
    """
    db = get_db()
    
    if current_user.role not in ["admin", "hr_manager"]:
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
    
    if current_user.role not in ["admin", "hr_manager"]:
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
    
    if current_user.role not in ["admin", "hr_manager"]:
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
async def update_employee(employee_id: str, data: dict, current_user: User = Depends(get_current_user)):
    """Update an employee's details."""
    db = get_db()
    
    if current_user.role not in ["admin", "hr_manager", "hr_executive"]:
        raise HTTPException(status_code=403, detail="Only HR can update employees")
    
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Sanitize text fields
    if "first_name" in data:
        data["first_name"] = sanitize_text(data["first_name"])
    if "last_name" in data:
        data["last_name"] = sanitize_text(data["last_name"])
    
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.employees.update_one({"id": employee_id}, {"$set": data})
    
    return {"message": "Employee updated"}


@router.delete("/{employee_id}")
async def delete_employee(employee_id: str, current_user: User = Depends(get_current_user)):
    """Delete (soft delete) an employee."""
    db = get_db()
    
    if current_user.role not in ["admin"]:
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
    
    if current_user.role not in ["admin", "hr_manager"]:
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
    return [d for d in departments if d]


@router.get("/stats/summary")
async def get_employee_stats(current_user: User = Depends(get_current_user)):
    """Get employee statistics summary."""
    db = get_db()
    
    if current_user.role not in ["admin", "hr_manager", "hr_executive"]:
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
        "by_level": {l["_id"]: l["count"] for l in level_stats if l["_id"]}
    }


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
    
    # 5. Expenses
    expenses = await db.expenses.find({"employee_id": employee_id}, {"_id": 0}).to_list(50)
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
    
    # Count linked records
    linked = {
        "attendance": await db.attendance.count_documents({"employee_id": employee_id}),
        "leave_requests": await db.leave_requests.count_documents({"employee_id": employee_id}),
        "expenses": await db.expenses.count_documents({"employee_id": employee_id}),
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

