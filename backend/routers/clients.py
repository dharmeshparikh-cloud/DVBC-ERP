"""
Clients Router - Client Master Management

Provides read access to client_master collection populated from kickoff approval.
Role-based filtering:
- Admin/Finance: See all clients
- Sales: See clients where they are sales_owner
- Consulting: See clients where they are consulting_owner
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from datetime import datetime, timezone
from typing import List, Optional
import uuid

from .deps import get_db
from .deps import get_current_user
from .models import User

router = APIRouter(prefix="/clients", tags=["Client Master"])


def get_role_filter(user: User) -> dict:
    """Build MongoDB filter based on user role."""
    # Admin/Finance see all
    admin_finance_roles = ['admin', 'finance_manager', 'finance_executive', 'accounts']
    if user.role in admin_finance_roles:
        return {}
    
    # Sales see their own clients
    sales_roles = ['sales_manager', 'executive', 'sales_executive']
    if user.role in sales_roles:
        return {"$or": [
            {"sales_owner_id": user.id},
            {"sales_person_id": user.id}
        ]}
    
    # Consulting see their assigned clients
    consulting_roles = ['principal_consultant', 'senior_consultant', 'consultant', 'project_manager', 'lean_consultant']
    if user.role in consulting_roles:
        return {"consulting_owner_id": user.id}
    
    # HR/Manager can see all for reporting
    if user.role in ['hr_manager', 'hr_executive', 'manager']:
        return {}
    
    # Default: only show clients user is associated with
    return {"$or": [
        {"sales_owner_id": user.id},
        {"consulting_owner_id": user.id}
    ]}


@router.get("")
async def get_clients(
    status: Optional[str] = None,
    industry: Optional[str] = None,
    search: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_user)
):
    """Get clients filtered by user role."""
    db = get_db()
    
    # Build query with role-based filter
    query = get_role_filter(current_user)
    
    # Add optional filters
    if status:
        query["status"] = status
    if industry:
        query["industry"] = industry
    if search:
        query["$or"] = query.get("$or", []) + [
            {"company_name": {"$regex": search, "$options": "i"}},
            {"primary_contact_name": {"$regex": search, "$options": "i"}}
        ]
    
    # Execute query
    total = await db.client_master.count_documents(query)
    clients = await db.client_master.find(
        query, {"_id": 0}
    ).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    
    return {
        "items": clients,
        "total": total,
        "skip": skip,
        "limit": limit
    }


@router.get("/stats/summary")
async def get_clients_stats(
    current_user: User = Depends(get_current_user)
):
    """Get client statistics summary."""
    db = get_db()
    
    # Build query with role-based filter
    query = get_role_filter(current_user)
    
    # Get all clients for stats
    clients = await db.client_master.find(query, {"_id": 0}).to_list(1000)
    
    # Calculate stats
    total_clients = len(clients)
    
    # Group by industry
    by_industry = {}
    for client in clients:
        ind = client.get("industry") or "Other"
        by_industry[ind] = by_industry.get(ind, 0) + 1
    
    # Calculate total revenue (from revenue_history if exists)
    total_revenue = 0
    for client in clients:
        if client.get("revenue_history"):
            for rev in client["revenue_history"]:
                total_revenue += rev.get("amount", 0)
        elif client.get("contract_value"):
            total_revenue += client["contract_value"]
    
    # Group by status
    by_status = {}
    for client in clients:
        status = client.get("status") or "active"
        by_status[status] = by_status.get(status, 0) + 1
    
    return {
        "total_clients": total_clients,
        "by_industry": by_industry,
        "by_status": by_status,
        "total_revenue": total_revenue
    }


@router.get("/{client_id}")
async def get_client_detail(
    client_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get single client details."""
    db = get_db()
    
    # Build query with role-based filter
    base_query = get_role_filter(current_user)
    query = {"id": client_id, **base_query}
    
    client = await db.client_master.find_one(query, {"_id": 0})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found or access denied")
    
    return client


