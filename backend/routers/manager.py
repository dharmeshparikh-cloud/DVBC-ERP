"""
Manager Router - Team management endpoints for reporting managers.
Namespace: /manager/*

This router provides team-level data access for managers based on reporting hierarchy.
"""

from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from pydantic import BaseModel

from .deps import get_db, MANAGER_ROLES, clean_mongo_doc
from .auth import get_current_user
from .models import User

router = APIRouter(prefix="/manager", tags=["Manager (Team Data)"])


# ============== Helper Functions ==============

async def get_reportees(user_id: str, employee_id: str) -> List[Dict]:
    """Get direct reportees for a manager"""
    db = get_db()
    
    # Find employees who report to this user
    reportees = await db.employees.find(
        {"$or": [
            {"reporting_manager_id": employee_id},
            {"reporting_manager_id": user_id}
        ]},
        {"_id": 0}
    ).to_list(100)
    
    return reportees


async def get_reportee_user_ids(user_id: str, employee_id: str) -> List[str]:
    """Get user IDs of direct reportees"""
    reportees = await get_reportees(user_id, employee_id)
    return [r.get("user_id") or r.get("id") for r in reportees if r.get("user_id") or r.get("id")]


# ============== Team Overview ==============

@router.get("/team")
async def get_my_team(current_user: User = Depends(get_current_user)):
    """Get list of direct reportees"""
    if current_user.role not in MANAGER_ROLES:
        raise HTTPException(status_code=403, detail="Manager access required")
    
    reportees = await get_reportees(current_user.id, current_user.employee_id)
    
    return {
        "manager_id": current_user.id,
        "team_count": len(reportees),
        "team_members": reportees
    }


@router.get("/team/summary")
async def get_team_summary(current_user: User = Depends(get_current_user)):
    """Get summary statistics for team"""
    if current_user.role not in MANAGER_ROLES:
        raise HTTPException(status_code=403, detail="Manager access required")
    
    db = get_db()
    reportee_ids = await get_reportee_user_ids(current_user.id, current_user.employee_id)
    
    if not reportee_ids:
        return {"message": "No team members found", "summary": {}}
    
    now = datetime.now(timezone.utc)
    month_start = datetime(now.year, now.month, 1, tzinfo=timezone.utc).isoformat()
    
    # Aggregate team stats
    summary = {
        "team_size": len(reportee_ids),
        "on_leave_today": 0,
        "pending_leave_requests": 0,
        "pending_expense_claims": 0,
        "active_projects": 0
    }
    
    # On leave today
    summary["on_leave_today"] = await db.leave_requests.count_documents({
        "employee_id": {"$in": reportee_ids},
        "status": "approved",
        "start_date": {"$lte": now.date().isoformat()},
        "end_date": {"$gte": now.date().isoformat()}
    })
    
    # Pending leave requests
    summary["pending_leave_requests"] = await db.leave_requests.count_documents({
        "employee_id": {"$in": reportee_ids},
        "status": "pending"
    })
    
    # Pending expense claims
    summary["pending_expense_claims"] = await db.expenses.count_documents({
        "employee_id": {"$in": reportee_ids},
        "status": "pending"
    })
    
    return summary


# ============== Team Attendance ==============

@router.get("/team/attendance")
async def get_team_attendance(
    month: Optional[int] = None,
    year: Optional[int] = None,
    current_user: User = Depends(get_current_user)
):
    """Get attendance records for team members"""
    if current_user.role not in MANAGER_ROLES:
        raise HTTPException(status_code=403, detail="Manager access required")
    
    db = get_db()
    reportee_ids = await get_reportee_user_ids(current_user.id, current_user.employee_id)
    
    now = datetime.now(timezone.utc)
    target_month = month or now.month
    target_year = year or now.year
    
    attendance = await db.attendance.find(
        {
            "$or": [
                {"employee_id": {"$in": reportee_ids}},
                {"user_id": {"$in": reportee_ids}}
            ],
            "month": target_month,
            "year": target_year
        },
        {"_id": 0}
    ).to_list(500)
    
    return {
        "month": target_month,
        "year": target_year,
        "records": attendance
    }


# ============== Team Leaves ==============

