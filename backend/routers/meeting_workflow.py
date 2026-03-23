"""
Meeting Workflow Router - Handles meeting scheduling, notifications, and client responses
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional
from datetime import datetime, timezone, timedelta
from pydantic import BaseModel

from routers.auth import get_current_user
from routers.deps import get_db
from services.meeting_notification_service import (
    send_meeting_invite,
    send_manager_notification,
    send_response_confirmation,
    process_auto_accept_meetings
)

import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/meeting-workflow", tags=["Meeting Workflow"])


class ClientResponseRequest(BaseModel):
    """Request body for client response via form (reschedule notes)"""
    notes: Optional[str] = None
    preferred_times: Optional[list] = None


class SendInviteRequest(BaseModel):
    """Request to send meeting invite"""
    meeting_id: str
    client_email: Optional[str] = None  # Override client email if needed


class StateTransitionRequest(BaseModel):
    """Request to transition meeting state"""
    meeting_id: str
    new_state: str
    reason: Optional[str] = None


# Valid state transitions
VALID_TRANSITIONS = {
    "DRAFT": ["SCHEDULED"],
    "SCHEDULED": ["CONFIRMED", "REJECTED", "RESCHEDULED", "AUTO_ACCEPTED", "CANCELLED"],
    "CONFIRMED": ["CONDUCTED", "CANCELLED"],
    "AUTO_ACCEPTED": ["CONDUCTED", "CANCELLED"],
    "RESCHEDULED": ["SCHEDULED", "CANCELLED"],
    "CONDUCTED": ["MOM_RECORDED"],
    "MOM_RECORDED": ["DELIVERED"],
    "REJECTED": [],
    "DELIVERED": [],
    "CANCELLED": []
}


@router.post("/send-invite")
async def send_meeting_invitation(
    request: SendInviteRequest,
    current_user = Depends(get_current_user),
    db = Depends(get_db)
):
    """
    Send meeting invitation email to client with Accept/Reject/Reschedule links.
    Creates a single-use token valid for 24 hours.
    """
    
    # Get meeting
    meeting = await db.meetings.find_one({"id": request.meeting_id}, {"_id": 0})
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    
    # Get client info
    client_email = request.client_email
    client_name = meeting.get('client_name', 'Client')
    
    if not client_email:
        # Try to get from client record
        if meeting.get('client_id'):
            client = await db.clients.find_one({"id": meeting['client_id']}, {"_id": 0})
            if client:
                client_email = client.get('email') or client.get('primary_contact_email')
                client_name = client.get('contact_name') or client.get('company_name') or client_name
    
    if not client_email:
        raise HTTPException(status_code=400, detail="Client email not found. Please provide client_email.")
    
    # Get scheduler info
    scheduled_by_name = meeting.get('scheduled_by_name') or current_user.full_name
    
    # Send invite
    result = await send_meeting_invite(
        meeting=meeting,
        client_email=client_email,
        client_name=client_name,
        scheduled_by_name=scheduled_by_name,
        db=db
    )
    
    # Notify manager if available
    if meeting.get('attendees'):
        # Find reporting manager of scheduler
        scheduler = await db.users.find_one({"id": meeting.get('scheduled_by') or current_user.id}, {"_id": 0})
        if scheduler and scheduler.get('reporting_manager_id'):
            manager = await db.users.find_one({"id": scheduler['reporting_manager_id']}, {"_id": 0})
            if manager and manager.get('email'):
                await send_manager_notification(
                    meeting=meeting,
                    manager_email=manager['email'],
                    manager_name=manager.get('full_name', 'Manager'),
                    scheduled_by_name=scheduled_by_name,
                    notification_type='NEW_MEETING'
                )
    
    return {
        "status": "success",
        "message": f"Meeting invitation sent to {client_email}",
        "token_expires_at": result.get('expires_at'),
        "meeting_id": request.meeting_id
    }


@router.get("/client-response")
async def handle_client_response(
    token: str = Query(..., description="Single-use response token"),
    action: str = Query(..., description="Response action: accept, reject, reschedule"),
    db = Depends(get_db)
):
    """
    Public endpoint - Handle client response from email link.
    Returns meeting details and response status for the branded page.
    """
    
    # Validate action
    if action not in ['accept', 'reject', 'reschedule']:
        raise HTTPException(status_code=400, detail="Invalid action. Use: accept, reject, reschedule")
    
    # Find meeting by token
    meeting = await db.meetings.find_one(
        {"client_response_token": token},
        {"_id": 0}
    )
    
    if not meeting:
        raise HTTPException(status_code=404, detail="Invalid or expired link")
    
    # Check if token already used
    if meeting.get('client_token_used'):
        return {
            "status": "already_responded",
            "message": "You have already responded to this meeting invitation.",
            "previous_response": meeting.get('client_response'),
            "meeting": {
                "id": meeting['id'],
                "title": meeting.get('title'),
                "client_name": meeting.get('client_name'),
                "project_name": meeting.get('project_name'),
                "meeting_date": meeting.get('meeting_date')
            }
        }
    
    # Check if token expired
    expires_at = meeting.get('client_token_expires_at')
    if expires_at:
        if isinstance(expires_at, str):
            expires_at = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
        if datetime.now(timezone.utc) > expires_at:
            return {
                "status": "expired",
                "message": "This invitation link has expired. The meeting may have been auto-accepted.",
                "meeting": {
                    "id": meeting['id'],
                    "title": meeting.get('title'),
                    "meeting_date": meeting.get('meeting_date')
                }
            }
    
    # Return meeting details for branded page to display
    # Actual response processing happens via POST
    return {
        "status": "pending",
        "action": action,
        "meeting": {
            "id": meeting['id'],
            "title": meeting.get('title'),
            "client_name": meeting.get('client_name'),
            "project_name": meeting.get('project_name'),
            "meeting_date": meeting.get('meeting_date'),
            "duration_minutes": meeting.get('duration_minutes'),
            "mode": meeting.get('mode'),
            "agenda": meeting.get('agenda', []),
            "scheduled_by_name": meeting.get('scheduled_by_name')
        },
        "token_valid": True
    }


@router.post("/client-response")
async def submit_client_response(
    token: str = Query(..., description="Single-use response token"),
    action: str = Query(..., description="Response action: accept, reject, reschedule"),
    request: Optional[ClientResponseRequest] = None,
    db = Depends(get_db)
):
    """
    Public endpoint - Submit client's response to meeting invitation.
    Marks token as used and updates meeting status.
    """
    
    # Find meeting by token
    meeting = await db.meetings.find_one(
        {"client_response_token": token},
        {"_id": 0}
    )
    
    if not meeting:
        raise HTTPException(status_code=404, detail="Invalid or expired link")
    
    if meeting.get('client_token_used'):
        raise HTTPException(status_code=400, detail="This link has already been used")
    
    # Check token expiry
    expires_at = meeting.get('client_token_expires_at')
    if expires_at:
        if isinstance(expires_at, str):
            expires_at = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
        if datetime.now(timezone.utc) > expires_at:
            raise HTTPException(status_code=400, detail="This invitation link has expired")
    
    now = datetime.now(timezone.utc)
    
    # Map action to response type and new state
    action_map = {
        'accept': ('ACCEPTED', 'CONFIRMED'),
        'reject': ('REJECTED', 'REJECTED'),
        'reschedule': ('RESCHEDULED', 'RESCHEDULED')
    }
    
    response_type, new_state = action_map.get(action, ('ACCEPTED', 'CONFIRMED'))
    
    # Build state history entry
    state_entry = {
        "from_state": meeting.get('status', 'SCHEDULED'),
        "to_state": new_state,
        "changed_by": "CLIENT",
        "changed_at": now.isoformat(),
        "reason": f"Client {action}ed the meeting"
    }
    
    if request and request.notes:
        state_entry["notes"] = request.notes
    
    # Update meeting
    update_data = {
        "status": new_state,
        "client_response": response_type,
        "client_response_at": now.isoformat(),
        "client_token_used": True
    }
    
    if request:
        if request.notes:
            update_data["client_response_notes"] = request.notes
        if request.preferred_times:
            update_data["client_preferred_times"] = request.preferred_times
    
    await db.meetings.update_one(
        {"id": meeting['id']},
        {
            "$set": update_data,
            "$push": {"state_history": state_entry}
        }
    )
    
    # Send confirmation email to client
    client_email = None
    client_name = meeting.get('client_name', 'Client')
    
    if meeting.get('invite_sent_to'):
        client_email = meeting['invite_sent_to'][0]
    
    if client_email:
        await send_response_confirmation(
            meeting=meeting,
            client_email=client_email,
            client_name=client_name,
            response_type=response_type
        )
    
    # Notify manager
    scheduler = await db.users.find_one({"id": meeting.get('scheduled_by')}, {"_id": 0})
    if scheduler and scheduler.get('reporting_manager_id'):
        manager = await db.users.find_one({"id": scheduler['reporting_manager_id']}, {"_id": 0})
        if manager and manager.get('email'):
            notification_type = f"CLIENT_{response_type}"
            await send_manager_notification(
                meeting=meeting,
                manager_email=manager['email'],
                manager_name=manager.get('full_name', 'Manager'),
                scheduled_by_name=meeting.get('scheduled_by_name', 'Consultant'),
                notification_type=notification_type
            )
    
    # Notify scheduler
    if scheduler and scheduler.get('email'):
        await send_manager_notification(
            meeting=meeting,
            manager_email=scheduler['email'],
            manager_name=scheduler.get('full_name', 'Consultant'),
            scheduled_by_name=meeting.get('scheduled_by_name', 'you'),
            notification_type=f"CLIENT_{response_type}"
        )
    
    logger.info(f"Client responded {action} to meeting {meeting['id']}")
    
    return {
        "status": "success",
        "message": f"Your response has been recorded. Meeting status: {new_state}",
        "response_type": response_type,
        "new_state": new_state,
        "meeting_id": meeting['id']
    }


@router.post("/transition-state")
async def transition_meeting_state(
    request: StateTransitionRequest,
    current_user = Depends(get_current_user),
    db = Depends(get_db)
):
    """
    Transition meeting to a new state with validation and audit logging.
    """
    
    meeting = await db.meetings.find_one({"id": request.meeting_id}, {"_id": 0})
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    
    current_state = meeting.get('status', 'DRAFT')
    new_state = request.new_state.upper()
    
    # Validate transition
    valid_next_states = VALID_TRANSITIONS.get(current_state, [])
    if new_state not in valid_next_states:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid state transition from {current_state} to {new_state}. Valid transitions: {valid_next_states}"
        )
    
    now = datetime.now(timezone.utc)
    
    # Build update
    update_data = {
        "status": new_state
    }
    
    # Special handling for certain transitions
    if new_state == "CONDUCTED":
        update_data["conducted_at"] = now.isoformat()
    elif new_state == "MOM_RECORDED":
        update_data["mom_generated"] = True
    elif new_state == "DELIVERED":
        update_data["is_delivered"] = True
        update_data["delivered_at"] = now.isoformat()
        update_data["delivered_by"] = current_user.id
    
    state_entry = {
        "from_state": current_state,
        "to_state": new_state,
        "changed_by": current_user.id,
        "changed_by_name": current_user.full_name,
        "changed_at": now.isoformat(),
        "reason": request.reason or f"Transitioned by {current_user.full_name}"
    }
    
    await db.meetings.update_one(
        {"id": request.meeting_id},
        {
            "$set": update_data,
            "$push": {"state_history": state_entry}
        }
    )
    
    logger.info(f"Meeting {request.meeting_id} transitioned from {current_state} to {new_state} by {current_user.full_name}")
    
    return {
        "status": "success",
        "meeting_id": request.meeting_id,
        "previous_state": current_state,
        "new_state": new_state
    }


@router.post("/process-auto-accept")
async def trigger_auto_accept(
    current_user = Depends(get_current_user),
    db = Depends(get_db)
):
    """
    Admin endpoint - Manually trigger auto-accept processing for expired meeting invites.
    This is also run automatically by the scheduled background task every hour.
    """
    
    if current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Use the scheduler to run the auto-accept process
    from services.meeting_auto_accept_scheduler import get_meeting_auto_accept_scheduler
    
    scheduler = get_meeting_auto_accept_scheduler()
    if scheduler:
        results = await scheduler.run_now()
        return {
            "status": "success",
            "processed_count": len(results),
            "meetings": results,
            "scheduler_status": scheduler.get_status()
        }
    else:
        # Fallback to direct process if scheduler not running
        results = await process_auto_accept_meetings(db)
        return {
            "status": "success",
            "processed_count": len(results),
            "meetings": results,
            "scheduler_status": {"running": False, "note": "Scheduler not initialized"}
        }


@router.get("/auto-accept-scheduler/status")
async def get_auto_accept_scheduler_status(
    current_user = Depends(get_current_user)
):
    """
    Get the status of the meeting auto-accept scheduler.
    """
    
    if current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="Admin access required")
    
    from services.meeting_auto_accept_scheduler import get_meeting_auto_accept_scheduler
    
    scheduler = get_meeting_auto_accept_scheduler()
    if scheduler:
        return {
            "status": "success",
            "scheduler": scheduler.get_status()
        }
    else:
        return {
            "status": "warning",
            "scheduler": {"running": False, "note": "Scheduler not initialized"}
        }


@router.get("/meeting-states")
async def get_meeting_states():
    """
    Get all valid meeting states and their allowed transitions.
    Useful for frontend to show workflow options.
    """
    
    states = {
        "DRAFT": {"label": "Draft", "color": "#71717a", "next": VALID_TRANSITIONS["DRAFT"]},
        "SCHEDULED": {"label": "Scheduled", "color": "#3b82f6", "next": VALID_TRANSITIONS["SCHEDULED"]},
        "CONFIRMED": {"label": "Confirmed", "color": "#10b981", "next": VALID_TRANSITIONS["CONFIRMED"]},
        "REJECTED": {"label": "Rejected", "color": "#ef4444", "next": VALID_TRANSITIONS["REJECTED"]},
        "RESCHEDULED": {"label": "Reschedule Requested", "color": "#f59e0b", "next": VALID_TRANSITIONS["RESCHEDULED"]},
        "AUTO_ACCEPTED": {"label": "Auto-Accepted", "color": "#14b8a6", "next": VALID_TRANSITIONS["AUTO_ACCEPTED"]},
        "CONDUCTED": {"label": "Conducted", "color": "#8b5cf6", "next": VALID_TRANSITIONS["CONDUCTED"]},
        "MOM_RECORDED": {"label": "MOM Recorded", "color": "#6366f1", "next": VALID_TRANSITIONS["MOM_RECORDED"]},
        "DELIVERED": {"label": "Delivered", "color": "#22c55e", "next": VALID_TRANSITIONS["DELIVERED"]},
        "CANCELLED": {"label": "Cancelled", "color": "#6b7280", "next": VALID_TRANSITIONS["CANCELLED"]}
    }
    
    return states


@router.get("/test-email")
async def send_test_email(
    to_email: str = Query(..., description="Email address to send test to"),
    current_user = Depends(get_current_user)
):
    """
    Send a test email to verify SMTP configuration.
    """
    
    from services.email_service import send_email
    
    html_content = f"""
    <html>
    <body style="font-family: Arial, sans-serif; padding: 20px;">
        <h2 style="color: #059669;">D&V Business Consulting - Test Email</h2>
        <p>This is a test email to verify the email notification system is working correctly.</p>
        <p>Sent by: <strong>{current_user.full_name}</strong></p>
        <p>Time: <strong>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</strong></p>
        <hr style="border: 1px solid #e5e7eb; margin: 20px 0;">
        <p style="color: #6b7280; font-size: 12px;">
            This is an automated test email from the Meeting Notification System.
        </p>
    </body>
    </html>
    """
    
    result = await send_email(
        to_email=to_email,
        subject="[Test] D&V Meeting Notification System",
        html_content=html_content
    )
    
    return {
        "status": result.get("status"),
        "message": result.get("message", "Email sent successfully"),
        "sent_to": to_email
    }



# ========== BACKDATED MEETING APPROVAL WORKFLOW ==========

import os

class BackdatedApprovalRequest(BaseModel):
    """Request for backdated meeting approval"""
    meeting_id: str
    reason: str  # Why the meeting is being recorded late


class ApprovalDecisionRequest(BaseModel):
    """Manager's approval decision"""
    meeting_id: str
    approved: bool
    notes: Optional[str] = None


