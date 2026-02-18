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
    """Get attendance summary for a month."""
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
    
    query = {"date": {"$gte": start_date, "$lt": end_date}}
    
    if employee_id:
        query["employee_id"] = employee_id
    
    # Count by status
    pipeline = [
        {"$match": query},
        {"$group": {
            "_id": "$status",
            "count": {"$sum": 1}
        }}
    ]
    
    results = await db.attendance.aggregate(pipeline).to_list(20)
    
    summary = {r["_id"]: r["count"] for r in results if r["_id"]}
    summary["total"] = sum(summary.values())
    
    return summary


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
        "by_location": {l["_id"]: l["count"] for l in location_stats if l["_id"]}
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
