"""
Approval Notification Service
Auto-triggers real-time email and WebSocket notifications for all approval workflows
"""
from datetime import datetime, timezone
from typing import Optional, Dict, Any
import uuid
import os


async def send_approval_notification(
    db,
    ws_manager,
    record_type: str,
    record_id: str,
    requester_id: str,
    requester_name: str,
    requester_email: str,
    approver_id: str,
    approver_name: str,
    approver_email: str,
    details: Dict[str, Any],
    custom_message: Optional[str] = None,
    link: Optional[str] = None
):
    """
    Send approval notification via:
    1. Real-time WebSocket notification
    2. Email with one-click Approve/Reject buttons
    3. In-app notification (stored in DB)
    
    Args:
        db: Database connection
        ws_manager: WebSocket manager for real-time notifications
        record_type: Type of record (leave_request, expense, kickoff, go_live, ctc, bank_change, sow)
        record_id: ID of the record requiring approval
        requester_id: User ID of person requesting approval
        requester_name: Name of requester
        requester_email: Email of requester
        approver_id: User ID of approver
        approver_name: Name of approver
        approver_email: Email of approver
        details: Dictionary of details to show in notification/email
        custom_message: Optional message from requester
        link: Optional link to the record in app
    """
    
    # Record type configurations
    type_config = {
        "leave_request": {
            "title": "Leave Request Approval",
            "notification_type": "leave_request",
            "email_subject": f"Leave Request from {requester_name} - Action Required",
            "link": link or "/leave-management"
        },
        "expense": {
            "title": "Expense Approval Required",
            "notification_type": "expense_submitted",
            "email_subject": f"Expense Approval: ₹{details.get('amount', '')} from {requester_name}",
            "link": link or "/expense-approvals"
        },
        "kickoff": {
            "title": "Project Kickoff Approval",
            "notification_type": "approval_request",
            "email_subject": f"Kickoff Approval - {details.get('project_name', 'New Project')}",
            "link": link or "/kickoff-requests"
        },
        "go_live": {
            "title": "Go-Live Approval Required",
            "notification_type": "go_live_approval",
            "email_subject": f"Go-Live Approval: {requester_name}",
            "link": link or "/go-live-dashboard"
        },
        "ctc": {
            "title": "CTC Approval Required",
            "notification_type": "ctc_approval",
            "email_subject": f"CTC Approval Required: {requester_name}",
            "link": link or "/ctc-approvals"
        },
        "bank_change": {
            "title": "Bank Details Change Approval",
            "notification_type": "approval_request",
            "email_subject": f"Bank Details Change: {requester_name}",
            "link": link or "/bank-change-requests"
        },
        "sow": {
            "title": "SOW Approval Required",
            "notification_type": "approval_request",
            "email_subject": f"SOW Approval: {details.get('sow_title', 'SOW Items')}",
            "link": link or "/sow-approvals"
        },
        "travel_reimbursement": {
            "title": "Travel Reimbursement Approval",
            "notification_type": "expense_submitted",
            "email_subject": f"Travel Reimbursement: ₹{details.get('amount', '')} from {requester_name}",
            "link": link or "/expense-approvals"
        }
    }
    
    config = type_config.get(record_type, {
        "title": f"{record_type.replace('_', ' ').title()} Approval",
        "notification_type": "approval_request",
        "email_subject": f"Approval Required from {requester_name}",
        "link": link or "/dashboard"
    })
    
    # 1. Create in-app notification
    notification = {
        "id": str(uuid.uuid4()),
        "user_id": approver_id,
        "type": config["notification_type"],
        "title": config["title"],
        "message": f"{requester_name} has submitted a {record_type.replace('_', ' ')} for your approval.",
        "link": config["link"],
        "reference_type": record_type,
        "reference_id": record_id,
        "is_read": False,
        "status": "pending",
        "created_at": datetime.now(timezone.utc)
    }
    
    await db.notifications.insert_one(notification)
    
    # 2. Send real-time WebSocket notification
    try:
        notif_json = {
            **notification,
            "created_at": notification["created_at"].isoformat()
        }
        await ws_manager.send_notification(approver_id, notif_json)
    except Exception as e:
        print(f"WebSocket notification failed: {e}")
    
    # 3. Send email with one-click actions
    try:
        await send_approval_email(
            db=db,
            record_type=record_type,
            record_id=record_id,
            recipient_email=approver_email,
            recipient_name=approver_name,
            requester_name=requester_name,
            details=details,
            custom_message=custom_message
        )
    except Exception as e:
        print(f"Email notification failed: {e}")
    
    return notification


