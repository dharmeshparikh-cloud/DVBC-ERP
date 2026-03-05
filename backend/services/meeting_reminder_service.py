"""
Meeting Reminder Service - Automated notifications for upcoming meetings

Features:
1. Send reminders to both clients and consultants
2. 24-hour and 1-hour advance reminders
3. User-configurable notification preferences
4. Email-based notifications
"""

from typing import Dict, List, Optional
from datetime import datetime, timezone, timedelta
from uuid import uuid4
import logging

logger = logging.getLogger("meeting_reminder_service")


async def get_user_notification_preferences(db, user_id: str) -> Dict:
    """
    Get user's notification preferences.
    Returns defaults if not set.
    """
    prefs = await db.notification_preferences.find_one(
        {"user_id": user_id},
        {"_id": 0}
    )
    
    if not prefs:
        # Return defaults
        return {
            "user_id": user_id,
            "meeting_reminders": {
                "enabled": True,
                "remind_24h": True,
                "remind_1h": True,
                "email": True,
                "in_app": True
            },
            "mom_notifications": {
                "enabled": True,
                "email": True
            }
        }
    
    return prefs


async def update_notification_preferences(db, user_id: str, preferences: Dict) -> Dict:
    """
    Update user's notification preferences.
    """
    now = datetime.now(timezone.utc).isoformat()
    
    prefs_doc = {
        "user_id": user_id,
        **preferences,
        "updated_at": now
    }
    
    result = await db.notification_preferences.update_one(
        {"user_id": user_id},
        {"$set": prefs_doc},
        upsert=True
    )
    
    return {
        "success": True,
        "user_id": user_id,
        "preferences": prefs_doc
    }


async def get_meetings_needing_reminders(db, reminder_type: str = "24h") -> List[Dict]:
    """
    Get meetings that need reminders sent.
    
    Args:
        reminder_type: "24h" or "1h"
    
    Returns:
        List of meetings needing reminders
    """
    now = datetime.now(timezone.utc)
    
    if reminder_type == "24h":
        # Meetings happening in 23-25 hours
        window_start = now + timedelta(hours=23)
        window_end = now + timedelta(hours=25)
        reminder_field = "reminder_24h_sent"
    else:  # 1h
        # Meetings happening in 55-65 minutes
        window_start = now + timedelta(minutes=55)
        window_end = now + timedelta(minutes=65)
        reminder_field = "reminder_1h_sent"
    
    meetings = await db.meetings.find({
        "meeting_date": {
            "$gte": window_start.isoformat(),
            "$lte": window_end.isoformat()
        },
        "is_delivered": False,
        reminder_field: {"$ne": True}
    }, {"_id": 0}).to_list(100)
    
    return meetings


