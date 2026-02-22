"""
Expenses Router - Expense Management, Receipts, Approvals
"""

from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone
from typing import Optional, List
import uuid

from .models import User, UserRole
from .deps import get_db, sanitize_text, HR_ROLES, HR_ADMIN_ROLES, MANAGER_ROLES, APPROVAL_ROLES
from .auth import get_current_user
from services.approval_notifications import send_approval_notification
from websocket_manager import get_manager as get_ws_manager

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
    
    is_hr_admin = current_user.role in HR_ADMIN_ROLES
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
    if current_user.role not in APPROVAL_ROLES:
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


@router.delete("/{expense_id}")
async def delete_expense(expense_id: str, current_user: User = Depends(get_current_user)):
    """Delete an expense (only draft, pending, or rejected)."""
    db = get_db()
    
    expense = await db.expenses.find_one({"id": expense_id}, {"_id": 0})
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    
    # Only owner or admin can delete
    if expense["created_by"] != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to delete this expense")
    
    # Cannot delete approved expenses
    if expense["status"] == "approved":
        raise HTTPException(status_code=400, detail="Cannot delete approved expenses")
    
    await db.expenses.delete_one({"id": expense_id})
    
    return {"message": "Expense deleted"}


# Expense approval threshold - below this HR approves directly, above needs Admin
EXPENSE_HR_THRESHOLD = 2000  # ₹2000


