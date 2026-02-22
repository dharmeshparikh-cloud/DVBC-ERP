"""
Admin Masters Router - Manage Tenure Types and Allocation Rules for Top-Down Pricing

This module provides CRUD operations for:
1. Tenure Types (Full-time, Weekly, Bi-weekly, etc.)
2. Allocation Rules (Percentage allocation per tenure type)
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
import os
import uuid

router = APIRouter(prefix="/masters", tags=["Admin Masters"])

# Database connection - will be set by main server
db = None

def set_db(database):
    global db
    db = database


# ============== Models ==============

class TenureType(BaseModel):
    """Tenure type with default allocation percentage"""
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str  # e.g., "Full-time", "Weekly", "Bi-weekly"
    code: str  # e.g., "full_time", "weekly", "bi_weekly"
    allocation_percentage: float  # e.g., 70.0 for 70%
    description: Optional[str] = None
    meetings_per_month: Optional[float] = None  # For auto-calculation reference
    is_active: bool = True
    is_default: bool = False  # Only one can be default
    created_by: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class TenureTypeCreate(BaseModel):
    name: str
    code: str
    allocation_percentage: float
    description: Optional[str] = None
    meetings_per_month: Optional[float] = None
    is_default: Optional[bool] = False


class TenureTypeUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    allocation_percentage: Optional[float] = None
    description: Optional[str] = None
    meetings_per_month: Optional[float] = None
    is_active: Optional[bool] = None
    is_default: Optional[bool] = None


class ConsultantRole(BaseModel):
    """Consultant roles with minimum rates"""
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str  # e.g., "Project Manager", "Lean Consultant"
    code: str  # e.g., "principal_consultant", "lean_consultant"
    min_rate_per_meeting: float = 10000  # Minimum rate per meeting
    max_rate_per_meeting: float = 50000  # Maximum rate per meeting
    default_rate: float = 12500
    seniority_level: int = 1  # 1-5 scale for sorting
    is_active: bool = True
    created_by: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ConsultantRoleCreate(BaseModel):
    name: str
    code: str
    min_rate_per_meeting: Optional[float] = 10000
    max_rate_per_meeting: Optional[float] = 50000
    default_rate: Optional[float] = 12500
    seniority_level: Optional[int] = 1


class ConsultantRoleUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    min_rate_per_meeting: Optional[float] = None
    max_rate_per_meeting: Optional[float] = None
    default_rate: Optional[float] = None
    seniority_level: Optional[int] = None
    is_active: Optional[bool] = None


class MeetingType(BaseModel):
    """Meeting types master"""
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str  # e.g., "Monthly Review", "Weekly Review"
    code: str
    default_duration_minutes: int = 60
    is_active: bool = True
    created_by: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class MeetingTypeCreate(BaseModel):
    name: str
    code: str
    default_duration_minutes: Optional[int] = 60


# ============== Default Data ==============

DEFAULT_TENURE_TYPES = [
    {"name": "Full-time Engagement", "code": "full_time", "allocation_percentage": 70.0, "meetings_per_month": 22, "description": "Daily engagement (22 working days/month)", "is_default": True},
    {"name": "Weekly Engagement", "code": "weekly", "allocation_percentage": 20.0, "meetings_per_month": 4, "description": "Once per week"},
    {"name": "Bi-weekly Engagement", "code": "bi_weekly", "allocation_percentage": 10.0, "meetings_per_month": 2, "description": "Once every two weeks"},
    {"name": "Monthly Engagement", "code": "monthly", "allocation_percentage": 5.0, "meetings_per_month": 1, "description": "Once per month"},
    {"name": "Quarterly Review", "code": "quarterly", "allocation_percentage": 2.5, "meetings_per_month": 0.33, "description": "Once per quarter"},
    {"name": "On-demand Support", "code": "on_demand", "allocation_percentage": 0.0, "meetings_per_month": 0, "description": "As needed basis (manual entry)"},
]

DEFAULT_CONSULTANT_ROLES = [
    {"name": "Principal Consultant", "code": "principal_consultant", "min_rate_per_meeting": 25000, "max_rate_per_meeting": 75000, "default_rate": 35000, "seniority_level": 5},
    {"name": "Lead Consultant", "code": "lead_consultant", "min_rate_per_meeting": 18000, "max_rate_per_meeting": 40000, "default_rate": 22000, "seniority_level": 4},
    {"name": "Senior Consultant", "code": "senior_consultant", "min_rate_per_meeting": 15000, "max_rate_per_meeting": 35000, "default_rate": 18000, "seniority_level": 3},
    {"name": "Consultant", "code": "consultant", "min_rate_per_meeting": 12000, "max_rate_per_meeting": 25000, "default_rate": 15000, "seniority_level": 2},
    {"name": "Lean Consultant", "code": "lean_consultant", "min_rate_per_meeting": 8000, "max_rate_per_meeting": 18000, "default_rate": 12500, "seniority_level": 1},
    {"name": "Subject Matter Expert", "code": "subject_matter_expert", "min_rate_per_meeting": 30000, "max_rate_per_meeting": 100000, "default_rate": 45000, "seniority_level": 5},
    {"name": "HR Consultant", "code": "hr_consultant", "min_rate_per_meeting": 12000, "max_rate_per_meeting": 30000, "default_rate": 15000, "seniority_level": 2},
    {"name": "Sales Trainer", "code": "sales_trainer", "min_rate_per_meeting": 15000, "max_rate_per_meeting": 40000, "default_rate": 20000, "seniority_level": 3},
    {"name": "Data Analyst", "code": "data_analyst", "min_rate_per_meeting": 10000, "max_rate_per_meeting": 25000, "default_rate": 12500, "seniority_level": 2},
    {"name": "Digital Marketing Manager", "code": "digital_marketing_manager", "min_rate_per_meeting": 12000, "max_rate_per_meeting": 30000, "default_rate": 15000, "seniority_level": 3},
    {"name": "Account Manager", "code": "sales_manager", "min_rate_per_meeting": 10000, "max_rate_per_meeting": 25000, "default_rate": 12500, "seniority_level": 2},
]

DEFAULT_MEETING_TYPES = [
    {"name": "Monthly Review", "code": "monthly_review", "default_duration_minutes": 90},
    {"name": "Weekly Review", "code": "weekly_review", "default_duration_minutes": 60},
    {"name": "Daily Standup", "code": "daily_standup", "default_duration_minutes": 30},
    {"name": "Online Review", "code": "online_review", "default_duration_minutes": 60},
    {"name": "On-site Visit", "code": "onsite_visit", "default_duration_minutes": 240},
    {"name": "Strategy Session", "code": "strategy_session", "default_duration_minutes": 120},
    {"name": "Training Session", "code": "training_session", "default_duration_minutes": 180},
    {"name": "Progress Update", "code": "progress_update", "default_duration_minutes": 45},
    {"name": "Kickoff Meeting", "code": "kickoff_meeting", "default_duration_minutes": 120},
    {"name": "Quarterly Business Review", "code": "qbr", "default_duration_minutes": 180},
]


# ============== Tenure Types Endpoints ==============

@router.post("/tenure-types", response_model=TenureType)
async def create_tenure_type(tenure_create: TenureTypeCreate, current_user_id: str = None):
    """Create a new tenure type with allocation percentage"""
    # Check for duplicate code
    existing = await db.tenure_types.find_one({"code": tenure_create.code})
    if existing:
        raise HTTPException(status_code=400, detail=f"Tenure type with code '{tenure_create.code}' already exists")
    
    # Validate allocation percentage
    if tenure_create.allocation_percentage < 0 or tenure_create.allocation_percentage > 100:
        raise HTTPException(status_code=400, detail="Allocation percentage must be between 0 and 100")
    
    # If setting as default, unset other defaults
    if tenure_create.is_default:
        await db.tenure_types.update_many({}, {"$set": {"is_default": False}})
    
    tenure = TenureType(**tenure_create.model_dump(), created_by=current_user_id)
    doc = tenure.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    
    await db.tenure_types.insert_one(doc)
    return tenure


@router.get("/tenure-types", response_model=List[TenureType])
async def get_tenure_types(include_inactive: bool = False):
    """Get all tenure types (for dropdowns and allocation rules)"""
    query = {} if include_inactive else {"is_active": True}
    tenure_types = await db.tenure_types.find(query, {"_id": 0}).sort("allocation_percentage", -1).to_list(100)
    
    for tt in tenure_types:
        if isinstance(tt.get('created_at'), str):
            tt['created_at'] = datetime.fromisoformat(tt['created_at'])
        if isinstance(tt.get('updated_at'), str):
            tt['updated_at'] = datetime.fromisoformat(tt['updated_at'])
    
    return tenure_types


@router.get("/tenure-types/{tenure_id}", response_model=TenureType)
async def get_tenure_type(tenure_id: str):
    """Get a specific tenure type"""
    tenure = await db.tenure_types.find_one({"id": tenure_id}, {"_id": 0})
    if not tenure:
        raise HTTPException(status_code=404, detail="Tenure type not found")
    
    if isinstance(tenure.get('created_at'), str):
        tenure['created_at'] = datetime.fromisoformat(tenure['created_at'])
    if isinstance(tenure.get('updated_at'), str):
        tenure['updated_at'] = datetime.fromisoformat(tenure['updated_at'])
    
    return TenureType(**tenure)


@router.put("/tenure-types/{tenure_id}", response_model=TenureType)
async def update_tenure_type(tenure_id: str, tenure_update: TenureTypeUpdate):
    """Update a tenure type"""
    existing = await db.tenure_types.find_one({"id": tenure_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Tenure type not found")
    
    update_data = tenure_update.model_dump(exclude_unset=True)
    
    # Validate allocation percentage if provided
    if 'allocation_percentage' in update_data:
        if update_data['allocation_percentage'] < 0 or update_data['allocation_percentage'] > 100:
            raise HTTPException(status_code=400, detail="Allocation percentage must be between 0 and 100")
    
    # If setting as default, unset other defaults
    if update_data.get('is_default'):
        await db.tenure_types.update_many({"id": {"$ne": tenure_id}}, {"$set": {"is_default": False}})
    
    update_data['updated_at'] = datetime.now(timezone.utc).isoformat()
    
    await db.tenure_types.update_one({"id": tenure_id}, {"$set": update_data})
    
    updated = await db.tenure_types.find_one({"id": tenure_id}, {"_id": 0})
    if isinstance(updated.get('created_at'), str):
        updated['created_at'] = datetime.fromisoformat(updated['created_at'])
    if isinstance(updated.get('updated_at'), str):
        updated['updated_at'] = datetime.fromisoformat(updated['updated_at'])
    
    return TenureType(**updated)


@router.delete("/tenure-types/{tenure_id}")
async def delete_tenure_type(tenure_id: str):
    """Soft delete a tenure type"""
    existing = await db.tenure_types.find_one({"id": tenure_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Tenure type not found")
    
    await db.tenure_types.update_one(
        {"id": tenure_id}, 
        {"$set": {"is_active": False, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    return {"message": "Tenure type deactivated successfully"}


# ============== Consultant Roles Endpoints ==============

@router.post("/consultant-roles", response_model=ConsultantRole)
async def create_consultant_role(role_create: ConsultantRoleCreate, current_user_id: str = None):
    """Create a new consultant role"""
    existing = await db.consultant_roles.find_one({"code": role_create.code})
    if existing:
        raise HTTPException(status_code=400, detail=f"Consultant role with code '{role_create.code}' already exists")
    
    role = ConsultantRole(**role_create.model_dump(), created_by=current_user_id)
    doc = role.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    
    await db.consultant_roles.insert_one(doc)
    return role


@router.get("/consultant-roles", response_model=List[ConsultantRole])
async def get_consultant_roles(include_inactive: bool = False):
    """Get all consultant roles"""
    query = {} if include_inactive else {"is_active": True}
    roles = await db.consultant_roles.find(query, {"_id": 0}).sort("seniority_level", -1).to_list(100)
    
    for role in roles:
        if isinstance(role.get('created_at'), str):
            role['created_at'] = datetime.fromisoformat(role['created_at'])
        if isinstance(role.get('updated_at'), str):
            role['updated_at'] = datetime.fromisoformat(role['updated_at'])
    
    return roles


@router.put("/consultant-roles/{role_id}", response_model=ConsultantRole)
async def update_consultant_role(role_id: str, role_update: ConsultantRoleUpdate):
    """Update a consultant role"""
    existing = await db.consultant_roles.find_one({"id": role_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Consultant role not found")
    
    update_data = role_update.model_dump(exclude_unset=True)
    update_data['updated_at'] = datetime.now(timezone.utc).isoformat()
    
    await db.consultant_roles.update_one({"id": role_id}, {"$set": update_data})
    
    updated = await db.consultant_roles.find_one({"id": role_id}, {"_id": 0})
    if isinstance(updated.get('created_at'), str):
        updated['created_at'] = datetime.fromisoformat(updated['created_at'])
    if isinstance(updated.get('updated_at'), str):
        updated['updated_at'] = datetime.fromisoformat(updated['updated_at'])
    
    return ConsultantRole(**updated)


@router.delete("/consultant-roles/{role_id}")
async def delete_consultant_role(role_id: str):
    """Soft delete a consultant role"""
    existing = await db.consultant_roles.find_one({"id": role_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Consultant role not found")
    
    await db.consultant_roles.update_one(
        {"id": role_id}, 
        {"$set": {"is_active": False, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    return {"message": "Consultant role deactivated successfully"}


# ============== Meeting Types Endpoints ==============

@router.get("/meeting-types", response_model=List[MeetingType])
async def get_meeting_types(include_inactive: bool = False):
    """Get all meeting types"""
    query = {} if include_inactive else {"is_active": True}
    types = await db.meeting_types.find(query, {"_id": 0}).to_list(100)
    
    for mt in types:
        if isinstance(mt.get('created_at'), str):
            mt['created_at'] = datetime.fromisoformat(mt['created_at'])
        if isinstance(mt.get('updated_at'), str):
            mt['updated_at'] = datetime.fromisoformat(mt['updated_at'])
    
    return types


@router.post("/meeting-types", response_model=MeetingType)
async def create_meeting_type(meeting_create: MeetingTypeCreate, current_user_id: str = None):
    """Create a new meeting type"""
    existing = await db.meeting_types.find_one({"code": meeting_create.code})
    if existing:
        raise HTTPException(status_code=400, detail=f"Meeting type with code '{meeting_create.code}' already exists")
    
    meeting = MeetingType(**meeting_create.model_dump(), created_by=current_user_id)
    doc = meeting.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    
    await db.meeting_types.insert_one(doc)
    return meeting


# ============== Seed Default Data Endpoint ==============

@router.post("/seed-defaults")
async def seed_default_masters():
    """Seed default master data (admin only)"""
    results = {"tenure_types": 0, "consultant_roles": 0, "meeting_types": 0}
    
    # Seed tenure types
    for tt_data in DEFAULT_TENURE_TYPES:
        existing = await db.tenure_types.find_one({"code": tt_data["code"]})
        if not existing:
            tenure = TenureType(**tt_data)
            doc = tenure.model_dump()
            doc['created_at'] = doc['created_at'].isoformat()
            doc['updated_at'] = doc['updated_at'].isoformat()
            await db.tenure_types.insert_one(doc)
            results["tenure_types"] += 1
    
    # Seed consultant roles
    for role_data in DEFAULT_CONSULTANT_ROLES:
        existing = await db.consultant_roles.find_one({"code": role_data["code"]})
        if not existing:
            role = ConsultantRole(**role_data)
            doc = role.model_dump()
            doc['created_at'] = doc['created_at'].isoformat()
            doc['updated_at'] = doc['updated_at'].isoformat()
            await db.consultant_roles.insert_one(doc)
            results["consultant_roles"] += 1
    
    # Seed meeting types
    for mt_data in DEFAULT_MEETING_TYPES:
        existing = await db.meeting_types.find_one({"code": mt_data["code"]})
        if not existing:
            meeting = MeetingType(**mt_data)
            doc = meeting.model_dump()
            doc['created_at'] = doc['created_at'].isoformat()
            doc['updated_at'] = doc['updated_at'].isoformat()
            await db.meeting_types.insert_one(doc)
            results["meeting_types"] += 1
    
    return {"message": "Default masters seeded successfully", "created": results}


# ============== Allocation Calculation Helpers ==============

@router.post("/calculate-allocation")
async def calculate_allocation(data: dict):
    """
    Calculate cost allocation based on total investment and team tenure types.
    
    Input:
    {
        "total_investment": 1000000,
        "team_members": [
            {"tenure_type_code": "full_time", "meetings_per_month": 22, "duration_months": 12},
            {"tenure_type_code": "weekly", "meetings_per_month": 4, "duration_months": 12}
        ]
    }
    
    Output: Breakup amount and rate per meeting for each team member
    """
    total_investment = data.get("total_investment", 0)
    team_members = data.get("team_members", [])
    
    if total_investment <= 0:
        raise HTTPException(status_code=400, detail="Total investment must be greater than 0")
    
    if not team_members:
        raise HTTPException(status_code=400, detail="At least one team member is required")
    
    # Get tenure types
    tenure_lookup = {}
    tenure_types = await db.tenure_types.find({"is_active": True}, {"_id": 0}).to_list(100)
    for tt in tenure_types:
        tenure_lookup[tt["code"]] = tt
    
    # Calculate total allocation percentage
    total_allocation = 0
    for member in team_members:
        tenure_code = member.get("tenure_type_code")
        if tenure_code in tenure_lookup:
            total_allocation += tenure_lookup[tenure_code]["allocation_percentage"]
    
    if total_allocation == 0:
        raise HTTPException(status_code=400, detail="Total allocation percentage cannot be zero")
    
    # Calculate breakup for each member
    results = []
    for member in team_members:
        tenure_code = member.get("tenure_type_code")
        if tenure_code not in tenure_lookup:
            continue
        
        tenure = tenure_lookup[tenure_code]
        duration_months = member.get("duration_months", 12)
        meetings_per_month = member.get("meetings_per_month") or tenure.get("meetings_per_month", 1)
        
        # Normalize allocation percentage to total
        normalized_allocation = (tenure["allocation_percentage"] / total_allocation) * 100
        
        # Calculate breakup amount
        breakup_amount = total_investment * (normalized_allocation / 100)
        
        # Calculate total meetings
        total_meetings = int(meetings_per_month * duration_months)
        
        # Calculate rate per meeting
        rate_per_meeting = breakup_amount / total_meetings if total_meetings > 0 else 0
        
        results.append({
            "tenure_type_code": tenure_code,
            "tenure_type_name": tenure["name"],
            "allocation_percentage": round(normalized_allocation, 2),
            "breakup_amount": round(breakup_amount, 2),
            "total_meetings": total_meetings,
            "rate_per_meeting": round(rate_per_meeting, 2),
            "duration_months": duration_months,
            "meetings_per_month": meetings_per_month
        })
    
    return {
        "total_investment": total_investment,
        "total_allocation_percentage": round(total_allocation, 2),
        "team_breakdown": results
    }
