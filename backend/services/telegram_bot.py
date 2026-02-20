"""
NETRA ERP Telegram Bot Service
Handles meeting logs, leave applications, and approvals via Telegram
"""

import os
import re
import httpx
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from motor.motor_asyncio import AsyncIOMotorDatabase
import logging

logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

# Conversation states
CONV_STATE = {}

class ConversationState:
    IDLE = "idle"
    MEETING_CLIENT = "meeting_client"
    MEETING_DURATION = "meeting_duration"
    MEETING_NOTES = "meeting_notes"
    LEAVE_TYPE = "leave_type"
    LEAVE_DATES = "leave_dates"
    LEAVE_REASON = "leave_reason"
    TIMESHEET_PROJECT = "timesheet_project"
    TIMESHEET_HOURS = "timesheet_hours"
    TIMESHEET_TASK = "timesheet_task"
    EXPENSE_TYPE = "expense_type"
    EXPENSE_AMOUNT = "expense_amount"
    EXPENSE_DESCRIPTION = "expense_description"
    EXPENSE_RECEIPT = "expense_receipt"


def parse_time_duration(text: str) -> Optional[Dict[str, Any]]:
    """
    Parse various time formats and return duration in hours
    Supports: "11:45 to 18:45", "9am - 5pm", "2.5 hours", "45 mins", "1h 15m"
    """
    text = text.lower().strip()
    
    # Pattern 1: Time range "11:45 to 18:45" or "11:45 - 18:45"
    time_range_pattern = r'(\d{1,2})[:\.]?(\d{2})?\s*(?:am|pm)?\s*(?:to|-)\s*(\d{1,2})[:\.]?(\d{2})?\s*(?:am|pm)?'
    match = re.search(time_range_pattern, text)
    if match:
        start_hour = int(match.group(1))
        start_min = int(match.group(2) or 0)
        end_hour = int(match.group(3))
        end_min = int(match.group(4) or 0)
        
        # Handle AM/PM
        if 'pm' in text:
            parts = text.split('to') if 'to' in text else text.split('-')
            if len(parts) == 2:
                if 'pm' in parts[1] and end_hour < 12:
                    end_hour += 12
                if 'pm' in parts[0] and start_hour < 12:
                    start_hour += 12
                if 'am' in parts[1] and end_hour == 12:
                    end_hour = 0
                if 'am' in parts[0] and start_hour == 12:
                    start_hour = 0
        
        # Calculate duration
        start_minutes = start_hour * 60 + start_min
        end_minutes = end_hour * 60 + end_min
        
        if end_minutes < start_minutes:
            end_minutes += 24 * 60  # Next day
            
        duration_minutes = end_minutes - start_minutes
        duration_hours = duration_minutes / 60
        
        return {
            "start_time": f"{start_hour:02d}:{start_min:02d}",
            "end_time": f"{end_hour:02d}:{end_min:02d}",
            "duration_hours": round(duration_hours, 2),
            "duration_display": format_duration(duration_hours)
        }
    
    # Pattern 2: Direct hours "2.5 hours" or "2 hours"
    hours_pattern = r'(\d+\.?\d*)\s*(?:hours?|hrs?|h)'
    match = re.search(hours_pattern, text)
    if match:
        hours = float(match.group(1))
        return {
            "duration_hours": hours,
            "duration_display": format_duration(hours)
        }
    
    # Pattern 3: Minutes "45 mins" or "90 minutes"
    mins_pattern = r'(\d+)\s*(?:minutes?|mins?|m)(?:\s|$)'
    match = re.search(mins_pattern, text)
    if match:
        minutes = int(match.group(1))
        hours = minutes / 60
        return {
            "duration_hours": round(hours, 2),
            "duration_display": format_duration(hours)
        }
    
    # Pattern 4: Combined "1h 15m" or "2h30m"
    combined_pattern = r'(\d+)\s*h(?:ours?)?\s*(\d+)?\s*m?'
    match = re.search(combined_pattern, text)
    if match:
        hours = int(match.group(1))
        minutes = int(match.group(2) or 0)
        total_hours = hours + minutes / 60
        return {
            "duration_hours": round(total_hours, 2),
            "duration_display": format_duration(total_hours)
        }
    
    # Pattern 5: Quick options
    quick_options = {
        "30 min": 0.5,
        "1 hour": 1,
        "2 hours": 2,
        "3 hours": 3,
        "half day": 4,
        "full day": 8
    }
    for option, hours in quick_options.items():
        if option in text:
            return {
                "duration_hours": hours,
                "duration_display": format_duration(hours)
            }
    
    return None


