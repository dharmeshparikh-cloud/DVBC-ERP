"""
Kickoff Router - Kickoff Requests Workflow (Sales to Consulting Handoff)

DUAL APPROVAL FLOW:
1. Principal Consultant (ONLY) approves internally → Project ID generated (PROJ-YYYYMMDD-XXXX)
2. Client receives email → Approves with confirmed start date
3. Client user account created (5-digit ID: 98XXX)
4. Project activated, consultant can be assigned manually
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import HTMLResponse
from datetime import datetime, timezone
from dateutil.relativedelta import relativedelta
from typing import List, Optional
import uuid
import os
import secrets
import string
from passlib.context import CryptContext

from .models import (
    KickoffRequest, KickoffRequestCreate, KickoffRequestUpdate, 
    KickoffReturnRequest, User, UserRole, Project, ClientUser, ProjectAssignment
)
from .deps import get_db, SALES_EXECUTIVE_ROLES, PRINCIPAL_CONSULTANT_ROLES
from .auth import get_current_user
from services.approval_notifications import send_approval_notification, notify_requester_on_action
from services.email_service import send_email
from services.funnel_notifications import kickoff_sent_email, kickoff_accepted_email, get_kickoff_notification_emails
from websocket_manager import get_manager as get_ws_manager

router = APIRouter(prefix="/kickoff-requests", tags=["Kickoff Requests"])

APP_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://lead-kickoff-flow.preview.emergentagent.com").replace("/api", "")
LOGO_URL = "https://dvconsulting.co.in/wp-content/uploads/2020/02/logov4-min.png"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ============== HELPER FUNCTIONS ==============

async def generate_project_id(db) -> str:
    """Generate Project ID in format: PROJ-YYYYMMDD-XXXX"""
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    prefix = f"PROJ-{today}-"
    
    # Find highest sequence for today
    existing = await db.projects.find(
        {"id": {"$regex": f"^{prefix}"}},
        {"_id": 0, "id": 1}
    ).to_list(1000)
    
    if existing:
        sequences = [int(p["id"].split("-")[-1]) for p in existing if p["id"].split("-")[-1].isdigit()]
        next_seq = max(sequences) + 1 if sequences else 1
    else:
        next_seq = 1
    
    return f"{prefix}{next_seq:04d}"


async def generate_client_id(db) -> str:
    """Generate Client ID: 5-digit starting from 98000"""
    # Find highest client_id starting with 98
    existing = await db.client_users.find(
        {"client_id": {"$regex": "^98"}},
        {"_id": 0, "client_id": 1}
    ).sort("client_id", -1).to_list(1)
    
    if existing:
        last_id = int(existing[0]["client_id"])
        next_id = last_id + 1
    else:
        next_id = 98000  # Starting point
    
    return str(next_id)


def generate_random_password(length: int = 12) -> str:
    """Generate a secure random password."""
    alphabet = string.ascii_letters + string.digits + "!@#$%"
    return ''.join(secrets.choice(alphabet) for _ in range(length))


@router.post("")
async def create_kickoff_request(
    kickoff_create: KickoffRequestCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    """Create a new kickoff request (Sales to Consulting handoff).
    Sends real-time email + WebSocket notification to assigned Senior/Principal Consultant.
    Also sends HTML summary email to sales managers.
    """
    db = get_db()
    
    # Only sales roles can create kickoff requests
    if current_user.role not in SALES_EXECUTIVE_ROLES:
        raise HTTPException(status_code=403, detail="Only sales roles can create kickoff requests")
    
    # Verify agreement exists
    agreement = await db.agreements.find_one({"id": kickoff_create.agreement_id}, {"_id": 0})
    if not agreement:
        raise HTTPException(status_code=404, detail="Agreement not found")
    
    # Get lead details
    lead = None
    if agreement.get("lead_id"):
        lead = await db.leads.find_one({"id": agreement["lead_id"]}, {"_id": 0})
    
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
    
    # Add lead_id to kickoff
    kickoff_doc = kickoff.model_dump()
    kickoff_doc['lead_id'] = agreement.get("lead_id")
    kickoff_doc['created_at'] = kickoff_doc['created_at'].isoformat()
    kickoff_doc['updated_at'] = kickoff_doc['updated_at'].isoformat()
    if kickoff_doc.get('expected_start_date'):
        kickoff_doc['expected_start_date'] = kickoff_doc['expected_start_date'].isoformat()
    
    await db.kickoff_requests.insert_one(kickoff_doc)
    
    # Get requester email
    requester_user = await db.users.find_one({"id": current_user.id})
    requester_email = requester_user.get("email", "") if requester_user else ""
    
    # Get PM details
    pm_user = None
    pm_name = "Not Assigned"
    if kickoff.assigned_pm_id:
        pm_user = await db.users.find_one(
            {"id": kickoff.assigned_pm_id}, 
            {"_id": 0, "id": 1, "full_name": 1, "email": 1}
        )
        if pm_user:
            pm_name = pm_user.get("full_name", "Project Manager")
    
    # Get meeting count and key commitments for the lead
    meetings_count = 0
    key_commitments = []
    if lead:
        meetings = await db.meetings.find({"lead_id": lead.get("id")}, {"_id": 0}).to_list(50)
        meetings_count = len(meetings)
        for m in meetings:
            key_commitments.extend(m.get("key_commitments", []) or [])
        key_commitments = list(set([k for k in key_commitments if k]))[:5]
    
    # Send real-time approval notification (email + WebSocket) to PM if assigned
    if pm_user:
        ws_manager = get_ws_manager()
        kickoff_details = {
            "Project Name": kickoff.project_name,
            "Client": kickoff.client_name,
            "Project Type": kickoff.project_type or "Mixed",
            "Project Value": f"₹{kickoff.project_value:,.0f}" if kickoff.project_value else "Not specified",
            "Expected Start": str(kickoff.expected_start_date)[:10] if kickoff.expected_start_date else "TBD",
            "Total Meetings": kickoff.total_meetings or "Not specified"
        }
        
        try:
            await send_approval_notification(
                db=db,
                ws_manager=ws_manager,
                record_type="kickoff",
                record_id=kickoff.id,
                requester_id=current_user.id,
                requester_name=current_user.full_name,
                requester_email=requester_email,
                approver_id=pm_user["id"],
                approver_name=pm_user.get("full_name", "Project Manager"),
                approver_email=pm_user.get("email", ""),
                details=kickoff_details,
                link="/kickoff-requests"
            )
        except Exception as e:
            print(f"Error sending kickoff notification to PM: {e}")
    
    # Get client email
    client_email = lead.get("email", "") if lead else ""
    
    # Send HTML summary email to team + client in background
    async def send_kickoff_sent_notification():
        try:
            # Get emails: Lead Owner, Manager, Sales Head, Senior Manager, Principal Consultant
            team_emails = await get_kickoff_notification_emails(db, current_user.id)
            
            email_data = kickoff_sent_email(
                lead_name=f"{lead.get('first_name', '')} {lead.get('last_name', '')}".strip() if lead else "N/A",
                company=kickoff.client_name or (lead.get("company") if lead else "Unknown"),
                project_name=kickoff.project_name,
                project_type=kickoff.project_type or "Mixed",
                start_date=str(kickoff.expected_start_date)[:10] if kickoff.expected_start_date else "TBD",
                assigned_pm=pm_name,
                contract_value=kickoff.project_value or 0,
                currency="INR",
                meetings_count=meetings_count,
                key_commitments=key_commitments,
                salesperson_name=current_user.full_name,
                approver_name=pm_name,
                client_email=client_email,
                app_url=APP_URL
            )
            
            # Send to team
            for email in team_emails:
                await send_email(
                    to_email=email,
                    subject=email_data["subject"],
                    html_content=email_data["html"],
                    plain_content=email_data["plain"]
                )
            
            # Send to client
            if client_email:
                await send_email(
                    to_email=client_email,
                    subject=f"Project Kickoff Initiated - {kickoff.project_name}",
                    html_content=email_data["html"],
                    plain_content=email_data["plain"]
                )
        except Exception as e:
            print(f"Failed to send kickoff sent notification: {e}")
    
    background_tasks.add_task(send_kickoff_sent_notification)
    
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
    if current_user.role in ["executive", "sales_manager"]:
        query["requested_by"] = current_user.id
    elif current_user.role in ["principal_consultant", "senior_consultant"]:
        query["assigned_pm_id"] = current_user.id
    
    kickoffs = await db.kickoff_requests.find(query, {"_id": 0}).sort("created_at", -1).to_list(1000)
    
    for kickoff in kickoffs:
        if isinstance(kickoff.get('created_at'), str):
            kickoff['created_at'] = datetime.fromisoformat(kickoff['created_at'])
        if isinstance(kickoff.get('updated_at'), str):
            kickoff['updated_at'] = datetime.fromisoformat(kickoff['updated_at'])
    
    return kickoffs


@router.get("/eligible-pms/list")
async def get_eligible_pms(current_user: User = Depends(get_current_user)):
    """
    Get list of consultants eligible to approve kickoff requests.
    Only Senior Consultants and Principal Consultants (NOT PM, NOT regular Consultant).
    """
    db = get_db()
    
    # Only Senior Consultant and Principal Consultant can approve kickoffs
    eligible_roles = ["senior_consultant", "principal_consultant"]
    
    consultants = await db.users.find(
        {"role": {"$in": eligible_roles}, "is_active": True},
        {"_id": 0, "id": 1, "full_name": 1, "email": 1, "role": 1}
    ).to_list(500)
    
    # Filter to only those who have reportees (are reporting managers for someone)
    eligible_pms = []
    for consultant in consultants:
        # Get employee record for this user to find their employee_id
        employee = await db.employees.find_one(
            {"user_id": consultant["id"]},
            {"_id": 0, "id": 1, "employee_id": 1}
        )
        
        if not employee:
            continue
            
        # Check if anyone reports to this employee (by employee.id or employee_id code)
        reportee_count = await db.employees.count_documents({
            "$or": [
                {"reporting_manager_id": employee.get("id")},
                {"reporting_manager_id": employee.get("employee_id")}
            ],
            "is_active": True
        })
        
        if reportee_count > 0:
            consultant["reportee_count"] = reportee_count
            consultant["employee_id"] = employee.get("employee_id")
            eligible_pms.append(consultant)
    
    return {
        "eligible_pms": eligible_pms,
        "total": len(eligible_pms)
    }


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
    """Get detailed kickoff request with related data including all sales funnel steps."""
    db = get_db()
    
    kickoff = await db.kickoff_requests.find_one({"id": request_id}, {"_id": 0})
    if not kickoff:
        raise HTTPException(status_code=404, detail="Kickoff request not found")
    
    # Get agreement details
    agreement = None
    if kickoff.get("agreement_id"):
        agreement = await db.agreements.find_one({"id": kickoff["agreement_id"]}, {"_id": 0})
    
    # Get lead details - try from kickoff first, then from agreement
    lead = None
    lead_id = kickoff.get("lead_id")
    if not lead_id and agreement:
        lead_id = agreement.get("lead_id")
    if lead_id:
        lead = await db.leads.find_one({"id": lead_id}, {"_id": 0})
    
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
    
    # Get ALL meeting history with full MOM details
    meetings = []
    client_expectations_summary = []
    key_commitments_summary = []
    total_meetings_held = 0
    
    if lead_id:
        meetings = await db.meetings.find(
            {"lead_id": lead_id},
            {"_id": 0}
        ).sort("meeting_date", -1).to_list(50)
        
        total_meetings_held = len(meetings)
        
        # Extract client expectations and key commitments from all meetings
        for meeting in meetings:
            if meeting.get("client_expectations"):
                for exp in meeting["client_expectations"]:
                    if exp and exp not in client_expectations_summary:
                        client_expectations_summary.append(exp)
            if meeting.get("key_commitments"):
                for com in meeting["key_commitments"]:
                    if com and com not in key_commitments_summary:
                        key_commitments_summary.append(com)
    
    # Get pricing plan details
    pricing_plan = None
    if lead_id:
        pricing_plan = await db.pricing_plans.find_one({"lead_id": lead_id}, {"_id": 0})
    if not pricing_plan and agreement:
        pricing_plan = await db.pricing_plans.find_one({"id": agreement.get("pricing_plan_id")}, {"_id": 0})
    
    # Get SOW details
    sow = None
    if lead_id:
        sow = await db.enhanced_sows.find_one({"lead_id": lead_id}, {"_id": 0})
        if not sow:
            sow = await db.sows.find_one({"lead_id": lead_id}, {"_id": 0})
    
    # Get quotation details
    quotation = None
    if lead_id:
        quotation = await db.quotations.find_one({"lead_id": lead_id}, {"_id": 0})
    
    # Get payment details
    payments = []
    if agreement:
        payments = await db.payment_verifications.find(
            {"agreement_id": agreement.get("id")},
            {"_id": 0}
        ).to_list(20)
    
    # Build funnel steps summary for reviewer
    funnel_steps_summary = {
        "lead_capture": {
            "completed": lead is not None,
            "data": {
                "company": lead.get("company") if lead else None,
                "contact": f"{lead.get('first_name', '')} {lead.get('last_name', '')}".strip() if lead else None,
                "email": lead.get("email") if lead else None,
                "phone": lead.get("phone") if lead else None,
                "source": lead.get("source") if lead else None
            } if lead else None
        },
        "meetings": {
            "completed": total_meetings_held > 0,
            "count": total_meetings_held,
            "data": {
                "total_meetings": total_meetings_held,
                "client_expectations": client_expectations_summary[:5],  # Top 5
                "key_commitments": key_commitments_summary[:5]  # Top 5
            }
        },
        "pricing_plan": {
            "completed": pricing_plan is not None,
            "data": {
                "id": pricing_plan.get("id") if pricing_plan else None,
                "total": pricing_plan.get("grand_total", 0) if pricing_plan else 0,
                "duration_months": pricing_plan.get("project_duration_months") if pricing_plan else None,
                "project_type": pricing_plan.get("project_type") if pricing_plan else None
            } if pricing_plan else None
        },
        "sow": {
            "completed": sow is not None,
            "data": {
                "id": sow.get("id") if sow else None,
                "scope_items_count": len(sow.get("scope_items", [])) if sow else 0,
                "deliverables_count": len(sow.get("deliverables", [])) if sow else 0
            } if sow else None
        },
        "quotation": {
            "completed": quotation is not None,
            "data": {
                "id": quotation.get("id") if quotation else None,
                "number": quotation.get("quotation_number") if quotation else None,
                "total": quotation.get("total_amount", 0) if quotation else 0
            } if quotation else None
        },
        "agreement": {
            "completed": agreement is not None,
            "data": {
                "id": agreement.get("id") if agreement else None,
                "number": agreement.get("agreement_number") if agreement else None,
                "status": agreement.get("status") if agreement else None,
                "signed_date": agreement.get("signed_date") if agreement else None
            } if agreement else None
        },
        "payments": {
            "completed": len(payments) > 0,
            "count": len(payments),
            "data": {
                "total_paid": sum(p.get("amount", 0) for p in payments if p.get("status") == "verified"),
                "verified_count": len([p for p in payments if p.get("status") == "verified"])
            }
        }
    }
    
    return {
        "kickoff_request": kickoff,
        "agreement": agreement,
        "lead": lead,
        "client": client,
        "assigned_pm": pm,
        "project": project,
        "meeting_history": meetings,
        "total_meetings_held": total_meetings_held,
        "client_expectations_summary": client_expectations_summary,
        "key_commitments_summary": key_commitments_summary,
        "pricing_plan": pricing_plan,
        "sow": sow,
        "quotation": quotation,
        "payments": payments,
        "funnel_steps_summary": funnel_steps_summary
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
    """Return a kickoff request to sales (Principal Consultant action)."""
    db = get_db()
    
    # Only Principal Consultant can return kickoffs
    if current_user.role not in PRINCIPAL_CONSULTANT_ROLES:
        raise HTTPException(status_code=403, detail="Only Principal Consultant can return kickoff requests")
    
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
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    """
    INTERNAL APPROVAL - Principal Consultant ONLY.
    Step 1 of dual approval flow.
    
    When approved:
    - Project ID generated (PROJ-YYYYMMDD-XXXX)
    - Status: internal_approved
    - Sales team notified
    - Client receives approval email
    """
    db = get_db()
    
    # ONLY Principal Consultant can approve kickoffs
    if current_user.role not in PRINCIPAL_CONSULTANT_ROLES:
        raise HTTPException(
            status_code=403, 
            detail="Only Principal Consultant can approve kickoff requests internally"
        )
    
    kickoff = await db.kickoff_requests.find_one({"id": request_id}, {"_id": 0})
    if not kickoff:
        raise HTTPException(status_code=404, detail="Kickoff request not found")
    
    # Can only approve pending requests
    if kickoff.get("status") != "pending":
        raise HTTPException(status_code=400, detail=f"Cannot approve request with status: {kickoff.get('status')}")
    
    # Check if already internally approved
    if kickoff.get("internal_approved"):
        raise HTTPException(status_code=400, detail="This kickoff has already been internally approved")
    
    # Generate Project ID (PROJ-YYYYMMDD-XXXX)
    project_id = await generate_project_id(db)
    
    # Generate client approval token
    client_approval_token = str(uuid.uuid4())
    
    # Update kickoff with internal approval
    await db.kickoff_requests.update_one(
        {"id": request_id},
        {"$set": {
            "internal_approved": True,
            "internal_approved_by": current_user.id,
            "internal_approved_by_name": current_user.full_name,
            "internal_approved_at": datetime.now(timezone.utc).isoformat(),
            "project_id": project_id,
            "client_approval_token": client_approval_token,
            "status": "internal_approved",
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    # Get lead details for client email
    lead = None
    client_email = kickoff.get("client_email")
    if kickoff.get("lead_id"):
        lead = await db.leads.find_one({"id": kickoff["lead_id"]}, {"_id": 0})
        if lead and not client_email:
            client_email = lead.get("email", "")
    
    # Notify Sales Team - Project approved
    notification = {
        "id": str(uuid.uuid4()),
        "type": "kickoff_internal_approved",
        "recipient_id": kickoff.get("requested_by"),
        "title": f"✅ Project Approved: {project_id}",
        "message": f"Project '{kickoff.get('project_name')}' approved by {current_user.full_name}. Awaiting client confirmation.",
        "kickoff_request_id": request_id,
        "project_id": project_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "read": False
    }
    await db.notifications.insert_one(notification)
    
    # Send email to client for approval
    if client_email:
        async def send_client_approval_email():
            try:
                approval_link = f"{APP_URL}/client-approval/{client_approval_token}"
                expected_start = str(kickoff.get('expected_start_date', 'TBD'))[:10]
                
                html_content = f"""
                <!DOCTYPE html>
                <html>
                <head><meta charset="utf-8"></head>
                <body style="margin: 0; padding: 0; font-family: 'Segoe UI', Arial, sans-serif; background-color: #f5f5f5;">
                    <table role="presentation" style="width: 100%; border-collapse: collapse;">
                        <tr>
                            <td align="center" style="padding: 40px 20px;">
                                <table role="presentation" style="width: 100%; max-width: 600px; background: #fff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                                    
                                    <!-- Header -->
                                    <tr>
                                        <td style="background: #f3f4f6; padding: 30px; text-align: center;">
                                            <img src="{LOGO_URL}" alt="D&V Business Consulting" style="height: 100px; width: auto;">
                                        </td>
                                    </tr>
                                    
                                    <!-- Badge -->
                                    <tr>
                                        <td style="padding: 30px 40px 0; text-align: center;">
                                            <span style="display: inline-block; background: #10b981; color: white; padding: 10px 25px; border-radius: 25px; font-weight: bold;">
                                                PROJECT APPROVED
                                            </span>
                                        </td>
                                    </tr>
                                    
                                    <!-- Title -->
                                    <tr>
                                        <td style="padding: 25px 40px 10px; text-align: center;">
                                            <h1 style="margin: 0; color: #1a1a2e; font-size: 24px;">
                                                Your Project is Ready!
                                            </h1>
                                        </td>
                                    </tr>
                                    
                                    <!-- Content -->
                                    <tr>
                                        <td style="padding: 10px 40px 30px;">
                                            <p style="color: #4b5563; font-size: 15px; line-height: 1.6;">
                                                Dear <strong>{kickoff.get('client_name')}</strong>,
                                            </p>
                                            <p style="color: #4b5563; font-size: 15px; line-height: 1.6;">
                                                We are pleased to inform you that your project has been approved by our Principal Consultant, <strong>{current_user.full_name}</strong>.
                                            </p>
                                            
                                            <!-- Project Details Box -->
                                            <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0;">
                                                <h3 style="margin: 0 0 15px; color: #1a1a2e; font-size: 16px;">Project Details</h3>
                                                <table style="width: 100%; font-size: 14px;">
                                                    <tr>
                                                        <td style="padding: 8px 0; color: #6b7280;">Project ID:</td>
                                                        <td style="padding: 8px 0; color: #1a1a2e; font-weight: bold;">{project_id}</td>
                                                    </tr>
                                                    <tr>
                                                        <td style="padding: 8px 0; color: #6b7280;">Project Name:</td>
                                                        <td style="padding: 8px 0; color: #1a1a2e;">{kickoff.get('project_name')}</td>
                                                    </tr>
                                                    <tr>
                                                        <td style="padding: 8px 0; color: #6b7280;">Type:</td>
                                                        <td style="padding: 8px 0; color: #1a1a2e;">{kickoff.get('project_type', 'Mixed').title()}</td>
                                                    </tr>
                                                    <tr>
                                                        <td style="padding: 8px 0; color: #6b7280;">Proposed Start Date:</td>
                                                        <td style="padding: 8px 0; color: #1a1a2e;">{expected_start}</td>
                                                    </tr>
                                                    <tr>
                                                        <td style="padding: 8px 0; color: #6b7280;">Contract Value:</td>
                                                        <td style="padding: 8px 0; color: #1a1a2e; font-weight: bold;">₹{kickoff.get('project_value', 0):,.0f}</td>
                                                    </tr>
                                                </table>
                                            </div>
                                            
                                            <p style="color: #4b5563; font-size: 15px; line-height: 1.6;">
                                                Please click the button below to <strong>confirm the project start date</strong> and activate your project:
                                            </p>
                                        </td>
                                    </tr>
                                    
                                    <!-- CTA Button -->
                                    <tr>
                                        <td style="padding: 0 40px 30px; text-align: center;">
                                            <a href="{approval_link}" style="display: inline-block; background: #10b981; color: white; padding: 16px 50px; text-decoration: none; border-radius: 8px; font-weight: bold; font-size: 16px;">
                                                ✓ Confirm & Approve Project
                                            </a>
                                        </td>
                                    </tr>
                                    
                                    <!-- Note -->
                                    <tr>
                                        <td style="padding: 0 40px 30px;">
                                            <div style="background: #fef3c7; padding: 15px; border-radius: 8px; border-left: 4px solid #f59e0b;">
                                                <p style="margin: 0; color: #92400e; font-size: 13px;">
                                                    <strong>What happens next?</strong><br>
                                                    Once you approve, you will receive your NETRA ERP login credentials to track your project progress, view documents, and communicate with your assigned consultant.
                                                </p>
                                            </div>
                                        </td>
                                    </tr>
                                    
                                    <!-- Footer -->
                                    <tr>
                                        <td style="background: #f8f9fa; padding: 25px 40px; text-align: center; border-top: 1px solid #e9ecef;">
                                            <p style="margin: 0 0 10px; color: #6c757d; font-size: 12px;">
                                                This is an automated notification from NETRA ERP
                                            </p>
                                            <p style="margin: 0; color: #adb5bd; font-size: 11px;">
                                                © {datetime.now().year} D&V Business Consulting. All rights reserved.
                                            </p>
                                        </td>
                                    </tr>
                                    
                                </table>
                            </td>
                        </tr>
                    </table>
                </body>
                </html>
                """
                
                await send_email(
                    to_email=client_email,
                    subject=f"✅ Project Approved: {project_id} - Please Confirm Start Date",
                    html_content=html_content,
                    plain_content=f"Your project {project_id} has been approved. Please confirm: {approval_link}"
                )
            except Exception as e:
                print(f"Failed to send client approval email: {e}")
        
        background_tasks.add_task(send_client_approval_email)
    
    # Send internal notification email (New Project Added)
    async def send_internal_notification():
        try:
            # Get all consulting team emails
            consulting_team = await db.users.find(
                {"role": {"$in": ["principal_consultant", "senior_consultant", "consultant", "lean_consultant"]}},
                {"_id": 0, "email": 1}
            ).to_list(100)
            
            team_emails = [u["email"] for u in consulting_team if u.get("email")]
            
            # Also get HR Manager emails
            hr_managers = await db.users.find(
                {"role": "hr_manager"},
                {"_id": 0, "email": 1}
            ).to_list(10)
            team_emails.extend([u["email"] for u in hr_managers if u.get("email")])
            
            for email in team_emails:
                await send_email(
                    to_email=email,
                    subject=f"🆕 New Project Added: {project_id} - {kickoff.get('project_name')}",
                    html_content=f"""
                    <html>
                    <body style="font-family: Arial; padding: 20px;">
                        <h2>New Project Added to System</h2>
                        <p>A new project has been internally approved and is awaiting client confirmation.</p>
                        <div style="background: #f5f5f5; padding: 15px; border-radius: 8px;">
                            <p><strong>Project ID:</strong> {project_id}</p>
                            <p><strong>Client:</strong> {kickoff.get('client_name')}</p>
                            <p><strong>Project:</strong> {kickoff.get('project_name')}</p>
                            <p><strong>Approved By:</strong> {current_user.full_name}</p>
                        </div>
                    </body>
                    </html>
                    """,
                    plain_content=f"New Project: {project_id} - {kickoff.get('project_name')}"
                )
        except Exception as e:
            print(f"Failed to send internal notification: {e}")
    
    background_tasks.add_task(send_internal_notification)
    
    return {
        "message": f"Project approved! Project ID: {project_id}. Awaiting client confirmation.",
        "status": "internal_approved",
        "project_id": project_id,
        "client_approval_pending": True,
        "client_email": client_email
    }


@router.get("/client-approve/{token}")
async def client_approve_kickoff_page(token: str):
    """
    CLIENT APPROVAL PAGE - Step 2 of dual approval.
    Shows project details and allows client to confirm start date.
    """
    db = get_db()
    
    kickoff = await db.kickoff_requests.find_one({"client_approval_token": token}, {"_id": 0})
    if not kickoff:
        return HTMLResponse(content="""
            <!DOCTYPE html>
            <html>
            <head><title>Invalid Link</title></head>
            <body style="font-family: Arial; text-align: center; padding: 50px; background: #f5f5f5;">
                <div style="max-width: 500px; margin: 0 auto; background: white; padding: 40px; border-radius: 12px;">
                    <h1 style="color: #ef4444;">❌ Invalid or Expired Link</h1>
                    <p style="color: #666;">This approval link is no longer valid or has expired.</p>
                    <p style="color: #999; font-size: 13px;">Please contact your D&V representative for assistance.</p>
                </div>
            </body>
            </html>
        """, status_code=404)
    
    if kickoff.get("client_approved"):
        return HTMLResponse(content=f"""
            <!DOCTYPE html>
            <html>
            <head><title>Already Approved</title></head>
            <body style="font-family: Arial; text-align: center; padding: 50px; background: #f5f5f5;">
                <div style="max-width: 500px; margin: 0 auto; background: white; padding: 40px; border-radius: 12px;">
                    <h1 style="color: #10b981;">✅ Already Approved</h1>
                    <p style="color: #666;">You have already approved this project.</p>
                    <p><strong>Project ID:</strong> {kickoff.get('project_id')}</p>
                    <p style="color: #999; font-size: 13px;">Check your email for NETRA login credentials.</p>
                </div>
            </body>
            </html>
        """)
    
    expected_start = str(kickoff.get('expected_start_date', ''))[:10] if kickoff.get('expected_start_date') else datetime.now().strftime('%Y-%m-%d')
    
    return HTMLResponse(content=f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Confirm Project - D&V Business Consulting</title>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body {{ font-family: 'Segoe UI', Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }}
                .container {{ max-width: 600px; margin: 0 auto; background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
                .header {{ background: #f3f4f6; padding: 30px; text-align: center; }}
                .header img {{ height: 80px; }}
                .content {{ padding: 30px 40px; }}
                .badge {{ display: inline-block; background: #10b981; color: white; padding: 8px 20px; border-radius: 20px; font-weight: bold; margin-bottom: 20px; }}
                .details {{ background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0; }}
                .details table {{ width: 100%; border-collapse: collapse; }}
                .details td {{ padding: 10px 0; }}
                .details td:first-child {{ color: #6b7280; }}
                .details td:last-child {{ color: #1a1a2e; font-weight: 500; }}
                .form-group {{ margin: 20px 0; }}
                .form-group label {{ display: block; margin-bottom: 8px; color: #374151; font-weight: 500; }}
                .form-group input {{ width: 100%; padding: 12px; border: 1px solid #d1d5db; border-radius: 8px; font-size: 16px; box-sizing: border-box; }}
                .btn {{ display: block; width: 100%; padding: 16px; background: #10b981; color: white; border: none; border-radius: 8px; font-size: 16px; font-weight: bold; cursor: pointer; margin-top: 20px; }}
                .btn:hover {{ background: #059669; }}
                .footer {{ background: #f8f9fa; padding: 20px; text-align: center; border-top: 1px solid #e5e7eb; }}
                .footer p {{ margin: 5px 0; color: #9ca3af; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <img src="{LOGO_URL}" alt="D&V Business Consulting">
                </div>
                <div class="content">
                    <div style="text-align: center;">
                        <span class="badge">CONFIRM PROJECT</span>
                        <h2 style="margin: 20px 0 10px; color: #1a1a2e;">Welcome, {kickoff.get('client_name')}!</h2>
                        <p style="color: #6b7280;">Please review and confirm your project details below.</p>
                    </div>
                    
                    <div class="details">
                        <table>
                            <tr>
                                <td>Project ID:</td>
                                <td><strong>{kickoff.get('project_id')}</strong></td>
                            </tr>
                            <tr>
                                <td>Project Name:</td>
                                <td>{kickoff.get('project_name')}</td>
                            </tr>
                            <tr>
                                <td>Type:</td>
                                <td>{kickoff.get('project_type', 'Mixed').title()}</td>
                            </tr>
                            <tr>
                                <td>Duration:</td>
                                <td>{kickoff.get('project_tenure_months', 12)} months</td>
                            </tr>
                            <tr>
                                <td>Contract Value:</td>
                                <td>₹{kickoff.get('project_value', 0):,.0f}</td>
                            </tr>
                        </table>
                    </div>
                    
                    <form action="/api/kickoff-requests/client-approve/{token}/confirm" method="POST">
                        <div class="form-group">
                            <label for="start_date">📅 Confirm Project Start Date:</label>
                            <input type="date" id="start_date" name="start_date" value="{expected_start}" required>
                        </div>
                        
                        <button type="submit" class="btn">✓ Approve & Start Project</button>
                    </form>
                    
                    <p style="margin-top: 20px; color: #6b7280; font-size: 13px; text-align: center;">
                        By clicking "Approve", you confirm the project details and agree to proceed with the engagement.
                    </p>
                </div>
                <div class="footer">
                    <p>© {datetime.now().year} D&V Business Consulting. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
    """)


