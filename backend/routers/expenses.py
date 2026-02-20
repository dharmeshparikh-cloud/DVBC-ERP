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


@router.get("/pending-approvals")
async def get_pending_approvals(current_user: User = Depends(get_current_user)):
    """Get expenses pending approval for the current user (managers/HR/admin)."""
    db = get_db()
    
    is_hr_admin = current_user.role in ["admin", "hr_manager"]
    is_manager = current_user.role in ["admin", "manager", "hr_manager", "principal_consultant"]
    
    # Get current user's employee record to check if they're a reporting manager
    employee = await db.employees.find_one({"user_id": current_user.id}, {"_id": 0, "employee_id": 1})
    emp_code = employee.get("employee_id") if employee else None
    
    expenses = []
    
    if is_hr_admin:
        # HR/Admin can see all pending and manager_approved expenses
        expenses = await db.expenses.find(
            {"status": {"$in": ["pending", "manager_approved", "approved", "rejected"]}},
            {"_id": 0}
        ).sort("created_at", -1).to_list(200)
    elif is_manager:
        # Managers see expenses where they are the approver
        query = {
            "$or": [
                {"current_approver_id": current_user.id},
                {"reporting_manager_id": emp_code} if emp_code else {"current_approver_id": current_user.id}
            ],
            "status": {"$in": ["pending", "approved", "rejected"]}
        }
        expenses = await db.expenses.find(query, {"_id": 0}).sort("created_at", -1).to_list(200)
    else:
        # Check if user is a reporting manager for anyone
        if emp_code:
            expenses = await db.expenses.find(
                {"reporting_manager_id": emp_code, "status": {"$in": ["pending", "approved", "rejected"]}},
                {"_id": 0}
            ).sort("created_at", -1).to_list(200)
    
    return expenses


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


# Expense approval threshold - below this HR approves directly, above needs Admin
EXPENSE_HR_THRESHOLD = 2000  # ₹2000


@router.post("/{expense_id}/submit")
async def submit_expense(expense_id: str, current_user: User = Depends(get_current_user)):
    """
    Submit expense for approval:
    - < ₹2000: HR directly approves (single level)
    - ≥ ₹2000: Admin approval required
    """
    db = get_db()
    
    expense = await db.expenses.find_one({"id": expense_id}, {"_id": 0})
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    
    if expense["created_by"] != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    
    if expense["status"] not in ["draft", "rejected"]:
        raise HTTPException(status_code=400, detail="Can only submit draft or rejected expenses")
    
    expense_amount = expense.get("total_amount") or expense.get("amount", 0)
    employee_name = expense.get("employee_name") or current_user.full_name
    now = datetime.now(timezone.utc).isoformat()
    
    # Determine approval flow based on amount
    requires_admin = expense_amount >= EXPENSE_HR_THRESHOLD
    
    approval_flow = []
    if requires_admin:
        # Large expense: HR → Admin
        approval_flow = [
            {"step": 1, "approver": "HR Manager", "role": "HR", "status": "pending"},
            {"step": 2, "approver": "Admin", "role": "Admin", "status": "pending"}
        ]
        current_approver = "HR Manager"
    else:
        # Small expense: HR only
        approval_flow = [
            {"step": 1, "approver": "HR Manager", "role": "HR", "status": "pending"}
        ]
        current_approver = "HR Manager"
    
    await db.expenses.update_one(
        {"id": expense_id},
        {"$set": {
            "status": "pending",
            "submitted_at": now,
            "updated_at": now,
            "approval_flow": approval_flow,
            "current_approver": current_approver,
            "current_approver_id": None,  # Any HR/Admin can approve
            "requires_admin_approval": requires_admin,
            "expense_threshold_applied": EXPENSE_HR_THRESHOLD
        }}
    )
    
    # Notify HR managers
    hr_managers = await db.users.find({"role": {"$in": ["hr_manager", "admin"]}}, {"_id": 0, "id": 1}).to_list(10)
    for hr in hr_managers:
        threshold_note = f" (Requires Admin approval)" if requires_admin else " (HR can approve directly)"
        notification = {
            "id": str(uuid.uuid4()),
            "user_id": hr["id"],
            "type": "expense_approval",
            "title": "Expense Approval Required",
            "message": f"{employee_name} submitted ₹{expense_amount:,.0f} expense{threshold_note}",
            "reference_type": "expense",
            "reference_id": expense_id,
            "is_read": False,
            "created_at": now
        }
        await db.notifications.insert_one(notification)
    
    return {
        "message": f"Expense submitted for approval",
        "approval_flow": approval_flow,
        "current_approver": current_approver,
        "requires_admin": requires_admin,
        "threshold": EXPENSE_HR_THRESHOLD
    }


