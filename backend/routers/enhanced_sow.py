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

SALES_ROLES = ["admin", "executive", "account_manager"]
CONSULTING_ROLES = ["consultant", "lean_consultant", "lead_consultant", "senior_consultant", "principal_consultant", "subject_matter_expert", "project_manager"]
CAN_ADD_SCOPES_ROLES = ["project_manager", "consultant", "principal_consultant", "admin"]  # Can add but not delete


def is_sales_team(role: str) -> bool:
    return role in SALES_ROLES


def is_consulting_team(role: str) -> bool:
    return role in CONSULTING_ROLES


def can_add_scopes(role: str) -> bool:
    return role in CAN_ADD_SCOPES_ROLES


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
        
        # Add custom scope to master for future use
        existing_template = await db.sow_scope_templates.find_one({
            "category_code": category.get("code") if category else "",
            "name": custom.get("name")
        })
        if not existing_template and category:
            new_template = {
                "id": str(uuid.uuid4()),
                "category_id": custom.get("category_id"),
                "category_code": category.get("code"),
                "name": custom.get("name"),
                "description": custom.get("description"),
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
    
    original_ids = {s.get("id") for s in original_scopes}
    
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
