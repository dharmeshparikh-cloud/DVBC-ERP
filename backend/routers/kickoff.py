"""
Kickoff Router - Kickoff Requests Workflow (Sales to Consulting Handoff)
"""

from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone
from typing import List, Optional
import uuid

from .models import (
    KickoffRequest, KickoffRequestCreate, KickoffRequestUpdate, 
    KickoffReturnRequest, User, UserRole, Project
)
from .deps import get_db
from .auth import get_current_user

router = APIRouter(prefix="/kickoff-requests", tags=["Kickoff Requests"])


@router.post("")
async def create_kickoff_request(
    kickoff_create: KickoffRequestCreate,
    current_user: User = Depends(get_current_user)
):
    """Create a new kickoff request (Sales to Consulting handoff)."""
    db = get_db()
    
    # Only sales roles can create kickoff requests
    if current_user.role not in ["admin", "executive", "account_manager", "manager"]:
        raise HTTPException(status_code=403, detail="Only sales roles can create kickoff requests")
    
    # Verify agreement exists
    agreement = await db.agreements.find_one({"id": kickoff_create.agreement_id}, {"_id": 0})
    if not agreement:
        raise HTTPException(status_code=404, detail="Agreement not found")
    
    # CRITICAL: Verify first installment payment before allowing kickoff request
    first_payment = await db.payment_verifications.find_one({
        "agreement_id": kickoff_create.agreement_id,
        "installment_number": 1,
        "status": "verified"
    })
    if not first_payment:
        raise HTTPException(
            status_code=400, 
            detail="First installment payment must be verified before creating kickoff request. Please record the advance payment first."
        )
    
    kickoff_dict = kickoff_create.model_dump()
    kickoff = KickoffRequest(
        **kickoff_dict,
        requested_by=current_user.id,
        requested_by_name=current_user.full_name
    )
    
    doc = kickoff.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    doc['updated_at'] = doc['updated_at'].isoformat()
    if doc.get('expected_start_date'):
        doc['expected_start_date'] = doc['expected_start_date'].isoformat()
    
    await db.kickoff_requests.insert_one(doc)
    
    # Create notification for PM if assigned
    if kickoff.assigned_pm_id:
        notification = {
            "id": str(uuid.uuid4()),
            "type": "kickoff_request",
            "recipient_id": kickoff.assigned_pm_id,
            "title": f"New Kickoff Request: {kickoff.project_name}",
            "message": f"A new project kickoff request has been submitted for {kickoff.client_name}",
            "kickoff_request_id": kickoff.id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "read": False
        }
        await db.notifications.insert_one(notification)
    
    return kickoff


