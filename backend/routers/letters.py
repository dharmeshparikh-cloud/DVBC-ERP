"""
Letter Management Router - Offer Letters, Appointment Letters, Templates with Approval Workflow
"""

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, EmailStr
import uuid
import base64
import os

from .models import User
from .deps import get_db, sanitize_text, HR_ROLES, HR_ADMIN_ROLES
from .auth import get_current_user

# Import email service
try:
    import sys
    import os
    # Add parent directory to path for services import
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from services.email_service import send_offer_letter_email, send_appointment_letter_email, send_acceptance_confirmation_email
    EMAIL_SERVICE_AVAILABLE = True
except ImportError as e:
    print(f"Email service not available: {e}")
    EMAIL_SERVICE_AVAILABLE = False

router = APIRouter(prefix="/letters", tags=["Letter Management"])

# Base URL for acceptance links
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'http://localhost:3000').replace('/api', '')


# ============== Letterhead Settings Model ==============

class LetterheadSettings(BaseModel):
    """Letterhead header and footer settings."""
    header_image: Optional[str] = None  # Base64 encoded image
    footer_image: Optional[str] = None  # Base64 encoded image
    company_name: Optional[str] = "D&V Business Consulting Pvt. Ltd."
    company_address: Optional[str] = None
    company_phone: Optional[str] = None
    company_email: Optional[str] = None
    company_cin: Optional[str] = None


# ============== Pydantic Models ==============

class LetterTemplateCreate(BaseModel):
    """Create a new letter template."""
    template_type: str  # "offer_letter" or "appointment_letter"
    name: str
    subject: str
    body_content: str  # HTML content with placeholders like {{employee_name}}, {{designation}}, etc.
    is_default: bool = False


class LetterTemplateUpdate(BaseModel):
    """Update a letter template."""
    name: Optional[str] = None
    subject: Optional[str] = None
    body_content: Optional[str] = None
    is_default: Optional[bool] = None


class OfferLetterCreate(BaseModel):
    """Create an offer letter for a candidate."""
    candidate_id: str  # Onboarding candidate ID
    template_id: str
    designation: str
    department: str
    joining_date: str
    salary_details: Dict[str, Any]  # CTC breakdown
    custom_fields: Optional[Dict[str, Any]] = None
    hr_signature_text: Optional[str] = None
    hr_signature_image: Optional[str] = None  # Base64 or URL


class AppointmentLetterCreate(BaseModel):
    """Create an appointment letter for an employee."""
    employee_id: str
    template_id: str
    custom_fields: Optional[Dict[str, Any]] = None
    hr_signature_text: Optional[str] = None
    hr_signature_image: Optional[str] = None


class LetterAcceptance(BaseModel):
    """Employee acceptance of a letter."""
    acceptance_token: str


# ============== Helper Functions ==============

async def get_next_employee_id(db):
    """Generate next employee ID in format EMP001, EMP002, etc."""
    # Find the highest existing employee ID by extracting and comparing numbers
    all_employees = await db.employees.find(
        {"employee_id": {"$regex": "^EMP\\d+$"}},  # Only match EMP followed by digits
        {"employee_id": 1}
    ).to_list(length=1000)
    
    max_num = 0
    for emp in all_employees:
        emp_id = emp.get("employee_id", "")
        try:
            # Extract number from EMP format (e.g., EMP001 -> 1, EMP1003 -> 1003)
            num = int(emp_id.replace("EMP", ""))
            if num > max_num:
                max_num = num
        except (ValueError, AttributeError):
            continue
    
    next_num = max_num + 1
    # Use 4 digits if we're past 999, otherwise 3 digits
    if next_num > 999:
        return f"EMP{next_num:04d}"
    return f"EMP{next_num:03d}"


async def create_notification(db, recipient_id: str, title: str, message: str, notification_type: str, reference_id: str = None):
    """Create a notification for a user."""
    notification = {
        "id": str(uuid.uuid4()),
        "type": notification_type,
        "recipient_id": recipient_id,
        "title": title,
        "message": message,
        "reference_id": reference_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "read": False,
        "clickable": True
    }
    await db.notifications.insert_one(notification)
    return notification


