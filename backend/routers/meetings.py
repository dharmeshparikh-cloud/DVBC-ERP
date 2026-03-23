"""
Meetings Router - Meeting Management, MOM, Action Items
Includes file attachments for offline meetings (photos/voice)
Sends email notifications when MOM is filled
"""

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, BackgroundTasks
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
import uuid
import base64
import os

from .models import Meeting, MeetingCreate, MOMCreate, ActionItemCreate, User
from .models import SALES_MEETING_ROLES, CONSULTING_MEETING_ROLES
from .deps import get_db
from .deps import get_current_user
from services.email_service import send_email
from services.funnel_notifications import meeting_mom_filled_email, get_sales_manager_emails
from .audit_logging import log_audit

router = APIRouter(prefix="/meetings", tags=["Meetings"])

# File storage path for meeting attachments
UPLOAD_DIR = "/app/uploads/meetings"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Allowed file types for offline meeting attachments
ALLOWED_IMAGE_TYPES = ["image/jpeg", "image/png", "image/webp", "image/heic"]
ALLOWED_AUDIO_TYPES = ["audio/mpeg", "audio/wav", "audio/webm", "audio/ogg", "audio/mp4", "audio/x-m4a"]
ALLOWED_DOCUMENT_TYPES = ["application/pdf", "application/msword", 
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "text/plain", "text/csv"]
ALLOWED_TYPES = ALLOWED_IMAGE_TYPES + ALLOWED_AUDIO_TYPES
ALLOWED_MOM_TYPES = ALLOWED_IMAGE_TYPES + ALLOWED_DOCUMENT_TYPES
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB

# MOM documents upload directory
MOM_UPLOAD_DIR = "/app/uploads/mom_documents"
os.makedirs(MOM_UPLOAD_DIR, exist_ok=True)

