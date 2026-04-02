"""
Meeting Notification Service - Send meeting invites with Accept/Reject/Reschedule links
"""

import secrets
import os
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
import logging

from services.email_service import send_email

logger = logging.getLogger(__name__)

# Get base URL for links
FRONTEND_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://role-security-2.preview.emergentagent.com')


def generate_response_token() -> str:
    """Generate a secure single-use token for client response"""
    return secrets.token_urlsafe(32)


def get_meeting_invite_html(
    meeting: Dict[str, Any],
    client_name: str,
    response_url: str,
    scheduled_by_name: str
) -> str:
    """Generate branded HTML email for meeting invite"""
    
    meeting_date = meeting.get('meeting_date')
    if isinstance(meeting_date, str):
        meeting_date = datetime.fromisoformat(meeting_date.replace('Z', '+00:00'))
    
    formatted_date = meeting_date.strftime('%A, %B %d, %Y')
    formatted_time = meeting_date.strftime('%I:%M %p')
    
    mode_display = {
        'online': 'Video Conference',
        'offline': 'In-Person Meeting',
        'tele_call': 'Phone Call'
    }.get(meeting.get('mode', 'online'), 'Meeting')
    
    agenda_html = ""
    if meeting.get('agenda'):
        agenda_items = "".join([f"<li style='margin-bottom: 8px;'>{item}</li>" for item in meeting['agenda'] if item])
        if agenda_items:
            agenda_html = f"""
            <div style="margin-top: 20px; padding: 15px; background-color: #f8f9fa; border-radius: 8px;">
                <h3 style="margin: 0 0 10px 0; color: #1a1a1a; font-size: 14px;">Agenda:</h3>
                <ul style="margin: 0; padding-left: 20px; color: #4a5568;">
                    {agenda_items}
                </ul>
            </div>
            """
    
    return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
    
    <!-- Header -->
    <div style="background: linear-gradient(135deg, #059669 0%, #047857 100%); padding: 30px; border-radius: 12px 12px 0 0; text-align: center;">
        <h1 style="color: white; margin: 0; font-size: 24px; font-weight: 600;">D&V Business Consulting</h1>
        <p style="color: rgba(255,255,255,0.9); margin: 8px 0 0 0; font-size: 14px;">Meeting Invitation</p>
    </div>
    
    <!-- Content -->
    <div style="background: white; padding: 30px; border: 1px solid #e5e7eb; border-top: none;">
        
        <p style="font-size: 16px; color: #1a1a1a;">Dear <strong>{client_name}</strong>,</p>
        
        <p style="color: #4a5568;">You have been invited to a meeting by <strong>{scheduled_by_name}</strong> from D&V Business Consulting.</p>
        
        <!-- Meeting Details Card -->
        <div style="background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 8px; padding: 20px; margin: 20px 0;">
            <h2 style="margin: 0 0 15px 0; color: #166534; font-size: 18px;">{meeting.get('title', 'Consulting Meeting')}</h2>
            
            <table style="width: 100%; border-collapse: collapse;">
                <tr>
                    <td style="padding: 8px 0; color: #6b7280; width: 100px;">
                        <strong>Date:</strong>
                    </td>
                    <td style="padding: 8px 0; color: #1a1a1a;">
                        {formatted_date}
                    </td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: #6b7280;">
                        <strong>Time:</strong>
                    </td>
                    <td style="padding: 8px 0; color: #1a1a1a;">
                        {formatted_time}
                    </td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: #6b7280;">
                        <strong>Duration:</strong>
                    </td>
                    <td style="padding: 8px 0; color: #1a1a1a;">
                        {meeting.get('duration_minutes', 60)} minutes
                    </td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: #6b7280;">
                        <strong>Mode:</strong>
                    </td>
                    <td style="padding: 8px 0; color: #1a1a1a;">
                        {mode_display}
                    </td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: #6b7280;">
                        <strong>Project:</strong>
                    </td>
                    <td style="padding: 8px 0; color: #1a1a1a;">
                        {meeting.get('project_name', 'N/A')}
                    </td>
                </tr>
            </table>
        </div>
        
        {agenda_html}
        
        <!-- Action Buttons -->
        <div style="margin-top: 30px; text-align: center;">
            <p style="color: #6b7280; font-size: 14px; margin-bottom: 20px;">
                Please respond to this invitation:
            </p>
            
            <table style="width: 100%; border-collapse: collapse;">
                <tr>
                    <td style="padding: 5px; text-align: center;">
                        <a href="{response_url}&action=accept" 
                           style="display: inline-block; background-color: #059669; color: white; padding: 14px 28px; text-decoration: none; border-radius: 8px; font-weight: 600; font-size: 14px;">
                            ✓ Accept
                        </a>
                    </td>
                    <td style="padding: 5px; text-align: center;">
                        <a href="{response_url}&action=reject" 
                           style="display: inline-block; background-color: #dc2626; color: white; padding: 14px 28px; text-decoration: none; border-radius: 8px; font-weight: 600; font-size: 14px;">
                            ✗ Decline
                        </a>
                    </td>
                    <td style="padding: 5px; text-align: center;">
                        <a href="{response_url}&action=reschedule" 
                           style="display: inline-block; background-color: #f59e0b; color: white; padding: 14px 28px; text-decoration: none; border-radius: 8px; font-weight: 600; font-size: 14px;">
                            ↻ Reschedule
                        </a>
                    </td>
                </tr>
            </table>
        </div>
        
        <!-- Expiry Notice -->
        <div style="margin-top: 25px; padding: 15px; background-color: #fef3c7; border: 1px solid #fcd34d; border-radius: 8px;">
            <p style="margin: 0; color: #92400e; font-size: 13px;">
                <strong>⏰ Important:</strong> This invitation link will expire in 24 hours. 
                If no response is received, the meeting will be <strong>automatically accepted</strong>.
            </p>
        </div>
        
        <p style="color: #6b7280; margin-top: 25px; font-size: 14px;">
            If you have any questions, please contact {scheduled_by_name} directly.
        </p>
        
    </div>
    
    <!-- Footer -->
    <div style="background: #f8f9fa; padding: 20px; border-radius: 0 0 12px 12px; border: 1px solid #e5e7eb; border-top: none; text-align: center;">
        <p style="margin: 0; color: #6b7280; font-size: 12px;">
            © {datetime.now().year} D&V Business Consulting Pvt. Ltd.
        </p>
        <p style="margin: 5px 0 0 0; color: #9ca3af; font-size: 11px;">
            This is an automated message. Please do not reply directly to this email.
        </p>
    </div>
    
