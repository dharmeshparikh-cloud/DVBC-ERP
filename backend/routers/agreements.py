"""
Agreements Router - Agreement creation, signing, payments, and approval workflow.
Sends email notification when agreement is created.
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from typing import Optional, List
from datetime import datetime, timezone
import uuid
import os
from pydantic import BaseModel, Field
from .deps import (
    get_db, MANAGER_ROLES, SALES_MANAGER_ROLES, SALES_ROLES, ADMIN_ROLES, 
    SENIOR_CONSULTING_ROLES, require_roles, get_role_group, has_role
)
from .models import User
from .deps import get_current_user
from services.email_service import send_email
from services.funnel_notifications import agreement_created_email, get_agreement_notification_emails

router = APIRouter(prefix="/agreements", tags=["Agreements"])

APP_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://sales-meeting-fix.preview.emergentagent.com").replace("/api", "")

# Role constants for this router - now using RBAC service as source of truth
AGREEMENT_VIEW_ROLES = SALES_ROLES + SENIOR_CONSULTING_ROLES  # sales, admin, principal_consultant
AGREEMENT_CREATE_ROLES = SALES_ROLES  # All sales roles including executive can create agreements
# AGREEMENT_APPROVE_ROLES now fetched from database via get_role_group("AGREEMENT_APPROVE_ROLES")


class AgreementSection(BaseModel):
    title: str
    content: str
    order: int = 0


class AgreementCreate(BaseModel):
    lead_id: str
    title: Optional[str] = "Consulting Services Agreement"
    client_name: str
    client_address: Optional[str] = ""
    client_email: Optional[str] = ""
    client_phone: Optional[str] = ""
    services_description: Optional[str] = ""
    total_value: float = 0
    payment_terms: Optional[str] = ""
    start_date: Optional[str] = None
    duration_months: Optional[int] = 12
    sections: Optional[List[dict]] = []


class RejectionRequest(BaseModel):
    reason: str


class AgreementSignatureData(BaseModel):
    signature_image: Optional[str] = None
    signed_by_name: str
    signed_by_designation: Optional[str] = ""
    signed_date: Optional[str] = None


class SendToClientRequest(BaseModel):
    email: str
    subject: Optional[str] = "Agreement for Review"
    message: Optional[str] = ""


class AgreementPaymentRecord(BaseModel):
    amount: float
    payment_date: str
    payment_method: str  # cheque, neft, upi, rtgs
    reference_number: Optional[str] = ""
    notes: Optional[str] = ""


@router.post("")
async def create_agreement(
    data: AgreementCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    """
    Create a new agreement.
    
    ACCESS: All sales roles (including Sales Executive) can create agreements.
    
    FUNNEL PREREQUISITE: Quotation must exist for this lead.
    
    WORKFLOW:
    1. Sales Executive creates agreement → status: 'draft'
    2. Sales Executive reviews and submits for approval → status: 'pending_approval'
    3. ONLY Principal Consultant or Admin can approve → status: 'approved'
    4. Only after PC approval can the agreement be sent to client
    
    NOTE: Agreements start in 'draft' status. They must be explicitly submitted
    for approval before PC/Admin can approve them.
    """
    db = get_db()
    
    # Role-based access check - all sales roles can create agreements
    if current_user.role not in AGREEMENT_CREATE_ROLES:
        raise HTTPException(status_code=403, detail="Access denied. Only sales roles can create agreements.")
    
    lead = await db.leads.find_one({"id": data.lead_id}, {"_id": 0})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    # FUNNEL VALIDATION: Check if quotation exists for this lead
    quotation = await db.quotations.find_one({"lead_id": data.lead_id}, {"_id": 0, "id": 1})
    if not quotation:
        raise HTTPException(
            status_code=400,
            detail="Cannot create agreement: A Quotation must be created first. Please complete the Quotation step in the sales funnel."
        )
    
    agreement_id = str(uuid.uuid4())
    agreement_number = f"AGR-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{str(uuid.uuid4())[:4].upper()}"
    
    # All agreements start as 'draft' - must be submitted for PC/Admin approval
    # Only after approval can they be sent to client
    initial_status = "draft"
    
    # Calculate end date
    from dateutil.relativedelta import relativedelta
    start = datetime.strptime(data.start_date, "%Y-%m-%d") if data.start_date else datetime.now(timezone.utc)
    end_date = (start + relativedelta(months=data.duration_months or 12)).strftime("%Y-%m-%d")
    
    agreement_doc = {
        "id": agreement_id,
        "agreement_number": agreement_number,
        "lead_id": data.lead_id,
        "title": data.title,
        "client_name": data.client_name or lead.get("company", ""),
        "client_address": data.client_address,
        "client_email": data.client_email or lead.get("email", ""),
        "client_phone": data.client_phone or lead.get("phone", ""),
        "services_description": data.services_description,
        "total_value": data.total_value,
        "payment_terms": data.payment_terms,
        "start_date": data.start_date,
        "end_date": end_date,
        "duration_months": data.duration_months,
        "sections": data.sections or [],
        "status": initial_status,
        "requires_admin_approval": current_user.role not in ADMIN_ROLES,
        "payments": [],
        "total_paid": 0,
        "created_by": current_user.id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.agreements.insert_one(agreement_doc)
    agreement_doc.pop("_id", None)
    
    # Client email
    client_email = data.client_email or lead.get("email", "")
    
    # Send email notification in background
    # Agreement: Manager + Manager's Manager + Client
    async def send_agreement_notification():
        try:
            # Get manager + manager's manager emails (NOT HR)
            manager_emails = await get_agreement_notification_emails(db)
            
            email_data = agreement_created_email(
                lead_name=f"{lead.get('first_name', '')} {lead.get('last_name', '')}".strip(),
                company=lead.get("company", "Unknown"),
                agreement_number=agreement_number,
                agreement_id=agreement_id,
                agreement_type=data.title or "Consulting Services Agreement",
                total_value=data.total_value,
                currency="INR",
                start_date=data.start_date or "TBD",
                end_date=end_date,
                status=initial_status,
                salesperson_name=current_user.full_name,
                client_email=client_email,
                app_url=APP_URL
            )
            
            # Send to managers
            for email in manager_emails:
                await send_email(
                    to_email=email,
                    subject=email_data["subject"],
                    html_content=email_data["html"],
                    plain_content=email_data["plain"]
                )
            
            # Send to client if email exists
            if client_email:
                await send_email(
                    to_email=client_email,
                    subject=f"Your Service Agreement #{agreement_number} from DVBC",
                    html_content=email_data["html"],
                    plain_content=email_data["plain"]
                )
        except Exception as e:
            print(f"Failed to send agreement notification: {e}")
    
    background_tasks.add_task(send_agreement_notification)
    
    return agreement_doc


@router.get("/{agreement_id}/full")
async def get_agreement_full(agreement_id: str, current_user: User = Depends(get_current_user)):
    """Get full agreement details"""
    db = get_db()
    
    agreement = await db.agreements.find_one({"id": agreement_id}, {"_id": 0})
    if not agreement:
        raise HTTPException(status_code=404, detail="Agreement not found")
    
    lead = await db.leads.find_one({"id": agreement.get("lead_id")}, {"_id": 0})
    
    return {
        "agreement": agreement,
        "lead": lead
    }


@router.get("")
async def get_agreements(
    status: Optional[str] = None,
    lead_id: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    sort_field: str = "created_at",
    sort_direction: str = "desc",
    search: Optional[str] = None,
    agreement_type: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get all agreements with optional filters, pagination, and sorting.
    Access: sales, admin, principal_consultant"""
    db = get_db()
    
    # Role-based access check
    if current_user.role not in AGREEMENT_VIEW_ROLES:
        raise HTTPException(status_code=403, detail="Access denied. You don't have permission to view agreements.")
    
    query = {}
    if status:
        query["status"] = status
    if lead_id:
        query["lead_id"] = lead_id
    if agreement_type:
        query["agreement_type"] = agreement_type
    if search:
        query["$or"] = [
            {"agreement_number": {"$regex": search, "$options": "i"}},
            {"client_name": {"$regex": search, "$options": "i"}},
        ]
    
    # Sorting
    sort_dir = -1 if sort_direction == "desc" else 1
    allowed_sort_fields = ["created_at", "agreement_number", "status", "agreement_type", "project_tenure_months", "total_value"]
    if sort_field not in allowed_sort_fields:
        sort_field = "created_at"
    
    # Count total
    total = await db.agreements.count_documents(query)
    
    # Paginated query
    skip = (page - 1) * page_size
    agreements = await db.agreements.find(query, {"_id": 0}).sort(sort_field, sort_dir).skip(skip).limit(page_size).to_list(page_size)
    
    return {
        "data": agreements,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size
    }


