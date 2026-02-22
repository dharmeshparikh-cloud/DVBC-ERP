"""
Drafts Router - Auto-save and draft management for forms
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import uuid

from .deps import get_db
from .auth import get_current_user
from .models import User

router = APIRouter(prefix="/drafts", tags=["Drafts"])


class DraftCreate(BaseModel):
    draft_type: str  # 'pricing_plan', 'lead', 'sow', etc.
    title: str
    data: Dict[str, Any]
    step: int = 0
    metadata: Dict[str, Any] = {}
    entity_id: Optional[str] = None  # Link to specific entity (e.g., lead_id)


class DraftUpdate(BaseModel):
    draft_type: Optional[str] = None
    title: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    step: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None
    entity_id: Optional[str] = None


class Draft(BaseModel):
    id: str
    draft_type: str
    title: str
    data: Dict[str, Any]
    step: int = 0
    metadata: Dict[str, Any] = {}
    entity_id: Optional[str] = None
    user_id: str
    status: str = "active"  # active, converted, archived
    created_at: datetime
    updated_at: datetime


@router.get("", response_model=List[Draft])
async def get_drafts(
    draft_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get all drafts for current user, optionally filtered by type and entity"""
    db = get_db()
    
    query = {
        "user_id": current_user.id,
        "status": "active"
    }
    
    if draft_type:
        query["draft_type"] = draft_type
    
    if entity_id:
        query["entity_id"] = entity_id
    
    drafts = await db.drafts.find(query, {"_id": 0}).sort("updated_at", -1).to_list(100)
    
    # Convert datetime strings
    for draft in drafts:
        if isinstance(draft.get('created_at'), str):
            draft['created_at'] = datetime.fromisoformat(draft['created_at'].replace('Z', '+00:00'))
        if isinstance(draft.get('updated_at'), str):
            draft['updated_at'] = datetime.fromisoformat(draft['updated_at'].replace('Z', '+00:00'))
    
    return drafts


@router.get("/{draft_id}", response_model=Draft)
async def get_draft(
    draft_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get a specific draft"""
    db = get_db()
    
    draft = await db.drafts.find_one(
        {"id": draft_id, "user_id": current_user.id},
        {"_id": 0}
    )
    
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    
    # Convert datetime strings
    if isinstance(draft.get('created_at'), str):
        draft['created_at'] = datetime.fromisoformat(draft['created_at'].replace('Z', '+00:00'))
    if isinstance(draft.get('updated_at'), str):
        draft['updated_at'] = datetime.fromisoformat(draft['updated_at'].replace('Z', '+00:00'))
    
    return draft


@router.post("")
async def create_draft(
    draft_data: DraftCreate,
    current_user: User = Depends(get_current_user)
):
    """Create a new draft"""
    db = get_db()
    
    draft = {
        "id": str(uuid.uuid4()),
        "draft_type": draft_data.draft_type,
        "title": draft_data.title,
        "data": draft_data.data,
        "step": draft_data.step,
        "metadata": draft_data.metadata,
        "entity_id": draft_data.entity_id,
        "user_id": current_user.id,
        "status": "active",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.drafts.insert_one(draft)
    
    # Fetch the clean version without _id
    saved_draft = await db.drafts.find_one({"id": draft["id"]}, {"_id": 0})
    
    return {"message": "Draft created", "draft": saved_draft}


@router.put("/{draft_id}")
async def update_draft(
    draft_id: str,
    draft_data: DraftUpdate,
    current_user: User = Depends(get_current_user)
):
    """Update an existing draft"""
    db = get_db()
    
    existing = await db.drafts.find_one(
        {"id": draft_id, "user_id": current_user.id},
        {"_id": 0}
    )
    
    if not existing:
        raise HTTPException(status_code=404, detail="Draft not found")
    
    update_fields = draft_data.model_dump(exclude_unset=True)
    update_fields["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.drafts.update_one(
        {"id": draft_id},
        {"$set": update_fields}
    )
    
    updated = await db.drafts.find_one({"id": draft_id}, {"_id": 0})
    
    # Convert datetime strings
    if isinstance(updated.get('created_at'), str):
        updated['created_at'] = datetime.fromisoformat(updated['created_at'].replace('Z', '+00:00'))
    if isinstance(updated.get('updated_at'), str):
        updated['updated_at'] = datetime.fromisoformat(updated['updated_at'].replace('Z', '+00:00'))
    
    return {"message": "Draft updated", "draft": updated}


@router.delete("/{draft_id}")
async def delete_draft(
    draft_id: str,
    current_user: User = Depends(get_current_user)
):
    """Delete a draft"""
    db = get_db()
    
    existing = await db.drafts.find_one(
        {"id": draft_id, "user_id": current_user.id},
        {"_id": 0}
    )
    
    if not existing:
        raise HTTPException(status_code=404, detail="Draft not found")
    
    await db.drafts.delete_one({"id": draft_id})
    
    return {"message": "Draft deleted"}


@router.post("/{draft_id}/convert")
async def convert_draft(
    draft_id: str,
    current_user: User = Depends(get_current_user)
):
    """Mark a draft as converted (when the actual record is created)"""
    db = get_db()
    
    existing = await db.drafts.find_one(
        {"id": draft_id, "user_id": current_user.id},
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
    
    return {"message": "Draft marked as converted"}
