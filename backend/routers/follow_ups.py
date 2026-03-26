"""
Follow-ups Router — Centralized follow-up system across all funnel stages.
Supports: create, update, close, schedule-next, history, escalation, reassignment.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, timezone, timedelta
import uuid
import os

from .deps import get_db
from .deps import get_current_user
from .models import User
from fastapi import Response, Request

router = APIRouter(prefix="/follow-ups", tags=["Follow-ups"])

# D&V Logo storage path
DV_LOGO_STORAGE_PATH = "netra-erp/assets/dv-logo.png"

@router.get("/assets/logo.png", include_in_schema=False)
async def serve_logo():
    """Public endpoint to serve D&V logo for emails."""
    import requests as sync_requests
    STORAGE_URL = "https://integrations.emergentagent.com/objstore/api/v1/storage"
    EMERGENT_KEY = os.environ.get("EMERGENT_LLM_KEY")
    try:
        init_resp = sync_requests.post(f"{STORAGE_URL}/init", json={"emergent_key": EMERGENT_KEY}, timeout=10)
        storage_key = init_resp.json()["storage_key"]
        resp = sync_requests.get(f"{STORAGE_URL}/objects/{DV_LOGO_STORAGE_PATH}", headers={"X-Storage-Key": storage_key}, timeout=30)
        resp.raise_for_status()
        return Response(content=resp.content, media_type="image/png", headers={"Cache-Control": "public, max-age=86400"})
    except Exception:
        # Fallback to existing web logo
        return Response(status_code=302, headers={"Location": "https://dvconsulting.co.in/wp-content/uploads/2020/02/logov4-min.png"})

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

    # Governance: Due date must not be in the past
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    due_date_utc = data.due_date.replace(tzinfo=timezone.utc) if data.due_date.tzinfo is None else data.due_date
    if due_date_utc < today_start:
        raise HTTPException(status_code=400, detail="Due date cannot be in the past. Please select today or a future date.")

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
    search: Optional[str] = Query(None, description="Search in notes, entity name"),
    due_date: Optional[str] = Query(None, description="Filter by due date (YYYY-MM-DD or TODAY)"),
    due_from: Optional[str] = Query(None, description="Due date from (YYYY-MM-DD)"),
    due_to: Optional[str] = Query(None, description="Due date to (YYYY-MM-DD)"),
    priority: Optional[str] = Query(None, description="Filter by priority"),
    sort_field: Optional[str] = Query("due_date", description="Sort field"),
    sort_direction: Optional[str] = Query("asc", description="Sort direction (asc/desc)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=500, description="Items per page"),
    current_user: User = Depends(get_current_user),
):
    """List follow-ups with filters, sorting, and pagination.
    
    SALES DATATABLE API - Supports Excel-like filtering.
    """
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
    if priority:
        query["priority"] = priority
    
    # Overdue filter
    if overdue_only:
        query["due_date"] = {"$lt": datetime.now(timezone.utc)}
        query["status"] = "open"
    
    # Due date filters
    if due_date == "TODAY":
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)
        query["due_date"] = {"$gte": today_start, "$lt": today_end}
    elif due_from or due_to:
        date_query = {}
        if due_from:
            date_query["$gte"] = datetime.fromisoformat(due_from + "T00:00:00")
        if due_to:
            date_query["$lte"] = datetime.fromisoformat(due_to + "T23:59:59")
        query["due_date"] = date_query
    
    # Text search
    if search:
        search_regex = {"$regex": search, "$options": "i"}
        query["$or"] = [
            {"notes": search_regex},
            {"client_name": search_regex},
            {"assigned_to_name": search_regex}
        ]
    
    # Sorting
    sort_order = 1 if sort_direction == "asc" else -1
    valid_sort_fields = ["due_date", "created_at", "status", "priority", "entity_type"]
    if sort_field not in valid_sort_fields:
        sort_field = "due_date"
    
    # Pagination
    skip = (page - 1) * page_size
    
    # Get total and paginated data
    total = await db.follow_ups.count_documents(query)
    follow_ups = await db.follow_ups.find(query, {"_id": 0}).sort(sort_field, sort_order).skip(skip).limit(page_size).to_list(page_size)
    
    # Enrich with lead email for linked leads
    lead_ids = list(set(f["lead_id"] for f in follow_ups if f.get("lead_id")))
    if lead_ids:
        leads_data = await db.leads.find(
            {"id": {"$in": lead_ids}},
            {"_id": 0, "id": 1, "email": 1, "company": 1, "first_name": 1, "last_name": 1}
        ).to_list(len(lead_ids))
        lead_map = {l["id"]: l for l in leads_data}
        for fu in follow_ups:
            if fu.get("lead_id") and fu["lead_id"] in lead_map:
                lead = lead_map[fu["lead_id"]]
                fu["lead_email"] = lead.get("email", "")
                fu["lead_company"] = lead.get("company", "")
                if not fu.get("client_name"):
                    fu["client_name"] = lead.get("company") or f"{lead.get('first_name', '')} {lead.get('last_name', '')}".strip()
    
    return {
        "data": serialize_list(follow_ups),
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size if total > 0 else 1
    }


@router.get("/dashboard/today")
async def get_today_follow_ups(current_user: User = Depends(get_current_user)):
    """Get follow-ups due today for dashboard widget. Includes overdue items."""
    db = get_db()

    now = datetime.now(timezone.utc)
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
    # Strip timezone from today_start for comparison since we normalize due_dt to naive
    today_start_naive = today_start.replace(tzinfo=None)
    now_naive = now.replace(tzinfo=None)
    
    for fu in follow_ups:
        due = fu.get("due_date")
        if isinstance(due, str):
            try:
                due_dt = datetime.fromisoformat(due.replace("Z", "+00:00")).replace(tzinfo=None)
            except Exception:
                due_dt = now_naive
        elif isinstance(due, datetime):
            due_dt = due.replace(tzinfo=None) if due.tzinfo else due
        else:
            due_dt = now_naive
        fu["is_overdue"] = due_dt < today_start_naive
        fu["days_overdue"] = max(0, (today_start_naive - due_dt).days) if due_dt < today_start_naive else 0

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

    cutoff = datetime.now(timezone.utc) - timedelta(days=2)

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
    now = datetime.now(timezone.utc)
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
    """Get a single follow-up with full history. Enriches with latest lead data."""
    db = get_db()
    fu = await db.follow_ups.find_one({"id": follow_up_id}, {"_id": 0})
    if not fu:
        raise HTTPException(status_code=404, detail="Follow-up not found")
    
    # Enrich with latest lead data (email, company, name)
    if fu.get("lead_id"):
        lead = await db.leads.find_one(
            {"id": fu["lead_id"]},
            {"_id": 0, "email": 1, "company": 1, "first_name": 1, "last_name": 1}
        )
        if lead:
            fu["lead_email"] = lead.get("email", "")
            fu["lead_company"] = lead.get("company", "")
            if not fu.get("client_name"):
                fu["client_name"] = lead.get("company") or f"{lead.get('first_name', '')} {lead.get('last_name', '')}".strip()
    
    return serialize_doc(fu)


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
    
    if fu.get("status") == "closed":
        raise HTTPException(status_code=400, detail="This follow-up is already closed.")

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
    
    if fu.get("status") == "closed":
        raise HTTPException(status_code=400, detail="This follow-up is already closed. Cannot schedule next.")

    # Governance: Next due date must not be in the past
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    due_date_utc = data.due_date.replace(tzinfo=timezone.utc) if data.due_date.tzinfo is None else data.due_date
    if due_date_utc < today_start:
        raise HTTPException(status_code=400, detail="Next due date cannot be in the past.")

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
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
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
    
    if fu.get("status") == "closed":
        raise HTTPException(status_code=400, detail="Cannot reassign a closed follow-up.")

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



class FollowUpEmailRequest(BaseModel):
    subject: str
    body: str
    recipient_email: Optional[str] = None  # Override lead email if needed


@router.post("/{follow_up_id}/send-email")
async def send_follow_up_email(
    follow_up_id: str,
    data: FollowUpEmailRequest,
    current_user: User = Depends(get_current_user)
):
    """Send a follow-up email to the lead's contact.
    Pre-fills with follow-up details, user can edit before sending."""
    db = get_db()
    
    fu = await db.follow_ups.find_one({"id": follow_up_id}, {"_id": 0})
    if not fu:
        raise HTTPException(status_code=404, detail="Follow-up not found")
    
    # Get lead email
    recipient_email = data.recipient_email
    if not recipient_email and fu.get("lead_id"):
        lead = await db.leads.find_one({"id": fu["lead_id"]}, {"_id": 0, "email": 1})
        if lead:
            recipient_email = lead.get("email")
    
    if not recipient_email:
        raise HTTPException(status_code=400, detail="No recipient email found. Please provide one or ensure the lead has an email.")
    
    if fu.get("status") == "closed":
        raise HTTPException(status_code=400, detail="Cannot send email for a closed follow-up.")
    
    # Use the existing async email service
    from services.email_service import send_email
    
    # Build branded HTML email with D&V logo and styled CTA buttons
    base_url = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
    if not base_url:
        base_url = "https://attendance-approvals.preview.emergentagent.com"
    close_link = f"{base_url}/api/follow-ups/{follow_up_id}/client-action?action=close"
    reschedule_link = f"{base_url}/api/follow-ups/{follow_up_id}/client-action?action=reschedule"
    logo_url = f"{base_url}/api/follow-ups/assets/logo.png"
    
    # Convert plain text body to clean HTML with table format for structured content
    body_lines = data.body.strip().split('\n')
    body_html_parts = []
    table_rows = []
    skip_keywords = ['client-action?action=', 'Confirm & Close', 'Reschedule Follow-up:', 'All Good - Close:', 'Need More Time -', 'To confirm', 'To request', 'If everything is aligned', 'If you need to reschedule']
    
    def flush_table():
        nonlocal table_rows
        if table_rows:
            rows_html = ''.join(f'<tr><td style="padding: 8px 14px; border-bottom: 1px solid #f0f0f0; color: #374151; font-size: 14px; line-height: 1.6;">{r}</td></tr>' for r in table_rows)
            body_html_parts.append(f'<table style="width: 100%; border-collapse: collapse; background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 6px; margin: 10px 0; overflow: hidden;"><tbody>{rows_html}</tbody></table>')
            table_rows = []
    
    for line in body_lines:
        stripped = line.strip()
        if any(kw in stripped for kw in skip_keywords):
            continue
        # Detect bullet/list lines and add to table
        if stripped.startswith('-') or stripped.startswith('•') or stripped.startswith('*'):
            table_rows.append(stripped.lstrip('-•* ').strip())
        elif ':' in stripped and len(stripped.split(':')[0]) < 30 and not stripped.startswith('Dear') and not stripped.startswith('Best') and not stripped.startswith('Warm'):
            # Key: Value pairs → table rows
            flush_table()
            key, val = stripped.split(':', 1)
            table_rows.append(f'<strong style="color: #111827;">{key.strip()}</strong>: {val.strip()}')
        else:
            flush_table()
            if stripped == '':
                body_html_parts.append('<br>')
            else:
                body_html_parts.append(f'<p style="margin: 0 0 6px 0; color: #374151; font-size: 15px; line-height: 1.7;">{stripped}</p>')
    flush_table()
    
    body_html = '\n'.join(body_html_parts)
    sender_name = current_user.full_name
    
    # Format the follow-up due date/time for display in email
    due_date = fu.get("due_date", "")
    entity_type = fu.get("entity_type", "")
    schedule_labels = {
        "lead": "Follow-up Scheduled",
        "meeting": "Meeting Scheduled",
        "pricing_plan": "Pricing Discussion Scheduled",
        "sow": "SOW Review Scheduled",
        "quotation": "Quotation Review Scheduled",
        "agreement": "Agreement Discussion Scheduled",
        "payment": "Payment Follow-up Scheduled",
        "kickoff": "Kickoff Scheduled",
        "project": "Project Review Scheduled",
    }
    schedule_label = schedule_labels.get(entity_type, "Follow-up Scheduled")
    schedule_html = ""
    if due_date:
        try:
            dt = datetime.fromisoformat(due_date.replace("Z", "+00:00")) if isinstance(due_date, str) else due_date
            schedule_display = dt.strftime("%A, %B %d, %Y at %I:%M %p")
            schedule_html = f"""
        <!-- Scheduled Date/Time Block -->
        <div style="padding: 0 36px 24px 36px;">
            <div style="background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 8px; padding: 16px 20px;">
                <p style="margin: 0 0 4px 0; color: #166534; font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;">{schedule_label}</p>
                <p style="margin: 0; color: #15803d; font-size: 16px; font-weight: 600;">{schedule_display}</p>
            </div>
        </div>"""
        except Exception:
            pass
    
    html_content = f"""
    <div style="font-family: 'Segoe UI', Arial, sans-serif; max-width: 600px; margin: 0 auto; background: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 12px rgba(0,0,0,0.06);">
        <!-- Logo Header - White Background -->
        <div style="padding: 28px 32px 20px 32px; text-align: center; border-bottom: 1px solid #f0f0f0;">
            <img src="{logo_url}" alt="D&V Business Consulting" style="max-height: 64px; max-width: 240px; width: auto;" />
        </div>
        
        <!-- Body -->
        <div style="padding: 32px 36px 20px 36px;">
            {body_html}
        </div>
        
        {schedule_html}
        
        <!-- CTA Buttons -->
        <div style="padding: 8px 36px 36px 36px; text-align: center;">
            <p style="margin: 0 0 20px 0; color: #6b7280; font-size: 14px;">How would you like to proceed?</p>
            <table cellpadding="0" cellspacing="0" border="0" style="margin: 0 auto;">
                <tr>
                    <td style="padding-right: 14px;">
                        <a href="{close_link}" style="display: inline-block; background: #059669; color: #ffffff; text-decoration: none; padding: 14px 32px; border-radius: 8px; font-size: 14px; font-weight: 600;">Looks Good, Confirm</a>
                    </td>
                    <td>
                        <a href="{reschedule_link}" style="display: inline-block; background: #ffffff; color: #b45309; text-decoration: none; padding: 13px 32px; border-radius: 8px; font-size: 14px; font-weight: 600; border: 2px solid #d97706;">Reschedule</a>
                    </td>
                </tr>
            </table>
        </div>
        
        <!-- Signature -->
        <div style="padding: 20px 36px; border-top: 1px solid #f0f0f0;">
            <p style="margin: 0; color: #111827; font-size: 14px; font-weight: 600;">{sender_name}</p>
            <p style="margin: 2px 0 0 0; color: #9ca3af; font-size: 13px;">D&amp;V Business Consulting</p>
        </div>
        
        <!-- Footer -->
        <div style="background: #f9fafb; padding: 14px 36px; text-align: center;">
            <p style="margin: 0; color: #b0b7c3; font-size: 10px;">D&amp;V Business Consulting &bull; Sent via NETRA</p>
        </div>
    </div>
    """
    
    result = await send_email(
        to_email=recipient_email,
        subject=data.subject,
        html_content=html_content,
        plain_content=data.body,
        reply_to=current_user.email if hasattr(current_user, 'email') else None
    )
    
    if result.get("status") == "error":
        raise HTTPException(status_code=500, detail=result.get("message", "Failed to send email"))
    
    # Log email in follow-up history
    now = datetime.now(timezone.utc).isoformat()
    await db.follow_ups.update_one(
        {"id": follow_up_id},
        {"$push": {"history": {
            "action": "email_sent",
            "date": now,
            "by": current_user.full_name,
            "by_id": current_user.id,
            "notes": f"Email sent to {recipient_email}: {data.subject}",
        }},
        "$set": {"updated_at": now}}
    )
    
    return {
        "message": f"Email sent to {recipient_email}",
        "recipient": recipient_email,
        "subject": data.subject,
    }


@router.get("/{follow_up_id}/email-template")
async def get_follow_up_email_template(
    follow_up_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get a pre-filled email template for a follow-up."""
    db = get_db()
    
    fu = await db.follow_ups.find_one({"id": follow_up_id}, {"_id": 0})
    if not fu:
        raise HTTPException(status_code=404, detail="Follow-up not found")
    
    # Get lead details
    lead = None
    if fu.get("lead_id"):
        lead = await db.leads.find_one({"id": fu["lead_id"]}, {"_id": 0})
    
    client_name = fu.get("client_name") or (f"{lead.get('first_name', '')} {lead.get('last_name', '')}" if lead else "Client")
    company = lead.get("company", "") if lead else ""
    recipient_email = lead.get("email", "") if lead else ""
    sender_name = current_user.full_name
    
    # Build prefilled subject and body
    stage_labels = {
        "lead": "our conversation",
        "meeting": "our recent meeting",
        "pricing_plan": "the pricing plan",
        "sow": "the scope of work",
        "quotation": "the quotation",
        "agreement": "the agreement",
        "payment": "the payment details",
    }
    stage_text = stage_labels.get(fu.get("entity_type", ""), "our discussion")
    
    subject = f"Follow-up: {stage_text} — {company}" if company else f"Follow-up: {stage_text}"
    
    notes = fu.get('notes', '')
    
    # Format the due date/time for display
    due_date = fu.get("due_date", "")
    entity_type = fu.get("entity_type", "")
    schedule_text_labels = {
        "lead": "Follow-up Scheduled",
        "meeting": "Meeting Scheduled",
        "pricing_plan": "Pricing Discussion Scheduled",
        "sow": "SOW Review Scheduled",
        "quotation": "Quotation Review Scheduled",
        "agreement": "Agreement Discussion Scheduled",
        "payment": "Payment Follow-up Scheduled",
        "kickoff": "Kickoff Scheduled",
        "project": "Project Review Scheduled",
    }
    schedule_label = schedule_text_labels.get(entity_type, "Follow-up Scheduled")
    schedule_display = ""
    if due_date:
        try:
            dt = datetime.fromisoformat(due_date.replace("Z", "+00:00")) if isinstance(due_date, str) else due_date
            schedule_display = dt.strftime("%A, %B %d, %Y at %I:%M %p")
        except Exception:
            schedule_display = str(due_date)
    
    body = (
        f"Dear {client_name.strip()},\n\n"
        f"I hope this email finds you well. I wanted to follow up regarding {stage_text}"
        f"{f' for {company}' if company else ''}.\n\n"
        f"{notes}\n\n"
        f"{f'{schedule_label}: {schedule_display}' if schedule_display else ''}\n\n"
        f"Please let me know if you have any questions or need additional information. "
        f"I'd be happy to schedule a call at your convenience.\n\n"
        f"Best regards,\n{sender_name}"
    )
    
    return {
        "subject": subject,
        "body": body,
        "recipient_email": recipient_email,
        "client_name": client_name.strip(),
        "company": company,
        "schedule_display": schedule_display,
        "schedule_label": schedule_label,
    }


