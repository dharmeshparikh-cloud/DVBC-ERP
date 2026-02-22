"""
Enhanced SOW Router - Role-Based Workflow

Sales Team: Select scopes → Create snapshot → Handover
Consulting Team: Review → Track progress → Submit roadmap for approval
"""

from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import uuid
import base64

router = APIRouter(prefix="/enhanced-sow", tags=["Enhanced SOW"])

# Database connection - will be set by main server
db = None

def set_db(database):
    global db
    db = database


# ============== Role Check Helpers ==============

SALES_ROLES = ["admin", "executive", "sales_manager"]
CONSULTING_ROLES = ["consultant", "lean_consultant", "lead_consultant", "senior_consultant", "principal_consultant", "subject_matter_expert", "project_manager"]
CAN_ADD_SCOPES_ROLES = ["project_manager", "consultant", "principal_consultant", "admin"]  # Can add but not delete


def is_sales_team(role: str) -> bool:
    return role in SALES_ROLES


def is_consulting_team(role: str) -> bool:
    return role in CONSULTING_ROLES


def can_add_scopes(role: str) -> bool:
    return role in CAN_ADD_SCOPES_ROLES


# ============== List SOWs ==============

@router.get("")
async def get_all_enhanced_sows():
    """Get all enhanced SOWs - root endpoint"""
    sows = await db.enhanced_sow.find({}, {"_id": 0}).sort("created_at", -1).to_list(500)
    return sows


@router.get("/list")
async def list_enhanced_sows(role: str = "all"):
    """List all enhanced SOWs - filtered by role access"""
    query = {}
    
    # For consulting, only show handed-over SOWs
    if role == "consulting":
        query["sales_handover_complete"] = True
    
    sows = await db.enhanced_sow.find(query, {"_id": 0}).sort("created_at", -1).to_list(500)
    return sows


# ============== Manager Approval ==============

@router.post("/{sow_id}/request-manager-approval")
async def request_manager_approval(
    sow_id: str,
    approval_data: dict,
    current_user_id: str = None,
    current_user_name: str = "Unknown"
):
    """Request approval from reporting manager for specific scopes"""
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
        "requested_by": current_user_id,
        "requested_by_name": current_user_name,
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

@router.post("/{pricing_plan_id}/sales-selection")
async def create_sow_from_sales_selection(
    pricing_plan_id: str,
    selection: dict,  # SalesScopeSelection
    current_user_id: str = None,
    current_user_name: str = "Unknown",
    current_user_role: str = "admin"
):
    """
    Sales team creates SOW by selecting scopes from master.
    Creates original scope snapshot (locked) and working scopes.
    """
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
    current_user_id: str = None,
    current_user_role: str = "admin"
):
    """Mark sales handover as complete - locks original snapshot"""
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
async def get_enhanced_sow(sow_id: str, current_user_role: str = "admin"):
    """Get enhanced SOW - consulting team doesn't see pricing data"""
    sow = await db.enhanced_sow.find_one({"id": sow_id}, {"_id": 0})
    if not sow:
        raise HTTPException(status_code=404, detail="SOW not found")
    
    # If consulting team, remove any pricing-related data
    if is_consulting_team(current_user_role):
        # Remove any accidentally included pricing info
        if "pricing_data" in sow:
            del sow["pricing_data"]
    
    return sow


@router.get("/by-pricing-plan/{pricing_plan_id}")
async def get_enhanced_sow_by_pricing_plan(pricing_plan_id: str, current_user_role: str = "admin"):
    """Get enhanced SOW by pricing plan ID"""
    sow = await db.enhanced_sow.find_one({"pricing_plan_id": pricing_plan_id}, {"_id": 0})
    if not sow:
        raise HTTPException(status_code=404, detail="Enhanced SOW not found for this pricing plan")
    
    # If consulting team, remove any pricing-related data
    if is_consulting_team(current_user_role):
        if "pricing_data" in sow:
            del sow["pricing_data"]
    
    return sow


