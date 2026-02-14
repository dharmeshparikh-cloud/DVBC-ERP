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
    count: int = 1
    meetings: int = 0
    hours: int = 0
    rate_per_meeting: Optional[float] = 12500

class SOWItem(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    category: str  # sales, hr, operations, training, analytics, digital_marketing
    sub_category: Optional[str] = None
    title: str = ""
    description: str = ""
    deliverables: List[str] = []
    timeline_weeks: Optional[int] = None
    order: int = 0

class SOWVersion(BaseModel):
    """Version history for SOW changes"""
    version: int
    changed_by: str
    changed_at: datetime
    change_type: str  # 'created', 'updated', 'item_added', 'item_updated'
    changes: Dict[str, Any] = {}  # What was changed
    snapshot: List[Dict] = []  # Full SOW items at this version

class SOW(BaseModel):
    """Standalone SOW linked to Pricing Plan"""
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    pricing_plan_id: str
    lead_id: str
    items: List[SOWItem] = []
    current_version: int = 1
    version_history: List[SOWVersion] = []
    is_frozen: bool = False
    frozen_at: Optional[datetime] = None
    frozen_by: Optional[str] = None
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
    order: Optional[int] = 0

class PricingPlan(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    lead_id: str
    project_duration_type: str  # 'monthly', 'quarterly', 'half_yearly', 'yearly', 'custom'
    project_duration_months: int
    payment_schedule: str  # 'monthly', 'quarterly', 'milestone', 'upfront'
    consultants: List[ConsultantAllocation] = []
    sow_id: Optional[str] = None  # Link to SOW
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