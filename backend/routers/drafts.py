"""
Drafts Router - Universal Auto-Save & Resume System
Provides system-wide draft persistence for all editable pages across ERP modules.

Features:
- Auto-save on field change, tab change, step change, blur, route exit
- Resume flow with modal (Resume/Discard/Cancel)
- Global resume on login ("Continue where you left off?")
- Auto-delete on submission/stage completion/entity closure
- RBAC compliance (employee-scoped, no cross-user visibility)
- Conflict handling with version checks
- Audit logging for all draft actions
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta
import uuid

from .deps import get_db
from .auth import get_current_user
from .models import User

router = APIRouter(prefix="/drafts", tags=["Drafts"])


# ============== Pydantic Models ==============

class DraftCreate(BaseModel):
    """Model for creating/updating a draft"""
    module: str  # sales, hr, consulting, projects, leads, travel, etc.
    draft_type: str = ""  # Backward compatible - 'pricing_plan', 'lead', 'sow', etc.
    title: str = ""
    entity_id: Optional[str] = None  # ID of entity being edited (null for new)
    route: str  # Current route path
    active_tab: Optional[str] = None  # Current active tab/step
    step: int = 0  # Backward compatible
    form_data: Dict[str, Any] = Field(default_factory=dict)  # JSON form data
    data: Dict[str, Any] = Field(default_factory=dict)  # Backward compatible
    metadata: Dict[str, Any] = Field(default_factory=dict)  # Additional context


class DraftUpdate(BaseModel):
    """Model for partial draft updates"""
    draft_type: Optional[str] = None
    title: Optional[str] = None
    active_tab: Optional[str] = None
    step: Optional[int] = None
    form_data: Optional[Dict[str, Any]] = None
    data: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


class Draft(BaseModel):
    """Full draft response model"""
    id: str
    employee_id: str
    module: str
    draft_type: str
    title: str
    entity_id: Optional[str]
    route: str
    active_tab: Optional[str]
    step: int
    form_data: Dict[str, Any]
    data: Dict[str, Any]
    metadata: Dict[str, Any]
    status: str
    version: int
    created_at: str
    updated_at: str
    last_saved_at: str


# ============== Helper Functions ==============

async def log_draft_action(db, action: str, draft_id: str, employee_id: str, details: dict = None):
    """Log draft-related actions for audit"""
    await db.audit_logs.insert_one({
        "id": str(uuid.uuid4()),
        "action": f"draft_{action}",
        "entity_type": "draft",
        "entity_id": draft_id,
        "performed_by": employee_id,
        "performed_at": datetime.now(timezone.utc).isoformat(),
        "details": details or {}
    })


def normalize_draft(draft: dict) -> dict:
    """Normalize draft data for consistent response format"""
    now = datetime.now(timezone.utc).isoformat()
    return {
        "id": draft.get("id"),
        "employee_id": draft.get("employee_id") or draft.get("user_id", ""),
        "module": draft.get("module", draft.get("draft_type", "general")),
        "draft_type": draft.get("draft_type", ""),
        "title": draft.get("title", ""),
        "entity_id": draft.get("entity_id"),
        "route": draft.get("route", "/"),
        "active_tab": draft.get("active_tab"),
        "step": draft.get("step", 0),
        "form_data": draft.get("form_data") or draft.get("data", {}),
        "data": draft.get("data") or draft.get("form_data", {}),
        "metadata": draft.get("metadata", {}),
        "status": draft.get("status", "active"),
        "version": draft.get("version", 1),
        "created_at": draft.get("created_at", now),
        "updated_at": draft.get("updated_at", now),
        "last_saved_at": draft.get("last_saved_at") or draft.get("updated_at", now)
    }


# ============== Core Endpoints ==============

@router.get("")
async def get_drafts(
    module: Optional[str] = None,
    draft_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    status: str = "active",
    limit: int = Query(default=50, le=100),
    current_user: User = Depends(get_current_user)
):
    """
    Get all drafts for current user.
    Strictly employee-scoped - no cross-user visibility.
    """
    db = get_db()
    
    query = {
        "$or": [
            {"employee_id": current_user.id},
            {"user_id": current_user.id}  # Backward compatibility
        ],
        "status": status
    }
    
    if module:
        query["module"] = module
    if draft_type:
        query["draft_type"] = draft_type
    if entity_id:
        query["entity_id"] = entity_id
    
    drafts = await db.drafts.find(query, {"_id": 0}).sort("updated_at", -1).to_list(limit)
    
    return [normalize_draft(d) for d in drafts]


@router.get("/check")
async def check_draft(
    module: str,
    route: str,
    entity_id: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """
    Check if a draft exists for specific module/entity/route.
    Used when opening an editable page to determine if resume modal should show.
    """
    db = get_db()
    
    query = {
        "$or": [
            {"employee_id": current_user.id},
            {"user_id": current_user.id}
        ],
        "module": module,
        "route": route,
        "status": "active"
    }
    
    if entity_id:
        query["entity_id"] = entity_id
    
    draft = await db.drafts.find_one(query, {"_id": 0})
    
    if draft:
        return {
            "has_draft": True,
            "draft": normalize_draft(draft)
        }
    
    return {"has_draft": False, "draft": None}


@router.get("/latest")
async def get_latest_draft(current_user: User = Depends(get_current_user)):
    """
    Get the most recent draft for login resume banner.
    Shows "Continue where you left off?" on login.
    """
    db = get_db()
    
    draft = await db.drafts.find_one(
        {
            "$or": [
                {"employee_id": current_user.id},
                {"user_id": current_user.id}
            ],
            "status": "active"
        },
        {"_id": 0},
        sort=[("updated_at", -1)]
    )
    
    if draft:
        return {
            "has_draft": True,
            "draft": normalize_draft(draft)
        }
    
    return {"has_draft": False, "draft": None}


@router.get("/{draft_id}")
async def get_draft(
    draft_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get a specific draft by ID. Only accessible by the draft owner."""
    db = get_db()
    
    draft = await db.drafts.find_one(
        {
            "id": draft_id,
            "$or": [
                {"employee_id": current_user.id},
                {"user_id": current_user.id}
            ]
        },
        {"_id": 0}
    )
    
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    
    return normalize_draft(draft)


