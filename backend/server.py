from fastapi import FastAPI, APIRouter, HTTPException, Depends, status, Response, Request
from fastapi.responses import FileResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
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
    is_active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

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

@api_router.post("/auth/register", response_model=User)
async def register(user_create: UserCreate):
    existing_user = await db.users.find_one({"email": user_create.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user_dict = user_create.model_dump(exclude={"password"})
    # Sanitize user input to prevent XSS
    if 'full_name' in user_dict:
        user_dict['full_name'] = sanitize_text(user_dict['full_name'])
    if 'department' in user_dict and user_dict['department']:
        user_dict['department'] = sanitize_text(user_dict['department'])
    
    user = User(**user_dict)
    
    doc = user.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['hashed_password'] = get_password_hash(user_create.password)
    
    await db.users.insert_one(doc)
    return user

@api_router.get("/auth/me", response_model=User)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user


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


# --- Google Auth Endpoint ---
class GoogleAuthRequest(BaseModel):
    session_id: str

@api_router.post("/auth/google", response_model=Token)
async def google_auth(auth_req: GoogleAuthRequest, request: Request):
    """Authenticate via Google (Emergent Auth) - restricted to allowed domain, pre-registered users only"""
    # 1. Call Emergent Auth to get session data
    try:
        async with httpx.AsyncClient() as client_http:
            resp = await client_http.get(
                EMERGENT_AUTH_URL,
                headers={"X-Session-ID": auth_req.session_id},
                timeout=10.0
            )
            if resp.status_code != 200:
                await log_security_event("google_login_failed", details={"reason": "emergent_auth_error", "status": resp.status_code}, request=request)
                raise HTTPException(status_code=401, detail="Google authentication failed")
            session_data = resp.json()
    except httpx.RequestError:
        raise HTTPException(status_code=502, detail="Could not reach authentication service")

    google_email = session_data.get("email", "").lower()
    google_name = session_data.get("name", "")

    # 2. Domain restriction
    email_domain = google_email.split("@")[-1] if "@" in google_email else ""
    if email_domain != ALLOWED_DOMAIN:
        await log_security_event("google_login_rejected_domain", email=google_email, details={"domain": email_domain, "allowed": ALLOWED_DOMAIN}, request=request)
        raise HTTPException(status_code=403, detail=f"Access restricted to @{ALLOWED_DOMAIN} accounts only")

    # 3. Pre-registered check — user must exist in DB
    user_data = await db.users.find_one({"email": google_email}, {"_id": 0})
    if not user_data:
        await log_security_event("google_login_rejected_unregistered", email=google_email, request=request)
        raise HTTPException(status_code=403, detail="Your account is not registered. Please contact your administrator.")

    if not user_data.get("is_active", True):
        await log_security_event("google_login_rejected_inactive", email=google_email, request=request)
        raise HTTPException(status_code=403, detail="Your account has been deactivated. Please contact your administrator.")

    # 4. Update google profile info if available
    update_fields = {"last_login": datetime.now(timezone.utc).isoformat(), "auth_method": "google"}
    if google_name and not user_data.get("full_name"):
        update_fields["full_name"] = sanitize_text(google_name)
    if session_data.get("picture"):
        update_fields["google_picture"] = session_data["picture"]
    await db.users.update_one({"email": google_email}, {"$set": update_fields})

    # 5. Issue JWT token (same as password login)
    if isinstance(user_data.get('created_at'), str):
        user_data['created_at'] = datetime.fromisoformat(user_data['created_at'])
    user_data.pop('hashed_password', None)
    user = User(**user_data)

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )

    await log_security_event("google_login_success", email=google_email, request=request)
    return Token(access_token=access_token, token_type="bearer", user=user)


# --- Admin OTP Password Reset ---
class OTPRequestModel(BaseModel):
    email: EmailStr

class OTPVerifyModel(BaseModel):
    email: EmailStr
    otp: str
    new_password: str

@api_router.post("/auth/admin/request-otp")
async def request_admin_otp(otp_req: OTPRequestModel, request: Request):
    """Generate an OTP for admin password reset. Only admin-role users can request OTP."""
    user_data = await db.users.find_one({"email": otp_req.email}, {"_id": 0})
    if not user_data:
        await log_security_event("otp_request_failed", email=otp_req.email, details={"reason": "user_not_found"}, request=request)
        raise HTTPException(status_code=404, detail="User not found")

    if user_data.get("role") != "admin":
        await log_security_event("otp_request_rejected", email=otp_req.email, details={"reason": "not_admin"}, request=request)
        raise HTTPException(status_code=403, detail="OTP password reset is only available for admin accounts")

    # Generate 6-digit OTP
    otp_code = ''.join(random.choices(string.digits, k=6))
    otp_expiry = datetime.now(timezone.utc) + timedelta(minutes=10)

    await db.otp_tokens.delete_many({"email": otp_req.email})
    await db.otp_tokens.insert_one({
        "email": otp_req.email,
        "otp": otp_code,
        "expires_at": otp_expiry.isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat(),
    })

    await log_security_event("otp_generated", email=otp_req.email, details={"otp_code": otp_code}, request=request)
    # In production, send OTP via email/SMS. For now, return it (admin can view in audit log)
    return {"message": "OTP generated successfully", "otp": otp_code, "expires_in_minutes": 10}


@api_router.post("/auth/admin/reset-password")
async def reset_admin_password(otp_verify: OTPVerifyModel, request: Request):
    """Verify OTP and reset admin password"""
    otp_record = await db.otp_tokens.find_one({"email": otp_verify.email, "otp": otp_verify.otp}, {"_id": 0})
    if not otp_record:
        await log_security_event("otp_verify_failed", email=otp_verify.email, details={"reason": "invalid_otp"}, request=request)
        raise HTTPException(status_code=400, detail="Invalid OTP")

    expires_at = datetime.fromisoformat(otp_record["expires_at"])
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        await db.otp_tokens.delete_many({"email": otp_verify.email})
        await log_security_event("otp_verify_failed", email=otp_verify.email, details={"reason": "otp_expired"}, request=request)
        raise HTTPException(status_code=400, detail="OTP has expired. Please request a new one.")

    if len(otp_verify.new_password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")

    new_hash = get_password_hash(otp_verify.new_password)
    await db.users.update_one({"email": otp_verify.email}, {"$set": {"hashed_password": new_hash}})
    await db.otp_tokens.delete_many({"email": otp_verify.email})

    await log_security_event("password_reset_success", email=otp_verify.email, request=request)
    return {"message": "Password reset successfully"}


# --- Admin Change Password (while logged in) ---
class ChangePasswordModel(BaseModel):
    current_password: str
    new_password: str

@api_router.post("/auth/change-password")
async def change_password(pwd_data: ChangePasswordModel, current_user: User = Depends(get_current_user), request: Request = None):
    """Change password for current user (admin only, since employees use Google)"""
    user_data = await db.users.find_one({"email": current_user.email}, {"_id": 0})
    if not user_data or not user_data.get("hashed_password"):
        raise HTTPException(status_code=400, detail="No password set for this account")

    if not verify_password(pwd_data.current_password, user_data["hashed_password"]):
        await log_security_event("password_change_failed", email=current_user.email, details={"reason": "wrong_current_password"}, request=request)
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    if len(pwd_data.new_password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")

    new_hash = get_password_hash(pwd_data.new_password)
    await db.users.update_one({"email": current_user.email}, {"$set": {"hashed_password": new_hash}})

    await log_security_event("password_change_success", email=current_user.email, request=request)
    return {"message": "Password changed successfully"}


# --- Security Audit Logs Endpoint ---
@api_router.get("/security-audit-logs")
async def get_security_audit_logs(
    event_type: Optional[str] = None,
    email: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user)
):
    """Get security audit logs (admin only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can view security audit logs")

    query = {}
    if event_type:
        query["event_type"] = event_type
    if email:
        query["email"] = {"$regex": email, "$options": "i"}
    if date_from:
        query.setdefault("timestamp", {})["$gte"] = date_from
    if date_to:
        query.setdefault("timestamp", {})["$lte"] = date_to

    total = await db.security_audit_logs.count_documents(query)
    logs = await db.security_audit_logs.find(query, {"_id": 0}).sort("timestamp", -1).skip(skip).limit(limit).to_list(limit)

    return {"logs": logs, "total": total}


# --- Update existing login to add audit logging ---
@api_router.post("/auth/login", response_model=Token)
async def login(user_login: UserLogin, request: Request = None):
    user_data = await db.users.find_one({"email": user_login.email}, {"_id": 0})
    if not user_data:
        await log_security_event("password_login_failed", email=user_login.email, details={"reason": "user_not_found"}, request=request)
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    if not verify_password(user_login.password, user_data.get('hashed_password', '')):
        await log_security_event("password_login_failed", email=user_login.email, details={"reason": "wrong_password"}, request=request)
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    if isinstance(user_data.get('created_at'), str):
        user_data['created_at'] = datetime.fromisoformat(user_data['created_at'])

    user_data.pop('hashed_password', None)
    user = User(**user_data)

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )

    await log_security_event("password_login_success", email=user_login.email, request=request)
    await db.users.update_one({"email": user_login.email}, {"$set": {"last_login": datetime.now(timezone.utc).isoformat(), "auth_method": "password"}})
    return Token(access_token=access_token, token_type="bearer", user=user)


@api_router.post("/leads", response_model=Lead)
async def create_lead(lead_create: LeadCreate, current_user: User = Depends(get_current_user)):
    if current_user.role == UserRole.MANAGER:
        raise HTTPException(status_code=403, detail="Managers can only view and download")
    
    lead_dict = lead_create.model_dump()
    
    # Calculate lead score
    score, breakdown = calculate_lead_score(lead_dict)
    
    lead = Lead(**lead_dict, created_by=current_user.id, lead_score=score, score_breakdown=breakdown)
    
    doc = lead.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    if doc['enriched_at']:
        doc['enriched_at'] = doc['enriched_at'].isoformat()
    
    await db.leads.insert_one(doc)
    return lead

@api_router.get("/leads", response_model=List[Lead])
async def get_leads(
    status: Optional[str] = None,
    assigned_to: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    query = {}
    if status:
        query['status'] = status
    if assigned_to:
        query['assigned_to'] = assigned_to
    
    if current_user.role == UserRole.MANAGER or current_user.role == UserRole.EXECUTIVE:
        if 'assigned_to' not in query:
            query['$or'] = [{"assigned_to": current_user.id}, {"created_by": current_user.id}]
    
    leads = await db.leads.find(query, {"_id": 0}).to_list(1000)
    
    for lead in leads:
        if isinstance(lead.get('created_at'), str):
            lead['created_at'] = datetime.fromisoformat(lead['created_at'])
        if isinstance(lead.get('updated_at'), str):
            lead['updated_at'] = datetime.fromisoformat(lead['updated_at'])
        if lead.get('enriched_at') and isinstance(lead['enriched_at'], str):
            lead['enriched_at'] = datetime.fromisoformat(lead['enriched_at'])
    
    return leads

@api_router.get("/leads/{lead_id}", response_model=Lead)
async def get_lead(lead_id: str, current_user: User = Depends(get_current_user)):
    lead_data = await db.leads.find_one({"id": lead_id}, {"_id": 0})
    if not lead_data:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    if isinstance(lead_data.get('created_at'), str):
        lead_data['created_at'] = datetime.fromisoformat(lead_data['created_at'])
    if isinstance(lead_data.get('updated_at'), str):
        lead_data['updated_at'] = datetime.fromisoformat(lead_data['updated_at'])
    if lead_data.get('enriched_at') and isinstance(lead_data['enriched_at'], str):
        lead_data['enriched_at'] = datetime.fromisoformat(lead_data['enriched_at'])
    
    return Lead(**lead_data)

@api_router.put("/leads/{lead_id}", response_model=Lead)
async def update_lead(
    lead_id: str,
    lead_update: LeadUpdate,
    current_user: User = Depends(get_current_user)
):
    if current_user.role == UserRole.MANAGER:
        raise HTTPException(status_code=403, detail="Managers can only view and download")
    
    lead_data = await db.leads.find_one({"id": lead_id}, {"_id": 0})
    if not lead_data:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    update_data = lead_update.model_dump(exclude_unset=True)
    update_data['updated_at'] = datetime.now(timezone.utc).isoformat()
    
    # Recalculate lead score with updated data
    merged_data = {**lead_data, **update_data}
    score, breakdown = calculate_lead_score(merged_data)
    update_data['lead_score'] = score
    update_data['score_breakdown'] = breakdown
    
    await db.leads.update_one({"id": lead_id}, {"$set": update_data})
    
    updated_lead_data = await db.leads.find_one({"id": lead_id}, {"_id": 0})
    if isinstance(updated_lead_data.get('created_at'), str):
        updated_lead_data['created_at'] = datetime.fromisoformat(updated_lead_data['created_at'])
    if isinstance(updated_lead_data.get('updated_at'), str):
        updated_lead_data['updated_at'] = datetime.fromisoformat(updated_lead_data['updated_at'])
    if updated_lead_data.get('enriched_at') and isinstance(updated_lead_data['enriched_at'], str):
        updated_lead_data['enriched_at'] = datetime.fromisoformat(updated_lead_data['enriched_at'])
    
    return Lead(**updated_lead_data)

@api_router.delete("/leads/{lead_id}")
async def delete_lead(lead_id: str, current_user: User = Depends(get_current_user)):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only admins can delete leads")
    
    result = await db.leads.delete_one({"id": lead_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Lead not found")
    return {"message": "Lead deleted successfully"}

@api_router.post("/projects", response_model=Project)
async def create_project(project_create: ProjectCreate, current_user: User = Depends(get_current_user)):
    if current_user.role == UserRole.MANAGER:
        raise HTTPException(status_code=403, detail="Managers can only view and download")
    
    project_dict = project_create.model_dump()
    project = Project(**project_dict, created_by=current_user.id)
    
    doc = project.model_dump()
    doc['start_date'] = doc['start_date'].isoformat()
    if doc['end_date']:
        doc['end_date'] = doc['end_date'].isoformat()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    
    await db.projects.insert_one(doc)
    return project

@api_router.get("/projects", response_model=List[Project])
async def get_projects(current_user: User = Depends(get_current_user)):
    query = {}
    if current_user.role != UserRole.ADMIN:
        query['$or'] = [{"assigned_team": current_user.id}, {"created_by": current_user.id}]
    
    projects = await db.projects.find(query, {"_id": 0}).to_list(1000)
    
    for project in projects:
        if isinstance(project.get('start_date'), str):
            project['start_date'] = datetime.fromisoformat(project['start_date'])
        if project.get('end_date') and isinstance(project['end_date'], str):
            project['end_date'] = datetime.fromisoformat(project['end_date'])
        if isinstance(project.get('created_at'), str):
            project['created_at'] = datetime.fromisoformat(project['created_at'])
        if isinstance(project.get('updated_at'), str):
            project['updated_at'] = datetime.fromisoformat(project['updated_at'])
    
    return projects

# Handover alerts must be defined BEFORE /projects/{project_id} to avoid route conflict
@api_router.get("/projects/handover-alerts")
async def get_handover_alerts(current_user: User = Depends(get_current_user)):
    """Get projects approaching 15-day handover deadline from agreement approval"""
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER, UserRole.PROJECT_MANAGER]:
        raise HTTPException(status_code=403, detail="Not authorized to view handover alerts")
    
    # Get approved agreements from last 30 days
    thirty_days_ago = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    
    agreements = await db.agreements.find(
        {
            "status": "approved",
            "approved_at": {"$gte": thirty_days_ago}
        },
        {"_id": 0}
    ).to_list(1000)
    
    alerts = []
    for agreement in agreements:
        approved_at = agreement.get('approved_at')
        if isinstance(approved_at, str):
            approved_at = datetime.fromisoformat(approved_at)
        
        if approved_at:
            days_since_approval = (datetime.now(timezone.utc) - approved_at).days
            days_remaining = 15 - days_since_approval
            
            # Check if project has been created for this agreement
            project = await db.projects.find_one(
                {"agreement_id": agreement['id']},
                {"_id": 0}
            )
            
            # Get lead info
            lead = None
            if agreement.get('lead_id'):
                lead = await db.leads.find_one(
                    {"id": agreement['lead_id']},
                    {"_id": 0, "first_name": 1, "last_name": 1, "company": 1}
                )
            
            alert_type = "on_track"
            if days_remaining <= 0:
                alert_type = "overdue"
            elif days_remaining <= 3:
                alert_type = "critical"
            elif days_remaining <= 7:
                alert_type = "warning"
            
            alerts.append({
                "agreement": agreement,
                "lead": lead,
                "project": project,
                "days_since_approval": days_since_approval,
                "days_remaining": days_remaining,
                "alert_type": alert_type,
                "has_project": project is not None,
                "has_consultants_assigned": project.get('assigned_consultants', []) if project else []
            })
    
    # Sort by days_remaining (most urgent first)
    alerts.sort(key=lambda x: x['days_remaining'])
    
    return alerts

@api_router.get("/projects/{project_id}", response_model=Project)
async def get_project(project_id: str, current_user: User = Depends(get_current_user)):
    project_data = await db.projects.find_one({"id": project_id}, {"_id": 0})
    if not project_data:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if isinstance(project_data.get('start_date'), str):
        project_data['start_date'] = datetime.fromisoformat(project_data['start_date'])
    if project_data.get('end_date') and isinstance(project_data['end_date'], str):
        project_data['end_date'] = datetime.fromisoformat(project_data['end_date'])
    if isinstance(project_data.get('created_at'), str):
        project_data['created_at'] = datetime.fromisoformat(project_data['created_at'])
    if isinstance(project_data.get('updated_at'), str):
        project_data['updated_at'] = datetime.fromisoformat(project_data['updated_at'])
    
    return Project(**project_data)

@api_router.post("/meetings", response_model=Meeting)
async def create_meeting(meeting_create: MeetingCreate, current_user: User = Depends(get_current_user)):
    meeting_type = meeting_create.type
    # Role-based access control
    if current_user.role == "hr_manager":
        raise HTTPException(status_code=403, detail="HR Managers do not have CRUD access to meetings")
    if meeting_type == "sales" and current_user.role not in SALES_MEETING_ROLES:
        raise HTTPException(status_code=403, detail="Only sales roles can create sales meetings")
    if meeting_type == "consulting" and current_user.role not in CONSULTING_MEETING_ROLES:
        raise HTTPException(status_code=403, detail="Only consulting/PM roles can create consulting meetings")
    # Consulting meetings require project_id
    if meeting_type == "consulting" and not meeting_create.project_id:
        raise HTTPException(status_code=400, detail="Consulting meetings must be linked to a project")

    meeting_dict = meeting_create.model_dump()
    meeting = Meeting(**meeting_dict, created_by=current_user.id)

    doc = meeting.model_dump()
    doc['meeting_date'] = doc['meeting_date'].isoformat()
    doc['created_at'] = doc['created_at'].isoformat()

    await db.meetings.insert_one(doc)

    if meeting.is_delivered and meeting.project_id:
        await db.projects.update_one(
            {"id": meeting.project_id},
            {"$inc": {"total_meetings_delivered": 1, "number_of_visits": 1}}
        )

    return meeting

@api_router.get("/meetings", response_model=List[Meeting])
async def get_meetings(
    project_id: Optional[str] = None,
    meeting_type: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    query = {}
    if project_id:
        query['project_id'] = project_id
    if meeting_type:
        query['type'] = meeting_type

    meetings = await db.meetings.find(query, {"_id": 0}).to_list(1000)

    for meeting in meetings:
        if isinstance(meeting.get('meeting_date'), str):
            meeting['meeting_date'] = datetime.fromisoformat(meeting['meeting_date'])
        if isinstance(meeting.get('created_at'), str):
            meeting['created_at'] = datetime.fromisoformat(meeting['created_at'])

    return meetings

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


@api_router.get("/meetings/{meeting_id}")
async def get_meeting(meeting_id: str, current_user: User = Depends(get_current_user)):
    """Get a single meeting with full MOM details"""
    meeting = await db.meetings.find_one({"id": meeting_id}, {"_id": 0})
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    
    if isinstance(meeting.get('meeting_date'), str):
        meeting['meeting_date'] = datetime.fromisoformat(meeting['meeting_date'])
    if isinstance(meeting.get('created_at'), str):
        meeting['created_at'] = datetime.fromisoformat(meeting['created_at'])
    
    return meeting


@api_router.patch("/meetings/{meeting_id}/mom")
async def update_meeting_mom(
    meeting_id: str,
    mom_data: MOMCreate,
    current_user: User = Depends(get_current_user)
):
    """Update Minutes of Meeting for a meeting"""
    meeting = await db.meetings.find_one({"id": meeting_id}, {"_id": 0})
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    
    update_data = mom_data.model_dump(exclude_unset=True)
    update_data['mom_generated'] = True
    update_data['updated_at'] = datetime.now(timezone.utc).isoformat()
    
    if update_data.get('next_meeting_date'):
        update_data['next_meeting_date'] = update_data['next_meeting_date'].isoformat()
    
    # Process action items
    action_items = update_data.get('action_items', [])
    for item in action_items:
        if not item.get('id'):
            item['id'] = str(uuid.uuid4())
        if item.get('due_date') and isinstance(item['due_date'], datetime):
            item['due_date'] = item['due_date'].isoformat()
    
    await db.meetings.update_one({"id": meeting_id}, {"$set": update_data})
    
    return {"message": "MOM updated successfully", "meeting_id": meeting_id}


@api_router.post("/meetings/{meeting_id}/action-items")
async def add_action_item(
    meeting_id: str,
    action_item: ActionItemCreate,
    current_user: User = Depends(get_current_user)
):
    """Add action item to meeting with optional follow-up task creation"""
    meeting = await db.meetings.find_one({"id": meeting_id}, {"_id": 0})
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    
    # Create action item
    new_item = {
        "id": str(uuid.uuid4()),
        "description": action_item.description,
        "assigned_to_id": action_item.assigned_to_id,
        "due_date": action_item.due_date.isoformat() if action_item.due_date else None,
        "priority": action_item.priority,
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    # Get assigned user name
    if action_item.assigned_to_id:
        user = await db.users.find_one({"id": action_item.assigned_to_id}, {"_id": 0, "full_name": 1})
        new_item["assigned_to_name"] = user.get("full_name") if user else None
    
    # Create follow-up task if requested
    follow_up_task_id = None
    if action_item.create_follow_up_task and action_item.assigned_to_id:
        # Get project info
        project = await db.projects.find_one({"id": meeting.get('project_id')}, {"_id": 0})
        
        follow_up_task = {
            "id": str(uuid.uuid4()),
            "type": "meeting_action_item",
            "meeting_id": meeting_id,
            "action_item_id": new_item["id"],
            "title": f"[Action Item] {action_item.description}",
            "description": f"Follow-up from meeting on {meeting.get('meeting_date', 'N/A')}",
            "assigned_to": action_item.assigned_to_id,
            "assigned_to_name": new_item.get("assigned_to_name"),
            "project_id": meeting.get('project_id'),
            "project_name": project.get('name') if project else None,
            "due_date": action_item.due_date.isoformat() if action_item.due_date else None,
            "priority": action_item.priority,
            "status": "pending",
            "created_by": current_user.id,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        await db.follow_up_tasks.insert_one(follow_up_task)
        follow_up_task_id = follow_up_task["id"]
        new_item["follow_up_task_id"] = follow_up_task_id
        
        # Notify reporting manager if requested
        if action_item.notify_reporting_manager and action_item.assigned_to_id:
            # Get employee record to find reporting manager
            employee = await db.employees.find_one({"user_id": action_item.assigned_to_id}, {"_id": 0})
            
            if employee and employee.get('reporting_manager_id'):
                manager = await db.users.find_one({"id": employee.get('reporting_manager_id')}, {"_id": 0})
                
                if manager:
                    notification = {
                        "id": str(uuid.uuid4()),
                        "type": "action_item_assigned",
                        "recipient_id": manager.get('id'),
                        "recipient_email": manager.get('email'),
                        "subject": f"Action Item Assigned to {new_item.get('assigned_to_name', 'Team Member')}",
                        "body": f"""
                        <h3>New Action Item Assignment</h3>
                        <p><strong>Assigned To:</strong> {new_item.get('assigned_to_name', 'N/A')}</p>
                        <p><strong>Task:</strong> {action_item.description}</p>
                        <p><strong>Priority:</strong> {action_item.priority.upper()}</p>
                        <p><strong>Due Date:</strong> {action_item.due_date.strftime('%Y-%m-%d') if action_item.due_date else 'Not set'}</p>
                        <p><strong>From Meeting:</strong> {meeting.get('title', 'Meeting')}</p>
                        <p><strong>Project:</strong> {project.get('name') if project else 'N/A'}</p>
                        <hr>
                        <p>This action item has been created as a follow-up from a meeting. Please ensure timely completion.</p>
                        """,
                        "meeting_id": meeting_id,
                        "action_item_id": new_item["id"],
                        "created_at": datetime.now(timezone.utc).isoformat(),
                        "sent": False
                    }
                    
                    await db.notifications.insert_one(notification)
                    print(f"[MOM] Notification queued for reporting manager: {manager.get('email')}")
    
    # Add action item to meeting
    action_items = meeting.get('action_items', []) or []
    action_items.append(new_item)
    
    await db.meetings.update_one(
        {"id": meeting_id},
        {"$set": {
            "action_items": action_items,
            "mom_generated": True,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    return {
        "message": "Action item added",
        "action_item": new_item,
        "follow_up_task_id": follow_up_task_id
    }


@api_router.patch("/meetings/{meeting_id}/action-items/{action_item_id}")
async def update_action_item_status(
    meeting_id: str,
    action_item_id: str,
    status: str,
    current_user: User = Depends(get_current_user)
):
    """Update action item status"""
    meeting = await db.meetings.find_one({"id": meeting_id}, {"_id": 0})
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    
    action_items = meeting.get('action_items', []) or []
    updated = False
    
    for item in action_items:
        if item.get('id') == action_item_id:
            item['status'] = status
            if status == 'completed':
                item['completed_at'] = datetime.now(timezone.utc).isoformat()
            updated = True
            
            # Update follow-up task if exists
            if item.get('follow_up_task_id'):
                await db.follow_up_tasks.update_one(
                    {"id": item['follow_up_task_id']},
                    {"$set": {"status": status, "updated_at": datetime.now(timezone.utc).isoformat()}}
                )
            break
    
    if not updated:
        raise HTTPException(status_code=404, detail="Action item not found")
    
    await db.meetings.update_one(
        {"id": meeting_id},
        {"$set": {"action_items": action_items, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    return {"message": "Action item status updated"}


@api_router.post("/meetings/{meeting_id}/send-mom")
async def send_mom_to_client(
    meeting_id: str,
    current_user: User = Depends(get_current_user)
):
    """Send MOM to client (email notification queued)"""
    meeting = await db.meetings.find_one({"id": meeting_id}, {"_id": 0})
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    
    # Get project and lead/client info
    project = None
    lead = None
    client = None
    
    if meeting.get('project_id'):
        project = await db.projects.find_one({"id": meeting['project_id']}, {"_id": 0})
    
    if meeting.get('lead_id'):
        lead = await db.leads.find_one({"id": meeting['lead_id']}, {"_id": 0})
    elif meeting.get('client_id'):
        client = await db.clients.find_one({"id": meeting['client_id']}, {"_id": 0})
    
    # Get client email
    client_email = None
    client_name = None
    
    if lead:
        client_email = lead.get('email')
        client_name = f"{lead.get('first_name', '')} {lead.get('last_name', '')}".strip()
    elif client:
        # Get primary contact email from client
        contacts = client.get('contacts', [])
        primary_contact = next((c for c in contacts if c.get('is_primary')), contacts[0] if contacts else None)
        if primary_contact:
            client_email = primary_contact.get('email')
            client_name = primary_contact.get('name')
    
    if not client_email:
        raise HTTPException(status_code=400, detail="No client email found")
    
    # Build MOM email content
    agenda_html = "".join([f"<li>{item}</li>" for item in meeting.get('agenda', [])])
    discussion_html = "".join([f"<li>{item}</li>" for item in meeting.get('discussion_points', [])])
    decisions_html = "".join([f"<li>{item}</li>" for item in meeting.get('decisions_made', [])])
    
    action_items_html = ""
    for item in meeting.get('action_items', []):
        action_items_html += f"""
        <tr>
            <td style="padding: 8px; border: 1px solid #ddd;">{item.get('description', '')}</td>
            <td style="padding: 8px; border: 1px solid #ddd;">{item.get('assigned_to_name', 'TBD')}</td>
            <td style="padding: 8px; border: 1px solid #ddd;">{item.get('due_date', 'TBD')}</td>
            <td style="padding: 8px; border: 1px solid #ddd;">{item.get('priority', 'Medium').upper()}</td>
        </tr>
        """
    
    meeting_date = meeting.get('meeting_date')
    if isinstance(meeting_date, str):
        meeting_date = datetime.fromisoformat(meeting_date)
    
    next_meeting = meeting.get('next_meeting_date')
    if next_meeting and isinstance(next_meeting, str):
        next_meeting = datetime.fromisoformat(next_meeting)
    
    email_body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto;">
        <h2 style="color: #333;">Minutes of Meeting</h2>
        
        <div style="background: #f5f5f5; padding: 15px; border-radius: 5px; margin-bottom: 20px;">
            <p><strong>Meeting Title:</strong> {meeting.get('title', 'Meeting')}</p>
            <p><strong>Project:</strong> {project.get('name', 'N/A') if project else 'N/A'}</p>
            <p><strong>Date:</strong> {meeting_date.strftime('%B %d, %Y %H:%M') if meeting_date else 'N/A'}</p>
            <p><strong>Mode:</strong> {meeting.get('mode', '').replace('_', ' ').title()}</p>
            <p><strong>Duration:</strong> {meeting.get('duration_minutes', 'N/A')} minutes</p>
            <p><strong>Attendees:</strong> {', '.join(meeting.get('attendee_names', []))}</p>
        </div>
        
        {'<h3>Agenda</h3><ul>' + agenda_html + '</ul>' if agenda_html else ''}
        
        {'<h3>Discussion Points</h3><ul>' + discussion_html + '</ul>' if discussion_html else ''}
        
        {'<h3>Decisions Made</h3><ul>' + decisions_html + '</ul>' if decisions_html else ''}
        
        {'''<h3>Action Items</h3>
        <table style="width: 100%; border-collapse: collapse;">
            <thead>
                <tr style="background: #333; color: white;">
                    <th style="padding: 10px; text-align: left;">Action Item</th>
                    <th style="padding: 10px; text-align: left;">Assigned To</th>
                    <th style="padding: 10px; text-align: left;">Due Date</th>
                    <th style="padding: 10px; text-align: left;">Priority</th>
                </tr>
            </thead>
            <tbody>''' + action_items_html + '''</tbody>
        </table>''' if action_items_html else ''}
        
        {f'<p><strong>Next Meeting:</strong> {next_meeting.strftime("%B %d, %Y %H:%M")}</p>' if next_meeting else ''}
        
        <hr style="margin: 30px 0;">
        <p style="color: #666; font-size: 12px;">
            This is an automated email from D&V Business Consulting.<br>
            If you have any questions, please contact your account manager.
        </p>
    </body>
    </html>
    """
    
    # Queue email notification
    notification = {
        "id": str(uuid.uuid4()),
        "type": "mom_sent",
        "recipient_email": client_email,
        "recipient_name": client_name,
        "subject": f"Minutes of Meeting - {meeting.get('title', 'Meeting')} - {meeting_date.strftime('%B %d, %Y') if meeting_date else ''}",
        "body": email_body,
        "meeting_id": meeting_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "sent": False  # Email sending is mocked
    }
    
    await db.notifications.insert_one(notification)
    
    # Update meeting
    await db.meetings.update_one(
        {"id": meeting_id},
        {"$set": {
            "mom_sent_to_client": True,
            "mom_sent_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    return {
        "message": "MOM sent to client (notification queued)",
        "client_email": client_email,
        "client_name": client_name
    }


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


@api_router.get("/stats/dashboard")
async def get_dashboard_stats(current_user: User = Depends(get_current_user)):
    query = {}
    if current_user.role != UserRole.ADMIN:
        query['$or'] = [{"assigned_to": current_user.id}, {"created_by": current_user.id}]
    
    total_leads = await db.leads.count_documents(query)
    new_leads = await db.leads.count_documents({**query, "status": LeadStatus.NEW})
    qualified_leads = await db.leads.count_documents({**query, "status": LeadStatus.QUALIFIED})
    closed_deals = await db.leads.count_documents({**query, "status": LeadStatus.CLOSED})
    
    project_query = {}
    if current_user.role != UserRole.ADMIN:
        project_query['$or'] = [{"assigned_team": current_user.id}, {"created_by": current_user.id}]
    
    active_projects = await db.projects.count_documents({**project_query, "status": "active"})
    
    return {
        "total_leads": total_leads,
        "new_leads": new_leads,
        "qualified_leads": qualified_leads,
        "closed_deals": closed_deals,
        "active_projects": active_projects
    }


# ============== Domain-Specific Dashboard Stats ==============

@api_router.get("/stats/sales-dashboard")
async def get_sales_dashboard_stats(current_user: User = Depends(get_current_user)):
    """Sales-specific dashboard stats - pipeline, conversions, revenue"""
    # Get user's leads or all if admin
    lead_query = {}
    if current_user.role not in ['admin', 'manager']:
        lead_query['$or'] = [{"assigned_to": current_user.id}, {"created_by": current_user.id}]
    
    # Lead pipeline stats
    total_leads = await db.leads.count_documents(lead_query)
    new_leads = await db.leads.count_documents({**lead_query, "status": "new"})
    contacted_leads = await db.leads.count_documents({**lead_query, "status": "contacted"})
    qualified_leads = await db.leads.count_documents({**lead_query, "status": "qualified"})
    proposal_leads = await db.leads.count_documents({**lead_query, "status": "proposal"})
    closed_leads = await db.leads.count_documents({**lead_query, "status": "closed"})
    
    # My Clients (sales person specific)
    my_clients = await db.clients.count_documents({"sales_person_id": current_user.id, "is_active": True})
    total_clients = await db.clients.count_documents({"is_active": True})
    
    # Quotations and Agreements
    quot_query = {} if current_user.role in ['admin', 'manager'] else {"created_by": current_user.id}
    pending_quotations = await db.quotations.count_documents({**quot_query, "status": "pending"})
    pending_agreements = await db.agreements.count_documents({**quot_query, "status": "pending_approval"})
    approved_agreements = await db.agreements.count_documents({**quot_query, "status": "approved"})
    
    # Kickoff requests sent
    kickoff_query = {} if current_user.role in ['admin', 'manager'] else {"requested_by": current_user.id}
    pending_kickoffs = await db.kickoff_requests.count_documents({**kickoff_query, "status": "pending"})
    
    # Revenue from closed deals (this month)
    from datetime import timedelta
    month_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # Calculate total revenue from clients
    pipeline = [
        {"$match": {"sales_person_id": current_user.id} if current_user.role not in ['admin', 'manager'] else {}},
        {"$unwind": {"path": "$revenue_history", "preserveNullAndEmptyArrays": False}},
        {"$group": {"_id": None, "total": {"$sum": "$revenue_history.amount"}}}
    ]
    revenue_result = await db.clients.aggregate(pipeline).to_list(1)
    total_revenue = revenue_result[0]['total'] if revenue_result else 0
    
    return {
        "pipeline": {
            "total": total_leads,
            "new": new_leads,
            "contacted": contacted_leads,
            "qualified": qualified_leads,
            "proposal": proposal_leads,
            "closed": closed_leads
        },
        "clients": {
            "my_clients": my_clients,
            "total_clients": total_clients
        },
        "quotations": {
            "pending": pending_quotations
        },
        "agreements": {
            "pending": pending_agreements,
            "approved": approved_agreements
        },
        "kickoffs": {
            "pending": pending_kickoffs
        },
        "revenue": {
            "total": total_revenue
        },
        "conversion_rate": round((closed_leads / total_leads * 100) if total_leads > 0 else 0, 1)
    }


@api_router.get("/stats/consulting-dashboard")
async def get_consulting_dashboard_stats(current_user: User = Depends(get_current_user)):
    """Consulting-specific dashboard stats - delivery, efficiency, workload"""
    is_pm = current_user.role in ['admin', 'project_manager', 'manager']
    
    # Projects stats
    if is_pm:
        active_projects = await db.projects.count_documents({"status": "active"})
        completed_projects = await db.projects.count_documents({"status": "completed"})
        on_hold_projects = await db.projects.count_documents({"status": "on_hold"})
    else:
        # For consultants - only their assigned projects
        active_projects = await db.consultant_assignments.count_documents({
            "consultant_id": current_user.id, "is_active": True
        })
        completed_projects = 0  # Will be calculated from assignments
        on_hold_projects = 0
    
    # Meetings stats
    meeting_pipeline = [
        {"$match": {"type": "consulting", "is_delivered": True}},
        {"$group": {"_id": None, "total": {"$sum": 1}}}
    ]
    delivered_meetings = await db.meetings.aggregate(meeting_pipeline).to_list(1)
    total_delivered = delivered_meetings[0]['total'] if delivered_meetings else 0
    
    # Pending meetings
    pending_meetings = await db.meetings.count_documents({"type": "consulting", "is_delivered": False})
    
    # Total committed from projects
    commit_pipeline = [
        {"$match": {"status": "active"}},
        {"$group": {"_id": None, "total": {"$sum": "$total_meetings_committed"}}}
    ]
    committed_result = await db.projects.aggregate(commit_pipeline).to_list(1)
    total_committed = committed_result[0]['total'] if committed_result else 0
    
    # Efficiency score (meetings delivered / committed)
    efficiency = round((total_delivered / total_committed * 100) if total_committed > 0 else 0, 1)
    
    # Incoming kickoff requests (for PM)
    incoming_kickoffs = 0
    if is_pm:
        incoming_kickoffs = await db.kickoff_requests.count_documents({"status": "pending"})
    
    # Consultant workload
    consultants_pipeline = [
        {"$match": {"is_active": True}},
        {"$group": {"_id": "$consultant_id", "projects": {"$sum": 1}}}
    ]
    workload = await db.consultant_assignments.aggregate(consultants_pipeline).to_list(100)
    
    # Average workload
    avg_workload = round(sum([w['projects'] for w in workload]) / len(workload), 1) if workload else 0
    
    # Handover alerts (projects at risk)
    at_risk_projects = await db.projects.count_documents({
        "status": "active",
        "$expr": {"$lt": ["$total_meetings_delivered", {"$multiply": ["$total_meetings_committed", 0.3]}]}
    })
    
    return {
        "projects": {
            "active": active_projects,
            "completed": completed_projects,
            "on_hold": on_hold_projects,
            "at_risk": at_risk_projects
        },
        "meetings": {
            "delivered": total_delivered,
            "pending": pending_meetings,
            "committed": total_committed
        },
        "efficiency_score": efficiency,
        "incoming_kickoffs": incoming_kickoffs,
        "consultant_workload": {
            "average": avg_workload,
            "distribution": workload[:10]  # Top 10
        }
    }


@api_router.get("/stats/hr-dashboard")
async def get_hr_dashboard_stats(current_user: User = Depends(get_current_user)):
    """HR-specific dashboard stats - employees, attendance, leaves, payroll"""
    if current_user.role not in ['admin', 'hr_manager', 'hr_executive', 'manager']:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Employee stats
    total_employees = await db.employees.count_documents({"is_active": True})
    new_this_month = await db.employees.count_documents({
        "is_active": True,
        "date_of_joining": {"$gte": datetime.now(timezone.utc).replace(day=1).isoformat()}
    })
    
    # Department breakdown
    dept_pipeline = [
        {"$match": {"is_active": True}},
        {"$group": {"_id": "$department", "count": {"$sum": 1}}}
    ]
    by_department = await db.employees.aggregate(dept_pipeline).to_list(20)
    
    # Today's attendance
    today = datetime.now(timezone.utc).date().isoformat()
    present_today = await db.attendance.count_documents({"date": today, "status": "present"})
    absent_today = await db.attendance.count_documents({"date": today, "status": "absent"})
    wfh_today = await db.attendance.count_documents({"date": today, "status": "wfh"})
    
    # Pending leave requests
    pending_leaves = await db.leave_requests.count_documents({"status": "pending"})
    
    # Pending expense approvals
    pending_expenses = await db.expenses.count_documents({"status": "pending"})
    
    # Payroll status (current month)
    current_month = datetime.now(timezone.utc).month
    current_year = datetime.now(timezone.utc).year
    payroll_processed = await db.salary_slips.count_documents({
        "month": current_month, "year": current_year
    })
    
    return {
        "employees": {
            "total": total_employees,
            "new_this_month": new_this_month,
            "by_department": {item['_id'] or 'Unassigned': item['count'] for item in by_department}
        },
        "attendance": {
            "present_today": present_today,
            "absent_today": absent_today,
            "wfh_today": wfh_today,
            "attendance_rate": round((present_today / total_employees * 100) if total_employees > 0 else 0, 1)
        },
        "leaves": {
            "pending_requests": pending_leaves
        },
        "expenses": {
            "pending_approvals": pending_expenses
        },
        "payroll": {
            "processed_this_month": payroll_processed,
            "pending": total_employees - payroll_processed
        }
    }


# ============== Kickoff Request Endpoints ==============

@api_router.post("/kickoff-requests")
async def create_kickoff_request(
    request: KickoffRequestCreate,
    current_user: User = Depends(get_current_user)
):
    """Create a kickoff request to hand off to consulting team"""
    if current_user.role not in ['admin', 'executive', 'account_manager', 'manager']:
        raise HTTPException(status_code=403, detail="Not authorized to create kickoff requests")
    
    kickoff = KickoffRequest(
        **request.model_dump(),
        requested_by=current_user.id,
        requested_by_name=current_user.full_name
    )
    
    doc = kickoff.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    if doc.get('expected_start_date'):
        doc['expected_start_date'] = doc['expected_start_date'].isoformat()
    
    await db.kickoff_requests.insert_one(doc)
    
    # Create notification for assigned PM
    if request.assigned_pm_id:
        notification = {
            "id": str(uuid.uuid4()),
            "user_id": request.assigned_pm_id,
            "type": "kickoff_request",
            "title": "New Kickoff Request",
            "message": f"New project kickoff request: {request.project_name} from {current_user.full_name}",
            "reference_id": kickoff.id,
            "is_read": False,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.notifications.insert_one(notification)
    
    return {"message": "Kickoff request created", "id": kickoff.id}


@api_router.get("/kickoff-requests")
async def get_kickoff_requests(
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get kickoff requests - for PM to see incoming, for sales to see their requests"""
    query = {}
    
    # Filter by status
    if status:
        query['status'] = status
    
    # Access control
    if current_user.role in ['project_manager']:
        # PM sees requests assigned to them or unassigned
        query['$or'] = [
            {"assigned_pm_id": current_user.id},
            {"assigned_pm_id": None}
        ]
    elif current_user.role not in ['admin', 'manager']:
        # Sales team sees their own requests
        query['requested_by'] = current_user.id
    
    requests = await db.kickoff_requests.find(query, {"_id": 0}).sort("created_at", -1).to_list(100)
    return requests


@api_router.get("/kickoff-requests/{request_id}")
async def get_kickoff_request(
    request_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get a specific kickoff request"""
    request = await db.kickoff_requests.find_one({"id": request_id}, {"_id": 0})
    if not request:
        raise HTTPException(status_code=404, detail="Kickoff request not found")
    return request


@api_router.get("/kickoff-requests/{request_id}/details")
async def get_kickoff_request_details(
    request_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get detailed kickoff request with SOW and team deployment from the parent Agreement.
    
    Note: Pricing/costing data is hidden from consulting roles (PM, consultants).
    Only Sales and Admin can see financial information.
    """
    kickoff = await db.kickoff_requests.find_one({"id": request_id}, {"_id": 0})
    if not kickoff:
        raise HTTPException(status_code=404, detail="Kickoff request not found")
    
    # Determine if user can see financial data (only sales/admin roles)
    can_see_financials = current_user.role in ['admin', 'executive', 'account_manager']
    
    # Get the agreement details
    agreement = None
    sow = None
    lead = None
    meetings = []
    team_deployment = []
    
    if kickoff.get('agreement_id'):
        agreement = await db.agreements.find_one({"id": kickoff['agreement_id']}, {"_id": 0})
        
        if agreement:
            # Get the SOW linked to this agreement
            if agreement.get('sow_id'):
                sow = await db.sow.find_one({"id": agreement['sow_id']}, {"_id": 0})
            
            # Get the lead info (limited for consulting)
            if agreement.get('lead_id'):
                lead_projection = {"_id": 0}
                lead = await db.leads.find_one({"id": agreement['lead_id']}, lead_projection)
            
            # Get team deployment from agreement
            team_deployment = agreement.get('team_deployment', [])
            
            # Remove financial/pricing data from agreement for consulting roles
            if not can_see_financials and agreement:
                # Remove sensitive financial fields
                sensitive_fields = [
                    'quotation_id', 'pricing_plan_id', 'payment_terms', 
                    'payment_conditions', 'total_value', 'base_amount',
                    'discount_percentage', 'gst_amount', 'grand_total'
                ]
                for field in sensitive_fields:
                    agreement.pop(field, None)
    
    # Get any sales meetings related to this lead (hide financial notes)
    if kickoff.get('lead_id'):
        meetings = await db.meetings.find(
            {"lead_id": kickoff['lead_id'], "type": "sales"},
            {"_id": 0}
        ).sort("meeting_date", -1).to_list(50)
    
    # Remove financial data from kickoff request for consulting roles
    if not can_see_financials:
        kickoff.pop('project_value', None)
    
    return {
        "kickoff_request": kickoff,
        "agreement": agreement,
        "sow": sow,
        "team_deployment": team_deployment,
        "lead": lead,
        "meetings": meetings,
        "can_see_financials": can_see_financials
    }


class KickoffRequestUpdate(BaseModel):
    expected_start_date: Optional[datetime] = None
    notes: Optional[str] = None
    assigned_pm_id: Optional[str] = None
    assigned_pm_name: Optional[str] = None


@api_router.put("/kickoff-requests/{request_id}")
async def update_kickoff_request(
    request_id: str,
    update_data: KickoffRequestUpdate,
    current_user: User = Depends(get_current_user)
):
    """Update kickoff request - PM can edit kickoff date before accepting"""
    if current_user.role not in ['admin', 'project_manager', 'manager']:
        raise HTTPException(status_code=403, detail="Not authorized to update kickoff requests")
    
    kickoff = await db.kickoff_requests.find_one({"id": request_id}, {"_id": 0})
    if not kickoff:
        raise HTTPException(status_code=404, detail="Kickoff request not found")
    
    if kickoff['status'] not in ['pending', 'returned']:
        raise HTTPException(status_code=400, detail="Can only update pending or returned requests")
    
    update_fields = {"updated_at": datetime.now(timezone.utc).isoformat()}
    
    if update_data.expected_start_date:
        update_fields['expected_start_date'] = update_data.expected_start_date.isoformat()
    if update_data.notes is not None:
        update_fields['notes'] = update_data.notes
    if update_data.assigned_pm_id:
        update_fields['assigned_pm_id'] = update_data.assigned_pm_id
        update_fields['assigned_pm_name'] = update_data.assigned_pm_name
    
    await db.kickoff_requests.update_one(
        {"id": request_id},
        {"$set": update_fields}
    )
    
    # Return updated kickoff
    updated = await db.kickoff_requests.find_one({"id": request_id}, {"_id": 0})
    return updated


class KickoffReturnRequest(BaseModel):
    reason: str
    return_notes: Optional[str] = None


@api_router.post("/kickoff-requests/{request_id}/return")
async def return_kickoff_request(
    request_id: str,
    return_data: KickoffReturnRequest,
    current_user: User = Depends(get_current_user)
):
    """Return a kickoff request back to the sales person with feedback"""
    if current_user.role not in ['admin', 'project_manager', 'manager']:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    kickoff = await db.kickoff_requests.find_one({"id": request_id}, {"_id": 0})
    if not kickoff:
        raise HTTPException(status_code=404, detail="Kickoff request not found")
    
    if kickoff['status'] != 'pending':
        raise HTTPException(status_code=400, detail="Can only return pending requests")
    
    await db.kickoff_requests.update_one(
        {"id": request_id},
        {"$set": {
            "status": "returned",
            "return_reason": return_data.reason,
            "return_notes": return_data.return_notes,
            "returned_by": current_user.id,
            "returned_by_name": current_user.full_name,
            "returned_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    # Notify the requester
    notification = {
        "id": str(uuid.uuid4()),
        "user_id": kickoff['requested_by'],
        "type": "kickoff_returned",
        "title": "Kickoff Request Returned",
        "message": f"Your kickoff request for '{kickoff['project_name']}' has been returned by {current_user.full_name}. Reason: {return_data.reason}",
        "reference_id": request_id,
        "is_read": False,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.notifications.insert_one(notification)
    
    return {"message": "Kickoff request returned to sender"}


@api_router.post("/kickoff-requests/{request_id}/resubmit")
async def resubmit_kickoff_request(
    request_id: str,
    current_user: User = Depends(get_current_user)
):
    """Resubmit a returned kickoff request (Sales side)"""
    if current_user.role not in ['admin', 'executive', 'account_manager', 'manager']:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    kickoff = await db.kickoff_requests.find_one({"id": request_id}, {"_id": 0})
    if not kickoff:
        raise HTTPException(status_code=404, detail="Kickoff request not found")
    
    if kickoff['status'] != 'returned':
        raise HTTPException(status_code=400, detail="Can only resubmit returned requests")
    
    # Verify the requester owns this request (unless admin)
    if current_user.role not in ['admin', 'manager'] and kickoff['requested_by'] != current_user.id:
        raise HTTPException(status_code=403, detail="Can only resubmit your own requests")
    
    await db.kickoff_requests.update_one(
        {"id": request_id},
        {"$set": {
            "status": "pending",
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    # Notify the PM
    if kickoff.get('assigned_pm_id'):
        notification = {
            "id": str(uuid.uuid4()),
            "user_id": kickoff['assigned_pm_id'],
            "type": "kickoff_resubmitted",
            "title": "Kickoff Request Resubmitted",
            "message": f"Kickoff request for '{kickoff['project_name']}' has been resubmitted by {current_user.full_name}",
            "reference_id": request_id,
            "is_read": False,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.notifications.insert_one(notification)
    
    return {"message": "Kickoff request resubmitted"}


@api_router.post("/kickoff-requests/{request_id}/accept")
async def accept_kickoff_request(
    request_id: str,
    current_user: User = Depends(get_current_user)
):
    """Accept a kickoff request and create a project"""
    if current_user.role not in ['admin', 'project_manager', 'manager']:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    kickoff = await db.kickoff_requests.find_one({"id": request_id}, {"_id": 0})
    if not kickoff:
        raise HTTPException(status_code=404, detail="Kickoff request not found")
    
    if kickoff['status'] != 'pending':
        raise HTTPException(status_code=400, detail="Request already processed")
    
    # Create project from kickoff request
    project = Project(
        name=kickoff['project_name'],
        client_name=kickoff['client_name'],
        lead_id=kickoff.get('lead_id'),
        agreement_id=kickoff['agreement_id'],
        project_type=kickoff.get('project_type', 'mixed'),
        start_date=datetime.fromisoformat(kickoff['expected_start_date']) if kickoff.get('expected_start_date') else datetime.now(timezone.utc),
        total_meetings_committed=kickoff.get('total_meetings', 0),
        project_value=kickoff.get('project_value'),
        notes=kickoff.get('notes'),
        created_by=current_user.id
    )
    
    project_doc = project.model_dump()
    project_doc['created_at'] = project_doc['created_at'].isoformat()
    project_doc['updated_at'] = project_doc['updated_at'].isoformat()
    project_doc['start_date'] = project_doc['start_date'].isoformat()
    if project_doc.get('end_date'):
        project_doc['end_date'] = project_doc['end_date'].isoformat()
    
    await db.projects.insert_one(project_doc)
    
    # Update kickoff request
    await db.kickoff_requests.update_one(
        {"id": request_id},
        {"$set": {
            "status": "converted",
            "project_id": project.id,
            "accepted_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    # Notify the requester
    notification = {
        "id": str(uuid.uuid4()),
        "user_id": kickoff['requested_by'],
        "type": "kickoff_accepted",
        "title": "Kickoff Request Accepted",
        "message": f"Project '{kickoff['project_name']}' has been created by {current_user.full_name}",
        "reference_id": project.id,
        "is_read": False,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.notifications.insert_one(notification)
    
    return {"message": "Kickoff accepted, project created", "project_id": project.id}


@api_router.post("/kickoff-requests/{request_id}/reject")
async def reject_kickoff_request(
    request_id: str,
    reason: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Reject a kickoff request"""
    if current_user.role not in ['admin', 'project_manager', 'manager']:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    kickoff = await db.kickoff_requests.find_one({"id": request_id}, {"_id": 0})
    if not kickoff:
        raise HTTPException(status_code=404, detail="Kickoff request not found")
    
    await db.kickoff_requests.update_one(
        {"id": request_id},
        {"$set": {
            "status": "rejected",
            "notes": reason or kickoff.get('notes', ''),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    return {"message": "Kickoff request rejected"}


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
    if current_user.role == UserRole.MANAGER:
        raise HTTPException(status_code=403, detail="Managers can only view and download")
    
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
    if current_user.role == UserRole.MANAGER:
        raise HTTPException(status_code=403, detail="Managers can only view and download")
    
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
    if current_user.role == UserRole.MANAGER:
        raise HTTPException(status_code=403, detail="Managers can only view and download")
    
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
    if current_user.role == UserRole.MANAGER:
        raise HTTPException(status_code=403, detail="Managers can only view and download")
    
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

@api_router.post("/quotations", response_model=Quotation)
async def create_quotation(quotation_create: QuotationCreate, current_user: User = Depends(get_current_user)):
    if current_user.role == UserRole.MANAGER:
        raise HTTPException(status_code=403, detail="Managers can only view and download")
    
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
    if current_user.role == UserRole.MANAGER:
        raise HTTPException(status_code=403, detail="Managers can only view and download")
    
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
    if current_user.role == UserRole.MANAGER:
        raise HTTPException(status_code=403, detail="Managers can only view and download")
    
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
    if current_user.role == UserRole.MANAGER:
        raise HTTPException(status_code=403, detail="Managers can only view and download")
    
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
    if current_user.role == UserRole.MANAGER:
        raise HTTPException(status_code=403, detail="Managers can only view and download")
    
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
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER]:
        raise HTTPException(status_code=403, detail="Only admins and managers can view consultant list")
    
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
    """Assign a consultant to a project"""
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER]:
        raise HTTPException(status_code=403, detail="Only admins and managers can assign consultants")
    
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
    
    return {"message": "Consultant assigned successfully", "assignment_id": new_assignment.id}

@api_router.patch("/projects/{project_id}/change-consultant")
async def change_consultant(
    project_id: str,
    old_consultant_id: str,
    new_consultant_id: str,
    current_user: User = Depends(get_current_user)
):
    """Change consultant on a project (before start date)"""
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER]:
        raise HTTPException(status_code=403, detail="Only admins and managers can change consultants")
    
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
    """Remove consultant from project"""
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER]:
        raise HTTPException(status_code=403, detail="Only admins and managers can unassign consultants")
    
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
        "projects": {"create": False, "read": True, "update": False, "delete": False},
        "tasks": {"create": False, "read": True, "update": False, "delete": False},
        "consultants": {"create": False, "read": True, "update": False, "delete": False},
        "users": {"create": False, "read": True, "update": False, "delete": False, "manage_roles": False},
        "reports": {"view": False, "export": False}
    },
    "hr_manager": {
        "leads": {"create": False, "read": False, "update": False, "delete": False},
        "pricing_plans": {"create": False, "read": False, "update": False, "delete": False},
        "sow": {"create": False, "read": False, "update": False, "delete": False, "freeze": False},
        "quotations": {"create": False, "read": False, "update": False, "delete": False},
        "agreements": {"create": False, "read": False, "update": False, "delete": False, "approve": False},
        "projects": {"create": False, "read": True, "update": False, "delete": False},
        "tasks": {"create": False, "read": True, "update": False, "delete": False},
        "consultants": {"create": True, "read": True, "update": True, "delete": False},
        "users": {"create": True, "read": True, "update": True, "delete": False, "manage_roles": False},
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

@api_router.post("/leave-requests")
async def create_leave_request(
    leave_data: LeaveRequestCreate,
    current_user: User = Depends(get_current_user)
):
    """Create a leave request. Manager's own leave escalates to their reporting manager + admin."""
    employee = await db.employees.find_one({"user_id": current_user.id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=400, detail="Employee record not found. Please contact HR.")
    
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
        "end_date": leave_data.end_date.isoformat(),
        "days": days,
        "reason": leave_data.reason,
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.leave_requests.insert_one(leave_request)
    
    # Create approval request — manager's leave escalates to their RM + admin
    approval = await create_approval_request(
        approval_type=ApprovalType.LEAVE_REQUEST,
        reference_id=leave_request['id'],
        reference_title=f"{leave_data.leave_type.replace('_', ' ').title()} - {days} day(s)",
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

# ==================== EMPLOYEES MODULE ====================

class EmploymentType(str):
    FULL_TIME = "full_time"
    CONTRACT = "contract"
    INTERN = "intern"
    PART_TIME = "part_time"

class BankDetails(BaseModel):
    account_number: Optional[str] = None
    ifsc_code: Optional[str] = None
    bank_name: Optional[str] = None
    branch: Optional[str] = None
    account_holder_name: Optional[str] = None

class EmployeeDocument(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    document_type: str  # id_proof, offer_letter, resume, contract, other
    filename: str
    original_filename: str
    file_size: int = 0
    uploaded_by: str
    uploaded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    description: Optional[str] = None

class LeaveBalance(BaseModel):
    casual_leave: int = 12
    sick_leave: int = 6
    earned_leave: int = 15
    used_casual: int = 0
    used_sick: int = 0
    used_earned: int = 0

class Employee(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    employee_id: str  # Company employee ID like EMP001
    
    # Basic Info
    first_name: str
    last_name: str
    email: EmailStr
    phone: Optional[str] = None
    personal_email: Optional[str] = None
    
    # Work Info
    department: Optional[str] = None
    designation: Optional[str] = None
    employment_type: str = EmploymentType.FULL_TIME
    joining_date: Optional[datetime] = None
    
    # Reporting
    reporting_manager_id: Optional[str] = None  # Employee ID of manager
    reporting_manager_name: Optional[str] = None
    
    # HR Details
    salary: Optional[float] = None
    bank_details: Optional[BankDetails] = None
    leave_balance: Optional[LeaveBalance] = None
    
    # Documents
    documents: List[dict] = []
    
    # System Link
    user_id: Optional[str] = None  # Link to user account (optional)
    role: Optional[str] = None  # User role if linked
    
    # Status
    is_active: bool = True
    termination_date: Optional[datetime] = None
    
    # Meta
    created_by: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class EmployeeCreate(BaseModel):
    employee_id: str
    first_name: str
    last_name: str
    email: EmailStr
    phone: Optional[str] = None
    personal_email: Optional[str] = None
    department: Optional[str] = None
    designation: Optional[str] = None
    employment_type: Optional[str] = EmploymentType.FULL_TIME
    joining_date: Optional[datetime] = None
    reporting_manager_id: Optional[str] = None
    salary: Optional[float] = None
    bank_details: Optional[BankDetails] = None

class EmployeeUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    personal_email: Optional[str] = None
    department: Optional[str] = None
    designation: Optional[str] = None
    employment_type: Optional[str] = None
    joining_date: Optional[datetime] = None
    reporting_manager_id: Optional[str] = None
    salary: Optional[float] = None
    bank_details: Optional[BankDetails] = None
    leave_balance: Optional[LeaveBalance] = None
    is_active: Optional[bool] = None
    termination_date: Optional[datetime] = None

# Helper to check HR access
def has_hr_access(user_role: str) -> bool:
    return user_role in [UserRole.ADMIN, UserRole.HR_MANAGER]

def has_hr_view_access(user_role: str) -> bool:
    return user_role in [UserRole.ADMIN, UserRole.HR_MANAGER, UserRole.HR_EXECUTIVE]

@api_router.get("/employees")
async def get_all_employees(
    department: Optional[str] = None,
    employment_type: Optional[str] = None,
    is_active: Optional[bool] = True,
    current_user: User = Depends(get_current_user)
):
    """Get all employees (HR access required for sensitive data)"""
    query = {}
    if department:
        query['department'] = department
    if employment_type:
        query['employment_type'] = employment_type
    if is_active is not None:
        query['is_active'] = is_active
    
    employees = await db.employees.find(query, {"_id": 0}).to_list(1000)
    
    # If not HR, hide sensitive data
    if not has_hr_view_access(current_user.role):
        for emp in employees:
            emp.pop('salary', None)
            emp.pop('bank_details', None)
            emp.pop('personal_email', None)
    
    # Parse dates
    for emp in employees:
        if isinstance(emp.get('created_at'), str):
            emp['created_at'] = datetime.fromisoformat(emp['created_at'])
        if isinstance(emp.get('updated_at'), str):
            emp['updated_at'] = datetime.fromisoformat(emp['updated_at'])
        if emp.get('joining_date') and isinstance(emp['joining_date'], str):
            emp['joining_date'] = datetime.fromisoformat(emp['joining_date'])
    
    return employees

@api_router.get("/employees/consultants")
async def get_employees_with_consultant_designation(
    current_user: User = Depends(get_current_user)
):
    """Get employees with designation containing 'Consultant' - for PM selection in kickoff flow"""
    # Query for employees with designation containing 'Consultant' (case-insensitive)
    query = {
        "is_active": True,
        "designation": {"$regex": "consultant", "$options": "i"}
    }
    
    employees = await db.employees.find(
        query,
        {"_id": 0, "id": 1, "first_name": 1, "last_name": 1, "designation": 1, 
         "department": 1, "email": 1, "user_id": 1}
    ).to_list(500)
    
    return employees

@api_router.post("/employees")
async def create_employee(
    employee_create: EmployeeCreate,
    current_user: User = Depends(get_current_user)
):
    """Create a new employee (Admin/HR Manager only)"""
    if not has_hr_access(current_user.role):
        raise HTTPException(status_code=403, detail="Only Admin/HR Manager can create employees")
    
    # Check if employee_id already exists
    existing = await db.employees.find_one({"employee_id": employee_create.employee_id})
    if existing:
        raise HTTPException(status_code=400, detail="Employee ID already exists")
    
    # Check if email already exists
    existing_email = await db.employees.find_one({"email": employee_create.email})
    if existing_email:
        raise HTTPException(status_code=400, detail="Email already exists")
    
    # Get reporting manager name if provided
    reporting_manager_name = None
    if employee_create.reporting_manager_id:
        manager = await db.employees.find_one({"id": employee_create.reporting_manager_id}, {"_id": 0})
        if manager:
            reporting_manager_name = f"{manager['first_name']} {manager['last_name']}"
    
    # Check if user exists with this email and link
    user = await db.users.find_one({"email": employee_create.email}, {"_id": 0})
    user_id = user.get('id') if user else None
    user_role = user.get('role') if user else None
    
    employee = Employee(
        **employee_create.model_dump(),
        reporting_manager_name=reporting_manager_name,
        user_id=user_id,
        role=user_role,
        leave_balance=LeaveBalance().model_dump(),
        created_by=current_user.id
    )
    
    doc = employee.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    if doc['joining_date']:
        doc['joining_date'] = doc['joining_date'].isoformat()
    if doc['termination_date']:
        doc['termination_date'] = doc['termination_date'].isoformat()
    
    await db.employees.insert_one(doc)
    
    return {"message": "Employee created successfully", "employee_id": employee.id, "emp_id": employee.employee_id}

@api_router.get("/employees/{employee_id}")
async def get_employee(
    employee_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get employee details"""
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # If not HR, hide sensitive data (unless viewing own profile)
    if not has_hr_view_access(current_user.role) and employee.get('user_id') != current_user.id:
        employee.pop('salary', None)
        employee.pop('bank_details', None)
        employee.pop('personal_email', None)
    
    return employee

@api_router.patch("/employees/{employee_id}")
async def update_employee(
    employee_id: str,
    employee_update: EmployeeUpdate,
    current_user: User = Depends(get_current_user)
):
    """Update employee (Admin/HR Manager only)"""
    if not has_hr_access(current_user.role):
        raise HTTPException(status_code=403, detail="Only Admin/HR Manager can update employees")
    
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    update_data = employee_update.model_dump(exclude_unset=True)
    
    # Get reporting manager name if updating
    if 'reporting_manager_id' in update_data and update_data['reporting_manager_id']:
        manager = await db.employees.find_one({"id": update_data['reporting_manager_id']}, {"_id": 0})
        if manager:
            update_data['reporting_manager_name'] = f"{manager['first_name']} {manager['last_name']}"
    
    # Handle dates
    if 'joining_date' in update_data and update_data['joining_date']:
        update_data['joining_date'] = update_data['joining_date'].isoformat()
    if 'termination_date' in update_data and update_data['termination_date']:
        update_data['termination_date'] = update_data['termination_date'].isoformat()
    
    # Handle nested objects
    if 'bank_details' in update_data and update_data['bank_details']:
        update_data['bank_details'] = update_data['bank_details'].model_dump() if hasattr(update_data['bank_details'], 'model_dump') else update_data['bank_details']
    if 'leave_balance' in update_data and update_data['leave_balance']:
        update_data['leave_balance'] = update_data['leave_balance'].model_dump() if hasattr(update_data['leave_balance'], 'model_dump') else update_data['leave_balance']
    
    update_data['updated_at'] = datetime.now(timezone.utc).isoformat()
    
    await db.employees.update_one(
        {"id": employee_id},
        {"$set": update_data}
    )
    
    return {"message": "Employee updated successfully"}

@api_router.delete("/employees/{employee_id}")
async def delete_employee(
    employee_id: str,
    current_user: User = Depends(get_current_user)
):
    """Soft delete employee (Admin only)"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only Admin can delete employees")
    
    result = await db.employees.update_one(
        {"id": employee_id},
        {"$set": {
            "is_active": False,
            "termination_date": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    return {"message": "Employee deactivated successfully"}

@api_router.post("/employees/{employee_id}/link-user")
async def link_employee_to_user(
    employee_id: str,
    user_id: str,
    current_user: User = Depends(get_current_user)
):
    """Link an employee to a user account (Admin/HR Manager only)"""
    if not has_hr_access(current_user.role):
        raise HTTPException(status_code=403, detail="Only Admin/HR Manager can link users")
    
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if user is already linked to another employee
    existing_link = await db.employees.find_one({"user_id": user_id, "id": {"$ne": employee_id}})
    if existing_link:
        raise HTTPException(status_code=400, detail="User is already linked to another employee")
    
    await db.employees.update_one(
        {"id": employee_id},
        {"$set": {
            "user_id": user_id,
            "role": user.get('role'),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    return {"message": "Employee linked to user successfully"}

@api_router.post("/employees/{employee_id}/unlink-user")
async def unlink_employee_from_user(
    employee_id: str,
    current_user: User = Depends(get_current_user)
):
    """Unlink an employee from user account (Admin/HR Manager only)"""
    if not has_hr_access(current_user.role):
        raise HTTPException(status_code=403, detail="Only Admin/HR Manager can unlink users")
    
    result = await db.employees.update_one(
        {"id": employee_id},
        {"$set": {
            "user_id": None,
            "role": None,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    return {"message": "Employee unlinked from user successfully"}

# Document upload for employees
EMPLOYEE_UPLOAD_DIR = "/app/uploads/employees"
os.makedirs(EMPLOYEE_UPLOAD_DIR, exist_ok=True)

class EmployeeDocumentUpload(BaseModel):
    document_type: str  # id_proof, offer_letter, resume, contract, other
    filename: str
    file_data: str  # Base64 encoded
    description: Optional[str] = None

@api_router.post("/employees/{employee_id}/documents")
async def upload_employee_document(
    employee_id: str,
    document: EmployeeDocumentUpload,
    current_user: User = Depends(get_current_user)
):
    """Upload document for employee (Admin/HR Manager only)"""
    if not has_hr_access(current_user.role):
        raise HTTPException(status_code=403, detail="Only Admin/HR Manager can upload documents")
    
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    import base64
    
    try:
        file_data = base64.b64decode(document.file_data)
        file_size = len(file_data)
        
        file_ext = document.filename.split('.')[-1] if '.' in document.filename else 'bin'
        stored_filename = f"{employee_id}_{str(uuid.uuid4())[:8]}.{file_ext}"
        file_path = os.path.join(EMPLOYEE_UPLOAD_DIR, stored_filename)
        
        with open(file_path, 'wb') as f:
            f.write(file_data)
        
        doc_record = {
            "id": str(uuid.uuid4()),
            "document_type": document.document_type,
            "filename": stored_filename,
            "original_filename": document.filename,
            "file_size": file_size,
            "uploaded_by": current_user.id,
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
            "description": document.description
        }
        
        documents = employee.get('documents', [])
        documents.append(doc_record)
        
        await db.employees.update_one(
            {"id": employee_id},
            {"$set": {
                "documents": documents,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }}
        )
        
        return {"message": "Document uploaded successfully", "document_id": doc_record['id']}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload document: {str(e)}")

@api_router.get("/employees/{employee_id}/documents/{document_id}")
async def download_employee_document(
    employee_id: str,
    document_id: str,
    current_user: User = Depends(get_current_user)
):
    """Download employee document (HR access or own profile)"""
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Check access
    if not has_hr_view_access(current_user.role) and employee.get('user_id') != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view documents")
    
    import base64
    
    documents = employee.get('documents', [])
    doc = None
    for d in documents:
        if d.get('id') == document_id:
            doc = d
            break
    
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    file_path = os.path.join(EMPLOYEE_UPLOAD_DIR, doc['filename'])
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found on server")
    
    with open(file_path, 'rb') as f:
        file_data = base64.b64encode(f.read()).decode('utf-8')
    
    return {
        "filename": doc['original_filename'],
        "file_data": file_data,
        "file_type": doc.get('document_type')
    }

@api_router.delete("/employees/{employee_id}/documents/{document_id}")
async def delete_employee_document(
    employee_id: str,
    document_id: str,
    current_user: User = Depends(get_current_user)
):
    """Delete employee document (Admin/HR Manager only)"""
    if not has_hr_access(current_user.role):
        raise HTTPException(status_code=403, detail="Only Admin/HR Manager can delete documents")
    
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    documents = employee.get('documents', [])
    new_documents = [d for d in documents if d.get('id') != document_id]
    
    if len(documents) == len(new_documents):
        raise HTTPException(status_code=404, detail="Document not found")
    
    await db.employees.update_one(
        {"id": employee_id},
        {"$set": {
            "documents": new_documents,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    return {"message": "Document deleted successfully"}

@api_router.get("/employees/org-chart/hierarchy")
async def get_org_chart(current_user: User = Depends(get_current_user)):
    """Get organizational hierarchy for org chart"""
    employees = await db.employees.find({"is_active": True}, {"_id": 0}).to_list(1000)
    
    # Build hierarchy
    hierarchy = []
    employee_map = {emp['id']: emp for emp in employees}
    
    # Find root employees (no reporting manager)
    for emp in employees:
        if not emp.get('reporting_manager_id'):
            hierarchy.append({
                "id": emp['id'],
                "employee_id": emp['employee_id'],
                "name": f"{emp['first_name']} {emp['last_name']}",
                "designation": emp.get('designation'),
                "department": emp.get('department'),
                "email": emp['email'],
                "has_user_access": emp.get('user_id') is not None,
                "children": get_subordinates(emp['id'], employee_map)
            })
    
    return hierarchy

def get_subordinates(manager_id: str, employee_map: dict) -> list:
    """Recursively get subordinates for org chart"""
    subordinates = []
    for emp_id, emp in employee_map.items():
        if emp.get('reporting_manager_id') == manager_id:
            subordinates.append({
                "id": emp['id'],
                "employee_id": emp['employee_id'],
                "name": f"{emp['first_name']} {emp['last_name']}",
                "designation": emp.get('designation'),
                "department": emp.get('department'),
                "email": emp['email'],
                "has_user_access": emp.get('user_id') is not None,
                "children": get_subordinates(emp['id'], employee_map)
            })
    return subordinates

@api_router.get("/employees/{employee_id}/subordinates")
async def get_employee_subordinates(
    employee_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get direct subordinates of an employee"""
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    subordinates = await db.employees.find(
        {"reporting_manager_id": employee_id, "is_active": True},
        {"_id": 0}
    ).to_list(100)
    
    return subordinates

@api_router.post("/employees/sync-from-users")
async def sync_employees_from_users(
    current_user: User = Depends(get_current_user)
):
    """Create employee records for all existing users (Admin only)"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only Admin can sync employees")
    
    users = await db.users.find({"is_active": True}, {"_id": 0, "hashed_password": 0}).to_list(1000)
    
    created_count = 0
    skipped_count = 0
    
    for user in users:
        # Check if employee already exists for this user
        existing = await db.employees.find_one({"$or": [
            {"user_id": user['id']},
            {"email": user['email']}
        ]})
        
        if existing:
            # Update existing employee with user link if not linked
            if not existing.get('user_id'):
                await db.employees.update_one(
                    {"id": existing['id']},
                    {"$set": {
                        "user_id": user['id'],
                        "role": user.get('role'),
                        "updated_at": datetime.now(timezone.utc).isoformat()
                    }}
                )
            skipped_count += 1
            continue
        
        # Generate employee ID
        count = await db.employees.count_documents({})
        emp_id = f"EMP{str(count + 1).zfill(3)}"
        
        # Parse name
        name_parts = user.get('full_name', 'Unknown User').split(' ', 1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ''
        
        employee = {
            "id": str(uuid.uuid4()),
            "employee_id": emp_id,
            "first_name": first_name,
            "last_name": last_name,
            "email": user['email'],
            "phone": user.get('phone'),
            "department": user.get('department'),
            "designation": user.get('designation'),
            "employment_type": EmploymentType.FULL_TIME,
            "joining_date": user.get('created_at'),
            "reporting_manager_id": None,
            "reporting_manager_name": None,
            "salary": None,
            "bank_details": None,
            "leave_balance": LeaveBalance().model_dump(),
            "documents": [],
            "user_id": user['id'],
            "role": user.get('role'),
            "is_active": True,
            "termination_date": None,
            "created_by": current_user.id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        await db.employees.insert_one(employee)
        created_count += 1
    
    return {
        "message": f"Sync completed. Created: {created_count}, Skipped: {skipped_count}",
        "created": created_count,
        "skipped": skipped_count
    }

@api_router.get("/employees/departments/list")
async def get_departments(current_user: User = Depends(get_current_user)):
    """Get list of all departments"""
    departments = await db.employees.distinct("department")
    return [d for d in departments if d]

@api_router.get("/employees/stats/summary")
async def get_employee_stats(current_user: User = Depends(get_current_user)):
    """Get employee statistics"""
    if not has_hr_view_access(current_user.role):
        raise HTTPException(status_code=403, detail="HR access required")
    
    total = await db.employees.count_documents({"is_active": True})
    by_department = await db.employees.aggregate([
        {"$match": {"is_active": True}},
        {"$group": {"_id": "$department", "count": {"$sum": 1}}}
    ]).to_list(100)
    by_employment_type = await db.employees.aggregate([
        {"$match": {"is_active": True}},
        {"$group": {"_id": "$employment_type", "count": {"$sum": 1}}}
    ]).to_list(100)
    with_user_access = await db.employees.count_documents({"is_active": True, "user_id": {"$ne": None}})
    
    return {
        "total_employees": total,
        "with_user_access": with_user_access,
        "without_user_access": total - with_user_access,
        "by_department": {item['_id'] or 'Unassigned': item['count'] for item in by_department},
        "by_employment_type": {item['_id'] or 'Unknown': item['count'] for item in by_employment_type}
    }


# ==================== CLIENT MASTER ====================

class ClientContact(BaseModel):
    """Single Point of Contact (SPOC) for a client"""
    name: str
    designation: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    is_primary: bool = False

class RevenueRecord(BaseModel):
    """Revenue history record"""
    year: int
    quarter: Optional[int] = None  # 1-4, or None for annual
    amount: float
    currency: str = "INR"
    notes: Optional[str] = None

class Client(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    company_name: str
    industry: Optional[str] = None
    location: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = "India"
    address: Optional[str] = None
    website: Optional[str] = None
    contacts: List[ClientContact] = []
    revenue_history: List[RevenueRecord] = []
    business_start_date: Optional[datetime] = None
    sales_person_id: Optional[str] = None  # User ID of sales person who closed the deal
    sales_person_name: Optional[str] = None
    lead_id: Optional[str] = None  # Link to original lead
    agreement_id: Optional[str] = None  # Link to agreement
    notes: Optional[str] = None
    is_active: bool = True
    created_by: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ClientCreate(BaseModel):
    company_name: str
    industry: Optional[str] = None
    location: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = "India"
    address: Optional[str] = None
    website: Optional[str] = None
    contacts: List[ClientContact] = []
    revenue_history: List[RevenueRecord] = []
    business_start_date: Optional[datetime] = None
    sales_person_id: Optional[str] = None
    sales_person_name: Optional[str] = None
    lead_id: Optional[str] = None
    agreement_id: Optional[str] = None
    notes: Optional[str] = None

class ClientUpdate(BaseModel):
    company_name: Optional[str] = None
    industry: Optional[str] = None
    location: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    address: Optional[str] = None
    website: Optional[str] = None
    contacts: Optional[List[ClientContact]] = None
    revenue_history: Optional[List[RevenueRecord]] = None
    business_start_date: Optional[datetime] = None
    sales_person_id: Optional[str] = None
    sales_person_name: Optional[str] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None

# Client Master can be managed by: Admin, Project Manager, Account Manager, Executive
def can_manage_clients(role: str) -> bool:
    return role in ['admin', 'project_manager', 'account_manager', 'executive', 'manager']

@api_router.post("/clients", response_model=Client)
async def create_client(
    client_create: ClientCreate,
    current_user: User = Depends(get_current_user)
):
    """Create a new client"""
    if not can_manage_clients(current_user.role):
        raise HTTPException(status_code=403, detail="Not authorized to create clients")
    
    client_dict = client_create.model_dump()
    client = Client(**client_dict, created_by=current_user.id)
    
    doc = client.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    if doc['business_start_date']:
        doc['business_start_date'] = doc['business_start_date'].isoformat()
    
    await db.clients.insert_one(doc)
    return client

@api_router.get("/clients")
async def get_clients(
    industry: Optional[str] = None,
    sales_person_id: Optional[str] = None,
    is_active: Optional[bool] = True,
    current_user: User = Depends(get_current_user)
):
    """Get all clients with optional filters"""
    query = {}
    if industry:
        query['industry'] = industry
    if sales_person_id:
        query['sales_person_id'] = sales_person_id
    if is_active is not None:
        query['is_active'] = is_active
    
    clients = await db.clients.find(query, {"_id": 0}).to_list(500)
    
    for client in clients:
        if isinstance(client.get('created_at'), str):
            client['created_at'] = datetime.fromisoformat(client['created_at'])
        if isinstance(client.get('updated_at'), str):
            client['updated_at'] = datetime.fromisoformat(client['updated_at'])
        if client.get('business_start_date') and isinstance(client['business_start_date'], str):
            client['business_start_date'] = datetime.fromisoformat(client['business_start_date'])
    
    return clients

@api_router.get("/clients/{client_id}")
async def get_client(
    client_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get a specific client by ID"""
    client = await db.clients.find_one({"id": client_id}, {"_id": 0})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    if isinstance(client.get('created_at'), str):
        client['created_at'] = datetime.fromisoformat(client['created_at'])
    if isinstance(client.get('updated_at'), str):
        client['updated_at'] = datetime.fromisoformat(client['updated_at'])
    if client.get('business_start_date') and isinstance(client['business_start_date'], str):
        client['business_start_date'] = datetime.fromisoformat(client['business_start_date'])
    
    return client

@api_router.patch("/clients/{client_id}")
async def update_client(
    client_id: str,
    client_update: ClientUpdate,
    current_user: User = Depends(get_current_user)
):
    """Update a client"""
    if not can_manage_clients(current_user.role):
        raise HTTPException(status_code=403, detail="Not authorized to update clients")
    
    client = await db.clients.find_one({"id": client_id}, {"_id": 0})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    update_data = client_update.model_dump(exclude_unset=True)
    update_data['updated_at'] = datetime.now(timezone.utc).isoformat()
    
    if 'business_start_date' in update_data and update_data['business_start_date']:
        update_data['business_start_date'] = update_data['business_start_date'].isoformat()
    
    await db.clients.update_one({"id": client_id}, {"$set": update_data})
    
    updated = await db.clients.find_one({"id": client_id}, {"_id": 0})
    return updated

@api_router.delete("/clients/{client_id}")
async def deactivate_client(
    client_id: str,
    current_user: User = Depends(get_current_user)
):
    """Deactivate a client (soft delete)"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only admins can deactivate clients")
    
    client = await db.clients.find_one({"id": client_id}, {"_id": 0})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    await db.clients.update_one(
        {"id": client_id},
        {"$set": {"is_active": False, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    return {"message": "Client deactivated successfully"}

@api_router.post("/clients/{client_id}/contacts")
async def add_client_contact(
    client_id: str,
    contact: ClientContact,
    current_user: User = Depends(get_current_user)
):
    """Add a contact to a client"""
    if not can_manage_clients(current_user.role):
        raise HTTPException(status_code=403, detail="Not authorized to manage clients")
    
    client = await db.clients.find_one({"id": client_id}, {"_id": 0})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    contacts = client.get('contacts', [])
    
    # If this is marked as primary, unmark other primary contacts
    if contact.is_primary:
        for c in contacts:
            c['is_primary'] = False
    
    contacts.append(contact.model_dump())
    
    await db.clients.update_one(
        {"id": client_id},
        {"$set": {"contacts": contacts, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    return {"message": "Contact added successfully"}

@api_router.post("/clients/{client_id}/revenue")
async def add_revenue_record(
    client_id: str,
    revenue: RevenueRecord,
    current_user: User = Depends(get_current_user)
):
    """Add a revenue record to a client"""
    if not can_manage_clients(current_user.role):
        raise HTTPException(status_code=403, detail="Not authorized to manage clients")
    
    client = await db.clients.find_one({"id": client_id}, {"_id": 0})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    revenue_history = client.get('revenue_history', [])
    revenue_history.append(revenue.model_dump())
    
    # Sort by year and quarter
    revenue_history.sort(key=lambda x: (x['year'], x.get('quarter') or 0))
    
    await db.clients.update_one(
        {"id": client_id},
        {"$set": {"revenue_history": revenue_history, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    return {"message": "Revenue record added successfully"}

@api_router.get("/clients/industries/list")
async def get_client_industries(current_user: User = Depends(get_current_user)):
    """Get list of all industries"""
    industries = await db.clients.distinct("industry")
    return [i for i in industries if i]

@api_router.get("/clients/stats/summary")
async def get_client_stats(current_user: User = Depends(get_current_user)):
    """Get client statistics"""
    total_clients = await db.clients.count_documents({"is_active": True})
    
    by_industry = await db.clients.aggregate([
        {"$match": {"is_active": True}},
        {"$group": {"_id": "$industry", "count": {"$sum": 1}}}
    ]).to_list(100)
    
    # Total revenue across all clients
    pipeline = [
        {"$match": {"is_active": True}},
        {"$unwind": "$revenue_history"},
        {"$group": {"_id": None, "total": {"$sum": "$revenue_history.amount"}}}
    ]
    total_revenue_result = await db.clients.aggregate(pipeline).to_list(1)
    total_revenue = total_revenue_result[0]['total'] if total_revenue_result else 0
    
    return {
        "total_clients": total_clients,
        "by_industry": {item['_id'] or 'Unspecified': item['count'] for item in by_industry},
        "total_revenue": total_revenue
    }


# ==================== EXPENSE SYSTEM ====================

class ExpenseCategory(str):
    TRAVEL = "travel"
    LOCAL_CONVEYANCE = "local_conveyance"
    FOOD = "food"
    ACCOMMODATION = "accommodation"
    OFFICE_SUPPLIES = "office_supplies"
    COMMUNICATION = "communication"
    CLIENT_ENTERTAINMENT = "client_entertainment"
    OTHER = "other"

class ExpenseLineItem(BaseModel):
    """Single expense line item"""
    category: str
    description: str
    amount: float
    date: datetime
    receipt_url: Optional[str] = None
    receipt_data: Optional[str] = None  # Base64 encoded receipt

class ExpenseRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    employee_id: str
    employee_name: str
    client_id: Optional[str] = None  # Link to client if client-related
    client_name: Optional[str] = None
    project_id: Optional[str] = None  # Link to project if project-related
    project_name: Optional[str] = None
    is_office_expense: bool = False  # True if not linked to client/project
    line_items: List[ExpenseLineItem] = []
    total_amount: float = 0
    currency: str = "INR"
    status: str = "draft"  # draft, pending, approved, rejected, reimbursed
    approval_request_id: Optional[str] = None
    rejection_reason: Optional[str] = None
    reimbursed_at: Optional[datetime] = None
    reimbursed_by: Optional[str] = None
    notes: Optional[str] = None
    created_by: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ExpenseRequestCreate(BaseModel):
    client_id: Optional[str] = None
    client_name: Optional[str] = None
    project_id: Optional[str] = None
    project_name: Optional[str] = None
    is_office_expense: bool = False
    line_items: List[ExpenseLineItem] = []
    notes: Optional[str] = None

class ExpenseRequestUpdate(BaseModel):
    client_id: Optional[str] = None
    client_name: Optional[str] = None
    project_id: Optional[str] = None
    project_name: Optional[str] = None
    is_office_expense: Optional[bool] = None
    line_items: Optional[List[ExpenseLineItem]] = None
    notes: Optional[str] = None

@api_router.post("/expenses")
async def create_expense_request(
    expense_create: ExpenseRequestCreate,
    current_user: User = Depends(get_current_user)
):
    """Create a new expense request"""
    # Get employee record
    employee = await db.employees.find_one({"user_id": current_user.id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=400, detail="No employee record found for this user")
    
    # Calculate total
    line_items_data = []
    total = 0
    for item in expense_create.line_items:
        item_dict = item.model_dump()
        item_dict['date'] = item_dict['date'].isoformat()
        line_items_data.append(item_dict)
        total += item.amount
    
    expense = ExpenseRequest(
        employee_id=employee['id'],
        employee_name=f"{employee['first_name']} {employee['last_name']}",
        client_id=expense_create.client_id,
        client_name=expense_create.client_name,
        project_id=expense_create.project_id,
        project_name=expense_create.project_name,
        is_office_expense=expense_create.is_office_expense,
        line_items=line_items_data,
        total_amount=total,
        notes=expense_create.notes,
        created_by=current_user.id
    )
    
    doc = expense.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    
    await db.expenses.insert_one(doc)
    
    return {"message": "Expense request created", "expense_id": expense.id, "total_amount": total}

@api_router.get("/expenses")
async def get_expenses(
    status: Optional[str] = None,
    employee_id: Optional[str] = None,
    client_id: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get expense requests. HR/Admin see all, managers see reportees + own, others see own only."""
    query = {}
    
    if current_user.role in ['admin', 'hr_manager']:
        # Full access
        if employee_id:
            query['employee_id'] = employee_id
    else:
        # Check if user has reportees (reporting manager)
        reportee_emp_ids = await get_all_reportee_ids(current_user.id)
        own_emp = await db.employees.find_one({"user_id": current_user.id}, {"_id": 0, "id": 1})
        own_id = own_emp['id'] if own_emp else None
        
        if reportee_emp_ids:
            # Show own + reportees
            all_visible = reportee_emp_ids + ([own_id] if own_id else [])
            if employee_id:
                query['employee_id'] = employee_id  # Allow filtering
            else:
                query['employee_id'] = {"$in": all_visible}
        elif own_id:
            query['employee_id'] = own_id
    
    if status:
        query['status'] = status
    if client_id:
        query['client_id'] = client_id
    
    expenses = await db.expenses.find(query, {"_id": 0}).sort("created_at", -1).to_list(500)
    return expenses

@api_router.get("/expenses/{expense_id}")
async def get_expense(
    expense_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get a specific expense request"""
    expense = await db.expenses.find_one({"id": expense_id}, {"_id": 0})
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    
    return expense

@api_router.patch("/expenses/{expense_id}")
async def update_expense(
    expense_id: str,
    expense_update: ExpenseRequestUpdate,
    current_user: User = Depends(get_current_user)
):
    """Update an expense request (only if draft status)"""
    expense = await db.expenses.find_one({"id": expense_id}, {"_id": 0})
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    
    if expense['status'] != 'draft':
        raise HTTPException(status_code=400, detail="Can only edit draft expenses")
    
    # Check ownership
    if expense['created_by'] != current_user.id and current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="Not authorized to edit this expense")
    
    update_data = expense_update.model_dump(exclude_unset=True)
    
    # Recalculate total if line items updated
    if 'line_items' in update_data:
        total = sum(item['amount'] for item in update_data['line_items'])
        update_data['total_amount'] = total
        # Convert dates to ISO format
        for item in update_data['line_items']:
            if isinstance(item.get('date'), datetime):
                item['date'] = item['date'].isoformat()
    
    update_data['updated_at'] = datetime.now(timezone.utc).isoformat()
    
    await db.expenses.update_one({"id": expense_id}, {"$set": update_data})
    
    updated = await db.expenses.find_one({"id": expense_id}, {"_id": 0})
    return updated

@api_router.post("/expenses/{expense_id}/submit")
async def submit_expense_for_approval(
    expense_id: str,
    current_user: User = Depends(get_current_user)
):
    """Submit expense for approval through reporting manager chain"""
    expense = await db.expenses.find_one({"id": expense_id}, {"_id": 0})
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    
    if expense['status'] != 'draft':
        raise HTTPException(status_code=400, detail="Expense already submitted")
    
    if expense['created_by'] != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to submit this expense")
    
    if not expense.get('line_items') or len(expense['line_items']) == 0:
        raise HTTPException(status_code=400, detail="Expense must have at least one line item")
    
    # Create approval request through reporting manager chain + HR
    approval = await create_approval_request(
        approval_type=ApprovalType.EXPENSE,
        reference_id=expense_id,
        reference_title=f"Expense: ₹{expense['total_amount']:,.2f}",
        requester_id=current_user.id,
        is_client_facing=bool(expense.get('client_id')),
        requires_hr_approval=True,  # Expenses require HR approval
        requires_admin_approval=False
    )
    
    await db.expenses.update_one(
        {"id": expense_id},
        {"$set": {
            "status": "pending",
            "approval_request_id": approval['id'],
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    # Notify admins about expense submission
    await notify_admins(
        notif_type="expense_submitted",
        title="Expense Submitted",
        message=f"Expense of ₹{expense['total_amount']:,.2f} submitted for approval.",
        reference_type="expense",
        reference_id=expense_id
    )
    
    # Notify reporting manager chain (direct + second-line)
    reporting_chain = await get_reporting_chain(current_user.id, max_levels=2)
    for rm in reporting_chain:
        if rm.get('user_id'):
            await db.notifications.insert_one({
                "id": str(uuid.uuid4()),
                "user_id": rm['user_id'],
                "type": "expense_submitted",
                "title": "Reportee Expense Submitted",
                "message": f"Expense of ₹{expense['total_amount']:,.2f} submitted by {expense.get('employee_name', 'Employee')}.",
                "reference_type": "expense",
                "reference_id": expense_id,
                "is_read": False,
                "created_at": datetime.now(timezone.utc).isoformat()
            })
    
    return {"message": "Expense submitted for approval", "approval_id": approval['id']}

@api_router.post("/expenses/{expense_id}/mark-reimbursed")
async def mark_expense_reimbursed(
    expense_id: str,
    current_user: User = Depends(get_current_user)
):
    """Mark an approved expense as reimbursed (HR/Admin only)"""
    if current_user.role not in ['admin', 'hr_manager']:
        raise HTTPException(status_code=403, detail="Only HR/Admin can mark expenses as reimbursed")
    
    expense = await db.expenses.find_one({"id": expense_id}, {"_id": 0})
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    
    if expense['status'] != 'approved':
        raise HTTPException(status_code=400, detail="Expense must be approved before reimbursement")
    
    await db.expenses.update_one(
        {"id": expense_id},
        {"$set": {
            "status": "reimbursed",
            "reimbursed_at": datetime.now(timezone.utc).isoformat(),
            "reimbursed_by": current_user.id,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    return {"message": "Expense marked as reimbursed"}

@api_router.get("/expenses/categories/list")
async def get_expense_categories():
    """Get list of expense categories"""
    return [
        {"value": "travel", "label": "Travel"},
        {"value": "local_conveyance", "label": "Local Conveyance"},
        {"value": "food", "label": "Food & Meals"},
        {"value": "accommodation", "label": "Accommodation"},
        {"value": "office_supplies", "label": "Office Supplies"},
        {"value": "communication", "label": "Communication"},
        {"value": "client_entertainment", "label": "Client Entertainment"},
        {"value": "other", "label": "Other"}
    ]

@api_router.get("/expenses/stats/summary")
async def get_expense_stats(
    current_user: User = Depends(get_current_user)
):
    """Get expense statistics"""
    if current_user.role not in ['admin', 'hr_manager', 'manager']:
        raise HTTPException(status_code=403, detail="Not authorized to view expense stats")
    
    pending = await db.expenses.count_documents({"status": "pending"})
    approved = await db.expenses.count_documents({"status": "approved"})
    reimbursed = await db.expenses.count_documents({"status": "reimbursed"})
    
    # Total pending amount
    pending_total = await db.expenses.aggregate([
        {"$match": {"status": "pending"}},
        {"$group": {"_id": None, "total": {"$sum": "$total_amount"}}}
    ]).to_list(1)
    
    return {
        "pending_count": pending,
        "approved_count": approved,
        "reimbursed_count": reimbursed,
        "pending_amount": pending_total[0]['total'] if pending_total else 0
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


# ==================== ATTENDANCE MODULE ====================

ATTENDANCE_STATUSES = ["present", "absent", "half_day", "work_from_home", "on_leave", "holiday"]

@api_router.post("/attendance")
async def create_attendance(data: dict, current_user: User = Depends(get_current_user)):
    """Create/update attendance record. HR can manage all, reporting managers can manage their reportees."""
    employee_id = data.get("employee_id")
    date_str = data.get("date")
    att_status = data.get("status", "present")
    if not employee_id or not date_str:
        raise HTTPException(status_code=400, detail="employee_id and date required")
    
    # Access control: HR, admin, or reporting manager of the employee
    if current_user.role in ["admin", "hr_manager", "hr_executive"]:
        pass  # Full access
    else:
        # Check if the employee is a reportee (direct or second-line)
        is_reportee = await is_any_reportee(current_user.id, employee_id)
        if not is_reportee:
            raise HTTPException(status_code=403, detail="You can only manage attendance for your reportees")
    
    existing = await db.attendance.find_one({"employee_id": employee_id, "date": date_str})
    if existing:
        await db.attendance.update_one(
            {"employee_id": employee_id, "date": date_str},
            {"$set": {"status": att_status, "remarks": data.get("remarks", ""), "updated_by": current_user.id, "updated_at": datetime.now(timezone.utc).isoformat()}}
        )
        return {"message": "Attendance updated"}
    record = {
        "id": str(uuid.uuid4()), "employee_id": employee_id, "date": date_str,
        "status": att_status, "remarks": data.get("remarks", ""),
        "created_by": current_user.id, "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.attendance.insert_one(record)
    return {"message": "Attendance recorded", "id": record["id"]}

@api_router.post("/attendance/bulk")
async def bulk_upload_attendance(records: List[dict], current_user: User = Depends(get_current_user)):
    """Bulk upload attendance. HR has full access, managers can upload for reportees only."""
    is_hr = current_user.role in ["admin", "hr_manager", "hr_executive"]
    reportee_ids = [] if is_hr else await get_all_reportee_ids(current_user.id)
    
    if not is_hr and not reportee_ids:
        raise HTTPException(status_code=403, detail="You have no reportees to manage attendance for")
    
    created, updated, skipped = 0, 0, 0
    for rec in records:
        emp_id = rec.get("employee_id")
        date_str = rec.get("date")
        if not emp_id or not date_str:
            continue
        # Reporting managers can only upload for their reportees
        if not is_hr and emp_id not in reportee_ids:
            skipped += 1
            continue
        existing = await db.attendance.find_one({"employee_id": emp_id, "date": date_str})
        if existing:
            await db.attendance.update_one(
                {"employee_id": emp_id, "date": date_str},
                {"$set": {"status": rec.get("status", "present"), "remarks": rec.get("remarks", ""), "updated_by": current_user.id, "updated_at": datetime.now(timezone.utc).isoformat()}}
            )
            updated += 1
        else:
            await db.attendance.insert_one({
                "id": str(uuid.uuid4()), "employee_id": emp_id, "date": date_str,
                "status": rec.get("status", "present"), "remarks": rec.get("remarks", ""),
                "created_by": current_user.id, "created_at": datetime.now(timezone.utc).isoformat()
            })
            created += 1
    return {"message": f"Created {created}, Updated {updated}, Skipped {skipped}", "created": created, "updated": updated, "skipped": skipped}

@api_router.get("/attendance")
async def get_attendance(employee_id: Optional[str] = None, month: Optional[str] = None, current_user: User = Depends(get_current_user)):
    """Get attendance records. HR sees all, managers see their reportees, others see own only."""
    query = {}
    if employee_id:
        query["employee_id"] = employee_id
    if month:
        query["date"] = {"$regex": f"^{month}"}
    
    # Scope filtering based on role
    if current_user.role not in ["admin", "hr_manager", "hr_executive"]:
        # Non-HR: check if they have reportees, otherwise only show own
        reportee_ids = await get_all_reportee_ids(current_user.id)
        own_emp = await db.employees.find_one({"user_id": current_user.id}, {"_id": 0, "id": 1})
        if reportee_ids:
            all_ids = reportee_ids + ([own_emp['id']] if own_emp else [])
            if not employee_id:
                query["employee_id"] = {"$in": all_ids}
        else:
            if own_emp and not employee_id:
                query["employee_id"] = own_emp['id']
    
    records = await db.attendance.find(query, {"_id": 0}).sort("date", -1).to_list(2000)
    return records

@api_router.get("/attendance/summary")
async def get_attendance_summary(month: Optional[str] = None, current_user: User = Depends(get_current_user)):
    """Get attendance summary per employee for a month"""
    query = {}
    if month:
        query["date"] = {"$regex": f"^{month}"}
    records = await db.attendance.find(query, {"_id": 0}).to_list(5000)
    employees = await db.employees.find({"is_active": True}, {"_id": 0, "id": 1, "employee_id": 1, "first_name": 1, "last_name": 1, "department": 1}).to_list(500)
    emp_map = {e["id"]: e for e in employees}
    summary = {}
    for r in records:
        eid = r["employee_id"]
        if eid not in summary:
            emp = emp_map.get(eid, {})
            summary[eid] = {"employee_id": eid, "emp_code": emp.get("employee_id", ""), "name": f"{emp.get('first_name', '')} {emp.get('last_name', '')}", "department": emp.get("department", ""), "present": 0, "absent": 0, "half_day": 0, "wfh": 0, "on_leave": 0, "total": 0}
        summary[eid]["total"] += 1
        s = r.get("status", "present")
        if s == "present": summary[eid]["present"] += 1
        elif s == "absent": summary[eid]["absent"] += 1
        elif s == "half_day": summary[eid]["half_day"] += 1
        elif s == "work_from_home": summary[eid]["wfh"] += 1
        elif s == "on_leave": summary[eid]["on_leave"] += 1
    return list(summary.values())


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
    gross_salary = employee.get("salary", 0) or 0
    if gross_salary <= 0:
        raise HTTPException(status_code=400, detail="Employee salary not configured")
    # Get components
    config = await db.payroll_config.find_one({"type": "salary_components"}, {"_id": 0})
    if not config:
        raise HTTPException(status_code=400, detail="Salary components not configured")
    earnings = []
    total_earnings = 0
    for comp in config.get("earnings", []):
        if comp.get("percentage"):
            amount = round(gross_salary * comp["percentage"] / 100, 2)
        else:
            amount = comp.get("fixed", 0)
        earnings.append({"name": comp["name"], "key": comp["key"], "amount": amount})
        total_earnings += amount
    deductions = []
    total_deductions = 0
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


api_router.include_router(masters_router.router)
api_router.include_router(sow_masters_router.router)
api_router.include_router(enhanced_sow_router.router)
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