# ============== Letter Template Endpoints ==============

@router.post("/templates")
async def create_letter_template(
    template: LetterTemplateCreate,
    current_user: User = Depends(get_current_user)
):
    """Create a new letter template (Admin/HR Manager only)."""
    db = get_db()
    
    if current_user.role not in HR_ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Only Admin or HR Manager can create templates")
    
    if template.template_type not in ["offer_letter", "appointment_letter"]:
        raise HTTPException(status_code=400, detail="Invalid template type")
    
    # If setting as default, unset other defaults of same type
    if template.is_default:
        await db.letter_templates.update_many(
            {"template_type": template.template_type, "is_default": True},
            {"$set": {"is_default": False}}
        )
    
    template_doc = {
        "id": str(uuid.uuid4()),
        "template_type": template.template_type,
        "name": sanitize_text(template.name),
        "subject": sanitize_text(template.subject),
        "body_content": template.body_content,
        "is_default": template.is_default,
        "is_active": True,
        "created_by": current_user.id,
        "created_by_name": current_user.full_name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "version": 1,
        "history": []
    }
    
    await db.letter_templates.insert_one(template_doc)
    
    return {"message": "Template created successfully", "template_id": template_doc["id"]}


@router.get("/templates")
async def get_letter_templates(
    template_type: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get all letter templates."""
    db = get_db()
    
    if current_user.role not in HR_ROLES:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    query = {"is_active": True}
    if template_type:
        query["template_type"] = template_type
    
    templates = await db.letter_templates.find(query, {"_id": 0, "history": 0}).to_list(100)
    return templates


@router.get("/templates/{template_id}")
async def get_letter_template(
    template_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get a specific letter template with history."""
    db = get_db()
    
    if current_user.role not in HR_ROLES:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    template = await db.letter_templates.find_one({"id": template_id}, {"_id": 0})
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    return template


@router.put("/templates/{template_id}")
async def update_letter_template(
    template_id: str,
    update: LetterTemplateUpdate,
    current_user: User = Depends(get_current_user)
):
    """Update a letter template (saves history)."""
    db = get_db()
    
    if current_user.role not in HR_ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Only Admin or HR Manager can update templates")
    
    template = await db.letter_templates.find_one({"id": template_id}, {"_id": 0})
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    # Save current version to history
    history_entry = {
        "version": template["version"],
        "name": template["name"],
        "subject": template["subject"],
        "body_content": template["body_content"],
        "modified_by": current_user.id,
        "modified_by_name": current_user.full_name,
        "modified_at": datetime.now(timezone.utc).isoformat()
    }
    
    update_data = update.model_dump(exclude_unset=True)
    if "name" in update_data:
        update_data["name"] = sanitize_text(update_data["name"])
    if "subject" in update_data:
        update_data["subject"] = sanitize_text(update_data["subject"])
    
    # If setting as default, unset other defaults
    if update_data.get("is_default"):
        await db.letter_templates.update_many(
            {"template_type": template["template_type"], "is_default": True, "id": {"$ne": template_id}},
            {"$set": {"is_default": False}}
        )
    
    update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    update_data["version"] = template["version"] + 1
    
    await db.letter_templates.update_one(
        {"id": template_id},
        {
            "$set": update_data,
            "$push": {"history": history_entry}
        }
    )
    
    return {"message": "Template updated successfully", "version": update_data["version"]}


@router.delete("/templates/{template_id}")
async def delete_letter_template(
    template_id: str,
    current_user: User = Depends(get_current_user)
):
    """Soft delete a letter template."""
    db = get_db()
    
    if current_user.role not in HR_ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Only Admin or HR Manager can delete templates")
    
    result = await db.letter_templates.update_one(
        {"id": template_id},
        {"$set": {"is_active": False, "deleted_by": current_user.id, "deleted_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Template not found")
    
    return {"message": "Template deleted successfully"}


# ============== Offer Letter Endpoints ==============

@router.post("/offer-letters")
async def create_offer_letter(
    offer: OfferLetterCreate,
    current_user: User = Depends(get_current_user)
):
    """Create and send an offer letter to a candidate."""
    db = get_db()
    
    if current_user.role not in HR_ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Only Admin or HR Manager can create offer letters")
    
    # Verify candidate exists and is verified
    candidate = await db.onboarding_candidates.find_one({"id": offer.candidate_id}, {"_id": 0})
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    
    if not candidate.get("background_verified") or not candidate.get("documents_verified"):
        raise HTTPException(status_code=400, detail="Background verification and documents must be verified first")
    
    # Get template
    template = await db.letter_templates.find_one({"id": offer.template_id, "is_active": True}, {"_id": 0})
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    # Generate acceptance token
    acceptance_token = str(uuid.uuid4())
    
    offer_letter = {
        "id": str(uuid.uuid4()),
        "letter_type": "offer_letter",
        "candidate_id": offer.candidate_id,
        "candidate_name": f"{candidate.get('first_name', '')} {candidate.get('last_name', '')}".strip(),
        "candidate_email": candidate.get("email"),
        "template_id": offer.template_id,
        "template_name": template["name"],
        "designation": offer.designation,
        "department": offer.department,
        "joining_date": offer.joining_date,
        "salary_details": offer.salary_details,
        "custom_fields": offer.custom_fields or {},
        "hr_signature_text": offer.hr_signature_text,
        "hr_signature_image": offer.hr_signature_image,
        "status": "pending_acceptance",  # pending_acceptance, accepted, rejected, expired
        "acceptance_token": acceptance_token,
        "created_by": current_user.id,
        "created_by_name": current_user.full_name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "sent_at": datetime.now(timezone.utc).isoformat(),
        "accepted_at": None,
        "accepted_by_name": None,
        "employee_id_assigned": None
    }
    
    await db.offer_letters.insert_one(offer_letter)
    
    # Create approval center entry
    approval_entry = {
        "id": str(uuid.uuid4()),
        "type": "offer_letter_sent",
        "reference_id": offer_letter["id"],
        "title": f"Offer Letter Sent - {offer_letter['candidate_name']}",
        "description": f"Offer letter for {offer.designation} sent to {candidate.get('email')}",
        "status": "pending_acceptance",
        "created_by": current_user.id,
        "created_by_name": current_user.full_name,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.approval_entries.insert_one(approval_entry)
    
    # Notify all HR managers and admins
    hr_admins = await db.users.find(
        {"role": {"$in": HR_ADMIN_ROLES}},
        {"_id": 0, "id": 1}
    ).to_list(100)
    
    for user in hr_admins:
        await create_notification(
            db,
            user["id"],
            "Offer Letter Sent",
            f"Offer letter sent to {offer_letter['candidate_name']} for {offer.designation}",
            "offer_letter_sent",
            offer_letter["id"]
        )
    
    # Send email to candidate
    acceptance_link = f"{BASE_URL}/accept-offer/{acceptance_token}"
    email_result = {"status": "skipped", "message": "Email service not configured"}
    
    if EMAIL_SERVICE_AVAILABLE:
        try:
            # Generate letter HTML for email
            letter_html = f"""
            <p><strong>Position:</strong> {offer.designation}</p>
            <p><strong>Department:</strong> {offer.department}</p>
            <p><strong>Joining Date:</strong> {offer.joining_date}</p>
            """
            if offer.salary_details.get("gross_monthly"):
                letter_html += f"<p><strong>Gross Monthly Salary:</strong> ₹{offer.salary_details['gross_monthly']:,}</p>"
            
            email_result = await send_offer_letter_email(
                to_email=candidate.get("email"),
                candidate_name=offer_letter["candidate_name"],
                designation=offer.designation,
                department=offer.department,
                acceptance_link=acceptance_link,
                letter_html=letter_html
            )
        except Exception as e:
            email_result = {"status": "error", "message": str(e)}
    
    # Update offer letter with email status
    await db.offer_letters.update_one(
        {"id": offer_letter["id"]},
        {"$set": {"email_status": email_result}}
    )
    
    return {
        "message": "Offer letter created and sent",
        "offer_letter_id": offer_letter["id"],
        "acceptance_link": acceptance_link,
        "email_status": email_result
    }


@router.get("/offer-letters")
async def get_offer_letters(
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get all offer letters."""
    db = get_db()
    
    if current_user.role not in HR_ROLES:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    query = {}
    if status:
        query["status"] = status
    
    letters = await db.offer_letters.find(query, {"_id": 0}).sort("created_at", -1).to_list(500)
    return letters


@router.get("/offer-letters/{letter_id}")
async def get_offer_letter(
    letter_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get a specific offer letter."""
    db = get_db()
    
    if current_user.role not in HR_ROLES:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    letter = await db.offer_letters.find_one({"id": letter_id}, {"_id": 0})
    if not letter:
        raise HTTPException(status_code=404, detail="Offer letter not found")
    
    return letter


@router.post("/offer-letters/accept")
async def accept_offer_letter(acceptance: LetterAcceptance):
    """Employee accepts an offer letter (public endpoint with token)."""
    db = get_db()
    
    letter = await db.offer_letters.find_one(
        {"acceptance_token": acceptance.acceptance_token, "status": "pending_acceptance"},
        {"_id": 0}
    )
    
    if not letter:
        raise HTTPException(status_code=404, detail="Invalid or expired acceptance link")
    
    # Generate employee ID
    employee_id = await get_next_employee_id(db)
    
    # Update offer letter
    await db.offer_letters.update_one(
        {"id": letter["id"]},
        {"$set": {
            "status": "accepted",
            "accepted_at": datetime.now(timezone.utc).isoformat(),
            "accepted_by_name": letter["candidate_name"],
            "employee_id_assigned": employee_id,
            "acceptance_signature": f"Digitally signed by {letter['candidate_name']} on {datetime.now(timezone.utc).strftime('%d-%b-%Y %H:%M UTC')}"
        }}
    )
    
    # Update candidate with employee ID
    await db.onboarding_candidates.update_one(
        {"id": letter["candidate_id"]},
        {"$set": {
            "employee_id": employee_id,
            "offer_accepted": True,
            "offer_accepted_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    # Update approval entry
    await db.approval_entries.update_one(
        {"reference_id": letter["id"]},
        {"$set": {
            "status": "accepted",
            "resolved_at": datetime.now(timezone.utc).isoformat(),
            "resolution_note": f"Accepted by {letter['candidate_name']}. Employee ID: {employee_id}"
        }}
    )
    
    # Notify HR managers and admins
    hr_admins = await db.users.find(
        {"role": {"$in": HR_ADMIN_ROLES}},
        {"_id": 0, "id": 1}
    ).to_list(100)
    
    for user in hr_admins:
        await create_notification(
            db,
            user["id"],
            "Offer Letter Accepted!",
            f"{letter['candidate_name']} has accepted the offer. Employee ID: {employee_id}. Appointment letter can now be generated.",
            "offer_letter_accepted",
            letter["id"]
        )
    
    return {
        "message": "Offer accepted successfully",
        "employee_id": employee_id,
        "candidate_name": letter["candidate_name"],
        "acceptance_signature": f"Digitally signed by {letter['candidate_name']}"
    }


# ============== Appointment Letter Endpoints ==============

@router.post("/appointment-letters")
async def create_appointment_letter(
    appointment: AppointmentLetterCreate,
    current_user: User = Depends(get_current_user)
):
    """Create an appointment letter for an employee (after offer acceptance)."""
    db = get_db()
    
    if current_user.role not in HR_ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Only Admin or HR Manager can create appointment letters")
    
    # Verify employee exists and has accepted offer
    employee = await db.onboarding_candidates.find_one({"id": appointment.employee_id}, {"_id": 0})
    if not employee:
        # Try regular employees collection
        employee = await db.employees.find_one({"id": appointment.employee_id}, {"_id": 0})
    
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    if not employee.get("employee_id"):
        raise HTTPException(status_code=400, detail="Employee must have an assigned Employee ID (offer must be accepted first)")
    
    # Get template
    template = await db.letter_templates.find_one({"id": appointment.template_id, "is_active": True}, {"_id": 0})
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    # Generate acceptance token for appointment letter
    acceptance_token = str(uuid.uuid4())
    
    appointment_letter = {
        "id": str(uuid.uuid4()),
        "letter_type": "appointment_letter",
        "employee_id": appointment.employee_id,
        "employee_code": employee.get("employee_id"),
        "employee_name": f"{employee.get('first_name', '')} {employee.get('last_name', '')}".strip(),
        "employee_email": employee.get("email"),
        "template_id": appointment.template_id,
        "template_name": template["name"],
        "custom_fields": appointment.custom_fields or {},
        "hr_signature_text": appointment.hr_signature_text,
        "hr_signature_image": appointment.hr_signature_image,
        "status": "pending_acceptance",
        "acceptance_token": acceptance_token,
        "created_by": current_user.id,
        "created_by_name": current_user.full_name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "sent_at": datetime.now(timezone.utc).isoformat(),
        "accepted_at": None,
        "accepted_by_name": None
    }
    
    await db.appointment_letters.insert_one(appointment_letter)
    
    # Create approval center entry
    approval_entry = {
        "id": str(uuid.uuid4()),
        "type": "appointment_letter_sent",
        "reference_id": appointment_letter["id"],
        "title": f"Appointment Letter Sent - {appointment_letter['employee_name']}",
        "description": f"Appointment letter sent to {employee.get('email')} ({employee.get('employee_id')})",
        "status": "pending_acceptance",
        "created_by": current_user.id,
        "created_by_name": current_user.full_name,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.approval_entries.insert_one(approval_entry)
    
    # Notify HR managers and admins
    hr_admins = await db.users.find(
        {"role": {"$in": HR_ADMIN_ROLES}},
        {"_id": 0, "id": 1}
    ).to_list(100)
    
    for user in hr_admins:
        await create_notification(
            db,
            user["id"],
            "Appointment Letter Sent",
            f"Appointment letter sent to {appointment_letter['employee_name']} ({employee.get('employee_id')})",
            "appointment_letter_sent",
            appointment_letter["id"]
        )
    
    return {
        "message": "Appointment letter created and sent",
        "appointment_letter_id": appointment_letter["id"],
        "acceptance_link": f"/accept-appointment/{acceptance_token}"
    }


@router.get("/appointment-letters")
async def get_appointment_letters(
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get all appointment letters."""
    db = get_db()
    
    if current_user.role not in HR_ROLES:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    query = {}
    if status:
        query["status"] = status
    
    letters = await db.appointment_letters.find(query, {"_id": 0}).sort("created_at", -1).to_list(500)
    return letters


@router.post("/appointment-letters/accept")
async def accept_appointment_letter(acceptance: LetterAcceptance):
    """Employee accepts an appointment letter (public endpoint with token)."""
    db = get_db()
    
    letter = await db.appointment_letters.find_one(
        {"acceptance_token": acceptance.acceptance_token, "status": "pending_acceptance"},
        {"_id": 0}
    )
    
    if not letter:
        raise HTTPException(status_code=404, detail="Invalid or expired acceptance link")
    
    # Update appointment letter
    await db.appointment_letters.update_one(
        {"id": letter["id"]},
        {"$set": {
            "status": "accepted",
            "accepted_at": datetime.now(timezone.utc).isoformat(),
            "accepted_by_name": letter["employee_name"],
            "acceptance_signature": f"Digitally signed by {letter['employee_name']} on {datetime.now(timezone.utc).strftime('%d-%b-%Y %H:%M UTC')}"
        }}
    )
    
    # Update approval entry
    await db.approval_entries.update_one(
        {"reference_id": letter["id"]},
        {"$set": {
            "status": "accepted",
            "resolved_at": datetime.now(timezone.utc).isoformat(),
            "resolution_note": f"Accepted by {letter['employee_name']}"
        }}
    )
    
    # Notify HR managers and admins
    hr_admins = await db.users.find(
        {"role": {"$in": HR_ADMIN_ROLES}},
        {"_id": 0, "id": 1}
    ).to_list(100)
    
    for user in hr_admins:
        await create_notification(
            db,
            user["id"],
            "Appointment Letter Accepted!",
            f"{letter['employee_name']} ({letter['employee_code']}) has accepted the appointment letter.",
            "appointment_letter_accepted",
            letter["id"]
        )
    
    return {
        "message": "Appointment letter accepted successfully",
        "employee_name": letter["employee_name"],
        "employee_code": letter["employee_code"],
        "acceptance_signature": f"Digitally signed by {letter['employee_name']}"
    }


# ============== Stats & Dashboard ==============

@router.get("/stats")
async def get_letter_stats(current_user: User = Depends(get_current_user)):
    """Get letter management statistics."""
    db = get_db()
    
    if current_user.role not in HR_ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    offer_pending = await db.offer_letters.count_documents({"status": "pending_acceptance"})
    offer_accepted = await db.offer_letters.count_documents({"status": "accepted"})
    appointment_pending = await db.appointment_letters.count_documents({"status": "pending_acceptance"})
    appointment_accepted = await db.appointment_letters.count_documents({"status": "accepted"})
    templates_count = await db.letter_templates.count_documents({"is_active": True})
    
    return {
        "offer_letters": {
            "pending": offer_pending,
            "accepted": offer_accepted
        },
        "appointment_letters": {
            "pending": appointment_pending,
            "accepted": appointment_accepted
        },
        "templates": templates_count
    }


# ============== Public Endpoints for Letter Viewing ==============

@router.get("/view/offer/{token}")
async def view_offer_letter(token: str):
    """Public endpoint to view an offer letter by acceptance token."""
    db = get_db()
    
    letter = await db.offer_letters.find_one(
        {"acceptance_token": token},
        {"_id": 0, "acceptance_token": 0}
    )
    
    if not letter:
        raise HTTPException(status_code=404, detail="Letter not found")
    
    # Get template
    template = await db.letter_templates.find_one({"id": letter["template_id"]}, {"_id": 0})
    
    return {
        "letter": letter,
        "template": template,
        "can_accept": letter["status"] == "pending_acceptance"
    }


@router.get("/view/appointment/{token}")
async def view_appointment_letter(token: str):
    """Public endpoint to view an appointment letter by acceptance token."""
    db = get_db()
    
    letter = await db.appointment_letters.find_one(
        {"acceptance_token": token},
        {"_id": 0, "acceptance_token": 0}
    )
    
    if not letter:
        raise HTTPException(status_code=404, detail="Letter not found")
    
    # Get template
    template = await db.letter_templates.find_one({"id": letter["template_id"]}, {"_id": 0})
    
    return {
        "letter": letter,
        "template": template,
        "can_accept": letter["status"] == "pending_acceptance"
    }



# ============== Letterhead Settings Endpoints ==============

@router.get("/letterhead-settings")
async def get_letterhead_settings(current_user: User = Depends(get_current_user)):
    """Get letterhead settings (header/footer images)."""
    db = get_db()
    
    if current_user.role not in HR_ROLES:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    settings = await db.letterhead_settings.find_one({"id": "main"}, {"_id": 0})
    
    if not settings:
        # Return default settings
        return {
            "id": "main",
            "header_image": None,
            "footer_image": None,
            "company_name": "D&V Business Consulting Pvt. Ltd.",
            "company_address": "123, Business Park, Andheri East, Mumbai - 400069",
            "company_phone": "+91 22 1234 5678",
            "company_email": "contact@dvconsulting.co.in",
            "company_cin": "U74999MH2020PTC123456"
        }
    
    return settings


@router.put("/letterhead-settings")
async def update_letterhead_settings(
    settings: LetterheadSettings,
    current_user: User = Depends(get_current_user)
):
    """Update letterhead settings (Admin/HR Manager only)."""
    db = get_db()
    
    if current_user.role not in HR_ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Only Admin or HR Manager can update letterhead settings")
    
    settings_doc = {
        "id": "main",
        "header_image": settings.header_image,
        "footer_image": settings.footer_image,
        "company_name": settings.company_name,
        "company_address": settings.company_address,
        "company_phone": settings.company_phone,
        "company_email": settings.company_email,
        "company_cin": settings.company_cin,
        "updated_by": current_user.id,
        "updated_by_name": current_user.full_name,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.letterhead_settings.update_one(
        {"id": "main"},
        {"$set": settings_doc},
        upsert=True
    )
    
    return {"message": "Letterhead settings updated successfully"}


@router.post("/letterhead-settings/upload-header")
async def upload_header_image(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """Upload letterhead header image."""
    db = get_db()
    
    if current_user.role not in HR_ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Only Admin or HR Manager can upload letterhead images")
    
    # Validate file type
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    # Read and encode file
    contents = await file.read()
    if len(contents) > 5 * 1024 * 1024:  # 5MB limit
        raise HTTPException(status_code=400, detail="File size must be less than 5MB")
    
    encoded = base64.b64encode(contents).decode("utf-8")
    data_uri = f"data:{file.content_type};base64,{encoded}"
    
    # Update settings
    await db.letterhead_settings.update_one(
        {"id": "main"},
        {
            "$set": {
                "header_image": data_uri,
                "header_filename": file.filename,
                "header_updated_by": current_user.id,
                "header_updated_at": datetime.now(timezone.utc).isoformat()
            }
        },
        upsert=True
    )
    
    return {"message": "Header image uploaded successfully", "filename": file.filename}


@router.post("/letterhead-settings/upload-footer")
async def upload_footer_image(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """Upload letterhead footer image."""
    db = get_db()
    
    if current_user.role not in HR_ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Only Admin or HR Manager can upload letterhead images")
    
    # Validate file type
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    # Read and encode file
    contents = await file.read()
    if len(contents) > 5 * 1024 * 1024:  # 5MB limit
        raise HTTPException(status_code=400, detail="File size must be less than 5MB")
    
    encoded = base64.b64encode(contents).decode("utf-8")
    data_uri = f"data:{file.content_type};base64,{encoded}"
    
    # Update settings
    await db.letterhead_settings.update_one(
        {"id": "main"},
        {
            "$set": {
                "footer_image": data_uri,
                "footer_filename": file.filename,
                "footer_updated_by": current_user.id,
                "footer_updated_at": datetime.now(timezone.utc).isoformat()
            }
        },
        upsert=True
    )
    
    return {"message": "Footer image uploaded successfully", "filename": file.filename}


@router.delete("/letterhead-settings/header")
async def delete_header_image(current_user: User = Depends(get_current_user)):
    """Delete letterhead header image."""
    db = get_db()
    
    if current_user.role not in HR_ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Only Admin or HR Manager can delete letterhead images")
    
    await db.letterhead_settings.update_one(
        {"id": "main"},
        {"$set": {"header_image": None, "header_filename": None}}
    )
    
    return {"message": "Header image deleted"}


@router.delete("/letterhead-settings/footer")
async def delete_footer_image(current_user: User = Depends(get_current_user)):
    """Delete letterhead footer image."""
    db = get_db()
    
    if current_user.role not in HR_ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Only Admin or HR Manager can delete letterhead images")
    
    await db.letterhead_settings.update_one(
        {"id": "main"},
        {"$set": {"footer_image": None, "footer_filename": None}}
    )
    
    return {"message": "Footer image deleted"}