</body>
</html>
"""


def get_meeting_response_confirmation_html(
    meeting: Dict[str, Any],
    client_name: str,
    response_type: str,  # ACCEPTED, REJECTED, RESCHEDULED
    calendar_link: Optional[str] = None
) -> str:
    """Generate HTML for response confirmation email"""
    
    meeting_date = meeting.get('meeting_date')
    if isinstance(meeting_date, str):
        meeting_date = datetime.fromisoformat(meeting_date.replace('Z', '+00:00'))
    
    formatted_date = meeting_date.strftime('%A, %B %d, %Y at %I:%M %p')
    
    status_config = {
        'ACCEPTED': {
            'title': 'Meeting Confirmed',
            'icon': '✓',
            'color': '#059669',
            'bg': '#f0fdf4',
            'message': f'Your meeting on <strong>{formatted_date}</strong> has been confirmed.'
        },
        'REJECTED': {
            'title': 'Meeting Declined',
            'icon': '✗',
            'color': '#dc2626',
            'bg': '#fef2f2',
            'message': 'The meeting has been declined. The organizer has been notified.'
        },
        'RESCHEDULED': {
            'title': 'Reschedule Requested',
            'icon': '↻',
            'color': '#f59e0b',
            'bg': '#fffbeb',
            'message': 'Your reschedule request has been sent. The organizer will contact you with new time options.'
        }
    }
    
    config = status_config.get(response_type, status_config['ACCEPTED'])
    
    calendar_html = ""
    if response_type == 'ACCEPTED' and calendar_link:
        calendar_html = f"""
        <div style="margin-top: 20px; text-align: center;">
            <a href="{calendar_link}" 
               style="display: inline-block; background-color: #3b82f6; color: white; padding: 12px 24px; text-decoration: none; border-radius: 8px; font-weight: 600; font-size: 14px;">
                📅 Add to Calendar
            </a>
        </div>
        """
    
    return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
    
    <!-- Header -->
    <div style="background: linear-gradient(135deg, #059669 0%, #047857 100%); padding: 30px; border-radius: 12px 12px 0 0; text-align: center;">
        <h1 style="color: white; margin: 0; font-size: 24px; font-weight: 600;">D&V Business Consulting</h1>
    </div>
    
    <!-- Content -->
    <div style="background: white; padding: 30px; border: 1px solid #e5e7eb; border-top: none;">
        
        <div style="text-align: center; padding: 20px; background: {config['bg']}; border-radius: 8px; margin-bottom: 20px;">
            <span style="font-size: 48px;">{config['icon']}</span>
            <h2 style="margin: 10px 0; color: {config['color']};">{config['title']}</h2>
        </div>
        
        <p style="font-size: 16px; color: #1a1a1a;">Dear <strong>{client_name}</strong>,</p>
        
        <p style="color: #4a5568;">{config['message']}</p>
        
        <!-- Meeting Details -->
        <div style="background: #f8f9fa; border-radius: 8px; padding: 15px; margin: 20px 0;">
            <p style="margin: 5px 0; color: #4a5568;">
                <strong>Meeting:</strong> {meeting.get('title', 'Consulting Meeting')}
            </p>
            <p style="margin: 5px 0; color: #4a5568;">
                <strong>Project:</strong> {meeting.get('project_name', 'N/A')}
            </p>
        </div>
        
        {calendar_html}
        
    </div>
    
    <!-- Footer -->
    <div style="background: #f8f9fa; padding: 20px; border-radius: 0 0 12px 12px; border: 1px solid #e5e7eb; border-top: none; text-align: center;">
        <p style="margin: 0; color: #6b7280; font-size: 12px;">
            © {datetime.now().year} D&V Business Consulting Pvt. Ltd.
        </p>
    </div>
    
</body>
</html>
"""


