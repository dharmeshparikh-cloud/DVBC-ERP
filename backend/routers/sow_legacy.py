"""
SOW (Scope of Work) Router - Legacy SOW endpoints from server.py
Handles SOW creation, items, versions, documents, and approval workflow.
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Optional, List
from datetime import datetime, timezone
import uuid
from pydantic import BaseModel
from .deps import get_db, HR_ADMIN_ROLES, MANAGER_ROLES
from .models import User
from .auth import get_current_user

router = APIRouter(prefix="/sow", tags=["SOW - Legacy"])


class SOWItemCreate(BaseModel):
    category: str
    description: str
    scope_details: Optional[str] = None
    deliverables: Optional[List[str]] = []
    timeline_days: Optional[int] = None


class BulkSOWItemsRequest(BaseModel):
    items: List[SOWItemCreate]


class DocumentUpload(BaseModel):
    name: str
    file_url: str
    file_type: Optional[str] = None
    description: Optional[str] = None


class SOWChangeRequestCreate(BaseModel):
    sow_id: str
    change_type: str  # 'scope_change', 'timeline_change', 'deliverable_change'
    description: str
    impact_assessment: Optional[str] = None
    requested_items: Optional[List[dict]] = []


@router.get("/categories")
async def get_sow_categories(current_user: User = Depends(get_current_user)):
    """Get available SOW categories"""
    return ["discovery", "implementation", "training", "support", "custom"]


@router.post("")
async def create_sow(data: dict, current_user: User = Depends(get_current_user)):
    """Create a new SOW"""
    db = get_db()
    
    sow_id = str(uuid.uuid4())
    pricing_plan_id = data.get("pricing_plan_id")
    
    if not pricing_plan_id:
        raise HTTPException(status_code=400, detail="pricing_plan_id is required")
    
    pricing_plan = await db.pricing_plans.find_one({"id": pricing_plan_id}, {"_id": 0})
    if not pricing_plan:
        raise HTTPException(status_code=404, detail="Pricing plan not found")
    
    sow_doc = {
        "id": sow_id,
        "pricing_plan_id": pricing_plan_id,
        "lead_id": pricing_plan.get("lead_id"),
        "client_name": data.get("client_name", pricing_plan.get("client_name", "")),
        "status": "draft",
        "version": 1,
        "items": [],
        "total_days": 0,
        "created_by": current_user.id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.sow.insert_one(sow_doc)
    sow_doc.pop("_id", None)
    return sow_doc


@router.get("/{sow_id}")
async def get_sow(sow_id: str, current_user: User = Depends(get_current_user)):
    """Get SOW by ID"""
    db = get_db()
    sow = await db.sow.find_one({"id": sow_id}, {"_id": 0})
    if not sow:
        raise HTTPException(status_code=404, detail="SOW not found")
    return sow


@router.get("/by-pricing-plan/{pricing_plan_id}")
async def get_sow_by_pricing_plan(pricing_plan_id: str, current_user: User = Depends(get_current_user)):
    """Get SOW by pricing plan ID"""
    db = get_db()
    sow = await db.sow.find_one({"pricing_plan_id": pricing_plan_id}, {"_id": 0})
    if not sow:
        raise HTTPException(status_code=404, detail="SOW not found for this pricing plan")
    return sow


@router.post("/{sow_id}/items")
async def add_sow_item(sow_id: str, item: SOWItemCreate, current_user: User = Depends(get_current_user)):
    """Add an item to SOW"""
    db = get_db()
    
    sow = await db.sow.find_one({"id": sow_id}, {"_id": 0})
    if not sow:
        raise HTTPException(status_code=404, detail="SOW not found")
    
    if sow.get("status") not in ["draft", "revision"]:
        raise HTTPException(status_code=400, detail="Cannot modify SOW in current status")
    
    item_id = str(uuid.uuid4())
    item_doc = {
        "id": item_id,
        "category": item.category,
        "description": item.description,
        "scope_details": item.scope_details,
        "deliverables": item.deliverables or [],
        "timeline_days": item.timeline_days or 0,
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.sow.update_one(
        {"id": sow_id},
        {
            "$push": {"items": item_doc},
            "$inc": {"total_days": item.timeline_days or 0},
            "$set": {"updated_at": datetime.now(timezone.utc).isoformat()}
        }
    )
    
    return {"message": "Item added", "item_id": item_id, "item": item_doc}


@router.post("/{sow_id}/items/bulk")
async def add_bulk_sow_items(sow_id: str, request: BulkSOWItemsRequest, current_user: User = Depends(get_current_user)):
    """Add multiple items to SOW"""
    db = get_db()
    
    sow = await db.sow.find_one({"id": sow_id}, {"_id": 0})
    if not sow:
        raise HTTPException(status_code=404, detail="SOW not found")
    
    if sow.get("status") not in ["draft", "revision"]:
        raise HTTPException(status_code=400, detail="Cannot modify SOW in current status")
    
    items_to_add = []
    total_days = 0
    
    for item in request.items:
        item_id = str(uuid.uuid4())
        item_doc = {
            "id": item_id,
            "category": item.category,
            "description": item.description,
            "scope_details": item.scope_details,
            "deliverables": item.deliverables or [],
            "timeline_days": item.timeline_days or 0,
            "status": "pending",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        items_to_add.append(item_doc)
        total_days += item.timeline_days or 0
    
    await db.sow.update_one(
        {"id": sow_id},
        {
            "$push": {"items": {"$each": items_to_add}},
            "$inc": {"total_days": total_days},
            "$set": {"updated_at": datetime.now(timezone.utc).isoformat()}
        }
    )
    
    return {"message": f"Added {len(items_to_add)} items", "items": items_to_add}


@router.delete("/{sow_id}/items/{item_id}")
async def delete_sow_item(sow_id: str, item_id: str, current_user: User = Depends(get_current_user)):
    """Delete an item from SOW"""
    db = get_db()
    
    sow = await db.sow.find_one({"id": sow_id}, {"_id": 0})
    if not sow:
        raise HTTPException(status_code=404, detail="SOW not found")
    
    if sow.get("status") not in ["draft", "revision"]:
        raise HTTPException(status_code=400, detail="Cannot modify SOW in current status")
    
    item_to_remove = next((i for i in sow.get("items", []) if i["id"] == item_id), None)
    if not item_to_remove:
        raise HTTPException(status_code=404, detail="Item not found")
    
    await db.sow.update_one(
        {"id": sow_id},
        {
            "$pull": {"items": {"id": item_id}},
            "$inc": {"total_days": -(item_to_remove.get("timeline_days", 0))},
            "$set": {"updated_at": datetime.now(timezone.utc).isoformat()}
        }
    )
    
    return {"message": "Item deleted"}


@router.patch("/{sow_id}/items/{item_id}")
async def update_sow_item(sow_id: str, item_id: str, data: dict, current_user: User = Depends(get_current_user)):
    """Update an item in SOW"""
    db = get_db()
    
    sow = await db.sow.find_one({"id": sow_id}, {"_id": 0})
    if not sow:
        raise HTTPException(status_code=404, detail="SOW not found")
    
    if sow.get("status") not in ["draft", "revision"]:
        raise HTTPException(status_code=400, detail="Cannot modify SOW in current status")
    
    items = sow.get("items", [])
    item_idx = next((i for i, item in enumerate(items) if item["id"] == item_id), None)
    if item_idx is None:
        raise HTTPException(status_code=404, detail="Item not found")
    
    old_days = items[item_idx].get("timeline_days", 0)
    new_days = data.get("timeline_days", old_days)
    days_diff = new_days - old_days
    
    update_fields = {}
    for key in ["category", "description", "scope_details", "deliverables", "timeline_days", "status"]:
        if key in data:
            update_fields[f"items.{item_idx}.{key}"] = data[key]
    
    update_fields["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.sow.update_one(
        {"id": sow_id},
        {
            "$set": update_fields,
            "$inc": {"total_days": days_diff}
        }
    )
    
    return {"message": "Item updated"}


@router.get("/{sow_id}/versions")
async def get_sow_versions(sow_id: str, current_user: User = Depends(get_current_user)):
    """Get all versions of a SOW"""
    db = get_db()
    
    versions = await db.sow_versions.find(
        {"sow_id": sow_id},
        {"_id": 0}
    ).sort("version", -1).to_list(50)
    
    return versions


@router.get("/{sow_id}/version/{version_num}")
async def get_sow_version(sow_id: str, version_num: int, current_user: User = Depends(get_current_user)):
    """Get a specific version of SOW"""
    db = get_db()
    
    version = await db.sow_versions.find_one(
        {"sow_id": sow_id, "version": version_num},
        {"_id": 0}
    )
    
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")
    
    return version


@router.patch("/{sow_id}/items/{item_id}/status")
async def update_sow_item_status(sow_id: str, item_id: str, data: dict, current_user: User = Depends(get_current_user)):
    """Update item status"""
    db = get_db()
    
    new_status = data.get("status")
    if not new_status:
        raise HTTPException(status_code=400, detail="status is required")
    
    valid_statuses = ["pending", "in_progress", "completed", "approved", "rejected"]
    if new_status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}")
    
    sow = await db.sow.find_one({"id": sow_id}, {"_id": 0})
    if not sow:
        raise HTTPException(status_code=404, detail="SOW not found")
    
    items = sow.get("items", [])
    item_idx = next((i for i, item in enumerate(items) if item["id"] == item_id), None)
    if item_idx is None:
        raise HTTPException(status_code=404, detail="Item not found")
    
    await db.sow.update_one(
        {"id": sow_id},
        {
            "$set": {
                f"items.{item_idx}.status": new_status,
                f"items.{item_idx}.status_updated_at": datetime.now(timezone.utc).isoformat(),
                f"items.{item_idx}.status_updated_by": current_user.id,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    return {"message": "Status updated", "new_status": new_status}


@router.post("/{sow_id}/submit-for-approval")
async def submit_sow_for_approval(sow_id: str, current_user: User = Depends(get_current_user)):
    """Submit SOW for approval"""
    db = get_db()
    
    sow = await db.sow.find_one({"id": sow_id}, {"_id": 0})
    if not sow:
        raise HTTPException(status_code=404, detail="SOW not found")
    
    if sow.get("status") not in ["draft", "revision"]:
        raise HTTPException(status_code=400, detail="SOW cannot be submitted in current status")
    
    if not sow.get("items"):
        raise HTTPException(status_code=400, detail="SOW must have at least one item")
    
    await db.sow.update_one(
        {"id": sow_id},
        {
            "$set": {
                "status": "pending_approval",
                "submitted_by": current_user.id,
                "submitted_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    return {"message": "SOW submitted for approval", "status": "pending_approval"}


@router.post("/{sow_id}/approve-all")
async def approve_sow(sow_id: str, current_user: User = Depends(get_current_user)):
    """Approve entire SOW (manager only)"""
    db = get_db()
    
    if current_user.role not in MANAGER_ROLES:
        raise HTTPException(status_code=403, detail="Only managers can approve SOW")
    
    sow = await db.sow.find_one({"id": sow_id}, {"_id": 0})
    if not sow:
        raise HTTPException(status_code=404, detail="SOW not found")
    
    if sow.get("status") != "pending_approval":
        raise HTTPException(status_code=400, detail="SOW is not pending approval")
    
    items = sow.get("items", [])
    for i, item in enumerate(items):
        items[i]["status"] = "approved"
        items[i]["approved_by"] = current_user.id
        items[i]["approved_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.sow.update_one(
        {"id": sow_id},
        {
            "$set": {
                "status": "approved",
                "items": items,
                "approved_by": current_user.id,
                "approved_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    return {"message": "SOW approved", "status": "approved"}


@router.post("/{sow_id}/documents")
async def add_sow_document(sow_id: str, doc: DocumentUpload, current_user: User = Depends(get_current_user)):
    """Add a document to SOW"""
    db = get_db()
    
    sow = await db.sow.find_one({"id": sow_id}, {"_id": 0})
    if not sow:
        raise HTTPException(status_code=404, detail="SOW not found")
    
    doc_id = str(uuid.uuid4())
    doc_record = {
        "id": doc_id,
        "name": doc.name,
        "file_url": doc.file_url,
        "file_type": doc.file_type,
        "description": doc.description,
        "uploaded_by": current_user.id,
        "uploaded_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.sow.update_one(
        {"id": sow_id},
        {
            "$push": {"documents": doc_record},
            "$set": {"updated_at": datetime.now(timezone.utc).isoformat()}
        }
    )
    
    return {"message": "Document added", "document_id": doc_id}


@router.get("/pending-approval")
async def get_pending_sows(current_user: User = Depends(get_current_user)):
    """Get all SOWs pending approval"""
    db = get_db()
    
    if current_user.role not in MANAGER_ROLES:
        raise HTTPException(status_code=403, detail="Only managers can view pending SOWs")
    
    sows = await db.sow.find(
        {"status": "pending_approval"},
        {"_id": 0}
    ).sort("submitted_at", -1).to_list(100)
    
    return sows


@router.get("/{sow_id}/progress")
async def get_sow_progress(sow_id: str, current_user: User = Depends(get_current_user)):
    """Get SOW progress summary"""
    db = get_db()
    
    sow = await db.sow.find_one({"id": sow_id}, {"_id": 0})
    if not sow:
        raise HTTPException(status_code=404, detail="SOW not found")
    
    items = sow.get("items", [])
    total = len(items)
    completed = len([i for i in items if i.get("status") == "completed"])
    approved = len([i for i in items if i.get("status") == "approved"])
    in_progress = len([i for i in items if i.get("status") == "in_progress"])
    pending = len([i for i in items if i.get("status") == "pending"])
    
    progress_pct = round((completed + approved) / total * 100, 1) if total > 0 else 0
    
    return {
        "sow_id": sow_id,
        "status": sow.get("status"),
        "total_items": total,
        "completed": completed,
        "approved": approved,
        "in_progress": in_progress,
        "pending": pending,
        "progress_percentage": progress_pct,
        "total_days": sow.get("total_days", 0)
    }
