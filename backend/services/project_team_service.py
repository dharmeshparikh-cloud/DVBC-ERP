"""
Project Team Service

PURPOSE: Provides a single source of truth for project team membership.
Instead of storing team in projects.team[] AND consultant_assignments,
all team data should come from consultant_assignments collection.

AUTHORITATIVE SOURCE: consultant_assignments collection
DEPRECATED: projects.team[] embedded array (do not write to this)

USAGE:
- Call get_project_team(db, project_id) to get current team
- Use assign_to_project() and remove_from_project() for changes
- Validate timesheets against active assignments

BENEFITS:
- Single source of truth for assignments
- Proper start_date/end_date tracking
- Assignment history preserved
"""

from typing import Dict, Optional, List
from datetime import datetime, timezone
from utils.timezone import today_ist, current_month_ist, now_ist
from uuid import uuid4
import logging

logger = logging.getLogger("project_team_service")


async def get_project_team(db, project_id: str, include_inactive: bool = False) -> List[Dict]:
    """
    Get current team for a project from consultant_assignments (authoritative source).
    
    Args:
        db: Database instance
        project_id: The project's UUID
        include_inactive: Whether to include ended assignments
    
    Returns:
        List of team member dicts with consultant details
    """
    try:
        query = {"project_id": project_id}
        
        if not include_inactive:
            today = today_ist()
            query["$or"] = [
                {"end_date": None},
                {"end_date": ""},
                {"end_date": {"$gte": today}},
                {"is_active": True}
            ]
        
        assignments = await db.consultant_assignments.find(
            query,
            {"_id": 0}
        ).to_list(None)
        
        # Enrich with consultant details
        team = []
        for assignment in assignments:
            consultant_id = assignment.get("consultant_id")
            
            # Get consultant details from employees
            consultant = await db.employees.find_one(
                {"id": consultant_id},
                {
                    "_id": 0,
                    "id": 1,
                    "employee_id": 1,
                    "first_name": 1,
                    "last_name": 1,
                    "email": 1,
                    "designation": 1,
                    "department": 1,
                    "profile_photo": 1
                }
            )
            
            team_member = {
                "assignment_id": assignment.get("id"),
                "consultant_id": consultant_id,
                "role_in_project": assignment.get("role", assignment.get("role_in_project", "")),
                "allocation_percent": assignment.get("allocation_percent", 100),
                "start_date": assignment.get("start_date"),
                "end_date": assignment.get("end_date"),
                "is_active": assignment.get("is_active", True),
                "hourly_rate": assignment.get("hourly_rate"),
                "billing_type": assignment.get("billing_type", "hourly")
            }
            
            if consultant:
                team_member["consultant_name"] = f"{consultant.get('first_name', '')} {consultant.get('last_name', '')}".strip()
                team_member["employee_id"] = consultant.get("employee_id")
                team_member["email"] = consultant.get("email")
                team_member["designation"] = consultant.get("designation")
                team_member["profile_photo"] = consultant.get("profile_photo")
            
            team.append(team_member)
        
        return team
        
    except Exception as e:
        logger.error(f"Error getting project team for {project_id}: {e}")
        return []


async def assign_to_project(
    db,
    project_id: str,
    consultant_id: str,
    role: str = "",
    allocation_percent: int = 100,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    hourly_rate: Optional[float] = None,
    assigned_by: Optional[str] = None
) -> Dict:
    """
    Assign a consultant to a project.
    Creates record in consultant_assignments (authoritative source).
    
    Returns:
        Dict with assignment details or error
    """
    try:
        # Check if already assigned
        existing = await db.consultant_assignments.find_one({
            "project_id": project_id,
            "consultant_id": consultant_id,
            "$or": [
                {"end_date": None},
                {"end_date": ""},
                {"is_active": True}
            ]
        })
        
        if existing:
            return {"error": "Consultant already assigned to this project", "existing": existing.get("id")}
        
        # Create assignment
        assignment_id = str(uuid4())
        now = datetime.now(timezone.utc).isoformat()
        
        assignment = {
            "id": assignment_id,
            "project_id": project_id,
            "consultant_id": consultant_id,
            "role": role,
            "role_in_project": role,
            "allocation_percent": allocation_percent,
            "start_date": start_date or now[:10],
            "end_date": end_date,
            "hourly_rate": hourly_rate,
            "billing_type": "hourly" if hourly_rate else "fixed",
            "is_active": True,
            "assigned_by": assigned_by,
            "created_at": now,
            "updated_at": now
        }
        
        await db.consultant_assignments.insert_one(assignment)
        
        logger.info(f"Assigned consultant {consultant_id} to project {project_id}")
        
        return {"success": True, "assignment_id": assignment_id, "assignment": assignment}
        
    except Exception as e:
        logger.error(f"Error assigning to project: {e}")
        return {"error": str(e)}


