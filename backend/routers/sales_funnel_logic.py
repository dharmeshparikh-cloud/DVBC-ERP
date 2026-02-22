"""
Sales Funnel Business Logic Router
Handles: Stage resume, Deal renewal, Dual approvals, Client consent
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, EmailStr
from enum import Enum
import uuid
import secrets
import hashlib

from .deps import (
    get_db, SALES_MANAGER_ROLES, SALES_ROLES, ADMIN_ROLES, 
    APPROVAL_ROLES, MANAGER_ROLES, SENIOR_CONSULTING_ROLES
)
from .auth import get_current_user
from .models import User

router = APIRouter(prefix="/sales-funnel", tags=["Sales Funnel Business Logic"])


# ============== Stage Constants ==============

class FunnelStage(str, Enum):
    LEAD = "lead"
    MEETING = "meeting"
    PRICING = "pricing"
    QUOTATION = "quotation"
    SOW = "sow"
    AGREEMENT = "agreement"
    PAYMENT = "payment"
    KICKOFF = "kickoff"
    COMPLETE = "complete"
    CLOSED_LOST = "closed_lost"


STAGE_ORDER = [
    FunnelStage.LEAD,
    FunnelStage.MEETING,
    FunnelStage.PRICING,
    FunnelStage.QUOTATION,
    FunnelStage.SOW,
    FunnelStage.AGREEMENT,
    FunnelStage.PAYMENT,
    FunnelStage.KICKOFF,
    FunnelStage.COMPLETE
]

# Stages requiring approval
APPROVAL_REQUIRED_STAGES = {
    FunnelStage.PRICING: {"min_approvers": 2, "roles": ["sales_manager", "principal_consultant", "admin"]},
    FunnelStage.SOW: {"min_approvers": 1, "roles": ["sales_manager", "manager", "admin"]},
    FunnelStage.AGREEMENT: {"min_approvers": 1, "roles": ["client"]},  # Client consent
    FunnelStage.KICKOFF: {"min_approvers": 3, "roles": ["senior_consultant", "principal_consultant", "client"]}
}


# ============== Pydantic Models ==============

class StageResumeRequest(BaseModel):
    lead_id: str


class StageProgressRequest(BaseModel):
    lead_id: str
    target_stage: str
    notes: Optional[str] = None


class DealRenewalRequest(BaseModel):
    original_lead_id: str
    renewal_reason: str
    new_estimated_value: Optional[float] = None
    notes: Optional[str] = None


class DualApprovalRequest(BaseModel):
    entity_type: str  # pricing, sow
    entity_id: str
    approval_notes: Optional[str] = None


class ClientConsentRequest(BaseModel):
    agreement_id: str
    client_email: EmailStr
    message: Optional[str] = None


class ClientConsentResponse(BaseModel):
    token: str
    decision: str  # approved, rejected
    client_name: Optional[str] = None
    client_signature: Optional[str] = None
    comments: Optional[str] = None


class KickoffApprovalRequest(BaseModel):
    lead_id: str
    approval_type: str  # consultant, principal, client
    approved: bool
    notes: Optional[str] = None


# ============== Stage Resume ==============

@router.get("/stage-status/{lead_id}")
async def get_stage_status(
    lead_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get current stage status and what's needed to progress"""
    if current_user.role not in SALES_ROLES:
        raise HTTPException(status_code=403, detail="Sales access required")
    
    db = get_db()
    lead = await db.leads.find_one({"id": lead_id}, {"_id": 0})
    
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    current_stage = lead.get("current_stage", FunnelStage.LEAD.value)
    stage_history = lead.get("stage_history", [])
    
    # Determine what's needed for next stage
    current_idx = next((i for i, s in enumerate(STAGE_ORDER) if s.value == current_stage), 0)
    next_stage = STAGE_ORDER[current_idx + 1] if current_idx < len(STAGE_ORDER) - 1 else None
    
    # Check if approval is needed
    approval_status = None
    if next_stage and next_stage in APPROVAL_REQUIRED_STAGES:
        approval_config = APPROVAL_REQUIRED_STAGES[next_stage]
        
        # Get existing approvals
        approvals = await db.stage_approvals.find({
            "lead_id": lead_id,
            "stage": next_stage.value,
            "status": "approved"
        }, {"_id": 0}).to_list(10)
        
        approval_status = {
            "required": approval_config["min_approvers"],
            "received": len(approvals),
            "approved_by": [a.get("approved_by") for a in approvals],
            "pending": approval_config["min_approvers"] - len(approvals)
        }
    
    return {
        "lead_id": lead_id,
        "current_stage": current_stage,
        "next_stage": next_stage.value if next_stage else None,
        "stage_index": current_idx,
        "total_stages": len(STAGE_ORDER),
        "stage_history": stage_history,
        "approval_status": approval_status,
        "can_progress": approval_status is None or approval_status["pending"] <= 0
    }