def get_manager_notification_html(
    meeting: Dict[str, Any],
    manager_name: str,
    scheduled_by_name: str,
    notification_type: str  # NEW_MEETING, CLIENT_ACCEPTED, CLIENT_REJECTED, CLIENT_RESCHEDULED
) -> str:
    """Generate HTML for manager notification emails"""
    
    meeting_date = meeting.get('meeting_date')
    if isinstance(meeting_date, str):
        meeting_date = datetime.fromisoformat(meeting_date.replace('Z', '+00:00'))
    
    formatted_date = meeting_date.strftime('%A, %B %d, %Y at %I:%M %p')
    
    type_config = {
        'NEW_MEETING': {
            'title': 'New Meeting Scheduled',
            'color': '#3b82f6',
            'message': f'{scheduled_by_name} has scheduled a new meeting.'
        },
        'CLIENT_ACCEPTED': {
            'title': 'Client Accepted Meeting',
            'color': '#059669',
            'message': f'The client has confirmed the meeting scheduled by {scheduled_by_name}.'
        },
        'CLIENT_REJECTED': {
            'title': 'Client Declined Meeting',
            'color': '#dc2626',
            'message': f'The client has declined the meeting scheduled by {scheduled_by_name}.'
        },
        'CLIENT_RESCHEDULED': {
            'title': 'Client Requested Reschedule',
            'color': '#f59e0b',
            'message': f'The client has requested to reschedule the meeting by {scheduled_by_name}.'
        },
        'AUTO_ACCEPTED': {
            'title': 'Meeting Auto-Accepted',
            'color': '#8b5cf6',
            'message': f'The meeting scheduled by {scheduled_by_name} was auto-accepted (no client response within 24h).'
        }
    }
    
    config = type_config.get(notification_type, type_config['NEW_MEETING'])
    
    return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
