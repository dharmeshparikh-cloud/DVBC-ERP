"""
Onboarding Router - Self-Service Candidate Onboarding

This module handles the new self-service onboarding flow:
1. HR sends invite to candidate
2. Candidate fills form via public link (no login)
3. HR reviews, assigns dept/manager, verifies
4. On completion: Employee ID generated, record created
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
from .auth import get_current_user
from services.email_service import (
    send_email,
    send_onboarding_invite_email,
    send_onboarding_submission_notification_email,
    send_onboarding_revision_request_email,
    send_onboarding_complete_email
)

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
    base_url = os.environ.get("FRONTEND_URL", "https://dvbc-intake.preview.emergentagent.com")
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
    ).sort("invited_at", -1).to_list(100)
    
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
    
    # Only HR Manager or Admin can verify
    if current_user.role not in ["hr_manager", "admin"]:
        raise HTTPException(status_code=403, detail="Only HR Manager or Admin can verify documents")
    
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


@router.post("/submissions/{submission_id}/verify-bank")
async def verify_bank(
    submission_id: str,
    current_user: User = Depends(get_current_user)
):
    """HR Manager verifies bank details."""
    db = get_db()
    
    if current_user.role not in ["hr_manager", "admin"]:
        raise HTTPException(status_code=403, detail="Only HR Manager or Admin can verify bank details")
    
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
        base_url = os.environ.get("FRONTEND_URL", "https://dvbc-intake.preview.emergentagent.com")
        onboarding_link = f"{base_url}/onboarding/candidate/{submission['token']}"
        
        await send_email(
            to_email=submission["candidate_email"],
            subject="Action Required: Update your onboarding details",
            body=f"""
            Dear {submission['candidate_name']},
            
            Our HR team has reviewed your onboarding submission and requires some updates:
            
            Reason: {reason}
            
            Please click the link below to update your details:
            {onboarding_link}
            
            Best regards,
            DVBC HR Team
            """
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
    
    # Validate all required fields are complete
    validation_errors = validate_submission_complete(submission)
    if validation_errors:
        raise HTTPException(status_code=400, detail=f"Cannot complete: {', '.join(validation_errors)}")
    
    now = datetime.now(timezone.utc)
    
    # Generate Employee ID (DVBC format)
    employee_id = await generate_employee_id(db)
    
    # Create employee record
    candidate = submission["candidate_details"]
    hr_assigned = submission["hr_assigned"]
    bank_details = submission["bank_details"]
    
    employee_record_id = str(uuid.uuid4())
    
    employee = {
        "id": employee_record_id,
        "employee_id": employee_id,
        
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
                "employee_id_generated": employee_id,
                "employee_record_id": employee_record_id
            },
            "$push": {
                "audit_log": {
                    "action": "completed",
                    "actor_id": current_user.id,
                    "actor_name": current_user.full_name,
                    "timestamp": now.isoformat(),
                    "details": {"employee_id": employee_id}
                }
            }
        }
    )
    
    # Send welcome email to candidate
    try:
        await send_email(
            to_email=submission["candidate_email"],
            subject=f"Welcome to DVBC! Your Employee ID: {employee_id}",
            body=f"""
            Dear {candidate['first_name']},
            
            Congratulations! Your onboarding is now complete.
            
            Your Employee Details:
            - Employee ID: {employee_id}
            - Department: {hr_assigned['department']}
            - Designation: {hr_assigned['designation']}
            - Joining Date: {hr_assigned['joining_date']}
            - Official Email: {hr_assigned['official_email']}
            
            You will receive your portal login credentials separately.
            
            Welcome to the team!
            
            Best regards,
            DVBC HR Team
            """
        )
    except Exception as e:
        print(f"Failed to send welcome email: {e}")
    
    return {
        "message": "Onboarding completed successfully",
        "employee_id": employee_id,
        "employee_record_id": employee_record_id
    }


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
    expires_at = datetime.fromisoformat(submission["link_expires_at"].replace("Z", "+00:00"))
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
        "emergency_contact": submission["emergency_contact"],
        "documents": submission["documents"],
        "declaration_signed": submission["declaration_signed"],
        "revision_history": submission.get("revision_history", []),
        "progress": calculate_submission_progress(submission)
    }


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
    expires_at = datetime.fromisoformat(submission["link_expires_at"].replace("Z", "+00:00"))
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
    expires_at = datetime.fromisoformat(submission["link_expires_at"].replace("Z", "+00:00"))
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
    if "emergency_contact" in data:
        update_fields["emergency_contact"] = data["emergency_contact"]
    if "declaration_signed" in data:
        update_fields["declaration_signed"] = data["declaration_signed"]
    
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
                base_url = os.environ.get("FRONTEND_URL", "https://dvbc-intake.preview.emergentagent.com")
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
    
    total_items = 7
    completed = 0
    
    # Candidate items
    if submission.get("candidate_details"):
        cd = submission["candidate_details"]
        if cd.get("first_name") and cd.get("last_name") and cd.get("phone"):
            completed += 1
    
    if submission.get("education") and len(submission["education"]) > 0:
        completed += 1
    
    if submission.get("bank_details"):
        bd = submission["bank_details"]
        if bd.get("account_number") and bd.get("ifsc_code"):
            completed += 1
    
    if submission.get("emergency_contact"):
        ec = submission["emergency_contact"]
        if ec.get("name") and ec.get("phone"):
            completed += 1
    
    if submission.get("documents") and len(submission["documents"]) >= 2:
        completed += 1
    
    if submission.get("declaration_signed"):
        completed += 1
    
    # Employment history is optional but counts
    if submission.get("employment_history") and len(submission["employment_history"]) > 0:
        completed += 1
    else:
        total_items -= 1  # Don't count if no history expected
    
    percentage = int((completed / total_items) * 100) if total_items > 0 else 0
    
    return {
        "completed": completed,
        "total": total_items,
        "percentage": percentage,
        "is_complete": completed == total_items
    }


def validate_submission_complete(submission: dict) -> list:
    """Validate that submission is ready for completion."""
    
    errors = []
    
    # Candidate details
    cd = submission.get("candidate_details")
    if not cd:
        errors.append("Personal details missing")
    elif not cd.get("first_name") or not cd.get("last_name"):
        errors.append("Candidate name incomplete")
    
    # Bank details
    bd = submission.get("bank_details")
    if not bd or not bd.get("account_number") or not bd.get("ifsc_code"):
        errors.append("Bank details incomplete")
    
    # Emergency contact
    ec = submission.get("emergency_contact")
    if not ec or not ec.get("name") or not ec.get("phone"):
        errors.append("Emergency contact missing")
    
    # Documents
    if not submission.get("documents") or len(submission["documents"]) < 2:
        errors.append("Required documents not uploaded")
    
    # Declaration
    if not submission.get("declaration_signed"):
        errors.append("Declaration not signed")
    
    # HR assigned fields
    hr = submission.get("hr_assigned", {})
    if not hr.get("department"):
        errors.append("Department not assigned")
    if not hr.get("reporting_manager_id"):
        errors.append("Reporting manager not assigned")
    if not hr.get("joining_date"):
        errors.append("Joining date not set")
    if not hr.get("official_email"):
        errors.append("Official email not assigned")
    
    # HR verification
    hv = submission.get("hr_verification", {})
    if not hv.get("documents_verified"):
        errors.append("Documents not verified by HR")
    if not hv.get("bank_verified"):
        errors.append("Bank details not verified by HR")
    
    return errors
