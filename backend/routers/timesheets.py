"""
Timesheets Router - Consultant timesheet tracking and approval.
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Optional, List
from datetime import datetime, timezone
import uuid
from pydantic import BaseModel
from .deps import get_db, MANAGER_ROLES, HR_ROLES, ADMIN_ROLES
from .models import User
from .auth import get_current_user

router = APIRouter(prefix="/timesheets", tags=["Timesheets"])

# Role constants for this router
TIMESHEET_VIEW_ALL_ROLES = list(set(MANAGER_ROLES + HR_ROLES + ADMIN_ROLES))  # self, manager, hr, admin


class TimesheetCreate(BaseModel):
    project_id: str
    date: str
    hours: float
    description: Optional[str] = ""
    task_id: Optional[str] = None


@router.get("")
async def get_timesheets(
    project_id: Optional[str] = None,
    employee_id: Optional[str] = None,
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get timesheets with filters"""
    db = get_db()
    
    query = {}
    if project_id:
        query["project_id"] = project_id
    if employee_id:
        query["employee_id"] = employee_id
    if status:
        query["status"] = status
    
    # Non-managers see only their own
    if current_user.role not in MANAGER_ROLES:
        query["employee_id"] = current_user.id
    
    timesheets = await db.timesheets.find(query, {"_id": 0}).sort("date", -1).to_list(500)
    return timesheets


@router.post("")
async def create_timesheet(data: TimesheetCreate, current_user: User = Depends(get_current_user)):
    """Create a timesheet entry"""
    db = get_db()
    
    # Verify project exists
    project = await db.projects.find_one({"id": data.project_id}, {"_id": 0, "id": 1})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    timesheet_id = str(uuid.uuid4())
    timesheet_doc = {
        "id": timesheet_id,
        "employee_id": current_user.id,
        "employee_name": current_user.full_name,
        "project_id": data.project_id,
        "date": data.date,
        "hours": data.hours,
        "description": data.description,
        "task_id": data.task_id,
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.timesheets.insert_one(timesheet_doc)
    timesheet_doc.pop("_id", None)
    return timesheet_doc


@router.get("/all")
async def get_all_timesheets(
    month: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get all timesheets (managers only)"""
    db = get_db()
    
    if current_user.role not in MANAGER_ROLES:
        raise HTTPException(status_code=403, detail="Only managers can view all timesheets")
    
    query = {}
    if month:
        query["date"] = {"$regex": f"^{month}"}
    
    timesheets = await db.timesheets.find(query, {"_id": 0}).sort("date", -1).to_list(1000)
    return timesheets


@router.post("/{timesheet_id}/approve")
async def approve_timesheet(timesheet_id: str, current_user: User = Depends(get_current_user)):
    """Approve a timesheet entry"""
    db = get_db()
    
    if current_user.role not in MANAGER_ROLES:
        raise HTTPException(status_code=403, detail="Only managers can approve timesheets")
    
    timesheet = await db.timesheets.find_one({"id": timesheet_id}, {"_id": 0})
    if not timesheet:
        raise HTTPException(status_code=404, detail="Timesheet not found")
    
    if timesheet.get("status") != "pending":
        raise HTTPException(status_code=400, detail="Timesheet is not pending")
    
    await db.timesheets.update_one(
        {"id": timesheet_id},
        {
            "$set": {
                "status": "approved",
                "approved_by": current_user.id,
                "approved_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    return {"message": "Timesheet approved"}
