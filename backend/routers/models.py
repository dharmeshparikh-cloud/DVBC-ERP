"""
Shared Pydantic models used across multiple routers.
"""

from pydantic import BaseModel, Field, EmailStr, ConfigDict
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import uuid


class UserRole(str):
    """User role constants."""
    ADMIN = "admin"
    MANAGER = "manager"
    EXECUTIVE = "executive"
    CONSULTANT = "consultant"
    PRINCIPAL_CONSULTANT = "principal_consultant"
    LEAN_CONSULTANT = "lean_consultant"
    LEAD_CONSULTANT = "lead_consultant"
    SENIOR_CONSULTANT = "senior_consultant"
    HR_EXECUTIVE = "hr_executive"
    HR_MANAGER = "hr_manager"
    SALES_MANAGER = "sales_manager"
    SUBJECT_MATTER_EXPERT = "subject_matter_expert"


class MeetingMode(str):
    ONLINE = "online"
    OFFLINE = "offline"
    TELE_CALL = "tele_call"
    MIXED = "mixed"


class ProjectType(str):
    ONLINE = "online"
    OFFLINE = "offline"
    MIXED = "mixed"


class LeadStatus(str):
    NEW = "new"
    CONTACTED = "contacted"
    QUALIFIED = "qualified"
    PROPOSAL = "proposal"
    AGREEMENT = "agreement"
    CLOSED = "closed"
    LOST = "lost"


# Default roles list (project_manager removed - use principal_consultant instead)
DEFAULT_ROLES = [
    {"id": "admin", "name": "Admin", "description": "Full system access", "is_system_role": True, "can_delete": False},
    {"id": "consultant", "name": "Consultant", "description": "View SOW, update progress/status", "is_system_role": True, "can_delete": False},
    {"id": "lean_consultant", "name": "Lean Consultant", "description": "Junior consultant role", "is_system_role": False, "can_delete": True},
    {"id": "lead_consultant", "name": "Lead Consultant", "description": "Lead consultant with team oversight", "is_system_role": False, "can_delete": True},
    {"id": "senior_consultant", "name": "Senior Consultant", "description": "Senior consultant - can approve SOW and manage projects", "is_system_role": True, "can_delete": False},
    {"id": "principal_consultant", "name": "Principal Consultant", "description": "Principal consultant - full project authority, freeze SOW, approve kickoffs", "is_system_role": True, "can_delete": False},
    {"id": "hr_executive", "name": "HR Executive", "description": "HR team member", "is_system_role": False, "can_delete": True},
    {"id": "hr_manager", "name": "HR Manager", "description": "HR team manager", "is_system_role": False, "can_delete": True},
    {"id": "sales_manager", "name": "Sales Manager", "description": "Handles client accounts and sales", "is_system_role": False, "can_delete": True},
    {"id": "subject_matter_expert", "name": "Subject Matter Expert", "description": "Domain expert for consulting", "is_system_role": False, "can_delete": True},
    {"id": "manager", "name": "Manager", "description": "View/Download access, approve agreements", "is_system_role": True, "can_delete": False},
    {"id": "executive", "name": "Executive", "description": "Sales team - create leads, SOW, quotations", "is_system_role": True, "can_delete": False},
]

# Role categories for SOW access control
SALES_ROLES = ["admin", "executive", "sales_manager"]
CONSULTING_ROLES = ["consultant", "lean_consultant", "lead_consultant", "senior_consultant", "principal_consultant", "subject_matter_expert"]
PM_ROLES = ["admin", "principal_consultant", "senior_consultant", "manager"]

# Meeting role access constants
SALES_MEETING_ROLES = ["admin", "executive", "sales_manager"]
CONSULTING_MEETING_ROLES = ["admin", "consultant", "principal_consultant",
    "lean_consultant", "lead_consultant", "senior_consultant", "subject_matter_expert", "manager"]

# Roles that can see all department data
ALL_DATA_ACCESS_ROLES = ["admin", "hr_manager", "principal_consultant"]

# Consultant bandwidth limits
CONSULTANT_BANDWIDTH_LIMITS = {
    "online": 12,
    "offline": 6,
    "mixed": 8
}


class User(BaseModel):
    """User model for authentication and authorization."""
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: EmailStr
    full_name: str
    role: str
    department: Optional[str] = None
    reporting_manager_id: Optional[str] = None
    designation: Optional[str] = None
    is_active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    role: Optional[str] = None
    department: Optional[str] = None