# App URL for email links
APP_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://attendance-engine-3.preview.emergentagent.com").replace("/api", "")


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
    
    # Set organizer fields
    meeting.organizer_id = current_user.id
    meeting.organizer_name = current_user.full_name
    meeting.created_by_name = current_user.full_name

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
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    """
    Record a sales funnel meeting with MOM (Minutes of Meeting).
    MOM is required before meeting can be submitted.
    Used by the Sales Funnel flow.
    Sends email notification to managers when MOM is recorded.
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
        # Travel details for offline meetings
        "travel_details": data.get("travel_details"),
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
    
    # Send email notification in background - to Managers, Client, and Reporting Manager
    async def send_mom_notification():
        try:
            # Get previous meetings for context
            previous_meetings = await db.meetings.find(
                {"lead_id": lead_id, "id": {"$ne": meeting_id}},
                {"_id": 0, "meeting_date": 1, "mom": 1, "notes": 1, "title": 1}
            ).sort("meeting_date", -1).to_list(5)
            
            # Get manager emails
            manager_emails = await get_sales_manager_emails(db)
            
            # Get client email from lead
            client_email = lead.get("email") or lead.get("contact_email")
            
            # Get reporting manager email
            reporting_manager_email = None
            if current_user.id:
                user_record = await db.users.find_one({"id": current_user.id}, {"_id": 0, "reporting_manager_id": 1})
                if user_record and user_record.get("reporting_manager_id"):
                    manager = await db.users.find_one({"id": user_record["reporting_manager_id"]}, {"_id": 0, "email": 1})
                    if manager:
                        reporting_manager_email = manager.get("email")
            
            # Prepare email data with enhanced template
            email_data = meeting_mom_filled_email(
                lead_name=f"{lead.get('first_name', '')} {lead.get('last_name', '')}".strip(),
                company=lead.get("company", "Unknown"),
                meeting_title=meeting_doc.get("title", "Sales Meeting"),
                meeting_date=meeting_date,
                meeting_time=meeting_time,
                meeting_type=meeting_type,
                attendees=data.get("attendees", []),
                mom_summary=mom[:500] if len(mom) > 500 else mom,
                client_expectations=data.get("client_expectations", [])[:5],
                key_commitments=data.get("key_commitments", [])[:5],
                salesperson_name=current_user.full_name,
                app_url=APP_URL,
                previous_meetings=previous_meetings
            )
            
            # Send to managers
            all_recipients = set(manager_emails or [])
            if reporting_manager_email:
                all_recipients.add(reporting_manager_email)
            
            for email in all_recipients:
                if email:
                    await send_email(
                        to_email=email,
                        subject=email_data["subject"],
                        html_content=email_data["html"],
                        plain_content=email_data["plain"]
                    )
            
            # Send client copy (without internal action button)
            if client_email:
                client_email_data = meeting_mom_filled_email(
                    lead_name=f"{lead.get('first_name', '')} {lead.get('last_name', '')}".strip(),
                    company=lead.get("company", "Unknown"),
                    meeting_title=meeting_doc.get("title", "Sales Meeting"),
                    meeting_date=meeting_date,
                    meeting_time=meeting_time,
                    meeting_type=meeting_type,
                    attendees=data.get("attendees", []),
                    mom_summary=mom[:500] if len(mom) > 500 else mom,
                    client_expectations=data.get("client_expectations", [])[:5],
                    key_commitments=data.get("key_commitments", [])[:5],
                    salesperson_name=current_user.full_name,
                    app_url=APP_URL,
                    previous_meetings=previous_meetings,
                    is_client_copy=True
                )
                await send_email(
                    to_email=client_email,
                    subject=client_email_data["subject"],
                    html_content=client_email_data["html"],
                    plain_content=client_email_data["plain"]
                )
                
                # Mark MOM as sent to client
                await db.meetings.update_one(
                    {"id": meeting_id},
                    {"$set": {"mom_sent_to_client": True, "mom_sent_at": datetime.now(timezone.utc).isoformat()}}
                )
                
        except Exception as e:
            print(f"Failed to send MOM notification: {e}")
    
    background_tasks.add_task(send_mom_notification)
    
    # Create expense record for offline meetings with travel details
    async def create_meeting_expense():
        try:
            travel_details = data.get("travel_details")
            if not travel_details:
                return
            
            # Only create expense for Car, Bike, or Transit (not Accompanied)
            travel_mode = travel_details.get("travel_mode", "")
            if travel_mode == "ACCOMPANIED":
                return
            
            # DUPLICATE PREVENTION: Check if expense already exists for this meeting
            existing_expense = await db.expenses.find_one({
                "meeting_id": meeting_id,
                "status": {"$ne": "rejected"}  # Allow if previous was rejected
            })
            if existing_expense:
                print(f"Expense already exists for meeting {meeting_id}: {existing_expense.get('id')}")
                return
            
            # Calculate expense amount - account for round trip
            expense_amount = 0
            distance_km = travel_details.get("distance_km", 0)
            is_round_trip = travel_details.get("is_round_trip", False)
            
            # Double distance for round trips
            total_km = distance_km * 2 if is_round_trip else distance_km
            
            if travel_mode == "DRIVING":
                expense_amount = total_km * 7  # Rs.7/km
            elif travel_mode == "TWO_WHEELER":
                expense_amount = total_km * 3  # Rs.3/km
            elif travel_mode == "TRANSIT":
                expense_amount = travel_details.get("transit_amount", 0)
            
            if expense_amount <= 0:
                return
            
            # Create expense record linked to lead and meeting
            expense_id = str(uuid.uuid4())
            expense_doc = {
                "id": expense_id,
                "employee_id": current_user.employee_id,  # Employee code for payroll
                "user_id": current_user.id,  # UUID for ownership queries
                "created_by": current_user.id,  # UUID for auth/ownership
                "employee_name": current_user.full_name,
                "category": "travel",
                "subcategory": f"meeting_travel_{travel_mode.lower()}",
                "description": f"Meeting Travel Expense - {lead.get('company', 'Client')} ({travel_mode})",
                "amount": round(expense_amount, 2),
                "total_amount": round(expense_amount, 2),  # For consistency with expense approval
                "currency": "INR",
                "expense_date": meeting_datetime.isoformat(),
                "status": "pending",  # Goes to approval workflow
                "receipt_url": None,
                "receipt_uploaded": travel_mode == "TRANSIT" and travel_details.get("transit_proof"),
                # Link to meeting and lead
                "meeting_id": meeting_id,
                "lead_id": lead_id,
                "lead_name": f"{lead.get('first_name', '')} {lead.get('last_name', '')}".strip(),
                "company": lead.get("company", ""),
                # Travel details for verification
                "travel_details": {
                    "start_location": travel_details.get("start_location"),
                    "end_location": travel_details.get("end_location"),
                    "via_locations": travel_details.get("via_locations", []),
                    "distance_km": distance_km,
                    "total_km": total_km,  # Includes round trip if applicable
                    "is_round_trip": is_round_trip,
                    "travel_mode": travel_mode,
                    "rate_per_km": 7 if travel_mode == "DRIVING" else (3 if travel_mode == "TWO_WHEELER" else 0),
                    "travel_start_time": travel_details.get("travel_start_time"),
                    "travel_end_time": travel_details.get("travel_end_time")
                },
                "expense_type": "meeting_expense",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            
            await db.expenses.insert_one(expense_doc)
            
            # Update meeting with expense reference
            await db.meetings.update_one(
                {"id": meeting_id},
                {"$set": {"expense_id": expense_id, "expense_amount": round(expense_amount, 2)}}
            )
            
            print(f"Created meeting expense: {expense_id} for Rs.{expense_amount}")
            
        except Exception as e:
            print(f"Failed to create meeting expense: {e}")
    
    background_tasks.add_task(create_meeting_expense)
    
    return {
        "message": "Meeting recorded successfully with MOM",
        "meeting_id": meeting_id,
        "meeting": meeting_doc
    }


@router.post("/{meeting_id}/attachments")
async def upload_meeting_attachment(
    meeting_id: str,
    file: UploadFile = File(...),
    attachment_type: str = Form(default="photo"),  # photo or voice
    current_user: User = Depends(get_current_user)
):
    """
    Upload photo or voice attachment for offline meetings.
    Mandatory for first offline meeting. Stored and inherited downstream.
    """
    db = get_db()
    
    # Verify meeting exists
    meeting = await db.meetings.find_one({"id": meeting_id}, {"_id": 0})
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    
    # Validate file type
    content_type = file.content_type
    if content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid file type. Allowed: images (jpeg, png, webp) and audio (mp3, wav, webm, ogg)"
        )
    
    # Read file content
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large. Maximum 20MB allowed")
    
    # Generate unique filename
    file_ext = file.filename.split('.')[-1] if '.' in file.filename else 'bin'
    file_id = str(uuid.uuid4())
    filename = f"{meeting_id}_{file_id}.{file_ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)
    
    # Save file
    with open(filepath, 'wb') as f:
        f.write(content)
    
    # Create attachment record
    attachment = {
        "id": file_id,
        "meeting_id": meeting_id,
        "lead_id": meeting.get("lead_id"),
        "filename": file.filename,
        "stored_filename": filename,
        "filepath": filepath,
        "content_type": content_type,
        "attachment_type": attachment_type,  # photo or voice
        "size_bytes": len(content),
        "uploaded_by": current_user.id,
        "uploaded_by_name": current_user.full_name,
        "uploaded_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.meeting_attachments.insert_one(attachment)
    
    # Update meeting with attachment reference
    attachments = meeting.get("attachments", []) or []
    attachments.append({
        "id": file_id,
        "filename": file.filename,
        "type": attachment_type,
        "content_type": content_type
    })
    
    await db.meetings.update_one(
        {"id": meeting_id},
        {"$set": {"attachments": attachments, "has_attachments": True}}
    )
    
    return {
        "message": "Attachment uploaded successfully",
        "attachment_id": file_id,
        "filename": file.filename,
        "type": attachment_type
    }


@router.get("/{meeting_id}/attachments")
async def get_meeting_attachments(
    meeting_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get all attachments for a meeting."""
    db = get_db()
    
    meeting = await db.meetings.find_one({"id": meeting_id}, {"_id": 0})
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    
    attachments = await db.meeting_attachments.find(
        {"meeting_id": meeting_id},
        {"_id": 0, "filepath": 0}  # Exclude internal path
    ).to_list(50)
    
    return attachments


