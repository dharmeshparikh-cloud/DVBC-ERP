"""
Project Completion Router - Handles project completion validation and status management.

Business Rules:
1. A project can only be marked as "completed" if:
   - Project timeline is over (start_date + tenure_months from pricing plan/agreement)
   - All scheduled installments are received as per pricing plan
2. Direct status updates to "completed" are blocked - must go through completion endpoint
"""

from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone
from dateutil.relativedelta import relativedelta
from typing import Optional, Dict, Any, List
from pydantic import BaseModel

from .deps import get_db, ADMIN_ROLES, PROJECT_ROLES
from .auth import get_current_user
from .models import User, UserRole

router = APIRouter(prefix="/project-completion", tags=["Project Completion"])


class ProjectCompletionRequest(BaseModel):
    """Request model for project completion"""
    notes: Optional[str] = None
    force_complete: bool = False  # Admin override for exceptional cases


class ProjectCompletionResponse(BaseModel):
    """Response model for completion validation"""
    project_id: str
    project_name: str
    can_complete: bool
    timeline_status: Dict[str, Any]
    payment_status: Dict[str, Any]
    validation_messages: List[str]
    warnings: List[str]


class ProjectStatusUpdateRequest(BaseModel):
    """Request model for project status update"""
    status: str
    notes: Optional[str] = None


@router.get("/{project_id}/validate")
async def validate_project_completion(
    project_id: str,
    current_user: User = Depends(get_current_user)
) -> ProjectCompletionResponse:
    """
    Validate if a project can be marked as completed.
    
    Checks:
    1. Timeline: Project tenure is complete (start_date + tenure_months)
    2. Payments: All scheduled installments received
    """
    db = get_db()
    
    # Get project
    project = await db.projects.find_one({"id": project_id}, {"_id": 0})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    validation_messages = []
    warnings = []
    timeline_valid = False
    payments_valid = False
    
    project_name = project.get('name') or project.get('project_name') or 'Unnamed Project'
    
    # === TIMELINE VALIDATION ===
    timeline_status = {
        "is_complete": False,
        "start_date": None,
        "tenure_months": None,
        "expected_end_date": None,
        "days_remaining": None,
        "source": None
    }
    
    start_date = project.get('start_date')
    tenure_months = project.get('tenure_months')
    pricing_plan_id = project.get('pricing_plan_id')
    agreement_id = project.get('agreement_id')
    
    # Try to get tenure from pricing plan if not directly available
    if not tenure_months and pricing_plan_id:
        pricing_plan = await db.pricing_plans.find_one({"id": pricing_plan_id}, {"_id": 0})
        if pricing_plan:
            # Calculate tenure from payment schedule breakdown
            schedule = pricing_plan.get('payment_plan', {}).get('schedule_breakdown', [])
            if schedule:
                tenure_months = len(schedule)
                timeline_status['source'] = 'pricing_plan'
    
    # Try to get tenure from agreement
    if not tenure_months and agreement_id:
        agreement = await db.agreements.find_one({"id": agreement_id}, {"_id": 0})
        if agreement:
            tenure_months = agreement.get('tenure_months')
            timeline_status['source'] = 'agreement'
    
    # Fallback to project's end_date if tenure not available
    end_date = project.get('end_date')
    
    if start_date:
        if isinstance(start_date, str):
            start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        # Ensure timezone-aware
        if start_date.tzinfo is None:
            start_date = start_date.replace(tzinfo=timezone.utc)
        
        timeline_status['start_date'] = start_date.isoformat()
        
        if tenure_months:
            timeline_status['tenure_months'] = tenure_months
            expected_end = start_date + relativedelta(months=tenure_months)
            timeline_status['expected_end_date'] = expected_end.isoformat()
            
            now = datetime.now(timezone.utc)
            if now >= expected_end:
                timeline_valid = True
                timeline_status['is_complete'] = True
                timeline_status['days_remaining'] = 0
            else:
                days_remaining = (expected_end - now).days
                timeline_status['days_remaining'] = days_remaining
                validation_messages.append(f"Project timeline not complete. {days_remaining} days remaining until {expected_end.strftime('%Y-%m-%d')}")
        elif end_date:
            if isinstance(end_date, str):
                end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            
            timeline_status['expected_end_date'] = end_date.isoformat()
            timeline_status['source'] = 'project_end_date'
            
            now = datetime.now(timezone.utc)
            if now >= end_date:
                timeline_valid = True
                timeline_status['is_complete'] = True
                timeline_status['days_remaining'] = 0
            else:
                days_remaining = (end_date - now).days
                timeline_status['days_remaining'] = days_remaining
                validation_messages.append(f"Project timeline not complete. {days_remaining} days remaining until {end_date.strftime('%Y-%m-%d')}")
        else:
            warnings.append("No tenure/end date defined. Cannot validate timeline completion.")
            timeline_valid = True  # Allow completion if no timeline defined
    else:
        warnings.append("No start date found. Cannot validate timeline completion.")
        timeline_valid = True  # Allow completion if no start date
    
    # === PAYMENT VALIDATION ===
    payment_status = {
        "is_complete": False,
        "total_installments": 0,
        "received_installments": 0,
        "expected_total": 0,
        "received_total": 0,
        "pending_amount": 0,
        "payment_details": []
    }
    
    # Get pricing plan for payment schedule
    expected_payments = []
    if pricing_plan_id:
        pricing_plan = await db.pricing_plans.find_one({"id": pricing_plan_id}, {"_id": 0})
        if pricing_plan:
            schedule = pricing_plan.get('payment_plan', {}).get('schedule_breakdown', [])
            expected_payments = schedule
            payment_status['total_installments'] = len(schedule)
            payment_status['expected_total'] = sum(p.get('net', p.get('basic', 0)) for p in schedule)
    
    # Get received payments from payment_verifications
    received_payments = await db.payment_verifications.find(
        {"$or": [
            {"agreement_id": agreement_id},
            {"project_id": project_id}
        ]},
        {"_id": 0}
    ).to_list(100) if agreement_id or project_id else []
    
    payment_status['received_installments'] = len(received_payments)
    payment_status['received_total'] = sum(p.get('received_amount', 0) for p in received_payments)
    payment_status['pending_amount'] = payment_status['expected_total'] - payment_status['received_total']
    
    # Build payment details
    for i, expected in enumerate(expected_payments, 1):
        received = next((p for p in received_payments if p.get('installment_number') == i), None)
        payment_status['payment_details'].append({
            "installment": i,
            "frequency": expected.get('frequency', f'Installment {i}'),
            "due_date": expected.get('due_date'),
            "expected_amount": expected.get('net', expected.get('basic', 0)),
            "received": received is not None,
            "received_amount": received.get('received_amount', 0) if received else 0,
            "transaction_id": received.get('transaction_id') if received else None
        })
    
    # Check if all payments received
    if payment_status['total_installments'] == 0:
        warnings.append("No payment schedule found. Cannot validate payment completion.")
        payments_valid = True  # Allow completion if no payments defined
    elif payment_status['received_installments'] >= payment_status['total_installments']:
        payments_valid = True
        payment_status['is_complete'] = True
    else:
        pending_count = payment_status['total_installments'] - payment_status['received_installments']
        validation_messages.append(
            f"Payment incomplete. {pending_count} installment(s) pending. "
            f"Received: ₹{payment_status['received_total']:,.2f} / Expected: ₹{payment_status['expected_total']:,.2f}"
        )
    
    can_complete = timeline_valid and payments_valid
    
    return ProjectCompletionResponse(
        project_id=project_id,
        project_name=project_name,
        can_complete=can_complete,
        timeline_status=timeline_status,
        payment_status=payment_status,
        validation_messages=validation_messages,
        warnings=warnings
    )