@router.patch("/{sow_id}/scopes/{scope_id}")
async def update_scope_item(
    sow_id: str,
    scope_id: str,
    update: dict,  # ConsultingScopeUpdate
    current_user_id: str = None,
    current_user_name: str = "Unknown",
    current_user_role: str = "consultant"
):
    """Update scope item - consulting team updates progress"""
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
        "changed_by": current_user_id,
        "changed_by_name": current_user_name,
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
        scope["revision_by"] = current_user_id
        scope["revision_by_name"] = current_user_name
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
    current_user_id: str = None,
    current_user_name: str = "Unknown",
    current_user_role: str = "consultant"
):
    """Add new scope - consulting team can add but NOT delete"""
    if not can_add_scopes(current_user_role):
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
    
    new_scope = {
        "id": str(uuid.uuid4()),
        "scope_template_id": scope_data.get("scope_template_id"),
        "category_id": scope_data.get("category_id"),
        "category_code": category.get("code"),
        "category_name": category.get("name"),
        "name": scope_data.get("name"),
        "description": scope_data.get("description"),
        "source": "consulting_added",
        "added_by": current_user_id,
        "added_by_name": current_user_name,
        "added_at": now.isoformat(),
        "revision_status": "confirmed",  # Auto-confirmed since consulting added it
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
            "changed_by": current_user_id,
            "changed_by_name": current_user_name,
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
    attachment_data: dict,  # filename, file_data (base64), description
    current_user_id: str = None,
    current_user_name: str = "Unknown"
):
    """Upload attachment to a scope item"""
    sow = await db.enhanced_sow.find_one({"id": sow_id}, {"_id": 0})
    if not sow:
        raise HTTPException(status_code=404, detail="SOW not found")
    
    scopes = sow.get("scopes", [])
    scope_idx = next((i for i, s in enumerate(scopes) if s.get("id") == scope_id), None)
    
    if scope_idx is None:
        raise HTTPException(status_code=404, detail="Scope not found")
    
    scope = scopes[scope_idx]
    now = datetime.now(timezone.utc)
    
    # Create attachment record
    attachment = {
        "id": str(uuid.uuid4()),
        "filename": f"{str(uuid.uuid4())}_{attachment_data.get('filename')}",
        "original_filename": attachment_data.get("filename"),
        "file_type": attachment_data.get("filename", "").split(".")[-1] if "." in attachment_data.get("filename", "") else "unknown",
        "file_size": len(base64.b64decode(attachment_data.get("file_data", ""))) if attachment_data.get("file_data") else 0,
        "uploaded_by": current_user_id,
        "uploaded_by_name": current_user_name,
        "uploaded_at": now.isoformat(),
        "description": attachment_data.get("description")
    }
    
    # Store file data (in production, use cloud storage)
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
        "changed_by": current_user_id,
        "changed_by_name": current_user_name,
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
    submit_data: dict,  # RoadmapSubmitRequest
    current_user_id: str = None,
    current_user_name: str = "Unknown"
):
    """Submit current roadmap for client approval"""
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
        "submitted_by": current_user_id,
        "submitted_by_name": current_user_name,
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
    response_data: dict,  # ClientApprovalResponse
    current_user_id: str = None,
    current_user_name: str = "Unknown"
):
    """Record client's response to roadmap approval request"""
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
    doc_data: dict,  # filename, file_data, consent_type, consent_for, related_item_id, notes
    current_user_id: str = None,
    current_user_name: str = "Unknown"
):
    """Upload client consent document (email screenshot, signed doc)"""
    sow = await db.enhanced_sow.find_one({"id": sow_id}, {"_id": 0})
    if not sow:
        raise HTTPException(status_code=404, detail="SOW not found")
    
    now = datetime.now(timezone.utc)
    
    consent_doc = {
        "id": str(uuid.uuid4()),
        "filename": f"{str(uuid.uuid4())}_{doc_data.get('filename')}",
        "original_filename": doc_data.get("filename"),
        "file_type": doc_data.get("filename", "").split(".")[-1] if "." in doc_data.get("filename", "") else "unknown",
        "file_size": len(base64.b64decode(doc_data.get("file_data", ""))) if doc_data.get("file_data") else 0,
        "consent_type": doc_data.get("consent_type", "document"),  # email, document, verbal_noted
        "consent_for": doc_data.get("consent_for", "roadmap_approval"),  # scope_revision, roadmap_approval
        "related_item_id": doc_data.get("related_item_id"),
        "uploaded_by": current_user_id,
        "uploaded_by_name": current_user_name,
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
    current_user_id: str = None,
    current_user_name: str = "Unknown"
):
    """Create a task under a specific scope"""
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
        "status": "pending",  # pending, in_progress, completed, approved
        "priority": task_data.get("priority", "medium"),
        "due_date": task_data.get("due_date"),
        "assigned_to_id": task_data.get("assigned_to_id"),
        "assigned_to_name": task_data.get("assigned_to_name"),
        "created_by_id": current_user_id,
        "created_by_name": current_user_name,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
        "attachments": [],
        "approval_status": None,  # None, pending, manager_approved, client_approved, fully_approved
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
    current_user_id: str = None,
    current_user_name: str = "Unknown"
):
    """Update a task within a scope"""
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
    current_user_id: str = None,
    current_user_name: str = "Unknown"
):
    """Upload attachment to a task"""
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
    
    # Create attachment
    attachment = {
        "id": str(uuid.uuid4()),
        "filename": f"{str(uuid.uuid4())}_{attachment_data.get('filename')}",
        "original_filename": attachment_data.get("filename"),
        "file_type": attachment_data.get("filename", "").split(".")[-1] if "." in attachment_data.get("filename", "") else "unknown",
        "uploaded_by": current_user_id,
        "uploaded_by_name": current_user_name,
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
    current_user_id: str = None,
    current_user_name: str = "Unknown"
):
    """
    Initiate approval request for a task.
    Parallel approval flow: Manager and Client approve independently.
    """
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
    
    # Initialize approval tracking
    task["approval_status"] = "pending"
    task["approval_request_date"] = now.isoformat()
    task["approval_requested_by_id"] = current_user_id
    task["approval_requested_by_name"] = current_user_name
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
    
    # Create notification records for reminders (2-day reminder logic can be handled by a cron job)
    notification = {
        "id": str(uuid.uuid4()),
        "type": "task_approval_request",
        "sow_id": sow_id,
        "scope_id": scope_id,
        "task_id": task_id,
        "task_name": task.get("name"),
        "requested_by_id": current_user_id,
        "requested_by_name": current_user_name,
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
    current_user_id: str = None,
    current_user_name: str = "Unknown",
    current_user_role: str = "consultant"
):
    """
    Process approval from Manager or Client.
    Approval type: 'manager' or 'client'
    Both can approve independently (parallel).
    """
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
        task["manager_approval"]["approved_by_id"] = current_user_id
        task["manager_approval"]["approved_by_name"] = current_user_name
        task["manager_approval"]["notes"] = notes
        
    elif approval_type == "client":
        if not task.get("client_approval"):
            raise HTTPException(status_code=400, detail="No client approval pending")
        
        task["client_approval"]["status"] = "approved" if approved else "rejected"
        task["client_approval"]["approved_at"] = now.isoformat()
        task["client_approval"]["approved_by_id"] = current_user_id
        task["client_approval"]["approved_by_name"] = current_user_name
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
    current_user_id: str = None,
    current_user_role: str = "consultant"
):
    """Get all tasks pending approval for this SOW"""
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
    current_user_role: str = "consultant"
):
    """
    Get complete change history for a SOW.
    Only visible to: Reporting Manager, Project Manager, Principal Consultant, Admin
    """
    # Check permission
    allowed_roles = ["admin", "principal_consultant", "project_manager", "manager", "reporting_manager"]
    if current_user_role not in allowed_roles:
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
    current_user_id: str = None,
    current_user_role: str = "consultant"
):
    """
    Get inherited SOW for a project.
    Shows the SOW linked to the project (inherited from sales flow).
    Access: Assigned Consultant (view only), PM/Principal/Admin (edit)
    """
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
    can_edit = current_user_role in ["admin", "principal_consultant", "project_manager", "manager"]
    
    # Check if user is assigned consultant
    is_assigned = False
    if current_user_id:
        assigned_consultants = project.get("assigned_consultants", [])
        is_assigned = current_user_id in assigned_consultants
    
    # For consultants not assigned, deny access
    if current_user_role == "consultant" and not is_assigned and not can_edit:
        raise HTTPException(status_code=403, detail="Not authorized to view this SOW")
    
    # Remove pricing data for consulting team
    if is_consulting_team(current_user_role) and not can_edit:
        if "pricing_data" in sow:
            del sow["pricing_data"]
    
    return {
        "sow": sow,
        "can_edit": can_edit,
        "is_assigned_consultant": is_assigned,
        "project_name": project.get("name"),
        "client_name": project.get("client_name")
    }


