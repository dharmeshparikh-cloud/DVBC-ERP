"""
Project SOW Delivery Router - Consulting Execution Layer

This module provides the delivery layer for SOW execution:
1. PROJECT_SOW - Inherited from SOW_MASTER (enhanced_sow), PM customizable
2. TASKS - Under each PROJECT_SOW scope
3. PROOFS - Attached to SOW or Task level

Architecture:
- SOW_MASTER (enhanced_sow) = Sales owned, locked after kickoff
- PROJECT_SOW = Delivery owned, copied from master on kickoff
- TASKS = Execution units under scopes
- PROOFS = Evidence/deliverables attached to SOW or Task

SSOT Rules:
- enhanced_sow is the single source of truth for SOW definition
- project_sow references enhanced_sow.id (sow_master_id)
- No duplicate SOW creation allowed
"""

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from enum import Enum
import uuid

from .deps import get_db, get_current_user, ADMIN_ROLES
from .models import User

router = APIRouter(prefix="/project-sow-delivery", tags=["Project SOW Delivery"])


# ============== Enums ==============

class ProjectSOWStatus(str, Enum):
    """Status at PROJECT_SOW and Scope level"""
    OPEN = "open"
    WIP = "wip"
    IMPLEMENTED = "implemented"  # Final status - requires proof
    NOT_APPLICABLE_PENDING = "na_pending"  # Pending manager approval
    NOT_APPLICABLE = "not_applicable"  # Approved by manager
    REOPEN = "reopen"


class TaskStatus(str, Enum):
    """Status for tasks under SOW"""
    OPEN = "open"
    WIP = "wip"
    IMPLEMENTED = "implemented"  # Changed from DELIVERED
    BLOCKED = "blocked"


class ProofEntityType(str, Enum):
    """Entity type for proof attachment"""
    PROJECT_SOW = "project_sow"
    TASK = "task"


# ============== Models ==============

class ProjectSOWScope(BaseModel):
    """Scope item in PROJECT_SOW (copied from master, customizable by PM)"""
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    original_scope_id: str  # Reference to scope in SOW_MASTER
    name: str
    description: Optional[str] = None
    category_id: str
    category_code: str
    category_name: str
    domain: Optional[str] = None  # From domains[] if set
    timeline_weeks: Optional[int] = None
    assigned_consultant_id: Optional[str] = None
    assigned_consultant_name: Optional[str] = None
    status: ProjectSOWStatus = ProjectSOWStatus.OPEN
    progress_percentage: float = 0.0
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    deliverables: List[str] = []  # Expected deliverables
    notes: Optional[str] = None
    is_customized: bool = False  # True if PM modified from original
    customized_by: Optional[str] = None
    customized_at: Optional[datetime] = None


class ProjectSOW(BaseModel):
    """PROJECT_SOW - Delivery layer, references SOW_MASTER"""
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    sow_master_id: str  # Reference to enhanced_sow.id
    project_id: str
    lead_id: str
    client_name: Optional[str] = None
    
    # Scopes (copied from master, PM can customize)
    scopes: List[ProjectSOWScope] = []
    
    # SOW-level status
    status: ProjectSOWStatus = ProjectSOWStatus.OPEN
    
    # Metadata
    created_from_kickoff: bool = True
    created_by: str
    created_by_name: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_by: Optional[str] = None
    updated_by_name: Optional[str] = None
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Re-open tracking
    reopen_count: int = 0
    last_reopen_at: Optional[datetime] = None
    last_reopen_by: Optional[str] = None
    last_reopen_reason: Optional[str] = None


class SOWTask(BaseModel):
    """Task under PROJECT_SOW scope"""
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    project_sow_id: str
    scope_id: Optional[str] = None  # Optional link to specific scope
    
    # Task details
    title: str
    description: Optional[str] = None
    
    # Assignment
    assigned_to: Optional[str] = None  # User ID
    assigned_to_name: Optional[str] = None
    
    # Status
    status: TaskStatus = TaskStatus.OPEN
    
    # Tracking
    due_date: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    remarks: Optional[str] = None
    
    # AI generated flag
    is_ai_generated: bool = False
    
    # Metadata
    created_by: str
    created_by_name: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_by: Optional[str] = None
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SOWProof(BaseModel):
    """Proof/Evidence attached to SOW or Task"""
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    entity_type: ProofEntityType
    entity_id: str  # project_sow.id or task.id
    
    # File info
    file_url: str
    file_name: str
    file_type: Optional[str] = None
    file_size: Optional[int] = None
    
    # Version tracking
    version: int = 1
    replaces_proof_id: Optional[str] = None  # Previous version
    
    # Metadata
    description: Optional[str] = None
    uploaded_by: str
    uploaded_by_name: Optional[str] = None
    uploaded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ============== Request Models ==============

