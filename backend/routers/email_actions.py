"""
Email Action System Router
- Send approval emails with one-click action links
- Secure token-based actions (24hr expiry)
- Google SMTP integration
- Pre-configured HTML templates
"""
from fastapi import APIRouter, HTTPException, Depends, Query, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta
from bson import ObjectId
import uuid
import os
import smtplib
import hashlib
import secrets
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

router = APIRouter(prefix="/email-actions", tags=["Email Actions"])


# Pydantic Models
class EmailConfig(BaseModel):
    header_html: Optional[str] = None
    footer_html: Optional[str] = None

class SendApprovalEmailRequest(BaseModel):
    record_type: str  # leave_request, expense, kickoff, go_live
    record_id: str
    recipient_email: str
    recipient_name: str
    requester_name: str
    details: Dict[str, Any]  # Dynamic details based on record type
    custom_message: Optional[str] = None


def get_db():
    from server import db
    return db


# ==================== EMAIL TEMPLATES ====================

def get_base_styles():
    """Get base CSS styles for emails"""
    return """
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 0; background-color: #f5f5f5; }
        .email-container { max-width: 600px; margin: 0 auto; background: #ffffff; }
        .content { padding: 30px; }
        .details-table { width: 100%; border-collapse: collapse; margin: 20px 0; }
        .details-table td { padding: 12px; border-bottom: 1px solid #eee; }
        .details-table td:first-child { color: #666; width: 40%; }
        .details-table td:last-child { font-weight: 500; }
        .action-buttons { text-align: center; padding: 25px 0; }
        .btn { display: inline-block; padding: 14px 32px; margin: 0 10px; text-decoration: none; border-radius: 6px; font-weight: 600; font-size: 14px; }
        .btn-approve { background: #22c55e; color: white !important; }
        .btn-reject { background: #ef4444; color: white !important; }
        .btn-view { background: #3b82f6; color: white !important; }
        .message-box { background: #f8fafc; border-left: 4px solid #3b82f6; padding: 15px; margin: 20px 0; }
        .expiry-notice { text-align: center; color: #999; font-size: 12px; padding: 15px; }
        h2 { color: #1f2937; margin: 0 0 20px 0; }
        .highlight { color: #f97316; font-weight: 600; }
    </style>
    """


def get_default_header():
    """Default email header - user can customize"""
    return """
    <div style="background: linear-gradient(135deg, #1f2937 0%, #374151 100%); padding: 30px; text-align: center;">
        <img src="https://customer-assets.emergentagent.com/job_service-flow-mgmt/artifacts/g8hoyjfe_DVBC%20NEW%20LOGO%201.png" alt="DVBC" style="height: 50px; margin-bottom: 10px;">
        <h1 style="color: white; margin: 0; font-size: 24px;">DVBC - NETRA</h1>
        <p style="color: #9ca3af; margin: 5px 0 0 0; font-size: 14px;">Business Management Platform</p>
    </div>
    """


def get_default_footer():
    """Default email footer - user can customize"""
    return """
    <div style="background: #f8fafc; padding: 25px; text-align: center; border-top: 1px solid #e5e7eb;">
        <p style="color: #666; margin: 0 0 10px 0; font-size: 14px;">This is an automated message from NETRA ERP</p>
        <p style="color: #999; margin: 0; font-size: 12px;">© 2026 DVBC Consulting. All rights reserved.</p>
        <p style="color: #999; margin: 10px 0 0 0; font-size: 11px;">
            If you did not expect this email, please ignore it or contact HR.
        </p>
    </div>
    """


async def get_email_config(db) -> dict:
    """Get custom email header/footer from settings"""
    config = await db.email_settings.find_one({"type": "email_template_config"})
    return config or {}


def generate_action_token(record_type: str, record_id: str, action: str, expiry_hours: int = 24) -> str:
    """Generate a secure, single-use token for email actions"""
    token_data = f"{record_type}:{record_id}:{action}:{secrets.token_hex(16)}"
    token = hashlib.sha256(token_data.encode()).hexdigest()[:32]
    return token


