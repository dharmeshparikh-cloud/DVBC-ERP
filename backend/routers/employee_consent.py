"""
Employee Consent Router - NDA/NCA/Data Usage Consent Management

This module handles:
1. Employment confirmation workflow with legal consent
2. NDA/NCA document versioning
3. Digital consent collection and storage
4. Access blocking until consent is signed
5. Re-consent flow when documents are updated
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from datetime import datetime, timezone
from typing import Optional, List
import uuid
import hashlib
import os

from .models import User
from .deps import get_db, get_role_group, has_role
from .auth import get_current_user
from services.email_service import send_email

router = APIRouter(prefix="/consent", tags=["Employee Consent"])


# ============== DOCUMENT TEMPLATES ==============

DEFAULT_CONSENT_DOCUMENTS = {
    "nda": {
        "title": "Non-Disclosure Agreement (NDA)",
        "version": "1.0",
        "effective_date": "2024-01-01",
        "content_summary": "Confidentiality obligations regarding company information, client data, and trade secrets.",
        "key_points": [
            "All company information is confidential",
            "No sharing of client data with third parties",
            "Obligations continue after employment ends",
            "Breach may result in legal action"
        ]
    },
    "nca": {
        "title": "Non-Compete Agreement (NCA)",
        "version": "1.0",
        "effective_date": "2024-01-01",
        "content_summary": "Restrictions on competitive employment during and after employment.",
        "key_points": [
            "Cannot work for direct competitors during employment",
            "Post-employment restrictions apply for specified period",
            "Geographic limitations as specified",
            "Exceptions require written approval"
        ]
    },
    "data_consent": {
        "title": "Data Processing Consent",
        "version": "1.0",
        "effective_date": "2024-01-01",
        "content_summary": "Consent for collection, storage, and processing of personal data.",
        "key_points": [
            "Personal data will be stored securely",
            "Data used only for employment purposes",
            "Right to access and correct personal data",
            "Data retention as per legal requirements"
        ]
    },
    "it_policy": {
        "title": "IT Usage Policy",
        "version": "1.0",
        "effective_date": "2024-01-01",
        "content_summary": "Acceptable use of company IT systems and equipment.",
        "key_points": [
            "Company systems for business use only",
            "No unauthorized software installation",
            "Email and internet usage may be monitored",
            "Report security incidents immediately"
        ]
    },
    "code_of_conduct": {
        "title": "Code of Conduct",
        "version": "1.0",
        "effective_date": "2024-01-01",
        "content_summary": "Expected professional behavior and ethical standards.",
        "key_points": [
            "Professional behavior at all times",
            "Zero tolerance for harassment",
            "Conflict of interest disclosure required",
            "Compliance with all company policies"
        ]
    }
}


def generate_consent_hash(employee_id: str, document_type: str, version: str, timestamp: str) -> str:
    """Generate a unique hash for consent record integrity."""
    data = f"{employee_id}:{document_type}:{version}:{timestamp}"
    return hashlib.sha256(data.encode()).hexdigest()


# ============== DOCUMENT MANAGEMENT ==============

@router.get("/documents")
async def get_consent_documents(current_user: User = Depends(get_current_user)):
    """Get all consent document templates."""
    db = get_db()
    
    # Try to get from database, fallback to defaults
    documents = await db.consent_documents.find({}, {"_id": 0}).to_list(20)
    
    if not documents:
        # Initialize with defaults
        for doc_type, doc_data in DEFAULT_CONSENT_DOCUMENTS.items():
            doc = {
                "id": str(uuid.uuid4()),
                "type": doc_type,
                **doc_data,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "is_active": True
            }
            await db.consent_documents.insert_one(doc)
            documents.append(doc)
    
    return documents


@router.post("/documents")
async def create_or_update_consent_document(
    data: dict,
    current_user: User = Depends(get_current_user)
):
    """Create or update a consent document (Admin only). Updating creates a new version."""
    db = get_db()
    
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    
    doc_type = data.get("type")
    if not doc_type:
        raise HTTPException(status_code=400, detail="Document type is required")
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Get existing document
    existing = await db.consent_documents.find_one(
        {"type": doc_type, "is_active": True},
        {"_id": 0}
    )
    
    if existing:
        # Deactivate old version
        await db.consent_documents.update_one(
            {"id": existing["id"]},
            {"$set": {"is_active": False, "superseded_at": now}}
        )
        
        # Calculate new version
        old_version = existing.get("version", "1.0")
        version_parts = old_version.split(".")
        new_version = f"{version_parts[0]}.{int(version_parts[1]) + 1}"
    else:
        new_version = "1.0"
    
    # Create new document
    new_doc = {
        "id": str(uuid.uuid4()),
        "type": doc_type,
        "title": data.get("title", DEFAULT_CONSENT_DOCUMENTS.get(doc_type, {}).get("title", doc_type)),
        "version": new_version,
        "effective_date": data.get("effective_date", now[:10]),
        "content_summary": data.get("content_summary"),
        "key_points": data.get("key_points", []),
        "full_content": data.get("full_content"),
        "created_at": now,
        "created_by": current_user.id,
        "created_by_name": current_user.full_name,
        "is_active": True,
        "requires_re_consent": data.get("requires_re_consent", True)
    }
    
    await db.consent_documents.insert_one(new_doc)
    
    # If requires re-consent, flag all employees
    if new_doc.get("requires_re_consent"):
        await db.employee_consent_log.update_many(
            {"document_type": doc_type, "status": "accepted"},
            {"$set": {"needs_reconsent": True, "reconsent_reason": f"Document updated to version {new_version}"}}
        )
    
    return {
        "message": "Document created/updated",
        "document_id": new_doc["id"],
        "version": new_version,
        "type": doc_type
    }


# ============== CONSENT WORKFLOW ==============

@router.post("/initiate/{employee_id}")
async def initiate_consent_workflow(
    employee_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Initiate consent collection workflow for an employee.
    Called after onboarding completion.
    """
    db = get_db()
    
    # Only HR can initiate
    hr_roles = get_role_group("HR_ROLES", fail_closed=True) or ["hr_manager", "hr_executive"]
    if not has_role(current_user.role, hr_roles + ["admin"]):
        raise HTTPException(status_code=403, detail="Only HR can initiate consent workflow")
    
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Check if consent already exists
    existing_consent = await db.employee_consent_status.find_one({"employee_id": employee_id})
    if existing_consent and existing_consent.get("all_consents_complete"):
        return {"message": "All consents already complete", "status": "complete"}
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Get active consent documents
    documents = await db.consent_documents.find({"is_active": True}, {"_id": 0}).to_list(20)
    if not documents:
        # Initialize defaults
        documents = []
        for doc_type, doc_data in DEFAULT_CONSENT_DOCUMENTS.items():
            doc = {
                "id": str(uuid.uuid4()),
                "type": doc_type,
                **doc_data,
                "created_at": now,
                "is_active": True
            }
            await db.consent_documents.insert_one(doc)
            documents.append(doc)
    
    # Create consent status record
    consent_status = {
        "id": str(uuid.uuid4()),
        "employee_id": employee_id,
        "employee_code": employee.get("employee_id"),
        "employee_name": employee.get("full_name"),
        "employee_email": employee.get("email") or employee.get("personal_email"),
        "initiated_by": current_user.id,
        "initiated_by_name": current_user.full_name,
        "initiated_at": now,
        "documents_to_consent": [d["type"] for d in documents],
        "consents_completed": [],
        "all_consents_complete": False,
        "erp_access_blocked": True,  # Block access until all consents
        "status": "pending"
    }
    
    await db.employee_consent_status.update_one(
        {"employee_id": employee_id},
        {"$set": consent_status},
        upsert=True
    )
    
    # Generate consent token
    consent_token = str(uuid.uuid4())
    await db.consent_tokens.insert_one({
        "token": consent_token,
        "employee_id": employee_id,
        "created_at": now,
        "expires_at": None,  # No expiry for consent
        "used": False
    })
    
    # Send email to employee
    base_url = os.environ.get("FRONTEND_URL", "https://netra-erp-mobile.preview.emergentagent.com")
    consent_link = f"{base_url}/consent/{consent_token}"
    
    try:
        await send_email(
            to_email=consent_status["employee_email"],
            subject="Employment Confirmation - Consent Required",
            html_content=f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <div style="background: linear-gradient(135deg, #f97316, #ea580c); padding: 30px; text-align: center;">
                    <h1 style="color: white; margin: 0;">Employment Confirmation</h1>
                    <p style="color: rgba(255,255,255,0.9); margin: 10px 0 0;">D&V Business Consulting</p>
                </div>
                <div style="padding: 30px; background: #f9f9f9;">
                    <p>Dear <strong>{employee.get('full_name', 'Employee')}</strong>,</p>
                    <p>Welcome to D&V Business Consulting! Before you can access the NETRA ERP portal, please review and accept the following documents:</p>
                    
                    <ul style="background: white; padding: 20px 20px 20px 40px; border-radius: 8px; margin: 20px 0;">
                        <li>Non-Disclosure Agreement (NDA)</li>
                        <li>Non-Compete Agreement (NCA)</li>
                        <li>Data Processing Consent</li>
                        <li>IT Usage Policy</li>
                        <li>Code of Conduct</li>
                    </ul>
                    
                    <div style="text-align: center; margin: 30px 0;">
                        <a href="{consent_link}" style="display: inline-block; background: #f97316; color: white; padding: 14px 40px; text-decoration: none; border-radius: 8px; font-weight: bold;">
                            Review & Accept Documents
                        </a>
                    </div>
                    
                    <p style="background: #fef3c7; padding: 12px; border-radius: 6px; font-size: 14px;">
                        <strong>Important:</strong> You must accept all documents before you can access the ERP portal.
                    </p>
                </div>
            </div>
            """
        )
    except Exception as e:
        print(f"Failed to send consent email: {e}")
    
    return {
        "message": "Consent workflow initiated",
        "consent_link": consent_link,
        "documents_to_consent": [d["type"] for d in documents]
    }


@router.get("/status/{employee_id}")
async def get_consent_status(
    employee_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get consent status for an employee."""
    db = get_db()
    
    status = await db.employee_consent_status.find_one(
        {"employee_id": employee_id},
        {"_id": 0}
    )
    
    if not status:
        return {"status": "not_initiated", "all_consents_complete": False}
    
    # Get detailed consent records
    consents = await db.employee_consent_log.find(
        {"employee_id": employee_id},
        {"_id": 0}
    ).to_list(20)
    
    return {
        **status,
        "consent_details": consents
    }


@router.get("/pending/{token}")
async def get_pending_consents(token: str):
    """
    Public endpoint - Get pending consent documents for an employee using token.
    No authentication required.
    """
    db = get_db()
    
    # Validate token
    token_record = await db.consent_tokens.find_one({"token": token})
    if not token_record:
        raise HTTPException(status_code=404, detail="Invalid consent link")
    
    employee_id = token_record["employee_id"]
    
    # Get consent status
    status = await db.employee_consent_status.find_one(
        {"employee_id": employee_id},
        {"_id": 0}
    )
    
    if not status:
        raise HTTPException(status_code=404, detail="Consent workflow not found")
    
    if status.get("all_consents_complete"):
        return {
            "status": "complete",
            "message": "All consents already completed",
            "employee_name": status.get("employee_name")
        }
    
    # Get documents to consent
    pending_types = [t for t in status.get("documents_to_consent", []) if t not in status.get("consents_completed", [])]
    
    documents = await db.consent_documents.find(
        {"type": {"$in": pending_types}, "is_active": True},
        {"_id": 0}
    ).to_list(20)
    
    return {
        "status": "pending",
        "employee_name": status.get("employee_name"),
        "pending_documents": documents,
        "completed_documents": status.get("consents_completed", [])
    }


@router.post("/accept/{token}")
async def accept_consent(
    token: str,
    data: dict,
    request: Request
):
    """
    Public endpoint - Accept a consent document.
    No authentication required - uses token.
    """
    db = get_db()
    
    # Validate token
    token_record = await db.consent_tokens.find_one({"token": token})
    if not token_record:
        raise HTTPException(status_code=404, detail="Invalid consent link")
    
    employee_id = token_record["employee_id"]
    document_type = data.get("document_type")
    
    if not document_type:
        raise HTTPException(status_code=400, detail="Document type is required")
    
    # Get the document
    document = await db.consent_documents.find_one(
        {"type": document_type, "is_active": True},
        {"_id": 0}
    )
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Get employee for details
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Get client IP
    client_ip = request.client.host if request.client else "unknown"
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        client_ip = forwarded_for.split(",")[0].strip()
    
    # Generate consent hash
    consent_hash = generate_consent_hash(employee_id, document_type, document.get("version", "1.0"), now)
    
    # Create consent record
    consent_record = {
        "id": str(uuid.uuid4()),
        "employee_id": employee_id,
        "employee_code": employee.get("employee_id"),
        "employee_name": employee.get("full_name"),
        "document_type": document_type,
        "document_id": document.get("id"),
        "document_version": document.get("version", "1.0"),
        "document_title": document.get("title"),
        "accepted": True,
        "accepted_at": now,
        "ip_address": client_ip,
        "user_agent": request.headers.get("User-Agent", "unknown")[:500],
        "digital_signature_hash": consent_hash,
        "status": "accepted",
        "needs_reconsent": False
    }
    
    await db.employee_consent_log.insert_one(consent_record)
    
    # Update consent status
    status = await db.employee_consent_status.find_one({"employee_id": employee_id})
    completed = status.get("consents_completed", []) if status else []
    if document_type not in completed:
        completed.append(document_type)
    
    all_complete = set(completed) >= set(status.get("documents_to_consent", []))
    
    await db.employee_consent_status.update_one(
        {"employee_id": employee_id},
        {"$set": {
            "consents_completed": completed,
            "all_consents_complete": all_complete,
            "erp_access_blocked": not all_complete,
            "last_consent_at": now,
            "status": "complete" if all_complete else "in_progress"
        }}
    )
    
    # If all complete, send confirmation and notify HR
    if all_complete:
        # Mark token as used
        await db.consent_tokens.update_one(
            {"token": token},
            {"$set": {"used": True, "used_at": now}}
        )
        
        # Notify HR
        if status and status.get("initiated_by"):
            await db.notifications.insert_one({
                "id": str(uuid.uuid4()),
                "user_id": status["initiated_by"],
                "type": "consent_complete",
                "title": "Employee Consent Complete",
                "message": f"{employee.get('full_name')} has completed all consent documents. ERP access is now enabled.",
                "is_read": False,
                "created_at": now
            })
        
        # Send confirmation email to employee
        try:
            await send_email(
                to_email=employee.get("email") or employee.get("personal_email"),
                subject="Consent Completed - ERP Access Enabled",
                html_content=f"""
                <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                    <div style="background: #16a34a; padding: 20px; text-align: center;">
                        <h2 style="color: white; margin: 0;">Consent Complete ✓</h2>
                    </div>
                    <div style="padding: 30px; background: #f9f9f9;">
                        <p>Dear <strong>{employee.get('full_name', 'Employee')}</strong>,</p>
                        <p>Thank you for reviewing and accepting all required documents. Your ERP access has been enabled.</p>
                        <p>You can now login to NETRA ERP using your Employee ID and password.</p>
                    </div>
                </div>
                """
            )
        except Exception as e:
            print(f"Failed to send consent confirmation email: {e}")
    
    return {
        "message": f"Consent for '{document.get('title')}' accepted",
        "document_type": document_type,
        "all_complete": all_complete,
        "remaining": [t for t in status.get("documents_to_consent", []) if t not in completed] if status else []
    }


# ============== ACCESS CHECK ==============

@router.get("/check-access/{employee_id}")
async def check_consent_access(employee_id: str):
    """
    Check if an employee has completed all required consents.
    Used by auth middleware to block ERP access.
    """
    db = get_db()
    
    status = await db.employee_consent_status.find_one(
        {"employee_id": employee_id},
        {"_id": 0, "all_consents_complete": 1, "erp_access_blocked": 1}
    )
    
    if not status:
        # No consent workflow initiated - allow access (legacy employees)
        return {"access_allowed": True, "reason": "consent_not_required"}
    
    if status.get("all_consents_complete") and not status.get("erp_access_blocked"):
        return {"access_allowed": True, "reason": "all_consents_complete"}
    
    return {
        "access_allowed": False,
        "reason": "pending_consents",
        "redirect_to": "/consent-required"
    }


# ============== RE-CONSENT ==============

@router.get("/needs-reconsent")
async def get_employees_needing_reconsent(
    current_user: User = Depends(get_current_user)
):
    """Get list of employees who need to re-consent due to document updates."""
    db = get_db()
    
    hr_roles = get_role_group("HR_ROLES", fail_closed=True) or []
    if not has_role(current_user.role, hr_roles + ["admin"]):
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Find employees with needs_reconsent flag
    reconsents = await db.employee_consent_log.find(
        {"needs_reconsent": True},
        {"_id": 0}
    ).to_list(500)
    
    # Group by employee
    by_employee = {}
    for r in reconsents:
        emp_id = r["employee_id"]
        if emp_id not in by_employee:
            by_employee[emp_id] = {
                "employee_id": emp_id,
                "employee_code": r.get("employee_code"),
                "employee_name": r.get("employee_name"),
                "documents": []
            }
        by_employee[emp_id]["documents"].append({
            "type": r["document_type"],
            "reason": r.get("reconsent_reason")
        })
    
    return list(by_employee.values())


@router.post("/trigger-reconsent/{employee_id}")
async def trigger_reconsent(
    employee_id: str,
    current_user: User = Depends(get_current_user)
):
    """Trigger re-consent workflow for an employee."""
    db = get_db()
    
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    
    # Reset consent status
    await db.employee_consent_status.update_one(
        {"employee_id": employee_id},
        {"$set": {
            "all_consents_complete": False,
            "erp_access_blocked": True,
            "consents_completed": [],
            "status": "reconsent_required"
        }}
    )
    
    # Clear the needs_reconsent flags
    await db.employee_consent_log.update_many(
        {"employee_id": employee_id, "needs_reconsent": True},
        {"$set": {"needs_reconsent": False, "superseded": True}}
    )
    
    # Initiate new consent workflow
    return await initiate_consent_workflow(employee_id, current_user)
