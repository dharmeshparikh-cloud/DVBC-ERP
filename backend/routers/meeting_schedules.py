"""
Meeting Schedule Router - Recurring Meetings & Calendar API

Endpoints for:
1. Create/manage recurring meeting schedules
2. Team calendar view
3. Conflict detection
4. Auto-generate next meetings
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from typing import Optional, List
from datetime import datetime, timezone, timedelta
import sys
import os
import uuid

from .deps import get_current_user
from .models import User
from .deps import get_db, get_role_group, has_role

# Add parent directory to path for services import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.meeting_schedule_service import (
    create_meeting_schedule,
    generate_next_meeting,
    check_meeting_conflict,
    get_team_calendar,
    get_consultant_schedule,
    detect_all_conflicts,
    auto_send_mom_on_delivery,
    WEEKDAY_NAMES
)

router = APIRouter(prefix="/meeting-schedules", tags=["Meeting Schedules"])


# ============== SCHEDULE CRUD ==============

@router.post("")
async def create_schedule(
    data: dict,
    current_user: User = Depends(get_current_user)
):
    """
    Create a recurring meeting schedule.
    
    Body:
    {
        "project_id": "uuid",
        "consultant_id": "uuid",
        "schedule_type": "fixed_day" | "interval",
        "config": {
            // For fixed_day:
            "day": "monday",
            "time": "10:00",
            "duration_minutes": 60
            
            // For interval:
            "interval_days": 7,
            "preferred_time": "10:00",
            "duration_minutes": 60
        }
    }
    """
    db = get_db()
    
    # Check permissions (Admin, Principal Consultant, Project Manager)
    allowed_roles = get_role_group("SENIOR_CONSULTING_ROLES", fail_closed=False) or []
    admin_roles = get_role_group("ADMIN_ROLES", fail_closed=False) or ["admin"]
    
    if not has_role(current_user.role, allowed_roles + admin_roles):
        raise HTTPException(status_code=403, detail="Not authorized to create meeting schedules")
    
    project_id = data.get("project_id")
    consultant_id = data.get("consultant_id")
    schedule_type = data.get("schedule_type")
    config = data.get("config", {})
    
    if not project_id or not consultant_id:
        raise HTTPException(status_code=400, detail="project_id and consultant_id are required")
    
    if schedule_type not in ["fixed_day", "interval"]:
        raise HTTPException(status_code=400, detail="schedule_type must be 'fixed_day' or 'interval'")
    
    if schedule_type == "fixed_day" and not config.get("day"):
        raise HTTPException(status_code=400, detail="day is required for fixed_day schedule")
    
    if schedule_type == "interval" and not config.get("interval_days"):
        raise HTTPException(status_code=400, detail="interval_days is required for interval schedule")
    
    result = await create_meeting_schedule(
        db,
        project_id,
        consultant_id,
        schedule_type,
        config,
        current_user.id
    )
    
    if result.get("error"):
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result


@router.get("")
async def list_schedules(
    project_id: Optional[str] = None,
    consultant_id: Optional[str] = None,
    is_active: Optional[bool] = True,
    current_user: User = Depends(get_current_user)
):
    """
    List meeting schedules with optional filters.
    """
    db = get_db()
    
    query = {}
    if project_id:
        query["project_id"] = project_id
    if consultant_id:
        query["consultant_id"] = consultant_id
    if is_active is not None:
        query["is_active"] = is_active
    
    schedules = await db.meeting_schedules.find(query, {"_id": 0}).sort("created_at", -1).to_list(100)
    
    return {"schedules": schedules, "total": len(schedules)}


# ============== ADDITIONAL MEETING REQUESTS ==============
# These routes must come BEFORE /{schedule_id} to avoid route conflicts

@router.post("/additional-meeting-request")
async def create_additional_meeting_request(
    data: dict,
    current_user: User = Depends(get_current_user)
):
    """
    Request an additional meeting beyond committed limit.
    
    Required when: total_meetings_delivered >= total_meetings_committed
    
    Body:
    {
        "project_id": "uuid",
        "reason": "Client requested additional training session",
        "requested_meetings": 2,
        "meeting_type": "Training",
        "urgency": "normal" | "urgent"
    }
    """
    db = get_db()
    
    project_id = data.get("project_id")
    if not project_id:
        raise HTTPException(status_code=400, detail="project_id is required")
    
    # Get project
    project = await db.projects.find_one({"id": project_id}, {"_id": 0})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    committed = project.get("total_meetings_committed", 0)
    delivered = project.get("total_meetings_delivered", 0)
    
    # Check if request is actually needed
    remaining = committed - delivered
    requested = data.get("requested_meetings", 1)
    
    if remaining > requested:
        return {
            "message": f"No approval needed. You have {remaining} meetings remaining within commitment.",
            "committed": committed,
            "delivered": delivered,
            "remaining": remaining,
            "approval_required": False
        }
    
    # Create additional meeting request
    request_id = str(uuid.uuid4())
    request_doc = {
        "id": request_id,
        "project_id": project_id,
        "project_name": project.get("name"),
        "client_name": project.get("client_name"),
        "requested_by": current_user.id,
        "requested_by_name": current_user.full_name,
        "reason": data.get("reason", ""),
        "requested_meetings": requested,
        "meeting_type": data.get("meeting_type", "General"),
        "urgency": data.get("urgency", "normal"),
        "current_committed": committed,
        "current_delivered": delivered,
        "status": "pending",  # pending -> approved/rejected
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.additional_meeting_requests.insert_one(request_doc)
    
    # Notify admin
    notification = {
        "id": str(uuid.uuid4()),
        "type": "additional_meeting_request",
        "title": f"Additional Meeting Request - {project.get('name')}",
        "message": f"{current_user.full_name} requested {requested} additional meeting(s) for {project.get('client_name')}. Reason: {data.get('reason', 'Not specified')}",
        "recipient_roles": ["admin", "principal_consultant"],
        "request_id": request_id,
        "project_id": project_id,
        "is_read": False,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.notifications.insert_one(notification)
    
    return {
        "message": "Additional meeting request submitted for admin approval",
        "request_id": request_id,
        "committed": committed,
        "delivered": delivered,
        "remaining": remaining,
        "requested": requested,
        "approval_required": True
    }


@router.get("/additional-meeting-requests")
async def get_additional_meeting_requests(
    project_id: Optional[str] = None,
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get additional meeting requests. Admin sees all, others see their own."""
    db = get_db()
    
    query = {}
    if project_id:
        query["project_id"] = project_id
    if status:
        query["status"] = status
    
    # Non-admin users can only see their own requests
    if current_user.role not in ["admin", "principal_consultant"]:
        query["requested_by"] = current_user.id
    
    requests = await db.additional_meeting_requests.find(query, {"_id": 0}).sort("created_at", -1).to_list(100)
    return requests


