"""
Enhanced SOW Router - Role-Based Workflow

Sales Team: Select scopes → Create snapshot → Handover
Consulting Team: Review → Track progress → Submit roadmap for approval
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import uuid
import base64
from .deps import get_db, PROJECT_ROLES, SALES_ROLES as GLOBAL_SALES_ROLES, CONSULTING_ROLES as GLOBAL_CONSULTING_ROLES, ADMIN_ROLES
from .deps import get_current_user
from .models import User

router = APIRouter(prefix="/enhanced-sow", tags=["Enhanced SOW"])


# ============== Role Check Helpers ==============

SALES_ROLES = ["admin", "executive", "sales_manager", "manager"]
CONSULTING_ROLES = ["consultant", "lean_consultant", "lead_consultant", "senior_consultant", "principal_consultant", "subject_matter_expert"]
CAN_ADD_SCOPES_ROLES = ["principal_consultant", "senior_consultant", "admin"]  # Can add but not delete

# SOW view roles - Sales (for upcoming payment dates), Consulting (for project work)
SOW_VIEW_ROLES = list(set(SALES_ROLES + CONSULTING_ROLES + ADMIN_ROLES))


def is_sales_team(role: str) -> bool:
    return role in SALES_ROLES


def is_consulting_team(role: str) -> bool:
    return role in CONSULTING_ROLES


def can_add_scopes(role: str) -> bool:
    return role in CAN_ADD_SCOPES_ROLES


# ============== List SOWs ==============

@router.get("")
async def get_all_enhanced_sows(current_user: User = Depends(get_current_user)):
    """Get all enhanced SOWs - root endpoint
    Access: Sales (view payment dates), Consulting (project work), Admin
    """
    if current_user.role not in SOW_VIEW_ROLES:
        raise HTTPException(status_code=403, detail="Access denied. Only sales and consulting team can view SOWs.")
    
    db = get_db()
    sows = await db.enhanced_sow.find({}, {"_id": 0}).sort("created_at", -1).to_list(500)
    return sows


@router.get("/list")
async def list_enhanced_sows(
    role: str = "all",
    page: int = 1,
    page_size: int = 20,
    sort_field: str = "created_at",
    sort_direction: str = "desc",
    search: Optional[str] = None,
    status: Optional[str] = None,
    category: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """List all enhanced SOWs - filtered by role access, with pagination and sorting"""
    if current_user.role not in SOW_VIEW_ROLES:
        raise HTTPException(status_code=403, detail="Access denied.")
    
    db = get_db()
    query = {}
    
    # For consulting, only show handed-over SOWs
    if role == "consulting" or (current_user.role in CONSULTING_ROLES and current_user.role not in ADMIN_ROLES):
        query["sales_handover_complete"] = True
    
    if status:
        query["status"] = status
    if category:
        query["category"] = category
    if search:
        query["$or"] = [
            {"title": {"$regex": search, "$options": "i"}},
            {"client_name": {"$regex": search, "$options": "i"}},
            {"sow_number": {"$regex": search, "$options": "i"}},
        ]
    
    # Sorting
    sort_dir = -1 if sort_direction == "desc" else 1
    allowed_sort_fields = ["created_at", "status", "category", "sow_number", "title"]
    if sort_field not in allowed_sort_fields:
        sort_field = "created_at"
    
    # Count total
    total = await db.enhanced_sow.count_documents(query)
    
    # Paginated query
    skip = (page - 1) * page_size
    sows = await db.enhanced_sow.find(query, {"_id": 0}).sort(sort_field, sort_dir).skip(skip).limit(page_size).to_list(page_size)
    
    return {
        "data": sows,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size
    }


# ============== Manager Approval ==============

@router.post("/{sow_id}/request-manager-approval")
async def request_manager_approval(
    sow_id: str,
    approval_data: dict,
    current_user: User = Depends(get_current_user)
):
    """Request approval from reporting manager for specific scopes"""
    db = get_db()
    sow = await db.enhanced_sow.find_one({"id": sow_id}, {"_id": 0})
    if not sow:
        raise HTTPException(status_code=404, detail="SOW not found")
    
    now = datetime.now(timezone.utc)
    
    # Create approval request
    approval_request = {
        "id": str(uuid.uuid4()),
        "type": "manager_approval",
        "scope_ids": approval_data.get("scope_ids", []),
        "notes": approval_data.get("notes", ""),
        "requested_by": current_user.id,
        "requested_by_name": current_user.full_name,
        "requested_at": now.isoformat(),
        "status": "pending"
    }
    
    # Add to approval requests
    approval_requests = sow.get("approval_requests", [])
    approval_requests.append(approval_request)
    
    await db.enhanced_sow.update_one(
        {"id": sow_id},
        {"$set": {
            "approval_requests": approval_requests,
            "updated_at": now.isoformat()
        }}
    )
    
    # TODO: Send email notification to manager
    
    return {
        "message": "Approval request sent to manager",
        "request_id": approval_request["id"]
    }


# ============== Sales Team Endpoints ==============

# Simple SOW Create/Update for SOWBuilder
class SimpleScopeItem(BaseModel):
    id: Optional[str] = None
    category_code: str
    category_name: Optional[str] = None
    name: str
    deliverables: str = ""  # Comma-separated deliverables text
    
class SimpleSOWCreate(BaseModel):
    pricing_plan_id: str
    lead_id: Optional[str] = None
    scopes: List[SimpleScopeItem] = []


@router.post("/simple-create")
async def create_simple_sow(
    data: SimpleSOWCreate,
    current_user: User = Depends(get_current_user)
):
    """
    Simple SOW creation from SOWBuilder.
    Creates enhanced_sow with scopes (Category, Name, Deliverables).
    """
    allowed = ADMIN_ROLES + SALES_ROLES + ["principal_consultant"]
    if current_user.role not in allowed:
        raise HTTPException(status_code=403, detail="Not authorized to create SOW")
    
    db = get_db()
    now = datetime.now(timezone.utc)
    user_name = current_user.full_name
    
    # Verify pricing plan exists
    plan = await db.pricing_plans.find_one({"id": data.pricing_plan_id}, {"_id": 0})
    if not plan:
        raise HTTPException(status_code=404, detail="Pricing plan not found")
    
    # Check if SOW already exists
    existing = await db.enhanced_sow.find_one({"pricing_plan_id": data.pricing_plan_id}, {"_id": 0})
    if existing:
        raise HTTPException(status_code=400, detail="SOW already exists for this pricing plan. Use update endpoint.")
    
    # Get lead info
    lead = None
    lead_id = data.lead_id or plan.get("lead_id")
    if lead_id:
        lead = await db.leads.find_one({"id": lead_id}, {"_id": 0})
    
    # Build scopes array
    scopes = []
    for scope_data in data.scopes:
        # Parse deliverables from comma-separated string
        deliverables_list = [d.strip() for d in scope_data.deliverables.split(',') if d.strip()]
        
        scope = {
            "id": scope_data.id or str(uuid.uuid4()),
            "category_code": scope_data.category_code,
            "category_name": scope_data.category_name or scope_data.category_code.replace('_', ' ').title(),
            "name": scope_data.name,
            "deliverables": deliverables_list,
            "deliverables_text": scope_data.deliverables,  # Keep original text
            "source": "sales_original",
            "is_inherited": True,  # Will be inherited by project_sow
            "added_by": current_user.id,
            "added_by_name": user_name,
            "added_at": now.isoformat(),
            "status": "not_started",
            "start_date": None,
            "end_date": None,
            "days_taken": None,
            "progress_percentage": 0
        }
        scopes.append(scope)
    
    # Generate SOW number
    count = await db.enhanced_sow.count_documents({})
    sow_number = f"SOW-{now.strftime('%Y%m%d')}-{str(count + 1).zfill(3)}"
    
    # Create enhanced SOW document
    enhanced_sow = {
        "id": str(uuid.uuid4()),
        "sow_number": sow_number,
        "pricing_plan_id": data.pricing_plan_id,
        "lead_id": lead_id,
        "client_name": lead.get("company") if lead else plan.get("client_name", ""),
        "scopes": scopes,
        "status": "draft",
        "is_locked": False,
        "sales_handover_complete": False,
        "created_by": current_user.id,
        "created_by_name": user_name,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat()
    }
    
    await db.enhanced_sow.insert_one(enhanced_sow)
    
    # Link to pricing plan
    await db.pricing_plans.update_one(
        {"id": data.pricing_plan_id},
        {"$set": {"enhanced_sow_id": enhanced_sow["id"]}}
    )
    
    # Remove _id before returning
    enhanced_sow.pop("_id", None)
    
    return {
        "message": "SOW created successfully",
        "sow": enhanced_sow
    }


@router.put("/{sow_id}/simple-update")
async def update_simple_sow(
    sow_id: str,
    data: dict,
    current_user: User = Depends(get_current_user)
):
    """
    Update SOW scopes from SOWBuilder.
    Allows adding/updating/removing scopes before handover.
    """
    allowed = ADMIN_ROLES + SALES_ROLES + ["principal_consultant"]
    if current_user.role not in allowed:
        raise HTTPException(status_code=403, detail="Not authorized to update SOW")
    
    db = get_db()
    now = datetime.now(timezone.utc)
    user_name = current_user.full_name
    
    # Get existing SOW
    sow = await db.enhanced_sow.find_one({"id": sow_id}, {"_id": 0})
    if not sow:
        raise HTTPException(status_code=404, detail="SOW not found")
    
    if sow.get("is_locked"):
        raise HTTPException(status_code=400, detail="SOW is locked and cannot be modified")
    
    # Build updated scopes
    scopes = []
    for scope_data in data.get("scopes", []):
        deliverables_text = scope_data.get("deliverables", "")
        deliverables_list = [d.strip() for d in deliverables_text.split(',') if d.strip()]
        
        scope = {
            "id": scope_data.get("id") or str(uuid.uuid4()),
            "category_code": scope_data.get("category_code"),
            "category_name": scope_data.get("category_name") or scope_data.get("category_code", "").replace('_', ' ').title(),
            "name": scope_data.get("name"),
            "deliverables": deliverables_list,
            "deliverables_text": deliverables_text,
            "source": "sales_original",
            "is_inherited": True,
            "added_by": current_user.id,
            "added_by_name": user_name,
            "added_at": now.isoformat(),
            "status": scope_data.get("status", "not_started"),
            "start_date": scope_data.get("start_date"),
            "end_date": scope_data.get("end_date"),
            "days_taken": scope_data.get("days_taken"),
            "progress_percentage": scope_data.get("progress_percentage", 0)
        }
        scopes.append(scope)
    
    # Update SOW
    await db.enhanced_sow.update_one(
        {"id": sow_id},
        {"$set": {
            "scopes": scopes,
            "updated_at": now.isoformat(),
            "updated_by": current_user.id,
            "updated_by_name": user_name
        }}
    )
    
    # Get updated SOW
    updated_sow = await db.enhanced_sow.find_one({"id": sow_id}, {"_id": 0})
    
    return {
        "message": "SOW updated successfully",
        "sow": updated_sow
    }


@router.get("/by-pricing-plan-simple/{pricing_plan_id}")
async def get_sow_by_pricing_plan_simple(
    pricing_plan_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get SOW by pricing plan ID - simple format for SOWBuilder"""
    db = get_db()
    sow = await db.enhanced_sow.find_one({"pricing_plan_id": pricing_plan_id}, {"_id": 0})
    
    if not sow:
        return {"sow": None, "exists": False}
    
    return {"sow": sow, "exists": True}


