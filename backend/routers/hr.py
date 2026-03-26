"""
HR Router - Bank Change Requests, HR-specific Approvals
"""

from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone
from utils.timezone import today_ist, current_month_ist, now_ist
from typing import Optional, List
import uuid

from .models import User, UserRole
from .deps import get_db, sanitize_text, HR_ROLES, HR_ADMIN_ROLES
from .deps import get_current_user

router = APIRouter(prefix="/hr", tags=["HR"])


@router.get("/pending-attendance-approvals")
async def get_pending_attendance_approvals(current_user: User = Depends(get_current_user)):
    """Get pending attendance approvals for HR."""
    db = get_db()
    
    if current_user.role not in HR_ROLES:
        raise HTTPException(status_code=403, detail="Only HR can view attendance approvals")
    
    pending = await db.attendance.find(
        {"status": "pending_approval"},
        {"_id": 0}
    ).sort("date", -1).to_list(500)
    
    return pending


@router.post("/attendance-approval/{attendance_id}")
async def approve_attendance(attendance_id: str, data: dict, current_user: User = Depends(get_current_user)):
    """Approve or reject attendance."""
    db = get_db()
    
    if current_user.role not in HR_ROLES:
        raise HTTPException(status_code=403, detail="Only HR can approve attendance")
    
    attendance = await db.attendance.find_one({"id": attendance_id}, {"_id": 0})
    if not attendance:
        raise HTTPException(status_code=404, detail="Attendance record not found")
    
    action = data.get("action")  # "approve" or "reject"
    
    if action == "approve":
        new_status = "approved"
    elif action == "reject":
        new_status = "rejected"
    else:
        raise HTTPException(status_code=400, detail="Invalid action")
    
    await db.attendance.update_one(
        {"id": attendance_id},
        {"$set": {
            "status": new_status,
            "approved_by": current_user.id,
            "approved_at": datetime.now(timezone.utc).isoformat(),
            "approval_remarks": data.get("remarks", "")
        }}
    )
    
    return {"message": f"Attendance {action}d"}


@router.get("/bank-change-requests")
async def get_hr_bank_change_requests(current_user: User = Depends(get_current_user)):
    """Get pending bank change requests for HR review."""
    db = get_db()
    
    if current_user.role not in HR_ROLES:
        raise HTTPException(status_code=403, detail="Only HR can view bank change requests")
    
    pending = await db.bank_change_requests.find(
        {"status": "pending_hr"},
        {"_id": 0}
    ).sort("created_at", -1).to_list(500)
    
    return pending


