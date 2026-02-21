"""
Sales Router - Sales targets, meetings, MOM, and related endpoints
Extracted from server.py for better modularity
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime, timezone
import uuid

from .deps import get_db
from .auth import get_current_user
from .models import User, UserRole

router = APIRouter(tags=["Sales"])

db = get_db()

# Role definitions
ALL_DATA_ACCESS_ROLES = [UserRole.ADMIN, UserRole.SALES_MANAGER, UserRole.HR_MANAGER, UserRole.PRINCIPAL_CONSULTANT]
SALES_MEETING_ROLES = [UserRole.ADMIN, UserRole.SALES_MANAGER, UserRole.EMPLOYEE, "sales_executive", "business_development"]


# ===== PYDANTIC MODELS =====

class YearlySalesTargetCreate(BaseModel):
    """Yearly sales target creation/update"""
    employee_id: str
    year: int
    target_type: str  # revenue, leads, meetings, conversions
    monthly_targets: dict  # {1: 100000, 2: 120000, ...}


class SalesMeetingCreate(BaseModel):
    """Create a sales meeting with a lead"""
    lead_id: str
    title: str
    meeting_type: str  # discovery, demo, proposal, negotiation, closing
    scheduled_date: str
    scheduled_time: str
    duration_minutes: int = 60
    location: Optional[str] = None  # Office, Client Site, Google Meet, Zoom
    meeting_link: Optional[str] = None
    attendees: Optional[List[str]] = []
    agenda: Optional[str] = None
    notes: Optional[str] = None


class MOMCreate(BaseModel):
    """Minutes of Meeting"""
    meeting_id: str
    summary: str
    discussion_points: List[str]
    action_items: List[dict]  # {task, owner, due_date}
    next_steps: Optional[str] = None
    client_feedback: Optional[str] = None
    lead_temperature_update: Optional[str] = None  # cold, warm, hot


class LeadUpdate(BaseModel):
    """Update lead fields"""
    model_config = ConfigDict(extra="ignore")
    status: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    company: Optional[str] = None
    job_title: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    linkedin_url: Optional[str] = None
    notes: Optional[str] = None


# ===== HELPER FUNCTIONS =====

async def get_team_member_ids(manager_id: str) -> List[str]:
    """Get all user IDs that report to this manager"""
    team_members = await db.users.find(
        {"reporting_manager_id": manager_id, "is_active": True},
        {"id": 1}
    ).to_list(1000)
    return [m['id'] for m in team_members]


def can_see_all_data(user: User) -> bool:
    return user.role in ALL_DATA_ACCESS_ROLES


# ===== SALES TARGETS ENDPOINTS =====

@router.post("/sales-targets")
async def create_yearly_sales_target(
    target: YearlySalesTargetCreate,
    current_user: User = Depends(get_current_user)
):
    """Create/Update yearly sales target for a team member (Manager Target Assignment UI)"""
    # Get employee to verify relationship
    employee = await db.employees.find_one({"employee_id": target.employee_id}, {"_id": 0})
    if not employee:
        # Try finding by id
        employee = await db.employees.find_one({"id": target.employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Verify manager relationship (optional for admins)
    if current_user.role not in ALL_DATA_ACCESS_ROLES:
        user = await db.users.find_one({"id": employee.get('user_id')}, {"_id": 0})
        if not user or user.get('reporting_manager_id') != current_user.id:
            raise HTTPException(status_code=403, detail="You can only set targets for your team members")
    
    # Check for existing target for this employee/year/type
    existing = await db.yearly_sales_targets.find_one({
        "employee_id": target.employee_id,
        "year": target.year,
        "target_type": target.target_type
    })
    
    if existing:
        # Update existing
        await db.yearly_sales_targets.update_one(
            {"id": existing['id']},
            {"$set": {
                "monthly_targets": target.monthly_targets,
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "updated_by": current_user.id
            }}
        )
        return {"message": "Target updated successfully", "id": existing['id']}
    
    # Create new
    target_dict = target.model_dump()
    target_dict['id'] = str(uuid.uuid4())
    target_dict['set_by'] = current_user.id
    target_dict['created_at'] = datetime.now(timezone.utc).isoformat()
    
    await db.yearly_sales_targets.insert_one(target_dict)
    return {"message": "Target created successfully", "id": target_dict['id']}


@router.get("/sales-targets")
async def get_yearly_sales_targets(
    employee_id: Optional[str] = None,
    year: Optional[int] = None,
    target_type: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get yearly sales targets for Target Management UI"""
    query = {}
    
    if employee_id:
        query['employee_id'] = employee_id
    
    if year:
        query['year'] = year
    
    if target_type:
        query['target_type'] = target_type
    
    # For non-admins, filter to subordinates only
    if current_user.role not in ALL_DATA_ACCESS_ROLES:
        # Get subordinate employee IDs
        subordinates = await db.users.find(
            {"reporting_manager_id": current_user.id, "is_active": True},
            {"_id": 0, "id": 1}
        ).to_list(100)
        sub_user_ids = [s['id'] for s in subordinates]
        
        # Get employee IDs for these users
        employees = await db.employees.find(
            {"user_id": {"$in": sub_user_ids}},
            {"_id": 0, "employee_id": 1, "id": 1}
        ).to_list(100)
        emp_ids = [e.get('employee_id') or e.get('id') for e in employees]
        
        if not employee_id:
            query['employee_id'] = {"$in": emp_ids}
    
    targets = await db.yearly_sales_targets.find(query, {"_id": 0}).to_list(100)
    
    return targets


