"""
Attendance Router - Check-in/out, Attendance Management, Approvals
"""

from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone, timedelta
from typing import Optional, List
import uuid

from .models import User, UserRole
from .deps import get_db
from .auth import get_current_user

router = APIRouter(prefix="/attendance", tags=["Attendance"])


@router.post("")
async def record_attendance(data: dict, current_user: User = Depends(get_current_user)):
    """Record attendance entry (HR/Admin manual entry)."""
    db = get_db()
    
    if current_user.role not in ["admin", "hr_manager", "hr_executive"]:
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
    
    if current_user.role not in ["admin", "hr_manager", "hr_executive"]:
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
    if current_user.role not in ["admin", "hr_manager", "hr_executive", "project_manager"]:
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
    
    if current_user.role not in ["admin", "hr_manager", "hr_executive"]:
        raise HTTPException(status_code=403, detail="Only HR can view attendance analytics")
    
    # Default to last 30 days
    if not date_from:
        date_from = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d")
    if not date_to:
        date_to = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
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
    
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    month_start = datetime.now(timezone.utc).strftime("%Y-%m-01")
    
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
DEFAULT_ATTENDANCE_POLICY = {
    "working_days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"],
    "non_consulting": {
        "check_in": "10:00",
        "check_out": "19:00"  # 7 PM
    },
    "consulting": {
        "check_in": "10:30",
        "check_out": "19:30"  # 7:30 PM
    },
    "grace_period_minutes": 30,
    "grace_days_per_month": 3,
    "late_penalty_amount": 100  # Rs. 100 penalty
}

# Keep ATTENDANCE_POLICY for backward compatibility
ATTENDANCE_POLICY = DEFAULT_ATTENDANCE_POLICY

CONSULTING_ROLES = ["consultant", "lean_consultant", "lead_consultant", "senior_consultant", "principal_consultant"]


