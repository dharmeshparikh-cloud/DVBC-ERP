"""
Dashboard Stats Router - Dashboard statistics for Admin, Sales, HR, Consulting
"""

from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone, timedelta
from typing import List, Optional

from .models import User, UserRole, CONSULTING_ROLES
from .deps import get_db
from .auth import get_current_user

router = APIRouter(prefix="/stats", tags=["Dashboard Stats"])


@router.get("/dashboard")
async def get_dashboard_stats(current_user: User = Depends(get_current_user)):
    """Get main dashboard statistics."""
    db = get_db()
    
    leads_count = await db.leads.count_documents({})
    projects_count = await db.projects.count_documents({})
    active_projects = await db.projects.count_documents({"status": "active"})
    meetings_count = await db.meetings.count_documents({})
    
    recent_leads = await db.leads.find({}, {"_id": 0}).sort("created_at", -1).limit(5).to_list(5)
    
    return {
        "leads_count": leads_count,
        "projects_count": projects_count,
        "active_projects": active_projects,
        "meetings_count": meetings_count,
        "recent_leads": recent_leads
    }


@router.get("/sales-dashboard")
async def get_sales_dashboard_stats(current_user: User = Depends(get_current_user)):
    """Get sales dashboard statistics."""
    db = get_db()
    
    # Lead statistics by status
    lead_stats = await db.leads.aggregate([
        {"$group": {"_id": "$status", "count": {"$sum": 1}}}
    ]).to_list(100)
    
    # Recent meetings
    recent_meetings = await db.meetings.find(
        {"type": "sales"},
        {"_id": 0}
    ).sort("meeting_date", -1).limit(5).to_list(5)
    
    # Agreements stats
    agreements_pending = await db.agreements.count_documents({"status": "pending"})
    agreements_approved = await db.agreements.count_documents({"status": "approved"})
    
    # SOW stats
    sow_total = await db.sow.count_documents({})
    
    return {
        "lead_stats": {s['_id']: s['count'] for s in lead_stats},
        "recent_meetings": recent_meetings,
        "agreements": {
            "pending": agreements_pending,
            "approved": agreements_approved
        },
        "sow_total": sow_total
    }


async def get_team_member_ids(manager_id: str) -> List[str]:
    """Get all team member IDs for a reporting manager."""
    db = get_db()
    team_members = await db.users.find(
        {"reporting_manager_id": manager_id},
        {"_id": 0, "id": 1}
    ).to_list(1000)
    return [m["id"] for m in team_members]


@router.get("/sales-dashboard-enhanced")
async def get_enhanced_sales_dashboard_stats(
    period: str = "month",
    current_user: User = Depends(get_current_user)
):
    """Get enhanced sales dashboard with team performance metrics."""
    db = get_db()
    
    # Determine date range
    now = datetime.now(timezone.utc)
    if period == "week":
        start_date = now - timedelta(days=7)
    elif period == "quarter":
        start_date = now - timedelta(days=90)
    elif period == "year":
        start_date = now - timedelta(days=365)
    else:  # month
        start_date = now - timedelta(days=30)
    
    start_str = start_date.isoformat()
    
    # Determine user scope (team or self)
    user_ids = [current_user.id]
    if current_user.role in ["admin", "manager", "principal_consultant"]:
        # Get all team members
        team_ids = await get_team_member_ids(current_user.id)
        user_ids.extend(team_ids)
    
    # Lead statistics
    lead_stats = await db.leads.aggregate([
        {"$match": {"created_at": {"$gte": start_str}}},
        {"$group": {
            "_id": "$status",
            "count": {"$sum": 1}
        }}
    ]).to_list(100)
    
    # Meeting statistics
    meeting_stats = await db.meetings.aggregate([
        {"$match": {
            "type": "sales",
            "meeting_date": {"$gte": start_str}
        }},
        {"$group": {
            "_id": "$mode",
            "count": {"$sum": 1}
        }}
    ]).to_list(100)
    
    # Deal pipeline value
    deals_pipeline = await db.agreements.aggregate([
        {"$match": {"status": {"$in": ["pending", "approved"]}}},
        {"$group": {
            "_id": "$status",
            "total_value": {"$sum": "$total_value"},
            "count": {"$sum": 1}
        }}
    ]).to_list(100)
    
    # Team performance (if manager)
    team_performance = []
    if current_user.role in ["admin", "manager", "principal_consultant"]:
        team_members = await db.users.find(
            {"reporting_manager_id": current_user.id},
            {"_id": 0, "id": 1, "full_name": 1, "email": 1}
        ).to_list(100)
        
        for member in team_members:
            member_leads = await db.leads.count_documents({
                "created_by": member["id"],
                "created_at": {"$gte": start_str}
            })
            member_meetings = await db.meetings.count_documents({
                "created_by": member["id"],
                "type": "sales",
                "meeting_date": {"$gte": start_str}
            })
            
            team_performance.append({
                "id": member["id"],
                "name": member["full_name"],
                "leads_created": member_leads,
                "meetings_held": member_meetings
            })
    
    return {
        "period": period,
        "lead_stats": {s['_id']: s['count'] for s in lead_stats},
        "meeting_stats": {s['_id']: s['count'] for s in meeting_stats},
        "deals_pipeline": deals_pipeline,
        "team_performance": team_performance,
        "total_leads": sum(s['count'] for s in lead_stats),
        "total_meetings": sum(s['count'] for s in meeting_stats)
    }


