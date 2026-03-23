"""
Exit Organisation Router - Employee Resignation & Full & Final Settlement

Flow:
1. Employee initiates "Exit Organisation" request
2. Mandatory exit interview questions
3. Admin approval
4. HR approval
5. 30-day notice period tracking
6. F&F calculation
7. Exit checklist completion
8. Final payout
"""

from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone, timedelta
from typing import Optional, List
import uuid

from .deps import get_db, get_current_user
from .models import User
from .audit_logging import log_audit

router = APIRouter(prefix="/exit", tags=["Exit Organisation"])

# Exit Interview Questions (Mandatory)
EXIT_INTERVIEW_QUESTIONS = [
    {"id": "reason", "question": "Primary reason for leaving?", "type": "select", "options": ["Better opportunity", "Personal reasons", "Relocation", "Health issues", "Higher studies", "Dissatisfaction", "Other"]},
    {"id": "experience", "question": "How would you rate your overall experience?", "type": "rating", "max": 5},
    {"id": "recommend", "question": "Would you recommend this company to others?", "type": "select", "options": ["Yes", "Maybe", "No"]},
    {"id": "management", "question": "How satisfied were you with management support?", "type": "rating", "max": 5},
    {"id": "growth", "question": "Were you provided adequate growth opportunities?", "type": "select", "options": ["Yes", "Partially", "No"]},
    {"id": "feedback", "question": "Any suggestions for improvement?", "type": "text"},
    {"id": "rejoin", "question": "Would you consider rejoining in the future?", "type": "select", "options": ["Yes", "Maybe", "No"]},
]

# Exit Checklist Items
EXIT_CHECKLIST = [
    {"id": "laptop_return", "item": "Laptop/Desktop Return", "category": "assets"},
    {"id": "id_card_return", "item": "ID Card Return", "category": "assets"},
    {"id": "access_card_return", "item": "Access Card Return", "category": "assets"},
    {"id": "company_assets", "item": "Other Company Assets", "category": "assets"},
    {"id": "email_backup", "item": "Email/Data Backup", "category": "it"},
    {"id": "access_revoked", "item": "System Access Revoked", "category": "it"},
    {"id": "knowledge_transfer", "item": "Knowledge Transfer Complete", "category": "handover"},
    {"id": "pending_work", "item": "Pending Work Handed Over", "category": "handover"},
    {"id": "no_dues_finance", "item": "No Dues - Finance", "category": "clearance"},
    {"id": "no_dues_admin", "item": "No Dues - Admin", "category": "clearance"},
    {"id": "no_dues_it", "item": "No Dues - IT", "category": "clearance"},
    {"id": "exit_interview_done", "item": "Exit Interview Completed", "category": "hr"},
    {"id": "relieving_letter", "item": "Relieving Letter Generated", "category": "hr"},
    {"id": "experience_letter", "item": "Experience Letter Generated", "category": "hr"},
]


@router.get("/interview-questions")
async def get_exit_interview_questions():
    """Get mandatory exit interview questions."""
    return {"questions": EXIT_INTERVIEW_QUESTIONS}


@router.get("/checklist-template")
async def get_exit_checklist_template():
    """Get exit checklist template."""
    return {"checklist": EXIT_CHECKLIST}


