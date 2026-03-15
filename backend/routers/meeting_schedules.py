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
    current_user: User = Depends(get_current_user)
):
    """
    Mark meeting as delivered and auto-send MOM to client.
    
    Requirements:
    - MOM must be filled (mom_generated = true)
    - Will send email to client automatically
    - If recurring, will trigger generation of next meeting
    """
    db = get_db()
    
    meeting = await db.meetings.find_one({"id": meeting_id}, {"_id": 0})
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    
    # Check MOM is filled
    if not meeting.get("mom_generated"):
        raise HTTPException(status_code=400, detail="MOM must be filled before completing meeting")
    
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
    
    return {
        "success": True,
        "meeting_id": meeting_id,
        "is_delivered": True,
        "mom_sent": send_result,
        "next_meeting": next_meeting_result
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
