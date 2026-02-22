"""
Project Payments Router - Payment tracking and schedule management
Handles payment visibility for consultants, sales managers, and admin
Includes payment reminders and transaction recording
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from datetime import datetime, timezone, timedelta
from typing import List, Optional
from pydantic import BaseModel, Field
import uuid

from .models import User
from .deps import get_db, PROJECT_PM_ROLES
from .auth import get_current_user

router = APIRouter(prefix="/project-payments", tags=["Project Payments"])


class PaymentReminderRequest(BaseModel):
    """Request to send payment reminder"""
    project_id: str
    installment_number: int
    client_email: Optional[str] = None
    custom_message: Optional[str] = None


class RecordPaymentRequest(BaseModel):
    """Request to record a payment with transaction ID"""
    project_id: str
    installment_number: int
    transaction_id: str
    amount_received: float
    payment_date: Optional[str] = None
    remarks: Optional[str] = None


class PaymentScheduleItem(BaseModel):
    """Individual payment schedule entry"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    frequency: str  # "Month 1", "Month 2", etc.
    due_date: str
    basic: float = 0
    gst: float = 0
    tds: float = 0
    conveyance: float = 0
    net: float = 0
    status: str = "pending"  # pending, received, overdue
    received_date: Optional[str] = None
    transaction_id: Optional[str] = None
    consultant_id: Optional[str] = None
    consultant_name: Optional[str] = None


