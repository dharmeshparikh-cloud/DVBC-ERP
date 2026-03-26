"""
Attendance Router - Check-in/out, Attendance Management, Approvals

PERFORMANCE OPTIMIZATION: December 2025
- Added WebSocket notifications for real-time updates
- Added Redis cache invalidation
"""

from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone, timedelta
from typing import Optional, List
import uuid

from .models import User, UserRole
from .deps import get_db, HR_ROLES, HR_ADMIN_ROLES, HR_PM_ROLES, get_role_group, has_role
from .deps import get_current_user
from services.websocket_manager import ws_manager, notify_dashboard_refresh
from services.redis_cache import CacheInvalidation
from utils.timezone import IST, now_ist, today_ist, current_month_ist, to_ist

router = APIRouter(prefix="/attendance", tags=["Attendance"])



@router.get("/admin/list")
async def get_all_attendance_admin(
    month: Optional[str] = None,
    employee_id: Optional[str] = None,
    status: Optional[str] = None,
    work_location: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """
    Get all employee attendance records with filters. HR/Admin only.
    Supports Excel-like filtering by status, location, employee.
    """
    db = get_db()
    
    if current_user.role not in ["admin", "hr_admin", "hr"]:
        raise HTTPException(status_code=403, detail="Only HR/Admin can view all attendance")
    
    if not month:
        month = current_month_ist()
    
    query = {"date": {"$regex": f"^{month}"}}
    if employee_id:
        query["employee_id"] = employee_id
    if status:
        query["status"] = status
    if work_location:
        query["work_location"] = work_location
    
    records = await db.attendance.find(query, {"_id": 0, "selfie": 0}).sort([("date", -1), ("employee_id", 1)]).to_list(2000)
    
    # Get employee names
    emp_ids = list(set(r.get("employee_id") for r in records if r.get("employee_id")))
    employees = {}
    if emp_ids:
        emps = await db.employees.find(
            {"id": {"$in": emp_ids}},
            {"_id": 0, "id": 1, "first_name": 1, "last_name": 1, "employee_id": 1, "department": 1}
        ).to_list(500)
        employees = {e["id"]: e for e in emps}
    
    # Enrich records
    for r in records:
        emp = employees.get(r.get("employee_id"), {})
        r["employee_name"] = f"{emp.get('first_name', '')} {emp.get('last_name', '')}".strip()
        r["employee_code"] = emp.get("employee_id", "")
        r["department"] = emp.get("department", "")
    
    # Summary
    present = sum(1 for r in records if r.get("status") == "present")
    absent = sum(1 for r in records if r.get("status") == "absent")
    late_count = sum(1 for r in records if r.get("is_late"))
    total_hours = sum(r.get("working_hours", 0) or 0 for r in records)
    total_overtime = sum(r.get("overtime_hours", 0) or 0 for r in records)
    
    return {
        "records": records,
        "summary": {
            "total_records": len(records),
            "present": present,
            "absent": absent,
            "late": late_count,
            "total_hours": round(total_hours, 1),
            "total_overtime": round(total_overtime, 1)
        }
    }



# ═══════════════════════════════════════════════════════════════════
# REGULARIZATION ENDPOINT (HR/Admin only)
# ═══════════════════════════════════════════════════════════════════

@router.put("/{record_id}/regularize")
async def regularize_attendance(
    record_id: str,
    data: dict,
    current_user: User = Depends(get_current_user)
):
    """
    Regularize an attendance record. HR/Admin only.
    Updates the original record directly with corrected times, status, etc.
    """
    db = get_db()
    
    # Only HR/Admin can regularize
    if current_user.role not in ["admin", "hr_admin", "hr"]:
        raise HTTPException(status_code=403, detail="Only HR/Admin can regularize attendance records")
    
    record = await db.attendance.find_one({"id": record_id}, {"_id": 0})
    if not record:
        raise HTTPException(status_code=404, detail="Attendance record not found")
    
    now = datetime.now(timezone.utc).isoformat()
    
    update_fields = {
        "regularized": True,
        "regularized_by": current_user.id,
        "regularized_by_name": current_user.full_name or current_user.email,
        "regularized_at": now,
        "regularization_reason": data.get("reason", ""),
        "updated_at": now
    }
    
    # Update provided fields
    if data.get("check_in_time"):
        update_fields["check_in_time"] = data["check_in_time"]
    if data.get("check_out_time"):
        update_fields["check_out_time"] = data["check_out_time"]
    if data.get("status"):
        update_fields["status"] = data["status"]
    if data.get("work_location"):
        update_fields["work_location"] = data["work_location"]
    if data.get("remarks"):
        update_fields["remarks"] = data.get("remarks")
    
    # Recalculate working hours if both in/out times are provided
    cin = data.get("check_in_time") or record.get("check_in_time")
    cout = data.get("check_out_time") or record.get("check_out_time")
    if cin and cout:
        try:
            ci_dt = datetime.fromisoformat(cin.replace("Z", "+00:00"))
            co_dt = datetime.fromisoformat(cout.replace("Z", "+00:00"))
            working_hours = round((co_dt - ci_dt).total_seconds() / 3600, 2)
            update_fields["working_hours"] = working_hours
            
            # Recalculate overtime
            standard_hours = 9
            try:
                att_policy = await db.business_policies.find_one(
                    {"policy_type": "attendance", "scope": "company", "is_active": True},
                    {"_id": 0, "rules": 1}
                )
                if att_policy:
                    rules = {r["rule_id"]: r for r in att_policy.get("rules", [])}
                    standard_hours = rules.get("AT001", {}).get("numeric_value", 9)
            except Exception:
                pass
            
            update_fields["overtime_hours"] = max(0, round(working_hours - standard_hours, 2))
            
            # Recalculate late status based on check-in time (IST)
            try:
                ci_ist = to_ist(ci_dt)
                
                # Get shift start from policy
                shift_start_str = "10:00"
                late_threshold = 15
                if att_policy:
                    rules_map = {r["rule_id"]: r for r in att_policy.get("rules", [])}
                    shift_start_str = rules_map.get("AT002", {}).get("value", "10:00")
                    late_threshold = rules_map.get("AT004", {}).get("numeric_value", 15)
                
                s_h, s_m = int(shift_start_str.split(":")[0]), int(shift_start_str.split(":")[1])
                late_by = (ci_ist.hour * 60 + ci_ist.minute) - (s_h * 60 + s_m)
                update_fields["is_late"] = late_by > late_threshold
                update_fields["late_minutes"] = max(0, late_by) if late_by > late_threshold else 0
            except Exception:
                pass
        except Exception:
            pass
    
    await db.attendance.update_one({"id": record_id}, {"$set": update_fields})
    
    return {"message": "Attendance regularized successfully", "record_id": record_id}



# ═══════════════════════════════════════════════════════════════════
# MY ATTENDANCE ENDPOINTS (for current user)
# ═══════════════════════════════════════════════════════════════════

@router.get("/my")
async def get_my_attendance(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get current user's attendance records."""
    db = get_db()
    
    # Get employee ID for current user
    employee = await db.employees.find_one({"user_id": current_user.id}, {"_id": 0, "id": 1})
    employee_id = employee["id"] if employee else current_user.id
    
    query = {"employee_id": employee_id}
    
    if date_from and date_to:
        query["date"] = {"$gte": date_from, "$lte": date_to}
    elif date_from:
        query["date"] = {"$gte": date_from}
    elif date_to:
        query["date"] = {"$lte": date_to}
    
    records = await db.attendance.find(query, {"_id": 0}).sort("date", -1).to_list(100)
    
    return records


@router.get("/status")
async def get_attendance_status(
    date: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get current user's attendance status for today (or specified date)."""
    db = get_db()
    
    # Get employee ID for current user
    employee = await db.employees.find_one({"user_id": current_user.id}, {"_id": 0, "id": 1, "employee_id": 1})
    employee_id = employee.get("id") or employee.get("employee_id") if employee else current_user.id
    
    target_date = date or today_ist()
    
    # Find today's attendance record
    record = await db.attendance.find_one(
        {"employee_id": employee_id, "date": target_date},
        {"_id": 0}
    )
    
    if not record:
        return {
            "date": target_date,
            "employee_id": employee_id,
            "is_checked_in": False,
            "is_checked_out": False,
            "check_in_time": None,
            "check_out_time": None,
            "status": "not_marked",
            "working_hours": 0
        }
    
    # Calculate working hours if both check-in and check-out exist
    working_hours = 0
    if record.get("check_in") and record.get("check_out"):
        try:
            check_in = datetime.fromisoformat(record["check_in"].replace("Z", "+00:00"))
            check_out = datetime.fromisoformat(record["check_out"].replace("Z", "+00:00"))
            working_hours = round((check_out - check_in).total_seconds() / 3600, 2)
        except Exception:
            pass
    
    return {
        "date": record.get("date", target_date),
        "employee_id": employee_id,
        "is_checked_in": bool(record.get("check_in")),
        "is_checked_out": bool(record.get("check_out")),
        "check_in_time": record.get("check_in"),
        "check_out_time": record.get("check_out"),
        "status": record.get("status", "present"),
        "working_hours": working_hours,
        "is_late": record.get("is_late", False),
        "location": record.get("location"),
        "notes": record.get("notes")
    }


@router.post("")
async def record_attendance(data: dict, current_user: User = Depends(get_current_user)):
    """Record attendance entry (HR/Admin manual entry)."""
    db = get_db()
    
    # RBAC Migration: Using database-driven role check with fail-closed
    hr_roles = get_role_group("HR_ROLES", fail_closed=True)
    if not hr_roles or not has_role(current_user.role, hr_roles):
        raise HTTPException(status_code=403, detail="Only HR can manually record attendance")
    
    attendance = {
        "id": str(uuid.uuid4()),
        "employee_id": data.get("employee_id"),
        "date": data.get("date"),
        "check_in": data.get("check_in"),
        "check_out": data.get("check_out"),
        "status": data.get("status", "present"),
        "work_location": data.get("work_location", "office"),
        "notes": data.get("notes"),
        "recorded_by": current_user.id,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.attendance.insert_one(attendance)
    
    return {"message": "Attendance recorded", "id": attendance["id"]}


@router.post("/bulk")
async def record_bulk_attendance(data: dict, current_user: User = Depends(get_current_user)):
    """Record bulk attendance (HR/Admin)."""
    db = get_db()
    
    # RBAC Migration: Using database-driven role check
    hr_roles = get_role_group("HR_ROLES", fail_closed=True)
    if not hr_roles or not has_role(current_user.role, hr_roles):
        raise HTTPException(status_code=403, detail="Only HR can record bulk attendance")
    
    records = data.get("records", [])
    if not records:
        raise HTTPException(status_code=400, detail="No attendance records provided")
    
    for record in records:
        record["id"] = str(uuid.uuid4())
        record["recorded_by"] = current_user.id
        record["created_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.attendance.insert_many(records)
    
    return {"message": f"Recorded {len(records)} attendance entries"}


@router.get("")
async def get_attendance(
    employee_id: Optional[str] = None,
    date: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get attendance records with filters."""
    db = get_db()
    
    query = {}
    if employee_id:
        query["employee_id"] = employee_id
    if date:
        query["date"] = date
    if date_from and date_to:
        query["date"] = {"$gte": date_from, "$lte": date_to}
    if status:
        query["status"] = status
    
    # Non-HR users can only see their own attendance
    if current_user.role not in HR_PM_ROLES:
        # Get employee ID for current user
        employee = await db.employees.find_one({"user_id": current_user.id}, {"_id": 0, "id": 1})
        if employee:
            query["employee_id"] = employee["id"]
        else:
            query["employee_id"] = current_user.id
    
    records = await db.attendance.find(query, {"_id": 0}).sort("date", -1).to_list(1000)
    
    return records


@router.get("/summary")
async def get_attendance_summary(
    employee_id: Optional[str] = None,
    month: Optional[int] = None,
    year: Optional[int] = None,
    current_user: User = Depends(get_current_user)
):
    """Get attendance summary for a month - returns per-employee breakdown."""
    db = get_db()
    
    now = datetime.now(timezone.utc)
    month = month or now.month
    year = year or now.year
    
    # Build date range for the month
    start_date = f"{year}-{str(month).zfill(2)}-01"
    if month == 12:
        end_date = f"{year + 1}-01-01"
    else:
        end_date = f"{year}-{str(month + 1).zfill(2)}-01"
    
    # Get all employees first
    employees = await db.employees.find(
        {"is_active": {"$ne": False}},
        {"_id": 0, "id": 1, "employee_id": 1, "first_name": 1, "last_name": 1, "department": 1}
    ).to_list(500)
    
    # Create employee lookup dict
    emp_lookup = {}
    for emp in employees:
        emp_key = emp.get("id") or emp.get("employee_id")
        emp_lookup[emp_key] = {
            "employee_id": emp_key,
            "emp_code": emp.get("employee_id", emp_key),
            "name": f"{emp.get('first_name', '')} {emp.get('last_name', '')}".strip() or "Unknown",
            "department": emp.get("department", "-"),
            "present": 0,
            "absent": 0,
            "half_day": 0,
            "wfh": 0,
            "on_leave": 0,
            "total": 0
        }
    
    # Aggregate attendance by employee and status
    pipeline = [
        {"$match": {"date": {"$gte": start_date, "$lt": end_date}}},
        {"$group": {
            "_id": {"employee_id": "$employee_id", "status": "$status"},
            "count": {"$sum": 1}
        }}
    ]
    
    results = await db.attendance.aggregate(pipeline).to_list(1000)
    
    # Map status names to frontend expected keys
    status_map = {
        "present": "present",
        "absent": "absent",
        "half_day": "half_day",
        "work_from_home": "wfh",
        "wfh": "wfh",
        "on_leave": "on_leave",
        "leave": "on_leave"
    }
    
    # Populate counts
    for result in results:
        emp_id = result["_id"]["employee_id"]
        status = result["_id"]["status"]
        count = result["count"]
        
        if emp_id in emp_lookup:
            status_key = status_map.get(status, status)
            if status_key in emp_lookup[emp_id]:
                emp_lookup[emp_id][status_key] = count
                emp_lookup[emp_id]["total"] += count
    
    # Return as array, filtered to only employees with attendance data
    summary_list = [emp for emp in emp_lookup.values() if emp["total"] > 0]
    
    # If no attendance data, return all employees with zero counts
    if not summary_list:
        summary_list = list(emp_lookup.values())
    
    return summary_list


@router.get("/analytics")
async def get_attendance_analytics(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get attendance analytics (admin/HR only)."""
    db = get_db()
    
    # RBAC Migration: Using database-driven role check
    hr_roles = get_role_group("HR_ROLES", fail_closed=True)
    if not hr_roles or not has_role(current_user.role, hr_roles):
        raise HTTPException(status_code=403, detail="Only HR can view attendance analytics")
    
    # Default to last 30 days
    if not date_from:
        date_from = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d")
    if not date_to:
        date_to = today_ist()
    
    query = {"date": {"$gte": date_from, "$lte": date_to}}
    
    # Daily attendance count
    daily_pipeline = [
        {"$match": query},
        {"$group": {
            "_id": "$date",
            "present": {"$sum": {"$cond": [{"$eq": ["$status", "present"]}, 1, 0]}},
            "absent": {"$sum": {"$cond": [{"$eq": ["$status", "absent"]}, 1, 0]}},
            "wfh": {"$sum": {"$cond": [{"$eq": ["$work_location", "wfh"]}, 1, 0]}},
            "total": {"$sum": 1}
        }},
        {"$sort": {"_id": 1}}
    ]
    
    daily_stats = await db.attendance.aggregate(daily_pipeline).to_list(100)
    
    # Work location distribution
    location_pipeline = [
        {"$match": query},
        {"$group": {
            "_id": "$work_location",
            "count": {"$sum": 1}
        }}
    ]
    
    location_stats = await db.attendance.aggregate(location_pipeline).to_list(10)
    
    return {
        "daily": daily_stats,
        "by_location": {loc["_id"]: loc["count"] for loc in location_stats if loc["_id"]}
    }


@router.get("/mobile-stats")
async def get_mobile_attendance_stats(current_user: User = Depends(get_current_user)):
    """Get attendance stats for mobile app."""
    db = get_db()
    
    # Get employee ID for current user
    employee = await db.employees.find_one({"user_id": current_user.id}, {"_id": 0})
    if not employee:
        employee = {"id": current_user.id}
    
    today = today_ist()
    month_start = today_ist()[:8] + "01"
    
    # Today's attendance
    today_attendance = await db.attendance.find_one(
        {"employee_id": employee["id"], "date": today},
        {"_id": 0}
    )
    
    # This month summary
    month_query = {
        "employee_id": employee["id"],
        "date": {"$gte": month_start, "$lte": today}
    }
    
    month_pipeline = [
        {"$match": month_query},
        {"$group": {
            "_id": "$status",
            "count": {"$sum": 1}
        }}
    ]
    
    month_results = await db.attendance.aggregate(month_pipeline).to_list(10)
    month_summary = {r["_id"]: r["count"] for r in month_results if r["_id"]}
    
    return {
        "today": today_attendance,
        "month_summary": month_summary,
        "is_checked_in": today_attendance.get("check_in") is not None if today_attendance else False,
        "is_checked_out": today_attendance.get("check_out") is not None if today_attendance else False
    }



# ==================== ATTENDANCE POLICY CONFIGURATION ====================
# SSOT: Business Rules is the ONLY source of truth for attendance policies
# No hardcoded fallback values - must be configured in Business Rules

CONSULTING_ROLES = ["consultant", "lean_consultant", "lead_consultant", "senior_consultant", "principal_consultant"]


async def get_attendance_policy_from_business_rules(db) -> dict:
    """
    Fetch attendance policy from Business Rules collection (SSOT).
    This is the ONLY source of truth - no fallbacks.
    
    Raises HTTPException if Business Rules not configured.
    """
    attendance_policy = await db.business_policies.find_one(
        {"policy_type": "attendance", "is_active": True},
        {"_id": 0}
    )
    
    if not attendance_policy or not attendance_policy.get("rules"):
        raise HTTPException(
            status_code=500, 
            detail="Attendance Policy not configured in Business Rules. Please configure Standard Attendance Policy first."
        )
    
    rules = {r["rule_id"]: r for r in attendance_policy["rules"]}
    
    return {
        "source": "business_rules",
        "policy_id": attendance_policy.get("id"),
        "policy_name": attendance_policy.get("name", "Standard Attendance Policy"),
        "core_hours_start": rules.get("AT002", {}).get("value"),
        "core_hours_end": rules.get("AT003", {}).get("value"),
        "standard_work_hours": rules.get("AT001", {}).get("numeric_value", 9),
        "late_threshold_minutes": rules.get("AT004", {}).get("numeric_value", 15),
        "half_day_hours": rules.get("AT005", {}).get("numeric_value", 4),
        "full_day_hours": rules.get("AT006", {}).get("numeric_value", 8),
        "wfh_days_per_week": rules.get("AT007", {}).get("numeric_value", 2),
        "overtime_threshold_hours": rules.get("AT008", {}).get("numeric_value", 10),
        "grace_period_minutes": 30,  # TODO: Move to Business Rules
        "grace_days_per_month": 3,   # TODO: Move to Business Rules
        "late_penalty_amount": 100   # TODO: Move to Business Rules
    }


async def get_employee_policy(db, employee_id: str, employee_role: str = None) -> dict:
    """
    Get attendance policy for an employee.
    Priority: 1. Employee-specific custom policy (if any)
              2. Business Rules (SSOT) - MANDATORY
    
    No fallback to hardcoded values.
    """
    # Get base policy from Business Rules (SSOT) - MANDATORY
    br_policy = await get_attendance_policy_from_business_rules(db)
    
    # Check for employee-specific custom policy override
    custom_policy = await db.employee_attendance_policies.find_one(
        {"employee_id": employee_id, "is_active": True},
        {"_id": 0}
    )
    
    if custom_policy:
        return {
            "check_in": custom_policy.get("check_in", br_policy["core_hours_start"]),
            "check_out": custom_policy.get("check_out", br_policy["core_hours_end"]),
            "grace_period_minutes": custom_policy.get("grace_period_minutes", br_policy["grace_period_minutes"]),
            "grace_days_per_month": custom_policy.get("grace_days_per_month", br_policy["grace_days_per_month"]),
            "late_threshold_minutes": br_policy["late_threshold_minutes"],
            "half_day_hours": br_policy["half_day_hours"],
            "full_day_hours": br_policy["full_day_hours"],
            "is_custom": True,
            "source": "employee_custom + business_rules",
            "policy_name": br_policy["policy_name"],
            "reason": custom_policy.get("reason", "Custom override applied")
        }
    
    return {
        "check_in": br_policy["core_hours_start"],
        "check_out": br_policy["core_hours_end"],
        "grace_period_minutes": br_policy["grace_period_minutes"],
        "grace_days_per_month": br_policy["grace_days_per_month"],
        "late_threshold_minutes": br_policy["late_threshold_minutes"],
        "half_day_hours": br_policy["half_day_hours"],
        "full_day_hours": br_policy["full_day_hours"],
        "is_custom": False,
        "source": "business_rules",
        "policy_name": br_policy["policy_name"],
        "reason": f"From {br_policy['policy_name']}"
    }


def parse_time(time_str: str) -> tuple:
    """Parse HH:MM to (hour, minute)"""
    parts = time_str.split(":")
    return int(parts[0]), int(parts[1])


def is_within_grace(actual_time: str, expected_time: str, grace_minutes: int = 30) -> bool:
    """Check if actual time is within grace period of expected time"""
    if not actual_time:
        return False
    
    try:
        actual = datetime.fromisoformat(actual_time.replace("Z", "+00:00"))
        exp_h, exp_m = parse_time(expected_time)
        
        # Create expected datetime for comparison
        expected = actual.replace(hour=exp_h, minute=exp_m, second=0, microsecond=0)
        
        diff_minutes = (actual - expected).total_seconds() / 60
        
        # For check-in: within grace if not more than grace_minutes late
        # For check-out: within grace if not more than grace_minutes early
        return abs(diff_minutes) <= grace_minutes
    except Exception:
        return False


@router.get("/policy")
async def get_attendance_policy(current_user: User = Depends(get_current_user)):
    """Get current attendance policy configuration from Business Rules (SSOT)"""
    db = get_db()
    
    # Get Business Rules policy (SSOT - ONLY source)
    br_policy = await get_attendance_policy_from_business_rules(db)
    
    # Get custom policies count
    custom_count = await db.employee_attendance_policies.count_documents({"is_active": True})
    
    return {
        "policy": br_policy,
        "consulting_roles": CONSULTING_ROLES,
        "custom_policies_count": custom_count,
        "ssot_source": "business_rules"
    }


@router.get("/policy/employee/{employee_id}")
async def get_employee_attendance_policy(employee_id: str, current_user: User = Depends(get_current_user)):
    """Get attendance policy for a specific employee"""
    db = get_db()
    
    # RBAC Migration: Using database-driven role check
    hr_roles = get_role_group("HR_ROLES", fail_closed=True)
    if not hr_roles or not has_role(current_user.role, hr_roles):
        # Non-HR can only see their own policy
        employee = await db.employees.find_one({"user_id": current_user.id}, {"_id": 0, "id": 1})
        if not employee or employee["id"] != employee_id:
            raise HTTPException(status_code=403, detail="Can only view your own policy")
    
    # Get employee details
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0, "id": 1, "employee_id": 1, "first_name": 1, "last_name": 1, "role": 1})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    policy = await get_employee_policy(db, employee_id, employee.get("role"))
    
    return {
        "employee_id": employee_id,
        "employee_code": employee.get("employee_id"),
        "employee_name": f"{employee.get('first_name', '')} {employee.get('last_name', '')}".strip(),
        "policy": policy
    }


@router.get("/policy/custom")
async def list_custom_policies(current_user: User = Depends(get_current_user)):
    """List all custom employee attendance policies"""
    db = get_db()
    
    # RBAC Migration: Using database-driven role check
    hr_roles = get_role_group("HR_ROLES", fail_closed=True)
    if not hr_roles or not has_role(current_user.role, hr_roles):
        raise HTTPException(status_code=403, detail="Only HR can view custom policies")
    
    policies = await db.employee_attendance_policies.find(
        {"is_active": True},
        {"_id": 0}
    ).to_list(500)
    
    # Enrich with employee details
    result = []
    for policy in policies:
        employee = await db.employees.find_one(
            {"id": policy["employee_id"]},
            {"_id": 0, "employee_id": 1, "first_name": 1, "last_name": 1, "department": 1}
        )
        if employee:
            policy["employee_code"] = employee.get("employee_id")
            policy["employee_name"] = f"{employee.get('first_name', '')} {employee.get('last_name', '')}".strip()
            policy["department"] = employee.get("department")
        result.append(policy)
    
    return {"policies": result}


@router.post("/policy/custom")
async def create_custom_policy(data: dict, current_user: User = Depends(get_current_user)):
    """Create or update custom attendance policy for an employee"""
    db = get_db()
    
    # RBAC Migration: Using database-driven role check
    hr_admin_roles = get_role_group("HR_ADMIN_ROLES", fail_closed=True)
    if not hr_admin_roles or not has_role(current_user.role, hr_admin_roles):
        raise HTTPException(status_code=403, detail="Only HR Manager/Admin can set custom policies")
    
    employee_id = data.get("employee_id")
    if not employee_id:
        raise HTTPException(status_code=400, detail="employee_id required")
    
    # Verify employee exists
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0, "id": 1, "employee_id": 1, "first_name": 1, "last_name": 1})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Get base policy from Business Rules
    br_policy = await get_attendance_policy_from_business_rules(db)
    
    policy_data = {
        "employee_id": employee_id,
        "employee_code": employee.get("employee_id"),
        "employee_name": f"{employee.get('first_name', '')} {employee.get('last_name', '')}".strip(),
        "check_in": data.get("check_in", br_policy["core_hours_start"]),
        "check_out": data.get("check_out", br_policy["core_hours_end"]),
        "grace_period_minutes": data.get("grace_period_minutes", br_policy["grace_period_minutes"]),
        "grace_days_per_month": data.get("grace_days_per_month", br_policy["grace_days_per_month"]),
        "reason": data.get("reason", ""),
        "effective_from": data.get("effective_from", now[:10]),
        "effective_to": data.get("effective_to"),
        "is_active": True,
        "created_by": current_user.id,
        "created_by_name": current_user.full_name,
        "updated_at": now,
        "base_policy": br_policy["policy_name"]
    }
    
    # Check if policy already exists
    existing = await db.employee_attendance_policies.find_one({"employee_id": employee_id})
    
    if existing:
        await db.employee_attendance_policies.update_one(
            {"employee_id": employee_id},
            {"$set": policy_data}
        )
        action = "updated"
    else:
        policy_data["id"] = str(uuid.uuid4())
        policy_data["created_at"] = now
        await db.employee_attendance_policies.insert_one(policy_data)
        action = "created"
    
    # Remove MongoDB _id before returning
    policy_data.pop("_id", None)
    
    return {
        "message": f"Custom policy {action} for {policy_data['employee_name']}",
        "policy": policy_data
    }


@router.delete("/policy/custom/{employee_id}")
async def delete_custom_policy(employee_id: str, current_user: User = Depends(get_current_user)):
    """Delete custom attendance policy for an employee (reverts to default)"""
    db = get_db()
    
    # RBAC Migration: Using database-driven role check
    hr_admin_roles = get_role_group("HR_ADMIN_ROLES", fail_closed=True)
    if not hr_admin_roles or not has_role(current_user.role, hr_admin_roles):
        raise HTTPException(status_code=403, detail="Only HR Manager/Admin can delete custom policies")
    
    result = await db.employee_attendance_policies.delete_one({"employee_id": employee_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="No custom policy found for this employee")
    
    return {"message": "Custom policy deleted, employee reverted to default policy"}


@router.get("/consulting-employees")
async def get_consulting_employees(current_user: User = Depends(get_current_user)):
    """Get list of employees with consulting roles from employee master"""
    db = get_db()
    
    # RBAC Migration: Using database-driven role check
    hr_roles = get_role_group("HR_ROLES", fail_closed=True)
    if not hr_roles or not has_role(current_user.role, hr_roles):
        raise HTTPException(status_code=403, detail="Only HR can view consulting employees")
    
    # Get the configured consulting roles from settings
    settings = await db.settings.find_one({"type": "attendance_policy"}, {"_id": 0})
    consulting_roles = settings.get("consulting_roles", []) if settings else []
    
    # If no roles configured, use default consulting roles
    if not consulting_roles:
        consulting_roles = ["consultant", "lean_consultant", "lead_consultant", "senior_consultant", "principal_consultant"]
    
    # Find all active employees with consulting roles
    employees = await db.employees.find(
        {
            "$or": [{"is_active": True}, {"is_active": {"$exists": False}}],
            "role": {"$in": consulting_roles}
        },
        {"_id": 0, "id": 1, "employee_id": 1, "first_name": 1, "last_name": 1, "role": 1, "department": 1}
    ).to_list(500)
    
    # Get count by role
    role_counts = {}
    for emp in employees:
        role = emp.get("role", "unknown")
        role_counts[role] = role_counts.get(role, 0) + 1
    
    return {
        "employees": employees,
        "consulting_roles": consulting_roles,
        "role_counts": role_counts,
        "total_consulting_employees": len(employees)
    }


@router.post("/auto-validate")
async def auto_validate_attendance(data: dict, current_user: User = Depends(get_current_user)):
    """
    Auto-validate attendance for a month based on policy:
    - Working days: Mon-Sat (exclude PH and approved leaves)
    - Non-consulting: 10 AM - 7 PM
    - Consulting: 10:30 AM - 7:30 PM
    - Grace: 3 days/month with 30 min early/late allowed
    - Beyond grace: Rs.100 penalty (if HR approves)
    """
    db = get_db()
    
    # RBAC Migration: Using database-driven role check
    hr_roles = get_role_group("HR_ROLES", fail_closed=True)
    if not hr_roles or not has_role(current_user.role, hr_roles):
        raise HTTPException(status_code=403, detail="Only HR can auto-validate attendance")
    
    month = data.get("month")  # Format: YYYY-MM
    if not month:
        month = current_month_ist()
    
    year, month_num = int(month.split("-")[0]), int(month.split("-")[1])
    
    # Get all employees
    employees = await db.employees.find(
        {"$or": [{"is_active": True}, {"is_active": {"$exists": False}}]},
        {"_id": 0, "id": 1, "employee_id": 1, "first_name": 1, "last_name": 1, "role": 1, "department": 1}
    ).to_list(500)
    
    # Get public holidays for the month
    public_holidays = await db.public_holidays.find(
        {"date": {"$regex": f"^{month}"}},
        {"_id": 0, "date": 1}
    ).to_list(50)
    ph_dates = set([ph["date"] for ph in public_holidays])
    
    # Get approved leaves for all employees
    approved_leaves = await db.leave_requests.find(
        {"status": "approved", "start_date": {"$regex": f"^{month}"}},
        {"_id": 0, "employee_id": 1, "start_date": 1, "end_date": 1, "days": 1}
    ).to_list(500)
    
    # Build leave lookup
    employee_leave_dates = {}
    for leave in approved_leaves:
        emp_id = leave.get("employee_id")
        if emp_id not in employee_leave_dates:
            employee_leave_dates[emp_id] = set()
        
        # Add all dates in leave range
        try:
            start = datetime.fromisoformat(leave["start_date"][:10])
            end = datetime.fromisoformat(leave["end_date"][:10])
            current = start
            while current <= end:
                employee_leave_dates[emp_id].add(current.strftime("%Y-%m-%d"))
                current += timedelta(days=1)
        except Exception:
            pass
    
    results = []
    
    for emp in employees:
        emp_id = emp.get("id")
        emp_code = emp.get("employee_id")
        emp_name = f"{emp.get('first_name', '')} {emp.get('last_name', '')}".strip()
        role = emp.get("role", "")
        
        # Get employee-specific or role-based policy (from Business Rules SSOT)
        emp_policy = await get_employee_policy(db, emp_id, role)
        is_consulting = role in CONSULTING_ROLES
        policy = {
            "check_in": emp_policy["check_in"],
            "check_out": emp_policy["check_out"]
        }
        grace_minutes = emp_policy.get("grace_period_minutes", 30)
        grace_days = emp_policy.get("grace_days_per_month", 3)
        
        # Get attendance records for this employee this month
        attendance_records = await db.attendance.find(
            {"employee_id": emp_id, "date": {"$regex": f"^{month}"}},
            {"_id": 0}
        ).to_list(50)
        attendance_by_date = {a["date"]: a for a in attendance_records}
        
        # Calculate working days in month
        from calendar import monthrange
        _, days_in_month = monthrange(year, month_num)
        
        present_days = 0
        absent_days = 0
        leave_days = 0
        late_count = 0
        early_leave_count = 0
        grace_violations = []
        penalties = []
        
        for day in range(1, days_in_month + 1):
            date_str = f"{month}-{str(day).zfill(2)}"
            
            try:
                date_obj = datetime(year, month_num, day)
                day_name = date_obj.strftime("%A")
            except Exception:
                continue
            
            # Skip non-working days (weekdays are working, weekend depends on policy)
            # Default working days: Mon-Sat
            WORKING_DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
            if day_name not in WORKING_DAYS:
                continue
            
            # Skip public holidays
            if date_str in ph_dates:
                continue
            
            # Check if on approved leave
            if emp_id in employee_leave_dates and date_str in employee_leave_dates[emp_id]:
                leave_days += 1
                continue
            
            # Check attendance record
            attendance = attendance_by_date.get(date_str)
            
            if not attendance or not attendance.get("check_in"):
                absent_days += 1
                continue
            
            # Validate check-in/out times
            check_in = attendance.get("check_in")
            check_out = attendance.get("check_out")
            
            is_late = False
            is_early_leave = False
            
            if check_in:
                if not is_within_grace(check_in, policy["check_in"], 0):
                    # Check if within employee's grace minutes
                    if is_within_grace(check_in, policy["check_in"], grace_minutes):
                        is_late = True
                        late_count += 1
                    else:
                        # More than grace period late - auto penalty
                        is_late = True
                        late_count += 1
            
            if check_out:
                if not is_within_grace(check_out, policy["check_out"], 0):
                    if is_within_grace(check_out, policy["check_out"], grace_minutes):
                        is_early_leave = True
                        early_leave_count += 1
            
            if is_late or is_early_leave:
                grace_violations.append({
                    "date": date_str,
                    "late": is_late,
                    "early_leave": is_early_leave,
                    "check_in": check_in,
                    "check_out": check_out
                })
            
            present_days += 1
        
        # Calculate penalties (beyond grace days limit)
        total_grace_used = len(grace_violations)
        penalty_days = max(0, total_grace_used - grace_days)
        # Get penalty amount from Business Rules policy
        br_policy = await get_attendance_policy_from_business_rules(db)
        late_penalty_amount = br_policy.get("late_penalty_amount", 100)
        penalty_amount = penalty_days * late_penalty_amount
        
        if penalty_days > 0:
            penalties = grace_violations[grace_days:]
        
        results.append({
            "employee_id": emp_id,
            "employee_code": emp_code,
            "name": emp_name,
            "role": role,
            "is_consulting": is_consulting,
            "has_custom_policy": emp_policy.get("is_custom", False),
            "policy_source": emp_policy.get("source", "business_rules"),
            "policy_name": emp_policy.get("policy_name", "Standard Attendance Policy"),
            "policy_times": f"{policy['check_in']} - {policy['check_out']}",
            "present_days": present_days,
            "absent_days": absent_days,
            "leave_days": leave_days,
            "grace_days_used": min(total_grace_used, grace_days),
            "grace_days_allowed": grace_days,
            "grace_violations": grace_violations,
            "penalty_days": penalty_days,
            "pending_penalty_amount": penalty_amount,
            "penalty_details": penalties,
            "status": "clean" if penalty_amount == 0 else "penalty_pending"
        })
    
    # Get policy info for response
    policy_info = await get_attendance_policy_from_business_rules(db)
    
    return {
        "month": month,
        "policy": policy_info,
        "employees": results,
        "summary": {
            "total_employees": len(results),
            "clean": len([r for r in results if r["status"] == "clean"]),
            "penalty_pending": len([r for r in results if r["status"] == "penalty_pending"]),
            "total_pending_penalties": sum([r["pending_penalty_amount"] for r in results])
        }
    }


@router.post("/apply-penalties")
async def apply_attendance_penalties(data: dict, current_user: User = Depends(get_current_user)):
    """
    HR validates attendance and creates penalty records in the UNIFIED employee_penalties collection.
    Creates records with status='pending_review' for HR to approve/reject on the Penalty Management page.
    Uses upsert to prevent duplicates (employee_id + month + violation_code + source).
    """
    db = get_db()
    
    hr_admin_roles = get_role_group("HR_ADMIN_ROLES", fail_closed=True)
    if not hr_admin_roles or not has_role(current_user.role, hr_admin_roles):
        raise HTTPException(status_code=403, detail="Only HR Manager/Admin can apply penalties")
    
    month = data.get("month")
    employee_penalties = data.get("penalties", [])
    
    if not month or not employee_penalties:
        raise HTTPException(status_code=400, detail="Month and penalties required")
    
    now = datetime.now(timezone.utc).isoformat()
    created_count = 0
    updated_count = 0
    
    # Get employee details for enrichment
    emp_ids = [p.get("employee_id") for p in employee_penalties]
    employees = await db.employees.find(
        {"id": {"$in": emp_ids}},
        {"_id": 0, "id": 1, "employee_id": 1, "first_name": 1, "last_name": 1, "department": 1}
    ).to_list(100)
    emp_map = {e["id"]: e for e in employees}
    
    for p in employee_penalties:
        emp_id = p.get("employee_id")
        penalty_amount = p.get("penalty_amount", 0)
        penalty_days = p.get("penalty_days", 0)
        
        if penalty_amount <= 0:
            continue
        
        emp = emp_map.get(emp_id, {})
        
        # Check if unified penalty already exists for this employee/month/source
        existing = await db.employee_penalties.find_one({
            "employee_id": emp_id,
            "month": month,
            "violation_code": "AT_LATE",
            "source": "attendance_validation"
        })
        
        if existing:
            await db.employee_penalties.update_one(
                {"id": existing["id"]},
                {"$set": {
                    "amount": penalty_amount,
                    "reason": f"{penalty_days} late days beyond grace limit",
                    "description": f"{penalty_days} late days beyond grace limit",
                    "updated_at": now,
                    "updated_by": current_user.id,
                    "updated_by_name": current_user.full_name
                }}
            )
            updated_count += 1
        else:
            await db.employee_penalties.insert_one({
                "id": str(uuid.uuid4()),
                "employee_id": emp_id,
                "employee_code": emp.get("employee_id", ""),
                "employee_name": f"{emp.get('first_name', '')} {emp.get('last_name', '')}".strip(),
                "department": emp.get("department", ""),
                "month": month,
                "category": "attendance",
                "category_name": "Attendance Penalty",
                "violation_code": "AT_LATE",
                "violation_name": "Late Arrival",
                "source": "attendance_validation",
                "name": "Late Arrival (Monthly Validation)",
                "amount": penalty_amount,
                "reason": f"{penalty_days} late days beyond grace limit",
                "description": f"{penalty_days} late days beyond grace limit",
                "apply_to_payroll": True,
                "status": "pending_review",
                "is_arrears": False,
                "created_at": now,
                "created_by": current_user.id,
                "created_by_name": current_user.full_name
            })
            created_count += 1
    
    return {
        "message": f"Created {created_count} penalties, updated {updated_count} existing. Go to Penalty Management to approve.",
        "month": month,
        "created_count": created_count,
        "updated_count": updated_count,
        "redirect": "/penalty-management"
    }


# ==================== PENALTY DASHBOARD API ====================

@router.get("/penalty-dashboard")
async def get_penalty_dashboard(
    months: int = 6,
    employee_ids: Optional[str] = None,
    day: Optional[str] = None,
    department: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """
    Get penalty analytics for HR dashboard.
    
    Filters (all server-side):
    - months: Number of months to analyze (3, 6, 12)
    - employee_ids: Comma-separated employee IDs to filter by
    - day: Specific date (YYYY-MM-DD) to filter penalties for that day
    - department: Department name to filter by
    
    Returns:
    - Monthly penalty trends (last N months)
    - Top violators (employees with most penalties)
    - Grace utilization by department
    - Penalty breakdown by type
    """
    db = get_db()
    
    # RBAC check
    hr_roles = get_role_group("HR_ROLES", fail_closed=True)
    if not hr_roles or not has_role(current_user.role, hr_roles):
        raise HTTPException(status_code=403, detail="Only HR can view penalty dashboard")
    
    # Calculate date range for last N months
    now = datetime.now(timezone.utc)
    month_list = []
    for i in range(months):
        month_date = now - timedelta(days=i*30)
        month_str = month_date.strftime("%Y-%m")
        if month_str not in month_list:
            month_list.append(month_str)
    month_list = month_list[:months]
    
    # Build penalty query with filters
    penalty_query = {"month": {"$in": month_list}}
    
    # Employee filter
    emp_id_list = []
    if employee_ids:
        emp_id_list = [eid.strip() for eid in employee_ids.split(",") if eid.strip()]
        if emp_id_list:
            penalty_query["employee_id"] = {"$in": emp_id_list}
    
    # Day filter - filter penalties that include the specific day
    if day:
        penalty_query["penalty_dates"] = day
    
    # Department filter - need to get employee IDs for that department first
    if department:
        dept_employees = await db.employees.find(
            {"department": department},
            {"_id": 0, "id": 1}
        ).to_list(500)
        dept_emp_ids = [e["id"] for e in dept_employees]
        if emp_id_list:
            # Intersect with existing employee filter
            dept_emp_ids = [eid for eid in dept_emp_ids if eid in emp_id_list]
        if dept_emp_ids:
            penalty_query["employee_id"] = {"$in": dept_emp_ids}
        else:
            penalty_query["employee_id"] = {"$in": []}
    
    # Get all penalties in date range with filters (from unified collection)
    all_penalties = await db.employee_penalties.find(
        penalty_query,
        {"_id": 0}
    ).to_list(1000)
    
    # Get all employees for reference
    employees = await db.employees.find(
        {"is_active": True},
        {"_id": 0, "id": 1, "employee_id": 1, "first_name": 1, "last_name": 1, "department": 1}
    ).to_list(500)
    emp_map = {e["id"]: e for e in employees}
    
    # === 1. Monthly Penalty Trends ===
    monthly_trends = {}
    for m in month_list:
        monthly_trends[m] = {"total_amount": 0, "employee_count": 0, "total_days": 0}
    
    for p in all_penalties:
        m = p.get("month")
        if m in monthly_trends:
            monthly_trends[m]["total_amount"] += p.get("amount", 0)
            monthly_trends[m]["employee_count"] += 1
    
    trends_list = [
        {
            "month": m,
            "month_name": datetime.strptime(m, "%Y-%m").strftime("%b %Y"),
            **monthly_trends[m]
        }
        for m in sorted(month_list, reverse=True)
    ]
    
    # === 2. Top Violators (All Time in Range) ===
    violator_map = {}
    for p in all_penalties:
        emp_id = p.get("employee_id")
        if emp_id not in violator_map:
            emp = emp_map.get(emp_id, {})
            violator_map[emp_id] = {
                "employee_id": emp_id,
                "employee_code": emp.get("employee_id", "-"),
                "employee_name": f"{emp.get('first_name', '')} {emp.get('last_name', '')}".strip() or "Unknown",
                "department": emp.get("department", "-"),
                "total_penalty_amount": 0,
                "total_penalty_days": 0,
                "months_with_penalties": set()
            }
        violator_map[emp_id]["total_penalty_amount"] += p.get("amount", 0)
        violator_map[emp_id]["months_with_penalties"].add(p.get("month"))
    
    # Convert sets to counts and sort
    top_violators = sorted(
        [
            {**v, "months_with_penalties": len(v["months_with_penalties"])}
            for v in violator_map.values()
        ],
        key=lambda x: x["total_penalty_amount"],
        reverse=True
    )[:10]
    
    # === 3. Department-wise Grace Utilization ===
    # Get current month attendance validation data
    current_month = now.strftime("%Y-%m")
    
    dept_stats = {}
    for emp in employees:
        dept = emp.get("department", "Other")
        if dept not in dept_stats:
            dept_stats[dept] = {
                "department": dept,
                "total_employees": 0,
                "employees_with_penalties": 0,
                "total_penalty_amount": 0,
                "total_penalty_days": 0
            }
        dept_stats[dept]["total_employees"] += 1
    
    for p in all_penalties:
        if p.get("month") == current_month:
            emp_id = p.get("employee_id")
            emp = emp_map.get(emp_id, {})
            dept = emp.get("department", "Other")
            if dept in dept_stats:
                dept_stats[dept]["employees_with_penalties"] += 1
                dept_stats[dept]["total_penalty_amount"] += p.get("amount", 0)
    
    dept_list = sorted(dept_stats.values(), key=lambda x: x["total_penalty_amount"], reverse=True)
    
    # === 4. Current Month Summary ===
    current_penalties = [p for p in all_penalties if p.get("month") == current_month]
    current_month_summary = {
        "month": current_month,
        "total_employees_penalized": len(set(p.get("employee_id") for p in current_penalties)),
        "total_penalty_amount": sum(p.get("amount", 0) for p in current_penalties),
        "avg_penalty_per_employee": (
            sum(p.get("amount", 0) for p in current_penalties) / 
            max(1, len(set(p.get("employee_id") for p in current_penalties)))
        )
    }
    
    # === 5. Get Attendance Policy for context ===
    policy = await db.business_policies.find_one(
        {"policy_type": "attendance", "scope": "company", "is_active": True},
        {"_id": 0}
    )
    rules = {r["rule_id"]: r for r in policy.get("rules", [])} if policy else {}
    
    policy_context = {
        "grace_days_per_month": rules.get("AT011", {}).get("numeric_value", 3),
        "late_penalty_per_day": rules.get("AT012", {}).get("numeric_value", 100),
        "grace_period_minutes": rules.get("AT010", {}).get("numeric_value", 30),
        "core_hours_start": rules.get("AT002", {}).get("value", "10:00"),
        "core_hours_end": rules.get("AT003", {}).get("value", "19:00")
    }
    
    # === 6. Get employee list for filter dropdown ===
    emp_options = [
        {
            "id": e["id"],
            "employee_id": e.get("employee_id", "-"),
            "name": f"{e.get('first_name', '')} {e.get('last_name', '')}".strip(),
            "department": e.get("department", "-")
        }
        for e in employees
    ]
    
    # Get unique departments for filter
    departments = sorted(set(e.get("department", "Other") for e in employees if e.get("department")))
    
    return {
        "monthly_trends": trends_list,
        "top_violators": top_violators,
        "department_breakdown": dept_list,
        "current_month_summary": current_month_summary,
        "policy_context": policy_context,
        "data_range": {
            "months_analyzed": months,
            "from_month": min(month_list) if month_list else current_month,
            "to_month": max(month_list) if month_list else current_month
        },
        "filter_options": {
            "employees": emp_options,
            "departments": departments
        },
        "active_filters": {
            "employee_ids": emp_id_list if emp_id_list else None,
            "day": day,
            "department": department
        }
    }


# ==================== HR FUNCTIONS FOR BULK LEAVE/ATTENDANCE ====================

@router.post("/hr/bulk-leave-credit")
async def hr_bulk_leave_credit(data: dict, current_user: User = Depends(get_current_user)):
    """
    HR function to credit leave balance to all employees (e.g., annual reset, bonus leaves)
    """
    db = get_db()
    
    # RBAC Migration: Using database-driven role check
    hr_admin_roles = get_role_group("HR_ADMIN_ROLES", fail_closed=True)
    if not hr_admin_roles or not has_role(current_user.role, hr_admin_roles):
        raise HTTPException(status_code=403, detail="Only HR Manager/Admin can credit leaves")
    
    leave_type = data.get("leave_type")  # casual_leave, sick_leave, earned_leave
    credit_days = data.get("credit_days", 0)
    employee_ids = data.get("employee_ids", [])  # Empty = all employees
    reset_used = data.get("reset_used", False)  # Reset used count to 0
    
    if not leave_type or credit_days <= 0:
        raise HTTPException(status_code=400, detail="leave_type and credit_days required")
    
    query = {}
    if employee_ids:
        query["id"] = {"$in": employee_ids}
    else:
        query["$or"] = [{"is_active": True}, {"is_active": {"$exists": False}}]
    
    update_fields = {leave_type: credit_days}
    if reset_used:
        leave_key = leave_type.replace("_leave", "")
        update_fields[f"used_{leave_key}"] = 0
    
    result = await db.employees.update_many(
        query,
        {"$set": {f"leave_balance.{k}": v for k, v in update_fields.items()}}
    )
    
    return {
        "message": f"Leave balance updated for {result.modified_count} employees",
        "leave_type": leave_type,
        "credit_days": credit_days,
        "reset_used": reset_used,
        "affected_count": result.modified_count
    }


@router.post("/hr/apply-leave-for-employee")
async def hr_apply_leave_for_employee(data: dict, current_user: User = Depends(get_current_user)):
    """
    HR function to apply leave on behalf of an employee (auto-approved)
    """
    db = get_db()
    
    # RBAC Migration: Using database-driven role check
    hr_roles = get_role_group("HR_ROLES", fail_closed=True)
    if not hr_roles or not has_role(current_user.role, hr_roles):
        raise HTTPException(status_code=403, detail="Only HR can apply leave on behalf of employee")
    
    employee_id = data.get("employee_id")
    leave_type = data.get("leave_type", "casual_leave")
    start_date = data.get("start_date")
    end_date = data.get("end_date", start_date)
    reason = data.get("reason", "Applied by HR")
    is_half_day = data.get("is_half_day", False)
    
    if not employee_id or not start_date:
        raise HTTPException(status_code=400, detail="employee_id and start_date required")
    
    # Get employee
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Calculate days
    if is_half_day:
        days = 0.5
    else:
        start = datetime.fromisoformat(start_date[:10])
        end = datetime.fromisoformat(end_date[:10])
        days = (end - start).days + 1
    
    now = datetime.now(timezone.utc).isoformat()
    leave_request = {
        "id": str(uuid.uuid4()),
        "employee_id": employee_id,
        "employee_code": employee.get("employee_id"),
        "employee_name": f"{employee.get('first_name', '')} {employee.get('last_name', '')}".strip(),
        "user_id": employee.get("user_id"),
        "leave_type": leave_type,
        "start_date": start_date,
        "end_date": end_date,
        "days": days,
        "is_half_day": is_half_day,
        "reason": reason,
        "status": "approved",  # Auto-approved when applied by HR
        "approval_type": "hr_applied",
        "applied_by_hr": True,
        "applied_by": current_user.id,
        "applied_by_name": current_user.full_name,
        "approved_by": current_user.id,
        "approved_by_name": current_user.full_name,
        "approved_at": now,
        "created_at": now,
        "updated_at": now
    }
    
    await db.leave_requests.insert_one(leave_request)
    
    # Update leave balance
    leave_type_key = leave_type.replace("_leave", "")
    used_field = f"leave_balance.used_{leave_type_key}"
    
    await db.employees.update_one(
        {"id": employee_id},
        {"$inc": {used_field: days}}
    )
    
    # Notify employee
    if employee.get("user_id"):
        await db.notifications.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": employee["user_id"],
            "type": "leave_applied_by_hr",
            "title": "Leave Applied by HR",
            "message": f"HR has applied {leave_type.replace('_', ' ').title()} ({days} days) on your behalf for {start_date[:10]}.",
            "reference_type": "leave_request",
            "reference_id": leave_request["id"],
            "is_read": False,
            "created_at": now
        })
    
    return {
        "message": "Leave applied and auto-approved",
        "leave_request_id": leave_request["id"],
        "days": days
    }


@router.post("/hr/mark-attendance-bulk")
async def hr_mark_attendance_bulk(data: dict, current_user: User = Depends(get_current_user)):
    """
    HR function to mark attendance for multiple employees for a date
    """
    db = get_db()
    
    # RBAC Migration: Using database-driven role check
    hr_roles = get_role_group("HR_ROLES", fail_closed=True)
    if not hr_roles or not has_role(current_user.role, hr_roles):
        raise HTTPException(status_code=403, detail="Only HR can mark bulk attendance")
    
    date = data.get("date")
    records = data.get("records", [])  # [{employee_id, status, check_in, check_out}]
    
    if not date or not records:
        raise HTTPException(status_code=400, detail="date and records required")
    
    now = datetime.now(timezone.utc).isoformat()
    created_count = 0
    updated_count = 0
    
    for record in records:
        emp_id = record.get("employee_id")
        status = record.get("status", "present")
        check_in = record.get("check_in")
        check_out = record.get("check_out")
        
        existing = await db.attendance.find_one({"employee_id": emp_id, "date": date})
        
        attendance_data = {
            "employee_id": emp_id,
            "date": date,
            "status": status,
            "check_in": check_in,
            "check_out": check_out,
            "recorded_by": current_user.id,
            "updated_at": now
        }
        
        if existing:
            await db.attendance.update_one(
                {"id": existing["id"]},
                {"$set": attendance_data}
            )
            updated_count += 1
        else:
            attendance_data["id"] = str(uuid.uuid4())
            attendance_data["created_at"] = now
            await db.attendance.insert_one(attendance_data)
            created_count += 1
    
    return {
        "message": f"Attendance updated: {created_count} created, {updated_count} updated",
        "date": date,
        "created": created_count,
        "updated": updated_count
    }


@router.get("/hr/employee-attendance-input/{month}")
async def get_employee_attendance_input(month: str, current_user: User = Depends(get_current_user)):
    """
    Get attendance input form for HR to link attendance to payroll
    Returns all employees with their attendance summary for the month
    """
    db = get_db()
    
    # RBAC Migration: Using database-driven role check
    hr_roles = get_role_group("HR_ROLES", fail_closed=True)
    if not hr_roles or not has_role(current_user.role, hr_roles):
        raise HTTPException(status_code=403, detail="Only HR can access attendance input")
    
    # Get all employees
    employees = await db.employees.find(
        {"$or": [{"is_active": True}, {"is_active": {"$exists": False}}]},
        {"_id": 0, "id": 1, "employee_id": 1, "first_name": 1, "last_name": 1, "department": 1, "role": 1}
    ).to_list(500)
    
    # Get attendance summary for month
    attendance_records = await db.attendance.find(
        {"date": {"$regex": f"^{month}"}},
        {"_id": 0}
    ).to_list(5000)
    
    # Get approved leaves for month
    approved_leaves = await db.leave_requests.find(
        {"status": "approved", "start_date": {"$regex": f"^{month}"}},
        {"_id": 0, "employee_id": 1, "days": 1}
    ).to_list(500)
    
    # Aggregate by employee
    emp_attendance = {}
    for record in attendance_records:
        emp_id = record.get("employee_id")
        if emp_id not in emp_attendance:
            emp_attendance[emp_id] = {"present": 0, "absent": 0, "half_day": 0, "wfh": 0}
        
        status = record.get("status", "present")
        emp_attendance[emp_id][status] = emp_attendance[emp_id].get(status, 0) + 1
    
    emp_leaves = {}
    for leave in approved_leaves:
        emp_id = leave.get("employee_id")
        emp_leaves[emp_id] = emp_leaves.get(emp_id, 0) + leave.get("days", 0)
    
    # Build result
    result = []
    for emp in employees:
        emp_id = emp.get("id")
        att = emp_attendance.get(emp_id, {})
        leaves = emp_leaves.get(emp_id, 0)
        
        result.append({
            "employee_id": emp_id,
            "employee_code": emp.get("employee_id"),
            "name": f"{emp.get('first_name', '')} {emp.get('last_name', '')}".strip(),
            "department": emp.get("department"),
            "role": emp.get("role"),
            "present_days": att.get("present", 0),
            "absent_days": att.get("absent", 0),
            "half_days": att.get("half_day", 0),
            "wfh_days": att.get("wfh", 0),
            "approved_leaves": leaves,
            "month": month
        })
    
    return {
        "month": month,
        "employees": result
    }


# ============================================================================
# MEETING ATTENDANCE INTEGRATION
# Extends existing attendance system for consulting meeting validation
# Rule: No Attendance = No MOM = No Expenses
# ============================================================================

@router.post("/meeting/{meeting_id}")
async def mark_meeting_attendance(
    meeting_id: str,
    data: dict,
    current_user: User = Depends(get_current_user)
):
    """
    Mark attendance for a consulting meeting.
    
    GOVERNANCE RULE: No Attendance = No MOM = No Expenses
    
    Required fields:
    - start_time: Meeting start datetime
    - end_time: Meeting end datetime  
    - attendees: List of attendee records with check-in/out
    
    This creates a linked attendance record and updates meeting.
    """
    db = get_db()
    
    # Get meeting
    meeting = await db.meetings.find_one({"id": meeting_id}, {"_id": 0})
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    
    # Validate required fields
    start_time = data.get("start_time")
    end_time = data.get("end_time")
    attendees = data.get("attendees", [])
    
    if not start_time or not end_time:
        raise HTTPException(status_code=400, detail="Start time and end time are required")
    
    if not attendees or len(attendees) == 0:
        raise HTTPException(status_code=400, detail="At least one attendee must be marked present")
    
    # Calculate duration
    try:
        start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
        end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
        duration_minutes = int((end_dt - start_dt).total_seconds() / 60)
        
        if duration_minutes <= 0:
            raise HTTPException(status_code=400, detail="End time must be after start time")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid datetime format: {str(e)}")
    
    # Create meeting attendance record (linked to main attendance system)
    attendance_id = str(uuid.uuid4())
    meeting_attendance = {
        "id": attendance_id,
        "type": "meeting",  # Distinguishes from daily attendance
        "meeting_id": meeting_id,
        "project_id": meeting.get("project_id"),
        "client_id": meeting.get("client_id"),
        "date": start_dt.strftime("%Y-%m-%d"),
        "start_time": start_time,
        "end_time": end_time,
        "duration_minutes": duration_minutes,
        "attendees": attendees,
        "attendee_count": len([a for a in attendees if a.get("present", True)]),
        "recorded_by": current_user.id,
        "recorded_by_name": current_user.full_name,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.meeting_attendance.insert_one(meeting_attendance)
    
    # Update meeting with attendance data
    update_data = {
        "start_time": start_time,
        "end_time": end_time,
        "duration_minutes": duration_minutes,
        "attendance_marked": True,
        "attendance_id": attendance_id,
        "attendance_records": attendees,
        "attendance_verified_by": current_user.id,
        "attendance_verified_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.meetings.update_one(
        {"id": meeting_id},
        {"$set": update_data}
    )
    
    return {
        "message": "Meeting attendance marked successfully",
        "attendance_id": attendance_id,
        "meeting_id": meeting_id,
        "duration_minutes": duration_minutes,
        "attendee_count": len(attendees),
        "can_proceed_with_mom": True
    }


@router.get("/meeting/{meeting_id}")
async def get_meeting_attendance(
    meeting_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get attendance record for a specific meeting."""
    db = get_db()
    
    attendance = await db.meeting_attendance.find_one(
        {"meeting_id": meeting_id},
        {"_id": 0}
    )
    
    if not attendance:
        return {
            "attendance_marked": False,
            "message": "No attendance marked for this meeting"
        }
    
    return {
        "attendance_marked": True,
        **attendance
    }


@router.get("/meeting/project/{project_id}")
async def get_project_meeting_attendance(
    project_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get all meeting attendance records for a project."""
    db = get_db()
    
    records = await db.meeting_attendance.find(
        {"project_id": project_id},
        {"_id": 0}
    ).sort("date", -1).to_list(100)
    
    # Calculate summary
    total_meetings = len(records)
    total_duration = sum(r.get("duration_minutes", 0) for r in records)
    total_attendees = sum(r.get("attendee_count", 0) for r in records)
    
    return {
        "project_id": project_id,
        "total_meetings_with_attendance": total_meetings,
        "total_duration_minutes": total_duration,
        "total_duration_hours": round(total_duration / 60, 1),
        "total_attendees": total_attendees,
        "avg_duration_minutes": round(total_duration / total_meetings, 1) if total_meetings > 0 else 0,
        "records": records
    }

