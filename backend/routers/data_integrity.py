"""
Data Architecture Admin Router - P1 Fixes

This router provides admin endpoints for data integrity management:
1. Client data lookups (single source from leads)
2. Project team validation (from consultant_assignments)
3. CTC versioning and history
4. Data consistency checks and migrations

These endpoints are for HR Admin and Admin roles only.
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Optional
from datetime import datetime, timezone
import sys
import os

from .auth import get_current_user
from .models import User
from .deps import get_db, get_role_group, has_role

# Add parent directory to path for services import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import services
from services.client_lookup_service import (
    get_client_details, 
    get_client_display_name,
    check_client_data_consistency,
    bulk_update_client_references
)
from services.project_team_service import (
    get_project_team,
    get_consultant_projects,
    sync_project_team_to_assignments,
    validate_timesheet_assignment
)
from services.ctc_versioning_service import (
    get_current_ctc,
    get_ctc_history,
    get_ctc_for_date,
    sync_ctc_to_employee
)

router = APIRouter(prefix="/data-integrity", tags=["Data Integrity"])


# ============== CLIENT DATA LOOKUP ==============

@router.get("/client/{lead_id}")
async def get_client_from_lead(lead_id: str, current_user: User = Depends(get_current_user)):
    """
    Get client details from the leads collection (single source of truth).
    
    Use this instead of reading client_name from projects/agreements.
    """
    db = get_db()
    
    client = await get_client_details(db, lead_id)
    if not client:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    return {"client": client, "source": "leads_collection"}


@router.get("/client-consistency-check")
async def check_client_consistency(current_user: User = Depends(get_current_user)):
    """
    Check for inconsistencies between stored client_name and lead source.
    Admin only.
    """
    db = get_db()
    
    admin_roles = get_role_group("ADMIN_ROLES", fail_closed=True)
    if not admin_roles or not has_role(current_user.role, admin_roles):
        raise HTTPException(status_code=403, detail="Admin only")
    
    result = await check_client_data_consistency(db)
    return result


@router.post("/client-sync/{entity_type}")
async def sync_client_data(
    entity_type: str,
    current_user: User = Depends(get_current_user)
):
    """
    Sync client_name fields with current lead data.
    
    Args:
        entity_type: "projects", "agreements", or "all"
    
    Admin only. Use with caution.
    """
    db = get_db()
    
    admin_roles = get_role_group("ADMIN_ROLES", fail_closed=True)
    if not admin_roles or not has_role(current_user.role, admin_roles):
        raise HTTPException(status_code=403, detail="Admin only")
    
    if entity_type not in ["projects", "agreements", "all"]:
        raise HTTPException(status_code=400, detail="Invalid entity_type")
    
    result = await bulk_update_client_references(db, entity_type)
    return result


# ============== PROJECT TEAM ENDPOINTS ==============

@router.get("/project/{project_id}/team")
async def get_project_team_endpoint(
    project_id: str,
    include_inactive: bool = False,
    current_user: User = Depends(get_current_user)
):
    """
    Get project team from consultant_assignments (single source of truth).
    
    This replaces reading from projects.team[] which is deprecated.
    """
    db = get_db()
    
    team = await get_project_team(db, project_id, include_inactive)
    
    return {
        "project_id": project_id,
        "team": team,
        "total_members": len(team),
        "active_members": len([m for m in team if m.get("is_active", True)]),
        "source": "consultant_assignments"
    }


@router.get("/consultant/{consultant_id}/projects")
async def get_consultant_projects_endpoint(
    consultant_id: str,
    include_inactive: bool = False,
    current_user: User = Depends(get_current_user)
):
    """
    Get all projects a consultant is assigned to.
    """
    db = get_db()
    
    projects = await get_consultant_projects(db, consultant_id, include_inactive)
    
    return {
        "consultant_id": consultant_id,
        "projects": projects,
        "total": len(projects),
        "active": len([p for p in projects if p.get("is_active", True)])
    }


@router.post("/project/{project_id}/sync-team")
async def sync_project_team(project_id: str, current_user: User = Depends(get_current_user)):
    """
    Migrate projects.team[] to consultant_assignments for a single project.
    Admin only.
    """
    db = get_db()
    
    admin_roles = get_role_group("ADMIN_ROLES", fail_closed=True)
    if not admin_roles or not has_role(current_user.role, admin_roles):
        raise HTTPException(status_code=403, detail="Admin only")
    
    result = await sync_project_team_to_assignments(db, project_id)
    return result


@router.post("/projects/sync-all-teams")
async def sync_all_project_teams(current_user: User = Depends(get_current_user)):
    """
    Migrate all projects.team[] to consultant_assignments.
    Admin only. Idempotent - safe to run multiple times.
    """
    db = get_db()
    
    admin_roles = get_role_group("ADMIN_ROLES", fail_closed=True)
    if not admin_roles or not has_role(current_user.role, admin_roles):
        raise HTTPException(status_code=403, detail="Admin only")
    
    # Get all projects
    projects = await db.projects.find({}, {"_id": 0, "id": 1}).to_list(1000)
    
    results = []
    for project in projects:
        result = await sync_project_team_to_assignments(db, project["id"])
        if result.get("synced", 0) > 0:
            results.append(result)
    
    return {
        "total_projects": len(projects),
        "projects_with_synced_members": len(results),
        "details": results[:20]  # Limit for response size
    }


@router.get("/validate-timesheet")
async def validate_timesheet_endpoint(
    project_id: str,
    consultant_id: str,
    date: str,
    current_user: User = Depends(get_current_user)
):
    """
    Validate if a timesheet entry is valid (consultant was assigned on that date).
    """
    db = get_db()
    
    is_valid = await validate_timesheet_assignment(db, project_id, consultant_id, date)
    
    return {
        "project_id": project_id,
        "consultant_id": consultant_id,
        "date": date,
        "is_valid": is_valid,
        "message": "Assignment valid for date" if is_valid else "No active assignment found for this date"
    }


# ============== CTC VERSIONING ENDPOINTS ==============

@router.get("/employee/{employee_id}/ctc/current")
async def get_employee_current_ctc(
    employee_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get current CTC from ctc_structures (single source of truth).
    """
    db = get_db()
    
    hr_roles = get_role_group("HR_ROLES", fail_closed=False) or []
    admin_roles = get_role_group("ADMIN_ROLES", fail_closed=False) or ["admin"]
    
    # Self or HR/Admin can view
    if current_user.id != employee_id and not has_role(current_user.role, hr_roles + admin_roles):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    ctc = await get_current_ctc(db, employee_id)
    
    if not ctc:
        return {
            "employee_id": employee_id,
            "has_ctc_structure": False,
            "message": "No CTC structure found. Check employees.salary for legacy data."
        }
    
    return {
        "employee_id": employee_id,
        "has_ctc_structure": True,
        "current_ctc": ctc,
        "source": "ctc_structures"
    }