async def send_meeting_reminder(
    db,
    meeting_id: str,
    reminder_type: str = "24h"
) -> Dict:
    """
    Send reminder for a specific meeting to all attendees and client.
    """
    from services.email_service import send_email
    
    meeting = await db.meetings.find_one({"id": meeting_id}, {"_id": 0})
    if not meeting:
        return {"error": "Meeting not found"}
    
    results = {
        "meeting_id": meeting_id,
        "consultants_notified": [],
        "client_notified": False,
        "errors": []
    }
    
    # Get meeting details
    meeting_date = meeting.get("meeting_date", "")
    if isinstance(meeting_date, str):
        try:
            meeting_dt = datetime.fromisoformat(meeting_date.replace('Z', '+00:00'))
            date_str = meeting_dt.strftime("%A, %B %d, %Y at %I:%M %p")
        except ValueError:
            date_str = meeting_date
    else:
        date_str = meeting_date.strftime("%A, %B %d, %Y at %I:%M %p") if meeting_date else "TBD"
    
    meeting_title = meeting.get("title", "Meeting")
    meeting_mode = meeting.get("mode", "online")
    
    # Determine time label
    time_label = "24 hours" if reminder_type == "24h" else "1 hour"
    
    # Build email template
    def build_reminder_email(recipient_name: str, is_client: bool = False):
        mode_text = {
            "online": "Online Meeting",
            "offline": "In-Person Meeting",
            "tele_call": "Phone Call"
        }.get(meeting_mode, "Meeting")
        
        role_text = "your scheduled meeting" if is_client else "a client meeting you're assigned to"
        
        return f"""
        <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto; background: #ffffff;">
            <div style="background: linear-gradient(135deg, #059669 0%, #10b981 100%); padding: 24px; border-radius: 12px 12px 0 0;">
                <h1 style="color: #ffffff; margin: 0; font-size: 20px; font-weight: 600;">⏰ Meeting Reminder</h1>
                <p style="color: #d1fae5; margin: 8px 0 0 0; font-size: 14px;">Starting in {time_label}</p>
            </div>
            
            <div style="padding: 24px; border: 1px solid #e5e7eb; border-top: none;">
                <p style="color: #374151; margin: 0 0 16px 0;">Hi {recipient_name},</p>
                <p style="color: #374151; margin: 0 0 20px 0;">This is a reminder for {role_text}:</p>
                
                <div style="background: #f9fafb; border-radius: 8px; padding: 16px; margin-bottom: 20px;">
                    <h2 style="color: #111827; margin: 0 0 12px 0; font-size: 18px;">{meeting_title}</h2>
                    <p style="color: #6b7280; margin: 4px 0; font-size: 14px;">
                        📅 <strong>{date_str}</strong>
                    </p>
                    <p style="color: #6b7280; margin: 4px 0; font-size: 14px;">
                        📍 <strong>{mode_text}</strong>
                    </p>
                    <p style="color: #6b7280; margin: 4px 0; font-size: 14px;">
                        ⏱️ <strong>{meeting.get('duration_minutes', 60)} minutes</strong>
                    </p>
                </div>
                
                {f'<p style="color: #374151; margin: 0 0 8px 0;"><strong>Attendees:</strong></p><p style="color: #6b7280; margin: 0 0 20px 0;">{", ".join(meeting.get("attendee_names", []))}</p>' if meeting.get("attendee_names") else ''}
                
                {f'<p style="color: #374151; margin: 0 0 8px 0;"><strong>Notes:</strong></p><p style="color: #6b7280; margin: 0 0 20px 0;">{meeting.get("notes", "")}</p>' if meeting.get("notes") else ''}
            </div>
            
            <div style="background: #f3f4f6; padding: 16px; border-radius: 0 0 12px 12px; text-align: center;">
                <p style="color: #6b7280; font-size: 12px; margin: 0;">D&V Business Consulting | NETRA ERP</p>
            </div>
        </div>
        """
    
    # 1. Send to consultants
    for attendee_id in meeting.get("attendees", []):
        # Check user preferences
        prefs = await get_user_notification_preferences(db, attendee_id)
        meeting_prefs = prefs.get("meeting_reminders", {})
        
        if not meeting_prefs.get("enabled", True):
            continue
        
        remind_field = "remind_24h" if reminder_type == "24h" else "remind_1h"
        if not meeting_prefs.get(remind_field, True):
            continue
        
        if not meeting_prefs.get("email", True):
            continue
        
        # Get user email
        user = await db.users.find_one({"id": attendee_id}, {"_id": 0, "email": 1, "full_name": 1})
        if not user or not user.get("email"):
            continue
        
        try:
            html_content = build_reminder_email(user.get("full_name", "Team Member"), is_client=False)
            await send_email(
                to_email=user["email"],
                subject=f"⏰ Reminder: {meeting_title} - Starting in {time_label}",
                html_content=html_content,
                plain_content=f"Meeting Reminder: {meeting_title} on {date_str}"
            )
            results["consultants_notified"].append(user["email"])
        except Exception as e:
            results["errors"].append({"user_id": attendee_id, "error": str(e)})
    
    # 2. Send to client (from lead)
    lead_id = meeting.get("lead_id")
    if not lead_id and meeting.get("project_id"):
        # Get lead from project
        project = await db.projects.find_one({"id": meeting["project_id"]}, {"_id": 0, "lead_id": 1})
        if project:
            lead_id = project.get("lead_id")
    
    if lead_id:
        lead = await db.leads.find_one({"id": lead_id}, {"_id": 0, "email": 1, "first_name": 1, "last_name": 1, "company": 1})
        if lead and lead.get("email"):
            # Check if client notifications are enabled (stored at lead level)
            client_prefs = await db.client_notification_preferences.find_one({"lead_id": lead_id}, {"_id": 0})
            
            # Default to enabled for clients
            if not client_prefs or client_prefs.get("meeting_reminders", {}).get("enabled", True):
                try:
                    client_name = f"{lead.get('first_name', '')} {lead.get('last_name', '')}".strip() or lead.get("company", "Client")
                    html_content = build_reminder_email(client_name, is_client=True)
                    await send_email(
                        to_email=lead["email"],
                        subject=f"⏰ Meeting Reminder: {meeting_title} - Starting in {time_label}",
                        html_content=html_content,
                        plain_content=f"Meeting Reminder: {meeting_title} on {date_str}"
                    )
                    results["client_notified"] = True
                    results["client_email"] = lead["email"]
                except Exception as e:
                    results["errors"].append({"lead_id": lead_id, "error": str(e)})
    
    # Mark reminder as sent
    reminder_field = "reminder_24h_sent" if reminder_type == "24h" else "reminder_1h_sent"
    await db.meetings.update_one(
        {"id": meeting_id},
        {"$set": {
            reminder_field: True,
            f"{reminder_field}_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    logger.info(f"Sent {reminder_type} reminder for meeting {meeting_id}: {len(results['consultants_notified'])} consultants, client: {results['client_notified']}")
    
    return results


async def process_all_pending_reminders(db, reminder_type: str = "24h") -> Dict:
    """
    Process all meetings needing reminders.
    Should be called by a cron job or scheduled task.
    """
    meetings = await get_meetings_needing_reminders(db, reminder_type)
    
    results = {
        "reminder_type": reminder_type,
        "meetings_processed": 0,
        "total_consultants_notified": 0,
        "total_clients_notified": 0,
        "errors": []
    }
    
    for meeting in meetings:
        try:
            result = await send_meeting_reminder(db, meeting["id"], reminder_type)
            results["meetings_processed"] += 1
            results["total_consultants_notified"] += len(result.get("consultants_notified", []))
            if result.get("client_notified"):
                results["total_clients_notified"] += 1
            if result.get("errors"):
                results["errors"].extend(result["errors"])
        except Exception as e:
            results["errors"].append({"meeting_id": meeting["id"], "error": str(e)})
    
    return results


async def send_test_reminder(db, user_id: str, email: str) -> Dict:
    """
    Send a test reminder to verify email setup.
    """
    from services.email_service import send_email
    
    try:
        html_content = f"""
        <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: linear-gradient(135deg, #059669 0%, #10b981 100%); padding: 24px; border-radius: 12px 12px 0 0;">
                <h1 style="color: #ffffff; margin: 0; font-size: 20px;">✅ Test Reminder</h1>
            </div>
            <div style="padding: 24px; border: 1px solid #e5e7eb; border-top: none; border-radius: 0 0 12px 12px;">
                <p style="color: #374151;">This is a test email to confirm your meeting reminder notifications are working correctly.</p>
                <p style="color: #6b7280; font-size: 14px;">You will receive reminders 24 hours and 1 hour before your scheduled meetings.</p>
            </div>
        </div>
        """
        
        await send_email(
            to_email=email,
            subject="✅ NETRA - Test Meeting Reminder",
            html_content=html_content,
            plain_content="This is a test reminder notification from NETRA ERP."
        )
        
        return {"success": True, "sent_to": email}
    except Exception as e:
        return {"success": False, "error": str(e)}