@router.get("/{meeting_id}/attachments/{attachment_id}/download")
async def download_meeting_attachment(
    meeting_id: str,
    attachment_id: str,
    current_user: User = Depends(get_current_user)
):
    """Download a specific attachment (returns base64 encoded content)."""
    db = get_db()
    
    attachment = await db.meeting_attachments.find_one(
        {"id": attachment_id, "meeting_id": meeting_id},
        {"_id": 0}
    )
    
    if not attachment:
        raise HTTPException(status_code=404, detail="Attachment not found")
    
    filepath = attachment.get("filepath")
    if not filepath or not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="File not found on server")
    
    with open(filepath, 'rb') as f:
        content = f.read()
    
    return {
        "filename": attachment.get("filename"),
        "content_type": attachment.get("content_type"),
        "attachment_type": attachment.get("attachment_type"),
        "content_base64": base64.b64encode(content).decode('utf-8')
    }


@router.delete("/{meeting_id}/attachments/{attachment_id}")
async def delete_meeting_attachment(
    meeting_id: str,
    attachment_id: str,
    current_user: User = Depends(get_current_user)
):
    """Delete a meeting attachment."""
    db = get_db()
    
    attachment = await db.meeting_attachments.find_one(
        {"id": attachment_id, "meeting_id": meeting_id},
        {"_id": 0}
    )
    
    if not attachment:
        raise HTTPException(status_code=404, detail="Attachment not found")
    
    # Delete file from disk
    filepath = attachment.get("filepath")
    if filepath and os.path.exists(filepath):
        os.remove(filepath)
    
    # Delete from database
    await db.meeting_attachments.delete_one({"id": attachment_id})
    
    # Update meeting's attachment list
    meeting = await db.meetings.find_one({"id": meeting_id}, {"_id": 0})
    if meeting:
        attachments = [a for a in (meeting.get("attachments") or []) if a.get("id") != attachment_id]
        await db.meetings.update_one(
            {"id": meeting_id},
            {"$set": {
                "attachments": attachments,
                "has_attachments": len(attachments) > 0
            }}
        )
    
    return {"message": "Attachment deleted successfully"}