class CreateProjectSOWRequest(BaseModel):
    """Create PROJECT_SOW from kickoff (usually auto-triggered)"""
    sow_master_id: str
    project_id: str


class UpdateProjectSOWStatusRequest(BaseModel):
    """Update PROJECT_SOW status"""
    status: ProjectSOWStatus
    reason: Optional[str] = None  # Required for reopen


class CustomizeScopeRequest(BaseModel):
    """PM customizing a scope in PROJECT_SOW"""
    name: Optional[str] = None
    description: Optional[str] = None
    timeline_weeks: Optional[int] = None
    assigned_consultant_id: Optional[str] = None
    deliverables: Optional[List[str]] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class CreateTaskRequest(BaseModel):
    """Create a new task"""
    scope_id: Optional[str] = None
    title: str
    description: Optional[str] = None
    assigned_to: Optional[str] = None
    due_date: Optional[datetime] = None
    is_ai_generated: bool = False


class UpdateTaskRequest(BaseModel):
    """Update task"""
    title: Optional[str] = None
    description: Optional[str] = None
    assigned_to: Optional[str] = None
    status: Optional[TaskStatus] = None
    due_date: Optional[datetime] = None
    remarks: Optional[str] = None


class UploadProofRequest(BaseModel):
    """Upload proof metadata (file uploaded separately via Object Storage)"""
    entity_type: ProofEntityType
    entity_id: str
    file_url: str
    file_name: str
    file_type: Optional[str] = None
    file_size: Optional[int] = None
    description: Optional[str] = None


# ============== Role Helpers ==============

PM_ROLES = ["admin", "principal_consultant", "senior_consultant", "manager", "project_manager"]
CONSULTANT_ROLES = ["consultant", "lean_consultant", "lead_consultant", "senior_consultant", "principal_consultant"]
MANAGER_ROLES = ["admin", "manager", "principal_consultant", "sales_manager", "hr_manager"]


def can_manage_project_sow(role: str) -> bool:
    """Check if role can manage PROJECT_SOW (customize scopes)"""
    return role in PM_ROLES


def can_execute_tasks(role: str) -> bool:
    """Check if role can work on tasks"""
    return role in CONSULTANT_ROLES or role in PM_ROLES


def can_reopen_sow(role: str) -> bool:
    """Check if role can request/approve reopen"""
    return role in MANAGER_ROLES


# ============== PROJECT_SOW CRUD ==============

