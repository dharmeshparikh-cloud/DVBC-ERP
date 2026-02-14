from fastapi import FastAPI, APIRouter, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr, ConfigDict
from typing import List, Optional
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
    Quotation, QuotationCreate, Agreement, AgreementCreate,
    calculate_quotation_totals
)
from agreement_templates import (
    AgreementTemplate, AgreementTemplateCreate,
    EmailNotificationTemplate, EmailNotificationTemplateCreate,
    AgreementEmailData, substitute_variables, prepare_agreement_email_data,
    extract_variables_from_template, DEFAULT_AGREEMENT_EMAIL_TEMPLATES
)
from email_service import EmailService, create_mock_email_service

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
    role: str
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
    
    # Calculate totals
    totals = calculate_quotation_totals(
        plan_dict['consultants'],
        plan_dict.get('discount_percentage', 0),
        18,  # GST percentage
        12500  # base rate
    )
    
    plan_dict['base_amount'] = totals['subtotal']
    plan_dict['total_amount'] = totals['grand_total']
    
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
    
    agreement_dict = agreement_create.model_dump()
    agreement_dict['agreement_number'] = agreement_number
    
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
    
    await db.agreements.insert_one(doc)
    
    # Don't update lead status yet - wait for manager approval
    # Status will be updated to 'closed' only after approval
    
    return agreement

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
async def get_pending_approvals(current_user: User = Depends(get_current_user)):
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
async def create_email_template(
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
async def get_email_templates(
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