@router.get("/hr-dashboard")
async def get_hr_dashboard_stats(current_user: User = Depends(get_current_user)):
    """Get HR dashboard statistics."""
    db = get_db()
    
    # Verify HR role
    if current_user.role not in ["admin", "hr_manager", "hr_executive"]:
        raise HTTPException(status_code=403, detail="HR access required")
    
    # Employee statistics
    total_employees = await db.employees.count_documents({})
    active_employees = await db.employees.count_documents({"status": "active"})
    
    # Leave statistics
    pending_leaves = await db.leave_requests.count_documents({"status": "pending"})
    
    # Attendance today
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    attendance_today = await db.attendance.count_documents({"date": today})
    
    # Pending approvals
    pending_bank_changes = await db.bank_change_requests.count_documents({"status": "pending_hr"})
    pending_ctc = await db.ctc_structures.count_documents({"status": "pending"})
    
    # Recent joiners (last 30 days)
    thirty_days_ago = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    recent_joiners = await db.employees.count_documents({
        "date_of_joining": {"$gte": thirty_days_ago}
    })
    
    return {
        "employees": {
            "total": total_employees,
            "active": active_employees,
            "recent_joiners": recent_joiners
        },
        "leaves": {
            "pending": pending_leaves
        },
        "attendance": {
            "today_count": attendance_today
        },
        "approvals": {
            "bank_changes": pending_bank_changes,
            "ctc_pending": pending_ctc
        }
    }


@router.get("/consulting-dashboard")
async def get_consulting_dashboard_stats(current_user: User = Depends(get_current_user)):
    """Get consulting dashboard statistics."""
    db = get_db()
    
    # Active projects
    active_projects = await db.projects.count_documents({"status": "active"})
    
    # My projects (for consultants)
    my_projects = 0
    if current_user.role in CONSULTING_ROLES:
        my_projects = await db.projects.count_documents({
            "assigned_consultants": current_user.id,
            "status": "active"
        })
    
    # Meetings this week
    week_start = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    consulting_meetings = await db.meetings.count_documents({
        "type": "consulting",
        "meeting_date": {"$gte": week_start}
    })
    
    # Pending kickoff requests
    pending_kickoffs = await db.kickoff_requests.count_documents({"status": "pending"})
    
    # SOW items by status
    sow_status_stats = await db.sow.aggregate([
        {"$unwind": "$items"},
        {"$group": {
            "_id": "$items.status",
            "count": {"$sum": 1}
        }}
    ]).to_list(100)
    
    return {
        "active_projects": active_projects,
        "my_projects": my_projects,
        "consulting_meetings_this_week": consulting_meetings,
        "pending_kickoffs": pending_kickoffs,
        "sow_item_status": {s['_id']: s['count'] for s in sow_status_stats if s['_id']}
    }
