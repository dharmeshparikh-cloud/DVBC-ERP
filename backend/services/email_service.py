"""
Email Service - Send transactional emails via Google Workspace SMTP
"""

import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import os
from pathlib import Path
from typing import Optional
import logging

# Load environment variables
from dotenv import load_dotenv
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

logger = logging.getLogger(__name__)

# Email configuration from environment
SMTP_HOST = os.environ.get('SMTP_HOST', 'smtp.gmail.com')
SMTP_PORT = int(os.environ.get('SMTP_PORT', '587'))
SMTP_USER = os.environ.get('SMTP_USER', '')  # myhr@dvconsulting.co.in
SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD', '')  # App password
SENDER_NAME = os.environ.get('SENDER_NAME', 'DVBC HR')

# Debug log
logger.info(f"Email service initialized - SMTP_USER: {SMTP_USER}, SMTP configured: {bool(SMTP_USER and SMTP_PASSWORD)}")


async def send_email(
    to_email: str,
    subject: str,
    html_content: str,
    plain_content: Optional[str] = None,
    reply_to: Optional[str] = None,
    attachment_path: Optional[str] = None,
    attachment_name: Optional[str] = None
) -> dict:
    """
    Send an email via SMTP.
    
    Args:
        to_email: Recipient email address
        subject: Email subject
        html_content: HTML body content
        plain_content: Plain text alternative (optional)
        reply_to: Reply-to address (optional)
        attachment_path: Path to attachment file (optional)
        attachment_name: Name for the attachment (optional)
    
    Returns:
        dict with status and message
    """
    
    # Check if SMTP is configured
    if not SMTP_USER or not SMTP_PASSWORD:
        logger.warning("SMTP not configured - email not sent")
        return {
            "status": "skipped",
            "message": "Email service not configured. Email queued for later delivery.",
            "to": to_email,
            "subject": subject
        }
    
    try:
        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = f"{SENDER_NAME} <{SMTP_USER}>"
        msg['To'] = to_email
        
        if reply_to:
            msg['Reply-To'] = reply_to
        
        # Add plain text part
        if plain_content:
            part1 = MIMEText(plain_content, 'plain', 'utf-8')
            msg.attach(part1)
        
        # Add HTML part
        part2 = MIMEText(html_content, 'html', 'utf-8')
        msg.attach(part2)
        
        # Add attachment if provided
        if attachment_path and os.path.exists(attachment_path):
            with open(attachment_path, 'rb') as f:
                attachment = MIMEBase('application', 'octet-stream')
                attachment.set_payload(f.read())
                encoders.encode_base64(attachment)
                attachment.add_header(
                    'Content-Disposition',
                    f'attachment; filename="{attachment_name or os.path.basename(attachment_path)}"'
                )
                msg.attach(attachment)
        
        # Send email
        await aiosmtplib.send(
            msg,
            hostname=SMTP_HOST,
            port=SMTP_PORT,
            start_tls=True,
            username=SMTP_USER,
            password=SMTP_PASSWORD
        )
        
        logger.info(f"Email sent successfully to {to_email}")
        return {
            "status": "sent",
            "message": "Email sent successfully",
            "to": to_email,
            "subject": subject
        }
        
    except aiosmtplib.SMTPAuthenticationError as e:
        logger.error(f"SMTP Authentication failed: {e}")
        return {
            "status": "error",
            "message": "Email authentication failed. Please check SMTP credentials.",
            "error": str(e)
        }
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        return {
            "status": "error",
            "message": f"Failed to send email: {str(e)}",
            "error": str(e)
        }