@router.post("/create-from-kickoff")
async def create_project_sow_from_kickoff(
    request: CreateProjectSOWRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Create PROJECT_SOW from SOW_MASTER on kickoff approval.
    This copies scopes from enhanced_sow and creates delivery layer.
    
    Called automatically on kickoff or manually by PM.
    """
    db = get_db()
    
    # Check if PROJECT_SOW already exists for this project
    existing = await db.project_sow.find_one({"project_id": request.project_id}, {"_id": 0})
    if existing:
        raise HTTPException(
            status_code=400, 
            detail=f"PROJECT_SOW already exists for project {request.project_id}. Use existing one."
        )
    
    # Get SOW_MASTER (enhanced_sow)
    sow_master = await db.enhanced_sow.find_one({"id": request.sow_master_id}, {"_id": 0})
    if not sow_master:
        raise HTTPException(status_code=404, detail="SOW Master not found")
    
    # Get project and lead info
    project = await db.projects.find_one({"id": request.project_id}, {"_id": 0})
    lead = await db.leads.find_one({"id": sow_master.get("lead_id")}, {"_id": 0})
    
    # Copy scopes from master
    master_scopes = sow_master.get("scopes", [])
    delivery_scopes = []
    
    for scope in master_scopes:
        delivery_scope = ProjectSOWScope(
            original_scope_id=scope.get("id", str(uuid.uuid4())),
            name=scope.get("name", ""),
            description=scope.get("description"),
            category_id=scope.get("category_id", ""),
            category_code=scope.get("category_code", ""),
            category_name=scope.get("category_name", ""),
            domain=scope.get("category_code"),  # Use category as domain for now
            timeline_weeks=scope.get("timeline_weeks"),
            assigned_consultant_id=scope.get("assigned_consultant_id"),
            assigned_consultant_name=scope.get("assigned_consultant_name"),
            deliverables=scope.get("deliverables", []),
            status=ProjectSOWStatus.OPEN,
            progress_percentage=0.0
        )
        delivery_scopes.append(delivery_scope.model_dump())
    
    # Create PROJECT_SOW
    project_sow = ProjectSOW(
        sow_master_id=request.sow_master_id,
        project_id=request.project_id,
        lead_id=sow_master.get("lead_id", ""),
        client_name=lead.get("company") if lead else project.get("client_name") if project else None,
        scopes=delivery_scopes,
        status=ProjectSOWStatus.OPEN,
        created_from_kickoff=True,
        created_by=current_user.id,
        created_by_name=current_user.full_name
    )
    
    await db.project_sow.insert_one(project_sow.model_dump())
    
    # Lock the SOW_MASTER
    await db.enhanced_sow.update_one(
        {"id": request.sow_master_id},
        {
            "$set": {
                "is_locked": True,
                "locked_at": datetime.now(timezone.utc).isoformat(),
                "locked_by": current_user.id,
                "project_id": request.project_id
            }
        }
    )
    
    return {
        "message": "PROJECT_SOW created successfully",
        "project_sow_id": project_sow.id,
        "scopes_count": len(delivery_scopes),
        "sow_master_locked": True
    }


@router.get("/project/{project_id}")
async def get_project_sow(
    project_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get PROJECT_SOW for a project with tasks and proofs"""
    db = get_db()
    
    project_sow = await db.project_sow.find_one({"project_id": project_id}, {"_id": 0})
    if not project_sow:
        # Check if SOW_MASTER exists but not yet converted
        project = await db.projects.find_one({"id": project_id}, {"_id": 0})
        if project:
            sow_master = await db.enhanced_sow.find_one({"project_id": project_id}, {"_id": 0})
            if sow_master:
                return {
                    "project_sow": None,
                    "sow_master_exists": True,
                    "sow_master_id": sow_master.get("id"),
                    "message": "SOW Master exists but PROJECT_SOW not yet created. Trigger kickoff to create."
                }
        raise HTTPException(status_code=404, detail="PROJECT_SOW not found")
    
    # Get tasks for this PROJECT_SOW
    tasks = await db.sow_tasks.find(
        {"project_sow_id": project_sow["id"]}, 
        {"_id": 0}
    ).sort("created_at", 1).to_list(500)
    
    # Get proofs for this PROJECT_SOW
    proofs = await db.sow_proofs.find(
        {"entity_type": "project_sow", "entity_id": project_sow["id"]},
        {"_id": 0}
    ).sort("uploaded_at", -1).to_list(100)
    
    # Get task-level proofs
    task_ids = [t["id"] for t in tasks]
    task_proofs = await db.sow_proofs.find(
        {"entity_type": "task", "entity_id": {"$in": task_ids}},
        {"_id": 0}
    ).to_list(500)
    
    # Map proofs to tasks
    task_proofs_map = {}
    for proof in task_proofs:
        tid = proof["entity_id"]
        if tid not in task_proofs_map:
            task_proofs_map[tid] = []
        task_proofs_map[tid].append(proof)
    
    # Attach proofs to tasks
    for task in tasks:
        task["proofs"] = task_proofs_map.get(task["id"], [])
    
    # Determine user access level
    can_edit = can_manage_project_sow(current_user.role)
    can_work = can_execute_tasks(current_user.role)
    
    return {
        "project_sow": project_sow,
        "tasks": tasks,
        "proofs": proofs,
        "permissions": {
            "can_edit_sow": can_edit,
            "can_manage_tasks": can_work,
            "can_reopen": can_reopen_sow(current_user.role)
        }
    }


@router.patch("/{project_sow_id}/status")
async def update_project_sow_status(
    project_sow_id: str,
    request: UpdateProjectSOWStatusRequest,
    current_user: User = Depends(get_current_user)
):
    """Update PROJECT_SOW status"""
    db = get_db()
    
    project_sow = await db.project_sow.find_one({"id": project_sow_id}, {"_id": 0})
    if not project_sow:
        raise HTTPException(status_code=404, detail="PROJECT_SOW not found")
    
    # Re-open requires manager role and reason
    if request.status == ProjectSOWStatus.REOPEN:
        if not can_reopen_sow(current_user.role):
            raise HTTPException(status_code=403, detail="Only managers can reopen SOW")
        if not request.reason:
            raise HTTPException(status_code=400, detail="Reason required for reopen")
        
        # Notify manager (simplified - just log for now)
        # TODO: Send notification
        
        update_data = {
            "status": request.status.value,
            "reopen_count": project_sow.get("reopen_count", 0) + 1,
            "last_reopen_at": datetime.now(timezone.utc).isoformat(),
            "last_reopen_by": current_user.id,
            "last_reopen_reason": request.reason,
            "updated_by": current_user.id,
            "updated_by_name": current_user.full_name,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
    else:
        update_data = {
            "status": request.status.value,
            "updated_by": current_user.id,
            "updated_by_name": current_user.full_name,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
    
    await db.project_sow.update_one(
        {"id": project_sow_id},
        {"$set": update_data}
    )
    
    return {"message": f"PROJECT_SOW status updated to {request.status.value}"}


@router.patch("/{project_sow_id}/scope/{scope_id}")
async def customize_scope(
    project_sow_id: str,
    scope_id: str,
    request: CustomizeScopeRequest,
    current_user: User = Depends(get_current_user)
):
    """PM customizes a scope in PROJECT_SOW"""
    if not can_manage_project_sow(current_user.role):
        raise HTTPException(status_code=403, detail="Only PM roles can customize scopes")
    
    db = get_db()
    
    project_sow = await db.project_sow.find_one({"id": project_sow_id}, {"_id": 0})
    if not project_sow:
        raise HTTPException(status_code=404, detail="PROJECT_SOW not found")
    
    # Find and update scope
    scopes = project_sow.get("scopes", [])
    scope_found = False
    
    for scope in scopes:
        if scope.get("id") == scope_id:
            scope_found = True
            # Update fields if provided
            if request.name is not None:
                scope["name"] = request.name
            if request.description is not None:
                scope["description"] = request.description
            if request.timeline_weeks is not None:
                scope["timeline_weeks"] = request.timeline_weeks
            if request.assigned_consultant_id is not None:
                scope["assigned_consultant_id"] = request.assigned_consultant_id
                # Get consultant name
                consultant = await db.users.find_one({"id": request.assigned_consultant_id}, {"_id": 0})
                if consultant:
                    scope["assigned_consultant_name"] = consultant.get("full_name")
            if request.deliverables is not None:
                scope["deliverables"] = request.deliverables
            if request.start_date is not None:
                scope["start_date"] = request.start_date.isoformat()
            if request.end_date is not None:
                scope["end_date"] = request.end_date.isoformat()
            
            # Mark as customized
            scope["is_customized"] = True
            scope["customized_by"] = current_user.id
            scope["customized_at"] = datetime.now(timezone.utc).isoformat()
            break
    
    if not scope_found:
        raise HTTPException(status_code=404, detail="Scope not found")
    
    await db.project_sow.update_one(
        {"id": project_sow_id},
        {
            "$set": {
                "scopes": scopes,
                "updated_by": current_user.id,
                "updated_by_name": current_user.full_name,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    return {"message": "Scope customized successfully"}


@router.patch("/{project_sow_id}/scope/{scope_id}/status")
async def update_scope_status(
    project_sow_id: str,
    scope_id: str,
    status: ProjectSOWStatus,
    current_user: User = Depends(get_current_user)
):
    """Update scope status (Consultant/PM can do this)"""
    if not can_execute_tasks(current_user.role):
        raise HTTPException(status_code=403, detail="Access denied")
    
    db = get_db()
    now = datetime.now(timezone.utc)
    
    project_sow = await db.project_sow.find_one({"id": project_sow_id}, {"_id": 0})
    if not project_sow:
        raise HTTPException(status_code=404, detail="PROJECT_SOW not found")
    
    scopes = project_sow.get("scopes", [])
    target_scope = None
    for scope in scopes:
        if scope.get("id") == scope_id:
            target_scope = scope
            break
    
    if not target_scope:
        raise HTTPException(status_code=404, detail="Scope not found")
    
    old_status = target_scope.get("status")
    
    # Handle "Not Applicable" - requires manager approval
    if status.value == "not_applicable":
        # Only managers can directly set to not_applicable
        if current_user.role not in ADMIN_ROLES + ["principal_consultant", "manager"]:
            raise HTTPException(
                status_code=403, 
                detail="Only managers can mark scope as Not Applicable. Request will be sent for approval."
            )
    
    # Handle "Not Applicable Pending" - consultant requests manager approval
    if status.value == "na_pending":
        target_scope["status"] = status.value
        target_scope["na_requested_by"] = current_user.id
        target_scope["na_requested_by_name"] = current_user.full_name
        target_scope["na_requested_at"] = now.isoformat()
        # TODO: Send notification to manager
    
    # Handle "Implemented" - requires proof
    elif status.value == "implemented":
        if old_status == "implemented":
            # Already implemented, no change
            return {"message": "Scope already implemented", "overall_status": project_sow.get("status")}
        
        # Check if there's at least one proof for this scope or its tasks
        scope_tasks = await db.sow_tasks.find({"scope_id": scope_id}, {"id": 1, "proofs": 1}).to_list(1000)
        task_ids = [t["id"] for t in scope_tasks]
        
        # Count proofs
        scope_proofs = await db.sow_proofs.count_documents({
            "entity_type": "scope", 
            "entity_id": scope_id
        })
        
        task_with_proofs = sum(1 for t in scope_tasks if t.get("proofs"))
        total_proofs = scope_proofs + task_with_proofs
        
        if total_proofs == 0:
            raise HTTPException(
                status_code=400, 
                detail="Cannot mark as Implemented without uploading at least one proof. Please upload proof for the scope or its tasks."
            )
        
        target_scope["status"] = status.value
        target_scope["end_date"] = now.isoformat()
        
        # Calculate days taken if start_date exists
        if target_scope.get("start_date"):
            start = datetime.fromisoformat(target_scope["start_date"].replace("Z", "+00:00"))
            days = (now - start).days
            target_scope["days_taken"] = days
        
        target_scope["implemented_by"] = current_user.id
        target_scope["implemented_by_name"] = current_user.full_name
        target_scope["implemented_at"] = now.isoformat()
    
    # Handle Reopen - clear implementation data
    elif status.value in ["open", "wip", "reopen"]:
        target_scope["status"] = status.value
        if old_status == "implemented":
            target_scope["end_date"] = None
            target_scope["days_taken"] = None
            target_scope["reopened_by"] = current_user.id
            target_scope["reopened_at"] = now.isoformat()
    
    else:
        target_scope["status"] = status.value
    
    # Recalculate overall SOW status
    statuses = [s.get("status") for s in scopes]
    if all(s in ["implemented", "not_applicable"] for s in statuses):
        overall_status = ProjectSOWStatus.IMPLEMENTED.value
    elif any(s == "wip" for s in statuses):
        overall_status = ProjectSOWStatus.WIP.value
    else:
        overall_status = project_sow.get("status", ProjectSOWStatus.OPEN.value)
    
    await db.project_sow.update_one(
        {"id": project_sow_id},
        {
            "$set": {
                "scopes": scopes,
                "status": overall_status,
                "updated_by": current_user.id,
                "updated_at": now.isoformat()
            }
        }
    )
    
    return {"message": f"Scope status updated to {status.value}", "overall_status": overall_status}


# Manager approval endpoint for Not Applicable
@router.post("/{project_sow_id}/scope/{scope_id}/approve-na")
async def approve_not_applicable(
    project_sow_id: str,
    scope_id: str,
    approve: bool = True,
    current_user: User = Depends(get_current_user)
):
    """Manager approves or rejects 'Not Applicable' request"""
    if current_user.role not in ADMIN_ROLES + ["principal_consultant", "manager"]:
        raise HTTPException(status_code=403, detail="Only managers can approve Not Applicable requests")
    
    db = get_db()
    now = datetime.now(timezone.utc)
    
    project_sow = await db.project_sow.find_one({"id": project_sow_id}, {"_id": 0})
    if not project_sow:
        raise HTTPException(status_code=404, detail="PROJECT_SOW not found")
    
    scopes = project_sow.get("scopes", [])
    for scope in scopes:
        if scope.get("id") == scope_id:
            if scope.get("status") != "na_pending":
                raise HTTPException(status_code=400, detail="Scope is not pending NA approval")
            
            if approve:
                scope["status"] = ProjectSOWStatus.NOT_APPLICABLE.value
                scope["na_approved_by"] = current_user.id
                scope["na_approved_by_name"] = current_user.full_name
                scope["na_approved_at"] = now.isoformat()
            else:
                # Rejected - revert to previous status (wip or open)
                scope["status"] = ProjectSOWStatus.WIP.value
                scope["na_rejected_by"] = current_user.id
                scope["na_rejected_at"] = now.isoformat()
            break
    
    # Recalculate overall status
    statuses = [s.get("status") for s in scopes]
    if all(s in ["implemented", "not_applicable"] for s in statuses):
        overall_status = ProjectSOWStatus.IMPLEMENTED.value
    elif any(s == "wip" for s in statuses):
        overall_status = ProjectSOWStatus.WIP.value
    else:
        overall_status = project_sow.get("status", ProjectSOWStatus.OPEN.value)
    
    await db.project_sow.update_one(
        {"id": project_sow_id},
        {
            "$set": {
                "scopes": scopes,
                "status": overall_status,
                "updated_at": now.isoformat()
            }
        }
    )
    
    action = "approved" if approve else "rejected"
    return {"message": f"Not Applicable request {action}", "overall_status": overall_status}


class ScopeDateUpdate(BaseModel):
    field: str  # "start_date" or "end_date"
    value: Optional[str] = None


@router.patch("/{project_sow_id}/scope/{scope_id}/date")
async def update_scope_date(
    project_sow_id: str,
    scope_id: str,
    data: ScopeDateUpdate,
    current_user: User = Depends(get_current_user)
):
    """Update scope start_date or end_date (Consultant/PM can do this)"""
    if not can_execute_tasks(current_user.role):
        raise HTTPException(status_code=403, detail="Access denied")
    
    if data.field not in ["start_date", "end_date"]:
        raise HTTPException(status_code=400, detail="Invalid field. Must be 'start_date' or 'end_date'")
    
    db = get_db()
    now = datetime.now(timezone.utc)
    
    project_sow = await db.project_sow.find_one({"id": project_sow_id}, {"_id": 0})
    if not project_sow:
        raise HTTPException(status_code=404, detail="PROJECT_SOW not found")
    
    scopes = project_sow.get("scopes", [])
    for scope in scopes:
        if scope.get("id") == scope_id:
            scope[data.field] = data.value
            
            # Recalculate days_taken if both dates are set
            if scope.get("start_date") and scope.get("end_date"):
                start = datetime.fromisoformat(scope["start_date"].replace("Z", "+00:00"))
                end = datetime.fromisoformat(scope["end_date"].replace("Z", "+00:00"))
                days = (end - start).days
                scope["days_taken"] = days
            break
    
    await db.project_sow.update_one(
        {"id": project_sow_id},
        {
            "$set": {
                "scopes": scopes,
                "updated_by": current_user.id,
                "updated_at": now.isoformat()
            }
        }
    )
    
    return {"message": f"Scope {data.field} updated"}


@router.post("/{project_sow_id}/scope/{scope_id}/ai-generate-tasks")
async def ai_generate_tasks_for_scope(
    project_sow_id: str,
    scope_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Generate AI-suggested tasks for a specific scope item.
    Tasks are created automatically and marked as AI-generated.
    """
    import os
    import httpx
    
    if not can_execute_tasks(current_user.role):
        raise HTTPException(status_code=403, detail="Access denied")
    
    db = get_db()
    
    # Get PROJECT_SOW and scope
    project_sow = await db.project_sow.find_one({"id": project_sow_id}, {"_id": 0})
    if not project_sow:
        raise HTTPException(status_code=404, detail="PROJECT_SOW not found")
    
    scope = None
    for s in project_sow.get("scopes", []):
        if s.get("id") == scope_id:
            scope = s
            break
    
    if not scope:
        raise HTTPException(status_code=404, detail="Scope not found")
    
    # Call AI suggestion endpoint internally
    try:
        from emergentintegrations.llm.chat import LlmChat, UserMessage
        
        EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY", "")
        if not EMERGENT_LLM_KEY:
            raise HTTPException(status_code=500, detail="AI service not configured")
        
        # Build prompt
        prompt_parts = [
            f"Generate 3-5 specific, actionable tasks for the following consulting scope item:",
            f"",
            f"SCOPE: {scope.get('name', '')}",
        ]
        
        if scope.get("description"):
            prompt_parts.append(f"DESCRIPTION: {scope.get('description')}")
        
        if scope.get("category_name"):
            prompt_parts.append(f"CATEGORY: {scope.get('category_name')}")
        
        if scope.get("deliverables"):
            prompt_parts.append(f"EXPECTED DELIVERABLES: {', '.join(scope.get('deliverables', []))}")
        
        if scope.get("timeline_weeks"):
            prompt_parts.append(f"TIMELINE: {scope.get('timeline_weeks')} weeks")
        
        prompt_parts.extend([
            "",
            "For each task, provide:",
            "- A clear, action-oriented title (max 10 words)",
            "- A brief description of what needs to be done (1-2 sentences)",
            "",
            "Output format (JSON array):",
            '[{"title": "Task title here", "description": "Task description here"}, ...]',
            "",
            "Output ONLY the JSON array, no explanations or markdown."
        ])
        
        full_prompt = "\n".join(prompt_parts)
        
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"sow-tasks-{uuid.uuid4().hex[:8]}",
            system_message="You are a consulting project manager assistant. Generate specific, actionable tasks for consulting engagements. Output only valid JSON arrays.",
        )
        chat.with_model("openai", "gpt-5.2")
        
        response = await chat.send_message(UserMessage(text=full_prompt))
        
        # Clean response and parse JSON
        import json
        clean = response.strip()
        if clean.startswith("```"):
            clean = clean.split("```")[1]
            if clean.startswith("json"):
                clean = clean[4:]
        clean = clean.strip()
        
        tasks_data = json.loads(clean)
        if not isinstance(tasks_data, list):
            tasks_data = [tasks_data]
        
        # Create tasks in database
        created_tasks = []
        for task_data in tasks_data[:5]:  # Max 5 tasks
            if isinstance(task_data, dict) and task_data.get("title"):
                task = SOWTask(
                    project_sow_id=project_sow_id,
                    scope_id=scope_id,
                    title=task_data.get("title", "")[:100],
                    description=task_data.get("description", "")[:500],
                    is_ai_generated=True,
                    created_by=current_user.id,
                    created_by_name=current_user.full_name
                )
                await db.sow_tasks.insert_one(task.model_dump())
                created_tasks.append({"id": task.id, "title": task.title})
        
        return {
            "message": f"Generated {len(created_tasks)} AI-suggested tasks",
            "tasks": created_tasks
        }
        
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Failed to parse AI response")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Task generation failed: {str(e)}")


# ============== TASK CRUD ==============

@router.post("/{project_sow_id}/tasks")
async def create_task(
    project_sow_id: str,
    request: CreateTaskRequest,
    current_user: User = Depends(get_current_user)
):
    """Create a new task under PROJECT_SOW"""
    if not can_execute_tasks(current_user.role):
        raise HTTPException(status_code=403, detail="Access denied")
    
    db = get_db()
    
    # Verify PROJECT_SOW exists
    project_sow = await db.project_sow.find_one({"id": project_sow_id}, {"_id": 0})
    if not project_sow:
        raise HTTPException(status_code=404, detail="PROJECT_SOW not found")
    
    # Get assignee name if assigned
    assigned_name = None
    if request.assigned_to:
        assignee = await db.users.find_one({"id": request.assigned_to}, {"_id": 0})
        if assignee:
            assigned_name = assignee.get("full_name")
    
    task = SOWTask(
        project_sow_id=project_sow_id,
        scope_id=request.scope_id,
        title=request.title,
        description=request.description,
        assigned_to=request.assigned_to,
        assigned_to_name=assigned_name,
        due_date=request.due_date,
        is_ai_generated=request.is_ai_generated,
        created_by=current_user.id,
        created_by_name=current_user.full_name
    )
    
    await db.sow_tasks.insert_one(task.model_dump())
    
    return {"message": "Task created", "task_id": task.id}


@router.get("/{project_sow_id}/tasks")
async def get_tasks(
    project_sow_id: str,
    scope_id: Optional[str] = None,
    status: Optional[TaskStatus] = None,
    current_user: User = Depends(get_current_user)
):
    """Get tasks for PROJECT_SOW, optionally filtered by scope or status"""
    db = get_db()
    
    query = {"project_sow_id": project_sow_id}
    if scope_id:
        query["scope_id"] = scope_id
    if status:
        query["status"] = status.value
    
    tasks = await db.sow_tasks.find(query, {"_id": 0}).sort("created_at", 1).to_list(500)
    
    # Attach proofs to each task
    for task in tasks:
        proofs = await db.sow_proofs.find(
            {"entity_type": "task", "entity_id": task["id"]},
            {"_id": 0}
        ).to_list(50)
        task["proofs"] = proofs
    
    return {"tasks": tasks, "total": len(tasks)}


@router.patch("/{project_sow_id}/tasks/{task_id}")
async def update_task(
    project_sow_id: str,
    task_id: str,
    request: UpdateTaskRequest,
    current_user: User = Depends(get_current_user)
):
    """Update a task"""
    if not can_execute_tasks(current_user.role):
        raise HTTPException(status_code=403, detail="Access denied")
    
    db = get_db()
    
    task = await db.sow_tasks.find_one({"id": task_id, "project_sow_id": project_sow_id}, {"_id": 0})
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    update_data = {
        "updated_by": current_user.id,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    if request.title is not None:
        update_data["title"] = request.title
    if request.description is not None:
        update_data["description"] = request.description
    if request.assigned_to is not None:
        update_data["assigned_to"] = request.assigned_to
        assignee = await db.users.find_one({"id": request.assigned_to}, {"_id": 0})
        if assignee:
            update_data["assigned_to_name"] = assignee.get("full_name")
    if request.status is not None:
        update_data["status"] = request.status.value
        if request.status == TaskStatus.DELIVERED:
            update_data["completed_at"] = datetime.now(timezone.utc).isoformat()
    if request.due_date is not None:
        update_data["due_date"] = request.due_date.isoformat()
    if request.remarks is not None:
        update_data["remarks"] = request.remarks
    
    await db.sow_tasks.update_one({"id": task_id}, {"$set": update_data})
    
    return {"message": "Task updated"}


@router.delete("/{project_sow_id}/tasks/{task_id}")
async def delete_task(
    project_sow_id: str,
    task_id: str,
    current_user: User = Depends(get_current_user)
):
    """Delete a task"""
    if not can_manage_project_sow(current_user.role):
        raise HTTPException(status_code=403, detail="Only PM roles can delete tasks")
    
    db = get_db()
    
    result = await db.sow_tasks.delete_one({"id": task_id, "project_sow_id": project_sow_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Also delete associated proofs
    await db.sow_proofs.delete_many({"entity_type": "task", "entity_id": task_id})
    
    return {"message": "Task deleted"}


# ============== PROOF CRUD ==============

@router.post("/proofs")
async def upload_proof(
    request: UploadProofRequest,
    current_user: User = Depends(get_current_user)
):
    """Register proof after file uploaded to Object Storage"""
    db = get_db()
    
    # Verify entity exists
    if request.entity_type == ProofEntityType.PROJECT_SOW:
        entity = await db.project_sow.find_one({"id": request.entity_id}, {"_id": 0})
    else:
        entity = await db.sow_tasks.find_one({"id": request.entity_id}, {"_id": 0})
    
    if not entity:
        raise HTTPException(status_code=404, detail=f"{request.entity_type.value} not found")
    
    # Check for existing proof with same name (versioning)
    existing = await db.sow_proofs.find_one({
        "entity_type": request.entity_type.value,
        "entity_id": request.entity_id,
        "file_name": request.file_name
    }, {"_id": 0})
    
    version = 1
    replaces_id = None
    if existing:
        version = existing.get("version", 1) + 1
        replaces_id = existing.get("id")
    
    proof = SOWProof(
        entity_type=request.entity_type,
        entity_id=request.entity_id,
        file_url=request.file_url,
        file_name=request.file_name,
        file_type=request.file_type,
        file_size=request.file_size,
        version=version,
        replaces_proof_id=replaces_id,
        description=request.description,
        uploaded_by=current_user.id,
        uploaded_by_name=current_user.full_name
    )
    
    await db.sow_proofs.insert_one(proof.model_dump())
    
    return {"message": "Proof registered", "proof_id": proof.id, "version": version}


@router.get("/proofs/{entity_type}/{entity_id}")
async def get_proofs(
    entity_type: ProofEntityType,
    entity_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get proofs for an entity"""
    db = get_db()
    
    proofs = await db.sow_proofs.find(
        {"entity_type": entity_type.value, "entity_id": entity_id},
        {"_id": 0}
    ).sort("uploaded_at", -1).to_list(100)
    
    return {"proofs": proofs, "total": len(proofs)}


@router.delete("/proofs/{proof_id}")
async def delete_proof(
    proof_id: str,
    current_user: User = Depends(get_current_user)
):
    """Delete a proof"""
    if not can_manage_project_sow(current_user.role):
        raise HTTPException(status_code=403, detail="Only PM roles can delete proofs")
    
    db = get_db()
    
    result = await db.sow_proofs.delete_one({"id": proof_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Proof not found")
    
    return {"message": "Proof deleted"}


# ============== GOVERNANCE ==============

@router.get("/governance/check-duplicate")
async def check_duplicate_sow(
    title: str,
    domain: str,
    exclude_id: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """
    Check if SOW with same title + domain exists.
    Used before creating new SOW to prevent duplicates.
    """
    db = get_db()
    
    query = {
        "title": {"$regex": f"^{title}$", "$options": "i"},  # Case-insensitive
        "$or": [
            {"category": domain},
            {"domains": domain}
        ]
    }
    
    if exclude_id:
        query["id"] = {"$ne": exclude_id}
    
    existing = await db.enhanced_sow.find_one(query, {"_id": 0, "id": 1, "title": 1})
    
    if existing:
        return {
            "duplicate_found": True,
            "existing_sow_id": existing.get("id"),
            "message": f"SOW with title '{title}' in domain '{domain}' already exists. Consider reusing."
        }
    
    return {"duplicate_found": False}


@router.get("/governance/sow-master/{sow_id}/is-locked")
async def check_sow_locked(
    sow_id: str,
    current_user: User = Depends(get_current_user)
):
    """Check if SOW_MASTER is locked"""
    db = get_db()
    
    sow = await db.enhanced_sow.find_one({"id": sow_id}, {"_id": 0, "is_locked": 1, "consulting_kickoff_complete": 1})
    if not sow:
        raise HTTPException(status_code=404, detail="SOW not found")
    
    is_locked = sow.get("is_locked", False) or sow.get("consulting_kickoff_complete", False)
    
    return {
        "is_locked": is_locked,
        "can_edit": not is_locked
    }