@router.post("/{expense_id}/submit")
async def submit_expense(expense_id: str, current_user: User = Depends(get_current_user)):
    """
    Submit expense for approval:
    - < ₹2000: HR directly approves (single level)
    - ≥ ₹2000: Admin approval required
    
    Sends real-time email + WebSocket notifications to approvers.
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
    
    # Get requester email
    requester_user = await db.users.find_one({"id": current_user.id})
    requester_email = requester_user.get("email", "") if requester_user else ""
    
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
    
    # Send real-time approval notifications (email + WebSocket) to HR managers
    hr_managers = await db.users.find(
        {"role": {"$in": ["hr_manager"]}}, 
        {"_id": 0, "id": 1, "full_name": 1, "email": 1}
    ).to_list(10)
    
    threshold_note = " (Requires Admin approval after HR)" if requires_admin else ""
    expense_details = {
        "Amount": f"₹{expense_amount:,.0f}",
        "Category": expense.get("category", "General").replace("_", " ").title(),
        "Description": expense.get("description") or expense.get("notes", "No description"),
        "Date": expense.get("expense_date", "Not specified"),
        "Note": threshold_note if requires_admin else "HR can approve directly"
    }
    
    ws_manager = get_ws_manager()
    
    for hr in hr_managers:
        try:
            await send_approval_notification(
                db=db,
                ws_manager=ws_manager,
                record_type="expense",
                record_id=expense_id,
                requester_id=current_user.id,
                requester_name=employee_name,
                requester_email=requester_email,
                approver_id=hr["id"],
                approver_name=hr.get("full_name", "HR Manager"),
                approver_email=hr.get("email", ""),
                details=expense_details,
                link="/expense-approvals"
            )
        except Exception as e:
            print(f"Error sending approval notification to HR {hr['id']}: {e}")
    
    return {
        "message": "Expense submitted for approval",
        "approval_flow": approval_flow,
        "current_approver": current_approver,
        "requires_admin": requires_admin,
        "threshold": EXPENSE_HR_THRESHOLD
    }


@router.post("/{expense_id}/approve")
async def approve_expense(expense_id: str, data: dict, current_user: User = Depends(get_current_user)):
    """
    Simplified expense approval:
    - < ₹2000: HR directly approves → linked to payroll
    - ≥ ₹2000: HR approves → Admin approves → linked to payroll
    """
    db = get_db()
    
    expense = await db.expenses.find_one({"id": expense_id}, {"_id": 0})
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    
    current_status = expense.get("status")
    approval_flow = expense.get("approval_flow", [])
    requires_admin = expense.get("requires_admin_approval", False)
    
    is_hr = current_user.role in ["hr_manager", "hr_executive"]
    is_admin = current_user.role == "admin"
    
    if not (is_hr or is_admin):
        raise HTTPException(status_code=403, detail="Only HR or Admin can approve expenses")
    
    if current_status not in ["pending", "hr_approved"]:
        raise HTTPException(status_code=400, detail=f"Expense cannot be approved in '{current_status}' status")
    
    now = datetime.now(timezone.utc).isoformat()
    employee_name = expense.get("employee_name", "Employee")
    expense_amount = expense.get("total_amount") or expense.get("amount", 0)
    
    if current_status == "pending":
        # HR approving
        if not (is_hr or is_admin):
            raise HTTPException(status_code=403, detail="Only HR can approve at this stage")
        
        # Update approval flow - HR step
        for step in approval_flow:
            if step.get("role") == "HR" and step.get("status") == "pending":
                step["status"] = "approved"
                step["approved_by"] = current_user.full_name
                step["approved_at"] = now
                step["remarks"] = data.get("remarks", "")
        
        if requires_admin:
            # Needs Admin approval next
            await db.expenses.update_one(
                {"id": expense_id},
                {"$set": {
                    "status": "hr_approved",
                    "hr_approved_by": current_user.id,
                    "hr_approved_by_name": current_user.full_name,
                    "hr_approved_at": now,
                    "hr_remarks": data.get("remarks", ""),
                    "approval_flow": approval_flow,
                    "current_approver": "Admin",
                    "updated_at": now
                }}
            )
            
            # Send real-time approval notification (email + WebSocket) to Admins
            admins = await db.users.find(
                {"role": "admin"}, 
                {"_id": 0, "id": 1, "full_name": 1, "email": 1}
            ).to_list(10)
            
            ws_manager = get_ws_manager()
            admin_expense_details = {
                "Amount": f"₹{expense_amount:,.0f}",
                "Employee": employee_name,
                "Category": expense.get("category", "General").replace("_", " ").title(),
                "Description": expense.get("description") or expense.get("notes", "No description"),
                "HR Approved By": current_user.full_name,
                "Status": "Pending Admin Approval"
            }
            
            for admin in admins:
                try:
                    await send_approval_notification(
                        db=db,
                        ws_manager=ws_manager,
                        record_type="expense",
                        record_id=expense_id,
                        requester_id=expense.get("user_id") or expense.get("employee_id"),
                        requester_name=employee_name,
                        requester_email="",  # Already HR-approved, email goes to admin
                        approver_id=admin["id"],
                        approver_name=admin.get("full_name", "Admin"),
                        approver_email=admin.get("email", ""),
                        details=admin_expense_details,
                        link="/expense-approvals"
                    )
                except Exception as e:
                    print(f"Error sending approval notification to Admin {admin['id']}: {e}")
            
            return {
                "message": "Expense approved by HR, sent to Admin for final approval",
                "status": "hr_approved",
                "next_step": "Admin approval"
            }
        else:
            # Small expense - HR approval is final
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
                    "payroll_period": payroll_period,
                    "payroll_linked": True,
                    "updated_at": now
                }}
            )
            
            # Link to payroll reimbursements
            if expense.get("employee_id"):
                await db.payroll_reimbursements.insert_one({
                    "id": str(uuid.uuid4()),
                    "employee_id": expense["employee_id"],
                    "employee_code": expense.get("employee_code"),
                    "employee_name": employee_name,
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
                    "title": "Expense Approved",
                    "message": f"Your expense of ₹{expense_amount:,.0f} approved by HR and linked to {payroll_period} payroll.",
                    "reference_type": "expense",
                    "reference_id": expense_id,
                    "is_read": False,
                    "created_at": now
                })
            
            return {
                "message": "Expense approved and linked to payroll",
                "status": "approved",
                "payroll_period": payroll_period
            }
    
    elif current_status == "hr_approved":
        # Admin final approval for large expenses
        if not is_admin:
            raise HTTPException(status_code=403, detail="Only Admin can give final approval for expenses ≥ ₹2000")
        
        # Update approval flow - Admin step
        for step in approval_flow:
            if step.get("role") == "Admin" and step.get("status") == "pending":
                step["status"] = "approved"
                step["approved_by"] = current_user.full_name
                step["approved_at"] = now
                step["remarks"] = data.get("remarks", "")
        
        payroll_period = datetime.now(timezone.utc).strftime("%Y-%m")
        
        await db.expenses.update_one(
            {"id": expense_id},
            {"$set": {
                "status": "approved",
                "admin_approved_by": current_user.id,
                "admin_approved_by_name": current_user.full_name,
                "admin_approved_at": now,
                "admin_remarks": data.get("remarks", ""),
                "approval_flow": approval_flow,
                "current_approver": None,
                "payroll_period": payroll_period,
                "payroll_linked": True,
                "updated_at": now
            }}
        )
        
        # Link to payroll reimbursements
        if expense.get("employee_id"):
            await db.payroll_reimbursements.insert_one({
                "id": str(uuid.uuid4()),
                "employee_id": expense["employee_id"],
                "employee_code": expense.get("employee_code"),
                "employee_name": employee_name,
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
                "message": f"Your expense of ₹{expense_amount:,.0f} approved by Admin and linked to {payroll_period} payroll.",
                "reference_type": "expense",
                "reference_id": expense_id,
                "is_read": False,
                "created_at": now
            })
        
        return {
            "message": "Expense approved by Admin and linked to payroll",
            "status": "approved",
            "payroll_period": payroll_period
        }


@router.post("/{expense_id}/reject")
async def reject_expense(expense_id: str, data: dict, current_user: User = Depends(get_current_user)):
    """Reject an expense."""
    db = get_db()
    
    if current_user.role not in APPROVAL_ROLES:
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
    
    if current_user.role not in HR_ADMIN_ROLES:
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
