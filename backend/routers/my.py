"""
My Router - User self-service endpoints (attendance check-in/out, profile, onboarding)
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
from datetime import datetime, timezone, timedelta
import uuid
from .deps import get_db, APPROVAL_ROLES
from .models import User
from .deps import get_current_user
from utils.timezone import IST, now_ist, today_ist, current_month_ist, to_ist

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
            "date": today_ist(),
            "has_checked_in": False,
            "has_checked_out": False,
            "check_in_time": None,
            "check_out_time": None,
            "work_location": None,
            "record": None,
            "no_employee_record": True
        }
    
    today = today_ist()
    
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


@router.post("/check-in")
async def self_check_in(data: dict, current_user: User = Depends(get_current_user)):
    """
    Self check-in for employees.
    Creates attendance record with check-in time, location, and optional selfie.
    Links to payroll for working hours calculation.
    """
    db = get_db()
    
    # Get employee record
    emp = await db.employees.find_one(
        {"$or": [{"user_id": current_user.id}, {"official_email": current_user.email}]},
        {"_id": 0}
    )
    
    if not emp:
        raise HTTPException(status_code=404, detail="Employee record not found. Please contact HR.")
    
    today = today_ist()
    now = now_ist()
    approved_leave_today = await db.leave_requests.find_one({
        "employee_id": emp["id"],
        "status": "approved",
        "start_date": {"$lte": today},
        "end_date": {"$gte": today}
    }, {"_id": 0, "leave_type": 1})
    if approved_leave_today:
        leave_label = approved_leave_today.get("leave_type", "leave").replace("_", " ").title()
        raise HTTPException(
            status_code=400,
            detail=f"Cannot check in — you have an approved {leave_label} for today. Please cancel the leave first."
        )
    
    # Check if already checked in today - allow re-check-in, archive previous
    existing = await db.attendance.find_one({"employee_id": emp["id"], "date": today}, {"_id": 0})
    if existing:
        # Archive the previous record (mark as superseded) and delete it
        await db.attendance_history.insert_one({
            **existing,
            "superseded_at": now.isoformat(),
            "superseded_reason": "re_checkin"
        })
        await db.attendance.delete_one({"id": existing["id"]})
    
    # Create attendance record
    # Handle both direct lat/lng and geo_location object from frontend
    geo = data.get("geo_location", {})
    latitude = data.get("latitude") or geo.get("latitude")
    longitude = data.get("longitude") or geo.get("longitude")
    
    attendance = {
        "id": str(uuid.uuid4()),
        "employee_id": emp["id"],
        "employee_name": f"{emp.get('first_name', '')} {emp.get('last_name', '')}".strip(),
        "user_id": current_user.id,
        "date": today,
        "check_in_time": now.isoformat(),
        "check_out_time": None,
        "status": "present",
        "work_location": data.get("work_location", "office"),
        "location_type": data.get("location_type", "office"),  # office, wfh, on_site
        "client_id": data.get("client_id"),  # For on-site check-ins
        "client_name": data.get("client_name"),
        "project_id": data.get("project_id"),
        "project_name": data.get("project_name"),
        "latitude": latitude,
        "longitude": longitude,
        "location_accuracy": geo.get("accuracy"),
        "location_address": geo.get("address") or data.get("location_address"),
        "location_locality": data.get("location_locality", ""),
        "location_area": data.get("location_area", ""),
        "location_city": data.get("location_city", ""),
        "selfie": data.get("selfie"),  # Base64 selfie image
        "remarks": data.get("remarks", "Self check-in"),
        "working_hours": None,  # Calculated on check-out
        "overtime_hours": 0,
        "is_late": False,
        "late_minutes": 0,
        "is_early_departure": False,
        "source": "self_service",
        "created_at": now.isoformat(),
        "updated_at": now.isoformat()
    }
    
    # Calculate late arrival using business policy shift start (IST)
    # now is already IST from now_ist()
    
    # Fetch shift start from business policy
    shift_start_str = "10:00"  # will be overridden by policy
    late_threshold_minutes = 15
    try:
        att_policy = await db.business_policies.find_one(
            {"policy_type": "attendance", "scope": "company", "is_active": True},
            {"_id": 0, "rules": 1}
        )
        if att_policy:
            rules = {r["rule_id"]: r for r in att_policy.get("rules", [])}
            shift_start_str = rules.get("AT002", {}).get("value", "10:00")
            late_threshold_minutes = rules.get("AT004", {}).get("numeric_value", 15)
    except Exception:
        pass
    
    # Parse shift start and compare with IST check-in time
    shift_h, shift_m = int(shift_start_str.split(":")[0]), int(shift_start_str.split(":")[1])
    checkin_total_min = now.hour * 60 + now.minute
    shift_total_min = shift_h * 60 + shift_m
    late_by_min = checkin_total_min - shift_total_min
    
    if late_by_min > late_threshold_minutes:
        attendance["is_late"] = True
        attendance["late_minutes"] = late_by_min
    
    await db.attendance.insert_one(attendance)
    
    # Remove selfie from response (too large)
    attendance.pop("selfie", None)
    attendance.pop("_id", None)
    
    return {
        "message": "Checked in successfully",
        "attendance": attendance
    }


@router.post("/check-out")
async def self_check_out(data: dict = None, current_user: User = Depends(get_current_user)):
    """
    Self check-out for employees.
    Updates attendance record with check-out time and calculates working hours.
    Links to payroll for working hours and overtime calculation.
    """
    db = get_db()
    data = data or {}
    
    # Get employee record
    emp = await db.employees.find_one(
        {"$or": [{"user_id": current_user.id}, {"official_email": current_user.email}]},
        {"_id": 0}
    )
    
    if not emp:
        raise HTTPException(status_code=404, detail="Employee record not found")
    
    today = today_ist()
    now = now_ist()
    
    # Find today's attendance record
    record = await db.attendance.find_one({"employee_id": emp["id"], "date": today}, {"_id": 0})
    if not record:
        raise HTTPException(status_code=400, detail="No check-in record found for today")
    
    if record.get("check_out_time"):
        # Allow re-checkout - archive previous checkout in history
        await db.attendance_history.insert_one({
            **record,
            "superseded_at": now.isoformat(),
            "superseded_reason": "re_checkout"
        })
    
    # Calculate working hours using IST-aware check-in time
    check_in_time = to_ist(datetime.fromisoformat(record["check_in_time"].replace("Z", "+00:00")))
    working_seconds = (now - check_in_time).total_seconds()
    working_hours = round(working_seconds / 3600, 2)
    
    # Fetch configured shift hours from business policy
    standard_work_hours = 9  # default
    try:
        att_policy = await db.business_policies.find_one(
            {"policy_type": "attendance", "scope": "company", "is_active": True},
            {"_id": 0, "rules": 1}
        )
        if att_policy:
            rules = {r["rule_id"]: r for r in att_policy.get("rules", [])}
            standard_work_hours = rules.get("AT001", {}).get("numeric_value", 9)
    except Exception:
        pass
    
    # Calculate overtime beyond shift hours
    overtime_hours = max(0, round(working_hours - standard_work_hours, 2))
    
    # Check for early departure based on standard work hours
    is_early_departure = working_hours < standard_work_hours
    
    # Update attendance record
    geo = data.get("geo_location", {})
    update_data = {
        "check_out_time": now.isoformat(),
        "working_hours": working_hours,
        "overtime_hours": overtime_hours,
        "is_early_departure": is_early_departure,
        "checkout_latitude": data.get("latitude") or geo.get("latitude"),
        "checkout_longitude": data.get("longitude") or geo.get("longitude"),
        "checkout_accuracy": geo.get("accuracy"),
        "checkout_address": geo.get("address") or data.get("checkout_address", ""),
        "checkout_remarks": data.get("remarks"),
        "updated_at": now.isoformat()
    }
    
    await db.attendance.update_one(
        {"id": record["id"]},
        {"$set": update_data}
    )
    
    # Update record with new data
    record.update(update_data)
    record.pop("selfie", None)
    
    return {
        "message": "Checked out successfully",
        "attendance": record,
        "working_hours": working_hours,
        "overtime_hours": overtime_hours
    }


@router.get("/attendance")
async def get_my_attendance(
    month: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """
    Get current user's attendance records for a month.
    Returns records with summary stats, leave type, late penalty info.
    """
    db = get_db()
    
    # Get employee record
    emp = await db.employees.find_one(
        {"$or": [{"user_id": current_user.id}, {"official_email": current_user.email}]},
        {"_id": 0}
    )
    
    if not emp:
        return {"records": [], "summary": {}, "employee": {}}
    
    # Default to current month (IST)
    if not month:
        month = current_month_ist()
    
    # Query attendance for the month
    records = await db.attendance.find(
        {
            "employee_id": emp["id"],
            "date": {"$regex": f"^{month}"}
        },
        {"_id": 0, "selfie": 0}
    ).sort("date", -1).to_list(50)
    
    # Fetch leave requests for this month to show leave type
    leaves = await db.leave_requests.find(
        {
            "employee_id": emp["id"],
            "status": {"$in": ["approved", "pending"]},
            "start_date": {"$regex": f"^{month}"}
        },
        {"_id": 0, "start_date": 1, "end_date": 1, "leave_type": 1, "status": 1, "days": 1}
    ).to_list(100)
    
    # Build leave date map
    leave_map = {}
    for lv in leaves:
        try:
            s = datetime.fromisoformat(lv["start_date"].replace("Z", "+00:00"))
            e = datetime.fromisoformat(lv.get("end_date", lv["start_date"]).replace("Z", "+00:00"))
            d = s
            while d <= e:
                leave_map[d.strftime("%Y-%m-%d")] = {
                    "leave_type": lv["leave_type"],
                    "leave_status": lv["status"]
                }
                d += __import__('datetime').timedelta(days=1)
        except Exception:
            pass
    
    # Enrich records with leave type (only for non-present statuses)
    for r in records:
        lv_info = leave_map.get(r.get("date"))
        if lv_info and r.get("status") != "present":
            r["leave_type"] = lv_info["leave_type"]
            r["leave_status"] = lv_info["leave_status"]
    
    # Fetch shift config for display
    shift_config = {"standard_work_hours": 9, "overtime_threshold_hours": 10, "core_hours_start": "10:00", "core_hours_end": "19:00"}
    late_threshold_minutes = 15
    try:
        att_policy = await db.business_policies.find_one(
            {"policy_type": "attendance", "scope": "company", "is_active": True},
            {"_id": 0, "rules": 1}
        )
        if att_policy:
            rules_map = {r["rule_id"]: r for r in att_policy.get("rules", [])}
            shift_config = {
                "standard_work_hours": rules_map.get("AT001", {}).get("numeric_value", 9),
                "overtime_threshold_hours": rules_map.get("AT008", {}).get("numeric_value", 10),
                "core_hours_start": rules_map.get("AT002", {}).get("value", "10:00"),
                "core_hours_end": rules_map.get("AT003", {}).get("value", "19:00"),
                "late_threshold_minutes": rules_map.get("AT004", {}).get("numeric_value", 15),
                "grace_period_minutes": rules_map.get("AT010", {}).get("numeric_value", 30),
                "grace_days_per_month": rules_map.get("AT011", {}).get("numeric_value", 3),
                "late_penalty_amount": rules_map.get("AT012", {}).get("numeric_value", 100),
            }
            late_threshold_minutes = shift_config.get("late_threshold_minutes", 15)
    except Exception:
        pass
    
    # Normalize field names and dynamically recalculate late status using IST
    shift_start_str = shift_config.get("core_hours_start", "10:00")
    shift_h, shift_m = int(shift_start_str.split(":")[0]), int(shift_start_str.split(":")[1])
    shift_total_min = shift_h * 60 + shift_m
    
    for r in records:
        # Normalize: ensure check_in_time is set (old records use check_in)
        if not r.get("check_in_time") and r.get("check_in"):
            r["check_in_time"] = r["check_in"]
        if not r.get("check_out_time") and r.get("check_out"):
            r["check_out_time"] = r["check_out"]
        
        # Dynamically recalculate is_late based on check-in vs shift start (IST)
        cin = r.get("check_in_time")
        if cin and r.get("status") == "present":
            try:
                ci_ist = to_ist(datetime.fromisoformat(cin.replace("Z", "+00:00")))
                checkin_total_min = ci_ist.hour * 60 + ci_ist.minute
                late_by = checkin_total_min - shift_total_min
                r["is_late"] = late_by > late_threshold_minutes
                r["late_minutes"] = max(0, late_by) if late_by > late_threshold_minutes else 0
            except Exception:
                pass
    
    # Calculate summary (after recalculation)
    present = sum(1 for r in records if r.get("status") == "present")
    absent = sum(1 for r in records if r.get("status") == "absent")
    half_day = sum(1 for r in records if r.get("status") == "half_day")
    wfh = sum(1 for r in records if r.get("work_location") == "wfh")
    on_leave = sum(1 for r in records if r.get("status") == "on_leave")
    late_count = sum(1 for r in records if r.get("is_late"))
    total_hours = sum(r.get("working_hours", 0) or 0 for r in records)
    total_overtime = sum(r.get("overtime_hours", 0) or 0 for r in records)
    
    return {
        "records": records,
        "summary": {
            "present": present,
            "absent": absent,
            "half_day": half_day,
            "wfh": wfh,
            "on_leave": on_leave,
            "late_count": late_count,
            "total_hours": round(total_hours, 1),
            "total_overtime": round(total_overtime, 1)
        },
        "shift_config": shift_config,
        "employee": {
            "name": f"{emp.get('first_name', '')} {emp.get('last_name', '')}".strip(),
            "employee_id": emp.get("employee_id", ""),
            "department": emp.get("department", "")
        }
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
    
    # Get employee record (may not exist for all users)
    emp = await db.employees.find_one(
        {"$or": [{"user_id": current_user.id}, {"official_email": current_user.email}]},
        {"_id": 0}
    )
    
    # Get user data
    user_data = await db.users.find_one(
        {"id": current_user.id},
        {"_id": 0, "hashed_password": 0}
    )
    
    # Return user info even if no employee record (use user data as fallback)
    if not emp:
        # Build profile from user data for users without employee records
        return {
            "id": current_user.id,
            "employee_id": user_data.get("employee_id", "N/A"),
            "first_name": user_data.get("first_name", user_data.get("name", "").split()[0] if user_data.get("name") else ""),
            "last_name": user_data.get("last_name", " ".join(user_data.get("name", "").split()[1:]) if user_data.get("name") else ""),
            "email": current_user.email,
            "department": user_data.get("department", ""),
            "designation": user_data.get("designation", ""),
            "role": current_user.role,
            "phone": user_data.get("phone", ""),
            "date_of_joining": user_data.get("date_of_joining", ""),
            "reporting_manager_name": user_data.get("reporting_manager_name", ""),
            "no_employee_record": True
        }
    
    # Combine employee and user data
    result = {**emp}
    result["email"] = current_user.email
    result["role"] = current_user.role
    if user_data:
        result["first_name"] = result.get("first_name") or user_data.get("first_name", "")
        result["last_name"] = result.get("last_name") or user_data.get("last_name", "")
    
    return result


@router.get("/leave-balance")
async def get_my_leave_balance(current_user: User = Depends(get_current_user)):
    """Get current user's leave balance"""
    db = get_db()
    
    # Find employee record
    emp = await db.employees.find_one(
        {"$or": [{"user_id": current_user.id}, {"official_email": current_user.email}]},
        {"_id": 0}
    )
    
    DEFAULT_LEAVE_BALANCE = {
        'casual_leave': 12,
        'sick_leave': 6,
        'earned_leave': 15
    }
    
    # Return default balance if no employee record
    if not emp:
        return {
            "casual": {"total": DEFAULT_LEAVE_BALANCE['casual_leave'], "used": 0, "available": DEFAULT_LEAVE_BALANCE['casual_leave']},
            "sick": {"total": DEFAULT_LEAVE_BALANCE['sick_leave'], "used": 0, "available": DEFAULT_LEAVE_BALANCE['sick_leave']},
            "earned": {"total": DEFAULT_LEAVE_BALANCE['earned_leave'], "used": 0, "available": DEFAULT_LEAVE_BALANCE['earned_leave']}
        }
    
    balance = emp.get('leave_balance', {})
    
    # Calculate actual used from leave_requests (authoritative source)
    approved_leaves = await db.leave_requests.find(
        {"employee_id": emp["id"], "status": "approved"},
        {"_id": 0, "leave_type": 1, "days": 1}
    ).to_list(500)
    
    used_casual = sum(lv.get("days", 0) for lv in approved_leaves if lv.get("leave_type") == "casual_leave")
    used_sick = sum(lv.get("days", 0) for lv in approved_leaves if lv.get("leave_type") == "sick_leave")
    used_earned = sum(lv.get("days", 0) for lv in approved_leaves if lv.get("leave_type") == "earned_leave")
    
    total_casual = balance.get('casual_leave', 12)
    total_sick = balance.get('sick_leave', 6)
    total_earned = balance.get('earned_leave', 15)
    
    return {
        "casual": {
            "total": total_casual,
            "used": used_casual,
            "available": total_casual - used_casual
        },
        "sick": {
            "total": total_sick,
            "used": used_sick,
            "available": total_sick - used_sick
        },
        "earned": {
            "total": total_earned,
            "used": used_earned,
            "available": total_earned - used_earned
        }
    }


