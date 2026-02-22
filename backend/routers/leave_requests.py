"""
Leave Requests Router - Leave application, approval workflow.
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Optional, List
from datetime import datetime, timezone, date
import uuid
from pydantic import BaseModel
from .deps import get_db, MANAGER_ROLES, HR_ROLES
from .models import User
from .auth import get_current_user

router = APIRouter(prefix="/leave-requests", tags=["Leave Requests"])


class LeaveRequestCreate(BaseModel):
    leave_type: str
    start_date: date
    end_date: date
    reason: Optional[str] = ""
    is_half_day: bool = False
    half_day_type: Optional[str] = None  # first_half, second_half


@router.get("")
async def get_leave_requests(
    status: Optional[str] = None,
    employee_id: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get leave requests with filters"""
    db = get_db()
    
    query = {}
    if status:
        query["status"] = status
    if employee_id:
        query["employee_id"] = employee_id
    
    # Non-managers see only their own
    if current_user.role not in MANAGER_ROLES and current_user.role not in HR_ROLES:
        emp = await db.employees.find_one({"user_id": current_user.id}, {"_id": 0})
        if emp:
            query["employee_id"] = emp["id"]
    
    requests = await db.leave_requests.find(query, {"_id": 0}).sort("created_at", -1).to_list(500)
    return requests


@router.get("/all")
async def get_all_leave_requests(
    current_user: User = Depends(get_current_user)
):
    """Get all leave requests (HR/Admin only)"""
    db = get_db()
    
    if current_user.role not in HR_ROLES:
        raise HTTPException(status_code=403, detail="Only HR can view all leave requests")
    
    requests = await db.leave_requests.find({}, {"_id": 0}).sort("created_at", -1).to_list(1000)
    return requests


