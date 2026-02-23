"""
Kickoff Router - Kickoff Requests Workflow (Sales to Consulting Handoff)
Sends email notifications when kickoff is sent and accepted.
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import HTMLResponse
from datetime import datetime, timezone
from dateutil.relativedelta import relativedelta
from typing import List, Optional
import uuid
import os

from .models import (
    KickoffRequest, KickoffRequestCreate, KickoffRequestUpdate, 
    KickoffReturnRequest, User, UserRole, Project
)
from .deps import get_db, SALES_EXECUTIVE_ROLES, SENIOR_CONSULTING_ROLES
from .auth import get_current_user
from services.approval_notifications import send_approval_notification, notify_requester_on_action
from services.email_service import send_email
from services.funnel_notifications import kickoff_sent_email, kickoff_accepted_email, get_kickoff_notification_emails
from websocket_manager import get_manager as get_ws_manager

router = APIRouter(prefix="/kickoff-requests", tags=["Kickoff Requests"])

APP_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://erp-approval-flow.preview.emergentagent.com").replace("/api", "")


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
    """Return a kickoff request to sales (PM action)."""
    db = get_db()
    
    # Only Senior Consultant and Principal Consultant can return kickoffs
    if current_user.role not in SENIOR_CONSULTING_ROLES:
        raise HTTPException(status_code=403, detail="Only Senior Consultant or Principal Consultant roles can return kickoff requests")
    
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
    CONSULTANT APPROVAL - First step of dual approval.
    Only Senior Consultant or Principal Consultant can approve.
    After consultant approves, client must also approve before project creation.
    """
    db = get_db()
    
    # Only Senior Consultant and Principal Consultant can accept kickoffs
    if current_user.role not in SENIOR_CONSULTING_ROLES:
        raise HTTPException(status_code=403, detail="Only Senior Consultant or Principal Consultant roles can approve kickoff requests")
    
    kickoff = await db.kickoff_requests.find_one({"id": request_id}, {"_id": 0})
    if not kickoff:
        raise HTTPException(status_code=404, detail="Kickoff request not found")
    
    # Can approve if pending OR if client has already approved (waiting for consultant)
    if kickoff.get("status") not in ["pending", "client_approved"]:
        raise HTTPException(status_code=400, detail="Can only approve pending or client-approved requests")
    
    # Check if consultant already approved
    if kickoff.get("consultant_approved"):
        raise HTTPException(status_code=400, detail="Consultant has already approved this kickoff")
    
    # Generate client approval token if not exists
    client_approval_token = kickoff.get("client_approval_token") or str(uuid.uuid4())
    
    # Update kickoff with consultant approval
    new_status = "approved" if kickoff.get("client_approved") else "consultant_approved"
    
    await db.kickoff_requests.update_one(
        {"id": request_id},
        {"$set": {
            "consultant_approved": True,
            "consultant_approved_by": current_user.id,
            "consultant_approved_by_name": current_user.full_name,
            "consultant_approved_at": datetime.now(timezone.utc).isoformat(),
            "client_approval_token": client_approval_token,
            "status": new_status,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    # If BOTH have now approved, create the project
    if new_status == "approved":
        return await _create_project_from_kickoff(request_id, current_user, background_tasks, db)
    
    # Otherwise, send notification to client for their approval
    lead = None
    if kickoff.get("lead_id"):
        lead = await db.leads.find_one({"id": kickoff["lead_id"]}, {"_id": 0})
    
    client_email = lead.get("email", "") if lead else ""
    
    # Send email to client requesting approval
    if client_email:
        async def send_client_approval_request():
            try:
                approval_link = f"{APP_URL}/kickoff-approval/{client_approval_token}"
                html_content = f"""
                <html>
                <head></head>
                <body style="font-family: Arial, sans-serif; padding: 20px;">
                    <div style="max-width: 600px; margin: 0 auto; background: #fff; border-radius: 8px; padding: 30px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                        <img src="{LOGO_URL}" alt="D&V Business Consulting" style="height: 80px; margin-bottom: 20px;">
                        
                        <h2 style="color: #1a1a2e;">Project Kickoff Approval Required</h2>
                        
                        <p>Dear {kickoff.get('client_name')},</p>
                        
                        <p>Our consultant <strong>{current_user.full_name}</strong> has approved the kickoff request for:</p>
                        
                        <div style="background: #f8f9fa; padding: 15px; border-radius: 6px; margin: 20px 0;">
                            <p style="margin: 5px 0;"><strong>Project:</strong> {kickoff.get('project_name')}</p>
                            <p style="margin: 5px 0;"><strong>Type:</strong> {kickoff.get('project_type', 'Mixed')}</p>
                            <p style="margin: 5px 0;"><strong>Expected Start:</strong> {str(kickoff.get('expected_start_date', 'TBD'))[:10]}</p>
                            <p style="margin: 5px 0;"><strong>Value:</strong> ₹{kickoff.get('project_value', 0):,.0f}</p>
                        </div>
                        
                        <p>Please click below to confirm and approve the project kickoff:</p>
                        
                        <div style="text-align: center; margin: 30px 0;">
                            <a href="{approval_link}" style="display: inline-block; background-color: #10b981; color: white; padding: 14px 40px; text-decoration: none; border-radius: 8px; font-weight: bold;">
                                ✓ Approve Project Kickoff
                            </a>
                        </div>
                        
                        <p style="color: #666; font-size: 13px;">
                            Once you approve, we will assign our senior consultant to your project and begin the onboarding process.
                        </p>
                        
                        <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                        <p style="color: #999; font-size: 12px;">This is an automated notification from NETRA ERP</p>
                    </div>
                </body>
                </html>
                """
                
                await send_email(
                    to_email=client_email,
                    subject=f"Action Required: Approve Project Kickoff - {kickoff.get('project_name')}",
                    html_content=html_content,
                    plain_content=f"Please approve the project kickoff: {approval_link}"
                )
            except Exception as e:
                print(f"Failed to send client approval request: {e}")
        
        background_tasks.add_task(send_client_approval_request)
    
    # Notify requester
    notification = {
        "id": str(uuid.uuid4()),
        "type": "kickoff_consultant_approved",
        "recipient_id": kickoff.get("requested_by"),
        "title": f"Kickoff Consultant Approved: {kickoff.get('project_name')}",
        "message": f"Approved by {current_user.full_name}. Awaiting client approval.",
        "kickoff_request_id": request_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "read": False
    }
    await db.notifications.insert_one(notification)
    
    return {
        "message": "Consultant approval recorded. Awaiting client approval.",
        "status": "consultant_approved",
        "client_approval_pending": True,
        "client_email": client_email
    }


LOGO_URL = "https://dvconsulting.co.in/wp-content/uploads/2020/02/logov4-min.png"


@router.get("/client-approve/{token}")
async def client_approve_kickoff_page(token: str):
    """
    CLIENT APPROVAL - Second step of dual approval.
    Client clicks a link from email to approve.
    Returns HTML page for client to confirm approval.
    """
    db = get_db()
    
    kickoff = await db.kickoff_requests.find_one({"client_approval_token": token}, {"_id": 0})
    if not kickoff:
        return HTMLResponse(content="""
            <html><body style="font-family: Arial; text-align: center; padding: 50px;">
                <h1 style="color: #ef4444;">Invalid or Expired Link</h1>
                <p>This approval link is no longer valid.</p>
            </body></html>
        """, status_code=404)
    
    if kickoff.get("client_approved"):
        return HTMLResponse(content=f"""
            <html><body style="font-family: Arial; text-align: center; padding: 50px;">
                <h1 style="color: #10b981;">✓ Already Approved</h1>
                <p>You have already approved the kickoff for <strong>{kickoff.get('project_name')}</strong>.</p>
            </body></html>
        """)
    
    # Show approval confirmation page
    return HTMLResponse(content=f"""
        <html>
        <head>
            <title>Approve Project Kickoff</title>
            <style>
                body {{ font-family: Arial, sans-serif; background: #f5f5f5; margin: 0; padding: 40px; }}
                .container {{ max-width: 600px; margin: 0 auto; background: white; border-radius: 12px; padding: 40px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
                .btn {{ display: inline-block; padding: 15px 40px; border-radius: 8px; text-decoration: none; font-weight: bold; margin: 10px; }}
                .btn-approve {{ background: #10b981; color: white; }}
                .btn-reject {{ background: #ef4444; color: white; }}
            </style>
        </head>
        <body>
            <div class="container">
                <img src="{LOGO_URL}" alt="D&V" style="height: 80px; margin-bottom: 20px;">
                <h2>Project Kickoff Approval</h2>
                <p>Please confirm your approval for:</p>
                <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0;">
                    <p><strong>Project:</strong> {kickoff.get('project_name')}</p>
                    <p><strong>Client:</strong> {kickoff.get('client_name')}</p>
                    <p><strong>Type:</strong> {kickoff.get('project_type', 'Mixed')}</p>
                    <p><strong>Value:</strong> ₹{kickoff.get('project_value', 0):,.0f}</p>
                </div>
                <div style="text-align: center; margin-top: 30px;">
                    <form action="/api/kickoff-requests/client-approve/{token}/confirm" method="POST" style="display: inline;">
                        <button type="submit" class="btn btn-approve">✓ Approve Kickoff</button>
                    </form>
                </div>
            </div>
        </body>
        </html>
    """)


@router.post("/client-approve/{token}/confirm")
async def client_confirm_kickoff_approval(
    token: str,
    background_tasks: BackgroundTasks
):
    """
    CLIENT APPROVAL CONFIRMATION - Final step of client approval.
    When client submits the approval form.
    """
    db = get_db()
    
    kickoff = await db.kickoff_requests.find_one({"client_approval_token": token}, {"_id": 0})
    if not kickoff:
        return HTMLResponse(content="""
            <html><body style="font-family: Arial; text-align: center; padding: 50px;">
                <h1 style="color: #ef4444;">Invalid Link</h1>
            </body></html>
        """, status_code=404)
    
    if kickoff.get("client_approved"):
        return HTMLResponse(content=f"""
            <html><body style="font-family: Arial; text-align: center; padding: 50px;">
                <h1 style="color: #10b981;">✓ Already Approved</h1>
            </body></html>
        """)
    
    # Determine new status
    new_status = "approved" if kickoff.get("consultant_approved") else "client_approved"
    
    await db.kickoff_requests.update_one(
        {"id": kickoff.get("id")},
        {"$set": {
            "client_approved": True,
            "client_approved_by": kickoff.get("client_name"),
            "client_approved_at": datetime.now(timezone.utc).isoformat(),
            "status": new_status,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    # Notify sales team about client approval
    notification = {
        "id": str(uuid.uuid4()),
        "type": "kickoff_client_approved",
        "recipient_id": kickoff.get("requested_by"),
        "title": f"Client Approved Kickoff: {kickoff.get('project_name')}",
        "message": f"Client {kickoff.get('client_name')} has approved the kickoff.",
        "kickoff_request_id": kickoff.get("id"),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "read": False
    }
    await db.notifications.insert_one(notification)
    
    # If BOTH have now approved, create the project
    if new_status == "approved":
        # Get consultant who approved for project creation
        consultant_id = kickoff.get("consultant_approved_by")
        consultant = await db.users.find_one({"id": consultant_id}, {"_id": 0}) if consultant_id else None
        
        if consultant:
            # Create a fake user object for project creation
            class FakeUser:
                def __init__(self, data):
                    self.id = data.get("id")
                    self.full_name = data.get("full_name", "Consultant")
                    self.role = data.get("role", "senior_consultant")
            
            fake_consultant = FakeUser(consultant)
            await _create_project_from_kickoff(kickoff.get("id"), fake_consultant, background_tasks, db)
        
        return HTMLResponse(content=f"""
            <html>
            <head><meta http-equiv="refresh" content="3;url={APP_URL}/dashboard"></head>
            <body style="font-family: Arial; text-align: center; padding: 50px;">
                <h1 style="color: #10b981;">🎉 Project Approved!</h1>
                <p>Thank you for your approval. The project <strong>{kickoff.get('project_name')}</strong> is now active.</p>
                <p>Our consultant will be assigned shortly.</p>
                <p style="color: #666;">Redirecting...</p>
            </body>
            </html>
        """)
    
    # Client approved but waiting for consultant
    return HTMLResponse(content=f"""
        <html>
        <body style="font-family: Arial; text-align: center; padding: 50px;">
            <h1 style="color: #3b82f6;">✓ Approval Recorded</h1>
            <p>Thank you! Your approval for <strong>{kickoff.get('project_name')}</strong> has been recorded.</p>
            <p>We are awaiting consultant approval to proceed.</p>
        </body>
        </html>
    """)


async def _create_project_from_kickoff(
    request_id: str,
    current_user,
    background_tasks: BackgroundTasks,
    db
):
    """
    Internal function to create project when BOTH consultant and client have approved.
    This is called when the final approval (either consultant or client) completes the dual approval.
    """
    kickoff = await db.kickoff_requests.find_one({"id": request_id}, {"_id": 0})
    if not kickoff:
        raise HTTPException(status_code=404, detail="Kickoff request not found")
    
    # Get agreement to link pricing plan and SOW
    agreement = await db.agreements.find_one({"id": kickoff.get("agreement_id")}, {"_id": 0})
    pricing_plan_id = agreement.get('pricing_plan_id') if agreement else None
    
    # Get lead details
    lead = None
    if kickoff.get("lead_id"):
        lead = await db.leads.find_one({"id": kickoff["lead_id"]}, {"_id": 0})
    elif agreement and agreement.get("lead_id"):
        lead = await db.leads.find_one({"id": agreement["lead_id"]}, {"_id": 0})
    
    # Get requester details for email
    requester = await db.users.find_one({"id": kickoff.get("requested_by")}, {"_id": 0})
    requester_name = requester.get("full_name", "Salesperson") if requester else "Salesperson"
    
    # Get tenure from kickoff request
    tenure_months = kickoff.get("project_tenure_months", 12)
    
    # Calculate end_date based on kickoff accept date + tenure
    kickoff_accepted_at = datetime.now(timezone.utc)
    calculated_end_date = kickoff_accepted_at + relativedelta(months=tenure_months)
    
    # Create project from kickoff request - SET STATUS TO ACTIVE
    project = Project(
        name=kickoff.get("project_name"),
        client_name=kickoff.get("client_name"),
        lead_id=kickoff.get("lead_id"),
        agreement_id=kickoff.get("agreement_id"),
        project_type=kickoff.get("project_type", "mixed"),
        start_date=kickoff_accepted_at,  # Kickoff accept date as start
        end_date=calculated_end_date,  # Auto-calculated end date
        tenure_months=tenure_months,  # Store tenure for reference
        total_meetings_committed=kickoff.get("total_meetings", 0),
        project_value=kickoff.get("project_value"),
        created_by=current_user.id,
        status="active"  # Auto-set to active on kickoff acceptance
    )
    
    project_doc = project.model_dump()
    project_doc['start_date'] = project_doc['start_date'].isoformat()
    project_doc['end_date'] = project_doc['end_date'].isoformat() if project_doc.get('end_date') else None
    project_doc['created_at'] = project_doc['created_at'].isoformat()
    project_doc['updated_at'] = project_doc['updated_at'].isoformat()
    project_doc['kickoff_request_id'] = request_id  # Link back to kickoff
    project_doc['kickoff_accepted_at'] = kickoff_accepted_at.isoformat()  # Store accept timestamp
    project_doc['consultant_approved_by'] = kickoff.get("consultant_approved_by")
    project_doc['consultant_approved_by_name'] = kickoff.get("consultant_approved_by_name")
    project_doc['client_approved_at'] = kickoff.get("client_approved_at")
    
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
    
    # Assign consultant to project in consulting hierarchy
    consultant_id = kickoff.get("consultant_approved_by") or kickoff.get("assigned_pm_id")
    if consultant_id:
        # Add to consulting hierarchy
        await db.project_assignments.insert_one({
            "id": str(uuid.uuid4()),
            "project_id": project.id,
            "consultant_id": consultant_id,
            "role": "lead_consultant",
            "assigned_at": datetime.now(timezone.utc).isoformat(),
            "status": "active"
        })
        
        # Update consultant's active projects
        await db.users.update_one(
            {"id": consultant_id},
            {"$push": {"active_project_ids": project.id}}
        )
    
    # Notify requester
    notification = {
        "id": str(uuid.uuid4()),
        "type": "kickoff_accepted",
        "recipient_id": kickoff.get("requested_by"),
        "title": f"🎉 Kickoff Fully Approved: {kickoff.get('project_name')}",
        "message": "Both consultant and client have approved. Project is now active!",
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
    
    # Get client email for notification
    client_email = lead.get("email", "") if lead else ""
    consultant_name = kickoff.get("consultant_approved_by_name") or current_user.full_name
    
    # Send HTML email notification in background
    async def send_kickoff_accepted_notification():
        try:
            # Get emails: Lead Owner, Manager, Sales Head, Senior Manager, Principal Consultant
            team_emails = await get_kickoff_notification_emails(db, kickoff.get("requested_by"))
            
            email_data = kickoff_accepted_email(
                lead_name=f"{lead.get('first_name', '')} {lead.get('last_name', '')}".strip() if lead else "N/A",
                company=kickoff.get("client_name") or (lead.get("company") if lead else "Unknown"),
                project_name=kickoff.get("project_name"),
                project_id=project.id,
                project_type=kickoff.get("project_type", "Mixed"),
                start_date=kickoff_accepted_at.strftime("%Y-%m-%d"),
                assigned_consultant=consultant_name,
                contract_value=kickoff.get("project_value") or 0,
                currency="INR",
                approved_by=f"{consultant_name} (Consultant) + {kickoff.get('client_name')} (Client)",
                approval_date=kickoff_accepted_at.strftime("%Y-%m-%d %H:%M"),
                salesperson_name=requester_name,
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
                    subject=f"🎉 Project Approved: {kickoff.get('project_name')} - Ready to Begin!",
                    html_content=email_data["html"],
                    plain_content=email_data["plain"]
                )
        except Exception as e:
            print(f"Failed to send kickoff accepted notification: {e}")
    
    background_tasks.add_task(send_kickoff_accepted_notification)
    
    return {
        "message": "Kickoff fully approved! Project created and consultant assigned.",
        "status": "converted",
        "project_id": project.id,
        "consultant_approved": True,
        "client_approved": True
    }
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
                    subject=f"🎉 Project Approved - {kickoff.get('project_name')}!",
                    html_content=email_data["html"],
                    plain_content=email_data["plain"]
                )
        except Exception as e:
            print(f"Failed to send kickoff accepted notification: {e}")
    
    background_tasks.add_task(send_kickoff_accepted_notification)
    
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
    """Reject a kickoff request (Senior/Principal Consultant action)."""
    db = get_db()
    
    # Only Senior Consultant and Principal Consultant can reject kickoffs
    if current_user.role not in SENIOR_CONSULTING_ROLES:
        raise HTTPException(status_code=403, detail="Only Senior Consultant or Principal Consultant roles can reject kickoff requests")
    
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
