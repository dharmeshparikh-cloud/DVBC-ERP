"""
Projects Router - Project Management, Consultant Assignment, Handover Alerts
"""

from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone, timedelta
from typing import List, Optional

from .models import Project, ProjectCreate, User, UserRole
from .deps import get_db
from .auth import get_current_user

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.post("", response_model=Project)
async def create_project(project_create: ProjectCreate, current_user: User = Depends(get_current_user)):
    """Create a new project."""
    db = get_db()
    if current_user.role == UserRole.MANAGER:
        raise HTTPException(status_code=403, detail="Managers can only view and download")
    
    project_dict = project_create.model_dump()
    project = Project(**project_dict, created_by=current_user.id)
    
    doc = project.model_dump()
    doc['start_date'] = doc['start_date'].isoformat()
    if doc['end_date']:
        doc['end_date'] = doc['end_date'].isoformat()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    
    await db.projects.insert_one(doc)
    return project


@router.get("")
async def get_projects(current_user: User = Depends(get_current_user)):
    """Get all projects (filtered by role)."""
    db = get_db()
    query = {}
    
    # HR Manager can view all projects (for workload planning) but not create
    if current_user.role == UserRole.HR_MANAGER:
        # HR Manager sees all projects but financial data will be stripped
        pass
    elif current_user.role != UserRole.ADMIN:
        query['$or'] = [{"assigned_team": current_user.id}, {"created_by": current_user.id}]
    
    projects = await db.projects.find(query, {"_id": 0}).to_list(1000)
    
    # Handle date conversion for flexible schema
    for project in projects:
        if isinstance(project.get('start_date'), str):
            try:
                project['start_date'] = datetime.fromisoformat(project['start_date'])
            except:
                pass
        if project.get('end_date') and isinstance(project['end_date'], str):
            try:
                project['end_date'] = datetime.fromisoformat(project['end_date'])
            except:
                pass
        if isinstance(project.get('created_at'), str):
            try:
                project['created_at'] = datetime.fromisoformat(project['created_at'])
            except:
                pass
        if isinstance(project.get('updated_at'), str):
            try:
                project['updated_at'] = datetime.fromisoformat(project['updated_at'])
            except:
                pass
        
        # Strip financial data for HR Manager (operational view only)
        if current_user.role == UserRole.HR_MANAGER:
            project.pop('budget', None)
            project.pop('actual_cost', None)
            project.pop('hourly_rate', None)
            project.pop('contract_value', None)
            project.pop('billing_details', None)
    
    return projects


# Handover alerts must be defined BEFORE /projects/{project_id} to avoid route conflict
@router.get("/handover-alerts")
async def get_handover_alerts(current_user: User = Depends(get_current_user)):
    """Get projects approaching 15-day handover deadline from agreement approval."""
    db = get_db()
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER, UserRole.PROJECT_MANAGER]:
        raise HTTPException(status_code=403, detail="Not authorized to view handover alerts")
    
    # Get approved agreements from last 30 days
    thirty_days_ago = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    
    agreements = await db.agreements.find(
        {
            "status": "approved",
            "approved_at": {"$gte": thirty_days_ago}
        },
        {"_id": 0}
    ).to_list(1000)
    
    alerts = []
    for agreement in agreements:
        approved_at = agreement.get('approved_at')
        if isinstance(approved_at, str):
            approved_at = datetime.fromisoformat(approved_at)
        
        if approved_at:
            days_since_approval = (datetime.now(timezone.utc) - approved_at).days
            days_remaining = 15 - days_since_approval
            
            # Check if project has been created for this agreement
            project = await db.projects.find_one(
                {"agreement_id": agreement['id']},
                {"_id": 0}
            )
            
            # Get lead info
            lead = None
            if agreement.get('lead_id'):
                lead = await db.leads.find_one(
                    {"id": agreement['lead_id']},
                    {"_id": 0, "first_name": 1, "last_name": 1, "company": 1}
                )
            
            alert_type = "on_track"
            if days_remaining <= 0:
                alert_type = "overdue"
            elif days_remaining <= 3:
                alert_type = "critical"
            elif days_remaining <= 7:
                alert_type = "warning"
            
            alerts.append({
                "agreement": agreement,
                "lead": lead,
                "project": project,
                "days_since_approval": days_since_approval,
                "days_remaining": days_remaining,
                "alert_type": alert_type,
                "has_project": project is not None,
                "has_consultants_assigned": project.get('assigned_consultants', []) if project else []
            })
    
    # Sort by days_remaining (most urgent first)
    alerts.sort(key=lambda x: x['days_remaining'])
    
    return alerts


@router.get("/{project_id}", response_model=Project)
async def get_project(project_id: str, current_user: User = Depends(get_current_user)):
    """Get a single project by ID."""
    db = get_db()
    project_data = await db.projects.find_one({"id": project_id}, {"_id": 0})
    if not project_data:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if isinstance(project_data.get('start_date'), str):
        project_data['start_date'] = datetime.fromisoformat(project_data['start_date'])
    if project_data.get('end_date') and isinstance(project_data['end_date'], str):
        project_data['end_date'] = datetime.fromisoformat(project_data['end_date'])
    if isinstance(project_data.get('created_at'), str):
        project_data['created_at'] = datetime.fromisoformat(project_data['created_at'])
    if isinstance(project_data.get('updated_at'), str):
        project_data['updated_at'] = datetime.fromisoformat(project_data['updated_at'])
    
    return Project(**project_data)