class UserLogin(BaseModel):
    employee_id: Optional[str] = None  # New: Login with Employee ID
    email: Optional[EmailStr] = None   # Legacy: Login with email (backward compatible)
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str
    user: User


class Lead(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    lead_owner: Optional[str] = None
    first_name: str
    last_name: str
    company: str
    contact_person: Optional[str] = None
    job_title: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    linkedin_url: Optional[str] = None
    street: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    country: Optional[str] = None
    lead_source: Optional[str] = None
    status: str = LeadStatus.NEW
    sales_status: Optional[str] = None
    product_interest: Optional[str] = None
    source: Optional[str] = None
    notes: Optional[str] = None
    assigned_to: Optional[str] = None
    created_by: str
    lead_score: Optional[int] = 0
    score_breakdown: Optional[dict] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    enriched_at: Optional[datetime] = None


class LeadCreate(BaseModel):
    lead_owner: Optional[str] = None
    first_name: str
    last_name: str
    company: str
    contact_person: Optional[str] = None
    job_title: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    linkedin_url: Optional[str] = None
    street: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    country: Optional[str] = None
    lead_source: Optional[str] = None
    status: Optional[str] = LeadStatus.NEW
    sales_status: Optional[str] = None
    product_interest: Optional[str] = None
    source: Optional[str] = None
    notes: Optional[str] = None
    assigned_to: Optional[str] = None


class LeadUpdate(BaseModel):
    lead_owner: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    company: Optional[str] = None
    contact_person: Optional[str] = None
    job_title: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    linkedin_url: Optional[str] = None
    street: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    country: Optional[str] = None
    lead_source: Optional[str] = None
    status: Optional[str] = None
    sales_status: Optional[str] = None
    product_interest: Optional[str] = None
    source: Optional[str] = None
    notes: Optional[str] = None
    assigned_to: Optional[str] = None


class Project(BaseModel):
    """
    Project model with Optional fields to handle legacy data.
    Fields that may be missing in older documents are Optional with defaults.
    Note: Some legacy records use 'project_name' instead of 'name'.
    """
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: Optional[str] = None  # Some legacy records use 'project_name' instead
    project_name: Optional[str] = None  # Legacy field alias
    client_name: Optional[str] = None  # May be missing in some legacy records
    client_id: Optional[str] = None  # Legacy field
    lead_id: Optional[str] = None
    agreement_id: Optional[str] = None
    kickoff_request_id: Optional[str] = None  # Legacy field
    project_type: Optional[str] = "mixed"
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    status: Optional[str] = "active"
    tenure_months: Optional[int] = None  # Legacy field
    meeting_frequency: Optional[str] = None  # Legacy field
    total_meetings: Optional[int] = None  # Legacy field
    total_meetings_committed: Optional[int] = 0
    total_meetings_delivered: Optional[int] = 0
    number_of_visits: Optional[int] = 0
    assigned_consultants: Optional[List[str]] = []
    assigned_team: Optional[List[str]] = []
    project_manager_id: Optional[str] = None  # Legacy field
    project_manager_name: Optional[str] = None  # Legacy field
    sow_items: Optional[List[Dict[str, Any]]] = []  # Legacy field
    sow_id: Optional[str] = None  # Legacy field
    team_deployment: Optional[List[Dict[str, Any]]] = []  # Legacy field
    contract_value: Optional[float] = None  # Legacy field
    budget: Optional[float] = None
    project_value: Optional[float] = None
    pricing_plan_id: Optional[str] = None
    notes: Optional[str] = None
    created_by: Optional[str] = None  # Optional for legacy data compatibility
    created_at: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc))
    approved_by: Optional[str] = None  # Legacy field
    approved_by_name: Optional[str] = None  # Legacy field


class ProjectCreate(BaseModel):
    name: str
    client_name: str
    lead_id: Optional[str] = None
    agreement_id: Optional[str] = None
    project_type: Optional[str] = "mixed"
    start_date: datetime
    end_date: Optional[datetime] = None
    total_meetings_committed: Optional[int] = 0
    assigned_consultants: Optional[List[str]] = []
    assigned_team: Optional[List[str]] = []
    budget: Optional[float] = None
    project_value: Optional[float] = None
    notes: Optional[str] = None