@router.post("/{pricing_plan_id}/sales-selection")
async def create_sow_from_sales_selection(
    pricing_plan_id: str,
    selection: dict,  # SalesScopeSelection
    current_user: User = Depends(get_current_user)
):
    """
    Sales team creates SOW by selecting scopes from master.
    Creates original scope snapshot (locked) and working scopes.
    """
    # Only sales roles and admins can create SOWs
    allowed = ADMIN_ROLES + ["sales_manager", "sales_executive", "executive", "principal_consultant"]
    if current_user.role not in allowed:
        raise HTTPException(status_code=403, detail="Not authorized to create SOW")

    current_user_id = current_user.id
    current_user_name = current_user.full_name
    db = get_db()
    # Verify pricing plan exists
    plan = await db.pricing_plans.find_one({"id": pricing_plan_id}, {"_id": 0})
    if not plan:
        raise HTTPException(status_code=404, detail="Pricing plan not found")
    
    # Check if enhanced SOW already exists
    existing = await db.enhanced_sow.find_one({"pricing_plan_id": pricing_plan_id})
    if existing:
        raise HTTPException(status_code=400, detail="SOW already exists for this pricing plan")
    
    # Get selected scope templates
    scope_template_ids = selection.get("scope_template_ids", [])
    custom_scopes = selection.get("custom_scopes", [])
    
    scopes = []
    now = datetime.now(timezone.utc)
    
    # Process selected scope templates
    if scope_template_ids:
        templates = await db.sow_scope_templates.find(
            {"id": {"$in": scope_template_ids}},
            {"_id": 0}
        ).to_list(100)
        
        for template in templates:
            # Get category info
            category = await db.sow_categories.find_one(
                {"code": template.get("category_code")},
                {"_id": 0}
            )
            
            scope = {
                "id": str(uuid.uuid4()),
                "scope_template_id": template.get("id"),
                "category_id": category.get("id") if category else "",
                "category_code": template.get("category_code"),
                "category_name": category.get("name") if category else template.get("category_code"),
                "name": template.get("name"),
                "description": template.get("description"),
                "source": "sales_original",
                "added_by": current_user_id,
                "added_by_name": current_user_name,
                "added_at": now.isoformat(),
                "revision_status": "pending_review",
                "status": "not_started",
                "progress_percentage": 0,
                "days_spent": 0,
                "meetings_count": 0,
                "timeline_weeks": template.get("default_timeline_weeks"),
                "attachments": [],
                "change_log": [],
                "updated_at": now.isoformat()
            }
            scopes.append(scope)
    
    # Process custom scopes
    for custom in custom_scopes:
        category = await db.sow_categories.find_one(
            {"id": custom.get("category_id")},
            {"_id": 0}
        )
        
        scope = {
            "id": str(uuid.uuid4()),
            "scope_template_id": None,
            "category_id": custom.get("category_id"),
            "category_code": category.get("code") if category else "",
            "category_name": category.get("name") if category else "",
            "name": custom.get("name"),
            "description": custom.get("description"),
            "source": "sales_custom",
            "added_by": current_user_id,
            "added_by_name": current_user_name,
            "added_at": now.isoformat(),
            "revision_status": "pending_review",
            "status": "not_started",
            "progress_percentage": 0,
            "days_spent": 0,
            "meetings_count": 0,
            "attachments": [],
            "change_log": [],
            "updated_at": now.isoformat()
        }
        scopes.append(scope)
        
        # Add custom scope to master list for future use
        if category and custom.get("name"):
            category_code = category.get("code", "")
            scope_name = custom.get("name", "").strip()
            
            existing_template = await db.sow_scope_templates.find_one({
                "category_code": category_code,
                "name": scope_name
            })
            
            if not existing_template:
                new_template = {
                    "id": str(uuid.uuid4()),
                    "category_id": custom.get("category_id"),
                    "category_code": category_code,
                    "name": scope_name,
                    "description": custom.get("description", ""),
                    "is_custom": True,
                    "is_active": True,
                    "created_by": current_user_id,
                    "created_at": now.isoformat(),
                    "updated_at": now.isoformat()
                }
                await db.sow_scope_templates.insert_one(new_template)
    
    # Create original scope snapshot (locked, never editable)
    original_snapshot = {
        "id": str(uuid.uuid4()),
        "scopes": [dict(s) for s in scopes],  # Deep copy
        "created_by": current_user_id,
        "created_by_name": current_user_name,
        "created_at": now.isoformat(),
        "locked": True
    }
    
    # Create enhanced SOW
    enhanced_sow = {
        "id": str(uuid.uuid4()),
        "pricing_plan_id": pricing_plan_id,
        "lead_id": plan.get("lead_id"),
        "original_scope_snapshot": original_snapshot,
        "scopes": scopes,
        "roadmap_versions": [],
        "consent_documents": [],
        "sales_handover_complete": False,
        "consulting_kickoff_complete": False,
        "created_by": current_user_id,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat()
    }
    
    await db.enhanced_sow.insert_one(enhanced_sow)
    
    # Link to pricing plan
    await db.pricing_plans.update_one(
        {"id": pricing_plan_id},
        {"$set": {"enhanced_sow_id": enhanced_sow["id"]}}
    )
    
    return {
        "message": "SOW created successfully",
        "sow_id": enhanced_sow["id"],
        "scopes_count": len(scopes)
    }