@router.post("")
async def save_draft(
    draft_data: DraftCreate,
    current_user: User = Depends(get_current_user)
):
    """
    Create or update a draft session (upsert).
    - If draft exists for same module/entity_id/route/employee -> update it
    - Otherwise create new draft
    - Prevents duplicate drafts per entity per user
    """
    db = get_db()
    
    # Normalize form_data/data
    form_data = draft_data.form_data or draft_data.data or {}
    
    # Check for existing draft (same module, entity, route, user)
    query = {
        "$or": [
            {"employee_id": current_user.id},
            {"user_id": current_user.id}
        ],
        "module": draft_data.module,
        "route": draft_data.route,
        "status": "active"
    }
    if draft_data.entity_id:
        query["entity_id"] = draft_data.entity_id
    
    existing = await db.drafts.find_one(query, {"_id": 0})
    
    now = datetime.now(timezone.utc).isoformat()
    
    if existing:
        # Update existing draft
        new_version = existing.get("version", 1) + 1
        update_data = {
            "active_tab": draft_data.active_tab,
            "step": draft_data.step,
            "form_data": form_data,
            "data": form_data,  # Backward compatibility
            "metadata": draft_data.metadata,
            "updated_at": now,
            "last_saved_at": now,
            "version": new_version
        }
        
        if draft_data.title:
            update_data["title"] = draft_data.title
        
        await db.drafts.update_one(
            {"id": existing["id"]},
            {"$set": update_data}
        )
        
        await log_draft_action(db, "updated", existing["id"], current_user.id, {
            "module": draft_data.module,
            "version": new_version
        })
        
        updated = await db.drafts.find_one({"id": existing["id"]}, {"_id": 0})
        return {"message": "Draft updated", "draft": normalize_draft(updated), "action": "updated"}
    
    # Create new draft
    draft_id = str(uuid.uuid4())
    draft = {
        "id": draft_id,
        "employee_id": current_user.id,
        "user_id": current_user.id,  # Backward compatibility
        "module": draft_data.module,
        "draft_type": draft_data.draft_type or draft_data.module,
        "title": draft_data.title or f"Draft - {draft_data.module}",
        "entity_id": draft_data.entity_id,
        "route": draft_data.route,
        "active_tab": draft_data.active_tab,
        "step": draft_data.step,
        "form_data": form_data,
        "data": form_data,  # Backward compatibility
        "metadata": draft_data.metadata,
        "status": "active",
        "version": 1,
        "created_at": now,
        "updated_at": now,
        "last_saved_at": now
    }
    
    await db.drafts.insert_one(draft)
    
    await log_draft_action(db, "created", draft_id, current_user.id, {
        "module": draft_data.module,
        "route": draft_data.route
    })
    
    saved = await db.drafts.find_one({"id": draft_id}, {"_id": 0})
    return {"message": "Draft created", "draft": normalize_draft(saved), "action": "created"}