@router.get("/{follow_up_id}/client-action")
async def client_follow_up_action(
    follow_up_id: str,
    action: str = "view",
    response_text: Optional[str] = None,
):
    """Public endpoint for client CTA buttons in emails.
    No auth required - uses follow_up_id as token.
    Returns a branded HTML response page."""
    db = get_db()
    
    fu = await db.follow_ups.find_one({"id": follow_up_id}, {"_id": 0})
    if not fu:
        return HTMLResponse(content=_build_action_page("Not Found", "This follow-up could not be found.", "error"), status_code=404)
    
    now = datetime.now(timezone.utc).isoformat()
    client_name = fu.get("client_name", "Client")
    due_date = fu.get("due_date", "")
    
    # Format due date nicely
    due_display = ""
    if due_date:
        try:
            dt = datetime.fromisoformat(due_date.replace("Z", "+00:00")) if isinstance(due_date, str) else due_date
            due_display = dt.strftime("%A, %B %d, %Y at %I:%M %p")
        except Exception:
            due_display = str(due_date)
    
    if action == "close":
        # Guard: already closed
        if fu.get("status") == "closed":
            details = f"Hi {client_name}, this follow-up has already been confirmed."
            if due_display:
                details += f"<br><br><div style='background:#f0fdf4;border:1px solid #bbf7d0;border-radius:8px;padding:14px 16px;'><p style='margin:0 0 4px 0;color:#166534;font-size:12px;font-weight:600;'>Confirmed Schedule</p><p style='margin:0;color:#15803d;font-size:15px;font-weight:600;'>{due_display}</p></div>"
            return HTMLResponse(content=_build_action_page("Already Confirmed", details, "success"))
        await db.follow_ups.update_one(
            {"id": follow_up_id},
            {"$set": {"status": "closed", "closed_at": now, "updated_at": now, "client_response": "Confirmed via email"},
             "$push": {"history": {
                "action": "client_closed",
                "date": now,
                "by": "Client (via email)",
                "notes": response_text or "Client confirmed via email CTA",
            }}}
        )
        details = f"Thank you for confirming, {client_name}! Your response has been recorded."
        if due_display:
            details += f"<br><br><div style='background:#f0fdf4;border:1px solid #bbf7d0;border-radius:8px;padding:16px;margin-top:8px;text-align:left;'><p style='margin:0 0 4px;color:#166534;font-size:13px;font-weight:600;'>Scheduled Follow-up</p><p style='margin:0;color:#15803d;font-size:15px;'>{due_display}</p></div>"
        details += "<br>Our team has been notified and will be in touch."
        return HTMLResponse(content=_build_action_page("Confirmed!", details, "success"))
    
    elif action == "reschedule":
        # Guard: already closed
        if fu.get("status") == "closed":
            details = f"Hi {client_name}, this follow-up has already been confirmed and cannot be rescheduled."
            if due_display:
                details += f"<br><br><div style='background:#f0fdf4;border:1px solid #bbf7d0;border-radius:8px;padding:14px 16px;'><p style='margin:0 0 4px 0;color:#166534;font-size:12px;font-weight:600;'>Confirmed Schedule</p><p style='margin:0;color:#15803d;font-size:15px;font-weight:600;'>{due_display}</p></div>"
            return HTMLResponse(content=_build_action_page("Already Confirmed", details, "success"))
        # Show a date/time picker form instead of instant confirmation
        base_url = os.environ.get("REACT_APP_BACKEND_URL", "https://attendance-approvals.preview.emergentagent.com").rstrip("/")
        submit_url = f"{base_url}/api/follow-ups/{follow_up_id}/client-reschedule"
        return HTMLResponse(content=_build_reschedule_page(client_name, due_display, submit_url))
    
    else:
        return HTMLResponse(content=_build_action_page(
            "Follow-up Details",
            f"Client: {client_name}<br>Status: {fu.get('status', 'open').title()}",
            "info"
        ))


