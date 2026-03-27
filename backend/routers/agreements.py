"""
Agreements Router - Agreement creation, signing, payments, and approval workflow.
Sends email notification when agreement is created.
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from typing import Optional, List
from datetime import datetime, timezone
from utils.timezone import today_ist, current_month_ist, now_ist
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

APP_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://erp-governance-hub-3.preview.emergentagent.com").replace("/api", "")

# RBAC: Role-based access for agreements
# TODO: Make configurable via Role & Permission page
# Principal Consultant: Full access
# Senior Consultant: View access for own agreements + reportees
# Consultant: No access
AGREEMENT_FULL_ACCESS_ROLES = ['executive', 'sales_manager', 'manager', 'admin', 'principal_consultant']
AGREEMENT_VIEW_ROLES = AGREEMENT_FULL_ACCESS_ROLES + ['senior_consultant']
AGREEMENT_CREATE_ROLES = SALES_ROLES  # All sales roles including executive can create agreements
# AGREEMENT_APPROVE_ROLES now fetched from database via get_role_group("AGREEMENT_APPROVE_ROLES")


class AgreementSection(BaseModel):
    title: str
    content: str
    order: int = 0


class AgreementCreate(BaseModel):
    lead_id: str
    quotation_id: Optional[str] = None
    title: Optional[str] = "Consulting Services Agreement"
    client_name: Optional[str] = None
    client_address: Optional[str] = ""
    client_email: Optional[str] = ""
    client_phone: Optional[str] = ""
    services_description: Optional[str] = ""
    total_value: float = 0
    payment_terms: Optional[str] = ""
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    duration_months: Optional[int] = 12
    sections: Optional[List[dict]] = []
    agreement_type: Optional[str] = "standard"
    special_conditions: Optional[str] = ""
    meeting_frequency: Optional[str] = "Monthly"
    project_tenure_months: Optional[int] = 12
    team_deployment: Optional[List[dict]] = []


class RejectionRequest(BaseModel):
    reason: str


class AgreementSignatureData(BaseModel):
    signature_image: Optional[str] = None
    signed_by_name: Optional[str] = ""
    signed_by_designation: Optional[str] = ""
    signed_date: Optional[str] = None
    signer_name: Optional[str] = None
    signer_designation: Optional[str] = None
    signer_email: Optional[str] = None
    signature_date: Optional[str] = None
    signed_at: Optional[str] = None


class SendToClientRequest(BaseModel):
    email: Optional[str] = None
    client_email: Optional[str] = None
    client_name: Optional[str] = None
    subject: Optional[str] = "Agreement for Review"
    message: Optional[str] = ""


class SendAgreementEmailRequest(BaseModel):
    recipient_email: str
    recipient_name: Optional[str] = ""


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
    Create a new agreement — immediately active (no approval flow).
    
    FUNNEL PREREQUISITE: Quotation must exist for this lead.
    All data is inherited from Lead + Pricing Plan + SOW + Quotation.
    """
    db = get_db()
    
    # Role-based access check
    if current_user.role not in AGREEMENT_CREATE_ROLES:
        raise HTTPException(status_code=403, detail="Access denied. Only sales roles can create agreements.")
    
    lead = await db.leads.find_one({"id": data.lead_id}, {"_id": 0})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    # Validate start date is not in the past
    if data.start_date:
        today_str = now_ist().strftime("%Y-%m-%d")
        if data.start_date < today_str:
            raise HTTPException(status_code=400, detail="Agreement start date cannot be earlier than today")
    
    # FUNNEL VALIDATION: Check if quotation exists for this lead
    quotation = await db.quotations.find_one({"lead_id": data.lead_id}, {"_id": 0})
    if not quotation:
        raise HTTPException(
            status_code=400,
            detail="Cannot create agreement: A Quotation must be created first."
        )
    
    if data.quotation_id:
        specific_quotation = await db.quotations.find_one({"id": data.quotation_id}, {"_id": 0})
        if specific_quotation:
            quotation = specific_quotation
    
    # Get pricing plan for inherited data
    pricing_plan = None
    if quotation.get("pricing_plan_id"):
        pricing_plan = await db.pricing_plans.find_one({"id": quotation["pricing_plan_id"]}, {"_id": 0})
    if not pricing_plan:
        pricing_plan = await db.pricing_plans.find_one({"lead_id": data.lead_id}, {"_id": 0})
    
    # Get SOW for inherited data
    sow = None
    if pricing_plan:
        sow = await db.enhanced_sow.find_one({"pricing_plan_id": pricing_plan.get("id")}, {"_id": 0})
    if not sow:
        sow = await db.enhanced_sow.find_one({"lead_id": data.lead_id}, {"_id": 0})
    
    agreement_id = str(uuid.uuid4())
    agreement_number = f"AGR-{now_ist().strftime('%Y%m%d')}-{str(uuid.uuid4())[:4].upper()}"
    
    # Inherit from pricing plan
    tenure = data.project_tenure_months or (pricing_plan.get("tenure_months") if pricing_plan else None) or data.duration_months or 12
    total_value = data.total_value or (pricing_plan.get("total_amount") if pricing_plan else None) or quotation.get("grand_total") or quotation.get("total") or quotation.get("total_amount") or 0
    team_deployment = data.team_deployment or (pricing_plan.get("team_deployment") if pricing_plan else []) or []
    payment_schedule = (pricing_plan.get("payment_plan") if pricing_plan else None) or {}
    start_date = data.start_date or (pricing_plan.get("payment_plan", {}).get("start_date") if pricing_plan else None) or now_ist().strftime("%Y-%m-%d")
    
    from dateutil.relativedelta import relativedelta
    start = datetime.strptime(start_date, "%Y-%m-%d") if start_date else datetime.now(timezone.utc)
    end_date_str = data.end_date or (start + relativedelta(months=tenure)).strftime("%Y-%m-%d")
    
    # SSOT: Client fields from Lead
    client_name = lead.get("company", "") or f"{lead.get('first_name', '')} {lead.get('last_name', '')}".strip()
    client_email = lead.get("email", "")
    client_phone = lead.get("phone", "") or lead.get("mobile", "")
    client_address = lead.get("address", "") or lead.get("company_address", "")
    client_gstin = lead.get("gstin", "") or lead.get("gst_number", "")
    
    # SOW scopes
    sow_scopes = []
    if sow:
        sow_scopes = sow.get("scopes") or sow.get("scope_items") or sow.get("items") or []
    
    agreement_doc = {
        "id": agreement_id,
        "agreement_number": agreement_number,
        "lead_id": data.lead_id,
        "quotation_id": data.quotation_id or quotation.get("id"),
        "pricing_plan_id": pricing_plan.get("id") if pricing_plan else None,
        "sow_id": sow.get("id") if sow else None,
        "title": data.title or f"Service Agreement - {client_name}",
        "client_name": client_name,
        "client_address": client_address,
        "client_email": client_email,
        "client_phone": client_phone,
        "client_gstin": client_gstin,
        "services_description": data.services_description,
        "total_value": total_value,
        "payment_terms": data.payment_terms,
        "payment_schedule": payment_schedule,
        "start_date": start_date,
        "end_date": end_date_str,
        "duration_months": tenure,
        "project_tenure_months": tenure,
        "sections": data.sections or [],
        "agreement_type": data.agreement_type or "standard",
        "special_conditions": data.special_conditions or "",
        "meeting_frequency": data.meeting_frequency or "Monthly",
        "team_deployment": team_deployment,
        "sow_scopes": sow_scopes,
        "status": "active",
        "payments": [],
        "total_paid": 0,
        "created_by": current_user.id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.agreements.insert_one(agreement_doc)
    agreement_doc.pop("_id", None)
    
    # Client email already set from Lead (SSOT)
    
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
                end_date=end_date_str,
                status="active",
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
    """Get full agreement with all inherited data from Lead, Pricing Plan, SOW, Quotation."""
    db = get_db()
    
    agreement = await db.agreements.find_one({"id": agreement_id}, {"_id": 0})
    if not agreement:
        raise HTTPException(status_code=404, detail="Agreement not found")
    
    lead_id = agreement.get("lead_id")
    lead = await db.leads.find_one({"id": lead_id}, {"_id": 0}) if lead_id else None
    
    # Get pricing plan
    pricing_plan = None
    if agreement.get("pricing_plan_id"):
        pricing_plan = await db.pricing_plans.find_one({"id": agreement["pricing_plan_id"]}, {"_id": 0})
    if not pricing_plan and lead_id:
        pricing_plan = await db.pricing_plans.find_one({"lead_id": lead_id}, {"_id": 0})
    
    # Get SOW
    sow = None
    if agreement.get("sow_id"):
        sow = await db.enhanced_sow.find_one({"id": agreement["sow_id"]}, {"_id": 0})
    if not sow and pricing_plan:
        sow = await db.enhanced_sow.find_one({"pricing_plan_id": pricing_plan.get("id")}, {"_id": 0})
    if not sow and lead_id:
        sow = await db.enhanced_sow.find_one({"lead_id": lead_id}, {"_id": 0})
    
    # Get quotation
    quotation = None
    if agreement.get("quotation_id"):
        quotation = await db.quotations.find_one({"id": agreement["quotation_id"]}, {"_id": 0})
    if not quotation and lead_id:
        quotation = await db.quotations.find_one({"lead_id": lead_id}, {"_id": 0})
    
    # Get meetings for this lead
    meetings = []
    if lead_id:
        meetings = await db.meetings.find({"lead_id": lead_id}, {"_id": 0}).to_list(50)
    
    # Build comprehensive team deployment (from pricing plan if not on agreement)
    team_deployment = agreement.get("team_deployment") or []
    if not team_deployment and pricing_plan:
        team_deployment = pricing_plan.get("team_deployment") or []
    
    # Build SOW scopes
    sow_scopes = agreement.get("sow_scopes") or []
    if not sow_scopes and sow:
        sow_scopes = sow.get("scopes") or sow.get("scope_items") or sow.get("items") or []
    
    # Payment schedule
    payment_schedule = agreement.get("payment_schedule") or {}
    if not payment_schedule and pricing_plan:
        payment_schedule = pricing_plan.get("payment_plan") or {}
    
    # Get first installment amount from pricing plan payment schedule
    first_installment_amount = 0
    if payment_schedule:
        schedule = payment_schedule.get("installments") or payment_schedule.get("schedule_breakdown") or []
        if schedule and len(schedule) > 0:
            first_installment_amount = schedule[0].get("amount") or schedule[0].get("net") or schedule[0].get("basic") or 0
    
    return {
        "agreement": agreement,
        "lead": lead,
        "pricing_plan": pricing_plan,
        "sow": sow,
        "quotation": quotation,
        "meetings": meetings,
        "inherited": {
            "team_deployment": team_deployment,
            "sow_scopes": sow_scopes,
            "payment_schedule": payment_schedule,
            "first_installment_amount": first_installment_amount,
            "total_value": agreement.get("total_value") or (pricing_plan.get("total_amount") if pricing_plan else 0),
            "duration_months": agreement.get("duration_months") or agreement.get("project_tenure_months") or (pricing_plan.get("tenure_months") if pricing_plan else 12),
            "start_date": agreement.get("start_date"),
            "end_date": agreement.get("end_date")
        }
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
    
    RBAC:
    - Admin/Sales/Principal Consultant: Full access
    - Senior Consultant: Own agreements + reportees' agreements only
    - Consultant: No access
    """
    db = get_db()
    
    # Role-based access check
    if current_user.role not in AGREEMENT_VIEW_ROLES:
        raise HTTPException(status_code=403, detail="Access denied. You don't have permission to view agreements.")
    
    query = {}
    
    # RBAC: Senior Consultant can only see agreements linked to their projects/reportees
    if current_user.role == 'senior_consultant':
        # Get projects where this user is assigned
        user_projects = await db.projects.find(
            {"$or": [
                {"project_manager_id": current_user.id},
                {"team_members": current_user.id},
                {"assigned_consultants": current_user.id}
            ]},
            {"_id": 0, "agreement_id": 1, "lead_id": 1}
        ).to_list(100)
        
        # Get reportees
        reportees = await db.employees.find(
            {"reporting_to": current_user.id},
            {"_id": 0, "id": 1}
        ).to_list(50)
        reportee_ids = [r["id"] for r in reportees]
        
        # Filter: agreements linked to user's projects OR created by reportees
        project_agreement_ids = [p.get("agreement_id") for p in user_projects if p.get("agreement_id")]
        project_lead_ids = [p.get("lead_id") for p in user_projects if p.get("lead_id")]
        
        query["$or"] = [
            {"id": {"$in": project_agreement_ids}},
            {"lead_id": {"$in": project_lead_ids}},
            {"created_by": {"$in": reportee_ids + [current_user.id]}}
        ]
    
    if status:
        query["status"] = status
    if lead_id:
        query["lead_id"] = lead_id
    if agreement_type:
        query["agreement_type"] = agreement_type
    if search:
        search_query = [
            {"agreement_number": {"$regex": search, "$options": "i"}},
            {"client_name": {"$regex": search, "$options": "i"}},
        ]
        if "$or" in query:
            query["$and"] = [{"$or": query.pop("$or")}, {"$or": search_query}]
        else:
            query["$or"] = search_query
    
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
    
    if agreement.get("status") not in ["approved", "sent_to_client", "sent", "draft"]:
        raise HTTPException(status_code=400, detail="Agreement must be approved before signing")
    
    # Support both frontend field names (signer_*) and backend field names (signed_by_*)
    signer_name = data.signed_by_name or data.signer_name or current_user.full_name
    signer_designation = data.signed_by_designation or data.signer_designation or ""
    sign_date = data.signed_date or data.signature_date or today_ist()
    
    update_data = {
        "status": "signed",
        "signature_image": data.signature_image,
        "signed_by_name": signer_name,
        "signed_by_designation": signer_designation,
        "signed_date": sign_date,
        "signed_at": data.signed_at or datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "client_signature": {
            "signer_name": signer_name,
            "signer_designation": signer_designation,
            "signer_email": data.signer_email or "",
            "signed_at": data.signed_at or datetime.now(timezone.utc).isoformat(),
            "signature_image": data.signature_image
        }
    }
    
    await db.agreements.update_one(
        {"id": agreement_id},
        {"$set": update_data}
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
                "sent_to_email": data.email or data.client_email,
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



@router.post("/{agreement_id}/send-email")
async def send_agreement_email(
    agreement_id: str,
    data: SendAgreementEmailRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    """Send agreement via email with PDF and DOCX attachments to specified recipient"""
    db = get_db()
    
    agreement = await db.agreements.find_one({"id": agreement_id}, {"_id": 0})
    if not agreement:
        raise HTTPException(status_code=404, detail="Agreement not found")
    
    # Get recipient from request body (dynamic)
    to_email = data.recipient_email
    recipient_name = data.recipient_name or "Sir/Madam"
    
    lead_id = agreement.get("lead_id")
    lead = await db.leads.find_one({"id": lead_id}, {"_id": 0}) if lead_id else None
    
    # Get inherited data
    pricing_plan = None
    if agreement.get("pricing_plan_id"):
        pricing_plan = await db.pricing_plans.find_one({"id": agreement["pricing_plan_id"]}, {"_id": 0})
    if not pricing_plan and lead_id:
        pricing_plan = await db.pricing_plans.find_one({"lead_id": lead_id}, {"_id": 0})
    
    sow = None
    if agreement.get("sow_id"):
        sow = await db.enhanced_sow.find_one({"id": agreement["sow_id"]}, {"_id": 0})
    if not sow and pricing_plan:
        sow = await db.enhanced_sow.find_one({"pricing_plan_id": pricing_plan.get("id")}, {"_id": 0})
    if not sow and lead_id:
        sow = await db.enhanced_sow.find_one({"lead_id": lead_id}, {"_id": 0})
    
    # Build data
    team_deployment = agreement.get("team_deployment") or (pricing_plan.get("team_deployment") if pricing_plan else []) or []
    sow_scopes = agreement.get("sow_scopes") or (sow.get("scopes") if sow else []) or []
    payment_schedule = agreement.get("payment_schedule") or (pricing_plan.get("payment_plan") if pricing_plan else {}) or {}
    total_value = agreement.get("total_value") or (pricing_plan.get("total_amount") if pricing_plan else 0)
    duration_months = agreement.get("duration_months") or (pricing_plan.get("tenure_months") if pricing_plan else 12) or 12
    start_date = agreement.get("start_date", "")
    end_date = agreement.get("end_date", "")
    
    client_name = agreement.get("client_name") or (lead.get("company") if lead else "")
    client_address = agreement.get("client_address") or (lead.get("address") if lead else "")
    client_gstin = agreement.get("client_gstin") or (lead.get("gstin") if lead else "")
    client_email_addr = agreement.get("client_email") or (lead.get("email") if lead else "")
    client_phone = agreement.get("client_phone") or (lead.get("phone") if lead else "")
    client_contact = f"{lead.get('first_name', '')} {lead.get('last_name', '')}".strip() if lead else ""
    
    agreement_number = agreement.get("agreement_number", "N/A")
    today_str = now_ist().strftime("%d %B %Y")
    
    # NDA end date (24 months)
    created_at = agreement.get("created_at", "")
    try:
        from dateutil.relativedelta import relativedelta
        created_dt = datetime.fromisoformat(created_at.replace("Z", "+00:00")) if created_at else datetime.now(timezone.utc)
        nda_end_dt = created_dt + relativedelta(months=24)
        nda_end_str = nda_end_dt.strftime("%d %B %Y")
    except Exception:
        nda_end_str = "24 months from date of Agreement"
    
    def fmt_inr(amount):
        try:
            return f"INR {amount:,.2f}"
        except Exception:
            return f"INR {amount}"
    
    # Company logo - download and convert to base64 for reliable PDF embedding
    import base64
    import requests
    logo_url = "https://customer-assets.emergentagent.com/job_30a69dc1-a599-4a88-9d0e-e1c06b1b2008/artifacts/tbs0jexj_1001419196.png"
    logo_base64 = ""
    try:
        logo_response = requests.get(logo_url, timeout=10)
        if logo_response.status_code == 200:
            logo_base64 = base64.b64encode(logo_response.content).decode('utf-8')
    except Exception as logo_err:
        print(f"Logo download error: {logo_err}")
    
    # Build agreement HTML for PDF/DOCX
    schedule = payment_schedule.get("installments") or payment_schedule.get("schedule_breakdown") or []
    
    # Calculate due dates for installments
    from dateutil.relativedelta import relativedelta
    
    def calculate_due_date(start_dt, idx, total_installments, duration_months):
        """Calculate due date based on installment index and duration"""
        if total_installments <= 1:
            return start_dt
        # Spread installments evenly across duration
        months_per_installment = duration_months // total_installments
        return start_dt + relativedelta(months=idx * months_per_installment)
    
    start_dt = None
    try:
        if start_date:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
    except Exception:
        start_dt = datetime.now()
    
    installments_html = ""
    for idx, inst in enumerate(schedule):
        amount = inst.get("amount") or inst.get("net") or inst.get("basic") or 0
        label = inst.get("label") or inst.get("frequency") or f"Installment {idx+1}"
        gst = inst.get("gst", 0)
        basic = inst.get("basic") or amount
        
        # Calculate due date - use from pricing plan if available, else calculate
        due_date_str = inst.get("due_date") or ""
        if not due_date_str and start_dt:
            due_dt = calculate_due_date(start_dt, idx, len(schedule), duration_months)
            due_date_str = due_dt.strftime("%d %b %Y")
        
        installments_html += f"""<tr>
            <td style="border:1px solid #d1d5db;padding:8px 12px;text-align:center;">{idx+1}</td>
            <td style="border:1px solid #d1d5db;padding:8px 12px;">{label}</td>
            <td style="border:1px solid #d1d5db;padding:8px 12px;text-align:right;">{fmt_inr(basic)}</td>
            <td style="border:1px solid #d1d5db;padding:8px 12px;text-align:right;">{fmt_inr(gst) if gst else '-'}</td>
            <td style="border:1px solid #d1d5db;padding:8px 12px;text-align:right;font-weight:600;">{fmt_inr(amount)}</td>
            <td style="border:1px solid #d1d5db;padding:8px 12px;text-align:center;">{due_date_str}</td>
        </tr>"""
    
    team_html = ""
    total_meetings = 0
    for idx, m in enumerate(team_deployment):
        meetings = (m.get("committed_meetings") or m.get("total_meetings") or 0) * (m.get("count") or 1)
        total_meetings += meetings
        team_html += f"""<tr>
            <td style="border:1px solid #d1d5db;padding:8px 12px;text-align:center;">{idx+1}</td>
            <td style="border:1px solid #d1d5db;padding:8px 12px;">{m.get('role','')}</td>
            <td style="border:1px solid #d1d5db;padding:8px 12px;">{m.get('meeting_type','')}</td>
            <td style="border:1px solid #d1d5db;padding:8px 12px;text-align:center;">{m.get('count',1)}</td>
            <td style="border:1px solid #d1d5db;padding:8px 12px;text-align:center;">{meetings}</td>
        </tr>"""
    
    scope_html = ""
    for idx, s in enumerate(sow_scopes):
        deliverables = s.get("deliverables") or s.get("items") or []
        items_list = [d if isinstance(d, str) else d.get("name", "") for d in deliverables]
        items_str = "<ul style='margin:0;padding-left:16px;'>" + "".join(f"<li>{i}</li>" for i in items_list if i) + "</ul>" if items_list else "-"
        scope_html += f"""<tr>
            <td style="border:1px solid #d1d5db;padding:7px 10px;text-align:center;">{idx+1}</td>
            <td style="border:1px solid #d1d5db;padding:7px 10px;font-weight:600;">{s.get('category','')}</td>
            <td style="border:1px solid #d1d5db;padding:7px 10px;">{s.get('name','')}</td>
            <td style="border:1px solid #d1d5db;padding:7px 10px;">{items_str}</td>
        </tr>"""
    
    sh = lambda n, t: f'<h2 style="font-size:14px;font-weight:700;margin:28px 0 10px;padding:8px 14px;background:#e5e7eb;color:#1a1a1a;text-transform:uppercase;letter-spacing:0.5px;">{n}. {t}</h2>'
    
    # Consultant Undertaking & Obligations content (from DV_Consultant_Obligations.docx)
    consultant_obligations_html = f"""
        {sh('5','Consultant Undertaking & Obligations')}
        <p style="margin:0 0 10px;text-align:justify;font-style:italic;">This section outlines the obligations of D&V Business Consulting, a consulting firm incorporated under applicable laws of India (hereinafter referred to as the "Consultant"), towards the Client (as defined in this Agreement).</p>
        
        <h3 style="font-size:12px;font-weight:700;margin:16px 0 8px;color:#1a1a1a;">5.1 Confidentiality Obligation</h3>
        <p style="margin:0 0 6px;text-align:justify;">The Consultant shall:</p>
        <ul style="margin:0 0 10px;padding-left:20px;font-size:12px;">
            <li>Maintain strict confidentiality of all information, documents, data, and materials received from the Client, including financial data, employee information, operational processes, business strategies, and system access credentials ("Client Confidential Information")</li>
            <li>Use such information solely for execution of services under this Agreement</li>
            <li>Not disclose, publish, or transfer any Client Confidential Information to any third party without prior written consent of the Client</li>
        </ul>
        
        <h3 style="font-size:12px;font-weight:700;margin:16px 0 8px;color:#1a1a1a;">5.2 Data Protection & Security</h3>
        <p style="margin:0 0 6px;text-align:justify;">The Consultant agrees to:</p>
        <ul style="margin:0 0 10px;padding-left:20px;font-size:12px;">
            <li>Implement reasonable safeguards to protect Client data from unauthorized access, loss, or misuse</li>
            <li>Ensure all personnel engaged are bound by confidentiality obligations</li>
            <li>Not retain or use Client data post completion, except for statutory or agreed purposes</li>
        </ul>
        
        <h3 style="font-size:12px;font-weight:700;margin:16px 0 8px;color:#1a1a1a;">5.3 Non-Solicitation</h3>
        <p style="margin:0 0 10px;text-align:justify;">The Consultant shall not, during the term of this Agreement and for 12 months thereafter: solicit or hire any key employee of the Client, or induce employees to leave the Client organization.</p>
        
        <h3 style="font-size:12px;font-weight:700;margin:16px 0 8px;color:#1a1a1a;">5.4 Standard of Performance</h3>
        <p style="margin:0 0 6px;text-align:justify;">The Consultant shall:</p>
        <ul style="margin:0 0 10px;padding-left:20px;font-size:12px;">
            <li>Perform services professionally and ethically</li>
            <li>Deploy qualified personnel</li>
            <li>Act in good faith to achieve project objectives</li>
        </ul>
        
        <h3 style="font-size:12px;font-weight:700;margin:16px 0 8px;color:#1a1a1a;">5.5 Limitation of Liability</h3>
        <p style="margin:0 0 6px;text-align:justify;">The Consultant shall not be liable for:</p>
        <ul style="margin:0 0 10px;padding-left:20px;font-size:12px;">
            <li>Incorrect or incomplete data provided by the Client</li>
            <li>Non-implementation of recommendations</li>
            <li>Indirect or consequential damages</li>
            <li>External factors beyond control</li>
        </ul>
        
        <h3 style="font-size:12px;font-weight:700;margin:16px 0 8px;color:#1a1a1a;">5.6 Survival</h3>
        <p style="margin:0 0 10px;text-align:justify;">Confidentiality and Data Protection obligations survive for 3 years post termination. Non-Solicitation survives for 12 months post termination.</p>
        
        <h3 style="font-size:12px;font-weight:700;margin:16px 0 8px;color:#1a1a1a;">5.7 Governing Law</h3>
        <p style="margin:0 0 10px;text-align:justify;">This Agreement shall be governed by laws of India. Jurisdiction: Ahmedabad, Gujarat.</p>
    """
    
    agreement_html = f"""
    <div style="font-family:'Segoe UI',Arial,sans-serif;max-width:800px;margin:0 auto;color:#1a1a1a;line-height:1.7;font-size:12.5px;">
        {'<div style="text-align:center;margin-bottom:20px;padding-top:10px;"><img src="data:image/png;base64,' + logo_base64 + '" alt="D&V Business Consulting" style="height:70px;max-width:280px;object-fit:contain;" /></div>' if logo_base64 else ''}
        <h1 style="text-align:center;font-size:20px;font-weight:700;margin:12px 0 4px;text-transform:uppercase;letter-spacing:2px;border-bottom:2px solid #9ca3af;padding-bottom:10px;">Service Agreement</h1>
        <p style="text-align:center;font-size:11px;color:#6b7280;margin:4px 0 16px;">Agreement No: <strong>{agreement_number}</strong></p>
        <div style="margin:12px 0;padding:12px 16px;background:#f3f4f6;border-left:4px solid #6b7280;">
            <p style="margin:0;">This Service Agreement is made on <strong>{today_str}</strong>, between:</p>
        </div>
        <table style="width:100%;border-collapse:collapse;margin:10px 0 18px;">
            <tr>
                <td style="width:47%;vertical-align:top;padding:12px;border:1px solid #e5e7eb;background:#f9fafb;">
                    <p style="font-weight:700;margin:0 0 4px;">Party A (Service Provider)</p>
                    <p style="margin:2px 0;font-weight:600;">D&V Business Consulting</p>
                    <p style="margin:2px 0;font-size:11px;color:#555;">301, Business Hub, Prahlad Nagar, Ahmedabad - 380015, Gujarat, India</p>
                </td>
                <td style="width:6%;text-align:center;vertical-align:middle;font-weight:700;">AND</td>
                <td style="width:47%;vertical-align:top;padding:12px;border:1px solid #e5e7eb;background:#f9fafb;">
                    <p style="font-weight:700;margin:0 0 4px;">Party B (Client)</p>
                    <p style="margin:2px 0;font-weight:600;">{client_name}</p>
                    {'<p style="margin:2px 0;font-size:11px;color:#555;">' + client_address + '</p>' if client_address else ''}
                    {'<p style="margin:2px 0;font-size:11px;">GSTIN: <strong>' + client_gstin + '</strong></p>' if client_gstin else ''}
                </td>
            </tr>
        </table>

        {sh('1','Scope of Work')}
        <table style="width:100%;border-collapse:collapse;margin:8px 0;font-size:11px;">
            <thead><tr style="background:#f3f4f6;"><th style="border:1px solid #d1d5db;padding:7px;width:35px;">S.No</th><th style="border:1px solid #d1d5db;padding:7px;">Category</th><th style="border:1px solid #d1d5db;padding:7px;">Scope</th><th style="border:1px solid #d1d5db;padding:7px;">Deliverables</th></tr></thead>
            <tbody>{scope_html}</tbody>
        </table>

        {sh('2','Team Deployment & Meeting Schedule')}
        <table style="width:100%;border-collapse:collapse;margin:8px 0;font-size:11px;">
            <thead><tr style="background:#f3f4f6;"><th style="border:1px solid #d1d5db;padding:7px;width:35px;">S.No</th><th style="border:1px solid #d1d5db;padding:7px;">Role</th><th style="border:1px solid #d1d5db;padding:7px;">Meeting Type</th><th style="border:1px solid #d1d5db;padding:7px;text-align:center;">Count</th><th style="border:1px solid #d1d5db;padding:7px;text-align:center;">Total Meetings</th></tr></thead>
            <tbody>{team_html}</tbody>
            <tfoot><tr style="background:#f3f4f6;font-weight:700;"><td colspan="4" style="border:1px solid #d1d5db;padding:7px;text-align:right;">Total</td><td style="border:1px solid #d1d5db;padding:7px;text-align:center;">{total_meetings}</td></tr></tfoot>
        </table>

        {sh('3','Investment & Payment Schedule')}
        <table style="width:100%;border-collapse:collapse;margin:8px 0;">
            <tr><td style="border:1px solid #d1d5db;padding:10px;font-weight:600;background:#f9fafb;width:35%;">Total Investment</td><td style="border:1px solid #d1d5db;padding:10px;font-weight:700;">{fmt_inr(total_value)}</td></tr>
            <tr><td style="border:1px solid #d1d5db;padding:10px;font-weight:600;background:#f9fafb;">Duration</td><td style="border:1px solid #d1d5db;padding:10px;">{duration_months} Months</td></tr>
            <tr><td style="border:1px solid #d1d5db;padding:10px;font-weight:600;background:#f9fafb;">Start Date</td><td style="border:1px solid #d1d5db;padding:10px;">{start_date}</td></tr>
            <tr><td style="border:1px solid #d1d5db;padding:10px;font-weight:600;background:#f9fafb;">End Date</td><td style="border:1px solid #d1d5db;padding:10px;">{end_date}</td></tr>
        </table>
        {'<table style="width:100%;border-collapse:collapse;margin:8px 0;font-size:11px;"><thead><tr style="background:#f3f4f6;"><th style="border:1px solid #d1d5db;padding:7px;width:35px;">S.No</th><th style="border:1px solid #d1d5db;padding:7px;">Description</th><th style="border:1px solid #d1d5db;padding:7px;text-align:right;">Basic</th><th style="border:1px solid #d1d5db;padding:7px;text-align:right;">GST</th><th style="border:1px solid #d1d5db;padding:7px;text-align:right;">Net Amount</th><th style="border:1px solid #d1d5db;padding:7px;text-align:center;">Due Date</th></tr></thead><tbody>' + installments_html + '</tbody></table>' if installments_html else ''}

        <h3 style="font-size:13px;font-weight:700;margin:20px 0 10px;color:#1a1a1a;">Key Payment Terms</h3>
        <table style="width:100%;border-collapse:collapse;margin:8px 0;font-size:11.5px;">
            <tr>
                <td style="border:1px solid #d1d5db;padding:10px;font-weight:600;background:#f9fafb;width:25%;vertical-align:top;">1. Fees & Taxes</td>
                <td style="border:1px solid #d1d5db;padding:10px;text-align:justify;">GST and TDS applicable as per law.</td>
            </tr>
            <tr>
                <td style="border:1px solid #d1d5db;padding:10px;font-weight:600;background:#f9fafb;vertical-align:top;">2. Advance / Milestone Payment</td>
                <td style="border:1px solid #d1d5db;padding:10px;text-align:justify;">Payments to be made in advance as per defined milestones.</td>
            </tr>
            <tr>
                <td style="border:1px solid #d1d5db;padding:10px;font-weight:600;background:#f9fafb;vertical-align:top;">3. Payment Timeline</td>
                <td style="border:1px solid #d1d5db;padding:10px;text-align:justify;">Due amount payable within 7 days of proforma issue date.</td>
            </tr>
            <tr>
                <td style="border:1px solid #d1d5db;padding:10px;font-weight:600;background:#f9fafb;vertical-align:top;">4. Delay & Suspension</td>
                <td style="border:1px solid #d1d5db;padding:10px;text-align:justify;">Delay beyond 7 days attracts 18% p.a. interest + right to suspend services immediately.</td>
            </tr>
            <tr>
                <td style="border:1px solid #d1d5db;padding:10px;font-weight:600;background:#f9fafb;vertical-align:top;">5. Non-Refundable</td>
                <td style="border:1px solid #d1d5db;padding:10px;text-align:justify;">All payments are strictly non-refundable, irrespective of service stoppage from any stage.</td>
            </tr>
            <tr>
                <td style="border:1px solid #d1d5db;padding:10px;font-weight:600;background:#f9fafb;vertical-align:top;">6. Discontinue Terms</td>
                <td style="border:1px solid #d1d5db;padding:10px;text-align:justify;">30 days written notice to be given from either side before next due date or due installment to be paid by client.</td>
            </tr>
            <tr>
                <td style="border:1px solid #d1d5db;padding:10px;font-weight:600;background:#f9fafb;vertical-align:top;">7. Other Expenses</td>
                <td style="border:1px solid #d1d5db;padding:10px;text-align:justify;">Train or flight tickets, local conveyance, miscellaneous travel expenses and stay expenses extra and payable separately as per client policy and mutually agreed separately.</td>
            </tr>
        </table>

        {sh('4','Terms & Conditions')}
        <p style="text-align:justify;">This agreement includes NDA, NCA, Anti-Poaching clauses enforced for 24 months until {nda_end_str}. Early termination requires 30 days written notice or mutual agreement. Full terms as per the signed agreement document.</p>

        {consultant_obligations_html}

        {sh('6','Signatures')}
        <div class="signature-block">
        <table style="width:100%;"><tr>
            <td style="width:47%;vertical-align:top;padding:16px;border:1px solid #e5e7eb;"><p style="font-weight:700;">For D&V Business Consulting</p><div style="height:50px;border-bottom:1px solid #999;"></div><p style="font-size:11px;">Authorized Signatory</p></td>
            <td style="width:6%;"></td>
            <td style="width:47%;vertical-align:top;padding:16px;border:1px solid #e5e7eb;"><p style="font-weight:700;">For {client_name}</p><div style="height:50px;border-bottom:1px solid #999;"></div><p style="font-size:11px;">Authorized Signatory</p></td>
        </tr></table>
        </div>
    </div>"""
    
    # Generate PDF and DOCX files
    import tempfile
    temp_dir = tempfile.mkdtemp()
    pdf_path = os.path.join(temp_dir, f"Agreement_{agreement_number}.pdf")
    docx_path = os.path.join(temp_dir, f"Agreement_{agreement_number}.docx")
    
    # Generate PDF using weasyprint
    try:
        from weasyprint import HTML
        full_html = f"""<html><head><meta charset="utf-8"><style>
            @page {{ size: A4; margin: 15mm 12mm; }}
            body {{ font-family: 'Segoe UI', Arial, sans-serif; font-size: 12.5px; }}
            table {{ border-collapse: collapse; }}
            .signature-block {{ page-break-inside: avoid; }}
        </style></head><body>{agreement_html}</body></html>"""
        HTML(string=full_html).write_pdf(pdf_path)
    except Exception as e:
        print(f"PDF generation error: {e}")
        pdf_path = None
    
    # Generate DOCX using python-docx
    try:
        from docx import Document
        from docx.shared import Pt, Inches, Cm, RGBColor
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        from docx.enum.table import WD_TABLE_ALIGNMENT
        from docx.oxml.ns import qn
        from docx.oxml import OxmlElement
        import requests
        from io import BytesIO
        
        doc = Document()
        
        # Set default font
        style = doc.styles['Normal']
        font = style.font
        font.name = 'Segoe UI'
        font.size = Pt(11)
        
        # Add logo
        try:
            logo_response = requests.get(logo_url, timeout=10)
            if logo_response.status_code == 200:
                logo_stream = BytesIO(logo_response.content)
                logo_para = doc.add_paragraph()
                logo_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
                logo_run = logo_para.add_run()
                logo_run.add_picture(logo_stream, width=Inches(2.5))
        except Exception as logo_err:
            print(f"Logo load error: {logo_err}")
        
        # Title
        title = doc.add_heading('SERVICE AGREEMENT', level=1)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        # Agreement number
        agr_num_para = doc.add_paragraph()
        agr_num_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        agr_num_run = agr_num_para.add_run(f"Agreement No: {agreement_number}")
        agr_num_run.font.size = Pt(10)
        agr_num_run.font.color.rgb = RGBColor(107, 114, 128)
        
        # Date intro
        intro = doc.add_paragraph()
        intro.add_run(f"This Service Agreement is made on ").font.size = Pt(11)
        intro.add_run(f"{today_str}").bold = True
        intro.add_run(", between:")
        
        # Parties table
        parties_table = doc.add_table(rows=1, cols=3)
        parties_table.alignment = WD_TABLE_ALIGNMENT.CENTER
        row = parties_table.rows[0]
        
        # Party A cell
        cell_a = row.cells[0]
        cell_a.text = ""
        p1 = cell_a.paragraphs[0]
        p1.add_run("Party A (Service Provider)").bold = True
        cell_a.add_paragraph("D&V Business Consulting").runs[0].bold = True
        cell_a.add_paragraph("301, Business Hub, Prahlad Nagar, Ahmedabad - 380015, Gujarat, India")
        
        # AND cell
        row.cells[1].text = "AND"
        row.cells[1].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        # Party B cell
        cell_b = row.cells[2]
        cell_b.text = ""
        p2 = cell_b.paragraphs[0]
        p2.add_run("Party B (Client)").bold = True
        cell_b.add_paragraph(client_name).runs[0].bold = True
        if client_address:
            cell_b.add_paragraph(client_address)
        if client_gstin:
            cell_b.add_paragraph(f"GSTIN: {client_gstin}")
        
        doc.add_paragraph()
        
        # 1. Scope of Work
        doc.add_heading('1. SCOPE OF WORK', level=2)
        if sow_scopes:
            scope_table = doc.add_table(rows=1, cols=4)
            scope_table.style = 'Table Grid'
            hdr = scope_table.rows[0].cells
            hdr[0].text = "S.No"
            hdr[1].text = "Category"
            hdr[2].text = "Scope"
            hdr[3].text = "Deliverables"
            for idx, s in enumerate(sow_scopes):
                row = scope_table.add_row().cells
                row[0].text = str(idx + 1)
                row[1].text = s.get('category', '') or ''
                row[2].text = s.get('name', '') or ''
                deliverables = s.get("deliverables") or s.get("items") or []
                items_list = [d if isinstance(d, str) else d.get("name", "") for d in deliverables]
                row[3].text = ", ".join([i for i in items_list if i])
        
        # 2. Team Deployment
        doc.add_heading('2. TEAM DEPLOYMENT & MEETING SCHEDULE', level=2)
        if team_deployment:
            team_table = doc.add_table(rows=1, cols=5)
            team_table.style = 'Table Grid'
            hdr = team_table.rows[0].cells
            hdr[0].text = "S.No"
            hdr[1].text = "Role"
            hdr[2].text = "Meeting Type"
            hdr[3].text = "Count"
            hdr[4].text = "Total Meetings"
            for idx, m in enumerate(team_deployment):
                meetings = (m.get("committed_meetings") or m.get("total_meetings") or 0) * (m.get("count") or 1)
                row = team_table.add_row().cells
                row[0].text = str(idx + 1)
                row[1].text = m.get('role', '') or ''
                row[2].text = m.get('meeting_type', '') or ''
                row[3].text = str(m.get('count', 1))
                row[4].text = str(meetings)
            # Total row
            total_row = team_table.add_row().cells
            total_row[0].text = ""
            total_row[1].text = ""
            total_row[2].text = ""
            total_row[3].text = "Total"
            total_row[3].paragraphs[0].runs[0].bold = True
            total_row[4].text = str(total_meetings)
            total_row[4].paragraphs[0].runs[0].bold = True
        
        # 3. Investment & Payment Schedule
        doc.add_heading('3. INVESTMENT & PAYMENT SCHEDULE', level=2)
        inv_table = doc.add_table(rows=4, cols=2)
        inv_table.style = 'Table Grid'
        inv_table.rows[0].cells[0].text = "Total Investment"
        inv_table.rows[0].cells[1].text = fmt_inr(total_value)
        inv_table.rows[1].cells[0].text = "Duration"
        inv_table.rows[1].cells[1].text = f"{duration_months} Months"
        inv_table.rows[2].cells[0].text = "Start Date"
        inv_table.rows[2].cells[1].text = start_date
        inv_table.rows[3].cells[0].text = "End Date"
        inv_table.rows[3].cells[1].text = end_date
        
        # Payment schedule
        if schedule:
            doc.add_paragraph()
            doc.add_paragraph("Payment Schedule:").runs[0].bold = True
            pay_table = doc.add_table(rows=1, cols=6)
            pay_table.style = 'Table Grid'
            hdr = pay_table.rows[0].cells
            hdr[0].text = "S.No"
            hdr[1].text = "Description"
            hdr[2].text = "Basic"
            hdr[3].text = "GST"
            hdr[4].text = "Net Amount"
            hdr[5].text = "Due Date"
            for idx, inst in enumerate(schedule):
                amount = inst.get("amount") or inst.get("net") or inst.get("basic") or 0
                label = inst.get("label") or inst.get("frequency") or f"Installment {idx+1}"
                gst = inst.get("gst", 0)
                basic = inst.get("basic") or amount
                # Calculate due date
                due_date_str = inst.get("due_date") or ""
                if not due_date_str and start_dt:
                    due_dt = calculate_due_date(start_dt, idx, len(schedule), duration_months)
                    due_date_str = due_dt.strftime("%d %b %Y")
                row = pay_table.add_row().cells
                row[0].text = str(idx + 1)
                row[1].text = label
                row[2].text = fmt_inr(basic)
                row[3].text = fmt_inr(gst) if gst else "-"
                row[4].text = fmt_inr(amount)
                row[5].text = due_date_str
        
        # Key Payment Terms
        doc.add_paragraph()
        doc.add_paragraph("Key Payment Terms:").runs[0].bold = True
        terms_table = doc.add_table(rows=7, cols=2)
        terms_table.style = 'Table Grid'
        terms_table.rows[0].cells[0].text = "1. Fees & Taxes"
        terms_table.rows[0].cells[1].text = "GST and TDS applicable as per law."
        terms_table.rows[1].cells[0].text = "2. Advance / Milestone Payment"
        terms_table.rows[1].cells[1].text = "Payments to be made in advance as per defined milestones."
        terms_table.rows[2].cells[0].text = "3. Payment Timeline"
        terms_table.rows[2].cells[1].text = "Due amount payable within 7 days of proforma issue date."
        terms_table.rows[3].cells[0].text = "4. Delay & Suspension"
        terms_table.rows[3].cells[1].text = "Delay beyond 7 days attracts 18% p.a. interest + right to suspend services immediately."
        terms_table.rows[4].cells[0].text = "5. Non-Refundable"
        terms_table.rows[4].cells[1].text = "All payments are strictly non-refundable, irrespective of service stoppage from any stage."
        terms_table.rows[5].cells[0].text = "6. Discontinue Terms"
        terms_table.rows[5].cells[1].text = "30 days written notice to be given from either side before next due date or due installment to be paid by client."
        terms_table.rows[6].cells[0].text = "7. Other Expenses"
        terms_table.rows[6].cells[1].text = "Train or flight tickets, local conveyance, miscellaneous travel expenses and stay expenses extra and payable separately as per client policy and mutually agreed separately."
        
        # 4. Terms & Conditions
        doc.add_heading('4. TERMS & CONDITIONS', level=2)
        doc.add_paragraph(f"This agreement includes NDA, NCA, Anti-Poaching clauses enforced for 24 months until {nda_end_str}. Early termination requires 30 days written notice or mutual agreement. Full terms as per the signed agreement document.")
        
        # 5. Consultant Undertaking & Obligations
        doc.add_heading('5. CONSULTANT UNDERTAKING & OBLIGATIONS', level=2)
        doc.add_paragraph("This section outlines the obligations of D&V Business Consulting towards the Client.")
        
        doc.add_paragraph("5.1 Confidentiality Obligation").runs[0].bold = True
        doc.add_paragraph("The Consultant shall maintain strict confidentiality of all information received from the Client, use such information solely for execution of services, and not disclose to any third party without prior written consent.")
        
        doc.add_paragraph("5.2 Data Protection & Security").runs[0].bold = True
        doc.add_paragraph("The Consultant agrees to implement reasonable safeguards to protect Client data, ensure all personnel are bound by confidentiality obligations, and not retain Client data post completion.")
        
        doc.add_paragraph("5.3 Non-Solicitation").runs[0].bold = True
        doc.add_paragraph("The Consultant shall not solicit or hire any key employee of the Client during the term and for 12 months thereafter.")
        
        doc.add_paragraph("5.4 Standard of Performance").runs[0].bold = True
        doc.add_paragraph("The Consultant shall perform services professionally and ethically, deploy qualified personnel, and act in good faith.")
        
        doc.add_paragraph("5.5 Limitation of Liability").runs[0].bold = True
        doc.add_paragraph("The Consultant shall not be liable for incorrect/incomplete data provided by Client, non-implementation of recommendations, indirect damages, or external factors beyond control.")
        
        doc.add_paragraph("5.6 Survival").runs[0].bold = True
        doc.add_paragraph("Confidentiality and Data Protection obligations survive for 3 years post termination. Non-Solicitation survives for 12 months.")
        
        doc.add_paragraph("5.7 Governing Law").runs[0].bold = True
        doc.add_paragraph("This Agreement shall be governed by laws of India. Jurisdiction: Ahmedabad, Gujarat.")
        
        # 6. Signatures
        doc.add_heading('6. SIGNATURES', level=2)
        sig_table = doc.add_table(rows=4, cols=2)
        sig_table.alignment = WD_TABLE_ALIGNMENT.CENTER
        
        sig_table.rows[0].cells[0].text = "For D&V Business Consulting"
        sig_table.rows[0].cells[0].paragraphs[0].runs[0].bold = True
        sig_table.rows[0].cells[1].text = f"For {client_name}"
        sig_table.rows[0].cells[1].paragraphs[0].runs[0].bold = True
        
        sig_table.rows[1].cells[0].text = ""
        sig_table.rows[1].cells[1].text = ""
        
        sig_table.rows[2].cells[0].text = "_________________________"
        sig_table.rows[2].cells[1].text = "_________________________"
        
        sig_table.rows[3].cells[0].text = "Authorized Signatory"
        sig_table.rows[3].cells[1].text = "Authorized Signatory"
        
        # Save DOCX
        doc.save(docx_path)
    except Exception as e:
        print(f"DOCX generation error: {e}")
        import traceback
        traceback.print_exc()
        docx_path = None
    
    # Build attachments list
    file_attachments = []
    if pdf_path and os.path.exists(pdf_path):
        file_attachments.append({"path": pdf_path, "name": f"Agreement_{agreement_number}.pdf"})
    if docx_path and os.path.exists(docx_path):
        file_attachments.append({"path": docx_path, "name": f"Agreement_{agreement_number}.docx"})
    
    # Professional email body
    email_html = f"""
    <div style="font-family:'Segoe UI',Arial,sans-serif;max-width:600px;margin:0 auto;color:#333;">
        <div style="background:#f8f9fa;padding:24px 32px;border-bottom:3px solid #1a1a1a;">
            <h2 style="margin:0;font-size:18px;color:#1a1a1a;">D&V Business Consulting</h2>
            <p style="margin:4px 0 0;font-size:12px;color:#666;">Business Advisory &amp; Consulting Services</p>
        </div>
        <div style="padding:24px 32px;">
            <p style="margin:0 0 16px;">Dear Sir/Madam,</p>
            <p style="margin:0 0 12px;">Please find attached the Service Agreement for your review and records. The details of the agreement are summarized below:</p>
            <table style="width:100%;border-collapse:collapse;margin:16px 0;font-size:13px;">
                <tr><td style="padding:8px 12px;border:1px solid #e5e7eb;background:#f9fafb;font-weight:600;width:40%;">Agreement No.</td><td style="padding:8px 12px;border:1px solid #e5e7eb;">{agreement_number}</td></tr>
                <tr><td style="padding:8px 12px;border:1px solid #e5e7eb;background:#f9fafb;font-weight:600;">Client</td><td style="padding:8px 12px;border:1px solid #e5e7eb;">{client_name}</td></tr>
                <tr><td style="padding:8px 12px;border:1px solid #e5e7eb;background:#f9fafb;font-weight:600;">Total Investment</td><td style="padding:8px 12px;border:1px solid #e5e7eb;">{fmt_inr(total_value)}</td></tr>
                <tr><td style="padding:8px 12px;border:1px solid #e5e7eb;background:#f9fafb;font-weight:600;">Duration</td><td style="padding:8px 12px;border:1px solid #e5e7eb;">{duration_months} Months ({start_date} to {end_date})</td></tr>
                <tr><td style="padding:8px 12px;border:1px solid #e5e7eb;background:#f9fafb;font-weight:600;">Total Meetings</td><td style="padding:8px 12px;border:1px solid #e5e7eb;">{total_meetings}</td></tr>
            </table>
            <p style="margin:16px 0 8px;">The agreement includes the following attachments:</p>
            <ul style="margin:0 0 16px;padding-left:20px;">
                <li><strong>Agreement PDF</strong> - For review and signing</li>
                <li><strong>Agreement DOCX</strong> - Editable version for any amendments</li>
            </ul>
            <p style="margin:0 0 12px;">Kindly review the agreement at your earliest convenience. Should you have any queries or require any modifications, please do not hesitate to reach out.</p>
            <p style="margin:16px 0 0;">Warm Regards,</p>
            <p style="margin:4px 0 0;font-weight:600;">{current_user.full_name}</p>
            <p style="margin:2px 0 0;font-size:12px;color:#666;">D&V Business Consulting</p>
        </div>
        <div style="background:#f8f9fa;padding:12px 32px;border-top:1px solid #e5e7eb;font-size:11px;color:#999;">
            <p style="margin:0;">This is a system-generated email from D&V Business Consulting ERP. Agreement No: {agreement_number}</p>
        </div>
    </div>"""
    
    email_plain = f"""Dear {recipient_name},

Please find attached the Service Agreement ({agreement_number}) for {client_name}.

Total Investment: {fmt_inr(total_value)}
Duration: {duration_months} Months ({start_date} to {end_date})

Warm Regards,
{current_user.full_name}
D&V Business Consulting"""
    
    # Send email to specified recipient
    result = await send_email(
        to_email=to_email,
        subject=f"Service Agreement - {client_name} [{agreement_number}]",
        html_content=email_html,
        plain_content=email_plain,
        attachments=file_attachments
    )
    
    # Cleanup temp files
    import shutil
    try:
        shutil.rmtree(temp_dir, ignore_errors=True)
    except Exception:
        pass
    
    if result.get("status") == "sent":
        return {"message": f"Agreement sent successfully to {to_email}", "status": "sent"}
    else:
        raise HTTPException(status_code=500, detail=result.get("message", "Failed to send email"))