@router.post("/{project_id}/complete")
async def complete_project(
    project_id: str,
    request: ProjectCompletionRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Mark a project as completed after validation.
    
    Only Admin/Project Manager can complete projects.
    Force complete option available for Admin only (exceptional cases).
    """
    db = get_db()
    
    # Authorization check
    allowed_roles = [UserRole.ADMIN, "project_manager", "principal_consultant"]
    if current_user.role not in allowed_roles:
        raise HTTPException(
            status_code=403, 
            detail="Only Admin, Project Manager, or Principal Consultant can complete projects"
        )
    
    # Get project
    project = await db.projects.find_one({"id": project_id}, {"_id": 0})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if project.get('status') == 'completed':
        raise HTTPException(status_code=400, detail="Project is already completed")
    
    # Validate completion
    validation = await validate_project_completion(project_id, current_user)
    
    # Check if force complete is being used
    if request.force_complete:
        if current_user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=403, 
                detail="Only Admin can force complete a project"
            )
        # Log force completion
        await db.audit_logs.insert_one({
            "action": "force_complete_project",
            "entity_type": "project",
            "entity_id": project_id,
            "performed_by": current_user.id,
            "performed_by_name": current_user.full_name,
            "details": {
                "validation_messages": validation.validation_messages,
                "warnings": validation.warnings,
                "notes": request.notes
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    elif not validation.can_complete:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Project cannot be completed. Please resolve the following:",
                "issues": validation.validation_messages,
                "warnings": validation.warnings
            }
        )
    
    # Update project status
    project_name = project.get('name') or project.get('project_name') or 'Unnamed Project'
    
    update_data = {
        "status": "completed",
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "completed_by": current_user.id,
        "completed_by_name": current_user.full_name,
        "completion_notes": request.notes,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    if request.force_complete:
        update_data["force_completed"] = True
        update_data["force_complete_reason"] = request.notes
    
    await db.projects.update_one(
        {"id": project_id},
        {"$set": update_data}
    )
    
    # Create notification
    await db.notifications.insert_one({
        "type": "project_completed",
        "title": f"Project Completed: {project_name}",
        "message": f"Project '{project_name}' has been marked as completed by {current_user.full_name}",
        "entity_type": "project",
        "entity_id": project_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "is_read": False
    })
    
    return {
        "success": True,
        "message": f"Project '{project_name}' has been marked as completed",
        "project_id": project_id,
        "completed_at": update_data["completed_at"],
        "completed_by": current_user.full_name,
        "force_completed": request.force_complete
    }


@router.patch("/{project_id}/status")
async def update_project_status(
    project_id: str,
    request: ProjectStatusUpdateRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Update project status with validation.
    
    Note: Direct updates to 'completed' status are blocked.
    Use the /complete endpoint instead.
    """
    db = get_db()
    
    # Block direct completion
    if request.status.lower() == "completed":
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Cannot directly set project status to 'completed'. Use the completion endpoint.",
                "endpoint": f"POST /api/project-completion/{project_id}/complete",
                "reason": "Project completion requires validation of timeline and payment status."
            }
        )
    
    # Get project
    project = await db.projects.find_one({"id": project_id}, {"_id": 0})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Valid status transitions
    valid_statuses = ["active", "on_hold", "at_risk", "delayed", "cancelled"]
    if request.status.lower() not in valid_statuses:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid status. Valid values: {', '.join(valid_statuses)}"
        )
    
    # Update status
    update_data = {
        "status": request.status.lower(),
        "status_notes": request.notes,
        "status_updated_by": current_user.id,
        "status_updated_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.projects.update_one(
        {"id": project_id},
        {"$set": update_data}
    )
    
    project_name = project.get('name') or project.get('project_name') or 'Unnamed Project'
    
    return {
        "success": True,
        "message": f"Project status updated to '{request.status}'",
        "project_id": project_id,
        "project_name": project_name,
        "new_status": request.status.lower()
    }


