"""
Stage Guard Router - Validates and manages sales funnel stage progression.

Prevents stage skipping and provides human-readable guidance instead of 403 errors.
"""

from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from pydantic import BaseModel

from .deps import get_db
from .auth import get_current_user
from .models import User

router = APIRouter(prefix="/stage-guard", tags=["Stage Guard"])

# Stage definitions with prerequisites
SALES_STAGES = {
    "LEAD": {"id": 1, "name": "Lead", "prerequisite": None},
    "MEETING": {"id": 2, "name": "Meeting", "prerequisite": "LEAD"},
    "PRICING": {"id": 3, "name": "Pricing Plan", "prerequisite": "MEETING"},
    "SOW": {"id": 4, "name": "SOW", "prerequisite": "PRICING"},
    "QUOTATION": {"id": 5, "name": "Quotation", "prerequisite": "SOW"},
    "AGREEMENT": {"id": 6, "name": "Agreement", "prerequisite": "QUOTATION"},
    "PAYMENT": {"id": 7, "name": "Payment", "prerequisite": "AGREEMENT"},
    "KICKOFF": {"id": 8, "name": "Kickoff", "prerequisite": "PAYMENT"},
    "CLOSED": {"id": 9, "name": "Closed/Project", "prerequisite": "KICKOFF"}
}

STAGE_ORDER = ["LEAD", "MEETING", "PRICING", "SOW", "QUOTATION", "AGREEMENT", "PAYMENT", "KICKOFF", "CLOSED"]

# Role-based access configuration
ROLE_CONFIG = {
    "executive": {
        "mode": "guided",
        "visible_stages": ["LEAD", "MEETING", "PRICING"],
        "can_skip_stages": False
    },
    "sales_manager": {
        "mode": "monitoring",
        "visible_stages": STAGE_ORDER,
        "can_skip_stages": False
    },
    "senior_consultant": {
        "mode": "monitoring",
        "visible_stages": STAGE_ORDER,
        "can_skip_stages": False
    },
    "principal_consultant": {
        "mode": "monitoring",
        "visible_stages": STAGE_ORDER,
        "can_skip_stages": False
    },
    "manager": {
        "mode": "monitoring",
        "visible_stages": STAGE_ORDER,
        "can_skip_stages": False
    },
    "admin": {
        "mode": "control",
        "visible_stages": STAGE_ORDER,
        "can_skip_stages": True
    }
}


class StageValidationRequest(BaseModel):
    """Request to validate stage access"""
    lead_id: str
    target_stage: str


class StageValidationResponse(BaseModel):
    """Response with validation result and guidance"""
    can_access: bool
    current_stage: str
    target_stage: str
    missing_stages: List[str]
    message: str
    redirect_to: Optional[str] = None


def get_stage_index(stage: str) -> int:
    """Get the index of a stage in the order"""
    try:
        return STAGE_ORDER.index(stage)
    except ValueError:
        return -1


def get_missing_stages(current_stage: str, target_stage: str) -> List[str]:
    """Get list of stages between current and target"""
    current_idx = get_stage_index(current_stage)
    target_idx = get_stage_index(target_stage)
    
    if target_idx <= current_idx:
        return []
    
    return STAGE_ORDER[current_idx + 1:target_idx]


def get_lead_current_stage(lead: dict) -> str:
    """Determine lead's current stage based on its data"""
    stage = lead.get("stage", "lead")
    
    # Map lead.stage to SALES_STAGES
    stage_mapping = {
        "lead": "LEAD",
        "new": "LEAD",
        "meeting": "MEETING",
        "meeting_scheduled": "MEETING",
        "meeting_done": "MEETING",
        "pricing": "PRICING",
        "pricing_sent": "PRICING",
        "sow": "SOW",
        "sow_sent": "SOW",
        "quotation": "QUOTATION",
        "quotation_sent": "QUOTATION",
        "agreement": "AGREEMENT",
        "agreement_sent": "AGREEMENT",
        "payment": "PAYMENT",
        "payment_pending": "PAYMENT",
        "payment_received": "PAYMENT",
        "kickoff": "KICKOFF",
        "kickoff_pending": "KICKOFF",
        "closed": "CLOSED",
        "won": "CLOSED",
        "project_created": "CLOSED"
    }
    
    return stage_mapping.get(stage.lower(), "LEAD")