async def create_action_token(db, record_type: str, record_id: str, action: str, recipient_email: str) -> str:
    """Create and store an action token in the database"""
    token = generate_action_token(record_type, record_id, action)
    
    token_doc = {
        "token": token,
        "record_type": record_type,
        "record_id": record_id,
        "action": action,
        "recipient_email": recipient_email,
        "created_at": datetime.now(timezone.utc),
        "expires_at": datetime.now(timezone.utc) + timedelta(hours=24),
        "used": False,
        "used_at": None
    }
    
    await db.email_action_tokens.insert_one(token_doc)
    return token


def build_approval_email(
    record_type: str,
    requester_name: str,
    recipient_name: str,
    details: dict,
    approve_url: str,
    reject_url: str,
    view_url: str,
    custom_message: str = None,
    header_html: str = None,
    footer_html: str = None
) -> str:
    """Build the HTML email content"""
    
    # Record type specific content
    type_config = {
        "leave_request": {
            "title": "Leave Request Approval",
            "icon": "📅",
            "action_text": "leave request"
        },
        "expense": {
            "title": "Expense Approval Required",
            "icon": "💰",
            "action_text": "expense claim"
        },
        "kickoff": {
            "title": "Project Kickoff Approval",
            "icon": "🚀",
            "action_text": "kickoff request"
        },
        "go_live": {
            "title": "Go-Live Approval Required",
            "icon": "✅",
            "action_text": "go-live request"
        }
    }
    
    config = type_config.get(record_type, {"title": "Approval Required", "icon": "📋", "action_text": "request"})
    
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
        <div class="message-box">
            <strong>Note from requester:</strong>
            <p style="margin: 10px 0 0 0;">{custom_message}</p>
        </div>
        """
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        {get_base_styles()}
    </head>
    <body>
        <div class="email-container">
            {header_html or get_default_header()}
            
            <div class="content">
                <h2>{config['icon']} {config['title']}</h2>
                
                <p>Hi <strong>{recipient_name}</strong>,</p>
                
                <p>
                    <span class="highlight">{requester_name}</span> has submitted a {config['action_text']} 
                    that requires your approval.
                </p>
                
                <table class="details-table">
                    {details_rows}
                </table>
                
                {custom_msg_html}
                
                <div class="action-buttons">
                    <a href="{approve_url}" class="btn btn-approve">✓ Approve</a>
                    <a href="{reject_url}" class="btn btn-reject">✗ Reject</a>
                </div>
                
                <p style="text-align: center;">
                    <a href="{view_url}" class="btn btn-view">View in NETRA →</a>
                </p>
                
                <p class="expiry-notice">
                    ⏰ These action links will expire in 24 hours for security reasons.
                </p>
            </div>
            
            {footer_html or get_default_footer()}
        </div>
    </body>
    </html>
    """
    
    return html


async def send_email(recipient_email: str, subject: str, html_content: str) -> bool:
    """Send email via Google SMTP"""
    try:
        smtp_host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
        smtp_port = int(os.environ.get("SMTP_PORT", "587"))
        smtp_user = os.environ.get("SMTP_USER")
        smtp_password = os.environ.get("SMTP_PASSWORD")
        sender_name = os.environ.get("SENDER_NAME", "DVBC NETRA")
        
        if not smtp_user or not smtp_password:
            raise Exception("SMTP credentials not configured")
        
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{sender_name} <{smtp_user}>"
        msg["To"] = recipient_email
        
        # Attach HTML
        html_part = MIMEText(html_content, "html")
        msg.attach(html_part)
        
        # Send
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.sendmail(smtp_user, recipient_email, msg.as_string())
        
        return True
        
    except Exception as e:
        print(f"Email send error: {str(e)}")
        return False


# ==================== ENDPOINTS ====================