@router.get("/pending-completion")
async def get_projects_pending_completion(
    current_user: User = Depends(get_current_user)
):
    """
    Get list of projects that are ready for completion (timeline over, payments received).
    """
    db = get_db()
    
    # Only certain roles can access this
    allowed_roles = ADMIN_ROLES + PROJECT_ROLES
    if current_user.role not in allowed_roles:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Get all active projects
    projects = await db.projects.find(
        {"status": {"$in": ["active", "on_hold"]}},
        {"_id": 0}
    ).to_list(500)
    
    pending_completion = []
    
    for project in projects:
        project_id = project.get('id')
        try:
            validation = await validate_project_completion(project_id, current_user)
            if validation.can_complete:
                pending_completion.append({
                    "project_id": project_id,
                    "project_name": validation.project_name,
                    "client_name": project.get('client_name', 'Unknown'),
                    "status": project.get('status'),
                    "timeline_status": validation.timeline_status,
                    "payment_status": {
                        "total_installments": validation.payment_status.get('total_installments', 0),
                        "received_installments": validation.payment_status.get('received_installments', 0),
                        "received_total": validation.payment_status.get('received_total', 0)
                    },
                    "warnings": validation.warnings
                })
        except Exception:
            continue
    
    return {
        "count": len(pending_completion),
        "projects": pending_completion
    }