async def send_approval_email(
    db,
    record_type: str,
    record_id: str,
    recipient_email: str,
    recipient_name: str,
    requester_name: str,
    details: Dict[str, Any],
    custom_message: Optional[str] = None
):
    """Send approval email with one-click action buttons"""
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    import secrets
    import hashlib
    
    # Get email config
    smtp_host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    smtp_user = os.environ.get("SMTP_USER")
    smtp_password = os.environ.get("SMTP_PASSWORD")
    sender_name = os.environ.get("SENDER_NAME", "DVBC NETRA")
    base_url = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8001")
    
    if not smtp_user or not smtp_password:
        print("SMTP credentials not configured, skipping email")
        return False
    
    # Generate action tokens
    def generate_token(action):
        token_data = f"{record_type}:{record_id}:{action}:{secrets.token_hex(16)}"
        return hashlib.sha256(token_data.encode()).hexdigest()[:32]
    
    approve_token = generate_token("approve")
    reject_token = generate_token("reject")
    
    # Store tokens
    for token, action in [(approve_token, "approve"), (reject_token, "reject")]:
        await db.email_action_tokens.insert_one({
            "token": token,
            "record_type": record_type,
            "record_id": record_id,
            "action": action,
            "recipient_email": recipient_email,
            "created_at": datetime.now(timezone.utc),
            "expires_at": datetime.now(timezone.utc) + __import__('datetime').timedelta(hours=24),
            "used": False
        })
    
    # Build URLs
    approve_url = f"{base_url}/api/email-actions/execute/{approve_token}"
    reject_url = f"{base_url}/api/email-actions/execute/{reject_token}"
    
    # Build email HTML
    html_content = build_approval_email_html(
        record_type=record_type,
        requester_name=requester_name,
        recipient_name=recipient_name,
        details=details,
        approve_url=approve_url,
        reject_url=reject_url,
        custom_message=custom_message
    )
    
    # Email subject
    subjects = {
        "leave_request": f"Leave Request from {requester_name} - Action Required",
        "expense": f"Expense Approval: ₹{details.get('amount', '')} from {requester_name}",
        "kickoff": f"Project Kickoff Approval - {details.get('project_name', 'New Project')}",
        "go_live": f"Go-Live Approval Required - {requester_name}",
        "ctc": f"CTC Approval Required - {requester_name}",
        "bank_change": f"Bank Details Change - {requester_name}",
        "sow": f"SOW Approval - {details.get('sow_title', requester_name)}",
        "travel_reimbursement": f"Travel Reimbursement - {requester_name}"
    }
    subject = subjects.get(record_type, f"Approval Required - {requester_name}")
    
    # Send email
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{sender_name} <{smtp_user}>"
    msg["To"] = recipient_email
    
    html_part = MIMEText(html_content, "html")
    msg.attach(html_part)
    
    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.sendmail(smtp_user, recipient_email, msg.as_string())
    
    # Log email
    await db.email_logs.insert_one({
        "id": str(uuid.uuid4()),
        "record_type": record_type,
        "record_id": record_id,
        "recipient_email": recipient_email,
        "recipient_name": recipient_name,
        "requester_name": requester_name,
        "subject": subject,
        "sent_at": datetime.now(timezone.utc),
        "status": "sent"
    })
    
    return True


