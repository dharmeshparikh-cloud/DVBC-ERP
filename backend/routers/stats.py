"""
Dashboard Stats Router - Dashboard statistics for Admin, Sales, HR, Consulting
Replaces legacy stats endpoints from server.py

RBAC MIGRATION: December 2025
- All role checks now use database-driven RBAC via get_role_group()
- Numeric role levels used for hierarchy-based access
- Team hierarchy filters for managers

PERFORMANCE OPTIMIZATION: December 2025
- Added in-memory caching for stats (5 min TTL)
- Cache invalidation on data changes
"""

from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone, timedelta
from typing import List, Optional
import logging

from .models import User, LeadStatus
from .deps import get_db, get_role_group, has_role
from .auth import get_current_user
from .rbac_service import rbac

# Performance caching
import sys
sys.path.insert(0, '/app/backend')
from services.cache_service import cache, stats_key, PerformanceCache

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/stats", tags=["Dashboard Stats"])


# ==================== HELPER FUNCTIONS ====================

def get_all_data_roles() -> List[str]:
    """Get roles that can see all company data (database-driven)."""
    return get_role_group("ALL_DATA_ACCESS_ROLES", fail_closed=False) or ["admin", "hr_manager", "principal_consultant"]


def get_manager_roles() -> List[str]:
    """Get manager-level roles (database-driven)."""
    return get_role_group("MANAGER_ROLES", fail_closed=False) or ["admin", "manager", "sr_manager", "sales_manager", "hr_manager", "principal_consultant"]


def can_see_all_data(user: User) -> bool:
    """Check if user role has access to all company data using RBAC."""
    return has_role(user.role, get_all_data_roles())


def is_manager_or_above(user: User) -> bool:
    """Check if user is manager level or above using RBAC level."""
    role_data = rbac.get_role(user.role)
    if role_data:
        return role_data.get("level", 0) >= 70
    return has_role(user.role, get_manager_roles())


@router.get("/dashboard")
async def get_dashboard_stats(current_user: User = Depends(get_current_user)):
    """
    Get main dashboard statistics - matches frontend expected format.
    
    Access Control (RBAC-driven):
    - ALL_DATA_ACCESS_ROLES: See all company data
    - MANAGER_ROLES: See team data (direct reports)
    - Others: See only own data
    """
    db = get_db()
    
    # Build query based on RBAC role hierarchy
    query = {}
    project_query = {}
    
    if can_see_all_data(current_user):
        # Admin, HR Manager, Principal Consultant see all data
        pass  # Empty query = all data
    elif is_manager_or_above(current_user):
        # Managers see their team's data
        team_ids = await get_team_member_ids(current_user.id)
        team_ids.append(current_user.id)
        query['$or'] = [
            {"assigned_to": {"$in": team_ids}},
            {"created_by": {"$in": team_ids}}
        ]
        project_query['$or'] = [
            {"assigned_team": {"$in": team_ids}},
            {"created_by": {"$in": team_ids}},
            {"assigned_consultants": {"$in": team_ids}}
        ]
    else:
        # Regular users see only their own data
        query['$or'] = [{"assigned_to": current_user.id}, {"created_by": current_user.id}]
        project_query['$or'] = [
            {"assigned_team": current_user.id},
            {"created_by": current_user.id},
            {"assigned_consultants": current_user.id}
        ]
    
    total_leads = await db.leads.count_documents(query)
    new_leads = await db.leads.count_documents({**query, "status": LeadStatus.NEW})
    qualified_leads = await db.leads.count_documents({**query, "status": LeadStatus.QUALIFIED})
    closed_deals = await db.leads.count_documents({**query, "status": LeadStatus.CLOSED})
    
    active_projects = await db.projects.count_documents({**project_query, "status": "active"})
    
    return {
        "total_leads": total_leads,
        "new_leads": new_leads,
        "qualified_leads": qualified_leads,
        "closed_deals": closed_deals,
        "active_projects": active_projects
    }