@router.post("/additional-meeting-requests/{request_id}/approve")
async def approve_additional_meeting_request(
    request_id: str,
    data: dict = None,
    current_user: User = Depends(get_current_user)
):
    """
    Approve an additional meeting request (Admin only).
    This will increase the project's total_meetings_committed.
    """
    db = get_db()
    
    if current_user.role not in ["admin", "principal_consultant"]:
        raise HTTPException(status_code=403, detail="Only admin/principal consultant can approve")
    
    request = await db.additional_meeting_requests.find_one({"id": request_id}, {"_id": 0})
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")
    
    if request.get("status") != "pending":
        raise HTTPException(status_code=400, detail=f"Request already {request.get('status')}")
    
    approved_meetings = data.get("approved_meetings", request.get("requested_meetings")) if data else request.get("requested_meetings")
    
    # Update request status
    await db.additional_meeting_requests.update_one(
        {"id": request_id},
        {"$set": {
            "status": "approved",
            "approved_meetings": approved_meetings,
            "approved_by": current_user.id,
            "approved_by_name": current_user.full_name,
            "approved_at": datetime.now(timezone.utc).isoformat(),
            "approval_remarks": data.get("remarks", "") if data else "",
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    # Increase project meeting commitment
    await db.projects.update_one(
        {"id": request.get("project_id")},
        {"$inc": {"total_meetings_committed": approved_meetings}}
    )
    
    # Notify requester
    notification = {
        "id": str(uuid.uuid4()),
        "type": "additional_meeting_approved",
        "title": "Additional Meeting Request Approved",
        "message": f"Your request for {approved_meetings} additional meeting(s) for {request.get('project_name')} has been approved by {current_user.full_name}.",
        "recipient_id": request.get("requested_by"),
        "is_read": False,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.notifications.insert_one(notification)
    
    return {
        "message": f"Approved {approved_meetings} additional meeting(s)",
        "request_id": request_id,
        "project_id": request.get("project_id"),
        "new_total_committed": (request.get("current_committed", 0) + approved_meetings)
    }


@router.post("/additional-meeting-requests/{request_id}/reject")
async def reject_additional_meeting_request(
    request_id: str,
    data: dict = None,
    current_user: User = Depends(get_current_user)
):
    """Reject an additional meeting request (Admin only)."""
    db = get_db()
    
    if current_user.role not in ["admin", "principal_consultant"]:
        raise HTTPException(status_code=403, detail="Only admin/principal consultant can reject")
    
    request = await db.additional_meeting_requests.find_one({"id": request_id}, {"_id": 0})
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")
    
    if request.get("status") != "pending":
        raise HTTPException(status_code=400, detail=f"Request already {request.get('status')}")
    
    await db.additional_meeting_requests.update_one(
        {"id": request_id},
        {"$set": {
            "status": "rejected",
            "rejected_by": current_user.id,
            "rejected_by_name": current_user.full_name,
            "rejected_at": datetime.now(timezone.utc).isoformat(),
            "rejection_reason": data.get("reason", "") if data else "",
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    # Notify requester
    notification = {
        "id": str(uuid.uuid4()),
        "type": "additional_meeting_rejected",
        "title": "Additional Meeting Request Rejected",
        "message": f"Your request for additional meetings for {request.get('project_name')} was rejected. Reason: {data.get('reason', 'Not specified') if data else 'Not specified'}",
        "recipient_id": request.get("requested_by"),
        "is_read": False,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.notifications.insert_one(notification)
    
    return {
        "message": "Request rejected",
        "request_id": request_id
    }


@router.get("/project/{project_id}/meeting-status")
async def get_project_meeting_status(
    project_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get meeting commitment status for a project.
    Shows committed vs delivered and whether additional meetings need approval.
    """
    db = get_db()
    
    project = await db.projects.find_one({"id": project_id}, {"_id": 0})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    committed = project.get("total_meetings_committed", 0)
    delivered = project.get("total_meetings_delivered", 0)
    remaining = committed - delivered
    
    # Check for pending requests
    pending_requests = await db.additional_meeting_requests.find({
        "project_id": project_id,
        "status": "pending"
    }, {"_id": 0}).to_list(10)
    
    # Get pricing plan for detailed breakdown
    pricing_plan = None
    if project.get("lead_id"):
        pricing_plan = await db.pricing_plans.find_one(
            {"lead_id": project["lead_id"]},
            {"_id": 0, "team_deployment": 1}
        )
    
    return {
        "project_id": project_id,
        "project_name": project.get("name"),
        "total_committed": committed,
        "total_delivered": delivered,
        "remaining": remaining,
        "percentage_used": round((delivered / committed * 100) if committed > 0 else 0, 1),
        "can_deliver_meeting": remaining > 0,
        "needs_approval": remaining <= 0,
        "pending_requests": pending_requests,
        "team_deployment": pricing_plan.get("team_deployment", []) if pricing_plan else []
    }


# ============== END ADDITIONAL MEETING REQUESTS ==============


@router.get("/{schedule_id}")
async def get_schedule(
    schedule_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get a single schedule by ID."""
    db = get_db()
    
    schedule = await db.meeting_schedules.find_one({"id": schedule_id}, {"_id": 0})
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    
    return schedule


@router.patch("/{schedule_id}")
async def update_schedule(
    schedule_id: str,
    data: dict,
    current_user: User = Depends(get_current_user)
):
    """
    Update a meeting schedule.
    Can update: config, is_active
    """
    db = get_db()
    
    schedule = await db.meeting_schedules.find_one({"id": schedule_id}, {"_id": 0})
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    
    # Build update
    update_fields = {"updated_at": datetime.now(timezone.utc).isoformat()}
    
    if "config" in data:
        update_fields["config"] = data["config"]
    
    if "is_active" in data:
        update_fields["is_active"] = data["is_active"]
    
    await db.meeting_schedules.update_one(
        {"id": schedule_id},
        {"$set": update_fields}
    )
    
    return {"success": True, "updated_fields": list(update_fields.keys())}


@router.delete("/{schedule_id}")
async def delete_schedule(
    schedule_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Deactivate a meeting schedule (soft delete).
    """
    db = get_db()
    
    result = await db.meeting_schedules.update_one(
        {"id": schedule_id},
        {
            "$set": {
                "is_active": False,
                "deactivated_by": current_user.id,
                "deactivated_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Schedule not found")
    
    return {"success": True, "message": "Schedule deactivated"}


# ============== MEETING GENERATION ==============

@router.post("/{schedule_id}/generate-next")
async def generate_next_meeting_endpoint(
    schedule_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Manually trigger generation of next meeting from schedule.
    """
    db = get_db()
    
    result = await generate_next_meeting(db, schedule_id, triggered_by=current_user.id)
    
    if result.get("error"):
        raise HTTPException(status_code=400, detail=result["error"])
    
    return result


@router.post("/generate-all-pending")
async def generate_all_pending_meetings(
    current_user: User = Depends(get_current_user)
):
    """
    Generate next meetings for all active schedules where next_meeting_date has passed.
    Admin/Principal Consultant only.
    """
    db = get_db()
    
    admin_roles = get_role_group("ADMIN_ROLES", fail_closed=False) or ["admin"]
    senior_roles = get_role_group("SENIOR_CONSULTING_ROLES", fail_closed=False) or []
    
    if not has_role(current_user.role, admin_roles + senior_roles):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    now = datetime.now(timezone.utc)
    
    # Find schedules needing generation
    schedules = await db.meeting_schedules.find({
        "is_active": True,
        "next_meeting_date": {"$lte": now.isoformat()}
    }, {"_id": 0, "id": 1}).to_list(100)
    
    results = []
    for schedule in schedules:
        result = await generate_next_meeting(db, schedule["id"], triggered_by="batch_generate")
        results.append({
            "schedule_id": schedule["id"],
            "result": result
        })
    
    return {
        "schedules_processed": len(schedules),
        "results": results
    }


# ============== CALENDAR VIEWS ==============

@router.get("/calendar/team")
async def get_team_calendar_endpoint(
    start_date: str,
    end_date: str,
    consultant_ids: Optional[str] = None,  # Comma-separated
    project_id: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """
    Get team calendar view for specified date range.
    
    Query params:
    - start_date: YYYY-MM-DD
    - end_date: YYYY-MM-DD
    - consultant_ids: Comma-separated list (optional)
    - project_id: Filter by project (optional)
    """
    db = get_db()
    
    consultant_list = None
    if consultant_ids:
        consultant_list = [c.strip() for c in consultant_ids.split(",")]
    
    result = await get_team_calendar(db, start_date, end_date, consultant_list, project_id)
    
    return result


@router.get("/calendar/week")
async def get_week_calendar(
    week_offset: int = 0,
    consultant_ids: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """
    Get calendar for a specific week.
    week_offset: 0 = current week, 1 = next week, -1 = last week
    """
    db = get_db()
    
    today = datetime.now(timezone.utc).date()
    # Start of week (Monday)
    start_of_week = today - timedelta(days=today.weekday()) + timedelta(weeks=week_offset)
    end_of_week = start_of_week + timedelta(days=6)
    
    consultant_list = None
    if consultant_ids:
        consultant_list = [c.strip() for c in consultant_ids.split(",")]
    
    result = await get_team_calendar(
        db,
        start_of_week.isoformat(),
        end_of_week.isoformat(),
        consultant_list
    )
    
    # Add week metadata
    result["week_start"] = start_of_week.isoformat()
    result["week_end"] = end_of_week.isoformat()
    result["week_offset"] = week_offset
    result["weekdays"] = WEEKDAY_NAMES
    
    return result


@router.get("/calendar/consultant/{consultant_id}")
async def get_consultant_calendar(
    consultant_id: str,
    weeks_ahead: int = 4,
    current_user: User = Depends(get_current_user)
):
    """
    Get a consultant's schedule and upcoming meetings.
    """
    db = get_db()
    
    result = await get_consultant_schedule(db, consultant_id, weeks_ahead)
    
    # Get consultant details
    consultant = await db.users.find_one(
        {"id": consultant_id},
        {"_id": 0, "id": 1, "full_name": 1, "email": 1, "role": 1}
    )
    
    if consultant:
        result["consultant"] = consultant
    
    return result


# ============== CONFLICT DETECTION ==============

@router.get("/conflicts/check")
async def check_conflict_endpoint(
    consultant_id: str,
    meeting_date: str,
    duration_minutes: int = 60,
    current_user: User = Depends(get_current_user)
):
    """
    Check if a proposed meeting time conflicts with existing meetings.
    """
    db = get_db()
    
    try:
        meeting_datetime = datetime.fromisoformat(meeting_date.replace('Z', '+00:00'))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid meeting_date format. Use ISO format.")
    
    result = await check_meeting_conflict(db, consultant_id, meeting_datetime, duration_minutes)
    
    return result


@router.get("/conflicts/all")
async def get_all_conflicts(
    consultant_ids: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """
    Detect all scheduling conflicts for team.
    Admin/Manager view.
    """
    db = get_db()
    
    consultant_list = None
    if consultant_ids:
        consultant_list = [c.strip() for c in consultant_ids.split(",")]
    
    conflicts = await detect_all_conflicts(db, consultant_list)
    
    # Enrich with consultant names
    if conflicts:
        consultant_ids_in_conflicts = list(set(c["consultant_id"] for c in conflicts))
        consultants = await db.users.find(
            {"id": {"$in": consultant_ids_in_conflicts}},
            {"_id": 0, "id": 1, "full_name": 1}
        ).to_list(100)
        consultant_map = {c["id"]: c["full_name"] for c in consultants}
        
        for conflict in conflicts:
            conflict["consultant_name"] = consultant_map.get(conflict["consultant_id"], "Unknown")
    
    return {
        "total_conflicts": len(conflicts),
        "conflicts": conflicts
    }


# ============== AUTO-SEND MOM ==============

@router.post("/meetings/{meeting_id}/complete-and-send")
async def complete_meeting_and_send_mom(
    meeting_id: str,
    background_tasks: BackgroundTasks,
    data: dict = None,
    current_user: User = Depends(get_current_user)
):
    """
    Mark meeting as delivered and auto-send MOM to client.
    
    Requirements:
    - MOM must be filled (mom_generated = true)
    - Project must have remaining meeting quota OR approved additional request
    - Will send email to client automatically
    - If recurring, will trigger generation of next meeting
    - Optional: travel_details for expense creation
    """
    db = get_db()
    
    if data is None:
        data = {}
    
    meeting = await db.meetings.find_one({"id": meeting_id}, {"_id": 0})
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    
    # Check MOM is filled
    if not meeting.get("mom_generated"):
        raise HTTPException(status_code=400, detail="MOM must be filled before completing meeting")
    
    # MEETING LIMIT VALIDATION: Check if project has remaining quota
    if meeting.get("project_id"):
        project = await db.projects.find_one({"id": meeting["project_id"]}, {"_id": 0})
        if project:
            committed = project.get("total_meetings_committed", 0)
            delivered = project.get("total_meetings_delivered", 0)
            remaining = committed - delivered
            
            if remaining <= 0:
                # Check for approved additional meeting request
                approved_request = await db.additional_meeting_requests.find_one({
                    "project_id": meeting["project_id"],
                    "status": "approved",
                    "used": {"$ne": True}  # Not yet used
                }, {"_id": 0})
                
                if not approved_request:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Meeting limit exceeded! Committed: {committed}, Delivered: {delivered}. Submit an additional meeting request for admin approval."
                    )
                
                # Mark the approved request as used
                await db.additional_meeting_requests.update_one(
                    {"id": approved_request["id"]},
                    {"$set": {"used": True, "used_at": datetime.now(timezone.utc).isoformat()}}
                )
    
    # Mark as delivered
    await db.meetings.update_one(
        {"id": meeting_id},
        {
            "$set": {
                "is_delivered": True,
                "delivered_at": datetime.now(timezone.utc).isoformat(),
                "delivered_by": current_user.id
            }
        }
    )
    
    # Update project meeting count
    if meeting.get("project_id"):
        await db.projects.update_one(
            {"id": meeting["project_id"]},
            {"$inc": {"total_meetings_delivered": 1}}
        )
    
    # Auto-send MOM
    send_result = await auto_send_mom_on_delivery(db, meeting_id)
    
    # If recurring, generate next meeting
    next_meeting_result = None
    if meeting.get("schedule_id"):
        next_meeting_result = await generate_next_meeting(
            db,
            meeting["schedule_id"],
            triggered_by=f"auto_after_{meeting_id}"
        )
    
    # Create expense record for consulting meetings with travel details
    expense_created = None
    travel_details = data.get("travel_details") if data else None
    
    if travel_details:
        travel_mode = travel_details.get("travel_mode", "")
        if travel_mode != "ACCOMPANIED":
            # DUPLICATE PREVENTION: Check if expense already exists
            existing_expense = await db.expenses.find_one({
                "meeting_id": meeting_id,
                "status": {"$ne": "rejected"}
            })
            
            if not existing_expense:
                # Calculate expense amount
                expense_amount = 0
                distance_km = travel_details.get("distance_km", 0)
                is_round_trip = travel_details.get("is_round_trip", False)
                total_km = distance_km * 2 if is_round_trip else distance_km
                
                if travel_mode == "DRIVING":
                    expense_amount = total_km * 7
                elif travel_mode == "TWO_WHEELER":
                    expense_amount = total_km * 3
                elif travel_mode == "TRANSIT":
                    expense_amount = travel_details.get("transit_amount", 0)
                
                if expense_amount > 0:
                    # Get project info
                    project = None
                    if meeting.get("project_id"):
                        project = await db.projects.find_one({"id": meeting["project_id"]}, {"_id": 0})
                    
                    expense_id = str(uuid.uuid4())
                    expense_doc = {
                        "id": expense_id,
                        "employee_id": current_user.employee_id,
                        "user_id": current_user.id,
                        "created_by": current_user.id,
                        "employee_name": current_user.full_name,
                        "category": "travel",
                        "subcategory": f"consulting_meeting_travel_{travel_mode.lower()}",
                        "description": f"Consulting Meeting Travel - {project.get('name', 'Project') if project else meeting.get('title', 'Meeting')} ({travel_mode})",
                        "amount": round(expense_amount, 2),
                        "total_amount": round(expense_amount, 2),
                        "currency": "INR",
                        "expense_date": meeting.get("meeting_date", datetime.now(timezone.utc).isoformat()),
                        "status": "pending",
                        "meeting_id": meeting_id,
                        "project_id": meeting.get("project_id"),
                        "project_name": project.get("name") if project else None,
                        "client_name": project.get("client_name") if project else meeting.get("client_name"),
                        "travel_details": {
                            "start_location": travel_details.get("start_location"),
                            "end_location": travel_details.get("end_location"),
                            "via_locations": travel_details.get("via_locations", []),
                            "distance_km": distance_km,
                            "total_km": total_km,
                            "is_round_trip": is_round_trip,
                            "travel_mode": travel_mode,
                            "rate_per_km": 7 if travel_mode == "DRIVING" else (3 if travel_mode == "TWO_WHEELER" else 0),
                            "travel_start_time": travel_details.get("travel_start_time"),
                            "travel_end_time": travel_details.get("travel_end_time")
                        },
                        "expense_type": "consulting_meeting_expense",
                        "created_at": datetime.now(timezone.utc).isoformat(),
                        "updated_at": datetime.now(timezone.utc).isoformat()
                    }
                    
                    await db.expenses.insert_one(expense_doc)
                    await db.meetings.update_one(
                        {"id": meeting_id},
                        {"$set": {"expense_id": expense_id, "expense_amount": round(expense_amount, 2)}}
                    )
                    expense_created = expense_id
    
    return {
        "success": True,
        "meeting_id": meeting_id,
        "is_delivered": True,
        "mom_sent": send_result,
        "next_meeting": next_meeting_result,
        "expense_created": expense_created
    }


# ============== HELPER ENDPOINTS ==============

@router.get("/options/weekdays")
async def get_weekday_options(current_user: User = Depends(get_current_user)):
    """Get weekday options for schedule configuration."""
    return {
        "weekdays": [
            {"value": day.lower(), "label": day}
            for day in WEEKDAY_NAMES
        ]
    }


@router.get("/stats/overview")
async def get_schedule_stats(
    current_user: User = Depends(get_current_user)
):
    """
    Get overview stats for meeting schedules.
    """
    db = get_db()
    
    now = datetime.now(timezone.utc)
    week_start = now - timedelta(days=now.weekday())
    week_end = week_start + timedelta(days=7)
    
    # Count active schedules
    active_schedules = await db.meeting_schedules.count_documents({"is_active": True})
    
    # Count meetings this week
    meetings_this_week = await db.meetings.count_documents({
        "meeting_date": {
            "$gte": week_start.isoformat(),
            "$lt": week_end.isoformat()
        }
    })
    
    # Count delivered this week
    delivered_this_week = await db.meetings.count_documents({
        "meeting_date": {
            "$gte": week_start.isoformat(),
            "$lt": week_end.isoformat()
        },
        "is_delivered": True
    })
    
    # Count pending MOM
    pending_mom = await db.meetings.count_documents({
        "is_delivered": False,
        "mom_generated": False,
        "meeting_date": {"$lt": now.isoformat()}
    })
    
    # Detect conflicts
    conflicts = await detect_all_conflicts(db)
    
    return {
        "active_schedules": active_schedules,
        "meetings_this_week": meetings_this_week,
        "delivered_this_week": delivered_this_week,
        "pending_mom": pending_mom,
        "total_conflicts": len(conflicts)
    }



# ============== NOTIFICATION PREFERENCES ==============

@router.get("/notifications/preferences")
async def get_notification_preferences(current_user: User = Depends(get_current_user)):
    """Get current user's notification preferences."""
    db = get_db()
    
    from services.meeting_reminder_service import get_user_notification_preferences
    prefs = await get_user_notification_preferences(db, current_user.id)
    
    return prefs


@router.put("/notifications/preferences")
async def update_notification_preferences_endpoint(
    data: dict,
    current_user: User = Depends(get_current_user)
):
    """
    Update notification preferences.
    
    Body:
    {
        "meeting_reminders": {
            "enabled": true,
            "remind_24h": true,
            "remind_1h": true,
            "email": true,
            "in_app": true
        },
        "mom_notifications": {
            "enabled": true,
            "email": true
        }
    }
    """
    db = get_db()
    
    from services.meeting_reminder_service import update_notification_preferences
    result = await update_notification_preferences(db, current_user.id, data)
    
    return result


@router.post("/notifications/test")
async def send_test_notification(current_user: User = Depends(get_current_user)):
    """Send a test reminder email to verify setup."""
    db = get_db()
    
    user = await db.users.find_one({"id": current_user.id}, {"_id": 0, "email": 1})
    if not user or not user.get("email"):
        raise HTTPException(status_code=400, detail="No email found for user")
    
    from services.meeting_reminder_service import send_test_reminder
    result = await send_test_reminder(db, current_user.id, user["email"])
    
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Failed to send test"))
    
    return result


@router.post("/reminders/process/{reminder_type}")
async def process_reminders(
    reminder_type: str,
    current_user: User = Depends(get_current_user)
):
    """
    Manually trigger reminder processing.
    Admin only. Normally run by cron job.
    
    Args:
        reminder_type: "24h" or "1h"
    """
    db = get_db()
    
    admin_roles = get_role_group("ADMIN_ROLES", fail_closed=False) or ["admin"]
    if not has_role(current_user.role, admin_roles):
        raise HTTPException(status_code=403, detail="Admin only")
    
    if reminder_type not in ["24h", "1h"]:
        raise HTTPException(status_code=400, detail="reminder_type must be '24h' or '1h'")
    
    from services.meeting_reminder_service import process_all_pending_reminders
    result = await process_all_pending_reminders(db, reminder_type)
    
    return result


@router.post("/meetings/{meeting_id}/send-reminder")
async def send_single_meeting_reminder(
    meeting_id: str,
    reminder_type: str = "1h",
    current_user: User = Depends(get_current_user)
):
    """
    Manually send reminder for a specific meeting.
    """
    db = get_db()
    
    meeting = await db.meetings.find_one({"id": meeting_id}, {"_id": 0})
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    
    from services.meeting_reminder_service import send_meeting_reminder
    result = await send_meeting_reminder(db, meeting_id, reminder_type)
    
    return result