@router.put("/{draft_id}")
async def update_draft(
    draft_id: str,
    draft_data: DraftUpdate,
    current_user: User = Depends(get_current_user)
):
    """Update an existing draft with version tracking."""
    db = get_db()
    
    existing = await db.drafts.find_one(
        {
            "id": draft_id,
            "$or": [
                {"employee_id": current_user.id},
                {"user_id": current_user.id}
            ]
        },
        {"_id": 0}
    )
    
    if not existing:
        raise HTTPException(status_code=404, detail="Draft not found")
    
    update_fields = draft_data.model_dump(exclude_unset=True)
    
    # Sync form_data and data for backward compatibility
    if "form_data" in update_fields:
        update_fields["data"] = update_fields["form_data"]
    elif "data" in update_fields:
        update_fields["form_data"] = update_fields["data"]
    
    now = datetime.now(timezone.utc).isoformat()
    update_fields["updated_at"] = now
    update_fields["last_saved_at"] = now
    update_fields["version"] = existing.get("version", 1) + 1
    
    await db.drafts.update_one(
        {"id": draft_id},
        {"$set": update_fields}
    )
    
    await log_draft_action(db, "updated", draft_id, current_user.id, {
        "version": update_fields["version"]
    })
    
    updated = await db.drafts.find_one({"id": draft_id}, {"_id": 0})
    return {"message": "Draft updated", "draft": normalize_draft(updated)}


@router.delete("/{draft_id}")
async def delete_draft(
    draft_id: str,
    current_user: User = Depends(get_current_user)
):
    """Discard (delete) a draft."""
    db = get_db()
    
    existing = await db.drafts.find_one(
        {
            "id": draft_id,
            "$or": [
                {"employee_id": current_user.id},
                {"user_id": current_user.id}
            ]
        },
        {"_id": 0}
    )
    
    if not existing:
        raise HTTPException(status_code=404, detail="Draft not found")
    
    await db.drafts.delete_one({"id": draft_id})
    
    await log_draft_action(db, "discarded", draft_id, current_user.id, {
        "module": existing.get("module"),
        "route": existing.get("route")
    })
    
    return {"message": "Draft deleted", "status": "success"}