def build_approval_email_html(
    record_type: str,
    requester_name: str,
    recipient_name: str,
    details: dict,
    approve_url: str,
    reject_url: str,
    custom_message: str = None
) -> str:
    """Build HTML email content for approval request"""
    
    type_config = {
        "leave_request": {"title": "Leave Request Approval", "icon": "📅"},
        "expense": {"title": "Expense Approval Required", "icon": "💰"},
        "kickoff": {"title": "Project Kickoff Approval", "icon": "🚀"},
        "go_live": {"title": "Go-Live Approval Required", "icon": "✅"},
        "ctc": {"title": "CTC Approval Required", "icon": "💼"},
        "bank_change": {"title": "Bank Details Change", "icon": "🏦"},
        "sow": {"title": "SOW Approval Required", "icon": "📋"},
        "travel_reimbursement": {"title": "Travel Reimbursement", "icon": "✈️"}
    }
    
    config = type_config.get(record_type, {"title": "Approval Required", "icon": "📋"})
    
    # Build details table
    details_rows = ""
    for key, value in details.items():
        label = key.replace("_", " ").title()
        details_rows += f"""
        <tr>
            <td style="padding: 12px; border-bottom: 1px solid #eee; color: #666; width: 40%;">{label}</td>
            <td style="padding: 12px; border-bottom: 1px solid #eee; font-weight: 500;">{value}</td>
        </tr>
        """
    
    custom_msg_html = ""
    if custom_message:
        custom_msg_html = f"""
        <div style="background: #f8fafc; border-left: 4px solid #3b82f6; padding: 15px; margin: 20px 0;">
            <strong>Note from requester:</strong>
            <p style="margin: 10px 0 0 0;">{custom_message}</p>
        </div>
        """
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 0; background-color: #f5f5f5;">
        <div style="max-width: 600px; margin: 0 auto; background: #ffffff;">
            <!-- Header -->
            <div style="background: linear-gradient(135deg, #1f2937 0%, #374151 100%); padding: 30px; text-align: center;">
                <img src="https://customer-assets.emergentagent.com/job_service-flow-mgmt/artifacts/g8hoyjfe_DVBC%20NEW%20LOGO%201.png" alt="DVBC" style="height: 50px; margin-bottom: 10px;">
                <h1 style="color: white; margin: 0; font-size: 24px;">DVBC - NETRA</h1>
                <p style="color: #9ca3af; margin: 5px 0 0 0; font-size: 14px;">Business Management Platform</p>
            </div>
            
            <!-- Content -->
            <div style="padding: 30px;">
                <h2 style="color: #1f2937; margin: 0 0 20px 0;">{config['icon']} {config['title']}</h2>
                
                <p>Hi <strong>{recipient_name}</strong>,</p>
                
                <p>
                    <span style="color: #f97316; font-weight: 600;">{requester_name}</span> has submitted a 
                    {record_type.replace('_', ' ')} that requires your approval.
                </p>
                
                <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
                    {details_rows}
                </table>
                
                {custom_msg_html}
                
                <div style="text-align: center; padding: 25px 0;">
                    <a href="{approve_url}" style="display: inline-block; padding: 14px 32px; margin: 0 10px; text-decoration: none; border-radius: 6px; font-weight: 600; font-size: 14px; background: #22c55e; color: white;">✓ Approve</a>
                    <a href="{reject_url}" style="display: inline-block; padding: 14px 32px; margin: 0 10px; text-decoration: none; border-radius: 6px; font-weight: 600; font-size: 14px; background: #ef4444; color: white;">✗ Reject</a>
                </div>
                
                <p style="text-align: center; color: #999; font-size: 12px;">
                    ⏰ These action links will expire in 24 hours for security reasons.
                </p>
            </div>
            
            <!-- Footer -->
            <div style="background: #f8fafc; padding: 25px; text-align: center; border-top: 1px solid #e5e7eb;">
                <p style="color: #666; margin: 0 0 10px 0; font-size: 14px;">This is an automated message from NETRA ERP</p>
                <p style="color: #999; margin: 0; font-size: 12px;">© 2026 DVBC Consulting. All rights reserved.</p>
            </div>
        </div>
    </body>
    </html>
    """


async def notify_requester_on_action(
    db,
    ws_manager,
    record_type: str,
    record_id: str,
    requester_id: str,
    action: str,  # approved, rejected
    approver_name: str,
    details: Dict[str, Any] = None
):
    """Notify the requester when their request is approved/rejected"""
    
    notification = {
        "id": str(uuid.uuid4()),
        "user_id": requester_id,
        "type": f"{record_type}_{action}",
        "title": f"Your {record_type.replace('_', ' ').title()} was {action.title()}",
        "message": f"Your request has been {action} by {approver_name}.",
        "reference_type": record_type,
        "reference_id": record_id,
        "is_read": False,
        "created_at": datetime.now(timezone.utc)
    }
    
    await db.notifications.insert_one(notification)
    
    # Real-time notification
    try:
        notif_json = {
            **notification,
            "created_at": notification["created_at"].isoformat()
        }
        await ws_manager.send_notification(requester_id, notif_json)
    except Exception as e:
        print(f"WebSocket notification to requester failed: {e}")
    
    return notification
