"""
Follow-ups Router — Centralized follow-up system across all funnel stages.
Supports: create, update, close, schedule-next, history, escalation, reassignment.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, timezone, timedelta
import uuid

from .deps import get_db
from .auth import get_current_user
from .models import User

router = APIRouter(prefix="/follow-ups", tags=["Follow-ups"])

VALID_ENTITY_TYPES = ["lead", "meeting", "pricing_plan", "sow", "quotation", "agreement", "payment", "kickoff", "project"]


class FollowUpCreate(BaseModel):
    entity_type: str  # lead, meeting, pricing_plan, sow, quotation, agreement, payment, kickoff, project
    entity_id: str
    lead_id: Optional[str] = None  # Always link back to lead for ownership transfer
    client_name: Optional[str] = None
    due_date: datetime
    notes: Optional[str] = None
    priority: Optional[str] = "medium"  # low, medium, high


class FollowUpUpdate(BaseModel):
    notes: str
    outcome: Optional[str] = None  # e.g., "client interested", "needs more time", etc.


class ScheduleNextFollowUp(BaseModel):
    due_date: datetime
    notes: Optional[str] = None
    priority: Optional[str] = "medium"


class ReassignFollowUp(BaseModel):
    new_owner_id: str
    reason: Optional[str] = None
    transfer_all_stages: bool = True  # Transfer ownership across entire funnel


def serialize_doc(doc):
    """Remove _id from MongoDB doc and convert datetime fields."""
    if doc and "_id" in doc:
        del doc["_id"]
    if doc:
        for key, val in doc.items():
            if isinstance(val, datetime):
                doc[key] = val.isoformat()
    return doc


def serialize_list(docs):
    """Serialize a list of MongoDB docs."""
    return [serialize_doc(d) for d in docs]


@router.post("")
async def create_follow_up(data: FollowUpCreate, current_user: User = Depends(get_current_user)):
    """Create a new follow-up for any funnel entity."""
    db = get_db()

    if data.entity_type not in VALID_ENTITY_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid entity_type. Must be one of: {VALID_ENTITY_TYPES}")

    # Auto-resolve client_name from lead if not provided
    client_name = data.client_name
    lead_id = data.lead_id
    if not client_name and lead_id:
        lead = await db.leads.find_one({"id": lead_id}, {"_id": 0, "company": 1, "first_name": 1, "last_name": 1})
        if lead:
            client_name = lead.get("company") or f"{lead.get('first_name', '')} {lead.get('last_name', '')}".strip()

    # If entity is a lead and no lead_id, use entity_id
    if data.entity_type == "lead" and not lead_id:
        lead_id = data.entity_id
        if not client_name:
            lead = await db.leads.find_one({"id": lead_id}, {"_id": 0, "company": 1, "first_name": 1, "last_name": 1})
            if lead:
                client_name = lead.get("company") or f"{lead.get('first_name', '')} {lead.get('last_name', '')}".strip()

    follow_up = {
        "id": str(uuid.uuid4()),
        "entity_type": data.entity_type,
        "entity_id": data.entity_id,
        "lead_id": lead_id,
        "client_name": client_name or "Unknown",
        "assigned_to": current_user.id,
        "assigned_to_name": current_user.full_name,
        "created_by": current_user.id,
        "created_by_name": current_user.full_name,
        "due_date": data.due_date,
        "notes": data.notes,
        "priority": data.priority or "medium",
        "status": "open",  # open, closed
        "history": [{
            "action": "created",
            "date": datetime.now(timezone.utc).isoformat(),
            "by": current_user.full_name,
            "by_id": current_user.id,
            "notes": data.notes,
            "due_date": data.due_date.isoformat(),
        }],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "closed_at": None,
        "last_follow_up_summary": None,
    }

    await db.follow_ups.insert_one(follow_up)

    # Also update the entity's next_follow_up field for backward compat
    if data.entity_type == "lead":
        await db.leads.update_one(
            {"id": data.entity_id},
            {"$set": {"next_follow_up": data.due_date, "follow_up_notes": data.notes}}
        )

    return serialize_doc(follow_up)


@router.get("")
async def list_follow_ups(
    status: Optional[str] = None,
    entity_type: Optional[str] = None,
    assigned_to: Optional[str] = None,
    overdue_only: bool = False,
    current_user: User = Depends(get_current_user),
):
    """List follow-ups with filters."""
    db = get_db()
    query = {}

    is_admin = current_user.role == "admin"
    is_manager = current_user.role in ["sales_manager", "manager", "principal_consultant", "admin"]

    # Scope: admins/managers see all, others see own
    if not is_admin and not is_manager:
        query["assigned_to"] = current_user.id
    elif assigned_to:
        query["assigned_to"] = assigned_to

    if status:
        query["status"] = status
    if entity_type:
        query["entity_type"] = entity_type
    if overdue_only:
        query["due_date"] = {"$lt": datetime.utcnow()}
        query["status"] = "open"

    follow_ups = await db.follow_ups.find(query, {"_id": 0}).sort("due_date", 1).to_list(500)
    return serialize_list(follow_ups)


@router.get("/dashboard/today")
async def get_today_follow_ups(current_user: User = Depends(get_current_user)):
    """Get follow-ups due today for dashboard widget. Includes overdue items."""
    db = get_db()

    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)

    is_admin = current_user.role == "admin"
    is_manager = current_user.role in ["sales_manager", "manager", "principal_consultant"]

    # Base query: open follow-ups due today or overdue
    query = {
        "status": "open",
        "due_date": {"$lt": today_end},
    }

    # Scope
    if not is_admin and not is_manager:
        query["assigned_to"] = current_user.id
    elif is_manager and not is_admin:
        # Manager sees own + reportees
        reportees = await db.employees.find(
            {"reporting_to": current_user.id}, {"_id": 0, "user_id": 1}
        ).to_list(100)
        reportee_ids = [r["user_id"] for r in reportees if r.get("user_id")]
        query["assigned_to"] = {"$in": [current_user.id] + reportee_ids}

    follow_ups = await db.follow_ups.find(query, {"_id": 0}).sort("due_date", 1).to_list(50)

    # Annotate each with overdue status
    for fu in follow_ups:
        due = fu.get("due_date")
        if isinstance(due, str):
            try:
                due_dt = datetime.fromisoformat(due.replace("Z", "+00:00")).replace(tzinfo=None)
            except Exception:
                due_dt = now
        elif isinstance(due, datetime):
            due_dt = due.replace(tzinfo=None) if due.tzinfo else due
        else:
            due_dt = now
        fu["is_overdue"] = due_dt < today_start
        fu["days_overdue"] = max(0, (today_start - due_dt).days) if due_dt < today_start else 0

    overdue_count = sum(1 for fu in follow_ups if fu["is_overdue"])
    today_count = sum(1 for fu in follow_ups if not fu["is_overdue"])

    return {
        "items": serialize_list(follow_ups),
        "overdue_count": overdue_count,
        "today_count": today_count,
        "total": len(follow_ups),
    }


@router.get("/escalations")
async def get_escalated_follow_ups(current_user: User = Depends(get_current_user)):
    """Get follow-ups that are overdue by >2 days — visible to managers/admin.
    Shows which sales person missed follow-ups so manager can take action."""
    db = get_db()

    is_manager = current_user.role in ["sales_manager", "manager", "principal_consultant", "admin"]
    if not is_manager:
        raise HTTPException(status_code=403, detail="Only managers can view escalations")

    cutoff = datetime.utcnow() - timedelta(days=2)

    query = {
        "status": "open",
        "due_date": {"$lt": cutoff},
    }

    # If not admin, scope to reportees
    if current_user.role != "admin":
        reportees = await db.employees.find(
            {"reporting_to": current_user.id}, {"_id": 0, "user_id": 1}
        ).to_list(100)
        reportee_ids = [r["user_id"] for r in reportees if r.get("user_id")]
        if reportee_ids:
            query["assigned_to"] = {"$in": reportee_ids}
        else:
            return {"items": [], "total": 0}

    escalated = await db.follow_ups.find(query, {"_id": 0}).sort("due_date", 1).to_list(100)

    # Compute days overdue
    now = datetime.utcnow()
    for fu in escalated:
        due = fu.get("due_date")
        try:
            if isinstance(due, str):
                due_dt = datetime.fromisoformat(due.replace("Z", "+00:00")).replace(tzinfo=None)
            elif isinstance(due, datetime):
                due_dt = due.replace(tzinfo=None) if due.tzinfo else due
            else:
                due_dt = now
            fu["days_overdue"] = max(0, (now - due_dt).days)
        except Exception:
            fu["days_overdue"] = 0

    return {"items": serialize_list(escalated), "total": len(escalated)}


@router.get("/{follow_up_id}")
async def get_follow_up(follow_up_id: str, current_user: User = Depends(get_current_user)):
    """Get a single follow-up with full history."""
    db = get_db()
    fu = await db.follow_ups.find_one({"id": follow_up_id}, {"_id": 0})
    if not fu:
        raise HTTPException(status_code=404, detail="Follow-up not found")
    return fu


@router.put("/{follow_up_id}/update")
async def add_follow_up_update(follow_up_id: str, data: FollowUpUpdate, current_user: User = Depends(get_current_user)):
    """Add an update/note to an open follow-up."""
    db = get_db()

    fu = await db.follow_ups.find_one({"id": follow_up_id}, {"_id": 0})
    if not fu:
        raise HTTPException(status_code=404, detail="Follow-up not found")

    history_entry = {
        "action": "updated",
        "date": datetime.now(timezone.utc).isoformat(),
        "by": current_user.full_name,
        "by_id": current_user.id,
        "notes": data.notes,
        "outcome": data.outcome,
    }

    await db.follow_ups.update_one(
        {"id": follow_up_id},
        {
            "$push": {"history": history_entry},
            "$set": {
                "last_follow_up_summary": data.notes,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
        },
    )

    updated = await db.follow_ups.find_one({"id": follow_up_id}, {"_id": 0})
    return serialize_doc(updated)


@router.put("/{follow_up_id}/close")
async def close_follow_up(follow_up_id: str, data: FollowUpUpdate, current_user: User = Depends(get_current_user)):
    """Close a follow-up with a final summary."""
    db = get_db()

    fu = await db.follow_ups.find_one({"id": follow_up_id}, {"_id": 0})
    if not fu:
        raise HTTPException(status_code=404, detail="Follow-up not found")

    history_entry = {
        "action": "closed",
        "date": datetime.now(timezone.utc).isoformat(),
        "by": current_user.full_name,
        "by_id": current_user.id,
        "notes": data.notes,
        "outcome": data.outcome,
    }

    await db.follow_ups.update_one(
        {"id": follow_up_id},
        {
            "$push": {"history": history_entry},
            "$set": {
                "status": "closed",
                "last_follow_up_summary": data.notes,
                "closed_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
        },
    )

    # Clear the entity's next_follow_up if it's a lead
    if fu.get("entity_type") == "lead":
        await db.leads.update_one(
            {"id": fu["entity_id"]},
            {"$set": {"next_follow_up": None, "follow_up_notes": None}}
        )

    updated = await db.follow_ups.find_one({"id": follow_up_id}, {"_id": 0})
    return serialize_doc(updated)


@router.post("/{follow_up_id}/schedule-next")
async def schedule_next_follow_up(follow_up_id: str, data: ScheduleNextFollowUp, current_user: User = Depends(get_current_user)):
    """Close current follow-up and create a new one with next date."""
    db = get_db()

    fu = await db.follow_ups.find_one({"id": follow_up_id}, {"_id": 0})
    if not fu:
        raise HTTPException(status_code=404, detail="Follow-up not found")

    # Close current
    close_entry = {
        "action": "closed_with_next",
        "date": datetime.now(timezone.utc).isoformat(),
        "by": current_user.full_name,
        "by_id": current_user.id,
        "notes": f"Closed and scheduled next follow-up for {data.due_date.strftime('%Y-%m-%d')}",
    }

    await db.follow_ups.update_one(
        {"id": follow_up_id},
        {
            "$push": {"history": close_entry},
            "$set": {
                "status": "closed",
                "closed_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
        },
    )

    # Create next follow-up
    new_follow_up = {
        "id": str(uuid.uuid4()),
        "entity_type": fu["entity_type"],
        "entity_id": fu["entity_id"],
        "lead_id": fu.get("lead_id"),
        "client_name": fu.get("client_name", "Unknown"),
        "assigned_to": fu["assigned_to"],
        "assigned_to_name": fu.get("assigned_to_name", ""),
        "created_by": current_user.id,
        "created_by_name": current_user.full_name,
        "due_date": data.due_date,
        "notes": data.notes,
        "priority": data.priority or fu.get("priority", "medium"),
        "status": "open",
        "history": [{
            "action": "created",
            "date": datetime.now(timezone.utc).isoformat(),
            "by": current_user.full_name,
            "by_id": current_user.id,
            "notes": data.notes,
            "due_date": data.due_date.isoformat(),
            "previous_follow_up_id": follow_up_id,
        }],
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
        "closed_at": None,
        "last_follow_up_summary": fu.get("last_follow_up_summary"),
    }

    await db.follow_ups.insert_one(new_follow_up)

    # Update entity's next_follow_up
    if fu.get("entity_type") == "lead":
        await db.leads.update_one(
            {"id": fu["entity_id"]},
            {"$set": {"next_follow_up": data.due_date, "follow_up_notes": data.notes}}
        )

    return serialize_doc(new_follow_up)


@router.post("/{follow_up_id}/reassign")
async def reassign_follow_up(follow_up_id: str, data: ReassignFollowUp, current_user: User = Depends(get_current_user)):
    """Reassign a follow-up (and optionally all funnel stages) to another sales person.
    Only managers and admins can reassign."""
    db = get_db()

    is_manager = current_user.role in ["sales_manager", "manager", "principal_consultant", "admin"]
    if not is_manager:
        raise HTTPException(status_code=403, detail="Only managers can reassign follow-ups")

    fu = await db.follow_ups.find_one({"id": follow_up_id}, {"_id": 0})
    if not fu:
        raise HTTPException(status_code=404, detail="Follow-up not found")

    # Get new owner info
    new_owner = await db.users.find_one({"id": data.new_owner_id}, {"_id": 0, "id": 1, "full_name": 1})
    if not new_owner:
        raise HTTPException(status_code=404, detail="New owner not found")

    old_owner_name = fu.get("assigned_to_name", "Unknown")
    new_owner_name = new_owner.get("full_name", "Unknown")

    # Reassign this follow-up
    history_entry = {
        "action": "reassigned",
        "date": datetime.now(timezone.utc).isoformat(),
        "by": current_user.full_name,
        "by_id": current_user.id,
        "notes": data.reason or f"Reassigned from {old_owner_name} to {new_owner_name}",
        "old_owner": old_owner_name,
        "new_owner": new_owner_name,
    }

    await db.follow_ups.update_one(
        {"id": follow_up_id},
        {
            "$push": {"history": history_entry},
            "$set": {
                "assigned_to": data.new_owner_id,
                "assigned_to_name": new_owner_name,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
        },
    )

    transfer_results = {"follow_up": True}

    # Transfer entire funnel ownership if requested
    if data.transfer_all_stages and fu.get("lead_id"):
        lead_id = fu["lead_id"]

        # Transfer lead
        await db.leads.update_one(
            {"id": lead_id},
            {"$set": {
                "assigned_to": data.new_owner_id,
                "lead_owner": data.new_owner_id,
                "created_by": data.new_owner_id,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }}
        )
        transfer_results["lead"] = True

        # Transfer all open follow-ups for this lead
        await db.follow_ups.update_many(
            {"lead_id": lead_id, "status": "open"},
            {"$set": {
                "assigned_to": data.new_owner_id,
                "assigned_to_name": new_owner_name,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
            "$push": {"history": {
                "action": "bulk_reassigned",
                "date": datetime.now(timezone.utc).isoformat(),
                "by": current_user.full_name,
                "by_id": current_user.id,
                "notes": f"Bulk reassigned as part of lead transfer to {new_owner_name}",
            }}}
        )

        # Transfer meetings
        r = await db.meetings.update_many(
            {"lead_id": lead_id},
            {"$set": {"created_by": data.new_owner_id}}
        )
        transfer_results["meetings"] = r.modified_count

        # Transfer pricing plans
        r = await db.pricing_plans.update_many(
            {"lead_id": lead_id},
            {"$set": {"created_by": data.new_owner_id}}
        )
        transfer_results["pricing_plans"] = r.modified_count

        # Transfer SOWs
        r = await db.sows.update_many(
            {"lead_id": lead_id},
            {"$set": {"created_by": data.new_owner_id}}
        )
        transfer_results["sows"] = r.modified_count

        # Transfer quotations
        r = await db.quotations.update_many(
            {"lead_id": lead_id},
            {"$set": {"created_by": data.new_owner_id}}
        )
        transfer_results["quotations"] = r.modified_count

        # Transfer agreements
        r = await db.agreements.update_many(
            {"lead_id": lead_id},
            {"$set": {"created_by": data.new_owner_id}}
        )
        transfer_results["agreements"] = r.modified_count

    updated = await db.follow_ups.find_one({"id": follow_up_id}, {"_id": 0})
    return {
        "follow_up": serialize_doc(updated),
        "transfer_results": transfer_results,
        "message": f"Follow-up reassigned to {new_owner_name}" + (
            f". All funnel stages for this lead have been transferred." if data.transfer_all_stages else ""
        ),
    }