@router.get("/overview")
async def get_stats_overview(current_user: User = Depends(get_current_user)):
    """Get overview statistics for dashboard - alias for dashboard endpoint."""
    return await get_dashboard_stats(current_user)


@router.get("/hr")
async def get_hr_stats(current_user: User = Depends(get_current_user)):
    """
    Get HR statistics for dashboard.
    
    Access Control (RBAC-driven):
    - HR_ROLES: Full access to HR statistics
    - MANAGER_ROLES: View access to high-level HR stats
    - Others: 403 Forbidden
    """
    db = get_db()
    
    # RBAC check - only HR and managers can see HR stats
    hr_roles = get_role_group("HR_ROLES", fail_closed=True)
    manager_roles = get_manager_roles()
    
    if not hr_roles:
        logger.warning("RBAC: HR_ROLES group not available, denying access")
        raise HTTPException(status_code=503, detail="Authorization service unavailable")
    
    if not has_role(current_user.role, hr_roles) and not has_role(current_user.role, manager_roles):
        raise HTTPException(status_code=403, detail="HR or Manager access required")
    
    total_employees = await db.employees.count_documents({"is_active": True})
    active_employees = await db.employees.count_documents({"is_active": True, "go_live_status": "active"})
    pending_onboarding = await db.employees.count_documents({"is_active": True, "go_live_status": {"$in": [None, "pending", "in_progress"]}})
    
    # Today's attendance
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    present_today = await db.attendance.count_documents({"date": today, "status": {"$in": ["present", "work_from_home"]}})
    
    # Pending leave requests
    pending_leaves = await db.leave_requests.count_documents({"status": "pending"})
    
    # Pending expense approvals
    pending_expenses = await db.expenses.count_documents({"status": "pending"})
    
    return {
        "total_employees": total_employees,
        "active_employees": active_employees,
        "pending_onboarding": pending_onboarding,
        "present_today": present_today,
        "attendance_percentage": round((present_today / total_employees * 100) if total_employees > 0 else 0, 1),
        "pending_leaves": pending_leaves,
        "pending_expenses": pending_expenses
    }


@router.get("/sales")
async def get_sales_stats(current_user: User = Depends(get_current_user)):
    """
    Get sales statistics for dashboard.
    
    Access Control (RBAC-driven):
    - SALES_MANAGER_ROLES: See all sales data + team revenue
    - SALES_ROLES: See own sales data only
    - Others: See only own created/assigned data
    """
    db = get_db()
    
    # RBAC check for sales access
    sales_roles = get_role_group("SALES_ROLES", fail_closed=False) or []
    sales_manager_roles = get_role_group("SALES_MANAGER_ROLES", fail_closed=False) or []
    
    query = {}
    revenue_query = {}
    
    if has_role(current_user.role, sales_manager_roles):
        # Managers see all sales data
        pass
    elif has_role(current_user.role, sales_roles):
        # Sales team sees their own data
        query['$or'] = [{"assigned_to": current_user.id}, {"created_by": current_user.id}]
        revenue_query = {"created_by": current_user.id}
    else:
        # Non-sales users see only their own data
        query['$or'] = [{"assigned_to": current_user.id}, {"created_by": current_user.id}]
        revenue_query = {"created_by": current_user.id}
    
    total_leads = await db.leads.count_documents(query)
    new_leads = await db.leads.count_documents({**query, "status": "new"})
    qualified = await db.leads.count_documents({**query, "status": "qualified"})
    closed = await db.leads.count_documents({**query, "status": "closed"})
    
    # Agreements - filtered by role
    agreement_query = {"status": "signed"}
    if revenue_query:
        agreement_query.update(revenue_query)
    agreements = await db.agreements.count_documents(agreement_query)
    
    # Revenue from agreements - filtered by role to prevent leakage
    revenue_match = {"status": "signed"}
    if revenue_query:
        revenue_match.update(revenue_query)
    
    revenue_agg = await db.agreements.aggregate([
        {"$match": revenue_match},
        {"$group": {"_id": None, "total": {"$sum": "$total_value"}}}
    ]).to_list(1)
    total_revenue = revenue_agg[0]["total"] if revenue_agg else 0
    
    # Conversion rate
    conversion_rate = round((closed / total_leads * 100) if total_leads > 0 else 0, 1)
    
    return {
        "total_leads": total_leads,
        "new_leads": new_leads,
        "qualified_leads": qualified,
        "closed_deals": closed,
        "signed_agreements": agreements,
        "total_revenue": total_revenue,
        "conversion_rate": conversion_rate
    }


