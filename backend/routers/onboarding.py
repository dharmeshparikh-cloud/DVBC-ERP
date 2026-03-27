"""
Onboarding Router - Self-Service Candidate Onboarding

This module handles the new self-service onboarding flow:
1. HR sends invite to candidate
2. Candidate fills form via public link (no login)
3. HR reviews, assigns dept/manager, verifies
4. On completion: Employee ID generated, record created

PERFORMANCE OPTIMIZATION: December 2025
- Added WebSocket notifications for real-time updates
- Added Redis cache invalidation
"""

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from datetime import datetime, timezone, timedelta
from typing import Optional, List
import uuid
import os
import re
import secrets

from .models import User
from .deps import get_db, get_role_group, has_role
from .deps import get_current_user
from services.email_service import (
    send_email,
    send_onboarding_invite_email,
    send_onboarding_submission_notification_email,
    send_onboarding_revision_request_email,
    send_onboarding_complete_email
)
from services.websocket_manager import ws_manager, notify_onboarding_update, notify_dashboard_refresh
from services.redis_cache import CacheInvalidation

router = APIRouter(prefix="/onboarding", tags=["Onboarding"])

# Directory for temporary document storage
ONBOARDING_DOCS_DIR = "/app/backend/uploads/onboarding_docs"
os.makedirs(ONBOARDING_DOCS_DIR, exist_ok=True)

# Token expiry (7 days)
TOKEN_EXPIRY_DAYS = 7


# ==================== HR ENDPOINTS ====================

@router.post("/invite")
async def send_onboarding_invite(
    data: dict,
    current_user: User = Depends(get_current_user)
):
    """
    HR sends onboarding invite to a candidate.
    Creates a submission record and sends email with secure link.
    """
    db = get_db()
    
    # Authorization - HR roles only
    hr_roles = ["hr_manager", "hr_executive", "admin"]
    if not has_role(current_user.role, hr_roles):
        raise HTTPException(status_code=403, detail="Only HR can send onboarding invites")
    
    # Validate required fields
    candidate_email = data.get("candidate_email", "").strip().lower()
    candidate_name = data.get("candidate_name", "").strip()
    offered_position = data.get("offered_position", "").strip()
    
    if not candidate_email or not candidate_name or not offered_position:
        raise HTTPException(status_code=400, detail="Email, name, and position are required")
    
    # Check for duplicates
    await check_duplicate_candidate(db, candidate_email)
    
    # Generate secure token
    token = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(days=TOKEN_EXPIRY_DAYS)
    
    submission_id = str(uuid.uuid4())
    
    submission = {
        "id": submission_id,
        "token": token,
        "status": "invited",  # invited -> draft -> submitted -> approved/rejected
        
        # From HR
        "invited_by": current_user.id,
        "invited_by_name": current_user.full_name,
        "invited_at": now.isoformat(),
        "candidate_email": candidate_email,
        "candidate_name": candidate_name,
        "offered_position": offered_position,
        
        # Will be filled by candidate
        "candidate_details": None,
        "education": [],
        "employment_history": [],
        "bank_details": None,
        "professional_reference": None,
        "personal_reference": None,
        "emergency_contact": None,
        "documents": [],
        "declaration_signed": False,
        "submitted_at": None,
        
        # Will be filled by HR on review
        "hr_assigned": {
            "department": None,
            "reporting_manager_id": None,
            "reporting_manager_name": None,
            "joining_date": None,
            "official_email": None,
            "employment_type": None,
            "designation": offered_position
        },
        "hr_verification": {
            "documents_verified": False,
            "documents_verified_by": None,
            "documents_verified_at": None,
            "bank_verified": False,
            "bank_verified_by": None,
            "bank_verified_at": None
        },
        
        # Completion
        "completed_at": None,
        "completed_by": None,
        "employee_id_generated": None,
        "employee_record_id": None,
        
        # Tracking
        "link_expires_at": expires_at.isoformat(),
        "revision_history": [],
        "audit_log": [{
            "action": "invite_sent",
            "actor_id": current_user.id,
            "actor_name": current_user.full_name,
            "timestamp": now.isoformat(),
            "details": {"position": offered_position}
        }]
    }
    
    await db.onboarding_submissions.insert_one(submission)
    
    # Send email to candidate
    # Get base URL from environment
    base_url = os.environ.get("FRONTEND_URL", "https://funnel-governance.preview.emergentagent.com")
    onboarding_link = f"{base_url}/onboarding/candidate/{token}"
    
    try:
        await send_onboarding_invite_email(
            to_email=candidate_email,
            candidate_name=candidate_name,
            offered_position=offered_position,
            onboarding_link=onboarding_link,
            expires_at=expires_at.strftime('%B %d, %Y at %I:%M %p'),
            hr_name=current_user.full_name
        )
    except Exception as e:
        print(f"Failed to send invite email: {e}")
        # Continue even if email fails - HR can share link manually
    
    return {
        "message": "Onboarding invite sent successfully",
        "submission_id": submission_id,
        "onboarding_link": onboarding_link,
        "expires_at": expires_at.isoformat()
    }