class Meeting(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: str = "consulting"
    project_id: Optional[str] = None
    client_id: Optional[str] = None
    lead_id: Optional[str] = None
    sow_id: Optional[str] = None
    meeting_date: datetime
    mode: str
    attendees: List[str] = []
    attendee_names: List[str] = []
    duration_minutes: Optional[int] = None
    notes: Optional[str] = None
    is_delivered: bool = False
    title: Optional[str] = None
    agenda: Optional[List[str]] = []
    discussion_points: Optional[List[str]] = []
    decisions_made: Optional[List[str]] = []
    action_items: Optional[List[Dict[str, Any]]] = []
    next_meeting_date: Optional[datetime] = None
    mom_generated: bool = False
    mom_sent_to_client: bool = False
    mom_sent_at: Optional[datetime] = None
    created_by: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class MeetingCreate(BaseModel):
    type: str = "consulting"
    project_id: Optional[str] = None
    client_id: Optional[str] = None
    lead_id: Optional[str] = None
    sow_id: Optional[str] = None
    meeting_date: datetime
    mode: str
    attendees: Optional[List[str]] = []
    attendee_names: Optional[List[str]] = []
    duration_minutes: Optional[int] = None
    notes: Optional[str] = None
    is_delivered: bool = False
    title: Optional[str] = None
    agenda: Optional[List[str]] = []


class MOMCreate(BaseModel):
    """Minutes of Meeting creation/update"""
    title: Optional[str] = None
    agenda: Optional[List[str]] = []
    discussion_points: Optional[List[str]] = []
    decisions_made: Optional[List[str]] = []
    action_items: Optional[List[Dict[str, Any]]] = []
    next_meeting_date: Optional[datetime] = None


class ActionItemCreate(BaseModel):
    """Create action item with follow-up task"""
    description: str
    assigned_to_id: Optional[str] = None
    due_date: Optional[datetime] = None
    priority: str = "medium"
    create_follow_up_task: bool = True
    notify_reporting_manager: bool = True


class SalesTarget(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    month: int
    year: int
    meeting_target: int = 0
    conversion_target: int = 0
    deal_value_target: float = 0.0
    set_by: str
    approved_by: Optional[str] = None
    approval_status: str = "pending"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = None


class SalesTargetCreate(BaseModel):
    user_id: str
    month: int
    year: int
    meeting_target: int = 0
    conversion_target: int = 0
    deal_value_target: float = 0.0


class PerformanceReview(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    reviewer_id: str
    month: int
    year: int
    meeting_quality_score: Optional[float] = None
    conversion_rate_score: Optional[float] = None
    response_time_score: Optional[float] = None
    mom_quality_score: Optional[float] = None
    target_achievement_score: Optional[float] = None
    overall_score: Optional[float] = None
    comments: Optional[str] = None
    review_date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    status: str = "draft"


class PerformanceReviewCreate(BaseModel):
    user_id: str
    month: int
    year: int
    meeting_quality_score: Optional[float] = None
    conversion_rate_score: Optional[float] = None
    response_time_score: Optional[float] = None
    mom_quality_score: Optional[float] = None
    target_achievement_score: Optional[float] = None
    comments: Optional[str] = None


class KickoffRequest(BaseModel):
    """Request from Sales team to Project Manager for project kickoff"""
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    agreement_id: str
    lead_id: Optional[str] = None
    client_id: Optional[str] = None
    client_name: str
    project_name: str
    project_type: str = "mixed"
    total_meetings: int = 0
    meeting_frequency: str = "Monthly"
    project_tenure_months: int = 12
    project_value: Optional[float] = None
    expected_start_date: Optional[datetime] = None
    assigned_pm_id: Optional[str] = None
    assigned_pm_name: Optional[str] = None
    status: str = "pending"
    notes: Optional[str] = None
    requested_by: str
    requested_by_name: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    accepted_at: Optional[datetime] = None
    project_id: Optional[str] = None
    return_reason: Optional[str] = None
    return_notes: Optional[str] = None
    returned_by: Optional[str] = None
    returned_by_name: Optional[str] = None
    returned_at: Optional[datetime] = None


class KickoffRequestCreate(BaseModel):
    agreement_id: str
    lead_id: Optional[str] = None
    client_id: Optional[str] = None
    client_name: str
    project_name: str
    project_type: Optional[str] = "mixed"
    total_meetings: Optional[int] = 0
    meeting_frequency: Optional[str] = "Monthly"
    project_tenure_months: Optional[int] = 12
    project_value: Optional[float] = None
    expected_start_date: Optional[datetime] = None
    assigned_pm_id: Optional[str] = None
    assigned_pm_name: Optional[str] = None
    notes: Optional[str] = None


class KickoffRequestUpdate(BaseModel):
    project_name: Optional[str] = None
    project_type: Optional[str] = None
    total_meetings: Optional[int] = None
    meeting_frequency: Optional[str] = None
    project_tenure_months: Optional[int] = None
    expected_start_date: Optional[datetime] = None
    assigned_pm_id: Optional[str] = None
    assigned_pm_name: Optional[str] = None
    notes: Optional[str] = None


class KickoffReturnRequest(BaseModel):
    return_reason: str
    return_notes: Optional[str] = None


class PaymentVerification(BaseModel):
    """Payment verification model for first installment validation"""
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    agreement_id: str
    pricing_plan_id: Optional[str] = None
    installment_number: int = 1
    expected_amount: float
    received_amount: float
    transaction_id: str
    payment_date: datetime
    payment_mode: str = "bank_transfer"  # bank_transfer, cheque, upi, cash
    bank_reference: Optional[str] = None
    verified_by: str
    verified_by_name: Optional[str] = None
    verified_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    notes: Optional[str] = None
    status: str = "verified"  # verified, pending, disputed
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PaymentVerificationCreate(BaseModel):
    agreement_id: str
    pricing_plan_id: Optional[str] = None
    installment_number: int = 1
    expected_amount: float
    received_amount: float
    transaction_id: str
    payment_date: datetime
    payment_mode: str = "bank_transfer"
    bank_reference: Optional[str] = None
    notes: Optional[str] = None


class CTCComponent(BaseModel):
    """Individual CTC component with calculation method"""
    key: str
    name: str
    calc_type: str
    value: float = 0
    annual: float = 0
    monthly: float = 0
    is_taxable: bool = True
    is_optional: bool = False
    vesting_months: Optional[int] = None


class CTCStructureRequest(BaseModel):
    """CTC Structure design request from HR"""
    employee_id: str
    annual_ctc: float
    effective_month: str
    component_config: Optional[list] = None
    retention_bonus: Optional[float] = 0
    retention_vesting_months: int = 12
    remarks: Optional[str] = None


class CTCStructure(BaseModel):
    """Employee CTC Structure with approval workflow"""
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    employee_id: str
    annual_ctc: float
    effective_month: str
    components: dict
    retention_bonus: float = 0
    retention_vesting_months: int = 12
    status: str = "pending"
    created_by: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    remarks: Optional[str] = None
    version: int = 1


class ConsultantAssignment(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    consultant_id: str
    project_id: str
    assigned_date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    assigned_by: str
    role_in_project: Optional[str] = "consultant"
    meetings_committed: int = 0
    meetings_completed: int = 0
    is_active: bool = True
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ConsultantAssignmentCreate(BaseModel):
    consultant_id: str
    project_id: str
    role_in_project: Optional[str] = "consultant"
    meetings_committed: Optional[int] = 0
    notes: Optional[str] = None


class ConsultantProfile(BaseModel):
    """Extended profile for consultant users"""
    model_config = ConfigDict(extra="ignore")
    user_id: str
    specializations: List[str] = []
    preferred_mode: str = "mixed"
    max_projects: int = 8
    current_project_count: int = 0
    total_project_value: float = 0
    bio: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ReviewParameter(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: Optional[str] = None
    weight: float = 1.0
    is_active: bool = True
    created_by: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class TravelReimbursement(BaseModel):
    """Travel reimbursement request model."""
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    employee_id: str
    employee_name: Optional[str] = None
    travel_date: datetime
    from_location: str
    from_coordinates: Optional[Dict[str, float]] = None
    to_location: str
    to_coordinates: Optional[Dict[str, float]] = None
    distance_km: float
    vehicle_type: str  # 'car' or 'two_wheeler'
    rate_per_km: float
    is_round_trip: bool = False
    calculated_amount: float
    purpose: Optional[str] = None
    attendance_id: Optional[str] = None
    status: str = "pending"
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    converted_to_expense: bool = False
    expense_id: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ReportRequest(BaseModel):
    """Report generation request."""
    report_id: str
    format: str = "excel"
    filters: Optional[Dict[str, Any]] = None
    date_range: Optional[Dict[str, str]] = None