@router.post("/send-approval")
async def send_approval_email(
    request: SendApprovalEmailRequest,
    db=Depends(get_db)
):
    """Send an approval email with action buttons"""
    
    # Get email config (custom header/footer)
    email_config = await get_email_config(db)
    
    # Get base URL from environment
    base_url = os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8001")
    
    # Create action tokens
    approve_token = await create_action_token(db, request.record_type, request.record_id, "approve", request.recipient_email)
    reject_token = await create_action_token(db, request.record_type, request.record_id, "reject", request.recipient_email)
    
    # Build URLs
    approve_url = f"{base_url}/api/email-actions/execute/{approve_token}"
    reject_url = f"{base_url}/api/email-actions/execute/{reject_token}"
    
    # View URL based on record type
    view_paths = {
        "leave_request": "/leave-management",
        "expense": "/expense-approvals",
        "kickoff": "/kickoff-requests",
        "go_live": "/go-live-dashboard"
    }
    view_url = f"{base_url}{view_paths.get(request.record_type, '/dashboard')}"
    
    # Build email HTML
    html_content = build_approval_email(
        record_type=request.record_type,
        requester_name=request.requester_name,
        recipient_name=request.recipient_name,
        details=request.details,
        approve_url=approve_url,
        reject_url=reject_url,
        view_url=view_url,
        custom_message=request.custom_message,
        header_html=email_config.get("header_html"),
        footer_html=email_config.get("footer_html")
    )
    
    # Email subject
    subjects = {
        "leave_request": f"Leave Request from {request.requester_name} - Action Required",
        "expense": f"Expense Approval: ₹{request.details.get('amount', '')} from {request.requester_name}",
        "kickoff": f"Project Kickoff Approval - {request.details.get('project_name', 'New Project')}",
        "go_live": f"Go-Live Approval Required - {request.requester_name}"
    }
    subject = subjects.get(request.record_type, f"Approval Required - {request.requester_name}")
    
    # Send email
    success = await send_email(request.recipient_email, subject, html_content)
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to send email")
    
    # Log the email
    email_log = {
        "id": str(uuid.uuid4()),
        "record_type": request.record_type,
        "record_id": request.record_id,
        "recipient_email": request.recipient_email,
        "recipient_name": request.recipient_name,
        "requester_name": request.requester_name,
        "subject": subject,
        "sent_at": datetime.now(timezone.utc),
        "status": "sent"
    }
    await db.email_logs.insert_one(email_log)
    
    return {"status": "sent", "email_id": email_log["id"]}


@router.get("/execute/{token}", response_class=HTMLResponse)
async def execute_action(
    token: str,
    db=Depends(get_db)
):
    """Execute an action from an email link"""
    
    # Find token
    token_doc = await db.email_action_tokens.find_one({"token": token})
    
    if not token_doc:
        return HTMLResponse(content=_get_error_page("Invalid Link", "This action link is invalid or has already been used."), status_code=400)
    
    if token_doc.get("used"):
        return HTMLResponse(content=_get_error_page("Already Used", "This action has already been completed."), status_code=400)
    
    # Handle datetime comparison - ensure both are timezone aware
    expires_at = token_doc.get("expires_at")
    now = datetime.now(timezone.utc)
    
    # If expires_at is naive, make it aware (assume UTC)
    if expires_at and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    
    if expires_at and expires_at < now:
        return HTMLResponse(content=_get_error_page("Link Expired", "This action link has expired. Please log in to NETRA to take action."), status_code=400)
    
    # Execute the action
    record_type = token_doc["record_type"]
    record_id = token_doc["record_id"]
    action = token_doc["action"]
    
    success = False
    message = ""
    
    if record_type == "leave_request":
        if action == "approve":
            result = await db.leave_requests.update_one(
                {"id": record_id},
                {"$set": {"status": "approved", "approved_at": datetime.now(timezone.utc), "approved_via": "email"}}
            )
            success = result.modified_count > 0
            message = "Leave request has been approved!"
        elif action == "reject":
            result = await db.leave_requests.update_one(
                {"id": record_id},
                {"$set": {"status": "rejected", "rejected_at": datetime.now(timezone.utc), "rejected_via": "email"}}
            )
            success = result.modified_count > 0
            message = "Leave request has been rejected."
    
    elif record_type == "expense":
        if action == "approve":
            result = await db.expenses.update_one(
                {"id": record_id},
                {"$set": {"status": "approved", "approved_at": datetime.now(timezone.utc), "approved_via": "email"}}
            )
            success = result.modified_count > 0
            message = "Expense has been approved!"
        elif action == "reject":
            result = await db.expenses.update_one(
                {"id": record_id},
                {"$set": {"status": "rejected", "rejected_at": datetime.now(timezone.utc), "rejected_via": "email"}}
            )
            success = result.modified_count > 0
            message = "Expense has been rejected."
    
    elif record_type == "kickoff":
        if action == "approve":
            result = await db.kickoff_requests.update_one(
                {"id": record_id},
                {"$set": {"status": "approved", "approved_at": datetime.now(timezone.utc), "approved_via": "email"}}
            )
            success = result.modified_count > 0
            message = "Kickoff request has been approved!"
    
    elif record_type == "go_live":
        if action == "approve":
            # Update employee status
            result = await db.employees.update_one(
                {"id": record_id},
                {"$set": {"status": "active", "go_live_approved_at": datetime.now(timezone.utc), "go_live_approved_via": "email"}}
            )
            success = result.modified_count > 0
            message = "Go-Live has been approved! Employee is now active."
    
    # Mark token as used
    await db.email_action_tokens.update_one(
        {"token": token},
        {"$set": {"used": True, "used_at": datetime.now(timezone.utc)}}
    )
    
    if success:
        return HTMLResponse(content=_get_success_page(action.title(), message), status_code=200)
    else:
        return HTMLResponse(content=_get_error_page("Action Failed", "Could not complete the action. The record may have already been processed."), status_code=400)