@router.patch("/{agreement_id}/submit-for-approval")
async def submit_agreement_for_approval(agreement_id: str, current_user: User = Depends(get_current_user)):
    """
    Submit a draft agreement for Principal Consultant/Admin approval.
    
    ACCESS: Sales roles who created the agreement can submit it.
    
    WORKFLOW:
    - Agreement must be in 'draft' status
    - Changes status to 'pending_approval'
    - Only then can PC/Admin approve it
    """
    db = get_db()
    
    agreement = await db.agreements.find_one({"id": agreement_id}, {"_id": 0})
    if not agreement:
        raise HTTPException(status_code=404, detail="Agreement not found")
    
    if agreement.get("status") != "draft":
        raise HTTPException(status_code=400, detail=f"Only draft agreements can be submitted. Current status: {agreement.get('status')}")
    
    await db.agreements.update_one(
        {"id": agreement_id},
        {
            "$set": {
                "status": "pending_approval",
                "submitted_for_approval_by": current_user.id,
                "submitted_for_approval_by_name": current_user.full_name,
                "submitted_for_approval_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    return {"message": "Agreement submitted for Principal Consultant approval", "status": "pending_approval"}


@router.patch("/{agreement_id}/approve")
async def approve_agreement(agreement_id: str, current_user: User = Depends(get_current_user)):
    """
    Approve an agreement.
    
    ACCESS: ONLY Principal Consultant or Admin can approve.
    No other managers (sales_manager, sr_manager, etc.) can approve.
    
    WORKFLOW:
    - Agreement must be in 'pending_approval' status (submitted by Sales)
    - After approval, agreement can be sent to client
    """
    db = get_db()
    
    # RBAC Migration: Using database-driven role check with fail-closed
    approve_roles = get_role_group("AGREEMENT_APPROVE_ROLES", fail_closed=True)
    if not approve_roles or not has_role(current_user.role, approve_roles):
        raise HTTPException(status_code=403, detail="Only Principal Consultant or Admin can approve agreements")
    
    agreement = await db.agreements.find_one({"id": agreement_id}, {"_id": 0})
    if not agreement:
        raise HTTPException(status_code=404, detail="Agreement not found")
    
    if agreement.get("status") != "pending_approval":
        raise HTTPException(status_code=400, detail="Agreement must be submitted for approval first. Current status: " + agreement.get("status", "unknown"))
    
    await db.agreements.update_one(
        {"id": agreement_id},
        {
            "$set": {
                "status": "approved",
                "approved_by": current_user.id,
                "approved_by_name": current_user.full_name,
                "approved_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    return {"message": "Agreement approved by Principal Consultant", "status": "approved"}


@router.patch("/{agreement_id}/reject")
async def reject_agreement(agreement_id: str, data: RejectionRequest, current_user: User = Depends(get_current_user)):
    """
    Reject an agreement.
    
    ACCESS: ONLY Principal Consultant or Admin can reject.
    
    WORKFLOW:
    - Agreement goes back to 'rejected' status
    - Sales can edit and resubmit after addressing feedback
    """
    db = get_db()
    
    # RBAC Migration: Using database-driven role check with fail-closed
    approve_roles = get_role_group("AGREEMENT_APPROVE_ROLES", fail_closed=True)
    if not approve_roles or not has_role(current_user.role, approve_roles):
        raise HTTPException(status_code=403, detail="Only Principal Consultant or Admin can reject agreements")
    
    agreement = await db.agreements.find_one({"id": agreement_id}, {"_id": 0})
    if not agreement:
        raise HTTPException(status_code=404, detail="Agreement not found")
    
    await db.agreements.update_one(
        {"id": agreement_id},
        {
            "$set": {
                "status": "rejected",
                "rejection_reason": data.reason,
                "rejected_by": current_user.id,
                "rejected_by_name": current_user.full_name,
                "rejected_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    return {"message": "Agreement rejected", "status": "rejected"}


@router.get("/pending-approval")
async def get_pending_agreements(current_user: User = Depends(get_current_user)):
    """Get agreements pending approval"""
    db = get_db()
    
    if current_user.role not in MANAGER_ROLES:
        raise HTTPException(status_code=403, detail="Only managers can view pending agreements")
    
    agreements = await db.agreements.find(
        {"status": "pending_approval"},
        {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    
    return agreements


@router.post("/{agreement_id}/sign")
async def sign_agreement(agreement_id: str, data: AgreementSignatureData, current_user: User = Depends(get_current_user)):
    """Record agreement signature — requires manager/admin/sales role"""
    if current_user.role not in ADMIN_ROLES and current_user.role not in SALES_MANAGER_ROLES and current_user.role not in MANAGER_ROLES:
        raise HTTPException(status_code=403, detail="Not authorized to sign agreements")
    db = get_db()
    
    agreement = await db.agreements.find_one({"id": agreement_id}, {"_id": 0})
    if not agreement:
        raise HTTPException(status_code=404, detail="Agreement not found")
    
    if agreement.get("status") not in ["approved", "sent_to_client"]:
        raise HTTPException(status_code=400, detail="Agreement must be approved before signing")
    
    await db.agreements.update_one(
        {"id": agreement_id},
        {
            "$set": {
                "status": "signed",
                "signature_image": data.signature_image,
                "signed_by_name": data.signed_by_name,
                "signed_by_designation": data.signed_by_designation,
                "signed_date": data.signed_date or datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                "signed_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    return {"message": "Agreement signed", "status": "signed"}


@router.post("/{agreement_id}/send-to-client")
async def send_agreement_to_client(agreement_id: str, data: SendToClientRequest, current_user: User = Depends(get_current_user)):
    """Send agreement to client for review.
    IMPORTANT: All client-facing communications require Principal Consultant approval.
    Only Principal Consultant or Admin can send agreements to clients."""
    db = get_db()
    
    # RBAC Migration: Using database-driven role check with fail-closed
    approve_roles = get_role_group("AGREEMENT_APPROVE_ROLES", fail_closed=True)
    if not approve_roles or not has_role(current_user.role, approve_roles):
        raise HTTPException(
            status_code=403, 
            detail="Only Principal Consultant can send client-facing communications. Please request PC approval."
        )
    
    agreement = await db.agreements.find_one({"id": agreement_id}, {"_id": 0})
    if not agreement:
        raise HTTPException(status_code=404, detail="Agreement not found")
    
    if agreement.get("status") not in ["approved", "draft"]:
        raise HTTPException(status_code=400, detail="Agreement must be approved or in draft to send")
    
    await db.agreements.update_one(
        {"id": agreement_id},
        {
            "$set": {
                "status": "sent_to_client",
                "sent_to_email": data.email,
                "sent_at": datetime.now(timezone.utc).isoformat(),
                "sent_by": current_user.id,
                "sent_by_name": current_user.full_name,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    return {"message": "Agreement sent to client", "email": data.email}


@router.post("/{agreement_id}/upload-signed")
async def upload_signed_agreement(agreement_id: str, data: dict, current_user: User = Depends(get_current_user)):
    """Upload signed agreement document"""
    db = get_db()
    
    agreement = await db.agreements.find_one({"id": agreement_id}, {"_id": 0})
    if not agreement:
        raise HTTPException(status_code=404, detail="Agreement not found")
    
    file_url = data.get("file_url")
    if not file_url:
        raise HTTPException(status_code=400, detail="file_url is required")
    
    await db.agreements.update_one(
        {"id": agreement_id},
        {
            "$set": {
                "status": "signed",
                "signed_document_url": file_url,
                "signed_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    return {"message": "Signed agreement uploaded", "status": "signed"}


@router.post("/{agreement_id}/record-payment")
async def record_agreement_payment(agreement_id: str, data: AgreementPaymentRecord, current_user: User = Depends(get_current_user)):
    """Record a payment against agreement — requires finance/admin/sales manager role"""
    allowed = ADMIN_ROLES + list(SALES_MANAGER_ROLES) + list(MANAGER_ROLES)
    if current_user.role not in allowed:
        raise HTTPException(status_code=403, detail="Not authorized to record payments")
    db = get_db()
    
    agreement = await db.agreements.find_one({"id": agreement_id}, {"_id": 0})
    if not agreement:
        raise HTTPException(status_code=404, detail="Agreement not found")
    
    payment_id = str(uuid.uuid4())
    payment_record = {
        "id": payment_id,
        "amount": data.amount,
        "payment_date": data.payment_date,
        "payment_method": data.payment_method,
        "reference_number": data.reference_number,
        "notes": data.notes,
        "recorded_by": current_user.id,
        "recorded_at": datetime.now(timezone.utc).isoformat()
    }
    
    new_total_paid = agreement.get("total_paid", 0) + data.amount
    
    await db.agreements.update_one(
        {"id": agreement_id},
        {
            "$push": {"payments": payment_record},
            "$set": {
                "total_paid": new_total_paid,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    return {
        "message": "Payment recorded",
        "payment_id": payment_id,
        "total_paid": new_total_paid,
        "balance": agreement.get("total_value", 0) - new_total_paid
    }


@router.get("/{agreement_id}/payments")
async def get_agreement_payments(agreement_id: str, current_user: User = Depends(get_current_user)):
    """Get all payments for an agreement"""
    db = get_db()
    
    agreement = await db.agreements.find_one({"id": agreement_id}, {"_id": 0, "payments": 1, "total_value": 1, "total_paid": 1})
    if not agreement:
        raise HTTPException(status_code=404, detail="Agreement not found")
    
    return {
        "payments": agreement.get("payments", []),
        "total_value": agreement.get("total_value", 0),
        "total_paid": agreement.get("total_paid", 0),
        "balance": agreement.get("total_value", 0) - agreement.get("total_paid", 0)
    }


@router.get("/{agreement_id}/export")
async def export_agreement(agreement_id: str, current_user: User = Depends(get_current_user)):
    """Export agreement data for document generation"""
    db = get_db()
    
    agreement = await db.agreements.find_one({"id": agreement_id}, {"_id": 0})
    if not agreement:
        raise HTTPException(status_code=404, detail="Agreement not found")
    
    lead = await db.leads.find_one({"id": agreement.get("lead_id")}, {"_id": 0})
    
    return {
        "agreement": agreement,
        "lead": lead,
        "export_date": datetime.now(timezone.utc).isoformat()
    }


@router.get("/{agreement_id}/download")
async def download_agreement(agreement_id: str, format: str = "pdf", current_user: User = Depends(get_current_user)):
    """Get download URL for agreement document"""
    db = get_db()
    
    agreement = await db.agreements.find_one({"id": agreement_id}, {"_id": 0})
    if not agreement:
        raise HTTPException(status_code=404, detail="Agreement not found")
    
    return {
        "agreement_id": agreement_id,
        "format": format,
        "message": "Document generation endpoint - requires document_generator integration"
    }
