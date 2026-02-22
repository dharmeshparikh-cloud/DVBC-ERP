"""
Pricing Plans Router - Create and manage pricing plans for leads/clients.

tenure_months is AUTO-CALCULATED from len(schedule_breakdown) - no duplicate entry required.
"""

from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
import uuid

from .deps import get_db, SALES_MANAGER_ROLES, ADMIN_ROLES, SALES_ROLES
from .auth import get_current_user
from .models import User

router = APIRouter(prefix="/pricing-plans", tags=["Pricing Plans"])

# Role constants for this router
PRICING_VIEW_ROLES = list(set(SALES_ROLES + ADMIN_ROLES))  # sales, admin


class PaymentScheduleItem(BaseModel):
    """Single payment installment"""
    frequency: str  # "Month 1 - Advance", "Month 2", etc.
    due_date: Optional[str] = None
    basic: float = 0
    gst: float = 0
    tds: float = 0
    net: float = 0


class TeamDeploymentItem(BaseModel):
    """Team member deployment in pricing"""
    role: str
    rate_per_meeting: float = 0
    meetings_per_month: int = 0
    committed_meetings: int = 0
    breakup_amount: float = 0


class PricingPlanCreate(BaseModel):
    """Create pricing plan - tenure_months auto-calculated from schedule_breakdown"""
    lead_id: str
    name: str
    total_amount: float
    payment_schedule: str = "monthly"  # monthly, quarterly, custom
    payment_plan: Dict[str, Any]  # Contains schedule_breakdown
    team_deployment: Optional[List[Dict[str, Any]]] = []


class PricingPlanUpdate(BaseModel):
    """Update pricing plan"""
    name: Optional[str] = None
    total_amount: Optional[float] = None
    payment_schedule: Optional[str] = None
    payment_plan: Optional[Dict[str, Any]] = None
    team_deployment: Optional[List[Dict[str, Any]]] = None


def calculate_tenure_months(payment_plan: dict) -> int:
    """Auto-calculate tenure_months from schedule_breakdown length"""
    if not payment_plan:
        return 0
    schedule = payment_plan.get("schedule_breakdown", [])
    return len(schedule) if schedule else 0