@router.post("/{follow_up_id}/client-reschedule")
async def client_reschedule_submit(follow_up_id: str, request: Request):
    """Handle reschedule form submission from client."""
    db = get_db()
    
    fu = await db.follow_ups.find_one({"id": follow_up_id}, {"_id": 0})
    if not fu:
        return HTMLResponse(content=_build_action_page("Not Found", "This follow-up could not be found.", "error"), status_code=404)
    
    if fu.get("status") == "closed":
        return HTMLResponse(content=_build_action_page("Already Confirmed", "This follow-up has already been confirmed and cannot be rescheduled.", "success"))
    
    # Parse form data
    form = await request.form()
    new_date = form.get("preferred_date", "")
    new_time = form.get("preferred_time", "")
    client_message = form.get("message", "")
    
    now = datetime.now(timezone.utc).isoformat()
    client_name = fu.get("client_name", "Client")
    
    reschedule_note = f"Client requested reschedule"
    if new_date:
        reschedule_note += f" to {new_date}"
    if new_time:
        reschedule_note += f" at {new_time}"
    if client_message:
        reschedule_note += f". Message: {client_message}"
    
    await db.follow_ups.update_one(
        {"id": follow_up_id},
        {"$set": {
            "status": "open",
            "updated_at": now,
            "client_response": reschedule_note,
            "client_preferred_date": new_date,
            "client_preferred_time": new_time,
        },
        "$push": {"history": {
            "action": "client_reschedule",
            "date": now,
            "by": "Client (via email)",
            "notes": reschedule_note,
        }}}
    )
    
    # Build confirmation display
    date_display = ""
    if new_date:
        try:
            dt = datetime.strptime(new_date, "%Y-%m-%d")
            date_display = dt.strftime("%A, %B %d, %Y")
            if new_time:
                date_display += f" at {new_time}"
        except Exception:
            date_display = f"{new_date} {new_time}".strip()
    
    msg = f"Thank you, {client_name}! Your reschedule request has been received."
    if date_display:
        msg += f"<br><br><div style='background:#fffbeb;border:1px solid #fde68a;border-radius:8px;padding:16px;margin-top:8px;text-align:left;'><p style='margin:0 0 4px;color:#92400e;font-size:13px;font-weight:600;'>Preferred Time</p><p style='margin:0;color:#b45309;font-size:15px;'>{date_display}</p></div>"
    msg += "<br>Our team will confirm the new schedule shortly."
    
    return HTMLResponse(content=_build_action_page("Reschedule Requested", msg, "reschedule"))