async def send_offer_letter_email(
    to_email: str,
    candidate_name: str,
    designation: str,
    department: str,
    acceptance_link: str,
    letter_html: str
) -> dict:
    """Send offer letter email with embedded content and acceptance link."""
    
    subject = f"Offer of Employment - {designation} at D&V Business Consulting"
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 700px; margin: 0 auto; padding: 20px; }}
            .header {{ text-align: center; padding: 20px 0; border-bottom: 3px solid #f97316; }}
            .logo {{ font-size: 24px; font-weight: bold; }}
            .logo span {{ color: #f97316; }}
            .content {{ padding: 30px 0; }}
            .cta-button {{ 
                display: inline-block; 
                background: #16a34a; 
                color: white !important; 
                padding: 15px 30px; 
                text-decoration: none; 
                border-radius: 8px; 
                font-weight: bold;
                margin: 20px 0;
            }}
            .cta-button:hover {{ background: #15803d; }}
            .footer {{ 
                text-align: center; 
                padding: 20px 0; 
                border-top: 1px solid #eee; 
                font-size: 12px; 
                color: #666; 
            }}
            .letter-preview {{
                background: #f9fafb;
                border: 1px solid #e5e7eb;
                border-radius: 8px;
                padding: 20px;
                margin: 20px 0;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div class="logo"><span>D&V</span> Business Consulting</div>
                <p style="margin: 5px 0; font-size: 14px; color: #666;">Human Resources Department</p>
            </div>
            
            <div class="content">
                <p>Dear <strong>{candidate_name}</strong>,</p>
                
                <p>We are pleased to extend an offer of employment for the position of 
                <strong>{designation}</strong> in our <strong>{department}</strong> department.</p>
                
                <p>Please review the offer letter below and click the button to accept:</p>
                
                <div class="letter-preview">
                    {letter_html}
                </div>
                
                <div style="text-align: center;">
                    <a href="{acceptance_link}" class="cta-button">
                        View & Accept Offer Letter
                    </a>
                </div>
                
                <p style="font-size: 14px; color: #666;">
                    If you have any questions, please don't hesitate to contact us at 
                    <a href="mailto:{SMTP_USER}">{SMTP_USER}</a>
                </p>
                
                <p>We look forward to welcoming you to the team!</p>
                
                <p>Best regards,<br>
                <strong>HR Team</strong><br>
                D&V Business Consulting Pvt. Ltd.</p>
            </div>
            
            <div class="footer">
                <p>D&V Business Consulting Pvt. Ltd.</p>
                <p>This is an automated message. Please do not reply directly to this email.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    plain_content = f"""
    Dear {candidate_name},
    
    We are pleased to extend an offer of employment for the position of {designation} 
    in our {department} department.
    
    Please click the link below to view and accept your offer letter:
    {acceptance_link}
    
    If you have any questions, please contact us at {SMTP_USER}
    
    Best regards,
    HR Team
    D&V Business Consulting Pvt. Ltd.
    """
    
    return await send_email(to_email, subject, html_content, plain_content)


async def send_appointment_letter_email(
    to_email: str,
    employee_name: str,
    employee_id: str,
    acceptance_link: str,
    letter_html: str
) -> dict:
    """Send appointment letter email with embedded content and acceptance link."""
    
    subject = f"Appointment Letter - {employee_id} | D&V Business Consulting"
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 700px; margin: 0 auto; padding: 20px; }}
            .header {{ text-align: center; padding: 20px 0; border-bottom: 3px solid #f97316; }}
            .logo {{ font-size: 24px; font-weight: bold; }}
            .logo span {{ color: #f97316; }}
            .content {{ padding: 30px 0; }}
            .cta-button {{ 
                display: inline-block; 
                background: #2563eb; 
                color: white !important; 
                padding: 15px 30px; 
                text-decoration: none; 
                border-radius: 8px; 
                font-weight: bold;
                margin: 20px 0;
            }}
            .footer {{ 
                text-align: center; 
                padding: 20px 0; 
                border-top: 1px solid #eee; 
                font-size: 12px; 
                color: #666; 
            }}
            .letter-preview {{
                background: #f9fafb;
                border: 1px solid #e5e7eb;
                border-radius: 8px;
                padding: 20px;
                margin: 20px 0;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div class="logo"><span>D&V</span> Business Consulting</div>
                <p style="margin: 5px 0; font-size: 14px; color: #666;">Human Resources Department</p>
            </div>
            
            <div class="content">
                <p>Dear <strong>{employee_name}</strong>,</p>
                
                <p>Congratulations! Your Employee ID is <strong>{employee_id}</strong>.</p>
                
                <p>Please find your appointment letter below. Click the button to acknowledge receipt:</p>
                
                <div class="letter-preview">
                    {letter_html}
                </div>
                
                <div style="text-align: center;">
                    <a href="{acceptance_link}" class="cta-button">
                        View & Acknowledge Appointment Letter
                    </a>
                </div>
                
                <p>Welcome to the D&V family!</p>
                
                <p>Best regards,<br>
                <strong>HR Team</strong><br>
                D&V Business Consulting Pvt. Ltd.</p>
            </div>
            
            <div class="footer">
                <p>D&V Business Consulting Pvt. Ltd.</p>
                <p>This is an automated message. Please do not reply directly to this email.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    plain_content = f"""
    Dear {employee_name},
    
    Congratulations! Your Employee ID is {employee_id}.
    
    Please click the link below to view and acknowledge your appointment letter:
    {acceptance_link}
    
    Welcome to the D&V family!
    
    Best regards,
    HR Team
    D&V Business Consulting Pvt. Ltd.
    """
    
    return await send_email(to_email, subject, html_content, plain_content)


async def send_acceptance_confirmation_email(
    to_email: str,
    recipient_name: str,
    letter_type: str,  # "offer" or "appointment"
    employee_id: Optional[str] = None
) -> dict:
    """Send confirmation email after letter acceptance."""
    
    if letter_type == "offer":
        subject = f"Offer Accepted - Welcome to D&V Business Consulting!"
        message = f"""
        <p>Dear <strong>{recipient_name}</strong>,</p>
        <p>Thank you for accepting our offer of employment!</p>
        <p>Your Employee ID is: <strong>{employee_id}</strong></p>
        <p>Our HR team will be in touch with you shortly regarding the next steps, 
        including your appointment letter and onboarding details.</p>
        """
    else:
        subject = f"Appointment Letter Acknowledged - {employee_id}"
        message = f"""
        <p>Dear <strong>{recipient_name}</strong>,</p>
        <p>Thank you for acknowledging your appointment letter.</p>
        <p>Your Employee ID: <strong>{employee_id}</strong></p>
        <p>We look forward to seeing you on your joining date. 
        Please contact HR if you have any questions.</p>
        """
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ text-align: center; padding: 20px 0; }}
            .success-icon {{ font-size: 48px; color: #16a34a; }}
            .footer {{ text-align: center; padding: 20px 0; font-size: 12px; color: #666; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div class="success-icon">✓</div>
                <h2 style="color: #16a34a;">Confirmation</h2>
            </div>
            {message}
            <p>Best regards,<br>HR Team<br>D&V Business Consulting Pvt. Ltd.</p>
            <div class="footer">
                <p>© D&V Business Consulting Pvt. Ltd.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return await send_email(to_email, subject, html_content)



# ==================== ONBOARDING EMAIL TEMPLATES ====================

# Company logo URL
COMPANY_LOGO_URL = "https://customer-assets.emergentagent.com/job_30a69dc1-a599-4a88-9d0e-e1c06b1b2008/artifacts/tbs0jexj_1001419196.png"

async def send_onboarding_invite_email(
    to_email: str,
    candidate_name: str,
    offered_position: str,
    onboarding_link: str,
    expires_at: str,
    hr_name: str = "HR Team"
) -> dict:
    """Send onboarding invite email to candidate with secure link."""
    
    subject = f"Complete Your Onboarding - {offered_position}"
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: 'Segoe UI', Arial, sans-serif; line-height: 1.6; color: #1f2937; margin: 0; padding: 0; background: #f3f4f6; }}
            .container {{ max-width: 600px; margin: 0 auto; background: white; }}
            .header {{ background: #ffffff; padding: 40px 30px; text-align: center; border-bottom: 3px solid #f97316; }}
            .logo {{ max-height: 80px; width: auto; }}
            .content {{ padding: 40px 30px; }}
            .highlight {{ background: #fef3c7; border-left: 4px solid #f59e0b; padding: 15px 20px; margin: 20px 0; border-radius: 0 8px 8px 0; }}
            .position {{ font-size: 18px; font-weight: 600; color: #f97316; }}
            .cta-button {{ 
                display: inline-block; 
                background: linear-gradient(135deg, #16a34a 0%, #15803d 100%); 
                color: white !important; 
                padding: 16px 40px; 
                text-decoration: none; 
                border-radius: 8px; 
                font-weight: bold;
                font-size: 16px;
                margin: 25px 0;
                box-shadow: 0 4px 14px 0 rgba(22, 163, 74, 0.4);
            }}
            .steps {{ background: #f9fafb; border-radius: 12px; padding: 25px; margin: 25px 0; }}
            .step {{ display: flex; align-items: flex-start; margin-bottom: 15px; }}
            .step-number {{ 
                background: #0f172a; 
                color: white; 
                width: 28px; 
                height: 28px; 
                border-radius: 50%; 
                display: flex; 
                align-items: center; 
                justify-content: center; 
                font-weight: bold; 
                font-size: 14px;
                margin-right: 15px;
                flex-shrink: 0;
            }}
            .step-text {{ color: #4b5563; }}
            .expiry {{ color: #dc2626; font-weight: 500; }}
            .footer {{ 
                background: #f9fafb; 
                padding: 25px 30px; 
                text-align: center; 
                font-size: 13px; 
                color: #6b7280; 
                border-top: 1px solid #e5e7eb;
            }}
            .help-text {{ font-size: 14px; color: #6b7280; margin-top: 20px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <img src="{COMPANY_LOGO_URL}" alt="D&V Business Consulting" class="logo" />
            </div>
            
            <div class="content">
                <p>Dear <strong>{candidate_name}</strong>,</p>
                
                <p>Congratulations! We are excited to welcome you as a <span class="position">{offered_position}</span>.</p>
                
                <div class="highlight">
                    <p style="margin: 0;"><strong>Next Step:</strong> Please complete your onboarding details using the secure link below.</p>
                </div>
                
                <div style="text-align: center;">
                    <a href="{onboarding_link}" class="cta-button">Complete Your Onboarding</a>
                </div>
                
                <div class="steps">
                    <h3 style="margin-top: 0; color: #1f2937;">What to Prepare:</h3>
                    <div class="step">
                        <span class="step-number">1</span>
                        <span class="step-text">Personal details (Date of birth, address, emergency contact)</span>
                    </div>
                    <div class="step">
                        <span class="step-number">2</span>
                        <span class="step-text">Educational qualifications</span>
                    </div>
                    <div class="step">
                        <span class="step-number">3</span>
                        <span class="step-text">Previous employment history (if applicable)</span>
                    </div>
                    <div class="step">
                        <span class="step-number">4</span>
                        <span class="step-text">Bank account details for salary processing</span>
                    </div>
                    <div class="step">
                        <span class="step-number">5</span>
                        <span class="step-text">Scanned copies of PAN Card, Aadhaar, and other documents</span>
                    </div>
                </div>
                
                <p class="expiry">⏰ This link expires on <strong>{expires_at}</strong>. Please complete your submission before then.</p>
                
                <p class="help-text">If you have any questions or face any issues, please contact our HR team.</p>
                
                <p style="margin-top: 30px;">
                    Best regards,<br>
                    <strong>{hr_name}</strong>
                </p>
            </div>
            
            <div class="footer">
                <p>© All Rights Reserved with D&V Business Consulting Pvt. Ltd.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    plain_content = f"""
Dear {candidate_name},

Congratulations! We are excited to welcome you as a {offered_position}.

Please complete your onboarding details using this link:
{onboarding_link}

What to prepare:
1. Personal details (Date of birth, address, emergency contact)
2. Educational qualifications
3. Previous employment history (if applicable)
4. Bank account details for salary processing
5. Scanned copies of PAN Card, Aadhaar, and other documents

This link expires on {expires_at}. Please complete your submission before then.

Best regards,
{hr_name}

© All Rights Reserved with D&V Business Consulting Pvt. Ltd.
    """
    
    return await send_email(to_email, subject, html_content, plain_content)


async def send_onboarding_submission_notification_email(
    to_email: str,
    hr_name: str,
    candidate_name: str,
    offered_position: str,
    review_link: str
) -> dict:
    """Send notification to HR when candidate submits their onboarding form."""
    
    subject = f"New Onboarding Submission - {candidate_name} ({offered_position})"
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; background: #f3f4f6; }}
            .container {{ max-width: 600px; margin: 0 auto; background: white; }}
            .header {{ background: #ffffff; padding: 30px; text-align: center; border-bottom: 3px solid #f97316; }}
            .logo {{ max-height: 70px; width: auto; }}
            .content {{ padding: 30px; }}
            .info-box {{ background: #f9fafb; padding: 20px; border-radius: 8px; margin: 20px 0; border: 1px solid #e5e7eb; }}
            .cta-button {{ 
                display: inline-block; 
                background: #f97316; 
                color: white !important; 
                padding: 12px 30px; 
                text-decoration: none; 
                border-radius: 6px; 
                font-weight: bold;
            }}
            .footer {{ background: #f9fafb; padding: 20px; text-align: center; font-size: 12px; color: #6b7280; border-top: 1px solid #e5e7eb; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <img src="{COMPANY_LOGO_URL}" alt="D&V Business Consulting" class="logo" />
            </div>
            <div class="content">
                <h2 style="color: #f97316; margin-top: 0;">New Onboarding Submission</h2>
                
                <p>Hi {hr_name},</p>
                
                <p>A candidate has submitted their onboarding details and is awaiting your review.</p>
                
                <div class="info-box">
                    <p style="margin: 5px 0;"><strong>Candidate:</strong> {candidate_name}</p>
                    <p style="margin: 5px 0;"><strong>Position:</strong> {offered_position}</p>
                    <p style="margin: 5px 0;"><strong>Status:</strong> Pending Review</p>
                </div>
                
                <p style="text-align: center; margin: 30px 0;">
                    <a href="{review_link}" class="cta-button">Review Submission</a>
                </p>
            </div>
            <div class="footer">
                <p>© All Rights Reserved with D&V Business Consulting Pvt. Ltd.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return await send_email(to_email, subject, html_content)


async def send_onboarding_revision_request_email(
    to_email: str,
    candidate_name: str,
    offered_position: str,
    revision_reason: str,
    onboarding_link: str,
    hr_name: str = "HR Team"
) -> dict:
    """Send email to candidate when HR requests revision of their submission."""
    
    subject = f"Action Required - Please Update Your Onboarding Details"
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; background: #f3f4f6; }}
            .container {{ max-width: 600px; margin: 0 auto; background: white; }}
            .header {{ background: #ffffff; padding: 30px; text-align: center; border-bottom: 3px solid #f59e0b; }}
            .logo {{ max-height: 70px; width: auto; }}
            .content {{ padding: 30px; }}
            .alert-banner {{ background: #fef3c7; padding: 15px 20px; text-align: center; border-bottom: 1px solid #fcd34d; }}
            .reason-box {{ background: #fef3c7; border-left: 4px solid #f59e0b; padding: 15px 20px; margin: 20px 0; border-radius: 0 8px 8px 0; }}
            .cta-button {{ 
                display: inline-block; 
                background: #16a34a; 
                color: white !important; 
                padding: 14px 35px; 
                text-decoration: none; 
                border-radius: 6px; 
                font-weight: bold;
            }}
            .footer {{ background: #f9fafb; padding: 20px; text-align: center; font-size: 12px; color: #6b7280; border-top: 1px solid #e5e7eb; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <img src="{COMPANY_LOGO_URL}" alt="D&V Business Consulting" class="logo" />
            </div>
            <div class="alert-banner">
                <strong>⚠️ Revision Requested</strong>
            </div>
            <div class="content">
                <p>Dear <strong>{candidate_name}</strong>,</p>
                
                <p>Our HR team has reviewed your onboarding submission for the <strong>{offered_position}</strong> position and requires some updates.</p>
                
                <div class="reason-box">
                    <p style="margin: 0;"><strong>Reason:</strong></p>
                    <p style="margin: 10px 0 0 0;">{revision_reason}</p>
                </div>
                
                <p>Please update your details using the link below:</p>
                
                <p style="text-align: center; margin: 30px 0;">
                    <a href="{onboarding_link}" class="cta-button">Update My Details</a>
                </p>
                
                <p>If you have any questions, please contact our HR team.</p>
                
                <p>Best regards,<br><strong>{hr_name}</strong></p>
            </div>
            <div class="footer">
                <p>© All Rights Reserved with D&V Business Consulting Pvt. Ltd.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return await send_email(to_email, subject, html_content)


async def send_onboarding_complete_email(
    to_email: str,
    candidate_name: str,
    employee_id: str,
    designation: str,
    department: str,
    joining_date: str,
    official_email: str,
    reporting_manager: str
) -> dict:
    """Send email to new employee when onboarding is complete."""
    
    subject = f"Welcome Aboard! Your Employee ID: {employee_id}"
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: 'Segoe UI', Arial, sans-serif; line-height: 1.6; color: #1f2937; margin: 0; padding: 0; background: #f3f4f6; }}
            .container {{ max-width: 600px; margin: 0 auto; background: white; }}
            .header {{ background: linear-gradient(135deg, #16a34a 0%, #15803d 100%); padding: 40px 30px; text-align: center; }}
            .header h1 {{ color: white; margin: 0; font-size: 28px; }}
            .header p {{ color: #bbf7d0; margin-top: 10px; }}
            .content {{ padding: 40px 30px; }}
            .employee-card {{ background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); color: white; padding: 30px; border-radius: 12px; margin: 20px 0; }}
            .employee-id {{ font-size: 32px; font-weight: bold; color: #f97316; letter-spacing: 2px; }}
            .details-grid {{ display: grid; gap: 15px; margin-top: 20px; }}
            .detail-item {{ display: flex; justify-content: space-between; border-bottom: 1px solid #334155; padding-bottom: 10px; }}
            .detail-label {{ color: #94a3b8; }}
            .detail-value {{ font-weight: 600; }}
            .next-steps {{ background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 8px; padding: 20px; margin: 25px 0; }}
            .footer {{ background: #f9fafb; padding: 25px 30px; text-align: center; font-size: 13px; color: #6b7280; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🎉 Welcome to the Team!</h1>
                <p>Your onboarding is complete</p>
            </div>
            
            <div class="content">
                <p>Dear <strong>{candidate_name}</strong>,</p>
                
                <p>We're thrilled to officially welcome you to D&V Business Consulting! Your onboarding process is now complete.</p>
                
                <div class="employee-card">
                    <p style="margin: 0; color: #94a3b8; font-size: 13px;">YOUR EMPLOYEE ID</p>
                    <p class="employee-id">{employee_id}</p>
                    
                    <div class="details-grid">
                        <div class="detail-item">
                            <span class="detail-label">Designation</span>
                            <span class="detail-value">{designation}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">Department</span>
                            <span class="detail-value">{department}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">Joining Date</span>
                            <span class="detail-value">{joining_date}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">Official Email</span>
                            <span class="detail-value">{official_email}</span>
                        </div>
                        <div class="detail-item" style="border: none;">
                            <span class="detail-label">Reporting Manager</span>
                            <span class="detail-value">{reporting_manager}</span>
                        </div>
                    </div>
                </div>
                
                <div class="next-steps">
                    <h3 style="margin-top: 0; color: #16a34a;">📋 Next Steps:</h3>
                    <ul style="margin: 0; padding-left: 20px; color: #4b5563;">
                        <li>You will receive your official email credentials shortly</li>
                        <li>Report to your manager on your joining date</li>
                        <li>Complete any remaining documentation on Day 1</li>
                        <li>HR will guide you through the "Go-Live" process</li>
                    </ul>
                </div>
                
                <p>If you have any questions before your start date, feel free to reach out to our HR team.</p>
                
                <p>We're excited to have you on board!</p>
                
                <p style="margin-top: 30px;">
                    Best regards,<br>
                    <strong>HR Team</strong><br>
                    D&V Business Consulting Pvt. Ltd.
                </p>
            </div>
            
            <div class="footer">
                <p>This email was sent from NETRA HR Management System.</p>
                <p>© D&V Business Consulting Pvt. Ltd. | All Rights Reserved</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return await send_email(to_email, subject, html_content)