@router.post("")
async def create_pricing_plan(
    data: PricingPlanCreate,
    current_user: User = Depends(get_current_user)
):
    """
    Create a new pricing plan.
    tenure_months is AUTO-CALCULATED from len(schedule_breakdown).
    """
    db = get_db()
    
    # Verify lead exists
    lead = await db.leads.find_one({"id": data.lead_id}, {"_id": 0})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    # Check if pricing plan already exists for this lead
    existing = await db.pricing_plans.find_one({"lead_id": data.lead_id}, {"_id": 0})
    if existing:
        raise HTTPException(
            status_code=400, 
            detail=f"Pricing plan already exists for this lead. Use PUT to update. (ID: {existing.get('id')})"
        )
    
    pricing_plan_id = f"pp-{int(datetime.now(timezone.utc).timestamp() * 1000)}"
    
    # Auto-calculate tenure_months from schedule_breakdown
    tenure_months = calculate_tenure_months(data.payment_plan)
    
    pricing_plan_doc = {
        "id": pricing_plan_id,
        "lead_id": data.lead_id,
        "name": data.name,
        "total_amount": data.total_amount,
        "tenure_months": tenure_months,  # AUTO-CALCULATED
        "payment_schedule": data.payment_schedule,
        "payment_plan": data.payment_plan,
        "team_deployment": data.team_deployment or [],
        "status": "draft",
        "created_by": current_user.id,
        "created_by_name": current_user.full_name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.pricing_plans.insert_one(pricing_plan_doc)
    pricing_plan_doc.pop("_id", None)
    
    # Update lead stage
    await db.leads.update_one(
        {"id": data.lead_id},
        {"$set": {"stage": "pricing", "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    return pricing_plan_doc


@router.get("")
async def get_pricing_plans(
    lead_id: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get all pricing plans, optionally filtered by lead_id.
    Access: sales, admin
    """
    db = get_db()
    
    # Role-based access check
    if current_user.role not in PRICING_VIEW_ROLES:
        raise HTTPException(status_code=403, detail="Access denied. Only sales team and admin can view pricing plans.")
    
    query = {}
    if lead_id:
        query["lead_id"] = lead_id
    
    plans = await db.pricing_plans.find(query, {"_id": 0}).to_list(500)
    
    # Ensure tenure_months exists (backfill for legacy data)
    for plan in plans:
        if "tenure_months" not in plan:
            plan["tenure_months"] = calculate_tenure_months(plan.get("payment_plan", {}))
    
    return plans


@router.get("/{plan_id}")
async def get_pricing_plan(
    plan_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get a single pricing plan by ID"""
    db = get_db()
    
    plan = await db.pricing_plans.find_one({"id": plan_id}, {"_id": 0})
    if not plan:
        raise HTTPException(status_code=404, detail="Pricing plan not found")
    
    # Ensure tenure_months exists (backfill for legacy data)
    if "tenure_months" not in plan:
        plan["tenure_months"] = calculate_tenure_months(plan.get("payment_plan", {}))
    
    return plan


@router.put("/{plan_id}")
async def update_pricing_plan(
    plan_id: str,
    data: PricingPlanUpdate,
    current_user: User = Depends(get_current_user)
):
    """
    Update a pricing plan.
    tenure_months is AUTO-RECALCULATED if schedule_breakdown changes.
    """
    db = get_db()
    
    existing = await db.pricing_plans.find_one({"id": plan_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Pricing plan not found")
    
    update_data = {"updated_at": datetime.now(timezone.utc).isoformat()}
    
    if data.name is not None:
        update_data["name"] = data.name
    if data.total_amount is not None:
        update_data["total_amount"] = data.total_amount
    if data.payment_schedule is not None:
        update_data["payment_schedule"] = data.payment_schedule
    if data.team_deployment is not None:
        update_data["team_deployment"] = data.team_deployment
    
    # If payment_plan is updated, auto-recalculate tenure_months
    if data.payment_plan is not None:
        update_data["payment_plan"] = data.payment_plan
        update_data["tenure_months"] = calculate_tenure_months(data.payment_plan)
    
    await db.pricing_plans.update_one(
        {"id": plan_id},
        {"$set": update_data}
    )
    
    updated = await db.pricing_plans.find_one({"id": plan_id}, {"_id": 0})
    return updated


@router.delete("/{plan_id}")
async def delete_pricing_plan(
    plan_id: str,
    current_user: User = Depends(get_current_user)
):
    """Delete a pricing plan (admin only)"""
    db = get_db()
    
    if current_user.role not in ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Only admin can delete pricing plans")
    
    existing = await db.pricing_plans.find_one({"id": plan_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Pricing plan not found")
    
    # Check if it's linked to agreements/projects
    linked_agreement = await db.agreements.find_one({"pricing_plan_id": plan_id})
    if linked_agreement:
        raise HTTPException(
            status_code=400, 
            detail="Cannot delete pricing plan linked to an agreement"
        )
    
    await db.pricing_plans.delete_one({"id": plan_id})
    
    return {"message": "Pricing plan deleted", "id": plan_id}


@router.post("/{plan_id}/clone")
async def clone_pricing_plan(
    plan_id: str,
    new_lead_id: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Clone a pricing plan, optionally for a different lead"""
    db = get_db()
    
    existing = await db.pricing_plans.find_one({"id": plan_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Pricing plan not found")
    
    new_id = f"pp-{int(datetime.now(timezone.utc).timestamp() * 1000)}"
    
    cloned = {
        **existing,
        "id": new_id,
        "lead_id": new_lead_id or existing.get("lead_id"),
        "name": f"{existing.get('name', 'Plan')} (Copy)",
        "status": "draft",
        "created_by": current_user.id,
        "created_by_name": current_user.full_name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    # Ensure tenure_months is set
    if "tenure_months" not in cloned:
        cloned["tenure_months"] = calculate_tenure_months(cloned.get("payment_plan", {}))
    
    await db.pricing_plans.insert_one(cloned)
    cloned.pop("_id", None)
    
    return cloned


@router.post("/backfill-tenure")
async def backfill_tenure_months(
    current_user: User = Depends(get_current_user)
):
    """
    Backfill tenure_months for all existing pricing plans that don't have it.
    Admin only.
    """
    db = get_db()
    
    if current_user.role not in ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Admin only")
    
    # Find plans without tenure_months
    plans = await db.pricing_plans.find(
        {"tenure_months": {"$exists": False}},
        {"_id": 0, "id": 1, "payment_plan": 1}
    ).to_list(1000)
    
    updated_count = 0
    for plan in plans:
        tenure = calculate_tenure_months(plan.get("payment_plan", {}))
        await db.pricing_plans.update_one(
            {"id": plan["id"]},
            {"$set": {"tenure_months": tenure}}
        )
        updated_count += 1
    
    return {
        "message": f"Backfilled tenure_months for {updated_count} pricing plans",
        "updated_count": updated_count
    }