@router.get("/change-requests")
async def get_my_change_requests(current_user: User = Depends(get_current_user)):
    """Get current user's profile change requests"""
    db = get_db()
    
    # Find all change requests by this user
    requests = await db.profile_change_requests.find(
        {"user_id": current_user.id},
        {"_id": 0}
    ).sort("created_at", -1).to_list(50)
    
    return requests


@router.post("/change-request")
async def submit_change_request(
    request_data: dict,
    current_user: User = Depends(get_current_user)
):
    """Submit a profile change request for HR approval"""
    db = get_db()
    
    change_request = {
        "id": str(uuid.uuid4()),
        "user_id": current_user.id,
        "employee_email": current_user.email,
        "section": request_data.get("section"),
        "changes": request_data.get("changes"),
        "reason": request_data.get("reason"),
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    # Handle bank proof document
    if request_data.get("proof_document"):
        change_request["proof_document"] = request_data.get("proof_document")
        change_request["proof_filename"] = request_data.get("proof_filename")
    
    await db.profile_change_requests.insert_one(change_request)
    
    return {"message": "Change request submitted successfully", "id": change_request["id"]}


@router.get("/pending-approvals")
async def get_my_pending_approvals(current_user: User = Depends(get_current_user)):
    """Get items pending current user's approval"""
    db = get_db()
    
    # Leave requests pending approval (if manager)
    leaves = []
    if current_user.role in APPROVAL_ROLES:
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
    total_leaves = sum(leave.get("days", 0) for leave in leaves)
    
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



@router.get("/guidance-state")
async def get_guidance_state(current_user: User = Depends(get_current_user)):
    """Get user's guidance system state (tips, features seen, workflow progress)"""
    db = get_db()
    
    # Try to find existing guidance state
    guidance = await db.user_guidance_state.find_one(
        {"user_id": current_user.id},
        {"_id": 0}
    )
    
    if guidance:
        return guidance
    
    # Return default state if not found
    return {
        "user_id": current_user.id,
        "dismissed_tips": [],
        "seen_features": [],
        "workflow_progress": {},
        "dont_show_tips": False
    }


@router.post("/guidance-state")
async def save_guidance_state(
    state_data: dict,
    current_user: User = Depends(get_current_user)
):
    """Save user's guidance system state"""
    db = get_db()
    
    guidance_state = {
        "user_id": current_user.id,
        "dismissed_tips": state_data.get("dismissed_tips", []),
        "seen_features": state_data.get("seen_features", []),
        "workflow_progress": state_data.get("workflow_progress", {}),
        "dont_show_tips": state_data.get("dont_show_tips", False),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.user_guidance_state.update_one(
        {"user_id": current_user.id},
        {"$set": guidance_state},
        upsert=True
    )
    
    return guidance_state
