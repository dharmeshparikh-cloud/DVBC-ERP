"""
HR Router - Bank Change Requests, HR-specific Approvals
"""

from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone
from typing import Optional, List
import uuid

from .models import User, UserRole
from .deps import get_db, sanitize_text, HR_ROLES, HR_ADMIN_ROLES
from .auth import get_current_user

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
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
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