@router.post("")
async def create_client(
    client_data: dict,
    current_user: User = Depends(get_current_user)
):
    """Create new client (Admin/Finance only)."""
    db = get_db()
    
    # Role check - only Admin/Finance can create
    allowed_roles = ['admin', 'finance_manager', 'finance_executive', 'accounts']
    if current_user.role not in allowed_roles:
        raise HTTPException(status_code=403, detail="Only Admin/Finance can create clients")
    
    # Validate required field
    if not client_data.get("company_name"):
        raise HTTPException(status_code=400, detail="Company name is required")
    
    # Check for duplicate
    existing = await db.client_master.find_one({
        "company_name": {"$regex": f"^{client_data['company_name']}$", "$options": "i"}
    })
    if existing:
        raise HTTPException(status_code=400, detail="A client with this company name already exists")
    
    # Build client document
    client_doc = {
        "id": str(uuid.uuid4()),
        "company_name": client_data.get("company_name"),
        "industry": client_data.get("industry", ""),
        "website": client_data.get("website", ""),
        "location": client_data.get("location", ""),
        "city": client_data.get("city", ""),
        "state": client_data.get("state", ""),
        "country": client_data.get("country", "India"),
        "address": client_data.get("address", ""),
        "business_start_date": client_data.get("business_start_date"),
        "sales_person_id": client_data.get("sales_person_id"),
        "sales_person_name": client_data.get("sales_person_name", ""),
        "notes": client_data.get("notes", ""),
        "contacts": [],
        "revenue_history": [],
        "status": "active",
        "created_from": "manual",
        "created_by": current_user.id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.client_master.insert_one(client_doc)
    
    # Return without _id
    return {k: v for k, v in client_doc.items() if k != "_id"}


@router.patch("/{client_id}")
async def update_client(
    client_id: str,
    update_data: dict,
    current_user: User = Depends(get_current_user)
):
    """Update client (Admin/Finance only)."""
    db = get_db()
    
    # Role check
    allowed_roles = ['admin', 'finance_manager', 'finance_executive', 'accounts']
    if current_user.role not in allowed_roles:
        raise HTTPException(status_code=403, detail="Only Admin/Finance can update clients")
    
    # Find client
    client = await db.client_master.find_one({"id": client_id}, {"_id": 0})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    # Build update
    update_fields = {}
    allowed_fields = [
        "company_name", "industry", "website", "location", "city", "state",
        "country", "address", "business_start_date", "sales_person_id",
        "sales_person_name", "notes", "status"
    ]
    
    for field in allowed_fields:
        if field in update_data:
            update_fields[field] = update_data[field]
    
    update_fields["updated_at"] = datetime.now(timezone.utc).isoformat()
    update_fields["updated_by"] = current_user.id
    
    await db.client_master.update_one(
        {"id": client_id},
        {"$set": update_fields}
    )
    
    return {"message": "Client updated successfully"}


@router.delete("/{client_id}")
async def deactivate_client(
    client_id: str,
    current_user: User = Depends(get_current_user)
):
    """Deactivate client (Admin only)."""
    db = get_db()
    
    # Only admin can deactivate
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only Admin can deactivate clients")
    
    # Find client
    client = await db.client_master.find_one({"id": client_id}, {"_id": 0})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    # Soft delete
    await db.client_master.update_one(
        {"id": client_id},
        {"$set": {
            "status": "inactive",
            "deactivated_at": datetime.now(timezone.utc).isoformat(),
            "deactivated_by": current_user.id,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    return {"message": "Client deactivated"}


@router.post("/{client_id}/contacts")
async def add_client_contact(
    client_id: str,
    contact_data: dict,
    current_user: User = Depends(get_current_user)
):
    """Add contact to client (Admin/Finance/Sales/Consulting can add)."""
    db = get_db()
    
    # Find client with role filter
    base_query = get_role_filter(current_user)
    query = {"id": client_id, **base_query}
    
    client = await db.client_master.find_one(query, {"_id": 0})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found or access denied")
    
    # Build contact
    contact = {
        "id": str(uuid.uuid4()),
        "name": contact_data.get("name"),
        "designation": contact_data.get("designation", ""),
        "email": contact_data.get("email", ""),
        "phone": contact_data.get("phone", ""),
        "is_primary": contact_data.get("is_primary", False),
        "added_by": current_user.id,
        "added_at": datetime.now(timezone.utc).isoformat()
    }
    
    # If marked as primary, unset other primaries
    if contact["is_primary"]:
        existing_contacts = client.get("contacts", [])
        for c in existing_contacts:
            c["is_primary"] = False
        await db.client_master.update_one(
            {"id": client_id},
            {"$set": {"contacts": existing_contacts}}
        )
    
    # Add contact
    await db.client_master.update_one(
        {"id": client_id},
        {
            "$push": {"contacts": contact},
            "$set": {"updated_at": datetime.now(timezone.utc).isoformat()}
        }
    )
    
    return {"message": "Contact added", "contact": contact}


@router.post("/{client_id}/revenue")
async def add_revenue_record(
    client_id: str,
    revenue_data: dict,
    current_user: User = Depends(get_current_user)
):
    """Add revenue record to client (Admin/Finance only)."""
    db = get_db()
    
    # Role check
    allowed_roles = ['admin', 'finance_manager', 'finance_executive', 'accounts']
    if current_user.role not in allowed_roles:
        raise HTTPException(status_code=403, detail="Only Admin/Finance can add revenue records")
    
    # Find client
    client = await db.client_master.find_one({"id": client_id}, {"_id": 0})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    # Build revenue record
    revenue = {
        "id": str(uuid.uuid4()),
        "year": revenue_data.get("year"),
        "quarter": revenue_data.get("quarter"),
        "amount": revenue_data.get("amount", 0),
        "currency": revenue_data.get("currency", "INR"),
        "notes": revenue_data.get("notes", ""),
        "recorded_by": current_user.id,
        "recorded_at": datetime.now(timezone.utc).isoformat()
    }
    
    # Add revenue
    await db.client_master.update_one(
        {"id": client_id},
        {
            "$push": {"revenue_history": revenue},
            "$set": {"updated_at": datetime.now(timezone.utc).isoformat()}
        }
    )
    
    return {"message": "Revenue record added", "revenue": revenue}