@router.post("/{expense_id}/approve")
async def approve_expense(expense_id: str, data: dict, current_user: User = Depends(get_current_user)):
    """
    Multi-level expense approval:
    - Step 1: Reporting Manager approves → moves to HR/Admin review
    - Step 2: HR/Admin approves → approved for payroll
    """
    db = get_db()
    
    expense = await db.expenses.find_one({"id": expense_id}, {"_id": 0})
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    
    current_status = expense.get("status")
    approval_flow = expense.get("approval_flow", [])
    
    # Check if user is authorized to approve at this stage
    is_manager_approval = current_status == "pending" and expense.get("current_approver_id") == current_user.id
    is_hr_admin = current_user.role in ["admin", "hr_manager"]
    is_any_manager = current_user.role in ["admin", "manager", "hr_manager", "principal_consultant"]
    
    # Also check if user is the reporting manager even if role doesn't match
    employee = await db.employees.find_one({"user_id": current_user.id}, {"_id": 0})
    is_reporting_manager = False
    if employee:
        emp_code = employee.get("employee_id")
        if emp_code == expense.get("reporting_manager_id"):
            is_reporting_manager = True
    
    if not (is_manager_approval or is_reporting_manager or is_any_manager):
        raise HTTPException(status_code=403, detail="Not authorized to approve this expense")
    
    if current_status not in ["pending", "manager_approved"]:
        raise HTTPException(status_code=400, detail=f"Expense cannot be approved in '{current_status}' status")
    
    now = datetime.now(timezone.utc).isoformat()
    employee_name = expense.get("employee_name", "Employee")
    expense_amount = expense.get("total_amount") or expense.get("amount", 0)
    
    if current_status == "pending":
        # Stage 1: Manager approval - move to HR review
        # Update approval flow
        for step in approval_flow:
            if step.get("role") == "Reporting Manager" and step.get("status") == "pending":
                step["status"] = "approved"
                step["approved_by"] = current_user.full_name
                step["approved_at"] = now
                step["remarks"] = data.get("remarks", "")
        
        # Add HR approval step
        approval_flow.append({
            "step": 2,
            "approver": "HR/Finance",
            "role": "HR",
            "status": "pending"
        })
        
        await db.expenses.update_one(
            {"id": expense_id},
            {"$set": {
                "status": "manager_approved",
                "manager_approved_by": current_user.id,
                "manager_approved_by_name": current_user.full_name,
                "manager_approved_at": now,
                "manager_remarks": data.get("remarks", ""),
                "approval_flow": approval_flow,
                "current_approver": "HR/Finance",
                "current_approver_id": None,  # Any HR/Admin can approve
                "updated_at": now
            }}
        )
        
        # Notify HR managers
        hr_managers = await db.users.find({"role": {"$in": ["hr_manager", "admin"]}}, {"_id": 0, "id": 1}).to_list(10)
        for hr in hr_managers:
            notification = {
                "id": str(uuid.uuid4()),
                "user_id": hr["id"],
                "type": "expense_hr_approval",
                "title": "Expense Ready for HR Approval",
                "message": f"{employee_name}'s expense of ₹{expense_amount:,.0f} approved by manager, pending HR approval for payroll",
                "reference_type": "expense",
                "reference_id": expense_id,
                "is_read": False,
                "created_at": now
            }
            await db.notifications.insert_one(notification)
        
        # Notify employee
        if expense.get("user_id"):
            await db.notifications.insert_one({
                "id": str(uuid.uuid4()),
                "user_id": expense["user_id"],
                "type": "expense_update",
                "title": "Expense Approved by Manager",
                "message": f"Your expense of ₹{expense_amount:,.0f} was approved by {current_user.full_name}. Pending HR approval.",
                "reference_type": "expense",
                "reference_id": expense_id,
                "is_read": False,
                "created_at": now
            })
        
        return {
            "message": "Expense approved by manager, sent to HR for final approval",
            "status": "manager_approved",
            "next_step": "HR/Finance approval"
        }
    
    elif current_status == "manager_approved":
        # Stage 2: HR/Admin final approval - approved for payroll
        if not is_hr_admin:
            raise HTTPException(status_code=403, detail="Only HR/Admin can give final approval")
        
        # Update approval flow
        for step in approval_flow:
            if step.get("role") == "HR" and step.get("status") == "pending":
                step["status"] = "approved"
                step["approved_by"] = current_user.full_name
                step["approved_at"] = now
                step["remarks"] = data.get("remarks", "")
        
        # Get payroll period (current month)
        payroll_period = datetime.now(timezone.utc).strftime("%Y-%m")
        
        await db.expenses.update_one(
            {"id": expense_id},
            {"$set": {
                "status": "approved",
                "hr_approved_by": current_user.id,
                "hr_approved_by_name": current_user.full_name,
                "hr_approved_at": now,
                "hr_remarks": data.get("remarks", ""),
                "approval_flow": approval_flow,
                "current_approver": None,
                "current_approver_id": None,
                "payroll_period": payroll_period,
                "payroll_linked": True,
                "updated_at": now
            }}
        )
        
        # Link to payroll - add to employee's pending reimbursements
        if expense.get("employee_id"):
            await db.payroll_reimbursements.insert_one({
                "id": str(uuid.uuid4()),
                "employee_id": expense["employee_id"],
                "employee_code": expense.get("employee_code"),
                "employee_name": expense.get("employee_name"),
                "expense_id": expense_id,
                "amount": expense_amount,
                "category": expense.get("category") or "expense_reimbursement",
                "description": expense.get("description") or expense.get("notes", ""),
                "payroll_period": payroll_period,
                "status": "pending",
                "approved_by": current_user.id,
                "approved_by_name": current_user.full_name,
                "created_at": now
            })
        
        # Notify employee
        if expense.get("user_id"):
            await db.notifications.insert_one({
                "id": str(uuid.uuid4()),
                "user_id": expense["user_id"],
                "type": "expense_approved",
                "title": "Expense Fully Approved",
                "message": f"Your expense of ₹{expense_amount:,.0f} has been approved and will be included in {payroll_period} payroll.",
                "reference_type": "expense",
                "reference_id": expense_id,
                "is_read": False,
                "created_at": now
            })
        
        return {
            "message": "Expense fully approved and linked to payroll",
            "status": "approved",
            "payroll_period": payroll_period
        }


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
