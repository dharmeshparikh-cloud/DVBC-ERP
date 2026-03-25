"""
Leads Router - Lead Management, Scoring, and CRUD operations

PERFORMANCE OPTIMIZATION: December 2025
- Added pagination support for list endpoints
- Added caching for lead lists
- Added WebSocket notifications for real-time updates

GOVERNANCE: March 2026
- Auto-create kickoff request when lead stage changes to closed_won
- Duplicate kickoff prevention
"""

from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from pydantic import BaseModel
from datetime import datetime, timezone, timedelta
from typing import List, Optional
import uuid

from .models import Lead, LeadCreate, LeadUpdate, User, UserRole, LeadStatus
from .deps import (
    get_db, SALES_ROLES, ADMIN_ROLES, get_role_group, has_role,
    PaginationParams, paginate_response, DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
)
from .deps import get_current_user
from .audit_logging import log_audit

# Performance caching
import sys
sys.path.insert(0, '/app/backend')
from services.cache_service import cache, list_key, PerformanceCache
from services.websocket_manager import ws_manager, notify_lead_update, notify_dashboard_refresh
from services.redis_cache import CacheInvalidation

router = APIRouter(prefix="/leads", tags=["Leads"])


def get_leads_access_roles():
    """Get roles that can access leads - uses RBAC service"""
    sales_roles = get_role_group("SALES_ROLES", fail_closed=False) or SALES_ROLES
    return sales_roles  # ADMIN_ROLES is already included in SALES_ROLES


def calculate_lead_score(lead_data: dict) -> tuple:
    """
    Calculate lead score based on multiple factors:
    - Job title seniority (0-40 points)
    - Contact completeness (0-30 points)
    - Engagement/status (0-30 points)
    """
    score = 0
    breakdown = {}
    
    # Job Title Scoring (0-40 points)
    job_title = (lead_data.get('job_title') or '').lower()
    title_score = 0
    if any(term in job_title for term in ['ceo', 'founder', 'president', 'owner']):
        title_score = 40
    elif any(term in job_title for term in ['cto', 'cfo', 'coo', 'vp', 'vice president', 'chief']):
        title_score = 35
    elif any(term in job_title for term in ['director', 'head of']):
        title_score = 25
    elif any(term in job_title for term in ['manager', 'lead']):
        title_score = 15
    else:
        title_score = 5
    
    breakdown['title_score'] = title_score
    score += title_score
    
    # Contact Completeness (0-30 points)
    contact_score = 0
    if lead_data.get('email'):
        contact_score += 10
    if lead_data.get('phone'):
        contact_score += 10
    if lead_data.get('linkedin_url'):
        contact_score += 10
    
    breakdown['contact_score'] = contact_score
    score += contact_score
    
    # Engagement/Status (0-30 points)
    status = lead_data.get('status', LeadStatus.NEW)
    status_score = {
        LeadStatus.NEW: 5,
        LeadStatus.CONTACTED: 10,
        LeadStatus.QUALIFIED: 20,
        LeadStatus.PROPOSAL: 25,
        LeadStatus.AGREEMENT: 30,
        LeadStatus.CLOSED: 30,
        LeadStatus.LOST: 0
    }.get(status, 5)
    
    breakdown['engagement_score'] = status_score
    score += status_score
    
    breakdown['total'] = score
    return score, breakdown


async def auto_create_kickoff_from_won_deal(
    db, 
    lead: dict, 
    current_user: User,
    background_tasks: BackgroundTasks = None
) -> dict:
    """
    Automatically create a kickoff request when a lead is marked as closed_won.
    
    GOVERNANCE:
    - Prevents duplicate kickoff requests for the same lead
    - Links to existing agreement if available
    - Sends notification to Principal Consultant
    
    Returns:
        dict with kickoff_id if created, or existing kickoff info if already exists
    """
    lead_id = lead.get("id")
    
    # Check for existing kickoff request (duplicate prevention)
    existing_kickoff = await db.kickoff_requests.find_one(
        {"lead_id": lead_id},
        {"_id": 0, "id": 1, "status": 1, "project_id": 1}
    )
    
    if existing_kickoff:
        return {
            "action": "skipped",
            "reason": "Kickoff request already exists",
            "kickoff_id": existing_kickoff.get("id"),
            "kickoff_status": existing_kickoff.get("status"),
            "project_id": existing_kickoff.get("project_id")
        }
    
    # Get agreement if exists
    agreement = await db.agreements.find_one(
        {"lead_id": lead_id},
        {"_id": 0, "id": 1, "agreement_number": 1, "total_value": 1, "status": 1}
    )
    
    # Get client info
    client = None
    if lead.get("client_id"):
        client = await db.clients.find_one(
            {"id": lead.get("client_id")},
            {"_id": 0, "id": 1, "company_name": 1}
        )
    
    # Find Principal Consultant to assign
    principal = await db.users.find_one(
        {"role": {"$in": ["principal_consultant", "admin"]}},
        {"_id": 0, "id": 1, "full_name": 1, "email": 1}
    )
    
    now = datetime.now(timezone.utc).isoformat()
    kickoff_id = str(uuid.uuid4())
    
    # Create kickoff request
    kickoff_doc = {
        "id": kickoff_id,
        "lead_id": lead_id,
        "agreement_id": agreement.get("id") if agreement else None,
        "agreement_number": agreement.get("agreement_number") if agreement else None,
        "client_id": lead.get("client_id") or (client.get("id") if client else None),
        "client_name": lead.get("company") or (client.get("company_name") if client else ""),
        "contact_person": lead.get("first_name", "") + " " + lead.get("last_name", ""),
        "contact_email": lead.get("email"),
        "contact_phone": lead.get("phone"),
        "project_name": f"{lead.get('company', 'New')} Consulting Project",
        "project_description": lead.get("requirements") or lead.get("notes") or "Auto-created from won deal",
        "estimated_value": agreement.get("total_value") if agreement else lead.get("budget"),
        "expected_start_date": None,  # To be confirmed by client
        "expected_duration_months": 3,  # Default
        "assigned_consultant_id": principal.get("id") if principal else None,
        "assigned_consultant_name": principal.get("full_name") if principal else None,
        "status": "pending",  # Pending Principal Consultant approval
        "source": "auto_from_won_deal",  # Track auto-creation
        "created_by": current_user.id,
        "created_by_name": current_user.full_name,
        "created_at": now,
        "updated_at": now
    }
    
    await db.kickoff_requests.insert_one(kickoff_doc)
    
    # Update lead with kickoff reference
    await db.leads.update_one(
        {"id": lead_id},
        {"$set": {
            "kickoff_id": kickoff_id,
            "kickoff_created_at": now,
            "updated_at": now
        }}
    )
    
    # Audit log
    await log_audit(
        action="lead.auto_kickoff_created",
        entity_type="kickoff_request",
        entity_id=kickoff_id,
        performed_by=current_user.id,
        after_state={
            "lead_id": lead_id,
            "status": "pending",
            "source": "auto_from_won_deal"
        },
        metadata={
            "lead_company": lead.get("company"),
            "has_agreement": agreement is not None,
            "assigned_to": principal.get("full_name") if principal else None
        }
    )
    
    # Send notification to Principal Consultant
    if principal and background_tasks:
        from services.notification_service import create_notification
        notification_data = {
            "user_id": principal.get("id"),
            "title": "New Kickoff Request (Auto-Created)",
            "message": f"Deal won: {lead.get('company')} - Kickoff request created automatically. Please review and approve.",
            "type": "kickoff_request",
            "entity_type": "kickoff_request",
            "entity_id": kickoff_id,
            "priority": "high"
        }
        background_tasks.add_task(create_notification, notification_data)
    
    return {
        "action": "created",
        "kickoff_id": kickoff_id,
        "assigned_to": principal.get("full_name") if principal else None,
        "status": "pending"
    }


