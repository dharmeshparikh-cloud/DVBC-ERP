"""
Client Authentication Router
Handles client login, password management, and client-specific operations.
Client IDs start from 98000 (5-digit format)
"""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer
from datetime import datetime, timezone, timedelta
from typing import Optional
from pydantic import BaseModel
from passlib.context import CryptContext
import jwt
import os

from .deps import get_db

router = APIRouter(prefix="/client-auth", tags=["Client Authentication"])

# JWT Settings
SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "netra-erp-secret-key-2024")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/client-auth/login")


# Request/Response Models
class ClientLoginRequest(BaseModel):
    client_id: str
    password: str


class ClientChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class ClientTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    client_id: str
    full_name: str
    company_name: str
    must_change_password: bool
    project_ids: list


def create_client_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS))
    to_encode.update({"exp": expire, "type": "client"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


async def get_current_client(token: str = Depends(oauth2_scheme)):
    """Dependency to get current authenticated client."""
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        client_id: str = payload.get("sub")
        token_type: str = payload.get("type")
        if client_id is None or token_type != "client":
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception
    
    db = get_db()
    client = await db.client_users.find_one({"client_id": client_id}, {"_id": 0})
    if client is None:
        raise credentials_exception
    if not client.get("is_active"):
        raise HTTPException(status_code=403, detail="Client account is deactivated")
    
    return client


@router.post("/login", response_model=ClientTokenResponse)
async def client_login(request: ClientLoginRequest):
    """
    Client login using Client ID (98XXX) and password.
    Returns JWT token for client portal access.
    """
    db = get_db()
    
    # Find client by client_id
    client = await db.client_users.find_one({"client_id": request.client_id}, {"_id": 0})
    
    if not client:
        raise HTTPException(status_code=401, detail="Invalid Client ID or password")
    
    if not client.get("is_active"):
        raise HTTPException(status_code=403, detail="Your account has been deactivated. Please contact support.")
    
    # Verify password
    if not pwd_context.verify(request.password, client.get("hashed_password", "")):
        raise HTTPException(status_code=401, detail="Invalid Client ID or password")
    
    # Update last login
    await db.client_users.update_one(
        {"client_id": request.client_id},
        {"$set": {"last_login": datetime.now(timezone.utc).isoformat()}}
    )
    
    # Create token
    token = create_client_token(data={"sub": request.client_id})
    
    return ClientTokenResponse(
        access_token=token,
        client_id=client.get("client_id"),
        full_name=client.get("full_name"),
        company_name=client.get("company_name"),
        must_change_password=client.get("must_change_password", False),
        project_ids=client.get("project_ids", [])
    )


@router.post("/change-password")
async def change_password(
    request: ClientChangePasswordRequest,
    current_client: dict = Depends(get_current_client)
):
    """
    Change client password. Required on first login.
    """
    db = get_db()
    
    # Verify current password
    if not pwd_context.verify(request.current_password, current_client.get("hashed_password", "")):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    
    # Validate new password
    if len(request.new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    
    # Hash and update
    new_hashed = pwd_context.hash(request.new_password)
    
    await db.client_users.update_one(
        {"client_id": current_client.get("client_id")},
        {"$set": {
            "hashed_password": new_hashed,
            "must_change_password": False,
            "password_changed_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    return {"message": "Password changed successfully"}


@router.get("/me")
async def get_client_profile(current_client: dict = Depends(get_current_client)):
    """Get current client profile."""
    # Remove sensitive data
    client_data = {k: v for k, v in current_client.items() if k != "hashed_password"}
    return client_data


@router.get("/my-projects")
async def get_client_projects(current_client: dict = Depends(get_current_client)):
    """Get all projects for the current client."""
    db = get_db()
    
    project_ids = current_client.get("project_ids", [])
    if not project_ids:
        return {"projects": []}
    
    projects = await db.projects.find(
        {"id": {"$in": project_ids}},
        {"_id": 0}
    ).to_list(100)
    
    # Enrich with consultant details
    for project in projects:
        # Get assigned consultants
        assignments = await db.project_assignments.find(
            {"project_id": project.get("id"), "is_active": True},
            {"_id": 0}
        ).to_list(10)
        project["consultants"] = assignments
        
        # Get agreement details
        if project.get("agreement_id"):
            agreement = await db.agreements.find_one(
                {"id": project.get("agreement_id")},
                {"_id": 0, "id": 1, "agreement_number": 1, "status": 1, "total_value": 1}
            )
            project["agreement"] = agreement
    
    return {"projects": projects}


@router.get("/project/{project_id}")
async def get_project_details(
    project_id: str,
    current_client: dict = Depends(get_current_client)
):
    """Get detailed project information including consultant, MOM, payments."""
    db = get_db()
    
    # Verify client has access to this project
    if project_id not in current_client.get("project_ids", []):
        raise HTTPException(status_code=403, detail="You don't have access to this project")
    
    project = await db.projects.find_one({"id": project_id}, {"_id": 0})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Get assigned consultants with details
    assignments = await db.project_assignments.find(
        {"project_id": project_id},
        {"_id": 0}
    ).to_list(20)
    
    active_consultants = []
    past_consultants = []
    for a in assignments:
        consultant = await db.users.find_one(
            {"id": a.get("consultant_id")},
            {"_id": 0, "id": 1, "full_name": 1, "email": 1, "phone": 1, "role": 1}
        )
        if consultant:
            a["consultant_details"] = consultant
        if a.get("is_active"):
            active_consultants.append(a)
        else:
            past_consultants.append(a)
    
    project["active_consultants"] = active_consultants
    project["past_consultants"] = past_consultants
    
    # Get reporting manager (Principal Consultant who approved)
    if project.get("internal_approved_by"):
        approver = await db.users.find_one(
            {"id": project.get("internal_approved_by")},
            {"_id": 0, "id": 1, "full_name": 1, "email": 1, "role": 1}
        )
        project["reporting_manager"] = approver
    
    # Get agreement
    if project.get("agreement_id"):
        agreement = await db.agreements.find_one(
            {"id": project.get("agreement_id")},
            {"_id": 0}
        )
        project["agreement"] = agreement
    
    # Get meetings/MOM
    meetings = await db.meetings.find(
        {"$or": [
            {"project_id": project_id},
            {"lead_id": project.get("lead_id")}
        ]},
        {"_id": 0}
    ).sort("date", -1).to_list(50)
    project["meetings"] = meetings
    
    # Get payments
    payments = await db.payment_verifications.find(
        {"$or": [
            {"project_id": project_id},
            {"agreement_id": project.get("agreement_id")}
        ]},
        {"_id": 0}
    ).sort("created_at", -1).to_list(50)
    project["payments"] = payments
    
    # Get upcoming payments (from agreement payment schedule)
    if project.get("agreement_id"):
        agreement = await db.agreements.find_one(
            {"id": project.get("agreement_id")},
            {"_id": 0, "payment_schedule": 1}
        )
        if agreement and agreement.get("payment_schedule"):
            project["upcoming_payments"] = [
                p for p in agreement.get("payment_schedule", [])
                if p.get("status") != "paid"
            ]
    
    # Get documents (SOW, Agreement, Invoices)
    documents = []
    
    # SOW
    sow = await db.enhanced_sow.find_one(
        {"project_id": project_id},
        {"_id": 0, "id": 1, "title": 1, "created_at": 1}
    )
    if sow:
        documents.append({"type": "SOW", "name": sow.get("title", "Scope of Work"), **sow})
    
    # Invoices
    invoices = await db.invoices.find(
        {"project_id": project_id},
        {"_id": 0}
    ).to_list(50)
    for inv in invoices:
        documents.append({"type": "Invoice", "name": f"Invoice #{inv.get('invoice_number', '')}", **inv})
    
    project["documents"] = documents
    
    return project


@router.post("/change-consultant-request")
async def request_consultant_change(
    project_id: str,
    reason: str,
    current_client: dict = Depends(get_current_client)
):
    """
    Client requests a consultant change.
    Creates a request for Principal Consultant and Admin to review.
    """
    db = get_db()
    
    # Verify access
    if project_id not in current_client.get("project_ids", []):
        raise HTTPException(status_code=403, detail="You don't have access to this project")
    
    project = await db.projects.find_one({"id": project_id}, {"_id": 0})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Create change request
    import uuid
    request_doc = {
        "id": str(uuid.uuid4()),
        "type": "consultant_change",
        "project_id": project_id,
        "project_name": project.get("name"),
        "client_id": current_client.get("client_id"),
        "client_name": current_client.get("full_name"),
        "reason": reason,
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.consultant_change_requests.insert_one(request_doc)
    
    # Notify Principal Consultants and Admins
    recipients = await db.users.find(
        {"role": {"$in": ["principal_consultant", "admin"]}},
        {"_id": 0, "id": 1}
    ).to_list(20)
    
    for user in recipients:
        notification = {
            "id": str(uuid.uuid4()),
            "type": "consultant_change_request",
            "recipient_id": user.get("id"),
            "title": f"Consultant Change Request: {project.get('name')}",
            "message": f"Client {current_client.get('full_name')} requested a consultant change. Reason: {reason[:100]}...",
            "project_id": project_id,
            "request_id": request_doc["id"],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "read": False
        }
        await db.notifications.insert_one(notification)
    
    return {
        "message": "Consultant change request submitted successfully",
        "request_id": request_doc["id"]
    }