@router.post("/bank-change-request/{request_id}/approve")
async def hr_approve_bank_change(request_id: str, data: dict, current_user: User = Depends(get_current_user)):
    """HR approves bank change request (moves to admin approval)."""
    db = get_db()
    
    if current_user.role not in HR_ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Only HR Manager can approve bank changes")
    
    request = await db.bank_change_requests.find_one({"id": request_id}, {"_id": 0})
    if not request:
        raise HTTPException(status_code=404, detail="Bank change request not found")
    
    if request["status"] != "pending_hr":
        raise HTTPException(status_code=400, detail="Request is not pending HR approval")
    
    await db.bank_change_requests.update_one(
        {"id": request_id},
        {"$set": {
            "status": "pending_admin",
            "hr_approved_by": current_user.id,
            "hr_approved_by_name": current_user.full_name,
            "hr_approved_at": datetime.now(timezone.utc).isoformat(),
            "hr_remarks": data.get("remarks", ""),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    # Notify admins
    admins = await db.users.find({"role": "admin"}, {"_id": 0, "id": 1}).to_list(50)
    for admin in admins:
        notification = {
            "id": str(uuid.uuid4()),
            "user_id": admin["id"],
            "type": "bank_change_admin_approval",
            "title": "Bank Detail Change - Admin Approval Required",
            "message": f"HR has approved bank detail change for {request.get('employee_name')}. Please review.",
            "reference_type": "bank_change_request",
            "reference_id": request_id,
            "is_read": False,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.notifications.insert_one(notification)
    
    return {"message": "Bank change approved by HR, pending admin approval"}


@router.post("/bank-change-request/{request_id}/reject")
async def hr_reject_bank_change(request_id: str, data: dict, current_user: User = Depends(get_current_user)):
    """HR rejects bank change request."""
    db = get_db()
    
    if current_user.role not in HR_ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Only HR Manager can reject bank changes")
    
    request = await db.bank_change_requests.find_one({"id": request_id}, {"_id": 0})
    if not request:
        raise HTTPException(status_code=404, detail="Bank change request not found")
    
    if request["status"] != "pending_hr":
        raise HTTPException(status_code=400, detail="Request is not pending HR approval")
    
    rejection_reason = data.get("reason", "")
    if not rejection_reason:
        raise HTTPException(status_code=400, detail="Rejection reason is required")
    
    await db.bank_change_requests.update_one(
        {"id": request_id},
        {"$set": {
            "status": "rejected",
            "rejected_by": current_user.id,
            "rejected_by_name": current_user.full_name,
            "rejected_at": datetime.now(timezone.utc).isoformat(),
            "rejection_reason": rejection_reason,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    # Notify employee
    notification = {
        "id": str(uuid.uuid4()),
        "user_id": request.get("employee_user_id"),
        "type": "bank_change_rejected",
        "title": "Bank Detail Change Request Rejected",
        "message": f"Your bank detail change request has been rejected. Reason: {rejection_reason}",
        "reference_type": "bank_change_request",
        "reference_id": request_id,
        "is_read": False,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.notifications.insert_one(notification)
    
    return {"message": "Bank change request rejected"}


@router.get("/admin/bank-change-requests")
async def get_admin_bank_change_requests(current_user: User = Depends(get_current_user)):
    """Get pending bank change requests for Admin final approval."""
    db = get_db()
    
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only Admin can view final approval requests")
    
    pending = await db.bank_change_requests.find(
        {"status": "pending_admin"},
        {"_id": 0}
    ).sort("created_at", -1).to_list(500)
    
    return pending


@router.post("/admin/bank-change-request/{request_id}/approve")
async def admin_approve_bank_change(request_id: str, data: dict, current_user: User = Depends(get_current_user)):
    """Admin final approval of bank change request."""
    db = get_db()
    
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only Admin can give final approval")
    
    request = await db.bank_change_requests.find_one({"id": request_id}, {"_id": 0})
    if not request:
        raise HTTPException(status_code=404, detail="Bank change request not found")
    
    if request["status"] != "pending_admin":
        raise HTTPException(status_code=400, detail="Request is not pending admin approval")
    
    # Update employee's bank details
    await db.employees.update_one(
        {"id": request["employee_id"]},
        {"$set": {
            "bank_details": request["new_bank_details"],
            "bank_details_updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    # Update request status
    await db.bank_change_requests.update_one(
        {"id": request_id},
        {"$set": {
            "status": "approved",
            "admin_approved_by": current_user.id,
            "admin_approved_by_name": current_user.full_name,
            "admin_approved_at": datetime.now(timezone.utc).isoformat(),
            "admin_remarks": data.get("remarks", ""),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    # Notify employee
    notification = {
        "id": str(uuid.uuid4()),
        "user_id": request.get("employee_user_id"),
        "type": "bank_change_approved",
        "title": "Bank Detail Change Approved",
        "message": "Your bank detail change request has been approved. Your new bank details are now active.",
        "reference_type": "bank_change_request",
        "reference_id": request_id,
        "is_read": False,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.notifications.insert_one(notification)
    
    return {"message": "Bank details updated successfully"}


@router.post("/admin/bank-change-request/{request_id}/reject")
async def admin_reject_bank_change(request_id: str, data: dict, current_user: User = Depends(get_current_user)):
    """Admin rejects bank change request."""
    db = get_db()
    
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only Admin can reject")
    
    request = await db.bank_change_requests.find_one({"id": request_id}, {"_id": 0})
    if not request:
        raise HTTPException(status_code=404, detail="Bank change request not found")
    
    rejection_reason = data.get("reason", "")
    if not rejection_reason:
        raise HTTPException(status_code=400, detail="Rejection reason is required")
    
    await db.bank_change_requests.update_one(
        {"id": request_id},
        {"$set": {
            "status": "rejected",
            "rejected_by": current_user.id,
            "rejected_by_name": current_user.full_name,
            "rejected_at": datetime.now(timezone.utc).isoformat(),
            "rejection_reason": rejection_reason,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    # Notify employee
    notification = {
        "id": str(uuid.uuid4()),
        "user_id": request.get("employee_user_id"),
        "type": "bank_change_rejected",
        "title": "Bank Detail Change Request Rejected by Admin",
        "message": f"Your bank detail change request has been rejected by admin. Reason: {rejection_reason}",
        "reference_type": "bank_change_request",
        "reference_id": request_id,
        "is_read": False,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.notifications.insert_one(notification)
    
    return {"message": "Bank change request rejected by admin"}


@router.get("/dashboard")
async def get_hr_dashboard(current_user: User = Depends(get_current_user)):
    """Get HR dashboard data."""
    db = get_db()
    
    if current_user.role not in HR_ROLES:
        raise HTTPException(status_code=403, detail="Only HR can access HR dashboard")
    
    # Employee counts
    total_employees = await db.employees.count_documents({})
    active_employees = await db.employees.count_documents({"status": "active"})
    
    # Pending approvals
    pending_bank_changes = await db.bank_change_requests.count_documents({"status": "pending_hr"})
    pending_ctc = await db.ctc_structures.count_documents({"status": "pending"})
    pending_leaves = await db.leave_requests.count_documents({"status": "pending"})
    pending_attendance = await db.attendance.count_documents({"status": "pending_approval"})
    
    # Today's attendance
    today = today_ist()
    today_attendance = await db.attendance.count_documents({"date": today})
    
    return {
        "employees": {
            "total": total_employees,
            "active": active_employees
        },
        "pending_approvals": {
            "bank_changes": pending_bank_changes,
            "ctc": pending_ctc,
            "leaves": pending_leaves,
            "attendance": pending_attendance,
            "total": pending_bank_changes + pending_ctc + pending_leaves + pending_attendance
        },
        "today_attendance": today_attendance
    }


@router.get("/dashboard/payroll-summary")
async def get_payroll_dashboard_summary(
    month: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """
    Get comprehensive payroll dashboard with clickable scorecards.
    
    Returns:
    - Monthly payroll summary with breakdowns
    - YTD (Year-to-Date) statistics
    - Pending actions
    - F&F pipeline
    - Loan/Advance summary
    """
    if current_user.role not in HR_ROLES:
        raise HTTPException(status_code=403, detail="Only HR can view payroll dashboard")
    
    db = get_db()
    
    # Default to current month
    if not month:
        month = current_month_ist()
    
    year = month.split("-")[0]
    
    # 1. Current Month Payroll Summary
    current_registers = await db.payroll_register.find(
        {"month": month, "status": {"$ne": "cancelled"}},
        {"_id": 0}
    ).to_list(10)
    
    current_month_data = {
        "month": month,
        "total_employees": 0,
        "total_gross": 0,
        "total_deductions": 0,
        "total_net": 0,
        "status": "not_processed"
    }
    
    if current_registers:
        latest = current_registers[0]
        current_month_data.update({
            "total_employees": latest.get("total_employees", 0),
            "total_gross": latest.get("total_gross", 0),
            "total_deductions": latest.get("total_deductions", 0),
            "total_net": latest.get("total_net", 0),
            "status": latest.get("status", "draft")
        })
    
    # 2. YTD Statistics
    ytd_registers = await db.payroll_register.find(
        {"month": {"$regex": f"^{year}"}, "status": "locked"},
        {"_id": 0}
    ).to_list(12)
    
    ytd_data = {
        "year": year,
        "months_processed": len(ytd_registers),
        "total_gross": sum(r.get("total_gross", 0) for r in ytd_registers),
        "total_deductions": sum(r.get("total_deductions", 0) for r in ytd_registers),
        "total_net": sum(r.get("total_net", 0) for r in ytd_registers),
        "avg_monthly_payroll": 0
    }
    
    if ytd_registers:
        ytd_data["avg_monthly_payroll"] = ytd_data["total_net"] / len(ytd_registers)
    
    # 3. Component-wise Breakdown (Current Month)
    calculations = await db.payroll_calculations.find(
        {"month": month},
        {"_id": 0, "total_deductions": 1, "tds_details": 1, "deductions": 1}
    ).to_list(500)
    
    component_summary = {
        "pf_total": 0,
        "pt_total": 0,
        "tds_total": 0,
        "esi_total": 0,
        "lop_total": 0,
        "loans_recovery": 0
    }
    
    for calc in calculations:
        tds = calc.get("tds_details", {})
        component_summary["tds_total"] += tds.get("monthly_tds", 0)
        
        for ded in calc.get("deductions", []):
            key = ded.get("key", "").lower()
            amt = abs(ded.get("amount", 0))
            if key == "pf":
                component_summary["pf_total"] += amt
            elif key == "pt":
                component_summary["pt_total"] += amt
            elif key == "esi":
                component_summary["esi_total"] += amt
            elif key == "lop":
                component_summary["lop_total"] += amt
            elif key in ["loan_emi", "advance_recovery"]:
                component_summary["loans_recovery"] += amt
    
    # 4. Department-wise Summary
    dept_summary = {}
    dept_calcs = await db.payroll_calculations.find(
        {"month": month},
        {"_id": 0, "department": 1, "gross_monthly": 1, "net_payable": 1}
    ).to_list(500)
    
    for calc in dept_calcs:
        dept = calc.get("department", "Unknown")
        if dept not in dept_summary:
            dept_summary[dept] = {"employees": 0, "gross": 0, "net": 0}
        dept_summary[dept]["employees"] += 1
        dept_summary[dept]["gross"] += calc.get("gross_monthly", 0) or 0
        dept_summary[dept]["net"] += calc.get("net_payable", 0) or 0
    
    # 5. Pending Actions
    pending_payroll_approval = await db.payroll_register.count_documents({
        "status": {"$in": ["draft", "pending_admin_approval"]}
    })
    
    pending_exits = await db.exit_settlements.count_documents({
        "status": {"$nin": ["completed", "cancelled"]}
    })
    
    pending_loans = await db.employee_loans.count_documents({"status": "active"})
    
    # 6. F&F Pipeline
    ff_pipeline = await db.exit_settlements.find(
        {"status": {"$nin": ["completed", "cancelled"]}},
        {"_id": 0, "id": 1, "employee_name": 1, "employee_code": 1, "status": 1, "last_working_date": 1}
    ).to_list(20)
    
    # 7. Active Loans Summary
    active_loans = await db.employee_loans.find(
        {"status": "active"},
        {"_id": 0}
    ).to_list(50)
    
    loans_summary = {
        "active_count": len(active_loans),
        "total_outstanding": sum(l.get("remaining_amount", 0) for l in active_loans),
        "monthly_recovery": sum(l.get("monthly_emi", 0) for l in active_loans)
    }
    
    # 8. Employee Count
    total_employees = await db.employees.count_documents({"status": {"$ne": "inactive"}})
    
    return {
        "scorecards": [
            {
                "id": "current_payroll",
                "title": f"Payroll - {month}",
                "value": round(current_month_data["total_net"], 2),
                "subtitle": f"{current_month_data['total_employees']} employees",
                "status": current_month_data["status"],
                "icon": "wallet",
                "color": "green" if current_month_data["status"] == "locked" else "amber",
                "link": f"/payroll-engine?month={month}&tab=register"
            },
            {
                "id": "ytd_payroll",
                "title": f"YTD Payroll ({year})",
                "value": round(ytd_data["total_net"], 2),
                "subtitle": f"{ytd_data['months_processed']} months processed",
                "icon": "trending-up",
                "color": "blue",
                "link": "/payroll-engine?tab=register"
            },
            {
                "id": "tds_liability",
                "title": "TDS Liability",
                "value": round(component_summary["tds_total"], 2),
                "subtitle": f"For {month}",
                "icon": "receipt",
                "color": "purple",
                "link": f"/payroll-engine?month={month}&tab=register&breakdown=tds"
            },
            {
                "id": "pf_contribution",
                "title": "PF Contribution",
                "value": round(component_summary["pf_total"] * 2, 2),  # Employee + Employer
                "subtitle": "Employee + Employer",
                "icon": "piggy-bank",
                "color": "indigo",
                "link": f"/payroll-engine?month={month}&tab=register&breakdown=pf"
            },
            {
                "id": "pending_exits",
                "title": "F&F Pipeline",
                "value": pending_exits,
                "subtitle": "Exits in progress",
                "icon": "user-minus",
                "color": "red" if pending_exits > 0 else "gray",
                "link": "/exit-settlement"
            },
            {
                "id": "active_loans",
                "title": "Loan Recovery",
                "value": round(loans_summary["monthly_recovery"], 2),
                "subtitle": f"{loans_summary['active_count']} active loans",
                "icon": "credit-card",
                "color": "orange",
                "link": "/loans"
            }
        ],
        "current_month": current_month_data,
        "ytd": ytd_data,
        "components": {k: round(v, 2) for k, v in component_summary.items()},
        "department_breakdown": [
            {"department": k, **{kk: round(vv, 2) for kk, vv in v.items()}}
            for k, v in dept_summary.items()
        ],
        "ff_pipeline": ff_pipeline,
        "loans_summary": loans_summary,
        "pending_actions": {
            "payroll_approvals": pending_payroll_approval,
            "exits": pending_exits,
            "loans": pending_loans
        },
        "total_employees": total_employees
    }