@router.get("/consulting")
async def get_consulting_stats(current_user: User = Depends(get_current_user)):
    """
    Get consulting statistics for dashboard.
    
    Access Control (RBAC-driven):
    - CONSULTING_ROLES: Full access
    - MANAGER_ROLES: View access
    - Others: 403 Forbidden
    """
    db = get_db()
    
    # RBAC check - only consulting team and managers can see consulting stats
    consulting_roles = get_role_group("CONSULTING_ROLES", fail_closed=False) or []
    manager_roles = get_manager_roles()
    
    allowed_roles = list(set(consulting_roles + manager_roles))
    
    if not has_role(current_user.role, allowed_roles):
        raise HTTPException(status_code=403, detail="Consulting or Manager access required")
    
    # Projects
    total_projects = await db.projects.count_documents({})
    active_projects = await db.projects.count_documents({"status": "active"})
    completed_projects = await db.projects.count_documents({"status": "completed"})
    
    # Consultants
    consultants = await db.users.count_documents({"role": "consultant", "is_active": True})
    
    # Meetings this week
    week_start = (datetime.now(timezone.utc) - timedelta(days=datetime.now(timezone.utc).weekday())).strftime("%Y-%m-%d")
    meetings_this_week = await db.meeting_records.count_documents({"meeting_date": {"$gte": week_start}})
    
    # Pending kickoffs
    pending_kickoffs = await db.kickoff_requests.count_documents({"status": "pending"})
    
    return {
        "total_projects": total_projects,
        "active_projects": active_projects,
        "completed_projects": completed_projects,
        "total_consultants": consultants,
        "meetings_this_week": meetings_this_week,
        "pending_kickoffs": pending_kickoffs
    }


async def get_team_member_ids(manager_id: str) -> List[str]:
    """Get all team member IDs for a reporting manager."""
    db = get_db()
    team_members = await db.users.find(
        {"reporting_manager_id": manager_id, "is_active": True},
        {"_id": 0, "id": 1}
    ).to_list(1000)
    return [m["id"] for m in team_members]


