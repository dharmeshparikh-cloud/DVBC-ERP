"""
my_day.py - "My Day" aggregation endpoint for consultant daily workflow
Returns attendance status, today's meetings, overdue MOMs, pending expenses,
and weekly progress in a single API call.
"""

from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends
from .deps import get_db, get_current_user
from .models import User

router = APIRouter()


@router.get("/my-day/summary")
async def get_my_day_summary(current_user: User = Depends(get_current_user)):
    """Aggregate all daily workflow data for the logged-in user."""
    db = get_db()
    now = datetime.now(timezone.utc)
    today_str = now.strftime("%Y-%m-%d")
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = now.replace(hour=23, minute=59, second=59, microsecond=999999)
    
    # Week boundaries (Monday-Sunday)
    week_start = today_start - timedelta(days=now.weekday())
    week_end = week_start + timedelta(days=6, hours=23, minutes=59, seconds=59)

    user_id = current_user.id
    emp_id = current_user.employee_id

    # === 1. Attendance Status ===
    attendance_record = await db.attendance.find_one(
        {"employee_id": emp_id, "date": today_str},
        {"_id": 0}
    )
    is_checked_in = bool(attendance_record and attendance_record.get("check_in"))
    check_in_time = attendance_record.get("check_in") if attendance_record else None
    check_out_time = attendance_record.get("check_out") if attendance_record else None

    # === 2. Today's Meetings ===
    all_meetings = await db.meetings.find(
        {
            "$or": [
                {"scheduled_by": user_id},
                {"attendees": user_id},
                {"created_by": user_id}
            ]
        },
        {"_id": 0, "id": 1, "title": 1, "meeting_date": 1, "status": 1,
         "mode": 1, "mom_generated": 1, "mom_sent_to_client": 1,
         "is_delivered": 1, "project_name": 1, "client_name": 1,
         "duration_minutes": 1, "start_time": 1, "expense_id": 1,
         "action_items": 1, "sow_id": 1}
    ).to_list(500)

    today_meetings = []
    upcoming_meetings = []
    overdue_mom_meetings = []
    pending_client_send = []
    this_week_meetings = []

    for m in all_meetings:
        try:
            md = m.get("meeting_date")
            if not md:
                continue
            if isinstance(md, str):
                meeting_dt = datetime.fromisoformat(md.replace("Z", "+00:00"))
            else:
                meeting_dt = md if md.tzinfo else md.replace(tzinfo=timezone.utc)
            
            meeting_date_str = meeting_dt.strftime("%Y-%m-%d")
            
            # Today's meetings
            if meeting_date_str == today_str:
                today_meetings.append(m)
            
            # This week's meetings
            if week_start <= meeting_dt <= week_end:
                this_week_meetings.append(m)
            
            # Upcoming (future, not today)
            if meeting_dt > today_end:
                upcoming_meetings.append(m)
            
            # Overdue MOM: past meeting, not cancelled, MOM not generated
            if meeting_dt < today_start and not m.get("mom_generated") and m.get("status") not in ("cancelled", "CANCELLED"):
                overdue_mom_meetings.append(m)
            
            # Pending client send: MOM generated but not sent
            if m.get("mom_generated") and not m.get("mom_sent_to_client"):
                pending_client_send.append(m)
                
        except Exception:
            continue

    # Sort today's meetings by time
    today_meetings.sort(key=lambda m: m.get("meeting_date", ""))
    upcoming_meetings.sort(key=lambda m: m.get("meeting_date", ""))

    # Next meeting
    next_meeting = None
    for m in today_meetings:
        try:
            md = m.get("meeting_date", "")
            if isinstance(md, str):
                mt = datetime.fromisoformat(md.replace("Z", "+00:00"))
            else:
                mt = md if md.tzinfo else md.replace(tzinfo=timezone.utc)
            if mt > now:
                next_meeting = {
                    "id": m.get("id"),
                    "title": m.get("title"),
                    "time": mt.strftime("%I:%M %p"),
                    "project_name": m.get("project_name"),
                    "mode": m.get("mode")
                }
                break
        except Exception:
            continue

    # === 3. Pending Expenses ===
    pending_expenses = await db.expenses.count_documents({
        "$or": [
            {"user_id": user_id},
            {"employee_id": emp_id},
            {"created_by": user_id}
        ],
        "status": "pending"
    })

    # In-person meetings today with no expense
    inperson_no_expense = [
        m for m in today_meetings 
        if m.get("mode") in ("offline", "in-person") and not m.get("expense_id")
    ]

    # === 4. Tasks/Action Items ===
    open_action_items = 0
    for m in all_meetings:
        for ai in (m.get("action_items") or []):
            if ai.get("status") != "completed" and ai.get("assignee_id") == user_id:
                open_action_items += 1

    # === 5. Weekly Progress ===
    week_total = len(this_week_meetings)
    week_delivered = len([m for m in this_week_meetings if m.get("is_delivered")])
    week_mom_done = len([m for m in this_week_meetings if m.get("mom_generated")])

    # === 6. Smart Suggestions (AI-powered recommendations) ===
    suggestions = []
    
    # Priority 1: Attendance not marked
    if not is_checked_in:
        suggestions.append({
            "id": "attendance",
            "priority": "high",
            "icon": "clock",
            "title": "Start your day",
            "description": "Mark your attendance to begin tracking your work hours",
            "action": "Check In Now",
            "action_path": "/my-attendance",
            "category": "attendance"
        })
    
    # Priority 2: Upcoming meeting prep (meeting in next 2 hours)
    for m in today_meetings:
        try:
            md = m.get("meeting_date", "")
            if isinstance(md, str):
                mt = datetime.fromisoformat(md.replace("Z", "+00:00"))
            else:
                mt = md if md.tzinfo else md.replace(tzinfo=timezone.utc)
            hours_until = (mt - now).total_seconds() / 3600
            if 0 < hours_until <= 2:
                suggestions.append({
                    "id": f"prep_{m.get('id')}",
                    "priority": "high",
                    "icon": "calendar",
                    "title": f"Prepare for: {m.get('title', 'Meeting')[:30]}",
                    "description": f"Meeting with {m.get('client_name', 'client')} in {int(hours_until * 60)} minutes",
                    "action": "View Details",
                    "action_path": "/consulting-meetings",
                    "category": "meeting_prep"
                })
                break  # Only show one prep suggestion
        except Exception:
            continue
    
    # Priority 3: Overdue MOMs (most critical workflow blocker)
    if len(overdue_mom_meetings) > 0:
        oldest_overdue = overdue_mom_meetings[0]
        suggestions.append({
            "id": "overdue_mom",
            "priority": "high",
            "icon": "file-text",
            "title": f"Record MOM for {oldest_overdue.get('title', 'meeting')[:25]}",
            "description": f"{len(overdue_mom_meetings)} meeting(s) awaiting MOM - blocking delivery",
            "action": "Record Now",
            "action_path": "/consulting-meetings",
            "category": "mom"
        })
    
    # Priority 4: MOMs ready to send
    if len(pending_client_send) > 0:
        suggestions.append({
            "id": "send_mom",
            "priority": "medium",
            "icon": "send",
            "title": "Send MOM to client",
            "description": f"{len(pending_client_send)} MOM(s) recorded but not sent to client",
            "action": "Send Now",
            "action_path": "/consulting-meetings",
            "category": "communication"
        })
    
    # Priority 5: Open action items
    if open_action_items > 0:
        suggestions.append({
            "id": "action_items",
            "priority": "medium",
            "icon": "check-square",
            "title": f"Complete {open_action_items} action item(s)",
            "description": "Tasks assigned from previous meetings need attention",
            "action": "View Tasks",
            "action_path": "/consulting-meetings",
            "category": "tasks"
        })
    
    # Priority 6: Expense filing for in-person meetings
    if len(inperson_no_expense) > 0:
        suggestions.append({
            "id": "file_expense",
            "priority": "medium",
            "icon": "receipt",
            "title": "File travel expense",
            "description": f"{len(inperson_no_expense)} in-person meeting(s) without expense claims",
            "action": "File Expense",
            "action_path": "/my-expenses",
            "category": "expense"
        })
    
    # Priority 7: Pending expenses need follow-up
    if pending_expenses > 3:
        suggestions.append({
            "id": "pending_expenses",
            "priority": "low",
            "icon": "wallet",
            "title": "Follow up on expenses",
            "description": f"{pending_expenses} expenses pending approval - consider checking status",
            "action": "View Status",
            "action_path": "/my-expenses",
            "category": "expense"
        })
    
    # Priority 8: Upcoming meetings need preparation
    if len(upcoming_meetings) > 0:
        next_upcoming = upcoming_meetings[0]
        try:
            md = next_upcoming.get("meeting_date", "")
            if isinstance(md, str):
                mt = datetime.fromisoformat(md.replace("Z", "+00:00"))
            else:
                mt = md if md.tzinfo else md.replace(tzinfo=timezone.utc)
            days_until = (mt - now).days
            if days_until <= 2:
                suggestions.append({
                    "id": "upcoming_prep",
                    "priority": "low",
                    "icon": "calendar-check",
                    "title": f"Upcoming: {next_upcoming.get('title', 'Meeting')[:25]}",
                    "description": f"Meeting in {days_until} day(s) - review agenda and prepare",
                    "action": "Prepare",
                    "action_path": "/consulting-meetings",
                    "category": "planning"
                })
        except Exception:
            pass
    
    # Priority 9: Weekly progress encouragement
    if week_total > 0 and week_delivered >= week_total:
        suggestions.append({
            "id": "great_week",
            "priority": "info",
            "icon": "trophy",
            "title": "Great week!",
            "description": f"You've delivered all {week_total} meetings this week. Keep it up!",
            "action": None,
            "action_path": None,
            "category": "motivation"
        })
    elif week_total > 0 and week_delivered / week_total >= 0.8:
        remaining = week_total - week_delivered
        suggestions.append({
            "id": "almost_there",
            "priority": "info",
            "icon": "trending-up",
            "title": "Almost there!",
            "description": f"Just {remaining} more delivery to complete your weekly target",
            "action": "View Progress",
            "action_path": "/consulting-meetings",
            "category": "motivation"
        })
    
    # Limit to top 5 suggestions, sorted by priority
    priority_order = {"high": 0, "medium": 1, "low": 2, "info": 3}
    suggestions.sort(key=lambda s: priority_order.get(s.get("priority", "low"), 2))
    suggestions = suggestions[:5]

    # === Build Response ===
    return {
        "date": today_str,
        "greeting": f"Good {'morning' if now.hour < 12 else ('afternoon' if now.hour < 17 else 'evening')}, {current_user.full_name}",
        
        "attendance": {
            "is_checked_in": is_checked_in,
            "check_in_time": check_in_time,
            "check_out_time": check_out_time,
            "needs_action": not is_checked_in
        },
        
        "today": {
            "total_meetings": len(today_meetings),
            "meetings": [{
                "id": m.get("id"),
                "title": m.get("title"),
                "time": m.get("meeting_date"),
                "mode": m.get("mode"),
                "project_name": m.get("project_name"),
                "mom_done": bool(m.get("mom_generated")),
                "has_expense": bool(m.get("expense_id"))
            } for m in today_meetings],
            "next_meeting": next_meeting
        },
        
        "action_required": {
            "overdue_moms": {
                "count": len(overdue_mom_meetings),
                "meetings": [{
                    "id": m.get("id"),
                    "title": m.get("title"),
                    "date": m.get("meeting_date"),
                    "project_name": m.get("project_name")
                } for m in overdue_mom_meetings[:5]]
            },
            "pending_client_send": {
                "count": len(pending_client_send),
                "meetings": [{
                    "id": m.get("id"),
                    "title": m.get("title")
                } for m in pending_client_send[:5]]
            },
            "missing_expenses": {
                "count": len(inperson_no_expense),
                "meetings": [{
                    "id": m.get("id"),
                    "title": m.get("title"),
                    "mode": m.get("mode")
                } for m in inperson_no_expense]
            },
            "open_tasks": open_action_items,
            "pending_expenses": pending_expenses
        },
        
        "upcoming": {
            "count": len(upcoming_meetings),
            "next_3": [{
                "id": m.get("id"),
                "title": m.get("title"),
                "date": m.get("meeting_date"),
                "project_name": m.get("project_name")
            } for m in upcoming_meetings[:3]]
        },
        
        "weekly_progress": {
            "total_meetings": week_total,
            "delivered": week_delivered,
            "mom_recorded": week_mom_done,
            "completion_pct": round(week_delivered / max(week_total, 1) * 100)
        },
        
        "smart_suggestions": suggestions
    }