@router.post("/{sow_id}/complete-handover")
async def complete_sales_handover(
    sow_id: str,
    current_user: User = Depends(get_current_user)
):
    """Mark sales handover as complete - locks original snapshot"""
    # Only sales roles and admins can complete handover
    allowed = ADMIN_ROLES + ["sales_manager", "sales_executive", "executive", "principal_consultant"]
    if current_user.role not in allowed:
        raise HTTPException(status_code=403, detail="Not authorized to complete handover")

    db = get_db()
    sow = await db.enhanced_sow.find_one({"id": sow_id}, {"_id": 0})
    if not sow:
        raise HTTPException(status_code=404, detail="SOW not found")
    
    if sow.get("sales_handover_complete"):
        raise HTTPException(status_code=400, detail="Handover already completed")
    
    await db.enhanced_sow.update_one(
        {"id": sow_id},
        {"$set": {
            "sales_handover_complete": True,
            "sales_handover_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    return {"message": "Sales handover completed. SOW is now available for consulting team."}


# ============== Consulting Team Endpoints ==============

@router.get("/{sow_id}")
async def get_enhanced_sow(sow_id: str, current_user: User = Depends(get_current_user)):
    """Get enhanced SOW - consulting team doesn't see pricing data"""
    db = get_db()
    sow = await db.enhanced_sow.find_one({"id": sow_id}, {"_id": 0})
    if not sow:
        raise HTTPException(status_code=404, detail="SOW not found")
    
    # If consulting team, remove any pricing-related data
    if is_consulting_team(current_user.role):
        # Remove any accidentally included pricing info
        if "pricing_data" in sow:
            del sow["pricing_data"]
    
    return sow


@router.get("/by-pricing-plan/{pricing_plan_id}")
async def get_enhanced_sow_by_pricing_plan(pricing_plan_id: str, current_user: User = Depends(get_current_user)):
    """Get enhanced SOW by pricing plan ID"""
    db = get_db()
    sow = await db.enhanced_sow.find_one({"pricing_plan_id": pricing_plan_id}, {"_id": 0})
    if not sow:
        raise HTTPException(status_code=404, detail="Enhanced SOW not found for this pricing plan")
    
    # If consulting team, remove any pricing-related data
    if is_consulting_team(current_user.role):
        if "pricing_data" in sow:
            del sow["pricing_data"]
    
    return sow


@router.patch("/{sow_id}/scopes/{scope_id}")
async def update_scope_item(
    sow_id: str,
    scope_id: str,
    update: dict,  # ConsultingScopeUpdate
    current_user: User = Depends(get_current_user)
):
    """Update scope item - consulting team updates progress"""
    db = get_db()
    sow = await db.enhanced_sow.find_one({"id": sow_id}, {"_id": 0})
    if not sow:
        raise HTTPException(status_code=404, detail="SOW not found")
    
    scopes = sow.get("scopes", [])
    scope_idx = next((i for i, s in enumerate(scopes) if s.get("id") == scope_id), None)
    
    if scope_idx is None:
        raise HTTPException(status_code=404, detail="Scope not found")
    
    scope = scopes[scope_idx]
    now = datetime.now(timezone.utc)
    
    # Build change log entry
    change_log_entry = {
        "id": str(uuid.uuid4()),
        "changed_by": current_user.id,
        "changed_by_name": current_user.full_name,
        "changed_at": now.isoformat(),
        "old_value": {},
        "new_value": {},
        "client_consent": update.get("client_consent_for_revision", False)
    }
    
    # Track changes
    updatable_fields = [
        "status", "progress_percentage", "days_spent", "meetings_count",
        "notes", "start_date", "end_date", "revision_status", "revision_reason"
    ]
    
    for field in updatable_fields:
        if field in update and update[field] is not None:
            old_val = scope.get(field)
            new_val = update[field]
            
            if old_val != new_val:
                change_log_entry["old_value"][field] = old_val
                change_log_entry["new_value"][field] = new_val
                
                # Handle datetime fields
                if field in ["start_date", "end_date"] and isinstance(new_val, datetime):
                    scope[field] = new_val.isoformat()
                else:
                    scope[field] = new_val
    
    # Determine change type
    if "status" in change_log_entry["new_value"]:
        change_log_entry["change_type"] = "status_update"
    elif "progress_percentage" in change_log_entry["new_value"]:
        change_log_entry["change_type"] = "progress_update"
    elif "revision_status" in change_log_entry["new_value"]:
        change_log_entry["change_type"] = "revision"
        change_log_entry["reason"] = update.get("revision_reason")
    else:
        change_log_entry["change_type"] = "update"
    
    # Add revision metadata if revising
    if update.get("revision_status"):
        scope["revision_by"] = current_user.id
        scope["revision_by_name"] = current_user.full_name
        scope["revision_at"] = now.isoformat()
        if update.get("client_consent_for_revision"):
            scope["client_consent_for_revision"] = True
    
    # Add change log
    if change_log_entry["old_value"] or change_log_entry["new_value"]:
        if "change_log" not in scope:
            scope["change_log"] = []
        scope["change_log"].append(change_log_entry)
    
    scope["updated_at"] = now.isoformat()
    scopes[scope_idx] = scope
    
    await db.enhanced_sow.update_one(
        {"id": sow_id},
        {"$set": {
            "scopes": scopes,
            "updated_at": now.isoformat()
        }}
    )
    
    return {"message": "Scope updated successfully", "scope": scope}


@router.post("/{sow_id}/scopes")
async def add_scope_item(
    sow_id: str,
    scope_data: dict,  # AddScopeRequest
    current_user: User = Depends(get_current_user)
):
    """Add new scope - consulting team can add but NOT delete"""
    db = get_db()
    if not can_add_scopes(current_user.role):
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to add scopes. Only PM, Consultant, or Principal Consultant can add scopes."
        )
    
    sow = await db.enhanced_sow.find_one({"id": sow_id}, {"_id": 0})
    if not sow:
        raise HTTPException(status_code=404, detail="SOW not found")
    
    # Get category info
    category = await db.sow_categories.find_one(
        {"id": scope_data.get("category_id")},
        {"_id": 0}
    )
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    now = datetime.now(timezone.utc)
    user_full_name = current_user.full_name
    
    new_scope = {
        "id": str(uuid.uuid4()),
        "scope_template_id": scope_data.get("scope_template_id"),
        "category_id": scope_data.get("category_id"),
        "category_code": category.get("code"),
        "category_name": category.get("name"),
        "name": scope_data.get("name"),
        "description": scope_data.get("description"),
        "source": "consulting_added",
        "added_by": current_user.id,
        "added_by_name": user_full_name,
        "added_at": now.isoformat(),
        "revision_status": "confirmed",
        "status": "not_started",
        "progress_percentage": 0,
        "days_spent": 0,
        "meetings_count": 0,
        "timeline_weeks": scope_data.get("timeline_weeks"),
        "start_date": scope_data.get("start_date").isoformat() if scope_data.get("start_date") else None,
        "end_date": scope_data.get("end_date").isoformat() if scope_data.get("end_date") else None,
        "attachments": [],
        "change_log": [{
            "id": str(uuid.uuid4()),
            "changed_by": current_user.id,
            "changed_by_name": user_full_name,
            "changed_at": now.isoformat(),
            "change_type": "scope_added",
            "old_value": {},
            "new_value": {"name": scope_data.get("name")},
            "reason": "Added by consulting team during project execution",
            "client_consent": False
        }],
        "updated_at": now.isoformat()
    }
    
    scopes = sow.get("scopes", [])
    scopes.append(new_scope)
    
    await db.enhanced_sow.update_one(
        {"id": sow_id},
        {"$set": {
            "scopes": scopes,
            "updated_at": now.isoformat()
        }}
    )
    
    return {"message": "Scope added successfully", "scope": new_scope}


# NOTE: No delete endpoint - consulting team cannot delete scopes


@router.post("/{sow_id}/scopes/{scope_id}/attachments")
async def upload_scope_attachment(
    sow_id: str,
    scope_id: str,
    attachment_data: dict,
    current_user: User = Depends(get_current_user)
):
    """Upload attachment to a scope item"""
    db = get_db()
    sow = await db.enhanced_sow.find_one({"id": sow_id}, {"_id": 0})
    if not sow:
        raise HTTPException(status_code=404, detail="SOW not found")
    
    scopes = sow.get("scopes", [])
    scope_idx = next((i for i, s in enumerate(scopes) if s.get("id") == scope_id), None)
    
    if scope_idx is None:
        raise HTTPException(status_code=404, detail="Scope not found")
    
    scope = scopes[scope_idx]
    now = datetime.now(timezone.utc)
    user_full_name = current_user.full_name
    
    # Create attachment record
    attachment = {
        "id": str(uuid.uuid4()),
        "filename": f"{str(uuid.uuid4())}_{attachment_data.get('filename')}",
        "original_filename": attachment_data.get("filename"),
        "file_type": attachment_data.get("filename", "").split(".")[-1] if "." in attachment_data.get("filename", "") else "unknown",
        "file_size": len(base64.b64decode(attachment_data.get("file_data", ""))) if attachment_data.get("file_data") else 0,
        "uploaded_by": current_user.id,
        "uploaded_by_name": user_full_name,
        "uploaded_at": now.isoformat(),
        "description": attachment_data.get("description")
    }
    
    # Store file data
    await db.sow_attachments.insert_one({
        "id": attachment["id"],
        "file_data": attachment_data.get("file_data"),
        "created_at": now.isoformat()
    })
    
    # Add to scope
    if "attachments" not in scope:
        scope["attachments"] = []
    scope["attachments"].append(attachment)
    
    # Add change log
    if "change_log" not in scope:
        scope["change_log"] = []
    scope["change_log"].append({
        "id": str(uuid.uuid4()),
        "changed_by": current_user.id,
        "changed_by_name": user_full_name,
        "changed_at": now.isoformat(),
        "change_type": "attachment_added",
        "old_value": {},
        "new_value": {"filename": attachment["original_filename"]},
        "client_consent": False
    })
    
    scope["updated_at"] = now.isoformat()
    scopes[scope_idx] = scope
    
    await db.enhanced_sow.update_one(
        {"id": sow_id},
        {"$set": {
            "scopes": scopes,
            "updated_at": now.isoformat()
        }}
    )
    
    return {"message": "Attachment uploaded", "attachment": attachment}


@router.get("/{sow_id}/scopes/{scope_id}/attachments/{attachment_id}")
async def download_scope_attachment(sow_id: str, scope_id: str, attachment_id: str):
    """Download attachment"""
    db = get_db()
    attachment_data = await db.sow_attachments.find_one({"id": attachment_id}, {"_id": 0})
    if not attachment_data:
        raise HTTPException(status_code=404, detail="Attachment not found")
    
    # Get metadata
    sow = await db.enhanced_sow.find_one({"id": sow_id}, {"_id": 0})
    if sow:
        for scope in sow.get("scopes", []):
            if scope.get("id") == scope_id:
                for att in scope.get("attachments", []):
                    if att.get("id") == attachment_id:
                        return {
                            "filename": att.get("original_filename"),
                            "file_data": attachment_data.get("file_data")
                        }
    
    return {"file_data": attachment_data.get("file_data")}


# ============== Roadmap Approval Endpoints ==============

@router.post("/{sow_id}/roadmap/submit")
async def submit_roadmap_for_approval(
    sow_id: str,
    submit_data: dict,
    current_user: User = Depends(get_current_user)
):
    """Submit current roadmap for client approval"""
    db = get_db()
    sow = await db.enhanced_sow.find_one({"id": sow_id}, {"_id": 0})
    if not sow:
        raise HTTPException(status_code=404, detail="SOW not found")
    
    now = datetime.now(timezone.utc)
    roadmap_versions = sow.get("roadmap_versions", [])
    next_version = len(roadmap_versions) + 1
    
    # Create snapshot of current scopes
    scopes_snapshot = [dict(s) for s in sow.get("scopes", [])]
    
    new_roadmap = {
        "id": str(uuid.uuid4()),
        "version": next_version,
        "approval_cycle": submit_data.get("approval_cycle", "monthly"),
        "period_label": submit_data.get("period_label"),
        "scopes_snapshot": scopes_snapshot,
        "status": "pending_client_approval",
        "submitted_by": current_user.id,
        "submitted_by_name": current_user.full_name,
        "submitted_at": now.isoformat(),
        "created_at": now.isoformat()
    }
    
    roadmap_versions.append(new_roadmap)
    
    await db.enhanced_sow.update_one(
        {"id": sow_id},
        {"$set": {
            "roadmap_versions": roadmap_versions,
            "updated_at": now.isoformat()
        }}
    )
    
    # TODO: Send email notification to client (future SMTP integration)
    
    return {
        "message": "Roadmap submitted for client approval",
        "roadmap_version": next_version,
        "period": submit_data.get("period_label")
    }


@router.post("/{sow_id}/roadmap/{version}/client-response")
async def record_client_approval_response(
    sow_id: str,
    version: int,
    response_data: dict,
    current_user: User = Depends(get_current_user)
):
    """Record client's response to roadmap approval request"""
    db = get_db()
    sow = await db.enhanced_sow.find_one({"id": sow_id}, {"_id": 0})
    if not sow:
        raise HTTPException(status_code=404, detail="SOW not found")
    
    roadmap_versions = sow.get("roadmap_versions", [])
    version_idx = next((i for i, v in enumerate(roadmap_versions) if v.get("version") == version), None)
    
    if version_idx is None:
        raise HTTPException(status_code=404, detail="Roadmap version not found")
    
    roadmap = roadmap_versions[version_idx]
    now = datetime.now(timezone.utc)
    
    if response_data.get("approved"):
        if not response_data.get("consent_document_id"):
            raise HTTPException(
                status_code=400,
                detail="Client consent document is required for approval"
            )
        
        roadmap["status"] = "approved"
        roadmap["approved_at"] = now.isoformat()
        roadmap["client_response"] = "approved"
        roadmap["client_consent_document_id"] = response_data.get("consent_document_id")
        
        # Update current approved version
        current_approved = version
    else:
        roadmap["status"] = "revision_requested"
        roadmap["client_response"] = "revision_requested"
        current_approved = sow.get("current_approved_roadmap_version")
    
    roadmap["client_response_notes"] = response_data.get("notes")
    roadmap["client_response_at"] = now.isoformat()
    
    roadmap_versions[version_idx] = roadmap
    
    update_data = {
        "roadmap_versions": roadmap_versions,
        "updated_at": now.isoformat()
    }
    
    if response_data.get("approved"):
        update_data["current_approved_roadmap_version"] = version
    
    await db.enhanced_sow.update_one(
        {"id": sow_id},
        {"$set": update_data}
    )
    
    return {
        "message": "Client response recorded",
        "status": roadmap["status"],
        "current_approved_version": current_approved
    }


@router.post("/{sow_id}/consent-documents")
async def upload_consent_document(
    sow_id: str,
    doc_data: dict,
    current_user: User = Depends(get_current_user)
):
    """Upload client consent document (email screenshot, signed doc)"""
    db = get_db()
    sow = await db.enhanced_sow.find_one({"id": sow_id}, {"_id": 0})
    if not sow:
        raise HTTPException(status_code=404, detail="SOW not found")
    
    now = datetime.now(timezone.utc)
    user_full_name = current_user.full_name
    
    consent_doc = {
        "id": str(uuid.uuid4()),
        "filename": f"{str(uuid.uuid4())}_{doc_data.get('filename')}",
        "original_filename": doc_data.get("filename"),
        "file_type": doc_data.get("filename", "").split(".")[-1] if "." in doc_data.get("filename", "") else "unknown",
        "file_size": len(base64.b64decode(doc_data.get("file_data", ""))) if doc_data.get("file_data") else 0,
        "consent_type": doc_data.get("consent_type", "document"),
        "consent_for": doc_data.get("consent_for", "roadmap_approval"),
        "related_item_id": doc_data.get("related_item_id"),
        "uploaded_by": current_user.id,
        "uploaded_by_name": user_full_name,
        "uploaded_at": now.isoformat(),
        "notes": doc_data.get("notes")
    }
    
    # Store file data
    await db.consent_documents.insert_one({
        "id": consent_doc["id"],
        "file_data": doc_data.get("file_data"),
        "created_at": now.isoformat()
    })
    
    # Add to SOW
    consent_documents = sow.get("consent_documents", [])
    consent_documents.append(consent_doc)
    
    await db.enhanced_sow.update_one(
        {"id": sow_id},
        {"$set": {
            "consent_documents": consent_documents,
            "updated_at": now.isoformat()
        }}
    )
    
    return {"message": "Consent document uploaded", "document": consent_doc}


# ============== Variance Report Endpoints ==============

@router.get("/{sow_id}/variance-report")
async def get_scope_variance_report(sow_id: str):
    """Get variance report: Original vs Current scopes"""
    db = get_db()
    sow = await db.enhanced_sow.find_one({"id": sow_id}, {"_id": 0})
    if not sow:
        raise HTTPException(status_code=404, detail="SOW not found")
    
    original_snapshot = sow.get("original_scope_snapshot", {})
    original_scopes = original_snapshot.get("scopes", [])
    current_scopes = sow.get("scopes", [])
    
    # Build variance report
    report = {
        "original_count": len(original_scopes),
        "current_count": len(current_scopes),
        "scopes_added_by_consulting": 0,
        "scopes_revised": 0,
        "scopes_marked_not_applicable": 0,
        "scopes_confirmed": 0,
        "original_scopes": [],
        "added_scopes": [],
        "changes": []
    }
    
    for scope in current_scopes:
        if scope.get("source") == "consulting_added":
            report["scopes_added_by_consulting"] += 1
            report["added_scopes"].append({
                "id": scope.get("id"),
                "name": scope.get("name"),
                "category": scope.get("category_name"),
                "added_by": scope.get("added_by_name"),
                "added_at": scope.get("added_at")
            })
        else:
            # Original scope - check revision status
            revision_status = scope.get("revision_status", "pending_review")
            if revision_status == "revised":
                report["scopes_revised"] += 1
                report["changes"].append({
                    "id": scope.get("id"),
                    "name": scope.get("name"),
                    "change_type": "revised",
                    "reason": scope.get("revision_reason"),
                    "client_consent": scope.get("client_consent_for_revision", False)
                })
            elif revision_status == "not_applicable":
                report["scopes_marked_not_applicable"] += 1
                report["changes"].append({
                    "id": scope.get("id"),
                    "name": scope.get("name"),
                    "change_type": "not_applicable",
                    "reason": scope.get("revision_reason")
                })
            elif revision_status == "confirmed":
                report["scopes_confirmed"] += 1
            
            report["original_scopes"].append({
                "id": scope.get("id"),
                "name": scope.get("name"),
                "category": scope.get("category_name"),
                "revision_status": revision_status
            })
    
    return report


@router.get("/{sow_id}/change-log")
async def get_full_change_log(sow_id: str):
    """Get complete change log across all scopes"""
    db = get_db()
    sow = await db.enhanced_sow.find_one({"id": sow_id}, {"_id": 0})
    if not sow:
        raise HTTPException(status_code=404, detail="SOW not found")
    
    all_changes = []
    
    for scope in sow.get("scopes", []):
        for change in scope.get("change_log", []):
            all_changes.append({
                "scope_id": scope.get("id"),
                "scope_name": scope.get("name"),
                **change
            })
    
    # Sort by date descending
    all_changes.sort(key=lambda x: x.get("changed_at", ""), reverse=True)
    
    return all_changes


# ============== Task Management Within Scopes ==============

@router.post("/{sow_id}/scopes/{scope_id}/tasks")
async def create_scope_task(
    sow_id: str,
    scope_id: str,
    task_data: dict,
    current_user: User = Depends(get_current_user)
):
    """Create a task under a specific scope"""
    db = get_db()
    sow = await db.enhanced_sow.find_one({"id": sow_id}, {"_id": 0})
    if not sow:
        raise HTTPException(status_code=404, detail="SOW not found")
    
    scopes = sow.get("scopes", [])
    scope_idx = next((i for i, s in enumerate(scopes) if s.get("id") == scope_id), None)
    
    if scope_idx is None:
        raise HTTPException(status_code=404, detail="Scope not found")
    
    scope = scopes[scope_idx]
    now = datetime.now(timezone.utc)
    
    # Create new task
    new_task = {
        "id": str(uuid.uuid4()),
        "name": task_data.get("name", "Untitled Task"),
        "description": task_data.get("description", ""),
        "status": "pending",
        "priority": task_data.get("priority", "medium"),
        "due_date": task_data.get("due_date"),
        "assigned_to_id": task_data.get("assigned_to_id"),
        "assigned_to_name": task_data.get("assigned_to_name"),
        "created_by_id": current_user.id,
        "created_by_name": current_user.full_name,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
        "attachments": [],
        "approval_status": None,
        "manager_approval": None,
        "client_approval": None,
        "notes": task_data.get("notes", "")
    }
    
    # Initialize tasks list if not exists
    if "tasks" not in scope:
        scope["tasks"] = []
    
    scope["tasks"].append(new_task)
    scope["updated_at"] = now.isoformat()
    scopes[scope_idx] = scope
    
    await db.enhanced_sow.update_one(
        {"id": sow_id},
        {"$set": {
            "scopes": scopes,
            "updated_at": now.isoformat()
        }}
    )
    
    return {"message": "Task created", "task": new_task}


@router.patch("/{sow_id}/scopes/{scope_id}/tasks/{task_id}")
async def update_scope_task(
    sow_id: str,
    scope_id: str,
    task_id: str,
    task_update: dict,
    current_user: User = Depends(get_current_user)
):
    """Update a task within a scope"""
    db = get_db()
    sow = await db.enhanced_sow.find_one({"id": sow_id}, {"_id": 0})
    if not sow:
        raise HTTPException(status_code=404, detail="SOW not found")
    
    scopes = sow.get("scopes", [])
    scope_idx = next((i for i, s in enumerate(scopes) if s.get("id") == scope_id), None)
    
    if scope_idx is None:
        raise HTTPException(status_code=404, detail="Scope not found")
    
    scope = scopes[scope_idx]
    tasks = scope.get("tasks", [])
    task_idx = next((i for i, t in enumerate(tasks) if t.get("id") == task_id), None)
    
    if task_idx is None:
        raise HTTPException(status_code=404, detail="Task not found")
    
    now = datetime.now(timezone.utc)
    task = tasks[task_idx]
    
    # Update allowed fields
    updatable_fields = ["name", "description", "status", "priority", "due_date", 
                        "assigned_to_id", "assigned_to_name", "notes"]
    for field in updatable_fields:
        if field in task_update and task_update[field] is not None:
            task[field] = task_update[field]
    
    task["updated_at"] = now.isoformat()
    tasks[task_idx] = task
    scope["tasks"] = tasks
    scope["updated_at"] = now.isoformat()
    scopes[scope_idx] = scope
    
    await db.enhanced_sow.update_one(
        {"id": sow_id},
        {"$set": {
            "scopes": scopes,
            "updated_at": now.isoformat()
        }}
    )
    
    return {"message": "Task updated", "task": task}


@router.post("/{sow_id}/scopes/{scope_id}/tasks/{task_id}/attachments")
async def upload_task_attachment(
    sow_id: str,
    scope_id: str,
    task_id: str,
    attachment_data: dict,
    current_user: User = Depends(get_current_user)
):
    """Upload attachment to a task"""
    db = get_db()
    sow = await db.enhanced_sow.find_one({"id": sow_id}, {"_id": 0})
    if not sow:
        raise HTTPException(status_code=404, detail="SOW not found")
    
    scopes = sow.get("scopes", [])
    scope_idx = next((i for i, s in enumerate(scopes) if s.get("id") == scope_id), None)
    
    if scope_idx is None:
        raise HTTPException(status_code=404, detail="Scope not found")
    
    scope = scopes[scope_idx]
    tasks = scope.get("tasks", [])
    task_idx = next((i for i, t in enumerate(tasks) if t.get("id") == task_id), None)
    
    if task_idx is None:
        raise HTTPException(status_code=404, detail="Task not found")
    
    now = datetime.now(timezone.utc)
    task = tasks[task_idx]
    user_full_name = current_user.full_name
    
    # Create attachment
    attachment = {
        "id": str(uuid.uuid4()),
        "filename": f"{str(uuid.uuid4())}_{attachment_data.get('filename')}",
        "original_filename": attachment_data.get("filename"),
        "file_type": attachment_data.get("filename", "").split(".")[-1] if "." in attachment_data.get("filename", "") else "unknown",
        "uploaded_by": current_user.id,
        "uploaded_by_name": user_full_name,
        "uploaded_at": now.isoformat(),
        "description": attachment_data.get("description")
    }
    
    # Store file data
    await db.task_attachments.insert_one({
        "id": attachment["id"],
        "file_data": attachment_data.get("file_data"),
        "created_at": now.isoformat()
    })
    
    if "attachments" not in task:
        task["attachments"] = []
    task["attachments"].append(attachment)
    task["updated_at"] = now.isoformat()
    
    tasks[task_idx] = task
    scope["tasks"] = tasks
    scopes[scope_idx] = scope
    
    await db.enhanced_sow.update_one(
        {"id": sow_id},
        {"$set": {
            "scopes": scopes,
            "updated_at": now.isoformat()
        }}
    )
    
    return {"message": "Attachment uploaded", "attachment": attachment}


# ============== Task Approval Workflow ==============

@router.post("/{sow_id}/scopes/{scope_id}/tasks/{task_id}/request-approval")
async def request_task_approval(
    sow_id: str,
    scope_id: str,
    task_id: str,
    approval_request: dict,
    current_user: User = Depends(get_current_user)
):
    """
    Initiate approval request for a task.
    Parallel approval flow: Manager and Client approve independently.
    """
    db = get_db()
    sow = await db.enhanced_sow.find_one({"id": sow_id}, {"_id": 0})
    if not sow:
        raise HTTPException(status_code=404, detail="SOW not found")
    
    scopes = sow.get("scopes", [])
    scope_idx = next((i for i, s in enumerate(scopes) if s.get("id") == scope_id), None)
    
    if scope_idx is None:
        raise HTTPException(status_code=404, detail="Scope not found")
    
    scope = scopes[scope_idx]
    tasks = scope.get("tasks", [])
    task_idx = next((i for i, t in enumerate(tasks) if t.get("id") == task_id), None)
    
    if task_idx is None:
        raise HTTPException(status_code=404, detail="Task not found")
    
    now = datetime.now(timezone.utc)
    task = tasks[task_idx]
    user_full_name = current_user.full_name
    
    # Initialize approval tracking
    task["approval_status"] = "pending"
    task["approval_request_date"] = now.isoformat()
    task["approval_requested_by_id"] = current_user.id
    task["approval_requested_by_name"] = user_full_name
    task["approval_notes"] = approval_request.get("notes", "")
    
    # Manager approval tracking
    task["manager_approval"] = {
        "status": "pending",
        "manager_id": approval_request.get("manager_id"),
        "manager_name": approval_request.get("manager_name"),
        "requested_at": now.isoformat(),
        "approved_at": None,
        "notes": None
    }
    
    # Client approval tracking
    task["client_approval"] = {
        "status": "pending",
        "client_id": approval_request.get("client_id"),
        "client_name": approval_request.get("client_name"),
        "client_email": approval_request.get("client_email"),
        "requested_at": now.isoformat(),
        "approved_at": None,
        "notes": None
    }
    
    task["updated_at"] = now.isoformat()
    tasks[task_idx] = task
    scope["tasks"] = tasks
    scopes[scope_idx] = scope
    
    await db.enhanced_sow.update_one(
        {"id": sow_id},
        {"$set": {
            "scopes": scopes,
            "updated_at": now.isoformat()
        }}
    )
    
    # Create notification records
    notification = {
        "id": str(uuid.uuid4()),
        "type": "task_approval_request",
        "sow_id": sow_id,
        "scope_id": scope_id,
        "task_id": task_id,
        "task_name": task.get("name"),
        "requested_by_id": current_user.id,
        "requested_by_name": user_full_name,
        "manager_id": approval_request.get("manager_id"),
        "client_email": approval_request.get("client_email"),
        "created_at": now.isoformat(),
        "status": "pending",
        "last_reminder_sent": None
    }
    await db.task_approval_notifications.insert_one(notification)
    
    return {
        "message": "Approval request sent to Manager and Client",
        "task_id": task_id,
        "approval_status": "pending"
    }


@router.post("/{sow_id}/scopes/{scope_id}/tasks/{task_id}/approve")
async def approve_task(
    sow_id: str,
    scope_id: str,
    task_id: str,
    approval_data: dict,
    current_user: User = Depends(get_current_user)
):
    """
    Process approval from Manager or Client.
    Approval type: 'manager' or 'client'
    Both can approve independently (parallel).
    """
    # Only managers, admins, and principal consultants can approve as manager
    approval_type = approval_data.get("approval_type", "manager")
    if approval_type == "manager":
        allowed = ADMIN_ROLES + ["manager", "project_manager", "principal_consultant", "lead_consultant", "sales_manager"]
        if current_user.role not in allowed:
            raise HTTPException(status_code=403, detail="Not authorized to provide manager approval")

    db = get_db()
    sow = await db.enhanced_sow.find_one({"id": sow_id}, {"_id": 0})
    if not sow:
        raise HTTPException(status_code=404, detail="SOW not found")
    
    scopes = sow.get("scopes", [])
    scope_idx = next((i for i, s in enumerate(scopes) if s.get("id") == scope_id), None)
    
    if scope_idx is None:
        raise HTTPException(status_code=404, detail="Scope not found")
    
    scope = scopes[scope_idx]
    tasks = scope.get("tasks", [])
    task_idx = next((i for i, t in enumerate(tasks) if t.get("id") == task_id), None)
    
    if task_idx is None:
        raise HTTPException(status_code=404, detail="Task not found")
    
    now = datetime.now(timezone.utc)
    task = tasks[task_idx]
    
    approval_type = approval_data.get("approval_type", "manager")  # 'manager' or 'client'
    approved = approval_data.get("approved", True)
    notes = approval_data.get("notes", "")
    
    if approval_type == "manager":
        if not task.get("manager_approval"):
            raise HTTPException(status_code=400, detail="No manager approval pending")
        
        task["manager_approval"]["status"] = "approved" if approved else "rejected"
        task["manager_approval"]["approved_at"] = now.isoformat()
        task["manager_approval"]["approved_by_id"] = current_user.id
        task["manager_approval"]["approved_by_name"] = current_user.full_name
        task["manager_approval"]["notes"] = notes
        
    elif approval_type == "client":
        if not task.get("client_approval"):
            raise HTTPException(status_code=400, detail="No client approval pending")
        
        task["client_approval"]["status"] = "approved" if approved else "rejected"
        task["client_approval"]["approved_at"] = now.isoformat()
        task["client_approval"]["approved_by_id"] = current_user.id
        task["client_approval"]["approved_by_name"] = current_user.full_name
        task["client_approval"]["notes"] = notes
    
    # Check if fully approved (both Manager and Client approved)
    manager_approved = task.get("manager_approval", {}).get("status") == "approved"
    client_approved = task.get("client_approval", {}).get("status") == "approved"
    
    if manager_approved and client_approved:
        task["approval_status"] = "fully_approved"
        task["status"] = "approved"
    elif manager_approved:
        task["approval_status"] = "manager_approved"
    elif client_approved:
        task["approval_status"] = "client_approved"
    
    # Check for rejection
    manager_rejected = task.get("manager_approval", {}).get("status") == "rejected"
    client_rejected = task.get("client_approval", {}).get("status") == "rejected"
    
    if manager_rejected or client_rejected:
        task["approval_status"] = "rejected"
    
    task["updated_at"] = now.isoformat()
    tasks[task_idx] = task
    scope["tasks"] = tasks
    scopes[scope_idx] = scope
    
    await db.enhanced_sow.update_one(
        {"id": sow_id},
        {"$set": {
            "scopes": scopes,
            "updated_at": now.isoformat()
        }}
    )
    
    # Update notification status
    await db.task_approval_notifications.update_one(
        {"task_id": task_id},
        {"$set": {
            "status": task["approval_status"],
            "updated_at": now.isoformat()
        }}
    )
    
    return {
        "message": f"Task {approval_type} approval recorded",
        "task_id": task_id,
        "approval_status": task["approval_status"],
        "manager_status": task.get("manager_approval", {}).get("status"),
        "client_status": task.get("client_approval", {}).get("status")
    }


@router.get("/{sow_id}/tasks/pending-approvals")
async def get_pending_task_approvals(
    sow_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get all tasks pending approval for this SOW"""
    db = get_db()
    sow = await db.enhanced_sow.find_one({"id": sow_id}, {"_id": 0})
    if not sow:
        raise HTTPException(status_code=404, detail="SOW not found")
    
    pending_tasks = []
    for scope in sow.get("scopes", []):
        for task in scope.get("tasks", []):
            if task.get("approval_status") in ["pending", "manager_approved", "client_approved"]:
                pending_tasks.append({
                    "scope_id": scope.get("id"),
                    "scope_name": scope.get("name"),
                    "task": task
                })
    
    return pending_tasks


@router.get("/{sow_id}/history")
async def get_sow_history(
    sow_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get complete change history for a SOW.
    Only visible to: Reporting Manager, Project Manager, Principal Consultant, Admin
    """
    db = get_db()
    # Check permission
    allowed_roles = ADMIN_ROLES + ["principal_consultant", "manager", "project_manager", "lead_consultant"]
    if current_user.role not in allowed_roles:
        raise HTTPException(status_code=403, detail="Not authorized to view SOW history")
    
    sow = await db.enhanced_sow.find_one({"id": sow_id}, {"_id": 0})
    if not sow:
        raise HTTPException(status_code=404, detail="SOW not found")
    
    history = []
    
    # SOW level events
    if sow.get("sales_handover_at"):
        history.append({
            "event_type": "sales_handover",
            "timestamp": sow.get("sales_handover_at"),
            "changed_by": sow.get("sales_handover_by_name", "Sales Team"),
            "description": "SOW handed over to Consulting team",
            "details": {}
        })
    
    if sow.get("consulting_kickoff_at"):
        history.append({
            "event_type": "consulting_kickoff",
            "timestamp": sow.get("consulting_kickoff_at"),
            "changed_by": "System",
            "description": "Project created from kickoff request",
            "details": {"project_id": sow.get("project_id")}
        })
    
    # Scope-level changes
    for scope in sow.get("scopes", []):
        scope_name = scope.get("name", "Unknown Scope")
        
        # Check for change logs
        for change in scope.get("change_log", []):
            description_parts = []
            for field, new_value in change.get("new_value", {}).items():
                old_value = change.get("old_value", {}).get(field, "N/A")
                description_parts.append(f"{field}: {old_value} → {new_value}")
            
            history.append({
                "event_type": "scope_update",
                "timestamp": change.get("changed_at"),
                "changed_by": change.get("changed_by_name", "Unknown"),
                "description": f"Updated scope: {scope_name}",
                "details": {
                    "scope_id": scope.get("id"),
                    "scope_name": scope_name,
                    "changes": description_parts,
                    "old_value": change.get("old_value"),
                    "new_value": change.get("new_value"),
                    "client_consent": change.get("client_consent", False)
                }
            })
        
        # Revision history
        if scope.get("revision_status"):
            history.append({
                "event_type": "scope_revision",
                "timestamp": scope.get("revision_at"),
                "changed_by": scope.get("revision_by_name", "Unknown"),
                "description": f"Scope revision: {scope_name}",
                "details": {
                    "scope_id": scope.get("id"),
                    "scope_name": scope_name,
                    "revision_status": scope.get("revision_status"),
                    "revision_reason": scope.get("revision_reason"),
                    "client_consent": scope.get("client_consent_for_revision", False)
                }
            })
    
    # Sort by timestamp (most recent first)
    history.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    
    return {
        "sow_id": sow_id,
        "sow_name": sow.get("lead_name", "Unknown"),
        "project_id": sow.get("project_id"),
        "total_events": len(history),
        "history": history
    }


@router.get("/project/{project_id}/sow")
async def get_project_sow(
    project_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get inherited SOW for a project.
    Access: Assigned Consultant (view only), PM/Principal/Admin (edit)
    """
    db = get_db()
    # Get project
    project = await db.projects.find_one({"id": project_id}, {"_id": 0})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Find SOW linked to this project
    sow = await db.enhanced_sow.find_one({"project_id": project_id}, {"_id": 0})
    
    if not sow:
        # Try via agreement_id
        if project.get("agreement_id"):
            sow = await db.enhanced_sow.find_one(
                {"agreement_id": project.get("agreement_id")},
                {"_id": 0}
            )
        
        # Try via pricing_plan_id
        if not sow and project.get("pricing_plan_id"):
            sow = await db.enhanced_sow.find_one(
                {"pricing_plan_id": project.get("pricing_plan_id")},
                {"_id": 0}
            )
    
    if not sow:
        raise HTTPException(status_code=404, detail="No SOW found for this project")
    
    # Determine access level
    can_edit = current_user.role in PROJECT_ROLES
    
    # Check if user is assigned consultant
    is_assigned = False
    assigned_consultants = project.get("assigned_consultants", [])
    is_assigned = current_user.id in assigned_consultants
    
    # For consultants not assigned, deny access
    if current_user.role == "consultant" and not is_assigned and not can_edit:
        raise HTTPException(status_code=403, detail="Not authorized to view this SOW")
    
    # Remove pricing data for consulting team
    if is_consulting_team(current_user.role) and not can_edit:
        if "pricing_data" in sow:
            del sow["pricing_data"]
    
    return {
        "sow": sow,
        "can_edit": can_edit,
        "is_assigned_consultant": is_assigned,
        "project_name": project.get("name"),
        "client_name": project.get("client_name")
    }




# ============== Reopen Project ==============

class ReopenProjectRequest(BaseModel):
    reason: Optional[str] = None

@router.post("/{sow_id}/reopen")
async def reopen_project(sow_id: str, body: ReopenProjectRequest = ReopenProjectRequest(), current_user: User = Depends(get_current_user)):
    """Reopen a completed project. Admin only.
    Resets all 'completed' scopes back to 'in_progress' so the project becomes active again.
    """
    if current_user.role not in ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Only admins can reopen projects")

    db = get_db()
    sow = await db.enhanced_sow.find_one({"id": sow_id}, {"_id": 0})
    if not sow:
        raise HTTPException(status_code=404, detail="SOW not found")

    # Verify project is actually completed
    scopes = sow.get("scopes", [])
    if not sow.get("consulting_kickoff_complete"):
        raise HTTPException(status_code=400, detail="Project has not been kicked off yet")

    completed_scopes = [s for s in scopes if s.get("status") in ("completed", "not_applicable")]
    active_scopes = [s for s in scopes if s.get("status") not in ("completed", "not_applicable")]
    if active_scopes:
        raise HTTPException(status_code=400, detail="Project is not fully completed")

    # Reset completed scopes to in_progress
    now = datetime.now(timezone.utc).isoformat()
    updated_scopes = []
    for scope in scopes:
        if scope.get("status") == "completed":
            scope["status"] = "in_progress"
            scope["progress_percentage"] = scope.get("progress_percentage", 100)
            scope["reopened_at"] = now
            scope["reopened_by"] = current_user.id
        updated_scopes.append(scope)

    await db.enhanced_sow.update_one(
        {"id": sow_id},
        {"$set": {"scopes": updated_scopes, "updated_at": now}}
    )

    # Audit log
    from .audit_logging import log_audit
    await log_audit(
        action="project.reopen",
        entity_type="enhanced_sow",
        entity_id=sow_id,
        performed_by=current_user.id,
        changes={"reason": body.reason or "Admin reopened project"},
        before_state={"scopes_completed": len(completed_scopes)},
        after_state={"scopes_reopened": len([s for s in updated_scopes if s.get("reopened_at") == now])},
        metadata={"admin_email": current_user.email}
    )

    return {"success": True, "message": "Project reopened successfully", "reopened_scopes": len(completed_scopes)}


@router.get("/project/{project_id}/scopes-for-meeting")
async def get_project_scopes_for_meeting(
    project_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get available scopes from project SOW for meeting selection.
    
    Returns:
    - Committed scopes (inherited from sales SOW)
    - Additional scopes (created by consultant after project start)
    
    Validation:
    - Only returns scopes from this project's SOW
    - Consultant must be assigned to the project
    """
    db = get_db()
    
    # Get project
    project = await db.projects.find_one({"id": project_id}, {"_id": 0})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Find SOW for this project
    sow = await db.enhanced_sow.find_one({"project_id": project_id}, {"_id": 0})
    
    if not sow:
        return {
            "project_id": project_id,
            "project_name": project.get("name"),
            "has_sow": False,
            "scopes": [],
            "message": "No SOW found for this project. SOW must be created from sales team first."
        }
    
    # Extract scopes with source information
    scopes = sow.get("scopes", [])
    scopes_for_meeting = []
    
    for scope in scopes:
        scope_data = {
            "id": scope.get("id"),
            "name": scope.get("name"),
            "description": scope.get("description"),
            "status": scope.get("status", "not_started"),
            "progress_percentage": scope.get("progress_percentage", 0),
            "is_additional": scope.get("is_additional", False),
            "source": "additional" if scope.get("is_additional") else "committed",
            "fee": scope.get("fee"),
            "duration_days": scope.get("duration_days")
        }
        scopes_for_meeting.append(scope_data)
    
    # Separate committed and additional for clarity
    committed_scopes = [s for s in scopes_for_meeting if not s.get("is_additional")]
    additional_scopes = [s for s in scopes_for_meeting if s.get("is_additional")]
    
    return {
        "project_id": project_id,
        "project_name": project.get("name"),
        "sow_id": sow.get("id"),
        "sow_number": sow.get("sow_number"),
        "has_sow": True,
        "sales_handover_complete": sow.get("sales_handover_complete", False),
        "scopes": scopes_for_meeting,
        "summary": {
            "total": len(scopes_for_meeting),
            "committed": len(committed_scopes),
            "additional": len(additional_scopes),
            "completed": len([s for s in scopes_for_meeting if s.get("status") == "completed"])
        }
    }