@router.post("/initiate")
async def initiate_exit_request(
    data: dict,
    current_user: User = Depends(get_current_user)
):
    """
    Employee initiates exit request with exit interview responses.
    This is the 'Exit Organisation' button action.
    """
    db = get_db()
    
    # Get employee record
    employee = await db.employees.find_one(
        {"$or": [{"user_id": current_user.id}, {"email": current_user.email}]},
        {"_id": 0}
    )
    
    if not employee:
        raise HTTPException(status_code=404, detail="Employee record not found")
    
    # Check if already has pending exit request
    existing = await db.exit_requests.find_one({
        "employee_id": employee["id"],
        "status": {"$in": ["pending", "admin_approved", "hr_approved", "in_progress"]}
    })
    
    if existing:
        raise HTTPException(status_code=400, detail="You already have a pending exit request")
    
    # Validate exit interview responses
    interview_responses = data.get("interview_responses", {})
    required_questions = [q["id"] for q in EXIT_INTERVIEW_QUESTIONS if q["type"] != "text"]
    
    for q_id in required_questions:
        if q_id not in interview_responses or not interview_responses[q_id]:
            question = next((q for q in EXIT_INTERVIEW_QUESTIONS if q["id"] == q_id), None)
            raise HTTPException(
                status_code=400, 
                detail=f"Please answer: {question['question'] if question else q_id}"
            )
    
    # Calculate last working day (30 days notice)
    notice_period_days = 30
    requested_date = data.get("requested_last_date")
    if requested_date:
        requested_lwd = datetime.fromisoformat(requested_date.replace('Z', '+00:00'))
        min_lwd = datetime.now(timezone.utc) + timedelta(days=notice_period_days)
        if requested_lwd < min_lwd:
            last_working_day = min_lwd
        else:
            last_working_day = requested_lwd
    else:
        last_working_day = datetime.now(timezone.utc) + timedelta(days=notice_period_days)
    
    exit_request = {
        "id": str(uuid.uuid4()),
        "employee_id": employee["id"],
        "employee_name": f"{employee.get('first_name', '')} {employee.get('last_name', '')}".strip(),
        "employee_code": employee.get("employee_id") or employee.get("employee_code"),
        "department": employee.get("department"),
        "designation": employee.get("designation"),
        "email": employee.get("email"),
        "status": "pending",  # pending -> admin_approved -> hr_approved -> in_progress -> completed
        "notice_period_days": notice_period_days,
        "resignation_date": datetime.now(timezone.utc).isoformat(),
        "last_working_day": last_working_day.isoformat(),
        "reason": interview_responses.get("reason"),
        "interview_responses": interview_responses,
        "checklist": {item["id"]: False for item in EXIT_CHECKLIST},
        "fnf_calculation": None,
        "approvals": {
            "admin": {"status": "pending", "approved_by": None, "approved_at": None, "remarks": None},
            "hr": {"status": "pending", "approved_by": None, "approved_at": None, "remarks": None}
        },
        "download_restricted": True,  # Restrict downloads during exit
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.exit_requests.insert_one(exit_request)
    
    # Update employee status
    await db.employees.update_one(
        {"id": employee["id"]},
        {"$set": {
            "exit_status": "resignation_pending",
            "exit_request_id": exit_request["id"],
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    # Log audit
    await log_audit(
        action="exit_request_initiated",
        entity_type="exit_request",
        entity_id=exit_request["id"],
        performed_by=current_user.id,
        changes={"employee_name": exit_request["employee_name"], "reason": exit_request["reason"]}
    )
    
    return {
        "message": "Exit request submitted successfully. Pending Admin approval.",
        "request_id": exit_request["id"],
        "last_working_day": last_working_day.isoformat(),
        "notice_period_days": notice_period_days
    }


@router.get("/my-request")
async def get_my_exit_request(current_user: User = Depends(get_current_user)):
    """Get current user's exit request if any."""
    db = get_db()
    
    employee = await db.employees.find_one(
        {"$or": [{"user_id": current_user.id}, {"email": current_user.email}]},
        {"_id": 0, "id": 1}
    )
    
    if not employee:
        return {"request": None}
    
    request = await db.exit_requests.find_one(
        {"employee_id": employee["id"]},
        {"_id": 0}
    )
    
    return {"request": request}


@router.get("/pending")
async def get_pending_exit_requests(current_user: User = Depends(get_current_user)):
    """Get all pending exit requests (Admin/HR only)."""
    db = get_db()
    
    if current_user.role not in ["admin", "hr_manager", "hr_executive"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    requests = await db.exit_requests.find(
        {"status": {"$in": ["pending", "admin_approved", "hr_approved", "in_progress"]}},
        {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    
    return {"requests": requests}


@router.get("/all")
async def get_all_exit_requests(
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get all exit requests with optional status filter."""
    db = get_db()
    
    if current_user.role not in ["admin", "hr_manager", "hr_executive"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    query = {}
    if status:
        query["status"] = status
    
    requests = await db.exit_requests.find(query, {"_id": 0}).sort("created_at", -1).to_list(500)
    
    return {"requests": requests}


@router.get("/{request_id}")
async def get_exit_request(request_id: str, current_user: User = Depends(get_current_user)):
    """Get specific exit request details."""
    db = get_db()
    
    request = await db.exit_requests.find_one({"id": request_id}, {"_id": 0})
    if not request:
        raise HTTPException(status_code=404, detail="Exit request not found")
    
    # Check access
    employee = await db.employees.find_one(
        {"$or": [{"user_id": current_user.id}, {"email": current_user.email}]},
        {"_id": 0, "id": 1}
    )
    
    is_own = employee and employee["id"] == request["employee_id"]
    is_hr_admin = current_user.role in ["admin", "hr_manager", "hr_executive"]
    
    if not is_own and not is_hr_admin:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return request


@router.post("/{request_id}/admin-approve")
async def admin_approve_exit(
    request_id: str,
    data: dict,
    current_user: User = Depends(get_current_user)
):
    """Admin approves exit request."""
    db = get_db()
    
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only Admin can approve at this stage")
    
    request = await db.exit_requests.find_one({"id": request_id}, {"_id": 0})
    if not request:
        raise HTTPException(status_code=404, detail="Exit request not found")
    
    if request["status"] != "pending":
        raise HTTPException(status_code=400, detail=f"Cannot approve request in '{request['status']}' status")
    
    await db.exit_requests.update_one(
        {"id": request_id},
        {"$set": {
            "status": "admin_approved",
            "approvals.admin": {
                "status": "approved",
                "approved_by": current_user.full_name,
                "approved_at": datetime.now(timezone.utc).isoformat(),
                "remarks": data.get("remarks", "")
            },
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    await log_audit(
        action="exit_request_admin_approved",
        entity_type="exit_request",
        entity_id=request_id,
        performed_by=current_user.id,
        changes={"employee_name": request["employee_name"]}
    )
    
    return {"message": "Exit request approved by Admin. Pending HR approval."}


@router.post("/{request_id}/hr-approve")
async def hr_approve_exit(
    request_id: str,
    data: dict,
    current_user: User = Depends(get_current_user)
):
    """HR approves exit request and starts F&F process."""
    db = get_db()
    
    if current_user.role not in ["admin", "hr_manager", "hr_executive"]:
        raise HTTPException(status_code=403, detail="Only HR can approve at this stage")
    
    request = await db.exit_requests.find_one({"id": request_id}, {"_id": 0})
    if not request:
        raise HTTPException(status_code=404, detail="Exit request not found")
    
    if request["status"] != "admin_approved":
        raise HTTPException(status_code=400, detail="Requires Admin approval first")
    
    # Calculate F&F
    fnf = await calculate_fnf(db, request["employee_id"], request["last_working_day"])
    
    await db.exit_requests.update_one(
        {"id": request_id},
        {"$set": {
            "status": "hr_approved",
            "approvals.hr": {
                "status": "approved",
                "approved_by": current_user.full_name,
                "approved_at": datetime.now(timezone.utc).isoformat(),
                "remarks": data.get("remarks", "")
            },
            "fnf_calculation": fnf,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    # Update employee status
    await db.employees.update_one(
        {"id": request["employee_id"]},
        {"$set": {"exit_status": "notice_period", "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    await log_audit(
        action="exit_request_hr_approved",
        entity_type="exit_request",
        entity_id=request_id,
        performed_by=current_user.id,
        changes={"employee_name": request["employee_name"], "fnf_total": fnf.get("net_payable")}
    )
    
    return {"message": "Exit request approved. Notice period started.", "fnf": fnf}


@router.post("/{request_id}/update-checklist")
async def update_exit_checklist(
    request_id: str,
    data: dict,
    current_user: User = Depends(get_current_user)
):
    """Update exit checklist items."""
    db = get_db()
    
    if current_user.role not in ["admin", "hr_manager", "hr_executive"]:
        raise HTTPException(status_code=403, detail="Only HR/Admin can update checklist")
    
    request = await db.exit_requests.find_one({"id": request_id}, {"_id": 0})
    if not request:
        raise HTTPException(status_code=404, detail="Exit request not found")
    
    checklist_updates = data.get("checklist", {})
    current_checklist = request.get("checklist", {})
    current_checklist.update(checklist_updates)
    
    await db.exit_requests.update_one(
        {"id": request_id},
        {"$set": {
            "checklist": current_checklist,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    return {"message": "Checklist updated", "checklist": current_checklist}


@router.post("/{request_id}/process-fnf")
async def process_fnf(
    request_id: str,
    data: dict,
    current_user: User = Depends(get_current_user)
):
    """Process F&F settlement after all checklist items completed."""
    db = get_db()
    
    if current_user.role not in ["admin", "hr_manager"]:
        raise HTTPException(status_code=403, detail="Only Admin/HR Manager can process F&F")
    
    request = await db.exit_requests.find_one({"id": request_id}, {"_id": 0})
    if not request:
        raise HTTPException(status_code=404, detail="Exit request not found")
    
    if request["status"] not in ["hr_approved", "in_progress"]:
        raise HTTPException(status_code=400, detail="Exit must be HR approved first")
    
    # Check checklist completion
    checklist = request.get("checklist", {})
    incomplete = [item for item, done in checklist.items() if not done]
    
    if incomplete and not data.get("force_complete"):
        raise HTTPException(
            status_code=400, 
            detail=f"Incomplete checklist items: {', '.join(incomplete)}. Use force_complete=true to override."
        )
    
    # Recalculate F&F with any adjustments
    fnf = request.get("fnf_calculation", {})
    adjustments = data.get("adjustments", {})
    
    if adjustments:
        fnf["adjustments"] = adjustments
        fnf["adjusted_amount"] = sum(adjustments.values())
        fnf["net_payable"] = fnf.get("gross_payable", 0) - fnf.get("total_deductions", 0) + fnf.get("adjusted_amount", 0)
    
    await db.exit_requests.update_one(
        {"id": request_id},
        {"$set": {
            "status": "completed",
            "fnf_calculation": fnf,
            "fnf_processed_by": current_user.full_name,
            "fnf_processed_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    # Update employee status to exited
    await db.employees.update_one(
        {"id": request["employee_id"]},
        {"$set": {
            "go_live_status": "exited",
            "exit_status": "completed",
            "exit_date": datetime.now(timezone.utc).isoformat(),
            "is_active": False,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    # Deactivate user account
    await db.users.update_one(
        {"email": request["email"]},
        {"$set": {"is_active": False, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    await log_audit(
        action="exit_fnf_processed",
        entity_type="exit_request",
        entity_id=request_id,
        performed_by=current_user.id,
        changes={"employee_name": request["employee_name"], "net_payable": fnf.get("net_payable")}
    )
    
    return {
        "message": "F&F processed successfully. Employee exit completed.",
        "fnf": fnf
    }


@router.post("/{request_id}/reject")
async def reject_exit_request(
    request_id: str,
    data: dict,
    current_user: User = Depends(get_current_user)
):
    """Reject/Cancel exit request."""
    db = get_db()
    
    if current_user.role not in ["admin", "hr_manager"]:
        raise HTTPException(status_code=403, detail="Only Admin/HR Manager can reject")
    
    request = await db.exit_requests.find_one({"id": request_id}, {"_id": 0})
    if not request:
        raise HTTPException(status_code=404, detail="Exit request not found")
    
    await db.exit_requests.update_one(
        {"id": request_id},
        {"$set": {
            "status": "rejected",
            "rejected_by": current_user.full_name,
            "rejection_reason": data.get("reason", ""),
            "rejected_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    # Reset employee exit status
    await db.employees.update_one(
        {"id": request["employee_id"]},
        {"$set": {
            "exit_status": None,
            "exit_request_id": None,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    return {"message": "Exit request rejected/cancelled."}


async def calculate_fnf(db, employee_id: str, last_working_day: str) -> dict:
    """Calculate Full & Final settlement amount."""
    
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        return {"error": "Employee not found"}
    
    # Get CTC/Salary info
    ctc = await db.ctc_structures.find_one(
        {"employee_id": employee_id, "status": "approved"},
        {"_id": 0}
    )
    
    monthly_gross = 0
    basic_salary = 0
    if ctc:
        monthly_gross = ctc.get("summary", {}).get("monthly_gross", 0)
        basic_salary = ctc.get("summary", {}).get("basic", 0) or monthly_gross * 0.5
    elif employee.get("salary"):
        monthly_gross = employee["salary"] / 12
        basic_salary = monthly_gross * 0.5
    
    lwd = datetime.fromisoformat(last_working_day.replace('Z', '+00:00'))
    today = datetime.now(timezone.utc)
    
    # Calculate days worked in final month
    days_in_month = 30
    if lwd.month == today.month:
        days_worked = lwd.day
    else:
        days_worked = days_in_month
    
    # Pro-rata salary for final month
    pending_salary = (monthly_gross / days_in_month) * days_worked
    
    # Leave encashment
    leave_balance = await db.leave_balances.find_one(
        {"employee_id": employee_id},
        {"_id": 0}
    )
    encashable_leaves = 0
    if leave_balance:
        # Typically earned/privilege leaves are encashable
        encashable_leaves = leave_balance.get("earned_leave", 0) + leave_balance.get("privilege_leave", 0)
    
    daily_basic = basic_salary / days_in_month
    leave_encashment = encashable_leaves * daily_basic
    
    # Pending expense reimbursements
    pending_expenses = await db.payroll_reimbursements.find(
        {"employee_id": employee_id, "status": "pending"},
        {"_id": 0}
    ).to_list(100)
    expense_reimbursement = sum(e.get("amount", 0) for e in pending_expenses)
    
    # Gratuity (if > 5 years service)
    joining_date = employee.get("date_of_joining") or employee.get("joining_date")
    gratuity = 0
    years_of_service = 0
    if joining_date:
        try:
            jd = datetime.fromisoformat(joining_date.replace('Z', '+00:00'))
            years_of_service = (lwd - jd).days / 365
            if years_of_service >= 5:
                # Gratuity = (Basic * 15 * Years) / 26
                gratuity = (basic_salary * 15 * int(years_of_service)) / 26
        except:
            pass
    
    # Bonus/Incentives pending
    pending_incentives = await db.incentive_payouts.find(
        {"employee_id": employee_id, "status": "pending"},
        {"_id": 0}
    ).to_list(50)
    bonus_incentives = sum(i.get("amount", 0) for i in pending_incentives)
    
    # Deductions
    # Advance recovery
    advance_recovery = employee.get("pending_advance", 0)
    
    # Notice period shortfall (if applicable)
    notice_shortfall = 0
    # This would be calculated based on actual resignation vs notice period
    
    # Asset recovery (placeholder - would be calculated based on checklist)
    asset_recovery = 0
    
    gross_payable = pending_salary + leave_encashment + expense_reimbursement + gratuity + bonus_incentives
    total_deductions = advance_recovery + notice_shortfall + asset_recovery
    net_payable = gross_payable - total_deductions
    
    return {
        "employee_name": f"{employee.get('first_name', '')} {employee.get('last_name', '')}".strip(),
        "employee_code": employee.get("employee_id") or employee.get("employee_code"),
        "last_working_day": last_working_day,
        "years_of_service": round(years_of_service, 1),
        "earnings": {
            "pending_salary": round(pending_salary, 2),
            "leave_encashment": round(leave_encashment, 2),
            "expense_reimbursement": round(expense_reimbursement, 2),
            "gratuity": round(gratuity, 2),
            "bonus_incentives": round(bonus_incentives, 2)
        },
        "deductions": {
            "advance_recovery": round(advance_recovery, 2),
            "notice_shortfall": round(notice_shortfall, 2),
            "asset_recovery": round(asset_recovery, 2)
        },
        "gross_payable": round(gross_payable, 2),
        "total_deductions": round(total_deductions, 2),
        "net_payable": round(net_payable, 2),
        "calculated_at": datetime.now(timezone.utc).isoformat()
    }


@router.get("/check-download-restriction/{user_id}")
async def check_download_restriction(user_id: str):
    """Check if user has download restrictions (during exit process)."""
    db = get_db()
    
    employee = await db.employees.find_one(
        {"$or": [{"user_id": user_id}, {"id": user_id}]},
        {"_id": 0, "id": 1, "exit_status": 1}
    )
    
    if not employee:
        return {"restricted": False}
    
    # Check if in exit process
    exit_request = await db.exit_requests.find_one(
        {"employee_id": employee["id"], "status": {"$in": ["pending", "admin_approved", "hr_approved", "in_progress"]}},
        {"_id": 0, "download_restricted": 1}
    )
    
    if exit_request and exit_request.get("download_restricted"):
        return {"restricted": True, "message": "Downloads restricted during exit process"}
    
    return {"restricted": False}