@router.post("/{draft_id}/convert")
async def convert_draft(
    draft_id: str,
    current_user: User = Depends(get_current_user)
):
    """Mark a draft as converted (when the actual record is created)."""
    db = get_db()
    
    existing = await db.drafts.find_one(
        {
            "id": draft_id,
            "$or": [
                {"employee_id": current_user.id},
                {"user_id": current_user.id}
            ]
        },
        {"_id": 0}
    )
    
    if not existing:
        raise HTTPException(status_code=404, detail="Draft not found")
    
    await db.drafts.update_one(
        {"id": draft_id},
        {"$set": {
            "status": "converted",
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    await log_draft_action(db, "auto_deleted", draft_id, current_user.id, {
        "reason": "converted",
        "module": existing.get("module")
    })
    
    return {"message": "Draft marked as converted", "status": "success"}


@router.post("/complete-by-entity")
async def complete_draft_by_entity(
    module: str,
    entity_id: str,
    route: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """
    Complete all drafts for a specific entity.
    Called after entity closure or stage completion.
    """
    db = get_db()
    
    query = {
        "$or": [
            {"employee_id": current_user.id},
            {"user_id": current_user.id}
        ],
        "module": module,
        "entity_id": entity_id,
        "status": "active"
    }
    
    if route:
        query["route"] = route
    
    result = await db.drafts.delete_many(query)
    
    if result.deleted_count > 0:
        await log_draft_action(db, "auto_deleted", f"{module}_{entity_id}", current_user.id, {
            "reason": "entity_completed",
            "count": result.deleted_count
        })
    
    return {
        "status": "success",
        "message": f"Deleted {result.deleted_count} draft(s)",
        "deleted_count": result.deleted_count
    }


@router.get("/version-check/{draft_id}")
async def check_draft_version(
    draft_id: str,
    client_version: int = Query(default=1),
    current_user: User = Depends(get_current_user)
):
    """
    Check if client's draft version matches server version.
    Used for conflict handling when multiple tabs update same draft.
    """
    db = get_db()
    
    draft = await db.drafts.find_one(
        {
            "id": draft_id,
            "$or": [
                {"employee_id": current_user.id},
                {"user_id": current_user.id}
            ]
        },
        {"_id": 0, "version": 1, "last_saved_at": 1, "updated_at": 1}
    )
    
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    
    server_version = draft.get("version", 1)
    
    return {
        "in_sync": client_version >= server_version,
        "server_version": server_version,
        "client_version": client_version,
        "last_saved_at": draft.get("last_saved_at") or draft.get("updated_at"),
        "has_conflict": client_version < server_version
    }


# ============== Admin Endpoints ==============

@router.get("/admin/all")
async def admin_list_all_drafts(
    module: Optional[str] = None,
    limit: int = Query(default=100, le=500),
    current_user: User = Depends(get_current_user)
):
    """Admin-only: List all drafts across all users (with audit logging)."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    db = get_db()
    
    query = {"status": "active"}
    if module:
        query["module"] = module
    
    drafts = await db.drafts.find(query, {"_id": 0}).sort("updated_at", -1).to_list(limit)
    
    await log_draft_action(db, "admin_viewed", "all", current_user.id, {
        "count": len(drafts),
        "module_filter": module
    })
    
    return {
        "total": len(drafts),
        "drafts": [normalize_draft(d) for d in drafts]
    }


@router.delete("/admin/purge")
async def admin_purge_drafts(
    older_than_days: int = Query(default=30, ge=1),
    current_user: User = Depends(get_current_user)
):
    """Admin-only: Purge old drafts (with audit logging)."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    db = get_db()
    
    cutoff = (datetime.now(timezone.utc) - timedelta(days=older_than_days)).isoformat()
    
    result = await db.drafts.delete_many({
        "updated_at": {"$lt": cutoff},
        "status": "active"
    })
    
    await log_draft_action(db, "admin_purged", "bulk", current_user.id, {
        "older_than_days": older_than_days,
        "deleted_count": result.deleted_count
    })
    
    return {
        "status": "success",
        "message": f"Purged {result.deleted_count} old draft(s)",
        "deleted_count": result.deleted_count
    }
