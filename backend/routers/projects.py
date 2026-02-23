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


@router.get("", response_model=List[Project])
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
    
    # Normalize legacy data and handle date conversion
    for project in projects:
        # Normalize name field (some legacy records use 'project_name')
        if not project.get('name') and project.get('project_name'):
            project['name'] = project['project_name']
        
        # Ensure name has a fallback
        if not project.get('name'):
            project['name'] = project.get('id', 'Unnamed Project')
        
        # Ensure client_name has a fallback
        if not project.get('client_name'):
            project['client_name'] = 'Unknown Client'
        
        # Handle date conversion for flexible schema
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
    
    # Normalize name field (some legacy records use 'project_name')
    if not project_data.get('name') and project_data.get('project_name'):
        project_data['name'] = project_data['project_name']
    
    # Ensure name has a fallback
    if not project_data.get('name'):
        project_data['name'] = project_data.get('id', 'Unnamed Project')
    
    # Ensure client_name has a fallback
    if not project_data.get('client_name'):
        project_data['client_name'] = 'Unknown Client'
    
    # Handle date conversion
    if isinstance(project_data.get('start_date'), str):
        project_data['start_date'] = datetime.fromisoformat(project_data['start_date'])
    if project_data.get('end_date') and isinstance(project_data['end_date'], str):
        project_data['end_date'] = datetime.fromisoformat(project_data['end_date'])
    if isinstance(project_data.get('created_at'), str):
        project_data['created_at'] = datetime.fromisoformat(project_data['created_at'])
    if isinstance(project_data.get('updated_at'), str):
        project_data['updated_at'] = datetime.fromisoformat(project_data['updated_at'])
    
    return Project(**project_data)



# ============== PRINCIPAL CONSULTANT ENDPOINTS ==============

@router.get("/all/for-assignment")
async def get_all_projects_for_assignment(
    status: Optional[str] = None,
    needs_assignment: Optional[bool] = None,
    current_user: User = Depends(get_current_user)
):
    """
    Get all projects for Principal Consultant to manage assignments.
    Only Principal Consultant and Admin can access this.
    """
    db = get_db()
    
    # Only Principal Consultant and Admin
    if current_user.role not in ["admin", "principal_consultant", "senior_consultant"]:
        raise HTTPException(status_code=403, detail="Only Principal Consultant can access this view")
    
    query = {}
    if status:
        query["status"] = status
    
    projects = await db.projects.find(query, {"_id": 0}).sort("created_at", -1).to_list(1000)
    
    result = []
    for project in projects:
        # Normalize project data
        if not project.get('name') and project.get('project_name'):
            project['name'] = project['project_name']
        if not project.get('name'):
            project['name'] = project.get('id', 'Unnamed Project')
        if not project.get('client_name'):
            project['client_name'] = 'Unknown Client'
        
        # Get consultant assignments for this project
        assignments = await db.consultant_assignments.find(
            {"project_id": project.get("id"), "is_active": True},
            {"_id": 0}
        ).to_list(20)
        
        # Get consultant details for each assignment
        for assignment in assignments:
            consultant = await db.users.find_one(
                {"id": assignment.get("consultant_id")},
                {"_id": 0, "id": 1, "full_name": 1, "email": 1, "role": 1}
            )
            if consultant:
                assignment["consultant_details"] = consultant
        
        project["consultant_assignments"] = assignments
        project["has_consultants"] = len(assignments) > 0
        
        # Get kickoff info
        if project.get("kickoff_request_id"):
            kickoff = await db.kickoff_requests.find_one(
                {"id": project.get("kickoff_request_id")},
                {"_id": 0, "internal_approved_by_name": 1, "internal_approved_at": 1, "client_approved_at": 1}
            )
            project["kickoff_info"] = kickoff
        
        # Filter if needs_assignment is specified
        if needs_assignment is not None:
            if needs_assignment and project["has_consultants"]:
                continue  # Skip projects that have assignments
            if not needs_assignment and not project["has_consultants"]:
                continue  # Skip projects without assignments
        
        result.append(project)
    
    return {
        "projects": result,
        "total": len(result),
        "needs_assignment_count": len([p for p in result if not p["has_consultants"]])
    }