def format_duration(hours: float) -> str:
    """Format hours to human readable string"""
    if hours == int(hours):
        return f"{int(hours)} hour{'s' if hours != 1 else ''}"
    else:
        h = int(hours)
        m = int((hours - h) * 60)
        if h == 0:
            return f"{m} min"
        return f"{h}h {m}m"


async def send_telegram_message(chat_id: int, text: str, reply_markup: dict = None) -> bool:
    """Send a message to Telegram chat"""
    try:
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML"
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup
            
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{TELEGRAM_API_URL}/sendMessage",
                json=payload,
                timeout=10
            )
            return response.status_code == 200
    except Exception as e:
        logger.error(f"Failed to send Telegram message: {e}")
        return False


def get_quick_reply_keyboard(options: list) -> dict:
    """Create inline keyboard with quick reply buttons"""
    keyboard = []
    row = []
    for i, option in enumerate(options):
        row.append({"text": option, "callback_data": option})
        if len(row) == 3 or i == len(options) - 1:
            keyboard.append(row)
            row = []
    return {"inline_keyboard": keyboard}


def get_user_state(chat_id: int) -> dict:
    """Get or create user conversation state"""
    if chat_id not in CONV_STATE:
        CONV_STATE[chat_id] = {
            "state": ConversationState.IDLE,
            "data": {}
        }
    return CONV_STATE[chat_id]


def set_user_state(chat_id: int, state: str, data: dict = None):
    """Set user conversation state"""
    if chat_id not in CONV_STATE:
        CONV_STATE[chat_id] = {"state": state, "data": data or {}}
    else:
        CONV_STATE[chat_id]["state"] = state
        if data:
            CONV_STATE[chat_id]["data"].update(data)


def clear_user_state(chat_id: int):
    """Clear user conversation state"""
    if chat_id in CONV_STATE:
        CONV_STATE[chat_id] = {"state": ConversationState.IDLE, "data": {}}


async def get_employee_by_telegram(db: AsyncIOMotorDatabase, telegram_username: str = None, telegram_id: int = None) -> Optional[dict]:
    """Find employee by Telegram username or ID"""
    query = {}
    if telegram_username:
        query["telegram_username"] = telegram_username.lower().replace("@", "")
    elif telegram_id:
        query["telegram_id"] = telegram_id
    
    if query:
        employee = await db.employees.find_one(query)
        return employee
    return None


async def link_telegram_account(db: AsyncIOMotorDatabase, employee_id: str, telegram_id: int, telegram_username: str):
    """Link Telegram account to employee"""
    await db.employees.update_one(
        {"employee_id": employee_id},
        {"$set": {
            "telegram_id": telegram_id,
            "telegram_username": telegram_username.lower().replace("@", "") if telegram_username else None,
            "telegram_linked_at": datetime.utcnow()
        }}
    )


async def get_recent_clients(db: AsyncIOMotorDatabase, employee_id: str, limit: int = 5) -> list:
    """Get recently met clients for quick selection"""
    # Get from leads/agreements
    leads = await db.leads.find(
        {"assigned_to": employee_id}
    ).sort("updated_at", -1).limit(limit).to_list(limit)
    
    clients = [lead.get("company_name", lead.get("name", "Unknown")) for lead in leads]
    return clients if clients else ["ABC Corp", "XYZ Ltd", "Tech Solutions"]


async def get_active_projects(db: AsyncIOMotorDatabase, employee_id: str) -> list:
    """Get active projects for the employee"""
    # Get from consultant assignments
    assignments = await db.consultant_assignments.find(
        {"consultant_id": employee_id, "status": "active"}
    ).to_list(20)
    
    project_ids = [a.get("project_id") for a in assignments]
    projects = await db.projects.find(
        {"id": {"$in": project_ids}}
    ).to_list(20)
    
    return [{"id": p.get("id"), "name": p.get("name", "Unknown Project")} for p in projects]


