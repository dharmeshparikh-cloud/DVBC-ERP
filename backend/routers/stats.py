"""
Dashboard Stats Router - Dashboard statistics for Admin, Sales, HR, Consulting
Replaces legacy stats endpoints from server.py
"""

from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone, timedelta
from typing import List, Optional

from .models import User, UserRole, LeadStatus, CONSULTING_ROLES, ALL_DATA_ACCESS_ROLES
from .deps import get_db
from .auth import get_current_user

router = APIRouter(prefix="/stats", tags=["Dashboard Stats"])


@router.get("/dashboard")
async def get_dashboard_stats(current_user: User = Depends(get_current_user)):
    """Get main dashboard statistics - matches frontend expected format."""
    db = get_db()
    
    query = {}
    if current_user.role != UserRole.ADMIN:
        query['$or'] = [{"assigned_to": current_user.id}, {"created_by": current_user.id}]
    
    total_leads = await db.leads.count_documents(query)
    new_leads = await db.leads.count_documents({**query, "status": LeadStatus.NEW})
    qualified_leads = await db.leads.count_documents({**query, "status": LeadStatus.QUALIFIED})
    closed_deals = await db.leads.count_documents({**query, "status": LeadStatus.CLOSED})
    
    project_query = {}
    if current_user.role != UserRole.ADMIN:
        project_query['$or'] = [{"assigned_team": current_user.id}, {"created_by": current_user.id}]
    
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
    """Get HR statistics for dashboard."""
    db = get_db()
    
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
    """Get sales statistics for dashboard."""
    db = get_db()
    
    query = {}
    if current_user.role not in ['admin', 'manager', 'sales_manager']:
        query['$or'] = [{"assigned_to": current_user.id}, {"created_by": current_user.id}]
    
    total_leads = await db.leads.count_documents(query)
    new_leads = await db.leads.count_documents({**query, "status": "new"})
    qualified = await db.leads.count_documents({**query, "status": "qualified"})
    closed = await db.leads.count_documents({**query, "status": "closed"})
    
    # Agreements
    agreements = await db.agreements.count_documents({"status": "signed"})
    
    # Revenue from agreements
    revenue_agg = await db.agreements.aggregate([
        {"$match": {"status": "signed"}},
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
    """Get consulting statistics for dashboard."""
    db = get_db()
    
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


def can_see_all_data(user: User) -> bool:
    return user.role in ALL_DATA_ACCESS_ROLES


@router.get("/sales-dashboard")
async def get_sales_dashboard_stats(current_user: User = Depends(get_current_user)):
    """Sales-specific dashboard stats - pipeline, conversions, revenue"""
    db = get_db()
    
    # Get user's leads or all if admin
    lead_query = {}
    if current_user.role not in ['admin', 'manager']:
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
    quot_query = {} if current_user.role in ['admin', 'manager'] else {"created_by": current_user.id}
    pending_quotations = await db.quotations.count_documents({**quot_query, "status": "pending"})
    pending_agreements = await db.agreements.count_documents({**quot_query, "status": "pending_approval"})
    approved_agreements = await db.agreements.count_documents({**quot_query, "status": "approved"})
    
    # Kickoff requests sent
    kickoff_query = {} if current_user.role in ['admin', 'manager'] else {"requested_by": current_user.id}
    pending_kickoffs = await db.kickoff_requests.count_documents({**kickoff_query, "status": "pending"})
    
    # Calculate total revenue from clients
    pipeline = [
        {"$match": {"sales_person_id": current_user.id} if current_user.role not in ['admin', 'manager'] else {}},
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
    is_pm = current_user.role in ['admin', 'project_manager', 'manager']
    
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
    
    if current_user.role not in ['admin', 'hr_manager', 'hr_executive', 'manager']:
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
