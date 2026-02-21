"""
Documentation Router - Generate and email ERP documentation
"""
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import FileResponse
from datetime import datetime, timezone
from typing import Optional
import os
import uuid
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication

from .deps import get_db
from .auth import get_current_user
from .models import User

router = APIRouter(prefix="/documentation", tags=["Documentation"])


def get_smtp_config():
    """Get SMTP configuration from environment"""
    return {
        "host": os.environ.get("SMTP_HOST", "smtp.gmail.com"),
        "port": int(os.environ.get("SMTP_PORT", "587")),
        "user": os.environ.get("SMTP_USER"),
        "password": os.environ.get("SMTP_PASSWORD"),
        "sender_name": os.environ.get("SENDER_NAME", "DVBC NETRA")
    }


async def send_documentation_email(
    recipient_email: str,
    recipient_name: str,
    pdf_path: str,
    docx_path: str,
    module_name: str = "HR Module"
):
    """Send documentation files via email"""
    config = get_smtp_config()
    
    if not config["user"] or not config["password"]:
        raise Exception("SMTP credentials not configured")
    
    msg = MIMEMultipart()
    msg["Subject"] = f"NETRA ERP - {module_name} Documentation"
    msg["From"] = f"{config['sender_name']} <{config['user']}>"
    msg["To"] = recipient_email
    
    # Email body
    body = f"""
    <html>
    <body style="font-family: 'Segoe UI', Arial, sans-serif; padding: 20px;">
        <div style="max-width: 600px; margin: 0 auto;">
            <div style="background: linear-gradient(135deg, #1f2937 0%, #374151 100%); padding: 30px; text-align: center; border-radius: 8px 8px 0 0;">
                <h1 style="color: white; margin: 0;">NETRA ERP</h1>
                <p style="color: #9ca3af; margin: 5px 0 0 0;">Documentation Pack</p>
            </div>
            
            <div style="padding: 30px; background: #f9fafb; border: 1px solid #e5e7eb; border-top: none; border-radius: 0 0 8px 8px;">
                <p>Dear {recipient_name},</p>
                
                <p>Please find attached the complete <strong>{module_name} Documentation</strong> for NETRA ERP.</p>
                
                <p>The documentation pack includes:</p>
                <ul>
                    <li><strong>PDF Version</strong> - For easy reading and printing</li>
                    <li><strong>DOCX Version</strong> - For editing and customization</li>
                </ul>
                
                <p>Documentation Contents:</p>
                <ol>
                    <li>System Overview</li>
                    <li>Business Logic Documentation</li>
                    <li>Role-Based Access & Permissions</li>
                    <li>End-to-End Workflow Maps</li>
                    <li>Configuration Guide (Admin Manual)</li>
                    <li>Standard Operating Procedures (SOPs)</li>
                    <li>Training Manual</li>
                    <li>Troubleshooting Guide</li>
                    <li>Audit & Compliance Controls</li>
                    <li>Quick Start Guide</li>
                </ol>
                
                <p style="margin-top: 20px;">If you have any questions about the documentation, please contact your system administrator.</p>
                
                <p>Best regards,<br>
                <strong>NETRA ERP System</strong></p>
            </div>
            
            <div style="text-align: center; padding: 20px; color: #6b7280; font-size: 12px;">
                <p>This is an automated message from NETRA ERP.</p>
                <p>© {datetime.now().year} DVBC Consulting. All rights reserved.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    msg.attach(MIMEText(body, "html"))
    
    # Attach PDF
    if os.path.exists(pdf_path):
        with open(pdf_path, "rb") as f:
            pdf_attachment = MIMEApplication(f.read(), _subtype="pdf")
            pdf_attachment.add_header(
                "Content-Disposition", 
                "attachment", 
                filename=os.path.basename(pdf_path)
            )
            msg.attach(pdf_attachment)
    
    # Attach DOCX
    if os.path.exists(docx_path):
        with open(docx_path, "rb") as f:
            docx_attachment = MIMEApplication(
                f.read(), 
                _subtype="vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
            docx_attachment.add_header(
                "Content-Disposition", 
                "attachment", 
                filename=os.path.basename(docx_path)
            )
            msg.attach(docx_attachment)
    
    # Send email
    with smtplib.SMTP(config["host"], config["port"]) as server:
        server.starttls()
        server.login(config["user"], config["password"])
        server.sendmail(config["user"], recipient_email, msg.as_string())
    
    return True


@router.post("/generate-hr-docs")
async def generate_hr_documentation(
    background_tasks: BackgroundTasks,
    email_to: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """
    Generate HR Module documentation in PDF and DOCX formats.
    Optionally email to specified address.
    """
    db = get_db()
    
    # Only HR and Admin can generate documentation
    if current_user.role not in ["admin", "hr_manager", "hr_executive"]:
        raise HTTPException(status_code=403, detail="Only HR/Admin can generate documentation")
    
    try:
        # Import the generator
        from services.documentation_generator import generate_hr_documentation
        
        # Generate documents
        result = generate_hr_documentation("/tmp")
        
        # Log the generation
        log_entry = {
            "id": str(uuid.uuid4()),
            "type": "hr_module_documentation",
            "generated_by": current_user.id,
            "generated_by_name": current_user.full_name,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "pdf_path": result["pdf_path"],
            "docx_path": result["docx_path"],
            "emailed_to": email_to
        }
        await db.documentation_logs.insert_one(log_entry)
        
        # Send email if requested
        email_status = "not_requested"
        if email_to:
            try:
                await send_documentation_email(
                    recipient_email=email_to,
                    recipient_name=current_user.full_name,
                    pdf_path=result["pdf_path"],
                    docx_path=result["docx_path"],
                    module_name="HR Module"
                )
                email_status = "sent"
            except Exception as e:
                email_status = f"failed: {str(e)}"
        
        return {
            "status": "success",
            "message": "HR Module documentation generated successfully",
            "pdf_download_url": f"/api/documentation/download/pdf/{os.path.basename(result['pdf_path'])}",
            "docx_download_url": f"/api/documentation/download/docx/{os.path.basename(result['docx_path'])}",
            "email_status": email_status,
            "generated_at": result["generated_at"]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Documentation generation failed: {str(e)}")


@router.get("/download/pdf/{filename}")
async def download_pdf(filename: str, current_user: User = Depends(get_current_user)):
    """Download generated PDF documentation"""
    file_path = f"/tmp/{filename}"
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found. Please regenerate documentation.")
    
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="application/pdf"
    )


@router.get("/download/docx/{filename}")
async def download_docx(filename: str, current_user: User = Depends(get_current_user)):
    """Download generated DOCX documentation"""
    file_path = f"/tmp/{filename}"
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found. Please regenerate documentation.")
    
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )


@router.get("/logs")
async def get_documentation_logs(current_user: User = Depends(get_current_user)):
    """Get documentation generation logs"""
    db = get_db()
    
    if current_user.role not in ["admin", "hr_manager"]:
        raise HTTPException(status_code=403, detail="Only Admin/HR Manager can view logs")
    
    logs = await db.documentation_logs.find(
        {},
        {"_id": 0}
    ).sort("generated_at", -1).to_list(50)
    
    return {"logs": logs}
