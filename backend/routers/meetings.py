"""
Meetings Router - Meeting Management, MOM, Action Items
"""

from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
import uuid

from .models import Meeting, MeetingCreate, MOMCreate, ActionItemCreate, User
from .models import SALES_MEETING_ROLES, CONSULTING_MEETING_ROLES
from .deps import get_db
from .auth import get_current_user

router = APIRouter(prefix="/meetings", tags=["Meetings"])


@router.post("", response_model=Meeting)
async def create_meeting(meeting_create: MeetingCreate, current_user: User = Depends(get_current_user)):
    """Create a new meeting."""
    db = get_db()
    meeting_type = meeting_create.type
    
    # Role-based access control
    if current_user.role == "hr_manager":
        raise HTTPException(status_code=403, detail="HR Managers do not have CRUD access to meetings")
    if meeting_type == "sales" and current_user.role not in SALES_MEETING_ROLES:
        raise HTTPException(status_code=403, detail="Only sales roles can create sales meetings")
    if meeting_type == "consulting" and current_user.role not in CONSULTING_MEETING_ROLES:
        raise HTTPException(status_code=403, detail="Only consulting/PM roles can create consulting meetings")
    
    # Consulting meetings require project_id
    if meeting_type == "consulting" and not meeting_create.project_id:
        raise HTTPException(status_code=400, detail="Consulting meetings must be linked to a project")

    meeting_dict = meeting_create.model_dump()
    meeting = Meeting(**meeting_dict, created_by=current_user.id)

    doc = meeting.model_dump()
    doc['meeting_date'] = doc['meeting_date'].isoformat()
    doc['created_at'] = doc['created_at'].isoformat()

    await db.meetings.insert_one(doc)

    if meeting.is_delivered and meeting.project_id:
        await db.projects.update_one(
            {"id": meeting.project_id},
            {"$inc": {"total_meetings_delivered": 1, "number_of_visits": 1}}
        )

    return meeting