@router.post("/recalculate-statuses")
async def recalculate_project_statuses(
    current_user: User = Depends(get_current_user)
):
    """
    Recalculate auto-status for all active projects.
    
    Status Logic:
    - active: Default - Project ongoing, timeline not exceeded
    - at_risk: Timeline < 30 days remaining AND (payments incomplete OR deliverables < 80%)
    - delayed: Timeline exceeded but NOT completed
    - completed: All conditions met (must go through /complete endpoint)
    """
    db = get_db()
    
    # Only admin/PM can trigger recalculation
    if current_user.role not in ADMIN_ROLES + PROJECT_ROLES:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Get all non-completed projects
    projects = await db.projects.find(
        {"status": {"$nin": ["completed", "cancelled", "on_hold"]}},
        {"_id": 0}
    ).to_list(500)
    
    results = {
        "processed": 0,
        "status_changes": [],
        "errors": []
    }
    
    for project in projects:
        project_id = project.get('id')
        project_name = project.get('name') or project.get('project_name') or 'Unnamed'
        current_status = project.get('status', 'active')
        
        try:
            validation = await validate_project_completion(project_id, current_user)
            
            # Determine new status based on validation
            new_status = current_status
            status_reason = None
            
            timeline = validation.timeline_status
            payment = validation.payment_status
            
            days_remaining = timeline.get('days_remaining')
            timeline_complete = timeline.get('is_complete', False)
            payments_complete = payment.get('is_complete', False)
            
            # Calculate deliverables percentage (meetings delivered / committed)
            meetings_committed = project.get('total_meetings_committed', 0)
            meetings_delivered = project.get('total_meetings_delivered', 0)
            deliverables_pct = (meetings_delivered / meetings_committed * 100) if meetings_committed > 0 else 0
            
            if timeline_complete and not payments_complete:
                new_status = "delayed"
                status_reason = f"Timeline over but payments incomplete ({payment.get('received_installments', 0)}/{payment.get('total_installments', 0)} received)"
            elif days_remaining is not None and days_remaining <= 0 and current_status != "completed":
                new_status = "delayed"
                status_reason = f"Timeline exceeded by {abs(days_remaining)} days"
            elif days_remaining is not None and 0 < days_remaining <= 30:
                # Check if at risk
                if not payments_complete or deliverables_pct < 80:
                    new_status = "at_risk"
                    reasons = []
                    if not payments_complete:
                        reasons.append(f"payments {payment.get('received_installments', 0)}/{payment.get('total_installments', 0)}")
                    if deliverables_pct < 80:
                        reasons.append(f"deliverables {deliverables_pct:.0f}%")
                    status_reason = f"{days_remaining} days remaining, issues: {', '.join(reasons)}"
            
            # Update if status changed
            if new_status != current_status:
                await db.projects.update_one(
                    {"id": project_id},
                    {"$set": {
                        "status": new_status,
                        "status_auto_updated": True,
                        "status_auto_reason": status_reason,
                        "status_auto_updated_at": datetime.now(timezone.utc).isoformat(),
                        "updated_at": datetime.now(timezone.utc).isoformat()
                    }}
                )
                
                results["status_changes"].append({
                    "project_id": project_id,
                    "project_name": project_name,
                    "old_status": current_status,
                    "new_status": new_status,
                    "reason": status_reason
                })
            
            results["processed"] += 1
            
        except Exception as e:
            results["errors"].append({
                "project_id": project_id,
                "error": str(e)
            })
    
    return results


@router.get("/{project_id}/timeline")
async def get_project_timeline(
    project_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get detailed project timeline information.
    Shows start date, end date, tenure, and remaining/overdue days.
    """
    db = get_db()
    
    project = await db.projects.find_one({"id": project_id}, {"_id": 0})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    project_name = project.get('name') or project.get('project_name') or 'Unnamed Project'
    
    # Get kickoff request for original tenure info
    kickoff = None
    if project.get('kickoff_request_id'):
        kickoff = await db.kickoff_requests.find_one(
            {"id": project.get('kickoff_request_id')}, 
            {"_id": 0}
        )
    
    # Parse dates
    start_date = project.get('start_date') or project.get('kickoff_accepted_at')
    end_date = project.get('end_date')
    tenure_months = project.get('tenure_months')
    
    if isinstance(start_date, str):
        start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
    if isinstance(end_date, str):
        end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
    
    # Calculate if not set
    if start_date and tenure_months and not end_date:
        end_date = start_date + relativedelta(months=tenure_months)
    
    # Calculate days remaining/overdue
    now = datetime.now(timezone.utc)
    days_info = {}
    
    if end_date:
        total_days = (end_date - start_date).days if start_date else None
        elapsed_days = (now - start_date).days if start_date else None
        remaining_days = (end_date - now).days
        
        if remaining_days > 0:
            days_info = {
                "days_remaining": remaining_days,
                "days_overdue": 0,
                "is_overdue": False,
                "progress_percentage": (elapsed_days / total_days * 100) if total_days else 0
            }
        else:
            days_info = {
                "days_remaining": 0,
                "days_overdue": abs(remaining_days),
                "is_overdue": True,
                "progress_percentage": 100
            }
    
    return {
        "project_id": project_id,
        "project_name": project_name,
        "client_name": project.get('client_name'),
        "status": project.get('status'),
        "timeline": {
            "start_date": start_date.isoformat() if start_date else None,
            "end_date": end_date.isoformat() if end_date else None,
            "tenure_months": tenure_months,
            "kickoff_accepted_at": project.get('kickoff_accepted_at'),
            **days_info
        },
        "kickoff_details": {
            "original_tenure_months": kickoff.get('project_tenure_months') if kickoff else None,
            "expected_start_date": kickoff.get('expected_start_date') if kickoff else None,
            "accepted_at": kickoff.get('accepted_at') if kickoff else None
        } if kickoff else None
    }