@router.post("", response_model=Lead)
async def create_lead(lead_create: LeadCreate, current_user: User = Depends(get_current_user)):
    """Create a new lead with duplicate detection."""
    db = get_db()
    
    # RBAC Migration: Check if manager-only role (view-only)
    manager_roles = get_role_group("MANAGER_ROLES", fail_closed=False) or []
    sales_exec_roles = get_role_group("SALES_EXECUTIVE_ROLES", fail_closed=False) or ['executive', 'sales_executive']
    if current_user.role in manager_roles and not has_role(current_user.role, sales_exec_roles):
        raise HTTPException(status_code=403, detail="Managers can only view and download")
    
    lead_dict = lead_create.model_dump()
    
    # SSOT: Check for duplicates before creating
    from services.lead_ssot_service import check_duplicate_lead
    duplicate_result = await check_duplicate_lead(
        db,
        email=lead_dict.get("email"),
        phone=lead_dict.get("phone"),
        company=lead_dict.get("company")
    )
    
    if duplicate_result["has_duplicates"]:
        # Return duplicate warning with existing lead info
        raise HTTPException(
            status_code=409,
            detail={
                "message": "Potential duplicate lead found",
                "duplicates": duplicate_result["duplicates"],
                "existing_lead_id": duplicate_result["duplicates"][0]["existing_lead"]["id"],
                "suggestion": "Consider using the existing lead instead of creating a duplicate"
            }
        )
    
    # Calculate lead score
    score, breakdown = calculate_lead_score(lead_dict)
    
    # Get employee info for better tracking
    employee = await db.employees.find_one({"user_id": current_user.id}, {"employee_id": 1, "first_name": 1, "last_name": 1, "_id": 0})
    
    lead = Lead(**lead_dict, created_by=current_user.id, lead_score=score, score_breakdown=breakdown)
    
    doc = lead.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    if doc['enriched_at']:
        doc['enriched_at'] = doc['enriched_at'].isoformat()
    
    # Add employee tracking info - from employee record or user record
    if employee:
        doc['created_by_employee_id'] = employee.get('employee_id')
        doc['created_by_name'] = f"{employee.get('first_name', '')} {employee.get('last_name', '')}".strip()
    elif current_user.employee_id:
        # Fallback to user's employee_id if no employee record exists
        doc['created_by_employee_id'] = current_user.employee_id
        doc['created_by_name'] = current_user.full_name
    
    await db.leads.insert_one(doc)
    
    # Real-time WebSocket notification
    await notify_lead_update(lead.id, "create", current_user.id)
    await notify_dashboard_refresh(current_user.id)
    
    # Invalidate Redis cache
    await CacheInvalidation.leads()
    
    return lead


@router.get("")
async def get_leads(
    status: Optional[str] = None,
    assigned_to: Optional[str] = None,
    search: Optional[str] = Query(None, description="Search in name, company, email"),
    source: Optional[str] = Query(None, description="Lead source filter"),
    industry: Optional[str] = Query(None, description="Industry filter"),
    deal_value_min: Optional[float] = Query(None, description="Minimum deal value"),
    deal_value_max: Optional[float] = Query(None, description="Maximum deal value"),
    created_from: Optional[str] = Query(None, description="Created date from (YYYY-MM-DD)"),
    created_to: Optional[str] = Query(None, description="Created date to (YYYY-MM-DD)"),
    days_since_activity: Optional[int] = Query(None, description="Days since last activity (stuck deals)"),
    sort_field: Optional[str] = Query("created_at", description="Sort field"),
    sort_direction: Optional[str] = Query("desc", description="Sort direction (asc/desc)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE, description="Items per page"),
    current_user: User = Depends(get_current_user)
):
    """Get all leads with advanced filters and pagination.
    
    SALES DATATABLE API - Supports Excel-like filtering:
    - Text search: name, company, email
    - Dropdown filters: status, assigned_to, source, industry
    - Range filters: deal_value_min/max
    - Date range: created_from/to
    - Stuck deals: days_since_activity
    
    Access: sales_*, admin
    
    Data scoping by hierarchy:
    - Admin: sees all leads
    - HR Manager: sees all leads  
    - Manager/Executive: sees own leads + team leads (reportees)
    """
    db = get_db()
    
    # RBAC Migration: Role-based access check
    leads_access_roles = get_leads_access_roles()
    if not has_role(current_user.role, leads_access_roles):
        raise HTTPException(status_code=403, detail="Access denied. Only sales team and admin can view leads.")
    
    query = {}
    
    # Basic filters
    if status:
        query['status'] = status
    if assigned_to:
        query['assigned_to'] = assigned_to
    if source:
        query['source'] = source
    if industry:
        query['industry'] = industry
    
    # Text search (case-insensitive)
    if search:
        search_regex = {"$regex": search, "$options": "i"}
        query["$or"] = [
            {"first_name": search_regex},
            {"last_name": search_regex},
            {"company": search_regex},
            {"email": search_regex},
            {"phone": search_regex}
        ]
    
    # Deal value range
    if deal_value_min is not None or deal_value_max is not None:
        value_query = {}
        if deal_value_min is not None:
            value_query["$gte"] = deal_value_min
        if deal_value_max is not None:
            value_query["$lte"] = deal_value_max
        query["deal_value"] = value_query
    
    # Date range filter
    if created_from or created_to:
        date_query = {}
        if created_from:
            date_query["$gte"] = datetime.fromisoformat(created_from + "T00:00:00")
        if created_to:
            date_query["$lte"] = datetime.fromisoformat(created_to + "T23:59:59")
        query["created_at"] = date_query
    
    # Stuck deals filter (no activity in X days)
    if days_since_activity:
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_since_activity)
        query["$and"] = query.get("$and", []) + [
            {"$or": [
                {"updated_at": {"$lt": cutoff_date}},
                {"updated_at": {"$exists": False}}
            ]}
        ]
    
    # RBAC Migration: Data scoping by role and hierarchy
    hr_admin_roles = get_role_group("HR_ADMIN_ROLES", fail_closed=False) or ['admin', 'hr_manager']
    if not has_role(current_user.role, hr_admin_roles):
        # Get current user's employee record
        user_employee = await db.employees.find_one(
            {"user_id": current_user.id}, 
            {"id": 1, "employee_id": 1, "_id": 0}
        )
        
        # Get IDs of reportees (employees who report to this user)
        reportee_user_ids = []
        if user_employee:
            emp_id = user_employee.get("employee_id")
            emp_internal_id = user_employee.get("id")
            
            # Find employees who report to this person
            if emp_id or emp_internal_id:
                reportees = await db.employees.find(
                    {
                        "$or": [
                            {"reporting_manager_id": emp_id},
                            {"reporting_manager_id": emp_internal_id}
                        ]
                    },
                    {"user_id": 1, "_id": 0}
                ).to_list(1000)
                reportee_user_ids = [r.get("user_id") for r in reportees if r.get("user_id")]
        
        # Build scoped query: own leads + team leads
        user_ids_to_include = [current_user.id] + reportee_user_ids
        if 'assigned_to' not in query:
            query['$or'] = [
                {"assigned_to": {"$in": user_ids_to_include}},
                {"created_by": {"$in": user_ids_to_include}}
            ]
    
    # Sorting
    sort_order = -1 if sort_direction == "desc" else 1
    valid_sort_fields = ["created_at", "updated_at", "company", "status", "deal_value", "first_name"]
    if sort_field not in valid_sort_fields:
        sort_field = "created_at"
    
    # Pagination
    params = PaginationParams(page=page, page_size=page_size, sort_by=sort_field, sort_order=sort_direction)
    
    # Get total count and paginated results
    total = await db.leads.count_documents(query)
    leads = await db.leads.find(
        query, 
        {"_id": 0}
    ).sort(sort_field, sort_order).skip(params.skip).limit(params.page_size).to_list(params.page_size)
    
    for lead in leads:
        if isinstance(lead.get('created_at'), str):
            lead['created_at'] = datetime.fromisoformat(lead['created_at'])
        if isinstance(lead.get('updated_at'), str):
            lead['updated_at'] = datetime.fromisoformat(lead['updated_at'])
        if lead.get('enriched_at') and isinstance(lead['enriched_at'], str):
            lead['enriched_at'] = datetime.fromisoformat(lead['enriched_at'])
    
    # Auto-sync funnel stage with lead status for accurate display
    FUNNEL_STATUS_MAP = {
        "lead_capture": LeadStatus.NEW,
        "record_meeting": LeadStatus.CONTACTED,
        "pricing_plan": LeadStatus.QUALIFIED,
        "scope_of_work": LeadStatus.QUALIFIED,
        "quotation": LeadStatus.PROPOSAL,
        "agreement": LeadStatus.AGREEMENT,
    }
    for lead in leads:
        lead_id = lead.get("id")
        current_status = lead.get("status", LeadStatus.NEW)
        # Skip if already in terminal state
        if current_status in ["won", "lost", "closed_won", "closed_lost", "paused"]:
            continue
        
        # Quick check for furthest completed step
        expected_status = LeadStatus.NEW
        if lead_id:
            has_meeting = await db.meetings.find_one({"lead_id": lead_id}, {"_id": 0, "id": 1})
            if has_meeting:
                expected_status = LeadStatus.CONTACTED
                has_pricing = await db.pricing_plans.find_one({"lead_id": lead_id}, {"_id": 0, "id": 1})
                if has_pricing:
                    expected_status = LeadStatus.QUALIFIED
                    has_sow = await db.enhanced_sows.find_one({"lead_id": lead_id}, {"_id": 0, "id": 1})
                    if not has_sow:
                        has_sow = await db.sows.find_one({"lead_id": lead_id}, {"_id": 0, "id": 1})
                    if has_sow:
                        has_quotation = await db.quotations.find_one({"lead_id": lead_id}, {"_id": 0, "id": 1})
                        if has_quotation:
                            expected_status = LeadStatus.PROPOSAL
                            has_agreement = await db.agreements.find_one({"lead_id": lead_id}, {"_id": 0, "id": 1})
                            if has_agreement:
                                expected_status = LeadStatus.AGREEMENT
            
            if current_status != expected_status:
                await db.leads.update_one(
                    {"id": lead_id},
                    {"$set": {"status": expected_status, "updated_at": datetime.now(timezone.utc).isoformat()}}
                )
                lead["status"] = expected_status
    
    # Return standardized response for SalesDataTable
    return {
        "data": leads,
        "total": total,
        "page": params.page,
        "page_size": params.page_size,
        "total_pages": (total + params.page_size - 1) // params.page_size if total > 0 else 1
    }