@router.post("/resume-stage")
async def resume_from_stage(
    request: StageResumeRequest,
    current_user: User = Depends(get_current_user)
):
    """Resume work from current stage - returns context for continuation"""
    if current_user.role not in SALES_ROLES:
        raise HTTPException(status_code=403, detail="Sales access required")
    
    db = get_db()
    lead = await db.leads.find_one({"id": request.lead_id}, {"_id": 0})
    
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    current_stage = lead.get("current_stage", FunnelStage.LEAD.value)
    
    # Build context for resumption
    context = {
        "lead": lead,
        "current_stage": current_stage,
        "stage_data": {}
    }
    
    # Fetch stage-specific data
    if current_stage == FunnelStage.PRICING.value:
        context["stage_data"]["pricing_plans"] = await db.pricing_plans.find(
            {"lead_id": request.lead_id}, {"_id": 0}
        ).to_list(10)
    
    elif current_stage == FunnelStage.SOW.value:
        context["stage_data"]["sow"] = await db.enhanced_sow.find_one(
            {"lead_id": request.lead_id}, {"_id": 0}
        )
    
    elif current_stage == FunnelStage.AGREEMENT.value:
        context["stage_data"]["agreement"] = await db.agreements.find_one(
            {"lead_id": request.lead_id}, {"_id": 0}
        )
    
    elif current_stage == FunnelStage.PAYMENT.value:
        context["stage_data"]["payments"] = await db.project_payments.find(
            {"lead_id": request.lead_id}, {"_id": 0}
        ).to_list(20)
    
    # Get pending actions
    context["pending_actions"] = []
    
    # Check for pending approvals
    pending_approvals = await db.stage_approvals.find({
        "lead_id": request.lead_id,
        "status": "pending"
    }, {"_id": 0}).to_list(10)
    
    if pending_approvals:
        context["pending_actions"].append({
            "type": "approval_required",
            "count": len(pending_approvals),
            "details": pending_approvals
        })
    
    # Log resume action
    await db.audit_logs.insert_one({
        "id": str(uuid.uuid4()),
        "action": "stage_resume",
        "entity_type": "lead",
        "entity_id": request.lead_id,
        "stage": current_stage,
        "performed_by": current_user.id,
        "performed_at": datetime.now(timezone.utc).isoformat()
    })
    
    return context


# ============== Deal Renewal ==============