async def remove_from_project(
    db,
    project_id: str,
    consultant_id: str,
    end_date: Optional[str] = None,
    removed_by: Optional[str] = None
) -> Dict:
    """
    Remove a consultant from a project.
    Sets end_date and is_active=False in consultant_assignments.
    """
    try:
        now = datetime.now(timezone.utc).isoformat()
        
        result = await db.consultant_assignments.update_one(
            {
                "project_id": project_id,
                "consultant_id": consultant_id,
                "is_active": True
            },
            {
                "$set": {
                    "end_date": end_date or now[:10],
                    "is_active": False,
                    "removed_by": removed_by,
                    "updated_at": now
                }
            }
        )
        
        if result.modified_count > 0:
            logger.info(f"Removed consultant {consultant_id} from project {project_id}")
            return {"success": True}
        else:
            return {"error": "Assignment not found or already inactive"}
        
    except Exception as e:
        logger.error(f"Error removing from project: {e}")
        return {"error": str(e)}


async def validate_timesheet_assignment(db, project_id: str, consultant_id: str, date: str) -> bool:
    """
    Validate if a consultant was assigned to a project on a given date.
    Used to validate timesheet submissions.
    
    Returns:
        bool: True if valid assignment exists for the date
    """
    try:
        assignment = await db.consultant_assignments.find_one({
            "project_id": project_id,
            "consultant_id": consultant_id,
            "start_date": {"$lte": date},
            "$or": [
                {"end_date": None},
                {"end_date": ""},
                {"end_date": {"$gte": date}}
            ]
        })
        
        return assignment is not None
        
    except Exception as e:
        logger.error(f"Error validating timesheet assignment: {e}")
        return False


async def get_consultant_projects(db, consultant_id: str, include_inactive: bool = False) -> List[Dict]:
    """
    Get all projects a consultant is/was assigned to.
    """
    try:
        query = {"consultant_id": consultant_id}
        
        if not include_inactive:
            today = today_ist()
            query["$or"] = [
                {"end_date": None},
                {"end_date": ""},
                {"end_date": {"$gte": today}},
                {"is_active": True}
            ]
        
        assignments = await db.consultant_assignments.find(query, {"_id": 0}).to_list(None)
        
        # Enrich with project details
        projects = []
        for assignment in assignments:
            project = await db.projects.find_one(
                {"id": assignment.get("project_id")},
                {"_id": 0, "id": 1, "project_code": 1, "project_name": 1, "status": 1, "client_name": 1}
            )
            
            if project:
                projects.append({
                    **assignment,
                    "project_details": project
                })
        
        return projects
        
    except Exception as e:
        logger.error(f"Error getting consultant projects: {e}")
        return []


async def sync_project_team_to_assignments(db, project_id: str) -> Dict:
    """
    Migration helper: Sync projects.team[] to consultant_assignments.
    Creates assignment records for team members not already in assignments.
    """
    try:
        project = await db.projects.find_one({"id": project_id}, {"_id": 0, "team": 1, "assigned_team": 1})
        
        if not project:
            return {"error": "Project not found"}
        
        team = project.get("team", []) or project.get("assigned_team", [])
        if isinstance(team, str):
            team = [team]
        
        synced = 0
        already_exists = 0
        
        for member in team:
            # member could be a string (consultant_id) or dict
            if isinstance(member, dict):
                consultant_id = member.get("id") or member.get("consultant_id")
            else:
                consultant_id = member
            
            if not consultant_id:
                continue
            
            # Check if already has assignment
            existing = await db.consultant_assignments.find_one({
                "project_id": project_id,
                "consultant_id": consultant_id
            })
            
            if existing:
                already_exists += 1
                continue
            
            # Create assignment
            result = await assign_to_project(db, project_id, consultant_id)
            if result.get("success"):
                synced += 1
        
        return {
            "project_id": project_id,
            "team_size": len(team),
            "synced": synced,
            "already_exists": already_exists
        }
        
    except Exception as e:
        logger.error(f"Error syncing project team: {e}")
        return {"error": str(e)}