@router.put("/config")
async def update_email_config(
    config: EmailConfig,
    db=Depends(get_db)
):
    """Update email header and footer HTML"""
    await db.email_settings.update_one(
        {"type": "email_template_config"},
        {"$set": {
            "header_html": config.header_html,
            "footer_html": config.footer_html,
            "updated_at": datetime.now(timezone.utc)
        }},
        upsert=True
    )
    return {"status": "updated"}


@router.get("/config")
async def get_email_config_endpoint(db=Depends(get_db)):
    """Get current email configuration"""
    config = await db.email_settings.find_one({"type": "email_template_config"})
    if config and "_id" in config:
        del config["_id"]
    return config or {"header_html": None, "footer_html": None}


@router.get("/logs")
async def get_email_logs(
    limit: int = Query(50, le=200),
    record_type: Optional[str] = None,
    db=Depends(get_db)
):
    """Get email send logs"""
    query = {}
    if record_type:
        query["record_type"] = record_type
    
    logs = await db.email_logs.find(query).sort("sent_at", -1).limit(limit).to_list(limit)
    
    result = []
    for log in logs:
        if "_id" in log:
            del log["_id"]
        result.append(log)
    
    return result


# ==================== HTML PAGES ====================

def _get_success_page(action: str, message: str) -> str:
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Action Completed - NETRA</title>
        <style>
            body {{ font-family: 'Segoe UI', sans-serif; margin: 0; padding: 40px; background: #f5f5f5; text-align: center; }}
            .card {{ max-width: 500px; margin: 0 auto; background: white; border-radius: 12px; padding: 40px; box-shadow: 0 4px 20px rgba(0,0,0,0.1); }}
            .icon {{ font-size: 64px; margin-bottom: 20px; }}
            h1 {{ color: #22c55e; margin: 0 0 15px 0; }}
            p {{ color: #666; font-size: 16px; }}
            .btn {{ display: inline-block; margin-top: 25px; padding: 12px 30px; background: #1f2937; color: white; text-decoration: none; border-radius: 6px; }}
        </style>
    </head>
    <body>
        <div class="card">
            <div class="icon">✅</div>
            <h1>{action} Successful!</h1>
            <p>{message}</p>
            <a href="/" class="btn">Go to NETRA</a>
        </div>
    </body>
    </html>
    """


def _get_error_page(title: str, message: str) -> str:
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{title} - NETRA</title>
        <style>
            body {{ font-family: 'Segoe UI', sans-serif; margin: 0; padding: 40px; background: #f5f5f5; text-align: center; }}
            .card {{ max-width: 500px; margin: 0 auto; background: white; border-radius: 12px; padding: 40px; box-shadow: 0 4px 20px rgba(0,0,0,0.1); }}
            .icon {{ font-size: 64px; margin-bottom: 20px; }}
            h1 {{ color: #ef4444; margin: 0 0 15px 0; }}
            p {{ color: #666; font-size: 16px; }}
            .btn {{ display: inline-block; margin-top: 25px; padding: 12px 30px; background: #1f2937; color: white; text-decoration: none; border-radius: 6px; }}
        </style>
    </head>
    <body>
        <div class="card">
            <div class="icon">⚠️</div>
            <h1>{title}</h1>
            <p>{message}</p>
            <a href="/" class="btn">Go to NETRA</a>
        </div>
    </body>
    </html>
    """
