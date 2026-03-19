"""
Projects Router - Project Management, Consultant Assignment, Handover Alerts

GOVERNANCE:
- Projects should be created via kickoff workflow (Principal Consultant approval)
- Direct project creation allowed only for admin with kickoff_bypass flag
- Consultant assignments tracked in consultant_assignments collection
"""

from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone, timedelta
from typing import List, Optional
import uuid

from .models import Project, ProjectCreate, User, UserRole
from .deps import get_db, get_role_group, has_role
from .deps import get_current_user
from .audit_logging import log_audit

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.post("", response_model=Project)
async def create_project(project_create: ProjectCreate, current_user: User = Depends(get_current_user)):
    """
    Create a new project.
    
    GOVERNANCE: Projects should typically be created via kickoff workflow.
    Direct creation requires admin role or kickoff_id reference.
    """
    db = get_db()
    
    # RBAC Migration: Check if manager-only role (view-only)
    project_roles = get_role_group("PROJECT_ROLES", fail_closed=True)
    admin_roles = get_role_group("ADMIN_ROLES", fail_closed=False) or ['admin']
    
    if not project_roles or not has_role(current_user.role, project_roles):
        raise HTTPException(status_code=403, detail="Only project team can create projects")
    
    # GOVERNANCE: Warn if creating without kickoff (unless admin)
    kickoff_id = getattr(project_create, 'kickoff_id', None)
    if not kickoff_id and not has_role(current_user.role, admin_roles):
        # Allow but log warning - future: make mandatory
        print(f"[GOVERNANCE WARNING] Project created without kickoff by {current_user.id}")
    
    project_dict = project_create.model_dump()
    project = Project(**project_dict, created_by=current_user.id)
    
    doc = project.model_dump()
    doc['start_date'] = doc['start_date'].isoformat()
    if doc['end_date']:
        doc['end_date'] = doc['end_date'].isoformat()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    
    # Add kickoff reference if provided
    if kickoff_id:
        doc['kickoff_id'] = kickoff_id
    
    await db.projects.insert_one(doc)
    
    # Audit log
    await log_audit(
        action="project.create",
        entity_type="project",
        entity_id=doc['id'],
        performed_by=current_user.id,
        after_state={
            "name": doc.get('name'),
            "client_id": doc.get('client_id'),
            "kickoff_id": kickoff_id
        },
        metadata={
            "has_kickoff": kickoff_id is not None,
            "created_by_role": current_user.role
        }
    )
    
    return project


@router.get("", response_model=List[Project])
async def get_projects(current_user: User = Depends(get_current_user)):
    """Get all projects (filtered by role)."""
    db = get_db()
    query = {}
    
    # RBAC Migration: HR Manager can view all projects (for workload planning) but not create
    hr_roles = get_role_group("HR_ROLES", fail_closed=False) or []
    admin_roles = get_role_group("ADMIN_ROLES", fail_closed=False) or ['admin']
    
    if has_role(current_user.role, hr_roles):
        # HR Manager sees all projects but financial data will be stripped
        pass
    elif not has_role(current_user.role, admin_roles):
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
        
        # Strip financial data for HR (operational view only)
        if has_role(current_user.role, hr_roles) and not has_role(current_user.role, admin_roles):
            project.pop('budget', None)
            project.pop('actual_cost', None)
            project.pop('hourly_rate', None)
            project.pop('contract_value', None)
            project.pop('billing_details', None)
    
    return projects