@router.post("/{project_id}/assign-consultant")
async def assign_consultant_to_project(
    project_id: str,
    data: dict,
    current_user: User = Depends(get_current_user)
):
    """
    Assign a consultant to a project.
    Only Principal Consultant and Admin can assign.
    Preserves assignment history.
    """
    db = get_db()
    
    # Only Principal Consultant and Admin
    if current_user.role not in ["admin", "principal_consultant", "senior_consultant"]:
        raise HTTPException(status_code=403, detail="Only Principal Consultant can assign consultants")
    
    # Verify project exists
    project = await db.projects.find_one({"id": project_id}, {"_id": 0})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    consultant_id = data.get("consultant_id")
    if not consultant_id:
        raise HTTPException(status_code=400, detail="consultant_id is required")
    
    # Verify consultant exists
    consultant = await db.users.find_one({"id": consultant_id}, {"_id": 0, "id": 1, "full_name": 1})
    if not consultant:
        raise HTTPException(status_code=404, detail="Consultant not found")
    
    # Check if already assigned
    existing = await db.consultant_assignments.find_one({
        "project_id": project_id,
        "consultant_id": consultant_id,
        "is_active": True
    })
    if existing:
        raise HTTPException(status_code=400, detail="Consultant is already assigned to this project")
    
    import uuid
    
    # Create assignment record (with history tracking)
    assignment = {
        "id": str(uuid.uuid4()),
        "project_id": project_id,
        "consultant_id": consultant_id,
        "consultant_name": consultant.get("full_name"),
        "role_in_project": data.get("role_in_project", "consultant"),
        "meetings_committed": data.get("meetings_committed", 0),
        "meetings_completed": 0,
        "notes": data.get("notes", ""),
        "assigned_by": current_user.id,
        "assigned_by_name": current_user.full_name,
        "assigned_at": datetime.now(timezone.utc).isoformat(),
        "is_active": True,
        "status": "active",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.consultant_assignments.insert_one(assignment)
    
    # Update project's consultant_assignments array
    await db.projects.update_one(
        {"id": project_id},
        {
            "$push": {"consultant_assignments": assignment["id"]},
            "$set": {"updated_at": datetime.now(timezone.utc).isoformat()}
        }
    )
    
    return {
        "message": f"Consultant {consultant.get('full_name')} assigned to project",
        "assignment_id": assignment["id"]
    }


@router.delete("/{project_id}/unassign-consultant/{consultant_id}")
async def unassign_consultant_from_project(
    project_id: str,
    consultant_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Remove a consultant from a project.
    Preserves history (marks as inactive, doesn't delete).
    """
    db = get_db()
    
    # Only Principal Consultant and Admin
    if current_user.role not in ["admin", "principal_consultant", "senior_consultant"]:
        raise HTTPException(status_code=403, detail="Only Principal Consultant can unassign consultants")
    
    # Find and deactivate assignment
    result = await db.consultant_assignments.update_one(
        {"project_id": project_id, "consultant_id": consultant_id, "is_active": True},
        {
            "$set": {
                "is_active": False,
                "status": "completed",
                "unassigned_by": current_user.id,
                "unassigned_by_name": current_user.full_name,
                "unassigned_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Assignment not found")
    
    return {"message": "Consultant unassigned from project"}


@router.patch("/{project_id}/change-consultant")
async def change_consultant_on_project(
    project_id: str,
    old_consultant_id: str,
    new_consultant_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Replace one consultant with another on a project.
    Preserves history of both assignments.
    """
    db = get_db()
    
    # Only Principal Consultant and Admin
    if current_user.role not in ["admin", "principal_consultant", "senior_consultant"]:
        raise HTTPException(status_code=403, detail="Only Principal Consultant can change consultants")
    
    # Verify project exists
    project = await db.projects.find_one({"id": project_id}, {"_id": 0})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Get old assignment
    old_assignment = await db.consultant_assignments.find_one({
        "project_id": project_id,
        "consultant_id": old_consultant_id,
        "is_active": True
    })
    if not old_assignment:
        raise HTTPException(status_code=404, detail="Old consultant assignment not found")
    
    # Verify new consultant exists
    new_consultant = await db.users.find_one({"id": new_consultant_id}, {"_id": 0, "id": 1, "full_name": 1})
    if not new_consultant:
        raise HTTPException(status_code=404, detail="New consultant not found")
    
    # Check if new consultant already assigned
    existing = await db.consultant_assignments.find_one({
        "project_id": project_id,
        "consultant_id": new_consultant_id,
        "is_active": True
    })
    if existing:
        raise HTTPException(status_code=400, detail="New consultant is already assigned to this project")
    
    import uuid
    
    # Deactivate old assignment
    await db.consultant_assignments.update_one(
        {"id": old_assignment["id"]},
        {
            "$set": {
                "is_active": False,
                "status": "replaced",
                "replaced_by": new_consultant_id,
                "replaced_by_name": new_consultant.get("full_name"),
                "replaced_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    # Create new assignment (inheriting from old)
    new_assignment = {
        "id": str(uuid.uuid4()),
        "project_id": project_id,
        "consultant_id": new_consultant_id,
        "consultant_name": new_consultant.get("full_name"),
        "role_in_project": old_assignment.get("role_in_project", "consultant"),
        "meetings_committed": old_assignment.get("meetings_committed", 0),
        "meetings_completed": 0,
        "notes": f"Replaced {old_assignment.get('consultant_name', 'previous consultant')}",
        "replaced_from_assignment_id": old_assignment["id"],
        "assigned_by": current_user.id,
        "assigned_by_name": current_user.full_name,
        "assigned_at": datetime.now(timezone.utc).isoformat(),
        "is_active": True,
        "status": "active",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.consultant_assignments.insert_one(new_assignment)
    
    return {
        "message": f"Consultant changed from {old_assignment.get('consultant_name')} to {new_consultant.get('full_name')}",
        "new_assignment_id": new_assignment["id"]
    }


@router.get("/{project_id}/assignment-history")
async def get_project_assignment_history(
    project_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get full history of consultant assignments for a project.
    Shows current and past assignments.
    """
    db = get_db()
    
    # Verify project exists
    project = await db.projects.find_one({"id": project_id}, {"_id": 0})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Get all assignments (active and inactive)
    assignments = await db.consultant_assignments.find(
        {"project_id": project_id},
        {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    
    # Enrich with consultant details
    for assignment in assignments:
        consultant = await db.users.find_one(
            {"id": assignment.get("consultant_id")},
            {"_id": 0, "id": 1, "full_name": 1, "email": 1, "role": 1}
        )
        if consultant:
            assignment["consultant_details"] = consultant
    
    return {
        "project_id": project_id,
        "project_name": project.get("name") or project.get("project_name"),
        "assignments": assignments,
        "active_count": len([a for a in assignments if a.get("is_active")]),
        "total_count": len(assignments)
    }