def _build_action_page(title: str, message: str, action_type: str) -> str:
    """Build a branded HTML response page for client actions with D&V logo."""
    colors = {
        "success": {"bg": "#059669", "icon": "&#10003;", "accent": "#ecfdf5", "border": "#a7f3d0"},
        "reschedule": {"bg": "#d97706", "icon": "&#128197;", "accent": "#fffbeb", "border": "#fde68a"},
        "error": {"bg": "#dc2626", "icon": "&#10007;", "accent": "#fef2f2", "border": "#fecaca"},
        "info": {"bg": "#2563eb", "icon": "&#8505;", "accent": "#eff6ff", "border": "#bfdbfe"},
    }
    c = colors.get(action_type, colors["info"])
    base_url = os.environ.get("REACT_APP_BACKEND_URL", "https://attendance-approvals.preview.emergentagent.com").rstrip("/")
    logo_url = f"{base_url}/api/follow-ups/assets/logo.png"
    
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} — D&V Business Consulting</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #f4f5f7; min-height: 100vh; display: flex; align-items: center; justify-content: center; padding: 20px; }}
        .card {{ background: #fff; border-radius: 12px; box-shadow: 0 4px 24px rgba(0,0,0,0.08); max-width: 480px; width: 100%; overflow: hidden; }}
        .header {{ padding: 28px 32px 20px; text-align: center; border-bottom: 1px solid #f0f0f0; }}
        .header img {{ max-height: 64px; max-width: 240px; width: auto; }}
        .body {{ padding: 40px 32px; text-align: center; }}
        .icon {{ width: 72px; height: 72px; border-radius: 50%; background: {c['accent']}; border: 2px solid {c['border']}; display: flex; align-items: center; justify-content: center; margin: 0 auto 24px; font-size: 32px; color: {c['bg']}; }}
        .body h1 {{ font-size: 24px; color: #111827; margin-bottom: 14px; font-weight: 700; }}
        .body p {{ color: #6b7280; font-size: 15px; line-height: 1.7; }}
        .footer {{ padding: 16px 32px; background: #f9fafb; border-top: 1px solid #f0f0f0; text-align: center; }}
        .footer p {{ color: #b0b7c3; font-size: 11px; }}
    </style>
</head>
<body>
    <div class="card">
        <div class="header">
            <img src="{logo_url}" alt="D&V Business Consulting" />
        </div>
        <div class="body">
            <div class="icon">{c['icon']}</div>
            <h1>{title}</h1>
            <p>{message}</p>
        </div>
        <div class="footer">
            <p>D&amp;V Business Consulting &bull; Powered by NETRA</p>
        </div>
    </div>
</body>
</html>"""


def _build_reschedule_page(client_name: str, current_schedule: str, submit_url: str) -> str:
    """Build a branded HTML page with a date/time picker for client to reschedule."""
    base_url = os.environ.get("REACT_APP_BACKEND_URL", "https://attendance-approvals.preview.emergentagent.com").rstrip("/")
    logo_url = f"{base_url}/api/follow-ups/assets/logo.png"
    
    # Calculate min date (tomorrow)
    from datetime import date
    min_date = (date.today() + timedelta(days=1)).isoformat()
    
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Reschedule — D&V Business Consulting</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #f4f5f7; min-height: 100vh; display: flex; align-items: center; justify-content: center; padding: 20px; }}
        .card {{ background: #fff; border-radius: 12px; box-shadow: 0 4px 24px rgba(0,0,0,0.08); max-width: 520px; width: 100%; overflow: hidden; }}
        .header {{ padding: 28px 32px 20px; text-align: center; border-bottom: 1px solid #f0f0f0; }}
        .header img {{ max-height: 64px; max-width: 240px; width: auto; }}
        .body {{ padding: 32px; }}
        .body h1 {{ font-size: 22px; color: #111827; margin-bottom: 8px; font-weight: 700; text-align: center; }}
        .body .subtitle {{ color: #6b7280; font-size: 14px; text-align: center; margin-bottom: 24px; line-height: 1.6; }}
        .current {{ background: #fffbeb; border: 1px solid #fde68a; border-radius: 8px; padding: 14px 16px; margin-bottom: 24px; }}
        .current p.label {{ font-size: 12px; color: #92400e; font-weight: 600; margin-bottom: 4px; }}
        .current p.value {{ font-size: 14px; color: #b45309; }}
        .form-group {{ margin-bottom: 18px; }}
        .form-group label {{ display: block; font-size: 13px; color: #374151; font-weight: 600; margin-bottom: 6px; }}
        .form-group input, .form-group textarea {{ width: 100%; padding: 10px 14px; border: 1px solid #d1d5db; border-radius: 8px; font-size: 14px; color: #111827; background: #fff; outline: none; transition: border-color 0.2s; }}
        .form-group input:focus, .form-group textarea:focus {{ border-color: #d97706; box-shadow: 0 0 0 3px rgba(217,119,6,0.1); }}
        .form-group textarea {{ resize: vertical; min-height: 70px; font-family: inherit; }}
        .row {{ display: flex; gap: 12px; }}
        .row .form-group {{ flex: 1; }}
        .submit-btn {{ width: 100%; padding: 13px; background: #d97706; color: #fff; border: none; border-radius: 8px; font-size: 15px; font-weight: 600; cursor: pointer; transition: background 0.2s; margin-top: 6px; }}
        .submit-btn:hover {{ background: #b45309; }}
        .submit-btn:disabled {{ background: #d1d5db; cursor: not-allowed; }}
        .footer {{ padding: 16px 32px; background: #f9fafb; border-top: 1px solid #f0f0f0; text-align: center; }}
        .footer p {{ color: #b0b7c3; font-size: 11px; }}
    </style>
</head>
<body>
    <div class="card">
        <div class="header">
            <img src="{logo_url}" alt="D&V Business Consulting" />
        </div>
        <div class="body">
            <h1>Reschedule Follow-up</h1>
            <p class="subtitle">Hi {client_name}, please pick a new date and time that works best for you.</p>
            
            {"<div class='current'><p class='label'>Current Schedule</p><p class='value'>" + current_schedule + "</p></div>" if current_schedule else ""}
            
            <form method="POST" action="{submit_url}" onsubmit="document.getElementById('submitBtn').disabled=true;document.getElementById('submitBtn').textContent='Submitting...';">
                <div class="row">
                    <div class="form-group">
                        <label for="preferred_date">Preferred Date *</label>
                        <input type="date" id="preferred_date" name="preferred_date" min="{min_date}" required />
                    </div>
                    <div class="form-group">
                        <label for="preferred_time">Preferred Time *</label>
                        <input type="time" id="preferred_time" name="preferred_time" required />
                    </div>
                </div>
                <div class="form-group">
                    <label for="message">Message (optional)</label>
                    <textarea id="message" name="message" placeholder="Any additional notes or preferences..."></textarea>
                </div>
                <button type="submit" id="submitBtn" class="submit-btn">Request Reschedule</button>
            </form>
        </div>
        <div class="footer">
            <p>D&amp;V Business Consulting &bull; Powered by NETRA</p>
        </div>
    </div>
</body>
</html>"""
