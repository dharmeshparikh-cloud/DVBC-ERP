"""
My Router - User self-service endpoints (attendance check-in/out, profile, onboarding)
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
from datetime import datetime, timezone
from .deps import get_db
from .models import User
from .auth import get_current_user

router = APIRouter(prefix="/my", tags=["My - Self Service"])


async def _get_my_employee(current_user: User):
    """Helper to get employee record for current user"""
    db = get_db()
    emp = await db.employees.find_one(
        {"$or": [{"user_id": current_user.id}, {"official_email": current_user.email}]},
        {"_id": 0}
    )
    if not emp:
        raise HTTPException(status_code=404, detail="Employee record not found")
    return emp


@router.get("/check-status")
async def get_check_in_status(current_user: User = Depends(get_current_user)):
    """Get current day's check-in/check-out status"""
    db = get_db()
    
    emp = await db.employees.find_one(
        {"$or": [{"user_id": current_user.id}, {"official_email": current_user.email}]},
        {"_id": 0}
    )
    
    # If no employee record, return default status
    if not emp:
        return {
            "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "has_checked_in": False,
            "has_checked_out": False,
            "check_in_time": None,
            "check_out_time": None,
            "work_location": None,
            "record": None,
            "no_employee_record": True
        }
    
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    record = await db.attendance.find_one(
        {"employee_id": emp["id"], "date": today},
        {"_id": 0, "selfie": 0}
    )
    
    return {
        "date": today,
        "has_checked_in": record is not None,
        "has_checked_out": record.get("check_out_time") is not None if record else False,
        "check_in_time": record.get("check_in_time") if record else None,
        "check_out_time": record.get("check_out_time") if record else None,
        "work_location": record.get("work_location") if record else None,
        "record": record
    }


@router.get("/onboarding-status")
async def get_onboarding_status(current_user: User = Depends(get_current_user)):
    """Check if user has completed the onboarding tour"""
    db = get_db()
    user_doc = await db.users.find_one({"id": current_user.id}, {"_id": 0, "has_completed_onboarding": 1})
    return {
        "has_completed_onboarding": user_doc.get("has_completed_onboarding", False) if user_doc else False
    }


@router.post("/complete-onboarding")
async def complete_onboarding(current_user: User = Depends(get_current_user)):
    """Mark onboarding tour as completed"""
    db = get_db()
    await db.users.update_one(
        {"id": current_user.id},
        {"$set": {
            "has_completed_onboarding": True,
            "onboarding_completed_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    return {"message": "Onboarding completed", "has_completed_onboarding": True}


@router.post("/reset-onboarding")
async def reset_onboarding(current_user: User = Depends(get_current_user)):
    """Reset onboarding status to replay the tour"""
    db = get_db()
    await db.users.update_one(
        {"id": current_user.id},
        {"$set": {"has_completed_onboarding": False}}
    )
    return {"message": "Onboarding reset", "has_completed_onboarding": False}


@router.get("/profile")
async def get_my_profile(current_user: User = Depends(get_current_user)):
    """Get current user's full profile"""
    db = get_db()
    emp = await _get_my_employee(current_user)
    
    # Get user data
    user_data = await db.users.find_one(
        {"id": current_user.id},
        {"_id": 0, "hashed_password": 0}
    )
    
    return {
        "user": user_data,
        "employee": emp
    }


@router.get("/pending-approvals")
async def get_my_pending_approvals(current_user: User = Depends(get_current_user)):
    """Get items pending current user's approval"""
    db = get_db()
    
    # Leave requests pending approval (if manager)
    leaves = []
    if current_user.role in ["admin", "manager", "hr_manager"]:
        leaves = await db.leave_requests.find(
            {"status": "pending"},
            {"_id": 0}
        ).to_list(50)
    
    # Expense claims pending
    expenses = await db.expenses.find(
        {"approver_id": current_user.id, "status": "pending"},
        {"_id": 0}
    ).to_list(50)
    
    # Attendance approvals
    attendance = await db.attendance.find(
        {"approver_id": current_user.id, "approval_status": "pending_approval"},
        {"_id": 0}
    ).to_list(50)
    
    return {
        "leaves": leaves,
        "expenses": expenses,
        "attendance": attendance,
        "total": len(leaves) + len(expenses) + len(attendance)
    }


@router.get("/recent-activity")
async def get_my_recent_activity(limit: int = 20, current_user: User = Depends(get_current_user)):
    """Get current user's recent activity"""
    db = get_db()
    
    emp = await _get_my_employee(current_user)
    
    # Get recent attendance
    attendance = await db.attendance.find(
        {"employee_id": emp["id"]},
        {"_id": 0, "selfie": 0}
    ).sort("date", -1).to_list(5)
    
    # Get recent leaves
    leaves = await db.leave_requests.find(
        {"employee_id": emp["id"]},
        {"_id": 0}
    ).sort("created_at", -1).to_list(5)
    
    # Get recent tasks
    tasks = await db.tasks.find(
        {"assigned_to": current_user.id},
        {"_id": 0}
    ).sort("updated_at", -1).to_list(5)
    
    return {
        "recent_attendance": attendance,
        "recent_leaves": leaves,
        "recent_tasks": tasks
    }


@router.get("/stats")
async def get_my_stats(current_user: User = Depends(get_current_user)):
    """Get current user's statistics"""
    db = get_db()
    
    emp = await _get_my_employee(current_user)
    now = datetime.now(timezone.utc)
    month_start = datetime(now.year, now.month, 1).strftime("%Y-%m-%d")
    
    # Attendance this month
    attendance_count = await db.attendance.count_documents({
        "employee_id": emp["id"],
        "date": {"$gte": month_start}
    })
    
    # Leaves taken this year
    year_start = datetime(now.year, 1, 1).strftime("%Y-%m-%d")
    leaves = await db.leave_requests.find({
        "employee_id": emp["id"],
        "status": "approved",
        "start_date": {"$gte": year_start}
    }, {"_id": 0, "days": 1}).to_list(100)
    total_leaves = sum(l.get("days", 0) for l in leaves)
    
    # Tasks
    pending_tasks = await db.tasks.count_documents({
        "assigned_to": current_user.id,
        "status": {"$in": ["pending", "in_progress"]}
    })
    
    return {
        "attendance_this_month": attendance_count,
        "leaves_taken_this_year": total_leaves,
        "pending_tasks": pending_tasks
    }