@router.post("/renew-deal")
async def renew_deal(
    request: DealRenewalRequest,
    current_user: User = Depends(get_current_user)
):
    """Create a renewal deal from a closed/completed deal"""
    if current_user.role not in SALES_ROLES:
        raise HTTPException(status_code=403, detail="Sales access required")
    
    db = get_db()
    
    # Get original lead
    original = await db.leads.find_one({"id": request.original_lead_id}, {"_id": 0})
    if not original:
        raise HTTPException(status_code=404, detail="Original lead not found")
    
    # Verify original is closed
    if original.get("current_stage") not in ["complete", "closed_won", "closed_lost"]:
        raise HTTPException(status_code=400, detail="Can only renew closed deals")
    
    # Create new lead with renewal reference
    new_lead_id = str(uuid.uuid4())
    renewal_lead = {
        "id": new_lead_id,
        "company": original.get("company"),
        # Use proper Lead model schema with first_name/last_name
        "first_name": original.get("first_name") or original.get("contact_name", "").split()[0] if original.get("contact_name") else "Renewal",
        "last_name": original.get("last_name") or " ".join(original.get("contact_name", "").split()[1:]) if original.get("contact_name") else "Contact",
        "email": original.get("email") or original.get("contact_email"),
        "phone": original.get("phone") or original.get("contact_phone"),
        "source": "renewal",
        "status": "new",
        "current_stage": FunnelStage.LEAD.value,
        "estimated_value": request.new_estimated_value or original.get("estimated_value"),
        "assigned_to": current_user.id,
        "renewal_info": {
            "original_lead_id": request.original_lead_id,
            "original_lead_status": original.get("current_stage"),
            "renewal_reason": request.renewal_reason,
            "renewal_date": datetime.now(timezone.utc).isoformat()
        },
        "stage_history": [{
            "stage": FunnelStage.LEAD.value,
            "entered_at": datetime.now(timezone.utc).isoformat(),
            "entered_by": current_user.id,
            "notes": f"Renewal from {request.original_lead_id}"
        }],
        "notes": request.notes,
        "created_by": current_user.id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.leads.insert_one(renewal_lead)
    
    # Update original lead with renewal reference
    await db.leads.update_one(
        {"id": request.original_lead_id},
        {"$set": {
            "renewed_to": new_lead_id,
            "renewed_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    # Audit log
    await db.audit_logs.insert_one({
        "id": str(uuid.uuid4()),
        "action": "deal_renewal",
        "entity_type": "lead",
        "entity_id": new_lead_id,
        "changes": {
            "original_lead_id": request.original_lead_id,
            "renewal_reason": request.renewal_reason
        },
        "performed_by": current_user.id,
        "performed_at": datetime.now(timezone.utc).isoformat()
    })
    
    renewal_lead.pop("_id", None)
    return {
        "status": "success",
        "message": "Deal renewed successfully",
        "new_lead": renewal_lead
    }


# ============== Dual Approval System ==============

@router.post("/request-approval")
async def request_dual_approval(
    entity_type: str,
    entity_id: str,
    current_user: User = Depends(get_current_user)
):
    """Submit entity for dual/multi approval"""
    if current_user.role not in SALES_ROLES:
        raise HTTPException(status_code=403, detail="Sales access required")
    
    db = get_db()
    
    # Determine approval requirements
    approval_config = None
    if entity_type == "pricing":
        approval_config = APPROVAL_REQUIRED_STAGES[FunnelStage.PRICING]
    elif entity_type == "sow":
        approval_config = APPROVAL_REQUIRED_STAGES[FunnelStage.SOW]
    else:
        raise HTTPException(status_code=400, detail="Invalid entity type")
    
    # Create approval request
    approval_request = {
        "id": str(uuid.uuid4()),
        "entity_type": entity_type,
        "entity_id": entity_id,
        "required_approvers": approval_config["min_approvers"],
        "allowed_roles": approval_config["roles"],
        "status": "pending",
        "approvals": [],
        "requested_by": current_user.id,
        "requested_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.approval_requests.insert_one(approval_request)
    approval_request.pop("_id", None)
    
    return {
        "status": "success",
        "approval_request": approval_request
    }


@router.post("/approve")
async def submit_approval(
    request: DualApprovalRequest,
    current_user: User = Depends(get_current_user)
):
    """Submit approval for an entity (part of dual/multi approval)"""
    if current_user.role not in APPROVAL_ROLES:
        raise HTTPException(status_code=403, detail="Approval authority required")
    
    db = get_db()
    
    # Get approval request
    approval_req = await db.approval_requests.find_one({
        "entity_type": request.entity_type,
        "entity_id": request.entity_id,
        "status": "pending"
    })
    
    if not approval_req:
        raise HTTPException(status_code=404, detail="No pending approval request found")
    
    # Check if user can approve
    if current_user.role not in approval_req.get("allowed_roles", []):
        raise HTTPException(status_code=403, detail="Your role cannot approve this")
    
    # Check if already approved by this user
    existing_approvals = approval_req.get("approvals", [])
    if any(a["approved_by"] == current_user.id for a in existing_approvals):
        raise HTTPException(status_code=400, detail="You have already approved this")
    
    # Add approval
    new_approval = {
        "approved_by": current_user.id,
        "approver_role": current_user.role,
        "approved_at": datetime.now(timezone.utc).isoformat(),
        "notes": request.approval_notes
    }
    
    existing_approvals.append(new_approval)
    
    # Check if fully approved
    is_fully_approved = len(existing_approvals) >= approval_req.get("required_approvers", 1)
    new_status = "approved" if is_fully_approved else "pending"
    
    await db.approval_requests.update_one(
        {"id": approval_req["id"]},
        {"$set": {
            "approvals": existing_approvals,
            "status": new_status,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    # If fully approved, update the entity
    if is_fully_approved:
        if request.entity_type == "pricing":
            await db.pricing_plans.update_one(
                {"id": request.entity_id},
                {"$set": {"status": "approved", "approved_at": datetime.now(timezone.utc).isoformat()}}
            )
        elif request.entity_type == "sow":
            await db.enhanced_sow.update_one(
                {"id": request.entity_id},
                {"$set": {"status": "approved", "approved_at": datetime.now(timezone.utc).isoformat()}}
            )
    
    return {
        "status": "success",
        "approval_status": new_status,
        "approvals_received": len(existing_approvals),
        "approvals_required": approval_req.get("required_approvers", 1),
        "is_fully_approved": is_fully_approved
    }


@router.get("/approval-status")
async def get_approval_status(
    entity_type: str,
    entity_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get approval status for an entity"""
    db = get_db()
    
    approval_req = await db.approval_requests.find_one({
        "entity_type": entity_type,
        "entity_id": entity_id
    }, {"_id": 0})
    
    if not approval_req:
        return {
            "submitted": False,
            "status": None,
            "approvals_received": 0,
            "approvals_required": 2 if entity_type == "pricing" else 1,
            "can_approve": current_user.role in APPROVAL_ROLES,
            "approvers": []
        }
    
    # Get approver details
    approvers = []
    for approval in approval_req.get("approvals", []):
        approver = await db.users.find_one({"id": approval["approved_by"]}, {"_id": 0, "full_name": 1, "email": 1})
        approvers.append({
            "name": approver.get("full_name") if approver else "Unknown",
            "email": approver.get("email") if approver else "",
            "decision": "approved",
            "approved_at": approval.get("approved_at")
        })
    
    return {
        "submitted": True,
        "status": approval_req.get("status"),
        "approvals_received": len(approval_req.get("approvals", [])),
        "approvals_required": approval_req.get("required_approvers", 2),
        "can_approve": current_user.role in approval_req.get("allowed_roles", []) and 
                       not any(a["approved_by"] == current_user.id for a in approval_req.get("approvals", [])),
        "approvers": approvers,
        "requested_at": approval_req.get("requested_at")
    }


# ============== Client Consent System ==============

def generate_consent_token() -> str:
    """Generate secure token for client consent"""
    return secrets.token_urlsafe(32)


@router.post("/send-consent-request")
async def send_client_consent_request(
    request: ClientConsentRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    """Send consent request to client via email"""
    if current_user.role not in SALES_ROLES:
        raise HTTPException(status_code=403, detail="Sales access required")
    
    db = get_db()
    
    # Get agreement
    agreement = await db.agreements.find_one({"id": request.agreement_id}, {"_id": 0})
    if not agreement:
        raise HTTPException(status_code=404, detail="Agreement not found")
    
    # Generate consent token
    token = generate_consent_token()
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    
    # Store consent request
    consent_request = {
        "id": str(uuid.uuid4()),
        "agreement_id": request.agreement_id,
        "token_hash": token_hash,
        "client_email": request.client_email,
        "status": "pending",
        "expires_at": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
        "sent_by": current_user.id,
        "sent_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.client_consent_requests.insert_one(consent_request)
    
    # Update agreement status
    await db.agreements.update_one(
        {"id": request.agreement_id},
        {"$set": {
            "consent_status": "pending",
            "consent_sent_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    # TODO: Send email in background (integrate with email service)
    # background_tasks.add_task(send_consent_email, request.client_email, token, agreement)
    
    consent_request.pop("_id", None)
    return {
        "status": "success",
        "message": f"Consent request sent to {request.client_email}",
        "consent_token": token,  # In production, this goes only in email
        "expires_at": consent_request["expires_at"]
    }


@router.post("/submit-consent")
async def submit_client_consent(response: ClientConsentResponse):
    """Submit client's consent decision (accessed via token link)"""
    db = get_db()
    
    # Hash the token to look up request
    token_hash = hashlib.sha256(response.token.encode()).hexdigest()
    
    consent_request = await db.client_consent_requests.find_one({
        "token_hash": token_hash,
        "status": "pending"
    })
    
    if not consent_request:
        raise HTTPException(status_code=404, detail="Invalid or expired consent token")
    
    # Check expiry
    if datetime.fromisoformat(consent_request["expires_at"].replace("Z", "+00:00")) < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Consent request has expired")
    
    # Update consent request
    await db.client_consent_requests.update_one(
        {"id": consent_request["id"]},
        {"$set": {
            "status": response.decision,
            "client_name": response.client_name,
            "client_signature": response.client_signature,
            "client_comments": response.comments,
            "responded_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    # Update agreement
    agreement_status = "client_approved" if response.decision == "approved" else "client_rejected"
    await db.agreements.update_one(
        {"id": consent_request["agreement_id"]},
        {"$set": {
            "consent_status": agreement_status,
            "client_consent_at": datetime.now(timezone.utc).isoformat(),
            "client_signature": response.client_signature,
            "status": "signed" if response.decision == "approved" else "rejected"
        }}
    )
    
    # Audit log
    await db.audit_logs.insert_one({
        "id": str(uuid.uuid4()),
        "action": "client_consent",
        "entity_type": "agreement",
        "entity_id": consent_request["agreement_id"],
        "changes": {
            "decision": response.decision,
            "client_name": response.client_name
        },
        "performed_by": "client",
        "performed_at": datetime.now(timezone.utc).isoformat()
    })
    
    return {
        "status": "success",
        "message": f"Consent {response.decision} recorded",
        "agreement_id": consent_request["agreement_id"]
    }


@router.get("/consent-status/{agreement_id}")
async def get_consent_status(
    agreement_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get client consent status for an agreement"""
    if current_user.role not in SALES_ROLES:
        raise HTTPException(status_code=403, detail="Sales access required")
    
    db = get_db()
    
    consent_requests = await db.client_consent_requests.find(
        {"agreement_id": agreement_id},
        {"_id": 0, "token_hash": 0}
    ).sort("sent_at", -1).to_list(10)
    
    agreement = await db.agreements.find_one(
        {"id": agreement_id},
        {"_id": 0, "consent_status": 1, "client_consent_at": 1}
    )
    
    return {
        "agreement_id": agreement_id,
        "current_status": agreement.get("consent_status") if agreement else None,
        "consent_history": consent_requests
    }


# ============== Multi-Party Kickoff Approval ==============

@router.post("/kickoff-approval")
async def submit_kickoff_approval(
    request: KickoffApprovalRequest,
    current_user: User = Depends(get_current_user)
):
    """Submit kickoff approval (consultant, principal, or client)"""
    db = get_db()
    
    # Validate approval type and role
    role_mapping = {
        "consultant": SENIOR_CONSULTING_ROLES,
        "principal": ["admin", "principal_consultant"],
        "client": ["client"]  # Client uses token-based auth
    }
    
    if request.approval_type not in role_mapping:
        raise HTTPException(status_code=400, detail="Invalid approval type")
    
    # For non-client approvals, check role
    if request.approval_type != "client":
        if current_user.role not in role_mapping[request.approval_type]:
            raise HTTPException(status_code=403, detail=f"Cannot submit {request.approval_type} approval")
    
    # Get or create kickoff approval record
    kickoff = await db.kickoff_approvals.find_one({"lead_id": request.lead_id})
    
    if not kickoff:
        kickoff = {
            "id": str(uuid.uuid4()),
            "lead_id": request.lead_id,
            "approvals": {},
            "status": "pending",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.kickoff_approvals.insert_one(kickoff)
    
    # Add approval
    kickoff["approvals"][request.approval_type] = {
        "approved": request.approved,
        "approved_by": current_user.id if request.approval_type != "client" else "client",
        "approved_at": datetime.now(timezone.utc).isoformat(),
        "notes": request.notes
    }
    
    # Check if all approvals received
    required_approvals = ["consultant", "principal", "client"]
    all_approved = all(
        kickoff["approvals"].get(a, {}).get("approved", False) 
        for a in required_approvals
    )
    
    new_status = "approved" if all_approved else "pending"
    
    await db.kickoff_approvals.update_one(
        {"lead_id": request.lead_id},
        {"$set": {
            "approvals": kickoff["approvals"],
            "status": new_status,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    # If fully approved, update lead stage
    if all_approved:
        await db.leads.update_one(
            {"id": request.lead_id},
            {"$set": {
                "current_stage": FunnelStage.KICKOFF.value,
                "kickoff_approved_at": datetime.now(timezone.utc).isoformat()
            },
            "$push": {
                "stage_history": {
                    "stage": FunnelStage.KICKOFF.value,
                    "entered_at": datetime.now(timezone.utc).isoformat(),
                    "notes": "Multi-party kickoff approved"
                }
            }}
        )
    
    return {
        "status": "success",
        "approval_type": request.approval_type,
        "approved": request.approved,
        "kickoff_status": new_status,
        "approvals_received": list(kickoff["approvals"].keys()),
        "all_approved": all_approved
    }


@router.get("/kickoff-status/{lead_id}")
async def get_kickoff_status(
    lead_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get multi-party kickoff approval status"""
    db = get_db()
    
    kickoff = await db.kickoff_approvals.find_one(
        {"lead_id": lead_id},
        {"_id": 0}
    )
    
    if not kickoff:
        return {
            "lead_id": lead_id,
            "status": "not_started",
            "approvals": {},
            "required": ["consultant", "principal", "client"]
        }
    
    return {
        "lead_id": lead_id,
        "status": kickoff.get("status"),
        "approvals": kickoff.get("approvals", {}),
        "required": ["consultant", "principal", "client"],
        "created_at": kickoff.get("created_at"),
        "updated_at": kickoff.get("updated_at")
    }