</head>
<body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
    
    <div style="background: {config['color']}; padding: 20px; border-radius: 8px 8px 0 0;">
        <h2 style="color: white; margin: 0;">{config['title']}</h2>
    </div>
    
    <div style="background: white; padding: 20px; border: 1px solid #e5e7eb; border-top: none; border-radius: 0 0 8px 8px;">
        <p>Dear <strong>{manager_name}</strong>,</p>
        <p>{config['message']}</p>
        
        <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; margin: 15px 0;">
            <p style="margin: 5px 0;"><strong>Meeting:</strong> {meeting.get('title', 'Consulting Meeting')}</p>
            <p style="margin: 5px 0;"><strong>Client:</strong> {meeting.get('client_name', 'N/A')}</p>
            <p style="margin: 5px 0;"><strong>Project:</strong> {meeting.get('project_name', 'N/A')}</p>
            <p style="margin: 5px 0;"><strong>Date:</strong> {formatted_date}</p>
        </div>
        
        <p style="color: #6b7280; font-size: 13px;">
            <a href="{FRONTEND_URL}/consulting-meetings" style="color: #059669;">View in Dashboard →</a>
        </p>
    </div>
    
</body>
</html>
"""


async def send_meeting_invite(
    meeting: Dict[str, Any],
    client_email: str,
    client_name: str,
    scheduled_by_name: str,
    db
) -> Dict[str, Any]:
    """
    Send meeting invitation email to client with Accept/Reject/Reschedule links.
    Returns the response token and updated meeting data.
    """
    
    # Generate single-use token
    token = generate_response_token()
    token_expires = datetime.now(timezone.utc) + timedelta(hours=24)
    
    # Build response URL
    response_url = f"{FRONTEND_URL}/meeting-response?token={token}"
    
    # Generate email HTML
    html_content = get_meeting_invite_html(
        meeting=meeting,
        client_name=client_name,
        response_url=response_url,
        scheduled_by_name=scheduled_by_name
    )
    
    # Send email
    meeting_date = meeting.get('meeting_date')
    if isinstance(meeting_date, str):
        meeting_date = datetime.fromisoformat(meeting_date.replace('Z', '+00:00'))
    
    formatted_date = meeting_date.strftime('%b %d, %Y')
    subject = f"Meeting Invitation: {meeting.get('title', 'Consulting Meeting')} - {formatted_date}"
    
    result = await send_email(
        to_email=client_email,
        subject=subject,
        html_content=html_content
    )
    
    # Update meeting with token and notification info
    update_data = {
        "client_response_token": token,
        "client_token_expires_at": token_expires.isoformat(),
        "client_token_used": False,
        "invite_sent_at": datetime.now(timezone.utc).isoformat(),
        "invite_sent_to": [client_email],
        "status": "SCHEDULED"
    }
    
    # Update in database
    await db.meetings.update_one(
        {"id": meeting['id']},
        {"$set": update_data}
    )
    
    logger.info(f"Meeting invite sent to {client_email} for meeting {meeting['id']}")
    
    return {
        "status": "sent" if result.get("status") == "success" else result.get("status"),
        "token": token,
        "expires_at": token_expires.isoformat(),
        "sent_to": client_email,
        "meeting_id": meeting['id']
    }


async def send_manager_notification(
    meeting: Dict[str, Any],
    manager_email: str,
    manager_name: str,
    scheduled_by_name: str,
    notification_type: str
) -> Dict[str, Any]:
    """Send notification to manager about meeting events"""
    
    html_content = get_manager_notification_html(
        meeting=meeting,
        manager_name=manager_name,
        scheduled_by_name=scheduled_by_name,
        notification_type=notification_type
    )
    
    type_subjects = {
        'NEW_MEETING': 'New Meeting Scheduled',
        'CLIENT_ACCEPTED': 'Client Confirmed Meeting',
        'CLIENT_REJECTED': 'Client Declined Meeting',
        'CLIENT_RESCHEDULED': 'Client Reschedule Request',
        'AUTO_ACCEPTED': 'Meeting Auto-Accepted'
    }
    
    subject = f"[{meeting.get('client_name', 'Client')}] {type_subjects.get(notification_type, 'Meeting Update')}"
    
    result = await send_email(
        to_email=manager_email,
        subject=subject,
        html_content=html_content
    )
    
    return result


async def send_response_confirmation(
    meeting: Dict[str, Any],
    client_email: str,
    client_name: str,
    response_type: str
) -> Dict[str, Any]:
    """Send confirmation email after client responds"""
    
    # Generate Google Calendar link for accepted meetings
    calendar_link = None
    if response_type == 'ACCEPTED':
        meeting_date = meeting.get('meeting_date')
        if isinstance(meeting_date, str):
            meeting_date = datetime.fromisoformat(meeting_date.replace('Z', '+00:00'))
        
        duration = meeting.get('duration_minutes') or 60
        end_time = meeting_date + timedelta(minutes=duration)
        
        # Google Calendar URL format
        calendar_link = (
            f"https://calendar.google.com/calendar/render?action=TEMPLATE"
            f"&text={meeting.get('title', 'Consulting Meeting').replace(' ', '+')}"
            f"&dates={meeting_date.strftime('%Y%m%dT%H%M%SZ')}/{end_time.strftime('%Y%m%dT%H%M%SZ')}"
            f"&details=Meeting+with+D%26V+Business+Consulting"
        )
    
    html_content = get_meeting_response_confirmation_html(
        meeting=meeting,
        client_name=client_name,
        response_type=response_type,
        calendar_link=calendar_link
    )
    
    subject_map = {
        'ACCEPTED': 'Meeting Confirmed',
        'REJECTED': 'Meeting Declined',
        'RESCHEDULED': 'Reschedule Request Received'
    }
    
    subject = f"{subject_map.get(response_type, 'Meeting Update')} - {meeting.get('title', 'Consulting Meeting')}"
    
    result = await send_email(
        to_email=client_email,
        subject=subject,
        html_content=html_content
    )
    
    return result


async def process_auto_accept_meetings(db) -> List[Dict[str, Any]]:
    """
    Background task: Find meetings with expired tokens and auto-accept them.
    Should be called periodically (e.g., every hour).
    """
    
    now = datetime.now(timezone.utc)
    
    # Find meetings that are:
    # - Status = SCHEDULED
    # - Token sent but not used
    # - Token expired (> 24h)
    # - Not already auto-accepted
    
    expired_meetings = await db.meetings.find({
        "status": "SCHEDULED",
        "client_token_used": False,
        "client_response_token": {"$ne": None},
        "client_token_expires_at": {"$lt": now.isoformat()}
    }).to_list(100)
    
    results = []
    
    for meeting in expired_meetings:
        # Auto-accept the meeting
        update_data = {
            "status": "AUTO_ACCEPTED",
            "client_response": "AUTO_ACCEPTED",
            "client_response_at": now.isoformat(),
            "client_token_used": True,
            "$push": {
                "state_history": {
                    "from_state": "SCHEDULED",
                    "to_state": "AUTO_ACCEPTED",
                    "changed_by": "SYSTEM",
                    "changed_at": now.isoformat(),
                    "reason": "No client response within 24 hours"
                }
            }
        }
        
        await db.meetings.update_one(
            {"id": meeting['id']},
            {"$set": {k: v for k, v in update_data.items() if k != "$push"}, "$push": update_data.get("$push", {})}
        )
        
        results.append({
            "meeting_id": meeting['id'],
            "title": meeting.get('title'),
            "client_name": meeting.get('client_name'),
            "status": "auto_accepted"
        })
        
        logger.info(f"Meeting {meeting['id']} auto-accepted due to no client response")
    
    return results