@router.get("/all-assignments")
async def get_all_consultant_assignments(
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """
    Get all consultant assignments across all projects.
    
    Args:
        status: Filter by status (active, inactive)
    """
    db = get_db()
    
    query = {}
    if status:
        if status == "active":
            query["is_active"] = True
        elif status == "inactive":
            query["is_active"] = False
    
    assignments = await db.consultant_assignments.find(
        query,
        {"_id": 0}
    ).sort("assigned_at", -1).to_list(1000)
    
    # Filter out assignments without project info
    valid_assignments = [
        a for a in assignments 
        if a.get("project_id") and a.get("consultant_id")
    ]
    
    return {
        "assignments": valid_assignments,
        "total": len(valid_assignments),
        "active": len([a for a in valid_assignments if a.get("is_active")]),
        "by_project": len(set(a.get("project_id") for a in valid_assignments))
    }


# Handover alerts must be defined BEFORE /projects/{project_id} to avoid route conflict
@router.get("/handover-alerts")
async def get_handover_alerts(current_user: User = Depends(get_current_user)):
    """Get projects approaching 15-day handover deadline from agreement approval."""
    db = get_db()
    
    # RBAC Migration: Check project roles
    project_roles = get_role_group("PROJECT_ROLES", fail_closed=True)
    if not project_roles or not has_role(current_user.role, project_roles):
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
    
    # RBAC Migration: Use database-driven role check
    senior_consulting_roles = get_role_group("SENIOR_CONSULTING_ROLES", fail_closed=True)
    if not senior_consulting_roles or not has_role(current_user.role, senior_consulting_roles):
        raise HTTPException(status_code=403, detail="Only Senior Consultants and above can access this view")
    
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
    
    # RBAC Migration: Use database-driven role check (fail-closed for critical operation)
    senior_consulting_roles = get_role_group("SENIOR_CONSULTING_ROLES", fail_closed=True)
    if not senior_consulting_roles or not has_role(current_user.role, senior_consulting_roles):
        raise HTTPException(status_code=403, detail="Only Senior Consultants and above can assign consultants")
    
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
    
    # RBAC Migration: Use database-driven role check (fail-closed for critical operation)
    senior_consulting_roles = get_role_group("SENIOR_CONSULTING_ROLES", fail_closed=True)
    if not senior_consulting_roles or not has_role(current_user.role, senior_consulting_roles):
        raise HTTPException(status_code=403, detail="Only Senior Consultants and above can unassign consultants")
    
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
    
    # RBAC Migration: Use database-driven role check (fail-closed for critical operation)
    senior_consulting_roles = get_role_group("SENIOR_CONSULTING_ROLES", fail_closed=True)
    if not senior_consulting_roles or not has_role(current_user.role, senior_consulting_roles):
        raise HTTPException(status_code=403, detail="Only Senior Consultants and above can change consultants")
    
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



@router.post("/{project_id}/sync-assignments")
async def sync_project_assignments(
    project_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Sync consultant_assignments with project team_members.
    Creates assignment records for any team members not yet in consultant_assignments.
    
    GOVERNANCE: Ensures all project team members have proper assignment records
    for tracking, reporting, and audit purposes.
    """
    db = get_db()
    
    # Verify project exists
    project = await db.projects.find_one({"id": project_id}, {"_id": 0})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Get team members from project
    team_members = project.get('team_members', []) or []
    assigned_consultants = project.get('assigned_consultants', []) or []
    all_members = list(set(team_members + assigned_consultants))
    
    if not all_members:
        return {"message": "No team members to sync", "created": 0}
    
    # Get existing assignments
    existing = await db.consultant_assignments.find(
        {"project_id": project_id, "is_active": True},
        {"_id": 0, "consultant_id": 1}
    ).to_list(100)
    existing_ids = set(a.get("consultant_id") for a in existing)
    
    # Create assignments for new members
    created = 0
    now = datetime.now(timezone.utc).isoformat()
    
    for member_id in all_members:
        if member_id in existing_ids:
            continue
        
        # Get user details
        user = await db.users.find_one({"id": member_id}, {"_id": 0})
        if not user:
            # Try by employee_id
            emp = await db.employees.find_one({"id": member_id}, {"_id": 0})
            if emp and emp.get("user_id"):
                user = await db.users.find_one({"id": emp["user_id"]}, {"_id": 0})
        
        if not user:
            continue
        
        assignment = {
            "id": str(uuid.uuid4()),
            "project_id": project_id,
            "project_name": project.get("name") or project.get("project_name"),
            "consultant_id": user["id"],
            "consultant_name": user.get("full_name"),
            "consultant_email": user.get("email"),
            "role": user.get("role", "consultant"),
            "assigned_by": current_user.id,
            "assigned_by_name": current_user.full_name,
            "assigned_at": now,
            "is_active": True,
            "status": "active",
            "source": "sync",  # Indicates auto-created via sync
            "created_at": now,
            "updated_at": now
        }
        
        await db.consultant_assignments.insert_one(assignment)
        created += 1
        
        # Send notification to the assigned consultant
        try:
            from services.notification_service import create_notification
            notification_data = {
                "user_id": user["id"],
                "title": "New Project Assignment",
                "message": f"You have been assigned to project: {project.get('name') or project.get('project_name')}",
                "type": "project_assignment",
                "entity_type": "project",
                "entity_id": project_id,
                "priority": "normal",
                "action_url": f"/projects/{project_id}"
            }
            await create_notification(notification_data)
        except Exception as e:
            print(f"Failed to send assignment notification: {e}")
    
    # Audit log
    if created > 0:
        await log_audit(
            action="project.assignments_synced",
            entity_type="project",
            entity_id=project_id,
            performed_by=current_user.id,
            after_state={"assignments_created": created},
            metadata={
                "project_name": project.get("name"),
                "total_members": len(all_members)
            }
        )
    
    return {
        "message": f"Synced {created} new assignments",
        "created": created,
        "total_members": len(all_members),
        "existing_assignments": len(existing_ids),
        "notifications_sent": created
    }


@router.post("/sync-all-assignments")
async def sync_all_project_assignments(
    current_user: User = Depends(get_current_user)
):
    """
    Sync assignments for ALL projects.
    Admin utility to ensure all projects have proper assignment records.
    """
    db = get_db()
    
    # Admin only
    admin_roles = get_role_group("ADMIN_ROLES", fail_closed=False) or ['admin']
    if not has_role(current_user.role, admin_roles):
        raise HTTPException(status_code=403, detail="Admin access required")
    
    projects = await db.projects.find({}, {"_id": 0, "id": 1}).to_list(1000)
    
    total_created = 0
    projects_updated = 0
    
    for project in projects:
        # Call sync for each project
        try:
            result = await sync_project_assignments(project["id"], current_user)
            if result.get("created", 0) > 0:
                total_created += result["created"]
                projects_updated += 1
        except Exception as e:
            print(f"Error syncing project {project['id']}: {e}")
    
    return {
        "message": f"Synced {total_created} assignments across {projects_updated} projects",
        "total_assignments_created": total_created,
        "projects_updated": projects_updated,
        "total_projects": len(projects)
    }