@router.get("/employee/{employee_id}/ctc/history")
async def get_employee_ctc_history(
    employee_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get CTC revision history for an employee.
    """
    db = get_db()
    
    hr_roles = get_role_group("HR_ROLES", fail_closed=False) or []
    admin_roles = get_role_group("ADMIN_ROLES", fail_closed=False) or ["admin"]
    
    if current_user.id != employee_id and not has_role(current_user.role, hr_roles + admin_roles):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    history = await get_ctc_history(db, employee_id)
    
    return {
        "employee_id": employee_id,
        "revision_count": len(history),
        "history": history
    }


@router.get("/employee/{employee_id}/ctc/as-of/{date}")
async def get_employee_ctc_on_date(
    employee_id: str,
    date: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get CTC that was effective on a specific date (for payroll calculations).
    """
    db = get_db()
    
    hr_roles = get_role_group("HR_ROLES", fail_closed=False) or []
    admin_roles = get_role_group("ADMIN_ROLES", fail_closed=False) or ["admin"]
    
    if not has_role(current_user.role, hr_roles + admin_roles):
        raise HTTPException(status_code=403, detail="HR/Admin only")
    
    ctc = await get_ctc_for_date(db, employee_id, date)
    
    if not ctc:
        return {
            "employee_id": employee_id,
            "date": date,
            "found": False,
            "message": "No CTC structure found effective on this date"
        }
    
    return {
        "employee_id": employee_id,
        "date": date,
        "found": True,
        "ctc": ctc
    }


@router.post("/employee/{employee_id}/ctc/sync")
async def sync_employee_ctc(
    employee_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Sync employee.current_ctc with the latest ctc_structures value.
    """
    db = get_db()
    
    hr_roles = get_role_group("HR_ROLES", fail_closed=False) or []
    admin_roles = get_role_group("ADMIN_ROLES", fail_closed=False) or ["admin"]
    
    if not has_role(current_user.role, hr_roles + admin_roles):
        raise HTTPException(status_code=403, detail="HR/Admin only")
    
    success = await sync_ctc_to_employee(db, employee_id)
    
    if success:
        ctc = await get_current_ctc(db, employee_id)
        return {
            "employee_id": employee_id,
            "synced": True,
            "current_ctc": ctc.get("annual_ctc") if ctc else None
        }
    
    return {
        "employee_id": employee_id,
        "synced": False,
        "message": "No CTC structure found to sync"
    }


@router.post("/employees/sync-all-ctc")
async def sync_all_employee_ctc(current_user: User = Depends(get_current_user)):
    """
    Sync all employees' current_ctc fields with their ctc_structures.
    Admin only.
    """
    db = get_db()
    
    admin_roles = get_role_group("ADMIN_ROLES", fail_closed=True)
    if not admin_roles or not has_role(current_user.role, admin_roles):
        raise HTTPException(status_code=403, detail="Admin only")
    
    # Get all employees with CTC structures
    employees_with_ctc = await db.ctc_structures.distinct("employee_id")
    
    synced = 0
    failed = []
    
    for employee_id in employees_with_ctc:
        success = await sync_ctc_to_employee(db, employee_id)
        if success:
            synced += 1
        else:
            failed.append(employee_id)
    
    return {
        "total_employees": len(employees_with_ctc),
        "synced": synced,
        "failed": len(failed),
        "failed_ids": failed[:20]
    }


# ============== OVERALL DATA HEALTH ==============

@router.get("/health-check")
async def data_health_check(current_user: User = Depends(get_current_user)):
    """
    Run a comprehensive data health check.
    Admin only.
    """
    db = get_db()
    
    admin_roles = get_role_group("ADMIN_ROLES", fail_closed=True)
    if not admin_roles or not has_role(current_user.role, admin_roles):
        raise HTTPException(status_code=403, detail="Admin only")
    
    results = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "checks": {}
    }
    
    # 1. Client data consistency
    try:
        client_check = await check_client_data_consistency(db)
        results["checks"]["client_data"] = {
            "status": "ok" if client_check.get("inconsistencies_found", 0) == 0 else "warning",
            "total_checked": client_check.get("total_checked", 0),
            "inconsistencies": client_check.get("inconsistencies_found", 0)
        }
    except Exception as e:
        results["checks"]["client_data"] = {"status": "error", "error": str(e)}
    
    # 2. Project team integrity
    try:
        projects = await db.projects.find({}, {"_id": 0, "id": 1, "team": 1, "assigned_team": 1}).to_list(1000)
        projects_with_team = [p for p in projects if p.get("team") or p.get("assigned_team")]
        
        assignments_count = await db.consultant_assignments.count_documents({})
        
        results["checks"]["project_teams"] = {
            "status": "ok",
            "total_projects": len(projects),
            "projects_with_legacy_team": len(projects_with_team),
            "total_assignments": assignments_count
        }
    except Exception as e:
        results["checks"]["project_teams"] = {"status": "error", "error": str(e)}
    
    # 3. CTC structure coverage
    try:
        total_employees = await db.employees.count_documents({})
        employees_with_ctc = await db.ctc_structures.distinct("employee_id")
        
        results["checks"]["ctc_structures"] = {
            "status": "ok",
            "total_employees": total_employees,
            "employees_with_ctc_structure": len(employees_with_ctc),
            "coverage_percent": round(len(employees_with_ctc) / total_employees * 100, 1) if total_employees > 0 else 0
        }
    except Exception as e:
        results["checks"]["ctc_structures"] = {"status": "error", "error": str(e)}
    
    # 4. Employee-User sync status (from previous P0 fix)
    try:
        from services.employee_user_sync import check_sync_status
        sync_status = await check_sync_status(db)
        results["checks"]["employee_user_sync"] = sync_status
    except Exception as e:
        results["checks"]["employee_user_sync"] = {"status": "error", "error": str(e)}
    
    return results
