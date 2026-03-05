"""
Meeting Schedule Service - Recurring Meetings & Calendar Management

Features:
1. Recurring patterns: Fixed day (Every Monday) OR Interval-based (Every 7 days)
2. Auto-generate next meeting when current one is completed
3. Conflict detection for same consultant overlapping times
4. Team calendar view for managers
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timezone, timedelta, time
from dateutil.relativedelta import relativedelta
from uuid import uuid4
import logging

logger = logging.getLogger("meeting_schedule_service")

# Day name to weekday number mapping
DAY_MAP = {
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
    "friday": 4, "saturday": 5, "sunday": 6
}

WEEKDAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


async def create_meeting_schedule(
    db,
    project_id: str,
    consultant_id: str,
    schedule_type: str,  # "fixed_day" or "interval"
    config: Dict,
    created_by: str
) -> Dict:
    """
    Create a recurring meeting schedule for a project-consultant pair.
    
    Args:
        project_id: Project ID
        consultant_id: Consultant's user ID
        schedule_type: "fixed_day" or "interval"
        config: {
            # For fixed_day:
            "day": "monday",
            "time": "10:00",
            "duration_minutes": 60
            
            # For interval:
            "interval_days": 7,
            "preferred_time": "10:00",
            "duration_minutes": 60
        }
        created_by: User who created the schedule
    
    Returns:
        Created schedule document
    """
    # Validate project exists
    project = await db.projects.find_one({"id": project_id}, {"_id": 0, "name": 1, "client_name": 1})
    if not project:
        return {"error": "Project not found"}
    
    # Validate consultant exists
    consultant = await db.users.find_one({"id": consultant_id}, {"_id": 0, "full_name": 1})
    if not consultant:
        return {"error": "Consultant not found"}
    
    # Check for existing schedule
    existing = await db.meeting_schedules.find_one({
        "project_id": project_id,
        "consultant_id": consultant_id,
        "is_active": True
    })
    if existing:
        return {"error": "Active schedule already exists for this project-consultant pair", "existing_id": existing.get("id")}
    
    schedule_id = str(uuid4())
    now = datetime.now(timezone.utc)
    
    schedule = {
        "id": schedule_id,
        "project_id": project_id,
        "project_name": project.get("name"),
        "client_name": project.get("client_name"),
        "consultant_id": consultant_id,
        "consultant_name": consultant.get("full_name"),
        "schedule_type": schedule_type,
        "config": config,
        "is_active": True,
        "meetings_generated": 0,
        "last_meeting_date": None,
        "next_meeting_date": None,
        "created_by": created_by,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat()
    }
    
    # Calculate first meeting date
    next_date = calculate_next_meeting_date(schedule_type, config, now)
    if next_date:
        schedule["next_meeting_date"] = next_date.isoformat()
    
    await db.meeting_schedules.insert_one(schedule)
    
    logger.info(f"Created meeting schedule {schedule_id} for project {project_id}, consultant {consultant_id}")
    
    return {"success": True, "schedule": schedule}


def calculate_next_meeting_date(
    schedule_type: str,
    config: Dict,
    from_date: datetime = None
) -> Optional[datetime]:
    """
    Calculate the next meeting date based on schedule type and config.
    """
    if from_date is None:
        from_date = datetime.now(timezone.utc)
    
    # Parse time
    time_str = config.get("time") or config.get("preferred_time", "10:00")
    hour, minute = map(int, time_str.split(":"))
    
    if schedule_type == "fixed_day":
        day_name = config.get("day", "monday").lower()
        target_weekday = DAY_MAP.get(day_name, 0)
        
        # Find next occurrence of this weekday
        days_ahead = target_weekday - from_date.weekday()
        if days_ahead <= 0:  # Target day already happened this week
            days_ahead += 7
        
        next_date = from_date + timedelta(days=days_ahead)
        next_date = next_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        return next_date
    
    elif schedule_type == "interval":
        interval_days = config.get("interval_days", 7)
        next_date = from_date + timedelta(days=interval_days)
        next_date = next_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        return next_date
    
    return None


async def generate_next_meeting(db, schedule_id: str, triggered_by: str = "auto") -> Dict:
    """
    Generate the next meeting based on schedule.
    Called when a meeting is marked as delivered.
    """
    schedule = await db.meeting_schedules.find_one({"id": schedule_id}, {"_id": 0})
    if not schedule:
        return {"error": "Schedule not found"}
    
    if not schedule.get("is_active"):
        return {"error": "Schedule is inactive"}
    
    # Calculate next meeting date
    last_date = schedule.get("last_meeting_date")
    if last_date:
        if isinstance(last_date, str):
            from_date = datetime.fromisoformat(last_date.replace('Z', '+00:00'))
        else:
            from_date = last_date
    else:
        from_date = datetime.now(timezone.utc)
    
    next_date = calculate_next_meeting_date(
        schedule.get("schedule_type"),
        schedule.get("config", {}),
        from_date
    )
    
    if not next_date:
        return {"error": "Could not calculate next meeting date"}
    
    # Check for conflicts
    conflict = await check_meeting_conflict(
        db,
        schedule.get("consultant_id"),
        next_date,
        schedule.get("config", {}).get("duration_minutes", 60)
    )
    
    if conflict.get("has_conflict"):
        logger.warning(f"Conflict detected for schedule {schedule_id}: {conflict}")
        # Still create but flag it
    
    # Create the meeting
    meeting_id = str(uuid4())
    now = datetime.now(timezone.utc)
    
    meeting = {
        "id": meeting_id,
        "type": "consulting",
        "project_id": schedule.get("project_id"),
        "lead_id": None,
        "client_id": None,
        "sow_id": None,
        "meeting_date": next_date.isoformat(),
        "mode": "online",
        "attendees": [schedule.get("consultant_id")],
        "attendee_names": [schedule.get("consultant_name")],
        "duration_minutes": schedule.get("config", {}).get("duration_minutes", 60),
        "notes": "",
        "is_delivered": False,
        "title": f"Recurring: {schedule.get('project_name')} - {schedule.get('client_name')}",
        "agenda": [],
        "discussion_points": [],
        "decisions_made": [],
        "action_items": [],
        "next_meeting_date": None,
        "mom_generated": False,
        "mom_sent_to_client": False,
        "mom_sent_at": None,
        # Recurring meeting metadata
        "schedule_id": schedule_id,
        "is_recurring": True,
        "recurrence_number": schedule.get("meetings_generated", 0) + 1,
        "has_conflict": conflict.get("has_conflict", False),
        "conflict_details": conflict.get("conflicts", []) if conflict.get("has_conflict") else None,
        "created_by": triggered_by,
        "created_at": now.isoformat()
    }
    
    await db.meetings.insert_one(meeting)
    
    # Update schedule
    await db.meeting_schedules.update_one(
        {"id": schedule_id},
        {
            "$set": {
                "last_meeting_date": from_date.isoformat(),
                "next_meeting_date": next_date.isoformat(),
                "updated_at": now.isoformat()
            },
            "$inc": {"meetings_generated": 1}
        }
    )
    
    logger.info(f"Generated meeting {meeting_id} from schedule {schedule_id}")
    
    return {
        "success": True,
        "meeting_id": meeting_id,
        "meeting_date": next_date.isoformat(),
        "has_conflict": conflict.get("has_conflict", False)
    }


async def check_meeting_conflict(
    db,
    consultant_id: str,
    meeting_datetime: datetime,
    duration_minutes: int = 60
) -> Dict:
    """
    Check if a consultant has conflicting meetings at the given time.
    """
    # Calculate meeting window
    start_time = meeting_datetime
    end_time = meeting_datetime + timedelta(minutes=duration_minutes)
    
    # Buffer time (30 minutes before/after)
    buffer_start = start_time - timedelta(minutes=30)
    buffer_end = end_time + timedelta(minutes=30)
    
    # Find overlapping meetings
    conflicts = []
    
    meetings = await db.meetings.find({
        "attendees": consultant_id,
        "is_delivered": False,
        "meeting_date": {
            "$gte": buffer_start.isoformat(),
            "$lte": buffer_end.isoformat()
        }
    }, {"_id": 0, "id": 1, "title": 1, "meeting_date": 1, "duration_minutes": 1, "project_id": 1}).to_list(10)
    
    for meeting in meetings:
        meeting_start = datetime.fromisoformat(meeting.get("meeting_date").replace('Z', '+00:00'))
        meeting_end = meeting_start + timedelta(minutes=meeting.get("duration_minutes", 60))
        
        # Check overlap
        if not (end_time <= meeting_start or start_time >= meeting_end):
            conflicts.append({
                "meeting_id": meeting.get("id"),
                "title": meeting.get("title"),
                "meeting_date": meeting.get("meeting_date"),
                "overlap_type": "time_overlap"
            })
    
    return {
        "has_conflict": len(conflicts) > 0,
        "conflicts": conflicts,
        "checked_window": {
            "start": buffer_start.isoformat(),
            "end": buffer_end.isoformat()
        }
    }


async def get_team_calendar(
    db,
    start_date: str,
    end_date: str,
    consultant_ids: List[str] = None,
    project_id: str = None
) -> Dict:
    """
    Get calendar view of all meetings for specified period.
    For manager view of team schedules.
    """
    query = {
        "meeting_date": {
            "$gte": start_date,
            "$lte": end_date
        }
    }
    
    if consultant_ids:
        query["attendees"] = {"$in": consultant_ids}
    
    if project_id:
        query["project_id"] = project_id
    
    meetings = await db.meetings.find(query, {"_id": 0}).sort("meeting_date", 1).to_list(500)
    
    # Group by date
    calendar = {}
    for meeting in meetings:
        date_str = meeting.get("meeting_date", "")[:10]  # YYYY-MM-DD
        if date_str not in calendar:
            calendar[date_str] = []
        
        calendar[date_str].append({
            "id": meeting.get("id"),
            "title": meeting.get("title"),
            "time": meeting.get("meeting_date", "")[11:16],  # HH:MM
            "duration": meeting.get("duration_minutes", 60),
            "project_id": meeting.get("project_id"),
            "attendees": meeting.get("attendee_names", []),
            "consultant_ids": meeting.get("attendees", []),
            "mode": meeting.get("mode"),
            "is_delivered": meeting.get("is_delivered", False),
            "mom_generated": meeting.get("mom_generated", False),
            "is_recurring": meeting.get("is_recurring", False),
            "has_conflict": meeting.get("has_conflict", False)
        })
    
    # Get consultant details for legend
    consultant_map = {}
    if consultant_ids:
        consultants = await db.users.find(
            {"id": {"$in": consultant_ids}},
            {"_id": 0, "id": 1, "full_name": 1}
        ).to_list(100)
        consultant_map = {c["id"]: c["full_name"] for c in consultants}
    
    return {
        "start_date": start_date,
        "end_date": end_date,
        "calendar": calendar,
        "total_meetings": len(meetings),
        "consultants": consultant_map
    }


async def get_consultant_schedule(db, consultant_id: str, weeks_ahead: int = 4) -> Dict:
    """
    Get a consultant's meeting schedule for the upcoming weeks.
    """
    now = datetime.now(timezone.utc)
    end_date = now + timedelta(weeks=weeks_ahead)
    
    # Get active schedules
    schedules = await db.meeting_schedules.find({
        "consultant_id": consultant_id,
        "is_active": True
    }, {"_id": 0}).to_list(50)
    
    # Get upcoming meetings
    meetings = await db.meetings.find({
        "attendees": consultant_id,
        "meeting_date": {
            "$gte": now.isoformat(),
            "$lte": end_date.isoformat()
        }
    }, {"_id": 0}).sort("meeting_date", 1).to_list(100)
    
    # Group by day of week for pattern view
    by_weekday = {i: [] for i in range(7)}
    for schedule in schedules:
        if schedule.get("schedule_type") == "fixed_day":
            day = schedule.get("config", {}).get("day", "monday").lower()
            weekday = DAY_MAP.get(day, 0)
            by_weekday[weekday].append({
                "schedule_id": schedule.get("id"),
                "project_name": schedule.get("project_name"),
                "client_name": schedule.get("client_name"),
                "time": schedule.get("config", {}).get("time", "10:00")
            })
    
    return {
        "consultant_id": consultant_id,
        "active_schedules": len(schedules),
        "upcoming_meetings": meetings,
        "weekly_pattern": {
            WEEKDAY_NAMES[i]: by_weekday[i] for i in range(7)
        }
    }


async def detect_all_conflicts(db, consultant_ids: List[str] = None) -> List[Dict]:
    """
    Detect all scheduling conflicts for specified consultants.
    """
    now = datetime.now(timezone.utc)
    end_date = now + timedelta(weeks=4)
    
    query = {
        "meeting_date": {
            "$gte": now.isoformat(),
            "$lte": end_date.isoformat()
        },
        "is_delivered": False
    }
    
    if consultant_ids:
        query["attendees"] = {"$in": consultant_ids}
    
    meetings = await db.meetings.find(query, {"_id": 0}).sort("meeting_date", 1).to_list(500)
    
    conflicts = []
    
    # Group by consultant
    by_consultant = {}
    for meeting in meetings:
        for consultant_id in meeting.get("attendees", []):
            if consultant_id not in by_consultant:
                by_consultant[consultant_id] = []
            by_consultant[consultant_id].append(meeting)
    
    # Check each consultant's meetings for overlaps
    for consultant_id, consultant_meetings in by_consultant.items():
        for i, m1 in enumerate(consultant_meetings):
            m1_start = datetime.fromisoformat(m1.get("meeting_date").replace('Z', '+00:00'))
            m1_end = m1_start + timedelta(minutes=m1.get("duration_minutes", 60))
            
            for m2 in consultant_meetings[i+1:]:
                m2_start = datetime.fromisoformat(m2.get("meeting_date").replace('Z', '+00:00'))
                m2_end = m2_start + timedelta(minutes=m2.get("duration_minutes", 60))
                
                # Check overlap
                if not (m1_end <= m2_start or m1_start >= m2_end):
                    conflicts.append({
                        "consultant_id": consultant_id,
                        "meeting_1": {
                            "id": m1.get("id"),
                            "title": m1.get("title"),
                            "date": m1.get("meeting_date")
                        },
                        "meeting_2": {
                            "id": m2.get("id"),
                            "title": m2.get("title"),
                            "date": m2.get("meeting_date")
                        },
                        "overlap_minutes": calculate_overlap_minutes(m1_start, m1_end, m2_start, m2_end)
                    })
    
    return conflicts


def calculate_overlap_minutes(start1, end1, start2, end2) -> int:
    """Calculate overlap in minutes between two time ranges."""
    overlap_start = max(start1, start2)
    overlap_end = min(end1, end2)
    if overlap_start < overlap_end:
        return int((overlap_end - overlap_start).total_seconds() / 60)
    return 0


async def auto_send_mom_on_delivery(db, meeting_id: str) -> Dict:
    """
    Automatically send MOM to client when meeting is marked as delivered.
    This is triggered after MOM is filled and meeting is marked delivered.
    """
    from services.email_service import send_email
    
    meeting = await db.meetings.find_one({"id": meeting_id}, {"_id": 0})
    if not meeting:
        return {"error": "Meeting not found"}
    
    if not meeting.get("mom_generated"):
        return {"error": "MOM not generated yet"}
    
    if meeting.get("mom_sent_to_client"):
        return {"already_sent": True}
    
    # Get client email from lead or project
    client_email = None
    client_name = None
    
    if meeting.get("lead_id"):
        lead = await db.leads.find_one({"id": meeting["lead_id"]}, {"_id": 0})
        if lead:
            client_email = lead.get("email")
            client_name = f"{lead.get('first_name', '')} {lead.get('last_name', '')}".strip() or lead.get("company")
    
    if not client_email and meeting.get("project_id"):
        project = await db.projects.find_one({"id": meeting["project_id"]}, {"_id": 0})
        if project and project.get("lead_id"):
            lead = await db.leads.find_one({"id": project["lead_id"]}, {"_id": 0})
            if lead:
                client_email = lead.get("email")
                client_name = lead.get("company") or f"{lead.get('first_name', '')} {lead.get('last_name', '')}".strip()
    
    if not client_email:
        return {"error": "No client email found"}
    
    # Build email content
    meeting_date = meeting.get("meeting_date", "")
    if isinstance(meeting_date, str):
        try:
            meeting_date = datetime.fromisoformat(meeting_date.replace('Z', '+00:00'))
            date_str = meeting_date.strftime("%B %d, %Y at %I:%M %p")
        except ValueError:
            date_str = meeting_date
    else:
        date_str = meeting_date.strftime("%B %d, %Y at %I:%M %p") if meeting_date else "N/A"
    
    # Build agenda/discussion HTML
    agenda_items = meeting.get("agenda", [])
    discussion_items = meeting.get("discussion_points", [])
    decisions = meeting.get("decisions_made", [])
    action_items = meeting.get("action_items", [])
    
    agenda_html = "".join([f"<li>{item}</li>" for item in agenda_items if item])
    discussion_html = "".join([f"<li>{item}</li>" for item in discussion_items if item])
    decisions_html = "".join([f"<li>{item}</li>" for item in decisions if item])
    
    action_rows = ""
    for item in action_items:
        if isinstance(item, dict):
            action_rows += f"""
            <tr>
                <td style="padding: 8px; border: 1px solid #e5e7eb;">{item.get('description', '')}</td>
                <td style="padding: 8px; border: 1px solid #e5e7eb;">{item.get('assigned_to_name', 'TBD')}</td>
                <td style="padding: 8px; border: 1px solid #e5e7eb;">{item.get('due_date', 'TBD')}</td>
            </tr>
            """
    
    html_content = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <div style="background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); padding: 20px; border-radius: 8px 8px 0 0;">
            <h1 style="color: #10b981; margin: 0; font-size: 24px;">Minutes of Meeting</h1>
            <p style="color: #9ca3af; margin: 5px 0 0 0;">{meeting.get('title', 'Meeting')}</p>
        </div>
        
        <div style="background: #ffffff; padding: 20px; border: 1px solid #e5e7eb; border-top: none;">
            <p style="color: #374151;"><strong>Date:</strong> {date_str}</p>
            <p style="color: #374151;"><strong>Attendees:</strong> {', '.join(meeting.get('attendee_names', []))}</p>
            
            {"<h3 style='color: #1f2937; border-bottom: 2px solid #10b981; padding-bottom: 5px;'>Agenda</h3><ul style='color: #374151;'>" + agenda_html + "</ul>" if agenda_html else ""}
            
            {"<h3 style='color: #1f2937; border-bottom: 2px solid #10b981; padding-bottom: 5px;'>Discussion Points</h3><ul style='color: #374151;'>" + discussion_html + "</ul>" if discussion_html else ""}
            
            {"<h3 style='color: #1f2937; border-bottom: 2px solid #10b981; padding-bottom: 5px;'>Decisions Made</h3><ul style='color: #374151;'>" + decisions_html + "</ul>" if decisions_html else ""}
            
            {"<h3 style='color: #1f2937; border-bottom: 2px solid #10b981; padding-bottom: 5px;'>Action Items</h3><table style='width: 100%; border-collapse: collapse;'><tr style='background: #f3f4f6;'><th style='padding: 8px; text-align: left; border: 1px solid #e5e7eb;'>Task</th><th style='padding: 8px; text-align: left; border: 1px solid #e5e7eb;'>Owner</th><th style='padding: 8px; text-align: left; border: 1px solid #e5e7eb;'>Due Date</th></tr>" + action_rows + "</table>" if action_rows else ""}
        </div>
        
        <div style="background: #f9fafb; padding: 15px; border-radius: 0 0 8px 8px; border: 1px solid #e5e7eb; border-top: none;">
            <p style="color: #6b7280; font-size: 12px; margin: 0;">This is an automated message from D&V Business Consulting.</p>
        </div>
    </div>
    """
    
    # Send email
    try:
        await send_email(
            to_email=client_email,
            subject=f"Minutes of Meeting - {meeting.get('title', 'Meeting')} ({date_str})",
            html_content=html_content,
            plain_content=f"Minutes of Meeting\n\nDate: {date_str}\nTitle: {meeting.get('title')}\n\nPlease view this email in HTML format for full details."
        )
        
        # Update meeting
        await db.meetings.update_one(
            {"id": meeting_id},
            {
                "$set": {
                    "mom_sent_to_client": True,
                    "mom_sent_at": datetime.now(timezone.utc).isoformat(),
                    "mom_sent_to_email": client_email
                }
            }
        )
        
        logger.info(f"Auto-sent MOM for meeting {meeting_id} to {client_email}")
        
        return {
            "success": True,
            "sent_to": client_email,
            "client_name": client_name
        }
        
    except Exception as e:
        logger.error(f"Failed to send MOM email for meeting {meeting_id}: {e}")
        return {"error": str(e)}