@router.get("/all")
async def get_all_leads(
    status: Optional[str] = None,
    assigned_to: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """
    Get all leads without pagination (for dropdowns, exports, etc).
    Limited to 1000 results.
    """
    db = get_db()
    
    leads_access_roles = get_leads_access_roles()
    if not has_role(current_user.role, leads_access_roles):
        raise HTTPException(status_code=403, detail="Access denied.")
    
    query = {}
    if status:
        query['status'] = status
    if assigned_to:
        query['assigned_to'] = assigned_to
    
    hr_admin_roles = get_role_group("HR_ADMIN_ROLES", fail_closed=False) or ['admin', 'hr_manager']
    if not has_role(current_user.role, hr_admin_roles):
        query['$or'] = [
            {"assigned_to": current_user.id},
            {"created_by": current_user.id}
        ]
    
    leads = await db.leads.find(query, {"_id": 0}).to_list(1000)
    return leads


@router.get("/progress/bulk")
async def get_all_leads_progress(current_user: User = Depends(get_current_user)):
    """
    Get funnel progress for all leads accessible to the user.
    Returns a simplified progress summary for each lead for list display.
    """
    db = get_db()
    
    # Define funnel steps
    FUNNEL_STEPS = [
        "lead_capture", "record_meeting", "pricing_plan", "scope_of_work",
        "quotation", "agreement", "record_payment", "kickoff_request", "project_created"
    ]
    
    # RBAC Migration: Get accessible leads based on role
    query = {}
    hr_admin_roles = get_role_group("HR_ADMIN_ROLES", fail_closed=False) or ['admin', 'hr_manager']
    if not has_role(current_user.role, hr_admin_roles):
        user_employee = await db.employees.find_one(
            {"user_id": current_user.id}, 
            {"id": 1, "employee_id": 1, "_id": 0}
        )
        reportee_user_ids = []
        if user_employee:
            emp_id = user_employee.get("employee_id")
            emp_internal_id = user_employee.get("id")
            if emp_id or emp_internal_id:
                reportees = await db.employees.find(
                    {"$or": [{"reporting_manager_id": emp_id}, {"reporting_manager_id": emp_internal_id}]},
                    {"user_id": 1, "_id": 0}
                ).to_list(1000)
                reportee_user_ids = [r.get("user_id") for r in reportees if r.get("user_id")]
        
        user_ids_to_include = [current_user.id] + reportee_user_ids
        query['$or'] = [
            {"assigned_to": {"$in": user_ids_to_include}},
            {"created_by": {"$in": user_ids_to_include}}
        ]
    
    leads = await db.leads.find(query, {"id": 1, "_id": 0}).to_list(1000)
    lead_ids = [lead["id"] for lead in leads]
    
    # Fetch related data in bulk
    meetings = await db.meetings.find({"lead_id": {"$in": lead_ids}}, {"lead_id": 1, "_id": 0}).to_list(10000)
    pricing_plans = await db.pricing_plans.find({"lead_id": {"$in": lead_ids}}, {"lead_id": 1, "_id": 0}).to_list(1000)
    sows = await db.sows.find({"lead_id": {"$in": lead_ids}}, {"lead_id": 1, "_id": 0}).to_list(1000)
    enhanced_sows = await db.enhanced_sows.find({"lead_id": {"$in": lead_ids}}, {"lead_id": 1, "_id": 0}).to_list(1000)
    quotations = await db.quotations.find({"lead_id": {"$in": lead_ids}}, {"lead_id": 1, "_id": 0}).to_list(1000)
    agreements = await db.agreements.find({"lead_id": {"$in": lead_ids}}, {"lead_id": 1, "status": 1, "_id": 0}).to_list(1000)
    kickoffs = await db.kickoff_requests.find({"lead_id": {"$in": lead_ids}}, {"lead_id": 1, "status": 1, "project_id": 1, "_id": 0}).to_list(1000)
    
    # Create lookup sets
    meeting_leads = set(m["lead_id"] for m in meetings)
    pricing_leads = set(p["lead_id"] for p in pricing_plans)
    sow_leads = set(s["lead_id"] for s in sows) | set(s["lead_id"] for s in enhanced_sows)
    quotation_leads = set(q["lead_id"] for q in quotations)
    agreement_map = {a["lead_id"]: a for a in agreements}
    kickoff_map = {k["lead_id"]: k for k in kickoffs}
    
    # Build progress map
    progress_map = {}
    for lead_id in lead_ids:
        completed_steps = ["lead_capture"]  # Always complete
        
        if lead_id in meeting_leads:
            completed_steps.append("record_meeting")
        if lead_id in pricing_leads:
            completed_steps.append("pricing_plan")
        if lead_id in sow_leads:
            completed_steps.append("scope_of_work")
        if lead_id in quotation_leads:
            completed_steps.append("quotation")
        
        agreement = agreement_map.get(lead_id)
        if agreement:
            completed_steps.append("agreement")
            if agreement.get("status") == "approved":
                # Could add payment check here
                pass
        
        kickoff = kickoff_map.get(lead_id)
        if kickoff:
            completed_steps.append("kickoff_request")
            if kickoff.get("status") in ["approved", "accepted", "converted"] and kickoff.get("project_id"):
                completed_steps.append("project_created")
        
        # Calculate current stage
        completed_count = len(completed_steps)
        current_step_index = min(completed_count, len(FUNNEL_STEPS) - 1)
        current_step = FUNNEL_STEPS[current_step_index]
        
        progress_map[lead_id] = {
            "completed_steps": completed_steps,
            "completed_count": completed_count,
            "total_steps": len(FUNNEL_STEPS),
            "current_step": current_step,
            "progress_percentage": round((completed_count / len(FUNNEL_STEPS)) * 100, 1),
            # Simplified flags for UI
            "meeting": "record_meeting" in completed_steps,
            "pricing": "pricing_plan" in completed_steps,
            "sow": "scope_of_work" in completed_steps,
            "quotation": "quotation" in completed_steps,
            "agreement": "agreement" in completed_steps,
            "kickoff": "kickoff_request" in completed_steps,
            "project": "project_created" in completed_steps,
            "current_stage": completed_count
        }
    
    return progress_map


@router.get("/{lead_id}", response_model=Lead)
async def get_lead(lead_id: str, current_user: User = Depends(get_current_user)):
    """Get a single lead by ID.
    
    Access control:
    - Admin/HR Manager: can access any lead
    - Others: can only access own leads or team leads
    """
    db = get_db()
    lead_data = await db.leads.find_one({"id": lead_id}, {"_id": 0})
    if not lead_data:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    # RBAC Migration: Check access based on hierarchy
    hr_admin_roles = get_role_group("HR_ADMIN_ROLES", fail_closed=False) or ['admin', 'hr_manager']
    if not has_role(current_user.role, hr_admin_roles):
        # Get accessible user IDs (self + reportees)
        accessible_user_ids = [current_user.id]
        
        user_employee = await db.employees.find_one(
            {"user_id": current_user.id}, 
            {"id": 1, "employee_id": 1, "_id": 0}
        )
        
        if user_employee:
            emp_id = user_employee.get("employee_id")
            emp_internal_id = user_employee.get("id")
            if emp_id or emp_internal_id:
                reportees = await db.employees.find(
                    {
                        "$or": [
                            {"reporting_manager_id": emp_id},
                            {"reporting_manager_id": emp_internal_id}
                        ]
                    },
                    {"user_id": 1, "_id": 0}
                ).to_list(1000)
                accessible_user_ids.extend([r.get("user_id") for r in reportees if r.get("user_id")])
        
        # Check if lead belongs to accessible users
        # Check by user ID, employee_id, or created_by_employee_id
        accessible_employee_ids = [current_user.employee_id] if current_user.employee_id else []
        if user_employee:
            accessible_employee_ids.append(user_employee.get("employee_id"))
        
        lead_assigned_to = lead_data.get('assigned_to')
        lead_created_by = lead_data.get('created_by')
        lead_created_by_employee_id = lead_data.get('created_by_employee_id')
        
        # Access check: user can access if they created it, are assigned to it, or their employee_id matches
        is_owner = lead_created_by in accessible_user_ids or lead_assigned_to in accessible_user_ids
        is_employee_match = lead_created_by_employee_id in accessible_employee_ids if lead_created_by_employee_id else False
        
        if not is_owner and not is_employee_match:
            raise HTTPException(status_code=403, detail="You don't have access to this lead")
    
    if isinstance(lead_data.get('created_at'), str):
        lead_data['created_at'] = datetime.fromisoformat(lead_data['created_at'])
    if isinstance(lead_data.get('updated_at'), str):
        lead_data['updated_at'] = datetime.fromisoformat(lead_data['updated_at'])
    if lead_data.get('enriched_at') and isinstance(lead_data['enriched_at'], str):
        lead_data['enriched_at'] = datetime.fromisoformat(lead_data['enriched_at'])
    
    return Lead(**lead_data)


@router.put("/{lead_id}", response_model=Lead)
@router.patch("/{lead_id}", response_model=Lead)
async def update_lead(
    lead_id: str,
    lead_update: LeadUpdate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    """
    Update a lead.
    
    GOVERNANCE: If stage changes to 'closed_won', automatically creates a kickoff request
    for seamless Sales to Consulting handoff.
    """
    db = get_db()
    if current_user.role == UserRole.MANAGER:
        raise HTTPException(status_code=403, detail="Managers can only view and download")
    
    lead_data = await db.leads.find_one({"id": lead_id}, {"_id": 0})
    if not lead_data:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    update_data = lead_update.model_dump(exclude_unset=True)
    update_data['updated_at'] = datetime.now(timezone.utc).isoformat()
    
    # Track status change for auto-kickoff (closed_won triggers kickoff)
    old_status = lead_data.get("status")
    new_status = update_data.get("status")
    status_changed_to_won = (
        new_status and 
        new_status.lower() in ["closed_won", "closedwon", "won"] and
        old_status != new_status
    )
    
    # A4: LEAD STAGE VALIDATION - Prevent skipping stages
    # Valid progression: new → contacted → qualified → proposal → negotiation → closed_won
    if status_changed_to_won:
        valid_pre_won_stages = ["negotiation", "proposal", "qualified"]
        if old_status and old_status.lower() not in valid_pre_won_stages:
            raise HTTPException(
                status_code=400,
                detail=f"A4: Cannot mark lead as won from '{old_status}' stage. Lead must progress through proper stages (qualified → proposal → negotiation → closed_won)."
            )
    
    # Recalculate lead score with updated data
    merged_data = {**lead_data, **update_data}
    score, breakdown = calculate_lead_score(merged_data)
    update_data['lead_score'] = score
    update_data['score_breakdown'] = breakdown
    
    await db.leads.update_one({"id": lead_id}, {"$set": update_data})
    
    # Real-time WebSocket notification
    await notify_lead_update(lead_id, "update", current_user.id)
    
    # Invalidate Redis cache for this lead
    await CacheInvalidation.lead(lead_id)
    
    # AUTO-KICKOFF: If deal is won, create kickoff request
    kickoff_result = None
    if status_changed_to_won:
        updated_lead = await db.leads.find_one({"id": lead_id}, {"_id": 0})
        kickoff_result = await auto_create_kickoff_from_won_deal(
            db, updated_lead, current_user, background_tasks
        )
        
        # Add kickoff info to update response
        if kickoff_result.get("action") == "created":
            await db.leads.update_one(
                {"id": lead_id},
                {"$set": {"auto_kickoff_result": kickoff_result}}
            )
    
    updated_lead_data = await db.leads.find_one({"id": lead_id}, {"_id": 0})
    if isinstance(updated_lead_data.get('created_at'), str):
        updated_lead_data['created_at'] = datetime.fromisoformat(updated_lead_data['created_at'])
    if isinstance(updated_lead_data.get('updated_at'), str):
        updated_lead_data['updated_at'] = datetime.fromisoformat(updated_lead_data['updated_at'])
    if updated_lead_data.get('enriched_at') and isinstance(updated_lead_data['enriched_at'], str):
        updated_lead_data['enriched_at'] = datetime.fromisoformat(updated_lead_data['enriched_at'])
    
    # Include kickoff result in response metadata
    if kickoff_result:
        updated_lead_data['_kickoff_result'] = kickoff_result
    
    return Lead(**updated_lead_data)


@router.delete("/{lead_id}")
async def delete_lead(lead_id: str, current_user: User = Depends(get_current_user)):
    """
    Delete a lead (admin only - critical operation).
    Uses RBAC service for authorization.
    """
    db = get_db()
    
    # RBAC check - admin only for lead deletion
    admin_roles = get_role_group("ADMIN_ROLES", fail_closed=True)
    if not admin_roles or not has_role(current_user.role, admin_roles):
        raise HTTPException(status_code=403, detail="Only admins can delete leads")
    
    result = await db.leads.delete_one({"id": lead_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Lead not found")
    return {"message": "Lead deleted successfully"}


class ReassignLeadRequest(BaseModel):
    new_owner_id: str
    reason: Optional[str] = None
    transfer_all_data: bool = True  # Transfer meetings, pricing, SOW, etc.

class BulkReassignRequest(BaseModel):
    from_user_id: str
    to_user_id: str
    reason: Optional[str] = None


@router.post("/{lead_id}/reassign")
async def reassign_lead(
    lead_id: str,
    data: ReassignLeadRequest,
    current_user: User = Depends(get_current_user)
):
    """Reassign a lead (and all associated data) to another sales person.
    Access: managers/admins can reassign directly, sales can initiate."""
    db = get_db()
    
    lead = await db.leads.find_one({"id": lead_id}, {"_id": 0})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    # Get new owner info
    new_owner = await db.users.find_one({"id": data.new_owner_id}, {"_id": 0, "id": 1, "full_name": 1, "email": 1})
    if not new_owner:
        raise HTTPException(status_code=404, detail="New owner not found")
    
    now = datetime.now(timezone.utc).isoformat()
    old_owner_name = lead.get("assigned_to_name", lead.get("lead_owner_name", "Unknown"))
    new_owner_name = new_owner.get("full_name", "Unknown")
    
    # Update lead ownership
    await db.leads.update_one(
        {"id": lead_id},
        {"$set": {
            "assigned_to": data.new_owner_id,
            "lead_owner": data.new_owner_id,
            "assigned_to_name": new_owner_name,
            "updated_at": now,
        },
        "$push": {"activity_log": {
            "action": "reassigned",
            "date": now,
            "by": current_user.full_name,
            "by_id": current_user.id,
            "details": f"Lead reassigned from {old_owner_name} to {new_owner_name}. Reason: {data.reason or 'N/A'}",
        }}}
    )
    
    transfer_results = {"lead": True}
    
    if data.transfer_all_data:
        # Transfer all associated data
        collections_to_transfer = [
            ("follow_ups", "assigned_to"),
            ("meetings", "created_by"),
            ("pricing_plans", "created_by"),
            ("sows", "created_by"),
            ("enhanced_sows", "created_by"),
            ("quotations", "created_by"),
            ("agreements", "created_by"),
        ]
        
        for collection_name, owner_field in collections_to_transfer:
            collection = db[collection_name]
            r = await collection.update_many(
                {"lead_id": lead_id},
                {"$set": {owner_field: data.new_owner_id, "updated_at": now}}
            )
            transfer_results[collection_name] = r.modified_count
        
        # Also update assigned_to_name in follow_ups
        await db.follow_ups.update_many(
            {"lead_id": lead_id},
            {"$set": {"assigned_to_name": new_owner_name}}
        )
    
    return {
        "message": f"Lead reassigned to {new_owner_name}",
        "transfer_results": transfer_results,
        "lead_id": lead_id,
        "new_owner": new_owner_name,
    }


@router.post("/bulk-reassign")
async def bulk_reassign_leads(
    data: BulkReassignRequest,
    current_user: User = Depends(get_current_user)
):
    """Bulk reassign ALL leads from one user to another.
    Use case: sales person resignation/role change.
    Access: managers and admins only."""
    db = get_db()
    
    # Only managers/admins can bulk reassign
    manager_roles = ["sales_manager", "manager", "principal_consultant", "admin"]
    if current_user.role not in manager_roles:
        raise HTTPException(status_code=403, detail="Only managers/admins can bulk reassign leads")
    
    # Validate users
    from_user = await db.users.find_one({"id": data.from_user_id}, {"_id": 0, "id": 1, "full_name": 1})
    to_user = await db.users.find_one({"id": data.to_user_id}, {"_id": 0, "id": 1, "full_name": 1})
    
    if not from_user:
        raise HTTPException(status_code=404, detail="Source user not found")
    if not to_user:
        raise HTTPException(status_code=404, detail="Target user not found")
    
    now = datetime.now(timezone.utc).isoformat()
    from_name = from_user.get("full_name", "Unknown")
    to_name = to_user.get("full_name", "Unknown")
    
    # Find all leads owned by from_user
    leads = await db.leads.find(
        {"$or": [
            {"assigned_to": data.from_user_id},
            {"lead_owner": data.from_user_id},
            {"created_by": data.from_user_id},
        ]},
        {"_id": 0, "id": 1}
    ).to_list(10000)
    
    lead_ids = [l["id"] for l in leads]
    
    if not lead_ids:
        return {"message": f"No leads found for {from_name}", "transferred_count": 0}
    
    # Transfer all leads
    r = await db.leads.update_many(
        {"id": {"$in": lead_ids}},
        {"$set": {
            "assigned_to": data.to_user_id,
            "lead_owner": data.to_user_id,
            "assigned_to_name": to_name,
            "updated_at": now,
        },
        "$push": {"activity_log": {
            "action": "bulk_reassigned",
            "date": now,
            "by": current_user.full_name,
            "by_id": current_user.id,
            "details": f"Bulk reassigned from {from_name} to {to_name}. Reason: {data.reason or 'Migration'}",
        }}}
    )
    
    transfer_results = {"leads": r.modified_count}
    
    # Transfer all associated data for these leads
    collections_to_transfer = [
        ("follow_ups", "assigned_to"),
        ("meetings", "created_by"),
        ("pricing_plans", "created_by"),
        ("sows", "created_by"),
        ("enhanced_sows", "created_by"),
        ("quotations", "created_by"),
        ("agreements", "created_by"),
    ]
    
    for collection_name, owner_field in collections_to_transfer:
        collection = db[collection_name]
        r2 = await collection.update_many(
            {"lead_id": {"$in": lead_ids}},
            {"$set": {owner_field: data.to_user_id, "updated_at": now}}
        )
        transfer_results[collection_name] = r2.modified_count
    
    # Update follow-up names
    await db.follow_ups.update_many(
        {"lead_id": {"$in": lead_ids}},
        {"$set": {"assigned_to_name": to_name}}
    )
    
    return {
        "message": f"Successfully transferred {len(lead_ids)} leads from {from_name} to {to_name}",
        "transferred_count": len(lead_ids),
        "transfer_results": transfer_results,
    }



@router.get("/{lead_id}/suggestions")
async def get_lead_suggestions(lead_id: str, current_user: User = Depends(get_current_user)):
    """Get AI-powered suggestions for a lead."""
    db = get_db()
    lead = await db.leads.find_one({"id": lead_id}, {"_id": 0})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    # Import here to avoid circular dependencies
    from email_templates import check_lead_for_suggestions
    return check_lead_for_suggestions(lead)


@router.post("/{lead_id}/generate-email")
async def generate_email_for_lead(
    lead_id: str,
    template_name: str,
    current_user: User = Depends(get_current_user)
):
    """Generate an email for a lead using a template."""
    db = get_db()
    lead = await db.leads.find_one({"id": lead_id}, {"_id": 0})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    template = await db.email_templates.find_one({"name": template_name}, {"_id": 0})
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    from email_templates import generate_email_from_template
    email_content = generate_email_from_template(template, lead)
    return email_content



# Stage mapping for sales funnel
STAGE_MAPPING = {
    "lead": "LEAD",
    "new": "LEAD",
    "meeting": "MEETING",
    "meeting_scheduled": "MEETING",
    "meeting_done": "MEETING",
    "pricing": "PRICING",
    "pricing_sent": "PRICING",
    "sow": "SOW",
    "sow_sent": "SOW",
    "quotation": "QUOTATION",
    "quotation_sent": "QUOTATION",
    "agreement": "AGREEMENT",
    "agreement_sent": "AGREEMENT",
    "payment": "PAYMENT",
    "payment_pending": "PAYMENT",
    "payment_received": "PAYMENT",
    "kickoff": "KICKOFF",
    "kickoff_pending": "KICKOFF",
    "closed": "CLOSED",
    "won": "CLOSED",
    "project_created": "CLOSED"
}

STAGE_ORDER = ["LEAD", "MEETING", "PRICING", "SOW", "QUOTATION", "AGREEMENT", "PAYMENT", "KICKOFF", "CLOSED"]
STAGE_NAMES = {
    "LEAD": "Lead",
    "MEETING": "Meeting",
    "PRICING": "Pricing Plan",
    "SOW": "SOW",
    "QUOTATION": "Quotation",
    "AGREEMENT": "Agreement",
    "PAYMENT": "Payment",
    "KICKOFF": "Kickoff",
    "CLOSED": "Closed"
}


@router.get("/{lead_id}/stage")
async def get_lead_stage(
    lead_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get the current sales funnel stage of a lead"""
    db = get_db()
    
    lead = await db.leads.find_one({"id": lead_id}, {"_id": 0})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    # Get current stage
    raw_stage = lead.get("stage", "lead")
    current_stage = STAGE_MAPPING.get(raw_stage.lower(), "LEAD")
    current_idx = STAGE_ORDER.index(current_stage) if current_stage in STAGE_ORDER else 0
    
    # Build stage status
    stages = []
    for i, stage in enumerate(STAGE_ORDER):
        stages.append({
            "stage": stage,
            "name": STAGE_NAMES.get(stage, stage),
            "is_completed": i < current_idx,
            "is_current": i == current_idx,
            "is_locked": i > current_idx
        })
    
    return {
        "lead_id": lead_id,
        "company_name": lead.get("company_name"),
        "current_stage": current_stage,
        "current_stage_name": STAGE_NAMES.get(current_stage, current_stage),
        "stage_index": current_idx,
        "raw_stage": raw_stage,
        "stages": stages
    }


@router.get("/{lead_id}/funnel-progress")
async def get_lead_funnel_progress(lead_id: str, current_user: User = Depends(get_current_user)):
    """
    Get the sales funnel progress for a lead.
    Returns completed steps, current step, overall progress, and linked IDs for all steps.
    """
    db = get_db()
    
    lead = await db.leads.find_one({"id": lead_id}, {"_id": 0})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    # Define funnel steps mapping
    FUNNEL_STEPS = [
        "lead_capture",
        "record_meeting", 
        "pricing_plan",
        "scope_of_work",
        "quotation",
        "agreement",
        "record_payment",
        "kickoff_request",
        "project_created"
    ]
    
    # Determine completed steps based on lead data
    completed_steps = []
    
    # Track linked IDs for each step
    linked_data = {
        "lead_id": lead_id,
        "meeting_ids": [],
        "meeting_count": 0,
        "last_meeting_date": None,
        "pricing_plan_id": None,
        "pricing_plan_total": 0,
        "sow_id": None,
        "sow_items_count": 0,
        "quotation_id": None,
        "quotation_number": None,
        "agreement_id": None,
        "agreement_number": None,
        "agreement_status": None,
        "total_paid": 0,
        "payment_count": 0,
        "kickoff_id": None,
        "kickoff_status": None,
        "project_id": None,
        "project_name": None
    }
    
    # Step 1: Lead Capture - always complete if lead exists
    completed_steps.append("lead_capture")
    
    # Step 2: Meeting - check if meetings exist with MOM
    meetings = await db.meetings.find(
        {"lead_id": lead_id},
        {"_id": 0}
    ).sort("meeting_date", -1).to_list(100)
    
    if meetings:
        completed_steps.append("record_meeting")
        linked_data["meeting_ids"] = [m.get("id") for m in meetings if m.get("id")]
        linked_data["meeting_count"] = len(meetings)
        if meetings[0].get("meeting_date"):
            linked_data["last_meeting_date"] = meetings[0]["meeting_date"][:10] if isinstance(meetings[0]["meeting_date"], str) else str(meetings[0]["meeting_date"])[:10]
    
    # Step 3: Pricing Plan - check if pricing exists
    pricing = await db.pricing_plans.find_one({"lead_id": lead_id}, {"_id": 0})
    if pricing:
        completed_steps.append("pricing_plan")
        linked_data["pricing_plan_id"] = pricing.get("id")
        linked_data["pricing_plan_total"] = pricing.get("grand_total", 0)
    
    # Step 4: SOW - check if SOW exists (check both sows and enhanced_sows collections)
    sow = await db.sows.find_one({"lead_id": lead_id}, {"_id": 0})
    if not sow:
        sow = await db.enhanced_sows.find_one({"lead_id": lead_id}, {"_id": 0})
    if sow:
        completed_steps.append("scope_of_work")
        linked_data["sow_id"] = sow.get("id")
        linked_data["sow_items_count"] = len(sow.get("scope_items", []))
    
    # Step 5: Quotation - check if quotation exists
    quotation = await db.quotations.find_one({"lead_id": lead_id}, {"_id": 0})
    if quotation:
        completed_steps.append("quotation")
        linked_data["quotation_id"] = quotation.get("id")
        linked_data["quotation_number"] = quotation.get("quotation_number")
    
    # Step 6: Agreement - check if agreement exists
    agreement = await db.agreements.find_one({"lead_id": lead_id}, {"_id": 0})
    
    # Track blocking status for agreement
    agreement_blocked = False
    blocked_reason = None
    blocked_at_step = None
    
    if agreement:
        completed_steps.append("agreement")
        linked_data["agreement_id"] = agreement.get("id")
        linked_data["agreement_number"] = agreement.get("agreement_number")
        linked_data["agreement_status"] = agreement.get("status")
        
        # Check if agreement is blocking further progress
        agreement_status = (agreement.get("status") or "").lower()
        if agreement_status in ["pending", "draft", "review", "rejected"]:
            agreement_blocked = True
            blocked_at_step = "agreement"
            if agreement_status == "rejected":
                blocked_reason = f"Agreement #{agreement.get('agreement_number', 'N/A')} has been rejected. Please revise and resubmit the agreement before proceeding."
            else:
                blocked_reason = f"Agreement #{agreement.get('agreement_number', 'N/A')} is {agreement_status}. Please get the agreement approved before proceeding to payment and kickoff."
        
        # Step 7: Payment - only check if agreement is NOT blocking
        if not agreement_blocked:
            payments = await db.payment_verifications.find(
                {"agreement_id": agreement.get("id"), "status": "verified"},
                {"_id": 0}
            ).to_list(100)
            
            if payments:
                linked_data["payment_count"] = len(payments)
                linked_data["total_paid"] = sum(p.get("amount", 0) for p in payments)
                completed_steps.append("record_payment")
            elif agreement.get("payment_status") == "paid" or agreement.get("payment_received"):
                completed_steps.append("record_payment")
    
    # Step 8: Kickoff Request - only check if agreement is NOT blocking
    kickoff = None
    if not agreement_blocked:
        kickoff = await db.kickoff_requests.find_one({"lead_id": lead_id}, {"_id": 0})
        if not kickoff and agreement:
            # Also check by agreement_id
            kickoff = await db.kickoff_requests.find_one({"agreement_id": agreement.get("id")}, {"_id": 0})
        
        if kickoff:
            completed_steps.append("kickoff_request")
            linked_data["kickoff_id"] = kickoff.get("id")
            linked_data["kickoff_status"] = kickoff.get("status")
            
            # Step 9: Project Created - check if kickoff approved/accepted
            if kickoff.get("status") in ["approved", "accepted", "converted"]:
                completed_steps.append("project_created")
                linked_data["project_id"] = kickoff.get("project_id")
                linked_data["project_name"] = kickoff.get("project_name")
    
    # Also check if lead status indicates completion (only if not blocked)
    if not agreement_blocked and lead.get("status") in ["won", "closed_won", "converted"]:
        if "project_created" not in completed_steps:
            completed_steps.append("project_created")
    
    # Calculate progress
    progress_percentage = (len(completed_steps) / len(FUNNEL_STEPS)) * 100
    
    # Determine current step
    current_step_index = len(completed_steps)
    current_step = FUNNEL_STEPS[current_step_index] if current_step_index < len(FUNNEL_STEPS) else "project_created"
    
    # Auto-update lead status based on funnel progress
    # Map funnel steps to lead status
    FUNNEL_TO_STATUS_MAP = {
        "lead_capture": LeadStatus.NEW,
        "record_meeting": LeadStatus.CONTACTED,
        "pricing_plan": LeadStatus.QUALIFIED,
        "scope_of_work": LeadStatus.QUALIFIED,
        "quotation": LeadStatus.PROPOSAL,
        "agreement": LeadStatus.AGREEMENT,
        "record_payment": LeadStatus.AGREEMENT,
        "kickoff_request": LeadStatus.AGREEMENT,
        "project_created": LeadStatus.CLOSED
    }
    
    # Determine expected status based on furthest completed step
    expected_status = LeadStatus.NEW
    for step in FUNNEL_STEPS:
        if step in completed_steps:
            expected_status = FUNNEL_TO_STATUS_MAP.get(step, LeadStatus.NEW)
    
    # Update lead status if it doesn't match (and not already won/lost)
    current_status = lead.get("status", LeadStatus.NEW)
    if current_status not in ["won", "lost", "closed_won", "closed_lost"]:
        if current_status != expected_status:
            await db.leads.update_one(
                {"id": lead_id},
                {"$set": {
                    "status": expected_status,
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }}
            )
            # Update local reference for response
            current_status = expected_status
    
    return {
        "lead_id": lead_id,
        "company": lead.get("company"),
        "completed_steps": completed_steps,
        "current_step": current_step,
        "total_steps": len(FUNNEL_STEPS),
        "completed_count": len(completed_steps),
        "progress_percentage": round(progress_percentage, 1),
        "status": current_status,  # Use updated status
        "lead_score": lead.get("score", 0),
        # Blocking status - prevents progress past agreement if not approved
        "is_blocked": agreement_blocked,
        "blocked_reason": blocked_reason,
        "blocked_at_step": blocked_at_step,
        # Linked data for downstream steps
        **linked_data
    }



@router.get("/{lead_id}/funnel-checklist")
async def get_funnel_step_checklist(lead_id: str, current_user: User = Depends(get_current_user)):
    """
    Get detailed checklist for each funnel step with requirements.
    Helps train/guide new salespeople through the process.
    """
    db = get_db()
    
    lead = await db.leads.find_one({"id": lead_id}, {"_id": 0})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    # Get current funnel progress
    meetings = await db.meetings.find({"lead_id": lead_id}, {"_id": 0}).to_list(100)
    pricing = await db.pricing_plans.find_one({"lead_id": lead_id}, {"_id": 0})
    sow = await db.enhanced_sows.find_one({"lead_id": lead_id}, {"_id": 0})
    if not sow:
        sow = await db.sows.find_one({"lead_id": lead_id}, {"_id": 0})
    quotation = await db.quotations.find_one({"lead_id": lead_id}, {"_id": 0})
    agreement = await db.agreements.find_one({"lead_id": lead_id}, {"_id": 0})
    kickoff = await db.kickoff_requests.find_one({"lead_id": lead_id}, {"_id": 0})
    
    # Check for offline meeting attachments
    offline_meetings = [m for m in meetings if m.get("mode") == "offline" or m.get("meeting_type", "").lower() == "offline"]
    has_offline_attachment = any(m.get("has_attachments") for m in offline_meetings)
    
    checklist = {
        "lead_capture": {
            "title": "Lead Capture",
            "description": "Gather initial contact information and qualify the lead",
            "requirements": [
                {"item": "Full name collected", "completed": bool(lead.get("first_name") and lead.get("last_name")), "required": True},
                {"item": "Company name entered", "completed": bool(lead.get("company")), "required": True},
                {"item": "Contact email provided", "completed": bool(lead.get("email")), "required": True},
                {"item": "Phone number available", "completed": bool(lead.get("phone")), "required": False},
                {"item": "Lead source identified", "completed": bool(lead.get("source")), "required": False}
            ],
            "tips": ["Verify email validity", "Research company on LinkedIn before meeting", "Note any referral source"],
            "completed": True  # Always true if lead exists
        },
        "record_meeting": {
            "title": "Record Meeting",
            "description": "Document all client interactions with Minutes of Meeting (MOM)",
            "requirements": [
                {"item": "At least one meeting recorded", "completed": len(meetings) > 0, "required": True},
                {"item": "Minutes of Meeting (MOM) filled", "completed": any(m.get("mom") for m in meetings), "required": True},
                {"item": "Client expectations documented", "completed": any(m.get("client_expectations") for m in meetings), "required": False},
                {"item": "Key commitments noted", "completed": any(m.get("key_commitments") for m in meetings), "required": False},
                {"item": "Offline meeting has photo/voice attachment", "completed": has_offline_attachment if offline_meetings else True, "required": bool(offline_meetings)}
            ],
            "tips": ["Always fill MOM immediately after meeting", "Capture client pain points", "Document any budget discussions"],
            "completed": len(meetings) > 0 and any(m.get("mom") for m in meetings)
        },
        "pricing_plan": {
            "title": "Pricing Plan",
            "description": "Create detailed pricing breakdown for client review",
            "requirements": [
                {"item": "Pricing plan created", "completed": pricing is not None, "required": True},
                {"item": "Project type selected", "completed": bool(pricing.get("project_type")) if pricing else False, "required": True},
                {"item": "Duration estimated", "completed": bool(pricing.get("project_duration_months")) if pricing else False, "required": False},
                {"item": "Services itemized", "completed": bool(pricing.get("services")) if pricing else False, "required": False}
            ],
            "tips": ["Review similar past projects for pricing reference", "Include all potential costs", "Consider phased pricing"],
            "completed": pricing is not None
        },
        "scope_of_work": {
            "title": "Scope of Work",
            "description": "Define deliverables, milestones, and project boundaries",
            "requirements": [
                {"item": "SOW document created", "completed": sow is not None, "required": True},
                {"item": "Scope items defined", "completed": bool(sow.get("scope_items")) if sow else False, "required": True},
                {"item": "Deliverables listed", "completed": bool(sow.get("deliverables")) if sow else False, "required": False},
                {"item": "Exclusions mentioned", "completed": bool(sow.get("exclusions")) if sow else False, "required": False}
            ],
            "tips": ["Be specific about what's included and excluded", "Reference client expectations from meetings", "Set clear milestones"],
            "completed": sow is not None
        },
        "quotation": {
            "title": "Quotation",
            "description": "Generate formal quote for client approval",
            "requirements": [
                {"item": "Quotation generated", "completed": quotation is not None, "required": True},
                {"item": "Quotation number assigned", "completed": bool(quotation.get("quotation_number")) if quotation else False, "required": True},
                {"item": "Terms included", "completed": bool(quotation.get("terms")) if quotation else False, "required": False}
            ],
            "tips": ["Double-check all amounts before sending", "Include payment terms", "Set validity period"],
            "completed": quotation is not None
        },
        "agreement": {
            "title": "Agreement",
            "description": "Prepare and get service agreement signed",
            "requirements": [
                {"item": "Agreement created", "completed": agreement is not None, "required": True},
                {"item": "Agreement sent to client", "completed": agreement.get("status") in ["sent", "signed", "active"] if agreement else False, "required": True},
                {"item": "Agreement signed by client", "completed": agreement.get("status") in ["signed", "active"] if agreement else False, "required": True}
            ],
            "tips": ["Ensure all stakeholders review before sending", "Follow up if not signed within a week", "Keep signed copy for records"],
            "completed": agreement is not None and agreement.get("status") in ["signed", "active"]
        },
        "record_payment": {
            "title": "Record Payment",
            "description": "Verify and document payment received",
            "requirements": [
                {"item": "Payment received", "completed": agreement.get("payment_status") == "paid" if agreement else False, "required": True},
                {"item": "Payment verified", "completed": agreement.get("payment_verified") if agreement else False, "required": True}
            ],
            "tips": ["Verify payment against agreement amount", "Update finance team immediately", "Keep transaction proof"],
            "completed": agreement is not None and agreement.get("payment_status") == "paid"
        },
        "kickoff_request": {
            "title": "Kickoff Request",
            "description": "Submit project kickoff for PM approval",
            "requirements": [
                {"item": "Kickoff request submitted", "completed": kickoff is not None, "required": True},
                {"item": "PM assigned", "completed": bool(kickoff.get("assigned_pm_id")) if kickoff else False, "required": True},
                {"item": "Kickoff approved", "completed": kickoff.get("status") == "approved" if kickoff else False, "required": True}
            ],
            "tips": ["Include all meeting history and client expectations", "Brief PM on key commitments", "Set realistic start date"],
            "completed": kickoff is not None and kickoff.get("status") == "approved"
        },
        "project_created": {
            "title": "Project Created",
            "description": "Project is live and handed over to delivery team",
            "requirements": [
                {"item": "Project created in system", "completed": bool(kickoff.get("project_id")) if kickoff else False, "required": True}
            ],
            "tips": ["Ensure smooth handover to PM", "Document any special client requirements", "Set follow-up reminders"],
            "completed": kickoff is not None and bool(kickoff.get("project_id"))
        }
    }
    
    return checklist


@router.post("/{lead_id}/funnel-draft")
async def save_funnel_draft(
    lead_id: str,
    data: dict,
    current_user: User = Depends(get_current_user)
):
    """
    Save/update sales funnel draft for a lead.
    Tracks current position and allows resume from where left off.
    """
    db = get_db()
    
    lead = await db.leads.find_one({"id": lead_id}, {"_id": 0})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Check for existing draft
    existing = await db.funnel_drafts.find_one({
        "lead_id": lead_id,
        "employee_id": current_user.id,
        "status": "active"
    }, {"_id": 0})
    
    if existing:
        # Update existing draft
        await db.funnel_drafts.update_one(
            {"id": existing["id"]},
            {"$set": {
                "current_step": data.get("current_step", existing.get("current_step")),
                "form_data": data.get("form_data", {}),
                "meeting_data": data.get("meeting_data"),
                "pricing_data": data.get("pricing_data"),
                "sow_data": data.get("sow_data"),
                "updated_at": now,
                "version": existing.get("version", 1) + 1
            }}
        )
        
        updated = await db.funnel_drafts.find_one({"id": existing["id"]}, {"_id": 0})
        return {"message": "Funnel draft updated", "draft": updated, "action": "updated"}
    
    # Create new draft
    draft_id = str(uuid.uuid4())
    draft = {
        "id": draft_id,
        "lead_id": lead_id,
        "employee_id": current_user.id,
        "lead_company": lead.get("company"),
        "lead_name": f"{lead.get('first_name', '')} {lead.get('last_name', '')}".strip(),
        "current_step": data.get("current_step", "lead_capture"),
        "form_data": data.get("form_data", {}),
        "meeting_data": data.get("meeting_data"),
        "pricing_data": data.get("pricing_data"),
        "sow_data": data.get("sow_data"),
        "status": "active",
        "version": 1,
        "created_at": now,
        "updated_at": now
    }
    
    await db.funnel_drafts.insert_one(draft)
    
    saved = await db.funnel_drafts.find_one({"id": draft_id}, {"_id": 0})
    return {"message": "Funnel draft created", "draft": saved, "action": "created"}


@router.get("/{lead_id}/funnel-draft")
async def get_funnel_draft(lead_id: str, current_user: User = Depends(get_current_user)):
    """Get the active funnel draft for a lead."""
    db = get_db()
    
    draft = await db.funnel_drafts.find_one({
        "lead_id": lead_id,
        "employee_id": current_user.id,
        "status": "active"
    }, {"_id": 0})
    
    if draft:
        return {"has_draft": True, "draft": draft}
    
    return {"has_draft": False, "draft": None}


@router.delete("/{lead_id}/funnel-draft")
async def delete_funnel_draft(lead_id: str, current_user: User = Depends(get_current_user)):
    """Delete/discard the funnel draft for a lead."""
    db = get_db()
    
    result = await db.funnel_drafts.delete_one({
        "lead_id": lead_id,
        "employee_id": current_user.id,
        "status": "active"
    })
    
    if result.deleted_count > 0:
        return {"message": "Funnel draft deleted", "status": "success"}
    
    return {"message": "No draft found to delete", "status": "not_found"}


@router.get("/funnel-drafts/all")
async def get_all_funnel_drafts(current_user: User = Depends(get_current_user)):
    """Get all active funnel drafts for current user."""
    db = get_db()
    
    drafts = await db.funnel_drafts.find({
        "employee_id": current_user.id,
        "status": "active"
    }, {"_id": 0}).sort("updated_at", -1).to_list(50)
    
    return drafts



# ==================== SSOT (Single Source of Truth) ENDPOINTS ====================

# Import SSOT service
import sys
sys.path.insert(0, '/app/backend')
from services.lead_ssot_service import (
    check_duplicate_lead, 
    get_lead_master_data,
    search_leads_for_dropdown,
    get_ssot_report,
    LEAD_SOURCES,
    LEAD_MASTER_FIELDS,
    DOWNSTREAM_FORMS
)


@router.get("/ssot/lead-sources")
async def get_lead_sources():
    """Get available lead source options for dropdown."""
    return {"sources": LEAD_SOURCES}


@router.post("/ssot/check-duplicates")
async def check_lead_duplicates(
    email: Optional[str] = None,
    phone: Optional[str] = None,
    company: Optional[str] = None,
    exclude_id: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """
    Check for duplicate leads before creation.
    Returns warning if duplicates found.
    """
    db = get_db()
    result = await check_duplicate_lead(db, email, phone, company, exclude_id)
    return result


@router.get("/ssot/master-data/{lead_id}")
async def get_lead_ssot_data(
    lead_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get master field data from lead for auto-filling downstream forms.
    These fields should be locked/read-only in downstream forms.
    """
    db = get_db()
    
    # First check if user has access to this lead
    lead = await db.leads.find_one({"id": lead_id}, {"_id": 0, "created_by": 1, "assigned_to": 1})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    # Check access
    admin_roles = get_role_group("ADMIN_ROLES", fail_closed=True)
    if not has_role(current_user.role, admin_roles):
        if lead.get("created_by") != current_user.id and lead.get("assigned_to") != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")
    
    master_data = await get_lead_master_data(db, lead_id)
    if not master_data:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    return {
        "master_data": master_data,
        "locked_fields": LEAD_MASTER_FIELDS,
        "message": "These fields are auto-filled from lead and should be read-only"
    }


@router.get("/ssot/search")
async def search_leads_ssot(
    q: str = Query("", description="Search query"),
    limit: int = Query(20, le=50),
    funnel_stage: str = Query("any", description="Filter by funnel stage: any, has_meeting, has_pricing_plan, has_quotation"),
    current_user: User = Depends(get_current_user)
):
    """
    Search leads for selection dropdown in downstream forms.
    Returns minimal data for selection UI.
    
    funnel_stage options:
    - any: All leads (default)
    - has_meeting: Leads with at least one meeting with MOM
    - has_pricing_plan: Leads with at least one pricing plan
    - has_quotation: Leads with at least one quotation
    """
    db = get_db()
    
    # Build base query
    base_query = {}
    
    if len(q) < 2:
        # Return recent leads if query too short
        base_query = {"$or": [
            {"created_by": current_user.id},
            {"assigned_to": current_user.id}
        ]}
    else:
        # Text search query
        search_regex = {"$regex": q, "$options": "i"}
        base_query = {"$or": [
            {"company": search_regex},
            {"first_name": search_regex},
            {"last_name": search_regex},
            {"email": search_regex}
        ]}
    
    # Get leads
    cursor = db.leads.find(
        base_query,
        {
            "_id": 0,
            "id": 1,
            "company": 1,
            "first_name": 1,
            "last_name": 1,
            "email": 1,
            "phone": 1,
            "status": 1,
            "city": 1
        }
    ).sort("updated_at", -1).limit(limit * 3)  # Fetch more to filter
    
    leads = await cursor.to_list(length=limit * 3)
    
    # Apply funnel stage filter
    if funnel_stage != "any":
        eligible_lead_ids = set()
        
        if funnel_stage == "has_meeting":
            # Find leads with meetings that have MOM
            meetings = await db.meetings.find(
                {"mom": {"$exists": True, "$nin": ["", None]}},
                {"lead_id": 1, "_id": 0}
            ).to_list(1000)
            eligible_lead_ids = {m["lead_id"] for m in meetings if m.get("lead_id")}
            
        elif funnel_stage == "has_pricing_plan":
            # Find leads with pricing plans
            plans = await db.pricing_plans.find(
                {},
                {"lead_id": 1, "_id": 0}
            ).to_list(1000)
            eligible_lead_ids = {p["lead_id"] for p in plans if p.get("lead_id")}
            
        elif funnel_stage == "has_quotation":
            # Find leads with quotations
            quotations = await db.quotations.find(
                {},
                {"lead_id": 1, "_id": 0}
            ).to_list(1000)
            eligible_lead_ids = {q["lead_id"] for q in quotations if q.get("lead_id")}
        
        # Filter leads by eligibility
        leads = [lead for lead in leads if lead["id"] in eligible_lead_ids]
    
    # Limit results
    leads = leads[:limit]
    
    formatted_leads = [
        {
            "id": lead["id"],
            "label": f"{lead.get('company', 'Unknown')} - {lead.get('first_name', '')} {lead.get('last_name', '')}".strip(),
            "company": lead.get("company", ""),
            "contact": f"{lead.get('first_name', '')} {lead.get('last_name', '')}".strip(),
            "email": lead.get("email", ""),
            "phone": lead.get("phone", ""),
            "status": lead.get("status", ""),
            "city": lead.get("city", "")
        }
        for lead in leads
    ]
    
    return {
        "leads": formatted_leads, 
        "total": len(formatted_leads),
        "funnel_stage": funnel_stage,
        "filtered": funnel_stage != "any"
    }


@router.get("/ssot/report")
async def get_ssot_implementation_report(current_user: User = Depends(get_current_user)):
    """
    Get report of SSOT implementation:
    - Fields locked
    - Forms updated  
    - Tables referencing lead_id
    """
    admin_roles = get_role_group("ADMIN_ROLES", fail_closed=True)
    if not has_role(current_user.role, admin_roles):
        raise HTTPException(status_code=403, detail="Admin only")
    
    return get_ssot_report()