@router.get("/team/leaves")
async def get_team_leaves(
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get leave requests from team members"""
    if current_user.role not in MANAGER_ROLES:
        raise HTTPException(status_code=403, detail="Manager access required")
    
    db = get_db()
    reportee_ids = await get_reportee_user_ids(current_user.id, current_user.employee_id)
    
    query = {"employee_id": {"$in": reportee_ids}}
    if status:
        query["status"] = status
    
    leaves = await db.leave_requests.find(query, {"_id": 0}).sort("created_at", -1).to_list(200)
    
    return leaves


@router.get("/team/leaves/pending")
async def get_pending_team_leaves(current_user: User = Depends(get_current_user)):
    """Get pending leave requests requiring approval"""
    if current_user.role not in MANAGER_ROLES:
        raise HTTPException(status_code=403, detail="Manager access required")
    
    db = get_db()
    reportee_ids = await get_reportee_user_ids(current_user.id, current_user.employee_id)
    
    pending = await db.leave_requests.find(
        {
            "employee_id": {"$in": reportee_ids},
            "status": "pending"
        },
        {"_id": 0}
    ).sort("created_at", 1).to_list(100)
    
    return pending


# ============== Team Expenses ==============

@router.get("/team/expenses")
async def get_team_expenses(
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get expense claims from team members"""
    if current_user.role not in MANAGER_ROLES:
        raise HTTPException(status_code=403, detail="Manager access required")
    
    db = get_db()
    reportee_ids = await get_reportee_user_ids(current_user.id, current_user.employee_id)
    
    query = {"employee_id": {"$in": reportee_ids}}
    if status:
        query["status"] = status
    
    expenses = await db.expenses.find(query, {"_id": 0}).sort("created_at", -1).to_list(200)
    
    return expenses


# ============== Team Timesheets ==============

@router.get("/team/timesheets")
async def get_team_timesheets(
    month: Optional[int] = None,
    year: Optional[int] = None,
    current_user: User = Depends(get_current_user)
):
    """Get timesheets from team members"""
    if current_user.role not in MANAGER_ROLES:
        raise HTTPException(status_code=403, detail="Manager access required")
    
    db = get_db()
    reportee_ids = await get_reportee_user_ids(current_user.id, current_user.employee_id)
    
    now = datetime.now(timezone.utc)
    
    query = {"employee_id": {"$in": reportee_ids}}
    
    if month and year:
        start_date = datetime(year, month, 1).isoformat()
        if month == 12:
            end_date = datetime(year + 1, 1, 1).isoformat()
        else:
            end_date = datetime(year, month + 1, 1).isoformat()
        query["date"] = {"$gte": start_date, "$lt": end_date}
    
    timesheets = await db.timesheets.find(query, {"_id": 0}).sort("date", -1).to_list(500)
    
    return timesheets


# ============== Team Leads (Sales Managers) ==============

@router.get("/team/leads")
async def get_team_leads(
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get leads assigned to team members (for sales managers)"""
    if current_user.role not in MANAGER_ROLES:
        raise HTTPException(status_code=403, detail="Manager access required")
    
    db = get_db()
    reportee_ids = await get_reportee_user_ids(current_user.id, current_user.employee_id)
    
    # Include manager's own leads
    all_ids = reportee_ids + [current_user.id, current_user.employee_id]
    
    query = {"assigned_to": {"$in": all_ids}}
    if status:
        query["status"] = status
    
    leads = await db.leads.find(query, {"_id": 0}).sort("updated_at", -1).to_list(500)
    
    return leads


@router.get("/team/leads/pipeline")
async def get_team_pipeline(current_user: User = Depends(get_current_user)):
    """Get team's sales pipeline summary"""
    if current_user.role not in MANAGER_ROLES:
        raise HTTPException(status_code=403, detail="Manager access required")
    
    db = get_db()
    reportee_ids = await get_reportee_user_ids(current_user.id, current_user.employee_id)
    all_ids = reportee_ids + [current_user.id, current_user.employee_id]
    
    pipeline = [
        {"$match": {"assigned_to": {"$in": all_ids}}},
        {"$group": {
            "_id": "$status",
            "count": {"$sum": 1},
            "total_value": {"$sum": {"$ifNull": ["$estimated_value", 0]}}
        }}
    ]
    
    results = await db.leads.aggregate(pipeline).to_list(20)
    
    summary = {}
    for r in results:
        summary[r["_id"]] = {
            "count": r["count"],
            "value": r.get("total_value", 0)
        }
    
    return {
        "team_size": len(reportee_ids),
        "stages": summary,
        "total_leads": sum(s["count"] for s in summary.values())
    }


# ============== Team Performance ==============

@router.get("/team/performance")
async def get_team_performance(
    period: str = "month",  # month, quarter, year
    current_user: User = Depends(get_current_user)
):
    """Get team performance metrics"""
    if current_user.role not in MANAGER_ROLES:
        raise HTTPException(status_code=403, detail="Manager access required")
    
    db = get_db()
    reportee_ids = await get_reportee_user_ids(current_user.id, current_user.employee_id)
    reportees = await get_reportees(current_user.id, current_user.employee_id)
    
    now = datetime.now(timezone.utc)
    
    # Calculate date range
    if period == "month":
        start_date = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
    elif period == "quarter":
        quarter_start_month = ((now.month - 1) // 3) * 3 + 1
        start_date = datetime(now.year, quarter_start_month, 1, tzinfo=timezone.utc)
    else:  # year
        start_date = datetime(now.year, 1, 1, tzinfo=timezone.utc)
    
    performance = []
    
    for emp in reportees:
        emp_id = emp.get("user_id") or emp.get("id")
        emp_data = {
            "employee_id": emp.get("employee_id"),
            "name": emp.get("full_name"),
            "role": emp.get("role"),
            "metrics": {}
        }
        
        # Attendance count
        emp_data["metrics"]["attendance_days"] = await db.attendance.count_documents({
            "$or": [{"employee_id": emp_id}, {"employee_id": emp.get("employee_id")}],
            "date": {"$gte": start_date.isoformat()}
        })
        
        # Leads (for sales)
        emp_data["metrics"]["leads_created"] = await db.leads.count_documents({
            "$or": [{"assigned_to": emp_id}, {"created_by": emp_id}],
            "created_at": {"$gte": start_date.isoformat()}
        })
        
        # Leads converted
        emp_data["metrics"]["leads_converted"] = await db.leads.count_documents({
            "$or": [{"assigned_to": emp_id}, {"created_by": emp_id}],
            "status": "closed_won",
            "updated_at": {"$gte": start_date.isoformat()}
        })
        
        performance.append(emp_data)
    
    return {
        "period": period,
        "start_date": start_date.isoformat(),
        "team_performance": performance
    }


# ============== Approvals ==============

@router.get("/approvals/pending")
async def get_pending_approvals(current_user: User = Depends(get_current_user)):
    """Get all items pending manager's approval"""
    if current_user.role not in MANAGER_ROLES:
        raise HTTPException(status_code=403, detail="Manager access required")
    
    db = get_db()
    reportee_ids = await get_reportee_user_ids(current_user.id, current_user.employee_id)
    
    pending = {
        "leave_requests": [],
        "expense_claims": [],
        "timesheet_approvals": []
    }
    
    # Pending leave requests
    pending["leave_requests"] = await db.leave_requests.find(
        {"employee_id": {"$in": reportee_ids}, "status": "pending"},
        {"_id": 0}
    ).to_list(50)
    
    # Pending expenses
    pending["expense_claims"] = await db.expenses.find(
        {"employee_id": {"$in": reportee_ids}, "status": "pending"},
        {"_id": 0}
    ).to_list(50)
    
    # Pending timesheets
    pending["timesheet_approvals"] = await db.timesheets.find(
        {"employee_id": {"$in": reportee_ids}, "status": "submitted"},
        {"_id": 0}
    ).to_list(50)
    
    return pending


# ============== Lead Reassignment ==============

class LeadReassignRequest(BaseModel):
    lead_id: str
    new_assignee_id: str
    reason: Optional[str] = None


@router.post("/leads/reassign")
async def reassign_lead(
    request: LeadReassignRequest,
    current_user: User = Depends(get_current_user)
):
    """Reassign a lead to another team member"""
    if current_user.role not in MANAGER_ROLES:
        raise HTTPException(status_code=403, detail="Manager access required")
    
    db = get_db()
    
    # Verify lead exists
    lead = await db.leads.find_one({"id": request.lead_id}, {"_id": 0})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    # Verify new assignee is in team
    reportee_ids = await get_reportee_user_ids(current_user.id, current_user.employee_id)
    if request.new_assignee_id not in reportee_ids and request.new_assignee_id != current_user.id:
        raise HTTPException(status_code=400, detail="Can only reassign to team members")
    
    # Update lead
    old_assignee = lead.get("assigned_to")
    await db.leads.update_one(
        {"id": request.lead_id},
        {"$set": {
            "assigned_to": request.new_assignee_id,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "updated_by": current_user.id
        }}
    )
    
    # Log the change
    await db.audit_logs.insert_one({
        "id": str(__import__("uuid").uuid4()),
        "action": "lead_reassign",
        "entity_type": "lead",
        "entity_id": request.lead_id,
        "changes": {
            "old_assignee": old_assignee,
            "new_assignee": request.new_assignee_id,
            "reason": request.reason
        },
        "performed_by": current_user.id,
        "performed_at": datetime.now(timezone.utc).isoformat()
    })
    
    return {"status": "success", "message": "Lead reassigned successfully"}