@router.post("/upload/documents")
async def upload_mom_documents(
    files: List[UploadFile] = File(...),
    current_user: User = Depends(get_current_user)
):
    """
    Upload documents for MOM attachments.
    Supports PDFs, Word docs, Excel, images, and plain text files.
    Returns list of uploaded file info for frontend to store with MOM.
    """
    uploaded_files = []
    
    for file in files:
        # Validate file type
        content_type = file.content_type
        if content_type not in ALLOWED_MOM_TYPES:
            continue  # Skip invalid files
        
        # Read file content
        content = await file.read()
        if len(content) > MAX_FILE_SIZE:
            continue  # Skip files that are too large
        
        # Generate unique filename
        file_ext = file.filename.split('.')[-1] if '.' in file.filename else 'bin'
        file_id = str(uuid.uuid4())
        filename = f"mom_{file_id}.{file_ext}"
        filepath = os.path.join(MOM_UPLOAD_DIR, filename)
        
        # Save file
        with open(filepath, 'wb') as f:
            f.write(content)
        
        # Create file info
        uploaded_files.append({
            "id": file_id,
            "filename": file.filename,
            "stored_filename": filename,
            "path": f"/uploads/mom_documents/{filename}",
            "url": f"/api/meetings/documents/{file_id}/download",
            "content_type": content_type,
            "size": len(content),
            "uploaded_by": current_user.id,
            "uploaded_at": datetime.now(timezone.utc).isoformat()
        })
    
    return {"files": uploaded_files, "count": len(uploaded_files)}


@router.get("/documents/{file_id}/download")
async def download_mom_document(
    file_id: str,
    current_user: User = Depends(get_current_user)
):
    """Download an uploaded MOM document."""
    from fastapi.responses import FileResponse
    
    # Find the file in upload directory
    for filename in os.listdir(MOM_UPLOAD_DIR):
        if file_id in filename:
            filepath = os.path.join(MOM_UPLOAD_DIR, filename)
            if os.path.exists(filepath):
                return FileResponse(
                    filepath,
                    filename=filename,
                    media_type="application/octet-stream"
                )
    
    raise HTTPException(status_code=404, detail="Document not found")


