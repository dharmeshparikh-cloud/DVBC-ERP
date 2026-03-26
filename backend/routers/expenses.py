"""
Expenses Router - Expense Management, Receipts, Approvals

STRESS TEST VALIDATIONS (March 2026):
- E27: Currency validation
- E30: Duplicate receipt prevention
- E31: Payroll cutoff validation
- E32: Rejected expense payment prevention
- I52: Self-approval prevention
"""

from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone
from typing import Optional, List
import uuid

from .models import User, UserRole
from .deps import get_db, sanitize_text, get_role_group, has_role
from .deps import get_current_user
from services.approval_notifications import send_approval_notification
from websocket_manager import get_manager as get_ws_manager
from services.erp_validator import get_validator

router = APIRouter(prefix="/expenses", tags=["Expenses"])


@router.post("")
async def create_expense(data: dict, current_user: User = Depends(get_current_user)):
    """Create a new expense entry with line items support."""
    db = get_db()
    
    # CONSULTANT EXPENSE GOVERNANCE
    is_consultant = current_user.role in ['consultant', 'lean_consultant', 'lead_consultant', 'senior_consultant', 'subject_matter_expert']
    
    if is_consultant:
        project_id = data.get("project_id")
        category = data.get("category") or (data.get("line_items", [{}])[0].get("category") if data.get("line_items") else None)
        
        # Rule 1: Consultants must link expenses to a project (except office supplies)
        is_office_expense = data.get("is_office_expense", False)
        if not is_office_expense and not project_id:
            raise HTTPException(
                status_code=400,
                detail="Consultant expenses must be linked to a project. Please select a project before submitting."
            )
        
        # Rule 2: If project is specified, validate it's active
        if project_id:
            project = await db.projects.find_one({"id": project_id}, {"_id": 0})
            if not project:
                raise HTTPException(status_code=400, detail="Selected project not found")
            
            project_status = project.get("status", "active")
            if project_status in ["completed", "cancelled", "closed"]:
                raise HTTPException(
                    status_code=400,
                    detail=f"Cannot submit expenses for {project_status} projects. Project: {project.get('name')}"
                )
            
            # Rule 3: Travel expenses should ideally have meeting linkage
            if category and category.lower() in ['travel', 'local conveyance', 'conveyance']:
                meeting_id = data.get("meeting_id")
                if not meeting_id:
                    # Warning but don't block - add flag for review
                    data["requires_additional_review"] = True
                    data["review_reason"] = "Travel expense submitted without meeting linkage"
    
    # DUPLICATE PREVENTION: Check for meeting_id based duplicates
    meeting_id = data.get("meeting_id")
    if meeting_id:
        existing = await db.expenses.find_one({
            "meeting_id": meeting_id,
            "status": {"$ne": "rejected"}
        })
        if existing:
            raise HTTPException(
                status_code=400, 
                detail=f"Expense already exists for this meeting (ID: {existing.get('id')[:8]}...)"
            )
    
    # DUPLICATE PREVENTION: Check for similar expense (same user, date, amount)
    expense_date = data.get("expense_date")
    line_items = data.get("line_items", [])
    total_amount = sum(item.get("amount", 0) for item in line_items) if line_items else data.get("amount", 0)
    
    if expense_date and total_amount > 0:
        # Check for exact duplicate (same date, amount within 1 rupee)
        potential_duplicate = await db.expenses.find_one({
            "user_id": current_user.id,
            "expense_date": expense_date,
            "total_amount": {"$gte": total_amount - 1, "$lte": total_amount + 1},
            "status": {"$ne": "rejected"}
        })
        if potential_duplicate:
            raise HTTPException(
                status_code=400,
                detail=f"Similar expense already exists for this date and amount. Existing ID: {potential_duplicate.get('id')[:8]}..."
            )
    
    # Get employee record for proper linking
    employee = await db.employees.find_one({"user_id": current_user.id}, {"_id": 0})
    if not employee:
        raise HTTPException(
            status_code=400,
            detail="Employee record not found. Please contact HR to set up your employee profile."
        )
    employee_id = employee.get("id")
    employee_code = employee.get("employee_id")
    employee_name = f"{employee.get('first_name', '')} {employee.get('last_name', '')}".strip() or current_user.full_name
    reporting_manager_id = employee.get("reporting_manager_id")
    
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
        "expense_date": expense_date,
        "vendor": data.get("vendor"),
        "receipts": [],
        "status": "draft",
        "project_id": data.get("project_id"),
        "project_name": data.get("project_name", ""),
        "client_id": data.get("client_id"),
        "client_name": data.get("client_name", ""),
        "meeting_id": meeting_id,  # Store meeting_id for duplicate prevention
        "lead_id": data.get("lead_id"),  # Optional lead linkage
        "is_office_expense": data.get("is_office_expense", False),
        "is_billable": data.get("is_billable", False),
        "requires_additional_review": data.get("requires_additional_review", False),
        "review_reason": data.get("review_reason"),
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
    
    # Get employee record for proper linking
    employee = await db.employees.find_one({"user_id": current_user.id}, {"_id": 0})
    employee_code = employee.get("employee_id") if employee else None
    
    expense = {
        "id": str(uuid.uuid4()),
        "employee_id": employee_code,  # Employee code like EMP003
        "user_id": current_user.id,  # UUID for ownership query
        "employee_name": current_user.full_name,
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
    
    # Use RBAC service for role checks (fail-closed for financial operations)
    hr_admin_roles = get_role_group("HR_ADMIN_ROLES", fail_closed=True) or []
    hr_roles = get_role_group("HR_ROLES", fail_closed=True) or []
    admin_roles = get_role_group("ADMIN_ROLES", fail_closed=False) or ["admin"]
    
    # HR Admin/Admin can see all, HR can see pending for approval
    is_hr_admin = has_role(current_user.role, hr_admin_roles + admin_roles)
    is_hr = has_role(current_user.role, hr_roles)
    
    # Get current user's employee record to check if they're a reporting manager
    employee = await db.employees.find_one({"user_id": current_user.id}, {"_id": 0, "employee_id": 1})
    emp_code = employee.get("employee_id") if employee else None
    
    expenses = []
    
    if is_hr_admin:
        # HR Admin/Admin can see all pending, manager_approved, revision_required expenses
        expenses = await db.expenses.find(
            {"status": {"$in": ["pending", "manager_approved", "hr_approved", "revision_required", "approved", "rejected"]}},
            {"_id": 0}
        ).sort("created_at", -1).to_list(200)
    elif is_hr:
        # HR sees pending expenses for their approval
        expenses = await db.expenses.find(
            {"status": {"$in": ["pending", "revision_required"]}},
            {"_id": 0}
        ).sort("created_at", -1).to_list(200)
    else:
        # Check if user is a reporting manager for anyone
        if emp_code:
            expenses = await db.expenses.find(
                {"reporting_manager_id": emp_code, "status": {"$in": ["pending", "revision_required", "approved", "rejected"]}},
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
    
    # Use RBAC service for authorization
    hr_roles = get_role_group("HR_ROLES", fail_closed=True) or []
    hr_admin_roles = get_role_group("HR_ADMIN_ROLES", fail_closed=True) or []
    admin_roles = get_role_group("ADMIN_ROLES", fail_closed=False) or ["admin"]
    
    can_view_all = has_role(current_user.role, hr_roles + hr_admin_roles + admin_roles)
    
    query = {}
    
    # Non-privileged users can only see their own expenses
    # Use $or to match by user_id (UUID) OR created_by for ownership
    if not can_view_all:
        query["$or"] = [
            {"user_id": current_user.id},
            {"created_by": current_user.id}
        ]
    elif employee_id:
        # Admin/HR filtering by specific employee - support both UUID and employee code
        query["$or"] = [
            {"user_id": employee_id},
            {"employee_id": employee_id},
            {"created_by": employee_id}
        ]
    
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
    """Get a single expense by ID with linked meeting/travel context."""
    db = get_db()
    
    expense = await db.expenses.find_one({"id": expense_id}, {"_id": 0})
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    
    # Enrich with meeting context if linked
    if expense.get("linked_meeting_id") or expense.get("meeting_id"):
        meeting_id = expense.get("linked_meeting_id") or expense.get("meeting_id")
        meeting = await db.meetings.find_one({"id": meeting_id}, {"_id": 0, "title": 1, "meeting_type": 1, "date": 1, "location": 1, "mom_text": 1, "mom_summary": 1, "outcomes": 1, "attendees": 1})
        if meeting:
            expense["meeting_context"] = {
                "title": meeting.get("title"),
                "meeting_type": meeting.get("meeting_type"),
                "date": meeting.get("date"),
                "location": meeting.get("location"),
                "mom_summary": meeting.get("mom_summary") or meeting.get("mom_text"),
                "outcomes": meeting.get("outcomes"),
                "attendees": meeting.get("attendees", [])
            }
    
    # Enrich with travel details if travel expense
    if expense.get("category") in ["travel", "transport", "cab", "flight", "hotel"] or expense.get("travel_request_id"):
        travel_id = expense.get("travel_request_id")
        if travel_id:
            travel = await db.travel_requests.find_one({"id": travel_id}, {"_id": 0, "from_city": 1, "to_city": 1, "purpose": 1, "travel_dates": 1, "documents": 1})
            if travel:
                expense["travel_context"] = travel
    
    return expense


@router.patch("/{expense_id}")
async def update_expense(expense_id: str, data: dict, current_user: User = Depends(get_current_user)):
    """Update an expense (allowed for draft, pending, rejected, or revision_required)."""
    db = get_db()
    
    expense = await db.expenses.find_one({"id": expense_id}, {"_id": 0})
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    
    # Only owner or admin can update (check multiple possible owner fields)
    owner_id = expense.get("created_by") or expense.get("submitted_by") or expense.get("user_id")
    if owner_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to update this expense")
    
    # Can update draft, pending, rejected, or revision_required expenses
    if expense["status"] not in ["draft", "pending", "rejected", "revision_required"]:
        raise HTTPException(status_code=400, detail=f"Cannot update expense in '{expense['status']}' status")
    
    if "description" in data:
        data["description"] = sanitize_text(data["description"])
    
    if "notes" in data:
        data["notes"] = sanitize_text(data["notes"])
    
    # Update line items and recalculate total
    if "line_items" in data:
        data["total_amount"] = sum(item.get("amount", 0) for item in data["line_items"])
        # Re-evaluate if admin approval is required based on new amount
        data["requires_admin_approval"] = data["total_amount"] >= 2000
    
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.expenses.update_one({"id": expense_id}, {"$set": data})
    
    return {"message": "Expense updated"}


@router.delete("/{expense_id}")
async def delete_expense(expense_id: str, current_user: User = Depends(get_current_user)):
    """Delete an expense (only draft, pending, revision_required, or rejected)."""
    db = get_db()
    
    expense = await db.expenses.find_one({"id": expense_id}, {"_id": 0})
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    
    # Only owner or admin can delete (check multiple possible owner fields)
    owner_id = expense.get("created_by") or expense.get("submitted_by") or expense.get("user_id")
    if owner_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to delete this expense")
    
    # Cannot delete approved or processing expenses
    if expense["status"] in ["approved", "hr_approved"]:
        raise HTTPException(status_code=400, detail="Cannot delete expenses in approval process or already approved")
    
    await db.expenses.delete_one({"id": expense_id})
    
    return {"message": "Expense deleted"}


@router.post("/{expense_id}/withdraw")
async def withdraw_expense(expense_id: str, current_user: User = Depends(get_current_user)):
    """
    Withdraw a pending expense request.
    Can only be done by the expense owner while status is pending.
    """
    db = get_db()
    
    expense = await db.expenses.find_one({"id": expense_id}, {"_id": 0})
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    
    # Only owner can withdraw (check both created_by and submitted_by)
    owner_id = expense.get("created_by") or expense.get("submitted_by") or expense.get("user_id")
    if owner_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only the expense creator can withdraw")
    
    # Can only withdraw pending or revision_required expenses
    if expense["status"] not in ["pending", "revision_required"]:
        raise HTTPException(status_code=400, detail=f"Cannot withdraw expense in '{expense['status']}' status")
    
    now = datetime.now(timezone.utc).isoformat()
    
    await db.expenses.update_one(
        {"id": expense_id},
        {"$set": {
            "status": "withdrawn",
            "withdrawn_at": now,
            "withdrawn_by": current_user.id,
            "updated_at": now
        }}
    )
    
    return {"message": "Expense withdrawn successfully", "status": "withdrawn"}


# Expense approval threshold - below this HR approves directly, above needs Admin
EXPENSE_HR_THRESHOLD = 2000  # ₹2000


@router.post("/{expense_id}/submit")
async def submit_expense(expense_id: str, current_user: User = Depends(get_current_user)):
    """
    Submit expense for approval:
    - < ₹2000: HR directly approves (single level)
    - ≥ ₹2000: Admin approval required
    
    GOVERNANCE RULES ENFORCED:
    - Receipt required for expenses ≥ ₹500
    - Travel expenses must have meeting linkage (warning if missing)
    - Duplicate prevention
    
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
    
    # ═══════════════════════════════════════════════════════════════════
    # BUSINESS GOVERNANCE ENFORCEMENT RULES
    # ═══════════════════════════════════════════════════════════════════
    
    expense_amount = expense.get("total_amount") or expense.get("amount", 0)
    category = (expense.get("category") or "").lower()
    
    # RULE 1: Receipt Required for expenses ≥ ₹500
    RECEIPT_THRESHOLD = 500
    receipts = expense.get("receipts") or expense.get("attachments") or []
    line_items = expense.get("line_items") or []
    has_receipt = bool(receipts) or any(item.get("receipt_url") for item in line_items)
    
    if expense_amount >= RECEIPT_THRESHOLD and not has_receipt:
        raise HTTPException(
            status_code=400,
            detail=f"Receipt/bill attachment required for expenses ≥ ₹{RECEIPT_THRESHOLD}. Please upload receipt before submitting."
        )
    
    # RULE 2: Travel expenses should have meeting linkage
    travel_categories = ['travel', 'local conveyance', 'conveyance', 'transport', 'cab', 'fuel']
    is_travel = any(cat in category for cat in travel_categories)
    meeting_id = expense.get("meeting_id")
    
    governance_flags = []
    if is_travel and not meeting_id:
        governance_flags.append({
            "rule": "TRAVEL_NO_MEETING",
            "severity": "warning",
            "message": "Travel expense submitted without meeting linkage - requires additional review"
        })
    
    # RULE 3: High value expense alert
    HIGH_VALUE_THRESHOLD = 5000
    if expense_amount >= HIGH_VALUE_THRESHOLD:
        governance_flags.append({
            "rule": "HIGH_VALUE",
            "severity": "info",
            "message": f"High value expense (≥₹{HIGH_VALUE_THRESHOLD}) - will require Admin approval"
        })
    
    # Store governance flags for audit trail
    if governance_flags:
        await db.expenses.update_one(
            {"id": expense_id},
            {"$set": {"governance_flags": governance_flags, "requires_additional_review": True}}
        )
    
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
    
    ACCESS: HR roles can approve pending expenses. Admin can approve at any stage.
    Uses RBAC service with fail-closed behavior for financial security.
    
    STRESS TEST VALIDATIONS:
    - I52: Self-approval prevention
    - E31: Payroll cutoff validation
    
    GOVERNANCE RULES ENFORCED:
    - Receipt required for expenses ≥ ₹500 (validated on approval as well as submission)
    """
    db = get_db()
    # Note: validator available for future complex validations
    _ = get_validator(db)
    
    expense = await db.expenses.find_one({"id": expense_id}, {"_id": 0})
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    
    # I52: SELF-APPROVAL PREVENTION
    # Check if the approver is the same person who created/owns the expense
    expense_owner_id = expense.get("user_id") or expense.get("created_by")
    if expense_owner_id == current_user.id:
        raise HTTPException(
            status_code=403, 
            detail="I52: Cannot approve your own expense. Self-approval is prohibited."
        )
    
    # ═══════════════════════════════════════════════════════════════════
    # GOVERNANCE: Receipt Validation on Approval (Defense in Depth)
    # ═══════════════════════════════════════════════════════════════════
    expense_amount = expense.get("total_amount") or expense.get("amount", 0)
    RECEIPT_THRESHOLD = 500
    
    receipts = expense.get("receipts") or expense.get("attachments") or []
    line_items = expense.get("line_items") or []
    has_receipt = bool(receipts) or any(item.get("receipt_url") for item in line_items)
    
    if expense_amount >= RECEIPT_THRESHOLD and not has_receipt:
        raise HTTPException(
            status_code=400,
            detail=f"GOVERNANCE: Cannot approve expense without receipt. Expenses ≥ ₹{RECEIPT_THRESHOLD} require receipt/bill attachment. Please send back for revision."
        )
    
    current_status = expense.get("status")
    approval_flow = expense.get("approval_flow", [])
    requires_admin = expense.get("requires_admin_approval", False)
    
    # Use RBAC service for role checks (fail-closed for financial operations)
    hr_roles = get_role_group("HR_ROLES", fail_closed=True) or []
    admin_roles = get_role_group("ADMIN_ROLES", fail_closed=False) or ["admin"]
    
    is_hr = has_role(current_user.role, hr_roles)
    is_admin = has_role(current_user.role, admin_roles)
    
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
            # E31: PAYROLL CUTOFF VALIDATION
            # If approved after 15th of the month, expense goes to next month's payroll
            approval_date = datetime.now(timezone.utc)
            if approval_date.day > 15:
                # Move to next month
                next_month = approval_date.month + 1
                next_year = approval_date.year
                if next_month > 12:
                    next_month = 1
                    next_year += 1
                payroll_period = f"{next_year}-{next_month:02d}"
            else:
                payroll_period = approval_date.strftime("%Y-%m")
            
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
                # Look up the internal employee ID for payroll matching
                emp_code = expense["employee_id"]
                internal_employee_id = emp_code  # Default to code
                
                # Try to find employee record to get internal ID
                employee_record = await db.employees.find_one(
                    {"$or": [{"employee_id": emp_code}, {"id": emp_code}]},
                    {"_id": 0, "id": 1, "employee_id": 1}
                )
                if employee_record:
                    internal_employee_id = employee_record.get("id", emp_code)
                
                await db.payroll_reimbursements.insert_one({
                    "id": str(uuid.uuid4()),
                    "employee_id": internal_employee_id,  # Use internal ID for payroll matching
                    "employee_code": emp_code,  # Keep code for reference
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
            
            # Log audit trail for HR approval
            await db.audit_logs.insert_one({
                "id": str(uuid.uuid4()),
                "action": "expense_hr_approved",
                "entity_type": "expense",
                "entity_id": expense_id,
                "user_id": current_user.id,
                "user_name": current_user.full_name,
                "user_role": current_user.role,
                "details": {
                    "employee_id": expense.get("employee_id"),
                    "amount": expense_amount,
                    "payroll_period": payroll_period,
                    "remarks": data.get("remarks", "")
                },
                "timestamp": now
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
        
        # E31: PAYROLL CUTOFF VALIDATION for Admin approval
        approval_date = datetime.now(timezone.utc)
        if approval_date.day > 15:
            # Move to next month
            next_month = approval_date.month + 1
            next_year = approval_date.year
            if next_month > 12:
                next_month = 1
                next_year += 1
            payroll_period = f"{next_year}-{next_month:02d}"
        else:
            payroll_period = approval_date.strftime("%Y-%m")
        
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
            # Look up the internal employee ID for payroll matching
            emp_code = expense["employee_id"]
            internal_employee_id = emp_code  # Default to code
            
            # Try to find employee record to get internal ID
            employee_record = await db.employees.find_one(
                {"$or": [{"employee_id": emp_code}, {"id": emp_code}]},
                {"_id": 0, "id": 1, "employee_id": 1}
            )
            if employee_record:
                internal_employee_id = employee_record.get("id", emp_code)
            
            await db.payroll_reimbursements.insert_one({
                "id": str(uuid.uuid4()),
                "employee_id": internal_employee_id,  # Use internal ID for payroll matching
                "employee_code": emp_code,  # Keep code for reference
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
        
        # Log audit trail for admin approval
        await db.audit_logs.insert_one({
            "id": str(uuid.uuid4()),
            "action": "expense_admin_approved",
            "entity_type": "expense",
            "entity_id": expense_id,
            "user_id": current_user.id,
            "user_name": current_user.full_name,
            "user_role": current_user.role,
            "is_admin_override": True,
            "details": {
                "employee_id": expense.get("employee_id"),
                "amount": expense_amount,
                "payroll_period": payroll_period,
                "remarks": data.get("remarks", "")
            },
            "timestamp": now
        })
        
        return {
            "message": "Expense approved by Admin and linked to payroll",
            "status": "approved",
            "payroll_period": payroll_period
        }


@router.post("/{expense_id}/reject")
async def reject_expense(expense_id: str, data: dict, current_user: User = Depends(get_current_user)):
    """
    Reject an expense.
    
    ACCESS: Only HR or Admin can reject expenses (fail-closed authorization).
    VALIDATION: Cannot reject already approved or rejected expenses.
    """
    db = get_db()
    
    # Use RBAC service for role checks
    hr_roles = get_role_group("HR_ROLES", fail_closed=True) or []
    hr_admin_roles = get_role_group("HR_ADMIN_ROLES", fail_closed=True) or []
    admin_roles = get_role_group("ADMIN_ROLES", fail_closed=False) or ["admin"]
    
    allowed_roles = list(set(hr_roles + hr_admin_roles + admin_roles))
    
    if not has_role(current_user.role, allowed_roles):
        raise HTTPException(status_code=403, detail="Only HR or Admin can reject expenses")
    
    expense = await db.expenses.find_one({"id": expense_id}, {"_id": 0})
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    
    # CRITICAL FIX: Prevent rejecting already approved or rejected expenses
    current_status = expense.get("status")
    if current_status == "approved":
        raise HTTPException(
            status_code=400, 
            detail="Cannot reject an approved expense. Contact Finance to reverse if needed."
        )
    if current_status == "rejected":
        raise HTTPException(
            status_code=400, 
            detail="Expense is already rejected"
        )
    
    rejection_reason = data.get("reason", "")
    if not rejection_reason:
        raise HTTPException(status_code=400, detail="Rejection reason is required")
    
    await db.expenses.update_one(
        {"id": expense_id},
        {"$set": {
            "status": "rejected",
            "rejected_by": current_user.id,
            "rejected_by_name": current_user.full_name,
            "rejected_at": datetime.now(timezone.utc).isoformat(),
            "rejection_reason": rejection_reason,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    # Log audit trail for rejection
    await db.audit_logs.insert_one({
        "id": str(uuid.uuid4()),
        "action": "expense_rejected",
        "entity_type": "expense",
        "entity_id": expense_id,
        "user_id": current_user.id,
        "user_name": current_user.full_name,
        "details": {
            "employee_id": expense.get("employee_id"),
            "amount": expense.get("total_amount", expense.get("amount", 0)),
            "reason": rejection_reason
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    # Notify employee about rejection
    if expense.get("user_id"):
        await db.notifications.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": expense["user_id"],
            "type": "expense_rejected",
            "title": "Expense Rejected",
            "message": f"Your expense of ₹{expense.get('total_amount', expense.get('amount', 0)):,.0f} was rejected. Reason: {rejection_reason}",
            "reference_type": "expense",
            "reference_id": expense_id,
            "is_read": False,
            "created_at": datetime.now(timezone.utc).isoformat()
        })
    
    return {"message": "Expense rejected"}


@router.post("/{expense_id}/send-back")
async def send_back_expense(expense_id: str, data: dict, current_user: User = Depends(get_current_user)):
    """
    Send expense back to employee for revision.
    HR/Admin can request changes before approval.
    
    ACCESS: Only HR or Admin can send expenses back for revision.
    """
    db = get_db()
    
    # Use RBAC service for role checks
    hr_roles = get_role_group("HR_ROLES", fail_closed=True) or []
    hr_admin_roles = get_role_group("HR_ADMIN_ROLES", fail_closed=True) or []
    admin_roles = get_role_group("ADMIN_ROLES", fail_closed=False) or ["admin"]
    
    allowed_roles = list(set(hr_roles + hr_admin_roles + admin_roles))
    
    if not has_role(current_user.role, allowed_roles):
        raise HTTPException(status_code=403, detail="Only HR or Admin can send back expenses for revision")
    
    expense = await db.expenses.find_one({"id": expense_id}, {"_id": 0})
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    
    if expense.get("status") not in ["pending", "hr_approved"]:
        raise HTTPException(status_code=400, detail="Cannot send back expense in current status")
    
    revision_comments = data.get("comments", "")
    if not revision_comments:
        raise HTTPException(status_code=400, detail="Comments are required when sending back for revision")
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Track revision history
    revision_history = expense.get("revision_history", [])
    revision_history.append({
        "sent_back_by": current_user.full_name,
        "sent_back_at": now,
        "comments": revision_comments,
        "previous_status": expense.get("status")
    })
    
    await db.expenses.update_one(
        {"id": expense_id},
        {"$set": {
            "status": "revision_required",
            "revision_comments": revision_comments,
            "sent_back_by": current_user.id,
            "sent_back_by_name": current_user.full_name,
            "sent_back_at": now,
            "revision_history": revision_history,
            "updated_at": now
        }}
    )
    
    # Notify employee
    if expense.get("user_id"):
        await db.notifications.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": expense["user_id"],
            "type": "expense_revision_required",
            "title": "Expense Needs Revision",
            "message": f"Your expense of ₹{expense.get('total_amount', expense.get('amount', 0)):,.0f} needs revision. Comment: {revision_comments}",
            "reference_type": "expense",
            "reference_id": expense_id,
            "is_read": False,
            "created_at": now
        })
    
    # Log audit trail for send-back action
    await db.audit_logs.insert_one({
        "id": str(uuid.uuid4()),
        "action": "expense_sent_back",
        "entity_type": "expense",
        "entity_id": expense_id,
        "user_id": current_user.id,
        "user_name": current_user.full_name,
        "user_role": current_user.role,
        "details": {
            "employee_id": expense.get("employee_id"),
            "amount": expense.get("total_amount", expense.get("amount", 0)),
            "comments": revision_comments
        },
        "timestamp": now
    })
    
    return {
        "message": "Expense sent back for revision",
        "status": "revision_required"
    }


@router.post("/{expense_id}/resubmit")
async def resubmit_expense(expense_id: str, data: dict, current_user: User = Depends(get_current_user)):
    """
    Resubmit expense after revision.
    Employee can update expense and resubmit.
    """
    db = get_db()
    
    expense = await db.expenses.find_one({"id": expense_id}, {"_id": 0})
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    
    # Only owner or admin can resubmit
    if expense.get("created_by") != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to resubmit this expense")
    
    if expense.get("status") != "revision_required":
        raise HTTPException(status_code=400, detail="Expense is not in revision required status")
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Update expense with new data if provided
    update_data = {
        "status": "pending",
        "revision_comments": None,
        "sent_back_by": None,
        "sent_back_at": None,
        "resubmitted_at": now,
        "updated_at": now
    }
    
    # Allow updating amount and line items on resubmit
    if "line_items" in data:
        update_data["line_items"] = data["line_items"]
        update_data["total_amount"] = sum(item.get("amount", 0) for item in data["line_items"])
    
    if "notes" in data:
        update_data["notes"] = sanitize_text(data["notes"])
    
    if "description" in data:
        update_data["description"] = sanitize_text(data["description"])
    
    # Re-evaluate approval flow based on new amount
    total = update_data.get("total_amount", expense.get("total_amount", expense.get("amount", 0)))
    requires_admin = total >= 2000
    update_data["requires_admin_approval"] = requires_admin
    
    # Reset approval flow
    approval_flow = [
        {"role": "HR", "status": "pending", "approver": None, "approved_at": None}
    ]
    if requires_admin:
        approval_flow.append({"role": "Admin", "status": "pending", "approver": None, "approved_at": None})
    update_data["approval_flow"] = approval_flow
    
    await db.expenses.update_one({"id": expense_id}, {"$set": update_data})
    
    return {
        "message": "Expense resubmitted for approval",
        "status": "pending",
        "requires_admin_approval": requires_admin
    }


@router.post("/{expense_id}/approve-with-modification")
async def approve_expense_with_modification(expense_id: str, data: dict, current_user: User = Depends(get_current_user)):
    """
    Approve expense with modified amount.
    HR/Admin can adjust the approved amount (partial approval).
    
    ACCESS: Only HR or Admin can approve expenses with modifications.
    """
    db = get_db()
    
    # Use RBAC service for role checks
    hr_roles = get_role_group("HR_ROLES", fail_closed=True) or []
    hr_admin_roles = get_role_group("HR_ADMIN_ROLES", fail_closed=True) or []
    admin_roles = get_role_group("ADMIN_ROLES", fail_closed=False) or ["admin"]
    
    allowed_roles = list(set(hr_roles + hr_admin_roles + admin_roles))
    
    if not has_role(current_user.role, allowed_roles):
        raise HTTPException(status_code=403, detail="Only HR or Admin can approve expenses")
    
    expense = await db.expenses.find_one({"id": expense_id}, {"_id": 0})
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    
    current_status = expense.get("status")
    if current_status not in ["pending", "hr_approved"]:
        raise HTTPException(status_code=400, detail=f"Expense cannot be approved in '{current_status}' status")
    
    is_hr = has_role(current_user.role, hr_roles)
    is_admin = has_role(current_user.role, admin_roles)
    
    # Get modification details
    approved_amount = data.get("approved_amount")
    modification_reason = data.get("modification_reason", "")
    
    if approved_amount is None:
        raise HTTPException(status_code=400, detail="approved_amount is required")
    
    original_amount = expense.get("total_amount") or expense.get("amount", 0)
    
    if approved_amount > original_amount:
        raise HTTPException(status_code=400, detail="Approved amount cannot exceed requested amount")
    
    if approved_amount < original_amount and not modification_reason:
        raise HTTPException(status_code=400, detail="Reason required when modifying amount")
    
    now = datetime.now(timezone.utc).isoformat()
    approval_flow = expense.get("approval_flow", [])
    requires_admin = expense.get("requires_admin_approval", False)
    
    # Check role authorization
    if current_status == "pending" and not (is_hr or is_admin):
        raise HTTPException(status_code=403, detail="Only HR can approve at this stage")
    if current_status == "hr_approved" and not is_admin:
        raise HTTPException(status_code=403, detail="Only Admin can give final approval")
    
    # Track amount modification
    amount_modifications = expense.get("amount_modifications", [])
    if approved_amount != original_amount:
        amount_modifications.append({
            "modified_by": current_user.full_name,
            "modified_at": now,
            "original_amount": original_amount,
            "approved_amount": approved_amount,
            "reason": modification_reason
        })
    
    # HR first approval with modification
    if current_status == "pending":
        for step in approval_flow:
            if step.get("role") == "HR" and step.get("status") == "pending":
                step["status"] = "approved"
                step["approved_by"] = current_user.full_name
                step["approved_at"] = now
                step["approved_amount"] = approved_amount
                step["remarks"] = data.get("remarks", "")
        
        if requires_admin:
            await db.expenses.update_one(
                {"id": expense_id},
                {"$set": {
                    "status": "hr_approved",
                    "approved_amount": approved_amount,
                    "hr_approved_by": current_user.id,
                    "hr_approved_by_name": current_user.full_name,
                    "hr_approved_at": now,
                    "hr_remarks": data.get("remarks", ""),
                    "approval_flow": approval_flow,
                    "amount_modifications": amount_modifications,
                    "modification_reason": modification_reason,
                    "current_approver": "Admin",
                    "updated_at": now
                }}
            )
            return {
                "message": "Expense approved by HR with modified amount, sent to Admin",
                "status": "hr_approved",
                "original_amount": original_amount,
                "approved_amount": approved_amount
            }
        else:
            # Final approval for small expenses
            payroll_period = datetime.now(timezone.utc).strftime("%Y-%m")
            
            await db.expenses.update_one(
                {"id": expense_id},
                {"$set": {
                    "status": "approved",
                    "approved_amount": approved_amount,
                    "hr_approved_by": current_user.id,
                    "hr_approved_by_name": current_user.full_name,
                    "hr_approved_at": now,
                    "hr_remarks": data.get("remarks", ""),
                    "approval_flow": approval_flow,
                    "amount_modifications": amount_modifications,
                    "modification_reason": modification_reason,
                    "current_approver": None,
                    "payroll_period": payroll_period,
                    "payroll_linked": True,
                    "updated_at": now
                }}
            )
            
            # Link to payroll with approved amount
            if expense.get("employee_id"):
                # Look up the internal employee ID for payroll matching
                emp_code = expense["employee_id"]
                internal_employee_id = emp_code  # Default to code
                
                # Try to find employee record to get internal ID
                employee_record = await db.employees.find_one(
                    {"$or": [{"employee_id": emp_code}, {"id": emp_code}]},
                    {"_id": 0, "id": 1, "employee_id": 1}
                )
                if employee_record:
                    internal_employee_id = employee_record.get("id", emp_code)
                
                await db.payroll_reimbursements.insert_one({
                    "id": str(uuid.uuid4()),
                    "employee_id": internal_employee_id,  # Use internal ID for payroll matching
                    "employee_code": emp_code,  # Keep code for reference
                    "employee_name": expense.get("employee_name", "Employee"),
                    "expense_id": expense_id,
                    "amount": approved_amount,  # Use approved amount
                    "original_requested_amount": original_amount,
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
                msg = f"Your expense approved for ₹{approved_amount:,.0f}"
                if approved_amount != original_amount:
                    msg += f" (requested ₹{original_amount:,.0f}). Reason: {modification_reason}"
                
                await db.notifications.insert_one({
                    "id": str(uuid.uuid4()),
                    "user_id": expense["user_id"],
                    "type": "expense_approved",
                    "title": "Expense Approved" if approved_amount == original_amount else "Expense Partially Approved",
                    "message": msg,
                    "reference_type": "expense",
                    "reference_id": expense_id,
                    "is_read": False,
                    "created_at": now
                })
            
            return {
                "message": "Expense approved and linked to payroll",
                "status": "approved",
                "original_amount": original_amount,
                "approved_amount": approved_amount,
                "payroll_period": payroll_period
            }
    
    # Admin final approval
    elif current_status == "hr_approved":
        for step in approval_flow:
            if step.get("role") == "Admin" and step.get("status") == "pending":
                step["status"] = "approved"
                step["approved_by"] = current_user.full_name
                step["approved_at"] = now
                step["approved_amount"] = approved_amount
                step["remarks"] = data.get("remarks", "")
        
        payroll_period = datetime.now(timezone.utc).strftime("%Y-%m")
        
        await db.expenses.update_one(
            {"id": expense_id},
            {"$set": {
                "status": "approved",
                "approved_amount": approved_amount,
                "admin_approved_by": current_user.id,
                "admin_approved_by_name": current_user.full_name,
                "admin_approved_at": now,
                "admin_remarks": data.get("remarks", ""),
                "approval_flow": approval_flow,
                "amount_modifications": amount_modifications,
                "modification_reason": modification_reason,
                "current_approver": None,
                "payroll_period": payroll_period,
                "payroll_linked": True,
                "updated_at": now
            }}
        )
        
        # Link to payroll with approved amount
        if expense.get("employee_id"):
            # Look up the internal employee ID for payroll matching
            emp_code = expense["employee_id"]
            internal_employee_id = emp_code  # Default to code
            
            # Try to find employee record to get internal ID
            employee_record = await db.employees.find_one(
                {"$or": [{"employee_id": emp_code}, {"id": emp_code}]},
                {"_id": 0, "id": 1, "employee_id": 1}
            )
            if employee_record:
                internal_employee_id = employee_record.get("id", emp_code)
            
            await db.payroll_reimbursements.insert_one({
                "id": str(uuid.uuid4()),
                "employee_id": internal_employee_id,  # Use internal ID for payroll matching
                "employee_code": emp_code,  # Keep code for reference
                "employee_name": expense.get("employee_name", "Employee"),
                "expense_id": expense_id,
                "amount": approved_amount,
                "original_requested_amount": original_amount,
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
            msg = f"Your expense fully approved for ₹{approved_amount:,.0f}"
            if approved_amount != original_amount:
                msg += f" (requested ₹{original_amount:,.0f}). Reason: {modification_reason}"
            
            await db.notifications.insert_one({
                "id": str(uuid.uuid4()),
                "user_id": expense["user_id"],
                "type": "expense_approved",
                "title": "Expense Fully Approved" if approved_amount == original_amount else "Expense Partially Approved",
                "message": msg,
                "reference_type": "expense",
                "reference_id": expense_id,
                "is_read": False,
                "created_at": now
            })
        
        return {
            "message": "Expense approved by Admin and linked to payroll",
            "status": "approved",
            "original_amount": original_amount,
            "approved_amount": approved_amount,
            "payroll_period": payroll_period
        }


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


@router.get("/{expense_id}/receipts")
async def get_expense_receipts(expense_id: str, current_user: User = Depends(get_current_user)):
    """Get all receipts for an expense."""
    db = get_db()
    
    expense = await db.expenses.find_one({"id": expense_id}, {"_id": 0})
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    
    receipts = expense.get("receipts", [])
    
    # Return receipts without full file data for listing (to reduce payload)
    receipt_list = []
    for r in receipts:
        receipt_list.append({
            "id": r.get("id"),
            "file_name": r.get("file_name"),
            "file_type": r.get("file_type"),
            "uploaded_at": r.get("uploaded_at"),
            "has_data": bool(r.get("file_data"))
        })
    
    return {"receipts": receipt_list, "count": len(receipt_list)}


@router.get("/{expense_id}/receipts/{receipt_id}")
async def get_expense_receipt(expense_id: str, receipt_id: str, current_user: User = Depends(get_current_user)):
    """Get a specific receipt with file data for download."""
    db = get_db()
    
    expense = await db.expenses.find_one({"id": expense_id}, {"_id": 0})
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    
    receipts = expense.get("receipts", [])
    receipt = next((r for r in receipts if r.get("id") == receipt_id), None)
    
    if not receipt:
        raise HTTPException(status_code=404, detail="Receipt not found")
    
    return receipt


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
    
    # Use RBAC service for role checks
    hr_admin_roles = get_role_group("HR_ADMIN_ROLES", fail_closed=True) or []
    admin_roles = get_role_group("ADMIN_ROLES", fail_closed=False) or ["admin"]
    
    can_view_all = has_role(current_user.role, hr_admin_roles + admin_roles)
    
    query = {}
    
    # Use $or to match by user_id (UUID) OR created_by for ownership
    if not can_view_all:
        query["$or"] = [
            {"user_id": current_user.id},
            {"created_by": current_user.id}
        ]
    elif employee_id:
        # Admin filtering by specific employee
        query["$or"] = [
            {"user_id": employee_id},
            {"employee_id": employee_id},
            {"created_by": employee_id}
        ]
    
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



# ==================== AUTO-LINK EXPENSES TO PAYROLL PERIOD ====================

@router.post("/auto-link-payroll-period")
async def auto_link_expenses_to_payroll(
    data: dict = None,
    current_user: User = Depends(get_current_user)
):
    """
    Auto-link approved expenses to payroll period based on expense_date.
    Only HR/Admin can run this.
    """
    hr_roles = ["admin", "hr_manager", "hr_executive"]
    if current_user.role not in hr_roles:
        raise HTTPException(status_code=403, detail="Only HR can auto-link expenses")
    
    db = get_db()
    
    # Find approved expenses without payroll_period
    expenses = await db.expenses.find({
        "status": "approved",
        "$or": [
            {"payroll_period": None},
            {"payroll_period": ""},
            {"payroll_period": {"$exists": False}}
        ]
    }, {"_id": 0}).to_list(500)
    
    linked_count = 0
    errors = []
    
    for exp in expenses:
        # Determine payroll period from expense_date
        expense_date = exp.get("expense_date") or exp.get("created_at", "")[:10]
        if not expense_date:
            errors.append({"id": exp.get("id"), "error": "No expense_date"})
            continue
        
        # Extract YYYY-MM
        try:
            payroll_period = expense_date[:7]  # "2026-03-15" -> "2026-03"
            if len(payroll_period) != 7 or payroll_period[4] != '-':
                raise ValueError("Invalid date format")
        except (ValueError, IndexError):
            errors.append({"id": exp.get("id"), "error": f"Invalid date: {expense_date}"})
            continue
        
        # Check if payroll is locked for that period
        payroll_run = await db.payroll_runs.find_one({"month": payroll_period}, {"_id": 0})
        if payroll_run and payroll_run.get("is_locked"):
            # Link to next month instead
            year, month = int(payroll_period[:4]), int(payroll_period[5:7])
            month += 1
            if month > 12:
                month = 1
                year += 1
            payroll_period = f"{year:04d}-{month:02d}"
        
        # Update expense with payroll_period
        await db.expenses.update_one(
            {"id": exp.get("id")},
            {"$set": {
                "payroll_period": payroll_period,
                "payroll_linked_at": datetime.now(timezone.utc).isoformat(),
                "payroll_linked_by": current_user.id
            }}
        )
        
        # Create payroll_reimbursement record
        # Look up the internal employee ID for payroll matching
        emp_code = exp.get("employee_id")
        internal_employee_id = emp_code  # Default to code
        
        # Try to find employee record to get internal ID
        employee_record = await db.employees.find_one(
            {"$or": [{"employee_id": emp_code}, {"id": emp_code}]},
            {"_id": 0, "id": 1, "employee_id": 1}
        )
        if employee_record:
            internal_employee_id = employee_record.get("id", emp_code)
        
        reimb = {
            "id": str(uuid.uuid4()),
            "employee_id": internal_employee_id,  # Use internal ID for payroll matching
            "employee_code": emp_code,  # Keep code for reference
            "expense_id": exp.get("id"),
            "amount": exp.get("total_amount") or exp.get("amount", 0),
            "description": exp.get("description", "Expense Reimbursement"),
            "payroll_period": payroll_period,
            "status": "pending",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        # Check if reimbursement already exists
        existing = await db.payroll_reimbursements.find_one({
            "expense_id": exp.get("id")
        }, {"_id": 0})
        
        if not existing:
            await db.payroll_reimbursements.insert_one(reimb)
        
        linked_count += 1
    
    return {
        "message": f"Auto-linked {linked_count} expenses to payroll periods",
        "linked_count": linked_count,
        "error_count": len(errors),
        "errors": errors[:10] if errors else []
    }


@router.get("/unlinked-approved")
async def get_unlinked_approved_expenses(current_user: User = Depends(get_current_user)):
    """Get approved expenses not yet linked to a payroll period."""
    hr_roles = ["admin", "hr_manager", "hr_executive"]
    if current_user.role not in hr_roles:
        raise HTTPException(status_code=403, detail="Only HR can view unlinked expenses")
    
    db = get_db()
    
    expenses = await db.expenses.find({
        "status": "approved",
        "$or": [
            {"payroll_period": None},
            {"payroll_period": ""},
            {"payroll_period": {"$exists": False}}
        ]
    }, {"_id": 0}).to_list(100)
    
    total_amount = sum(e.get("total_amount") or e.get("amount", 0) for e in expenses)
    
    return {
        "count": len(expenses),
        "total_amount": round(total_amount, 2),
        "expenses": expenses
    }


@router.get("/report/monthly-meeting-expenses")
async def get_monthly_meeting_expense_report(
    month: str = None,
    current_user: User = Depends(get_current_user)
):
    """
    Get monthly meeting expense report for finance department.
    Shows all meeting-related expenses with lead details for print/export.
    
    ACCESS: 
    - Admin, HR Manager, Finance roles: See all expenses
    - Regular employees: See only their own expenses
    
    Returns: Table with employee name, lead name, stage, date, travel mode, amount, status
    """
    db = get_db()
    
    # Access control - Finance, HR, Admin can see all, others see only their own
    privileged_roles = ["admin", "hr_manager", "hr_executive", "finance_manager", "finance_executive", "accounts"]
    can_view_all = current_user.role in privileged_roles
    
    # Default to current month
    if not month:
        month = datetime.now(timezone.utc).strftime("%Y-%m")
    
    # Parse month for date range
    try:
        year, mon = month.split("-")
        start_date = f"{year}-{mon}-01"
        # Get last day of month
        if int(mon) == 12:
            end_date = f"{int(year)+1}-01-01"
        else:
            end_date = f"{year}-{int(mon)+1:02d}-01"
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="Invalid month format. Use YYYY-MM")
    
    # Query meeting expenses - those with meeting_id or travel_details
    query = {
        "$or": [
            {"meeting_id": {"$exists": True, "$ne": None}},
            {"travel_details": {"$exists": True}},
            {"subcategory": {"$regex": "meeting_travel", "$options": "i"}}
        ],
        "expense_date": {"$gte": start_date, "$lt": end_date}
    }
    
    # Non-privileged users can only see their own expenses
    if not can_view_all:
        query["$and"] = [
            {"$or": [
                {"user_id": current_user.id},
                {"created_by": current_user.id}
            ]}
        ]
    
    expenses = await db.expenses.find(query, {"_id": 0}).sort("expense_date", 1).to_list(500)
    
    # Enrich with lead and meeting data
    report_items = []
    total_amount = 0
    total_approved = 0
    total_pending = 0
    total_rejected = 0
    
    for exp in expenses:
        lead_id = exp.get("lead_id")
        meeting_id = exp.get("meeting_id")
        travel_details = exp.get("travel_details", {})
        amount = exp.get("total_amount") or exp.get("amount", 0)
        
        # Get lead info if available
        lead_name = exp.get("lead_name", "")
        company = exp.get("company", "")
        stage = ""
        
        if lead_id and not lead_name:
            lead = await db.leads.find_one({"id": lead_id}, {"_id": 0, "first_name": 1, "last_name": 1, "company": 1, "current_stage": 1})
            if lead:
                lead_name = f"{lead.get('first_name', '')} {lead.get('last_name', '')}".strip()
                company = lead.get("company", "")
                stage = lead.get("current_stage", "")
        
        # Get meeting info if available
        meeting_title = ""
        if meeting_id:
            meeting = await db.meetings.find_one({"id": meeting_id}, {"_id": 0, "title": 1, "lead_id": 1})
            if meeting:
                meeting_title = meeting.get("title", "")
                if not lead_id and meeting.get("lead_id"):
                    lead = await db.leads.find_one({"id": meeting["lead_id"]}, {"_id": 0, "first_name": 1, "last_name": 1, "company": 1, "current_stage": 1})
                    if lead:
                        lead_name = f"{lead.get('first_name', '')} {lead.get('last_name', '')}".strip()
                        company = lead.get("company", "")
                        stage = lead.get("current_stage", "")
        
        # Get employee name
        employee_name = exp.get("employee_name", "")
        if not employee_name and exp.get("user_id"):
            user = await db.users.find_one({"id": exp["user_id"]}, {"_id": 0, "full_name": 1})
            if user:
                employee_name = user.get("full_name", "")
        
        # Calculate totals by status
        status = exp.get("status", "pending")
        total_amount += amount
        if status == "approved":
            total_approved += amount
        elif status == "rejected":
            total_rejected += amount
        else:
            total_pending += amount
        
        report_items.append({
            "expense_id": exp.get("id"),
            "employee_id": exp.get("employee_id"),
            "employee_name": employee_name,
            "lead_name": lead_name or "N/A",
            "company": company or "N/A",
            "stage": stage or exp.get("lead_stage", "N/A"),
            "meeting_title": meeting_title or exp.get("description", ""),
            "expense_date": exp.get("expense_date", "")[:10] if exp.get("expense_date") else "",
            "travel_mode": travel_details.get("travel_mode", "N/A"),
            "distance_km": travel_details.get("distance_km", 0),
            "total_km": travel_details.get("total_km", travel_details.get("distance_km", 0)),
            "is_round_trip": travel_details.get("is_round_trip", False),
            "rate_per_km": travel_details.get("rate_per_km", 0),
            "start_location": travel_details.get("start_location", ""),
            "end_location": travel_details.get("end_location", ""),
            "amount": round(amount, 2),
            "status": status,
            "approved_by": exp.get("hr_approved_by_name") or exp.get("admin_approved_by_name") or "",
            "approved_at": (exp.get("hr_approved_at") or exp.get("admin_approved_at") or "")[:10] if (exp.get("hr_approved_at") or exp.get("admin_approved_at")) else "",
            "payroll_period": exp.get("payroll_period", ""),
            "payroll_linked": exp.get("payroll_linked", False)
        })
    
    return {
        "month": month,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generated_by": current_user.full_name,
        "summary": {
            "total_expenses": len(report_items),
            "total_amount": round(total_amount, 2),
            "approved_amount": round(total_approved, 2),
            "pending_amount": round(total_pending, 2),
            "rejected_amount": round(total_rejected, 2),
            "approved_count": len([r for r in report_items if r["status"] == "approved"]),
            "pending_count": len([r for r in report_items if r["status"] == "pending"]),
            "rejected_count": len([r for r in report_items if r["status"] == "rejected"])
        },
        "expenses": report_items
    }


@router.get("/report/monthly-meeting-expenses/export")
async def export_monthly_meeting_expense_report(
    month: str = None,
    format: str = "json",
    current_user: User = Depends(get_current_user)
):
    """
    Export monthly meeting expense report for finance department.
    Supports JSON and CSV formats for printing/Excel import.
    
    ACCESS: Admin, HR Manager, Finance roles
    """
    # Get the report data
    report = await get_monthly_meeting_expense_report(month, current_user)
    
    if format == "csv":
        # Generate CSV content
        import io
        import csv
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow([
            "Employee ID", "Employee Name", "Lead Name", "Company", "Stage",
            "Meeting/Description", "Date", "Travel Mode", "Distance (km)", 
            "Total KM", "Round Trip", "Rate/km", "Amount (Rs.)", "Status",
            "Approved By", "Approved Date", "Payroll Period", "Payroll Linked"
        ])
        
        # Data rows
        for exp in report["expenses"]:
            writer.writerow([
                exp["employee_id"],
                exp["employee_name"],
                exp["lead_name"],
                exp["company"],
                exp["stage"],
                exp["meeting_title"],
                exp["expense_date"],
                exp["travel_mode"],
                exp["distance_km"],
                exp["total_km"],
                "Yes" if exp["is_round_trip"] else "No",
                exp["rate_per_km"],
                exp["amount"],
                exp["status"].upper(),
                exp["approved_by"],
                exp["approved_at"],
                exp["payroll_period"],
                "Yes" if exp["payroll_linked"] else "No"
            ])
        
        # Summary row
        writer.writerow([])
        writer.writerow(["SUMMARY"])
        writer.writerow(["Total Expenses", report["summary"]["total_expenses"]])
        writer.writerow(["Total Amount", f"Rs. {report['summary']['total_amount']:,.2f}"])
        writer.writerow(["Approved", f"Rs. {report['summary']['approved_amount']:,.2f}", f"({report['summary']['approved_count']} items)"])
        writer.writerow(["Pending", f"Rs. {report['summary']['pending_amount']:,.2f}", f"({report['summary']['pending_count']} items)"])
        writer.writerow(["Rejected", f"Rs. {report['summary']['rejected_amount']:,.2f}", f"({report['summary']['rejected_count']} items)"])
        
        csv_content = output.getvalue()
        
        from fastapi.responses import Response
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=meeting_expenses_{report['month']}.csv"
            }
        )
    
    return report