async def get_employee_policy(db, employee_id: str, employee_role: str = None) -> dict:
    """
    Get attendance policy for an employee.
    First checks for custom policy, then falls back to default.
    """
    # Check for employee-specific custom policy
    custom_policy = await db.employee_attendance_policies.find_one(
        {"employee_id": employee_id, "is_active": True},
        {"_id": 0}
    )
    
    if custom_policy:
        return {
            "check_in": custom_policy.get("check_in", DEFAULT_ATTENDANCE_POLICY["non_consulting"]["check_in"]),
            "check_out": custom_policy.get("check_out", DEFAULT_ATTENDANCE_POLICY["non_consulting"]["check_out"]),
            "grace_period_minutes": custom_policy.get("grace_period_minutes", DEFAULT_ATTENDANCE_POLICY["grace_period_minutes"]),
            "grace_days_per_month": custom_policy.get("grace_days_per_month", DEFAULT_ATTENDANCE_POLICY["grace_days_per_month"]),
            "is_custom": True,
            "reason": custom_policy.get("reason", "")
        }
    
    # Fall back to role-based policy
    is_consulting = employee_role in CONSULTING_ROLES if employee_role else False
    base_policy = DEFAULT_ATTENDANCE_POLICY["consulting" if is_consulting else "non_consulting"]
    
    return {
        "check_in": base_policy["check_in"],
        "check_out": base_policy["check_out"],
        "grace_period_minutes": DEFAULT_ATTENDANCE_POLICY["grace_period_minutes"],
        "grace_days_per_month": DEFAULT_ATTENDANCE_POLICY["grace_days_per_month"],
        "is_custom": False,
        "reason": ""
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
    """Get current attendance policy configuration"""
    db = get_db()
    
    # Get custom policies count
    custom_count = await db.employee_attendance_policies.count_documents({"is_active": True})
    
    return {
        "policy": DEFAULT_ATTENDANCE_POLICY,
        "consulting_roles": CONSULTING_ROLES,
        "custom_policies_count": custom_count
    }


@router.get("/policy/employee/{employee_id}")
async def get_employee_attendance_policy(employee_id: str, current_user: User = Depends(get_current_user)):
    """Get attendance policy for a specific employee"""
    db = get_db()
    
    if current_user.role not in ["admin", "hr_manager", "hr_executive"]:
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
    
    if current_user.role not in ["admin", "hr_manager", "hr_executive"]:
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
    
    if current_user.role not in ["admin", "hr_manager"]:
        raise HTTPException(status_code=403, detail="Only HR Manager/Admin can set custom policies")
    
    employee_id = data.get("employee_id")
    if not employee_id:
        raise HTTPException(status_code=400, detail="employee_id required")
    
    # Verify employee exists
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0, "id": 1, "employee_id": 1, "first_name": 1, "last_name": 1})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    now = datetime.now(timezone.utc).isoformat()
    
    policy_data = {
        "employee_id": employee_id,
        "employee_code": employee.get("employee_id"),
        "employee_name": f"{employee.get('first_name', '')} {employee.get('last_name', '')}".strip(),
        "check_in": data.get("check_in", DEFAULT_ATTENDANCE_POLICY["non_consulting"]["check_in"]),
        "check_out": data.get("check_out", DEFAULT_ATTENDANCE_POLICY["non_consulting"]["check_out"]),
        "grace_period_minutes": data.get("grace_period_minutes", DEFAULT_ATTENDANCE_POLICY["grace_period_minutes"]),
        "grace_days_per_month": data.get("grace_days_per_month", DEFAULT_ATTENDANCE_POLICY["grace_days_per_month"]),
        "reason": data.get("reason", ""),
        "effective_from": data.get("effective_from", now[:10]),
        "effective_to": data.get("effective_to"),
        "is_active": True,
        "created_by": current_user.id,
        "created_by_name": current_user.full_name,
        "updated_at": now
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
    
    return {
        "message": f"Custom policy {action} for {policy_data['employee_name']}",
        "policy": policy_data
    }


@router.delete("/policy/custom/{employee_id}")
async def delete_custom_policy(employee_id: str, current_user: User = Depends(get_current_user)):
    """Delete custom attendance policy for an employee (reverts to default)"""
    db = get_db()
    
    if current_user.role not in ["admin", "hr_manager"]:
        raise HTTPException(status_code=403, detail="Only HR Manager/Admin can delete custom policies")
    
    result = await db.employee_attendance_policies.delete_one({"employee_id": employee_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="No custom policy found for this employee")
    
    return {"message": "Custom policy deleted, employee reverted to default policy"}


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
    
    if current_user.role not in ["admin", "hr_manager", "hr_executive"]:
        raise HTTPException(status_code=403, detail="Only HR can auto-validate attendance")
    
    month = data.get("month")  # Format: YYYY-MM
    if not month:
        month = datetime.now(timezone.utc).strftime("%Y-%m")
    
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
        
        # Get employee-specific or role-based policy
        emp_policy = await get_employee_policy(db, emp_id, role)
        is_consulting = role in CONSULTING_ROLES
        policy = {
            "check_in": emp_policy["check_in"],
            "check_out": emp_policy["check_out"]
        }
        grace_minutes = emp_policy.get("grace_period_minutes", DEFAULT_ATTENDANCE_POLICY["grace_period_minutes"])
        grace_days = emp_policy.get("grace_days_per_month", DEFAULT_ATTENDANCE_POLICY["grace_days_per_month"])
        
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
            
            # Skip non-working days
            if day_name not in DEFAULT_ATTENDANCE_POLICY["working_days"]:
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
                    # Check if within 30 min grace
                    if is_within_grace(check_in, policy["check_in"], 30):
                        is_late = True
                        late_count += 1
                    else:
                        # More than 30 min late - auto penalty
                        is_late = True
                        late_count += 1
            
            if check_out:
                if not is_within_grace(check_out, policy["check_out"], 0):
                    if is_within_grace(check_out, policy["check_out"], 30):
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
        
        # Calculate penalties (beyond 3 grace days)
        total_grace_used = len(grace_violations)
        penalty_days = max(0, total_grace_used - ATTENDANCE_POLICY["grace_days_per_month"])
        penalty_amount = penalty_days * ATTENDANCE_POLICY["late_penalty_amount"]
        
        if penalty_days > 0:
            penalties = grace_violations[ATTENDANCE_POLICY["grace_days_per_month"]:]
        
        results.append({
            "employee_id": emp_id,
            "employee_code": emp_code,
            "name": emp_name,
            "role": role,
            "is_consulting": is_consulting,
            "present_days": present_days,
            "absent_days": absent_days,
            "leave_days": leave_days,
            "grace_days_used": min(total_grace_used, ATTENDANCE_POLICY["grace_days_per_month"]),
            "grace_violations": grace_violations,
            "penalty_days": penalty_days,
            "pending_penalty_amount": penalty_amount,
            "penalty_details": penalties,
            "status": "clean" if penalty_amount == 0 else "penalty_pending"
        })
    
    return {
        "month": month,
        "policy": ATTENDANCE_POLICY,
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
    HR approves and applies attendance penalties to payroll.
    Adds Rs.100 penalty per violation day beyond 3 grace days.
    """
    db = get_db()
    
    if current_user.role not in ["admin", "hr_manager"]:
        raise HTTPException(status_code=403, detail="Only HR Manager/Admin can apply penalties")
    
    month = data.get("month")
    employee_penalties = data.get("penalties", [])  # [{employee_id, penalty_amount, penalty_days}]
    
    if not month or not employee_penalties:
        raise HTTPException(status_code=400, detail="Month and penalties required")
    
    now = datetime.now(timezone.utc).isoformat()
    applied_count = 0
    
    for p in employee_penalties:
        emp_id = p.get("employee_id")
        penalty_amount = p.get("penalty_amount", 0)
        penalty_days = p.get("penalty_days", 0)
        
        if penalty_amount <= 0:
            continue
        
        # Update payroll inputs with penalty
        await db.payroll_inputs.update_one(
            {"employee_id": emp_id, "month": month},
            {"$inc": {"penalty": penalty_amount},
             "$set": {
                 "attendance_penalty_applied": True,
                 "attendance_penalty_days": penalty_days,
                 "attendance_penalty_approved_by": current_user.id,
                 "attendance_penalty_approved_at": now
             }},
            upsert=True
        )
        
        # Create penalty record for audit
        await db.attendance_penalties.insert_one({
            "id": str(uuid.uuid4()),
            "employee_id": emp_id,
            "month": month,
            "penalty_days": penalty_days,
            "penalty_amount": penalty_amount,
            "approved_by": current_user.id,
            "approved_by_name": current_user.full_name,
            "created_at": now
        })
        
        applied_count += 1
    
    return {
        "message": f"Applied penalties for {applied_count} employees",
        "month": month,
        "applied_count": applied_count
    }


# ==================== HR FUNCTIONS FOR BULK LEAVE/ATTENDANCE ====================

@router.post("/hr/bulk-leave-credit")
async def hr_bulk_leave_credit(data: dict, current_user: User = Depends(get_current_user)):
    """
    HR function to credit leave balance to all employees (e.g., annual reset, bonus leaves)
    """
    db = get_db()
    
    if current_user.role not in ["admin", "hr_manager"]:
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
    
    if current_user.role not in ["admin", "hr_manager", "hr_executive"]:
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
    
    if current_user.role not in ["admin", "hr_manager", "hr_executive"]:
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
    
    if current_user.role not in ["admin", "hr_manager", "hr_executive"]:
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