@router.post("/client-approve/{token}/confirm")
async def client_confirm_approval(
    token: str,
    background_tasks: BackgroundTasks,
    start_date: str = None
):
    """
    CLIENT APPROVAL CONFIRMATION - Final step.
    
    When client approves:
    1. Status → approved
    2. Create client user account (ID: 98XXX)
    3. Send welcome email with credentials
    4. Notify all stakeholders
    """
    db = get_db()
    
    # Handle form data
    from fastapi import Form, Request
    
    kickoff = await db.kickoff_requests.find_one({"client_approval_token": token}, {"_id": 0})
    if not kickoff:
        return HTMLResponse(content="""
            <html><body style="font-family: Arial; text-align: center; padding: 50px;">
                <h1 style="color: #ef4444;">Invalid Link</h1>
            </body></html>
        """, status_code=404)
    
    if kickoff.get("client_approved"):
        return HTMLResponse(content="""
            <html><body style="font-family: Arial; text-align: center; padding: 50px;">
                <h1 style="color: #10b981;">✅ Already Approved</h1>
            </body></html>
        """)
    
    # Get client email from lead
    lead = None
    client_email = kickoff.get("client_email")
    if kickoff.get("lead_id"):
        lead = await db.leads.find_one({"id": kickoff["lead_id"]}, {"_id": 0})
        if lead and not client_email:
            client_email = lead.get("email", "")
    
    # Generate client ID (98XXX format)
    client_id = await generate_client_id(db)
    
    # Generate random password
    temp_password = generate_random_password()
    hashed_password = pwd_context.hash(temp_password)
    
    # Determine confirmed start date
    confirmed_start = start_date or str(kickoff.get('expected_start_date', ''))[:10]
    if not confirmed_start:
        confirmed_start = datetime.now().strftime('%Y-%m-%d')
    
    # Create client user account
    client_user = {
        "id": str(uuid.uuid4()),
        "client_id": client_id,
        "email": client_email,
        "hashed_password": hashed_password,
        "full_name": kickoff.get("client_name"),
        "company_name": kickoff.get("client_name"),
        "phone": lead.get("phone") if lead else None,
        "lead_id": kickoff.get("lead_id"),
        "project_ids": [kickoff.get("project_id")],
        "agreement_ids": [kickoff.get("agreement_id")] if kickoff.get("agreement_id") else [],
        "is_active": True,
        "must_change_password": True,
        "role": "client",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.client_users.insert_one(client_user)
    
    # Update kickoff request
    await db.kickoff_requests.update_one(
        {"id": kickoff.get("id")},
        {"$set": {
            "client_approved": True,
            "client_approved_by": kickoff.get("client_name"),
            "client_approved_at": datetime.now(timezone.utc).isoformat(),
            "confirmed_start_date": confirmed_start,
            "status": "approved",
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    # Create/Update project record
    project_id = kickoff.get("project_id")
    existing_project = await db.projects.find_one({"id": project_id}, {"_id": 0})
    
    if not existing_project:
        # Create new project
        tenure_months = kickoff.get("project_tenure_months", 12)
        start_dt = datetime.strptime(confirmed_start, "%Y-%m-%d")
        end_dt = start_dt + relativedelta(months=tenure_months)
        
        project_doc = {
            "id": project_id,
            "name": kickoff.get("project_name"),
            "client_name": kickoff.get("client_name"),
            "client_id": client_id,
            "lead_id": kickoff.get("lead_id"),
            "agreement_id": kickoff.get("agreement_id"),
            "kickoff_request_id": kickoff.get("id"),
            "project_type": kickoff.get("project_type", "mixed"),
            "start_date": confirmed_start,
            "end_date": end_dt.strftime("%Y-%m-%d"),
            "tenure_months": tenure_months,
            "total_meetings_committed": kickoff.get("total_meetings", 0),
            "project_value": kickoff.get("project_value"),
            "status": "active",
            "internal_approved_by": kickoff.get("internal_approved_by"),
            "internal_approved_by_name": kickoff.get("internal_approved_by_name"),
            "client_approved_at": datetime.now(timezone.utc).isoformat(),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "consultant_assignments": []  # Will be assigned manually by Principal Consultant
        }
        await db.projects.insert_one(project_doc)
    else:
        # Update existing project
        await db.projects.update_one(
            {"id": project_id},
            {"$set": {
                "client_id": client_id,
                "start_date": confirmed_start,
                "status": "active",
                "client_approved_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }}
        )
    
    # Send welcome email to client with credentials
    async def send_client_welcome_email():
        try:
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head><meta charset="utf-8"></head>
            <body style="margin: 0; padding: 0; font-family: 'Segoe UI', Arial, sans-serif; background: #f5f5f5;">
                <table style="width: 100%;">
                    <tr>
                        <td align="center" style="padding: 40px 20px;">
                            <table style="width: 100%; max-width: 600px; background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                                
                                <!-- Header with Full-Width Welcome -->
                                <tr>
                                    <td style="background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); padding: 50px 40px; text-align: center;">
                                        <img src="{LOGO_URL}" alt="D&V" style="height: 80px; margin-bottom: 20px;">
                                        <h1 style="color: white; margin: 0; font-size: 32px;">Welcome to<br>D&V Business Consulting!</h1>
                                    </td>
                                </tr>
                                
                                <!-- Green Success Banner -->
                                <tr>
                                    <td style="background: #10b981; padding: 20px; text-align: center;">
                                        <p style="color: white; margin: 0; font-size: 18px; font-weight: bold;">
                                            🎉 Your Project is Now Active!
                                        </p>
                                    </td>
                                </tr>
                                
                                <!-- Content -->
                                <tr>
                                    <td style="padding: 40px;">
                                        <p style="color: #4b5563; font-size: 16px; line-height: 1.6;">
                                            Dear <strong>{kickoff.get('client_name')}</strong>,
                                        </p>
                                        <p style="color: #4b5563; font-size: 16px; line-height: 1.6;">
                                            Thank you for confirming your project. We are excited to begin our journey together!
                                        </p>
                                        
                                        <!-- Project Details -->
                                        <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 25px 0;">
                                            <h3 style="margin: 0 0 15px; color: #1a1a2e;">Project Details</h3>
                                            <table style="width: 100%; font-size: 14px;">
                                                <tr><td style="padding: 8px 0; color: #6b7280;">Project ID:</td><td style="color: #1a1a2e;"><strong>{project_id}</strong></td></tr>
                                                <tr><td style="padding: 8px 0; color: #6b7280;">Project Name:</td><td style="color: #1a1a2e;">{kickoff.get('project_name')}</td></tr>
                                                <tr><td style="padding: 8px 0; color: #6b7280;">Start Date:</td><td style="color: #1a1a2e;"><strong>{confirmed_start}</strong></td></tr>
                                            </table>
                                        </div>
                                        
                                        <!-- Login Credentials Box -->
                                        <div style="background: #eff6ff; border: 2px solid #3b82f6; padding: 25px; border-radius: 8px; margin: 25px 0;">
                                            <h3 style="margin: 0 0 15px; color: #1e40af;">🔐 Your NETRA Portal Access</h3>
                                            <table style="width: 100%; font-size: 15px;">
                                                <tr>
                                                    <td style="padding: 10px 0; color: #1e40af;">Client ID:</td>
                                                    <td style="color: #1a1a2e; font-weight: bold; font-family: monospace; font-size: 18px;">{client_id}</td>
                                                </tr>
                                                <tr>
                                                    <td style="padding: 10px 0; color: #1e40af;">Temporary Password:</td>
                                                    <td style="color: #1a1a2e; font-weight: bold; font-family: monospace; font-size: 18px;">{temp_password}</td>
                                                </tr>
                                            </table>
                                            <p style="margin: 15px 0 0; color: #92400e; font-size: 13px; background: #fef3c7; padding: 10px; border-radius: 4px;">
                                                ⚠️ Please change your password upon first login.
                                            </p>
                                        </div>
                                        
                                        <!-- What You Can Do -->
                                        <h3 style="color: #1a1a2e; margin: 30px 0 15px;">What You Can Do in NETRA:</h3>
                                        <ul style="color: #4b5563; font-size: 14px; line-height: 2;">
                                            <li>📊 View your project progress and status</li>
                                            <li>👤 See your assigned consultant details</li>
                                            <li>📅 Check meeting schedules</li>
                                            <li>📄 Access documents (SOW, Agreement, Invoices)</li>
                                            <li>💰 View payment history and upcoming payments</li>
                                            <li>📝 Review Meeting Notes (MOM) from consultants</li>
                                            <li>🔄 Request consultant change if needed</li>
                                        </ul>
                                        
                                        <!-- Login Button -->
                                        <div style="text-align: center; margin: 30px 0;">
                                            <a href="{APP_URL}/client-login" style="display: inline-block; background: #3b82f6; color: white; padding: 16px 50px; text-decoration: none; border-radius: 8px; font-weight: bold; font-size: 16px;">
                                                Login to NETRA Portal
                                            </a>
                                        </div>
                                    </td>
                                </tr>
                                
                                <!-- Footer -->
                                <tr>
                                    <td style="background: #f8f9fa; padding: 25px 40px; text-align: center; border-top: 1px solid #e9ecef;">
                                        <p style="margin: 0 0 10px; color: #6c757d; font-size: 14px;">
                                            Questions? Contact your assigned consultant or email us.
                                        </p>
                                        <p style="margin: 0; color: #adb5bd; font-size: 12px;">
                                            © {datetime.now().year} D&V Business Consulting. All rights reserved.
                                        </p>
                                    </td>
                                </tr>
                                
                            </table>
                        </td>
                    </tr>
                </table>
            </body>
            </html>
            """
            
            await send_email(
                to_email=client_email,
                subject=f"🎉 Welcome to D&V! Your Project {project_id} is Active",
                html_content=html_content,
                plain_content=f"Welcome to D&V Business Consulting! Your Client ID: {client_id}, Password: {temp_password}"
            )
        except Exception as e:
            print(f"Failed to send client welcome email: {e}")
    
    background_tasks.add_task(send_client_welcome_email)
    
    # Send notification to all stakeholders
    async def send_stakeholder_notifications():
        try:
            # Get all recipients: Consulting Team + HR Manager + Sales Team
            recipients = []
            
            # Consulting team
            consulting = await db.users.find(
                {"role": {"$in": ["principal_consultant", "senior_consultant", "consultant", "lean_consultant"]}},
                {"_id": 0, "id": 1, "email": 1, "full_name": 1}
            ).to_list(100)
            recipients.extend(consulting)
            
            # HR Manager
            hr = await db.users.find({"role": "hr_manager"}, {"_id": 0, "id": 1, "email": 1}).to_list(10)
            recipients.extend(hr)
            
            # Sales team (requester)
            if kickoff.get("requested_by"):
                sales = await db.users.find_one({"id": kickoff.get("requested_by")}, {"_id": 0, "id": 1, "email": 1})
                if sales:
                    recipients.append(sales)
            
            # Create notifications
            for user in recipients:
                notification = {
                    "id": str(uuid.uuid4()),
                    "type": "project_client_approved",
                    "recipient_id": user.get("id"),
                    "title": f"✅ Client Approved: {project_id}",
                    "message": f"{kickoff.get('client_name')} has approved. Project starts {confirmed_start}.",
                    "project_id": project_id,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "read": False
                }
                await db.notifications.insert_one(notification)
                
                # Send email
                if user.get("email"):
                    await send_email(
                        to_email=user["email"],
                        subject=f"✅ Project {project_id} Activated - Client Approved",
                        html_content=f"""
                        <html>
                        <body style="font-family: Arial; padding: 20px;">
                            <div style="max-width: 600px; margin: 0 auto; background: #fff; border-radius: 8px; padding: 30px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                                <img src="{LOGO_URL}" style="height: 60px; margin-bottom: 20px;">
                                <h2 style="color: #10b981;">Project Activated!</h2>
                                <p>Client <strong>{kickoff.get('client_name')}</strong> has approved the project.</p>
                                <div style="background: #f5f5f5; padding: 15px; border-radius: 8px; margin: 20px 0;">
                                    <p><strong>Project ID:</strong> {project_id}</p>
                                    <p><strong>Project:</strong> {kickoff.get('project_name')}</p>
                                    <p><strong>Start Date:</strong> {confirmed_start}</p>
                                    <p><strong>Client ID:</strong> {client_id}</p>
                                </div>
                                <p style="color: #666;">Consultant can now be assigned via All Projects page.</p>
                            </div>
                        </body>
                        </html>
                        """,
                        plain_content=f"Project {project_id} activated. Start: {confirmed_start}"
                    )
        except Exception as e:
            print(f"Failed to send stakeholder notifications: {e}")
    
    background_tasks.add_task(send_stakeholder_notifications)
    
    # Return success page
    return HTMLResponse(content=f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Project Approved - D&V Business Consulting</title>
            <meta http-equiv="refresh" content="5;url={APP_URL}/client-login">
        </head>
        <body style="margin: 0; padding: 0; font-family: 'Segoe UI', Arial, sans-serif; background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); min-height: 100vh; display: flex; align-items: center; justify-content: center;">
            <div style="text-align: center; padding: 40px;">
                <img src="{LOGO_URL}" style="height: 80px; margin-bottom: 30px;">
                <div style="background: white; padding: 50px; border-radius: 16px; box-shadow: 0 20px 40px rgba(0,0,0,0.3); max-width: 500px;">
                    <div style="font-size: 60px; margin-bottom: 20px;">🎉</div>
                    <h1 style="color: #10b981; margin: 0 0 20px;">Welcome to D&V!</h1>
                    <p style="color: #4b5563; font-size: 18px; line-height: 1.6;">
                        Your project <strong>{project_id}</strong> is now active!
                    </p>
                    <p style="color: #6b7280; margin: 20px 0;">
                        We've sent your login credentials to <strong>{client_email}</strong>
                    </p>
                    <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 25px 0;">
                        <p style="margin: 5px 0; color: #1a1a2e;"><strong>Your Client ID:</strong> {client_id}</p>
                        <p style="margin: 5px 0; color: #1a1a2e;"><strong>Project Start:</strong> {confirmed_start}</p>
                    </div>
                    <p style="color: #9ca3af; font-size: 13px;">
                        Redirecting to login page in 5 seconds...
                    </p>
                    <a href="{APP_URL}/client-login" style="display: inline-block; background: #3b82f6; color: white; padding: 14px 40px; text-decoration: none; border-radius: 8px; font-weight: bold; margin-top: 20px;">
                        Go to Login Now
                    </a>
                </div>
            </div>
        </body>
        </html>
    """)


@router.post("/{request_id}/reject")
async def reject_kickoff_request(
    request_id: str,
    reason: str,
    current_user: User = Depends(get_current_user)
):
    """Reject a kickoff request (Principal Consultant ONLY)."""
    db = get_db()
    
    # Only Principal Consultant can reject kickoffs
    if current_user.role not in PRINCIPAL_CONSULTANT_ROLES:
        raise HTTPException(status_code=403, detail="Only Principal Consultant can reject kickoff requests")
    
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
