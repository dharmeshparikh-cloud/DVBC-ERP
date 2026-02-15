from pydantic import BaseModel, Field, EmailStr, ConfigDict
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import uuid

class CommunicationLog(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    lead_id: str
    communication_type: str  # 'call', 'email', 'sms', 'whatsapp'
    notes: Optional[str] = None
    outcome: Optional[str] = None
    created_by: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class CommunicationLogCreate(BaseModel):
    lead_id: str
    communication_type: str
    notes: Optional[str] = None
    outcome: Optional[str] = None

class ConsultantAllocation(BaseModel):
    consultant_type: str  # 'lead', 'lean', 'principal', 'hr', 'sales', 'project_manager', 'trainer'
    role: Optional[str] = None  # Full role name e.g., "Project Manager"
    meeting_type: Optional[str] = None  # e.g., "Weekly Review", "Monthly Review"
    tenure_type_code: Optional[str] = None  # e.g., "full_time", "weekly" - for top-down pricing
    frequency: Optional[str] = None  # e.g., "5 per week", "1 per month"
    mode: Optional[str] = "Online"  # Online, Offline, Mixed
    count: int = 1
    meetings: int = 0
    hours: int = 0
    rate_per_meeting: Optional[float] = 12500
    committed_meetings: Optional[int] = 0  # Auto-calculated based on frequency and duration
    allocation_percentage: Optional[float] = 0  # TOP-DOWN: Percentage of total investment
    breakup_amount: Optional[float] = 0  # TOP-DOWN: Allocated amount for this consultant

class SOWItemStatus(str):
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"

class SOWDocument(BaseModel):
    """Document attached to SOW"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    filename: str
    original_filename: str
    file_type: str
    file_size: int
    uploaded_by: str
    uploaded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    description: Optional[str] = None

class SOWItem(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    category: str  # sales, hr, operations, training, analytics, digital_marketing
    sub_category: Optional[str] = None
    title: str = ""
    description: str = ""
    deliverables: List[str] = []
    timeline_weeks: Optional[int] = None
    start_week: Optional[int] = None  # For roadmap positioning
    order: int = 0
    # New fields for status tracking
    status: str = SOWItemStatus.DRAFT  # draft, pending_review, approved, rejected, in_progress, completed
    status_updated_by: Optional[str] = None
    status_updated_at: Optional[datetime] = None
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    documents: List[SOWDocument] = []
    notes: Optional[str] = None
    # Consultant assignment
    assigned_consultant_id: Optional[str] = None
    assigned_consultant_name: Optional[str] = None
    # Backend support team (optional)
    has_backend_support: bool = False
    backend_support_id: Optional[str] = None
    backend_support_name: Optional[str] = None
    backend_support_role: Optional[str] = None  # e.g., "Developer", "Designer", "QA"

class SOWVersion(BaseModel):
    """Version history for SOW changes"""
    version: int
    changed_by: str
    changed_at: datetime
    change_type: str  # 'created', 'updated', 'item_added', 'item_updated', 'status_changed', 'document_added'
    changes: Dict[str, Any] = {}  # What was changed
    snapshot: List[Dict] = []  # Full SOW items at this version

class SOWOverallStatus(str):
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    PARTIALLY_APPROVED = "partially_approved"
    APPROVED = "approved"
    COMPLETE = "complete"

class SOW(BaseModel):
    """Standalone SOW linked to Pricing Plan"""
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    pricing_plan_id: str
    lead_id: str
    items: List[SOWItem] = []
    documents: List[SOWDocument] = []  # SOW-level documents
    overall_status: str = SOWOverallStatus.DRAFT  # Overall SOW status
    current_version: int = 1
    version_history: List[SOWVersion] = []
    is_frozen: bool = False
    frozen_at: Optional[datetime] = None
    frozen_by: Optional[str] = None
    submitted_for_approval: bool = False
    submitted_at: Optional[datetime] = None
    submitted_by: Optional[str] = None
    final_approved_by: Optional[str] = None
    final_approved_at: Optional[datetime] = None
    created_by: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class SOWCreate(BaseModel):
    pricing_plan_id: str
    lead_id: str
    items: Optional[List[Dict]] = []

class SOWItemCreate(BaseModel):
    category: str
    sub_category: Optional[str] = None
    title: str
    description: Optional[str] = ""
    deliverables: Optional[List[str]] = []
    timeline_weeks: Optional[int] = None
    start_week: Optional[int] = None
    order: Optional[int] = 0
    status: Optional[str] = SOWItemStatus.DRAFT
    notes: Optional[str] = None
    assigned_consultant_id: Optional[str] = None
    assigned_consultant_name: Optional[str] = None
    has_backend_support: Optional[bool] = False
    backend_support_id: Optional[str] = None
    backend_support_name: Optional[str] = None
    backend_support_role: Optional[str] = None

class SOWItemStatusUpdate(BaseModel):
    status: str
    rejection_reason: Optional[str] = None
    notes: Optional[str] = None

class PricingPlan(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    lead_id: str
    project_duration_type: str  # 'monthly', 'quarterly', 'half_yearly', 'yearly', 'custom'
    project_duration_months: int
    payment_schedule: str  # 'monthly', 'quarterly', 'milestone', 'upfront'
    consultants: List[ConsultantAllocation] = []
    team_deployment: List[Dict[str, Any]] = []  # Full team deployment data with allocation
    sow_id: Optional[str] = None  # Link to SOW
    total_investment: float = 0  # TOP-DOWN: Primary input from salesperson
    base_amount: float = 0
    discount_percentage: float = 0
    gst_percentage: float = 18
    total_amount: float = 0
    growth_consulting_plan: Optional[str] = None
    growth_guarantee: Optional[str] = None
    is_active: bool = True  # Soft delete flag
    created_by: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class PricingPlanCreate(BaseModel):
    lead_id: str
    project_duration_type: str
    project_duration_months: int
    payment_schedule: str
    consultants: List[ConsultantAllocation] = []
    team_deployment: Optional[List[Dict[str, Any]]] = []  # Full team deployment data with allocation
    total_investment: Optional[float] = 0  # TOP-DOWN: Primary input
    discount_percentage: Optional[float] = 0
    growth_consulting_plan: Optional[str] = None
    growth_guarantee: Optional[str] = None

class Quotation(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    pricing_plan_id: str
    lead_id: str
    sow_id: Optional[str] = None  # Link to SOW
    quotation_number: str
    version: int = 1
    is_final: bool = False
    status: str = 'draft'  # 'draft', 'sent', 'accepted', 'rejected', 'revised'
    base_rate_per_meeting: float = 12500
    total_meetings: int = 0
    subtotal: float = 0
    discount_amount: float = 0
    gst_amount: float = 0
    grand_total: float = 0
    notes: Optional[str] = None
    is_active: bool = True  # Soft delete flag
    created_by: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class QuotationCreate(BaseModel):
    pricing_plan_id: str
    lead_id: str
    sow_id: Optional[str] = None
    base_rate_per_meeting: Optional[float] = 12500
    notes: Optional[str] = None

# Agreement Sections for structured agreement document
class AgreementSection(BaseModel):
    section_type: str  # party_info, confidentiality, nda, nca, renewal, conveyance, sow, project_details, team, pricing, payment_terms, signature
    title: str
    content: str = ""
    order: int = 0
    is_required: bool = True

class TeamDeploymentMember(BaseModel):
    """Team member deployment structure for agreement"""
    role: str  # e.g., "Project Manager", "Data Analyst", "Digital Marketing Manager"
    meeting_type: str  # e.g., "Monthly Review", "Online Review", "On-site Visit"
    frequency: str  # e.g., "1 per month", "2 per week", "As needed"
    mode: str = "online"  # online, offline, mixed
    base_rate_per_meeting: float = 12500  # Rate per meeting in INR
    committed_meetings: int = 0  # Auto-calculated based on frequency and tenure
    notes: Optional[str] = None


class Agreement(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    quotation_id: str
    lead_id: str
    sow_id: Optional[str] = None  # Link to SOW
    pricing_plan_id: Optional[str] = None
    agreement_number: str
    agreement_type: str = 'standard'  # 'standard', 'nda', 'custom'
    
    # Agreement Sections
    party_name: str = ""
    company_section: str = "Agreement between D&V Business Consulting and Client"
    confidentiality_clause: str = ""
    nda_clause: str = ""
    nca_clause: str = ""
    renewal_clause: str = ""
    conveyance_clause: str = ""
    project_start_date: Optional[datetime] = None
    project_duration_months: Optional[int] = None
    team_engagement: str = ""
    payment_terms: str = 'Net 30 days'
    payment_conditions: str = ""
    signature_section: str = ""
    
    # NEW: Team Deployment Structure (for consulting team visibility)
    meeting_frequency: str = "Monthly"  # Weekly, Bi-weekly, Monthly, Quarterly
    project_tenure_months: int = 12  # Project duration in months
    team_deployment: List[Dict[str, Any]] = []  # List of TeamDeploymentMember as dicts
    
    # Structured sections for export
    sections: List[AgreementSection] = []
    
    special_conditions: Optional[str] = None
    signed_date: Optional[datetime] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    status: str = 'pending_approval'  # 'pending_approval', 'approved', 'rejected', 'sent', 'signed'
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    terms_and_conditions: Optional[str] = None
    
    is_active: bool = True  # Soft delete flag
    created_by: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class AgreementCreate(BaseModel):
    quotation_id: str
    lead_id: str
    sow_id: Optional[str] = None
    pricing_plan_id: Optional[str] = None
    agreement_type: Optional[str] = 'standard'
    party_name: Optional[str] = ""
    confidentiality_clause: Optional[str] = ""
    nda_clause: Optional[str] = ""
    nca_clause: Optional[str] = ""
    renewal_clause: Optional[str] = ""
    conveyance_clause: Optional[str] = ""
    project_start_date: Optional[datetime] = None
    project_duration_months: Optional[int] = None
    team_engagement: Optional[str] = ""
    payment_terms: Optional[str] = 'Net 30 days'
    payment_conditions: Optional[str] = ""
    special_conditions: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    terms_and_conditions: Optional[str] = None
    # NEW: Team Deployment fields
    meeting_frequency: Optional[str] = "Monthly"
    project_tenure_months: Optional[int] = 12
    team_deployment: Optional[List[Dict[str, Any]]] = []

def calculate_quotation_totals(consultants: List[ConsultantAllocation], discount_percentage: float, gst_percentage: float, base_rate: float) -> dict:
    """Calculate quotation totals based on consultants and pricing"""
    total_meetings = sum(c.meetings for c in consultants)
    
    # Calculate base amount (meetings * rate per meeting)
    subtotal = sum(c.meetings * (c.rate_per_meeting or base_rate) for c in consultants)
    
    # Apply discount
    discount_amount = subtotal * (discount_percentage / 100)
    amount_after_discount = subtotal - discount_amount
    
    # Apply GST
    gst_amount = amount_after_discount * (gst_percentage / 100)
    grand_total = amount_after_discount + gst_amount
    
    return {
        'total_meetings': total_meetings,
        'subtotal': round(subtotal, 2),
        'discount_amount': round(discount_amount, 2),
        'gst_amount': round(gst_amount, 2),
        'grand_total': round(grand_total, 2)
    }

# Default agreement section templates
DEFAULT_AGREEMENT_SECTIONS = [
    {"section_type": "party_info", "title": "Party Information", "order": 1, "is_required": True},
    {"section_type": "company_section", "title": "Agreement Between Parties", "order": 2, "is_required": True},
    {"section_type": "confidentiality", "title": "Confidentiality", "order": 3, "is_required": True},
    {"section_type": "nda", "title": "Non-Disclosure Agreement (NDA)", "order": 4, "is_required": True},
    {"section_type": "nca", "title": "Non-Compete Agreement (NCA)", "order": 5, "is_required": False},
    {"section_type": "renewal", "title": "Renewal Terms", "order": 6, "is_required": False},
    {"section_type": "conveyance", "title": "Conveyance", "order": 7, "is_required": False},
    {"section_type": "sow", "title": "Scope of Work", "order": 8, "is_required": True},
    {"section_type": "project_details", "title": "Project Details", "order": 9, "is_required": True},
    {"section_type": "team", "title": "Team Engagement", "order": 10, "is_required": True},
    {"section_type": "pricing", "title": "Pricing Plan", "order": 11, "is_required": True},
    {"section_type": "payment_terms", "title": "Payment Terms & Conditions", "order": 12, "is_required": True},
    {"section_type": "signature", "title": "Signatures", "order": 13, "is_required": True},
]