"""
Expenses Router - Expense Management, Receipts, Approvals
"""

from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone
from typing import Optional, List
import uuid

from .models import User, UserRole
from .deps import get_db, sanitize_text
from .auth import get_current_user

router = APIRouter(prefix="/expenses", tags=["Expenses"])


@router.post("")
async def create_expense(data: dict, current_user: User = Depends(get_current_user)):
    """Create a new expense entry with line items support."""
    db = get_db()
    
    # Get employee record for proper linking
    employee = await db.employees.find_one({"user_id": current_user.id}, {"_id": 0})
    employee_id = employee.get("id") if employee else current_user.id
    employee_code = employee.get("employee_id") if employee else None
    employee_name = f"{employee.get('first_name', '')} {employee.get('last_name', '')}".strip() if employee else current_user.full_name
    reporting_manager_id = employee.get("reporting_manager_id") if employee else None
    
    # Handle line_items format from frontend
    line_items = data.get("line_items", [])
    total_amount = sum(item.get("amount", 0) for item in line_items) if line_items else data.get("amount", 0)
    
    expense = {
        "id": str(uuid.uuid4()),
        "employee_id": employee_id,
        "employee_code": employee_code,
        "employee_name": employee_name,
        "user_id": current_user.id,
        "reporting_manager_id": reporting_manager_id,  # For approval flow
        "category": data.get("category"),
        "subcategory": data.get("subcategory"),
        "line_items": line_items,
        "total_amount": total_amount,
        "amount": total_amount,  # Keep for backwards compatibility
        "currency": data.get("currency", "INR"),
        "description": sanitize_text(data.get("description", "") or data.get("notes", "")),
        "notes": data.get("notes", ""),
        "expense_date": data.get("expense_date"),
        "vendor": data.get("vendor"),
        "receipts": [],
        "status": "draft",
        "project_id": data.get("project_id"),
        "project_name": data.get("project_name", ""),
        "client_id": data.get("client_id"),
        "client_name": data.get("client_name", ""),
        "is_office_expense": data.get("is_office_expense", False),
        "is_billable": data.get("is_billable", False),
        "created_by": current_user.id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.expenses.insert_one(expense)
    
    return {"message": "Expense created", "expense_id": expense["id"]}


@router.post("/quick")
async def create_quick_expense(data: dict, current_user: User = Depends(get_current_user)):
    """Create a quick expense with minimal fields."""
    db = get_db()
    
    expense = {
        "id": str(uuid.uuid4()),
        "employee_id": current_user.id,
        "category": data.get("category", "miscellaneous"),
        "amount": data.get("amount", 0),
        "currency": "INR",
        "description": sanitize_text(data.get("description", "")),
        "expense_date": data.get("expense_date", datetime.now(timezone.utc).strftime("%Y-%m-%d")),
        "receipts": [],
        "status": "draft",
        "is_billable": False,
        "created_by": current_user.id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.expenses.insert_one(expense)
    
    return {"message": "Quick expense created", "expense_id": expense["id"]}


@router.get("")
async def get_expenses(
    employee_id: Optional[str] = None,
    status: Optional[str] = None,
    category: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get expenses with filters."""
    db = get_db()
    
    query = {}
    
    # Non-admin users can only see their own expenses
    if current_user.role not in ["admin", "hr_manager", "hr_executive", "manager"]:
        query["employee_id"] = current_user.id
    elif employee_id:
        query["employee_id"] = employee_id
    
    if status:
        query["status"] = status
    if category:
        query["category"] = category
    if date_from and date_to:
        query["expense_date"] = {"$gte": date_from, "$lte": date_to}
    
    expenses = await db.expenses.find(query, {"_id": 0}).sort("created_at", -1).to_list(500)
    
    return expenses


@router.get("/{expense_id}")
async def get_expense(expense_id: str, current_user: User = Depends(get_current_user)):
    """Get a single expense by ID."""
    db = get_db()
    
    expense = await db.expenses.find_one({"id": expense_id}, {"_id": 0})
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    
    return expense


@router.patch("/{expense_id}")
async def update_expense(expense_id: str, data: dict, current_user: User = Depends(get_current_user)):
    """Update an expense."""
    db = get_db()
    
    expense = await db.expenses.find_one({"id": expense_id}, {"_id": 0})
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    
    # Only owner or admin can update
    if expense["created_by"] != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to update this expense")
    
    if expense["status"] not in ["draft", "rejected"]:
        raise HTTPException(status_code=400, detail="Can only update draft or rejected expenses")
    
    if "description" in data:
        data["description"] = sanitize_text(data["description"])
    
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.expenses.update_one({"id": expense_id}, {"$set": data})
    
    return {"message": "Expense updated"}


@router.post("/{expense_id}/submit")
async def submit_expense(expense_id: str, current_user: User = Depends(get_current_user)):
    """Submit an expense for approval - routes to reporting manager."""
    db = get_db()
    
    expense = await db.expenses.find_one({"id": expense_id}, {"_id": 0})
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    
    if expense["created_by"] != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    
    if expense["status"] not in ["draft", "rejected"]:
        raise HTTPException(status_code=400, detail="Can only submit draft or rejected expenses")
    
    # Get the employee record to find reporting manager
    employee = await db.employees.find_one({"user_id": expense["created_by"]}, {"_id": 0})
    reporting_manager_id = expense.get("reporting_manager_id") or (employee.get("reporting_manager_id") if employee else None)
    
    # Find the reporting manager's user_id for notification
    manager_user_id = None
    manager_name = None
    if reporting_manager_id:
        # reporting_manager_id is now an employee_id code like "EMP110"
        manager_emp = await db.employees.find_one({"employee_id": reporting_manager_id}, {"_id": 0})
        if manager_emp:
            manager_user_id = manager_emp.get("user_id")
            manager_name = f"{manager_emp.get('first_name', '')} {manager_emp.get('last_name', '')}".strip()
    
    # Build approval flow info
    approval_flow = []
    if manager_name:
        approval_flow.append({"step": 1, "approver": manager_name, "role": "Reporting Manager", "status": "pending"})
    else:
        # If no reporting manager, route to HR
        approval_flow.append({"step": 1, "approver": "HR Manager", "role": "HR", "status": "pending"})
    
    await db.expenses.update_one(
        {"id": expense_id},
        {"$set": {
            "status": "pending",
            "submitted_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "approval_flow": approval_flow,
            "current_approver": manager_name or "HR Manager",
            "current_approver_id": manager_user_id
        }}
    )
    
    # Notify the reporting manager
    if manager_user_id:
        employee_name = expense.get("employee_name") or current_user.full_name
        expense_amount = expense.get("total_amount") or expense.get("amount", 0)
        notification = {
            "id": str(uuid.uuid4()),
            "user_id": manager_user_id,
            "type": "expense_approval",
            "title": "Expense Approval Required",
            "message": f"{employee_name} submitted an expense of ₹{expense_amount:,.0f} for approval",
            "reference_type": "expense",
            "reference_id": expense_id,
            "is_read": False,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.notifications.insert_one(notification)
    else:
        # Notify HR managers if no reporting manager
        hr_managers = await db.users.find({"role": {"$in": ["hr_manager", "admin"]}}, {"_id": 0, "id": 1}).to_list(10)
        for hr in hr_managers:
            notification = {
                "id": str(uuid.uuid4()),
                "user_id": hr["id"],
                "type": "expense_approval",
                "title": "Expense Approval Required",
                "message": f"{current_user.full_name} submitted an expense of ₹{expense.get('total_amount', 0):,.0f} for approval",
                "reference_type": "expense",
                "reference_id": expense_id,
                "is_read": False,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            await db.notifications.insert_one(notification)
    
    return {
        "message": "Expense submitted for approval",
        "approval_flow": approval_flow,
        "current_approver": manager_name or "HR Manager"
    }


@router.post("/{expense_id}/approve")
async def approve_expense(expense_id: str, data: dict, current_user: User = Depends(get_current_user)):
    """Approve an expense."""
    db = get_db()
    
    if current_user.role not in ["admin", "manager", "hr_manager"]:
        raise HTTPException(status_code=403, detail="Not authorized to approve expenses")
    
    expense = await db.expenses.find_one({"id": expense_id}, {"_id": 0})
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    
    if expense["status"] != "pending":
        raise HTTPException(status_code=400, detail="Expense is not pending approval")
    
    await db.expenses.update_one(
        {"id": expense_id},
        {"$set": {
            "status": "approved",
            "approved_by": current_user.id,
            "approved_by_name": current_user.full_name,
            "approved_at": datetime.now(timezone.utc).isoformat(),
            "approval_remarks": data.get("remarks", ""),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    return {"message": "Expense approved"}


@router.post("/{expense_id}/reject")
async def reject_expense(expense_id: str, data: dict, current_user: User = Depends(get_current_user)):
    """Reject an expense."""
    db = get_db()
    
    if current_user.role not in ["admin", "manager", "hr_manager"]:
        raise HTTPException(status_code=403, detail="Not authorized to reject expenses")
    
    expense = await db.expenses.find_one({"id": expense_id}, {"_id": 0})
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    
    rejection_reason = data.get("reason", "")
    if not rejection_reason:
        raise HTTPException(status_code=400, detail="Rejection reason is required")
    
    await db.expenses.update_one(
        {"id": expense_id},
        {"$set": {
            "status": "rejected",
            "rejected_by": current_user.id,
            "rejected_at": datetime.now(timezone.utc).isoformat(),
            "rejection_reason": rejection_reason,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    return {"message": "Expense rejected"}


@router.post("/{expense_id}/upload-receipt")
async def upload_receipt(expense_id: str, data: dict, current_user: User = Depends(get_current_user)):
    """Upload a receipt for an expense."""
    db = get_db()
    
    expense = await db.expenses.find_one({"id": expense_id}, {"_id": 0})
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    
    receipt = {
        "id": str(uuid.uuid4()),
        "file_data": data.get("file_data"),  # Base64 encoded
        "file_name": data.get("file_name"),
        "file_type": data.get("file_type"),
        "uploaded_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.expenses.update_one(
        {"id": expense_id},
        {"$push": {"receipts": receipt}}
    )
    
    return {"message": "Receipt uploaded", "receipt_id": receipt["id"]}


@router.delete("/{expense_id}/receipts/{receipt_id}")
async def delete_receipt(expense_id: str, receipt_id: str, current_user: User = Depends(get_current_user)):
    """Delete a receipt from an expense."""
    db = get_db()
    
    expense = await db.expenses.find_one({"id": expense_id}, {"_id": 0})
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    
    if expense["created_by"] != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    
    await db.expenses.update_one(
        {"id": expense_id},
        {"$pull": {"receipts": {"id": receipt_id}}}
    )
    
    return {"message": "Receipt deleted"}


@router.get("/categories/list")
async def get_expense_categories(current_user: User = Depends(get_current_user)):
    """Get list of expense categories."""
    categories = [
        {"key": "travel", "name": "Travel", "subcategories": ["flight", "train", "bus", "taxi", "fuel"]},
        {"key": "food", "name": "Food & Meals", "subcategories": ["client_meal", "team_meal", "working_lunch"]},
        {"key": "accommodation", "name": "Accommodation", "subcategories": ["hotel", "guest_house"]},
        {"key": "office_supplies", "name": "Office Supplies", "subcategories": ["stationery", "equipment"]},
        {"key": "communication", "name": "Communication", "subcategories": ["phone", "internet"]},
        {"key": "software", "name": "Software & Subscriptions", "subcategories": ["software", "cloud_services"]},
        {"key": "miscellaneous", "name": "Miscellaneous", "subcategories": ["other"]}
    ]
    return categories


@router.get("/stats/summary")
async def get_expense_stats(
    employee_id: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get expense statistics summary."""
    db = get_db()
    
    query = {}
    
    if current_user.role not in ["admin", "hr_manager"]:
        query["employee_id"] = current_user.id
    elif employee_id:
        query["employee_id"] = employee_id
    
    if date_from and date_to:
        query["expense_date"] = {"$gte": date_from, "$lte": date_to}
    
    # By status
    status_pipeline = [
        {"$match": query},
        {"$group": {
            "_id": "$status",
            "count": {"$sum": 1},
            "total": {"$sum": "$amount"}
        }}
    ]
    
    status_results = await db.expenses.aggregate(status_pipeline).to_list(10)
    
    # By category
    category_pipeline = [
        {"$match": {**query, "status": {"$in": ["approved", "pending"]}}},
        {"$group": {
            "_id": "$category",
            "count": {"$sum": 1},
            "total": {"$sum": "$amount"}
        }}
    ]
    
    category_results = await db.expenses.aggregate(category_pipeline).to_list(20)
    
    return {
        "by_status": {r["_id"]: {"count": r["count"], "total": r["total"]} for r in status_results if r["_id"]},
        "by_category": {r["_id"]: {"count": r["count"], "total": r["total"]} for r in category_results if r["_id"]}
    }
