"""
Consultants Router - Consultant profiles, projects, and dashboard.
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Optional, List
from datetime import datetime, timezone
import uuid
from .deps import get_db, MANAGER_ROLES
from .models import User
from .auth import get_current_user

router = APIRouter(prefix="/consultants", tags=["Consultants"])


@router.post("")
async def create_consultant(data: dict, current_user: User = Depends(get_current_user)):
    """Create a new consultant user"""
    db = get_db()
    
    if current_user.role not in MANAGER_ROLES:
        raise HTTPException(status_code=403, detail="Only managers can create consultants")
    
    email = data.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="Email is required")
    
    existing = await db.users.find_one({"email": email}, {"_id": 0})
    if existing:
        raise HTTPException(status_code=400, detail="User with this email already exists")
    
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    
    user_id = str(uuid.uuid4())
    password = data.get("password", "consultant123")
    
    user_doc = {
        "id": user_id,
        "email": email,
        "hashed_password": pwd_context.hash(password),
        "full_name": data.get("full_name", ""),
        "role": "consultant",
        "is_active": True,
        "skills": data.get("skills", []),
        "expertise_areas": data.get("expertise_areas", []),
        "hourly_rate": data.get("hourly_rate", 0),
        "availability_status": "available",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.users.insert_one(user_doc)
    user_doc.pop("_id", None)
    user_doc.pop("hashed_password", None)
    return user_doc


@router.get("")
async def get_consultants(
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get all consultants"""
    db = get_db()
    
    query = {"role": "consultant"}
    if status:
        query["availability_status"] = status
    
    consultants = await db.users.find(
        query,
        {"_id": 0, "hashed_password": 0}
    ).to_list(500)
    
    return consultants


@router.get("/{consultant_id}")
async def get_consultant(consultant_id: str, current_user: User = Depends(get_current_user)):
    """Get consultant by ID"""
    db = get_db()
    
    consultant = await db.users.find_one(
        {"id": consultant_id, "role": "consultant"},
        {"_id": 0, "hashed_password": 0}
    )
    
    if not consultant:
        raise HTTPException(status_code=404, detail="Consultant not found")
    
    # Get assigned projects
    projects = await db.consultant_assignments.find(
        {"consultant_id": consultant_id},
        {"_id": 0}
    ).to_list(50)
    
    consultant["projects"] = projects
    return consultant


@router.patch("/{consultant_id}/profile")
async def update_consultant_profile(consultant_id: str, data: dict, current_user: User = Depends(get_current_user)):
    """Update consultant profile"""
    db = get_db()
    
    # Only self or manager can update
    if current_user.id != consultant_id and current_user.role not in MANAGER_ROLES:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    update_fields = {}
    allowed_fields = ["full_name", "skills", "expertise_areas", "hourly_rate", "availability_status", "bio"]
    
    for field in allowed_fields:
        if field in data:
            update_fields[field] = data[field]
    
    update_fields["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.users.update_one({"id": consultant_id}, {"$set": update_fields})
    
    return {"message": "Profile updated"}


@router.put("/{consultant_id}/profile")
async def replace_consultant_profile(consultant_id: str, data: dict, current_user: User = Depends(get_current_user)):
    """Replace consultant profile (full update)"""
    return await update_consultant_profile(consultant_id, data, current_user)


# Consultant self-service endpoints
@router.get("/my/projects", tags=["Consultant Self-Service"])
async def get_my_projects(current_user: User = Depends(get_current_user)):
    """Get current consultant's assigned projects"""
    db = get_db()
    
    assignments = await db.consultant_assignments.find(
        {"consultant_id": current_user.id, "status": "active"},
        {"_id": 0}
    ).to_list(50)
    
    project_ids = [a["project_id"] for a in assignments]
    
    projects = await db.projects.find(
        {"id": {"$in": project_ids}},
        {"_id": 0}
    ).to_list(50)
    
    return projects


@router.get("/my/dashboard-stats", tags=["Consultant Self-Service"])
async def get_consultant_dashboard(current_user: User = Depends(get_current_user)):
    """Get consultant dashboard statistics"""
    db = get_db()
    
    # Active projects
    active_assignments = await db.consultant_assignments.count_documents({
        "consultant_id": current_user.id,
        "status": "active"
    })
    
    # Pending tasks
    pending_tasks = await db.tasks.count_documents({
        "assigned_to": current_user.id,
        "status": {"$in": ["pending", "in_progress"]}
    })
    
    # This month's hours
    now = datetime.now(timezone.utc)
    month_start = datetime(now.year, now.month, 1).strftime("%Y-%m-%d")
    
    timesheets = await db.timesheets.find({
        "employee_id": current_user.id,
        "date": {"$gte": month_start}
    }, {"_id": 0, "hours": 1}).to_list(100)
    
    total_hours = sum(t.get("hours", 0) for t in timesheets)
    
    return {
        "active_projects": active_assignments,
        "pending_tasks": pending_tasks,
        "hours_this_month": total_hours,
        "availability_status": current_user.availability_status if hasattr(current_user, 'availability_status') else "available"
    }
