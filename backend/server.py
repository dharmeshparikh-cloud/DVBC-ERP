from fastapi import FastAPI, APIRouter, HTTPException, Depends, status, Response, Request
from fastapi.responses import FileResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
import os
import logging
import re
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr, ConfigDict
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
import uuid
import httpx
import random
import string
from email_templates import (
    EmailTemplate, EmailTemplateCreate, FollowUpReminder, FollowUpReminderCreate,
    generate_email_from_template, check_lead_for_suggestions
)
from sales_workflow import (
    CommunicationLog, CommunicationLogCreate,
    PricingPlan, PricingPlanCreate, ConsultantAllocation, SOWItem,
    Quotation, QuotationCreate, Agreement, AgreementCreate, AgreementSection,
    SOW, SOWCreate, SOWItemCreate, SOWVersion, SOWItemStatus, SOWOverallStatus,
    SOWDocument, SOWItemStatusUpdate, DEFAULT_AGREEMENT_SECTIONS,
    calculate_quotation_totals
)
from agreement_templates import (
    AgreementTemplate, AgreementTemplateCreate,
    EmailNotificationTemplate, EmailNotificationTemplateCreate,
    AgreementEmailData, substitute_variables, prepare_agreement_email_data,
    extract_variables_from_template, DEFAULT_AGREEMENT_EMAIL_TEMPLATES
)
from email_service import EmailService, create_mock_email_service
from reports import (
    REPORT_DEFINITIONS, get_report_data_functions,
    generate_excel, generate_pdf
)
from document_generator import AgreementDocumentGenerator, SOWDocumentGenerator
from routers import masters as masters_router
from routers import sow_masters as sow_masters_router
from routers import enhanced_sow as enhanced_sow_router
from routers import deps as router_deps
from routers import auth as auth_router
from routers import leads as leads_router
from routers import projects as projects_router
from routers import meetings as meetings_router
from routers import stats as stats_router
from routers import security as security_router
from routers import users as users_router
from routers import kickoff as kickoff_router
from routers import ctc as ctc_router
from routers import employees as employees_router
from routers import attendance as attendance_router
from routers import expenses as expenses_router
from routers import hr as hr_router
from routers import role_management as role_management_router
from routers import letters as letters_router
from routers import payments as payments_router
from routers import project_payments as project_payments_router
from routers import department_access as department_access_router
from routers import permission_config as permission_config_router

# Helper function to sanitize user input (prevent XSS)
def sanitize_text(text: str) -> str:
    """Remove HTML tags and dangerous characters from text."""
    if not text or not isinstance(text, str):
        return text
    # Remove HTML tags
    clean = re.sub(r'<[^>]*>', '', text)
    # Remove script-related keywords
    clean = re.sub(r'javascript:', '', clean, flags=re.IGNORECASE)
    clean = re.sub(r'onerror\s*=', '', clean, flags=re.IGNORECASE)
    clean = re.sub(r'onclick\s*=', '', clean, flags=re.IGNORECASE)
    return clean.strip()

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Initialize routers with database
masters_router.set_db(db)
sow_masters_router.set_db(db)
enhanced_sow_router.set_db(db)
router_deps.set_db(db)

app = FastAPI(title="Consulting Workflow Management API")
api_router = APIRouter(prefix="/api")

SECRET_KEY = os.environ.get('SECRET_KEY', 'your-secret-key-change-in-production')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 43200

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

# Google Auth Config
ALLOWED_DOMAIN = os.environ.get('ALLOWED_DOMAIN', 'dvconsulting.co.in')
EMERGENT_AUTH_URL = "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data"

class UserRole(str):
    ADMIN = "admin"
    MANAGER = "manager"
    EXECUTIVE = "executive"
    CONSULTANT = "consultant"
    PROJECT_MANAGER = "project_manager"
    PRINCIPAL_CONSULTANT = "principal_consultant"
    LEAN_CONSULTANT = "lean_consultant"
    LEAD_CONSULTANT = "lead_consultant"
    SENIOR_CONSULTANT = "senior_consultant"
    HR_EXECUTIVE = "hr_executive"
    HR_MANAGER = "hr_manager"
    ACCOUNT_MANAGER = "account_manager"
    SUBJECT_MATTER_EXPERT = "subject_matter_expert"

# Default roles list
DEFAULT_ROLES = [
    {"id": "admin", "name": "Admin", "description": "Full system access", "is_system_role": True, "can_delete": False},
    {"id": "consultant", "name": "Consultant", "description": "View SOW, update progress/status", "is_system_role": True, "can_delete": False},
    {"id": "lean_consultant", "name": "Lean Consultant", "description": "Junior consultant role", "is_system_role": False, "can_delete": True},
    {"id": "lead_consultant", "name": "Lead Consultant", "description": "Lead consultant with team oversight", "is_system_role": False, "can_delete": True},
    {"id": "senior_consultant", "name": "Senior Consultant", "description": "Senior consultant with advanced permissions", "is_system_role": False, "can_delete": True},
    {"id": "project_manager", "name": "Project Manager", "description": "Audit, approve, authorize SOW for client", "is_system_role": True, "can_delete": False},
    {"id": "principal_consultant", "name": "Principal Consultant", "description": "Principal consultant with freeze authority", "is_system_role": True, "can_delete": False},
    {"id": "hr_executive", "name": "HR Executive", "description": "HR team member", "is_system_role": False, "can_delete": True},
    {"id": "hr_manager", "name": "HR Manager", "description": "HR team manager", "is_system_role": False, "can_delete": True},
    {"id": "account_manager", "name": "Account Manager", "description": "Handles client accounts and sales", "is_system_role": False, "can_delete": True},
    {"id": "subject_matter_expert", "name": "Subject Matter Expert", "description": "Domain expert for consulting", "is_system_role": False, "can_delete": True},
    {"id": "manager", "name": "Manager", "description": "View/Download access, approve agreements", "is_system_role": True, "can_delete": False},
    {"id": "executive", "name": "Executive", "description": "Sales team - create leads, SOW, quotations", "is_system_role": True, "can_delete": False},
]

# Role categories for SOW access control
SALES_ROLES = ["admin", "executive", "account_manager"]  # Can create & edit SOW
CONSULTING_ROLES = ["consultant", "lean_consultant", "lead_consultant", "senior_consultant", "principal_consultant", "subject_matter_expert"]  # View SOW, update progress
PM_ROLES = ["admin", "project_manager", "manager"]  # Audit, approve, authorize

class MeetingMode(str):
    ONLINE = "online"
    OFFLINE = "offline"
    TELE_CALL = "tele_call"
    MIXED = "mixed"

class ProjectType(str):
    ONLINE = "online"
    OFFLINE = "offline"
    MIXED = "mixed"

# Consultant bandwidth limits
CONSULTANT_BANDWIDTH_LIMITS = {
    "online": 12,
    "offline": 6,
    "mixed": 8
}

class LeadStatus(str):
    NEW = "new"
    CONTACTED = "contacted"
    QUALIFIED = "qualified"
    PROPOSAL = "proposal"
    AGREEMENT = "agreement"
    CLOSED = "closed"
    LOST = "lost"

class User(BaseModel):
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

# Roles that can see all department data
ALL_DATA_ACCESS_ROLES = ["admin", "hr_manager", "principal_consultant"]

# Sales Performance Models
class SalesTarget(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    month: int  # 1-12
    year: int
    meeting_target: int = 0
    conversion_target: int = 0
    deal_value_target: float = 0.0
    set_by: str  # reporting manager id
    approved_by: Optional[str] = None  # principal consultant id
    approval_status: str = "pending"  # pending, approved, rejected
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
    meeting_quality_score: Optional[float] = None  # 1-5
    conversion_rate_score: Optional[float] = None  # 1-5
    response_time_score: Optional[float] = None  # 1-5
    mom_quality_score: Optional[float] = None  # 1-5
    target_achievement_score: Optional[float] = None  # 1-5
    overall_score: Optional[float] = None
    comments: Optional[str] = None
    review_date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    status: str = "draft"  # draft, submitted, acknowledged

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

class ReviewParameter(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: Optional[str] = None
    weight: float = 1.0  # Weight for overall score calculation
    is_active: bool = True
    created_by: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class CTCComponent(BaseModel):
    """Individual CTC component with calculation method"""
    key: str
    name: str
    calc_type: str  # "percentage_of_ctc", "percentage_of_basic", "fixed", "balance"
    value: float = 0  # percentage or fixed amount
    annual: float = 0
    monthly: float = 0
    is_taxable: bool = True
    is_optional: bool = False
    vesting_months: Optional[int] = None  # For retention bonus

class CTCStructureRequest(BaseModel):
    """CTC Structure design request from HR"""
    employee_id: str
    annual_ctc: float
    effective_month: str  # YYYY-MM format
    component_config: Optional[list] = None  # Custom component configuration
    retention_bonus: Optional[float] = 0  # Optional retention bonus
    retention_vesting_months: int = 12  # Default 1 year
    remarks: Optional[str] = None

class CTCStructure(BaseModel):
    """Employee CTC Structure with approval workflow"""
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    employee_id: str
    annual_ctc: float
    effective_month: str  # YYYY-MM - payroll month from which this applies
    components: dict  # Full breakdown
    retention_bonus: float = 0
    retention_vesting_months: int = 12
    status: str = "pending"  # pending, approved, rejected, active, superseded
    created_by: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    remarks: Optional[str] = None
    version: int = 1

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    role: Optional[str] = None
    department: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
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
    sales_status: Optional[str] = None  # 'not_interested', 'call_back', 'send_details', 'wrong_number', 'schedule_meeting', 'meeting_done'
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
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    client_name: str
    lead_id: Optional[str] = None
    agreement_id: Optional[str] = None
    project_type: str = "mixed"  # online, offline, mixed
    start_date: datetime
    end_date: Optional[datetime] = None
    status: str = "active"  # active, completed, on_hold, cancelled
    total_meetings_committed: int = 0
    total_meetings_delivered: int = 0
    number_of_visits: int = 0
    assigned_consultants: List[str] = []  # List of consultant user IDs
    assigned_team: List[str] = []
    budget: Optional[float] = None
    project_value: Optional[float] = None
    notes: Optional[str] = None
    created_by: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

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

class ConsultantAssignment(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    consultant_id: str
    project_id: str
    assigned_date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    assigned_by: str
    role_in_project: Optional[str] = "consultant"  # lead_consultant, consultant, support
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
    preferred_mode: str = "mixed"  # online, offline, mixed
    max_projects: int = 8
    current_project_count: int = 0
    total_project_value: float = 0
    bio: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# Kickoff Request Model - Sales to Consulting Handoff
class KickoffRequest(BaseModel):
    """Request from Sales team to Project Manager for project kickoff"""
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    agreement_id: str
    lead_id: Optional[str] = None
    client_id: Optional[str] = None
    client_name: str
    project_name: str
    project_type: str = "mixed"  # online, offline, mixed
    total_meetings: int = 0
    # Meeting and tenure fields (visible to consulting)
    meeting_frequency: str = "Monthly"  # Weekly, Bi-weekly, Monthly, Quarterly
    project_tenure_months: int = 12
    # Financial fields (hidden from consulting roles)
    project_value: Optional[float] = None  # Only visible to sales/admin
    expected_start_date: Optional[datetime] = None
    assigned_pm_id: Optional[str] = None  # Project Manager assigned
    assigned_pm_name: Optional[str] = None
    status: str = "pending"  # pending, accepted, rejected, converted, returned
    notes: Optional[str] = None
    requested_by: str
    requested_by_name: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    accepted_at: Optional[datetime] = None
    project_id: Optional[str] = None  # Set when converted to project
    # Return fields
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
    project_value: Optional[float] = None  # Optional, only for internal tracking
    expected_start_date: Optional[datetime] = None
    assigned_pm_id: Optional[str] = None
    assigned_pm_name: Optional[str] = None
    notes: Optional[str] = None

# Meeting role access constants
SALES_MEETING_ROLES = ["admin", "executive", "account_manager"]
CONSULTING_MEETING_ROLES = ["admin", "project_manager", "consultant", "principal_consultant",
    "lean_consultant", "lead_consultant", "senior_consultant", "subject_matter_expert", "manager"]

# =====================================================
# SIMPLIFIED PERMISSION SYSTEM
# =====================================================
# New system uses only:
# 1. Department → What pages user can access
# 2. Has Reportees → Auto-detected from reporting_manager_id for team permissions
# 3. is_view_only → Boolean flag for view-only users
# 4. Special Permissions → Admin/HR granted cross-department access
# =====================================================

# Admin users who can do everything
ADMIN_USERS = ["admin"]

# HR users who can manage employees
HR_USERS = ["admin", "hr_manager", "hr_executive"]

# Department to pages mapping
DEPARTMENT_PAGES = {
    "Sales": ["/dashboard", "/leads", "/clients", "/sales-meetings", "/quotations", "/pricing-plans",
              "/agreements", "/payment-verification", "/sales-funnel", "/sow", "/kickoff-requests"],
    "HR": ["/employees", "/onboarding", "/attendance", "/leave-mgmt", "/payroll", "/org-chart",
           "/letter-management", "/letterhead-settings", "/ctc-designer", "/attendance-approvals"],
    "Consulting": ["/consulting", "/my-projects", "/project-deliverables", "/consulting-meetings",
                   "/meeting-mom", "/project-payments", "/task-management"],
    "Finance": ["/finance", "/invoices", "/payments", "/expenses", "/reports"],
    "Admin": ["/admin-masters", "/department-access", "/user-management", "/system-settings"]
}

# My Workspace pages - available to ALL authenticated users
MY_WORKSPACE_PAGES = ["/my-attendance", "/my-leaves", "/my-salary-slips", "/my-expenses",
                      "/my-bank-details", "/mobile-app", "/change-password"]


async def get_user_departments(user_id: str) -> list:
    """Get all departments a user has access to (primary + special permissions)"""
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not user:
        return []
    
    departments = user.get("departments", [])
    if user.get("department") and user.get("department") not in departments:
        departments.append(user.get("department"))
    
    # Add special permission departments
    special = user.get("special_permissions", {})
    if special.get("extra_departments"):
        departments.extend(special.get("extra_departments", []))
    
    return list(set(departments))


async def has_reportees(user_id: str) -> bool:
    """Check if user has any employees reporting to them"""
    count = await db.employees.count_documents({"reporting_manager_id": user_id})
    return count > 0


async def get_reportee_ids(user_id: str) -> list:
    """Get list of employee IDs who report to this user"""
    employees = await db.employees.find(
        {"reporting_manager_id": user_id},
        {"id": 1, "user_id": 1, "_id": 0}
    ).to_list(1000)
    return [e.get("user_id") or e.get("id") for e in employees]


def is_admin_user(user) -> bool:
    """Check if user is an admin"""
    return user.role in ADMIN_USERS or user.department == "Admin"


def is_hr_user(user) -> bool:
    """Check if user is HR"""
    return user.role in HR_USERS or user.department == "HR"


def can_edit_data(user) -> bool:
    """Check if user can create/edit data (not view-only)"""
    # Admins and HR can always edit
    if is_admin_user(user) or is_hr_user(user):
        return True
    # Check view_only flag
    return not getattr(user, 'is_view_only', False)


async def can_edit_data_async(user) -> bool:
    """
    Async version - Check if user can create/edit data.
    Checks database for is_view_only flag.
    """
    # Admins and HR can always edit
    if is_admin_user(user) or is_hr_user(user):
        return True
    
    # Check database for view_only flag
    db_user = await db.users.find_one({"id": user.id}, {"is_view_only": 1, "_id": 0})
    if db_user and db_user.get("is_view_only", False):
        return False
    
    employee = await db.employees.find_one({"user_id": user.id}, {"is_view_only": 1, "_id": 0})
    if employee and employee.get("is_view_only", False):
        return False
    
    return True


def check_edit_permission(user):
    """
    Raises HTTPException if user cannot edit.
    Use this instead of role-based checks.
    """
    if not can_edit_data(user):
        raise HTTPException(
            status_code=403,
            detail="You have view-only access. Contact admin for edit permissions."
        )


async def can_access_employee_data(current_user, target_employee_id: str) -> bool:
    """
    Check if current user can access target employee's data.
    Rules:
    1. Admin/HR can access all
    2. User can access own data
    3. Manager can access reportees' data
    """
    if is_admin_user(current_user) or is_hr_user(current_user):
        return True
    
    # Own data
    if current_user.id == target_employee_id:
        return True
    
    # Check if target reports to current user
    reportee_ids = await get_reportee_ids(current_user.id)
    return target_employee_id in reportee_ids


async def get_accessible_employee_ids(current_user) -> list:
    """
    Get list of employee IDs the current user can access.
    Returns None if user can access all (admin/HR).
    """
    if is_admin_user(current_user) or is_hr_user(current_user):
        return None  # Can access all
    
    accessible = [current_user.id]  # Own data
    reportee_ids = await get_reportee_ids(current_user.id)
    accessible.extend(reportee_ids)
    
    return list(set(accessible))


class MeetingActionItem(BaseModel):
    """Action item from MOM"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    description: str
    assigned_to_id: Optional[str] = None
    assigned_to_name: Optional[str] = None
    due_date: Optional[datetime] = None
    priority: str = "medium"
    status: str = "pending"
    completed_at: Optional[datetime] = None
    follow_up_task_id: Optional[str] = None

class Meeting(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: str = "consulting"  # 'sales' or 'consulting'
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

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def calculate_lead_score(lead_data: dict) -> tuple[int, dict]:
    """
    Calculate lead score based on multiple factors:
    - Job title seniority (0-40 points)
    - Contact completeness (0-30 points)
    - Engagement/status (0-30 points)
    """
    score = 0
    breakdown = {}
    
    # Job Title Scoring (0-40 points)
    job_title = (lead_data.get('job_title') or '').lower()
    title_score = 0
    if any(term in job_title for term in ['ceo', 'founder', 'president', 'owner']):
        title_score = 40
    elif any(term in job_title for term in ['cto', 'cfo', 'coo', 'vp', 'vice president', 'chief']):
        title_score = 35
    elif any(term in job_title for term in ['director', 'head of']):
        title_score = 25
    elif any(term in job_title for term in ['manager', 'lead']):
        title_score = 15
    else:
        title_score = 5
    
    breakdown['title_score'] = title_score
    score += title_score
    
    # Contact Completeness (0-30 points)
    contact_score = 0
    if lead_data.get('email'):
        contact_score += 10
    if lead_data.get('phone'):
        contact_score += 10
    if lead_data.get('linkedin_url'):
        contact_score += 10
    
    breakdown['contact_score'] = contact_score
    score += contact_score
    
    # Engagement/Status (0-30 points)
    status = lead_data.get('status', LeadStatus.NEW)
    status_score = {
        LeadStatus.NEW: 5,
        LeadStatus.CONTACTED: 10,
        LeadStatus.QUALIFIED: 20,
        LeadStatus.PROPOSAL: 25,
        LeadStatus.AGREEMENT: 30,
        LeadStatus.CLOSED: 30,
        LeadStatus.LOST: 0
    }.get(status, 5)
    
    breakdown['engagement_score'] = status_score
    score += status_score
    
    breakdown['total'] = score
    return score, breakdown

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user_data = await db.users.find_one({"email": email}, {"_id": 0})
    if user_data is None:
        raise credentials_exception
    if isinstance(user_data.get('created_at'), str):
        user_data['created_at'] = datetime.fromisoformat(user_data['created_at'])
    return User(**user_data)

# --- Security Audit Logging ---
async def log_security_event(event_type: str, email: str = None, details: dict = None, request: Request = None):
    """Log a security event to the audit log collection"""
    log_entry = {
        "id": str(uuid.uuid4()),
        "event_type": event_type,
        "email": email,
        "details": details or {},
        "ip_address": request.client.host if request else None,
        "user_agent": request.headers.get("user-agent", "") if request else None,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    await db.security_audit_logs.insert_one(log_entry)




# NOTE: Basic leads CRUD now handled by leads_router
# Additional lead endpoints below (suggestions, generate-email, bulk-upload) remain here

# NOTE: Basic projects CRUD + handover-alerts now handled by projects_router  
# Additional project endpoints below (assign-consultant, SOW, etc.) remain here

# NOTE: Basic meetings CRUD now handled by meetings_router
# Consulting-specific endpoints below remain here

@api_router.get("/consulting-meetings/tracking")
async def get_consulting_tracking(current_user: User = Depends(get_current_user)):
    """Get committed vs actual meetings per project for consulting meetings"""
    projects = await db.projects.find({}, {"_id": 0}).to_list(1000)
    tracking = []
    for project in projects:
        committed = project.get('total_meetings_committed', 0)
        delivered = project.get('total_meetings_delivered', 0)
        # Count consulting meetings for this project
        actual_count = await db.meetings.count_documents({
            "project_id": project['id'],
            "type": "consulting"
        })
        tracking.append({
            "project_id": project['id'],
            "project_name": project.get('name', ''),
            "client_name": project.get('client_name', ''),
            "committed": committed,
            "delivered": delivered,
            "actual_meetings": actual_count,
            "status": project.get('status', 'active'),
            "variance": actual_count - committed if committed > 0 else 0,
            "completion_pct": round((actual_count / committed * 100), 1) if committed > 0 else 0
        })
    return tracking




@api_router.get("/follow-up-tasks")
async def get_follow_up_tasks(
    assigned_to: Optional[str] = None,
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get follow-up tasks"""
    query = {}
    if assigned_to:
        query['assigned_to'] = assigned_to
    if status:
        query['status'] = status
    
    # If not admin, show only own tasks or tasks of reportees
    if current_user.role != UserRole.ADMIN:
        query['$or'] = [
            {"assigned_to": current_user.id},
            {"created_by": current_user.id}
        ]
    
    tasks = await db.follow_up_tasks.find(query, {"_id": 0}).sort("created_at", -1).to_list(1000)
    return tasks


# ===== Helper functions for team/role-based queries =====
async def get_team_member_ids(manager_id: str) -> List[str]:
    """Get all user IDs that report to this manager"""
    team_members = await db.users.find(
        {"reporting_manager_id": manager_id, "is_active": True},
        {"id": 1}
    ).to_list(1000)
    return [m['id'] for m in team_members]


def can_see_all_data(user: User) -> bool:
    return user.role in ALL_DATA_ACCESS_ROLES


# ===== SALES TARGETS ENDPOINTS =====
@api_router.post("/sales-targets")
async def create_sales_target(
    target: SalesTargetCreate,
    current_user: User = Depends(get_current_user)
):
    """Create sales target for a team member (by reporting manager)"""
    # Verify current user is the reporting manager of target user
    target_user = await db.users.find_one({"id": target.user_id})
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if target_user.get('reporting_manager_id') != current_user.id and current_user.role not in ALL_DATA_ACCESS_ROLES:
        raise HTTPException(status_code=403, detail="You can only set targets for your team members")
    
    # Check for existing target
    existing = await db.sales_targets.find_one({
        "user_id": target.user_id,
        "month": target.month,
        "year": target.year
    })
    if existing:
        raise HTTPException(status_code=400, detail="Target already exists for this month")
    
    target_dict = target.model_dump()
    target_dict['id'] = str(uuid.uuid4())
    target_dict['set_by'] = current_user.id
    target_dict['approval_status'] = "pending"
    target_dict['created_at'] = datetime.now(timezone.utc).isoformat()
    
    await db.sales_targets.insert_one(target_dict)
    return {"message": "Target created successfully", "id": target_dict['id']}


@api_router.get("/sales-targets")
async def get_sales_targets(
    user_id: Optional[str] = None,
    month: Optional[int] = None,
    year: Optional[int] = None,
    current_user: User = Depends(get_current_user)
):
    """Get sales targets"""
    query = {}
    
    if user_id:
        query['user_id'] = user_id
    elif current_user.role not in ALL_DATA_ACCESS_ROLES:
        # Show own targets or targets of team members
        team_ids = await get_team_member_ids(current_user.id)
        query['user_id'] = {"$in": [current_user.id] + team_ids}
    
    if month:
        query['month'] = month
    if year:
        query['year'] = year
    
    targets = await db.sales_targets.find(query, {"_id": 0}).to_list(100)
    
    # Enrich with user names
    for t in targets:
        user = await db.users.find_one({"id": t['user_id']}, {"full_name": 1})
        t['user_name'] = user.get('full_name') if user else 'Unknown'
    
    return targets


@api_router.patch("/sales-targets/{target_id}/approve")
async def approve_sales_target(
    target_id: str,
    action: str,  # approve or reject
    current_user: User = Depends(get_current_user)
):
    """Approve/reject sales target (Principal Consultant only)"""
    if current_user.role not in ["principal_consultant", "admin"]:
        raise HTTPException(status_code=403, detail="Only Principal Consultants can approve targets")
    
    target = await db.sales_targets.find_one({"id": target_id})
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")
    
    await db.sales_targets.update_one(
        {"id": target_id},
        {"$set": {
            "approval_status": "approved" if action == "approve" else "rejected",
            "approved_by": current_user.id,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    return {"message": f"Target {action}d successfully"}


# ===== PERFORMANCE REVIEW ENDPOINTS =====
@api_router.post("/performance-reviews")
async def create_performance_review(
    review: PerformanceReviewCreate,
    current_user: User = Depends(get_current_user)
):
    """Create performance review (by reporting manager)"""
    # Verify reviewer is the reporting manager
    target_user = await db.users.find_one({"id": review.user_id})
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if target_user.get('reporting_manager_id') != current_user.id and current_user.role not in ALL_DATA_ACCESS_ROLES:
        raise HTTPException(status_code=403, detail="You can only review your team members")
    
    # Check for existing review
    existing = await db.performance_reviews.find_one({
        "user_id": review.user_id,
        "month": review.month,
        "year": review.year
    })
    if existing:
        raise HTTPException(status_code=400, detail="Review already exists for this month")
    
    review_dict = review.model_dump()
    review_dict['id'] = str(uuid.uuid4())
    review_dict['reviewer_id'] = current_user.id
    review_dict['status'] = "draft"
    review_dict['review_date'] = datetime.now(timezone.utc).isoformat()
    
    # Calculate overall score
    scores = [
        review_dict.get('meeting_quality_score'),
        review_dict.get('conversion_rate_score'),
        review_dict.get('response_time_score'),
        review_dict.get('mom_quality_score'),
        review_dict.get('target_achievement_score')
    ]
    valid_scores = [s for s in scores if s is not None]
    review_dict['overall_score'] = round(sum(valid_scores) / len(valid_scores), 2) if valid_scores else None
    
    await db.performance_reviews.insert_one(review_dict)
    return {"message": "Review created successfully", "id": review_dict['id']}


@api_router.get("/performance-reviews")
async def get_performance_reviews(
    user_id: Optional[str] = None,
    month: Optional[int] = None,
    year: Optional[int] = None,
    current_user: User = Depends(get_current_user)
):
    """Get performance reviews"""
    query = {}
    
    if user_id:
        # Check if user can view this person's reviews
        if user_id != current_user.id:
            target_user = await db.users.find_one({"id": user_id})
            if target_user and target_user.get('reporting_manager_id') != current_user.id and current_user.role not in ALL_DATA_ACCESS_ROLES:
                raise HTTPException(status_code=403, detail="Access denied")
        query['user_id'] = user_id
    elif current_user.role not in ALL_DATA_ACCESS_ROLES:
        # Show own reviews or reviews of team members
        team_ids = await get_team_member_ids(current_user.id)
        query['$or'] = [
            {'user_id': current_user.id},
            {'user_id': {"$in": team_ids}},
            {'reviewer_id': current_user.id}
        ]
    
    if month:
        query['month'] = month
    if year:
        query['year'] = year
    
    reviews = await db.performance_reviews.find(query, {"_id": 0}).to_list(100)
    
    # Enrich with names
    for r in reviews:
        user = await db.users.find_one({"id": r['user_id']}, {"full_name": 1})
        reviewer = await db.users.find_one({"id": r['reviewer_id']}, {"full_name": 1})
        r['user_name'] = user.get('full_name') if user else 'Unknown'
        r['reviewer_name'] = reviewer.get('full_name') if reviewer else 'Unknown'
    
    return reviews


@api_router.patch("/performance-reviews/{review_id}/submit")
async def submit_performance_review(
    review_id: str,
    current_user: User = Depends(get_current_user)
):
    """Submit performance review for acknowledgment"""
    review = await db.performance_reviews.find_one({"id": review_id})
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    
    if review['reviewer_id'] != current_user.id and current_user.role not in ALL_DATA_ACCESS_ROLES:
        raise HTTPException(status_code=403, detail="Only the reviewer can submit")
    
    await db.performance_reviews.update_one(
        {"id": review_id},
        {"$set": {"status": "submitted"}}
    )
    
    return {"message": "Review submitted successfully"}


# ===== TEAM MANAGEMENT ENDPOINTS =====
@api_router.get("/my-team")
async def get_my_team(current_user: User = Depends(get_current_user)):
    """Get team members reporting to current user"""
    team = await db.users.find(
        {"reporting_manager_id": current_user.id, "is_active": True},
        {"_id": 0, "hashed_password": 0}
    ).to_list(100)
    
    # Enrich with performance stats
    for member in team:
        # Get this month's stats
        now = datetime.now(timezone.utc)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        member['stats'] = {
            'leads_count': await db.leads.count_documents({"assigned_to": member['id']}),
            'closures_this_month': await db.leads.count_documents({
                "assigned_to": member['id'],
                "status": "closed",
                "updated_at": {"$gte": month_start.isoformat()}
            }),
            'meetings_this_month': await db.meetings.count_documents({
                "created_by": member['id'],
                "type": "sales",
                "meeting_date": {"$gte": month_start.isoformat()}
            })
        }
        
        # Get current target
        target = await db.sales_targets.find_one({
            "user_id": member['id'],
            "month": now.month,
            "year": now.year,
            "approval_status": "approved"
        }, {"_id": 0})
        member['current_target'] = target
        
        # Get latest review
        review = await db.performance_reviews.find_one(
            {"user_id": member['id']},
            {"_id": 0},
            sort=[("review_date", -1)]
        )
        member['latest_review'] = review
    
    return {
        "team_count": len(team),
        "members": team
    }


@api_router.patch("/users/{user_id}/reporting-manager")
async def set_reporting_manager(
    user_id: str,
    manager_id: str,
    current_user: User = Depends(get_current_user)
):
    """Set reporting manager for a user (Admin/HR only)"""
    if current_user.role not in ["admin", "hr_manager"]:
        raise HTTPException(status_code=403, detail="Only Admin/HR can set reporting managers")
    
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    manager = await db.users.find_one({"id": manager_id})
    if not manager:
        raise HTTPException(status_code=404, detail="Manager not found")
    
    await db.users.update_one(
        {"id": user_id},
        {"$set": {"reporting_manager_id": manager_id}}
    )
    
    return {"message": "Reporting manager updated successfully"}


# ============== My Clients Endpoint (Sales Person Specific) ==============

@api_router.get("/my-clients")
async def get_my_clients(current_user: User = Depends(get_current_user)):
    """Get clients belonging to the current sales person"""
    clients = await db.clients.find(
        {"sales_person_id": current_user.id, "is_active": True},
        {"_id": 0}
    ).to_list(500)
    
    for client in clients:
        if isinstance(client.get('created_at'), str):
            client['created_at'] = datetime.fromisoformat(client['created_at'])
        if isinstance(client.get('updated_at'), str):
            client['updated_at'] = datetime.fromisoformat(client['updated_at'])
    
    return clients

@api_router.post("/email-templates", response_model=EmailTemplate)
async def create_email_template(template_create: EmailTemplateCreate, current_user: User = Depends(get_current_user)):
    # SIMPLIFIED: Use is_view_only check instead of role
    if not await can_edit_data_async(current_user):
        raise HTTPException(status_code=403, detail="You have view-only access")
    
    template_dict = template_create.model_dump()
    template = EmailTemplate(**template_dict, created_by=current_user.id)
    
    doc = template.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    
    await db.email_templates.insert_one(doc)
    return template

@api_router.get("/email-templates", response_model=List[EmailTemplate])
async def get_email_templates(current_user: User = Depends(get_current_user)):
    templates = await db.email_templates.find({}, {"_id": 0}).to_list(1000)
    
    for template in templates:
        if isinstance(template.get('created_at'), str):
            template['created_at'] = datetime.fromisoformat(template['created_at'])
        if isinstance(template.get('updated_at'), str):
            template['updated_at'] = datetime.fromisoformat(template['updated_at'])
    
    return templates

@api_router.post("/follow-up-reminders", response_model=FollowUpReminder)
async def create_follow_up_reminder(reminder_create: FollowUpReminderCreate, current_user: User = Depends(get_current_user)):
    if not await can_edit_data_async(current_user):
        raise HTTPException(status_code=403, detail="You have view-only access")
    
    reminder_dict = reminder_create.model_dump()
    reminder = FollowUpReminder(**reminder_dict, created_by=current_user.id)
    
    doc = reminder.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    if doc['due_date']:
        doc['due_date'] = doc['due_date'].isoformat()
    if doc['completed_at']:
        doc['completed_at'] = doc['completed_at'].isoformat()
    
    await db.follow_up_reminders.insert_one(doc)
    return reminder

@api_router.get("/follow-up-reminders", response_model=List[FollowUpReminder])
async def get_follow_up_reminders(
    lead_id: Optional[str] = None,
    is_completed: Optional[bool] = None,
    current_user: User = Depends(get_current_user)
):
    query = {}
    if lead_id:
        query['lead_id'] = lead_id
    if is_completed is not None:
        query['is_completed'] = is_completed
    
    reminders = await db.follow_up_reminders.find(query, {"_id": 0}).to_list(1000)
    
    for reminder in reminders:
        if isinstance(reminder.get('created_at'), str):
            reminder['created_at'] = datetime.fromisoformat(reminder['created_at'])
        if reminder.get('due_date') and isinstance(reminder['due_date'], str):
            reminder['due_date'] = datetime.fromisoformat(reminder['due_date'])
        if reminder.get('completed_at') and isinstance(reminder['completed_at'], str):
            reminder['completed_at'] = datetime.fromisoformat(reminder['completed_at'])
    
    return reminders

@api_router.patch("/follow-up-reminders/{reminder_id}/complete")
async def complete_reminder(reminder_id: str, current_user: User = Depends(get_current_user)):
    result = await db.follow_up_reminders.update_one(
        {"id": reminder_id},
        {"$set": {"is_completed": True, "completed_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Reminder not found")
    
    return {"message": "Reminder marked as complete"}


# ==============================
# SALES MEETINGS & MOM ENDPOINTS
# ==============================

class SalesMeetingCreate(BaseModel):
    """Create a sales meeting with a lead"""
    lead_id: str
    title: str
    meeting_type: str  # discovery, demo, proposal, negotiation, closing
    scheduled_date: str
    scheduled_time: str
    duration_minutes: int = 60
    location: Optional[str] = None  # Office, Client Site, Google Meet, Zoom
    meeting_link: Optional[str] = None
    attendees: Optional[List[str]] = []
    agenda: Optional[str] = None
    notes: Optional[str] = None


class MOMCreate(BaseModel):
    """Minutes of Meeting"""
    meeting_id: str
    summary: str
    discussion_points: List[str]
    action_items: List[dict]  # {task, owner, due_date}
    next_steps: Optional[str] = None
    client_feedback: Optional[str] = None
    lead_temperature_update: Optional[str] = None  # cold, warm, hot


@api_router.post("/sales-meetings")
async def create_sales_meeting(
    meeting: SalesMeetingCreate,
    current_user: User = Depends(get_current_user)
):
    """Create a new sales meeting for a lead"""
    if current_user.role not in SALES_MEETING_ROLES:
        raise HTTPException(status_code=403, detail="Only sales team can create meetings")
    
    # Verify lead exists
    lead = await db.leads.find_one({"id": meeting.lead_id}, {"_id": 0})
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    meeting_doc = {
        "id": str(uuid.uuid4()),
        "lead_id": meeting.lead_id,
        "lead_name": f"{lead.get('first_name', '')} {lead.get('last_name', '')}".strip(),
        "company": lead.get("company", ""),
        "title": meeting.title,
        "meeting_type": meeting.meeting_type,
        "scheduled_date": meeting.scheduled_date,
        "scheduled_time": meeting.scheduled_time,
        "duration_minutes": meeting.duration_minutes,
        "location": meeting.location,
        "meeting_link": meeting.meeting_link,
        "attendees": meeting.attendees or [],
        "agenda": meeting.agenda,
        "notes": meeting.notes,
        "status": "scheduled",  # scheduled, completed, cancelled, no_show
        "mom_id": None,  # Will be linked when MOM is created
        "created_by": current_user.id,
        "created_by_name": current_user.full_name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.sales_meetings.insert_one(meeting_doc)
    
    # Update lead status to "contacted" if it's "new"
    if lead.get("status") == "new":
        await db.leads.update_one(
            {"id": meeting.lead_id},
            {"$set": {"status": "contacted", "updated_at": datetime.now(timezone.utc).isoformat()}}
        )
    
    meeting_doc.pop("_id", None)
    return meeting_doc


@api_router.get("/sales-meetings")
async def get_sales_meetings(
    lead_id: Optional[str] = None,
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get sales meetings with optional filters"""
    query = {}
    if lead_id:
        query["lead_id"] = lead_id
    if status:
        query["status"] = status
    
    meetings = await db.sales_meetings.find(query, {"_id": 0}).sort("scheduled_date", -1).to_list(500)
    return meetings


@api_router.get("/sales-meetings/{meeting_id}")
async def get_sales_meeting(meeting_id: str, current_user: User = Depends(get_current_user)):
    """Get a single sales meeting by ID"""
    meeting = await db.sales_meetings.find_one({"id": meeting_id}, {"_id": 0})
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    return meeting


@api_router.patch("/sales-meetings/{meeting_id}")
async def update_sales_meeting(
    meeting_id: str,
    data: dict,
    current_user: User = Depends(get_current_user)
):
    """Update a sales meeting"""
    if current_user.role not in SALES_MEETING_ROLES:
        raise HTTPException(status_code=403, detail="Only sales team can update meetings")
    
    meeting = await db.sales_meetings.find_one({"id": meeting_id})
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    
    allowed_fields = ["title", "scheduled_date", "scheduled_time", "duration_minutes", 
                      "location", "meeting_link", "attendees", "agenda", "notes", "status"]
    update_dict = {k: v for k, v in data.items() if k in allowed_fields}
    update_dict["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.sales_meetings.update_one({"id": meeting_id}, {"$set": update_dict})
    return {"message": "Meeting updated successfully"}


@api_router.post("/sales-meetings/{meeting_id}/complete")
async def complete_sales_meeting(
    meeting_id: str,
    current_user: User = Depends(get_current_user)
):
    """Mark a meeting as completed"""
    result = await db.sales_meetings.update_one(
        {"id": meeting_id},
        {"$set": {
            "status": "completed",
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Meeting not found")
    return {"message": "Meeting marked as completed"}


@api_router.post("/sales-meetings/{meeting_id}/mom")
async def create_meeting_mom(
    meeting_id: str,
    mom: MOMCreate,
    current_user: User = Depends(get_current_user)
):
    """Create Minutes of Meeting (MOM) for a sales meeting"""
    if current_user.role not in SALES_MEETING_ROLES:
        raise HTTPException(status_code=403, detail="Only sales team can create MOM")
    
    # Verify meeting exists
    meeting = await db.sales_meetings.find_one({"id": meeting_id}, {"_id": 0})
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    
    mom_doc = {
        "id": str(uuid.uuid4()),
        "meeting_id": meeting_id,
        "lead_id": meeting.get("lead_id"),
        "summary": mom.summary,
        "discussion_points": mom.discussion_points,
        "action_items": mom.action_items,
        "next_steps": mom.next_steps,
        "client_feedback": mom.client_feedback,
        "lead_temperature_update": mom.lead_temperature_update,
        "created_by": current_user.id,
        "created_by_name": current_user.full_name,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.sales_mom.insert_one(mom_doc)
    
    # Link MOM to meeting and mark meeting as completed
    await db.sales_meetings.update_one(
        {"id": meeting_id},
        {"$set": {
            "mom_id": mom_doc["id"],
            "status": "completed",
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    # Update lead status based on meeting type and temperature
    lead_id = meeting.get("lead_id")
    if lead_id:
        new_status = None
        meeting_type = meeting.get("meeting_type", "")
        
        # Auto-update lead status based on meeting type
        if meeting_type == "discovery":
            new_status = "contacted"
        elif meeting_type == "demo":
            new_status = "qualified"
        elif meeting_type == "proposal":
            new_status = "proposal"
        elif meeting_type == "negotiation":
            new_status = "proposal"
        elif meeting_type == "closing":
            new_status = "agreement"
        
        if new_status:
            update_fields = {
                "status": new_status,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            
            # Update temperature if provided
            if mom.lead_temperature_update:
                temp_map = {"cold": 20, "warm": 60, "hot": 90}
                update_fields["temperature"] = mom.lead_temperature_update
                update_fields["score"] = temp_map.get(mom.lead_temperature_update, 50)
            
            await db.leads.update_one({"id": lead_id}, {"$set": update_fields})
    
    mom_doc.pop("_id", None)
    return {
        "message": "MOM created successfully",
        "mom": mom_doc,
        "lead_status_updated": new_status
    }


@api_router.get("/sales-meetings/{meeting_id}/mom")
async def get_meeting_mom(meeting_id: str, current_user: User = Depends(get_current_user)):
    """Get MOM for a sales meeting"""
    mom = await db.sales_mom.find_one({"meeting_id": meeting_id}, {"_id": 0})
    if not mom:
        raise HTTPException(status_code=404, detail="MOM not found for this meeting")
    return mom


@api_router.get("/leads/{lead_id}/meetings")
async def get_lead_meetings(lead_id: str, current_user: User = Depends(get_current_user)):
    """Get all meetings for a specific lead"""
    meetings = await db.sales_meetings.find(
        {"lead_id": lead_id},
        {"_id": 0}
    ).sort("scheduled_date", -1).to_list(100)
    return meetings


@api_router.get("/leads/{lead_id}/mom-history")
async def get_lead_mom_history(lead_id: str, current_user: User = Depends(get_current_user)):
    """Get all MOMs for a specific lead"""
    moms = await db.sales_mom.find(
        {"lead_id": lead_id},
        {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    return moms


class LeadUpdate(BaseModel):
    """Update lead fields"""
    model_config = ConfigDict(extra="ignore")
    status: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    company: Optional[str] = None
    job_title: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    linkedin_url: Optional[str] = None
    notes: Optional[str] = None


@api_router.patch("/leads/{lead_id}")
async def update_lead(
    lead_id: str,
    update_data: LeadUpdate,
    current_user: User = Depends(get_current_user)
):
    """Update a lead - including status change"""
    existing = await db.leads.find_one({"id": lead_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    # Build update dict with only provided fields
    update_dict = {}
    for field, value in update_data.model_dump(exclude_unset=True).items():
        if value is not None:
            update_dict[field] = value
    
    if not update_dict:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    update_dict["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    # If status changed, log it
    if "status" in update_dict and update_dict["status"] != existing.get("status"):
        update_dict["status_history"] = existing.get("status_history", []) + [{
            "from": existing.get("status"),
            "to": update_dict["status"],
            "changed_by": current_user.id,
            "changed_at": datetime.now(timezone.utc).isoformat()
        }]
    
    await db.leads.update_one({"id": lead_id}, {"$set": update_dict})
    
    return {"message": "Lead updated successfully"}


@api_router.get("/leads/{lead_id}/suggestions")
async def get_lead_suggestions(lead_id: str, current_user: User = Depends(get_current_user)):
    lead_data = await db.leads.find_one({"id": lead_id}, {"_id": 0})
    if not lead_data:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    suggestions = check_lead_for_suggestions(lead_data)
    return {"suggestions": [s.model_dump() for s in suggestions]}

@api_router.post("/leads/{lead_id}/generate-email")
async def generate_email_for_lead(
    lead_id: str,
    template_id: str,
    current_user: User = Depends(get_current_user)
):
    lead_data = await db.leads.find_one({"id": lead_id}, {"_id": 0})
    if not lead_data:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    template_data = await db.email_templates.find_one({"id": template_id}, {"_id": 0})
    if not template_data:
        raise HTTPException(status_code=404, detail="Template not found")
    
    if isinstance(template_data.get('created_at'), str):
        template_data['created_at'] = datetime.fromisoformat(template_data['created_at'])
    if isinstance(template_data.get('updated_at'), str):
        template_data['updated_at'] = datetime.fromisoformat(template_data['updated_at'])
    
    template = EmailTemplate(**template_data)
    email = generate_email_from_template(template, lead_data)
    
    return email

@api_router.post("/communication-logs", response_model=CommunicationLog)
async def create_communication_log(log_create: CommunicationLogCreate, current_user: User = Depends(get_current_user)):
    if not await can_edit_data_async(current_user):
        raise HTTPException(status_code=403, detail="You have view-only access")
    
    log_dict = log_create.model_dump()
    log = CommunicationLog(**log_dict, created_by=current_user.id)
    
    doc = log.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    
    await db.communication_logs.insert_one(doc)
    return log

@api_router.get("/communication-logs")
async def get_communication_logs(
    lead_id: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    query = {}
    if lead_id:
        query['lead_id'] = lead_id
    
    logs = await db.communication_logs.find(query, {"_id": 0}).sort("created_at", -1).to_list(1000)
    
    for log in logs:
        if isinstance(log.get('created_at'), str):
            log['created_at'] = datetime.fromisoformat(log['created_at'])
    
    return logs

@api_router.post("/pricing-plans", response_model=PricingPlan)
async def create_pricing_plan(plan_create: PricingPlanCreate, current_user: User = Depends(get_current_user)):
    if not await can_edit_data_async(current_user):
        raise HTTPException(status_code=403, detail="You have view-only access")
    
    plan_dict = plan_create.model_dump()
    
    # Convert consultant dicts to ConsultantAllocation objects for calculation
    consultant_objects = [ConsultantAllocation(**c) if isinstance(c, dict) else c for c in plan_dict.get('consultants', [])]
    
    # Calculate totals
    totals = calculate_quotation_totals(
        consultant_objects,
        plan_dict.get('discount_percentage', 0),
        18,  # GST percentage
        12500  # base rate
    )
    
    plan_dict['base_amount'] = totals['subtotal']
    plan_dict['total_amount'] = totals['grand_total']
    plan_dict['is_active'] = True
    
    plan = PricingPlan(**plan_dict, created_by=current_user.id)
    
    doc = plan.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    
    await db.pricing_plans.insert_one(doc)
    return plan

@api_router.get("/pricing-plans")
async def get_pricing_plans(
    lead_id: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    query = {}
    if lead_id:
        query['lead_id'] = lead_id
    
    plans = await db.pricing_plans.find(query, {"_id": 0}).to_list(1000)
    
    for plan in plans:
        if isinstance(plan.get('created_at'), str):
            plan['created_at'] = datetime.fromisoformat(plan['created_at'])
        if isinstance(plan.get('updated_at'), str):
            plan['updated_at'] = datetime.fromisoformat(plan['updated_at'])
    
    return plans

# ==================== SOW (SCOPE OF WORK) - Sales Flow ====================

SOW_CATEGORIES = [
    {"value": "sales", "label": "Sales"},
    {"value": "hr", "label": "HR"},
    {"value": "operations", "label": "Operations"},
    {"value": "training", "label": "Training"},
    {"value": "analytics", "label": "Analytics"},
    {"value": "digital_marketing", "label": "Digital Marketing"}
]

@api_router.get("/sow-categories")
async def get_sow_categories_list():
    """Get available SOW categories"""
    return SOW_CATEGORIES

@api_router.post("/sow")
async def create_sow(
    sow_create: SOWCreate,
    current_user: User = Depends(get_current_user)
):
    """Create SOW for a pricing plan (Sales flow)"""
    # Verify pricing plan exists
    plan = await db.pricing_plans.find_one({"id": sow_create.pricing_plan_id}, {"_id": 0})
    if not plan:
        raise HTTPException(status_code=404, detail="Pricing plan not found")
    
    # Check if SOW already exists for this pricing plan
    existing = await db.sow.find_one({"pricing_plan_id": sow_create.pricing_plan_id})
    if existing:
        raise HTTPException(status_code=400, detail="SOW already exists for this pricing plan")
    
    # Create SOW items with IDs
    items = []
    for idx, item_data in enumerate(sow_create.items or []):
        item = SOWItem(
            category=item_data.get('category', 'general'),
            sub_category=item_data.get('sub_category'),
            title=item_data.get('title', ''),
            description=item_data.get('description', ''),
            deliverables=item_data.get('deliverables', []),
            timeline_weeks=item_data.get('timeline_weeks'),
            order=idx
        )
        items.append(item.model_dump())
    
    # Create initial version
    initial_version = SOWVersion(
        version=1,
        changed_by=current_user.id,
        changed_at=datetime.now(timezone.utc),
        change_type="created",
        changes={"action": "SOW created"},
        snapshot=items.copy()
    )
    
    sow = SOW(
        pricing_plan_id=sow_create.pricing_plan_id,
        lead_id=sow_create.lead_id,
        items=items,
        current_version=1,
        version_history=[initial_version.model_dump()],
        created_by=current_user.id
    )
    
    doc = sow.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    for v in doc['version_history']:
        v['changed_at'] = v['changed_at'].isoformat() if isinstance(v['changed_at'], datetime) else v['changed_at']
    
    await db.sow.insert_one(doc)
    
    # Link SOW to pricing plan
    await db.pricing_plans.update_one(
        {"id": sow_create.pricing_plan_id},
        {"$set": {"sow_id": sow.id}}
    )
    
    return {"message": "SOW created successfully", "sow_id": sow.id}

@api_router.get("/sow/{sow_id}")
async def get_sow(
    sow_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get SOW by ID"""
    sow = await db.sow.find_one({"id": sow_id}, {"_id": 0})
    if not sow:
        raise HTTPException(status_code=404, detail="SOW not found")
    return sow

@api_router.get("/sow/by-pricing-plan/{pricing_plan_id}")
async def get_sow_by_pricing_plan(
    pricing_plan_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get SOW by pricing plan ID"""
    sow = await db.sow.find_one({"pricing_plan_id": pricing_plan_id}, {"_id": 0})
    if not sow:
        raise HTTPException(status_code=404, detail="SOW not found for this pricing plan")
    return sow

@api_router.post("/sow/{sow_id}/items")
async def add_sow_item(
    sow_id: str,
    item: SOWItemCreate,
    current_user: User = Depends(get_current_user)
):
    """Add item to SOW with version tracking"""
    sow = await db.sow.find_one({"id": sow_id}, {"_id": 0})
    if not sow:
        raise HTTPException(status_code=404, detail="SOW not found")
    
    # Check freeze status - only Admin can edit frozen SOW
    if sow.get('is_frozen') and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="SOW is frozen. Only Admin can modify.")
    
    # Create new item
    new_item = SOWItem(
        category=item.category,
        sub_category=item.sub_category,
        title=item.title,
        description=item.description or "",
        deliverables=item.deliverables or [],
        timeline_weeks=item.timeline_weeks,
        order=item.order or len(sow.get('items', []))
    )
    
    items = sow.get('items', [])
    items.append(new_item.model_dump())
    
    # Create version entry
    new_version = sow.get('current_version', 1) + 1
    version_entry = {
        "version": new_version,
        "changed_by": current_user.id,
        "changed_at": datetime.now(timezone.utc).isoformat(),
        "change_type": "item_added",
        "changes": {"added_item": new_item.title, "category": item.category},
        "snapshot": items.copy()
    }
    
    version_history = sow.get('version_history', [])
    version_history.append(version_entry)
    
    await db.sow.update_one(
        {"id": sow_id},
        {"$set": {
            "items": items,
            "current_version": new_version,
            "version_history": version_history,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    return {"message": "Item added to SOW", "item_id": new_item.id, "version": new_version}

class BulkSOWItemsRequest(BaseModel):
    items: List[SOWItemCreate]

@api_router.post("/sow/{sow_id}/items/bulk")
async def add_sow_items_bulk(
    sow_id: str,
    bulk_request: BulkSOWItemsRequest,
    current_user: User = Depends(get_current_user)
):
    """Add multiple SOW items at once (for inline/spreadsheet editing)"""
    sow = await db.sow.find_one({"id": sow_id}, {"_id": 0})
    if not sow:
        raise HTTPException(status_code=404, detail="SOW not found")
    
    if sow.get('is_frozen') and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="SOW is frozen. Only Admin can modify.")
    
    existing_items = sow.get('items', [])
    new_items = []
    
    for idx, item in enumerate(bulk_request.items):
        new_item = SOWItem(
            category=item.category,
            sub_category=item.sub_category,
            title=item.title,
            description=item.description or "",
            deliverables=item.deliverables or [],
            timeline_weeks=item.timeline_weeks,
            start_week=item.start_week,
            order=item.order or len(existing_items) + idx,
            status=item.status or SOWItemStatus.DRAFT,
            notes=item.notes,
            assigned_consultant_id=item.assigned_consultant_id,
            assigned_consultant_name=item.assigned_consultant_name,
            has_backend_support=item.has_backend_support or False,
            backend_support_id=item.backend_support_id,
            backend_support_name=item.backend_support_name,
            backend_support_role=item.backend_support_role
        )
        new_items.append(new_item.model_dump())
    
    all_items = existing_items + new_items
    
    new_version = sow.get('current_version', 1) + 1
    version_entry = {
        "version": new_version,
        "changed_by": current_user.id,
        "changed_by_name": current_user.full_name,
        "changed_at": datetime.now(timezone.utc).isoformat(),
        "change_type": "bulk_items_added",
        "changes": {"count": len(new_items), "titles": [i['title'] for i in new_items]},
        "snapshot": all_items.copy()
    }
    
    version_history = sow.get('version_history', [])
    version_history.append(version_entry)
    
    await db.sow.update_one(
        {"id": sow_id},
        {"$set": {
            "items": all_items,
            "current_version": new_version,
            "version_history": version_history,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    return {
        "message": f"{len(new_items)} items added to SOW",
        "item_ids": [i['id'] for i in new_items],
        "version": new_version
    }

@api_router.delete("/sow/{sow_id}/items/{item_id}")
async def delete_sow_item(
    sow_id: str,
    item_id: str,
    current_user: User = Depends(get_current_user)
):
    """Delete a SOW item (soft delete by removing from list)"""
    sow = await db.sow.find_one({"id": sow_id}, {"_id": 0})
    if not sow:
        raise HTTPException(status_code=404, detail="SOW not found")
    
    if sow.get('is_frozen') and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="SOW is frozen. Only Admin can modify.")
    
    items = sow.get('items', [])
    deleted_item = None
    
    for item in items:
        if item.get('id') == item_id:
            deleted_item = item
            break
    
    if not deleted_item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    items = [i for i in items if i.get('id') != item_id]
    
    new_version = sow.get('current_version', 1) + 1
    version_entry = {
        "version": new_version,
        "changed_by": current_user.id,
        "changed_by_name": current_user.full_name,
        "changed_at": datetime.now(timezone.utc).isoformat(),
        "change_type": "item_deleted",
        "changes": {"deleted_item": deleted_item.get('title')},
        "snapshot": items.copy()
    }
    
    version_history = sow.get('version_history', [])
    version_history.append(version_entry)
    
    await db.sow.update_one(
        {"id": sow_id},
        {"$set": {
            "items": items,
            "current_version": new_version,
            "version_history": version_history,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    return {"message": "Item deleted", "version": new_version}

@api_router.patch("/sow/{sow_id}/items/{item_id}")
async def update_sow_item(
    sow_id: str,
    item_id: str,
    item_update: SOWItemCreate,
    current_user: User = Depends(get_current_user)
):
    """Update SOW item with version tracking"""
    sow = await db.sow.find_one({"id": sow_id}, {"_id": 0})
    if not sow:
        raise HTTPException(status_code=404, detail="SOW not found")
    
    # Check freeze status
    if sow.get('is_frozen') and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="SOW is frozen. Only Admin can modify.")
    
    items = sow.get('items', [])
    updated = False
    old_item = None
    
    for item in items:
        if item.get('id') == item_id:
            old_item = item.copy()
            item['category'] = item_update.category
            item['sub_category'] = item_update.sub_category
            item['title'] = item_update.title
            item['description'] = item_update.description or ""
            item['deliverables'] = item_update.deliverables or []
            item['timeline_weeks'] = item_update.timeline_weeks
            item['start_week'] = item_update.start_week
            item['assigned_consultant_id'] = item_update.assigned_consultant_id
            item['assigned_consultant_name'] = item_update.assigned_consultant_name
            item['has_backend_support'] = item_update.has_backend_support or False
            item['backend_support_id'] = item_update.backend_support_id
            item['backend_support_name'] = item_update.backend_support_name
            item['backend_support_role'] = item_update.backend_support_role
            item['notes'] = item_update.notes
            updated = True
            break
    
    if not updated:
        raise HTTPException(status_code=404, detail="Item not found")
    
    # Create version entry with changes highlighted
    new_version = sow.get('current_version', 1) + 1
    changes = {}
    if old_item:
        for key in ['title', 'description', 'category', 'deliverables', 'timeline_weeks']:
            if old_item.get(key) != item_update.model_dump().get(key):
                changes[key] = {"old": old_item.get(key), "new": item_update.model_dump().get(key)}
    
    version_entry = {
        "version": new_version,
        "changed_by": current_user.id,
        "changed_at": datetime.now(timezone.utc).isoformat(),
        "change_type": "item_updated",
        "changes": {"item_id": item_id, "changes": changes},
        "snapshot": items.copy()
    }
    
    version_history = sow.get('version_history', [])
    version_history.append(version_entry)
    
    await db.sow.update_one(
        {"id": sow_id},
        {"$set": {
            "items": items,
            "current_version": new_version,
            "version_history": version_history,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    return {"message": "SOW item updated", "version": new_version}

@api_router.get("/sow/{sow_id}/versions")
async def get_sow_versions(
    sow_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get all versions of SOW with change history"""
    sow = await db.sow.find_one({"id": sow_id}, {"_id": 0})
    if not sow:
        raise HTTPException(status_code=404, detail="SOW not found")
    
    # Enrich version history with user names
    versions = sow.get('version_history', [])
    for version in versions:
        user = await db.users.find_one({"id": version.get('changed_by')}, {"_id": 0, "full_name": 1})
        version['changed_by_name'] = user.get('full_name', 'Unknown') if user else 'Unknown'
    
    return {
        "current_version": sow.get('current_version', 1),
        "is_frozen": sow.get('is_frozen', False),
        "versions": versions
    }

@api_router.get("/sow/{sow_id}/version/{version_num}")
async def get_sow_at_version(
    sow_id: str,
    version_num: int,
    current_user: User = Depends(get_current_user)
):
    """Get SOW items at a specific version"""
    sow = await db.sow.find_one({"id": sow_id}, {"_id": 0})
    if not sow:
        raise HTTPException(status_code=404, detail="SOW not found")
    
    versions = sow.get('version_history', [])
    for version in versions:
        if version.get('version') == version_num:
            return {
                "version": version_num,
                "items": version.get('snapshot', []),
                "changed_by": version.get('changed_by'),
                "changed_at": version.get('changed_at'),
                "change_type": version.get('change_type'),
                "changes": version.get('changes', {})
            }
    
    raise HTTPException(status_code=404, detail=f"Version {version_num} not found")

# SOW Status Update APIs
SOW_ITEM_STATUSES = [
    {"value": "draft", "label": "Draft", "color": "zinc"},
    {"value": "pending_review", "label": "Pending Review", "color": "yellow"},
    {"value": "approved", "label": "Approved", "color": "emerald"},
    {"value": "rejected", "label": "Rejected", "color": "red"},
    {"value": "in_progress", "label": "In Progress", "color": "blue"},
    {"value": "completed", "label": "Completed", "color": "green"}
]

@api_router.get("/sow-item-statuses")
async def get_sow_item_statuses():
    """Get available SOW item statuses"""
    return SOW_ITEM_STATUSES

@api_router.patch("/sow/{sow_id}/items/{item_id}/status")
async def update_sow_item_status(
    sow_id: str,
    item_id: str,
    status_update: SOWItemStatusUpdate,
    current_user: User = Depends(get_current_user)
):
    """Update SOW item status (user updates, manager approves)"""
    sow = await db.sow.find_one({"id": sow_id}, {"_id": 0})
    if not sow:
        raise HTTPException(status_code=404, detail="SOW not found")
    
    # Check permissions - Manager can approve/reject, others can update status
    new_status = status_update.status
    if new_status in [SOWItemStatus.APPROVED, SOWItemStatus.REJECTED]:
        if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER]:
            raise HTTPException(status_code=403, detail="Only Manager/Admin can approve or reject")
    
    items = sow.get('items', [])
    updated = False
    old_status = None
    item_title = None
    item_documents = []
    
    for item in items:
        if item.get('id') == item_id:
            old_status = item.get('status', 'draft')
            item_title = item.get('title', 'Untitled')
            item_documents = item.get('documents', [])
            item['status'] = new_status
            item['status_updated_by'] = current_user.id
            item['status_updated_at'] = datetime.now(timezone.utc).isoformat()
            
            if new_status == SOWItemStatus.APPROVED:
                item['approved_by'] = current_user.id
                item['approved_at'] = datetime.now(timezone.utc).isoformat()
                item['rejection_reason'] = None
            elif new_status == SOWItemStatus.REJECTED:
                item['rejection_reason'] = status_update.rejection_reason
                item['approved_by'] = None
                item['approved_at'] = None
            
            if status_update.notes:
                item['notes'] = status_update.notes
            
            updated = True
            break
    
    if not updated:
        raise HTTPException(status_code=404, detail="Item not found")
    
    # Create version entry
    new_version = sow.get('current_version', 1) + 1
    version_entry = {
        "version": new_version,
        "changed_by": current_user.id,
        "changed_at": datetime.now(timezone.utc).isoformat(),
        "change_type": "status_changed",
        "changes": {"item_id": item_id, "old_status": old_status, "new_status": new_status},
        "snapshot": items.copy()
    }
    
    version_history = sow.get('version_history', [])
    version_history.append(version_entry)
    
    # Calculate overall SOW status
    overall_status = calculate_sow_overall_status(items)
    
    await db.sow.update_one(
        {"id": sow_id},
        {"$set": {
            "items": items,
            "current_version": new_version,
            "version_history": version_history,
            "overall_status": overall_status,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    # Send email notifications when SOW item is marked as Completed
    if new_status == SOWItemStatus.COMPLETED:
        try:
            # Get lead/client info
            lead = None
            if sow.get('lead_id'):
                lead = await db.leads.find_one({"id": sow.get('lead_id')}, {"_id": 0})
            
            # Get managers to notify
            managers = await db.users.find(
                {"role": {"$in": [UserRole.ADMIN, UserRole.MANAGER]}},
                {"_id": 0, "email": 1, "full_name": 1}
            ).to_list(length=None)
            
            # Prepare email content
            doc_count = len(item_documents)
            doc_names = ", ".join([d.get('original_filename', d.get('filename', 'Unnamed')) for d in item_documents]) if item_documents else "No documents attached"
            
            email_subject = f"SOW Item Completed: {item_title}"
            email_body = f"""
            <h2>SOW Item Completed</h2>
            <p><strong>Item:</strong> {item_title}</p>
            <p><strong>Completed by:</strong> {current_user.full_name}</p>
            <p><strong>Date:</strong> {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}</p>
            <p><strong>Documents ({doc_count}):</strong> {doc_names}</p>
            <hr>
            <p>This item has been marked as completed in the Scope of Work.</p>
            """
            
            # Store notification records for managers
            for manager in managers:
                await db.notifications.insert_one({
                    "id": str(uuid.uuid4()),
                    "user_id": manager.get('id'),
                    "email": manager.get('email'),
                    "type": "sow_item_completed",
                    "subject": email_subject,
                    "body": email_body,
                    "sow_id": sow_id,
                    "item_id": item_id,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "sent": False  # Email sending is mocked - mark as pending
                })
            
            # Notify client if lead exists
            if lead and lead.get('email'):
                await db.notifications.insert_one({
                    "id": str(uuid.uuid4()),
                    "user_id": None,
                    "email": lead.get('email'),
                    "type": "sow_item_completed_client",
                    "subject": email_subject,
                    "body": email_body,
                    "sow_id": sow_id,
                    "item_id": item_id,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "sent": False  # Email sending is mocked - mark as pending
                })
            
            # Log the notification attempt
            print(f"[SOW COMPLETION] Notifications queued for item '{item_title}' - Managers: {len(managers)}, Client: {1 if lead else 0}")
            
        except Exception as e:
            print(f"[SOW COMPLETION] Error sending notifications: {str(e)}")
            # Don't fail the status update if notification fails
    
    return {"message": f"Status updated to {new_status}", "version": new_version, "overall_status": overall_status}

def calculate_sow_overall_status(items):
    """Calculate overall SOW status based on item statuses"""
    if not items:
        return SOWOverallStatus.DRAFT
    
    statuses = [item.get('status', 'draft') for item in items]
    
    # All completed = complete
    if all(s == SOWItemStatus.COMPLETED for s in statuses):
        return SOWOverallStatus.COMPLETE
    
    # All approved or completed = approved
    if all(s in [SOWItemStatus.APPROVED, SOWItemStatus.COMPLETED] for s in statuses):
        return SOWOverallStatus.APPROVED
    
    # Any pending review = pending approval
    if any(s == SOWItemStatus.PENDING_REVIEW for s in statuses):
        return SOWOverallStatus.PENDING_APPROVAL
    
    # Some approved = partially approved
    if any(s == SOWItemStatus.APPROVED for s in statuses):
        return SOWOverallStatus.PARTIALLY_APPROVED
    
    return SOWOverallStatus.DRAFT

@api_router.post("/sow/{sow_id}/submit-for-approval")
async def submit_sow_for_approval(
    sow_id: str,
    item_ids: Optional[List[str]] = None,  # Optional: specific item IDs to submit
    current_user: User = Depends(get_current_user)
):
    """Submit SOW for manager approval using reporting manager hierarchy"""
    sow = await db.sow.find_one({"id": sow_id}, {"_id": 0})
    if not sow:
        raise HTTPException(status_code=404, detail="SOW not found")
    
    items = sow.get('items', [])
    if not items:
        raise HTTPException(status_code=400, detail="Cannot submit empty SOW for approval")
    
    # Determine which items to submit
    items_to_submit = []
    for item in items:
        if item_ids:
            # Submit only selected items
            if item['id'] in item_ids and item.get('status') == SOWItemStatus.DRAFT:
                items_to_submit.append(item)
        else:
            # Submit all draft items
            if item.get('status') == SOWItemStatus.DRAFT:
                items_to_submit.append(item)
    
    if not items_to_submit:
        raise HTTPException(status_code=400, detail="No items to submit for approval")
    
    # Check if any items are client-facing (requires multi-level approval)
    is_client_facing = any(item.get('is_client_deliverable', False) for item in items_to_submit)
    
    # Create approval requests for each item using reporting manager chain
    approval_ids = []
    for item in items_to_submit:
        # Update item status
        item['status'] = SOWItemStatus.PENDING_REVIEW
        item['status_updated_by'] = current_user.id
        item['status_updated_at'] = datetime.now(timezone.utc).isoformat()
        
        # Create approval request with reporting manager chain
        approval = await create_approval_request(
            approval_type=ApprovalType.SOW_ITEM,
            reference_id=item['id'],
            reference_title=item.get('title', 'SOW Item'),
            requester_id=current_user.id,
            is_client_facing=is_client_facing or item.get('is_client_deliverable', False),
            requires_hr_approval=False,
            requires_admin_approval=False
        )
        
        item['approval_request_id'] = approval['id']
        approval_ids.append(approval['id'])
    
    # Update the items in the main items list
    for idx, item in enumerate(items):
        for submitted_item in items_to_submit:
            if item['id'] == submitted_item['id']:
                items[idx] = submitted_item
                break
    
    # Create version entry
    new_version = sow.get('current_version', 1) + 1
    version_entry = {
        "version": new_version,
        "changed_by": current_user.id,
        "changed_at": datetime.now(timezone.utc).isoformat(),
        "change_type": "submitted_for_approval",
        "changes": {"action": f"Submitted {len(items_to_submit)} item(s) for approval", "item_ids": [i['id'] for i in items_to_submit]},
        "snapshot": items.copy()
    }
    
    version_history = sow.get('version_history', [])
    version_history.append(version_entry)
    
    await db.sow.update_one(
        {"id": sow_id},
        {"$set": {
            "items": items,
            "current_version": new_version,
            "version_history": version_history,
            "overall_status": SOWOverallStatus.PENDING_APPROVAL,
            "submitted_for_approval": True,
            "submitted_at": datetime.now(timezone.utc).isoformat(),
            "submitted_by": current_user.id,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    return {
        "message": "SOW items submitted for approval via reporting manager chain",
        "version": new_version,
        "items_submitted": len(items_to_submit),
        "approval_request_ids": approval_ids
    }

@api_router.post("/sow/{sow_id}/approve-all")
async def approve_all_sow_items(
    sow_id: str,
    current_user: User = Depends(get_current_user)
):
    """Approve all pending SOW items (Manager only)"""
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER]:
        raise HTTPException(status_code=403, detail="Only Manager/Admin can approve")
    
    sow = await db.sow.find_one({"id": sow_id}, {"_id": 0})
    if not sow:
        raise HTTPException(status_code=404, detail="SOW not found")
    
    items = sow.get('items', [])
    approved_count = 0
    
    for item in items:
        if item.get('status') == SOWItemStatus.PENDING_REVIEW:
            item['status'] = SOWItemStatus.APPROVED
            item['approved_by'] = current_user.id
            item['approved_at'] = datetime.now(timezone.utc).isoformat()
            item['status_updated_by'] = current_user.id
            item['status_updated_at'] = datetime.now(timezone.utc).isoformat()
            approved_count += 1
    
    if approved_count == 0:
        raise HTTPException(status_code=400, detail="No items pending approval")
    
    # Create version entry
    new_version = sow.get('current_version', 1) + 1
    version_entry = {
        "version": new_version,
        "changed_by": current_user.id,
        "changed_at": datetime.now(timezone.utc).isoformat(),
        "change_type": "bulk_approved",
        "changes": {"action": f"Approved {approved_count} items"},
        "snapshot": items.copy()
    }
    
    version_history = sow.get('version_history', [])
    version_history.append(version_entry)
    
    overall_status = calculate_sow_overall_status(items)
    
    await db.sow.update_one(
        {"id": sow_id},
        {"$set": {
            "items": items,
            "current_version": new_version,
            "version_history": version_history,
            "overall_status": overall_status,
            "final_approved_by": current_user.id,
            "final_approved_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    return {"message": f"Approved {approved_count} items", "version": new_version, "overall_status": overall_status}

# Document Upload for SOW
import base64
import os

UPLOAD_DIR = "/app/uploads/sow"
os.makedirs(UPLOAD_DIR, exist_ok=True)

class DocumentUpload(BaseModel):
    filename: str
    file_data: str  # Base64 encoded
    description: Optional[str] = None

@api_router.post("/sow/{sow_id}/documents")
async def upload_sow_document(
    sow_id: str,
    document: DocumentUpload,
    current_user: User = Depends(get_current_user)
):
    """Upload document to SOW"""
    sow = await db.sow.find_one({"id": sow_id}, {"_id": 0})
    if not sow:
        raise HTTPException(status_code=404, detail="SOW not found")
    
    try:
        # Decode base64 file data
        file_data = base64.b64decode(document.file_data)
        file_size = len(file_data)
        
        # Generate unique filename
        file_ext = document.filename.split('.')[-1] if '.' in document.filename else 'bin'
        stored_filename = f"{sow_id}_{str(uuid.uuid4())[:8]}.{file_ext}"
        file_path = os.path.join(UPLOAD_DIR, stored_filename)
        
        # Save file
        with open(file_path, 'wb') as f:
            f.write(file_data)
        
        # Create document record
        doc_record = SOWDocument(
            filename=stored_filename,
            original_filename=document.filename,
            file_type=file_ext,
            file_size=file_size,
            uploaded_by=current_user.id,
            description=document.description
        )
        
        doc_dict = doc_record.model_dump()
        doc_dict['uploaded_at'] = doc_dict['uploaded_at'].isoformat()
        
        documents = sow.get('documents', [])
        documents.append(doc_dict)
        
        # Create version entry
        new_version = sow.get('current_version', 1) + 1
        version_entry = {
            "version": new_version,
            "changed_by": current_user.id,
            "changed_at": datetime.now(timezone.utc).isoformat(),
            "change_type": "document_added",
            "changes": {"filename": document.filename, "size": file_size},
            "snapshot": sow.get('items', [])
        }
        
        version_history = sow.get('version_history', [])
        version_history.append(version_entry)
        
        await db.sow.update_one(
            {"id": sow_id},
            {"$set": {
                "documents": documents,
                "current_version": new_version,
                "version_history": version_history,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }}
        )
        
        return {"message": "Document uploaded", "document_id": doc_record.id, "version": new_version}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@api_router.post("/sow/{sow_id}/items/{item_id}/documents")
async def upload_item_document(
    sow_id: str,
    item_id: str,
    document: DocumentUpload,
    current_user: User = Depends(get_current_user)
):
    """Upload document to specific SOW item"""
    sow = await db.sow.find_one({"id": sow_id}, {"_id": 0})
    if not sow:
        raise HTTPException(status_code=404, detail="SOW not found")
    
    try:
        # Decode base64 file data
        file_data = base64.b64decode(document.file_data)
        file_size = len(file_data)
        
        # Generate unique filename
        file_ext = document.filename.split('.')[-1] if '.' in document.filename else 'bin'
        stored_filename = f"{item_id}_{str(uuid.uuid4())[:8]}.{file_ext}"
        file_path = os.path.join(UPLOAD_DIR, stored_filename)
        
        # Save file
        with open(file_path, 'wb') as f:
            f.write(file_data)
        
        # Create document record
        doc_record = {
            "id": str(uuid.uuid4()),
            "filename": stored_filename,
            "original_filename": document.filename,
            "file_type": file_ext,
            "file_size": file_size,
            "uploaded_by": current_user.id,
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
            "description": document.description
        }
        
        items = sow.get('items', [])
        item_found = False
        
        for item in items:
            if item.get('id') == item_id:
                if 'documents' not in item:
                    item['documents'] = []
                item['documents'].append(doc_record)
                item_found = True
                break
        
        if not item_found:
            raise HTTPException(status_code=404, detail="Item not found")
        
        # Create version entry
        new_version = sow.get('current_version', 1) + 1
        version_entry = {
            "version": new_version,
            "changed_by": current_user.id,
            "changed_at": datetime.now(timezone.utc).isoformat(),
            "change_type": "item_document_added",
            "changes": {"item_id": item_id, "filename": document.filename},
            "snapshot": items.copy()
        }
        
        version_history = sow.get('version_history', [])
        version_history.append(version_entry)
        
        await db.sow.update_one(
            {"id": sow_id},
            {"$set": {
                "items": items,
                "current_version": new_version,
                "version_history": version_history,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }}
        )
        
        return {"message": "Document uploaded to item", "document_id": doc_record['id'], "version": new_version}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@api_router.get("/sow/{sow_id}/items/{item_id}/documents/{document_id}")
async def download_item_document(
    sow_id: str,
    item_id: str,
    document_id: str,
    current_user: User = Depends(get_current_user)
):
    """Download document from specific SOW item"""
    sow = await db.sow.find_one({"id": sow_id}, {"_id": 0})
    if not sow:
        raise HTTPException(status_code=404, detail="SOW not found")
    
    # Find the item
    for item in sow.get('items', []):
        if item.get('id') == item_id:
            for doc in item.get('documents', []):
                if doc.get('id') == document_id:
                    file_path = os.path.join(UPLOAD_DIR, doc['filename'])
                    if os.path.exists(file_path):
                        with open(file_path, 'rb') as f:
                            file_data = base64.b64encode(f.read()).decode()
                        return {
                            "filename": doc.get('original_filename', doc.get('filename')),
                            "file_type": doc.get('file_type', 'bin'),
                            "file_data": file_data
                        }
                    else:
                        raise HTTPException(status_code=404, detail="File not found on disk")
            raise HTTPException(status_code=404, detail="Document not found in item")
    
    raise HTTPException(status_code=404, detail="Item not found")

@api_router.get("/sow/{sow_id}/documents/{document_id}")
async def download_sow_document(
    sow_id: str,
    document_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get document download info"""
    sow = await db.sow.find_one({"id": sow_id}, {"_id": 0})
    if not sow:
        raise HTTPException(status_code=404, detail="SOW not found")
    
    # Search in SOW documents
    for doc in sow.get('documents', []):
        if doc.get('id') == document_id:
            file_path = os.path.join(UPLOAD_DIR, doc['filename'])
            if os.path.exists(file_path):
                with open(file_path, 'rb') as f:
                    file_data = base64.b64encode(f.read()).decode()
                return {
                    "filename": doc['original_filename'],
                    "file_type": doc['file_type'],
                    "file_data": file_data
                }
    
    # Search in item documents
    for item in sow.get('items', []):
        for doc in item.get('documents', []):
            if doc.get('id') == document_id:
                file_path = os.path.join(UPLOAD_DIR, doc['filename'])
                if os.path.exists(file_path):
                    with open(file_path, 'rb') as f:
                        file_data = base64.b64encode(f.read()).decode()
                    return {
                        "filename": doc['original_filename'],
                        "file_type": doc['file_type'],
                        "file_data": file_data
                    }
    
    raise HTTPException(status_code=404, detail="Document not found")

@api_router.get("/sow/pending-approval")
async def get_sow_pending_approval(current_user: User = Depends(get_current_user)):
    """Get all SOWs pending manager approval"""
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER]:
        raise HTTPException(status_code=403, detail="Only Manager/Admin can view pending approvals")
    
    sows = await db.sow.find(
        {"overall_status": SOWOverallStatus.PENDING_APPROVAL},
        {"_id": 0}
    ).to_list(100)
    
    # Enrich with lead and pricing plan info
    result = []
    for sow in sows:
        lead = await db.leads.find_one({"id": sow.get('lead_id')}, {"_id": 0})
        plan = await db.pricing_plans.find_one({"id": sow.get('pricing_plan_id')}, {"_id": 0})
        
        pending_items = len([i for i in sow.get('items', []) if i.get('status') == SOWItemStatus.PENDING_REVIEW])
        
        result.append({
            **sow,
            "lead": lead,
            "pricing_plan": plan,
            "pending_items_count": pending_items
        })
    
    return result


# ==================== SOW CHANGE REQUESTS ====================

class SOWChangeRequestCreate(BaseModel):
    sow_id: str
    change_type: str  # 'add_scope', 'modify_scope', 'remove_scope', 'update_task', 'add_task'
    scope_id: Optional[str] = None
    task_id: Optional[str] = None
    title: str
    description: str
    proposed_changes: Dict[str, Any]  # The actual changes to apply
    requires_client_approval: bool = False

class SOWChangeRequest(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    sow_id: str
    change_type: str
    scope_id: Optional[str] = None
    task_id: Optional[str] = None
    title: str
    description: str
    proposed_changes: Dict[str, Any]
    requires_client_approval: bool = False
    status: str = 'pending'  # pending, rm_approved, rm_rejected, client_approved, client_rejected, applied
    requested_by: str
    requested_by_name: str
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    rm_approval: Optional[Dict[str, Any]] = None
    client_approval: Optional[Dict[str, Any]] = None
    applied_at: Optional[str] = None

@api_router.post("/sow-change-requests")
async def create_sow_change_request(
    request: SOWChangeRequestCreate,
    current_user: User = Depends(get_current_user)
):
    """Create a SOW change request (Consultant workflow)"""
    # Verify SOW exists
    sow = await db.enhanced_sow.find_one({"id": request.sow_id}, {"_id": 0})
    if not sow:
        # Try regular sow collection
        sow = await db.sow.find_one({"id": request.sow_id}, {"_id": 0})
    
    if not sow:
        raise HTTPException(status_code=404, detail="SOW not found")
    
    change_request = SOWChangeRequest(
        sow_id=request.sow_id,
        change_type=request.change_type,
        scope_id=request.scope_id,
        task_id=request.task_id,
        title=sanitize_text(request.title),
        description=sanitize_text(request.description),
        proposed_changes=request.proposed_changes,
        requires_client_approval=request.requires_client_approval,
        requested_by=current_user.id,
        requested_by_name=sanitize_text(current_user.full_name)
    )
    
    doc = change_request.model_dump()
    await db.sow_change_requests.insert_one(doc)
    
    # Create notification for RM/PM
    notification = {
        "id": str(uuid.uuid4()),
        "user_id": None,  # Will be sent to PM/RM
        "type": "sow_change_request",
        "title": "SOW Change Request",
        "message": f"{current_user.full_name} requested a change: {request.title}",
        "reference_id": change_request.id,
        "is_read": False,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    # Find PMs/Managers to notify
    pms = await db.users.find(
        {"role": {"$in": ["project_manager", "manager", "admin"]}},
        {"_id": 0, "id": 1}
    ).to_list(10)
    
    for pm in pms:
        notif = {**notification, "id": str(uuid.uuid4()), "user_id": pm['id']}
        await db.notifications.insert_one(notif)
    
    return {"message": "Change request created", "id": change_request.id, "status": "pending"}

@api_router.get("/sow-change-requests")
async def get_sow_change_requests(
    sow_id: Optional[str] = None,
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get SOW change requests"""
    query = {}
    
    if sow_id:
        query["sow_id"] = sow_id
    if status:
        query["status"] = status
    
    # Consultants see only their requests, PM/Admin see all
    if current_user.role not in ['admin', 'manager', 'project_manager']:
        query["requested_by"] = current_user.id
    
    requests = await db.sow_change_requests.find(query, {"_id": 0}).sort("created_at", -1).to_list(100)
    return requests

@api_router.get("/sow-change-requests/pending")
async def get_pending_change_requests(current_user: User = Depends(get_current_user)):
    """Get pending SOW change requests for approval (PM/RM view)"""
    if current_user.role not in ['admin', 'manager', 'project_manager']:
        raise HTTPException(status_code=403, detail="Not authorized to view pending requests")
    
    requests = await db.sow_change_requests.find(
        {"status": "pending"},
        {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    
    # Enrich with SOW info
    result = []
    for req in requests:
        sow = await db.enhanced_sow.find_one({"id": req['sow_id']}, {"_id": 0, "id": 1, "lead_id": 1})
        if not sow:
            sow = await db.sow.find_one({"id": req['sow_id']}, {"_id": 0, "id": 1, "lead_id": 1})
        
        lead = None
        if sow and sow.get('lead_id'):
            lead = await db.leads.find_one({"id": sow['lead_id']}, {"_id": 0, "company": 1, "first_name": 1, "last_name": 1})
        
        result.append({
            **req,
            "client_name": f"{lead['first_name']} {lead['last_name']}" if lead else "Unknown",
            "company": lead.get('company') if lead else None
        })
    
    return result

@api_router.post("/sow-change-requests/{request_id}/approve")
async def approve_sow_change_request(
    request_id: str,
    approval_type: str,  # 'rm' or 'client'
    comments: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Approve a SOW change request"""
    change_req = await db.sow_change_requests.find_one({"id": request_id}, {"_id": 0})
    if not change_req:
        raise HTTPException(status_code=404, detail="Change request not found")
    
    if approval_type == 'rm':
        if current_user.role not in ['admin', 'manager', 'project_manager']:
            raise HTTPException(status_code=403, detail="Not authorized to approve")
        
        rm_approval = {
            "approved_by": current_user.id,
            "approved_by_name": current_user.full_name,
            "approved_at": datetime.now(timezone.utc).isoformat(),
            "comments": comments
        }
        
        new_status = 'rm_approved'
        if change_req.get('requires_client_approval'):
            new_status = 'pending_client'
        
        await db.sow_change_requests.update_one(
            {"id": request_id},
            {"$set": {"status": new_status, "rm_approval": rm_approval}}
        )
        
        # If no client approval needed, apply changes
        if not change_req.get('requires_client_approval'):
            await apply_sow_changes(request_id)
        
        return {"message": "Approved by RM", "status": new_status}
    
    elif approval_type == 'client':
        # Client approval (can be done by admin on behalf of client)
        client_approval = {
            "approved_by": current_user.id,
            "approved_by_name": current_user.full_name,
            "approved_at": datetime.now(timezone.utc).isoformat(),
            "comments": comments,
            "on_behalf_of_client": True
        }
        
        await db.sow_change_requests.update_one(
            {"id": request_id},
            {"$set": {"status": "client_approved", "client_approval": client_approval}}
        )
        
        # Apply changes after client approval
        await apply_sow_changes(request_id)
        
        return {"message": "Approved by client", "status": "client_approved"}

@api_router.post("/sow-change-requests/{request_id}/reject")
async def reject_sow_change_request(
    request_id: str,
    rejection_reason: str,
    current_user: User = Depends(get_current_user)
):
    """Reject a SOW change request"""
    if current_user.role not in ['admin', 'manager', 'project_manager']:
        raise HTTPException(status_code=403, detail="Not authorized to reject")
    
    change_req = await db.sow_change_requests.find_one({"id": request_id}, {"_id": 0})
    if not change_req:
        raise HTTPException(status_code=404, detail="Change request not found")
    
    await db.sow_change_requests.update_one(
        {"id": request_id},
        {"$set": {
            "status": "rejected",
            "rm_approval": {
                "rejected_by": current_user.id,
                "rejected_by_name": current_user.full_name,
                "rejected_at": datetime.now(timezone.utc).isoformat(),
                "reason": rejection_reason
            }
        }}
    )
    
    # Notify requester
    notification = {
        "id": str(uuid.uuid4()),
        "user_id": change_req['requested_by'],
        "type": "sow_change_rejected",
        "title": "SOW Change Request Rejected",
        "message": f"Your change request '{change_req['title']}' was rejected: {rejection_reason}",
        "reference_id": request_id,
        "is_read": False,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.notifications.insert_one(notification)
    
    return {"message": "Change request rejected", "status": "rejected"}

async def apply_sow_changes(request_id: str):
    """Apply approved changes to the SOW"""
    change_req = await db.sow_change_requests.find_one({"id": request_id}, {"_id": 0})
    if not change_req:
        return
    
    sow_collection = db.enhanced_sow
    sow = await sow_collection.find_one({"id": change_req['sow_id']}, {"_id": 0})
    if not sow:
        sow_collection = db.sow
        sow = await sow_collection.find_one({"id": change_req['sow_id']}, {"_id": 0})
    
    if not sow:
        return
    
    changes = change_req.get('proposed_changes', {})
    change_type = change_req.get('change_type')
    
    update_data = {"updated_at": datetime.now(timezone.utc).isoformat()}
    
    if change_type == 'add_scope':
        scopes = sow.get('scopes', [])
        new_scope = changes.get('new_scope', {})
        new_scope['id'] = str(uuid.uuid4())
        new_scope['created_at'] = datetime.now(timezone.utc).isoformat()
        new_scope['status'] = 'not_started'
        scopes.append(new_scope)
        update_data['scopes'] = scopes
        
        # Also add to master data if it's a new scope type
        if new_scope.get('add_to_master'):
            master_scope = {
                "id": str(uuid.uuid4()),
                "name": new_scope.get('name'),
                "description": new_scope.get('description'),
                "category": new_scope.get('category', 'Custom'),
                "created_at": datetime.now(timezone.utc).isoformat(),
                "source": "consultant_request"
            }
            await db.master_scopes.insert_one(master_scope)
    
    elif change_type == 'modify_scope':
        scopes = sow.get('scopes', [])
        scope_id = change_req.get('scope_id')
        for scope in scopes:
            if scope.get('id') == scope_id:
                scope.update(changes.get('updates', {}))
                scope['updated_at'] = datetime.now(timezone.utc).isoformat()
                break
        update_data['scopes'] = scopes
    
    elif change_type == 'add_task':
        scopes = sow.get('scopes', [])
        scope_id = change_req.get('scope_id')
        for scope in scopes:
            if scope.get('id') == scope_id:
                tasks = scope.get('tasks', [])
                new_task = changes.get('new_task', {})
                new_task['id'] = str(uuid.uuid4())
                new_task['created_at'] = datetime.now(timezone.utc).isoformat()
                new_task['status'] = 'pending'
                tasks.append(new_task)
                scope['tasks'] = tasks
                break
        update_data['scopes'] = scopes
    
    await sow_collection.update_one({"id": change_req['sow_id']}, {"$set": update_data})
    
    # Mark change request as applied
    await db.sow_change_requests.update_one(
        {"id": request_id},
        {"$set": {"status": "applied", "applied_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    # Notify requester
    notification = {
        "id": str(uuid.uuid4()),
        "user_id": change_req['requested_by'],
        "type": "sow_change_applied",
        "title": "SOW Changes Applied",
        "message": f"Your change request '{change_req['title']}' has been approved and applied",
        "reference_id": request_id,
        "is_read": False,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.notifications.insert_one(notification)

# ==================== PAYMENT REMINDERS ====================

@api_router.get("/payment-reminders")
async def get_payment_reminders(current_user: User = Depends(get_current_user)):
    """Get upcoming payment reminders for all projects based on their pricing plans"""
    
    # Get all active projects
    projects = await db.projects.find(
        {"status": {"$in": ["active", "in_progress", None]}},
        {"_id": 0}
    ).to_list(100)
    
    # Get agreements, pricing plans, and enhanced SOWs
    agreements = await db.agreements.find({}, {"_id": 0}).to_list(200)
    pricing_plans = await db.pricing_plans.find({}, {"_id": 0}).to_list(200)
    enhanced_sows = await db.enhanced_sow.find({}, {"_id": 0}).to_list(200)
    leads = await db.leads.find({}, {"_id": 0}).to_list(500)
    
    reminders = []
    
    for project in projects:
        # Find related agreement
        agreement = next((a for a in agreements if a.get('id') == project.get('agreement_id')), None)
        
        # Find pricing plan from agreement or directly from project
        pricing_plan = None
        if agreement and agreement.get('pricing_plan_id'):
            pricing_plan = next((p for p in pricing_plans if p.get('id') == agreement.get('pricing_plan_id')), None)
        elif project.get('pricing_plan_id'):
            pricing_plan = next((p for p in pricing_plans if p.get('id') == project.get('pricing_plan_id')), None)
        
        # Find SOW for additional info
        sow = next((s for s in enhanced_sows if 
                    s.get('project_id') == project.get('id') or 
                    s.get('agreement_id') == project.get('agreement_id') or
                    s.get('pricing_plan_id') == (pricing_plan.get('id') if pricing_plan else None)), None)
        
        # Get payment frequency and tenure from pricing plan first, then fallback to SOW
        if pricing_plan:
            payment_frequency = pricing_plan.get('payment_frequency') or pricing_plan.get('payment_terms', {}).get('frequency', 'monthly')
            project_tenure = pricing_plan.get('tenure_months') or pricing_plan.get('project_duration_months', 12)
        elif sow:
            payment_frequency = sow.get('payment_frequency', 'monthly')
            project_tenure = sow.get('project_tenure_months', 12)
        else:
            payment_frequency = 'monthly'
            project_tenure = 12
        
        start_date_str = project.get('start_date') or (agreement.get('signed_at') if agreement else None) or (sow.get('created_at') if sow else None)
        
        if not start_date_str:
            continue
        
        try:
            if isinstance(start_date_str, str):
                start_date = datetime.fromisoformat(start_date_str.replace('Z', '+00:00'))
            else:
                start_date = start_date_str
        except (ValueError, TypeError):
            continue
        
        # Calculate payment dates based on frequency
        payment_dates = []
        current_date = datetime.now(timezone.utc)
        
        if payment_frequency == 'monthly':
            interval_months = 1
        elif payment_frequency == 'quarterly':
            interval_months = 3
        elif payment_frequency == 'bi-annual':
            interval_months = 6
        elif payment_frequency == 'yearly':
            interval_months = 12
        else:
            interval_months = 1
        
        # Generate payment dates
        total_installments = max(1, project_tenure // interval_months)
        for i in range(1, total_installments + 1):
            payment_month = start_date.month + (interval_months * i) - 1
            payment_year = start_date.year + (payment_month // 12)
            payment_month = (payment_month % 12) + 1
            
            try:
                payment_date = datetime(payment_year, payment_month, min(start_date.day, 28), tzinfo=timezone.utc)
                
                # Only include upcoming payments (next 90 days)
                days_until = (payment_date - current_date).days
                if -30 <= days_until <= 90:  # Include slightly overdue payments too
                    payment_dates.append({
                        "due_date": payment_date.isoformat(),
                        "installment_number": i,
                        "total_installments": total_installments,
                        "days_until_due": days_until,
                        "is_overdue": days_until < 0
                    })
            except (ValueError, OverflowError):
                continue
        
        if payment_dates:
            # Get lead/client info
            lead_id = project.get('lead_id') or (agreement.get('lead_id') if agreement else None)
            lead = next((l for l in leads if l.get('id') == lead_id), None)
            
            reminders.append({
                "project_id": project.get('id'),
                "project_name": project.get('name'),
                "agreement_id": agreement.get('id') if agreement else None,
                "pricing_plan_id": pricing_plan.get('id') if pricing_plan else None,
                "client_name": project.get('client_name') or (f"{lead['first_name']} {lead['last_name']}" if lead else "Unknown"),
                "company": lead.get('company') if lead else None,
                "payment_frequency": payment_frequency,
                "project_tenure_months": project_tenure,
                "total_installments": total_installments,
                "upcoming_payments": payment_dates
            })
    
    # Sort by nearest due date
    reminders.sort(key=lambda x: x['upcoming_payments'][0]['days_until_due'] if x['upcoming_payments'] else 999)
    
    return reminders

@api_router.get("/payment-reminders/project/{project_id}")
async def get_project_payment_schedule(
    project_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get payment schedule for a specific project"""
    project = await db.projects.find_one({"id": project_id}, {"_id": 0})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Find related SOW
    sow = await db.enhanced_sow.find_one(
        {"$or": [{"project_id": project_id}, {"agreement_id": project.get('agreement_id')}]},
        {"_id": 0}
    )
    
    if not sow:
        sow = await db.sow.find_one(
            {"agreement_id": project.get('agreement_id')},
            {"_id": 0}
        )
    
    payment_frequency = sow.get('payment_frequency', 'monthly') if sow else 'monthly'
    project_tenure = sow.get('project_tenure_months', 12) if sow else 12
    start_date_str = project.get('start_date')
    
    schedule = []
    
    if start_date_str:
        try:
            start_date = datetime.fromisoformat(start_date_str.replace('Z', '+00:00'))
            current_date = datetime.now(timezone.utc)
            
            if payment_frequency == 'monthly':
                interval_months = 1
            elif payment_frequency == 'quarterly':
                interval_months = 3
            elif payment_frequency == 'bi-annual':
                interval_months = 6
            elif payment_frequency == 'yearly':
                interval_months = 12
            else:
                interval_months = 1
            
            for i in range(1, project_tenure // interval_months + 2):
                payment_month = start_date.month + (interval_months * i) - 1
                payment_year = start_date.year + (payment_month // 12)
                payment_month = (payment_month % 12) + 1
                
                try:
                    payment_date = datetime(payment_year, payment_month, min(start_date.day, 28), tzinfo=timezone.utc)
                    days_until = (payment_date - current_date).days
                    
                    schedule.append({
                        "installment_number": i,
                        "due_date": payment_date.isoformat(),
                        "days_until_due": days_until,
                        "status": "overdue" if days_until < 0 else ("due_soon" if days_until <= 7 else ("upcoming" if days_until <= 30 else "scheduled"))
                    })
                except (ValueError, OverflowError):
                    continue
        except (ValueError, TypeError):
            pass
    
    return {
        "project_id": project_id,
        "project_name": project.get('name'),
        "payment_frequency": payment_frequency,
        "project_tenure_months": project_tenure,
        "schedule": schedule
    }


# ==============================
# PROJECT PAYMENTS ENDPOINTS
# ==============================

@api_router.post("/project-payments/record")
async def record_project_payment(
    payment_data: dict,
    current_user: User = Depends(get_current_user)
):
    """
    Record a payment for a project installment with transaction ID.
    Required fields: project_id, installment_number, transaction_id, received_amount
    """
    project_id = payment_data.get('project_id')
    installment_number = payment_data.get('installment_number')
    transaction_id = payment_data.get('transaction_id')
    received_amount = payment_data.get('received_amount')
    
    if not all([project_id, installment_number, transaction_id, received_amount]):
        raise HTTPException(status_code=400, detail="Missing required fields: project_id, installment_number, transaction_id, received_amount")
    
    # Verify project exists
    project = await db.projects.find_one({"id": project_id}, {"_id": 0})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Check for duplicate transaction ID
    existing_txn = await db.project_payments.find_one({"transaction_id": transaction_id})
    if existing_txn:
        raise HTTPException(status_code=400, detail="Transaction ID already exists")
    
    # Check if this installment was already paid
    existing_payment = await db.project_payments.find_one({
        "project_id": project_id,
        "installment_number": installment_number
    })
    if existing_payment:
        raise HTTPException(status_code=400, detail=f"Installment #{installment_number} was already recorded")
    
    # Create payment record
    payment_record = {
        "id": str(uuid.uuid4()),
        "project_id": project_id,
        "agreement_id": payment_data.get('agreement_id'),
        "pricing_plan_id": payment_data.get('pricing_plan_id'),
        "installment_number": installment_number,
        "transaction_id": transaction_id,
        "received_amount": float(received_amount),
        "payment_date": payment_data.get('payment_date', datetime.now(timezone.utc).isoformat()),
        "payment_mode": payment_data.get('payment_mode', 'bank_transfer'),
        "notes": payment_data.get('notes', ''),
        "recorded_by": current_user.id,
        "recorded_by_name": current_user.full_name,
        "status": "verified",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.project_payments.insert_one(payment_record)
    
    # Return without _id
    if '_id' in payment_record:
        del payment_record['_id']
    
    return {
        "message": "Payment recorded successfully",
        "payment": payment_record
    }


@api_router.get("/project-payments/project/{project_id}")
async def get_project_payments(
    project_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get all recorded payments for a project"""
    payments = await db.project_payments.find(
        {"project_id": project_id},
        {"_id": 0}
    ).sort("installment_number", 1).to_list(100)
    
    return payments


@api_router.post("/payment-reminders/send")
async def send_payment_reminder(
    reminder_data: dict,
    current_user: User = Depends(get_current_user)
):
    """
    Send a payment reminder email/notification.
    Note: Email service must be configured for actual delivery.
    Currently logs the reminder for audit purposes.
    """
    project_id = reminder_data.get('project_id')
    installment_number = reminder_data.get('installment_number')
    
    if not project_id or not installment_number:
        raise HTTPException(status_code=400, detail="project_id and installment_number are required")
    
    # Log the reminder
    reminder_log = {
        "id": str(uuid.uuid4()),
        "project_id": project_id,
        "installment_number": installment_number,
        "client_name": reminder_data.get('client_name'),
        "client_email": reminder_data.get('client_email'),
        "due_date": reminder_data.get('due_date'),
        "project_name": reminder_data.get('project_name'),
        "sent_by": current_user.id,
        "sent_by_name": current_user.full_name,
        "sent_at": datetime.now(timezone.utc).isoformat(),
        "status": "logged"  # Would be "sent" if email service is configured
    }
    
    await db.payment_reminder_logs.insert_one(reminder_log)
    
    return {
        "message": "Reminder logged successfully",
        "reminder_id": reminder_log["id"]
    }


@api_router.post("/quotations", response_model=Quotation)
async def create_quotation(quotation_create: QuotationCreate, current_user: User = Depends(get_current_user)):
    if not await can_edit_data_async(current_user):
        raise HTTPException(status_code=403, detail="You have view-only access")
    
    # Get pricing plan
    plan_data = await db.pricing_plans.find_one({"id": quotation_create.pricing_plan_id}, {"_id": 0})
    if not plan_data:
        raise HTTPException(status_code=404, detail="Pricing plan not found")
    
    # Calculate quotation totals
    totals = calculate_quotation_totals(
        [ConsultantAllocation(**c) for c in plan_data.get('consultants', [])],
        plan_data.get('discount_percentage', 0),
        plan_data.get('gst_percentage', 18),
        quotation_create.base_rate_per_meeting
    )
    
    # Generate quotation number
    count = await db.quotations.count_documents({})
    quotation_number = f"QT-{datetime.now().year}-{count + 1:04d}"
    
    quotation_dict = quotation_create.model_dump()
    quotation_dict['quotation_number'] = quotation_number
    quotation_dict['total_meetings'] = totals['total_meetings']
    quotation_dict['subtotal'] = totals['subtotal']
    quotation_dict['discount_amount'] = totals['discount_amount']
    quotation_dict['gst_amount'] = totals['gst_amount']
    quotation_dict['grand_total'] = totals['grand_total']
    
    quotation = Quotation(**quotation_dict, created_by=current_user.id)
    
    doc = quotation.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    
    await db.quotations.insert_one(doc)
    return quotation

@api_router.get("/quotations")
async def get_quotations(
    lead_id: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    query = {}
    if lead_id:
        query['lead_id'] = lead_id
    
    quotations = await db.quotations.find(query, {"_id": 0}).to_list(1000)
    
    for quotation in quotations:
        if isinstance(quotation.get('created_at'), str):
            quotation['created_at'] = datetime.fromisoformat(quotation['created_at'])
        if isinstance(quotation.get('updated_at'), str):
            quotation['updated_at'] = datetime.fromisoformat(quotation['updated_at'])
    
    return quotations

@api_router.patch("/quotations/{quotation_id}/finalize")
async def finalize_quotation(quotation_id: str, current_user: User = Depends(get_current_user)):
    result = await db.quotations.update_one(
        {"id": quotation_id},
        {"$set": {"is_final": True, "status": "sent", "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Quotation not found")
    
    return {"message": "Quotation finalized"}

@api_router.post("/agreements", response_model=Agreement)
async def create_agreement(agreement_create: AgreementCreate, current_user: User = Depends(get_current_user)):
    if not await can_edit_data_async(current_user):
        raise HTTPException(status_code=403, detail="You have view-only access")
    
    # Generate agreement number
    count = await db.agreements.count_documents({})
    agreement_number = f"AGR-{datetime.now().year}-{count + 1:04d}"
    
    # Get quotation, pricing plan, and SOW for the agreement
    quotation = await db.quotations.find_one({"id": agreement_create.quotation_id}, {"_id": 0})
    pricing_plan = None
    sow = None
    
    if quotation:
        pricing_plan = await db.pricing_plans.find_one({"id": quotation.get('pricing_plan_id')}, {"_id": 0})
        if pricing_plan and pricing_plan.get('sow_id'):
            sow = await db.sow.find_one({"id": pricing_plan.get('sow_id')}, {"_id": 0})
    
    # Get lead info
    lead = await db.leads.find_one({"id": agreement_create.lead_id}, {"_id": 0})
    
    agreement_dict = agreement_create.model_dump()
    agreement_dict['agreement_number'] = agreement_number
    
    # Link SOW and pricing plan IDs
    if sow:
        agreement_dict['sow_id'] = sow.get('id')
    if pricing_plan:
        agreement_dict['pricing_plan_id'] = pricing_plan.get('id')
    
    # Auto-populate party name if not provided
    if not agreement_dict.get('party_name') and lead:
        agreement_dict['party_name'] = f"{lead.get('first_name', '')} {lead.get('last_name', '')} ({lead.get('company', '')})"
    
    # Auto-populate project duration if not provided
    if not agreement_dict.get('project_duration_months') and pricing_plan:
        agreement_dict['project_duration_months'] = pricing_plan.get('project_duration_months')
    
    # Build default sections
    sections = []
    for section_template in DEFAULT_AGREEMENT_SECTIONS:
        section = AgreementSection(
            section_type=section_template['section_type'],
            title=section_template['title'],
            order=section_template['order'],
            is_required=section_template['is_required'],
            content=""
        )
        sections.append(section.model_dump())
    agreement_dict['sections'] = sections
    
    agreement = Agreement(**agreement_dict, created_by=current_user.id)
    
    doc = agreement.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    if doc['start_date']:
        doc['start_date'] = doc['start_date'].isoformat()
    if doc['end_date']:
        doc['end_date'] = doc['end_date'].isoformat()
    if doc['signed_date']:
        doc['signed_date'] = doc['signed_date'].isoformat()
    if doc.get('project_start_date'):
        doc['project_start_date'] = doc['project_start_date'].isoformat()
    
    await db.agreements.insert_one(doc)
    
    # Don't update lead status yet - wait for manager approval
    # Status will be updated to 'closed' only after approval
    
    return agreement

@api_router.get("/agreements/{agreement_id}/full")
async def get_agreement_full_details(
    agreement_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get agreement with all related data (SOW, pricing plan, quotation, lead)"""
    agreement = await db.agreements.find_one({"id": agreement_id}, {"_id": 0})
    if not agreement:
        raise HTTPException(status_code=404, detail="Agreement not found")
    
    # Get related data
    quotation = None
    pricing_plan = None
    sow = None
    lead = None
    
    if agreement.get('quotation_id'):
        quotation = await db.quotations.find_one({"id": agreement['quotation_id']}, {"_id": 0})
    
    if agreement.get('pricing_plan_id'):
        pricing_plan = await db.pricing_plans.find_one({"id": agreement['pricing_plan_id']}, {"_id": 0})
    elif quotation and quotation.get('pricing_plan_id'):
        pricing_plan = await db.pricing_plans.find_one({"id": quotation['pricing_plan_id']}, {"_id": 0})
    
    if agreement.get('sow_id'):
        sow = await db.sow.find_one({"id": agreement['sow_id']}, {"_id": 0})
    elif pricing_plan and pricing_plan.get('sow_id'):
        sow = await db.sow.find_one({"id": pricing_plan['sow_id']}, {"_id": 0})
    
    if agreement.get('lead_id'):
        lead = await db.leads.find_one({"id": agreement['lead_id']}, {"_id": 0})
    
    return {
        "agreement": agreement,
        "quotation": quotation,
        "pricing_plan": pricing_plan,
        "sow": sow,
        "lead": lead
    }

@api_router.get("/agreements/{agreement_id}/export")
async def export_agreement(
    agreement_id: str,
    format: str = "json",  # json, html (for PDF generation on frontend)
    current_user: User = Depends(get_current_user)
):
    """Export agreement in various formats"""
    agreement = await db.agreements.find_one({"id": agreement_id}, {"_id": 0})
    if not agreement:
        raise HTTPException(status_code=404, detail="Agreement not found")
    
    # Get all related data
    quotation = None
    pricing_plan = None
    sow = None
    lead = None
    
    if agreement.get('quotation_id'):
        quotation = await db.quotations.find_one({"id": agreement['quotation_id']}, {"_id": 0})
    
    if agreement.get('pricing_plan_id'):
        pricing_plan = await db.pricing_plans.find_one({"id": agreement['pricing_plan_id']}, {"_id": 0})
    elif quotation and quotation.get('pricing_plan_id'):
        pricing_plan = await db.pricing_plans.find_one({"id": quotation['pricing_plan_id']}, {"_id": 0})
    
    if agreement.get('sow_id'):
        sow = await db.sow.find_one({"id": agreement['sow_id']}, {"_id": 0})
    elif pricing_plan and pricing_plan.get('sow_id'):
        sow = await db.sow.find_one({"id": pricing_plan['sow_id']}, {"_id": 0})
    
    if agreement.get('lead_id'):
        lead = await db.leads.find_one({"id": agreement['lead_id']}, {"_id": 0})
    
    # Build SOW table data
    sow_table = []
    if sow:
        for item in sow.get('items', []):
            sow_table.append({
                "category": item.get('category', '').replace('_', ' ').title(),
                "title": item.get('title', ''),
                "description": item.get('description', ''),
                "deliverables": item.get('deliverables', []),
                "timeline_weeks": item.get('timeline_weeks')
            })
    
    # Build team deployment table
    team_table = []
    if pricing_plan:
        for consultant in pricing_plan.get('consultants', []):
            team_table.append({
                "type": consultant.get('consultant_type', '').replace('_', ' ').title(),
                "count": consultant.get('count', 1),
                "meetings": consultant.get('meetings', 0),
                "hours": consultant.get('hours', 0),
                "rate": consultant.get('rate_per_meeting', 12500)
            })
    
    export_data = {
        "agreement_number": agreement.get('agreement_number'),
        "party_name": agreement.get('party_name', ''),
        "company_section": agreement.get('company_section', 'Agreement between D&V Business Consulting and Client'),
        "client": {
            "name": f"{lead.get('first_name', '')} {lead.get('last_name', '')}" if lead else '',
            "company": lead.get('company', '') if lead else '',
            "email": lead.get('email', '') if lead else '',
            "phone": lead.get('phone', '') if lead else ''
        },
        "confidentiality_clause": agreement.get('confidentiality_clause', ''),
        "nda_clause": agreement.get('nda_clause', ''),
        "nca_clause": agreement.get('nca_clause', ''),
        "renewal_clause": agreement.get('renewal_clause', ''),
        "conveyance_clause": agreement.get('conveyance_clause', ''),
        "sow_table": sow_table,
        "project_details": {
            "start_date": agreement.get('project_start_date') or agreement.get('start_date'),
            "duration_months": agreement.get('project_duration_months') or (pricing_plan.get('project_duration_months') if pricing_plan else None),
            "payment_schedule": pricing_plan.get('payment_schedule', '') if pricing_plan else ''
        },
        "team_engagement": team_table,
        "pricing": {
            "subtotal": quotation.get('subtotal', 0) if quotation else 0,
            "discount": quotation.get('discount_amount', 0) if quotation else 0,
            "gst": quotation.get('gst_amount', 0) if quotation else 0,
            "total": quotation.get('grand_total', 0) if quotation else 0,
            "total_meetings": quotation.get('total_meetings', 0) if quotation else 0
        },
        "payment_terms": agreement.get('payment_terms', 'Net 30 days'),
        "payment_conditions": agreement.get('payment_conditions', ''),
        "special_conditions": agreement.get('special_conditions', ''),
        "signature_section": agreement.get('signature_section', ''),
        "status": agreement.get('status'),
        "created_at": agreement.get('created_at'),
        "sections": agreement.get('sections', [])
    }
    
    return export_data


@api_router.get("/agreements/{agreement_id}/download")
async def download_agreement_document(
    agreement_id: str,
    format: str = "pdf",  # pdf or docx
    current_user: User = Depends(get_current_user)
):
    """Download agreement as Word or PDF document"""
    agreement = await db.agreements.find_one({"id": agreement_id}, {"_id": 0})
    if not agreement:
        raise HTTPException(status_code=404, detail="Agreement not found")
    
    # Get all related data
    quotation = None
    pricing_plan = None
    sow = None
    lead = None
    
    if agreement.get('quotation_id'):
        quotation = await db.quotations.find_one({"id": agreement['quotation_id']}, {"_id": 0})
    
    if agreement.get('pricing_plan_id'):
        pricing_plan = await db.pricing_plans.find_one({"id": agreement['pricing_plan_id']}, {"_id": 0})
    elif quotation and quotation.get('pricing_plan_id'):
        pricing_plan = await db.pricing_plans.find_one({"id": quotation['pricing_plan_id']}, {"_id": 0})
    
    if agreement.get('sow_id'):
        sow = await db.sow.find_one({"id": agreement['sow_id']}, {"_id": 0})
    elif pricing_plan and pricing_plan.get('sow_id'):
        sow = await db.sow.find_one({"id": pricing_plan['sow_id']}, {"_id": 0})
    
    if agreement.get('lead_id'):
        lead = await db.leads.find_one({"id": agreement['lead_id']}, {"_id": 0})
    
    # Build SOW table data
    sow_table = []
    if sow:
        for item in sow.get('items', []):
            sow_table.append({
                "category": item.get('category', '').replace('_', ' ').title(),
                "title": item.get('title', ''),
                "description": item.get('description', ''),
                "deliverables": item.get('deliverables', []),
                "timeline_weeks": item.get('timeline_weeks')
            })
    
    # Build team deployment table
    team_table = []
    if pricing_plan:
        for consultant in pricing_plan.get('consultants', []):
            team_table.append({
                "type": consultant.get('consultant_type', '').replace('_', ' ').title(),
                "count": consultant.get('count', 1),
                "meetings": consultant.get('meetings', 0),
                "hours": consultant.get('hours', 0),
                "rate": consultant.get('rate_per_meeting', 12500)
            })
    
    # Prepare export data
    export_data = {
        "agreement_number": agreement.get('agreement_number'),
        "party_name": agreement.get('party_name', ''),
        "company_section": agreement.get('company_section', 'Agreement between D&V Business Consulting and Client'),
        "client": {
            "name": f"{lead.get('first_name', '')} {lead.get('last_name', '')}" if lead else '',
            "company": lead.get('company', '') if lead else '',
            "email": lead.get('email', '') if lead else '',
            "phone": lead.get('phone', '') if lead else ''
        },
        "confidentiality_clause": agreement.get('confidentiality_clause', ''),
        "nda_clause": agreement.get('nda_clause', ''),
        "nca_clause": agreement.get('nca_clause', ''),
        "renewal_clause": agreement.get('renewal_clause', ''),
        "conveyance_clause": agreement.get('conveyance_clause', ''),
        "sow_table": sow_table,
        "project_details": {
            "start_date": agreement.get('project_start_date') or agreement.get('start_date'),
            "duration_months": agreement.get('project_duration_months') or (pricing_plan.get('project_duration_months') if pricing_plan else None),
            "payment_schedule": pricing_plan.get('payment_schedule', '') if pricing_plan else ''
        },
        "team_engagement": team_table,
        "pricing": {
            "subtotal": quotation.get('subtotal', 0) if quotation else 0,
            "discount": quotation.get('discount_amount', 0) if quotation else 0,
            "gst": quotation.get('gst_amount', 0) if quotation else 0,
            "total": quotation.get('grand_total', 0) if quotation else 0,
            "total_meetings": quotation.get('total_meetings', 0) if quotation else 0
        },
        "payment_terms": agreement.get('payment_terms', 'Net 30 days'),
        "payment_conditions": agreement.get('payment_conditions', ''),
        "special_conditions": agreement.get('special_conditions', ''),
        "created_at": agreement.get('created_at'),
    }
    
    # Generate document
    generator = AgreementDocumentGenerator(export_data)
    
    agreement_num = agreement.get('agreement_number', 'Agreement').replace('/', '-')
    
    if format.lower() == 'docx':
        buffer = generator.generate_word()
        filename = f"{agreement_num}.docx"
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    else:
        buffer = generator.generate_pdf()
        filename = f"{agreement_num}.pdf"
        media_type = "application/pdf"
    
    return Response(
        content=buffer.getvalue(),
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@api_router.get("/agreements")
async def get_agreements(
    lead_id: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    query = {}
    if lead_id:
        query['lead_id'] = lead_id
    
    agreements = await db.agreements.find(query, {"_id": 0}).to_list(1000)
    
    for agreement in agreements:
        if isinstance(agreement.get('created_at'), str):
            agreement['created_at'] = datetime.fromisoformat(agreement['created_at'])
        if isinstance(agreement.get('updated_at'), str):
            agreement['updated_at'] = datetime.fromisoformat(agreement['updated_at'])
        if agreement.get('start_date') and isinstance(agreement['start_date'], str):
            agreement['start_date'] = datetime.fromisoformat(agreement['start_date'])
        if agreement.get('end_date') and isinstance(agreement['end_date'], str):
            agreement['end_date'] = datetime.fromisoformat(agreement['end_date'])
        if agreement.get('signed_date') and isinstance(agreement['signed_date'], str):
            agreement['signed_date'] = datetime.fromisoformat(agreement['signed_date'])
        if agreement.get('approved_at') and isinstance(agreement['approved_at'], str):
            agreement['approved_at'] = datetime.fromisoformat(agreement['approved_at'])
    
    return agreements

@api_router.patch("/agreements/{agreement_id}/approve")
async def approve_agreement(
    agreement_id: str,
    current_user: User = Depends(get_current_user)
):
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER]:
        raise HTTPException(status_code=403, detail="Only managers and admins can approve agreements")
    
    agreement_data = await db.agreements.find_one({"id": agreement_id}, {"_id": 0})
    if not agreement_data:
        raise HTTPException(status_code=404, detail="Agreement not found")
    
    # Update agreement status to approved
    await db.agreements.update_one(
        {"id": agreement_id},
        {"$set": {
            "status": "approved",
            "approved_by": current_user.id,
            "approved_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    # Update lead status to 'closed' when agreement is approved
    lead_id = agreement_data.get('lead_id')
    if lead_id:
        await db.leads.update_one(
            {"id": lead_id},
            {"$set": {
                "status": "closed",
                "updated_at": datetime.now(timezone.utc).isoformat()
            }}
        )
    
    return {"message": "Agreement approved and lead marked as closed"}

class RejectionRequest(BaseModel):
    rejection_reason: str

@api_router.patch("/agreements/{agreement_id}/reject")
async def reject_agreement(
    agreement_id: str,
    rejection_data: RejectionRequest,
    current_user: User = Depends(get_current_user)
):
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER]:
        raise HTTPException(status_code=403, detail="Only managers and admins can reject agreements")
    
    result = await db.agreements.update_one(
        {"id": agreement_id},
        {"$set": {
            "status": "rejected",
            "approved_by": current_user.id,
            "approved_at": datetime.now(timezone.utc).isoformat(),
            "rejection_reason": rejection_data.rejection_reason,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Agreement not found")
    
    return {"message": "Agreement rejected"}

@api_router.get("/agreements/pending-approval")
async def get_agreement_pending_approvals(current_user: User = Depends(get_current_user)):
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER]:
        raise HTTPException(status_code=403, detail="Only managers and admins can view pending approvals")
    
    agreements = await db.agreements.find(
        {"status": "pending_approval"},
        {"_id": 0}
    ).to_list(1000)
    
    result = []
    for agreement in agreements:
        if isinstance(agreement.get('created_at'), str):
            agreement['created_at'] = datetime.fromisoformat(agreement['created_at'])
        if isinstance(agreement.get('updated_at'), str):
            agreement['updated_at'] = datetime.fromisoformat(agreement['updated_at'])
        if agreement.get('start_date') and isinstance(agreement['start_date'], str):
            agreement['start_date'] = datetime.fromisoformat(agreement['start_date'])
        if agreement.get('end_date') and isinstance(agreement['end_date'], str):
            agreement['end_date'] = datetime.fromisoformat(agreement['end_date'])
        
        # Get associated quotation
        quotation = None
        if agreement.get('quotation_id'):
            quotation = await db.quotations.find_one(
                {"id": agreement['quotation_id']},
                {"_id": 0}
            )
        
        result.append({
            "agreement": agreement,
            "quotation": quotation
        })
    
    return result


# ============== Agreement E-Signature Endpoint ==============

class AgreementSignatureData(BaseModel):
    signer_name: str
    signer_designation: Optional[str] = None
    signer_email: EmailStr
    signature_date: Optional[str] = None
    signature_image: Optional[str] = None  # Base64 encoded signature canvas data
    signed_at: Optional[str] = None


@api_router.post("/agreements/{agreement_id}/sign")
async def sign_agreement(
    agreement_id: str,
    signature_data: AgreementSignatureData,
    current_user: User = Depends(get_current_user)
):
    """E-Sign an agreement with canvas-based signature"""
    agreement = await db.agreements.find_one({"id": agreement_id}, {"_id": 0})
    if not agreement:
        raise HTTPException(status_code=404, detail="Agreement not found")
    
    if agreement.get('status') == 'signed':
        raise HTTPException(status_code=400, detail="Agreement is already signed")
    
    now = datetime.now(timezone.utc)
    
    client_signature = {
        "signer_name": signature_data.signer_name,
        "signer_designation": signature_data.signer_designation,
        "signer_email": signature_data.signer_email,
        "signature_date": signature_data.signature_date or now.strftime('%Y-%m-%d'),
        "signature_image": signature_data.signature_image,  # Canvas signature data
        "signed_at": now.isoformat(),
        "signed_by_user_id": current_user.id if current_user else None
    }
    
    await db.agreements.update_one(
        {"id": agreement_id},
        {"$set": {
            "status": "signed",
            "client_signature": client_signature,
            "signed_date": now.isoformat(),
            "updated_at": now.isoformat()
        }}
    )
    
    # Update lead status to closed
    if agreement.get('lead_id'):
        await db.leads.update_one(
            {"id": agreement['lead_id']},
            {"$set": {
                "status": "closed",
                "updated_at": now.isoformat()
            }}
        )
    
    return {"message": "Agreement signed successfully", "signed_at": now.isoformat()}


@api_router.post("/leads/bulk-upload")
async def bulk_upload_leads(
    leads_data: List[LeadCreate],
    skip_duplicates: bool = True,
    current_user: User = Depends(get_current_user)
):
    if not await can_edit_data_async(current_user):
        raise HTTPException(status_code=403, detail="You have view-only access")
    
    created_leads = []
    skipped_duplicates = []
    errors = []
    
    for lead_data in leads_data:
        try:
            # Check for duplicates based on email or phone
            if skip_duplicates:
                existing = await db.leads.find_one({
                    "$or": [
                        {"email": lead_data.email} if lead_data.email else {},
                        {"phone": lead_data.phone} if lead_data.phone else {}
                    ]
                }, {"_id": 0})
                
                if existing:
                    skipped_duplicates.append({
                        "email": lead_data.email,
                        "phone": lead_data.phone,
                        "reason": "Duplicate found"
                    })
                    continue
            
            # Create lead
            lead_dict = lead_data.model_dump()
            score, breakdown = calculate_lead_score(lead_dict)
            
            lead = Lead(**lead_dict, created_by=current_user.id, lead_score=score, score_breakdown=breakdown)
            
            doc = lead.model_dump()
            doc['created_at'] = doc['created_at'].isoformat()
            doc['updated_at'] = doc['updated_at'].isoformat()
            if doc['enriched_at']:
                doc['enriched_at'] = doc['enriched_at'].isoformat()
            
            await db.leads.insert_one(doc)
            created_leads.append(lead.id)
            
        except Exception as e:
            errors.append({
                "email": lead_data.email if hasattr(lead_data, 'email') else None,
                "error": str(e)
            })
    
    return {
        "created_count": len(created_leads),
        "skipped_count": len(skipped_duplicates),
        "error_count": len(errors),
        "created_leads": created_leads,
        "skipped_duplicates": skipped_duplicates,
        "errors": errors
    }

@api_router.post("/agreement-templates", response_model=AgreementTemplate)
async def create_agreement_template(
    template_create: AgreementTemplateCreate,
    current_user: User = Depends(get_current_user)
):
    if not await can_edit_data_async(current_user):
        raise HTTPException(status_code=403, detail="You have view-only access")
    
    template_dict = template_create.model_dump()
    
    # Auto-extract variables if not provided
    if not template_dict.get('variables'):
        template_dict['variables'] = extract_variables_from_template(template_dict['template_content'])
    
    template = AgreementTemplate(**template_dict, created_by=current_user.id)
    
    doc = template.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    
    await db.agreement_templates.insert_one(doc)
    return template

@api_router.get("/agreement-templates")
async def get_agreement_templates(current_user: User = Depends(get_current_user)):
    templates = await db.agreement_templates.find({}, {"_id": 0}).to_list(1000)
    
    for template in templates:
        if isinstance(template.get('created_at'), str):
            template['created_at'] = datetime.fromisoformat(template['created_at'])
        if isinstance(template.get('updated_at'), str):
            template['updated_at'] = datetime.fromisoformat(template['updated_at'])
    
    return templates

@api_router.post("/email-notification-templates", response_model=EmailNotificationTemplate)
async def create_email_notification_template(
    template_create: EmailNotificationTemplateCreate,
    current_user: User = Depends(get_current_user)
):
    if not await can_edit_data_async(current_user):
        raise HTTPException(status_code=403, detail="You have view-only access")
    
    template_dict = template_create.model_dump()
    
    # Auto-extract variables
    all_content = template_dict['subject'] + template_dict['body']
    template_dict['variables'] = extract_variables_from_template(all_content)
    
    template = EmailNotificationTemplate(**template_dict, created_by=current_user.id)
    
    doc = template.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    
    await db.email_notification_templates.insert_one(doc)
    return template

@api_router.get("/email-notification-templates")
async def get_email_notification_templates(
    template_type: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    query = {}
    if template_type:
        query['template_type'] = template_type
    
    templates = await db.email_notification_templates.find(query, {"_id": 0}).to_list(1000)
    
    for template in templates:
        if isinstance(template.get('created_at'), str):
            template['created_at'] = datetime.fromisoformat(template['created_at'])
        if isinstance(template.get('updated_at'), str):
            template['updated_at'] = datetime.fromisoformat(template['updated_at'])
    
    return templates

@api_router.get("/email-notification-templates/default")
async def get_default_email_templates():
    """Get default email templates"""
    return DEFAULT_AGREEMENT_EMAIL_TEMPLATES

@api_router.post("/agreements/{agreement_id}/send-email")
async def send_agreement_email(
    agreement_id: str,
    email_data: AgreementEmailData,
    current_user: User = Depends(get_current_user)
):
    """Send agreement to client via email"""
    
    # Fetch agreement
    agreement_data = await db.agreements.find_one({"id": agreement_id}, {"_id": 0})
    if not agreement_data:
        raise HTTPException(status_code=404, detail="Agreement not found")
    
    # Fetch related data
    lead_data = await db.leads.find_one({"id": agreement_data['lead_id']}, {"_id": 0})
    if not lead_data:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    quotation_data = await db.quotations.find_one({"id": agreement_data['quotation_id']}, {"_id": 0})
    if not quotation_data:
        quotation_data = {}
    
    # Get email template
    template_data = await db.email_notification_templates.find_one(
        {"id": email_data.email_template_id}, 
        {"_id": 0}
    )
    if not template_data:
        raise HTTPException(status_code=404, detail="Email template not found")
    
    # Prepare substitution data
    substitution_data = prepare_agreement_email_data(
        agreement_data,
        lead_data,
        quotation_data,
        current_user.model_dump()
    )
    
    # Use custom subject/body if provided, otherwise use template
    subject = email_data.custom_subject or template_data['subject']
    body = email_data.custom_body or template_data['body']
    
    # Substitute variables
    final_subject = substitute_variables(subject, substitution_data)
    final_body = substitute_variables(body, substitution_data)
    
    # Initialize email service with user's email
    # For testing, use mock service. In production, use real SMTP
    use_mock = os.environ.get('USE_MOCK_EMAIL', 'true').lower() == 'true'
    
    if use_mock:
        EmailServiceClass = create_mock_email_service()
    else:
        EmailServiceClass = EmailService
    
    email_service = EmailServiceClass(
        sender_email=current_user.email,
        sender_password=None  # Will use environment variable SMTP_PASSWORD
    )
    
    # Send email
    result = email_service.send_email(
        to_email=email_data.recipient_email,
        subject=final_subject,
        body=final_body,
        cc_emails=email_data.cc_emails,
        attachment_path=email_data.attachment_url,
        attachment_name=f"Agreement_{agreement_data['agreement_number']}.pdf"
    )
    
    # Log email send
    await db.communication_logs.insert_one({
        "id": str(uuid.uuid4()),
        "lead_id": agreement_data['lead_id'],
        "communication_type": "email",
        "notes": f"Agreement email sent: {final_subject}",
        "outcome": "sent" if result['success'] else "failed",
        "created_by": current_user.id,
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    return {
        **result,
        "final_subject": final_subject,
        "final_body": final_body
    }

# ==================== CONSULTANT MANAGEMENT APIs ====================

@api_router.post("/consultants", response_model=User)
async def create_consultant(user_create: UserCreate, current_user: User = Depends(get_current_user)):
    """Create a new consultant (Admin only)"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only admins can create consultant accounts")
    
    # Force role to consultant
    existing_user = await db.users.find_one({"email": user_create.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Sanitize user input to prevent XSS
    sanitized_name = sanitize_text(user_create.full_name)
    sanitized_dept = sanitize_text(user_create.department) if user_create.department else None
    
    hashed_password = get_password_hash(user_create.password)
    user = User(
        email=user_create.email,
        full_name=sanitized_name,
        role=UserRole.CONSULTANT,
        department=sanitized_dept
    )
    
    user_dict = user.model_dump()
    user_dict['hashed_password'] = hashed_password
    user_dict['created_at'] = user_dict['created_at'].isoformat()
    
    await db.users.insert_one(user_dict)
    
    # Create consultant profile with bandwidth settings
    preferred_mode = "mixed"
    max_projects = CONSULTANT_BANDWIDTH_LIMITS.get(preferred_mode, 8)
    
    profile = {
        "user_id": user.id,
        "specializations": [],
        "preferred_mode": preferred_mode,
        "max_projects": max_projects,
        "current_project_count": 0,
        "total_project_value": 0,
        "bio": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    await db.consultant_profiles.insert_one(profile)
    
    return user

@api_router.get("/consultants")
async def get_consultants(current_user: User = Depends(get_current_user)):
    """Get all consultants with their project stats"""
    # Allow admin, managers, and HR managers (read-only for workload view)
    allowed_roles = [UserRole.ADMIN, UserRole.MANAGER, UserRole.HR_MANAGER]
    if current_user.role not in allowed_roles:
        raise HTTPException(status_code=403, detail="Only admins, managers, and HR managers can view consultant list")
    
    # Get all consultant users
    consultants = await db.users.find(
        {"role": UserRole.CONSULTANT, "is_active": True},
        {"_id": 0, "hashed_password": 0}
    ).to_list(1000)
    
    result = []
    for consultant in consultants:
        # Get consultant profile
        profile = await db.consultant_profiles.find_one(
            {"user_id": consultant['id']},
            {"_id": 0}
        )
        
        # Get active project assignments
        assignments = await db.consultant_assignments.find(
            {"consultant_id": consultant['id'], "is_active": True},
            {"_id": 0}
        ).to_list(100)
        
        # Calculate stats
        project_ids = [a['project_id'] for a in assignments]
        projects = await db.projects.find(
            {"id": {"$in": project_ids}},
            {"_id": 0}
        ).to_list(100)
        
        total_value = sum(p.get('project_value', 0) or 0 for p in projects)
        total_meetings_committed = sum(a.get('meetings_committed', 0) for a in assignments)
        total_meetings_completed = sum(a.get('meetings_completed', 0) for a in assignments)
        
        # Calculate bandwidth
        max_projects = profile.get('max_projects', 8) if profile else 8
        current_count = len(assignments)
        available_slots = max(0, max_projects - current_count)
        
        result.append({
            **consultant,
            "profile": profile,
            "stats": {
                "total_projects": current_count,
                "total_project_value": total_value,
                "total_meetings_committed": total_meetings_committed,
                "total_meetings_completed": total_meetings_completed,
                "max_projects": max_projects,
                "available_slots": available_slots,
                "bandwidth_percentage": round((current_count / max_projects) * 100) if max_projects > 0 else 0
            },
            "assignments": assignments
        })
    
    return result

@api_router.get("/consultants/{consultant_id}")
async def get_consultant(consultant_id: str, current_user: User = Depends(get_current_user)):
    """Get consultant details with projects"""
    # Consultants can view their own profile, admins/managers can view all
    if current_user.role == UserRole.CONSULTANT and current_user.id != consultant_id:
        raise HTTPException(status_code=403, detail="You can only view your own profile")
    
    consultant = await db.users.find_one(
        {"id": consultant_id, "role": UserRole.CONSULTANT},
        {"_id": 0, "hashed_password": 0}
    )
    if not consultant:
        raise HTTPException(status_code=404, detail="Consultant not found")
    
    # Get profile
    profile = await db.consultant_profiles.find_one(
        {"user_id": consultant_id},
        {"_id": 0}
    )
    
    # Get assignments with project details
    assignments = await db.consultant_assignments.find(
        {"consultant_id": consultant_id},
        {"_id": 0}
    ).to_list(100)
    
    projects_with_details = []
    for assignment in assignments:
        project = await db.projects.find_one(
            {"id": assignment['project_id']},
            {"_id": 0}
        )
        if project:
            projects_with_details.append({
                "assignment": assignment,
                "project": project
            })
    
    return {
        **consultant,
        "profile": profile,
        "projects": projects_with_details
    }

@api_router.patch("/consultants/{consultant_id}/profile")
async def update_consultant_profile(
    consultant_id: str,
    preferred_mode: Optional[str] = None,
    specializations: Optional[List[str]] = None,
    bio: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Update consultant profile (Admin only for bandwidth, consultant can update bio)"""
    if current_user.role != UserRole.ADMIN and current_user.id != consultant_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    update_data = {"updated_at": datetime.now(timezone.utc).isoformat()}
    
    if preferred_mode and current_user.role == UserRole.ADMIN:
        update_data["preferred_mode"] = preferred_mode
        update_data["max_projects"] = CONSULTANT_BANDWIDTH_LIMITS.get(preferred_mode, 8)
    
    if specializations is not None:
        update_data["specializations"] = specializations
    
    if bio is not None:
        update_data["bio"] = bio
    
    await db.consultant_profiles.update_one(
        {"user_id": consultant_id},
        {"$set": update_data}
    )
    
    return {"message": "Profile updated successfully"}

# ==================== PROJECT ASSIGNMENT APIs ====================

@api_router.post("/projects/{project_id}/assign-consultant")
async def assign_consultant_to_project(
    project_id: str,
    assignment: ConsultantAssignmentCreate,
    current_user: User = Depends(get_current_user)
):
    """Assign a consultant to a project - Only PM, Principal Consultant, and Admin can assign"""
    # Team Assignment is a Consulting function - HR cannot assign consultants
    allowed_roles = [UserRole.ADMIN, UserRole.MANAGER, UserRole.PROJECT_MANAGER, UserRole.PRINCIPAL_CONSULTANT]
    if current_user.role not in allowed_roles:
        raise HTTPException(status_code=403, detail="Only Admin, Project Manager, or Principal Consultant can assign consultants")
    
    # Verify project exists
    project = await db.projects.find_one({"id": project_id}, {"_id": 0})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Verify consultant exists and is active
    consultant = await db.users.find_one(
        {"id": assignment.consultant_id, "role": UserRole.CONSULTANT, "is_active": True},
        {"_id": 0}
    )
    if not consultant:
        raise HTTPException(status_code=404, detail="Consultant not found or inactive")
    
    # Check consultant bandwidth
    profile = await db.consultant_profiles.find_one({"user_id": assignment.consultant_id}, {"_id": 0})
    active_assignments = await db.consultant_assignments.count_documents({
        "consultant_id": assignment.consultant_id,
        "is_active": True
    })
    
    max_projects = profile.get('max_projects', 8) if profile else 8
    if active_assignments >= max_projects:
        raise HTTPException(
            status_code=400, 
            detail=f"Consultant has reached maximum project capacity ({max_projects})"
        )
    
    # Check if already assigned
    existing = await db.consultant_assignments.find_one({
        "consultant_id": assignment.consultant_id,
        "project_id": project_id,
        "is_active": True
    })
    if existing:
        raise HTTPException(status_code=400, detail="Consultant already assigned to this project")
    
    # Create assignment
    new_assignment = ConsultantAssignment(
        consultant_id=assignment.consultant_id,
        project_id=project_id,
        assigned_by=current_user.id,
        role_in_project=assignment.role_in_project,
        meetings_committed=assignment.meetings_committed,
        notes=assignment.notes
    )
    
    doc = new_assignment.model_dump()
    doc['assigned_date'] = doc['assigned_date'].isoformat()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    
    await db.consultant_assignments.insert_one(doc)
    
    # Update project's assigned_consultants list
    await db.projects.update_one(
        {"id": project_id},
        {
            "$addToSet": {"assigned_consultants": assignment.consultant_id},
            "$set": {"updated_at": datetime.now(timezone.utc).isoformat()}
        }
    )
    
    # Create notification for consultant and their reporting manager
    notification_doc = {
        "id": str(uuid.uuid4()),
        "type": "project_assignment",
        "title": "New Project Assignment",
        "message": f"You have been assigned to project: {project.get('name')}",
        "recipient_id": assignment.consultant_id,
        "project_id": project_id,
        "read": False,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.notifications.insert_one(notification_doc)
    
    # Notify reporting manager
    if consultant.get('reporting_manager_id'):
        manager_notification = {
            "id": str(uuid.uuid4()),
            "type": "reportee_assignment",
            "title": "Reportee Assigned to Project",
            "message": f"{consultant.get('full_name')} has been assigned to project: {project.get('name')}",
            "recipient_id": consultant.get('reporting_manager_id'),
            "project_id": project_id,
            "consultant_id": assignment.consultant_id,
            "read": False,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.notifications.insert_one(manager_notification)
    
    return {"message": "Consultant assigned successfully", "assignment_id": new_assignment.id}

@api_router.patch("/projects/{project_id}/change-consultant")
async def change_consultant(
    project_id: str,
    old_consultant_id: str,
    new_consultant_id: str,
    current_user: User = Depends(get_current_user)
):
    """Change consultant on a project (before start date) - Only PM, Principal Consultant, and Admin"""
    allowed_roles = [UserRole.ADMIN, UserRole.MANAGER, UserRole.PROJECT_MANAGER, UserRole.PRINCIPAL_CONSULTANT]
    if current_user.role not in allowed_roles:
        raise HTTPException(status_code=403, detail="Only Admin, Project Manager, or Principal Consultant can change consultants")
    
    # Get project
    project = await db.projects.find_one({"id": project_id}, {"_id": 0})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Check if project has started (only admin can change after start)
    start_date = project.get('start_date')
    if isinstance(start_date, str):
        start_date = datetime.fromisoformat(start_date)
    
    if start_date and start_date <= datetime.now(timezone.utc):
        if current_user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=403, 
                detail="Only admins can change consultants after project start date"
            )
    
    # Verify new consultant
    new_consultant = await db.users.find_one(
        {"id": new_consultant_id, "role": UserRole.CONSULTANT, "is_active": True}
    )
    if not new_consultant:
        raise HTTPException(status_code=404, detail="New consultant not found")
    
    # Check new consultant's bandwidth
    profile = await db.consultant_profiles.find_one({"user_id": new_consultant_id}, {"_id": 0})
    active_count = await db.consultant_assignments.count_documents({
        "consultant_id": new_consultant_id,
        "is_active": True
    })
    max_projects = profile.get('max_projects', 8) if profile else 8
    
    if active_count >= max_projects:
        raise HTTPException(status_code=400, detail="New consultant has reached maximum capacity")
    
    # Deactivate old assignment
    await db.consultant_assignments.update_one(
        {"consultant_id": old_consultant_id, "project_id": project_id, "is_active": True},
        {"$set": {"is_active": False, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    # Create new assignment
    new_assignment = ConsultantAssignment(
        consultant_id=new_consultant_id,
        project_id=project_id,
        assigned_by=current_user.id,
        notes=f"Replaced {old_consultant_id}"
    )
    
    doc = new_assignment.model_dump()
    doc['assigned_date'] = doc['assigned_date'].isoformat()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    
    await db.consultant_assignments.insert_one(doc)
    
    # Update project
    await db.projects.update_one(
        {"id": project_id},
        {
            "$pull": {"assigned_consultants": old_consultant_id},
            "$addToSet": {"assigned_consultants": new_consultant_id},
            "$set": {"updated_at": datetime.now(timezone.utc).isoformat()}
        }
    )
    
    return {"message": "Consultant changed successfully"}

@api_router.patch("/projects/{project_id}/update-start-date")
async def update_project_start_date(
    project_id: str,
    new_start_date: datetime,
    current_user: User = Depends(get_current_user)
):
    """Update project start date (Admin only)"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only admins can change project start date")
    
    result = await db.projects.update_one(
        {"id": project_id},
        {"$set": {
            "start_date": new_start_date.isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Project not found")
    
    return {"message": "Start date updated successfully"}

@api_router.delete("/projects/{project_id}/unassign-consultant/{consultant_id}")
async def unassign_consultant(
    project_id: str,
    consultant_id: str,
    current_user: User = Depends(get_current_user)
):
    """Remove consultant from project - Only PM, Principal Consultant, and Admin can unassign"""
    allowed_roles = [UserRole.ADMIN, UserRole.MANAGER, UserRole.PROJECT_MANAGER, UserRole.PRINCIPAL_CONSULTANT]
    if current_user.role not in allowed_roles:
        raise HTTPException(status_code=403, detail="Only Admin, Project Manager, or Principal Consultant can unassign consultants")
    
    result = await db.consultant_assignments.update_one(
        {"consultant_id": consultant_id, "project_id": project_id, "is_active": True},
        {"$set": {"is_active": False, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Assignment not found")
    
    # Update project
    await db.projects.update_one(
        {"id": project_id},
        {
            "$pull": {"assigned_consultants": consultant_id},
            "$set": {"updated_at": datetime.now(timezone.utc).isoformat()}
        }
    )
    
    return {"message": "Consultant unassigned successfully"}


# ==================== TIMESHEET SYSTEM ====================

class TimesheetCreate(BaseModel):
    """Create or update a timesheet"""
    model_config = ConfigDict(extra="ignore")
    week_start: str  # YYYY-MM-DD
    entries: dict  # {project_id: {date: hours}}
    notes: Optional[dict] = {}  # {project_id: note}
    status: str = "draft"  # draft, submitted


@api_router.get("/timesheets")
async def get_timesheet(
    week_start: str,
    current_user: User = Depends(get_current_user)
):
    """Get timesheet for a specific week"""
    timesheet = await db.timesheets.find_one({
        "user_id": current_user.id,
        "week_start": week_start
    }, {"_id": 0})
    
    return timesheet


@api_router.post("/timesheets")
async def save_timesheet(
    timesheet: TimesheetCreate,
    current_user: User = Depends(get_current_user)
):
    """Save or update a timesheet"""
    # Check if timesheet exists
    existing = await db.timesheets.find_one({
        "user_id": current_user.id,
        "week_start": timesheet.week_start
    })
    
    if existing and existing.get("status") == "approved":
        raise HTTPException(status_code=400, detail="Cannot modify approved timesheet")
    
    # Calculate total hours
    total_hours = 0
    for project_id, dates in timesheet.entries.items():
        for date, hours in dates.items():
            total_hours += hours
    
    timesheet_data = {
        "user_id": current_user.id,
        "week_start": timesheet.week_start,
        "entries": timesheet.entries,
        "notes": timesheet.notes,
        "status": timesheet.status,
        "total_hours": total_hours,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    if existing:
        await db.timesheets.update_one(
            {"user_id": current_user.id, "week_start": timesheet.week_start},
            {"$set": timesheet_data}
        )
    else:
        timesheet_data["id"] = str(uuid.uuid4())
        timesheet_data["created_at"] = datetime.now(timezone.utc).isoformat()
        await db.timesheets.insert_one(timesheet_data)
    
    # If submitted, create approval request
    if timesheet.status == "submitted":
        await create_approval_request(
            approval_type=ApprovalType.TIMESHEET,
            reference_id=timesheet_data.get("id") or existing.get("id"),
            reference_title=f"Timesheet Week: {timesheet.week_start} ({total_hours}h)",
            requester_id=current_user.id,
            requires_hr_approval=False,
            requires_admin_approval=True
        )
    
    return {"message": f"Timesheet {'updated' if existing else 'created'} successfully"}


@api_router.get("/timesheets/all")
async def get_all_timesheets(
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get all timesheets (HR/Admin only)"""
    if current_user.role not in [UserRole.ADMIN, UserRole.HR_MANAGER]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    query = {}
    if status:
        query["status"] = status
    
    timesheets = await db.timesheets.find(query, {"_id": 0}).sort("week_start", -1).to_list(200)
    
    # Enrich with user info
    for ts in timesheets:
        user = await db.users.find_one({"id": ts["user_id"]}, {"_id": 0, "email": 1, "full_name": 1})
        if user:
            ts["user_name"] = user.get("full_name", user.get("email"))
    
    return timesheets


@api_router.post("/timesheets/{timesheet_id}/approve")
async def approve_timesheet(
    timesheet_id: str,
    current_user: User = Depends(get_current_user)
):
    """Approve a timesheet"""
    if current_user.role not in [UserRole.ADMIN, UserRole.HR_MANAGER, UserRole.PROJECT_MANAGER]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    result = await db.timesheets.update_one(
        {"id": timesheet_id},
        {"$set": {
            "status": "approved",
            "approved_by": current_user.id,
            "approved_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Timesheet not found")
    
    return {"message": "Timesheet approved"}


# ==================== CONSULTANT DASHBOARD APIs ====================

@api_router.get("/consultant/my-projects")
async def get_my_projects(current_user: User = Depends(get_current_user)):
    """Get projects assigned to current consultant"""
    if current_user.role != UserRole.CONSULTANT:
        raise HTTPException(status_code=403, detail="Only consultants can access this endpoint")
    
    assignments = await db.consultant_assignments.find(
        {"consultant_id": current_user.id, "is_active": True},
        {"_id": 0}
    ).to_list(100)
    
    projects_with_details = []
    for assignment in assignments:
        project = await db.projects.find_one(
            {"id": assignment['project_id']},
            {"_id": 0}
        )
        if project:
            # Get lead/client info
            lead = None
            if project.get('lead_id'):
                lead = await db.leads.find_one(
                    {"id": project['lead_id']},
                    {"_id": 0, "first_name": 1, "last_name": 1, "company": 1, "email": 1}
                )
            
            projects_with_details.append({
                "assignment": assignment,
                "project": project,
                "client": lead
            })
    
    return projects_with_details

@api_router.get("/consultant/dashboard-stats")
async def get_consultant_dashboard_stats(current_user: User = Depends(get_current_user)):
    """Get dashboard stats for consultant"""
    if current_user.role != UserRole.CONSULTANT:
        raise HTTPException(status_code=403, detail="Only consultants can access this endpoint")
    
    # Get active assignments
    assignments = await db.consultant_assignments.find(
        {"consultant_id": current_user.id, "is_active": True},
        {"_id": 0}
    ).to_list(100)
    
    project_ids = [a['project_id'] for a in assignments]
    projects = await db.projects.find(
        {"id": {"$in": project_ids}},
        {"_id": 0}
    ).to_list(100)
    
    # Calculate stats
    total_meetings_committed = sum(a.get('meetings_committed', 0) for a in assignments)
    total_meetings_completed = sum(a.get('meetings_completed', 0) for a in assignments)
    total_project_value = sum(p.get('project_value', 0) or 0 for p in projects)
    
    active_projects = len([p for p in projects if p.get('status') == 'active'])
    completed_projects = len([p for p in projects if p.get('status') == 'completed'])
    
    # Get profile for bandwidth
    profile = await db.consultant_profiles.find_one(
        {"user_id": current_user.id},
        {"_id": 0}
    )
    max_projects = profile.get('max_projects', 8) if profile else 8
    
    return {
        "total_projects": len(assignments),
        "active_projects": active_projects,
        "completed_projects": completed_projects,
        "total_project_value": total_project_value,
        "total_meetings_committed": total_meetings_committed,
        "total_meetings_completed": total_meetings_completed,
        "meetings_pending": total_meetings_committed - total_meetings_completed,
        "max_projects": max_projects,
        "available_slots": max(0, max_projects - len(assignments)),
        "bandwidth_percentage": round((len(assignments) / max_projects) * 100) if max_projects > 0 else 0
    }

# ==================== TASK MANAGEMENT APIs ====================

class TaskStatus(str):
    TO_DO = "to_do"
    OWN_TASK = "own_task"
    IN_PROGRESS = "in_progress"
    DELEGATED = "delegated"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class TaskCategory(str):
    GENERAL = "general"
    MEETING = "meeting"
    DELIVERABLE = "deliverable"
    REVIEW = "review"
    FOLLOW_UP = "follow_up"
    ADMIN = "admin"
    CLIENT_COMMUNICATION = "client_communication"

class Task(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    project_id: str
    title: str
    description: Optional[str] = None
    category: str = TaskCategory.GENERAL
    status: str = TaskStatus.TO_DO
    priority: str = "medium"  # low, medium, high, urgent
    assigned_to: Optional[str] = None  # consultant user id
    delegated_to: Optional[str] = None  # if delegated
    sow_id: Optional[str] = None  # Link to SOW
    sow_item_id: Optional[str] = None  # Link to specific SOW item
    sow_item_title: Optional[str] = None  # SOW item title for display
    start_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    completed_date: Optional[datetime] = None
    estimated_hours: Optional[float] = None
    actual_hours: Optional[float] = None
    dependencies: List[str] = []  # task ids this depends on
    order: int = 0  # for gantt chart ordering
    created_by: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class TaskCreate(BaseModel):
    project_id: str
    title: str
    description: Optional[str] = None
    category: Optional[str] = TaskCategory.GENERAL
    status: Optional[str] = TaskStatus.TO_DO
    priority: Optional[str] = "medium"
    assigned_to: Optional[str] = None
    sow_id: Optional[str] = None
    sow_item_id: Optional[str] = None
    sow_item_title: Optional[str] = None
    start_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    estimated_hours: Optional[float] = None
    dependencies: Optional[List[str]] = []
    order: Optional[int] = 0

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    assigned_to: Optional[str] = None
    delegated_to: Optional[str] = None
    sow_id: Optional[str] = None
    sow_item_id: Optional[str] = None
    sow_item_title: Optional[str] = None
    start_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    completed_date: Optional[datetime] = None
    estimated_hours: Optional[float] = None
    actual_hours: Optional[float] = None
    order: Optional[int] = None

@api_router.post("/tasks", response_model=Task)
async def create_task(task_create: TaskCreate, current_user: User = Depends(get_current_user)):
    """Create a new task for a project"""
    # Verify project exists
    project = await db.projects.find_one({"id": task_create.project_id}, {"_id": 0})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    task_dict = task_create.model_dump()
    task = Task(**task_dict, created_by=current_user.id)
    
    doc = task.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    if doc['start_date']:
        doc['start_date'] = doc['start_date'].isoformat()
    if doc['due_date']:
        doc['due_date'] = doc['due_date'].isoformat()
    if doc['completed_date']:
        doc['completed_date'] = doc['completed_date'].isoformat()
    
    await db.tasks.insert_one(doc)
    return task

@api_router.get("/tasks")
async def get_tasks(
    project_id: Optional[str] = None,
    assigned_to: Optional[str] = None,
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get tasks with optional filters"""
    query = {}
    if project_id:
        query['project_id'] = project_id
    if assigned_to:
        query['assigned_to'] = assigned_to
    if status:
        query['status'] = status
    
    tasks = await db.tasks.find(query, {"_id": 0}).sort("order", 1).to_list(1000)
    
    for task in tasks:
        if isinstance(task.get('created_at'), str):
            task['created_at'] = datetime.fromisoformat(task['created_at'])
        if isinstance(task.get('updated_at'), str):
            task['updated_at'] = datetime.fromisoformat(task['updated_at'])
        if task.get('start_date') and isinstance(task['start_date'], str):
            task['start_date'] = datetime.fromisoformat(task['start_date'])
        if task.get('due_date') and isinstance(task['due_date'], str):
            task['due_date'] = datetime.fromisoformat(task['due_date'])
        if task.get('completed_date') and isinstance(task['completed_date'], str):
            task['completed_date'] = datetime.fromisoformat(task['completed_date'])
    
    return tasks

@api_router.get("/tasks/{task_id}")
async def get_task(task_id: str, current_user: User = Depends(get_current_user)):
    """Get a single task"""
    task = await db.tasks.find_one({"id": task_id}, {"_id": 0})
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if isinstance(task.get('created_at'), str):
        task['created_at'] = datetime.fromisoformat(task['created_at'])
    if isinstance(task.get('updated_at'), str):
        task['updated_at'] = datetime.fromisoformat(task['updated_at'])
    if task.get('start_date') and isinstance(task['start_date'], str):
        task['start_date'] = datetime.fromisoformat(task['start_date'])
    if task.get('due_date') and isinstance(task['due_date'], str):
        task['due_date'] = datetime.fromisoformat(task['due_date'])
    
    return task

@api_router.patch("/tasks/{task_id}")
async def update_task(
    task_id: str,
    task_update: TaskUpdate,
    current_user: User = Depends(get_current_user)
):
    """Update a task"""
    task = await db.tasks.find_one({"id": task_id}, {"_id": 0})
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    update_data = task_update.model_dump(exclude_unset=True)
    update_data['updated_at'] = datetime.now(timezone.utc).isoformat()
    
    # Handle status changes
    if 'status' in update_data:
        if update_data['status'] == TaskStatus.COMPLETED and not update_data.get('completed_date'):
            update_data['completed_date'] = datetime.now(timezone.utc).isoformat()
        # Notify reporting manager + admin on status changes
        old_status = task.get('status', '')
        new_status = update_data['status']
        if old_status != new_status:
            task_title = task.get('title', 'Task')
            project = await db.projects.find_one({"id": task.get('project_id')}, {"_id": 0, "name": 1})
            proj_name = project.get('name', '') if project else ''
            # Notify assigned consultant's reporting manager
            if task.get('assigned_to'):
                chain = await get_reporting_chain(task['assigned_to'], max_levels=2)
                for rm in chain:
                    if rm.get('user_id'):
                        await db.notifications.insert_one({
                            "id": str(uuid.uuid4()), "user_id": rm['user_id'],
                            "type": "task_status_change",
                            "title": f"Task {new_status.replace('_', ' ').title()}: {task_title}",
                            "message": f"'{task_title}' in {proj_name} changed from {old_status.replace('_', ' ')} to {new_status.replace('_', ' ')}.",
                            "reference_type": "task", "reference_id": task['id'],
                            "is_read": False, "created_at": datetime.now(timezone.utc).isoformat()
                        })
            # Notify admin on delayed/overdue
            if new_status in ['delayed', 'cancelled']:
                await notify_admins(
                    notif_type="task_alert",
                    title=f"Task {new_status.title()}: {task_title}",
                    message=f"'{task_title}' in {proj_name} is now {new_status}.",
                    reference_type="task", reference_id=task['id']
                )
    
    # Handle datetime fields
    if 'start_date' in update_data and update_data['start_date']:
        update_data['start_date'] = update_data['start_date'].isoformat()
    if 'due_date' in update_data and update_data['due_date']:
        update_data['due_date'] = update_data['due_date'].isoformat()
    if 'completed_date' in update_data and update_data['completed_date']:
        update_data['completed_date'] = update_data['completed_date'].isoformat()
    
    await db.tasks.update_one({"id": task_id}, {"$set": update_data})
    
    return {"message": "Task updated successfully"}

@api_router.delete("/tasks/{task_id}")
async def delete_task(task_id: str, current_user: User = Depends(get_current_user)):
    """Delete a task"""
    result = await db.tasks.delete_one({"id": task_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return {"message": "Task deleted successfully"}

@api_router.patch("/tasks/{task_id}/delegate")
async def delegate_task(
    task_id: str,
    delegated_to: str,
    current_user: User = Depends(get_current_user)
):
    """Delegate a task to another user"""
    task = await db.tasks.find_one({"id": task_id}, {"_id": 0})
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Verify target user exists
    target_user = await db.users.find_one({"id": delegated_to}, {"_id": 0})
    if not target_user:
        raise HTTPException(status_code=404, detail="Target user not found")
    
    await db.tasks.update_one(
        {"id": task_id},
        {"$set": {
            "delegated_to": delegated_to,
            "status": TaskStatus.DELEGATED,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    return {"message": "Task delegated successfully"}

@api_router.patch("/tasks/reorder")
async def reorder_tasks(
    task_orders: List[dict],  # [{"id": "task_id", "order": 1}, ...]
    current_user: User = Depends(get_current_user)
):
    """Reorder tasks (for drag-and-drop in Gantt chart)"""
    for item in task_orders:
        await db.tasks.update_one(
            {"id": item['id']},
            {"$set": {"order": item['order'], "updated_at": datetime.now(timezone.utc).isoformat()}}
        )
    
    return {"message": "Tasks reordered successfully"}

@api_router.patch("/tasks/{task_id}/dates")
async def update_task_dates(task_id: str, data: dict, current_user: User = Depends(get_current_user)):
    """Update task start/end dates (for Gantt chart drag-and-drop)"""
    task = await db.tasks.find_one({"id": task_id}, {"_id": 0})
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    update = {"updated_at": datetime.now(timezone.utc).isoformat()}
    if "start_date" in data:
        update["start_date"] = data["start_date"]
    if "end_date" in data or "due_date" in data:
        update["due_date"] = data.get("due_date") or data.get("end_date")
    await db.tasks.update_one({"id": task_id}, {"$set": update})
    return {"message": "Task dates updated"}

@api_router.get("/projects/{project_id}/tasks-gantt")
async def get_project_tasks_for_gantt(
    project_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get tasks formatted for Gantt chart, grouped by SOW item"""
    tasks = await db.tasks.find({"project_id": project_id}, {"_id": 0}).sort("order", 1).to_list(1000)
    
    gantt_data = []
    for task in tasks:
        start = task.get('start_date')
        end = task.get('due_date')
        
        if isinstance(start, str):
            start = datetime.fromisoformat(start)
        if isinstance(end, str):
            end = datetime.fromisoformat(end)
        
        gantt_data.append({
            "id": task['id'],
            "name": task['title'],
            "start": start.isoformat() if start else None,
            "end": end.isoformat() if end else None,
            "status": task.get('status', 'to_do'),
            "category": task.get('category', 'general'),
            "priority": task.get('priority', 'medium'),
            "assigned_to": task.get('assigned_to'),
            "sow_id": task.get('sow_id'),
            "sow_item_id": task.get('sow_item_id'),
            "sow_item_title": task.get('sow_item_title', ''),
            "dependencies": task.get('dependencies', []),
            "progress": 100 if task.get('status') == TaskStatus.COMPLETED else 
                       50 if task.get('status') == TaskStatus.IN_PROGRESS else 0
        })
    
    return gantt_data


# --- SOW Progress (calculated from linked tasks) ---
@api_router.get("/sow/{sow_id}/progress")
async def get_sow_progress(sow_id: str, current_user: User = Depends(get_current_user)):
    """Get progress of each SOW item based on linked tasks"""
    sow = await db.sows.find_one({"id": sow_id}, {"_id": 0})
    if not sow:
        raise HTTPException(status_code=404, detail="SOW not found")
    tasks = await db.tasks.find({"sow_id": sow_id}, {"_id": 0}).to_list(500)
    item_progress = {}
    for task in tasks:
        item_id = task.get('sow_item_id', 'unlinked')
        if item_id not in item_progress:
            item_progress[item_id] = {"total": 0, "completed": 0, "in_progress": 0, "delayed": 0}
        item_progress[item_id]["total"] += 1
        if task.get('status') == 'completed':
            item_progress[item_id]["completed"] += 1
        elif task.get('status') == 'in_progress':
            item_progress[item_id]["in_progress"] += 1
        elif task.get('status') == 'delayed':
            item_progress[item_id]["delayed"] += 1
    result = []
    for item in sow.get('items', []):
        prog = item_progress.get(item['id'], {"total": 0, "completed": 0, "in_progress": 0, "delayed": 0})
        pct = round(prog["completed"] / prog["total"] * 100) if prog["total"] > 0 else 0
        result.append({
            "sow_item_id": item['id'], "title": item.get('title', ''), "status": item.get('status', ''),
            "total_tasks": prog["total"], "completed_tasks": prog["completed"],
            "in_progress_tasks": prog["in_progress"], "delayed_tasks": prog["delayed"],
            "progress_percent": pct
        })
    return {"sow_id": sow_id, "sow_title": sow.get('title', ''), "items": result}


# --- Client Communication Log ---
@api_router.post("/client-communications")
async def create_client_communication(data: dict, current_user: User = Depends(get_current_user)):
    """Log a communication sent to client (manual or auto-generated)"""
    comm = {
        "id": str(uuid.uuid4()),
        "project_id": data.get("project_id"),
        "sow_id": data.get("sow_id"),
        "client_id": data.get("client_id"),
        "client_name": data.get("client_name", ""),
        "type": data.get("type", "progress_update"),  # progress_update, manual_update, escalation
        "subject": data.get("subject", ""),
        "message": data.get("message", ""),
        "sow_progress": data.get("sow_progress"),  # optional progress snapshot
        "sent_via": data.get("sent_via", "email"),
        "sent_by": current_user.id,
        "sent_by_name": current_user.full_name,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.client_communications.insert_one(comm)
    # Log email (MOCKED)
    print(f"[CLIENT EMAIL] To: {comm['client_name']} | Subject: {comm['subject']} | By: {current_user.full_name}")
    # Notify admins
    await notify_admins(
        notif_type="client_communication",
        title=f"Client Update Sent: {comm['client_name']}",
        message=f"{current_user.full_name} sent '{comm['subject']}' to {comm['client_name']}.",
        reference_type="client_communication", reference_id=comm['id']
    )
    return {"message": "Communication logged", "id": comm['id']}

@api_router.get("/client-communications")
async def get_client_communications(
    project_id: Optional[str] = None,
    sow_id: Optional[str] = None,
    client_id: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get client communication log"""
    query = {}
    if project_id: query["project_id"] = project_id
    if sow_id: query["sow_id"] = sow_id
    if client_id: query["client_id"] = client_id
    comms = await db.client_communications.find(query, {"_id": 0}).sort("created_at", -1).to_list(200)
    return comms


@api_router.post("/sow/{sow_id}/send-progress-report")
async def send_sow_progress_report(sow_id: str, data: dict, current_user: User = Depends(get_current_user)):
    """Generate and send SOW progress report to client"""
    sow = await db.sows.find_one({"id": sow_id}, {"_id": 0})
    if not sow:
        raise HTTPException(status_code=404, detail="SOW not found")
    # Get progress
    tasks = await db.tasks.find({"sow_id": sow_id}, {"_id": 0}).to_list(500)
    total_tasks = len(tasks)
    completed = sum(1 for t in tasks if t.get('status') == 'completed')
    delayed = sum(1 for t in tasks if t.get('status') == 'delayed')
    overall_pct = round(completed / total_tasks * 100) if total_tasks > 0 else 0
    # Build report
    report_items = []
    for item in sow.get('items', []):
        item_tasks = [t for t in tasks if t.get('sow_item_id') == item['id']]
        item_done = sum(1 for t in item_tasks if t.get('status') == 'completed')
        report_items.append({
            "title": item.get('title', ''),
            "total": len(item_tasks), "completed": item_done,
            "progress": round(item_done / len(item_tasks) * 100) if item_tasks else 0
        })
    client_name = data.get("client_name", "Client")
    subject = data.get("subject", f"Progress Report: {sow.get('title', 'SOW')} - {overall_pct}% Complete")
    message = data.get("message", "")
    # Auto-generate message if empty
    if not message:
        lines = [f"Dear {client_name},\n", f"Please find the progress update for {sow.get('title', 'your project')}:\n",
                 f"Overall Progress: {overall_pct}% ({completed}/{total_tasks} tasks completed)\n"]
        if delayed > 0:
            lines.append(f"Attention: {delayed} task(s) are currently delayed.\n")
        for ri in report_items:
            lines.append(f"- {ri['title']}: {ri['progress']}% ({ri['completed']}/{ri['total']} tasks)")
        lines.append(f"\nBest regards,\n{current_user.full_name}\nD&V Business Consulting")
        message = "\n".join(lines)
    # Save communication log
    comm = {
        "id": str(uuid.uuid4()), "project_id": sow.get('project_id') or sow.get('lead_id'),
        "sow_id": sow_id, "client_id": data.get("client_id"),
        "client_name": client_name, "type": "progress_update",
        "subject": subject, "message": message,
        "sow_progress": {"overall_percent": overall_pct, "total_tasks": total_tasks, "completed": completed, "delayed": delayed, "items": report_items},
        "sent_via": "email", "sent_by": current_user.id, "sent_by_name": current_user.full_name,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.client_communications.insert_one(comm)
    print(f"[CLIENT PROGRESS REPORT] To: {client_name} | {overall_pct}% complete | By: {current_user.full_name}")
    await notify_admins(
        notif_type="client_progress_report", title=f"Progress Report Sent: {sow.get('title', 'SOW')}",
        message=f"{current_user.full_name} sent progress report ({overall_pct}%) to {client_name}.",
        reference_type="sow", reference_id=sow_id
    )
    return {"message": "Progress report sent", "id": comm['id'], "progress": overall_pct}

# ==================== SOW (SCOPE OF WORK) MANAGEMENT ====================

class SOWCategory(str):
    SALES = "sales"
    HR = "hr"
    OPERATIONS = "operations"
    TRAINING = "training"
    ANALYTICS = "analytics"
    DIGITAL_MARKETING = "digital_marketing"

SOW_CATEGORIES = [
    {"value": "sales", "label": "Sales"},
    {"value": "hr", "label": "HR"},
    {"value": "operations", "label": "Operations"},
    {"value": "training", "label": "Training"},
    {"value": "analytics", "label": "Analytics"},
    {"value": "digital_marketing", "label": "Digital Marketing"}
]

class SOWItemDetail(BaseModel):
    """Individual scope item within a category"""
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    description: Optional[str] = None
    deliverables: List[str] = []
    timeline_weeks: Optional[int] = None
    status: str = "planned"  # planned, in_progress, completed
    order: int = 0

class ProjectSOW(BaseModel):
    """Project Scope of Work"""
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    project_id: str
    agreement_id: Optional[str] = None
    category: str  # sales, hr, operations, training, analytics, digital_marketing
    items: List[SOWItemDetail] = []
    is_frozen: bool = False
    frozen_at: Optional[datetime] = None
    frozen_by: Optional[str] = None
    created_by: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class SOWCreate(BaseModel):
    project_id: str
    agreement_id: Optional[str] = None
    category: str
    items: Optional[List[dict]] = []

class SOWItemCreate(BaseModel):
    title: str
    description: Optional[str] = None
    deliverables: Optional[List[str]] = []
    timeline_weeks: Optional[int] = None
    order: Optional[int] = 0

# ==================== KICK-OFF MEETING ====================

class KickoffMeetingAttendee(BaseModel):
    """Attendee for kick-off meeting"""
    user_id: str
    name: str
    email: str
    role: str  # principal_consultant, sales_executive, client_contact, consultant
    is_required: bool = False
    attendance_status: str = "pending"  # pending, confirmed, declined

class KickoffMeeting(BaseModel):
    """Kick-off meeting after agreement approval"""
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    project_id: str
    agreement_id: str
    meeting_date: datetime
    meeting_time: Optional[str] = None
    meeting_mode: str = "online"  # online, offline, mixed
    location: Optional[str] = None
    meeting_link: Optional[str] = None
    agenda: Optional[str] = None
    attendees: List[KickoffMeetingAttendee] = []
    principal_consultant_id: str
    sales_executive_id: str
    status: str = "scheduled"  # scheduled, completed, cancelled
    sow_frozen: bool = False
    notes: Optional[str] = None
    created_by: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class KickoffMeetingCreate(BaseModel):
    project_id: str
    agreement_id: str
    meeting_date: datetime
    meeting_time: Optional[str] = None
    meeting_mode: Optional[str] = "online"
    location: Optional[str] = None
    meeting_link: Optional[str] = None
    agenda: Optional[str] = None
    principal_consultant_id: str
    attendee_ids: Optional[List[str]] = []  # Additional consultant IDs

class Notification(BaseModel):
    """System notification"""
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    title: str
    message: str
    notification_type: str  # kickoff_scheduled, sow_frozen, reminder
    related_entity_type: Optional[str] = None  # project, meeting, agreement
    related_entity_id: Optional[str] = None
    is_read: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# SOW APIs

@api_router.get("/sow-categories")
async def get_sow_categories():
    """Get available SOW categories"""
    return SOW_CATEGORIES

@api_router.post("/projects/{project_id}/sow")
async def create_project_sow(
    project_id: str,
    sow_create: SOWCreate,
    current_user: User = Depends(get_current_user)
):
    """Create SOW for a project category"""
    # Verify project exists
    project = await db.projects.find_one({"id": project_id}, {"_id": 0})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Check if SOW already exists for this category
    existing = await db.project_sow.find_one({
        "project_id": project_id,
        "category": sow_create.category
    })
    if existing:
        raise HTTPException(status_code=400, detail=f"SOW for category '{sow_create.category}' already exists")
    
    # Create SOW items
    items = []
    for idx, item_data in enumerate(sow_create.items or []):
        item = SOWItemDetail(
            title=item_data.get('title', ''),
            description=item_data.get('description'),
            deliverables=item_data.get('deliverables', []),
            timeline_weeks=item_data.get('timeline_weeks'),
            order=idx
        )
        items.append(item.model_dump())
    
    sow = ProjectSOW(
        project_id=project_id,
        agreement_id=sow_create.agreement_id,
        category=sow_create.category,
        items=items,
        created_by=current_user.id
    )
    
    doc = sow.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    if doc['frozen_at']:
        doc['frozen_at'] = doc['frozen_at'].isoformat()
    
    await db.project_sow.insert_one(doc)
    return {"message": "SOW created successfully", "sow_id": sow.id}

@api_router.get("/projects/{project_id}/sow")
async def get_project_sow(
    project_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get all SOW entries for a project"""
    sow_entries = await db.project_sow.find(
        {"project_id": project_id},
        {"_id": 0}
    ).to_list(100)
    
    return sow_entries

@api_router.post("/projects/{project_id}/sow/{sow_id}/items")
async def add_project_sow_item(
    project_id: str,
    sow_id: str,
    item: SOWItemCreate,
    current_user: User = Depends(get_current_user)
):
    """Add item to SOW (only if not frozen, or admin can edit)"""
    sow = await db.project_sow.find_one({"id": sow_id, "project_id": project_id}, {"_id": 0})
    if not sow:
        raise HTTPException(status_code=404, detail="SOW not found")
    
    # Check freeze status
    if sow.get('is_frozen') and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="SOW is frozen. Only Admin can modify.")
    
    new_item = SOWItemDetail(
        title=item.title,
        description=item.description,
        deliverables=item.deliverables or [],
        timeline_weeks=item.timeline_weeks,
        order=item.order
    )
    
    await db.project_sow.update_one(
        {"id": sow_id},
        {
            "$push": {"items": new_item.model_dump()},
            "$set": {"updated_at": datetime.now(timezone.utc).isoformat()}
        }
    )
    
    return {"message": "Item added to SOW", "item_id": new_item.id}

@api_router.patch("/projects/{project_id}/sow/{sow_id}/items/{item_id}")
async def update_project_sow_item(
    project_id: str,
    sow_id: str,
    item_id: str,
    item_update: SOWItemCreate,
    current_user: User = Depends(get_current_user)
):
    """Update SOW item (only if not frozen, or admin can edit)"""
    sow = await db.project_sow.find_one({"id": sow_id, "project_id": project_id}, {"_id": 0})
    if not sow:
        raise HTTPException(status_code=404, detail="SOW not found")
    
    # Check freeze status
    if sow.get('is_frozen') and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="SOW is frozen. Only Admin can modify.")
    
    # Update the specific item
    items = sow.get('items', [])
    updated = False
    for item in items:
        if item.get('id') == item_id:
            item['title'] = item_update.title
            item['description'] = item_update.description
            item['deliverables'] = item_update.deliverables or []
            item['timeline_weeks'] = item_update.timeline_weeks
            updated = True
            break
    
    if not updated:
        raise HTTPException(status_code=404, detail="Item not found")
    
    await db.project_sow.update_one(
        {"id": sow_id},
        {"$set": {"items": items, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    return {"message": "SOW item updated"}

@api_router.delete("/projects/{project_id}/sow/{sow_id}/items/{item_id}")
async def delete_project_sow_item(
    project_id: str,
    sow_id: str,
    item_id: str,
    current_user: User = Depends(get_current_user)
):
    """Delete SOW item (only if not frozen, or admin can edit)"""
    sow = await db.project_sow.find_one({"id": sow_id, "project_id": project_id}, {"_id": 0})
    if not sow:
        raise HTTPException(status_code=404, detail="SOW not found")
    
    # Check freeze status
    if sow.get('is_frozen') and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="SOW is frozen. Only Admin can modify.")
    
    items = [item for item in sow.get('items', []) if item.get('id') != item_id]
    
    await db.project_sow.update_one(
        {"id": sow_id},
        {"$set": {"items": items, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    return {"message": "SOW item deleted"}

# Kick-off Meeting APIs

@api_router.post("/kickoff-meetings")
async def schedule_kickoff_meeting(
    meeting_create: KickoffMeetingCreate,
    current_user: User = Depends(get_current_user)
):
    """Schedule a kick-off meeting (freezes SOW)"""
    # Verify project exists
    project = await db.projects.find_one({"id": meeting_create.project_id}, {"_id": 0})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Verify agreement exists
    agreement = await db.agreements.find_one({"id": meeting_create.agreement_id}, {"_id": 0})
    if not agreement:
        raise HTTPException(status_code=404, detail="Agreement not found")
    
    # Check if kickoff meeting already exists for this project
    existing = await db.kickoff_meetings.find_one({"project_id": meeting_create.project_id})
    if existing:
        raise HTTPException(status_code=400, detail="Kick-off meeting already scheduled for this project")
    
    # Get principal consultant info
    principal = await db.users.find_one(
        {"id": meeting_create.principal_consultant_id},
        {"_id": 0, "hashed_password": 0}
    )
    if not principal:
        raise HTTPException(status_code=404, detail="Principal consultant not found")
    
    # Get sales executive (created_by from agreement)
    sales_exec = await db.users.find_one(
        {"id": agreement.get('created_by')},
        {"_id": 0, "hashed_password": 0}
    )
    
    # Get lead (client contact)
    lead = None
    if agreement.get('lead_id'):
        lead = await db.leads.find_one({"id": agreement['lead_id']}, {"_id": 0})
    
    # Build attendees list
    attendees = [
        KickoffMeetingAttendee(
            user_id=principal['id'],
            name=principal['full_name'],
            email=principal['email'],
            role="principal_consultant",
            is_required=True
        ).model_dump()
    ]
    
    if sales_exec:
        attendees.append(KickoffMeetingAttendee(
            user_id=sales_exec['id'],
            name=sales_exec['full_name'],
            email=sales_exec['email'],
            role="sales_executive",
            is_required=True
        ).model_dump())
    
    if lead:
        attendees.append(KickoffMeetingAttendee(
            user_id=lead['id'],
            name=f"{lead.get('first_name', '')} {lead.get('last_name', '')}",
            email=lead.get('email', ''),
            role="client_contact",
            is_required=True
        ).model_dump())
    
    # Add additional consultants
    for consultant_id in meeting_create.attendee_ids or []:
        consultant = await db.users.find_one(
            {"id": consultant_id},
            {"_id": 0, "hashed_password": 0}
        )
        if consultant:
            attendees.append(KickoffMeetingAttendee(
                user_id=consultant['id'],
                name=consultant['full_name'],
                email=consultant['email'],
                role="consultant",
                is_required=False
            ).model_dump())
    
    meeting = KickoffMeeting(
        project_id=meeting_create.project_id,
        agreement_id=meeting_create.agreement_id,
        meeting_date=meeting_create.meeting_date,
        meeting_time=meeting_create.meeting_time,
        meeting_mode=meeting_create.meeting_mode or "online",
        location=meeting_create.location,
        meeting_link=meeting_create.meeting_link,
        agenda=meeting_create.agenda,
        attendees=attendees,
        principal_consultant_id=meeting_create.principal_consultant_id,
        sales_executive_id=agreement.get('created_by', ''),
        sow_frozen=True,
        created_by=current_user.id
    )
    
    doc = meeting.model_dump()
    doc['meeting_date'] = doc['meeting_date'].isoformat()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    
    await db.kickoff_meetings.insert_one(doc)
    
    # Freeze all SOW entries for this project
    await db.project_sow.update_many(
        {"project_id": meeting_create.project_id},
        {"$set": {
            "is_frozen": True,
            "frozen_at": datetime.now(timezone.utc).isoformat(),
            "frozen_by": current_user.id
        }}
    )
    
    # Create notification for sales executive
    if sales_exec:
        notification = Notification(
            user_id=sales_exec['id'],
            title="Kick-off Meeting Scheduled",
            message=f"Kick-off meeting scheduled for project '{project.get('name')}' on {meeting_create.meeting_date.strftime('%Y-%m-%d')}",
            notification_type="kickoff_scheduled",
            related_entity_type="project",
            related_entity_id=meeting_create.project_id
        )
        
        notif_doc = notification.model_dump()
        notif_doc['created_at'] = notif_doc['created_at'].isoformat()
        await db.notifications.insert_one(notif_doc)
    
    return {"message": "Kick-off meeting scheduled and SOW frozen", "meeting_id": meeting.id}

@api_router.get("/kickoff-meetings")
async def get_kickoff_meetings(
    project_id: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get kick-off meetings"""
    query = {}
    if project_id:
        query['project_id'] = project_id
    
    meetings = await db.kickoff_meetings.find(query, {"_id": 0}).to_list(100)
    
    # Enrich with project and agreement details
    result = []
    for meeting in meetings:
        project = await db.projects.find_one({"id": meeting['project_id']}, {"_id": 0})
        agreement = await db.agreements.find_one({"id": meeting['agreement_id']}, {"_id": 0})
        
        result.append({
            **meeting,
            "project": project,
            "agreement": agreement
        })
    
    return result

@api_router.get("/kickoff-meetings/{meeting_id}")
async def get_kickoff_meeting_detail(
    meeting_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get kick-off meeting with full SOW summary"""
    meeting = await db.kickoff_meetings.find_one({"id": meeting_id}, {"_id": 0})
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    
    # Get project
    project = await db.projects.find_one({"id": meeting['project_id']}, {"_id": 0})
    
    # Get agreement
    agreement = await db.agreements.find_one({"id": meeting['agreement_id']}, {"_id": 0})
    
    # Get quotation (for pricing details)
    quotation = None
    if agreement and agreement.get('quotation_id'):
        quotation = await db.quotations.find_one({"id": agreement['quotation_id']}, {"_id": 0})
    
    # Get pricing plan
    pricing_plan = None
    if quotation and quotation.get('pricing_plan_id'):
        pricing_plan = await db.pricing_plans.find_one({"id": quotation['pricing_plan_id']}, {"_id": 0})
    
    # Get lead (client)
    lead = None
    if agreement and agreement.get('lead_id'):
        lead = await db.leads.find_one({"id": agreement['lead_id']}, {"_id": 0})
    
    # Get SOW entries
    sow_entries = await db.project_sow.find(
        {"project_id": meeting['project_id']},
        {"_id": 0}
    ).to_list(100)
    
    return {
        "meeting": meeting,
        "project": project,
        "agreement": agreement,
        "quotation": quotation,
        "pricing_plan": pricing_plan,
        "lead": lead,
        "sow": sow_entries
    }

@api_router.patch("/kickoff-meetings/{meeting_id}/complete")
async def complete_kickoff_meeting(
    meeting_id: str,
    notes: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Mark kick-off meeting as completed"""
    result = await db.kickoff_meetings.update_one(
        {"id": meeting_id},
        {"$set": {
            "status": "completed",
            "notes": notes,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Meeting not found")
    
    return {"message": "Meeting marked as completed"}

# Notification APIs

@api_router.get("/notifications")
async def get_user_notifications(
    current_user: User = Depends(get_current_user)
):
    """Get notifications for current user"""
    notifications = await db.notifications.find(
        {"user_id": current_user.id},
        {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    
    return notifications

@api_router.patch("/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: str,
    current_user: User = Depends(get_current_user)
):
    """Mark notification as read"""
    await db.notifications.update_one(
        {"id": notification_id, "user_id": current_user.id},
        {"$set": {"is_read": True}}
    )
    return {"message": "Notification marked as read"}

@api_router.get("/notifications/unread-count")
async def get_unread_notification_count(
    current_user: User = Depends(get_current_user)
):
    """Get count of unread notifications"""
    count = await db.notifications.count_documents({
        "user_id": current_user.id,
        "is_read": False
    })
    return {"count": count}

@api_router.patch("/notifications/mark-all-read")
async def mark_all_notifications_read(current_user: User = Depends(get_current_user)):
    """Mark all notifications as read for the current user"""
    result = await db.notifications.update_many(
        {"user_id": current_user.id, "is_read": False},
        {"$set": {"is_read": True}}
    )
    return {"message": f"{result.modified_count} notifications marked as read"}

# ==================== ENHANCED CONSULTANT PROFILE ====================

class ConsultantProfileUpdate(BaseModel):
    preferred_mode: Optional[str] = None
    specializations: Optional[List[str]] = None
    bio: Optional[str] = None
    hourly_rate: Optional[float] = None
    availability_notes: Optional[str] = None

@api_router.put("/consultants/{consultant_id}/profile")
async def update_full_consultant_profile(
    consultant_id: str,
    profile_update: ConsultantProfileUpdate,
    current_user: User = Depends(get_current_user)
):
    """Update consultant profile (Admin can update all, consultant can update limited fields)"""
    # Check authorization
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER] and current_user.id != consultant_id:
        raise HTTPException(status_code=403, detail="Not authorized to update this profile")
    
    # Verify consultant exists
    consultant = await db.users.find_one(
        {"id": consultant_id, "role": {"$in": [UserRole.CONSULTANT, UserRole.PRINCIPAL_CONSULTANT, UserRole.PROJECT_MANAGER]}},
        {"_id": 0}
    )
    if not consultant:
        raise HTTPException(status_code=404, detail="Consultant not found")
    
    update_data = profile_update.model_dump(exclude_unset=True)
    update_data['updated_at'] = datetime.now(timezone.utc).isoformat()
    
    # If changing mode, update max_projects
    if 'preferred_mode' in update_data and current_user.role in [UserRole.ADMIN, UserRole.MANAGER]:
        update_data['max_projects'] = CONSULTANT_BANDWIDTH_LIMITS.get(update_data['preferred_mode'], 8)
    
    # Ensure profile exists
    existing_profile = await db.consultant_profiles.find_one({"user_id": consultant_id})
    if not existing_profile:
        # Create profile if it doesn't exist
        profile_doc = {
            "user_id": consultant_id,
            "specializations": [],
            "preferred_mode": "mixed",
            "max_projects": 8,
            "current_project_count": 0,
            "total_project_value": 0,
            "bio": None,
            "hourly_rate": None,
            "availability_notes": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
            **update_data
        }
        await db.consultant_profiles.insert_one(profile_doc)
    else:
        await db.consultant_profiles.update_one(
            {"user_id": consultant_id},
            {"$set": update_data}
        )
    
    return {"message": "Profile updated successfully"}

# ==================== USER ROLE MANAGEMENT ====================

# Old update_user_role removed - consolidated in ROLE MANAGEMENT APIS section

@api_router.get("/users")
async def get_all_users(
    role: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get all users (Admin/Manager only)"""
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    query = {"is_active": True}
    if role:
        query['role'] = role
    
    users = await db.users.find(query, {"_id": 0, "hashed_password": 0}).to_list(1000)
    
    for user in users:
        if isinstance(user.get('created_at'), str):
            user['created_at'] = datetime.fromisoformat(user['created_at'])
    
    return users

# ==================== USER PROFILE & RIGHTS CONFIGURATION ====================

class UserProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    department: Optional[str] = None
    designation: Optional[str] = None
    bio: Optional[str] = None
    profile_image: Optional[str] = None

class UserRightsConfig(BaseModel):
    """User rights configuration for role-based access"""
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    role: str
    permissions: dict = {}  # Module-wise permissions
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# Default role permissions
DEFAULT_ROLE_PERMISSIONS = {
    "admin": {
        "leads": {"create": True, "read": True, "update": True, "delete": False},
        "pricing_plans": {"create": True, "read": True, "update": True, "delete": False},
        "sow": {"create": True, "read": True, "update": True, "delete": False, "freeze": True},
        "quotations": {"create": True, "read": True, "update": True, "delete": False},
        "agreements": {"create": True, "read": True, "update": True, "delete": False, "approve": True},
        "projects": {"create": True, "read": True, "update": True, "delete": False},
        "tasks": {"create": True, "read": True, "update": True, "delete": True},
        "consultants": {"create": True, "read": True, "update": True, "delete": False},
        "users": {"create": True, "read": True, "update": True, "delete": False, "manage_roles": True},
        "reports": {"view": True, "export": True}
    },
    "manager": {
        "leads": {"create": False, "read": True, "update": False, "delete": False},
        "pricing_plans": {"create": False, "read": True, "update": False, "delete": False},
        "sow": {"create": False, "read": True, "update": False, "delete": False, "freeze": False},
        "quotations": {"create": False, "read": True, "update": False, "delete": False},
        "agreements": {"create": False, "read": True, "update": False, "delete": False, "approve": True},
        "projects": {"create": False, "read": True, "update": False, "delete": False},
        "tasks": {"create": False, "read": True, "update": False, "delete": False},
        "consultants": {"create": False, "read": True, "update": False, "delete": False},
        "users": {"create": False, "read": True, "update": False, "delete": False, "manage_roles": False},
        "reports": {"view": True, "export": True}
    },
    "executive": {
        "leads": {"create": True, "read": True, "update": True, "delete": False},
        "pricing_plans": {"create": True, "read": True, "update": True, "delete": False},
        "sow": {"create": True, "read": True, "update": True, "delete": False, "freeze": False},
        "quotations": {"create": True, "read": True, "update": True, "delete": False},
        "agreements": {"create": True, "read": True, "update": True, "delete": False, "approve": False},
        "projects": {"create": False, "read": True, "update": False, "delete": False},
        "tasks": {"create": False, "read": True, "update": False, "delete": False},
        "consultants": {"create": False, "read": True, "update": False, "delete": False},
        "users": {"create": False, "read": False, "update": False, "delete": False, "manage_roles": False},
        "reports": {"view": False, "export": False}
    },
    "consultant": {
        "leads": {"create": False, "read": False, "update": False, "delete": False},
        "pricing_plans": {"create": False, "read": False, "update": False, "delete": False},
        "sow": {"create": False, "read": True, "update": False, "delete": False, "freeze": False},
        "quotations": {"create": False, "read": False, "update": False, "delete": False},
        "agreements": {"create": False, "read": False, "update": False, "delete": False, "approve": False},
        "projects": {"create": False, "read": True, "update": False, "delete": False},
        "tasks": {"create": True, "read": True, "update": True, "delete": False},
        "consultants": {"create": False, "read": False, "update": False, "delete": False},
        "users": {"create": False, "read": False, "update": False, "delete": False, "manage_roles": False},
        "reports": {"view": False, "export": False}
    },
    "principal_consultant": {
        "leads": {"create": False, "read": True, "update": False, "delete": False},
        "pricing_plans": {"create": False, "read": True, "update": False, "delete": False},
        "sow": {"create": False, "read": True, "update": True, "delete": False, "freeze": True},
        "quotations": {"create": False, "read": True, "update": False, "delete": False},
        "agreements": {"create": False, "read": True, "update": False, "delete": False, "approve": False},
        "projects": {"create": False, "read": True, "update": True, "delete": False},
        "tasks": {"create": True, "read": True, "update": True, "delete": False},
        "consultants": {"create": False, "read": True, "update": False, "delete": False},
        "users": {"create": False, "read": False, "update": False, "delete": False, "manage_roles": False},
        "reports": {"view": True, "export": False}
    },
    "project_manager": {
        "leads": {"create": False, "read": True, "update": False, "delete": False},
        "pricing_plans": {"create": False, "read": True, "update": False, "delete": False},
        "sow": {"create": False, "read": True, "update": True, "delete": False, "freeze": False, "approve": True, "authorize_client": True},
        "quotations": {"create": False, "read": True, "update": False, "delete": False},
        "agreements": {"create": False, "read": True, "update": False, "delete": False, "approve": True},
        "projects": {"create": True, "read": True, "update": True, "delete": False},
        "tasks": {"create": True, "read": True, "update": True, "delete": True},
        "consultants": {"create": False, "read": True, "update": False, "delete": False},
        "users": {"create": False, "read": False, "update": False, "delete": False, "manage_roles": False},
        "reports": {"view": True, "export": True}
    },
    # New roles with default permissions
    "lean_consultant": {
        "leads": {"create": False, "read": False, "update": False, "delete": False},
        "pricing_plans": {"create": False, "read": False, "update": False, "delete": False},
        "sow": {"create": False, "read": True, "update": False, "delete": False, "freeze": False, "update_status": True},
        "quotations": {"create": False, "read": False, "update": False, "delete": False},
        "agreements": {"create": False, "read": False, "update": False, "delete": False, "approve": False},
        "projects": {"create": False, "read": True, "update": False, "delete": False},
        "tasks": {"create": True, "read": True, "update": True, "delete": False},
        "consultants": {"create": False, "read": False, "update": False, "delete": False},
        "users": {"create": False, "read": False, "update": False, "delete": False, "manage_roles": False},
        "reports": {"view": False, "export": False}
    },
    "lead_consultant": {
        "leads": {"create": False, "read": True, "update": False, "delete": False},
        "pricing_plans": {"create": False, "read": True, "update": False, "delete": False},
        "sow": {"create": False, "read": True, "update": True, "delete": False, "freeze": False, "update_status": True},
        "quotations": {"create": False, "read": True, "update": False, "delete": False},
        "agreements": {"create": False, "read": True, "update": False, "delete": False, "approve": False},
        "projects": {"create": False, "read": True, "update": True, "delete": False},
        "tasks": {"create": True, "read": True, "update": True, "delete": True},
        "consultants": {"create": False, "read": True, "update": False, "delete": False},
        "users": {"create": False, "read": False, "update": False, "delete": False, "manage_roles": False},
        "reports": {"view": True, "export": False}
    },
    "senior_consultant": {
        "leads": {"create": False, "read": True, "update": False, "delete": False},
        "pricing_plans": {"create": False, "read": True, "update": False, "delete": False},
        "sow": {"create": False, "read": True, "update": True, "delete": False, "freeze": False, "update_status": True},
        "quotations": {"create": False, "read": True, "update": False, "delete": False},
        "agreements": {"create": False, "read": True, "update": False, "delete": False, "approve": False},
        "projects": {"create": False, "read": True, "update": True, "delete": False},
        "tasks": {"create": True, "read": True, "update": True, "delete": True},
        "consultants": {"create": False, "read": True, "update": False, "delete": False},
        "users": {"create": False, "read": False, "update": False, "delete": False, "manage_roles": False},
        "reports": {"view": True, "export": False}
    },
    "hr_executive": {
        "leads": {"create": False, "read": False, "update": False, "delete": False},
        "pricing_plans": {"create": False, "read": False, "update": False, "delete": False},
        "sow": {"create": False, "read": False, "update": False, "delete": False, "freeze": False},
        "quotations": {"create": False, "read": False, "update": False, "delete": False},
        "agreements": {"create": False, "read": False, "update": False, "delete": False, "approve": False},
        "projects": {"create": False, "read": False, "update": False, "delete": False},
        "tasks": {"create": False, "read": False, "update": False, "delete": False},
        "consultants": {"create": False, "read": False, "update": False, "delete": False},
        "consulting_meetings": {"create": False, "read": False, "update": False, "delete": False},
        "users": {"create": False, "read": True, "update": False, "delete": False, "manage_roles": False},
        "employees": {"create": True, "read": True, "update": True, "delete": False, "bank_details": False},
        "attendance": {"create": True, "read": True, "update": True, "delete": False},
        "leaves": {"create": True, "read": True, "update": True, "delete": False, "approve": False},
        "payroll": {"create": False, "read": True, "update": False, "delete": False},
        "reports": {"view": False, "export": False}
    },
    "hr_manager": {
        "leads": {"create": False, "read": False, "update": False, "delete": False},
        "pricing_plans": {"create": False, "read": False, "update": False, "delete": False},
        "sow": {"create": False, "read": False, "update": False, "delete": False, "freeze": False},
        "quotations": {"create": False, "read": False, "update": False, "delete": False},
        "agreements": {"create": False, "read": False, "update": False, "delete": False, "approve": False},
        "projects": {"create": False, "read": True, "update": False, "delete": False, "view_financials": False},
        "tasks": {"create": False, "read": True, "update": False, "delete": False},
        "consultants": {"create": True, "read": True, "update": True, "delete": False, "view_workload": True},
        "consulting_meetings": {"create": False, "read": True, "update": False, "delete": False, "view_summary_only": True},
        "users": {"create": True, "read": True, "update": True, "delete": False, "manage_roles": False},
        "employees": {"create": True, "read": True, "update": True, "delete": False, "bank_details": "with_proof"},
        "attendance": {"create": True, "read": True, "update": True, "delete": False},
        "leaves": {"create": True, "read": True, "update": True, "delete": False, "approve": True},
        "payroll": {"create": True, "read": True, "update": True, "delete": False},
        "reports": {"view": True, "export": True}
    },
    "account_manager": {
        "leads": {"create": True, "read": True, "update": True, "delete": False},
        "pricing_plans": {"create": True, "read": True, "update": True, "delete": False},
        "sow": {"create": True, "read": True, "update": True, "delete": False, "freeze": False},
        "quotations": {"create": True, "read": True, "update": True, "delete": False},
        "agreements": {"create": True, "read": True, "update": True, "delete": False, "approve": False},
        "projects": {"create": False, "read": True, "update": False, "delete": False},
        "tasks": {"create": False, "read": True, "update": False, "delete": False},
        "consultants": {"create": False, "read": True, "update": False, "delete": False},
        "users": {"create": False, "read": False, "update": False, "delete": False, "manage_roles": False},
        "reports": {"view": True, "export": True}
    },
    "subject_matter_expert": {
        "leads": {"create": False, "read": True, "update": False, "delete": False},
        "pricing_plans": {"create": False, "read": True, "update": False, "delete": False},
        "sow": {"create": False, "read": True, "update": True, "delete": False, "freeze": False, "update_status": True},
        "quotations": {"create": False, "read": True, "update": False, "delete": False},
        "agreements": {"create": False, "read": True, "update": False, "delete": False, "approve": False},
        "projects": {"create": False, "read": True, "update": True, "delete": False},
        "tasks": {"create": True, "read": True, "update": True, "delete": False},
        "consultants": {"create": False, "read": True, "update": False, "delete": False},
        "users": {"create": False, "read": False, "update": False, "delete": False, "manage_roles": False},
        "reports": {"view": True, "export": False}
    }
}

@api_router.get("/users/me")
async def get_current_user_profile(current_user: User = Depends(get_current_user)):
    """Get current user's profile"""
    user = await db.users.find_one({"id": current_user.id}, {"_id": 0, "hashed_password": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@api_router.patch("/users/me")
async def update_current_user_profile(
    profile_update: UserProfileUpdate,
    current_user: User = Depends(get_current_user)
):
    """Update current user's profile"""
    update_data = profile_update.model_dump(exclude_unset=True)
    update_data['updated_at'] = datetime.now(timezone.utc).isoformat()
    
    # Don't allow changing email to existing email
    if 'email' in update_data:
        existing = await db.users.find_one({"email": update_data['email'], "id": {"$ne": current_user.id}})
        if existing:
            raise HTTPException(status_code=400, detail="Email already in use")
    
    await db.users.update_one(
        {"id": current_user.id},
        {"$set": update_data}
    )
    
    return {"message": "Profile updated successfully"}

@api_router.get("/users/{user_id}/profile")
async def get_user_profile(
    user_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get user profile (Admin/Manager only, or own profile)"""
    if current_user.id != user_id and current_user.role not in [UserRole.ADMIN, UserRole.MANAGER]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    user = await db.users.find_one({"id": user_id}, {"_id": 0, "hashed_password": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@api_router.patch("/users/{user_id}/profile")
async def update_user_profile(
    user_id: str,
    profile_update: UserProfileUpdate,
    current_user: User = Depends(get_current_user)
):
    """Update user profile (Admin only)"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only admins can update other users' profiles")
    
    update_data = profile_update.model_dump(exclude_unset=True)
    update_data['updated_at'] = datetime.now(timezone.utc).isoformat()
    
    result = await db.users.update_one(
        {"id": user_id},
        {"$set": update_data}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {"message": "Profile updated successfully"}

@api_router.get("/role-permissions")
async def get_role_permissions(current_user: User = Depends(get_current_user)):
    """Get all role permissions configuration"""
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Check if custom permissions exist in database
    custom_permissions = await db.role_permissions.find({}, {"_id": 0}).to_list(100)
    
    if custom_permissions:
        return {perm['role']: perm['permissions'] for perm in custom_permissions}
    
    return DEFAULT_ROLE_PERMISSIONS

@api_router.get("/role-permissions/{role}")
async def get_role_permission(
    role: str,
    current_user: User = Depends(get_current_user)
):
    """Get permissions for a specific role"""
    # Check database first
    custom = await db.role_permissions.find_one({"role": role}, {"_id": 0})
    if custom:
        return custom['permissions']
    
    # Return default
    if role in DEFAULT_ROLE_PERMISSIONS:
        return DEFAULT_ROLE_PERMISSIONS[role]
    
    raise HTTPException(status_code=404, detail="Role not found")

@api_router.patch("/role-permissions/{role}")
async def update_role_permissions(
    role: str,
    permissions: dict,
    current_user: User = Depends(get_current_user)
):
    """Update permissions for a role (Admin only)"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only admins can modify role permissions")
    
    # Upsert into database
    await db.role_permissions.update_one(
        {"role": role},
        {"$set": {
            "role": role,
            "permissions": permissions,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }},
        upsert=True
    )
    
    return {"message": f"Permissions updated for role: {role}"}

@api_router.get("/users/me/permissions")
async def get_current_user_permissions(current_user: User = Depends(get_current_user)):
    """Get current user's permissions"""
    # Check database first
    custom = await db.role_permissions.find_one({"role": current_user.role}, {"_id": 0})
    if custom:
        return custom['permissions']
    
    # Return default
    if current_user.role in DEFAULT_ROLE_PERMISSIONS:
        return DEFAULT_ROLE_PERMISSIONS[current_user.role]
    
    return {}

# ==================== ROLE MANAGEMENT APIS ====================

class RoleCreate(BaseModel):
    id: str
    name: str
    description: Optional[str] = None

class RoleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    permissions: Optional[dict] = None

@api_router.get("/roles")
async def get_all_roles(current_user: User = Depends(get_current_user)):
    """Get all available roles"""
    # First check if custom roles exist in database
    custom_roles = await db.roles.find({}, {"_id": 0}).to_list(100)
    
    if custom_roles:
        # Merge with DEFAULT_ROLES to ensure system roles always exist
        role_ids = {r['id'] for r in custom_roles}
        for default_role in DEFAULT_ROLES:
            if default_role['id'] not in role_ids:
                custom_roles.append(default_role)
        return sorted(custom_roles, key=lambda x: x.get('name', ''))
    
    # Initialize roles from defaults if none exist
    return sorted(DEFAULT_ROLES, key=lambda x: x.get('name', ''))

@api_router.post("/roles")
async def create_role(
    role_create: RoleCreate,
    current_user: User = Depends(get_current_user)
):
    """Create a new custom role (Admin only)"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only admins can create roles")
    
    # Check if role ID already exists
    existing = await db.roles.find_one({"id": role_create.id})
    if existing:
        raise HTTPException(status_code=400, detail="Role ID already exists")
    
    # Check against default roles
    default_role_ids = {r['id'] for r in DEFAULT_ROLES}
    if role_create.id in default_role_ids:
        raise HTTPException(status_code=400, detail="Cannot override system role")
    
    # Create role with default consultant permissions (safe starting point)
    new_role = {
        "id": role_create.id,
        "name": role_create.name,
        "description": role_create.description or "",
        "is_system_role": False,
        "can_delete": True,
        "created_by": current_user.id,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.roles.insert_one(new_role)
    
    # Create default permissions for the role (copy from consultant)
    default_perms = DEFAULT_ROLE_PERMISSIONS.get("consultant", {})
    await db.role_permissions.update_one(
        {"role": role_create.id},
        {"$set": {
            "role": role_create.id,
            "permissions": default_perms,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }},
        upsert=True
    )
    
    return {"message": f"Role '{role_create.name}' created successfully", "role_id": role_create.id}

@api_router.get("/roles/{role_id}")
async def get_role(
    role_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get a specific role with its permissions"""
    # Check database first
    role = await db.roles.find_one({"id": role_id}, {"_id": 0})
    
    if not role:
        # Check defaults
        for default_role in DEFAULT_ROLES:
            if default_role['id'] == role_id:
                role = default_role
                break
    
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    
    # Get permissions
    custom_perms = await db.role_permissions.find_one({"role": role_id}, {"_id": 0})
    if custom_perms:
        role['permissions'] = custom_perms['permissions']
    else:
        role['permissions'] = DEFAULT_ROLE_PERMISSIONS.get(role_id, {})
    
    return role

@api_router.patch("/roles/{role_id}")
async def update_role(
    role_id: str,
    role_update: RoleUpdate,
    current_user: User = Depends(get_current_user)
):
    """Update a role (Admin only)"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only admins can update roles")
    
    # Check if updating a system role name (not allowed for system roles)
    for default_role in DEFAULT_ROLES:
        if default_role['id'] == role_id and default_role.get('is_system_role'):
            # System roles: only permissions can be updated, not name/description
            if role_update.name or role_update.description:
                pass  # Allow update even for system roles
    
    update_data = {}
    if role_update.name:
        update_data['name'] = role_update.name
    if role_update.description is not None:
        update_data['description'] = role_update.description
    
    if update_data:
        update_data['updated_at'] = datetime.now(timezone.utc).isoformat()
        
        # Update or insert in db
        await db.roles.update_one(
            {"id": role_id},
            {"$set": update_data},
            upsert=True
        )
    
    # Update permissions if provided
    if role_update.permissions:
        await db.role_permissions.update_one(
            {"role": role_id},
            {"$set": {
                "role": role_id,
                "permissions": role_update.permissions,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }},
            upsert=True
        )
    
    return {"message": f"Role '{role_id}' updated successfully"}

@api_router.delete("/roles/{role_id}")
async def delete_role(
    role_id: str,
    current_user: User = Depends(get_current_user)
):
    """Delete a custom role (Admin only)"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only admins can delete roles")
    
    # Check if it's a system role
    for default_role in DEFAULT_ROLES:
        if default_role['id'] == role_id and not default_role.get('can_delete', True):
            raise HTTPException(status_code=400, detail="Cannot delete system role")
    
    # Check if any users have this role
    users_with_role = await db.users.count_documents({"role": role_id})
    if users_with_role > 0:
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot delete role. {users_with_role} user(s) currently have this role."
        )
    
    # Delete role
    await db.roles.delete_one({"id": role_id})
    await db.role_permissions.delete_one({"role": role_id})
    
    return {"message": f"Role '{role_id}' deleted successfully"}

@api_router.get("/roles/categories/sow")
async def get_sow_role_categories():
    """Get role categories for SOW access control"""
    return {
        "sales_roles": SALES_ROLES,
        "consulting_roles": CONSULTING_ROLES,
        "pm_roles": PM_ROLES
    }

# Update user role API (enhanced)
@api_router.patch("/users/{user_id}/role")
async def update_user_role(
    user_id: str,
    role: str = None,
    current_user: User = Depends(get_current_user)
):
    """Update user's role (Admin only)"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only admins can change user roles")
    
    # Verify role exists
    role_exists = False
    for default_role in DEFAULT_ROLES:
        if default_role['id'] == role:
            role_exists = True
            break
    
    if not role_exists:
        custom_role = await db.roles.find_one({"id": role})
        if not custom_role:
            raise HTTPException(status_code=400, detail="Invalid role")
    
    result = await db.users.update_one(
        {"id": user_id},
        {"$set": {"role": role, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    
    # If promoting to consultant-type role, ensure profile exists
    consultant_roles = ["consultant", "lean_consultant", "lead_consultant", "senior_consultant", 
                       "principal_consultant", "subject_matter_expert", "project_manager"]
    if role in consultant_roles:
        existing_profile = await db.consultant_profiles.find_one({"user_id": user_id})
        if not existing_profile:
            profile = {
                "user_id": user_id,
                "specializations": [],
                "preferred_mode": "mixed",
                "max_projects": CONSULTANT_BANDWIDTH_LIMITS.get("mixed", 8),
                "current_project_count": 0,
                "total_project_value": 0,
                "bio": None,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            await db.consultant_profiles.insert_one(profile)
    
    return {"message": f"User role updated to '{role}'"}

# Get all available modules and actions for permission configuration
@api_router.get("/permission-modules")
async def get_permission_modules(current_user: User = Depends(get_current_user)):
    """Get all available modules and actions for permission configuration"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only admins can view permission modules")
    
    return {
        "modules": [
            {"id": "leads", "name": "Leads", "description": "Lead management"},
            {"id": "pricing_plans", "name": "Pricing Plans", "description": "Pricing plan management"},
            {"id": "sow", "name": "SOW", "description": "Scope of Work management"},
            {"id": "quotations", "name": "Quotations", "description": "Quotation management"},
            {"id": "agreements", "name": "Agreements", "description": "Agreement management"},
            {"id": "projects", "name": "Projects", "description": "Project management"},
            {"id": "tasks", "name": "Tasks", "description": "Task management"},
            {"id": "consultants", "name": "Consultants", "description": "Consultant management"},
            {"id": "users", "name": "Users", "description": "User management"},
            {"id": "reports", "name": "Reports", "description": "Reports and analytics"}
        ],
        "actions": {
            "common": ["create", "read", "update", "delete"],
            "sow": ["create", "read", "update", "delete", "freeze", "approve", "authorize_client", "update_status"],
            "agreements": ["create", "read", "update", "delete", "approve"],
            "users": ["create", "read", "update", "delete", "manage_roles"],
            "reports": ["view", "export"]
        }
    }

# User list with role information
@api_router.get("/users-with-roles")
async def get_users_with_roles(
    role: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get all users with their role information (Admin/Manager only)"""
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER, UserRole.HR_MANAGER]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    query = {}
    if role:
        query['role'] = role
    
    users = await db.users.find(query, {"_id": 0, "hashed_password": 0}).to_list(1000)
    
    # Get all roles for mapping
    roles_list = await db.roles.find({}, {"_id": 0}).to_list(100)
    roles_map = {r['id']: r for r in roles_list}
    
    # Add role details to default roles
    for default_role in DEFAULT_ROLES:
        if default_role['id'] not in roles_map:
            roles_map[default_role['id']] = default_role
    
    # Enrich users with role info
    for user in users:
        role_id = user.get('role')
        if role_id and role_id in roles_map:
            user['role_info'] = roles_map[role_id]
        if isinstance(user.get('created_at'), str):
            pass  # Already string
    
    return users

# ==================== APPROVAL WORKFLOW ENGINE ====================

class ApprovalType(str):
    SOW_ITEM = "sow_item"
    SOW_DOCUMENT = "sow_document"
    AGREEMENT = "agreement"
    QUOTATION = "quotation"
    LEAVE_REQUEST = "leave_request"
    EXPENSE = "expense"
    CLIENT_COMMUNICATION = "client_communication"

class ApprovalStatus(str):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    ESCALATED = "escalated"

class ApprovalLevel(BaseModel):
    level: int
    approver_id: str
    approver_name: str
    approver_role: str
    status: str = ApprovalStatus.PENDING
    comments: Optional[str] = None
    action_date: Optional[datetime] = None

class ApprovalRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    approval_type: str  # sow_item, agreement, leave_request, expense, etc.
    reference_id: str  # ID of the item being approved
    reference_title: str  # Title for display
    
    requester_id: str
    requester_name: str
    requester_employee_id: Optional[str] = None
    
    # Approval chain
    approval_levels: List[dict] = []
    current_level: int = 1
    max_level: int = 1
    
    # Status
    overall_status: str = ApprovalStatus.PENDING
    requires_hr_approval: bool = False
    requires_admin_approval: bool = False
    is_client_facing: bool = False
    
    # Metadata
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None

# Helper function to get employee's reporting chain
async def get_reporting_chain(user_id: str, max_levels: int = 3) -> List[dict]:
    """Get the approval chain based on reporting manager hierarchy"""
    chain = []
    
    # Get employee record for the user
    employee = await db.employees.find_one({"user_id": user_id}, {"_id": 0})
    if not employee:
        return chain
    
    current_manager_id = employee.get('reporting_manager_id')
    level = 1
    
    while current_manager_id and level <= max_levels:
        manager = await db.employees.find_one({"id": current_manager_id}, {"_id": 0})
        if not manager:
            break
        
        chain.append({
            "level": level,
            "employee_id": manager['id'],
            "user_id": manager.get('user_id'),
            "name": f"{manager['first_name']} {manager['last_name']}",
            "role": manager.get('role'),
            "designation": manager.get('designation')
        })
        
        current_manager_id = manager.get('reporting_manager_id')
        level += 1
    
    return chain


# --- Reporting Manager Helper Functions ---
async def get_direct_reportee_ids(user_id: str) -> List[str]:
    """Get employee IDs of direct reportees of a user"""
    employee = await db.employees.find_one({"user_id": user_id}, {"_id": 0})
    if not employee:
        return []
    mgr_emp_id = employee['id']
    reportees = await db.employees.find(
        {"reporting_manager_id": mgr_emp_id, "is_active": True},
        {"_id": 0, "id": 1, "user_id": 1}
    ).to_list(200)
    return [r['id'] for r in reportees]


async def get_all_reportee_ids(user_id: str) -> List[str]:
    """Get employee IDs of direct + second-line reportees"""
    employee = await db.employees.find_one({"user_id": user_id}, {"_id": 0})
    if not employee:
        return []
    mgr_emp_id = employee['id']
    # Direct reportees
    direct = await db.employees.find(
        {"reporting_manager_id": mgr_emp_id, "is_active": True},
        {"_id": 0, "id": 1}
    ).to_list(200)
    direct_ids = [r['id'] for r in direct]
    # Second-line reportees (reportees of direct reportees)
    second_line = []
    if direct_ids:
        second = await db.employees.find(
            {"reporting_manager_id": {"$in": direct_ids}, "is_active": True},
            {"_id": 0, "id": 1}
        ).to_list(500)
        second_line = [r['id'] for r in second]
    return direct_ids + second_line


async def get_reportee_user_ids(user_id: str) -> List[str]:
    """Get user IDs of direct + second-line reportees"""
    employee = await db.employees.find_one({"user_id": user_id}, {"_id": 0})
    if not employee:
        return []
    mgr_emp_id = employee['id']
    direct = await db.employees.find(
        {"reporting_manager_id": mgr_emp_id, "is_active": True},
        {"_id": 0, "id": 1, "user_id": 1}
    ).to_list(200)
    direct_ids = [r['id'] for r in direct]
    direct_user_ids = [r['user_id'] for r in direct if r.get('user_id')]
    second_line_user_ids = []
    if direct_ids:
        second = await db.employees.find(
            {"reporting_manager_id": {"$in": direct_ids}, "is_active": True},
            {"_id": 0, "user_id": 1}
        ).to_list(500)
        second_line_user_ids = [r['user_id'] for r in second if r.get('user_id')]
    return direct_user_ids + second_line_user_ids


async def is_direct_reportee(manager_user_id: str, employee_id: str) -> bool:
    """Check if employee is a direct reportee of the manager"""
    manager_emp = await db.employees.find_one({"user_id": manager_user_id}, {"_id": 0, "id": 1})
    if not manager_emp:
        return False
    reportee = await db.employees.find_one({"id": employee_id, "reporting_manager_id": manager_emp['id']}, {"_id": 0})
    return reportee is not None


async def is_any_reportee(manager_user_id: str, employee_id: str) -> bool:
    """Check if employee is a direct or second-line reportee"""
    all_ids = await get_all_reportee_ids(manager_user_id)
    return employee_id in all_ids

# Helper function to get fallback approvers by role
async def get_role_based_approvers(roles: List[str]) -> List[dict]:
    """Get approvers based on roles (fallback when no reporting manager)"""
    approvers = []
    users = await db.users.find({"role": {"$in": roles}, "is_active": True}, {"_id": 0, "hashed_password": 0}).to_list(100)
    
    for user in users:
        employee = await db.employees.find_one({"user_id": user['id']}, {"_id": 0})
        approvers.append({
            "user_id": user['id'],
            "name": user.get('full_name', 'Unknown'),
            "role": user['role'],
            "employee_id": employee['id'] if employee else None,
            "designation": employee.get('designation') if employee else user['role']
        })
    
    return approvers

# Create approval request with proper chain
async def create_approval_request(
    approval_type: str,
    reference_id: str,
    reference_title: str,
    requester_id: str,
    is_client_facing: bool = False,
    requires_hr_approval: bool = False,
    requires_admin_approval: bool = False
) -> dict:
    """Create an approval request with the appropriate approval chain"""
    
    # Get requester info
    requester = await db.users.find_one({"id": requester_id}, {"_id": 0, "hashed_password": 0})
    requester_name = requester.get('full_name', 'Unknown') if requester else 'Unknown'
    
    requester_employee = await db.employees.find_one({"user_id": requester_id}, {"_id": 0})
    requester_employee_id = requester_employee['id'] if requester_employee else None
    
    # Build approval chain
    approval_levels = []
    
    # Level 1: Reporting Manager (or fallback to role-based)
    reporting_chain = await get_reporting_chain(requester_id, max_levels=2 if is_client_facing else 1)
    
    if reporting_chain:
        # Use reporting manager chain
        for rm in reporting_chain:
            approval_levels.append({
                "level": len(approval_levels) + 1,
                "approver_id": rm.get('user_id') or rm.get('employee_id'),
                "approver_name": rm['name'],
                "approver_role": rm.get('role') or rm.get('designation'),
                "approver_type": "reporting_manager",
                "status": ApprovalStatus.PENDING,
                "comments": None,
                "action_date": None
            })
    else:
        # Fallback to role-based approvers
        fallback_roles = [UserRole.PROJECT_MANAGER, UserRole.MANAGER]
        fallback_approvers = await get_role_based_approvers(fallback_roles)
        
        if fallback_approvers:
            # Pick first available approver
            approver = fallback_approvers[0]
            approval_levels.append({
                "level": 1,
                "approver_id": approver['user_id'],
                "approver_name": approver['name'],
                "approver_role": approver['role'],
                "approver_type": "role_based_fallback",
                "status": ApprovalStatus.PENDING,
                "comments": None,
                "action_date": None
            })
    
    # Add HR approval if required (for leave/expenses)
    if requires_hr_approval:
        hr_approvers = await get_role_based_approvers([UserRole.HR_MANAGER])
        if hr_approvers:
            approval_levels.append({
                "level": len(approval_levels) + 1,
                "approver_id": hr_approvers[0]['user_id'],
                "approver_name": hr_approvers[0]['name'],
                "approver_role": hr_approvers[0]['role'],
                "approver_type": "hr_approval",
                "status": ApprovalStatus.PENDING,
                "comments": None,
                "action_date": None
            })
    
    # Add Admin approval if required
    if requires_admin_approval:
        admin_approvers = await get_role_based_approvers([UserRole.ADMIN])
        if admin_approvers:
            approval_levels.append({
                "level": len(approval_levels) + 1,
                "approver_id": admin_approvers[0]['user_id'],
                "approver_name": admin_approvers[0]['name'],
                "approver_role": admin_approvers[0]['role'],
                "approver_type": "admin_approval",
                "status": ApprovalStatus.PENDING,
                "comments": None,
                "action_date": None
            })
    
    approval_request = {
        "id": str(uuid.uuid4()),
        "approval_type": approval_type,
        "reference_id": reference_id,
        "reference_title": reference_title,
        "requester_id": requester_id,
        "requester_name": requester_name,
        "requester_employee_id": requester_employee_id,
        "approval_levels": approval_levels,
        "current_level": 1,
        "max_level": len(approval_levels),
        "overall_status": ApprovalStatus.PENDING,
        "requires_hr_approval": requires_hr_approval,
        "requires_admin_approval": requires_admin_approval,
        "is_client_facing": is_client_facing,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "completed_at": None
    }
    
    await db.approval_requests.insert_one(approval_request)
    
    # Create notification for first approver
    if approval_levels:
        await create_approval_notification(
            approver_id=approval_levels[0]['approver_id'],
            approval_request_id=approval_request['id'],
            approval_type=approval_type,
            reference_title=reference_title,
            requester_name=requester_name
        )
    
    return approval_request

async def create_approval_notification(
    approver_id: str,
    approval_request_id: str,
    approval_type: str,
    reference_title: str,
    requester_name: str
):
    """Create notification for approver"""
    notification = {
        "id": str(uuid.uuid4()),
        "user_id": approver_id,
        "type": "approval_request",
        "title": f"Approval Required: {approval_type.replace('_', ' ').title()}",
        "message": f"{requester_name} has submitted '{reference_title}' for your approval.",
        "reference_type": approval_type,
        "reference_id": approval_request_id,
        "is_read": False,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.notifications.insert_one(notification)
    
    # Log email notification (MOCKED)
    print(f"[EMAIL NOTIFICATION] Approval request sent to user {approver_id} for {reference_title}")

    # Also notify all admins (if approver is not already admin)
    await notify_admins(
        notif_type="approval_request",
        title=f"New Approval: {approval_type.replace('_', ' ').title()}",
        message=f"{requester_name} submitted '{reference_title}' for approval.",
        reference_type=approval_type,
        reference_id=approval_request_id,
        exclude_user_id=approver_id
    )


async def notify_admins(notif_type: str, title: str, message: str, reference_type: str = None, reference_id: str = None, exclude_user_id: str = None):
    """Send a notification to all admin-role users"""
    query = {"role": "admin", "is_active": {"$ne": False}}
    admins = await db.users.find(query, {"_id": 0, "id": 1}).to_list(50)
    for admin in admins:
        if exclude_user_id and admin['id'] == exclude_user_id:
            continue
        notif = {
            "id": str(uuid.uuid4()),
            "user_id": admin['id'],
            "type": notif_type,
            "title": title,
            "message": message,
            "reference_type": reference_type,
            "reference_id": reference_id,
            "is_read": False,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.notifications.insert_one(notif)

# API: Get pending approvals for current user
@api_router.get("/approvals/pending")
async def get_pending_approvals(current_user: User = Depends(get_current_user)):
    """Get all pending approvals for the current user"""
    approvals = await db.approval_requests.find({
        "overall_status": ApprovalStatus.PENDING,
        "approval_levels": {
            "$elemMatch": {
                "approver_id": current_user.id,
                "status": ApprovalStatus.PENDING
            }
        }
    }, {"_id": 0}).to_list(100)
    
    # Filter to only show approvals at the current level that this user can action
    actionable = []
    for approval in approvals:
        for level in approval['approval_levels']:
            if level['approver_id'] == current_user.id and \
               level['status'] == ApprovalStatus.PENDING and \
               level['level'] == approval['current_level']:
                approval['can_action'] = True
                actionable.append(approval)
                break
    
    return actionable

# API: Get all approval requests (for admin/managers)
@api_router.get("/approvals/all")
async def get_all_approvals(
    status: Optional[str] = None,
    approval_type: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get all approval requests (Admin/Manager only)"""
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER, UserRole.HR_MANAGER]:
        raise HTTPException(status_code=403, detail="Not authorized to view all approvals")
    
    query = {}
    if status:
        query['overall_status'] = status
    if approval_type:
        query['approval_type'] = approval_type
    
    approvals = await db.approval_requests.find(query, {"_id": 0}).to_list(500)
    return approvals

# API: Get my submitted approval requests
@api_router.get("/approvals/my-requests")
async def get_my_approval_requests(current_user: User = Depends(get_current_user)):
    """Get approval requests submitted by the current user"""
    approvals = await db.approval_requests.find(
        {"requester_id": current_user.id},
        {"_id": 0}
    ).to_list(100)
    return approvals

# API: Action an approval (approve/reject)
class ApprovalAction(BaseModel):
    action: str  # approve, reject
    comments: Optional[str] = None

@api_router.post("/approvals/{approval_id}/action")
async def action_approval(
    approval_id: str,
    action_data: ApprovalAction,
    current_user: User = Depends(get_current_user)
):
    """Approve or reject an approval request"""
    approval = await db.approval_requests.find_one({"id": approval_id}, {"_id": 0})
    if not approval:
        raise HTTPException(status_code=404, detail="Approval request not found")
    
    if approval['overall_status'] != ApprovalStatus.PENDING:
        raise HTTPException(status_code=400, detail="This approval has already been completed")
    
    # Find the current level that this user can action
    can_action = False
    current_level_idx = None
    for idx, level in enumerate(approval['approval_levels']):
        if level['approver_id'] == current_user.id and \
           level['status'] == ApprovalStatus.PENDING and \
           level['level'] == approval['current_level']:
            can_action = True
            current_level_idx = idx
            break
    
    if not can_action:
        raise HTTPException(status_code=403, detail="You cannot action this approval")
    
    # RULE: Manager cannot approve their own leave request
    if approval.get('requester_id') == current_user.id:
        raise HTTPException(status_code=403, detail="You cannot approve your own request. It must be escalated to your reporting manager or admin.")
    
    # RULE: For leave/expense approvals, non-admin approvers can only approve direct reportees
    if current_user.role != 'admin' and approval.get('approval_type') in [ApprovalType.LEAVE_REQUEST, ApprovalType.EXPENSE]:
        requester_emp = await db.employees.find_one({"user_id": approval['requester_id']}, {"_id": 0, "id": 1})
        if requester_emp:
            is_direct = await is_direct_reportee(current_user.id, requester_emp['id'])
            # Allow HR managers to approve regardless
            if not is_direct and current_user.role not in ['hr_manager']:
                raise HTTPException(status_code=403, detail="You can only approve requests from your direct reportees.")
    
    # Update the level
    new_status = ApprovalStatus.APPROVED if action_data.action == 'approve' else ApprovalStatus.REJECTED
    approval['approval_levels'][current_level_idx]['status'] = new_status
    approval['approval_levels'][current_level_idx]['comments'] = action_data.comments
    approval['approval_levels'][current_level_idx]['action_date'] = datetime.now(timezone.utc).isoformat()
    
    if action_data.action == 'approve':
        # Check if there are more levels
        if approval['current_level'] < approval['max_level']:
            # Move to next level
            approval['current_level'] += 1
            
            # Notify next approver
            next_level = approval['approval_levels'][current_level_idx + 1]
            await create_approval_notification(
                approver_id=next_level['approver_id'],
                approval_request_id=approval_id,
                approval_type=approval['approval_type'],
                reference_title=approval['reference_title'],
                requester_name=approval['requester_name']
            )
        else:
            # All levels approved
            approval['overall_status'] = ApprovalStatus.APPROVED
            approval['completed_at'] = datetime.now(timezone.utc).isoformat()
            
            # Update the referenced item status
            await update_referenced_item_status(approval, ApprovalStatus.APPROVED)
            
            # Notify requester
            await db.notifications.insert_one({
                "id": str(uuid.uuid4()),
                "user_id": approval['requester_id'],
                "type": "approval_completed",
                "title": "Approval Completed",
                "message": f"Your request '{approval['reference_title']}' has been fully approved.",
                "reference_type": approval['approval_type'],
                "reference_id": approval['reference_id'],
                "is_read": False,
                "created_at": datetime.now(timezone.utc).isoformat()
            })

            # Notify admins about approval completion
            await notify_admins(
                notif_type="approval_completed",
                title=f"Approved: {approval['approval_type'].replace('_', ' ').title()}",
                message=f"'{approval['reference_title']}' by {approval['requester_name']} has been approved.",
                reference_type=approval['approval_type'],
                reference_id=approval['reference_id'],
                exclude_user_id=current_user.id
            )
    else:
        # Rejected
        approval['overall_status'] = ApprovalStatus.REJECTED
        approval['completed_at'] = datetime.now(timezone.utc).isoformat()
        
        # Update the referenced item status
        await update_referenced_item_status(approval, ApprovalStatus.REJECTED)
        
        # Notify requester
        await db.notifications.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": approval['requester_id'],
            "type": "approval_rejected",
            "title": "Approval Rejected",
            "message": f"Your request '{approval['reference_title']}' has been rejected. Comments: {action_data.comments or 'None'}",
            "reference_type": approval['approval_type'],
            "reference_id": approval['reference_id'],
            "is_read": False,
            "created_at": datetime.now(timezone.utc).isoformat()
        })

        # Notify admins about rejection
        await notify_admins(
            notif_type="approval_rejected",
            title=f"Rejected: {approval['approval_type'].replace('_', ' ').title()}",
            message=f"'{approval['reference_title']}' by {approval['requester_name']} was rejected by {current_user.full_name}.",
            reference_type=approval['approval_type'],
            reference_id=approval['reference_id'],
            exclude_user_id=current_user.id
        )
    
    approval['updated_at'] = datetime.now(timezone.utc).isoformat()
    
    await db.approval_requests.update_one(
        {"id": approval_id},
        {"$set": approval}
    )
    
    return {"message": f"Approval {action_data.action}d successfully", "status": approval['overall_status']}

async def update_referenced_item_status(approval: dict, status: str):
    """Update the status of the referenced item after approval action"""
    ref_type = approval['approval_type']
    ref_id = approval['reference_id']
    
    if ref_type == ApprovalType.SOW_ITEM:
        # Update SOW item status
        sow = await db.sows.find_one({"items.id": ref_id}, {"_id": 0})
        if sow:
            new_status = "approved" if status == ApprovalStatus.APPROVED else "rejected"
            for item in sow.get('items', []):
                if item['id'] == ref_id:
                    item['status'] = new_status
                    item['approval_status'] = status
                    break
            await db.sows.update_one(
                {"id": sow['id']},
                {"$set": {"items": sow['items'], "updated_at": datetime.now(timezone.utc).isoformat()}}
            )
    
    elif ref_type == ApprovalType.AGREEMENT:
        new_status = "approved" if status == ApprovalStatus.APPROVED else "rejected"
        await db.agreements.update_one(
            {"id": ref_id},
            {"$set": {"status": new_status, "updated_at": datetime.now(timezone.utc).isoformat()}}
        )
    
    elif ref_type == ApprovalType.QUOTATION:
        new_status = "approved" if status == ApprovalStatus.APPROVED else "rejected"
        await db.quotations.update_one(
            {"id": ref_id},
            {"$set": {"status": new_status, "updated_at": datetime.now(timezone.utc).isoformat()}}
        )
    
    elif ref_type == ApprovalType.LEAVE_REQUEST:
        new_status = "approved" if status == ApprovalStatus.APPROVED else "rejected"
        await db.leave_requests.update_one(
            {"id": ref_id},
            {"$set": {"status": new_status, "updated_at": datetime.now(timezone.utc).isoformat()}}
        )
        
        # Update leave balance if approved
        if status == ApprovalStatus.APPROVED:
            leave_request = await db.leave_requests.find_one({"id": ref_id}, {"_id": 0})
            if leave_request:
                leave_type = leave_request.get('leave_type', 'casual_leave')
                days = leave_request.get('days', 1)
                used_field = f"leave_balance.used_{leave_type.replace('_leave', '')}"
                await db.employees.update_one(
                    {"id": leave_request['employee_id']},
                    {"$inc": {used_field: days}}
                )

# API: Get approval chain preview (before submitting)
@api_router.get("/approvals/preview-chain")
async def preview_approval_chain(
    approval_type: str,
    is_client_facing: bool = False,
    requires_hr_approval: bool = False,
    requires_admin_approval: bool = False,
    current_user: User = Depends(get_current_user)
):
    """Preview the approval chain before submitting"""
    approval_levels = []
    
    # Get reporting chain
    reporting_chain = await get_reporting_chain(current_user.id, max_levels=2 if is_client_facing else 1)
    
    if reporting_chain:
        for rm in reporting_chain:
            approval_levels.append({
                "level": len(approval_levels) + 1,
                "approver_name": rm['name'],
                "approver_role": rm.get('role') or rm.get('designation'),
                "approver_type": "Reporting Manager"
            })
    else:
        approval_levels.append({
            "level": 1,
            "approver_name": "Role-based (PM/Manager)",
            "approver_role": "Project Manager or Manager",
            "approver_type": "Fallback"
        })
    
    if requires_hr_approval:
        approval_levels.append({
            "level": len(approval_levels) + 1,
            "approver_name": "HR Manager",
            "approver_role": "HR Manager",
            "approver_type": "HR Approval"
        })
    
    if requires_admin_approval:
        approval_levels.append({
            "level": len(approval_levels) + 1,
            "approver_name": "Admin",
            "approver_role": "Admin",
            "approver_type": "Final Approval"
        })
    
    return {
        "approval_type": approval_type,
        "levels": approval_levels,
        "total_levels": len(approval_levels)
    }

# ==================== SCOPE TASK APPROVAL MODULE ====================
# Parallel approval system for SOW scope tasks (Manager + Client)

class ScopeTaskApprovalStatus(str):
    PENDING = "pending"
    MANAGER_APPROVED = "manager_approved"
    CLIENT_APPROVED = "client_approved"
    FULLY_APPROVED = "fully_approved"
    MANAGER_REJECTED = "manager_rejected"
    CLIENT_REJECTED = "client_rejected"

class ScopeTaskApproval(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    sow_id: str
    scope_id: str
    scope_name: str
    
    # Initiator
    initiated_by: str
    initiated_by_name: str
    initiated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Parallel approvals
    manager_approval: Optional[dict] = None  # {status, approver_id, approver_name, approved_at, comments}
    client_approval: Optional[dict] = None   # {status, approver_id, approver_name, approved_at, comments}
    
    # Overall status
    status: str = ScopeTaskApprovalStatus.PENDING
    
    # Deadline and reminders
    deadline: Optional[datetime] = None
    reminder_interval_days: int = 2
    last_reminder_sent: Optional[datetime] = None
    reminder_count: int = 0
    
    # Notes
    notes: Optional[str] = None
    attachments: List[str] = []
    
    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None

class ScopeTaskApprovalCreate(BaseModel):
    sow_id: str
    scope_ids: List[str]  # Can submit multiple scopes at once
    deadline_days: Optional[int] = 7  # Days from now
    notes: Optional[str] = None

class ScopeTaskApprovalAction(BaseModel):
    action: str  # approve, reject
    approver_type: str  # manager, client
    comments: Optional[str] = None

@api_router.post("/scope-task-approvals")
async def create_scope_task_approval(
    approval_data: ScopeTaskApprovalCreate,
    current_user: User = Depends(get_current_user)
):
    """Create task approval requests for selected scopes (parallel Manager + Client approval)"""
    # Get SOW
    sow = await db.enhanced_sows.find_one({"id": approval_data.sow_id}, {"_id": 0})
    if not sow:
        raise HTTPException(status_code=404, detail="SOW not found")
    
    created_approvals = []
    deadline = datetime.now(timezone.utc) + timedelta(days=approval_data.deadline_days or 7)
    
    for scope_id in approval_data.scope_ids:
        # Find scope in SOW
        scope = None
        for s in sow.get('scopes', []):
            if s.get('id') == scope_id:
                scope = s
                break
        
        if not scope:
            continue
        
        # Check if approval already exists and is pending
        existing = await db.scope_task_approvals.find_one({
            "sow_id": approval_data.sow_id,
            "scope_id": scope_id,
            "status": {"$in": [ScopeTaskApprovalStatus.PENDING, ScopeTaskApprovalStatus.MANAGER_APPROVED, ScopeTaskApprovalStatus.CLIENT_APPROVED]}
        })
        if existing:
            continue  # Skip if pending approval exists
        
        approval = ScopeTaskApproval(
            sow_id=approval_data.sow_id,
            scope_id=scope_id,
            scope_name=scope.get('name', 'Unknown Scope'),
            initiated_by=current_user.id,
            initiated_by_name=current_user.full_name,
            deadline=deadline,
            notes=approval_data.notes,
            manager_approval={"status": "pending", "approver_id": None, "approver_name": None, "approved_at": None, "comments": None},
            client_approval={"status": "pending", "approver_id": None, "approver_name": None, "approved_at": None, "comments": None}
        )
        
        doc = approval.model_dump()
        doc['created_at'] = doc['created_at'].isoformat()
        doc['updated_at'] = doc['updated_at'].isoformat()
        doc['initiated_at'] = doc['initiated_at'].isoformat()
        if doc['deadline']:
            doc['deadline'] = doc['deadline'].isoformat()
        
        await db.scope_task_approvals.insert_one(doc)
        created_approvals.append(doc)
        
        # Update scope status in SOW
        for s in sow.get('scopes', []):
            if s.get('id') == scope_id:
                s['approval_status'] = 'pending_approval'
                s['approval_id'] = approval.id
                break
    
    # Update SOW with new approval statuses
    await db.enhanced_sows.update_one(
        {"id": approval_data.sow_id},
        {"$set": {"scopes": sow['scopes'], "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    # Create notifications for managers (project team)
    project = await db.projects.find_one({"sow_id": approval_data.sow_id}, {"_id": 0})
    if project:
        # Notify all team members
        for member in project.get('team_members', []):
            if member.get('user_id') and member['user_id'] != current_user.id:
                await db.notifications.insert_one({
                    "id": str(uuid.uuid4()),
                    "user_id": member['user_id'],
                    "type": "task_approval_request",
                    "title": "Task Approval Required",
                    "message": f"{current_user.full_name} has requested approval for {len(created_approvals)} scope task(s)",
                    "reference_type": "scope_task_approval",
                    "reference_id": approval_data.sow_id,
                    "is_read": False,
                    "created_at": datetime.now(timezone.utc).isoformat()
                })
    
    return {
        "message": f"Created {len(created_approvals)} task approval request(s)",
        "approvals": created_approvals
    }

@api_router.get("/scope-task-approvals/sow/{sow_id}")
async def get_sow_task_approvals(
    sow_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get all task approvals for a SOW"""
    approvals = await db.scope_task_approvals.find(
        {"sow_id": sow_id},
        {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    
    return approvals

@api_router.get("/scope-task-approvals/pending")
async def get_pending_task_approvals(
    current_user: User = Depends(get_current_user)
):
    """Get all pending task approvals for the current user (as manager or client)"""
    # Get SOWs where user is a team member
    projects = await db.projects.find(
        {"team_members.user_id": current_user.id},
        {"_id": 0, "sow_id": 1}
    ).to_list(100)
    sow_ids = [p['sow_id'] for p in projects if p.get('sow_id')]
    
    # Get pending approvals
    approvals = await db.scope_task_approvals.find({
        "sow_id": {"$in": sow_ids},
        "status": {"$in": [
            ScopeTaskApprovalStatus.PENDING,
            ScopeTaskApprovalStatus.MANAGER_APPROVED,
            ScopeTaskApprovalStatus.CLIENT_APPROVED
        ]}
    }, {"_id": 0}).sort("created_at", -1).to_list(100)
    
    return approvals

@api_router.post("/scope-task-approvals/{approval_id}/action")
async def action_scope_task_approval(
    approval_id: str,
    action_data: ScopeTaskApprovalAction,
    current_user: User = Depends(get_current_user)
):
    """Approve or reject a scope task (Manager or Client)"""
    approval = await db.scope_task_approvals.find_one({"id": approval_id}, {"_id": 0})
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")
    
    if approval['status'] == ScopeTaskApprovalStatus.FULLY_APPROVED:
        raise HTTPException(status_code=400, detail="This task has already been fully approved")
    
    now = datetime.now(timezone.utc)
    update_data = {"updated_at": now.isoformat()}
    
    if action_data.approver_type == "manager":
        if approval.get('manager_approval', {}).get('status') != 'pending':
            raise HTTPException(status_code=400, detail="Manager approval already processed")
        
        update_data['manager_approval'] = {
            "status": "approved" if action_data.action == "approve" else "rejected",
            "approver_id": current_user.id,
            "approver_name": current_user.full_name,
            "approved_at": now.isoformat(),
            "comments": action_data.comments
        }
        
        if action_data.action == "reject":
            update_data['status'] = ScopeTaskApprovalStatus.MANAGER_REJECTED
            update_data['completed_at'] = now.isoformat()
        elif approval.get('client_approval', {}).get('status') == 'approved':
            update_data['status'] = ScopeTaskApprovalStatus.FULLY_APPROVED
            update_data['completed_at'] = now.isoformat()
        else:
            update_data['status'] = ScopeTaskApprovalStatus.MANAGER_APPROVED
            
    elif action_data.approver_type == "client":
        if approval.get('client_approval', {}).get('status') != 'pending':
            raise HTTPException(status_code=400, detail="Client approval already processed")
        
        update_data['client_approval'] = {
            "status": "approved" if action_data.action == "approve" else "rejected",
            "approver_id": current_user.id,
            "approver_name": current_user.full_name,
            "approved_at": now.isoformat(),
            "comments": action_data.comments
        }
        
        if action_data.action == "reject":
            update_data['status'] = ScopeTaskApprovalStatus.CLIENT_REJECTED
            update_data['completed_at'] = now.isoformat()
        elif approval.get('manager_approval', {}).get('status') == 'approved':
            update_data['status'] = ScopeTaskApprovalStatus.FULLY_APPROVED
            update_data['completed_at'] = now.isoformat()
        else:
            update_data['status'] = ScopeTaskApprovalStatus.CLIENT_APPROVED
    
    await db.scope_task_approvals.update_one(
        {"id": approval_id},
        {"$set": update_data}
    )
    
    # Update scope status in SOW if fully approved or rejected
    if update_data.get('status') in [ScopeTaskApprovalStatus.FULLY_APPROVED, ScopeTaskApprovalStatus.MANAGER_REJECTED, ScopeTaskApprovalStatus.CLIENT_REJECTED]:
        sow = await db.enhanced_sows.find_one({"id": approval['sow_id']}, {"_id": 0})
        if sow:
            new_scope_status = "approved" if update_data['status'] == ScopeTaskApprovalStatus.FULLY_APPROVED else "rejected"
            for scope in sow.get('scopes', []):
                if scope.get('id') == approval['scope_id']:
                    scope['approval_status'] = new_scope_status
                    break
            await db.enhanced_sows.update_one(
                {"id": approval['sow_id']},
                {"$set": {"scopes": sow['scopes'], "updated_at": now.isoformat()}}
            )
    
    # Create notification for initiator
    status_msg = "approved" if action_data.action == "approve" else "rejected"
    await db.notifications.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": approval['initiated_by'],
        "type": "task_approval_update",
        "title": f"Task {status_msg.title()} by {action_data.approver_type.title()}",
        "message": f"'{approval['scope_name']}' has been {status_msg} by {current_user.full_name} ({action_data.approver_type})",
        "reference_type": "scope_task_approval",
        "reference_id": approval_id,
        "is_read": False,
        "created_at": now.isoformat()
    })
    
    return {
        "message": f"Task {status_msg} by {action_data.approver_type}",
        "status": update_data.get('status', approval['status'])
    }

# Background task to send reminders (called periodically)
async def send_approval_reminders():
    """Send reminders for pending approvals every 2 days"""
    now = datetime.now(timezone.utc)
    two_days_ago = now - timedelta(days=2)
    
    # Find approvals that need reminders
    pending_approvals = await db.scope_task_approvals.find({
        "status": {"$in": [
            ScopeTaskApprovalStatus.PENDING,
            ScopeTaskApprovalStatus.MANAGER_APPROVED,
            ScopeTaskApprovalStatus.CLIENT_APPROVED
        ]},
        "$or": [
            {"last_reminder_sent": None},
            {"last_reminder_sent": {"$lt": two_days_ago.isoformat()}}
        ]
    }, {"_id": 0}).to_list(100)
    
    for approval in pending_approvals:
        # Get SOW and project info
        sow = await db.enhanced_sows.find_one({"id": approval['sow_id']}, {"_id": 0})
        if not sow:
            continue
        
        project = await db.projects.find_one({"sow_id": approval['sow_id']}, {"_id": 0})
        
        # Send notification to all team members
        if project:
            for member in project.get('team_members', []):
                if member.get('user_id'):
                    await db.notifications.insert_one({
                        "id": str(uuid.uuid4()),
                        "user_id": member['user_id'],
                        "type": "task_approval_reminder",
                        "title": "Task Approval Reminder",
                        "message": f"Pending approval for '{approval['scope_name']}' - Please review",
                        "reference_type": "scope_task_approval",
                        "reference_id": approval['id'],
                        "is_read": False,
                        "created_at": now.isoformat()
                    })
        
        # Update reminder tracking
        await db.scope_task_approvals.update_one(
            {"id": approval['id']},
            {"$set": {
                "last_reminder_sent": now.isoformat(),
                "reminder_count": approval.get('reminder_count', 0) + 1
            }}
        )
    
    return len(pending_approvals)

@api_router.post("/scope-task-approvals/send-reminders")
async def trigger_approval_reminders(
    current_user: User = Depends(get_current_user)
):
    """Manually trigger approval reminders (admin only)"""
    if current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="Admin only")
    
    count = await send_approval_reminders()
    return {"message": f"Sent reminders for {count} pending approvals"}

# ==================== LEAVE REQUEST MODULE ====================

class LeaveType(str):
    CASUAL = "casual_leave"
    SICK = "sick_leave"
    EARNED = "earned_leave"

class LeaveRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    employee_id: str
    employee_name: str
    user_id: str
    
    leave_type: str  # casual_leave, sick_leave, earned_leave
    start_date: datetime
    end_date: datetime
    days: int
    reason: str
    
    status: str = "pending"  # pending, approved, rejected
    approval_request_id: Optional[str] = None
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class LeaveRequestCreate(BaseModel):
    leave_type: str
    start_date: datetime
    end_date: datetime
    reason: str
    is_half_day: bool = False
    half_day_type: str = "first_half"  # first_half or second_half

@api_router.post("/leave-requests")
async def create_leave_request(
    leave_data: LeaveRequestCreate,
    current_user: User = Depends(get_current_user)
):
    """Create a leave request. Manager's own leave escalates to their reporting manager + admin."""
    employee = await db.employees.find_one({"user_id": current_user.id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=400, detail="Employee record not found. Please contact HR.")
    
    # Calculate days - half day = 0.5
    if leave_data.is_half_day:
        days = 0.5
    else:
        days = (leave_data.end_date - leave_data.start_date).days + 1
    
    leave_balance = employee.get('leave_balance', {})
    leave_type_key = leave_data.leave_type.replace('_leave', '')
    available = leave_balance.get(leave_data.leave_type, 0) - leave_balance.get(f'used_{leave_type_key}', 0)
    
    if days > available:
        raise HTTPException(status_code=400, detail=f"Insufficient leave balance. Available: {available} days")
    
    # Check if user is a manager/reporting manager — their leave must escalate to THEIR manager + admin
    is_manager_role = current_user.role in ['manager', 'project_manager', 'hr_manager', 'principal_consultant']
    has_reportees = len(await get_direct_reportee_ids(current_user.id)) > 0
    requires_admin = is_manager_role or has_reportees  # Manager's own leave needs admin approval
    
    leave_request = {
        "id": str(uuid.uuid4()),
        "employee_id": employee['id'],
        "employee_name": f"{employee['first_name']} {employee['last_name']}",
        "user_id": current_user.id,
        "leave_type": leave_data.leave_type,
        "start_date": leave_data.start_date.isoformat(),
        "end_date": leave_data.end_date.isoformat() if not leave_data.is_half_day else leave_data.start_date.isoformat(),
        "days": days,
        "is_half_day": leave_data.is_half_day,
        "half_day_type": leave_data.half_day_type if leave_data.is_half_day else None,
        "reason": leave_data.reason,
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.leave_requests.insert_one(leave_request)
    
    # Create approval request — manager's leave escalates to their RM + admin
    half_day_label = f" ({leave_data.half_day_type.replace('_', ' ').title()})" if leave_data.is_half_day else ""
    approval = await create_approval_request(
        approval_type=ApprovalType.LEAVE_REQUEST,
        reference_id=leave_request['id'],
        reference_title=f"{leave_data.leave_type.replace('_', ' ').title()} - {days} day(s){half_day_label}",
        requester_id=current_user.id,
        requires_hr_approval=True,
        requires_admin_approval=requires_admin,
        is_client_facing=False
    )
    
    await db.leave_requests.update_one(
        {"id": leave_request['id']},
        {"$set": {"approval_request_id": approval['id']}}
    )
    
    await notify_admins(
        notif_type="leave_request",
        title="New Leave Request",
        message=f"{leave_request['employee_name']} requested {leave_data.leave_type.replace('_', ' ').title()} for {days} day(s).",
        reference_type="leave_request",
        reference_id=leave_request['id']
    )
    
    # Notify reporting manager (direct + second-line)
    reporting_chain = await get_reporting_chain(current_user.id, max_levels=2)
    for rm in reporting_chain:
        if rm.get('user_id'):
            await db.notifications.insert_one({
                "id": str(uuid.uuid4()),
                "user_id": rm['user_id'],
                "type": "leave_request",
                "title": "Reportee Leave Request",
                "message": f"{leave_request['employee_name']} requested {leave_data.leave_type.replace('_', ' ').title()} for {days} day(s).",
                "reference_type": "leave_request",
                "reference_id": leave_request['id'],
                "is_read": False,
                "created_at": datetime.now(timezone.utc).isoformat()
            })
    
    return {"message": "Leave request submitted for approval", "leave_request_id": leave_request['id']}

@api_router.get("/leave-requests")
async def get_leave_requests(current_user: User = Depends(get_current_user)):
    """Get leave requests for current user"""
    requests = await db.leave_requests.find(
        {"user_id": current_user.id},
        {"_id": 0}
    ).sort("created_at", -1).to_list(50)
    return requests

@api_router.get("/leave-requests/all")
async def get_all_leave_requests(current_user: User = Depends(get_current_user)):
    """Get all leave requests. HR/Admin see all. Reporting managers see their reportees'."""
    if current_user.role in [UserRole.ADMIN, UserRole.HR_MANAGER, UserRole.HR_EXECUTIVE]:
        requests = await db.leave_requests.find({}, {"_id": 0}).sort("created_at", -1).to_list(200)
        return requests
    
    # Reporting managers see their reportees' leave requests
    reportee_user_ids = await get_reportee_user_ids(current_user.id)
    if reportee_user_ids:
        requests = await db.leave_requests.find(
            {"user_id": {"$in": reportee_user_ids}},
            {"_id": 0}
        ).sort("created_at", -1).to_list(200)
        return requests
    
    raise HTTPException(status_code=403, detail="Not authorized")


@api_router.post("/leave-requests/{leave_id}/withdraw")
async def withdraw_leave_request(
    leave_id: str,
    current_user: User = Depends(get_current_user)
):
    """Withdraw a pending leave request. Only the requester can withdraw their own request."""
    # Find the leave request
    leave_request = await db.leave_requests.find_one({"id": leave_id}, {"_id": 0})
    if not leave_request:
        raise HTTPException(status_code=404, detail="Leave request not found")
    
    # Verify ownership
    if leave_request.get("user_id") != current_user.id:
        raise HTTPException(status_code=403, detail="You can only withdraw your own leave requests")
    
    # Check if it's still pending
    if leave_request.get("status") != "pending":
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot withdraw a leave request that is already {leave_request.get('status')}"
        )
    
    # Update leave request status to withdrawn
    await db.leave_requests.update_one(
        {"id": leave_id},
        {"$set": {
            "status": "withdrawn",
            "withdrawn_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    # Also update the approval request if it exists
    if leave_request.get("approval_request_id"):
        await db.approval_requests.update_one(
            {"id": leave_request["approval_request_id"]},
            {"$set": {
                "status": "withdrawn",
                "updated_at": datetime.now(timezone.utc).isoformat()
            }}
        )
    
    # Notify managers that the request was withdrawn
    await notify_admins(
        notif_type="leave_withdrawn",
        title="Leave Request Withdrawn",
        message=f"{leave_request['employee_name']} has withdrawn their leave request ({leave_request['leave_type'].replace('_', ' ').title()}, {leave_request['days']} days).",
        reference_type="leave_request",
        reference_id=leave_id
    )
    
    return {"message": "Leave request withdrawn successfully", "leave_id": leave_id}


# ==================== STAFFING REQUEST SYSTEM ====================

class StaffingRequestCreate(BaseModel):
    """Create a new staffing request"""
    model_config = ConfigDict(extra="ignore")
    project_name: str
    purpose: str
    budget_range: Optional[str] = None
    timeline: str  # Expected start date or timeline
    location: str
    work_mode: str = "office"  # office, client_site, remote
    skills_required: List[str] = []
    experience_years: Optional[int] = None
    headcount: int = 1
    priority: str = "normal"  # low, normal, high, urgent
    additional_notes: Optional[str] = None


@api_router.post("/staffing-requests")
async def create_staffing_request(
    request: StaffingRequestCreate,
    current_user: User = Depends(get_current_user)
):
    """Create a new staffing request - requires Admin approval"""
    # Get employee details for the requester
    employee = await db.employees.find_one({"user_id": current_user.id}, {"_id": 0})
    
    requester_name = f"{current_user.email}"
    reporting_manager = None
    requester_employee_id = None
    
    if employee:
        requester_name = f"{employee.get('first_name', '')} {employee.get('last_name', '')}".strip()
        reporting_manager = employee.get('reporting_manager')
        requester_employee_id = employee.get('employee_id') or employee.get('id')
    
    staffing_request = {
        "id": str(uuid.uuid4()),
        "requester_id": current_user.id,
        "requester_name": requester_name,
        "requester_employee_id": requester_employee_id,
        "requester_email": current_user.email,
        "reporting_manager": reporting_manager,
        "project_name": request.project_name,
        "purpose": request.purpose,
        "budget_range": request.budget_range,
        "timeline": request.timeline,
        "location": request.location,
        "work_mode": request.work_mode,
        "skills_required": request.skills_required,
        "experience_years": request.experience_years,
        "headcount": request.headcount,
        "priority": request.priority,
        "additional_notes": request.additional_notes,
        "status": "pending_approval",  # pending_approval, approved, rejected, fulfilled
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.staffing_requests.insert_one(staffing_request)
    
    # Notify admins about new staffing request
    await notify_admins(
        notif_type="staffing_request",
        title="New Staffing Request",
        message=f"{requester_name} submitted a staffing request for {request.project_name} ({request.headcount} resource(s)) - Priority: {request.priority}",
        reference_type="staffing_request",
        reference_id=staffing_request["id"]
    )
    
    return {"message": "Staffing request submitted for approval", "id": staffing_request["id"]}


@api_router.get("/staffing-requests")
async def get_staffing_requests(
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get staffing requests - Admin/HR see all, others see their own"""
    query = {}
    
    if current_user.role not in [UserRole.ADMIN, UserRole.HR_MANAGER]:
        # Regular users only see their own requests
        query["requester_id"] = current_user.id
    
    if status:
        query["status"] = status
    
    requests = await db.staffing_requests.find(query, {"_id": 0}).sort("created_at", -1).to_list(200)
    return requests


@api_router.get("/staffing-requests/{request_id}")
async def get_staffing_request(
    request_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get a specific staffing request"""
    request = await db.staffing_requests.find_one({"id": request_id}, {"_id": 0})
    if not request:
        raise HTTPException(status_code=404, detail="Staffing request not found")
    
    # Check access
    if current_user.role not in [UserRole.ADMIN, UserRole.HR_MANAGER]:
        if request.get("requester_id") != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")
    
    return request


@api_router.post("/staffing-requests/{request_id}/approve")
async def approve_staffing_request(
    request_id: str,
    current_user: User = Depends(get_current_user)
):
    """Approve a staffing request - Admin only"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only Admin can approve staffing requests")
    
    request = await db.staffing_requests.find_one({"id": request_id}, {"_id": 0})
    if not request:
        raise HTTPException(status_code=404, detail="Staffing request not found")
    
    if request.get("status") != "pending_approval":
        raise HTTPException(status_code=400, detail=f"Request is already {request.get('status')}")
    
    await db.staffing_requests.update_one(
        {"id": request_id},
        {"$set": {
            "status": "approved",
            "approved_by": current_user.id,
            "approved_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    # Notify requester
    await db.notifications.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": request["requester_id"],
        "type": "staffing_approved",
        "title": "Staffing Request Approved",
        "message": f"Your staffing request for {request['project_name']} has been approved",
        "reference_type": "staffing_request",
        "reference_id": request_id,
        "is_read": False,
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    return {"message": "Staffing request approved"}


@api_router.post("/staffing-requests/{request_id}/reject")
async def reject_staffing_request(
    request_id: str,
    reason: str = "",
    current_user: User = Depends(get_current_user)
):
    """Reject a staffing request - Admin only"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only Admin can reject staffing requests")
    
    request = await db.staffing_requests.find_one({"id": request_id}, {"_id": 0})
    if not request:
        raise HTTPException(status_code=404, detail="Staffing request not found")
    
    await db.staffing_requests.update_one(
        {"id": request_id},
        {"$set": {
            "status": "rejected",
            "rejected_by": current_user.id,
            "rejection_reason": reason,
            "rejected_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    # Notify requester
    await db.notifications.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": request["requester_id"],
        "type": "staffing_rejected",
        "title": "Staffing Request Rejected",
        "message": f"Your staffing request for {request['project_name']} was rejected. Reason: {reason or 'Not specified'}",
        "reference_type": "staffing_request",
        "reference_id": request_id,
        "is_read": False,
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    return {"message": "Staffing request rejected"}


@api_router.get("/leave-balance/reportees")
async def get_reportees_leave_balance(current_user: User = Depends(get_current_user)):
    """Get leave balance for reportees (view only for reporting managers). HR/Admin see all."""
    if current_user.role in [UserRole.ADMIN, UserRole.HR_MANAGER, UserRole.HR_EXECUTIVE]:
        employees = await db.employees.find({"is_active": True}, {"_id": 0, "id": 1, "first_name": 1, "last_name": 1, "leave_balance": 1, "user_id": 1}).to_list(200)
        return employees
    
    reportee_ids = await get_all_reportee_ids(current_user.id)
    if not reportee_ids:
        return []
    
    employees = await db.employees.find(
        {"id": {"$in": reportee_ids}, "is_active": True},
        {"_id": 0, "id": 1, "first_name": 1, "last_name": 1, "leave_balance": 1, "user_id": 1}
    ).to_list(200)
    return employees





# ==================== TRAVEL REIMBURSEMENT SYSTEM ====================

# Travel reimbursement rates (INR per km)
TRAVEL_RATES = {
    "car": 7.0,  # ₹7 per km for car
    "two_wheeler": 3.0,  # ₹3 per km for two-wheeler/bike
    "public_transport": 0,  # Actuals only
    "cab": 0  # Actuals only
}

class TravelReimbursement(BaseModel):
    """Travel reimbursement record linked to attendance or manual entry"""
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    employee_id: str
    employee_name: str
    travel_date: str  # YYYY-MM-DD
    
    # Type: "attendance" (auto from check-in/out) or "manual" (sales team input)
    travel_type: str = "manual"  # attendance, manual
    attendance_id: Optional[str] = None  # Link to attendance record if auto
    
    # Locations
    start_location: dict  # {latitude, longitude, address, name}
    end_location: dict  # {latitude, longitude, address, name}
    
    # Trip details
    is_round_trip: bool = False
    distance_km: float = 0
    vehicle_type: str = "car"  # car, two_wheeler, public_transport, cab
    rate_per_km: float = 7.0
    
    # Amounts
    calculated_amount: float = 0  # Auto-calculated from distance * rate
    actual_amount: Optional[float] = None  # For receipts/actuals
    final_amount: float = 0  # Amount to reimburse
    
    # For client visits
    client_id: Optional[str] = None
    client_name: Optional[str] = None
    project_id: Optional[str] = None
    project_name: Optional[str] = None
    
    # Status
    status: str = "pending"  # pending, approved, rejected, linked_to_expense
    expense_id: Optional[str] = None  # When converted to expense
    
    # Metadata
    notes: Optional[str] = None
    receipt: Optional[str] = None  # Base64 receipt for actuals
    created_by: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


def calculate_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance in kilometers using Haversine formula"""
    distance_meters = calculate_distance(lat1, lon1, lat2, lon2)
    return round(distance_meters / 1000, 2)


@api_router.get("/travel/rates")
async def get_travel_rates(current_user: User = Depends(get_current_user)):
    """Get current travel reimbursement rates"""
    return {
        "rates": TRAVEL_RATES,
        "description": {
            "car": "₹7 per km for personal car",
            "two_wheeler": "₹3 per km for bike/scooter",
            "public_transport": "Actual expense with receipt",
            "cab": "Actual expense with receipt"
        }
    }


@api_router.post("/travel/calculate-distance")
async def calculate_travel_distance(
    data: dict,
    current_user: User = Depends(get_current_user)
):
    """
    Calculate distance between two locations.
    Used by sales team for manual travel entries.
    """
    start = data.get("start_location", {})
    end = data.get("end_location", {})
    
    if not start.get("latitude") or not start.get("longitude"):
        raise HTTPException(status_code=400, detail="Start location coordinates required")
    if not end.get("latitude") or not end.get("longitude"):
        raise HTTPException(status_code=400, detail="End location coordinates required")
    
    distance = calculate_distance_km(
        start["latitude"], start["longitude"],
        end["latitude"], end["longitude"]
    )
    
    is_round_trip = data.get("is_round_trip", False)
    if is_round_trip:
        distance *= 2
    
    vehicle_type = data.get("vehicle_type", "car")
    rate = TRAVEL_RATES.get(vehicle_type, 0)
    
    calculated_amount = round(distance * rate, 2) if rate > 0 else 0
    
    return {
        "distance_km": distance,
        "is_round_trip": is_round_trip,
        "vehicle_type": vehicle_type,
        "rate_per_km": rate,
        "calculated_amount": calculated_amount,
        "requires_receipt": rate == 0
    }



# Google Maps API Key
GOOGLE_MAPS_API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY", "")

@api_router.get("/travel/location-search")
async def search_locations(
    query: str,
    lat: Optional[float] = None,
    lng: Optional[float] = None,
    current_user: User = Depends(get_current_user)
):
    """
    Search for locations using Google Geocoding API.
    Used by sales team to find client meeting locations.
    """
    if not query or len(query) < 2:
        raise HTTPException(status_code=400, detail="Query must be at least 2 characters")
    
    if not GOOGLE_MAPS_API_KEY:
        raise HTTPException(status_code=500, detail="Google Maps API key not configured")
    
    try:
        async with httpx.AsyncClient() as client:
            # Use Google Geocoding API (more widely enabled)
            params = {
                "address": query,
                "key": GOOGLE_MAPS_API_KEY,
                "components": "country:IN",  # Restrict to India
                "language": "en"
            }
            
            response = await client.get(
                "https://maps.googleapis.com/maps/api/geocode/json",
                params=params,
                timeout=10.0
            )
            
            if response.status_code != 200:
                return {"results": [], "error": "Location service unavailable"}
            
            data = response.json()
            
            if data.get("status") not in ["OK", "ZERO_RESULTS"]:
                return {"results": [], "error": data.get("error_message", f"API error: {data.get('status')}")}
            
            results = []
            
            for result in data.get("results", [])[:5]:  # Limit to 5 results
                geometry = result.get("geometry", {})
                location = geometry.get("location", {})
                
                # Extract short name from address components
                address_components = result.get("address_components", [])
                name = result.get("formatted_address", "").split(",")[0]
                
                # Try to get a better name from components
                for comp in address_components:
                    types = comp.get("types", [])
                    if "point_of_interest" in types or "establishment" in types:
                        name = comp.get("long_name", name)
                        break
                    elif "sublocality_level_1" in types or "locality" in types:
                        name = comp.get("long_name", name)
                
                results.append({
                    "place_id": result.get("place_id", ""),
                    "name": name,
                    "address": result.get("formatted_address", ""),
                    "latitude": location.get("lat", 0),
                    "longitude": location.get("lng", 0),
                    "types": result.get("types", [])
                })
            
            return {"results": results}
            
    except Exception as e:
        return {"results": [], "error": str(e)}


@api_router.get("/travel/place-details/{place_id}")
async def get_place_details(
    place_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get detailed place information including coordinates from Google Geocoding API.
    """
    if not GOOGLE_MAPS_API_KEY:
        raise HTTPException(status_code=500, detail="Google Maps API key not configured")
    
    try:
        async with httpx.AsyncClient() as client:
            # Use place_id with Geocoding API
            response = await client.get(
                "https://maps.googleapis.com/maps/api/geocode/json",
                params={
                    "place_id": place_id,
                    "key": GOOGLE_MAPS_API_KEY
                },
                timeout=10.0
            )
            
            if response.status_code != 200:
                raise HTTPException(status_code=500, detail="Failed to get place details")
            
            data = response.json()
            
            if data.get("status") != "OK" or not data.get("results"):
                raise HTTPException(status_code=404, detail="Place not found")
            
            result = data["results"][0]
            geometry = result.get("geometry", {})
            location = geometry.get("location", {})
            
            name = result.get("formatted_address", "").split(",")[0]
            
            return {
                "place_id": result.get("place_id"),
                "name": name,
                "address": result.get("formatted_address", ""),
                "latitude": location.get("lat", 0),
                "longitude": location.get("lng", 0)
            }
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@api_router.post("/travel/reimbursement")
async def create_travel_reimbursement(
    data: dict,
    current_user: User = Depends(get_current_user)
):
    """
    Create a travel reimbursement request.
    Supports both auto (from attendance) and manual entries.
    """
    employee = await db.employees.find_one({"user_id": current_user.id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=400, detail="No employee record found")
    
    start_location = data.get("start_location", {})
    end_location = data.get("end_location", {})
    
    if not start_location.get("latitude") or not end_location.get("latitude"):
        raise HTTPException(status_code=400, detail="Both start and end locations are required")
    
    # Calculate distance
    distance = calculate_distance_km(
        start_location["latitude"], start_location["longitude"],
        end_location["latitude"], end_location["longitude"]
    )
    
    is_round_trip = data.get("is_round_trip", False)
    if is_round_trip:
        distance *= 2
    
    vehicle_type = data.get("vehicle_type", "car")
    rate = TRAVEL_RATES.get(vehicle_type, 0)
    calculated_amount = round(distance * rate, 2)
    
    # For actuals (cab/public transport), use the actual amount
    actual_amount = data.get("actual_amount")
    final_amount = actual_amount if actual_amount else calculated_amount
    
    travel_record = {
        "id": str(uuid.uuid4()),
        "employee_id": employee["id"],
        "employee_name": f"{employee['first_name']} {employee['last_name']}",
        "travel_date": data.get("travel_date", datetime.now(timezone.utc).strftime("%Y-%m-%d")),
        "travel_type": data.get("travel_type", "manual"),
        "attendance_id": data.get("attendance_id"),
        "start_location": start_location,
        "end_location": end_location,
        "is_round_trip": is_round_trip,
        "distance_km": distance,
        "vehicle_type": vehicle_type,
        "rate_per_km": rate,
        "calculated_amount": calculated_amount,
        "actual_amount": actual_amount,
        "final_amount": final_amount,
        "client_id": data.get("client_id"),
        "client_name": data.get("client_name"),
        "project_id": data.get("project_id"),
        "project_name": data.get("project_name"),
        "status": "pending",
        "notes": data.get("notes"),
        "receipt": data.get("receipt"),
        "created_by": current_user.id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.travel_reimbursements.insert_one(travel_record)
    
    return {
        "message": "Travel reimbursement request created",
        "id": travel_record["id"],
        "distance_km": distance,
        "calculated_amount": calculated_amount,
        "final_amount": final_amount
    }


@api_router.get("/travel/reimbursements")
async def get_travel_reimbursements(
    status: Optional[str] = None,
    month: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get travel reimbursement requests for current user or all (HR/Admin)"""
    query = {}
    
    if current_user.role not in ["admin", "hr_manager", "manager"]:
        employee = await db.employees.find_one({"user_id": current_user.id}, {"_id": 0})
        if employee:
            query["employee_id"] = employee["id"]
    
    if status:
        query["status"] = status
    
    if month:
        query["travel_date"] = {"$regex": f"^{month}"}
    
    records = await db.travel_reimbursements.find(query, {"_id": 0, "receipt": 0}).sort("created_at", -1).to_list(500)
    
    # Calculate totals
    total_distance = sum(r.get("distance_km", 0) for r in records)
    total_amount = sum(r.get("final_amount", 0) for r in records)
    pending_amount = sum(r.get("final_amount", 0) for r in records if r.get("status") == "pending")
    
    return {
        "records": records,
        "summary": {
            "total_records": len(records),
            "total_distance_km": round(total_distance, 2),
            "total_amount": round(total_amount, 2),
            "pending_amount": round(pending_amount, 2)
        }
    }


@api_router.get("/travel/reimbursements/{travel_id}")
async def get_travel_reimbursement(
    travel_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get a specific travel reimbursement record"""
    record = await db.travel_reimbursements.find_one({"id": travel_id}, {"_id": 0})
    if not record:
        raise HTTPException(status_code=404, detail="Travel reimbursement not found")
    
    return record


@api_router.post("/travel/reimbursements/{travel_id}/approve")
async def approve_travel_reimbursement(
    travel_id: str,
    current_user: User = Depends(get_current_user)
):
    """Approve a travel reimbursement (HR/Admin only)"""
    if current_user.role not in ["admin", "hr_manager", "manager"]:
        raise HTTPException(status_code=403, detail="Only HR/Admin/Manager can approve")
    
    record = await db.travel_reimbursements.find_one({"id": travel_id}, {"_id": 0})
    if not record:
        raise HTTPException(status_code=404, detail="Travel reimbursement not found")
    
    if record["status"] != "pending":
        raise HTTPException(status_code=400, detail="Only pending requests can be approved")
    
    await db.travel_reimbursements.update_one(
        {"id": travel_id},
        {"$set": {
            "status": "approved",
            "approved_by": current_user.id,
            "approved_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    return {"message": "Travel reimbursement approved"}


@api_router.post("/travel/reimbursements/{travel_id}/reject")
async def reject_travel_reimbursement(
    travel_id: str,
    data: dict = None,
    current_user: User = Depends(get_current_user)
):
    """Reject a travel reimbursement (HR/Admin only)"""
    if current_user.role not in ["admin", "hr_manager", "manager"]:
        raise HTTPException(status_code=403, detail="Only HR/Admin/Manager can reject")
    
    record = await db.travel_reimbursements.find_one({"id": travel_id}, {"_id": 0})
    if not record:
        raise HTTPException(status_code=404, detail="Travel reimbursement not found")
    
    await db.travel_reimbursements.update_one(
        {"id": travel_id},
        {"$set": {
            "status": "rejected",
            "rejection_reason": data.get("reason", "Rejected") if data else "Rejected",
            "rejected_by": current_user.id,
            "rejected_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    return {"message": "Travel reimbursement rejected"}


@api_router.post("/travel/reimbursements/{travel_id}/convert-to-expense")
async def convert_travel_to_expense(
    travel_id: str,
    current_user: User = Depends(get_current_user)
):
    """Convert an approved travel reimbursement to an expense for payroll integration"""
    if current_user.role not in ["admin", "hr_manager"]:
        raise HTTPException(status_code=403, detail="Only HR/Admin can convert to expense")
    
    record = await db.travel_reimbursements.find_one({"id": travel_id}, {"_id": 0})
    if not record:
        raise HTTPException(status_code=404, detail="Travel reimbursement not found")
    
    if record["status"] != "approved":
        raise HTTPException(status_code=400, detail="Only approved requests can be converted")
    
    # Create expense entry
    expense_id = f"TRV{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}{str(uuid.uuid4())[:4].upper()}"
    
    expense_doc = {
        "id": expense_id,
        "employee_id": record["employee_id"],
        "employee_name": record["employee_name"],
        "description": f"Travel Reimbursement: {record['start_location'].get('name', 'Start')} to {record['end_location'].get('name', 'End')}" + (" (Round Trip)" if record.get("is_round_trip") else ""),
        "category": "travel_reimbursement",
        "expense_date": record["travel_date"],
        "line_items": [{
            "description": f"Travel: {record['distance_km']} km @ ₹{record['rate_per_km']}/km ({record['vehicle_type']})",
            "category": "travel_reimbursement",
            "amount": record["final_amount"],
            "date": record["travel_date"]
        }],
        "total_amount": record["final_amount"],
        "status": "approved",  # Already approved as travel claim
        "travel_reimbursement_id": travel_id,
        "client_id": record.get("client_id"),
        "client_name": record.get("client_name"),
        "project_id": record.get("project_id"),
        "project_name": record.get("project_name"),
        "notes": record.get("notes"),
        "created_by": current_user.id,
        "approved_by": current_user.id,
        "approved_at": datetime.now(timezone.utc).isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.expenses.insert_one(expense_doc)
    
    # Update travel record
    await db.travel_reimbursements.update_one(
        {"id": travel_id},
        {"$set": {
            "status": "linked_to_expense",
            "expense_id": expense_id,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    return {
        "message": "Travel reimbursement converted to expense",
        "expense_id": expense_id,
        "amount": record["final_amount"]
    }


@api_router.get("/my/travel-reimbursements")
async def get_my_travel_reimbursements(
    month: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get current user's travel reimbursements"""
    employee = await db.employees.find_one({"user_id": current_user.id}, {"_id": 0})
    if not employee:
        return {"records": [], "summary": {}}
    
    query = {"employee_id": employee["id"]}
    if month:
        query["travel_date"] = {"$regex": f"^{month}"}
    
    records = await db.travel_reimbursements.find(query, {"_id": 0, "receipt": 0}).sort("created_at", -1).to_list(200)
    
    # Calculate totals
    total_distance = sum(r.get("distance_km", 0) for r in records)
    total_amount = sum(r.get("final_amount", 0) for r in records)
    pending_count = len([r for r in records if r.get("status") == "pending"])
    approved_count = len([r for r in records if r.get("status") == "approved"])
    
    return {
        "records": records,
        "summary": {
            "total_records": len(records),
            "pending_count": pending_count,
            "approved_count": approved_count,
            "total_distance_km": round(total_distance, 2),
            "total_amount": round(total_amount, 2)
        }
    }


@api_router.post("/attendance/{attendance_id}/calculate-travel")
async def calculate_attendance_travel(
    attendance_id: str,
    data: dict,
    current_user: User = Depends(get_current_user)
):
    """
    Calculate travel reimbursement from attendance record (for consultants).
    Uses check-in and check-out locations.
    """
    employee = await db.employees.find_one({"user_id": current_user.id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=400, detail="No employee record found")
    
    # Get attendance record
    attendance = await db.attendance.find_one({"id": attendance_id}, {"_id": 0})
    if not attendance:
        raise HTTPException(status_code=404, detail="Attendance record not found")
    
    # Check if this attendance belongs to the user
    if attendance.get("employee_id") != employee["id"]:
        raise HTTPException(status_code=403, detail="Not authorized to access this attendance")
    
    check_in_location = attendance.get("geo_location", {})
    check_out_location = attendance.get("check_out_location", {})
    
    if not check_in_location.get("latitude") or not check_out_location.get("latitude"):
        raise HTTPException(status_code=400, detail="Both check-in and check-out locations are required")
    
    # For consultants: calculate from home/office to client site
    # Get home location (from employee profile or settings)
    home_location = data.get("home_location", {})
    
    # Calculate distances
    vehicle_type = data.get("vehicle_type", "car")
    rate = TRAVEL_RATES.get(vehicle_type, 7.0)
    is_round_trip = data.get("is_round_trip", True)  # Default round trip
    
    # Distance from start point to check-in (client site)
    if home_location.get("latitude"):
        distance = calculate_distance_km(
            home_location["latitude"], home_location["longitude"],
            check_in_location["latitude"], check_in_location["longitude"]
        )
    else:
        # Use check-in to check-out distance
        distance = calculate_distance_km(
            check_in_location["latitude"], check_in_location["longitude"],
            check_out_location["latitude"], check_out_location["longitude"]
        )
    
    if is_round_trip:
        distance *= 2
    
    calculated_amount = round(distance * rate, 2)
    
    return {
        "attendance_id": attendance_id,
        "travel_date": attendance.get("date"),
        "check_in_location": {
            "latitude": check_in_location.get("latitude"),
            "longitude": check_in_location.get("longitude"),
            "address": check_in_location.get("address")
        },
        "check_out_location": {
            "latitude": check_out_location.get("latitude"),
            "longitude": check_out_location.get("longitude"),
            "address": check_out_location.get("address")
        },
        "distance_km": distance,
        "is_round_trip": is_round_trip,
        "vehicle_type": vehicle_type,
        "rate_per_km": rate,
        "calculated_amount": calculated_amount
    }


@api_router.get("/travel/stats")
async def get_travel_stats(
    month: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get travel reimbursement statistics (HR/Admin)"""
    if current_user.role not in ["admin", "hr_manager"]:
        raise HTTPException(status_code=403, detail="Only HR/Admin can view stats")
    
    query = {}
    if month:
        query["travel_date"] = {"$regex": f"^{month}"}
    
    # Get all records
    records = await db.travel_reimbursements.find(query, {"_id": 0}).to_list(2000)
    
    # Calculate stats
    total_records = len(records)
    pending = [r for r in records if r.get("status") == "pending"]
    approved = [r for r in records if r.get("status") == "approved"]
    
    total_distance = sum(r.get("distance_km", 0) for r in records)
    total_amount = sum(r.get("final_amount", 0) for r in records)
    pending_amount = sum(r.get("final_amount", 0) for r in pending)
    
    # By vehicle type
    by_vehicle = {}
    for r in records:
        vt = r.get("vehicle_type", "unknown")
        if vt not in by_vehicle:
            by_vehicle[vt] = {"count": 0, "distance": 0, "amount": 0}
        by_vehicle[vt]["count"] += 1
        by_vehicle[vt]["distance"] += r.get("distance_km", 0)
        by_vehicle[vt]["amount"] += r.get("final_amount", 0)
    
    return {
        "total_records": total_records,
        "pending_count": len(pending),
        "approved_count": len(approved),
        "total_distance_km": round(total_distance, 2),
        "total_amount": round(total_amount, 2),
        "pending_amount": round(pending_amount, 2),
        "by_vehicle_type": by_vehicle
    }



# ==================== REPORTS MODULE ====================

class ReportRequest(BaseModel):
    report_id: str
    format: str = "excel"  # excel or pdf
    filters: Optional[Dict[str, Any]] = None

# Role-based report access mapping
REPORT_ROLE_ACCESS = {
    "admin": list(REPORT_DEFINITIONS.keys()),  # Admin sees all
    "manager": ["lead_summary", "lead_conversion_funnel", "lead_source_analysis", 
                "client_overview", "client_revenue_analysis", "client_industry_breakdown",
                "sales_pipeline_status", "quotation_analysis", "agreement_status",
                "employee_directory", "employee_department_analysis", "leave_utilization",
                "expense_summary", "expense_by_category", "sow_status_report", 
                "project_summary", "consultant_allocation", "approval_turnaround", "pending_approvals"],
    "hr_manager": ["employee_directory", "employee_department_analysis", "leave_utilization",
                   "expense_summary", "expense_by_category", "approval_turnaround", "pending_approvals"],
    "hr_executive": ["employee_directory"],
    "project_manager": ["client_overview", "agreement_status", "sow_status_report", 
                        "project_summary", "consultant_allocation"],
    "executive": ["lead_summary", "lead_conversion_funnel", "lead_source_analysis",
                  "client_overview", "client_industry_breakdown", "sales_pipeline_status",
                  "quotation_analysis", "agreement_status"],
    "account_manager": ["lead_summary", "lead_conversion_funnel", "lead_source_analysis",
                        "client_overview", "client_revenue_analysis", "client_industry_breakdown",
                        "sales_pipeline_status", "quotation_analysis", "agreement_status"],
    "principal_consultant": ["sow_status_report", "project_summary", "consultant_allocation"],
}

def get_accessible_reports(role: str) -> List[str]:
    """Get list of report IDs accessible by role"""
    if role == "admin":
        return list(REPORT_DEFINITIONS.keys())
    return REPORT_ROLE_ACCESS.get(role, [])

@api_router.get("/reports")
async def get_available_reports(current_user: User = Depends(get_current_user)):
    """Get list of reports available to current user based on role"""
    accessible = get_accessible_reports(current_user.role)
    
    reports = []
    for report_id, definition in REPORT_DEFINITIONS.items():
        if report_id in accessible:
            reports.append({
                "id": report_id,
                "name": definition["name"],
                "description": definition["description"],
                "category": definition["category"]
            })
    
    # Group by category
    by_category = {}
    for r in reports:
        cat = r["category"]
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(r)
    
    return {
        "reports": reports,
        "by_category": by_category,
        "total_available": len(reports)
    }

@api_router.get("/reports/{report_id}/preview")
async def preview_report(
    report_id: str,
    current_user: User = Depends(get_current_user)
):
    """Preview report data without downloading"""
    accessible = get_accessible_reports(current_user.role)
    if report_id not in accessible:
        raise HTTPException(status_code=403, detail="Not authorized to access this report")
    
    if report_id not in REPORT_DEFINITIONS:
        raise HTTPException(status_code=404, detail="Report not found")
    
    # Get data generator function
    data_functions = get_report_data_functions()
    if report_id not in data_functions:
        raise HTTPException(status_code=500, detail="Report generator not implemented")
    
    # Generate report data
    report_data = await data_functions[report_id](db)
    
    return {
        "report_id": report_id,
        "report_info": REPORT_DEFINITIONS[report_id],
        "data": report_data
    }

@api_router.post("/reports/generate")
async def generate_report(
    request: ReportRequest,
    current_user: User = Depends(get_current_user)
):
    """Generate and download report in specified format"""
    accessible = get_accessible_reports(current_user.role)
    if request.report_id not in accessible:
        raise HTTPException(status_code=403, detail="Not authorized to access this report")
    
    if request.report_id not in REPORT_DEFINITIONS:
        raise HTTPException(status_code=404, detail="Report not found")
    
    # Get data generator function
    data_functions = get_report_data_functions()
    if request.report_id not in data_functions:
        raise HTTPException(status_code=500, detail="Report generator not implemented")
    
    # Generate report data
    report_data = await data_functions[request.report_id](db, request.filters)
    
    # Generate file based on format
    if request.format == "excel":
        file_bytes = generate_excel(report_data)
        filename = f"{request.report_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    elif request.format == "pdf":
        file_bytes = generate_pdf(report_data)
        filename = f"{request.report_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        media_type = "application/pdf"
    else:
        raise HTTPException(status_code=400, detail="Invalid format. Use 'excel' or 'pdf'")
    
    return Response(
        content=file_bytes,
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@api_router.get("/reports/categories")
async def get_report_categories(current_user: User = Depends(get_current_user)):
    """Get list of report categories"""
    categories = set()
    for definition in REPORT_DEFINITIONS.values():
        categories.add(definition["category"])
    return sorted(list(categories))

@api_router.get("/reports/stats")
async def get_report_stats(current_user: User = Depends(get_current_user)):
    """Get quick stats for dashboard"""
    if current_user.role not in ["admin", "manager"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Quick counts from various collections
    leads_count = await db.leads.count_documents({})
    clients_count = await db.clients.count_documents({"is_active": True})
    employees_count = await db.employees.count_documents({})
    projects_count = await db.projects.count_documents({})
    pending_approvals = await db.approval_requests.count_documents({"overall_status": "pending"})
    
    # Revenue calculation
    clients = await db.clients.find({"is_active": True}, {"revenue_history": 1}).to_list(500)
    total_revenue = sum(
        sum(r.get('amount', 0) for r in c.get('revenue_history', []))
        for c in clients
    )
    
    # Expense stats
    expense_pipeline = [
        {"$match": {"status": {"$in": ["pending", "approved"]}}},
        {"$group": {"_id": "$status", "total": {"$sum": "$total_amount"}}}
    ]
    expense_stats = await db.expenses.aggregate(expense_pipeline).to_list(10)
    expense_by_status = {e['_id']: e['total'] for e in expense_stats}
    
    return {
        "leads": leads_count,
        "clients": clients_count,
        "employees": employees_count,
        "projects": projects_count,
        "pending_approvals": pending_approvals,
        "total_revenue": total_revenue,
        "pending_expenses": expense_by_status.get('pending', 0),
        "approved_expenses": expense_by_status.get('approved', 0)
    }




# ==================== PAYROLL MODULE ====================

@api_router.get("/payroll/salary-components")
async def get_salary_components(current_user: User = Depends(get_current_user)):
    """Get salary component configuration"""
    config = await db.payroll_config.find_one({"type": "salary_components"}, {"_id": 0})
    if not config:
        default = {
            "type": "salary_components",
            "earnings": [
                {"name": "Basic Salary", "key": "basic", "percentage": 40, "is_default": True},
                {"name": "HRA", "key": "hra", "percentage": 20, "is_default": True},
                {"name": "Special Allowance", "key": "special_allowance", "percentage": 20, "is_default": True},
                {"name": "Conveyance Allowance", "key": "conveyance", "fixed": 1600, "is_default": True},
                {"name": "Medical Allowance", "key": "medical", "fixed": 1250, "is_default": True}
            ],
            "deductions": [
                {"name": "Provident Fund", "key": "pf", "percentage": 12, "is_default": True},
                {"name": "Professional Tax", "key": "pt", "fixed": 200, "is_default": True},
                {"name": "ESI", "key": "esi", "percentage": 0.75, "is_default": True}
            ]
        }
        await db.payroll_config.insert_one(default)
        return default
    return config

@api_router.post("/payroll/salary-components")
async def update_salary_components(data: dict, current_user: User = Depends(get_current_user)):
    """Update salary components (Admin/HR only)"""
    if current_user.role not in ["admin", "hr_manager"]:
        raise HTTPException(status_code=403, detail="Only Admin/HR Manager can update salary components")
    await db.payroll_config.update_one({"type": "salary_components"}, {"$set": data}, upsert=True)
    return {"message": "Salary components updated"}

@api_router.post("/payroll/salary-components/add")
async def add_salary_component(data: dict, current_user: User = Depends(get_current_user)):
    """Add a new salary component (Admin/HR only)"""
    if current_user.role not in ["admin", "hr_manager"]:
        raise HTTPException(status_code=403, detail="Only Admin/HR Manager can modify salary components")
    comp_type = data.get("type")  # "earnings" or "deductions"
    if comp_type not in ["earnings", "deductions"]:
        raise HTTPException(status_code=400, detail="type must be 'earnings' or 'deductions'")
    name = data.get("name", "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Component name is required")
    key = data.get("key", name.lower().replace(" ", "_"))
    component = {"name": name, "key": key, "is_default": False}
    if data.get("percentage"):
        component["percentage"] = float(data["percentage"])
    elif data.get("fixed") is not None:
        component["fixed"] = float(data["fixed"])
    else:
        raise HTTPException(status_code=400, detail="Either percentage or fixed amount required")
    config = await db.payroll_config.find_one({"type": "salary_components"}, {"_id": 0})
    if not config:
        raise HTTPException(status_code=400, detail="Salary components not initialized")
    existing_keys = [c["key"] for c in config.get(comp_type, [])]
    if key in existing_keys:
        raise HTTPException(status_code=400, detail=f"Component with key '{key}' already exists")
    config[comp_type].append(component)
    await db.payroll_config.update_one({"type": "salary_components"}, {"$set": {comp_type: config[comp_type]}})
    return {"message": f"{name} added to {comp_type}"}

@api_router.delete("/payroll/salary-components/{comp_type}/{comp_key}")
async def remove_salary_component(comp_type: str, comp_key: str, current_user: User = Depends(get_current_user)):
    """Remove a salary component (Admin/HR only). Cannot remove default components."""
    if current_user.role not in ["admin", "hr_manager"]:
        raise HTTPException(status_code=403, detail="Only Admin/HR Manager can modify salary components")
    if comp_type not in ["earnings", "deductions"]:
        raise HTTPException(status_code=400, detail="type must be 'earnings' or 'deductions'")
    config = await db.payroll_config.find_one({"type": "salary_components"}, {"_id": 0})
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")
    updated = [c for c in config.get(comp_type, []) if c["key"] != comp_key]
    if len(updated) == len(config.get(comp_type, [])):
        raise HTTPException(status_code=404, detail="Component not found")
    await db.payroll_config.update_one({"type": "salary_components"}, {"$set": {comp_type: updated}})
    return {"message": f"Component removed from {comp_type}"}


# --- Payroll Input Table (Monthly per-employee overrides) ---
@api_router.get("/payroll/inputs")
async def get_payroll_inputs(month: str, current_user: User = Depends(get_current_user)):
    """Get payroll input data for a month (Admin/HR only)"""
    if current_user.role not in ["admin", "hr_manager", "hr_executive"]:
        raise HTTPException(status_code=403, detail="Only HR can access payroll inputs")
    inputs = await db.payroll_inputs.find({"month": month}, {"_id": 0}).to_list(500)
    input_map = {i["employee_id"]: i for i in inputs}
    employees = await db.employees.find({"is_active": True}, {"_id": 0, "id": 1, "employee_id": 1, "first_name": 1, "last_name": 1, "department": 1, "salary": 1}).to_list(500)
    result = []
    for emp in employees:
        existing = input_map.get(emp["id"], {})
        result.append({
            "employee_id": emp["id"],
            "emp_code": emp.get("employee_id", ""),
            "name": f"{emp['first_name']} {emp['last_name']}",
            "department": emp.get("department", ""),
            "salary": emp.get("salary", 0),
            "month": month,
            "present_days": existing.get("present_days", 0),
            "absent_days": existing.get("absent_days", 0),
            "public_holidays": existing.get("public_holidays", 0),
            "leaves": existing.get("leaves", 0),
            "working_days": existing.get("working_days", 30),
            "incentive": existing.get("incentive", 0),
            "incentive_reason": existing.get("incentive_reason", ""),
            "expense_reimbursement": existing.get("expense_reimbursement", 0),
            "expense_ids": existing.get("expense_ids", []),
            "advance": existing.get("advance", 0),
            "advance_reason": existing.get("advance_reason", ""),
            "penalty": existing.get("penalty", 0),
            "penalty_reason": existing.get("penalty_reason", ""),
            "overtime_hours": existing.get("overtime_hours", 0),
            "remarks": existing.get("remarks", ""),
        })
    return result

@api_router.post("/payroll/inputs")
async def save_payroll_input(data: dict, current_user: User = Depends(get_current_user)):
    """Save payroll input for a single employee for a month (Admin/HR only). All numeric fields mandatory."""
    if current_user.role not in ["admin", "hr_manager"]:
        raise HTTPException(status_code=403, detail="Only Admin/HR Manager can update payroll inputs")
    employee_id = data.get("employee_id")
    month = data.get("month")
    if not employee_id or not month:
        raise HTTPException(status_code=400, detail="employee_id and month required")
    required_fields = ["working_days", "present_days", "absent_days", "public_holidays", "leaves", "overtime_hours", "incentive", "advance", "penalty"]
    for f in required_fields:
        if data.get(f) is None or data.get(f) == '':
            raise HTTPException(status_code=400, detail=f"Field '{f.replace('_', ' ')}' is mandatory. Enter 0 if not applicable.")
    input_doc = {
        "employee_id": employee_id,
        "month": month,
        "present_days": data.get("present_days", 0),
        "absent_days": data.get("absent_days", 0),
        "public_holidays": data.get("public_holidays", 0),
        "leaves": data.get("leaves", 0),
        "working_days": data.get("working_days", 30),
        "incentive": data.get("incentive", 0),
        "incentive_reason": data.get("incentive_reason", ""),
        "advance": data.get("advance", 0),
        "advance_reason": data.get("advance_reason", ""),
        "penalty": data.get("penalty", 0),
        "penalty_reason": data.get("penalty_reason", ""),
        "overtime_hours": data.get("overtime_hours", 0),
        "remarks": data.get("remarks", ""),
        "updated_by": current_user.id,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    await db.payroll_inputs.update_one(
        {"employee_id": employee_id, "month": month},
        {"$set": input_doc},
        upsert=True
    )
    return {"message": "Payroll input saved"}

@api_router.post("/payroll/inputs/bulk")
async def save_payroll_inputs_bulk(data: dict, current_user: User = Depends(get_current_user)):
    """Save payroll inputs for multiple employees (Admin/HR only)"""
    if current_user.role not in ["admin", "hr_manager"]:
        raise HTTPException(status_code=403, detail="Only Admin/HR Manager can update payroll inputs")
    month = data.get("month")
    inputs = data.get("inputs", [])
    if not month or not inputs:
        raise HTTPException(status_code=400, detail="month and inputs required")
    saved = 0
    for inp in inputs:
        inp["month"] = month
        inp["updated_by"] = current_user.id
        inp["updated_at"] = datetime.now(timezone.utc).isoformat()
        await db.payroll_inputs.update_one(
            {"employee_id": inp["employee_id"], "month": month},
            {"$set": inp},
            upsert=True
        )
        saved += 1
    return {"message": f"Saved {saved} payroll inputs"}

@api_router.get("/payroll/salary-slips")
async def get_salary_slips(employee_id: Optional[str] = None, month: Optional[str] = None, current_user: User = Depends(get_current_user)):
    """Get generated salary slips"""
    query = {}
    if employee_id:
        query["employee_id"] = employee_id
    if month:
        query["month"] = month
    # Non-HR can only see their own
    if current_user.role not in ["admin", "hr_manager", "hr_executive"]:
        emp = await db.employees.find_one({"user_id": current_user.id}, {"_id": 0, "id": 1})
        if emp:
            query["employee_id"] = emp["id"]
        else:
            return []
    slips = await db.salary_slips.find(query, {"_id": 0}).sort("month", -1).to_list(500)
    return slips

@api_router.post("/payroll/generate-slip")
async def generate_salary_slip(data: dict, current_user: User = Depends(get_current_user)):
    """Generate salary slip for an employee. Admin/HR only. Cannot modify own payroll if non-admin."""
    if current_user.role not in ["admin", "hr_manager"]:
        raise HTTPException(status_code=403, detail="Only Admin/HR Manager can generate salary slips")
    employee_id = data.get("employee_id")
    month = data.get("month")  # YYYY-MM
    if not employee_id or not month:
        raise HTTPException(status_code=400, detail="employee_id and month required")
    
    # RULE: Non-admin managers cannot generate their own salary slip
    if current_user.role != "admin":
        own_emp = await db.employees.find_one({"user_id": current_user.id}, {"_id": 0, "id": 1})
        if own_emp and own_emp['id'] == employee_id:
            raise HTTPException(status_code=403, detail="You cannot generate your own salary slip. Only admin can modify your payroll.")
    
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # RULE: Employee must be Go-Live Active to generate salary slip
    go_live_status = employee.get("go_live_status")
    if go_live_status != "active":
        emp_name = f"{employee.get('first_name', '')} {employee.get('last_name', '')}".strip()
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot generate salary slip for {emp_name}. Employee is not Go-Live Active. Current status: {go_live_status or 'Not Started'}"
        )
    
    gross_salary = employee.get("salary", 0) or 0
    if gross_salary <= 0:
        raise HTTPException(status_code=400, detail="Employee salary not configured")
    
    # Check if employee has an approved CTC structure effective for this month
    active_ctc = await db.ctc_structures.find_one({
        "employee_id": employee_id,
        "status": "active",
        "effective_month": {"$lte": month}
    }, {"_id": 0}, sort=[("effective_month", -1)])
    
    earnings = []
    total_earnings = 0
    deductions = []
    total_deductions = 0
    
    if active_ctc and active_ctc.get("components"):
        # Use employee's approved CTC structure
        for key, comp in active_ctc["components"].items():
            if not comp.get("enabled", True):
                continue
            monthly_amount = comp.get("monthly", 0)
            if monthly_amount <= 0:
                continue
            
            if comp.get("is_earning", True) and not comp.get("is_deferred"):
                earnings.append({
                    "name": comp.get("name", key), 
                    "key": key, 
                    "amount": round(monthly_amount, 2)
                })
                total_earnings += monthly_amount
            elif comp.get("is_deduction"):
                deductions.append({
                    "name": comp.get("name", key), 
                    "key": key, 
                    "amount": round(monthly_amount, 2)
                })
                total_deductions += monthly_amount
        
        # Update gross_salary from CTC summary
        gross_salary = active_ctc.get("summary", {}).get("gross_monthly", gross_salary)
    else:
        # Fall back to global salary components
        config = await db.payroll_config.find_one({"type": "salary_components"}, {"_id": 0})
        if not config:
            raise HTTPException(status_code=400, detail="Salary components not configured")
        
        for comp in config.get("earnings", []):
            if comp.get("percentage"):
                amount = round(gross_salary * comp["percentage"] / 100, 2)
            else:
                amount = comp.get("fixed", 0)
            earnings.append({"name": comp["name"], "key": comp["key"], "amount": amount})
            total_earnings += amount
        
        for comp in config.get("deductions", []):
            if comp.get("percentage"):
                amount = round(gross_salary * comp["percentage"] / 100, 2)
            else:
                amount = comp.get("fixed", 0)
            deductions.append({"name": comp["name"], "key": comp["key"], "amount": amount})
            total_deductions += amount
    
    # Get attendance for the month
    att_records = await db.attendance.find({"employee_id": employee_id, "date": {"$regex": f"^{month}"}}, {"_id": 0}).to_list(50)
    present_days = sum(1 for r in att_records if r.get("status") in ["present", "work_from_home"])
    absent_days = sum(1 for r in att_records if r.get("status") == "absent")
    half_days = sum(1 for r in att_records if r.get("status") == "half_day")
    
    # Auto-calculate approved leaves for this month
    leave_requests = await db.leave_requests.find({
        "employee_id": employee_id,
        "status": "approved",
        "$or": [
            {"start_date": {"$regex": f"^{month}"}},
            {"end_date": {"$regex": f"^{month}"}}
        ]
    }, {"_id": 0}).to_list(50)
    
    auto_leaves = 0
    auto_half_day_leaves = 0
    for lr in leave_requests:
        if lr.get("is_half_day"):
            auto_half_day_leaves += 0.5
        else:
            auto_leaves += lr.get("days", 0)
    
    # Get payroll inputs (manual overrides)
    payroll_input = await db.payroll_inputs.find_one({"employee_id": employee_id, "month": month}, {"_id": 0})
    if payroll_input:
        # Override attendance from payroll inputs if provided
        if payroll_input.get("present_days", 0) > 0:
            present_days = payroll_input["present_days"]
        if payroll_input.get("absent_days", 0) > 0:
            absent_days = payroll_input["absent_days"]
        # Add incentive as earning
        incentive_amt = payroll_input.get("incentive", 0) or 0
        if incentive_amt > 0:
            reason = payroll_input.get("incentive_reason", "")
            earnings.append({"name": f"Incentive{(' - ' + reason) if reason else ''}", "key": "incentive", "amount": round(incentive_amt, 2)})
            total_earnings += incentive_amt
        # Add overtime if any
        ot_hours = payroll_input.get("overtime_hours", 0) or 0
        if ot_hours > 0:
            ot_rate = round(gross_salary / (30 * 8), 2)  # hourly rate
            ot_amount = round(ot_hours * ot_rate * 1.5, 2)
            earnings.append({"name": f"Overtime ({ot_hours} hrs)", "key": "overtime", "amount": ot_amount})
            total_earnings += ot_amount
        # Add advance as deduction
        advance_amt = payroll_input.get("advance", 0) or 0
        if advance_amt > 0:
            reason = payroll_input.get("advance_reason", "")
            deductions.append({"name": f"Salary Advance{(' - ' + reason) if reason else ''}", "key": "advance", "amount": round(advance_amt, 2)})
            total_deductions += advance_amt
        # Add penalty as deduction
        penalty_amt = payroll_input.get("penalty", 0) or 0
        if penalty_amt > 0:
            reason = payroll_input.get("penalty_reason", "")
            deductions.append({"name": f"Penalty{(' - ' + reason) if reason else ''}", "key": "penalty", "amount": round(penalty_amt, 2)})
            total_deductions += penalty_amt
    working_days = payroll_input.get("working_days", 30) if payroll_input else 30
    public_holidays = payroll_input.get("public_holidays", 0) if payroll_input else 0
    leaves_count = payroll_input.get("leaves", 0) if payroll_input else 0
    # Use auto-calculated leaves if no manual override
    if leaves_count == 0:
        leaves_count = auto_leaves + auto_half_day_leaves
    
    # Track half-day leaves separately for payroll display
    half_day_leaves = auto_half_day_leaves
    
    # Fetch approved/reimbursed expenses for this employee in this month
    expense_reimb = 0
    expense_query = {"employee_id": employee_id, "status": {"$in": ["approved", "reimbursed"]}}
    all_expenses = await db.expenses.find(expense_query, {"_id": 0}).to_list(500)
    for exp in all_expenses:
        exp_date = exp.get("created_at", "")
        if isinstance(exp_date, str) and exp_date.startswith(month):
            expense_reimb += exp.get("total_amount", 0)
        elif hasattr(exp_date, 'strftime') and exp_date.strftime("%Y-%m") == month:
            expense_reimb += exp.get("total_amount", 0)
    expense_reimb = round(expense_reimb, 2)
    if expense_reimb > 0:
        earnings.append({"name": "Conveyance Reimbursement", "key": "expense_reimbursement", "amount": expense_reimb})
        total_earnings += expense_reimb
    # Check existing
    existing = await db.salary_slips.find_one({"employee_id": employee_id, "month": month}, {"_id": 0})
    slip = {
        "id": existing["id"] if existing else str(uuid.uuid4()),
        "employee_id": employee_id,
        "employee_name": f"{employee['first_name']} {employee['last_name']}",
        "employee_code": employee.get("employee_id", ""),
        "department": employee.get("department", ""),
        "designation": employee.get("designation", ""),
        "month": month,
        "gross_salary": gross_salary,
        "earnings": earnings,
        "total_earnings": round(total_earnings, 2),
        "deductions": deductions,
        "total_deductions": round(total_deductions, 2),
        "net_salary": round(total_earnings - total_deductions, 2),
        "present_days": present_days,
        "absent_days": absent_days,
        "half_days": half_days,
        "working_days": working_days,
        "public_holidays": public_holidays,
        "leaves": leaves_count,
        "half_day_leaves": half_day_leaves,
        "bank_details": employee.get("bank_details"),
        "generated_by": current_user.id,
        "generated_at": datetime.now(timezone.utc).isoformat()
    }
    if existing:
        await db.salary_slips.update_one({"id": existing["id"]}, {"$set": slip})
    else:
        await db.salary_slips.insert_one(slip)
    return slip

@api_router.post("/payroll/generate-bulk")
async def generate_bulk_salary_slips(data: dict, current_user: User = Depends(get_current_user)):
    """Generate salary slips for all active employees for a month"""
    if current_user.role not in ["admin", "hr_manager"]:
        raise HTTPException(status_code=403, detail="Only Admin/HR Manager can generate salary slips")
    month = data.get("month")
    if not month:
        raise HTTPException(status_code=400, detail="month required (YYYY-MM)")
    employees = await db.employees.find({"is_active": True, "salary": {"$gt": 0}}, {"_id": 0}).to_list(500)
    generated = 0
    for emp in employees:
        try:
            await generate_salary_slip({"employee_id": emp["id"], "month": month}, current_user)
            generated += 1
        except Exception:
            pass
    return {"message": f"Generated {generated} salary slips for {month}", "count": generated}




# ==================== SELF-SERVICE (MY WORKSPACE) ====================

async def _get_my_employee(current_user):
    emp = await db.employees.find_one({"user_id": current_user.id}, {"_id": 0})
    if not emp:
        raise HTTPException(status_code=400, detail="No employee record linked to your account. Please contact HR.")
    return emp

@api_router.get("/my/attendance")
async def get_my_attendance(month: Optional[str] = None, current_user: User = Depends(get_current_user)):
    emp = await _get_my_employee(current_user)
    query = {"employee_id": emp["id"]}
    if month:
        query["date"] = {"$regex": f"^{month}"}
    records = await db.attendance.find(query, {"_id": 0}).sort("date", -1).to_list(500)
    # Build summary
    summary = {"present": 0, "absent": 0, "half_day": 0, "wfh": 0, "on_leave": 0, "total": 0}
    for r in records:
        summary["total"] += 1
        s = r.get("status", "present")
        if s == "present": summary["present"] += 1
        elif s == "absent": summary["absent"] += 1
        elif s == "half_day": summary["half_day"] += 1
        elif s == "work_from_home": summary["wfh"] += 1
        elif s == "on_leave": summary["on_leave"] += 1
    return {"records": records, "summary": summary, "employee": {"name": f"{emp['first_name']} {emp['last_name']}", "employee_id": emp["employee_id"], "department": emp.get("department", "")}}


def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two coordinates in meters using Haversine formula"""
    import math
    R = 6371000  # Earth's radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c


async def validate_checkin_location(emp: dict, geo_location: dict, work_location: str) -> dict:
    """
    Validate check-in location against approved locations.
    - Consulting/Delivery employees: Can check in from office OR assigned client locations
    - Other employees (HR, Admin, Sales, etc.): Can ONLY check in from office
    Returns: {is_valid: bool, matched_location: str|None, all_approved_locations: list}
    """
    GEOFENCE_RADIUS = 500  # 500 meters
    
    lat = geo_location.get("latitude")
    lon = geo_location.get("longitude")
    
    if not lat or not lon:
        return {"is_valid": False, "matched_location": None, "reason": "Location not captured"}
    
    approved_locations = []
    dept = emp.get("department", "").lower()
    role = emp.get("designation", "").lower()
    
    # Determine if employee can check in from client sites
    can_use_client_sites = dept in ["consulting", "delivery"] or "consultant" in role
    
    # Get office locations (available to everyone)
    office_settings = await db.settings.find_one({"type": "office_locations"})
    if office_settings and office_settings.get("locations"):
        for loc in office_settings["locations"]:
            approved_locations.append({
                "name": loc.get("name", "Office"),
                "type": "office",
                "latitude": loc.get("latitude"),
                "longitude": loc.get("longitude"),
                "address": loc.get("address")
            })
    
    # For consulting/delivery employees, also get their assigned client locations
    if can_use_client_sites:
        # Get projects assigned to this employee
        projects = await db.projects.find({
            "$or": [
                {"team_members": {"$elemMatch": {"employee_id": emp["id"]}}},
                {"project_manager_id": emp["id"]}
            ]
        }).to_list(100)
        
        # Get client locations from assigned projects
        client_ids = list(set([p.get("client_id") for p in projects if p.get("client_id")]))
        if client_ids:
            clients = await db.clients.find({"id": {"$in": client_ids}}).to_list(100)
            for client in clients:
                if client.get("geo_coordinates"):
                    approved_locations.append({
                        "name": client.get("company_name", "Client"),
                        "type": "client",
                        "latitude": client["geo_coordinates"].get("latitude"),
                        "longitude": client["geo_coordinates"].get("longitude"),
                        "address": client.get("address")
                    })
    
    # Check if current location matches any approved location
    for loc in approved_locations:
        if loc.get("latitude") and loc.get("longitude"):
            distance = calculate_distance(lat, lon, loc["latitude"], loc["longitude"])
            if distance <= GEOFENCE_RADIUS:
                return {
                    "is_valid": True,
                    "matched_location": loc["name"],
                    "location_type": loc["type"],
                    "distance": round(distance),
                    "approved_locations": approved_locations
                }
    
    return {
        "is_valid": False,
        "matched_location": None,
        "reason": "Location not within 500m of any approved location",
        "approved_locations": approved_locations
    }


@api_router.get("/my/assigned-clients")
async def get_my_assigned_clients(current_user: User = Depends(get_current_user)):
    """
    Get list of clients from projects assigned to the current employee.
    Used for On-Site attendance check-in to select which client they're visiting.
    """
    emp = await _get_my_employee(current_user)
    
    # Find all active projects where this employee is assigned
    projects = await db.projects.find(
        {
            "$or": [
                {"assigned_consultants": emp["id"]},
                {"assigned_team": current_user.id},
                {"assigned_consultants": current_user.id}
            ],
            "status": {"$in": ["active", "in_progress", "ongoing"]}
        },
        {"_id": 0, "id": 1, "name": 1, "client_name": 1, "lead_id": 1}
    ).to_list(100)
    
    # Build unique client list from projects
    clients = []
    seen_clients = set()
    
    for project in projects:
        client_name = project.get("client_name", "")
        if client_name and client_name not in seen_clients:
            seen_clients.add(client_name)
            
            # Try to get client location if available
            lead_id = project.get("lead_id")
            client_location = None
            if lead_id:
                lead = await db.leads.find_one({"id": lead_id}, {"_id": 0, "city": 1, "state": 1, "street": 1})
                if lead:
                    addr_parts = [lead.get("street"), lead.get("city"), lead.get("state")]
                    client_location = ", ".join([p for p in addr_parts if p])
            
            clients.append({
                "id": project.get("id"),
                "project_id": project.get("id"),
                "project_name": project.get("name"),
                "client_name": client_name,
                "client_location": client_location
            })
    
    # Also fetch from clients collection if linked
    direct_clients = await db.clients.find(
        {"is_active": True},
        {"_id": 0, "id": 1, "company_name": 1, "billing_address": 1}
    ).to_list(50)
    
    for client in direct_clients:
        company = client.get("company_name", "")
        if company and company not in seen_clients:
            seen_clients.add(company)
            clients.append({
                "id": client.get("id"),
                "project_id": None,
                "project_name": None,
                "client_name": company,
                "client_location": client.get("billing_address", {}).get("city") if isinstance(client.get("billing_address"), dict) else None
            })
    
    return {"clients": clients, "count": len(clients)}


@api_router.post("/my/check-in")
async def self_check_in(data: dict, current_user: User = Depends(get_current_user)):
    """
    Self check-in for employees with mandatory selfie and GPS location.
    - Validates location against office/client locations (500m radius)
    - Requires selfie capture
    - Auto-approves if location matches, else sends to HR for approval
    - WFH is NOT allowed
    - Consulting employees can check in from office OR assigned client sites
    - Non-consulting employees (HR, Admin, Sales) can ONLY check in from office
    - Employee must be Go-Live Active to check in
    """
    emp = await _get_my_employee(current_user)
    
    # Check if employee is Go-Live Active
    go_live_status = emp.get("go_live_status")
    if go_live_status != "active":
        raise HTTPException(
            status_code=403, 
            detail="You cannot check in until your Go-Live status is Active. Please contact HR."
        )
    
    # Check if employee mobile app access is disabled
    if emp.get("mobile_app_disabled"):
        raise HTTPException(status_code=403, detail="Mobile app access is disabled for your account. Please contact HR.")
    
    date_str = data.get("date", datetime.now(timezone.utc).strftime("%Y-%m-%d"))
    
    # Check if already checked in today
    existing = await db.attendance.find_one({"employee_id": emp["id"], "date": date_str})
    if existing:
        if existing.get("check_out_time"):
            raise HTTPException(status_code=400, detail="You have already completed check-in and check-out today")
        raise HTTPException(status_code=400, detail="You have already checked in today")
    
    # Validate work location - WFH NOT allowed
    work_location = data.get("work_location", "in_office")
    if work_location not in ["in_office", "onsite"]:
        raise HTTPException(status_code=400, detail="Invalid work location. Only 'In Office' or 'On-Site' allowed.")
    
    # Non-consulting employees cannot select "onsite" - BUT Sales can also visit clients
    dept = emp.get("department", "").lower()
    role = emp.get("designation", "").lower()
    user_role = current_user.role.lower() if current_user.role else ""
    is_consulting = dept in ["consulting", "delivery"] or "consultant" in role
    is_sales = user_role in ["admin", "executive", "account_manager", "manager"] or dept in ["sales", "business development"]
    
    # Both consulting and sales teams can do onsite visits
    if work_location == "onsite" and not (is_consulting or is_sales):
        raise HTTPException(
            status_code=400, 
            detail="On-Site check-in is only available for Consulting/Delivery or Sales team members. Please select 'Office'."
        )
    
    # For onsite, client selection is mandatory
    client_id = data.get("client_id")
    client_name = data.get("client_name")
    project_id = data.get("project_id")
    project_name = data.get("project_name")
    
    if work_location == "onsite" and not client_name:
        raise HTTPException(status_code=400, detail="Please select a client for On-Site check-in")
    
    # Mandatory selfie
    selfie_data = data.get("selfie")
    if not selfie_data:
        raise HTTPException(status_code=400, detail="Selfie is mandatory for check-in")
    
    # Mandatory geo-location
    geo_location = data.get("geo_location")
    if not geo_location or not geo_location.get("latitude"):
        raise HTTPException(status_code=400, detail="GPS location is mandatory for check-in")
    
    # Validate location against approved locations (geofencing)
    location_validation = await validate_checkin_location(emp, geo_location, work_location)
    
    # Determine approval status
    if location_validation["is_valid"]:
        approval_status = "approved"
        approval_note = f"Auto-approved: Within 500m of {location_validation['matched_location']}"
    else:
        approval_status = "pending_approval"
        justification = data.get("justification", "")
        if not justification:
            raise HTTPException(
                status_code=400, 
                detail="You are not within 500m of any approved location. Please provide justification for HR approval."
            )
        approval_note = f"Pending HR approval: {location_validation.get('reason', 'Unknown location')}"
    
    # Build attendance record
    record = {
        "id": str(uuid.uuid4()),
        "employee_id": emp["id"],
        "employee_name": f"{emp['first_name']} {emp['last_name']}",
        "department": emp.get("department", ""),
        "date": date_str,
        "status": "present",
        "work_location": work_location,
        # Client info for onsite visits
        "client_id": client_id if work_location == "onsite" else None,
        "client_name": client_name if work_location == "onsite" else None,
        "project_id": project_id if work_location == "onsite" else None,
        "project_name": project_name if work_location == "onsite" else None,
        "approval_status": approval_status,
        "approval_note": approval_note,
        "justification": data.get("justification", ""),
        "remarks": data.get("remarks", "Self check-in with selfie"),
        "check_in_method": "self_check_in",
        "check_in_time": datetime.now(timezone.utc).isoformat(),
        "selfie": selfie_data,  # Base64 encoded image
        "geo_location": {
            "latitude": geo_location.get("latitude"),
            "longitude": geo_location.get("longitude"),
            "accuracy": geo_location.get("accuracy"),
            "address": geo_location.get("address"),
            "captured_at": geo_location.get("captured_at", datetime.now(timezone.utc).isoformat())
        },
        "location_validation": {
            "is_valid": location_validation["is_valid"],
            "matched_location": location_validation.get("matched_location"),
            "location_type": location_validation.get("location_type"),
            "distance": location_validation.get("distance")
        },
        "created_by": current_user.id,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.attendance.insert_one(record)
    
    # If pending approval, create notification for HR
    if approval_status == "pending_approval":
        hr_users = await db.users.find({"role": {"$in": ["hr_manager", "admin"]}}, {"id": 1}).to_list(50)
        for hr_user in hr_users:
            await db.notifications.insert_one({
                "id": str(uuid.uuid4()),
                "user_id": hr_user["id"],
                "message": f"Attendance approval required: {emp['first_name']} {emp['last_name']} checked in from unknown location",
                "type": "attendance_approval_required",
                "reference_id": record["id"],
                "is_read": False,
                "created_at": datetime.now(timezone.utc).isoformat()
            })
    
    return {
        "message": "Check-in successful" if approval_status == "approved" else "Check-in submitted for HR approval",
        "id": record["id"],
        "date": date_str,
        "status": "present",
        "work_location": work_location,
        "client_id": client_id,
        "client_name": client_name,
        "project_id": project_id,
        "project_name": project_name,
        "approval_status": approval_status,
        "matched_location": location_validation.get("matched_location"),
        "check_in_time": record["check_in_time"]
    }


@api_router.get("/hr/pending-attendance-approvals")
async def get_pending_attendance_approvals(current_user: User = Depends(get_current_user)):
    """Get all attendance records pending HR approval"""
    if current_user.role not in ["admin", "hr_manager"]:
        raise HTTPException(status_code=403, detail="HR access required")
    
    records = await db.attendance.find(
        {"approval_status": "pending_approval"},
        {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    
    return {"pending_approvals": records, "count": len(records)}


@api_router.post("/hr/attendance-approval/{attendance_id}")
async def approve_reject_attendance(
    attendance_id: str, 
    data: dict,
    current_user: User = Depends(get_current_user)
):
    """Approve or reject attendance check-in"""
    if current_user.role not in ["admin", "hr_manager"]:
        raise HTTPException(status_code=403, detail="HR access required")
    
    action = data.get("action")  # "approve" or "reject"
    hr_remarks = data.get("remarks", "")
    
    if action not in ["approve", "reject"]:
        raise HTTPException(status_code=400, detail="Action must be 'approve' or 'reject'")
    
    record = await db.attendance.find_one({"id": attendance_id})
    if not record:
        raise HTTPException(status_code=404, detail="Attendance record not found")
    
    new_status = "approved" if action == "approve" else "rejected"
    
    await db.attendance.update_one(
        {"id": attendance_id},
        {"$set": {
            "approval_status": new_status,
            "approved_by": current_user.id,
            "approved_by_name": current_user.full_name,
            "approved_at": datetime.now(timezone.utc).isoformat(),
            "hr_remarks": hr_remarks
        }}
    )
    
    # Notify employee
    emp = await db.employees.find_one({"id": record["employee_id"]})
    if emp:
        user = await db.users.find_one({"email": emp.get("email")})
        if user:
            await db.notifications.insert_one({
                "id": str(uuid.uuid4()),
                "user_id": user["id"],
                "message": f"Your attendance for {record['date']} has been {new_status} by HR",
                "type": "attendance_approval_result",
                "is_read": False,
                "created_at": datetime.now(timezone.utc).isoformat()
            })
    
    return {"message": f"Attendance {new_status}", "attendance_id": attendance_id}


@api_router.post("/my/check-out")
async def self_check_out(data: dict, current_user: User = Depends(get_current_user)):
    """
    Self check-out for employees with GPS location verification.
    Must have checked in first. Records check-out time and location.
    """
    emp = await _get_my_employee(current_user)
    
    # Check if employee mobile app access is disabled
    if emp.get("mobile_app_disabled"):
        raise HTTPException(status_code=403, detail="Mobile app access is disabled for your account.")
    
    date_str = data.get("date", datetime.now(timezone.utc).strftime("%Y-%m-%d"))
    
    # Find today's check-in
    existing = await db.attendance.find_one({"employee_id": emp["id"], "date": date_str})
    if not existing:
        raise HTTPException(status_code=400, detail="You must check in first before checking out")
    
    if existing.get("check_out_time"):
        raise HTTPException(status_code=400, detail="You have already checked out today")
    
    # Geo-location for check-out
    geo_location = data.get("geo_location")
    
    # Calculate work hours
    check_in_time = existing.get("check_in_time")
    check_out_time = datetime.now(timezone.utc).isoformat()
    
    work_hours = None
    if check_in_time:
        try:
            check_in_dt = datetime.fromisoformat(check_in_time.replace('Z', '+00:00'))
            check_out_dt = datetime.now(timezone.utc)
            duration = check_out_dt - check_in_dt
            work_hours = round(duration.total_seconds() / 3600, 2)
        except:
            pass
    
    # Calculate travel reimbursement if applicable (On-Site check-in)
    travel_reimbursement = None
    check_in_location = existing.get("geo_location", {})
    work_location = existing.get("work_location", "")
    
    if work_location == "onsite" and check_in_location.get("latitude") and geo_location and geo_location.get("latitude"):
        # Get home/office location for calculation
        office_settings = await db.settings.find_one({"type": "office_locations"})
        home_lat, home_lon = None, None
        office_name = "Office"
        
        # Use first office as default home point
        if office_settings and office_settings.get("locations"):
            first_office = office_settings["locations"][0]
            home_lat = first_office.get("latitude")
            home_lon = first_office.get("longitude")
            office_name = first_office.get("name", "Office")
        
        # Fallback: Use Bangalore office as default if no office configured
        if not home_lat or not home_lon:
            home_lat = 12.9716  # Bangalore default
            home_lon = 77.5946
            office_name = "Main Office"
        
        # Distance from office to client site (one way)
        distance_km = calculate_distance_km(
            home_lat, home_lon,
            check_in_location["latitude"], check_in_location["longitude"]
        )
        
        # Only show travel reimbursement if distance is meaningful (> 1 km)
        if distance_km > 1:
            # Round trip
            total_distance = distance_km * 2
            rate = TRAVEL_RATES.get("car", 7.0)
            calculated_amount = round(total_distance * rate, 2)
            
            travel_reimbursement = {
                "distance_km": round(total_distance, 2),
                "rate_per_km": rate,
                "calculated_amount": calculated_amount,
                "vehicle_type": "car",
                "is_round_trip": True,
                "from_location": office_name,
                "to_location": existing.get("client_name") or check_in_location.get("address", "Client Site")[:50] if check_in_location.get("address") else "Client Site",
                "office_lat": home_lat,
                "office_lon": home_lon,
                "client_lat": check_in_location["latitude"],
                "client_lon": check_in_location["longitude"],
                # Include client info from attendance
                "client_id": existing.get("client_id"),
                "client_name": existing.get("client_name"),
                "project_id": existing.get("project_id"),
                "project_name": existing.get("project_name")
            }
    
    await db.attendance.update_one(
        {"id": existing["id"]},
        {"$set": {
            "check_out_time": check_out_time,
            "check_out_location": geo_location,
            "work_hours": work_hours,
            "travel_reimbursement": travel_reimbursement,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    # Determine if we should redirect to expense/reimbursement page
    redirect_to_expense = travel_reimbursement is not None and travel_reimbursement.get("distance_km", 0) > 1
    
    return {
        "message": "Check-out successful",
        "id": existing["id"],
        "attendance_id": existing["id"],
        "check_out_time": check_out_time,
        "work_hours": work_hours,
        "travel_reimbursement": travel_reimbursement,
        "redirect_to_expense": redirect_to_expense,
        "client_id": existing.get("client_id"),
        "client_name": existing.get("client_name"),
        "project_id": existing.get("project_id"),
        "project_name": existing.get("project_name")
    }


@api_router.get("/my/check-status")
async def get_check_in_status(current_user: User = Depends(get_current_user)):
    """Get current day's check-in/check-out status"""
    emp = await _get_my_employee(current_user)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    record = await db.attendance.find_one(
        {"employee_id": emp["id"], "date": today},
        {"_id": 0, "selfie": 0}  # Exclude large selfie data
    )
    
    return {
        "date": today,
        "is_checked_in": record is not None,
        "is_checked_out": record.get("check_out_time") is not None if record else False,
        "record": record
    }


@api_router.put("/hr/employee/{employee_id}/mobile-access")
async def toggle_employee_mobile_access(
    employee_id: str,
    data: dict,
    current_user: User = Depends(get_current_user)
):
    """Enable or disable employee mobile app access (Admin/HR Manager only)"""
    if current_user.role not in ["admin", "hr_manager"]:
        raise HTTPException(status_code=403, detail="Admin or HR Manager access required")
    
    disabled = data.get("disabled", False)
    reason = data.get("reason", "")
    
    result = await db.employees.update_one(
        {"id": employee_id},
        {"$set": {
            "mobile_app_disabled": disabled,
            "mobile_app_disabled_reason": reason,
            "mobile_app_disabled_by": current_user.id,
            "mobile_app_disabled_at": datetime.now(timezone.utc).isoformat() if disabled else None
        }}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Create notification
    emp = await db.employees.find_one({"id": employee_id})
    if emp:
        user = await db.users.find_one({"email": emp.get("email")})
        if user:
            await db.notifications.insert_one({
                "id": str(uuid.uuid4()),
                "user_id": user["id"],
                "message": f"Your mobile app access has been {'disabled' if disabled else 'enabled'}" + (f": {reason}" if reason and disabled else ""),
                "type": "mobile_access_changed",
                "is_read": False,
                "created_at": datetime.now(timezone.utc).isoformat()
            })
    
    return {
        "message": f"Mobile app access {'disabled' if disabled else 'enabled'} for employee",
        "employee_id": employee_id
    }


@api_router.get("/hr/employees-mobile-access")
async def get_employees_mobile_access(current_user: User = Depends(get_current_user)):
    """Get list of employees with their mobile app access status"""
    if current_user.role not in ["admin", "hr_manager"]:
        raise HTTPException(status_code=403, detail="Admin or HR Manager access required")
    
    employees = await db.employees.find(
        {},
        {"_id": 0, "id": 1, "employee_id": 1, "first_name": 1, "last_name": 1, 
         "department": 1, "mobile_app_disabled": 1, "mobile_app_disabled_reason": 1}
    ).to_list(500)
    
    return {"employees": employees}


@api_router.get("/settings/office-locations")
async def get_office_locations(current_user: User = Depends(get_current_user)):
    """Get configured office locations"""
    settings = await db.settings.find_one({"type": "office_locations"})
    if settings:
        return {"locations": settings.get("locations", [])}
    return {"locations": []}


@api_router.post("/settings/office-locations")
async def save_office_locations(data: dict, current_user: User = Depends(get_current_user)):
    """Save office locations for geofencing (Admin only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    locations = data.get("locations", [])
    
    await db.settings.update_one(
        {"type": "office_locations"},
        {"$set": {
            "type": "office_locations",
            "locations": locations,
            "updated_by": current_user.id,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }},
        upsert=True
    )
    
    return {"message": "Office locations saved", "count": len(locations)}


@api_router.put("/clients/{client_id}/geo-coordinates")
async def update_client_geo_coordinates(
    client_id: str, 
    data: dict, 
    current_user: User = Depends(get_current_user)
):
    """Update client's geo coordinates for geofencing"""
    if current_user.role not in ["admin", "hr_manager", "sales_manager"]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    result = await db.clients.update_one(
        {"id": client_id},
        {"$set": {
            "geo_coordinates": {
                "latitude": data.get("latitude"),
                "longitude": data.get("longitude"),
                "address": data.get("address")
            },
            "geo_updated_by": current_user.id,
            "geo_updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Client not found")
    
    return {"message": "Client geo-coordinates updated"}


@api_router.get("/my/leave-balance")
async def get_my_leave_balance(current_user: User = Depends(get_current_user)):
    emp = await _get_my_employee(current_user)
    balance = emp.get("leave_balance", {})
    return {
        "casual": {"total": balance.get("casual_leave", 12), "used": balance.get("used_casual", 0), "available": balance.get("casual_leave", 12) - balance.get("used_casual", 0)},
        "sick": {"total": balance.get("sick_leave", 6), "used": balance.get("used_sick", 0), "available": balance.get("sick_leave", 6) - balance.get("used_sick", 0)},
        "earned": {"total": balance.get("earned_leave", 15), "used": balance.get("used_earned", 0), "available": balance.get("earned_leave", 15) - balance.get("used_earned", 0)},
        "employee_name": f"{emp['first_name']} {emp['last_name']}"
    }

@api_router.get("/my/salary-slips")
async def get_my_salary_slips(current_user: User = Depends(get_current_user)):
    emp = await _get_my_employee(current_user)
    slips = await db.salary_slips.find({"employee_id": emp["id"]}, {"_id": 0}).sort("month", -1).to_list(100)
    return slips

@api_router.get("/my/expenses")
async def get_my_expenses(current_user: User = Depends(get_current_user)):
    emp = await _get_my_employee(current_user)
    expenses = await db.expenses.find({"employee_id": emp["id"]}, {"_id": 0}).sort("created_at", -1).to_list(200)
    summary = {"draft": 0, "pending": 0, "approved": 0, "rejected": 0, "reimbursed": 0, "total_amount": 0, "reimbursed_amount": 0}
    for e in expenses:
        st = e.get("status", "draft")
        summary[st] = summary.get(st, 0) + 1
        summary["total_amount"] += e.get("total_amount", 0)
        if st == "reimbursed":
            summary["reimbursed_amount"] += e.get("total_amount", 0)
    return {"expenses": expenses, "summary": summary}


# ==================== PROJECT ROADMAP ====================

@api_router.post("/roadmaps")
async def create_roadmap(data: dict, current_user: User = Depends(get_current_user)):
    """Create project roadmap (PM/Manager/Admin)"""
    if current_user.role not in ["admin", "project_manager", "manager", "principal_consultant"]:
        raise HTTPException(status_code=403, detail="Only PM/Manager/Admin can create roadmaps")
    project_id = data.get("project_id")
    if not project_id:
        raise HTTPException(status_code=400, detail="project_id required")
    project = await db.projects.find_one({"id": project_id}, {"_id": 0})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    roadmap = {
        "id": str(uuid.uuid4()), "project_id": project_id,
        "project_name": project.get("name", ""), "client_name": project.get("client_name", ""),
        "sow_id": data.get("sow_id", ""), "title": data.get("title", f"Roadmap - {project.get('name', '')}"),
        "phases": data.get("phases", []),
        "status": "draft",
        "submitted_to_client": False, "submitted_to_client_at": None,
        "created_by": current_user.id, "created_by_name": current_user.full_name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    for phase in roadmap["phases"]:
        if not phase.get("id"):
            phase["id"] = str(uuid.uuid4())
        for item in phase.get("items", []):
            if not item.get("id"):
                item["id"] = str(uuid.uuid4())
            item.setdefault("status", "not_started")
    await db.roadmaps.insert_one(roadmap)
    return {k: v for k, v in roadmap.items() if k != "_id"}

@api_router.get("/roadmaps")
async def get_roadmaps(project_id: Optional[str] = None, current_user: User = Depends(get_current_user)):
    query = {}
    if project_id:
        query["project_id"] = project_id
    roadmaps = await db.roadmaps.find(query, {"_id": 0}).sort("created_at", -1).to_list(200)
    return roadmaps

@api_router.get("/roadmaps/{roadmap_id}")
async def get_roadmap(roadmap_id: str, current_user: User = Depends(get_current_user)):
    roadmap = await db.roadmaps.find_one({"id": roadmap_id}, {"_id": 0})
    if not roadmap:
        raise HTTPException(status_code=404, detail="Roadmap not found")
    return roadmap

@api_router.patch("/roadmaps/{roadmap_id}")
async def update_roadmap(roadmap_id: str, data: dict, current_user: User = Depends(get_current_user)):
    roadmap = await db.roadmaps.find_one({"id": roadmap_id}, {"_id": 0})
    if not roadmap:
        raise HTTPException(status_code=404, detail="Roadmap not found")
    update = {}
    for key in ["title", "phases", "status"]:
        if key in data:
            update[key] = data[key]
    if "phases" in update:
        for phase in update["phases"]:
            if not phase.get("id"):
                phase["id"] = str(uuid.uuid4())
            for item in phase.get("items", []):
                if not item.get("id"):
                    item["id"] = str(uuid.uuid4())
                item.setdefault("status", "not_started")
    update["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.roadmaps.update_one({"id": roadmap_id}, {"$set": update})
    return {"message": "Roadmap updated"}

@api_router.post("/roadmaps/{roadmap_id}/submit-to-client")
async def submit_roadmap_to_client(roadmap_id: str, current_user: User = Depends(get_current_user)):
    roadmap = await db.roadmaps.find_one({"id": roadmap_id}, {"_id": 0})
    if not roadmap:
        raise HTTPException(status_code=404, detail="Roadmap not found")
    await db.roadmaps.update_one({"id": roadmap_id}, {"$set": {
        "status": "submitted_to_client", "submitted_to_client": True,
        "submitted_to_client_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }})
    # Queue notification (MOCKED)
    await db.notifications.insert_one({
        "id": str(uuid.uuid4()), "type": "roadmap_submitted",
        "subject": f"Project Roadmap: {roadmap.get('title', '')}",
        "body": f"Roadmap for project {roadmap.get('project_name', '')} has been submitted.",
        "created_at": datetime.now(timezone.utc).isoformat(), "sent": False
    })
    return {"message": "Roadmap submitted to client"}

@api_router.patch("/roadmaps/{roadmap_id}/items/{item_id}/status")
async def update_roadmap_item_status(roadmap_id: str, item_id: str, data: dict, current_user: User = Depends(get_current_user)):
    """Update a roadmap item status (any assigned user)"""
    roadmap = await db.roadmaps.find_one({"id": roadmap_id}, {"_id": 0})
    if not roadmap:
        raise HTTPException(status_code=404, detail="Roadmap not found")
    updated = False
    for phase in roadmap.get("phases", []):
        for item in phase.get("items", []):
            if item.get("id") == item_id:
                item["status"] = data.get("status", item.get("status"))
                if data.get("status") == "completed":
                    item["completed_at"] = datetime.now(timezone.utc).isoformat()
                updated = True
                break
        if updated:
            break
    if not updated:
        raise HTTPException(status_code=404, detail="Item not found")
    await db.roadmaps.update_one({"id": roadmap_id}, {"$set": {"phases": roadmap["phases"], "updated_at": datetime.now(timezone.utc).isoformat()}})
    return {"message": "Item status updated"}


# ==================== PERFORMANCE METRICS ====================

DEFAULT_METRICS = [
    {"name": "SOW Timely Delivery", "key": "sow_delivery", "weight": 20, "description": "Percentage of SOW items delivered on time"},
    {"name": "Roadmap Achievement", "key": "roadmap_achievement", "weight": 20, "description": "Roadmap milestones completed vs planned"},
    {"name": "Records Timeliness", "key": "records_timeliness", "weight": 15, "description": "Timely update of project records and documents"},
    {"name": "SOW Quality Score", "key": "sow_quality", "weight": 25, "description": "Quality rating of SOW documents by reporting manager"},
    {"name": "Meeting Adherence", "key": "meeting_adherence", "weight": 20, "description": "Meeting schedule timeline and date adherence"}
]

@api_router.post("/performance-metrics")
async def create_performance_metrics(data: dict, current_user: User = Depends(get_current_user)):
    """Create performance metrics config for a project (Principal Consultant)"""
    if current_user.role not in ["admin", "principal_consultant", "project_manager"]:
        raise HTTPException(status_code=403, detail="Only Principal Consultant/PM/Admin can configure metrics")
    project_id = data.get("project_id")
    if not project_id:
        raise HTTPException(status_code=400, detail="project_id required")
    metrics = data.get("metrics", DEFAULT_METRICS)
    for m in metrics:
        if not m.get("id"):
            m["id"] = str(uuid.uuid4())
    config = {
        "id": str(uuid.uuid4()), "project_id": project_id,
        "project_name": data.get("project_name", ""),
        "metrics": metrics,
        "status": "pending_approval",
        "created_by": current_user.id, "created_by_name": current_user.full_name,
        "approved_by": None, "approved_by_name": None, "approved_at": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    await db.performance_metrics.insert_one(config)
    return {k: v for k, v in config.items() if k != "_id"}

@api_router.get("/performance-metrics")
async def get_performance_metrics(project_id: Optional[str] = None, status: Optional[str] = None, current_user: User = Depends(get_current_user)):
    query = {}
    if project_id:
        query["project_id"] = project_id
    if status:
        query["status"] = status
    configs = await db.performance_metrics.find(query, {"_id": 0}).sort("created_at", -1).to_list(200)
    return configs

@api_router.get("/performance-metrics/{config_id}")
async def get_performance_metric(config_id: str, current_user: User = Depends(get_current_user)):
    config = await db.performance_metrics.find_one({"id": config_id}, {"_id": 0})
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")
    return config

@api_router.patch("/performance-metrics/{config_id}")
async def update_performance_metrics(config_id: str, data: dict, current_user: User = Depends(get_current_user)):
    config = await db.performance_metrics.find_one({"id": config_id}, {"_id": 0})
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")
    update = {}
    if "metrics" in data:
        for m in data["metrics"]:
            if not m.get("id"):
                m["id"] = str(uuid.uuid4())
        update["metrics"] = data["metrics"]
    if "project_name" in data:
        update["project_name"] = data["project_name"]
    update["status"] = "pending_approval"
    update["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.performance_metrics.update_one({"id": config_id}, {"$set": update})
    return {"message": "Metrics updated, pending admin approval"}

@api_router.post("/performance-metrics/{config_id}/approve")
async def approve_performance_metrics(config_id: str, current_user: User = Depends(get_current_user)):
    """Admin approves performance metrics before they populate to users"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only Admin can approve performance metrics")
    config = await db.performance_metrics.find_one({"id": config_id}, {"_id": 0})
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")
    await db.performance_metrics.update_one({"id": config_id}, {"$set": {
        "status": "approved", "approved_by": current_user.id,
        "approved_by_name": current_user.full_name,
        "approved_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }})
    return {"message": "Performance metrics approved"}

@api_router.post("/performance-metrics/{config_id}/reject")
async def reject_performance_metrics(config_id: str, current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only Admin can reject")
    await db.performance_metrics.update_one({"id": config_id}, {"$set": {"status": "rejected", "updated_at": datetime.now(timezone.utc).isoformat()}})
    return {"message": "Performance metrics rejected"}


# ==================== PERFORMANCE SCORES ====================

@api_router.post("/performance-scores")
async def create_performance_score(data: dict, current_user: User = Depends(get_current_user)):
    """Rate consultant performance (Reporting Manager/PM)"""
    if current_user.role not in ["admin", "manager", "project_manager", "principal_consultant"]:
        raise HTTPException(status_code=403, detail="Only RM/PM/Admin can rate performance")
    project_id = data.get("project_id")
    consultant_id = data.get("consultant_id")
    month = data.get("month")
    if not all([project_id, consultant_id, month]):
        raise HTTPException(status_code=400, detail="project_id, consultant_id, and month required")
    # Get approved metrics config
    config = await db.performance_metrics.find_one({"project_id": project_id, "status": "approved"}, {"_id": 0})
    if not config:
        raise HTTPException(status_code=400, detail="No approved performance metrics for this project")
    consultant = await db.users.find_one({"id": consultant_id}, {"_id": 0, "full_name": 1})
    scores = data.get("scores", [])
    total_weight = sum(m.get("weight", 0) for m in config.get("metrics", []))
    weighted_total = 0
    for s in scores:
        metric = next((m for m in config["metrics"] if m["id"] == s.get("metric_id")), None)
        if metric:
            weighted_total += (s.get("score", 0) * metric.get("weight", 0)) / 100
    overall = round((weighted_total / total_weight * 100) if total_weight > 0 else 0, 1)
    existing = await db.performance_scores.find_one({"project_id": project_id, "consultant_id": consultant_id, "month": month}, {"_id": 0})
    score_doc = {
        "id": existing["id"] if existing else str(uuid.uuid4()),
        "project_id": project_id, "consultant_id": consultant_id,
        "consultant_name": consultant.get("full_name", "") if consultant else "",
        "month": month, "scores": scores,
        "overall_score": overall,
        "metrics_config_id": config["id"],
        "rated_by": current_user.id, "rated_by_name": current_user.full_name,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    if existing:
        await db.performance_scores.update_one({"id": existing["id"]}, {"$set": score_doc})
    else:
        await db.performance_scores.insert_one(score_doc)
    return {k: v for k, v in score_doc.items() if k != "_id"}

@api_router.get("/performance-scores")
async def get_performance_scores(project_id: Optional[str] = None, consultant_id: Optional[str] = None, current_user: User = Depends(get_current_user)):
    query = {}
    if project_id:
        query["project_id"] = project_id
    if consultant_id:
        query["consultant_id"] = consultant_id
    scores = await db.performance_scores.find(query, {"_id": 0}).sort("month", -1).to_list(500)
    return scores

@api_router.get("/performance-scores/summary")
async def get_performance_summary(project_id: Optional[str] = None, current_user: User = Depends(get_current_user)):
    """Get aggregated performance summary per consultant"""
    query = {}
    if project_id:
        query["project_id"] = project_id
    scores = await db.performance_scores.find(query, {"_id": 0}).to_list(1000)
    summary = {}
    for s in scores:
        cid = s["consultant_id"]
        if cid not in summary:
            summary[cid] = {"consultant_id": cid, "consultant_name": s.get("consultant_name", ""), "months_rated": 0, "total_score": 0, "scores_by_month": []}
        summary[cid]["months_rated"] += 1
        summary[cid]["total_score"] += s.get("overall_score", 0)
        summary[cid]["scores_by_month"].append({"month": s["month"], "overall_score": s["overall_score"]})
    for cid in summary:
        summary[cid]["avg_score"] = round(summary[cid]["total_score"] / max(summary[cid]["months_rated"], 1), 1)
    return list(summary.values())


@api_router.get("/downloads/feature-index")
async def download_feature_index():
    """Download the Feature Index Word document"""
    file_path = os.path.join(ROOT_DIR.parent, "uploads", "Feature_Index_DVB_Consulting.docx")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Feature index document not found")
    return FileResponse(file_path, filename="Feature_Index_DVB_Consulting.docx",
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document")


@api_router.get("/downloads/api-documentation")
async def download_api_documentation():
    """Download the API Documentation HTML"""
    file_path = os.path.join(ROOT_DIR, "docs", "api-documentation.html")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="API documentation not found")
    return FileResponse(file_path, filename="DV_Business_Consulting_API_Documentation.html",
        media_type="text/html")


@api_router.get("/downloads/postman-collection")
async def download_postman_collection():
    """Download the Postman Collection JSON"""
    file_path = os.path.join(ROOT_DIR, "docs", "DV_Business_Consulting_API.postman_collection.json")
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Postman collection not found")
    return FileResponse(file_path, filename="DV_Business_Consulting_API.postman_collection.json",
        media_type="application/json")


# ============== EMPLOYEE BANK DETAILS CHANGE REQUEST ==============

@api_router.get("/my/profile")
async def get_my_profile(current_user: User = Depends(get_current_user)):
    """Get current user's employee profile including bank details"""
    employee = await db.employees.find_one({"user_id": current_user.id}, {"_id": 0})
    if not employee:
        # Try finding by email
        employee = await db.employees.find_one({"work_email": current_user.email}, {"_id": 0})
    return employee or {}


@api_router.get("/my/bank-change-requests")
async def get_my_bank_change_requests(current_user: User = Depends(get_current_user)):
    """Get all bank detail change requests for current user"""
    employee = await db.employees.find_one({"user_id": current_user.id})
    if not employee:
        employee = await db.employees.find_one({"work_email": current_user.email})
    if not employee:
        return []
    
    requests = await db.bank_change_requests.find(
        {"employee_id": str(employee["_id"])},
        {"_id": 0}
    ).sort("created_at", -1).limit(10).to_list(length=10)
    return requests


@api_router.post("/my/bank-change-request")
async def submit_bank_change_request(
    request_data: dict,
    current_user: User = Depends(get_current_user)
):
    """Submit a bank details change request"""
    employee = await db.employees.find_one({"user_id": current_user.id})
    if not employee:
        employee = await db.employees.find_one({"work_email": current_user.email})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee profile not found")
    
    # Check for pending requests
    existing_pending = await db.bank_change_requests.find_one({
        "employee_id": str(employee["_id"]),
        "status": {"$in": ["pending_hr", "pending_admin"]}
    })
    if existing_pending:
        raise HTTPException(status_code=400, detail="You already have a pending bank change request")
    
    new_request = {
        "employee_id": str(employee["_id"]),
        "employee_name": f"{employee.get('first_name', '')} {employee.get('last_name', '')}",
        "employee_code": employee.get("employee_code", ""),
        "current_bank_details": employee.get("bank_details", {}),
        "new_bank_details": request_data.get("new_bank_details", {}),
        "proof_document": request_data.get("proof_document"),
        "proof_filename": request_data.get("proof_filename"),
        "reason": request_data.get("reason", ""),
        "status": "pending_hr",
        "hr_approved_by": None,
        "hr_approved_at": None,
        "admin_approved_by": None,
        "admin_approved_at": None,
        "rejection_reason": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.bank_change_requests.insert_one(new_request)
    
    # Create notification for HR
    await db.notifications.insert_one({
        "type": "bank_change_request",
        "message": f"Bank details change request from {new_request['employee_name']}",
        "link": "/hr/approvals",
        "for_roles": ["hr_manager", "hr_executive"],
        "read": False,
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    return {"message": "Bank details change request submitted successfully"}


@api_router.get("/hr/bank-change-requests")
async def get_hr_bank_change_requests(
    status: str = None,
    current_user: User = Depends(get_current_user)
):
    """Get bank change requests for HR review"""
    if current_user.role not in ["admin", "hr_manager", "hr_executive"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    query = {}
    if status:
        query["status"] = status
    else:
        query["status"] = "pending_hr"
    
    requests = await db.bank_change_requests.find(query, {"_id": 0}).sort("created_at", -1).to_list(length=50)
    return requests


@api_router.post("/hr/bank-change-request/{employee_id}/approve")
async def hr_approve_bank_change(
    employee_id: str,
    current_user: User = Depends(get_current_user)
):
    """HR approves bank change request - moves to admin approval"""
    if current_user.role not in ["hr_manager", "hr_executive"]:
        raise HTTPException(status_code=403, detail="Only HR can approve")
    
    result = await db.bank_change_requests.update_one(
        {"employee_id": employee_id, "status": "pending_hr"},
        {"$set": {
            "status": "pending_admin",
            "hr_approved_by": current_user.email,
            "hr_approved_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Request not found or already processed")
    
    # Notify admin
    req = await db.bank_change_requests.find_one({"employee_id": employee_id})
    await db.notifications.insert_one({
        "type": "bank_change_admin_review",
        "message": f"Bank change request pending admin approval: {req.get('employee_name', '')}",
        "link": "/approvals",
        "for_roles": ["admin"],
        "read": False,
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    return {"message": "Request approved by HR, pending admin approval"}


@api_router.post("/hr/bank-change-request/{employee_id}/reject")
async def hr_reject_bank_change(
    employee_id: str,
    rejection_data: dict,
    current_user: User = Depends(get_current_user)
):
    """HR rejects bank change request"""
    if current_user.role not in ["hr_manager", "hr_executive"]:
        raise HTTPException(status_code=403, detail="Only HR can reject")
    
    result = await db.bank_change_requests.update_one(
        {"employee_id": employee_id, "status": "pending_hr"},
        {"$set": {
            "status": "rejected",
            "rejection_reason": rejection_data.get("reason", "Rejected by HR"),
            "hr_approved_by": current_user.email,
            "hr_approved_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Request not found or already processed")
    
    return {"message": "Request rejected"}


@api_router.get("/admin/bank-change-requests")
async def get_admin_bank_change_requests(
    current_user: User = Depends(get_current_user)
):
    """Get bank change requests pending admin approval"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    
    requests = await db.bank_change_requests.find(
        {"status": "pending_admin"},
        {"_id": 0}
    ).sort("created_at", -1).to_list(length=50)
    return requests


@api_router.post("/admin/bank-change-request/{employee_id}/approve")
async def admin_approve_bank_change(
    employee_id: str,
    current_user: User = Depends(get_current_user)
):
    """Admin final approval - updates employee bank details"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    
    request = await db.bank_change_requests.find_one({
        "employee_id": employee_id,
        "status": "pending_admin"
    })
    
    if not request:
        raise HTTPException(status_code=404, detail="Request not found or already processed")
    
    # Update employee bank details
    await db.employees.update_one(
        {"_id": ObjectId(employee_id)},
        {"$set": {
            "bank_details": request["new_bank_details"],
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    # Update request status
    await db.bank_change_requests.update_one(
        {"employee_id": employee_id, "status": "pending_admin"},
        {"$set": {
            "status": "approved",
            "admin_approved_by": current_user.email,
            "admin_approved_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    return {"message": "Bank details updated successfully"}


@api_router.post("/admin/bank-change-request/{employee_id}/reject")
async def admin_reject_bank_change(
    employee_id: str,
    rejection_data: dict,
    current_user: User = Depends(get_current_user)
):
    """Admin rejects bank change request"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    
    result = await db.bank_change_requests.update_one(
        {"employee_id": employee_id, "status": "pending_admin"},
        {"$set": {
            "status": "rejected",
            "rejection_reason": rejection_data.get("reason", "Rejected by Admin"),
            "admin_approved_by": current_user.email,
            "admin_approved_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Request not found or already processed")
    
    return {"message": "Request rejected"}


# ==================== EMPLOYEE GO-LIVE WORKFLOW ====================

class GoLiveRequest(BaseModel):
    """Model for Go-Live approval request"""
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    employee_id: str
    employee_name: str
    employee_code: str
    department: str
    checklist: Dict[str, bool] = {}  # onboarding, ctc, bank, documents, access
    status: str = "pending"  # pending, approved, rejected
    submitted_by: str
    submitted_by_name: str
    submitted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    approved_by: Optional[str] = None
    approved_by_name: Optional[str] = None
    approved_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    notes: Optional[str] = None


@api_router.get("/go-live/checklist/{employee_id}")
async def get_go_live_checklist(
    employee_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get Go-Live checklist status for an employee."""
    global db
    
    # Find employee by employee_id field (EMP001) or id (uuid)
    employee = await db.employees.find_one(
        {"$or": [{"employee_id": employee_id}, {"id": employee_id}]},
        {"_id": 0}
    )
    
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    emp_id = employee.get("id") or employee.get("employee_id")
    
    # Check CTC status
    ctc = await db.ctc_structures.find_one(
        {"employee_id": emp_id, "status": {"$in": ["active", "approved"]}},
        {"_id": 0}
    )
    
    # Check bank details
    bank_details = employee.get("bank_details", {})
    bank_verified = bank_details.get("proof_verified", False) if bank_details else False
    
    # Check documents generated
    documents = await db.document_history.count_documents({"employee_id": emp_id})
    
    # Check portal access
    has_access = employee.get("has_portal_access", False)
    
    # Check existing go-live request
    go_live_request = await db.go_live_requests.find_one(
        {"employee_id": emp_id},
        {"_id": 0}
    )
    
    checklist = {
        "onboarding_complete": employee.get("onboarding_status") == "completed" or bool(employee.get("first_name")),
        "ctc_approved": bool(ctc),
        "bank_details_added": bool(bank_details and bank_details.get("account_number")),
        "bank_verified": bank_verified,
        "documents_generated": documents > 0,
        "portal_access_granted": has_access,
        "go_live_status": go_live_request.get("status") if go_live_request else "not_submitted"
    }
    
    return {
        "employee": {
            "id": emp_id,
            "employee_id": employee.get("employee_id"),
            "name": f"{employee.get('first_name', '')} {employee.get('last_name', '')}".strip(),
            "department": employee.get("department") or employee.get("primary_department"),
            "designation": employee.get("designation")
        },
        "checklist": checklist,
        "ctc_details": {
            "annual_ctc": ctc.get("annual_ctc") if ctc else None,
            "effective_from": ctc.get("effective_from") if ctc else None
        } if ctc else None,
        "go_live_request": go_live_request
    }


@api_router.post("/go-live/submit/{employee_id}")
async def submit_go_live_request(
    employee_id: str,
    data: dict,
    current_user: User = Depends(get_current_user)
):
    """HR submits Go-Live request for Admin approval."""
    global db
    
    if current_user.role not in ["admin", "hr_manager", "hr_executive"]:
        raise HTTPException(status_code=403, detail="Only HR can submit Go-Live requests")
    
    # Get employee
    employee = await db.employees.find_one(
        {"$or": [{"employee_id": employee_id}, {"id": employee_id}]},
        {"_id": 0}
    )
    
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    emp_id = employee.get("id") or employee.get("employee_id")
    
    # Check if already submitted
    existing = await db.go_live_requests.find_one({"employee_id": emp_id, "status": "pending"})
    if existing:
        raise HTTPException(status_code=400, detail="Go-Live request already pending for this employee")
    
    # Create Go-Live request
    go_live_request = {
        "id": str(uuid.uuid4()),
        "employee_id": emp_id,
        "employee_name": f"{employee.get('first_name', '')} {employee.get('last_name', '')}".strip(),
        "employee_code": employee.get("employee_id"),
        "department": employee.get("department") or employee.get("primary_department", ""),
        "checklist": data.get("checklist", {}),
        "status": "pending",
        "submitted_by": current_user.id,
        "submitted_by_name": current_user.full_name,
        "submitted_at": datetime.now(timezone.utc).isoformat(),
        "notes": data.get("notes")
    }
    
    await db.go_live_requests.insert_one(go_live_request)
    
    # Notify admins
    admins = await db.users.find({"role": "admin"}, {"_id": 0, "id": 1}).to_list(20)
    for admin in admins:
        notification = {
            "id": str(uuid.uuid4()),
            "user_id": admin["id"],
            "type": "go_live_request",
            "title": "Go-Live Approval Required",
            "message": f"Go-Live request submitted for {go_live_request['employee_name']} ({go_live_request['employee_code']})",
            "link": "/approvals",
            "read": False,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.notifications.insert_one(notification)
    
    return {"message": "Go-Live request submitted for approval", "request_id": go_live_request["id"]}


@api_router.get("/go-live/pending")
async def get_pending_go_live_requests(current_user: User = Depends(get_current_user)):
    """Get all pending Go-Live requests (Admin only)."""
    global db
    
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only Admin can view pending Go-Live requests")
    
    requests = await db.go_live_requests.find(
        {"status": "pending"},
        {"_id": 0}
    ).sort("submitted_at", -1).to_list(100)
    
    return requests


@api_router.post("/go-live/{request_id}/approve")
async def approve_go_live(
    request_id: str,
    current_user: User = Depends(get_current_user)
):
    """Admin approves Go-Live request."""
    global db
    
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only Admin can approve Go-Live")
    
    request = await db.go_live_requests.find_one({"id": request_id, "status": "pending"})
    if not request:
        raise HTTPException(status_code=404, detail="Request not found or already processed")
    
    # Update request
    await db.go_live_requests.update_one(
        {"id": request_id},
        {"$set": {
            "status": "approved",
            "approved_by": current_user.id,
            "approved_by_name": current_user.full_name,
            "approved_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    # Update employee go_live_status
    await db.employees.update_one(
        {"$or": [{"id": request["employee_id"]}, {"employee_id": request["employee_id"]}]},
        {"$set": {
            "go_live_status": "active",
            "go_live_approved_at": datetime.now(timezone.utc).isoformat(),
            "go_live_approved_by": current_user.full_name,
            "is_active": True
        }}
    )
    
    # Notify HR who submitted
    notification = {
        "id": str(uuid.uuid4()),
        "user_id": request["submitted_by"],
        "type": "go_live_approved",
        "title": "Go-Live Approved",
        "message": f"Go-Live approved for {request['employee_name']} ({request['employee_code']}). Employee is now active!",
        "link": "/employees",
        "read": False,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.notifications.insert_one(notification)
    
    return {"message": "Go-Live approved. Employee is now active!"}


@api_router.post("/go-live/{request_id}/reject")
async def reject_go_live(
    request_id: str,
    data: dict,
    current_user: User = Depends(get_current_user)
):
    """Admin rejects Go-Live request."""
    global db
    
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only Admin can reject Go-Live")
    
    request = await db.go_live_requests.find_one({"id": request_id, "status": "pending"})
    if not request:
        raise HTTPException(status_code=404, detail="Request not found or already processed")
    
    await db.go_live_requests.update_one(
        {"id": request_id},
        {"$set": {
            "status": "rejected",
            "approved_by": current_user.id,
            "approved_by_name": current_user.full_name,
            "approved_at": datetime.now(timezone.utc).isoformat(),
            "rejection_reason": data.get("reason", "")
        }}
    )
    
    # Notify HR
    notification = {
        "id": str(uuid.uuid4()),
        "user_id": request["submitted_by"],
        "type": "go_live_rejected",
        "title": "Go-Live Rejected",
        "message": f"Go-Live rejected for {request['employee_name']}. Reason: {data.get('reason', 'Not specified')}",
        "link": "/employees",
        "read": False,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.notifications.insert_one(notification)
    
    return {"message": "Go-Live request rejected"}


@api_router.post("/bank-verify/{employee_id}")
async def verify_bank_details(
    employee_id: str,
    current_user: User = Depends(get_current_user)
):
    """HR or Admin verifies employee bank details."""
    global db
    
    if current_user.role not in ["admin", "hr_manager"]:
        raise HTTPException(status_code=403, detail="Only HR Manager or Admin can verify bank details")
    
    result = await db.employees.update_one(
        {"$or": [{"employee_id": employee_id}, {"id": employee_id}]},
        {"$set": {
            "bank_details.proof_verified": True,
            "bank_details.verified_by": current_user.full_name,
            "bank_details.verified_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    return {"message": "Bank details verified"}


# ==================== DOCUMENT HISTORY (HR Documents) ====================

class GeneratedDocument(BaseModel):
    """Model for storing generated HR documents"""
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    document_type: str  # offer_letter, appointment_letter, confirmation_letter, experience_letter
    employee_id: str
    employee_name: str
    content: str  # HTML content
    custom_values: Optional[Dict[str, Any]] = {}
    generated_by: str
    generated_by_name: str
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    status: str = "generated"  # generated, sent, signed, archived
    sent_at: Optional[datetime] = None
    signed_at: Optional[datetime] = None
    notes: Optional[str] = None


class GeneratedDocumentCreate(BaseModel):
    document_type: str
    employee_id: str
    employee_name: str
    content: str
    custom_values: Optional[Dict[str, Any]] = {}
    notes: Optional[str] = None


@api_router.post("/document-history")
async def create_document_history(
    doc_data: GeneratedDocumentCreate,
    current_user: User = Depends(get_current_user)
):
    """Save a generated document to history"""
    if current_user.role not in ["admin", "hr_manager", "hr_executive"]:
        raise HTTPException(status_code=403, detail="Only Admin/HR can generate documents")
    
    doc = GeneratedDocument(
        document_type=doc_data.document_type,
        employee_id=doc_data.employee_id,
        employee_name=doc_data.employee_name,
        content=doc_data.content,
        custom_values=doc_data.custom_values,
        generated_by=current_user.id if hasattr(current_user, 'id') else str(current_user.email),
        generated_by_name=current_user.full_name,
        notes=doc_data.notes
    )
    
    await db.document_history.insert_one(doc.model_dump())
    
    # Notify the employee (using direct DB insert)
    try:
        notification = {
            "id": str(uuid.uuid4()),
            "user_id": doc_data.employee_id,
            "type": "document_generated",
            "title": f"New Document Generated: {doc_data.document_type.replace('_', ' ').title()}",
            "message": f"A {doc_data.document_type.replace('_', ' ').title()} has been generated for you by {current_user.full_name}.",
            "reference_type": "document",
            "reference_id": doc.id,
            "read": False,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.notifications.insert_one(notification)
    except Exception as e:
        print(f"[DOCUMENT NOTIFICATION] Failed to create notification: {e}")
    
    return {"message": "Document saved to history", "id": doc.id}


# ==================== DOCUMENT TEMPLATES ====================

class DocumentTemplate(BaseModel):
    """Reusable document template"""
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    document_type: str  # offer_letter, appointment_letter, confirmation_letter, experience_letter
    name: str
    subject: str
    content: str  # HTML with placeholders
    is_default: bool = False
    created_by: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class DocumentTemplateCreate(BaseModel):
    document_type: str
    name: str
    subject: str
    content: str
    is_default: Optional[bool] = False


@api_router.post("/document-templates")
async def create_document_template(
    template_data: DocumentTemplateCreate,
    current_user: User = Depends(get_current_user)
):
    """Create a new document template"""
    if current_user.role not in ["admin", "hr_manager"]:
        raise HTTPException(status_code=403, detail="Only Admin/HR Manager can create templates")
    
    template = DocumentTemplate(
        document_type=template_data.document_type,
        name=template_data.name,
        subject=template_data.subject,
        content=template_data.content,
        is_default=template_data.is_default,
        created_by=current_user.email
    )
    
    await db.document_templates.insert_one(template.model_dump())
    return {"message": "Template created", "id": template.id}


@api_router.get("/document-templates")
async def get_document_templates(
    document_type: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get all document templates"""
    query = {}
    if document_type:
        query["document_type"] = document_type
    
    templates = await db.document_templates.find(query, {"_id": 0}).sort("created_at", -1).to_list(100)
    return templates


@api_router.put("/document-templates/{template_id}")
async def update_document_template(
    template_id: str,
    template_data: DocumentTemplateCreate,
    current_user: User = Depends(get_current_user)
):
    """Update a document template"""
    if current_user.role not in ["admin", "hr_manager"]:
        raise HTTPException(status_code=403, detail="Only Admin/HR Manager can update templates")
    
    result = await db.document_templates.update_one(
        {"id": template_id},
        {"$set": {
            "name": template_data.name,
            "subject": template_data.subject,
            "content": template_data.content,
            "document_type": template_data.document_type,
            "is_default": template_data.is_default,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Template not found")
    
    return {"message": "Template updated"}


@api_router.delete("/document-templates/{template_id}")
async def delete_document_template(
    template_id: str,
    current_user: User = Depends(get_current_user)
):
    """Delete a document template"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only Admin can delete templates")
    
    result = await db.document_templates.delete_one({"id": template_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Template not found")
    
    return {"message": "Template deleted"}


@api_router.post("/document-history/{doc_id}/send-email")
async def send_document_email(
    doc_id: str,
    email_data: dict,
    current_user: User = Depends(get_current_user)
):
    """Send document via email to employee"""
    if current_user.role not in ["admin", "hr_manager", "hr_executive"]:
        raise HTTPException(status_code=403, detail="Only Admin/HR can send documents")
    
    doc = await db.document_history.find_one({"id": doc_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    to_email = email_data.get("to_email")
    if not to_email:
        # Try to get employee email
        employee = await db.employees.find_one({"employee_id": doc["employee_id"]}, {"_id": 0})
        if employee:
            to_email = employee.get("email") or employee.get("personal_email")
    
    if not to_email:
        raise HTTPException(status_code=400, detail="No email address found")
    
    # Update document status
    await db.document_history.update_one(
        {"id": doc_id},
        {"$set": {
            "status": "sent",
            "sent_at": datetime.now(timezone.utc).isoformat(),
            "sent_to": to_email,
            "sent_by": current_user.email
        }}
    )
    
    # Log the email (actual sending would be done via email service)
    print(f"[DOCUMENT EMAIL] Sending {doc['document_type']} to {to_email} for {doc['employee_name']}")
    
    return {"message": f"Document sent to {to_email}", "status": "sent"}


# ==================== EMPLOYEE PERMISSIONS ====================

class EmployeePermissionUpdate(BaseModel):
    permissions: Optional[Dict[str, Any]] = {}
    reporting_manager_id: Optional[str] = None
    role: Optional[str] = None


class PermissionChangeRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    employee_id: str
    employee_name: str
    requested_by: str
    requested_by_name: str
    changes: Dict[str, Any]
    original_values: Dict[str, Any]
    note: Optional[str] = None
    status: str = "pending"  # pending, approved, rejected
    approved_by: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    processed_at: Optional[datetime] = None


@api_router.get("/employee-permissions/{employee_id}")
async def get_employee_permissions(
    employee_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get permissions for a specific employee"""
    # Get employee
    employee = await db.employees.find_one({"employee_id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Get user account if exists
    user = await db.users.find_one({"employee_id": employee_id}, {"_id": 0})
    
    # Get or create permissions record
    perms = await db.employee_permissions.find_one({"employee_id": employee_id}, {"_id": 0})
    
    return {
        "employee_id": employee_id,
        "role": user.get("role") if user else None,
        "reporting_manager_id": employee.get("reporting_manager_id"),
        "permissions": perms.get("permissions", {}) if perms else {},
        "is_active": user.get("is_active", False) if user else False
    }


@api_router.put("/employee-permissions/{employee_id}")
async def update_employee_permissions(
    employee_id: str,
    update_data: EmployeePermissionUpdate,
    current_user: User = Depends(get_current_user)
):
    """Update permissions for an employee (Admin only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only Admin can directly update permissions")
    
    # Update employee record
    employee_update = {}
    if update_data.reporting_manager_id is not None:
        employee_update["reporting_manager_id"] = update_data.reporting_manager_id
    
    if employee_update:
        await db.employees.update_one(
            {"employee_id": employee_id},
            {"$set": employee_update}
        )
    
    # Update user role if provided
    if update_data.role:
        await db.users.update_one(
            {"employee_id": employee_id},
            {"$set": {"role": update_data.role}}
        )
    
    # Update or create permissions record
    await db.employee_permissions.update_one(
        {"employee_id": employee_id},
        {"$set": {
            "employee_id": employee_id,
            "permissions": update_data.permissions,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "updated_by": current_user.email
        }},
        upsert=True
    )
    
    return {"message": "Permissions updated successfully"}


@api_router.post("/permission-change-requests")
async def create_permission_change_request(
    request_data: dict,
    current_user: User = Depends(get_current_user)
):
    """Submit a permission change request for admin approval"""
    if current_user.role not in ["hr_manager", "hr_executive"]:
        raise HTTPException(status_code=403, detail="Only HR can submit change requests")
    
    req = PermissionChangeRequest(
        employee_id=request_data["employee_id"],
        employee_name=request_data["employee_name"],
        requested_by=current_user.email,
        requested_by_name=current_user.full_name,
        changes=request_data["changes"],
        original_values=request_data["original_values"],
        note=request_data.get("note")
    )
    
    await db.permission_change_requests.insert_one(req.model_dump())
    
    # Notify admins
    admins = await db.users.find({"role": "admin"}, {"_id": 0, "id": 1}).to_list(10)
    for admin in admins:
        notification = {
            "id": str(uuid.uuid4()),
            "user_id": admin.get("id"),
            "type": "permission_change_request",
            "title": f"Permission Change Request: {req.employee_name}",
            "message": f"{current_user.full_name} requested permission changes for {req.employee_name}",
            "reference_type": "permission_request",
            "reference_id": req.id,
            "read": False,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.notifications.insert_one(notification)
    
    return {"message": "Request submitted for approval", "id": req.id}


@api_router.get("/permission-change-requests")
async def get_permission_change_requests(
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get permission change requests"""
    query = {}
    if status:
        query["status"] = status
    
    # HR can see their own requests, Admin can see all
    if current_user.role not in ["admin"]:
        query["requested_by"] = current_user.email
    
    requests = await db.permission_change_requests.find(query, {"_id": 0}).sort("created_at", -1).to_list(50)
    return requests


@api_router.post("/permission-change-requests/{request_id}/approve")
async def approve_permission_change(
    request_id: str,
    current_user: User = Depends(get_current_user)
):
    """Approve a permission change request (Admin only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only Admin can approve requests")
    
    req = await db.permission_change_requests.find_one({"id": request_id}, {"_id": 0})
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    
    if req["status"] != "pending":
        raise HTTPException(status_code=400, detail="Request already processed")
    
    # Apply the changes
    changes = req["changes"]
    employee_id = req["employee_id"]
    
    # Update employee record
    if changes.get("reporting_manager_id"):
        await db.employees.update_one(
            {"employee_id": employee_id},
            {"$set": {"reporting_manager_id": changes["reporting_manager_id"]}}
        )
    
    # Update user role
    if changes.get("role"):
        await db.users.update_one(
            {"employee_id": employee_id},
            {"$set": {"role": changes["role"]}}
        )
    
    # Update permissions
    if changes.get("permissions"):
        await db.employee_permissions.update_one(
            {"employee_id": employee_id},
            {"$set": {
                "employee_id": employee_id,
                "permissions": changes["permissions"],
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "updated_by": current_user.email
            }},
            upsert=True
        )
    
    # Update request status
    await db.permission_change_requests.update_one(
        {"id": request_id},
        {"$set": {
            "status": "approved",
            "approved_by": current_user.email,
            "processed_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    # Notify requester
    notification = {
        "id": str(uuid.uuid4()),
        "user_id": req["requested_by"],
        "type": "permission_request_approved",
        "title": f"Permission Change Approved",
        "message": f"Your permission change request for {req['employee_name']} has been approved by {current_user.full_name}",
        "reference_type": "permission_request",
        "reference_id": request_id,
        "read": False,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.notifications.insert_one(notification)
    
    return {"message": "Request approved and changes applied"}


@api_router.post("/permission-change-requests/{request_id}/reject")
async def reject_permission_change(
    request_id: str,
    current_user: User = Depends(get_current_user)
):
    """Reject a permission change request (Admin only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only Admin can reject requests")
    
    req = await db.permission_change_requests.find_one({"id": request_id}, {"_id": 0})
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    
    # Update request status
    await db.permission_change_requests.update_one(
        {"id": request_id},
        {"$set": {
            "status": "rejected",
            "approved_by": current_user.email,
            "processed_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    # Notify requester
    notification = {
        "id": str(uuid.uuid4()),
        "user_id": req["requested_by"],
        "type": "permission_request_rejected",
        "title": f"Permission Change Rejected",
        "message": f"Your permission change request for {req['employee_name']} has been rejected",
        "reference_type": "permission_request",
        "reference_id": request_id,
        "read": False,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.notifications.insert_one(notification)
    
    return {"message": "Request rejected"}


@api_router.get("/document-history")
async def get_document_history(
    employee_id: Optional[str] = None,
    document_type: Optional[str] = None,
    limit: int = 50,
    current_user: User = Depends(get_current_user)
):
    """Get document history with optional filters"""
    query = {}
    if employee_id:
        query["employee_id"] = employee_id
    if document_type:
        query["document_type"] = document_type
    
    docs = await db.document_history.find(query, {"_id": 0}).sort("generated_at", -1).limit(limit).to_list(limit)
    return docs


@api_router.get("/document-history/{doc_id}")
async def get_document_by_id(
    doc_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get a specific document by ID"""
    doc = await db.document_history.find_one({"id": doc_id}, {"_id": 0})
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@api_router.put("/document-history/{doc_id}/status")
async def update_document_status(
    doc_id: str,
    status_data: dict,
    current_user: User = Depends(get_current_user)
):
    """Update document status (sent, signed, archived)"""
    if current_user.role not in ["admin", "hr_manager", "hr_executive"]:
        raise HTTPException(status_code=403, detail="Only Admin/HR can update document status")
    
    update_fields = {"status": status_data.get("status")}
    if status_data.get("status") == "sent":
        update_fields["sent_at"] = datetime.now(timezone.utc).isoformat()
    elif status_data.get("status") == "signed":
        update_fields["signed_at"] = datetime.now(timezone.utc).isoformat()
    
    if status_data.get("notes"):
        update_fields["notes"] = status_data.get("notes")
    
    result = await db.document_history.update_one(
        {"id": doc_id},
        {"$set": update_fields}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return {"message": "Document status updated"}


@api_router.delete("/document-history/{doc_id}")
async def delete_document_from_history(
    doc_id: str,
    current_user: User = Depends(get_current_user)
):
    """Delete a document from history (Admin only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only Admin can delete documents")
    
    result = await db.document_history.delete_one({"id": doc_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return {"message": "Document deleted"}


@api_router.get("/document-history/employee/{employee_id}/stats")
async def get_employee_document_stats(
    employee_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get document statistics for an employee"""
    pipeline = [
        {"$match": {"employee_id": employee_id}},
        {"$group": {
            "_id": "$document_type",
            "count": {"$sum": 1},
            "latest": {"$max": "$generated_at"}
        }}
    ]
    
    stats = await db.document_history.aggregate(pipeline).to_list(10)
    
    # Format response
    result = {
        "total_documents": 0,
        "by_type": {},
        "latest_document": None
    }
    
    for stat in stats:
        result["by_type"][stat["_id"]] = {
            "count": stat["count"],
            "latest": stat["latest"]
        }
        result["total_documents"] += stat["count"]
    
    # Get latest document
    latest = await db.document_history.find_one(
        {"employee_id": employee_id}, 
        {"_id": 0},
        sort=[("generated_at", -1)]
    )
    if latest:
        result["latest_document"] = {
            "id": latest.get("id"),
            "type": latest.get("document_type"),
            "generated_at": latest.get("generated_at")
        }
    
    return result


api_router.include_router(masters_router.router)
api_router.include_router(sow_masters_router.router)
api_router.include_router(enhanced_sow_router.router)

# Modular routers (Phase 2 - enabled)
api_router.include_router(stats_router.router)
api_router.include_router(security_router.router)
api_router.include_router(kickoff_router.router)
api_router.include_router(ctc_router.router)
api_router.include_router(employees_router.router)
api_router.include_router(attendance_router.router)
api_router.include_router(expenses_router.router)
api_router.include_router(hr_router.router)

# Phase 3 - Core routers (auth, leads, projects, meetings, users)
api_router.include_router(auth_router.router)
api_router.include_router(leads_router.router)
api_router.include_router(projects_router.router)
api_router.include_router(meetings_router.router)
api_router.include_router(users_router.router)
api_router.include_router(role_management_router.router)
api_router.include_router(letters_router.router)
api_router.include_router(payments_router.router)
api_router.include_router(project_payments_router.router)
api_router.include_router(department_access_router.router)
api_router.include_router(permission_config_router.router)

app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()