@router.get("/sales-dashboard")
async def get_sales_dashboard_stats(current_user: User = Depends(get_current_user)):
    """Sales-specific dashboard stats - pipeline, conversions, revenue"""
    db = get_db()
    
    # RBAC Migration: Use database-driven role check
    manager_roles = get_role_group("MANAGER_ROLES", fail_closed=False) or ['admin', 'manager']
    is_manager = has_role(current_user.role, manager_roles)
    
    # Get user's leads or all if admin/manager
    lead_query = {}
    if not is_manager:
        lead_query['$or'] = [{"assigned_to": current_user.id}, {"created_by": current_user.id}]
    
    # Lead pipeline stats
    total_leads = await db.leads.count_documents(lead_query)
    new_leads = await db.leads.count_documents({**lead_query, "status": "new"})
    contacted_leads = await db.leads.count_documents({**lead_query, "status": "contacted"})
    qualified_leads = await db.leads.count_documents({**lead_query, "status": "qualified"})
    proposal_leads = await db.leads.count_documents({**lead_query, "status": "proposal"})
    closed_leads = await db.leads.count_documents({**lead_query, "status": "closed"})
    
    # My Clients (sales person specific)
    my_clients = await db.clients.count_documents({"sales_person_id": current_user.id, "is_active": True})
    total_clients = await db.clients.count_documents({"is_active": True})
    
    # Quotations and Agreements
    quot_query = {} if is_manager else {"created_by": current_user.id}
    pending_quotations = await db.quotations.count_documents({**quot_query, "status": "pending"})
    pending_agreements = await db.agreements.count_documents({**quot_query, "status": "pending_approval"})
    approved_agreements = await db.agreements.count_documents({**quot_query, "status": "approved"})
    
    # Kickoff requests sent
    kickoff_query = {} if is_manager else {"requested_by": current_user.id}
    pending_kickoffs = await db.kickoff_requests.count_documents({**kickoff_query, "status": "pending"})
    
    # Calculate total revenue from clients
    pipeline = [
        {"$match": {"sales_person_id": current_user.id} if not is_manager else {}},
        {"$unwind": {"path": "$revenue_history", "preserveNullAndEmptyArrays": False}},
        {"$group": {"_id": None, "total": {"$sum": "$revenue_history.amount"}}}
    ]
    revenue_result = await db.clients.aggregate(pipeline).to_list(1)
    total_revenue = revenue_result[0]['total'] if revenue_result else 0
    
    return {
        "pipeline": {
            "total": total_leads,
            "new": new_leads,
            "contacted": contacted_leads,
            "qualified": qualified_leads,
            "proposal": proposal_leads,
            "closed": closed_leads
        },
        "clients": {
            "my_clients": my_clients,
            "total_clients": total_clients
        },
        "quotations": {
            "pending": pending_quotations
        },
        "agreements": {
            "pending": pending_agreements,
            "approved": approved_agreements
        },
        "kickoffs": {
            "pending": pending_kickoffs
        },
        "revenue": {
            "total": total_revenue
        },
        "conversion_rate": round((closed_leads / total_leads * 100) if total_leads > 0 else 0, 1)
    }