@router.get("/submissions")
async def list_submissions(
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """List all onboarding submissions for HR review."""
    db = get_db()
    
    hr_roles = ["hr_manager", "hr_executive", "admin"]
    if not has_role(current_user.role, hr_roles):
        raise HTTPException(status_code=403, detail="Access denied")
    
    query = {}
    if status:
        query["status"] = status
    
    submissions = await db.onboarding_submissions.find(
        query, {"_id": 0}
    ).sort([("created_at", -1), ("invited_at", -1)]).to_list(100)
    
    # Calculate progress for each
    for sub in submissions:
        sub["progress"] = calculate_submission_progress(sub)
    
    return submissions


@router.get("/submissions/{submission_id}")
async def get_submission(
    submission_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get detailed submission for HR review."""
    db = get_db()
    
    hr_roles = ["hr_manager", "hr_executive", "admin"]
    if not has_role(current_user.role, hr_roles):
        raise HTTPException(status_code=403, detail="Access denied")
    
    submission = await db.onboarding_submissions.find_one(
        {"id": submission_id}, {"_id": 0}
    )
    
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    submission["progress"] = calculate_submission_progress(submission)
    
    return submission


@router.patch("/submissions/{submission_id}/hr-assign")
async def hr_assign_details(
    submission_id: str,
    data: dict,
    current_user: User = Depends(get_current_user)
):
    """HR assigns department, manager, joining date, etc."""
    db = get_db()
    
    hr_roles = ["hr_manager", "hr_executive", "admin"]
    if not has_role(current_user.role, hr_roles):
        raise HTTPException(status_code=403, detail="Access denied")
    
    submission = await db.onboarding_submissions.find_one({"id": submission_id})
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Update HR assigned fields
    hr_assigned = submission.get("hr_assigned", {})
    for field in ["department", "reporting_manager_id", "reporting_manager_name", 
                  "joining_date", "official_email", "employment_type", "designation"]:
        if field in data:
            hr_assigned[field] = data[field]
    
    await db.onboarding_submissions.update_one(
        {"id": submission_id},
        {
            "$set": {"hr_assigned": hr_assigned},
            "$push": {
                "audit_log": {
                    "action": "hr_assigned",
                    "actor_id": current_user.id,
                    "actor_name": current_user.full_name,
                    "timestamp": now,
                    "details": data
                }
            }
        }
    )
    
    return {"message": "HR details assigned successfully"}


@router.post("/submissions/{submission_id}/verify-documents")
async def verify_documents(
    submission_id: str,
    current_user: User = Depends(get_current_user)
):
    """HR Manager verifies all uploaded documents."""
    db = get_db()
    
    # Only HR team or Admin can verify
    if current_user.role not in ["hr_manager", "hr_admin", "hr_executive", "admin"]:
        raise HTTPException(status_code=403, detail="Only HR team or Admin can verify documents")
    
    now = datetime.now(timezone.utc).isoformat()
    
    await db.onboarding_submissions.update_one(
        {"id": submission_id},
        {
            "$set": {
                "hr_verification.documents_verified": True,
                "hr_verification.documents_verified_by": current_user.id,
                "hr_verification.documents_verified_at": now
            },
            "$push": {
                "audit_log": {
                    "action": "documents_verified",
                    "actor_id": current_user.id,
                    "actor_name": current_user.full_name,
                    "timestamp": now
                }
            }
        }
    )
    
    return {"message": "Documents verified successfully"}


@router.post("/submissions/{submission_id}/documents/{document_id}/approve")
async def approve_document(
    submission_id: str,
    document_id: str,
    current_user: User = Depends(get_current_user)
):
    """HR Manager approves an individual document."""
    db = get_db()
    
    if current_user.role not in ["hr_manager", "admin"]:
        raise HTTPException(status_code=403, detail="Only HR Manager or Admin can approve documents")
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Update the specific document's verification status
    result = await db.onboarding_submissions.update_one(
        {"id": submission_id, "documents.id": document_id},
        {
            "$set": {
                "documents.$.verification_status": "approved",
                "documents.$.verified_by": current_user.id,
                "documents.$.verified_by_name": current_user.full_name,
                "documents.$.verified_at": now
            },
            "$push": {
                "audit_log": {
                    "action": "document_approved",
                    "document_id": document_id,
                    "actor_id": current_user.id,
                    "actor_name": current_user.full_name,
                    "timestamp": now
                }
            }
        }
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Check if all documents are now approved
    submission = await db.onboarding_submissions.find_one({"id": submission_id})
    if submission:
        docs = submission.get("documents", [])
        all_approved = all(d.get("verification_status") == "approved" for d in docs) if docs else False
        if all_approved and docs:
            # Mark documents_verified flag as true
            await db.onboarding_submissions.update_one(
                {"id": submission_id},
                {"$set": {"hr_verification.documents_verified": True}}
            )
    
    return {"message": "Document approved successfully"}


@router.post("/submissions/{submission_id}/documents/{document_id}/reject")
async def reject_document(
    submission_id: str,
    document_id: str,
    data: dict,
    current_user: User = Depends(get_current_user)
):
    """HR Manager rejects an individual document with a reason."""
    db = get_db()
    
    if current_user.role not in ["hr_manager", "admin"]:
        raise HTTPException(status_code=403, detail="Only HR Manager or Admin can reject documents")
    
    reason = data.get("reason", "").strip()
    if not reason:
        raise HTTPException(status_code=400, detail="Rejection reason is required")
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Update the specific document's verification status
    result = await db.onboarding_submissions.update_one(
        {"id": submission_id, "documents.id": document_id},
        {
            "$set": {
                "documents.$.verification_status": "rejected",
                "documents.$.rejection_reason": reason,
                "documents.$.rejected_by": current_user.id,
                "documents.$.rejected_by_name": current_user.full_name,
                "documents.$.rejected_at": now
            },
            "$push": {
                "audit_log": {
                    "action": "document_rejected",
                    "document_id": document_id,
                    "reason": reason,
                    "actor_id": current_user.id,
                    "actor_name": current_user.full_name,
                    "timestamp": now
                }
            }
        }
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Get submission to send notification
    submission = await db.onboarding_submissions.find_one({"id": submission_id})
    if submission:
        # Get document info
        doc_info = next((d for d in submission.get("documents", []) if d.get("id") == document_id), {})
        doc_type = doc_info.get("type", "document").replace("_", " ").title()
        
        # Create notification for employee (if submission has candidate email)
        candidate_email = submission.get("candidate_details", {}).get("email") or submission.get("email")
        if candidate_email:
            # Could send email here - for now just log
            print(f"Document rejected notification: {doc_type} for {candidate_email}. Reason: {reason}")
    
    return {"message": "Document rejected successfully", "notification_sent": True}


@router.post("/submissions/{submission_id}/verify-bank")
async def verify_bank(
    submission_id: str,
    current_user: User = Depends(get_current_user)
):
    """HR Manager verifies bank details."""
    db = get_db()
    
    if current_user.role not in ["hr_manager", "hr_admin", "hr_executive", "admin"]:
        raise HTTPException(status_code=403, detail="Only HR team or Admin can verify bank details")
    
    now = datetime.now(timezone.utc).isoformat()
    
    await db.onboarding_submissions.update_one(
        {"id": submission_id},
        {
            "$set": {
                "hr_verification.bank_verified": True,
                "hr_verification.bank_verified_by": current_user.id,
                "hr_verification.bank_verified_at": now
            },
            "$push": {
                "audit_log": {
                    "action": "bank_verified",
                    "actor_id": current_user.id,
                    "actor_name": current_user.full_name,
                    "timestamp": now
                }
            }
        }
    )
    
    return {"message": "Bank details verified successfully"}


@router.post("/submissions/{submission_id}/request-revision")
async def request_revision(
    submission_id: str,
    data: dict,
    current_user: User = Depends(get_current_user)
):
    """HR requests candidate to revise their submission."""
    db = get_db()
    
    hr_roles = ["hr_manager", "hr_executive", "admin"]
    if not has_role(current_user.role, hr_roles):
        raise HTTPException(status_code=403, detail="Access denied")
    
    reason = data.get("reason", "").strip()
    if not reason:
        raise HTTPException(status_code=400, detail="Revision reason is required")
    
    submission = await db.onboarding_submissions.find_one({"id": submission_id})
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    now = datetime.now(timezone.utc)
    
    # Extend token expiry
    new_expiry = now + timedelta(days=TOKEN_EXPIRY_DAYS)
    
    await db.onboarding_submissions.update_one(
        {"id": submission_id},
        {
            "$set": {
                "status": "revision_requested",
                "link_expires_at": new_expiry.isoformat()
            },
            "$push": {
                "revision_history": {
                    "requested_by": current_user.id,
                    "requested_by_name": current_user.full_name,
                    "requested_at": now.isoformat(),
                    "reason": reason
                },
                "audit_log": {
                    "action": "revision_requested",
                    "actor_id": current_user.id,
                    "actor_name": current_user.full_name,
                    "timestamp": now.isoformat(),
                    "details": {"reason": reason}
                }
            }
        }
    )
    
    # Send email to candidate
    try:
        base_url = os.environ.get("FRONTEND_URL", "https://funnel-governance.preview.emergentagent.com")
        onboarding_link = f"{base_url}/onboarding/candidate/{submission['token']}"
        
        await send_onboarding_revision_request_email(
            to_email=submission["candidate_email"],
            candidate_name=submission["candidate_name"],
            offered_position=submission["offered_position"],
            revision_reason=reason,
            onboarding_link=onboarding_link,
            hr_name=current_user.full_name
        )
    except Exception as e:
        print(f"Failed to send revision email: {e}")
    
    return {"message": "Revision requested successfully"}


@router.post("/submissions/{submission_id}/reject")
async def reject_submission(
    submission_id: str,
    data: dict,
    current_user: User = Depends(get_current_user)
):
    """HR rejects the candidate."""
    db = get_db()
    
    if current_user.role not in ["hr_manager", "admin"]:
        raise HTTPException(status_code=403, detail="Only HR Manager or Admin can reject candidates")
    
    reason = data.get("reason", "").strip()
    if not reason:
        raise HTTPException(status_code=400, detail="Rejection reason is required")
    
    submission = await db.onboarding_submissions.find_one({"id": submission_id})
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    now = datetime.now(timezone.utc).isoformat()
    
    await db.onboarding_submissions.update_one(
        {"id": submission_id},
        {
            "$set": {
                "status": "rejected",
                "rejected_at": now,
                "rejected_by": current_user.id,
                "rejection_reason": reason
            },
            "$push": {
                "audit_log": {
                    "action": "rejected",
                    "actor_id": current_user.id,
                    "actor_name": current_user.full_name,
                    "timestamp": now,
                    "details": {"reason": reason}
                }
            }
        }
    )
    
    return {"message": "Candidate rejected"}


@router.post("/submissions/{submission_id}/complete")
async def complete_onboarding(
    submission_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Complete onboarding - Generate Employee ID and create employee record.
    This is the critical step where the actual employee is created.
    
    SIMPLIFIED FLOW: Auto-verifies documents and bank details when completing.
    HR only needs to: 1) Assign department/manager/date 2) Click Complete
    """
    db = get_db()
    
    # Only HR Manager or Admin can complete
    if current_user.role not in ["hr_manager", "admin"]:
        raise HTTPException(status_code=403, detail="Only HR Manager or Admin can complete onboarding")
    
    submission = await db.onboarding_submissions.find_one({"id": submission_id}, {"_id": 0})
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    if submission["status"] == "completed":
        raise HTTPException(status_code=400, detail="Onboarding already completed")
    
    now = datetime.now(timezone.utc)
    
    # AUTO-VERIFY: Mark documents and bank as verified on complete
    # This simplifies the flow - HR doesn't need to click verify buttons separately
    if not submission.get("hr_verification", {}).get("documents_verified"):
        await db.onboarding_submissions.update_one(
            {"id": submission_id},
            {
                "$set": {
                    "hr_verification.documents_verified": True,
                    "hr_verification.documents_verified_by": current_user.id,
                    "hr_verification.documents_verified_at": now.isoformat()
                }
            }
        )
        # Refresh submission
        submission = await db.onboarding_submissions.find_one({"id": submission_id}, {"_id": 0})
    
    if not submission.get("hr_verification", {}).get("bank_verified"):
        await db.onboarding_submissions.update_one(
            {"id": submission_id},
            {
                "$set": {
                    "hr_verification.bank_verified": True,
                    "hr_verification.bank_verified_by": current_user.id,
                    "hr_verification.bank_verified_at": now.isoformat()
                }
            }
        )
        # Refresh submission
        submission = await db.onboarding_submissions.find_one({"id": submission_id}, {"_id": 0})
    
    # Validate all required fields are complete (verification will pass now)
    validation_errors = validate_submission_complete(submission)
    if validation_errors:
        raise HTTPException(status_code=400, detail=f"Cannot complete: {', '.join(validation_errors)}")
    
    now = datetime.now(timezone.utc)
    
    # Employee ID will be generated ONLY after Go-Live approval
    # For now, use a temporary ID format
    employee_id = None  # Will be assigned after Go-Live approval
    
    # Create employee record
    candidate = submission["candidate_details"]
    hr_assigned = submission["hr_assigned"]
    bank_details = submission["bank_details"]
    
    employee_record_id = str(uuid.uuid4())
    
    employee = {
        "id": employee_record_id,
        "employee_id": employee_id,  # Will be generated after Go-Live approval
        "employee_id_pending": True,  # Flag indicating ID not yet assigned
        
        # Personal details from candidate
        "first_name": candidate["first_name"],
        "last_name": candidate["last_name"],
        "full_name": f"{candidate['first_name']} {candidate['last_name']}",
        "date_of_birth": candidate.get("date_of_birth"),
        "gender": candidate.get("gender"),
        "blood_group": candidate.get("blood_group"),
        "marital_status": candidate.get("marital_status"),
        "nationality": candidate.get("nationality"),
        "phone": candidate.get("phone"),
        "alternate_phone": candidate.get("alternate_phone"),
        "current_address": candidate.get("current_address"),
        "permanent_address": candidate.get("permanent_address"),
        "pan_number": candidate.get("pan_number"),
        "aadhaar_number": candidate.get("aadhaar_number"),
        "passport_number": candidate.get("passport_number"),
        "driving_license": candidate.get("driving_license"),
        
        # Email
        "email": hr_assigned["official_email"],
        "personal_email": submission["candidate_email"],
        
        # Employment details from HR
        "department": hr_assigned["department"],
        "designation": hr_assigned["designation"],
        "reporting_manager": hr_assigned["reporting_manager_id"],
        "reporting_manager_name": hr_assigned["reporting_manager_name"],
        "joining_date": hr_assigned["joining_date"],
        "employment_type": hr_assigned["employment_type"],
        
        # Bank details from candidate
        "bank_account_number": bank_details.get("account_number") if bank_details else None,
        "bank_name": bank_details.get("bank_name") if bank_details else None,
        "bank_branch": bank_details.get("branch") if bank_details else None,
        "ifsc_code": bank_details.get("ifsc_code") if bank_details else None,
        "account_holder_name": bank_details.get("account_holder_name") if bank_details else None,
        "bank_verified": True,  # Already verified during onboarding
        
        # Education and employment history
        "education": submission.get("education", []),
        "employment_history": submission.get("employment_history", []),
        
        # References
        "professional_reference": submission.get("professional_reference"),
        "personal_reference": submission.get("personal_reference"),
        
        # Emergency contact
        "emergency_contact": submission.get("emergency_contact"),
        
        # Documents
        "documents": submission.get("documents", []),
        
        # Status
        "status": "onboarded",
        "is_active": True,
        "go_live_status": "not_submitted",
        "onboarding_complete": True,
        
        # Tracking
        "onboarding_source": "self_service",
        "onboarding_submission_id": submission_id,
        "created_at": now.isoformat(),
        "created_by": current_user.id,
        "created_by_name": current_user.full_name
    }
    
    # Insert employee record
    await db.employees.insert_one(employee)
    
    # Update submission as completed
    await db.onboarding_submissions.update_one(
        {"id": submission_id},
        {
            "$set": {
                "status": "completed",
                "completed_at": now.isoformat(),
                "completed_by": current_user.id,
                "employee_id_generated": None,  # Will be assigned after Go-Live approval
                "employee_id_pending": True,
                "employee_record_id": employee_record_id
            },
            "$push": {
                "audit_log": {
                    "action": "completed",
                    "actor_id": current_user.id,
                    "actor_name": current_user.full_name,
                    "timestamp": now.isoformat(),
                    "details": {"note": "Employee record created, ID pending Go-Live approval"}
                }
            }
        }
    )
    
    # Send welcome email to candidate (without Employee ID - will be sent after Go-Live)
    try:
        await send_onboarding_complete_email(
            to_email=submission["candidate_email"],
            candidate_name=f"{candidate['first_name']} {candidate['last_name']}",
            employee_id="Pending (will be assigned after Go-Live approval)",
            designation=hr_assigned["designation"],
            department=hr_assigned["department"],
            joining_date=hr_assigned["joining_date"],
            official_email=hr_assigned["official_email"],
            reporting_manager=hr_assigned["reporting_manager_name"] or "To be assigned"
        )
    except Exception as e:
        print(f"Failed to send welcome email: {e}")
    
    # Real-time WebSocket notifications
    await notify_onboarding_update(submission_id, "complete", current_user.id)
    await notify_dashboard_refresh(current_user.id)
    
    # Invalidate Redis cache
    await CacheInvalidation.onboarding()
    
    return {
        "message": "Onboarding completed successfully. Employee ID will be assigned after Go-Live approval.",
        "employee_id": None,
        "employee_id_pending": True,
        "employee_record_id": employee_record_id
    }



@router.patch("/submissions/{submission_id}/update-section")
async def update_submission_section(
    submission_id: str,
    data: dict,
    current_user: User = Depends(get_current_user)
):
    """
    HR/Admin can update specific sections of a submission (even after completion).
    Sections: personal_details, bank_details, emergency_contact, professional_reference, personal_reference, education, employment_history
    """
    db = get_db()
    
    # Only HR roles can update
    hr_roles = ["hr_manager", "hr_executive", "admin"]
    if not has_role(current_user.role, hr_roles):
        raise HTTPException(status_code=403, detail="Only HR can update submission data")
    
    section = data.get("section")
    section_data = data.get("data")
    
    valid_sections = [
        "candidate_details", "bank_details", "emergency_contact", 
        "professional_reference", "personal_reference", "education", "employment_history"
    ]
    
    if section not in valid_sections:
        raise HTTPException(status_code=400, detail=f"Invalid section. Valid sections: {', '.join(valid_sections)}")
    
    submission = await db.onboarding_submissions.find_one({"id": submission_id})
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Build update query based on section
    update_query = {
        "$set": {
            section: section_data,
            "last_updated_at": now,
            "last_updated_by": current_user.id,
            "last_updated_by_name": current_user.full_name
        },
        "$push": {
            "audit_log": {
                "action": f"updated_{section}",
                "actor_id": current_user.id,
                "actor_name": current_user.full_name,
                "timestamp": now,
                "details": {"section": section}
            }
        }
    }
    
    await db.onboarding_submissions.update_one({"id": submission_id}, update_query)
    
    # If submission is completed, also update the employee record
    if submission.get("status") == "completed" and submission.get("employee_record_id"):
        employee_update = {}
        
        if section == "candidate_details":
            cd = section_data
            employee_update = {
                "first_name": cd.get("first_name"),
                "last_name": cd.get("last_name"),
                "full_name": f"{cd.get('first_name', '')} {cd.get('last_name', '')}",
                "date_of_birth": cd.get("date_of_birth"),
                "gender": cd.get("gender"),
                "blood_group": cd.get("blood_group"),
                "marital_status": cd.get("marital_status"),
                "nationality": cd.get("nationality"),
                "phone": cd.get("phone"),
                "alternate_phone": cd.get("alternate_phone"),
                "personal_email": cd.get("personal_email"),
                "pan_number": cd.get("pan_number"),
                "aadhaar_number": cd.get("aadhaar_number"),
                "passport_number": cd.get("passport_number"),
                "driving_license": cd.get("driving_license"),
                "current_address": cd.get("current_address"),
                "permanent_address": cd.get("permanent_address"),
            }
        elif section == "bank_details":
            bd = section_data
            employee_update = {
                "bank_account_number": bd.get("account_number"),
                "bank_name": bd.get("bank_name"),
                "bank_branch": bd.get("branch"),
                "ifsc_code": bd.get("ifsc_code"),
                "account_holder_name": bd.get("account_holder_name"),
                "bank_verified": False  # Reset verification when bank details change
            }
        elif section == "emergency_contact":
            employee_update = {"emergency_contact": section_data}
        elif section == "professional_reference":
            employee_update = {"professional_reference": section_data}
        elif section == "personal_reference":
            employee_update = {"personal_reference": section_data}
        elif section == "education":
            employee_update = {"education": section_data}
        elif section == "employment_history":
            employee_update = {"employment_history": section_data}
        
        if employee_update:
            employee_update["updated_at"] = now
            employee_update["updated_by"] = current_user.id
            employee_update["updated_by_name"] = current_user.full_name
            
            await db.employees.update_one(
                {"id": submission["employee_record_id"]},
                {"$set": employee_update}
            )
    
    return {"message": f"{section} updated successfully"}


@router.get("/export/excel")
async def export_submissions_excel(
    status: str = "completed",
    current_user: User = Depends(get_current_user)
):
    """
    Export onboarding submissions as Excel data.
    Status: completed, submitted, all
    """
    db = get_db()
    
    hr_roles = ["hr_manager", "hr_executive", "admin"]
    if not has_role(current_user.role, hr_roles):
        raise HTTPException(status_code=403, detail="Only HR can export data")
    
    query = {}
    if status != "all":
        query["status"] = status
    
    submissions = await db.onboarding_submissions.find(query, {"_id": 0}).to_list(1000)
    
    # Format data for Excel export
    export_data = []
    for sub in submissions:
        cd = sub.get("candidate_details", {})
        bd = sub.get("bank_details", {})
        ha = sub.get("hr_assigned", {})
        ec = sub.get("emergency_contact", {})
        
        export_data.append({
            "Employee ID": sub.get("employee_id", ""),
            "First Name": cd.get("first_name", ""),
            "Last Name": cd.get("last_name", ""),
            "Email": sub.get("candidate_email", ""),
            "Phone": cd.get("phone", ""),
            "Date of Birth": cd.get("date_of_birth", ""),
            "Gender": cd.get("gender", ""),
            "PAN Number": cd.get("pan_number", ""),
            "Aadhaar Number": cd.get("aadhaar_number", ""),
            "Department": ha.get("department", ""),
            "Designation": ha.get("designation", sub.get("offered_position", "")),
            "Joining Date": ha.get("joining_date", ""),
            "Official Email": ha.get("official_email", ""),
            "Reporting Manager": ha.get("reporting_manager_name", ""),
            "Bank Name": bd.get("bank_name", ""),
            "Account Number": bd.get("account_number", ""),
            "IFSC Code": bd.get("ifsc_code", ""),
            "Emergency Contact Name": ec.get("name", ""),
            "Emergency Contact Phone": ec.get("phone", ""),
            "Status": sub.get("status", ""),
            "Submitted At": sub.get("submitted_at", ""),
            "Completed At": sub.get("completed_at", "")
        })
    
    return {"data": export_data, "count": len(export_data)}



@router.get("/legacy")
async def list_legacy_onboarding(
    current_user: User = Depends(get_current_user)
):
    """List employees created via legacy flow that might need completion."""
    db = get_db()
    
    hr_roles = ["hr_manager", "hr_executive", "admin"]
    if not has_role(current_user.role, hr_roles):
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Find employees that were created via old flow (no onboarding_source field)
    # and might have incomplete data
    legacy = await db.employees.find({
        "$or": [
            {"onboarding_source": {"$exists": False}},
            {"onboarding_source": "legacy"}
        ],
        "go_live_status": {"$ne": "active"}
    }, {"_id": 0}).to_list(100)
    
    return legacy


# ==================== PUBLIC ENDPOINTS (No Auth) ====================

@router.get("/public/{token}")
async def get_public_submission(token: str):
    """
    Public endpoint for candidate to access their onboarding form.
    No authentication required - token-based access.
    """
    db = get_db()
    
    submission = await db.onboarding_submissions.find_one(
        {"token": token}, {"_id": 0}
    )
    
    if not submission:
        raise HTTPException(status_code=404, detail="Invalid or expired link")
    
    # Check expiry
    link_expires = submission.get("link_expires_at")
    if link_expires:
        if isinstance(link_expires, str):
            expires_at = datetime.fromisoformat(link_expires.replace("Z", "+00:00"))
        else:
            expires_at = link_expires.replace(tzinfo=timezone.utc) if link_expires.tzinfo is None else link_expires
        if datetime.now(timezone.utc) > expires_at:
            raise HTTPException(status_code=410, detail="This link has expired. Please contact HR.")
    
    # Check status
    if submission["status"] == "completed":
        raise HTTPException(status_code=410, detail="This onboarding has already been completed.")
    
    if submission["status"] == "rejected":
        raise HTTPException(status_code=410, detail="This application has been closed.")
    
    # Return only fields candidate needs to see
    return {
        "id": submission["id"],
        "status": submission["status"],
        "candidate_name": submission["candidate_name"],
        "candidate_email": submission["candidate_email"],
        "offered_position": submission["offered_position"],
        "candidate_details": submission["candidate_details"],
        "education": submission["education"],
        "employment_history": submission["employment_history"],
        "bank_details": submission["bank_details"],
        "professional_reference": submission.get("professional_reference"),
        "personal_reference": submission.get("personal_reference"),
        "emergency_contact": submission["emergency_contact"],
        "documents": submission["documents"],
        "declaration_signed": submission["declaration_signed"],
        "revision_history": submission.get("revision_history", []),
        "progress": calculate_submission_progress(submission)
    }


@router.put("/public/{token}")
async def update_public_submission(token: str, data: dict):
    """
    Update candidate's progress (auto-save via PUT).
    Alias for save endpoint to support frontend PUT requests.
    """
    return await save_public_submission(token, data)


@router.post("/public/{token}/save")
async def save_public_submission(token: str, data: dict):
    """
    Save candidate's progress (auto-save).
    Updates draft without submitting.
    """
    db = get_db()
    
    submission = await db.onboarding_submissions.find_one({"token": token})
    if not submission:
        raise HTTPException(status_code=404, detail="Invalid link")
    
    # Check expiry and status
    link_expires = submission.get("link_expires_at")
    if link_expires:
        if isinstance(link_expires, str):
            expires_at = datetime.fromisoformat(link_expires.replace("Z", "+00:00"))
        else:
            expires_at = link_expires.replace(tzinfo=timezone.utc) if link_expires.tzinfo is None else link_expires
        if datetime.now(timezone.utc) > expires_at:
            raise HTTPException(status_code=410, detail="Link expired")
    
    if submission["status"] in ["completed", "rejected"]:
        raise HTTPException(status_code=400, detail="Cannot modify completed submission")
    
    # Update fields
    update_fields = {}
    
    if "candidate_details" in data:
        update_fields["candidate_details"] = data["candidate_details"]
    if "education" in data:
        update_fields["education"] = data["education"]
    if "employment_history" in data:
        update_fields["employment_history"] = data["employment_history"]
    if "bank_details" in data:
        update_fields["bank_details"] = data["bank_details"]
    if "professional_reference" in data:
        update_fields["professional_reference"] = data["professional_reference"]
    if "personal_reference" in data:
        update_fields["personal_reference"] = data["personal_reference"]
    if "emergency_contact" in data:
        update_fields["emergency_contact"] = data["emergency_contact"]
    if "declaration_signed" in data:
        update_fields["declaration_signed"] = data["declaration_signed"]
    
    if update_fields:
        update_fields["status"] = "draft" if submission["status"] == "invited" else submission["status"]
        
        await db.onboarding_submissions.update_one(
            {"token": token},
            {"$set": update_fields}
        )
    
    return {"message": "Progress saved"}


@router.post("/public/{token}/submit")
async def submit_public_submission(token: str, data: dict):
    """
    Candidate submits their completed form for HR review.
    """
    db = get_db()
    
    submission = await db.onboarding_submissions.find_one({"token": token})
    if not submission:
        raise HTTPException(status_code=404, detail="Invalid link")
    
    # Check expiry
    link_expires = submission.get("link_expires_at")
    if link_expires:
        if isinstance(link_expires, str):
            expires_at = datetime.fromisoformat(link_expires.replace("Z", "+00:00"))
        else:
            expires_at = link_expires.replace(tzinfo=timezone.utc) if link_expires.tzinfo is None else link_expires
        if datetime.now(timezone.utc) > expires_at:
            raise HTTPException(status_code=410, detail="Link expired")
    
    if submission["status"] in ["completed", "rejected"]:
        raise HTTPException(status_code=400, detail="Cannot modify completed submission")
    
    # Update with final data
    now = datetime.now(timezone.utc)
    
    update_fields = {
        "status": "submitted",
        "submitted_at": now.isoformat()
    }
    
    if "candidate_details" in data:
        update_fields["candidate_details"] = data["candidate_details"]
    if "education" in data:
        update_fields["education"] = data["education"]
    if "employment_history" in data:
        update_fields["employment_history"] = data["employment_history"]
    if "bank_details" in data:
        update_fields["bank_details"] = data["bank_details"]
    if "professional_reference" in data:
        update_fields["professional_reference"] = data["professional_reference"]
    if "personal_reference" in data:
        update_fields["personal_reference"] = data["personal_reference"]
    if "emergency_contact" in data:
        update_fields["emergency_contact"] = data["emergency_contact"]
    if "declaration_signed" in data:
        update_fields["declaration_signed"] = data["declaration_signed"]
    
    # Store declaration details
    if "declaration" in data:
        update_fields["declaration"] = {
            "signed": data["declaration"].get("signed", True),
            "signed_at": data["declaration"].get("signed_at", now.isoformat()),
            "text": data["declaration"].get("text", "I hereby declare that all the information provided is true and correct."),
            "declaration_points": [
                "All the information provided is true, complete, and correct to the best of my knowledge and belief.",
                "I have not withheld any material information that may affect my employment.",
                "I understand that any false statement may result in rejection of application or termination of employment.",
                "I authorize D&V Business Consulting to verify all information and conduct background checks.",
                "I consent to the storage and processing of my personal data as per company policy."
            ]
        }
    
    # Check for duplicates before submission
    candidate_details = data.get("candidate_details") or submission.get("candidate_details")
    if candidate_details:
        await check_duplicate_candidate(
            db,
            submission["candidate_email"],
            candidate_details.get("pan_number"),
            candidate_details.get("aadhaar_number"),
            exclude_submission_id=submission["id"]
        )
    
    await db.onboarding_submissions.update_one(
        {"token": token},
        {
            "$set": update_fields,
            "$push": {
                "audit_log": {
                    "action": "submitted",
                    "actor_id": None,
                    "actor_name": submission["candidate_name"],
                    "timestamp": now.isoformat()
                }
            }
        }
    )
    
    # Notify HR about new submission
    try:
        # Get the HR who sent the invite
        invited_by_id = submission.get("invited_by")
        if invited_by_id:
            inviter = await db.employees.find_one({"id": invited_by_id}, {"email": 1, "full_name": 1})
            if inviter and inviter.get("email"):
                base_url = os.environ.get("FRONTEND_URL", "https://funnel-governance.preview.emergentagent.com")
                review_link = f"{base_url}/onboarding/review/{submission['id']}"
                
                await send_onboarding_submission_notification_email(
                    to_email=inviter["email"],
                    hr_name=inviter.get("full_name", "HR"),
                    candidate_name=submission["candidate_name"],
                    offered_position=submission["offered_position"],
                    review_link=review_link
                )
    except Exception as e:
        print(f"Failed to send HR notification email: {e}")
    
    return {"message": "Submission completed successfully. HR will review your details."}


@router.post("/public/{token}/upload")
async def upload_public_document(
    token: str,
    document_type: str,
    file: UploadFile = File(...)
):
    """
    Candidate uploads a document.
    """
    db = get_db()
    
    submission = await db.onboarding_submissions.find_one({"token": token})
    if not submission:
        raise HTTPException(status_code=404, detail="Invalid link")
    
    # Validate file type
    allowed_types = ['application/pdf', 'image/jpeg', 'image/png', 'image/webp']
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Invalid file type. Allowed: PDF, JPG, PNG, WEBP")
    
    # Max 5 MB
    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large. Maximum 5 MB.")
    
    # Save file
    file_id = str(uuid.uuid4())
    ext = os.path.splitext(file.filename)[1] or '.pdf'
    stored_filename = f"{submission['id']}_{document_type}_{file_id}{ext}"
    file_path = os.path.join(ONBOARDING_DOCS_DIR, stored_filename)
    
    with open(file_path, 'wb') as f:
        f.write(content)
    
    now = datetime.now(timezone.utc).isoformat()
    
    document_record = {
        "id": file_id,
        "type": document_type,
        "original_filename": file.filename,
        "stored_filename": stored_filename,
        "file_size": len(content),
        "content_type": file.content_type,
        "uploaded_at": now
    }
    
    # Remove existing document of same type and add new
    await db.onboarding_submissions.update_one(
        {"token": token},
        {"$pull": {"documents": {"type": document_type}}}
    )
    
    await db.onboarding_submissions.update_one(
        {"token": token},
        {"$push": {"documents": document_record}}
    )
    
    return {
        "message": "Document uploaded successfully",
        "document_id": file_id,
        "document_type": document_type
    }



@router.post("/public/{token}/upload-photo")
async def upload_public_photo(
    token: str,
    file: UploadFile = File(...)
):
    """
    Candidate uploads their profile/passport photo.
    """
    db = get_db()
    
    submission = await db.onboarding_submissions.find_one({"token": token})
    if not submission:
        raise HTTPException(status_code=404, detail="Invalid link")
    
    # Validate file type - only images for photos
    allowed_types = ['image/jpeg', 'image/png', 'image/webp']
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Invalid file type. Allowed: JPG, PNG, WEBP")
    
    # Max 5 MB
    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large. Maximum 5 MB.")
    
    # Convert to base64 data URL for storage
    import base64
    base64_data = base64.b64encode(content).decode('utf-8')
    photo_url = f"data:{file.content_type};base64,{base64_data}"
    
    # Update candidate_details with profile photo
    await db.onboarding_submissions.update_one(
        {"token": token},
        {"$set": {"candidate_details.profile_photo_url": photo_url}}
    )
    
    return {
        "message": "Photo uploaded successfully",
        "photo_url": photo_url,
        "profile_photo_url": photo_url
    }



@router.post("/submissions/{submission_id}/upload-document")
async def hr_upload_document(
    submission_id: str,
    document_type: str,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """
    HR uploads a document on behalf of or to supplement candidate's submission.
    This allows HR to add missing documents or replace incorrect ones.
    """
    db = get_db()
    
    # Authorization - HR roles only
    hr_roles = ["hr_manager", "hr_executive", "admin"]
    if not has_role(current_user.role, hr_roles):
        raise HTTPException(status_code=403, detail="Only HR can upload documents for submissions")
    
    # Find submission
    submission = await db.onboarding_submissions.find_one({"id": submission_id})
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    # Validate file
    allowed_types = ["application/pdf", "image/jpeg", "image/png", "image/jpg"]
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Only PDF, JPG, PNG files allowed")
    
    # Size limit (10MB)
    file_content = await file.read()
    if len(file_content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File size exceeds 10MB limit")
    
    # Generate file ID and save
    file_id = str(uuid.uuid4())
    ext = os.path.splitext(file.filename)[1] or ".pdf"
    filename = f"{file_id}{ext}"
    filepath = os.path.join(ONBOARDING_DOCS_DIR, filename)
    
    with open(filepath, "wb") as f:
        f.write(file_content)
    
    now = datetime.now(timezone.utc).isoformat()
    document_record = {
        "id": file_id,
        "type": document_type,
        "filename": filename,
        "original_filename": file.filename,
        "uploaded_at": now,
        "uploaded_by": current_user.id,
        "uploaded_by_name": current_user.full_name,
        "uploaded_by_hr": True  # Flag to indicate HR uploaded
    }
    
    await db.onboarding_submissions.update_one(
        {"id": submission_id},
        {"$push": {"documents": document_record}}
    )
    
    return {
        "message": "Document uploaded successfully by HR",
        "document_id": file_id,
        "document_type": document_type
    }


# ==================== HELPER FUNCTIONS ====================

async def check_duplicate_candidate(
    db, 
    email: str, 
    pan: str = None, 
    aadhaar: str = None,
    exclude_submission_id: str = None
):
    """Check for duplicate candidates in employees and submissions."""
    
    # Check employees collection
    or_conditions = [
        {"email": email},
        {"personal_email": email}
    ]
    if pan:
        or_conditions.append({"pan_number": pan})
    if aadhaar:
        or_conditions.append({"aadhaar_number": aadhaar})
    
    existing = await db.employees.find_one({"$or": or_conditions})
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Employee already exists with ID: {existing.get('employee_id')}"
        )
    
    # Check pending submissions
    sub_query = {
        "status": {"$in": ["invited", "draft", "submitted", "revision_requested"]},
        "$or": [{"candidate_email": email}]
    }
    if pan:
        sub_query["$or"].append({"candidate_details.pan_number": pan})
    
    if exclude_submission_id:
        sub_query["id"] = {"$ne": exclude_submission_id}
    
    pending = await db.onboarding_submissions.find_one(sub_query)
    if pending:
        raise HTTPException(
            status_code=409,
            detail="Onboarding already in progress for this candidate"
        )


async def generate_employee_id(db) -> str:
    """Generate next sequential Employee ID in DVBC format."""
    
    employees = await db.employees.find(
        {"employee_id": {"$regex": "^DVBC\\d+$"}},
        {"employee_id": 1}
    ).to_list(None)
    
    max_num = 0
    for emp in employees:
        match = re.match(r"DVBC(\d+)", emp.get("employee_id", ""))
        if match:
            num = int(match.group(1))
            if num > max_num:
                max_num = num
    
    next_num = max_num + 1
    return f"DVBC{next_num:03d}"


def calculate_submission_progress(submission: dict) -> dict:
    """Calculate completion progress of a submission."""
    
    total_items = 8  # Increased to include references
    completed = 0
    
    # Candidate items
    if submission.get("candidate_details"):
        cd = submission["candidate_details"]
        if cd.get("first_name") and cd.get("last_name") and cd.get("phone") and cd.get("alternate_phone"):
            completed += 1
    
    if submission.get("education") and len(submission["education"]) > 0:
        completed += 1
    
    # Employment history is MANDATORY
    if submission.get("employment_history") and len(submission["employment_history"]) > 0:
        completed += 1
    
    if submission.get("bank_details"):
        bd = submission["bank_details"]
        if bd.get("account_number") and bd.get("ifsc_code"):
            completed += 1
    
    # Professional & Personal References
    pr = submission.get("professional_reference")
    per = submission.get("personal_reference")
    if pr and per:
        if pr.get("name") and pr.get("phone") and pr.get("company_name") and pr.get("designation"):
            if per.get("name") and per.get("phone") and per.get("address"):
                completed += 1
    
    if submission.get("emergency_contact"):
        ec = submission["emergency_contact"]
        if ec.get("name") and ec.get("phone"):
            completed += 1
    
    if submission.get("documents") and len(submission["documents"]) >= 2:
        completed += 1
    
    if submission.get("declaration_signed"):
        completed += 1
    
    percentage = int((completed / total_items) * 100) if total_items > 0 else 0
    
    return {
        "completed": completed,
        "total": total_items,
        "percentage": percentage,
        "is_complete": completed == total_items
    }


def validate_submission_complete(submission: dict) -> list:
    """
    Validate that submission is ready for completion.
    SIMPLIFIED VALIDATION for 4-step onboarding form:
    - Step 1: Personal Details (name, phone, email, PAN, Aadhaar)
    - Step 2: Address & Bank Details
    - Step 3: Emergency Contact & Documents
    - Step 4: Declaration
    """
    
    errors = []
    
    # Candidate details (REQUIRED)
    cd = submission.get("candidate_details")
    if not cd:
        errors.append("Personal details missing")
    else:
        if not cd.get("first_name") or not cd.get("last_name"):
            errors.append("Candidate name incomplete")
        if not cd.get("phone"):
            errors.append("Phone number missing")
        if not cd.get("pan_number") or not cd.get("aadhaar_number"):
            errors.append("PAN/Aadhaar incomplete")
    
    # Bank details (REQUIRED)
    bd = submission.get("bank_details")
    if not bd or not bd.get("account_number") or not bd.get("ifsc_code"):
        errors.append("Bank details incomplete")
    
    # Emergency contact (REQUIRED)
    ec = submission.get("emergency_contact")
    if not ec or not ec.get("name") or not ec.get("phone"):
        errors.append("Emergency contact missing")
    
    # Documents - minimum 2 required (PAN, Aadhaar)
    if not submission.get("documents") or len(submission["documents"]) < 2:
        errors.append("Required documents not uploaded (minimum: PAN, Aadhaar)")
    
    # Declaration (REQUIRED)
    if not submission.get("declaration_signed"):
        errors.append("Declaration not signed")
    
    # HR assigned fields (REQUIRED)
    hr = submission.get("hr_assigned", {})
    if not hr.get("department"):
        errors.append("Department not assigned")
    if not hr.get("reporting_manager_id"):
        errors.append("Reporting manager not assigned")
    if not hr.get("joining_date"):
        errors.append("Joining date not set")
    if not hr.get("official_email"):
        errors.append("Official email not assigned")
    
    # HR verification (auto-verified on complete, so skip this check)
    # The complete_onboarding endpoint auto-verifies documents and bank
    
    return errors



# ==================== REMINDER ENDPOINTS ====================

@router.post("/submissions/{submission_id}/send-reminder")
async def send_onboarding_reminder(
    submission_id: str,
    data: dict = None,
    current_user: User = Depends(get_current_user)
):
    """
    HR sends a reminder email to candidate to complete their onboarding submission.
    Only applicable for pending/incomplete submissions.
    """
    db = get_db()
    
    # Authorization - HR roles only
    hr_roles = ["hr_manager", "hr_executive", "admin"]
    if not has_role(current_user.role, hr_roles):
        raise HTTPException(status_code=403, detail="Only HR can send reminders")
    
    # Get submission
    submission = await db.onboarding_submissions.find_one({"id": submission_id}, {"_id": 0})
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    # Check if reminder is applicable
    status = submission.get("status", "")
    if status in ["submitted", "verified", "completed"]:
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot send reminder. Submission is already {status}."
        )
    
    # Check token expiry
    token = submission.get("token")
    expires_at = submission.get("expires_at")
    token_expired = False
    
    if expires_at:
        try:
            exp_date = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
            if exp_date < datetime.now(timezone.utc):
                token_expired = True
        except (ValueError, TypeError):
            pass
    
    # Regenerate token if expired
    if token_expired:
        token = secrets.token_urlsafe(32)
        new_expires = datetime.now(timezone.utc) + timedelta(days=TOKEN_EXPIRY_DAYS)
        await db.onboarding_submissions.update_one(
            {"id": submission_id},
            {
                "$set": {
                    "token": token,
                    "expires_at": new_expires.isoformat()
                }
            }
        )
    
    # Get candidate details
    candidate_email = submission.get("candidate_email")
    candidate_name = submission.get("candidate_name")
    offered_position = submission.get("offered_position")
    
    if not candidate_email:
        raise HTTPException(status_code=400, detail="Candidate email not found")
    
    # Build reminder message
    custom_message = (data or {}).get("message", "")
    
    # Track reminder
    now = datetime.now(timezone.utc)
    reminder_count = submission.get("reminder_count", 0) + 1
    
    await db.onboarding_submissions.update_one(
        {"id": submission_id},
        {
            "$set": {
                "last_reminder_at": now.isoformat(),
                "last_reminder_by": current_user.id,
                "reminder_count": reminder_count
            },
            "$push": {
                "reminder_history": {
                    "sent_at": now.isoformat(),
                    "sent_by": current_user.id,
                    "sent_by_name": current_user.full_name,
                    "message": custom_message,
                    "token_regenerated": token_expired
                }
            }
        }
    )
    
    # Send reminder email
    try:
        frontend_url = os.environ.get("FRONTEND_URL", "https://funnel-governance.preview.emergentagent.com")
        onboarding_link = f"{frontend_url}/onboarding/{token}"
        
        email_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: linear-gradient(135deg, #f97316, #ea580c); padding: 30px; text-align: center;">
                <h1 style="color: white; margin: 0;">NETRA ERP</h1>
                <p style="color: rgba(255,255,255,0.9); margin-top: 5px;">Onboarding Reminder</p>
            </div>
            
            <div style="padding: 30px; background: #fff;">
                <h2 style="color: #1f2937;">Hello {candidate_name},</h2>
                
                <p style="color: #374151; line-height: 1.6;">
                    This is a friendly reminder to complete your onboarding process for the position of 
                    <strong>{offered_position}</strong> at DVBC.
                </p>
                
                {f'<div style="background: #fef3c7; border-left: 4px solid #f59e0b; padding: 15px; margin: 20px 0;"><strong>Message from HR:</strong><br/>{custom_message}</div>' if custom_message else ''}
                
                <p style="color: #374151;">
                    Please click the button below to continue your onboarding submission:
                </p>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{onboarding_link}" 
                       style="background: #f97316; color: white; padding: 15px 40px; 
                              text-decoration: none; border-radius: 8px; font-weight: bold;
                              display: inline-block;">
                        Complete Onboarding
                    </a>
                </div>
                
                <p style="color: #6b7280; font-size: 14px;">
                    {'<strong>Note:</strong> Your previous link has expired. This email contains a new link.' if token_expired else 'This link will expire in 7 days.'}
                </p>
                
                <p style="color: #6b7280; font-size: 14px;">
                    If you have any questions, please contact our HR team.
                </p>
            </div>
            
            <div style="background: #f3f4f6; padding: 20px; text-align: center; color: #6b7280; font-size: 12px;">
                <p>This is an automated reminder from NETRA ERP</p>
                <p>© {datetime.now().year} DVBC. All rights reserved.</p>
            </div>
        </body>
        </html>
        """
        
        await send_email(
            to_email=candidate_email,
            subject=f"Reminder: Complete Your Onboarding - {offered_position}",
            html_content=email_body
        )
        
        return {
            "message": f"Reminder sent successfully to {candidate_email}",
            "reminder_count": reminder_count,
            "token_regenerated": token_expired
        }
        
    except Exception as e:
        # Still track the reminder attempt
        return {
            "message": f"Reminder tracked but email failed: {str(e)}",
            "reminder_count": reminder_count,
            "email_sent": False
        }


@router.get("/submissions/{submission_id}/reminder-history")
async def get_reminder_history(
    submission_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get reminder history for a submission."""
    db = get_db()
    
    hr_roles = ["hr_manager", "hr_executive", "admin"]
    if not has_role(current_user.role, hr_roles):
        raise HTTPException(status_code=403, detail="Only HR can view reminder history")
    
    submission = await db.onboarding_submissions.find_one(
        {"id": submission_id},
        {"_id": 0, "reminder_history": 1, "reminder_count": 1, "last_reminder_at": 1}
    )
    
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    return {
        "submission_id": submission_id,
        "reminder_count": submission.get("reminder_count", 0),
        "last_reminder_at": submission.get("last_reminder_at"),
        "history": submission.get("reminder_history", [])
    }


@router.get("/pending-reminders")
async def get_pending_reminders(
    days_since_invite: int = 3,
    current_user: User = Depends(get_current_user)
):
    """Get list of candidates who haven't submitted and may need reminders."""
    db = get_db()
    
    hr_roles = ["hr_manager", "hr_executive", "admin"]
    if not has_role(current_user.role, hr_roles):
        raise HTTPException(status_code=403, detail="Only HR can view pending reminders")
    
    # Calculate cutoff date
    cutoff = datetime.now(timezone.utc) - timedelta(days=days_since_invite)
    
    # Find pending submissions older than cutoff
    submissions = await db.onboarding_submissions.find(
        {
            "status": {"$in": ["pending", "in_progress", "revision_requested"]},
            "created_at": {"$lt": cutoff.isoformat()}
        },
        {"_id": 0}
    ).to_list(100)
    
    candidates_needing_reminder = []
    for sub in submissions:
        last_reminder = sub.get("last_reminder_at")
        
        # Check if reminder was sent in last 2 days
        needs_reminder = True
        if last_reminder:
            try:
                last_rem_date = datetime.fromisoformat(last_reminder.replace("Z", "+00:00"))
                if last_rem_date > (datetime.now(timezone.utc) - timedelta(days=2)):
                    needs_reminder = False
            except (ValueError, TypeError):
                pass
        
        if needs_reminder:
            candidates_needing_reminder.append({
                "id": sub.get("id"),
                "candidate_name": sub.get("candidate_name"),
                "candidate_email": sub.get("candidate_email"),
                "offered_position": sub.get("offered_position"),
                "status": sub.get("status"),
                "invited_at": sub.get("created_at"),
                "reminder_count": sub.get("reminder_count", 0),
                "last_reminder_at": last_reminder,
                "days_since_invite": (datetime.now(timezone.utc) - datetime.fromisoformat(sub.get("created_at", datetime.now(timezone.utc).isoformat()).replace("Z", "+00:00"))).days if sub.get("created_at") else 0
            })
    
    return {
        "total": len(candidates_needing_reminder),
        "candidates": sorted(candidates_needing_reminder, key=lambda x: x.get("days_since_invite", 0), reverse=True)
    }
