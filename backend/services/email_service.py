"""
Email Service - Send transactional emails via Google Workspace SMTP
"""

import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import os
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# Email configuration from environment
SMTP_HOST = os.environ.get('SMTP_HOST', 'smtp.gmail.com')
SMTP_PORT = int(os.environ.get('SMTP_PORT', '587'))
SMTP_USER = os.environ.get('SMTP_USER', '')  # myhr@dvconsulting.co.in
SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD', '')  # App password
SENDER_NAME = os.environ.get('SENDER_NAME', 'DVBC HR')


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