@router.post("/request-backdated-approval")
async def request_backdated_approval(
    request: BackdatedApprovalRequest,
    current_user = Depends(get_current_user),
    db = Depends(get_db)
):
    """
    Request approval for recording a backdated meeting (>24h ago).
    Sends notification to direct reporting manager.
    """
    
    # Get meeting
    meeting = await db.meetings.find_one({"id": request.meeting_id}, {"_id": 0})
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    
    # Check if already has approval request
    if meeting.get('backdated_approval_status') == 'PENDING':
        raise HTTPException(status_code=400, detail="Approval request already pending")
    
    if meeting.get('backdated_approval_status') == 'APPROVED':
        raise HTTPException(status_code=400, detail="Meeting already approved")
    
    # Get requester's manager
    requester = await db.users.find_one({"id": current_user.id}, {"_id": 0})
    if not requester:
        raise HTTPException(status_code=404, detail="User not found")
    
    manager_id = requester.get('reporting_manager_id')
    if not manager_id:
        raise HTTPException(status_code=400, detail="No reporting manager configured. Please contact admin.")
    
    manager = await db.users.find_one({"id": manager_id}, {"_id": 0})
    if not manager:
        raise HTTPException(status_code=404, detail="Reporting manager not found")
    
    now = datetime.now(timezone.utc)
    
    # Update meeting with approval request
    await db.meetings.update_one(
        {"id": request.meeting_id},
        {
            "$set": {
                "is_backdated": True,
                "backdated_approval_status": "PENDING",
                "backdated_reason": request.reason,
                "backdated_requested_by": current_user.id,
                "backdated_requested_at": now.isoformat(),
                "backdated_manager_id": manager_id
            },
            "$push": {
                "state_history": {
                    "from_state": meeting.get('status', 'DRAFT'),
                    "to_state": "PENDING_APPROVAL",
                    "changed_by": current_user.id,
                    "changed_by_name": current_user.full_name,
                    "changed_at": now.isoformat(),
                    "reason": f"Backdated approval requested: {request.reason}"
                }
            }
        }
    )
    
    # Send email notification to manager
    if manager.get('email'):
        from services.email_service import send_email
        
        meeting_date = meeting.get('meeting_date', '')
        if isinstance(meeting_date, str):
            try:
                meeting_date = datetime.fromisoformat(meeting_date.replace('Z', '+00:00')).strftime('%B %d, %Y')
            except:
                pass
        
        frontend_url = os.environ.get('REACT_APP_BACKEND_URL', 'https://exit-org-preview.preview.emergentagent.com')
        
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; padding: 20px;">
            <h2 style="color: #f59e0b;">Backdated Meeting Approval Required</h2>
            <p>Dear <strong>{manager.get('full_name', 'Manager')}</strong>,</p>
            <p><strong>{current_user.full_name}</strong> has requested approval to record a backdated meeting.</p>
            
            <div style="background: #fffbeb; border: 1px solid #fcd34d; padding: 15px; border-radius: 8px; margin: 20px 0;">
                <p style="margin: 5px 0;"><strong>Meeting:</strong> {meeting.get('title', 'Consulting Meeting')}</p>
                <p style="margin: 5px 0;"><strong>Client:</strong> {meeting.get('client_name', 'N/A')}</p>
                <p style="margin: 5px 0;"><strong>Project:</strong> {meeting.get('project_name', 'N/A')}</p>
                <p style="margin: 5px 0;"><strong>Meeting Date:</strong> {meeting_date}</p>
                <p style="margin: 5px 0;"><strong>Reason for late recording:</strong> {request.reason}</p>
            </div>
            
            <p>Please review and approve/reject this request in the <a href="{frontend_url}/approvals" style="color: #059669;">Approvals Center</a>.</p>
            
            <hr style="border: 1px solid #e5e7eb; margin: 20px 0;">
            <p style="color: #6b7280; font-size: 12px;">
                This is an automated notification from the Meeting Management System.
            </p>
        </body>
        </html>
        """
        
        await send_email(
            to_email=manager['email'],
            subject=f"[Approval Required] Backdated Meeting - {meeting.get('title', 'Meeting')}",
            html_content=html_content
        )
        
        logger.info(f"Backdated approval notification sent to {manager['email']}")
    
    return {
        "status": "success",
        "message": f"Approval request sent to {manager.get('full_name', 'your manager')}",
        "meeting_id": request.meeting_id,
        "manager_name": manager.get('full_name'),
        "approval_status": "PENDING"
    }


@router.post("/approve-backdated")
async def approve_backdated_meeting(
    request: ApprovalDecisionRequest,
    current_user = Depends(get_current_user),
    db = Depends(get_db)
):
    """
    Manager approves or rejects a backdated meeting request.
    """
    
    # Get meeting
    meeting = await db.meetings.find_one({"id": request.meeting_id}, {"_id": 0})
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    
    # Verify current user is the assigned manager
    if meeting.get('backdated_manager_id') != current_user.id:
        # Also allow admin
        if current_user.role != 'admin':
            raise HTTPException(status_code=403, detail="Only the assigned manager or admin can approve this request")
    
    if meeting.get('backdated_approval_status') != 'PENDING':
        raise HTTPException(status_code=400, detail=f"Meeting is not pending approval. Current status: {meeting.get('backdated_approval_status')}")
    
    now = datetime.now(timezone.utc)
    new_status = "APPROVED" if request.approved else "REJECTED"
    
    # Update meeting
    update_data = {
        "backdated_approval_status": new_status,
        "backdated_approved_by": current_user.id,
        "backdated_approved_by_name": current_user.full_name,
        "backdated_approved_at": now.isoformat(),
        "backdated_approval_notes": request.notes
    }
    
    # If approved, allow MOM recording (set status to CONDUCTED)
    if request.approved:
        update_data["status"] = "CONDUCTED"
    
    state_entry = {
        "from_state": "PENDING_APPROVAL",
        "to_state": new_status,
        "changed_by": current_user.id,
        "changed_by_name": current_user.full_name,
        "changed_at": now.isoformat(),
        "reason": f"Backdated meeting {new_status.lower()} by manager" + (f": {request.notes}" if request.notes else "")
    }
    
    await db.meetings.update_one(
        {"id": request.meeting_id},
        {
            "$set": update_data,
            "$push": {"state_history": state_entry}
        }
    )
    
    # Notify the requester
    requester_id = meeting.get('backdated_requested_by')
    if requester_id:
        requester = await db.users.find_one({"id": requester_id}, {"_id": 0})
        if requester and requester.get('email'):
            from services.email_service import send_email
            
            status_color = "#10b981" if request.approved else "#ef4444"
            status_text = "Approved" if request.approved else "Rejected"
            
            html_content = f"""
            <html>
            <body style="font-family: Arial, sans-serif; padding: 20px;">
                <h2 style="color: {status_color};">Backdated Meeting {status_text}</h2>
                <p>Dear <strong>{requester.get('full_name', 'Consultant')}</strong>,</p>
                <p>Your request to record a backdated meeting has been <strong style="color: {status_color};">{status_text.lower()}</strong> by {current_user.full_name}.</p>
                
                <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; margin: 20px 0;">
                    <p style="margin: 5px 0;"><strong>Meeting:</strong> {meeting.get('title', 'Consulting Meeting')}</p>
                    <p style="margin: 5px 0;"><strong>Client:</strong> {meeting.get('client_name', 'N/A')}</p>
                    {f'<p style="margin: 5px 0;"><strong>Manager Notes:</strong> {request.notes}</p>' if request.notes else ''}
                </div>
                
                {"<p>You can now proceed to record the MOM for this meeting.</p>" if request.approved else "<p>Please contact your manager for more details.</p>"}
            </body>
            </html>
            """
            
            await send_email(
                to_email=requester['email'],
                subject=f"[{status_text}] Backdated Meeting - {meeting.get('title', 'Meeting')}",
                html_content=html_content
            )
    
    logger.info(f"Backdated meeting {request.meeting_id} {new_status.lower()} by {current_user.full_name}")
    
    return {
        "status": "success",
        "message": f"Meeting {new_status.lower()}",
        "meeting_id": request.meeting_id,
        "approval_status": new_status
    }


@router.get("/pending-approvals")
async def get_pending_approvals(
    current_user = Depends(get_current_user),
    db = Depends(get_db)
):
    """
    Get list of meetings pending approval for the current manager.
    Returns meetings where current user is the assigned approver.
    """
    
    # Find meetings pending this manager's approval
    pending = await db.meetings.find(
        {
            "backdated_approval_status": "PENDING",
            "backdated_manager_id": current_user.id
        },
        {"_id": 0}
    ).to_list(100)
    
    # Also include for admin - all pending approvals
    if current_user.role == 'admin':
        all_pending = await db.meetings.find(
            {"backdated_approval_status": "PENDING"},
            {"_id": 0}
        ).to_list(100)
        
        # Merge without duplicates
        pending_ids = {m['id'] for m in pending}
        for m in all_pending:
            if m['id'] not in pending_ids:
                pending.append(m)
    
    # Enrich with requester info
    for meeting in pending:
        requester_id = meeting.get('backdated_requested_by')
        if requester_id:
            requester = await db.users.find_one({"id": requester_id}, {"_id": 0, "full_name": 1, "email": 1})
            if requester:
                meeting['requester_name'] = requester.get('full_name')
                meeting['requester_email'] = requester.get('email')
    
    return {
        "pending_count": len(pending),
        "meetings": pending
    }
