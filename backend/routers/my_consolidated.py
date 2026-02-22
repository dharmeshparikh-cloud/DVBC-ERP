"""
Consolidated My Router - All personal/self-service endpoints in one place.
Namespace: /my/*

This router aggregates all personal data endpoints for a unified API experience.
"""

from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from pydantic import BaseModel

from .deps import get_db, clean_mongo_doc
from .auth import get_current_user
from .models import User

router = APIRouter(prefix="/my", tags=["My (Self-Service)"])


# ============== Profile & Details ==============

@router.get("/profile")
async def get_my_profile(current_user: User = Depends(get_current_user)):
    """Get current user's full profile"""
    db = get_db()
    
    # Get user record
    user = await db.users.find_one({"id": current_user.id}, {"_id": 0, "hashed_password": 0})
    
    # Get employee record
    employee = await db.employees.find_one(
        {"$or": [{"user_id": current_user.id}, {"employee_id": current_user.employee_id}]},
        {"_id": 0}
    )
    
    return {
        "user": user,
        "employee": employee,
        "role": current_user.role,
        "employee_id": current_user.employee_id
    }


@router.get("/details")
async def get_my_details(current_user: User = Depends(get_current_user)):
    """Get my personal details including bank info"""
    db = get_db()
    
    employee = await db.employees.find_one(
        {"$or": [{"user_id": current_user.id}, {"employee_id": current_user.employee_id}]},
        {"_id": 0}
    )
    
    if not employee:
        return {"message": "Employee record not found", "user_id": current_user.id}
    
    return clean_mongo_doc(employee)


# ============== Attendance ==============

@router.get("/attendance")
async def get_my_attendance(
    month: Optional[int] = None,
    year: Optional[int] = None,
    current_user: User = Depends(get_current_user)
):
    """Get my attendance records"""
    db = get_db()
    
    now = datetime.now(timezone.utc)
    target_month = month or now.month
    target_year = year or now.year
    
    # Query by user_id or employee_id
    query = {
        "$or": [
            {"employee_id": current_user.id},
            {"employee_id": current_user.employee_id},
            {"user_id": current_user.id}
        ],
        "month": target_month,
        "year": target_year
    }
    
    attendance = await db.attendance.find(query, {"_id": 0}).to_list(100)
    
    return {
        "month": target_month,
        "year": target_year,
        "records": attendance
    }


# ============== Leaves ==============

