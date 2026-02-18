"""
Project Payments Router - Payment tracking and schedule management
Handles payment visibility for consultants, sales managers, and admin
"""

from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone
from typing import List, Optional
from pydantic import BaseModel, Field
import uuid

from .models import User
from .deps import get_db
from .auth import get_current_user

router = APIRouter(prefix="/project-payments", tags=["Project Payments"])


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
    - First advance payment (from payment_verifications)
    - Payment schedule from pricing plan
    - Consultant-wise breakdown
    Accessible by: Assigned Consultant, Reporting Manager, PM, Principal Consultant, Admin
    """
    db = get_db()
    
    # Get project details
    project = await db.projects.find_one({"id": project_id}, {"_id": 0})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Check access permissions
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
                payment_schedule.append({
                    "id": str(uuid.uuid4()),
                    "installment_number": idx + 1,
                    "frequency": item.get("frequency", f"Month {idx + 1}"),
                    "due_date": item.get("due_date"),
                    "basic": item.get("basic", 0),
                    "gst": item.get("gst", 0),
                    "tds": item.get("tds", 0),
                    "conveyance": item.get("conveyance", 0),
                    "net": item.get("net", 0),
                    "status": "received" if idx == 0 and first_payment else "pending"
                })
    
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
            # Get team deployment info from pricing plan for this consultant role
            consultant_payment = None
            if pricing_plan and pricing_plan.get("team_deployment"):
                for deployment in pricing_plan.get("team_deployment", []):
                    if deployment.get("role") == assignment.get("role_in_project"):
                        consultant_payment = {
                            "rate_per_meeting": deployment.get("rate_per_meeting", 0),
                            "meetings_per_month": deployment.get("meetings_per_month", 0),
                            "committed_meetings": deployment.get("committed_meetings", 0),
                            "breakup_amount": deployment.get("breakup_amount", 0)
                        }
                        break
            
            consultant_breakdown.append({
                "consultant_id": assignment.get("consultant_id"),
                "consultant_name": consultant.get("full_name"),
                "employee_id": consultant.get("employee_id"),
                "role_in_project": assignment.get("role_in_project"),
                "meetings_committed": assignment.get("meetings_committed", 0),
                "assigned_date": assignment.get("assigned_date"),
                "payment_info": consultant_payment
            })
    
    return {
        "project_id": project_id,
        "project_name": project.get("name"),
        "client_name": project.get("client_name"),
        "agreement_id": agreement_id,
        "pricing_plan_id": pricing_plan_id,
        "total_value": pricing_plan.get("total_amount", 0) if pricing_plan else project.get("project_value", 0),
        "first_advance_payment": {
            "received": bool(first_payment),
            "amount": first_payment.get("received_amount") if first_payment else None,
            "transaction_id": first_payment.get("transaction_id") if first_payment else None,
            "payment_date": first_payment.get("payment_date") if first_payment else None,
            "verified_by": first_payment.get("verified_by_name") if first_payment else None
        },
        "payment_schedule": payment_schedule,
        "consultant_breakdown": consultant_breakdown,
        "payment_frequency": pricing_plan.get("payment_schedule", "monthly") if pricing_plan else "monthly"
    }


@router.get("/my-payments")
async def get_my_payments(
    current_user: User = Depends(get_current_user)
):
    """
    Get payments for projects the current user is associated with.
    For consultants: Their assigned projects
    For managers: Projects of their reportees
    For admin/PM: All projects
    """
    db = get_db()
    
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
            
            results.append({
                "project_id": project_id,
                "project_name": project.get("name"),
                "client_name": project.get("client_name"),
                "status": project.get("status", "active"),
                "total_value": total_value,
                "first_payment_received": bool(first_payment),
                "first_payment_amount": first_payment.get("received_amount") if first_payment else None,
                "upcoming_payments_count": upcoming_payments,
                "start_date": project.get("start_date")
            })
        except Exception:
            continue
    
    return {
        "user_role": current_user.role,
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
    if current_user.role not in ["admin", "principal_consultant", "manager", "project_manager"]:
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