@router.post("")
async def create_leave_request(
    leave_data: LeaveRequestCreate,
    current_user: User = Depends(get_current_user)
):
    """Create a leave request"""
    db = get_db()
    
    employee = await db.employees.find_one({"user_id": current_user.id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=400, detail="Employee record not found. Please contact HR.")
    
    # Calculate days
    if leave_data.is_half_day:
        days = 0.5
    else:
        days = (leave_data.end_date - leave_data.start_date).days + 1
    
    # Default leave balance
    DEFAULT_LEAVE_BALANCE = {
        'casual_leave': 12,
        'sick_leave': 6,
        'earned_leave': 15
    }
    
    leave_balance = employee.get('leave_balance', {})
    total_entitled = leave_balance.get(leave_data.leave_type, DEFAULT_LEAVE_BALANCE.get(leave_data.leave_type, 0))
    used = leave_balance.get(f'used_{leave_data.leave_type.replace("_leave", "")}', 0)
    available = total_entitled - used
    
    if days > available and leave_data.leave_type not in ['loss_of_pay', 'lop']:
        raise HTTPException(status_code=400, detail=f"Insufficient leave balance. Available: {available} days, Requested: {days} days")
    
    # Get reporting manager
    reporting_manager_id = employee.get('reporting_manager_id')
    rm_name = None
    rm_user_id = None
    if reporting_manager_id:
        rm_emp = await db.employees.find_one({"employee_id": reporting_manager_id}, {"_id": 0})
        if rm_emp:
            rm_user_id = rm_emp.get("user_id")
            rm_name = f"{rm_emp.get('first_name', '')} {rm_emp.get('last_name', '')}".strip()
    
    now = datetime.now(timezone.utc).isoformat()
    leave_request = {
        "id": str(uuid.uuid4()),
        "employee_id": employee['id'],
        "employee_code": employee.get('employee_id'),
        "employee_name": f"{employee['first_name']} {employee['last_name']}",
        "user_id": current_user.id,
        "leave_type": leave_data.leave_type,
        "start_date": leave_data.start_date.isoformat(),
        "end_date": leave_data.end_date.isoformat() if not leave_data.is_half_day else leave_data.start_date.isoformat(),
        "days": days,
        "is_half_day": leave_data.is_half_day,
        "half_day_type": leave_data.half_day_type if leave_data.is_half_day else None,
        "reason": leave_data.reason,
        "status": "pending",
        "reporting_manager_id": reporting_manager_id,
        "reporting_manager_name": rm_name,
        "rm_user_id": rm_user_id,
        "created_at": now,
        "updated_at": now
    }
    
    await db.leave_requests.insert_one(leave_request)
    leave_request.pop("_id", None)
    
    return {
        "message": "Leave request submitted",
        "leave_request_id": leave_request['id'],
        "approver": rm_name or "HR Manager"
    }


@router.post("/{leave_id}/rm-approve")
async def rm_approve_leave(leave_id: str, data: dict = None, current_user: User = Depends(get_current_user)):
    """Reporting Manager approve/reject leave"""
    db = get_db()
    
    leave = await db.leave_requests.find_one({"id": leave_id}, {"_id": 0})
    if not leave:
        raise HTTPException(status_code=404, detail="Leave request not found")
    
    if leave.get("status") != "pending":
        raise HTTPException(status_code=400, detail="Leave request is not pending")
    
    action = data.get("action", "approve") if data else "approve"
    comments = data.get("comments", "") if data else ""
    
    new_status = "approved" if action == "approve" else "rejected"
    
    update_data = {
        "status": new_status,
        "rm_action": action,
        "rm_action_by": current_user.id,
        "rm_action_at": datetime.now(timezone.utc).isoformat(),
        "rm_comments": comments,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    # Update leave balance if approved
    if new_status == "approved":
        employee = await db.employees.find_one({"id": leave["employee_id"]}, {"_id": 0})
        if employee:
            leave_type_key = leave["leave_type"].replace("_leave", "")
            await db.employees.update_one(
                {"id": leave["employee_id"]},
                {"$inc": {f"leave_balance.used_{leave_type_key}": leave["days"]}}
            )
    
    await db.leave_requests.update_one({"id": leave_id}, {"$set": update_data})
    
    return {"message": f"Leave request {new_status}", "status": new_status}


@router.post("/{leave_id}/withdraw")
async def withdraw_leave(leave_id: str, current_user: User = Depends(get_current_user)):
    """Withdraw a pending leave request"""
    db = get_db()
    
    leave = await db.leave_requests.find_one({"id": leave_id}, {"_id": 0})
    if not leave:
        raise HTTPException(status_code=404, detail="Leave request not found")
    
    # Check ownership
    if leave.get("user_id") != current_user.id and current_user.role not in HR_ROLES:
        raise HTTPException(status_code=403, detail="Not authorized to withdraw this leave")
    
    if leave.get("status") != "pending":
        raise HTTPException(status_code=400, detail="Only pending leave requests can be withdrawn")
    
    await db.leave_requests.update_one(
        {"id": leave_id},
        {
            "$set": {
                "status": "withdrawn",
                "withdrawn_by": current_user.id,
                "withdrawn_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    return {"message": "Leave request withdrawn"}


@router.get("/{leave_id}")
async def get_leave_request(leave_id: str, current_user: User = Depends(get_current_user)):
    """Get a specific leave request"""
    db = get_db()
    
    leave = await db.leave_requests.find_one({"id": leave_id}, {"_id": 0})
    if not leave:
        raise HTTPException(status_code=404, detail="Leave request not found")
    
    return leave


@router.post("/{leave_id}/attachments")
async def upload_leave_attachment(
    leave_id: str,
    data: dict,
    current_user: User = Depends(get_current_user)
):
    """Upload attachment to a leave request (e.g., medical certificate, documents)."""
    db = get_db()
    
    leave_req = await db.leave_requests.find_one({"id": leave_id}, {"_id": 0})
    if not leave_req:
        raise HTTPException(status_code=404, detail="Leave request not found")
    
    # Only owner or HR can upload
    if leave_req.get("user_id") != current_user.id and current_user.role not in HR_ROLES:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    attachment = {
        "id": str(uuid.uuid4()),
        "file_name": data.get("file_name"),
        "file_type": data.get("file_type"),
        "file_data": data.get("file_data"),  # Base64 encoded
        "description": data.get("description", ""),
        "uploaded_by": current_user.id,
        "uploaded_by_name": current_user.full_name,
        "uploaded_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.leave_requests.update_one(
        {"id": leave_id},
        {"$push": {"attachments": attachment}}
    )
    
    return {"message": "Attachment uploaded", "attachment_id": attachment["id"]}


@router.get("/{leave_id}/attachments")
async def get_leave_attachments(
    leave_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get attachments for a leave request."""
    db = get_db()
    
    leave_req = await db.leave_requests.find_one({"id": leave_id}, {"_id": 0})
    if not leave_req:
        raise HTTPException(status_code=404, detail="Leave request not found")
    
    attachments = leave_req.get("attachments", [])
    
    # Return list without file data
    attachment_list = []
    for a in attachments:
        attachment_list.append({
            "id": a.get("id"),
            "file_name": a.get("file_name"),
            "file_type": a.get("file_type"),
            "description": a.get("description"),
            "uploaded_by_name": a.get("uploaded_by_name"),
            "uploaded_at": a.get("uploaded_at"),
            "has_data": bool(a.get("file_data"))
        })
    
    return {"attachments": attachment_list, "count": len(attachment_list)}


@router.get("/{leave_id}/attachments/{attachment_id}")
async def get_leave_attachment(
    leave_id: str,
    attachment_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get a specific attachment with file data for download."""
    db = get_db()
    
    leave_req = await db.leave_requests.find_one({"id": leave_id}, {"_id": 0})
    if not leave_req:
        raise HTTPException(status_code=404, detail="Leave request not found")
    
    attachments = leave_req.get("attachments", [])
    attachment = next((a for a in attachments if a.get("id") == attachment_id), None)
    
    if not attachment:
        raise HTTPException(status_code=404, detail="Attachment not found")
    
    return attachment


@router.delete("/{leave_id}/attachments/{attachment_id}")
async def delete_leave_attachment(
    leave_id: str,
    attachment_id: str,
    current_user: User = Depends(get_current_user)
):
    """Delete an attachment from a leave request."""
    db = get_db()
    
    leave_req = await db.leave_requests.find_one({"id": leave_id}, {"_id": 0})
    if not leave_req:
        raise HTTPException(status_code=404, detail="Leave request not found")
    
    # Only owner or HR can delete
    if leave_req.get("user_id") != current_user.id and current_user.role not in HR_ROLES:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    await db.leave_requests.update_one(
        {"id": leave_id},
        {"$pull": {"attachments": {"id": attachment_id}}}
    )
    
    return {"message": "Attachment deleted"}


@router.get("/employee/{employee_id}/balance")
async def get_leave_balance(employee_id: str, current_user: User = Depends(get_current_user)):
    """Get leave balance for an employee"""
    db = get_db()
    
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    DEFAULT_LEAVE_BALANCE = {
        'casual_leave': 12,
        'sick_leave': 6,
        'earned_leave': 15
    }
    
    balance = employee.get('leave_balance', {})
    
    result = {}
    for leave_type, default_val in DEFAULT_LEAVE_BALANCE.items():
        entitled = balance.get(leave_type, default_val)
        used = balance.get(f'used_{leave_type.replace("_leave", "")}', 0)
        result[leave_type] = {
            "entitled": entitled,
            "used": used,
            "available": entitled - used
        }
    
    return result
