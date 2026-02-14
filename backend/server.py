from fastapi import FastAPI, APIRouter, HTTPException, Depends, status, Response
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr, ConfigDict
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
import uuid
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

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

app = FastAPI(title="Consulting Workflow Management API")
api_router = APIRouter(prefix="/api")

SECRET_KEY = os.environ.get('SECRET_KEY', 'your-secret-key-change-in-production')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 43200

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

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

class Meeting(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    project_id: str
    meeting_date: datetime
    mode: str
    attendees: List[str] = []
    duration_minutes: Optional[int] = None
    notes: Optional[str] = None
    is_delivered: bool = False
    created_by: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class MeetingCreate(BaseModel):
    project_id: str
    meeting_date: datetime
    mode: str
    attendees: Optional[List[str]] = []
    duration_minutes: Optional[int] = None
    notes: Optional[str] = None
    is_delivered: bool = False

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
    user = User(**user_dict)
    
    doc = user.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['hashed_password'] = get_password_hash(user_create.password)
    
    await db.users.insert_one(doc)
    return user

@api_router.post("/auth/login", response_model=Token)
async def login(user_login: UserLogin):
    user_data = await db.users.find_one({"email": user_login.email}, {"_id": 0})
    if not user_data:
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    
    if not verify_password(user_login.password, user_data['hashed_password']):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    
    if isinstance(user_data.get('created_at'), str):
        user_data['created_at'] = datetime.fromisoformat(user_data['created_at'])
    
    user_data.pop('hashed_password', None)
    user = User(**user_data)
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    
    return Token(access_token=access_token, token_type="bearer", user=user)

@api_router.get("/auth/me", response_model=User)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user

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
    if current_user.role == UserRole.MANAGER:
        raise HTTPException(status_code=403, detail="Managers can only view and download")
    
    meeting_dict = meeting_create.model_dump()
    meeting = Meeting(**meeting_dict, created_by=current_user.id)
    
    doc = meeting.model_dump()
    doc['meeting_date'] = doc['meeting_date'].isoformat()
    doc['created_at'] = doc['created_at'].isoformat()
    
    await db.meetings.insert_one(doc)
    
    if meeting.is_delivered:
        await db.projects.update_one(
            {"id": meeting.project_id},
            {"$inc": {"total_meetings_delivered": 1, "number_of_visits": 1}}
        )
    
    return meeting

@api_router.get("/meetings", response_model=List[Meeting])
async def get_meetings(
    project_id: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    query = {}
    if project_id:
        query['project_id'] = project_id
    
    meetings = await db.meetings.find(query, {"_id": 0}).to_list(1000)
    
    for meeting in meetings:
        if isinstance(meeting.get('meeting_date'), str):
            meeting['meeting_date'] = datetime.fromisoformat(meeting['meeting_date'])
        if isinstance(meeting.get('created_at'), str):
            meeting['created_at'] = datetime.fromisoformat(meeting['created_at'])
    
    return meetings

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


@api_router.get("/sow/{sow_id}/download")
async def download_sow_document(
    sow_id: str,
    format: str = "pdf",  # pdf or docx
    current_user: User = Depends(get_current_user)
):
    """Download SOW as Word or PDF document"""
    sow = await db.sow.find_one({"id": sow_id}, {"_id": 0})
    if not sow:
        raise HTTPException(status_code=404, detail="SOW not found")
    
    # Get lead data
    lead = None
    if sow.get('lead_id'):
        lead = await db.leads.find_one({"id": sow['lead_id']}, {"_id": 0})
    
    # Get pricing plan data
    pricing_plan = None
    if sow.get('pricing_plan_id'):
        pricing_plan = await db.pricing_plans.find_one({"id": sow['pricing_plan_id']}, {"_id": 0})
    
    # Generate document
    generator = SOWDocumentGenerator(sow, lead, pricing_plan)
    
    # Create filename
    client_name = lead.get('company', 'Client') if lead else 'SOW'
    client_name = "".join(c for c in client_name if c.isalnum() or c in ' -_')[:30]
    
    if format.lower() == 'docx':
        buffer = generator.generate_word()
        filename = f"SOW_{client_name}.docx"
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    else:
        buffer = generator.generate_pdf()
        filename = f"SOW_{client_name}.pdf"
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
    
    hashed_password = get_password_hash(user_create.password)
    user = User(
        email=user_create.email,
        full_name=user_create.full_name,
        role=UserRole.CONSULTANT,
        department=user_create.department
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

@api_router.get("/projects/{project_id}/tasks-gantt")
async def get_project_tasks_for_gantt(
    project_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get tasks formatted for Gantt chart"""
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
            "dependencies": task.get('dependencies', []),
            "progress": 100 if task.get('status') == TaskStatus.COMPLETED else 
                       50 if task.get('status') == TaskStatus.IN_PROGRESS else 0
        })
    
    return gantt_data

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

# Note: Notifications APIs already exist above at lines 3846-3867
# Added mark-all-read endpoint here as it's new

@api_router.post("/notifications/mark-all-read")
async def mark_all_notifications_read_v2(current_user: User = Depends(get_current_user)):
    """Mark all notifications as read"""
    await db.notifications.update_many(
        {"user_id": current_user.id, "is_read": False},
        {"$set": {"is_read": True}}
    )
    return {"message": "All notifications marked as read"}

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
    """Create a leave request (automatically routed to reporting manager + HR)"""
    # Get employee record
    employee = await db.employees.find_one({"user_id": current_user.id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=400, detail="Employee record not found. Please contact HR.")
    
    # Calculate days
    days = (leave_data.end_date - leave_data.start_date).days + 1
    
    # Check leave balance
    leave_balance = employee.get('leave_balance', {})
    leave_type_key = leave_data.leave_type.replace('_leave', '')
    available = leave_balance.get(leave_data.leave_type, 0) - leave_balance.get(f'used_{leave_type_key}', 0)
    
    if days > available:
        raise HTTPException(status_code=400, detail=f"Insufficient leave balance. Available: {available} days")
    
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
    
    # Create approval request (Reporting Manager → HR)
    approval = await create_approval_request(
        approval_type=ApprovalType.LEAVE_REQUEST,
        reference_id=leave_request['id'],
        reference_title=f"{leave_data.leave_type.replace('_', ' ').title()} - {days} day(s)",
        requester_id=current_user.id,
        requires_hr_approval=True,
        requires_admin_approval=False,
        is_client_facing=False
    )
    
    # Link approval to leave request
    await db.leave_requests.update_one(
        {"id": leave_request['id']},
        {"$set": {"approval_request_id": approval['id']}}
    )
    
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
    """Get all leave requests (HR/Admin only)"""
    if current_user.role not in [UserRole.ADMIN, UserRole.HR_MANAGER, UserRole.HR_EXECUTIVE]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    requests = await db.leave_requests.find({}, {"_id": 0}).sort("created_at", -1).to_list(200)
    return requests

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
    """Get expense requests"""
    query = {}
    
    # Non-admin/hr users can only see their own expenses
    if current_user.role not in ['admin', 'hr_manager', 'manager', 'project_manager']:
        employee = await db.employees.find_one({"user_id": current_user.id}, {"_id": 0})
        if employee:
            query['employee_id'] = employee['id']
    else:
        if employee_id:
            query['employee_id'] = employee_id
    
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