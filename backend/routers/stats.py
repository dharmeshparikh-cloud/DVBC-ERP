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
from utils.timezone import today_ist, current_month_ist, now_ist
from typing import List, Optional
import logging

from .models import User, LeadStatus
from .deps import get_db, get_role_group, has_role
from .deps import get_current_user
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
    
    Performance: Cached for 5 minutes per user scope
    """
    db = get_db()
    
    # Determine cache scope based on user role
    if can_see_all_data(current_user):
        cache_scope = "global"
    elif is_manager_or_above(current_user):
        cache_scope = f"manager:{current_user.id}"
    else:
        cache_scope = f"user:{current_user.id}"
    
    cache_key = stats_key("dashboard", cache_scope)
    
    # Try cache first
    cached = await cache.get(cache_key)
    if cached is not None:
        logger.debug(f"Cache hit: {cache_key}")
        return cached
    
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
    
    result = {
        "total_leads": total_leads,
        "new_leads": new_leads,
        "qualified_leads": qualified_leads,
        "closed_deals": closed_deals,
        "active_projects": active_projects
    }
    
    # Cache result
    await cache.set(cache_key, result, PerformanceCache.TTL_DASHBOARD_STATS)
    
    return result


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
    
    Performance: Cached for 5 minutes (global scope)
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
    
    # Check cache - HR stats are global
    cache_key = stats_key("hr", "global")
    cached = await cache.get(cache_key)
    if cached is not None:
        return cached
    
    total_employees = await db.employees.count_documents({"is_active": True})
    active_employees = await db.employees.count_documents({"is_active": True, "go_live_status": "active"})
    pending_onboarding = await db.employees.count_documents({"is_active": True, "go_live_status": {"$in": [None, "pending", "in_progress"]}})
    
    # Today's attendance
    today = today_ist()
    present_today = await db.attendance.count_documents({"date": today, "status": {"$in": ["present", "work_from_home"]}})
    
    # Pending leave requests
    pending_leaves = await db.leave_requests.count_documents({"status": "pending"})
    
    # Pending expense approvals
    pending_expenses = await db.expenses.count_documents({"status": "pending"})
    
    result = {
        "total_employees": total_employees,
        "active_employees": active_employees,
        "pending_onboarding": pending_onboarding,
        "present_today": present_today,
        "attendance_percentage": round((present_today / total_employees * 100) if total_employees > 0 else 0, 1),
        "pending_leaves": pending_leaves,
        "pending_expenses": pending_expenses
    }
    
    # Cache result
    await cache.set(cache_key, result, PerformanceCache.TTL_DASHBOARD_STATS)
    
    return result


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



# ==================== CACHE MANAGEMENT ====================

@router.get("/cache/stats")
async def get_cache_stats(current_user: User = Depends(get_current_user)):
    """
    Get cache statistics for monitoring.
    Admin only endpoint.
    """
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    return cache.get_stats()


@router.post("/cache/invalidate")
async def invalidate_cache(
    pattern: str = None,
    current_user: User = Depends(get_current_user)
):
    """
    Invalidate cache entries.
    Admin only endpoint.
    
    Args:
        pattern: Optional pattern to match (e.g., "stats:*" to invalidate all stats)
                 If not provided, clears all cache.
    """
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    if pattern:
        count = cache.invalidate_pattern(pattern)
        return {"message": f"Invalidated {count} cache entries matching '{pattern}'"}
    else:
        count = cache.invalidate_all()
        return {"message": f"Cleared all {count} cache entries"}


# ============================================================================
# CONSULTING EFFORTS SUMMARY REPORT
# Comprehensive project handoff summary with all metrics
# Used for audit, manager review, and project closure
# ============================================================================

@router.get("/consulting/efforts-summary")
async def get_consulting_efforts_summary(
    project_id: Optional[str] = None,
    consultant_id: Optional[str] = None,
    client_id: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """
    Comprehensive Consulting Efforts Summary Report.
    
    Includes:
    - Meetings per consultant, project, client
    - Task assigned/completed, timely delivery metrics
    - Average duration, reschedules with reasons
    - Client approved meetings, total/extra meetings
    - Project expenses, payments (received/overdue/late)
    
    Filters: project_id, consultant_id, client_id, date_from, date_to
    """
    db = get_db()
    
    # Build query filters
    meeting_filter = {"type": "consulting"}
    project_filter = {}
    expense_filter = {}
    
    if project_id:
        meeting_filter["project_id"] = project_id
        project_filter["id"] = project_id
        expense_filter["project_id"] = project_id
    
    if client_id:
        meeting_filter["client_id"] = client_id
        project_filter["client_id"] = client_id
    
    if consultant_id:
        meeting_filter["created_by"] = consultant_id
    
    if date_from:
        meeting_filter["meeting_date"] = {"$gte": date_from}
    if date_to:
        if "meeting_date" in meeting_filter:
            meeting_filter["meeting_date"]["$lte"] = date_to
        else:
            meeting_filter["meeting_date"] = {"$lte": date_to}
    
    # Get meetings with attendance data
    meetings = await db.meetings.find(meeting_filter, {"_id": 0}).to_list(1000)
    
    # Get projects
    if project_filter:
        projects = await db.projects.find(project_filter, {"_id": 0}).to_list(100)
    else:
        project_ids = list(set(m.get("project_id") for m in meetings if m.get("project_id")))
        projects = await db.projects.find({"id": {"$in": project_ids}}, {"_id": 0}).to_list(100)
    
    # Get expenses
    if expense_filter:
        expenses = await db.expenses.find(expense_filter, {"_id": 0}).to_list(500)
    else:
        expenses = await db.expenses.find({"type": "travel"}, {"_id": 0}).to_list(500)
    
    # Get payments
    payments = await db.payments.find(
        {"project_id": {"$in": [p.get("id") for p in projects]}} if projects else {},
        {"_id": 0}
    ).to_list(500)
    
    # Get SOWs (Enhanced SOW - Committed by Sales)
    sow_filter = {}
    if project_id:
        sow_filter["project_id"] = project_id
    sows = await db.enhanced_sow.find(sow_filter, {"_id": 0}).to_list(200)
    
    # Calculate SOW metrics
    total_sows = len(sows)
    committed_sows = len([s for s in sows if s.get("sales_handover_complete")])
    
    # Calculate scope metrics
    total_committed_scopes = 0
    total_additional_scopes = 0
    total_completed_scopes = 0
    
    for sow in sows:
        scopes = sow.get("scopes", [])
        for scope in scopes:
            if scope.get("is_additional"):
                total_additional_scopes += 1
            else:
                total_committed_scopes += 1
            if scope.get("status") == "completed" or scope.get("progress_percentage", 0) >= 100:
                total_completed_scopes += 1
    
    # Average SOW progress
    sow_progress_list = [s.get("progress_percentage", 0) or 0 for s in sows]
    avg_sow_progress = round(sum(sow_progress_list) / len(sow_progress_list), 1) if sow_progress_list else 0
    
    # Calculate metrics
    total_meetings = len(meetings)
    delivered_meetings = len([m for m in meetings if m.get("is_delivered")])
    pending_meetings = total_meetings - delivered_meetings
    with_mom = len([m for m in meetings if m.get("mom_generated")])
    with_attendance = len([m for m in meetings if m.get("attendance_marked")])
    mom_sent = len([m for m in meetings if m.get("mom_sent_to_client")])
    
    # Duration metrics
    durations = [(m.get("duration_minutes") or 0) for m in meetings if m.get("duration_minutes")]
    total_duration_minutes = sum(durations) if durations else 0
    avg_duration_minutes = round(sum(durations) / len(durations), 1) if durations else 0
    
    # Meetings by consultant
    consultant_meetings = {}
    for m in meetings:
        consultant_id = m.get("created_by")
        consultant_name = m.get("created_by_name", "Unknown")
        if consultant_id not in consultant_meetings:
            consultant_meetings[consultant_id] = {
                "id": consultant_id,
                "name": consultant_name,
                "total": 0,
                "delivered": 0,
                "with_mom": 0,
                "total_duration": 0
            }
        consultant_meetings[consultant_id]["total"] += 1
        if m.get("is_delivered"):
            consultant_meetings[consultant_id]["delivered"] += 1
        if m.get("mom_generated"):
            consultant_meetings[consultant_id]["with_mom"] += 1
        consultant_meetings[consultant_id]["total_duration"] += m.get("duration_minutes") or 0
    
    # Meetings by project
    project_meetings = {}
    for m in meetings:
        pid = m.get("project_id")
        pname = m.get("project_name", "Unknown Project")
        if pid not in project_meetings:
            project_meetings[pid] = {
                "id": pid,
                "name": pname,
                "total": 0,
                "delivered": 0,
                "committed": 0,
                "extra": 0,
                "total_duration": 0
            }
        project_meetings[pid]["total"] += 1
        if m.get("is_delivered"):
            project_meetings[pid]["delivered"] += 1
        project_meetings[pid]["total_duration"] += m.get("duration_minutes") or 0
    
    # Add committed counts from projects
    for p in projects:
        pid = p.get("id")
        if pid in project_meetings:
            committed = p.get("total_meetings_committed", 0)
            project_meetings[pid]["committed"] = committed
            delivered = project_meetings[pid]["delivered"]
            project_meetings[pid]["extra"] = max(0, delivered - committed)
    
    # Meetings by client
    client_meetings = {}
    for m in meetings:
        cid = m.get("client_id")
        cname = m.get("client_name", "Unknown Client")
        if cid not in client_meetings:
            client_meetings[cid] = {
                "id": cid,
                "name": cname,
                "total": 0,
                "delivered": 0,
                "approved": 0
            }
        client_meetings[cid]["total"] += 1
        if m.get("is_delivered"):
            client_meetings[cid]["delivered"] += 1
        if m.get("mom_sent_to_client"):
            client_meetings[cid]["approved"] += 1
    
    # Task metrics
    all_action_items = []
    for m in meetings:
        items = m.get("action_items", [])
        all_action_items.extend(items)
    
    total_tasks = len(all_action_items)
    completed_tasks = len([t for t in all_action_items if t.get("status") == "completed"])
    
    # Calculate timely delivery (tasks completed by due date)
    timely_tasks = 0
    for t in all_action_items:
        if t.get("status") == "completed" and t.get("due_date") and t.get("completed_at"):
            try:
                due = datetime.fromisoformat(t["due_date"].replace('Z', '+00:00'))
                completed = datetime.fromisoformat(t["completed_at"].replace('Z', '+00:00'))
                if completed <= due:
                    timely_tasks += 1
            except:
                pass
    
    timely_delivery_rate = round((timely_tasks / completed_tasks * 100) if completed_tasks > 0 else 0, 1)
    
    # Expense metrics
    total_expenses = sum(e.get("amount", 0) for e in expenses)
    approved_expenses = sum(e.get("amount", 0) for e in expenses if e.get("status") == "approved")
    pending_expenses = sum(e.get("amount", 0) for e in expenses if e.get("status") == "pending")
    
    # Payment metrics
    total_payments = sum(p.get("amount", 0) for p in payments)
    received_payments = sum(p.get("amount", 0) for p in payments if p.get("status") == "received")
    
    # Overdue/late payment calculation
    overdue_payments = 0
    late_payments = 0
    today = datetime.now(timezone.utc)
    for p in payments:
        due_date = p.get("due_date")
        status = p.get("status")
        if due_date:
            try:
                due = datetime.fromisoformat(due_date.replace('Z', '+00:00'))
                if status != "received" and due < today:
                    overdue_payments += p.get("amount", 0)
                elif status == "received" and p.get("received_at"):
                    received_at = datetime.fromisoformat(p["received_at"].replace('Z', '+00:00'))
                    if received_at > due:
                        late_payments += p.get("amount", 0)
            except:
                pass
    
    return {
        "summary": {
            "total_meetings": total_meetings,
            "delivered_meetings": delivered_meetings,
            "pending_meetings": pending_meetings,
            "meetings_with_mom": with_mom,
            "meetings_with_attendance": with_attendance,
            "mom_sent_to_client": mom_sent,
            "attendance_compliance_rate": round((with_attendance / total_meetings * 100) if total_meetings > 0 else 0, 1)
        },
        "duration": {
            "total_minutes": total_duration_minutes,
            "total_hours": round(total_duration_minutes / 60, 1),
            "average_minutes": avg_duration_minutes
        },
        "tasks": {
            "total": total_tasks,
            "completed": completed_tasks,
            "pending": total_tasks - completed_tasks,
            "completion_rate": round((completed_tasks / total_tasks * 100) if total_tasks > 0 else 0, 1),
            "timely_delivery_rate": timely_delivery_rate
        },
        "by_consultant": list(consultant_meetings.values()),
        "by_project": list(project_meetings.values()),
        "by_client": list(client_meetings.values()),
        "expenses": {
            "total": total_expenses,
            "approved": approved_expenses,
            "pending": pending_expenses
        },
        "payments": {
            "total_invoiced": total_payments,
            "received": received_payments,
            "pending": total_payments - received_payments,
            "overdue": overdue_payments,
            "late": late_payments,
            "collection_rate": round((received_payments / total_payments * 100) if total_payments > 0 else 0, 1)
        },
        "sow": {
            "total": total_sows,
            "committed_by_sales": committed_sows,
            "avg_progress": avg_sow_progress,
            "scopes": {
                "committed": total_committed_scopes,
                "additional": total_additional_scopes,
                "completed": total_completed_scopes,
                "pending": total_committed_scopes + total_additional_scopes - total_completed_scopes
            }
        },
        "filters_applied": {
            "project_id": project_id,
            "consultant_id": consultant_id,
            "client_id": client_id,
            "date_from": date_from,
            "date_to": date_to
        }
    }


@router.get("/consulting/project/{project_id}/handoff-summary")
async def get_project_handoff_summary(
    project_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Complete Project Handoff Summary for audit.
    
    Includes all details needed for project closure:
    - Complete meeting history with attendance
    - All tasks and their status
    - All expenses and their approval status
    - All payments and collection status
    - Reschedule history
    """
    db = get_db()
    
    # Get project
    project = await db.projects.find_one({"id": project_id}, {"_id": 0})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Get client
    client = await db.clients.find_one({"id": project.get("client_id")}, {"_id": 0})
    
    # Get all meetings with full details
    meetings = await db.meetings.find(
        {"project_id": project_id, "type": "consulting"},
        {"_id": 0}
    ).sort("meeting_date", 1).to_list(500)
    
    # Get meeting attendance records
    attendance_records = await db.meeting_attendance.find(
        {"project_id": project_id},
        {"_id": 0}
    ).to_list(500)
    
    # Get consultant assignments
    assignments = await db.consultant_assignments.find(
        {"project_id": project_id},
        {"_id": 0}
    ).to_list(50)
    
    # Get expenses
    expenses = await db.expenses.find(
        {"project_id": project_id},
        {"_id": 0}
    ).to_list(500)
    
    # Get payments
    payments = await db.payments.find(
        {"project_id": project_id},
        {"_id": 0}
    ).to_list(100)
    
    # Get additional meeting requests
    additional_requests = await db.additional_meeting_requests.find(
        {"project_id": project_id},
        {"_id": 0}
    ).to_list(50)
    
    # Calculate metrics
    total_meetings = len(meetings)
    delivered = len([m for m in meetings if m.get("is_delivered")])
    with_mom = len([m for m in meetings if m.get("mom_generated")])
    with_attendance = len([m for m in meetings if m.get("attendance_marked")])
    
    total_duration = sum(m.get("duration_minutes", 0) for m in meetings)
    
    # All tasks from all meetings
    all_tasks = []
    for m in meetings:
        for task in m.get("action_items", []):
            task["meeting_id"] = m.get("id")
            task["meeting_title"] = m.get("title")
            task["meeting_date"] = m.get("meeting_date")
            all_tasks.append(task)
    
    completed_tasks = len([t for t in all_tasks if t.get("status") == "completed"])
    
    # Expense summary
    total_expenses = sum(e.get("amount", 0) for e in expenses)
    approved_expenses = sum(e.get("amount", 0) for e in expenses if e.get("status") == "approved")
    
    # Payment summary
    total_invoiced = sum(p.get("amount", 0) for p in payments)
    received = sum(p.get("amount", 0) for p in payments if p.get("status") == "received")
    
    return {
        "project": {
            "id": project.get("id"),
            "name": project.get("name"),
            "type": project.get("type"),
            "status": project.get("status"),
            "start_date": project.get("start_date"),
            "end_date": project.get("end_date"),
            "total_value": project.get("total_value"),
            "meetings_committed": project.get("total_meetings_committed", 0),
            "meetings_delivered": project.get("total_meetings_delivered", 0)
        },
        "client": {
            "id": client.get("id") if client else None,
            "name": client.get("company_name") if client else project.get("client_name"),
            "contacts": client.get("contacts", []) if client else []
        },
        "team": assignments,
        "meetings": {
            "total": total_meetings,
            "delivered": delivered,
            "with_mom": with_mom,
            "with_attendance": with_attendance,
            "total_duration_hours": round(total_duration / 60, 1),
            "list": meetings
        },
        "attendance_records": attendance_records,
        "tasks": {
            "total": len(all_tasks),
            "completed": completed_tasks,
            "pending": len(all_tasks) - completed_tasks,
            "list": all_tasks
        },
        "expenses": {
            "total": total_expenses,
            "approved": approved_expenses,
            "pending": total_expenses - approved_expenses,
            "list": expenses
        },
        "payments": {
            "total_invoiced": total_invoiced,
            "received": received,
            "pending": total_invoiced - received,
            "list": payments
        },
        "additional_meeting_requests": additional_requests,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generated_by": current_user.full_name
    }