@router.get("/project/{project_id}")
async def get_project_payments(
    project_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get all payment information for a project including:
    - First advance payment (from payment_verifications) - HIDDEN for consultant/reporting_manager
    - Payment schedule from pricing plan - amounts HIDDEN for consultant/reporting_manager
    - Consultant-wise breakdown - payment amounts HIDDEN for consultant/reporting_manager
    Accessible by: Assigned Consultant, Reporting Manager, PM, Principal Consultant, Admin
    
    VISIBILITY RULES:
    - Consultant: Only sees upcoming payment DATES (no amounts, no first payment)
    - Reporting Manager: Sees payment dates, consultant names (no amounts)
    - Admin/Principal Consultant: Full view (amounts, dates, consultant name, first payment)
    """
    db = get_db()
    
    # Get project details
    project = await db.projects.find_one({"id": project_id}, {"_id": 0})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Check access permissions and determine role type
    can_view_amounts = current_user.role in ["admin", "principal_consultant"]
    is_manager_view = current_user.role in ["project_manager", "manager"]  # Can see consultant names, no amounts
    is_admin = current_user.role in ["admin", "principal_consultant", "project_manager", "manager"]
    is_assigned_consultant = current_user.id in (project.get("assigned_consultants") or [])
    
    # Check if user is reporting manager of assigned consultants
    is_reporting_manager = False
    if not is_admin and not is_assigned_consultant:
        # Check consultant assignments for reporting manager
        assignments = await db.consultant_assignments.find(
            {"project_id": project_id, "is_active": True},
            {"_id": 0}
        ).to_list(100)
        
        for assignment in assignments:
            consultant = await db.users.find_one(
                {"id": assignment.get("consultant_id")},
                {"_id": 0, "reporting_manager_id": 1}
            )
            if consultant and consultant.get("reporting_manager_id") == current_user.id:
                is_reporting_manager = True
                break
    
    if not is_admin and not is_assigned_consultant and not is_reporting_manager:
        raise HTTPException(status_code=403, detail="Not authorized to view project payments")
    
    # Reporting manager gets same visibility as manager role (no amounts)
    if is_reporting_manager and not is_admin:
        is_manager_view = True
    
    # Get agreement and first advance payment
    agreement_id = project.get("agreement_id")
    first_payment = None
    if agreement_id:
        first_payment = await db.payment_verifications.find_one(
            {"agreement_id": agreement_id, "installment_number": 1},
            {"_id": 0}
        )
    
    # Get pricing plan for payment schedule
    pricing_plan_id = project.get("pricing_plan_id")
    payment_schedule = []
    pricing_plan = None
    
    if not pricing_plan_id and agreement_id:
        # Try to get from agreement
        agreement = await db.agreements.find_one({"id": agreement_id}, {"_id": 0})
        if agreement:
            pricing_plan_id = agreement.get("pricing_plan_id")
            if not pricing_plan_id and agreement.get("quotation_id"):
                quotation = await db.quotations.find_one(
                    {"id": agreement.get("quotation_id")},
                    {"_id": 0}
                )
                if quotation:
                    pricing_plan_id = quotation.get("pricing_plan_id")
    
    if pricing_plan_id:
        pricing_plan = await db.pricing_plans.find_one(
            {"id": pricing_plan_id},
            {"_id": 0}
        )
        if pricing_plan and pricing_plan.get("payment_plan"):
            schedule_breakdown = pricing_plan["payment_plan"].get("schedule_breakdown", [])
            for idx, item in enumerate(schedule_breakdown):
                is_first_payment_received = idx == 0 and first_payment
                
                # Build payment schedule item based on role visibility
                schedule_item = {
                    "id": str(uuid.uuid4()),
                    "installment_number": idx + 1,
                    "frequency": item.get("frequency", f"Month {idx + 1}"),
                    "due_date": item.get("due_date"),
                    "status": "received" if is_first_payment_received else "pending"
                }
                
                # Only add amounts for admin/principal_consultant
                if can_view_amounts:
                    schedule_item.update({
                        "basic": item.get("basic", 0),
                        "gst": item.get("gst", 0),
                        "tds": item.get("tds", 0),
                        "conveyance": item.get("conveyance", 0),
                        "net": item.get("net", 0)
                    })
                
                # For consultants: skip first payment if received (they shouldn't see it at all)
                if is_assigned_consultant and not is_admin and is_first_payment_received:
                    continue  # Skip this entry entirely
                
                payment_schedule.append(schedule_item)
    
    # Get consultant assignments with details
    assignments = await db.consultant_assignments.find(
        {"project_id": project_id, "is_active": True},
        {"_id": 0}
    ).to_list(100)
    
    consultant_breakdown = []
    for assignment in assignments:
        consultant = await db.users.find_one(
            {"id": assignment.get("consultant_id")},
            {"_id": 0, "full_name": 1, "employee_id": 1, "reporting_manager_id": 1}
        )
        if consultant:
            consultant_item = {
                "consultant_id": assignment.get("consultant_id"),
                "consultant_name": consultant.get("full_name"),
                "employee_id": consultant.get("employee_id"),
                "role_in_project": assignment.get("role_in_project"),
                "meetings_committed": assignment.get("meetings_committed", 0),
                "assigned_date": assignment.get("assigned_date")
            }
            
            # Only add payment info for admin/principal_consultant
            if can_view_amounts and pricing_plan and pricing_plan.get("team_deployment"):
                for deployment in pricing_plan.get("team_deployment", []):
                    if deployment.get("role") == assignment.get("role_in_project"):
                        consultant_item["payment_info"] = {
                            "rate_per_meeting": deployment.get("rate_per_meeting", 0),
                            "meetings_per_month": deployment.get("meetings_per_month", 0),
                            "committed_meetings": deployment.get("committed_meetings", 0),
                            "breakup_amount": deployment.get("breakup_amount", 0)
                        }
                        break
            
            consultant_breakdown.append(consultant_item)
    
    # Build response based on role visibility
    response = {
        "project_id": project_id,
        "project_name": project.get("name"),
        "client_name": project.get("client_name"),
        "agreement_id": agreement_id,
        "pricing_plan_id": pricing_plan_id,
        "payment_schedule": payment_schedule,
        "consultant_breakdown": consultant_breakdown,
        "payment_frequency": pricing_plan.get("payment_schedule", "monthly") if pricing_plan else "monthly",
        "user_role": current_user.role,
        "can_view_amounts": can_view_amounts,
        "is_consultant_view": is_assigned_consultant and not is_admin
    }
    
    # Add total value and first payment info only for users who can view amounts
    if can_view_amounts:
        response["total_value"] = pricing_plan.get("total_amount", 0) if pricing_plan else project.get("project_value", 0)
        response["first_advance_payment"] = {
            "received": bool(first_payment),
            "amount": first_payment.get("received_amount") if first_payment else None,
            "transaction_id": first_payment.get("transaction_id") if first_payment else None,
            "payment_date": first_payment.get("payment_date") if first_payment else None,
            "verified_by": first_payment.get("verified_by_name") if first_payment else None
        }
    elif is_manager_view:
        # Managers can see that first payment was received, but not the amount
        response["total_value"] = None  # Hidden
        response["first_advance_payment"] = {
            "received": bool(first_payment),
            "amount": None,  # Hidden
            "transaction_id": None,  # Hidden
            "payment_date": first_payment.get("payment_date") if first_payment else None,
            "verified_by": None  # Hidden
        }
    else:
        # Consultants: no first payment info, no total value
        response["total_value"] = None
        response["first_advance_payment"] = None
    
    return response


@router.get("/my-payments")
async def get_my_payments(
    current_user: User = Depends(get_current_user)
):
    """
    Get payments for projects the current user is associated with.
    For consultants: Their assigned projects (no amounts)
    For managers: Projects of their reportees (no amounts)
    For admin/Principal Consultant: All projects with full details
    
    VISIBILITY RULES:
    - Consultant: Only sees upcoming payment count (no amounts)
    - Reporting Manager/Manager: Sees payment dates, consultant names (no amounts)
    - Admin/Principal Consultant: Full view (amounts, dates, consultant names)
    """
    db = get_db()
    
    can_view_amounts = current_user.role in ["admin", "principal_consultant"]
    project_ids = []
    
    if current_user.role in ["admin", "principal_consultant", "project_manager"]:
        # Get all active projects
        projects = await db.projects.find(
            {"status": {"$ne": "completed"}},
            {"_id": 0, "id": 1}
        ).to_list(1000)
        project_ids = [p["id"] for p in projects]
    
    elif current_user.role == "consultant":
        # Get assigned projects
        assignments = await db.consultant_assignments.find(
            {"consultant_id": current_user.id, "is_active": True},
            {"_id": 0, "project_id": 1}
        ).to_list(100)
        project_ids = [a["project_id"] for a in assignments]
    
    elif current_user.role == "manager":
        # Get projects of reportees
        reportees = await db.users.find(
            {"reporting_manager_id": current_user.id},
            {"_id": 0, "id": 1}
        ).to_list(100)
        reportee_ids = [r["id"] for r in reportees]
        
        assignments = await db.consultant_assignments.find(
            {"consultant_id": {"$in": reportee_ids}, "is_active": True},
            {"_id": 0, "project_id": 1}
        ).to_list(100)
        project_ids = list(set([a["project_id"] for a in assignments]))
    
    # Get payment details for each project
    results = []
    for project_id in project_ids[:50]:  # Limit to 50 projects
        try:
            project = await db.projects.find_one({"id": project_id}, {"_id": 0})
            if not project:
                continue
            
            # Get first payment
            first_payment = None
            if project.get("agreement_id"):
                first_payment = await db.payment_verifications.find_one(
                    {"agreement_id": project.get("agreement_id"), "installment_number": 1},
                    {"_id": 0}
                )
            
            # Get pricing plan
            pricing_plan_id = project.get("pricing_plan_id")
            total_value = project.get("project_value", 0)
            upcoming_payments = 0
            
            if pricing_plan_id:
                pricing_plan = await db.pricing_plans.find_one(
                    {"id": pricing_plan_id},
                    {"_id": 0, "total_amount": 1, "payment_plan": 1}
                )
                if pricing_plan:
                    total_value = pricing_plan.get("total_amount", 0)
                    schedule = pricing_plan.get("payment_plan", {}).get("schedule_breakdown", [])
                    # Count upcoming payments (skip first if already received)
                    start_idx = 1 if first_payment else 0
                    upcoming_payments = len(schedule) - start_idx
            
            # Get assigned consultants names for the project
            consultant_names = []
            assignments = await db.consultant_assignments.find(
                {"project_id": project_id, "is_active": True},
                {"_id": 0, "consultant_id": 1}
            ).to_list(20)
            
            for assignment in assignments:
                consultant = await db.users.find_one(
                    {"id": assignment.get("consultant_id")},
                    {"_id": 0, "full_name": 1}
                )
                if consultant:
                    consultant_names.append(consultant.get("full_name"))
            
            # Build result based on role visibility
            result_item = {
                "project_id": project_id,
                "project_name": project.get("name"),
                "client_name": project.get("client_name"),
                "status": project.get("status", "active"),
                "upcoming_payments_count": upcoming_payments,
                "start_date": project.get("start_date"),
                "consultant_names": consultant_names  # Always show consultant names
            }
            
            # Add amount fields only for admin/principal_consultant
            if can_view_amounts:
                result_item["total_value"] = total_value
                result_item["first_payment_received"] = bool(first_payment)
                result_item["first_payment_amount"] = first_payment.get("received_amount") if first_payment else None
            else:
                result_item["total_value"] = None  # Hidden
                result_item["first_payment_received"] = bool(first_payment)  # Can see status
                result_item["first_payment_amount"] = None  # Hidden
            
            results.append(result_item)
        except Exception:
            continue
    
    return {
        "user_role": current_user.role,
        "can_view_amounts": can_view_amounts,
        "total_projects": len(results),
        "payments": results
    }


@router.get("/upcoming")
async def get_upcoming_payments(
    current_user: User = Depends(get_current_user)
):
    """
    Get upcoming payment schedule across all accessible projects.
    For: Admin, Principal Consultant, Sales Manager
    """
    db = get_db()
    
    # Only admin, principal consultant, and managers can view all upcoming payments
    if current_user.role not in PROJECT_PM_ROLES:
        raise HTTPException(status_code=403, detail="Not authorized to view upcoming payments")
    
    # Get all active projects
    projects = await db.projects.find(
        {"status": {"$in": ["active", "pending_kickoff"]}},
        {"_id": 0}
    ).to_list(500)
    
    upcoming_payments = []
    
    for project in projects:
        pricing_plan_id = project.get("pricing_plan_id")
        if not pricing_plan_id and project.get("agreement_id"):
            agreement = await db.agreements.find_one(
                {"id": project.get("agreement_id")},
                {"_id": 0}
            )
            if agreement and agreement.get("quotation_id"):
                quotation = await db.quotations.find_one(
                    {"id": agreement.get("quotation_id")},
                    {"_id": 0}
                )
                if quotation:
                    pricing_plan_id = quotation.get("pricing_plan_id")
        
        if pricing_plan_id:
            pricing_plan = await db.pricing_plans.find_one(
                {"id": pricing_plan_id},
                {"_id": 0}
            )
            if pricing_plan and pricing_plan.get("payment_plan"):
                schedule = pricing_plan["payment_plan"].get("schedule_breakdown", [])
                
                # Check first payment status
                first_payment = None
                if project.get("agreement_id"):
                    first_payment = await db.payment_verifications.find_one(
                        {"agreement_id": project.get("agreement_id"), "installment_number": 1},
                        {"_id": 0}
                    )
                
                for idx, item in enumerate(schedule):
                    if idx == 0 and first_payment:
                        continue  # Skip first payment if already received
                    
                    upcoming_payments.append({
                        "project_id": project["id"],
                        "project_name": project.get("name"),
                        "client_name": project.get("client_name"),
                        "installment_number": idx + 1,
                        "frequency": item.get("frequency"),
                        "due_date": item.get("due_date"),
                        "amount": item.get("net", 0),
                        "status": "pending"
                    })
    
    # Sort by due date
    upcoming_payments.sort(key=lambda x: x.get("due_date", "9999-12-31"))
    
    return {
        "total_upcoming": len(upcoming_payments),
        "payments": upcoming_payments[:100]  # Limit to 100
    }



@router.post("/send-reminder")
async def send_payment_reminder(
    request: PaymentReminderRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    """
    Send payment reminder to client.
    Only allowed for consulting team roles and when payment is within 7 days of due date.
    """
    db = get_db()
    
    # Check if user is from consulting team
    allowed_roles = ["admin", "principal_consultant", "project_manager", "manager", "consultant", "lead_consultant", "senior_consultant"]
    if current_user.role not in allowed_roles:
        raise HTTPException(status_code=403, detail="Only consulting team can send payment reminders")
    
    # Get project
    project = await db.projects.find_one({"id": request.project_id}, {"_id": 0})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Get pricing plan for schedule
    pricing_plan_id = project.get("pricing_plan_id")
    if not pricing_plan_id:
        raise HTTPException(status_code=400, detail="Project has no pricing plan")
    
    pricing_plan = await db.pricing_plans.find_one({"id": pricing_plan_id}, {"_id": 0})
    if not pricing_plan:
        raise HTTPException(status_code=404, detail="Pricing plan not found")
    
    schedule = pricing_plan.get("payment_plan", {}).get("schedule_breakdown", [])
    if request.installment_number < 1 or request.installment_number > len(schedule):
        raise HTTPException(status_code=400, detail="Invalid installment number")
    
    installment = schedule[request.installment_number - 1]
    due_date_str = installment.get("due_date")
    
    if due_date_str:
        try:
            due_date = datetime.fromisoformat(due_date_str.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            due_date = datetime.strptime(due_date_str[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
        
        # Check if within 7 days of due date
        days_until_due = (due_date - datetime.now(timezone.utc)).days
        if days_until_due > 7:
            raise HTTPException(
                status_code=400, 
                detail=f"Reminders can only be sent within 7 days of due date. Due in {days_until_due} days."
            )
    
    # Get client email from agreement/prospect
    client_email = request.client_email
    if not client_email:
        agreement = await db.agreements.find_one({"id": project.get("agreement_id")}, {"_id": 0})
        if agreement:
            prospect = await db.prospects.find_one({"id": agreement.get("prospect_id")}, {"_id": 0})
            if prospect:
                client_email = prospect.get("email")
    
    # Record the reminder
    reminder_id = str(uuid.uuid4())
    reminder_record = {
        "id": reminder_id,
        "project_id": request.project_id,
        "project_name": project.get("name"),
        "installment_number": request.installment_number,
        "amount_due": installment.get("net", 0),
        "due_date": due_date_str,
        "sent_by": current_user.id,
        "sent_by_name": current_user.full_name,
        "sent_at": datetime.now(timezone.utc).isoformat(),
        "client_email": client_email,
        "custom_message": request.custom_message,
        "status": "sent"
    }
    
    await db.payment_reminders.insert_one(reminder_record)
    
    # Create notifications for Finance, Sales, Admin, Reporting Manager, HR
    notification_roles = ["admin", "finance", "sales_manager", "hr_manager"]
    notification_users = await db.users.find(
        {"role": {"$in": notification_roles}, "is_active": True},
        {"_id": 0, "id": 1, "full_name": 1}
    ).to_list(100)
    
    for notif_user in notification_users:
        await db.notifications.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": notif_user["id"],
            "type": "payment_reminder_sent",
            "title": "Payment Reminder Sent",
            "message": f"Payment reminder sent for {project.get('name')} - Installment #{request.installment_number} (Due: {due_date_str[:10] if due_date_str else 'TBD'})",
            "link": f"/projects/{request.project_id}/payments",
            "read": False,
            "created_at": datetime.now(timezone.utc).isoformat()
        })
    
    # TODO: Send actual email to client (MOCKED for now)
    # background_tasks.add_task(send_reminder_email, client_email, project, installment)
    
    return {
        "success": True,
        "message": f"Payment reminder sent for installment #{request.installment_number}",
        "reminder_id": reminder_id,
        "client_email": client_email or "No email found"
    }


@router.post("/record-payment")
async def record_installment_payment(
    request: RecordPaymentRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Record a payment received for a specific installment.
    Consulting team adds transaction ID once client pays.
    Notifies Finance, Sales, Admin, Reporting Manager, HR for incentive calculation.
    """
    db = get_db()
    
    # Check if user is from consulting team
    allowed_roles = ["admin", "principal_consultant", "project_manager", "manager", "consultant", "lead_consultant", "senior_consultant"]
    if current_user.role not in allowed_roles:
        raise HTTPException(status_code=403, detail="Only consulting team can record payments")
    
    # Get project
    project = await db.projects.find_one({"id": request.project_id}, {"_id": 0})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Get pricing plan for schedule
    pricing_plan_id = project.get("pricing_plan_id")
    if not pricing_plan_id:
        raise HTTPException(status_code=400, detail="Project has no pricing plan")
    
    pricing_plan = await db.pricing_plans.find_one({"id": pricing_plan_id}, {"_id": 0})
    if not pricing_plan:
        raise HTTPException(status_code=404, detail="Pricing plan not found")
    
    schedule = pricing_plan.get("payment_plan", {}).get("schedule_breakdown", [])
    if request.installment_number < 1 or request.installment_number > len(schedule):
        raise HTTPException(status_code=400, detail="Invalid installment number")
    
    installment = schedule[request.installment_number - 1]
    
    # Check if already recorded
    existing = await db.installment_payments.find_one({
        "project_id": request.project_id,
        "installment_number": request.installment_number
    })
    if existing:
        raise HTTPException(status_code=400, detail="Payment already recorded for this installment")
    
    # Record the payment
    payment_id = str(uuid.uuid4())
    payment_record = {
        "id": payment_id,
        "project_id": request.project_id,
        "project_name": project.get("name"),
        "agreement_id": project.get("agreement_id"),
        "installment_number": request.installment_number,
        "frequency": installment.get("frequency"),
        "expected_amount": installment.get("net", 0),
        "amount_received": request.amount_received,
        "transaction_id": request.transaction_id,
        "payment_date": request.payment_date or datetime.now(timezone.utc).isoformat(),
        "recorded_by": current_user.id,
        "recorded_by_name": current_user.full_name,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "remarks": request.remarks,
        "status": "received"
    }
    
    await db.installment_payments.insert_one(payment_record)
    
    # Create notifications for Finance, Sales, Admin, Reporting Manager, HR
    notification_roles = ["admin", "finance", "sales_manager", "hr_manager", "principal_consultant"]
    notification_users = await db.users.find(
        {"role": {"$in": notification_roles}, "is_active": True},
        {"_id": 0, "id": 1, "full_name": 1}
    ).to_list(100)
    
    # Also notify project's reporting manager
    assigned_consultants = project.get("assigned_consultants", [])
    for consultant_id in assigned_consultants:
        consultant = await db.users.find_one({"id": consultant_id}, {"_id": 0})
        if consultant and consultant.get("reporting_manager_id"):
            rm = await db.users.find_one({"id": consultant.get("reporting_manager_id")}, {"_id": 0, "id": 1})
            if rm:
                notification_users.append(rm)
    
    for notif_user in notification_users:
        await db.notifications.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": notif_user["id"],
            "type": "payment_received",
            "title": "Payment Received",
            "message": f"Payment received for {project.get('name')} - Installment #{request.installment_number}: ₹{request.amount_received:,.2f} (Txn: {request.transaction_id})",
            "link": f"/projects/{request.project_id}/payments",
            "read": False,
            "created_at": datetime.now(timezone.utc).isoformat()
        })
    
    return {
        "success": True,
        "message": f"Payment recorded for installment #{request.installment_number}",
        "payment_id": payment_id,
        "notifications_sent": len(notification_users)
    }