@router.get("/leads/{lead_id}/stage")
async def get_lead_stage(
    lead_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get the current stage of a lead"""
    db = get_db()
    
    lead = await db.leads.find_one({"id": lead_id}, {"_id": 0})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    current_stage = get_lead_current_stage(lead)
    current_idx = get_stage_index(current_stage)
    
    # Get stage completion status
    stages_status = []
    for i, stage in enumerate(STAGE_ORDER):
        stages_status.append({
            "stage": stage,
            "name": SALES_STAGES[stage]["name"],
            "is_completed": i < current_idx,
            "is_current": i == current_idx,
            "is_locked": i > current_idx
        })
    
    return {
        "lead_id": lead_id,
        "current_stage": current_stage,
        "current_stage_name": SALES_STAGES[current_stage]["name"],
        "stage_index": current_idx,
        "stages": stages_status
    }


@router.post("/validate-access")
async def validate_stage_access(
    request: StageValidationRequest,
    current_user: User = Depends(get_current_user)
) -> StageValidationResponse:
    """
    Validate if user can access a specific stage for a lead.
    Returns human-readable guidance instead of 403.
    """
    db = get_db()
    
    # Get role config
    role_config = ROLE_CONFIG.get(current_user.role, ROLE_CONFIG["executive"])
    
    # Admin can skip stages
    if role_config["can_skip_stages"]:
        return StageValidationResponse(
            can_access=True,
            current_stage="LEAD",
            target_stage=request.target_stage,
            missing_stages=[],
            message="Access granted (admin mode)"
        )
    
    # Get lead
    lead = await db.leads.find_one({"id": request.lead_id}, {"_id": 0})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    current_stage = get_lead_current_stage(lead)
    target_stage = request.target_stage.upper()
    
    # Check if target stage is valid
    if target_stage not in SALES_STAGES:
        raise HTTPException(status_code=400, detail=f"Invalid stage: {target_stage}")
    
    # Check if target stage is visible for this role
    if target_stage not in role_config["visible_stages"]:
        return StageValidationResponse(
            can_access=False,
            current_stage=current_stage,
            target_stage=target_stage,
            missing_stages=[],
            message=f"The {SALES_STAGES[target_stage]['name']} stage is not available for your role. Please contact your manager."
        )
    
    current_idx = get_stage_index(current_stage)
    target_idx = get_stage_index(target_stage)
    
    # Can access current or previous stages
    if target_idx <= current_idx:
        return StageValidationResponse(
            can_access=True,
            current_stage=current_stage,
            target_stage=target_stage,
            missing_stages=[],
            message="Access granted"
        )
    
    # Cannot skip stages
    missing_stages = get_missing_stages(current_stage, target_stage)
    missing_names = [SALES_STAGES[s]["name"] for s in missing_stages]
    
    first_missing = missing_stages[0] if missing_stages else current_stage
    redirect_stage = SALES_STAGES.get(first_missing, {})
    
    return StageValidationResponse(
        can_access=False,
        current_stage=current_stage,
        target_stage=target_stage,
        missing_stages=missing_stages,
        message=f"Complete {' → '.join(missing_names)} before accessing {SALES_STAGES[target_stage]['name']}.",
        redirect_to=f"/sales-funnel/{first_missing.lower()}?lead={request.lead_id}"
    )


@router.post("/leads/{lead_id}/advance-stage")
async def advance_lead_stage(
    lead_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Advance a lead to the next stage after completing current stage.
    Returns guidance for next action.
    """
    db = get_db()
    
    lead = await db.leads.find_one({"id": lead_id}, {"_id": 0})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    current_stage = get_lead_current_stage(lead)
    current_idx = get_stage_index(current_stage)
    
    if current_idx >= len(STAGE_ORDER) - 1:
        return {
            "success": False,
            "message": "Lead is already at final stage",
            "current_stage": current_stage
        }
    
    next_stage = STAGE_ORDER[current_idx + 1]
    
    # Update lead stage
    stage_mapping_reverse = {
        "LEAD": "lead",
        "MEETING": "meeting",
        "PRICING": "pricing",
        "SOW": "sow",
        "QUOTATION": "quotation",
        "AGREEMENT": "agreement",
        "PAYMENT": "payment",
        "KICKOFF": "kickoff",
        "CLOSED": "closed"
    }
    
    new_stage_value = stage_mapping_reverse.get(next_stage, "lead")
    
    await db.leads.update_one(
        {"id": lead_id},
        {"$set": {
            "stage": new_stage_value,
            "stage_updated_at": datetime.now(timezone.utc).isoformat(),
            "stage_updated_by": current_user.id,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    return {
        "success": True,
        "message": f"{SALES_STAGES[current_stage]['name']} completed! Ready for {SALES_STAGES[next_stage]['name']}.",
        "previous_stage": current_stage,
        "current_stage": next_stage,
        "next_action": {
            "name": f"Create {SALES_STAGES[next_stage]['name']}",
            "path": f"/sales-funnel/{next_stage.lower()}?lead={lead_id}"
        }
    }


@router.get("/role-config")
async def get_role_configuration(
    current_user: User = Depends(get_current_user)
):
    """Get the stage configuration for the current user's role"""
    role_config = ROLE_CONFIG.get(current_user.role, ROLE_CONFIG["executive"])
    
    visible_stages_info = [
        {
            "stage": stage,
            "name": SALES_STAGES[stage]["name"],
            "id": SALES_STAGES[stage]["id"]
        }
        for stage in role_config["visible_stages"]
    ]
    
    return {
        "role": current_user.role,
        "mode": role_config["mode"],
        "can_skip_stages": role_config["can_skip_stages"],
        "visible_stages": visible_stages_info,
        "sidebar_mode": "guided" if role_config["mode"] == "guided" else "full"
    }


@router.get("/funnel-overview")
async def get_funnel_overview(
    current_user: User = Depends(get_current_user)
):
    """Get overview of leads at each stage (for managers/admins)"""
    db = get_db()
    
    role_config = ROLE_CONFIG.get(current_user.role, ROLE_CONFIG["executive"])
    
    # Only monitoring/control modes can see overview
    if role_config["mode"] == "guided":
        raise HTTPException(
            status_code=403,
            detail="Funnel overview is not available in guided mode. Complete your current tasks to progress."
        )
    
    # Build query based on role
    query = {}
    if current_user.role not in ["admin", "manager", "sr_manager"]:
        # Non-admin managers see their team's leads
        query["$or"] = [
            {"created_by": current_user.id},
            {"assigned_to": current_user.id}
        ]
    
    leads = await db.leads.find(query, {"_id": 0, "id": 1, "stage": 1, "company_name": 1}).to_list(1000)
    
    # Count leads by stage
    stage_counts = {stage: 0 for stage in STAGE_ORDER}
    for lead in leads:
        lead_stage = get_lead_current_stage(lead)
        if lead_stage in stage_counts:
            stage_counts[lead_stage] += 1
    
    funnel_data = [
        {
            "stage": stage,
            "name": SALES_STAGES[stage]["name"],
            "count": stage_counts[stage],
            "id": SALES_STAGES[stage]["id"]
        }
        for stage in STAGE_ORDER
    ]
    
    return {
        "total_leads": len(leads),
        "funnel": funnel_data
    }
