"""
Enhanced SOW Models for Role-Based Workflow

This module extends the SOW system with:
1. Sales Team: Simple scope selection from master
2. Consulting Team: Detailed progress tracking with Gantt/Kanban
3. Roadmap approval workflow with client consent
4. Change tracking to avoid internal conflicts
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from enum import Enum
import uuid


# ============== Enums ==============

class ScopeStatus(str, Enum):
    """Status for scope items"""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    NOT_APPLICABLE = "not_applicable"


class ScopeSource(str, Enum):
    """Source of scope - original from sales or added by consulting"""
    SALES_ORIGINAL = "sales_original"  # From sales team's original selection
    CONSULTING_ADDED = "consulting_added"  # Added by consulting team
    SALES_CUSTOM = "sales_custom"  # Custom scope added by sales


class ScopeRevisionStatus(str, Enum):
    """Status of scope after consulting review"""
    PENDING_REVIEW = "pending_review"  # Not yet reviewed by consulting
    CONFIRMED = "confirmed"  # Scope is accurate, proceed
    REVISED = "revised"  # Scope needs adjustment (requires reason + client consent)
    NOT_APPLICABLE = "not_applicable"  # Scope not relevant (requires reason)


class RoadmapApprovalStatus(str, Enum):
    """Status of roadmap approval"""
    DRAFT = "draft"
    PENDING_CLIENT_APPROVAL = "pending_client_approval"
    APPROVED = "approved"
    REVISION_REQUESTED = "revision_requested"


class ApprovalCycle(str, Enum):
    """Approval cycle type"""
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


# ============== Enhanced Scope Item ==============

class ScopeAttachment(BaseModel):
    """Attachment for scope item"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    filename: str
    original_filename: str
    file_type: str
    file_size: int
    uploaded_by: str
    uploaded_by_name: Optional[str] = None
    uploaded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    description: Optional[str] = None


class ScopeChangeLog(BaseModel):
    """Change log entry for a scope item"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    changed_by: str
    changed_by_name: str
    changed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    change_type: str  # status_update, progress_update, revision, notes_added, attachment_added
    old_value: Optional[Dict[str, Any]] = None
    new_value: Optional[Dict[str, Any]] = None
    reason: Optional[str] = None  # Mandatory for revisions
    client_consent: bool = False  # Whether client approved this change


class EnhancedScopeItem(BaseModel):
    """Enhanced scope item with full tracking"""
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    
    # Basic Info (from master or custom)
    scope_template_id: Optional[str] = None  # Reference to SOWScopeTemplate
    category_id: str
    category_code: str
    category_name: str
    name: str
    description: Optional[str] = None
    
    # Source tracking
    source: str = ScopeSource.SALES_ORIGINAL
    added_by: str
    added_by_name: str
    added_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Consulting review status
    revision_status: str = ScopeRevisionStatus.PENDING_REVIEW
    revision_reason: Optional[str] = None
    revision_by: Optional[str] = None
    revision_by_name: Optional[str] = None
    revision_at: Optional[datetime] = None
    client_consent_for_revision: bool = False
    client_consent_document: Optional[str] = None  # Document/email reference
    
    # Progress tracking (Consulting team)
    status: str = ScopeStatus.NOT_STARTED
    progress_percentage: float = 0  # 0-100
    days_spent: int = 0
    meetings_count: int = 0
    notes: Optional[str] = None
    
    # Timeline
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    timeline_weeks: Optional[int] = None
    
    # Assignments
    assigned_consultant_id: Optional[str] = None
    assigned_consultant_name: Optional[str] = None
    
    # Attachments & Change Log
    attachments: List[ScopeAttachment] = []
    change_log: List[ScopeChangeLog] = []
    
    # Timestamps
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ============== Original Scope Snapshot ==============

class OriginalScopeSnapshot(BaseModel):
    """Locked snapshot of original scopes from sales - never editable"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    scopes: List[Dict[str, Any]] = []  # Copy of original scope items
    created_by: str
    created_by_name: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    locked: bool = True  # Always true


# ============== Roadmap & Approval ==============

class RoadmapVersion(BaseModel):
    """Version of the roadmap for approval tracking"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    version: int
    approval_cycle: str = ApprovalCycle.MONTHLY
    period_label: str  # e.g., "January 2026", "Q1 2026", "2026"
    
    # Scope snapshot at this version
    scopes_snapshot: List[Dict[str, Any]] = []
    
    # Approval status
    status: str = RoadmapApprovalStatus.DRAFT
    
    # Submission
    submitted_by: Optional[str] = None
    submitted_by_name: Optional[str] = None
    submitted_at: Optional[datetime] = None
    
    # Client response
    client_response: Optional[str] = None  # approved, revision_requested
    client_response_notes: Optional[str] = None
    client_response_at: Optional[datetime] = None
    client_consent_document_id: Optional[str] = None  # Email/document upload reference
    
    # If approved
    approved_at: Optional[datetime] = None
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ClientConsentDocument(BaseModel):
    """Document storing client consent (email screenshot, signed doc, etc.)"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    filename: str
    original_filename: str
    file_type: str
    file_size: int
    consent_type: str  # email, document, verbal_noted
    consent_for: str  # scope_revision, roadmap_approval
    related_item_id: Optional[str] = None  # Scope or roadmap version ID
    uploaded_by: str
    uploaded_by_name: str
    uploaded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    notes: Optional[str] = None


# ============== Enhanced SOW ==============

class EnhancedSOW(BaseModel):
    """Enhanced SOW with role-based workflow"""
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    pricing_plan_id: str
    lead_id: str
    project_id: Optional[str] = None  # Linked after kickoff
    
    # Original snapshot from sales (locked)
    original_scope_snapshot: Optional[OriginalScopeSnapshot] = None
    
    # Current scopes (editable by consulting)
    scopes: List[EnhancedScopeItem] = []
    
    # Roadmap versions for approval
    roadmap_versions: List[RoadmapVersion] = []
    current_approved_roadmap_version: Optional[int] = None
    
    # Client consent documents
    consent_documents: List[ClientConsentDocument] = []
    
    # Status
    sales_handover_complete: bool = False
    sales_handover_at: Optional[datetime] = None
    consulting_kickoff_complete: bool = False
    consulting_kickoff_at: Optional[datetime] = None
    
    # Timestamps
    created_by: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ============== Request/Response Models ==============

class SalesScopeSelection(BaseModel):
    """Request model for sales team selecting scopes"""
    scope_template_ids: List[str] = []  # Selected from master
    custom_scopes: List[Dict[str, str]] = []  # Custom scopes: [{"name": "...", "category_id": "..."}]


class ConsultingScopeUpdate(BaseModel):
    """Request model for consulting team updating a scope"""
    status: Optional[str] = None
    progress_percentage: Optional[float] = None
    days_spent: Optional[int] = None
    meetings_count: Optional[int] = None
    notes: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    revision_status: Optional[str] = None
    revision_reason: Optional[str] = None
    client_consent_for_revision: Optional[bool] = None


class AddScopeRequest(BaseModel):
    """Request to add a new scope (consulting team)"""
    scope_template_id: Optional[str] = None  # From master
    category_id: str
    name: str
    description: Optional[str] = None
    timeline_weeks: Optional[int] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class RoadmapSubmitRequest(BaseModel):
    """Request to submit roadmap for client approval"""
    approval_cycle: str = ApprovalCycle.MONTHLY
    period_label: str
    notes: Optional[str] = None


class ClientApprovalResponse(BaseModel):
    """Client response to roadmap approval"""
    approved: bool
    notes: Optional[str] = None
    consent_document_id: Optional[str] = None  # Required if approved
