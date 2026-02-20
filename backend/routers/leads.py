"""
Leads Router - Lead Management, Scoring, and CRUD operations
"""

from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone
from typing import List, Optional

from .models import Lead, LeadCreate, LeadUpdate, User, UserRole, LeadStatus
from .deps import get_db
from .auth import get_current_user

router = APIRouter(prefix="/leads", tags=["Leads"])


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
    
    Data scoping by hierarchy:
    - Admin: sees all leads
    - HR Manager: sees all leads  
    - Manager/Executive: sees own leads + team leads (reportees)
    """
    db = get_db()
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