@router.get("/leaves")
async def get_my_leaves(
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get my leave requests"""
    db = get_db()
    
    query = {
        "$or": [
            {"employee_id": current_user.id},
            {"employee_id": current_user.employee_id},
            {"user_id": current_user.id}
        ]
    }
    
    if status:
        query["status"] = status
    
    leaves = await db.leave_requests.find(query, {"_id": 0}).sort("created_at", -1).to_list(100)
    
    return leaves


@router.get("/leave-balance")
async def get_my_leave_balance(current_user: User = Depends(get_current_user)):
    """Get my current leave balance"""
    db = get_db()
    
    balance = await db.leave_balances.find_one(
        {"$or": [
            {"employee_id": current_user.id},
            {"employee_id": current_user.employee_id}
        ]},
        {"_id": 0}
    )
    
    if not balance:
        # Return default balance
        balance = {
            "casual_leave": {"total": 12, "used": 0, "available": 12},
            "sick_leave": {"total": 6, "used": 0, "available": 6},
            "earned_leave": {"total": 0, "used": 0, "available": 0}
        }
    
    return balance


# ============== Salary & Expenses ==============

@router.get("/salary-slips")
async def get_my_salary_slips(
    year: Optional[int] = None,
    current_user: User = Depends(get_current_user)
):
    """Get my salary slips"""
    db = get_db()
    
    query = {
        "$or": [
            {"employee_id": current_user.id},
            {"employee_id": current_user.employee_id}
        ]
    }
    
    if year:
        query["year"] = year
    
    slips = await db.salary_slips.find(query, {"_id": 0}).sort([("year", -1), ("month", -1)]).to_list(100)
    
    return slips


@router.get("/expenses")
async def get_my_expenses(
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get my expense claims"""
    db = get_db()
    
    query = {
        "$or": [
            {"employee_id": current_user.id},
            {"employee_id": current_user.employee_id},
            {"submitted_by": current_user.id}
        ]
    }
    
    if status:
        query["status"] = status
    
    expenses = await db.expenses.find(query, {"_id": 0}).sort("created_at", -1).to_list(100)
    
    return expenses


# ============== Projects & Timesheets ==============

@router.get("/projects")
async def get_my_projects(current_user: User = Depends(get_current_user)):
    """Get projects assigned to me"""
    db = get_db()
    
    # Get projects where user is a team member
    projects = await db.projects.find(
        {"$or": [
            {"team_members": {"$elemMatch": {"user_id": current_user.id}}},
            {"team_members": {"$elemMatch": {"employee_id": current_user.employee_id}}},
            {"consultant_id": current_user.id},
            {"created_by": current_user.id}
        ]},
        {"_id": 0}
    ).to_list(100)
    
    return projects


@router.get("/timesheets")
async def get_my_timesheets(
    month: Optional[int] = None,
    year: Optional[int] = None,
    current_user: User = Depends(get_current_user)
):
    """Get my timesheets"""
    db = get_db()
    
    now = datetime.now(timezone.utc)
    
    query = {
        "$or": [
            {"employee_id": current_user.id},
            {"employee_id": current_user.employee_id},
            {"user_id": current_user.id}
        ]
    }
    
    if month and year:
        start_date = datetime(year, month, 1).isoformat()
        if month == 12:
            end_date = datetime(year + 1, 1, 1).isoformat()
        else:
            end_date = datetime(year, month + 1, 1).isoformat()
        query["date"] = {"$gte": start_date, "$lt": end_date}
    
    timesheets = await db.timesheets.find(query, {"_id": 0}).sort("date", -1).to_list(200)
    
    return timesheets


# ============== Approvals & Requests ==============

@router.get("/approvals")
async def get_my_approval_requests(
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get approval requests submitted by me"""
    db = get_db()
    
    query = {
        "$or": [
            {"requested_by": current_user.id},
            {"submitted_by": current_user.id}
        ]
    }
    
    if status:
        query["status"] = status
    
    approvals = await db.approval_requests.find(query, {"_id": 0}).sort("created_at", -1).to_list(100)
    
    return approvals


@router.get("/pending-actions")
async def get_my_pending_actions(current_user: User = Depends(get_current_user)):
    """Get items requiring my action"""
    db = get_db()
    
    pending = {
        "leave_requests": 0,
        "expense_approvals": 0,
        "timesheet_approvals": 0,
        "document_reviews": 0
    }
    
    # Count pending items assigned to this user for approval
    if current_user.role in ["admin", "manager", "hr_manager", "principal_consultant"]:
        pending["leave_requests"] = await db.leave_requests.count_documents({
            "status": "pending",
            "approver_id": current_user.id
        })
        
        pending["expense_approvals"] = await db.expenses.count_documents({
            "status": "pending",
            "approver_id": current_user.id
        })
    
    return pending


# ============== Sales Funnel (For Sales Users) ==============

@router.get("/leads")
async def get_my_leads(
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get leads assigned to me"""
    db = get_db()
    
    query = {
        "$or": [
            {"assigned_to": current_user.id},
            {"assigned_to": current_user.employee_id},
            {"created_by": current_user.id}
        ]
    }
    
    if status:
        query["status"] = status
    
    leads = await db.leads.find(query, {"_id": 0}).sort("updated_at", -1).to_list(200)
    
    return leads


@router.get("/funnel-summary")
async def get_my_funnel_summary(current_user: User = Depends(get_current_user)):
    """Get my sales funnel summary"""
    db = get_db()
    
    # Get my leads by stage
    pipeline = [
        {"$match": {
            "$or": [
                {"assigned_to": current_user.id},
                {"assigned_to": current_user.employee_id}
            ]
        }},
        {"$group": {
            "_id": "$status",
            "count": {"$sum": 1},
            "total_value": {"$sum": "$estimated_value"}
        }}
    ]
    
    results = await db.leads.aggregate(pipeline).to_list(20)
    
    summary = {r["_id"]: {"count": r["count"], "value": r.get("total_value", 0)} for r in results}
    
    return {
        "user_id": current_user.id,
        "stages": summary,
        "total_leads": sum(s["count"] for s in summary.values())
    }


# ============== Dashboard Stats ==============

@router.get("/dashboard-stats")
async def get_my_dashboard_stats(current_user: User = Depends(get_current_user)):
    """Get personalized dashboard statistics"""
    db = get_db()
    
    now = datetime.now(timezone.utc)
    month_start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
    
    stats = {
        "attendance_this_month": 0,
        "leaves_taken": 0,
        "pending_requests": 0,
        "active_projects": 0,
        "leads_count": 0
    }
    
    # Attendance count
    stats["attendance_this_month"] = await db.attendance.count_documents({
        "$or": [{"employee_id": current_user.id}, {"employee_id": current_user.employee_id}],
        "date": {"$gte": month_start.isoformat()}
    })
    
    # Leaves taken this year
    stats["leaves_taken"] = await db.leave_requests.count_documents({
        "$or": [{"employee_id": current_user.id}, {"employee_id": current_user.employee_id}],
        "status": "approved",
        "start_date": {"$gte": f"{now.year}-01-01"}
    })
    
    # Active projects
    stats["active_projects"] = await db.projects.count_documents({
        "$or": [
            {"team_members.user_id": current_user.id},
            {"consultant_id": current_user.id}
        ],
        "status": {"$in": ["active", "in_progress"]}
    })
    
    # My leads (for sales users)
    stats["leads_count"] = await db.leads.count_documents({
        "$or": [{"assigned_to": current_user.id}, {"assigned_to": current_user.employee_id}]
    })
    
    return stats


# ============== Payments ==============

@router.get("/payments")
async def get_my_payments(current_user: User = Depends(get_current_user)):
    """Get payments related to my projects"""
    db = get_db()
    
    # Get my projects first
    my_projects = await db.projects.find(
        {"$or": [
            {"team_members.user_id": current_user.id},
            {"consultant_id": current_user.id}
        ]},
        {"id": 1, "_id": 0}
    ).to_list(100)
    
    project_ids = [p["id"] for p in my_projects]
    
    if not project_ids:
        return []
    
    payments = await db.project_payments.find(
        {"project_id": {"$in": project_ids}},
        {"_id": 0}
    ).sort("payment_date", -1).to_list(100)
    
    return payments


# ============== Permissions ==============

@router.get("/permissions")
async def get_my_permissions(current_user: User = Depends(get_current_user)):
    """Get my effective permissions"""
    db = get_db()
    
    # Get employee-specific overrides
    override = await db.employee_permissions.find_one(
        {"employee_id": current_user.employee_id},
        {"_id": 0}
    )
    
    return {
        "role": current_user.role,
        "employee_id": current_user.employee_id,
        "has_custom_permissions": override is not None,
        "overrides": override
    }


# ============== Department Access ==============

@router.get("/department-access")
async def get_my_department_access(current_user: User = Depends(get_current_user)):
    """Get my department access configuration"""
    db = get_db()
    
    # Get employee's primary department
    employee = await db.employees.find_one(
        {"$or": [{"user_id": current_user.id}, {"employee_id": current_user.employee_id}]},
        {"_id": 0, "department": 1}
    )
    
    primary_dept = employee.get("department") if employee else None
    
    # Get additional department access
    access = await db.department_access.find_one(
        {"employee_id": current_user.employee_id},
        {"_id": 0}
    )
    
    return {
        "primary_department": primary_dept,
        "additional_departments": access.get("additional_departments", []) if access else [],
        "can_view": access.get("can_view", []) if access else [],
        "can_edit": access.get("can_edit", []) if access else []
    }


# ============== Travel ==============

@router.get("/travel")
async def get_my_travel_claims(
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get my travel reimbursement claims"""
    db = get_db()
    
    query = {
        "$or": [
            {"employee_id": current_user.id},
            {"employee_id": current_user.employee_id},
            {"submitted_by": current_user.id}
        ]
    }
    
    if status:
        query["status"] = status
    
    claims = await db.travel_claims.find(query, {"_id": 0}).sort("created_at", -1).to_list(50)
    
    return claims


# ============== Scorecard ==============

@router.get("/scorecard")
async def get_my_scorecard(current_user: User = Depends(get_current_user)):
    """Get my performance scorecard"""
    db = get_db()
    
    scorecard = await db.employee_scorecards.find_one(
        {"$or": [
            {"employee_id": current_user.id},
            {"employee_id": current_user.employee_id}
        ]},
        {"_id": 0}
    )
    
    if not scorecard:
        # Return empty scorecard structure
        return {
            "employee_id": current_user.employee_id,
            "metrics": [],
            "overall_score": None,
            "last_updated": None
        }
    
    return scorecard