async def save_meeting_log(db: AsyncIOMotorDatabase, data: dict) -> str:
    """Save meeting log to database"""
    meeting = {
        "id": f"MTG-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "employee_id": data.get("employee_id"),
        "employee_name": data.get("employee_name"),
        "client_name": data.get("client_name"),
        "meeting_date": data.get("meeting_date", datetime.now().strftime("%Y-%m-%d")),
        "start_time": data.get("start_time"),
        "end_time": data.get("end_time"),
        "duration_hours": data.get("duration_hours"),
        "notes": data.get("notes"),
        "source": "telegram",
        "created_at": datetime.utcnow(),
        "status": "logged"
    }
    
    await db.meeting_logs.insert_one(meeting)
    
    # Also create timesheet entry if linked to project
    if data.get("project_id"):
        timesheet = {
            "employee_id": data.get("employee_id"),
            "project_id": data.get("project_id"),
            "date": data.get("meeting_date", datetime.now().strftime("%Y-%m-%d")),
            "hours": data.get("duration_hours"),
            "description": f"Client meeting: {data.get('client_name')} - {data.get('notes', '')}",
            "source": "telegram",
            "created_at": datetime.utcnow(),
            "status": "pending"
        }
        await db.timesheets.insert_one(timesheet)
    
    return meeting["id"]