@router.get("")
async def get_kickoff_requests(
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get kickoff requests (filtered by role)."""
    db = get_db()
    
    query = {}
    if status:
        query["status"] = status
    
    # Filter based on role
    if current_user.role in ["executive", "account_manager"]:
        query["requested_by"] = current_user.id
    elif current_user.role in ["project_manager"]:
        query["assigned_pm_id"] = current_user.id
    
    kickoffs = await db.kickoff_requests.find(query, {"_id": 0}).sort("created_at", -1).to_list(1000)
    
    for kickoff in kickoffs:
        if isinstance(kickoff.get('created_at'), str):
            kickoff['created_at'] = datetime.fromisoformat(kickoff['created_at'])
        if isinstance(kickoff.get('updated_at'), str):
            kickoff['updated_at'] = datetime.fromisoformat(kickoff['updated_at'])
    
    return kickoffs


@router.get("/{request_id}")
async def get_kickoff_request(
    request_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get a single kickoff request."""
    db = get_db()
    
    kickoff = await db.kickoff_requests.find_one({"id": request_id}, {"_id": 0})
    if not kickoff:
        raise HTTPException(status_code=404, detail="Kickoff request not found")
    
    return kickoff


@router.get("/{request_id}/details")
async def get_kickoff_request_details(
    request_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get detailed kickoff request with related data."""
    db = get_db()
    
    kickoff = await db.kickoff_requests.find_one({"id": request_id}, {"_id": 0})
    if not kickoff:
        raise HTTPException(status_code=404, detail="Kickoff request not found")
    
    # Get agreement details
    agreement = None
    if kickoff.get("agreement_id"):
        agreement = await db.agreements.find_one({"id": kickoff["agreement_id"]}, {"_id": 0})
    
    # Get lead details
    lead = None
    if kickoff.get("lead_id"):
        lead = await db.leads.find_one({"id": kickoff["lead_id"]}, {"_id": 0})
    
    # Get client details
    client = None
    if kickoff.get("client_id"):
        client = await db.clients.find_one({"id": kickoff["client_id"]}, {"_id": 0})
    
    # Get PM details
    pm = None
    if kickoff.get("assigned_pm_id"):
        pm = await db.users.find_one(
            {"id": kickoff["assigned_pm_id"]},
            {"_id": 0, "id": 1, "full_name": 1, "email": 1}
        )
    
    # Get project if created
    project = None
    if kickoff.get("project_id"):
        project = await db.projects.find_one({"id": kickoff["project_id"]}, {"_id": 0})
    
    # Get meeting history
    meetings = []
    if kickoff.get("lead_id"):
        meetings = await db.meetings.find(
            {"lead_id": kickoff["lead_id"]},
            {"_id": 0}
        ).sort("meeting_date", -1).limit(10).to_list(10)
    
    return {
        "kickoff_request": kickoff,
        "agreement": agreement,
        "lead": lead,
        "client": client,
        "assigned_pm": pm,
        "project": project,
        "meeting_history": meetings
    }


@router.put("/{request_id}")
async def update_kickoff_request(
    request_id: str,
    update_data: KickoffRequestUpdate,
    current_user: User = Depends(get_current_user)
):
    """Update a kickoff request."""
    db = get_db()
    
    kickoff = await db.kickoff_requests.find_one({"id": request_id}, {"_id": 0})
    if not kickoff:
        raise HTTPException(status_code=404, detail="Kickoff request not found")
    
    # Only creator, assigned PM, or admin can update
    if current_user.role != "admin" and current_user.id not in [kickoff.get("requested_by"), kickoff.get("assigned_pm_id")]:
        raise HTTPException(status_code=403, detail="Not authorized to update this request")
    
    update_dict = update_data.model_dump(exclude_unset=True)
    update_dict["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    if update_dict.get("expected_start_date"):
        update_dict["expected_start_date"] = update_dict["expected_start_date"].isoformat()
    
    await db.kickoff_requests.update_one({"id": request_id}, {"$set": update_dict})
    
    return {"message": "Kickoff request updated"}


@router.post("/{request_id}/return")
async def return_kickoff_request(
    request_id: str,
    return_data: KickoffReturnRequest,
    current_user: User = Depends(get_current_user)
):
    """Return a kickoff request to sales (PM action)."""
    db = get_db()
    
    if current_user.role not in ["admin", "project_manager", "principal_consultant", "manager"]:
        raise HTTPException(status_code=403, detail="Only PM roles can return kickoff requests")
    
    kickoff = await db.kickoff_requests.find_one({"id": request_id}, {"_id": 0})
    if not kickoff:
        raise HTTPException(status_code=404, detail="Kickoff request not found")
    
    if kickoff.get("status") not in ["pending", "accepted"]:
        raise HTTPException(status_code=400, detail="Can only return pending or accepted requests")
    
    await db.kickoff_requests.update_one(
        {"id": request_id},
        {"$set": {
            "status": "returned",
            "return_reason": return_data.return_reason,
            "return_notes": return_data.return_notes,
            "returned_by": current_user.id,
            "returned_by_name": current_user.full_name,
            "returned_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    # Notify requester
    notification = {
        "id": str(uuid.uuid4()),
        "type": "kickoff_returned",
        "recipient_id": kickoff.get("requested_by"),
        "title": f"Kickoff Request Returned: {kickoff.get('project_name')}",
        "message": f"Reason: {return_data.return_reason}",
        "kickoff_request_id": request_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "read": False
    }
    await db.notifications.insert_one(notification)
    
    return {"message": "Kickoff request returned to sales"}


@router.post("/{request_id}/resubmit")
async def resubmit_kickoff_request(
    request_id: str,
    current_user: User = Depends(get_current_user)
):
    """Resubmit a returned kickoff request."""
    db = get_db()
    
    kickoff = await db.kickoff_requests.find_one({"id": request_id}, {"_id": 0})
    if not kickoff:
        raise HTTPException(status_code=404, detail="Kickoff request not found")
    
    # Only original requester or admin can resubmit
    if current_user.role != "admin" and current_user.id != kickoff.get("requested_by"):
        raise HTTPException(status_code=403, detail="Only the original requester can resubmit")
    
    if kickoff.get("status") != "returned":
        raise HTTPException(status_code=400, detail="Can only resubmit returned requests")
    
    await db.kickoff_requests.update_one(
        {"id": request_id},
        {"$set": {
            "status": "pending",
            "return_reason": None,
            "return_notes": None,
            "returned_by": None,
            "returned_by_name": None,
            "returned_at": None,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    # Notify PM if assigned
    if kickoff.get("assigned_pm_id"):
        notification = {
            "id": str(uuid.uuid4()),
            "type": "kickoff_resubmitted",
            "recipient_id": kickoff.get("assigned_pm_id"),
            "title": f"Kickoff Request Resubmitted: {kickoff.get('project_name')}",
            "message": f"The kickoff request for {kickoff.get('client_name')} has been resubmitted",
            "kickoff_request_id": request_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "read": False
        }
        await db.notifications.insert_one(notification)
    
    return {"message": "Kickoff request resubmitted"}


@router.post("/{request_id}/accept")
async def accept_kickoff_request(
    request_id: str,
    current_user: User = Depends(get_current_user)
):
    """Accept a kickoff request and create a project (PM action)."""
    db = get_db()
    
    if current_user.role not in ["admin", "project_manager", "principal_consultant", "manager"]:
        raise HTTPException(status_code=403, detail="Only PM roles can accept kickoff requests")
    
    kickoff = await db.kickoff_requests.find_one({"id": request_id}, {"_id": 0})
    if not kickoff:
        raise HTTPException(status_code=404, detail="Kickoff request not found")
    
    if kickoff.get("status") != "pending":
        raise HTTPException(status_code=400, detail="Can only accept pending requests")
    
    # Get agreement to link pricing plan and SOW
    agreement = await db.agreements.find_one({"id": kickoff.get("agreement_id")}, {"_id": 0})
    pricing_plan_id = agreement.get('pricing_plan_id') if agreement else None
    
    # Create project from kickoff request - SET STATUS TO ACTIVE
    project = Project(
        name=kickoff.get("project_name"),
        client_name=kickoff.get("client_name"),
        lead_id=kickoff.get("lead_id"),
        agreement_id=kickoff.get("agreement_id"),
        project_type=kickoff.get("project_type", "mixed"),
        start_date=datetime.now(timezone.utc),
        total_meetings_committed=kickoff.get("total_meetings", 0),
        project_value=kickoff.get("project_value"),
        created_by=current_user.id,
        status="active"  # Auto-set to active on kickoff acceptance
    )
    
    project_doc = project.model_dump()
    project_doc['start_date'] = project_doc['start_date'].isoformat()
    project_doc['created_at'] = project_doc['created_at'].isoformat()
    project_doc['updated_at'] = project_doc['updated_at'].isoformat()
    
    # Add pricing_plan_id to project for SOW linkage
    if pricing_plan_id:
        project_doc['pricing_plan_id'] = pricing_plan_id
    
    await db.projects.insert_one(project_doc)
    
    # Link enhanced_sow to project via agreement_id
    if kickoff.get("agreement_id"):
        await db.enhanced_sow.update_many(
            {"agreement_id": kickoff.get("agreement_id")},
            {"$set": {
                "project_id": project.id,
                "consulting_kickoff_complete": True,
                "consulting_kickoff_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }}
        )
        
        # Also try to link via pricing_plan_id if agreement_id match didn't work
        if pricing_plan_id:
            await db.enhanced_sow.update_many(
                {"pricing_plan_id": pricing_plan_id, "project_id": {"$exists": False}},
                {"$set": {
                    "project_id": project.id,
                    "agreement_id": kickoff.get("agreement_id"),
                    "consulting_kickoff_complete": True,
                    "consulting_kickoff_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }}
            )
    
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
    
    # Notify requester
    notification = {
        "id": str(uuid.uuid4()),
        "type": "kickoff_accepted",
        "recipient_id": kickoff.get("requested_by"),
        "title": f"Kickoff Request Accepted: {kickoff.get('project_name')}",
        "message": f"Project created and ready for team assignment",
        "kickoff_request_id": request_id,
        "project_id": project.id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "read": False
    }
    await db.notifications.insert_one(notification)
    
    # Notify HR about new project (for staffing)
    hr_users = await db.users.find(
        {"role": {"$in": ["hr_manager"]}},
        {"_id": 0, "id": 1}
    ).to_list(10)
    
    for hr in hr_users:
        hr_notification = {
            "id": str(uuid.uuid4()),
            "type": "new_project_staffing",
            "recipient_id": hr["id"],
            "title": f"New Project Created: {project.name}",
            "message": f"A new project for {kickoff.get('client_name')} needs staffing",
            "project_id": project.id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "read": False
        }
        await db.notifications.insert_one(hr_notification)
    
    return {
        "message": "Kickoff request accepted",
        "project_id": project.id
    }


@router.post("/{request_id}/reject")
async def reject_kickoff_request(
    request_id: str,
    reason: str,
    current_user: User = Depends(get_current_user)
):
    """Reject a kickoff request (PM action)."""
    db = get_db()
    
    if current_user.role not in ["admin", "project_manager", "principal_consultant", "manager"]:
        raise HTTPException(status_code=403, detail="Only PM roles can reject kickoff requests")
    
    kickoff = await db.kickoff_requests.find_one({"id": request_id}, {"_id": 0})
    if not kickoff:
        raise HTTPException(status_code=404, detail="Kickoff request not found")
    
    await db.kickoff_requests.update_one(
        {"id": request_id},
        {"$set": {
            "status": "rejected",
            "return_reason": reason,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    # Notify requester
    notification = {
        "id": str(uuid.uuid4()),
        "type": "kickoff_rejected",
        "recipient_id": kickoff.get("requested_by"),
        "title": f"Kickoff Request Rejected: {kickoff.get('project_name')}",
        "message": f"Reason: {reason}",
        "kickoff_request_id": request_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "read": False
    }
    await db.notifications.insert_one(notification)
    
    return {"message": "Kickoff request rejected"}
