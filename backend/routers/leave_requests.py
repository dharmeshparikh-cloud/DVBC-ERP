"""
Leave Requests Router - Leave application, approval workflow.
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Optional, List
from datetime import datetime, timezone, date
import uuid
from pydantic import BaseModel
from .deps import get_db, MANAGER_ROLES, HR_ROLES, get_role_group, has_role
from .models import User
from .deps import get_current_user

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
    
    # RBAC Migration: Non-managers see only their own
    manager_roles = get_role_group("MANAGER_ROLES", fail_closed=False) or MANAGER_ROLES
    hr_roles = get_role_group("HR_ROLES", fail_closed=False) or HR_ROLES
    if not has_role(current_user.role, manager_roles) and not has_role(current_user.role, hr_roles):
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
    
    # RBAC Migration
    hr_roles = get_role_group("HR_ROLES", fail_closed=True)
    if not hr_roles or not has_role(current_user.role, hr_roles):
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
    
    # RBAC Migration: Check ownership
    hr_roles = get_role_group("HR_ROLES", fail_closed=False) or HR_ROLES
    if leave.get("user_id") != current_user.id and not has_role(current_user.role, hr_roles):
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


@router.get("/employee/{employee_id}/balance")
async def get_leave_balance(employee_id: str, current_user: User = Depends(get_current_user)):
    """
    Get leave balance for an employee.
    
    P0 FIX: Now calculates balance from leave_requests (authoritative source)
    instead of reading from employees.leave_balance (which could be stale).
    """
    db = get_db()
    
    # Import the calculation service
    import sys
    sys.path.insert(0, '/app/backend')
    from services.leave_balance_service import calculate_leave_balance
    
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0, "id": 1})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Calculate balance from authoritative source (leave_requests)
    balance = await calculate_leave_balance(db, employee_id)
    
    # Return in expected format
    result = {}
    for leave_type in ["casual_leave", "sick_leave", "earned_leave"]:
        result[leave_type] = balance.get(leave_type, {"entitled": 0, "used": 0, "available": 0})
    
    return result


@router.get("/stats/company-wide")
async def get_company_leave_stats(current_user: User = Depends(get_current_user)):
    """
    Get company-wide leave utilization statistics.
    
    P0 FIX: Now calculates from leave_requests (authoritative source)
    instead of reading from employees.leave_balance (which could be stale).
    """
    db = get_db()
    
    # Only HR and Admin can view company-wide stats
    allowed_roles = ['admin', 'hr_manager', 'hr_executive', 'hr_admin']
    if current_user.role not in allowed_roles and current_user.department != 'HR':
        raise HTTPException(status_code=403, detail="Only HR can view company-wide leave stats")
    
    # Import the calculation service
    import sys
    sys.path.insert(0, '/app/backend')
    from services.leave_balance_service import calculate_leave_balance, get_leave_entitlements
    
    DEFAULT_LEAVE_TYPES = ['casual_leave', 'sick_leave', 'earned_leave']
    
    # Get all active employees
    employees = await db.employees.find(
        {"is_active": {"$ne": False}},
        {"_id": 0, "id": 1}
    ).to_list(None)
    
    total_employees = len(employees)
    if total_employees == 0:
        return {
            "total_employees": 0,
            "leave_types": {}
        }
    
    # Aggregate leave stats using the calculation service
    stats = {lt: {"total_entitled": 0, "total_used": 0, "employees_with_usage": 0} for lt in DEFAULT_LEAVE_TYPES}
    
    for emp in employees:
        try:
            balance = await calculate_leave_balance(db, emp["id"])
            for leave_type in DEFAULT_LEAVE_TYPES:
                lt_balance = balance.get(leave_type, {})
                stats[leave_type]["total_entitled"] += lt_balance.get("entitled", 0)
                stats[leave_type]["total_used"] += lt_balance.get("used", 0)
                if lt_balance.get("used", 0) > 0:
                    stats[leave_type]["employees_with_usage"] += 1
        except Exception:
            continue
    
    # Calculate final stats
    result_stats = {}
    for leave_type in DEFAULT_LEAVE_TYPES:
        total_entitled = stats[leave_type]["total_entitled"]
        total_used = stats[leave_type]["total_used"]
        utilization_pct = round((total_used / total_entitled * 100), 1) if total_entitled > 0 else 0
        
        result_stats[leave_type] = {
            "label": leave_type.replace('_', ' ').title(),
            "total_entitled": total_entitled,
            "total_used": total_used,
            "total_available": total_entitled - total_used,
            "utilization_percent": utilization_pct,
            "employees_with_usage": stats[leave_type]["employees_with_usage"],
            "avg_used_per_employee": round(total_used / total_employees, 1) if total_employees > 0 else 0
        }
    
    # Get pending leave requests count
    pending_count = await db.leave_requests.count_documents({
        "status": {"$in": ["pending", "rm_approved"]},
        "rm_status": {"$in": ["pending", None]}
    })
    
    # Get leave requests this month
    from datetime import datetime
    start_of_month = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    requests_this_month = await db.leave_requests.count_documents({
        "created_at": {"$gte": start_of_month}
    })
    
    return {
        "total_employees": total_employees,
        "pending_requests": pending_count,
        "requests_this_month": requests_this_month,
        "leave_types": result_stats,
        "data_source": "calculated_from_leave_requests"  # P0 FIX indicator
    }