@router.get("/sales-dashboard-enhanced")
async def get_enhanced_sales_dashboard_stats(
    view_mode: str = "own",
    current_user: User = Depends(get_current_user)
):
    """Enhanced Sales dashboard with comprehensive metrics"""
    db = get_db()
    
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # Determine query scope based on view_mode and permissions
    user_ids = [current_user.id]
    
    if view_mode == "team":
        team_ids = await get_team_member_ids(current_user.id)
        if team_ids:
            user_ids = team_ids + [current_user.id]
    elif view_mode == "all" and can_see_all_data(current_user):
        user_ids = None
    
    # Build query filter
    if user_ids:
        lead_query = {"$or": [{"assigned_to": {"$in": user_ids}}, {"created_by": {"$in": user_ids}}]}
        meeting_query = {"$or": [{"created_by": {"$in": user_ids}}, {"attendees": {"$in": user_ids}}]}
    else:
        lead_query = {}
        meeting_query = {}
    
    # ===== LEAD METRICS =====
    total_leads = await db.leads.count_documents(lead_query)
    new_leads = await db.leads.count_documents({**lead_query, "status": "new"})
    contacted_leads = await db.leads.count_documents({**lead_query, "status": "contacted"})
    qualified_leads = await db.leads.count_documents({**lead_query, "status": "qualified"})
    proposal_leads = await db.leads.count_documents({**lead_query, "status": "proposal"})
    agreement_leads = await db.leads.count_documents({**lead_query, "status": "agreement"})
    closed_leads = await db.leads.count_documents({**lead_query, "status": "closed"})
    lost_leads = await db.leads.count_documents({**lead_query, "status": "lost"})
    
    # Lead temperature
    hot_leads = await db.leads.count_documents({**lead_query, "lead_score": {"$gte": 80}})
    warm_leads = await db.leads.count_documents({**lead_query, "lead_score": {"$gte": 50, "$lt": 80}})
    cold_leads = await db.leads.count_documents({**lead_query, "lead_score": {"$lt": 50}})
    
    # ===== MEETING METRICS =====
    total_meetings = await db.meetings.count_documents({**meeting_query, "type": "sales"})
    meetings_this_month = await db.meetings.count_documents({
        **meeting_query, 
        "type": "sales",
        "meeting_date": {"$gte": month_start.isoformat()}
    })
    meetings_with_mom = await db.meetings.count_documents({
        **meeting_query, 
        "type": "sales",
        "mom_generated": True
    })
    
    # Lead to Meeting ratio
    leads_with_meetings = await db.meetings.distinct("lead_id", {**meeting_query, "type": "sales", "lead_id": {"$ne": None}})
    lead_to_meeting_ratio = round((len(leads_with_meetings) / total_leads * 100) if total_leads > 0 else 0, 1)
    
    # ===== CLOSURE METRICS =====
    total_closures = closed_leads
    lead_to_closure_ratio = round((closed_leads / total_leads * 100) if total_leads > 0 else 0, 1)
    
    # ===== DEAL VALUE =====
    agreement_pipeline = [
        {"$match": {"status": "approved"}},
        {"$group": {"_id": None, "total": {"$sum": "$total_value"}}}
    ]
    if user_ids:
        agreement_pipeline[0]["$match"]["created_by"] = {"$in": user_ids}
    deal_value_result = await db.agreements.aggregate(agreement_pipeline).to_list(1)
    total_deal_value = deal_value_result[0]['total'] if deal_value_result else 0
    
    # ===== TARGETS VS ACHIEVEMENT =====
    current_month = now.month
    current_year = now.year
    
    targets = await db.sales_targets.find({
        "user_id": {"$in": user_ids} if user_ids else {"$exists": True},
        "month": current_month,
        "year": current_year,
        "approval_status": "approved"
    }).to_list(100)
    
    total_meeting_target = sum(t.get('meeting_target', 0) for t in targets)
    total_conversion_target = sum(t.get('conversion_target', 0) for t in targets)
    total_value_target = sum(t.get('deal_value_target', 0) for t in targets)
    
    # ===== MONTH OVER MONTH =====
    mom_data = []
    for i in range(6):
        month_date = now - timedelta(days=30*i)
        m_start = month_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        m_end = (m_start + timedelta(days=32)).replace(day=1)
        
        month_leads = await db.leads.count_documents({
            **lead_query,
            "created_at": {"$gte": m_start.isoformat(), "$lt": m_end.isoformat()}
        })
        month_closures = await db.leads.count_documents({
            **lead_query,
            "status": "closed",
            "updated_at": {"$gte": m_start.isoformat(), "$lt": m_end.isoformat()}
        })
        month_meetings_count = await db.meetings.count_documents({
            **meeting_query,
            "type": "sales",
            "meeting_date": {"$gte": m_start.isoformat(), "$lt": m_end.isoformat()}
        })
        
        mom_data.append({
            "month": m_start.strftime("%b %Y"),
            "leads": month_leads,
            "closures": month_closures,
            "meetings": month_meetings_count,
            "conversion_rate": round((month_closures / month_leads * 100) if month_leads > 0 else 0, 1)
        })
    
    mom_data.reverse()
    
    # ===== LEAD SOURCE DISTRIBUTION =====
    source_pipeline = [
        {"$match": lead_query} if lead_query else {"$match": {}},
        {"$group": {"_id": "$lead_source", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 10}
    ]
    lead_sources = await db.leads.aggregate(source_pipeline).to_list(10)
    
    # ===== KICKOFF REQUESTS =====
    kickoff_query_filter = {"requested_by": {"$in": user_ids}} if user_ids else {}
    pending_kickoffs = await db.kickoff_requests.count_documents({**kickoff_query_filter, "status": "pending"})
    
    # ===== TEAM LEADERBOARD =====
    leaderboard = []
    if view_mode in ["team", "all"]:
        team_ids_for_board = await get_team_member_ids(current_user.id) if view_mode == "team" else None
        
        leaderboard_pipeline = [
            {"$match": {"status": "closed"} if not team_ids_for_board else {"status": "closed", "assigned_to": {"$in": team_ids_for_board}}},
            {"$group": {"_id": "$assigned_to", "closures": {"$sum": 1}}},
            {"$sort": {"closures": -1}},
            {"$limit": 10}
        ]
        top_performers = await db.leads.aggregate(leaderboard_pipeline).to_list(10)
        
        for performer in top_performers:
            user_doc = await db.users.find_one({"id": performer['_id']}, {"_id": 0, "full_name": 1, "email": 1})
            if user_doc:
                leaderboard.append({
                    "user_id": performer['_id'],
                    "name": user_doc.get('full_name', 'Unknown'),
                    "closures": performer['closures']
                })
    
    closures_this_month = await db.leads.count_documents({
        **lead_query,
        "status": "closed",
        "updated_at": {"$gte": month_start.isoformat()}
    })
    
    return {
        "pipeline": {
            "total": total_leads,
            "new": new_leads,
            "contacted": contacted_leads,
            "qualified": qualified_leads,
            "proposal": proposal_leads,
            "agreement": agreement_leads,
            "closed": closed_leads,
            "lost": lost_leads
        },
        "temperature": {
            "hot": hot_leads,
            "warm": warm_leads,
            "cold": cold_leads
        },
        "meetings": {
            "total": total_meetings,
            "this_month": meetings_this_month,
            "with_mom": meetings_with_mom,
            "mom_completion_rate": round((meetings_with_mom / total_meetings * 100) if total_meetings > 0 else 0, 1)
        },
        "ratios": {
            "lead_to_meeting": lead_to_meeting_ratio,
            "lead_to_closure": lead_to_closure_ratio
        },
        "closures": {
            "total": total_closures,
            "this_month": closures_this_month
        },
        "deal_value": {
            "total": total_deal_value,
            "this_month": 0
        },
        "targets": {
            "meeting_target": total_meeting_target,
            "meeting_actual": meetings_this_month,
            "meeting_achievement": round((meetings_this_month / total_meeting_target * 100) if total_meeting_target > 0 else 0, 1),
            "conversion_target": total_conversion_target,
            "conversion_actual": closures_this_month,
            "value_target": total_value_target,
            "value_actual": total_deal_value
        },
        "mom_performance": mom_data,
        "lead_sources": [{"source": s['_id'] or "Unknown", "count": s['count']} for s in lead_sources],
        "kickoffs_pending": pending_kickoffs,
        "leaderboard": leaderboard,
        "view_mode": view_mode,
        "has_team": len(await get_team_member_ids(current_user.id)) > 0
    }


@router.get("/consulting-dashboard")
async def get_consulting_dashboard_stats(current_user: User = Depends(get_current_user)):
    """Consulting-specific dashboard stats - delivery, efficiency, workload"""
    db = get_db()
    
    # RBAC Migration: Use database-driven role check
    senior_consulting_roles = get_role_group("SENIOR_CONSULTING_ROLES", fail_closed=False) or ['admin', 'principal_consultant', 'senior_consultant']
    manager_roles = get_role_group("MANAGER_ROLES", fail_closed=False) or ['admin', 'manager']
    is_pm = has_role(current_user.role, senior_consulting_roles) or has_role(current_user.role, manager_roles)
    
    # Projects stats
    if is_pm:
        active_projects = await db.projects.count_documents({"status": "active"})
        completed_projects = await db.projects.count_documents({"status": "completed"})
        on_hold_projects = await db.projects.count_documents({"status": "on_hold"})
    else:
        active_projects = await db.consultant_assignments.count_documents({
            "consultant_id": current_user.id, "is_active": True
        })
        completed_projects = 0
        on_hold_projects = 0
    
    # Meetings stats
    meeting_pipeline = [
        {"$match": {"type": "consulting", "is_delivered": True}},
        {"$group": {"_id": None, "total": {"$sum": 1}}}
    ]
    delivered_meetings = await db.meetings.aggregate(meeting_pipeline).to_list(1)
    total_delivered = delivered_meetings[0]['total'] if delivered_meetings else 0
    
    pending_meetings = await db.meetings.count_documents({"type": "consulting", "is_delivered": False})
    
    commit_pipeline = [
        {"$match": {"status": "active"}},
        {"$group": {"_id": None, "total": {"$sum": "$total_meetings_committed"}}}
    ]
    committed_result = await db.projects.aggregate(commit_pipeline).to_list(1)
    total_committed = committed_result[0]['total'] if committed_result else 0
    
    efficiency = round((total_delivered / total_committed * 100) if total_committed > 0 else 0, 1)
    
    incoming_kickoffs = 0
    if is_pm:
        incoming_kickoffs = await db.kickoff_requests.count_documents({"status": "pending"})
    
    consultants_pipeline = [
        {"$match": {"is_active": True}},
        {"$group": {"_id": "$consultant_id", "projects": {"$sum": 1}}}
    ]
    workload = await db.consultant_assignments.aggregate(consultants_pipeline).to_list(100)
    
    avg_workload = round(sum([w['projects'] for w in workload]) / len(workload), 1) if workload else 0
    
    at_risk_projects = await db.projects.count_documents({
        "status": "active",
        "$expr": {"$lt": ["$total_meetings_delivered", {"$multiply": ["$total_meetings_committed", 0.3]}]}
    })
    
    return {
        "projects": {
            "active": active_projects,
            "completed": completed_projects,
            "on_hold": on_hold_projects,
            "at_risk": at_risk_projects
        },
        "meetings": {
            "delivered": total_delivered,
            "pending": pending_meetings,
            "committed": total_committed
        },
        "efficiency_score": efficiency,
        "incoming_kickoffs": incoming_kickoffs,
        "consultant_workload": {
            "average": avg_workload,
            "distribution": workload[:10]
        }
    }


@router.get("/hr-dashboard")
async def get_hr_dashboard_stats(current_user: User = Depends(get_current_user)):
    """HR-specific dashboard stats - employees, attendance, leaves, payroll"""
    db = get_db()
    
    # RBAC Migration: Use database-driven role check
    hr_roles = get_role_group("HR_ROLES", fail_closed=True)
    manager_roles = get_role_group("MANAGER_ROLES", fail_closed=False) or []
    if not hr_roles or (not has_role(current_user.role, hr_roles) and not has_role(current_user.role, manager_roles)):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    total_employees = await db.employees.count_documents({"is_active": True})
    new_this_month = await db.employees.count_documents({
        "is_active": True,
        "date_of_joining": {"$gte": datetime.now(timezone.utc).replace(day=1).isoformat()}
    })
    
    dept_pipeline = [
        {"$match": {"is_active": True}},
        {"$group": {"_id": "$department", "count": {"$sum": 1}}}
    ]
    by_department = await db.employees.aggregate(dept_pipeline).to_list(20)
    
    today = datetime.now(timezone.utc).date().isoformat()
    present_today = await db.attendance.count_documents({"date": today, "status": "present"})
    absent_today = await db.attendance.count_documents({"date": today, "status": "absent"})
    wfh_today = await db.attendance.count_documents({"date": today, "status": "wfh"})
    
    pending_leaves = await db.leave_requests.count_documents({"status": "pending"})
    pending_expenses = await db.expenses.count_documents({"status": "pending"})
    
    current_month = datetime.now(timezone.utc).month
    current_year = datetime.now(timezone.utc).year
    payroll_processed = await db.salary_slips.count_documents({
        "month": current_month, "year": current_year
    })
    
    return {
        "employees": {
            "total": total_employees,
            "new_this_month": new_this_month,
            "by_department": {item['_id'] or 'Unassigned': item['count'] for item in by_department}
        },
        "attendance": {
            "present_today": present_today,
            "absent_today": absent_today,
            "wfh_today": wfh_today,
            "attendance_rate": round((present_today / total_employees * 100) if total_employees > 0 else 0, 1)
        },
        "leaves": {
            "pending_requests": pending_leaves
        },
        "expenses": {
            "pending_approvals": pending_expenses
        },
        "payroll": {
            "processed_this_month": payroll_processed,
            "pending": total_employees - payroll_processed
        }
    }