@router.patch("/sales-targets/{target_id}")
async def update_yearly_sales_target(
    target_id: str,
    target_update: YearlySalesTargetCreate,
    current_user: User = Depends(get_current_user)
):
    """Update a yearly sales target"""
    existing = await db.yearly_sales_targets.find_one({"id": target_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Target not found")
    
    await db.yearly_sales_targets.update_one(
        {"id": target_id},
        {"$set": {
            "monthly_targets": target_update.monthly_targets,
            "target_type": target_update.target_type,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "updated_by": current_user.id
        }}
    )
    
    return {"message": "Target updated successfully"}


@router.delete("/sales-targets/{target_id}")
async def delete_yearly_sales_target(
    target_id: str,
    current_user: User = Depends(get_current_user)
):
    """Delete a yearly sales target"""
    existing = await db.yearly_sales_targets.find_one({"id": target_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Target not found")
    
    # Verify ownership (set_by or admin)
    if existing.get('set_by') != current_user.id and current_user.role not in ALL_DATA_ACCESS_ROLES:
        raise HTTPException(status_code=403, detail="You can only delete targets you created")
    
    await db.yearly_sales_targets.delete_one({"id": target_id})
    
    return {"message": "Target deleted successfully"}


@router.patch("/sales-targets/{target_id}/approve")
async def approve_sales_target(
    target_id: str,
    action: str,  # approve or reject
    current_user: User = Depends(get_current_user)
):
    """Approve/reject sales target (Principal Consultant only)"""
    if current_user.role not in ["principal_consultant", "admin"]:
        raise HTTPException(status_code=403, detail="Only Principal Consultants can approve targets")
    
    target = await db.sales_targets.find_one({"id": target_id})
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")
    
    await db.sales_targets.update_one(
        {"id": target_id},
        {"$set": {
            "approval_status": "approved" if action == "approve" else "rejected",
            "approved_by": current_user.id,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    return {"message": f"Target {action}d successfully"}


# ===== SALES MEETINGS ENDPOINTS =====

@router.post("/sales-meetings")
async def create_sales_meeting(
    meeting: SalesMeetingCreate,
    current_user: User = Depends(get_current_user)
):
    """Create a new sales meeting for a lead"""
    if current_user.role not in SALES_MEETING_ROLES:
        raise HTTPException(status_code=403, detail="Only sales team can create meetings")
    
    # Verify lead exists
    lead = await db.leads.find_one({"id": meeting.lead_id}, {"_id": 0})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    meeting_doc = {
        "id": str(uuid.uuid4()),
        "lead_id": meeting.lead_id,
        "lead_name": f"{lead.get('first_name', '')} {lead.get('last_name', '')}".strip(),
        "company": lead.get("company", ""),
        "title": meeting.title,
        "meeting_type": meeting.meeting_type,
        "scheduled_date": meeting.scheduled_date,
        "scheduled_time": meeting.scheduled_time,
        "duration_minutes": meeting.duration_minutes,
        "location": meeting.location,
        "meeting_link": meeting.meeting_link,
        "attendees": meeting.attendees or [],
        "agenda": meeting.agenda,
        "notes": meeting.notes,
        "status": "scheduled",  # scheduled, completed, cancelled, no_show
        "mom_id": None,  # Will be linked when MOM is created
        "created_by": current_user.id,
        "created_by_name": current_user.full_name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.sales_meetings.insert_one(meeting_doc)
    
    # Update lead status to "contacted" if it's "new"
    if lead.get("status") == "new":
        await db.leads.update_one(
            {"id": meeting.lead_id},
            {"$set": {"status": "contacted", "updated_at": datetime.now(timezone.utc).isoformat()}}
        )
    
    meeting_doc.pop("_id", None)
    return meeting_doc


@router.get("/sales-meetings")
async def get_sales_meetings(
    lead_id: Optional[str] = None,
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get sales meetings with optional filters"""
    query = {}
    if lead_id:
        query["lead_id"] = lead_id
    if status:
        query["status"] = status
    
    meetings = await db.sales_meetings.find(query, {"_id": 0}).sort("scheduled_date", -1).to_list(500)
    return meetings


@router.get("/sales-meetings/{meeting_id}")
async def get_sales_meeting(meeting_id: str, current_user: User = Depends(get_current_user)):
    """Get a single sales meeting by ID"""
    meeting = await db.sales_meetings.find_one({"id": meeting_id}, {"_id": 0})
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    return meeting


@router.patch("/sales-meetings/{meeting_id}")
async def update_sales_meeting(
    meeting_id: str,
    data: dict,
    current_user: User = Depends(get_current_user)
):
    """Update a sales meeting"""
    if current_user.role not in SALES_MEETING_ROLES:
        raise HTTPException(status_code=403, detail="Only sales team can update meetings")
    
    meeting = await db.sales_meetings.find_one({"id": meeting_id})
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    
    allowed_fields = ["title", "scheduled_date", "scheduled_time", "duration_minutes", 
                      "location", "meeting_link", "attendees", "agenda", "notes", "status"]
    update_dict = {k: v for k, v in data.items() if k in allowed_fields}
    update_dict["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.sales_meetings.update_one({"id": meeting_id}, {"$set": update_dict})
    return {"message": "Meeting updated successfully"}


@router.post("/sales-meetings/{meeting_id}/complete")
async def complete_sales_meeting(
    meeting_id: str,
    current_user: User = Depends(get_current_user)
):
    """Mark a meeting as completed"""
    result = await db.sales_meetings.update_one(
        {"id": meeting_id},
        {"$set": {
            "status": "completed",
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Meeting not found")
    return {"message": "Meeting marked as completed"}


@router.post("/sales-meetings/{meeting_id}/mom")
async def create_meeting_mom(
    meeting_id: str,
    mom: MOMCreate,
    current_user: User = Depends(get_current_user)
):
    """Create Minutes of Meeting (MOM) for a sales meeting"""
    if current_user.role not in SALES_MEETING_ROLES:
        raise HTTPException(status_code=403, detail="Only sales team can create MOM")
    
    # Verify meeting exists
    meeting = await db.sales_meetings.find_one({"id": meeting_id}, {"_id": 0})
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    
    mom_doc = {
        "id": str(uuid.uuid4()),
        "meeting_id": meeting_id,
        "lead_id": meeting.get("lead_id"),
        "summary": mom.summary,
        "discussion_points": mom.discussion_points,
        "action_items": mom.action_items,
        "next_steps": mom.next_steps,
        "client_feedback": mom.client_feedback,
        "lead_temperature_update": mom.lead_temperature_update,
        "created_by": current_user.id,
        "created_by_name": current_user.full_name,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.sales_mom.insert_one(mom_doc)
    
    # Link MOM to meeting and mark meeting as completed
    await db.sales_meetings.update_one(
        {"id": meeting_id},
        {"$set": {
            "mom_id": mom_doc["id"],
            "status": "completed",
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    # Update lead status based on meeting type and temperature
    lead_id = meeting.get("lead_id")
    new_status = None
    if lead_id:
        meeting_type = meeting.get("meeting_type", "")
        
        # Auto-update lead status based on meeting type
        if meeting_type == "discovery":
            new_status = "contacted"
        elif meeting_type == "demo":
            new_status = "qualified"
        elif meeting_type == "proposal":
            new_status = "proposal"
        elif meeting_type == "negotiation":
            new_status = "proposal"
        elif meeting_type == "closing":
            new_status = "agreement"
        
        if new_status:
            update_fields = {
                "status": new_status,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            
            # Update temperature if provided
            if mom.lead_temperature_update:
                temp_map = {"cold": 20, "warm": 60, "hot": 90}
                update_fields["temperature"] = mom.lead_temperature_update
                update_fields["score"] = temp_map.get(mom.lead_temperature_update, 50)
            
            await db.leads.update_one({"id": lead_id}, {"$set": update_fields})
    
    mom_doc.pop("_id", None)
    return {
        "message": "MOM created successfully",
        "mom": mom_doc,
        "lead_status_updated": new_status
    }


@router.get("/sales-meetings/{meeting_id}/mom")
async def get_meeting_mom(meeting_id: str, current_user: User = Depends(get_current_user)):
    """Get MOM for a sales meeting"""
    mom = await db.sales_mom.find_one({"meeting_id": meeting_id}, {"_id": 0})
    if not mom:
        raise HTTPException(status_code=404, detail="MOM not found for this meeting")
    return mom


@router.get("/leads/{lead_id}/meetings")
async def get_lead_meetings(lead_id: str, current_user: User = Depends(get_current_user)):
    """Get all meetings for a specific lead"""
    meetings = await db.sales_meetings.find(
        {"lead_id": lead_id},
        {"_id": 0}
    ).sort("scheduled_date", -1).to_list(100)
    return meetings


@router.get("/leads/{lead_id}/mom-history")
async def get_lead_mom_history(lead_id: str, current_user: User = Depends(get_current_user)):
    """Get all MOMs for a specific lead"""
    moms = await db.sales_mom.find(
        {"lead_id": lead_id},
        {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    return moms