async def handle_telegram_message(db: AsyncIOMotorDatabase, message: dict) -> str:
    """Main handler for incoming Telegram messages"""
    chat_id = message.get("chat", {}).get("id")
    text = message.get("text", "").strip()
    user = message.get("from", {})
    telegram_username = user.get("username", "")
    telegram_id = user.get("id")
    first_name = user.get("first_name", "User")
    
    if not chat_id or not text:
        return "Invalid message"
    
    # Get user state
    user_state = get_user_state(chat_id)
    current_state = user_state["state"]
    state_data = user_state["data"]
    
    # Check if employee is linked
    employee = await get_employee_by_telegram(db, telegram_username, telegram_id)
    
    # Handle commands
    text_lower = text.lower()
    
    # === COMMAND: /start ===
    if text_lower == "/start":
        if employee:
            welcome_msg = f"""
<b>Welcome back, {employee.get('first_name', first_name)}!</b>

I'm your NETRA ERP assistant. Here's what I can help with:

<b>Quick Commands:</b>
• <code>Log meeting</code> - Record client meeting
• <code>Apply leave</code> - Submit leave request
• <code>Log hours</code> - Add timesheet entry
• <code>My leaves</code> - Check leave balance
• <code>My tasks</code> - View assigned tasks

Just type a command or tap a button below!
"""
            keyboard = get_quick_reply_keyboard(["Log meeting", "Apply leave", "My leaves"])
        else:
            welcome_msg = f"""
<b>Hello {first_name}!</b>

I'm NETRA ERP Bot. To use me, please link your account first.

Send your Employee ID (e.g., <code>EMP001</code>) to get started.
"""
            keyboard = None
        
        await send_telegram_message(chat_id, welcome_msg, keyboard)
        return "Sent welcome message"
    
    # === COMMAND: Link account ===
    if not employee and text_lower.startswith("emp"):
        # Try to link account
        potential_emp_id = text.upper()
        emp = await db.employees.find_one({"employee_id": potential_emp_id})
        if emp:
            await link_telegram_account(db, potential_emp_id, telegram_id, telegram_username)
            msg = f"""
<b>Account Linked Successfully!</b>

Welcome, <b>{emp.get('first_name', '')} {emp.get('last_name', '')}</b>!

You're now connected to NETRA ERP. Try these commands:
• <code>Log meeting</code>
• <code>Apply leave</code>
• <code>My leaves</code>
"""
            keyboard = get_quick_reply_keyboard(["Log meeting", "Apply leave", "My leaves"])
            await send_telegram_message(chat_id, msg, keyboard)
            return "Account linked"
        else:
            await send_telegram_message(chat_id, f"Employee ID <code>{potential_emp_id}</code> not found. Please check and try again.")
            return "Employee not found"
    
    # Require linked account for other commands
    if not employee:
        await send_telegram_message(chat_id, "Please link your account first by sending your Employee ID (e.g., <code>EMP001</code>)")
        return "Account not linked"
    
    employee_id = employee.get("employee_id")
    employee_name = f"{employee.get('first_name', '')} {employee.get('last_name', '')}"
    
    # === COMMAND: Log meeting ===
    if text_lower in ["log meeting", "meeting", "add meeting"]:
        clients = await get_recent_clients(db, employee_id)
        msg = """
<b>Log Client Meeting</b>

Let's capture your meeting details.

<b>Which client did you meet?</b>
<i>Select below or type the client name:</i>
"""
        keyboard = get_quick_reply_keyboard(clients[:5])
        set_user_state(chat_id, ConversationState.MEETING_CLIENT, {"employee_id": employee_id, "employee_name": employee_name})
        await send_telegram_message(chat_id, msg, keyboard)
        return "Started meeting log flow"
    
    # === COMMAND: Apply leave ===
    if text_lower in ["apply leave", "leave", "request leave"]:
        # Get leave balance
        leave_balance = employee.get("leave_balance", {"casual_leave": 12, "sick_leave": 6, "earned_leave": 15})
        
        msg = f"""
<b>Apply for Leave</b>

<b>Your current balance:</b>
• Casual Leave: <b>{leave_balance.get('casual_leave', 12)} days</b>
• Sick Leave: <b>{leave_balance.get('sick_leave', 6)} days</b>
• Earned Leave: <b>{leave_balance.get('earned_leave', 15)} days</b>

<b>Which type of leave?</b>
"""
        keyboard = get_quick_reply_keyboard(["Casual", "Sick", "Earned"])
        set_user_state(chat_id, ConversationState.LEAVE_TYPE, {"employee_id": employee_id, "employee_name": employee_name})
        await send_telegram_message(chat_id, msg, keyboard)
        return "Started leave application flow"
    
    # === COMMAND: My leaves ===
    if text_lower in ["my leaves", "leave balance", "check leave"]:
        leave_balance = employee.get("leave_balance", {"casual_leave": 12, "sick_leave": 6, "earned_leave": 15})
        
        # Get pending leave requests
        pending_leaves = await db.leave_requests.find({
            "employee_id": employee_id,
            "status": "pending"
        }).to_list(5)
        
        pending_text = ""
        if pending_leaves:
            pending_text = "\n\n<b>Pending Requests:</b>\n"
            for leave in pending_leaves:
                pending_text += f"• {leave.get('leave_type', 'Leave')}: {leave.get('start_date', '')} to {leave.get('end_date', '')}\n"
        
        msg = f"""
<b>Your Leave Balance</b>

• Casual Leave: <b>{leave_balance.get('casual_leave', 12)} days</b>
• Sick Leave: <b>{leave_balance.get('sick_leave', 6)} days</b>
• Earned Leave: <b>{leave_balance.get('earned_leave', 15)} days</b>
{pending_text}
<i>Type "Apply leave" to submit a new request</i>
"""
        keyboard = get_quick_reply_keyboard(["Apply leave", "Log meeting"])
        await send_telegram_message(chat_id, msg, keyboard)
        return "Showed leave balance"
    
    # === COMMAND: Log hours / Timesheet ===
    if text_lower in ["log hours", "timesheet", "add hours", "log time"]:
        # Get active projects
        projects = await get_active_projects(db, employee_id)
        
        if not projects:
            msg = """
<b>Log Timesheet Hours</b>

You don't have any active project assignments.

Please contact your manager to get assigned to a project.
"""
            await send_telegram_message(chat_id, msg)
            return "No projects"
        
        project_names = [p.get("name", "Unknown")[:20] for p in projects[:5]]
        
        msg = """
<b>Log Timesheet Hours</b>

<b>Select project:</b>
<i>Or type the project name</i>
"""
        keyboard = get_quick_reply_keyboard(project_names)
        set_user_state(chat_id, ConversationState.TIMESHEET_PROJECT, {
            "employee_id": employee_id, 
            "employee_name": employee_name,
            "projects": {p.get("name"): p.get("id") for p in projects}
        })
        await send_telegram_message(chat_id, msg, keyboard)
        return "Started timesheet flow"
    
    # === COMMAND: Add expense ===
    if text_lower in ["add expense", "expense", "submit expense", "log expense"]:
        msg = """
<b>Submit Expense</b>

<b>What type of expense?</b>
"""
        keyboard = get_quick_reply_keyboard(["Travel", "Food", "Accommodation", "Office Supplies", "Client Meeting", "Other"])
        set_user_state(chat_id, ConversationState.EXPENSE_TYPE, {"employee_id": employee_id, "employee_name": employee_name})
        await send_telegram_message(chat_id, msg, keyboard)
        return "Started expense flow"
    
    # === COMMAND: Pending approvals (for managers) ===
    if text_lower in ["pending approvals", "approvals", "my approvals"]:
        # Check if user is a manager
        reportees = await db.employees.find({"reporting_manager_id": employee_id}).to_list(100)
        
        if not reportees:
            await send_telegram_message(chat_id, "You don't have any team members reporting to you.")
            return "Not a manager"
        
        # Get pending leave requests
        reportee_ids = [r.get("employee_id") for r in reportees]
        pending_leaves = await db.leave_requests.find({
            "employee_id": {"$in": reportee_ids},
            "status": "pending"
        }).to_list(10)
        
        if not pending_leaves:
            msg = """
<b>Pending Approvals</b>

No pending approvals.

Your team is all caught up!
"""
        else:
            msg = f"""
<b>Pending Approvals</b>

You have <b>{len(pending_leaves)}</b> pending leave request(s):

"""
            for leave in pending_leaves[:5]:
                emp = await db.employees.find_one({"employee_id": leave.get("employee_id")})
                emp_name = f"{emp.get('first_name', '')} {emp.get('last_name', '')}" if emp else leave.get("employee_id")
                msg += f"• <b>{emp_name}</b>: {leave.get('leave_type', 'Leave')} ({leave.get('start_date', '')} to {leave.get('end_date', '')})\n"
            
            msg += "\n<i>Open NETRA app to approve/reject</i>"
        
        keyboard = get_quick_reply_keyboard(["Log meeting", "My leaves"])
        await send_telegram_message(chat_id, msg, keyboard)
        return "Showed pending approvals"
    
    # === CONVERSATION FLOWS ===
    
    # Meeting Flow - Client Selection
    if current_state == ConversationState.MEETING_CLIENT:
        state_data["client_name"] = text
        msg = """
<b>Meeting Duration?</b>

<i>Select a quick option or type custom time:</i>
• <code>11:45 to 18:45</code>
• <code>2.5 hours</code>
• <code>1h 30m</code>
"""
        keyboard = get_quick_reply_keyboard(["30 min", "1 hour", "2 hours", "3 hours", "Half day", "Full day"])
        set_user_state(chat_id, ConversationState.MEETING_DURATION, state_data)
        await send_telegram_message(chat_id, msg, keyboard)
        return "Waiting for duration"
    
    # Meeting Flow - Duration
    if current_state == ConversationState.MEETING_DURATION:
        duration_info = parse_time_duration(text)
        if not duration_info:
            await send_telegram_message(chat_id, "I couldn't understand that time format. Please try again:\n• <code>11:45 to 18:45</code>\n• <code>2 hours</code>\n• <code>90 mins</code>")
            return "Invalid duration"
        
        state_data.update(duration_info)
        
        confirm_msg = f"Got it! <b>{duration_info['duration_display']}</b>"
        if duration_info.get('start_time'):
            confirm_msg += f" ({duration_info['start_time']} - {duration_info['end_time']})"
        
        msg = f"""
{confirm_msg}

<b>Brief notes/outcome?</b>
<i>Type key points from the meeting:</i>
"""
        set_user_state(chat_id, ConversationState.MEETING_NOTES, state_data)
        await send_telegram_message(chat_id, msg)
        return "Waiting for notes"
    
    # Meeting Flow - Notes (Final)
    if current_state == ConversationState.MEETING_NOTES:
        state_data["notes"] = text
        state_data["meeting_date"] = datetime.now().strftime("%Y-%m-%d")
        
        # Save meeting
        meeting_id = await save_meeting_log(db, state_data)
        
        # Calculate billable amount (example: Rs 5000/hour)
        billable = state_data.get("duration_hours", 0) * 5000
        
        time_display = f"{state_data.get('start_time', '')} - {state_data.get('end_time', '')}" if state_data.get('start_time') else state_data.get('duration_display', '')
        
        msg = f"""
<b>Meeting Logged Successfully!</b>

<b>Client:</b> {state_data.get('client_name', 'N/A')}
<b>Time:</b> {time_display}
<b>Duration:</b> {state_data.get('duration_display', 'N/A')}
<b>Date:</b> {state_data.get('meeting_date', 'Today')}
<b>ID:</b> <code>{meeting_id}</code>

<i>Synced to NETRA ERP</i>
"""
        keyboard = get_quick_reply_keyboard(["Log meeting", "Apply leave", "My leaves"])
        clear_user_state(chat_id)
        await send_telegram_message(chat_id, msg, keyboard)
        return "Meeting logged"
    
    # Leave Flow - Type Selection
    if current_state == ConversationState.LEAVE_TYPE:
        leave_type = text.lower()
        if leave_type not in ["casual", "sick", "earned"]:
            leave_type = "casual"  # Default
        
        state_data["leave_type"] = leave_type
        msg = """
<b>Leave Dates?</b>

<i>Enter dates in any format:</i>
• <code>25 Dec</code> (single day)
• <code>25-27 Dec</code> (range)
• <code>25 Dec to 27 Dec</code>
"""
        set_user_state(chat_id, ConversationState.LEAVE_DATES, state_data)
        await send_telegram_message(chat_id, msg)
        return "Waiting for dates"
    
    # Leave Flow - Dates
    if current_state == ConversationState.LEAVE_DATES:
        state_data["dates_raw"] = text
        # Parse dates (simplified)
        state_data["start_date"] = text.split("-")[0].strip() if "-" in text else text.split("to")[0].strip() if "to" in text else text
        state_data["end_date"] = text.split("-")[-1].strip() if "-" in text else text.split("to")[-1].strip() if "to" in text else text
        
        msg = """
<b>Reason for leave?</b>
<i>Brief description:</i>
"""
        set_user_state(chat_id, ConversationState.LEAVE_REASON, state_data)
        await send_telegram_message(chat_id, msg)
        return "Waiting for reason"
    
    # Leave Flow - Reason (Final)
    if current_state == ConversationState.LEAVE_REASON:
        state_data["reason"] = text
        
        # Create leave request
        leave_request = {
            "employee_id": state_data.get("employee_id"),
            "employee_name": state_data.get("employee_name"),
            "leave_type": f"{state_data.get('leave_type', 'casual')}_leave",
            "start_date": state_data.get("start_date"),
            "end_date": state_data.get("end_date"),
            "reason": state_data.get("reason"),
            "status": "pending",
            "source": "telegram",
            "created_at": datetime.utcnow()
        }
        
        await db.leave_requests.insert_one(leave_request)
        
        # Get reporting manager
        rm = await db.employees.find_one({"employee_id": employee.get("reporting_manager_id")})
        rm_name = f"{rm.get('first_name', '')} {rm.get('last_name', '')}" if rm else "Manager"
        
        msg = f"""
<b>Leave Request Submitted!</b>

<b>Type:</b> {state_data.get('leave_type', 'Casual').title()} Leave
<b>Dates:</b> {state_data.get('start_date', '')} to {state_data.get('end_date', '')}
<b>Reason:</b> {state_data.get('reason', '')}
<b>Status:</b> Pending Approval

<i>Sent to: {rm_name}</i>
"""
        keyboard = get_quick_reply_keyboard(["My leaves", "Log meeting"])
        clear_user_state(chat_id)
        await send_telegram_message(chat_id, msg, keyboard)
        
        # TODO: Send notification to manager's Telegram if linked
        
        return "Leave request submitted"
    
    # === DEFAULT: Show help ===
    msg = f"""
<b>Hi {employee.get('first_name', first_name)}!</b>

I didn't understand that. Try these commands:

• <code>Log meeting</code> - Record client meeting
• <code>Apply leave</code> - Submit leave request
• <code>My leaves</code> - Check leave balance

Or tap a button below:
"""
    keyboard = get_quick_reply_keyboard(["Log meeting", "Apply leave", "My leaves"])
    await send_telegram_message(chat_id, msg, keyboard)
    return "Showed help"


async def handle_callback_query(db: AsyncIOMotorDatabase, callback_query: dict) -> str:
    """Handle inline keyboard button clicks"""
    chat_id = callback_query.get("message", {}).get("chat", {}).get("id")
    data = callback_query.get("data", "")
    
    if not chat_id or not data:
        return "Invalid callback"
    
    # Treat callback data as if it was a text message
    fake_message = {
        "chat": {"id": chat_id},
        "text": data,
        "from": callback_query.get("from", {})
    }
    
    return await handle_telegram_message(db, fake_message)
