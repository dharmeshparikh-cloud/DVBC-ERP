from pydantic import BaseModel, Field, EmailStr, ConfigDict
from typing import List, Optional
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
    category: str
    sub_category: Optional[str] = None
    description: str
    deliverables: List[str] = []

class PricingPlan(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    lead_id: str
    project_duration_type: str  # 'monthly', 'quarterly', 'half_yearly', 'yearly', 'custom'
    project_duration_months: int
    payment_schedule: str  # 'monthly', 'quarterly', 'milestone', 'upfront'
    consultants: List[ConsultantAllocation] = []
    sow_items: List[SOWItem] = []
    base_amount: float = 0
    discount_percentage: float = 0
    gst_percentage: float = 18
    total_amount: float = 0
    growth_consulting_plan: Optional[str] = None
    growth_guarantee: Optional[str] = None
    created_by: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class PricingPlanCreate(BaseModel):
    lead_id: str
    project_duration_type: str
    project_duration_months: int
    payment_schedule: str
    consultants: List[ConsultantAllocation] = []
    sow_items: List[SOWItem] = []
    discount_percentage: Optional[float] = 0
    growth_consulting_plan: Optional[str] = None
    growth_guarantee: Optional[str] = None

class Quotation(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    pricing_plan_id: str
    lead_id: str
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
    created_by: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class QuotationCreate(BaseModel):
    pricing_plan_id: str
    lead_id: str
    base_rate_per_meeting: Optional[float] = 12500
    notes: Optional[str] = None

class Agreement(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    quotation_id: str
    lead_id: str
    agreement_number: str
    agreement_type: str = 'standard'  # 'standard', 'nda', 'custom'
    payment_terms: str = 'Net 30 days'
    special_conditions: Optional[str] = None
    signed_date: Optional[datetime] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    status: str = 'pending_approval'  # 'pending_approval', 'approved', 'rejected', 'sent', 'signed'
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    terms_and_conditions: Optional[str] = None
    created_by: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class AgreementCreate(BaseModel):
    quotation_id: str
    lead_id: str
    agreement_type: Optional[str] = 'standard'
    payment_terms: Optional[str] = 'Net 30 days'
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