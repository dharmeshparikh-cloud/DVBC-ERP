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
        }
    }