@router.get("", response_model=List[Meeting])
async def get_meetings(
    project_id: Optional[str] = None,
    meeting_type: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get all meetings with optional filters."""
    db = get_db()
    query = {}
    if project_id:
        query['project_id'] = project_id
    if meeting_type:
        query['type'] = meeting_type

    meetings = await db.meetings.find(query, {"_id": 0}).to_list(1000)

    for meeting in meetings:
        if isinstance(meeting.get('meeting_date'), str):
            meeting['meeting_date'] = datetime.fromisoformat(meeting['meeting_date'])
        if isinstance(meeting.get('created_at'), str):
            meeting['created_at'] = datetime.fromisoformat(meeting['created_at'])

    return meetings


@router.get("/lead/{lead_id}")
async def get_meetings_by_lead(lead_id: str, current_user: User = Depends(get_current_user)):
    """Get all meetings for a specific lead."""
    db = get_db()
    
    # Verify lead exists
    lead = await db.leads.find_one({"id": lead_id}, {"_id": 0})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    meetings = await db.meetings.find(
        {"lead_id": lead_id},
        {"_id": 0}
    ).sort("meeting_date", -1).to_list(100)
    
    for meeting in meetings:
        if isinstance(meeting.get('meeting_date'), str):
            meeting['meeting_date'] = datetime.fromisoformat(meeting['meeting_date'])
        if isinstance(meeting.get('created_at'), str):
            meeting['created_at'] = datetime.fromisoformat(meeting['created_at'])
    
    return meetings


@router.post("/record")
async def record_sales_meeting(
    data: Dict[str, Any],
    current_user: User = Depends(get_current_user)
):
    """
    Record a sales funnel meeting with MOM (Minutes of Meeting).
    MOM is required before meeting can be submitted.
    Used by the Sales Funnel flow.
    """
    db = get_db()
    
    # Validate required fields
    lead_id = data.get("lead_id")
    if not lead_id:
        raise HTTPException(status_code=400, detail="lead_id is required")
    
    # Verify lead exists
    lead = await db.leads.find_one({"id": lead_id}, {"_id": 0})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    meeting_date = data.get("meeting_date")
    meeting_time = data.get("meeting_time", "00:00")
    if not meeting_date:
        raise HTTPException(status_code=400, detail="meeting_date is required")
    
    # MOM is required
    mom = data.get("mom", "").strip()
    if not mom:
        raise HTTPException(status_code=400, detail="Minutes of Meeting (MOM) is required before submitting")
    
    # Parse meeting date and time
    try:
        if "T" in meeting_date:
            meeting_datetime = datetime.fromisoformat(meeting_date.replace('Z', '+00:00'))
        else:
            meeting_datetime = datetime.strptime(f"{meeting_date} {meeting_time}", "%Y-%m-%d %H:%M")
            meeting_datetime = meeting_datetime.replace(tzinfo=timezone.utc)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid meeting_date format")
    
    # Map meeting_type to mode
    meeting_type = data.get("meeting_type", "Online")
    mode = "online" if meeting_type.lower() == "online" else "offline"
    
    # Create meeting document with MOM
    meeting_id = str(uuid.uuid4())
    meeting_doc = {
        "id": meeting_id,
        "type": "sales",
        "lead_id": lead_id,
        "project_id": None,
        "client_id": None,
        "sow_id": None,
        "meeting_date": meeting_datetime.isoformat(),
        "meeting_time": meeting_time,
        "mode": mode,
        "meeting_type": meeting_type,
        "attendees": data.get("attendees", []),
        "attendee_names": data.get("attendees", []),
        "duration_minutes": data.get("duration_minutes"),
        "notes": data.get("notes", ""),
        "title": data.get("title") or f"Sales Meeting - {lead.get('company', 'Client')}",
        "is_delivered": True,
        # MOM fields
        "mom": mom,
        "mom_generated": True,
        "agenda": data.get("agenda", []),
        "discussion_points": data.get("discussion_points", []),
        "decisions_made": data.get("decisions_made", []),
        "action_items": data.get("action_items", []),
        "client_expectations": data.get("client_expectations", []),
        "key_commitments": data.get("key_commitments", []),
        "next_steps": data.get("next_steps", ""),
        "next_meeting_date": None,
        "mom_sent_to_client": False,
        "mom_sent_at": None,
        # Metadata
        "created_by": current_user.id,
        "created_by_name": current_user.full_name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.meetings.insert_one(meeting_doc)
    
    # Update lead stage to meeting if it's still at lead/new stage
    current_status = lead.get("status", "new").lower()
    if current_status in ["new", "lead", "contacted"]:
        await db.leads.update_one(
            {"id": lead_id},
            {"$set": {
                "status": "meeting",
                "stage": "meeting",
                "updated_at": datetime.now(timezone.utc).isoformat()
            }}
        )
    
    # Return meeting without _id
    if "_id" in meeting_doc:
        del meeting_doc["_id"]
    
    return {
        "message": "Meeting recorded successfully with MOM",
        "meeting_id": meeting_id,
        "meeting": meeting_doc
    }


@router.get("/{meeting_id}")
async def get_meeting(meeting_id: str, current_user: User = Depends(get_current_user)):
    """Get a single meeting with full MOM details."""
    db = get_db()
    meeting = await db.meetings.find_one({"id": meeting_id}, {"_id": 0})
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    
    if isinstance(meeting.get('meeting_date'), str):
        meeting['meeting_date'] = datetime.fromisoformat(meeting['meeting_date'])
    if isinstance(meeting.get('created_at'), str):
        meeting['created_at'] = datetime.fromisoformat(meeting['created_at'])
    
    return meeting


@router.patch("/{meeting_id}/mom")
async def update_meeting_mom(
    meeting_id: str,
    mom_data: MOMCreate,
    current_user: User = Depends(get_current_user)
):
    """Update Minutes of Meeting for a meeting."""
    db = get_db()
    meeting = await db.meetings.find_one({"id": meeting_id}, {"_id": 0})
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    
    update_data = mom_data.model_dump(exclude_unset=True)
    update_data['mom_generated'] = True
    update_data['updated_at'] = datetime.now(timezone.utc).isoformat()
    
    if update_data.get('next_meeting_date'):
        update_data['next_meeting_date'] = update_data['next_meeting_date'].isoformat()
    
    # Process action items
    action_items = update_data.get('action_items', [])
    for item in action_items:
        if not item.get('id'):
            item['id'] = str(uuid.uuid4())
        if item.get('due_date') and isinstance(item['due_date'], datetime):
            item['due_date'] = item['due_date'].isoformat()
    
    await db.meetings.update_one({"id": meeting_id}, {"$set": update_data})
    
    return {"message": "MOM updated successfully", "meeting_id": meeting_id}


@router.post("/{meeting_id}/action-items")
async def add_action_item(
    meeting_id: str,
    action_item: ActionItemCreate,
    current_user: User = Depends(get_current_user)
):
    """Add action item to meeting with optional follow-up task creation."""
    db = get_db()
    meeting = await db.meetings.find_one({"id": meeting_id}, {"_id": 0})
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    
    # Create action item
    new_item = {
        "id": str(uuid.uuid4()),
        "description": action_item.description,
        "assigned_to_id": action_item.assigned_to_id,
        "due_date": action_item.due_date.isoformat() if action_item.due_date else None,
        "priority": action_item.priority,
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    # Get assigned user name
    if action_item.assigned_to_id:
        user = await db.users.find_one({"id": action_item.assigned_to_id}, {"_id": 0, "full_name": 1})
        new_item["assigned_to_name"] = user.get("full_name") if user else None
    
    # Create follow-up task if requested
    follow_up_task_id = None
    if action_item.create_follow_up_task and action_item.assigned_to_id:
        # Get project info
        project = await db.projects.find_one({"id": meeting.get('project_id')}, {"_id": 0})
        
        follow_up_task = {
            "id": str(uuid.uuid4()),
            "type": "meeting_action_item",
            "meeting_id": meeting_id,
            "action_item_id": new_item["id"],
            "title": f"[Action Item] {action_item.description}",
            "description": f"Follow-up from meeting on {meeting.get('meeting_date', 'N/A')}",
            "assigned_to": action_item.assigned_to_id,
            "assigned_to_name": new_item.get("assigned_to_name"),
            "project_id": meeting.get('project_id'),
            "project_name": project.get('name') if project else None,
            "due_date": action_item.due_date.isoformat() if action_item.due_date else None,
            "priority": action_item.priority,
            "status": "pending",
            "created_by": current_user.id,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        await db.follow_up_tasks.insert_one(follow_up_task)
        follow_up_task_id = follow_up_task["id"]
        new_item["follow_up_task_id"] = follow_up_task_id
        
        # Notify reporting manager if requested
        if action_item.notify_reporting_manager and action_item.assigned_to_id:
            # Get employee record to find reporting manager
            employee = await db.employees.find_one({"user_id": action_item.assigned_to_id}, {"_id": 0})
            
            if employee and employee.get('reporting_manager_id'):
                manager = await db.users.find_one({"id": employee.get('reporting_manager_id')}, {"_id": 0})
                
                if manager:
                    notification = {
                        "id": str(uuid.uuid4()),
                        "type": "action_item_assigned",
                        "recipient_id": manager.get('id'),
                        "recipient_email": manager.get('email'),
                        "subject": f"Action Item Assigned to {new_item.get('assigned_to_name', 'Team Member')}",
                        "body": f"""
                        <h3>New Action Item Assignment</h3>
                        <p><strong>Assigned To:</strong> {new_item.get('assigned_to_name', 'N/A')}</p>
                        <p><strong>Task:</strong> {action_item.description}</p>
                        <p><strong>Priority:</strong> {action_item.priority.upper()}</p>
                        <p><strong>Due Date:</strong> {action_item.due_date.strftime('%Y-%m-%d') if action_item.due_date else 'Not set'}</p>
                        <p><strong>From Meeting:</strong> {meeting.get('title', 'Meeting')}</p>
                        <p><strong>Project:</strong> {project.get('name') if project else 'N/A'}</p>
                        <hr>
                        <p>This action item has been created as a follow-up from a meeting. Please ensure timely completion.</p>
                        """,
                        "meeting_id": meeting_id,
                        "action_item_id": new_item["id"],
                        "created_at": datetime.now(timezone.utc).isoformat(),
                        "sent": False
                    }
                    
                    await db.notifications.insert_one(notification)
    
    # Add action item to meeting
    action_items = meeting.get('action_items', []) or []
    action_items.append(new_item)
    
    await db.meetings.update_one(
        {"id": meeting_id},
        {"$set": {
            "action_items": action_items,
            "mom_generated": True,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    return {
        "message": "Action item added",
        "action_item": new_item,
        "follow_up_task_id": follow_up_task_id
    }


@router.patch("/{meeting_id}/action-items/{action_item_id}")
async def update_action_item_status(
    meeting_id: str,
    action_item_id: str,
    status: str,
    current_user: User = Depends(get_current_user)
):
    """Update action item status."""
    db = get_db()
    meeting = await db.meetings.find_one({"id": meeting_id}, {"_id": 0})
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    
    action_items = meeting.get('action_items', []) or []
    updated = False
    
    for item in action_items:
        if item.get('id') == action_item_id:
            item['status'] = status
            if status == 'completed':
                item['completed_at'] = datetime.now(timezone.utc).isoformat()
            updated = True
            
            # Update follow-up task if exists
            if item.get('follow_up_task_id'):
                await db.follow_up_tasks.update_one(
                    {"id": item['follow_up_task_id']},
                    {"$set": {"status": status, "updated_at": datetime.now(timezone.utc).isoformat()}}
                )
            break
    
    if not updated:
        raise HTTPException(status_code=404, detail="Action item not found")
    
    await db.meetings.update_one(
        {"id": meeting_id},
        {"$set": {"action_items": action_items, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    return {"message": "Action item status updated"}


@router.post("/{meeting_id}/send-mom")
async def send_mom_to_client(
    meeting_id: str,
    current_user: User = Depends(get_current_user)
):
    """Send MOM to client (email notification queued)."""
    db = get_db()
    meeting = await db.meetings.find_one({"id": meeting_id}, {"_id": 0})
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    
    # Get project and lead/client info
    project = None
    lead = None
    client = None
    
    if meeting.get('project_id'):
        project = await db.projects.find_one({"id": meeting['project_id']}, {"_id": 0})
    
    if meeting.get('lead_id'):
        lead = await db.leads.find_one({"id": meeting['lead_id']}, {"_id": 0})
    elif meeting.get('client_id'):
        client = await db.clients.find_one({"id": meeting['client_id']}, {"_id": 0})
    
    # Get client email
    client_email = None
    client_name = None
    
    if lead:
        client_email = lead.get('email')
        client_name = f"{lead.get('first_name', '')} {lead.get('last_name', '')}".strip()
    elif client:
        # Get primary contact email from client
        contacts = client.get('contacts', [])
        primary_contact = next((c for c in contacts if c.get('is_primary')), contacts[0] if contacts else None)
        if primary_contact:
            client_email = primary_contact.get('email')
            client_name = primary_contact.get('name')
    
    if not client_email:
        raise HTTPException(status_code=400, detail="No client email found")
    
    # Build MOM email content
    agenda_html = "".join([f"<li>{item}</li>" for item in meeting.get('agenda', [])])
    discussion_html = "".join([f"<li>{item}</li>" for item in meeting.get('discussion_points', [])])
    decisions_html = "".join([f"<li>{item}</li>" for item in meeting.get('decisions_made', [])])
    
    action_items_html = ""
    for item in meeting.get('action_items', []):
        action_items_html += f"""
        <tr>
            <td style="padding: 8px; border: 1px solid #ddd;">{item.get('description', '')}</td>
            <td style="padding: 8px; border: 1px solid #ddd;">{item.get('assigned_to_name', 'TBD')}</td>
            <td style="padding: 8px; border: 1px solid #ddd;">{item.get('due_date', 'TBD')}</td>
            <td style="padding: 8px; border: 1px solid #ddd;">{item.get('priority', 'Medium').upper()}</td>
        </tr>
        """
    
    meeting_date = meeting.get('meeting_date')
    if isinstance(meeting_date, str):
        meeting_date = datetime.fromisoformat(meeting_date)
    
    next_meeting = meeting.get('next_meeting_date')
    if next_meeting and isinstance(next_meeting, str):
        next_meeting = datetime.fromisoformat(next_meeting)
    
    # Create notification
    notification = {
        "id": str(uuid.uuid4()),
        "type": "mom_email",
        "recipient_email": client_email,
        "recipient_name": client_name,
        "subject": f"Minutes of Meeting - {meeting.get('title', 'Meeting')}",
        "body": f"MOM for meeting on {meeting_date.strftime('%B %d, %Y') if meeting_date else 'N/A'}",
        "meeting_id": meeting_id,
        "project_id": meeting.get('project_id'),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "sent": False
    }
    
    await db.notifications.insert_one(notification)
    
    # Mark meeting as MOM sent
    await db.meetings.update_one(
        {"id": meeting_id},
        {"$set": {
            "mom_sent_to_client": True,
            "mom_sent_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    return {"message": "MOM email queued for sending", "notification_id": notification["id"]}