@router.get("/lead/{lead_id}/attachments")
async def get_all_lead_meeting_attachments(
    lead_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get all meeting attachments for a lead.
    Used for inheriting attachments downstream in the funnel.
    """
    db = get_db()
    
    attachments = await db.meeting_attachments.find(
        {"lead_id": lead_id},
        {"_id": 0, "filepath": 0}
    ).sort("uploaded_at", -1).to_list(100)
    
    return attachments


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
    background_tasks: BackgroundTasks,
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
    
    # Extract travel details for expense creation (don't store in meeting doc)
    travel_details = update_data.pop('travel_details', None)
    
    await db.meetings.update_one({"id": meeting_id}, {"$set": update_data})
    
    # Create expense record for offline meetings with travel details
    if travel_details and meeting.get('mode') == 'offline':
        async def create_meeting_expense():
            try:
                # Only create expense for Car, Bike, or Transit (not Accompanied)
                travel_mode = travel_details.get("travel_mode", "")
                if travel_mode == "ACCOMPANIED":
                    return
                
                # DUPLICATE PREVENTION: Check if expense already exists for this meeting
                existing_expense = await db.expenses.find_one({
                    "meeting_id": meeting_id,
                    "status": {"$ne": "rejected"}  # Allow if previous was rejected
                })
                if existing_expense:
                    print(f"Expense already exists for meeting {meeting_id}: {existing_expense.get('id')}")
                    return
                
                # Calculate expense amount - account for round trip
                expense_amount = 0
                distance_km = travel_details.get("distance_km", 0)
                is_round_trip = travel_details.get("is_round_trip", False)
                
                # Double distance for round trips
                total_km = distance_km * 2 if is_round_trip else distance_km
                
                if travel_mode == "DRIVING":
                    expense_amount = total_km * 7  # Rs.7/km
                elif travel_mode == "TWO_WHEELER":
                    expense_amount = total_km * 3  # Rs.3/km
                elif travel_mode == "TRANSIT":
                    expense_amount = travel_details.get("transit_amount", 0)
                
                # Use expense_amount from frontend if provided
                if travel_details.get("expense_amount") and travel_details.get("expense_amount") > 0:
                    expense_amount = travel_details.get("expense_amount")
                
                if expense_amount <= 0:
                    return
                
                # Get client/project info
                client = None
                project = None
                if meeting.get('client_id'):
                    client = await db.clients.find_one({"id": meeting.get('client_id')}, {"_id": 0})
                if meeting.get('project_id'):
                    project = await db.projects.find_one({"id": meeting.get('project_id')}, {"_id": 0})
                
                # Create expense record
                expense_id = str(uuid.uuid4())
                expense_doc = {
                    "id": expense_id,
                    "employee_id": current_user.employee_id,  # Employee code for payroll
                    "user_id": current_user.id,  # UUID for ownership queries
                    "created_by": current_user.id,  # UUID for auth/ownership
                    "employee_name": current_user.full_name,
                    "category": "travel",
                    "subcategory": f"meeting_travel_{travel_mode.lower()}",
                    "description": f"Meeting Travel Expense - {client.get('company_name') if client else meeting.get('client_name', 'Client')} ({travel_mode})",
                    "amount": round(expense_amount, 2),
                    "total_amount": round(expense_amount, 2),
                    "currency": "INR",
                    "expense_date": meeting.get('meeting_date', datetime.now(timezone.utc).isoformat()),
                    "status": "pending",  # Goes to approval workflow
                    "receipt_url": None,
                    "receipt_uploaded": travel_mode == "TRANSIT" and travel_details.get("transit_proof"),
                    # Link to meeting and project
                    "meeting_id": meeting_id,
                    "project_id": meeting.get('project_id'),
                    "project_name": project.get('name') if project else meeting.get('project_name'),
                    "client_id": meeting.get('client_id'),
                    "client_name": client.get('company_name') if client else meeting.get('client_name', ''),
                    # Travel details for verification
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
                    "expense_type": "meeting_expense",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
                
                await db.expenses.insert_one(expense_doc)
                
                # Update meeting with expense reference
                await db.meetings.update_one(
                    {"id": meeting_id},
                    {"$set": {"expense_id": expense_id, "expense_amount": round(expense_amount, 2), "travel_details": travel_details}}
                )
                
                print(f"Created meeting expense: {expense_id} for Rs.{expense_amount}")
                
            except Exception as e:
                print(f"Failed to create meeting expense: {e}")
        
        background_tasks.add_task(create_meeting_expense)
    
    # Audit log for MOM update
    await log_audit(
        action="meeting.mom_updated",
        entity_type="meeting",
        entity_id=meeting_id,
        performed_by=current_user.id,
        changes={
            "mom_generated": {"from": meeting.get("mom_generated"), "to": True},
            "has_travel_details": {"value": travel_details is not None}
        },
        metadata={
            "meeting_title": meeting.get("title"),
            "project_id": meeting.get("project_id"),
            "mode": meeting.get("mode")
        }
    )
    
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