@router.get("/installment-payments/{project_id}")
async def get_installment_payments(
    project_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get all recorded installment payments for a project.
    """
    db = get_db()
    
    payments = await db.installment_payments.find(
        {"project_id": project_id},
        {"_id": 0}
    ).sort("installment_number", 1).to_list(100)
    
    return {
        "project_id": project_id,
        "payments": payments,
        "total": len(payments)
    }


@router.get("/check-reminder-eligibility/{project_id}/{installment_number}")
async def check_reminder_eligibility(
    project_id: str,
    installment_number: int,
    current_user: User = Depends(get_current_user)
):
    """
    Check if a payment reminder can be sent for a specific installment.
    Returns eligibility status and days until due.
    """
    db = get_db()
    
    # Get project
    project = await db.projects.find_one({"id": project_id}, {"_id": 0})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Get pricing plan
    pricing_plan_id = project.get("pricing_plan_id")
    if not pricing_plan_id:
        return {"eligible": False, "reason": "No pricing plan"}
    
    pricing_plan = await db.pricing_plans.find_one({"id": pricing_plan_id}, {"_id": 0})
    if not pricing_plan:
        return {"eligible": False, "reason": "Pricing plan not found"}
    
    schedule = pricing_plan.get("payment_plan", {}).get("schedule_breakdown", [])
    if installment_number < 1 or installment_number > len(schedule):
        return {"eligible": False, "reason": "Invalid installment"}
    
    installment = schedule[installment_number - 1]
    due_date_str = installment.get("due_date")
    
    # Check if payment already recorded
    existing_payment = await db.installment_payments.find_one({
        "project_id": project_id,
        "installment_number": installment_number
    })
    if existing_payment:
        return {
            "eligible": False, 
            "reason": "Payment already received",
            "payment": existing_payment
        }
    
    if not due_date_str:
        return {"eligible": False, "reason": "No due date set"}
    
    try:
        due_date = datetime.fromisoformat(due_date_str.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        due_date = datetime.strptime(due_date_str[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
    
    days_until_due = (due_date - datetime.now(timezone.utc)).days
    
    # Check consulting team role
    allowed_roles = ["admin", "principal_consultant", "project_manager", "manager", "consultant", "lead_consultant", "senior_consultant"]
    is_consulting_team = current_user.role in allowed_roles
    
    # Get last reminder sent
    last_reminder = await db.payment_reminders.find_one(
        {"project_id": project_id, "installment_number": installment_number},
        {"_id": 0}
    )
    
    return {
        "eligible": days_until_due <= 7 and days_until_due >= 0 and is_consulting_team,
        "days_until_due": days_until_due,
        "due_date": due_date_str,
        "is_consulting_team": is_consulting_team,
        "within_reminder_window": days_until_due <= 7 and days_until_due >= 0,
        "last_reminder": last_reminder,
        "installment": installment
    }
