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
    
    return {
        "total": total,
        "active": active,
        "terminated": terminated,
        "by_department": {d["_id"]: d["count"] for d in dept_stats if d["_id"]},
        "by_role": {r["_id"]: r["count"] for r in role_stats if r["_id"]}
    }
