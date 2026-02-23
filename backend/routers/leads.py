"""
Leads Router - Lead Management, Scoring, and CRUD operations
"""

from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone
from typing import List, Optional
import uuid

from .models import Lead, LeadCreate, LeadUpdate, User, UserRole, LeadStatus
from .deps import get_db, SALES_ROLES, ADMIN_ROLES
from .auth import get_current_user

router = APIRouter(prefix="/leads", tags=["Leads"])

# Role constants for this router
LEADS_ACCESS_ROLES = SALES_ROLES + ADMIN_ROLES  # sales_*, admin


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


@router.post("", response_model=Lead)
async def create_lead(lead_create: LeadCreate, current_user: User = Depends(get_current_user)):
    """Create a new lead."""
    db = get_db()
    if current_user.role == UserRole.MANAGER:
        raise HTTPException(status_code=403, detail="Managers can only view and download")
    
    lead_dict = lead_create.model_dump()
    
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
    
    # Add employee tracking info
    if employee:
        doc['created_by_employee_id'] = employee.get('employee_id')
        doc['created_by_name'] = f"{employee.get('first_name', '')} {employee.get('last_name', '')}".strip()
    
    await db.leads.insert_one(doc)
    return lead


@router.get("", response_model=List[Lead])
async def get_leads(
    status: Optional[str] = None,
    assigned_to: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get all leads with optional filters.
    
    Access: sales_*, admin
    
    Data scoping by hierarchy:
    - Admin: sees all leads
    - HR Manager: sees all leads  
    - Manager/Executive: sees own leads + team leads (reportees)
    """
    db = get_db()
    
    # Role-based access check
    if current_user.role not in LEADS_ACCESS_ROLES:
        raise HTTPException(status_code=403, detail="Access denied. Only sales team and admin can view leads.")
    
    query = {}
    if status:
        query['status'] = status
    if assigned_to:
        query['assigned_to'] = assigned_to
    
    # Data scoping by role and hierarchy
    if current_user.role not in ['admin', 'hr_manager']:
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
    
    leads = await db.leads.find(query, {"_id": 0}).to_list(1000)
    
    for lead in leads:
        if isinstance(lead.get('created_at'), str):
            lead['created_at'] = datetime.fromisoformat(lead['created_at'])
        if isinstance(lead.get('updated_at'), str):
            lead['updated_at'] = datetime.fromisoformat(lead['updated_at'])
        if lead.get('enriched_at') and isinstance(lead['enriched_at'], str):
            lead['enriched_at'] = datetime.fromisoformat(lead['enriched_at'])
    
    return leads


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
    
    # Check access based on hierarchy
    if current_user.role not in ['admin', 'hr_manager']:
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
        if lead_data.get('assigned_to') not in accessible_user_ids and lead_data.get('created_by') not in accessible_user_ids:
            raise HTTPException(status_code=403, detail="You don't have access to this lead")
    
    if isinstance(lead_data.get('created_at'), str):
        lead_data['created_at'] = datetime.fromisoformat(lead_data['created_at'])
    if isinstance(lead_data.get('updated_at'), str):
        lead_data['updated_at'] = datetime.fromisoformat(lead_data['updated_at'])
    if lead_data.get('enriched_at') and isinstance(lead_data['enriched_at'], str):
        lead_data['enriched_at'] = datetime.fromisoformat(lead_data['enriched_at'])
    
    return Lead(**lead_data)


@router.put("/{lead_id}", response_model=Lead)
async def update_lead(
    lead_id: str,
    lead_update: LeadUpdate,
    current_user: User = Depends(get_current_user)
):
    """Update a lead."""
    db = get_db()
    if current_user.role == UserRole.MANAGER:
        raise HTTPException(status_code=403, detail="Managers can only view and download")
    
    lead_data = await db.leads.find_one({"id": lead_id}, {"_id": 0})
    if not lead_data:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    update_data = lead_update.model_dump(exclude_unset=True)
    update_data['updated_at'] = datetime.now(timezone.utc).isoformat()
    
    # Recalculate lead score with updated data
    merged_data = {**lead_data, **update_data}
    score, breakdown = calculate_lead_score(merged_data)
    update_data['lead_score'] = score
    update_data['score_breakdown'] = breakdown
    
    await db.leads.update_one({"id": lead_id}, {"$set": update_data})
    
    updated_lead_data = await db.leads.find_one({"id": lead_id}, {"_id": 0})
    if isinstance(updated_lead_data.get('created_at'), str):
        updated_lead_data['created_at'] = datetime.fromisoformat(updated_lead_data['created_at'])
    if isinstance(updated_lead_data.get('updated_at'), str):
        updated_lead_data['updated_at'] = datetime.fromisoformat(updated_lead_data['updated_at'])
    if updated_lead_data.get('enriched_at') and isinstance(updated_lead_data['enriched_at'], str):
        updated_lead_data['enriched_at'] = datetime.fromisoformat(updated_lead_data['enriched_at'])
    
    return Lead(**updated_lead_data)


@router.delete("/{lead_id}")
async def delete_lead(lead_id: str, current_user: User = Depends(get_current_user)):
    """Delete a lead (admin only)."""
    db = get_db()
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only admins can delete leads")
    
    result = await db.leads.delete_one({"id": lead_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Lead not found")
    return {"message": "Lead deleted successfully"}


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
    if agreement:
        completed_steps.append("agreement")
        linked_data["agreement_id"] = agreement.get("id")
        linked_data["agreement_number"] = agreement.get("agreement_number")
        linked_data["agreement_status"] = agreement.get("status")
        
        # Step 7: Payment - check if payment recorded
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
    
    # Step 8: Kickoff Request - check if kickoff exists
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
    
    # Also check if lead status indicates completion
    if lead.get("status") in ["won", "closed_won", "converted"]:
        if "project_created" not in completed_steps:
            completed_steps.append("project_created")
    
    # Calculate progress
    progress_percentage = (len(completed_steps) / len(FUNNEL_STEPS)) * 100
    
    # Determine current step
    current_step_index = len(completed_steps)
    current_step = FUNNEL_STEPS[current_step_index] if current_step_index < len(FUNNEL_STEPS) else "project_created"
    
    return {
        "lead_id": lead_id,
        "company": lead.get("company"),
        "completed_steps": completed_steps,
        "current_step": current_step,
        "total_steps": len(FUNNEL_STEPS),
        "completed_count": len(completed_steps),
        "progress_percentage": round(progress_percentage, 1),
        "status": lead.get("status"),
        "lead_score": lead.get("score", 0),
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

