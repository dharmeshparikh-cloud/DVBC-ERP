"""
Go-Live Router - Employee Activation Approval Workflow

This module handles the Go-Live approval process where:
1. HR prepares employee checklist items (documents, bank details, etc.)
2. HR submits Go-Live request for admin approval
3. Admin reviews and approves/rejects
4. On approval, employee status becomes 'active'
"""

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Response
from fastapi.responses import StreamingResponse
from datetime import datetime, timezone
from typing import Optional
import uuid
import os
import io

from .models import User
from .deps import get_db, get_role_group, has_role
from .auth import get_current_user
from services.email_service import send_email
from services.bank_validation_service import (
    validate_ifsc, 
    validate_account_number, 
    validate_bank_proof_file,
    mask_account_number,
    ALLOWED_BANK_PROOF_TYPES,
    MAX_BANK_PROOF_SIZE
)
import re


async def generate_employee_id(db) -> str:
    """Generate next sequential Employee ID in DVBC format."""
    
    employees = await db.employees.find(
        {"employee_id": {"$regex": "^DVBC\\d+$"}},
        {"employee_id": 1}
    ).to_list(None)
    
    max_num = 0
    for emp in employees:
        match = re.match(r"DVBC(\d+)", emp.get("employee_id", ""))
        if match:
            num = int(match.group(1))
            if num > max_num:
                max_num = num
    
    next_num = max_num + 1
    return f"DVBC{next_num:03d}"

router = APIRouter(prefix="/go-live", tags=["Go-Live"])

# Directory for storing bank proof documents
BANK_PROOF_DIR = "/app/backend/uploads/bank_proofs"
os.makedirs(BANK_PROOF_DIR, exist_ok=True)


# ==================== CHECKLIST ENDPOINTS ====================

@router.get("/checklist/{employee_id}")
async def get_go_live_checklist(
    employee_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get Go-Live checklist for an employee.
    Shows completion status of all required items before activation.
    """
    db = get_db()
    
    # Get employee details
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        employee = await db.employees.find_one({"employee_id": employee_id}, {"_id": 0})
    
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Build checklist based on employee data
    checklist = {
        "personal_details": {
            "label": "Personal Details Complete",
            "completed": bool(employee.get("first_name") and employee.get("last_name") and employee.get("phone")),
            "icon": "User"
        },
        "official_email": {
            "label": "Official Email Assigned",
            "completed": bool(employee.get("official_email") or employee.get("email")),
            "icon": "Mail"
        },
        "department_assigned": {
            "label": "Department Assigned",
            "completed": bool(employee.get("department")),
            "icon": "Building2"
        },
        "reporting_manager": {
            "label": "Reporting Manager Assigned",
            "completed": bool(employee.get("reporting_manager") or employee.get("reporting_manager_id")),
            "icon": "User"
        },
        "bank_details": {
            "label": "Bank Details Provided",
            "completed": bool(employee.get("bank_account_number") or employee.get("bank_details")),
            "icon": "CreditCard"
        },
        "bank_verified": {
            "label": "Bank Details Verified",
            "completed": employee.get("bank_verified", False),
            "icon": "Shield"
        },
        "documents_uploaded": {
            "label": "Required Documents Uploaded",
            "completed": bool(employee.get("documents") and len(employee.get("documents", [])) >= 2),
            "icon": "FileText"
        },
        "portal_access": {
            "label": "Portal Access Enabled",
            "completed": bool(employee.get("user_id")),
            "icon": "Key"
        }
    }
    
    # Calculate overall readiness
    completed_count = sum(1 for item in checklist.values() if item["completed"])
    total_count = len(checklist)
    is_ready = completed_count == total_count
    
    # Get existing go-live request if any
    go_live_request = await db.go_live_requests.find_one(
        {"employee_id": employee.get("id", employee_id)},
        {"_id": 0}
    )
    
    return {
        "employee": {
            "id": employee.get("id"),
            "employee_id": employee.get("employee_id"),
            "name": f"{employee.get('first_name', '')} {employee.get('last_name', '')}".strip(),
            "email": employee.get("official_email") or employee.get("personal_email"),
            "department": employee.get("department"),
            "designation": employee.get("designation"),
            "go_live_status": employee.get("go_live_status", "not_submitted"),
            "joining_date": employee.get("joining_date") or employee.get("date_of_joining")
        },
        "checklist": checklist,
        "summary": {
            "completed": completed_count,
            "total": total_count,
            "percentage": round((completed_count / total_count) * 100),
            "is_ready": is_ready
        },
        "request": go_live_request
    }


# ==================== SUBMISSION ENDPOINTS ====================

@router.post("/submit/{employee_id}")
async def submit_go_live_request(
    employee_id: str,
    data: dict,
    current_user: User = Depends(get_current_user)
):
    """
    Submit Go-Live request for admin approval.
    
    ACCESS: HR roles can submit go-live requests.
    """
    db = get_db()
    
    # Authorization: HR roles
    hr_roles = get_role_group("HR_ROLES", fail_closed=True) or []
    hr_admin_roles = get_role_group("HR_ADMIN_ROLES", fail_closed=True) or []
    admin_roles = get_role_group("ADMIN_ROLES", fail_closed=False) or ["admin"]
    
    allowed_roles = list(set(hr_roles + hr_admin_roles + admin_roles))
    if not has_role(current_user.role, allowed_roles):
        raise HTTPException(status_code=403, detail="Only HR or Admin can submit Go-Live requests")
    
    # Get employee
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        employee = await db.employees.find_one({"employee_id": employee_id}, {"_id": 0})
    
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Check if already active
    if employee.get("go_live_status") == "active":
        raise HTTPException(status_code=400, detail="Employee is already active")
    
    # Check if request already pending
    existing = await db.go_live_requests.find_one({
        "employee_id": employee.get("id"),
        "status": "pending"
    })
    if existing:
        raise HTTPException(status_code=400, detail="A Go-Live request is already pending for this employee")
    
    # Get checklist status
    checklist_data = data.get("checklist", {})
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Create go-live request
    request_id = str(uuid.uuid4())
    go_live_request = {
        "id": request_id,
        "employee_id": employee.get("id"),
        "employee_code": employee.get("employee_id"),
        "employee_name": f"{employee.get('first_name', '')} {employee.get('last_name', '')}".strip(),
        "department": employee.get("department"),
        "designation": employee.get("designation"),
        "submitted_by": current_user.id,
        "submitted_by_name": current_user.full_name,
        "submitted_at": now,
        "status": "pending",
        "checklist_snapshot": checklist_data,
        "notes": data.get("notes", ""),
        "created_at": now,
        "updated_at": now
    }
    
    await db.go_live_requests.insert_one(go_live_request)
    
    # Update employee status
    await db.employees.update_one(
        {"id": employee.get("id")},
        {"$set": {
            "go_live_status": "pending",
            "go_live_requested_at": now,
            "go_live_requested_by": current_user.id
        }}
    )
    
    # Create notification for admins
    admin_users = await db.users.find({"role": "admin", "is_active": True}, {"_id": 0, "id": 1}).to_list(100)
    for admin in admin_users:
        await db.notifications.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": admin["id"],
            "type": "go_live_request",
            "title": "Go-Live Approval Required",
            "message": f"Go-Live request submitted for {go_live_request['employee_name']} ({employee.get('department', 'N/A')})",
            "reference_type": "go_live",
            "reference_id": request_id,
            "is_read": False,
            "created_at": now
        })
    
    # Log audit trail
    await db.go_live_audit_logs.insert_one({
        "id": str(uuid.uuid4()),
        "request_id": request_id,
        "employee_id": employee.get("id"),
        "action": "submitted",
        "actor_id": current_user.id,
        "actor_name": current_user.full_name,
        "actor_role": current_user.role,
        "details": {"notes": data.get("notes", "")},
        "timestamp": now
    })
    
    return {
        "message": "Go-Live request submitted for admin approval",
        "request_id": request_id,
        "status": "pending"
    }


# ==================== ADMIN APPROVAL ENDPOINTS ====================

@router.get("/pending")
async def get_pending_go_live_requests(
    current_user: User = Depends(get_current_user)
):
    """
    Get all pending Go-Live requests.
    
    ACCESS: Admin and HR Admin can view pending requests.
    """
    db = get_db()
    
    # Authorization
    hr_admin_roles = get_role_group("HR_ADMIN_ROLES", fail_closed=True) or []
    admin_roles = get_role_group("ADMIN_ROLES", fail_closed=False) or ["admin"]
    
    if not has_role(current_user.role, hr_admin_roles + admin_roles):
        raise HTTPException(status_code=403, detail="Only Admin can view pending Go-Live requests")
    
    requests = await db.go_live_requests.find(
        {"status": "pending"},
        {"_id": 0}
    ).sort("submitted_at", -1).to_list(100)
    
    return requests


@router.get("/all")
async def get_all_go_live_requests(
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """
    Get all Go-Live requests with optional status filter.
    
    ACCESS: HR and Admin roles.
    """
    db = get_db()
    
    # Authorization
    hr_roles = get_role_group("HR_ROLES", fail_closed=True) or []
    hr_admin_roles = get_role_group("HR_ADMIN_ROLES", fail_closed=True) or []
    admin_roles = get_role_group("ADMIN_ROLES", fail_closed=False) or ["admin"]
    
    allowed_roles = list(set(hr_roles + hr_admin_roles + admin_roles))
    if not has_role(current_user.role, allowed_roles):
        raise HTTPException(status_code=403, detail="Access denied")
    
    query = {}
    if status:
        query["status"] = status
    
    requests = await db.go_live_requests.find(query, {"_id": 0}).sort("created_at", -1).to_list(500)
    
    return requests


@router.get("/request/{request_id}/details")
async def get_go_live_request_details(
    request_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get detailed Go-Live request info for Admin approval review.
    Includes all employee details, CTC structure, documents, etc.
    
    ACCESS: Admin only.
    """
    db = get_db()
    
    # Authorization: Admin only
    admin_roles = get_role_group("ADMIN_ROLES", fail_closed=False) or ["admin"]
    hr_roles = get_role_group("HR_ROLES", fail_closed=True) or []
    allowed_roles = list(set(admin_roles + hr_roles))
    
    if not has_role(current_user.role, allowed_roles):
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Get request
    request = await db.go_live_requests.find_one({"id": request_id}, {"_id": 0})
    if not request:
        raise HTTPException(status_code=404, detail="Go-Live request not found")
    
    # Get employee details
    employee = await db.employees.find_one({"id": request.get("employee_id")}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Get CTC structure if exists
    ctc_structure = None
    if employee.get("ctc_structure_id"):
        ctc_structure = await db.ctc_structures.find_one(
            {"id": employee["ctc_structure_id"]}, {"_id": 0}
        )
    
    # Get onboarding submission if exists
    submission = None
    if employee.get("onboarding_submission_id"):
        submission = await db.onboarding_submissions.find_one(
            {"id": employee["onboarding_submission_id"]}, {"_id": 0}
        )
    
    # Get manager details if exists
    reporting_manager = None
    if employee.get("reporting_manager_id"):
        reporting_manager = await db.employees.find_one(
            {"id": employee["reporting_manager_id"]},
            {"_id": 0, "id": 1, "employee_id": 1, "full_name": 1, "designation": 1}
        )
    
    # Generate preview Employee ID (what will be assigned on approval)
    preview_employee_id = None
    if not employee.get("employee_id") or employee.get("employee_id_pending"):
        preview_employee_id = await generate_employee_id(db)
    
    return {
        "request": request,
        "employee": {
            "id": employee.get("id"),
            "current_employee_id": employee.get("employee_id"),
            "employee_id_pending": employee.get("employee_id_pending", False),
            "preview_employee_id": preview_employee_id,
            "full_name": employee.get("full_name"),
            "first_name": employee.get("first_name"),
            "last_name": employee.get("last_name"),
            "personal_email": employee.get("personal_email"),
            "official_email": employee.get("official_email"),
            "phone": employee.get("phone"),
            "date_of_birth": employee.get("date_of_birth"),
            "gender": employee.get("gender"),
            "department": employee.get("department"),
            "designation": employee.get("designation"),
            "role": employee.get("role"),
            "joining_date": employee.get("joining_date"),
            "reporting_manager_id": employee.get("reporting_manager_id"),
            "reporting_manager_name": employee.get("reporting_manager_name"),
            "employment_type": employee.get("employment_type"),
            "pan_number": employee.get("pan_number"),
            "aadhaar_number": employee.get("aadhaar_number"),
            "bank_account_number": mask_account_number(employee.get("bank_account_number", "")),
            "bank_name": employee.get("bank_name"),
            "ifsc_code": employee.get("ifsc_code"),
            "bank_verified": employee.get("bank_verified", False),
            "documents": employee.get("documents", []),
            "current_ctc": employee.get("current_ctc"),
            "go_live_status": employee.get("go_live_status"),
            "has_portal_access": employee.get("has_portal_access", False)
        },
        "ctc_structure": ctc_structure,
        "reporting_manager": reporting_manager,
        "submission_summary": {
            "id": submission.get("id") if submission else None,
            "status": submission.get("status") if submission else None,
            "submitted_at": submission.get("submitted_at") if submission else None,
            "completed_at": submission.get("completed_at") if submission else None,
            "education": submission.get("education") if submission else None,
            "employment_history": submission.get("employment_history") if submission else None,
            "emergency_contact": submission.get("emergency_contact") if submission else None,
            "professional_reference": submission.get("professional_reference") if submission else None
        } if submission else None
    }


@router.post("/{request_id}/approve")
async def approve_go_live_request(
    request_id: str,
    data: dict = None,
    current_user: User = Depends(get_current_user)
):
    """
    Approve a Go-Live request.
    
    ACCESS: Only Admin can approve Go-Live requests.
    
    WORKFLOW:
    1. Validates request exists and is pending
    2. Generates Employee ID (DVBC format) if not already assigned
    3. Updates request status to 'approved'
    4. Updates employee go_live_status to 'active'
    5. Creates audit log
    6. Notifies HR and employee
    """
    db = get_db()
    
    # Authorization: Admin only
    admin_roles = get_role_group("ADMIN_ROLES", fail_closed=False) or ["admin"]
    if not has_role(current_user.role, admin_roles):
        raise HTTPException(status_code=403, detail="Only Admin can approve Go-Live requests")
    
    # Get request
    request = await db.go_live_requests.find_one({"id": request_id}, {"_id": 0})
    if not request:
        raise HTTPException(status_code=404, detail="Go-Live request not found")
    
    if request.get("status") != "pending":
        raise HTTPException(status_code=400, detail=f"Cannot approve request in '{request.get('status')}' status")
    
    now = datetime.now(timezone.utc).isoformat()
    remarks = data.get("remarks", "") if data else ""
    
    # Get employee to check if Employee ID needs to be generated
    employee = await db.employees.find_one({"id": request.get("employee_id")}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Generate Employee ID if not already assigned
    generated_employee_id = None
    if not employee.get("employee_id") or employee.get("employee_id_pending"):
        generated_employee_id = await generate_employee_id(db)
    
    # Update request
    await db.go_live_requests.update_one(
        {"id": request_id},
        {"$set": {
            "status": "approved",
            "approved_by": current_user.id,
            "approved_by_name": current_user.full_name,
            "approved_at": now,
            "approval_remarks": remarks,
            "generated_employee_id": generated_employee_id,
            "updated_at": now
        }}
    )
    
    # Update employee to active and assign Employee ID
    employee_update = {
        "go_live_status": "active",
        "go_live_approved_at": now,
        "go_live_approved_by": current_user.id,
        "go_live_approved_by_name": current_user.full_name,
        "is_active": True,
        "activation_date": now
    }
    
    # Assign Employee ID if generated
    if generated_employee_id:
        employee_update["employee_id"] = generated_employee_id
        employee_update["employee_id_pending"] = False
        employee_update["employee_id_assigned_at"] = now
        employee_update["employee_id_assigned_by"] = current_user.id
    
    await db.employees.update_one(
        {"id": request.get("employee_id")},
        {"$set": employee_update}
    )
    
    # Also update the onboarding submission if exists
    if employee.get("onboarding_submission_id"):
        await db.onboarding_submissions.update_one(
            {"id": employee["onboarding_submission_id"]},
            {"$set": {
                "employee_id_generated": generated_employee_id or employee.get("employee_id"),
                "employee_id_pending": False
            }}
        )
    
    # Notify HR who submitted
    if request.get("submitted_by"):
        await db.notifications.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": request["submitted_by"],
            "type": "go_live_approved",
            "title": "Go-Live Approved",
            "message": f"Go-Live request for {request.get('employee_name')} has been approved by {current_user.full_name}",
            "reference_type": "go_live",
            "reference_id": request_id,
            "is_read": False,
            "created_at": now
        })
    
    # Notify employee if they have a user account
    employee = await db.employees.find_one({"id": request.get("employee_id")}, {"_id": 0, "user_id": 1})
    if employee and employee.get("user_id"):
        await db.notifications.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": employee["user_id"],
            "type": "go_live_activated",
            "title": "Welcome! Your Account is Now Active",
            "message": "Congratulations! Your employee account has been activated. You now have full access to the portal.",
            "reference_type": "go_live",
            "reference_id": request_id,
            "is_read": False,
            "created_at": now
        })
    
    # Audit log
    await db.go_live_audit_logs.insert_one({
        "id": str(uuid.uuid4()),
        "request_id": request_id,
        "employee_id": request.get("employee_id"),
        "action": "approved",
        "actor_id": current_user.id,
        "actor_name": current_user.full_name,
        "actor_role": current_user.role,
        "details": {"remarks": remarks},
        "timestamp": now
    })
    
    # Send activation email to employee and HR
    employee_full = await db.employees.find_one({"id": request.get("employee_id")}, {"_id": 0})
    if employee_full:
        employee_email = employee_full.get("email") or employee_full.get("personal_email")
        
        # Get reporting manager name
        reporting_manager_name = employee_full.get("reporting_manager_name", "")
        if not reporting_manager_name and employee_full.get("reporting_manager_id"):
            manager = await db.employees.find_one({"id": employee_full.get("reporting_manager_id")}, {"_id": 0, "full_name": 1})
            reporting_manager_name = manager.get("full_name") if manager else "To be assigned"
        
        # ERP Login URL
        erp_login_url = os.environ.get("FRONTEND_URL", "https://data-sync-upgrade.preview.emergentagent.com") + "/login"
        
        if employee_email:
            try:
                # Email to Employee with login details
                await send_email(
                    to_email=employee_email,
                    subject="Welcome to D&V Business Consulting - Your Account is Now Active!",
                    html_content=f"""
                    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                        <div style="background: linear-gradient(135deg, #f97316, #ea580c); padding: 30px; text-align: center;">
                            <h1 style="color: white; margin: 0;">Welcome Aboard!</h1>
                            <p style="color: rgba(255,255,255,0.9); margin: 10px 0 0;">D&V Business Consulting</p>
                        </div>
                        <div style="padding: 30px; background: #f9f9f9;">
                            <p>Dear <strong>{employee_full.get('full_name', 'Employee')}</strong>,</p>
                            <p>Congratulations! Your employee account has been activated. You can now access the NETRA ERP portal.</p>
                            
                            <div style="background: white; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #f97316;">
                                <h3 style="margin-top: 0; color: #333;">Your Login Details</h3>
                                <table style="width: 100%; border-collapse: collapse;">
                                    <tr><td style="padding: 8px 0; color: #666;">Employee ID:</td><td style="padding: 8px 0; font-weight: bold;">{employee_full.get('employee_id')}</td></tr>
                                    <tr><td style="padding: 8px 0; color: #666;">Official Email:</td><td style="padding: 8px 0; font-weight: bold;">{employee_full.get('email')}</td></tr>
                                    <tr><td style="padding: 8px 0; color: #666;">Department:</td><td style="padding: 8px 0; font-weight: bold;">{employee_full.get('department')}</td></tr>
                                    <tr><td style="padding: 8px 0; color: #666;">Designation:</td><td style="padding: 8px 0; font-weight: bold;">{employee_full.get('designation')}</td></tr>
                                    <tr><td style="padding: 8px 0; color: #666;">Reporting Manager:</td><td style="padding: 8px 0; font-weight: bold;">{reporting_manager_name or 'To be assigned'}</td></tr>
                                </table>
                            </div>
                            
                            <div style="text-align: center; margin: 30px 0;">
                                <a href="{erp_login_url}" style="display: inline-block; background: #f97316; color: white; padding: 14px 40px; text-decoration: none; border-radius: 8px; font-weight: bold; font-size: 16px;">
                                    Login to NETRA ERP
                                </a>
                            </div>
                            
                            <p style="background: #fef3c7; padding: 12px; border-radius: 6px; font-size: 14px;">
                                <strong>Note:</strong> Use your <strong>Employee ID</strong> and the password shared during onboarding to login.
                            </p>
                            
                            <p>If you have any questions or need assistance, please contact HR.</p>
                            
                            <p style="margin-top: 30px;">Best Regards,<br><strong>D&V Business Consulting</strong></p>
                        </div>
                        <div style="background: #333; padding: 15px; text-align: center;">
                            <p style="color: #999; margin: 0; font-size: 12px;">This is an automated email from NETRA ERP</p>
                        </div>
                    </div>
                    """
                )
            except Exception as e:
                print(f"Failed to send activation email to employee: {e}")
        
        # Email to HR who submitted the request
        if request.get("submitted_by"):
            hr_user = await db.users.find_one({"id": request["submitted_by"]}, {"_id": 0})
            if hr_user and hr_user.get("email"):
                try:
                    await send_email(
                        to_email=hr_user["email"],
                        subject=f"Go-Live Approved: {employee_full.get('full_name')} is Now Active",
                        html_content=f"""
                        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                            <div style="background: #16a34a; padding: 20px; text-align: center;">
                                <h2 style="color: white; margin: 0;">Go-Live Approved ✓</h2>
                            </div>
                            <div style="padding: 30px; background: #f9f9f9;">
                                <p>Hi {hr_user.get('full_name', 'HR')},</p>
                                <p>The Go-Live request for <strong>{employee_full.get('full_name')}</strong> has been approved by <strong>{current_user.full_name}</strong>.</p>
                                
                                <div style="background: white; padding: 20px; border-radius: 8px; margin: 20px 0;">
                                    <h3 style="margin-top: 0;">Employee Details</h3>
                                    <p><strong>Employee ID:</strong> {employee_full.get('employee_id')}</p>
                                    <p><strong>Name:</strong> {employee_full.get('full_name')}</p>
                                    <p><strong>Email:</strong> {employee_full.get('email')}</p>
                                    <p><strong>Department:</strong> {employee_full.get('department')}</p>
                                    <p><strong>Designation:</strong> {employee_full.get('designation')}</p>
                                    <p><strong>Status:</strong> <span style="color: #16a34a; font-weight: bold;">ACTIVE</span></p>
                                </div>
                                
                                <p>The employee can now login to NETRA ERP using their Employee ID.</p>
                                <p>You can view their details in the <a href="https://data-sync-upgrade.preview.emergentagent.com/employees?edit={employee_full.get('id')}">Employee Directory</a>.</p>
                            </div>
                        </div>
                        """
                    )
                except Exception as e:
                    print(f"Failed to send Go-Live approval email to HR: {e}")
    
    return {
        "message": "Go-Live approved. Employee is now active.",
        "status": "approved",
        "employee_name": request.get("employee_name")
    }


@router.post("/{request_id}/reject")
async def reject_go_live_request(
    request_id: str,
    data: dict,
    current_user: User = Depends(get_current_user)
):
    """
    Reject a Go-Live request.
    
    ACCESS: Only Admin can reject Go-Live requests.
    """
    db = get_db()
    
    # Authorization: Admin only
    admin_roles = get_role_group("ADMIN_ROLES", fail_closed=False) or ["admin"]
    if not has_role(current_user.role, admin_roles):
        raise HTTPException(status_code=403, detail="Only Admin can reject Go-Live requests")
    
    # Get request
    request = await db.go_live_requests.find_one({"id": request_id}, {"_id": 0})
    if not request:
        raise HTTPException(status_code=404, detail="Go-Live request not found")
    
    if request.get("status") != "pending":
        raise HTTPException(status_code=400, detail=f"Cannot reject request in '{request.get('status')}' status")
    
    reason = data.get("reason", "")
    if not reason:
        raise HTTPException(status_code=400, detail="Rejection reason is required")
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Update request
    await db.go_live_requests.update_one(
        {"id": request_id},
        {"$set": {
            "status": "rejected",
            "rejected_by": current_user.id,
            "rejected_by_name": current_user.full_name,
            "rejected_at": now,
            "rejection_reason": reason,
            "updated_at": now
        }}
    )
    
    # Update employee status back to rejected
    await db.employees.update_one(
        {"id": request.get("employee_id")},
        {"$set": {
            "go_live_status": "rejected",
            "go_live_rejection_reason": reason,
            "go_live_rejected_at": now
        }}
    )
    
    # Notify HR who submitted
    if request.get("submitted_by"):
        await db.notifications.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": request["submitted_by"],
            "type": "go_live_rejected",
            "title": "Go-Live Rejected",
            "message": f"Go-Live request for {request.get('employee_name')} was rejected. Reason: {reason}",
            "reference_type": "go_live",
            "reference_id": request_id,
            "is_read": False,
            "created_at": now
        })
    
    # Audit log
    await db.go_live_audit_logs.insert_one({
        "id": str(uuid.uuid4()),
        "request_id": request_id,
        "employee_id": request.get("employee_id"),
        "action": "rejected",
        "actor_id": current_user.id,
        "actor_name": current_user.full_name,
        "actor_role": current_user.role,
        "details": {"reason": reason},
        "timestamp": now
    })
    
    return {
        "message": "Go-Live request rejected",
        "status": "rejected"
    }


# ==================== BANK VERIFICATION ====================

@router.post("/bank-verify/{employee_id}")
async def verify_bank_details(
    employee_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Mark employee bank details as verified.
    
    ACCESS: HR Manager and Admin only.
    """
    db = get_db()
    
    # Authorization
    hr_admin_roles = get_role_group("HR_ADMIN_ROLES", fail_closed=True) or []
    admin_roles = get_role_group("ADMIN_ROLES", fail_closed=False) or ["admin"]
    
    if not has_role(current_user.role, hr_admin_roles + admin_roles):
        raise HTTPException(status_code=403, detail="Only HR Manager or Admin can verify bank details")
    
    # Get employee
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        employee = await db.employees.find_one({"employee_id": employee_id}, {"_id": 0})
    
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    now = datetime.now(timezone.utc).isoformat()
    
    await db.employees.update_one(
        {"id": employee.get("id", employee_id)},
        {"$set": {
            "bank_verified": True,
            "bank_verified_by": current_user.id,
            "bank_verified_by_name": current_user.full_name,
            "bank_verified_at": now
        }}
    )
    
    # Audit log
    await db.go_live_audit_logs.insert_one({
        "id": str(uuid.uuid4()),
        "employee_id": employee.get("id", employee_id),
        "action": "bank_verified",
        "actor_id": current_user.id,
        "actor_name": current_user.full_name,
        "actor_role": current_user.role,
        "timestamp": now
    })
    
    return {"message": "Bank details verified successfully"}


# ==================== BANK VALIDATION ENDPOINTS ====================

@router.post("/validate-ifsc")
async def validate_ifsc_code(
    data: dict,
    current_user: User = Depends(get_current_user)
):
    """
    Validate IFSC code format and lookup bank details.
    
    Request: { "ifsc_code": "SBIN0001234" }
    
    Returns bank name, branch, city, state if valid.
    """
    ifsc_code = data.get("ifsc_code", "")
    result = await validate_ifsc(ifsc_code)
    return result


@router.post("/validate-account")
async def validate_account_number_endpoint(
    data: dict,
    current_user: User = Depends(get_current_user)
):
    """
    Validate bank account number format.
    
    Request: { "account_number": "12345678901", "ifsc_code": "SBIN0001234" }
    
    If IFSC is provided, validates against bank-specific patterns.
    """
    account_number = data.get("account_number", "")
    ifsc_code = data.get("ifsc_code", "")
    result = validate_account_number(account_number, ifsc_code)
    return result


@router.post("/validate-bank-details/{employee_id}")
async def validate_employee_bank_details(
    employee_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Validate bank details for an employee and store validation results.
    
    Validates both IFSC and account number, updates employee record with results.
    """
    db = get_db()
    
    # Get employee
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        employee = await db.employees.find_one({"employee_id": employee_id}, {"_id": 0})
    
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Get bank details
    ifsc_code = employee.get("ifsc_code") or employee.get("bank_ifsc")
    account_number = employee.get("bank_account_number") or employee.get("account_number")
    
    if not ifsc_code and not account_number:
        raise HTTPException(status_code=400, detail="No bank details found for this employee")
    
    results = {
        "ifsc_validation": None,
        "account_validation": None,
        "overall_valid": False
    }
    
    # Validate IFSC
    if ifsc_code:
        results["ifsc_validation"] = await validate_ifsc(ifsc_code)
    
    # Validate account number
    if account_number:
        results["account_validation"] = validate_account_number(account_number, ifsc_code)
    
    # Determine overall validity
    ifsc_valid = results["ifsc_validation"]["valid"] if results["ifsc_validation"] else True
    account_valid = results["account_validation"]["valid"] if results["account_validation"] else True
    results["overall_valid"] = ifsc_valid and account_valid
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Store validation results
    await db.employees.update_one(
        {"id": employee.get("id", employee_id)},
        {"$set": {
            "bank_validation_results": results,
            "bank_validation_at": now,
            "bank_validation_by": current_user.id
        }}
    )
    
    # Audit log
    await db.go_live_audit_logs.insert_one({
        "id": str(uuid.uuid4()),
        "employee_id": employee.get("id", employee_id),
        "action": "bank_validated",
        "actor_id": current_user.id,
        "actor_name": current_user.full_name,
        "actor_role": current_user.role,
        "details": {
            "ifsc_valid": ifsc_valid,
            "account_valid": account_valid,
            "overall_valid": results["overall_valid"]
        },
        "timestamp": now
    })
    
    return results


# ==================== BANK PROOF DOCUMENT ENDPOINTS ====================

@router.post("/bank-proof/upload/{employee_id}")
async def upload_bank_proof(
    employee_id: str,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """
    Upload bank proof document (cancelled cheque, passbook, etc.)
    
    Allowed types: PDF, JPG, PNG, WEBP
    Max size: 5 MB
    """
    db = get_db()
    
    # Authorization
    hr_roles = get_role_group("HR_ROLES", fail_closed=True) or []
    hr_admin_roles = get_role_group("HR_ADMIN_ROLES", fail_closed=True) or []
    admin_roles = get_role_group("ADMIN_ROLES", fail_closed=False) or ["admin"]
    
    allowed_roles = list(set(hr_roles + hr_admin_roles + admin_roles))
    if not has_role(current_user.role, allowed_roles):
        raise HTTPException(status_code=403, detail="Only HR or Admin can upload bank proofs")
    
    # Get employee
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        employee = await db.employees.find_one({"employee_id": employee_id}, {"_id": 0})
    
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Read file content
    content = await file.read()
    file_size = len(content)
    
    # Validate file
    validation = validate_bank_proof_file(file.content_type, file_size)
    if not validation["valid"]:
        raise HTTPException(status_code=400, detail=validation["error"])
    
    # Generate unique filename
    file_ext = ALLOWED_BANK_PROOF_TYPES.get(file.content_type, '.bin')
    document_id = str(uuid.uuid4())
    filename = f"{employee.get('id', employee_id)}_{document_id}{file_ext}"
    file_path = os.path.join(BANK_PROOF_DIR, filename)
    
    # Save file
    with open(file_path, 'wb') as f:
        f.write(content)
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Store document metadata
    document_record = {
        "id": document_id,
        "employee_id": employee.get("id", employee_id),
        "original_filename": file.filename,
        "stored_filename": filename,
        "file_path": file_path,
        "file_size": file_size,
        "content_type": file.content_type,
        "uploaded_by": current_user.id,
        "uploaded_by_name": current_user.full_name,
        "uploaded_at": now,
        "document_type": "bank_proof"
    }
    
    # Update employee with bank proof reference
    await db.employees.update_one(
        {"id": employee.get("id", employee_id)},
        {
            "$set": {"bank_proof_uploaded": True, "bank_proof_uploaded_at": now},
            "$push": {"bank_proof_documents": document_record}
        }
    )
    
    # Audit log
    await db.go_live_audit_logs.insert_one({
        "id": str(uuid.uuid4()),
        "employee_id": employee.get("id", employee_id),
        "action": "bank_proof_uploaded",
        "actor_id": current_user.id,
        "actor_name": current_user.full_name,
        "actor_role": current_user.role,
        "details": {
            "document_id": document_id,
            "filename": file.filename,
            "file_size": file_size
        },
        "timestamp": now
    })
    
    return {
        "message": "Bank proof uploaded successfully",
        "document_id": document_id,
        "filename": file.filename
    }


@router.get("/bank-proof/download/{employee_id}/{document_id}")
async def download_bank_proof(
    employee_id: str,
    document_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Download bank proof document.
    """
    db = get_db()
    
    # Authorization
    hr_roles = get_role_group("HR_ROLES", fail_closed=True) or []
    hr_admin_roles = get_role_group("HR_ADMIN_ROLES", fail_closed=True) or []
    admin_roles = get_role_group("ADMIN_ROLES", fail_closed=False) or ["admin"]
    
    allowed_roles = list(set(hr_roles + hr_admin_roles + admin_roles))
    if not has_role(current_user.role, allowed_roles):
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Get employee
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        employee = await db.employees.find_one({"employee_id": employee_id}, {"_id": 0})
    
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Find document
    documents = employee.get("bank_proof_documents", [])
    document = next((d for d in documents if d["id"] == document_id), None)
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    file_path = document.get("file_path")
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found on server")
    
    # Read and return file
    with open(file_path, 'rb') as f:
        content = f.read()
    
    return Response(
        content=content,
        media_type=document.get("content_type", "application/octet-stream"),
        headers={
            "Content-Disposition": f"attachment; filename=\"{document.get('original_filename', 'bank_proof')}\""
        }
    )


@router.get("/bank-proof/list/{employee_id}")
async def list_bank_proofs(
    employee_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    List all bank proof documents for an employee.
    """
    db = get_db()
    
    # Authorization
    hr_roles = get_role_group("HR_ROLES", fail_closed=True) or []
    hr_admin_roles = get_role_group("HR_ADMIN_ROLES", fail_closed=True) or []
    admin_roles = get_role_group("ADMIN_ROLES", fail_closed=False) or ["admin"]
    
    allowed_roles = list(set(hr_roles + hr_admin_roles + admin_roles))
    if not has_role(current_user.role, allowed_roles):
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Get employee
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        employee = await db.employees.find_one({"employee_id": employee_id}, {"_id": 0})
    
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    documents = employee.get("bank_proof_documents", [])
    
    # Remove file_path from response for security
    safe_documents = []
    for doc in documents:
        safe_doc = {k: v for k, v in doc.items() if k != "file_path"}
        safe_documents.append(safe_doc)
    
    return {
        "employee_id": employee.get("id", employee_id),
        "employee_name": f"{employee.get('first_name', '')} {employee.get('last_name', '')}".strip(),
        "documents": safe_documents,
        "total": len(safe_documents)
    }


@router.delete("/bank-proof/delete/{employee_id}/{document_id}")
async def delete_bank_proof(
    employee_id: str,
    document_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Delete a bank proof document.
    """
    db = get_db()
    
    # Authorization - Admin only can delete
    admin_roles = get_role_group("ADMIN_ROLES", fail_closed=False) or ["admin"]
    hr_admin_roles = get_role_group("HR_ADMIN_ROLES", fail_closed=True) or []
    
    if not has_role(current_user.role, admin_roles + hr_admin_roles):
        raise HTTPException(status_code=403, detail="Only Admin or HR Admin can delete bank proofs")
    
    # Get employee
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        employee = await db.employees.find_one({"employee_id": employee_id}, {"_id": 0})
    
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Find and remove document
    documents = employee.get("bank_proof_documents", [])
    document = next((d for d in documents if d["id"] == document_id), None)
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Delete file from disk
    file_path = document.get("file_path")
    if file_path and os.path.exists(file_path):
        os.remove(file_path)
    
    now = datetime.now(timezone.utc).isoformat()
    
    # Remove from database
    await db.employees.update_one(
        {"id": employee.get("id", employee_id)},
        {"$pull": {"bank_proof_documents": {"id": document_id}}}
    )
    
    # Check if any documents remain
    remaining = len(documents) - 1
    if remaining == 0:
        await db.employees.update_one(
            {"id": employee.get("id", employee_id)},
            {"$set": {"bank_proof_uploaded": False}}
        )
    
    # Audit log
    await db.go_live_audit_logs.insert_one({
        "id": str(uuid.uuid4()),
        "employee_id": employee.get("id", employee_id),
        "action": "bank_proof_deleted",
        "actor_id": current_user.id,
        "actor_name": current_user.full_name,
        "actor_role": current_user.role,
        "details": {
            "document_id": document_id,
            "filename": document.get("original_filename")
        },
        "timestamp": now
    })
    
    return {"message": "Bank proof deleted successfully"}


# ==================== STATISTICS ====================

@router.get("/stats")
async def get_go_live_stats(
    current_user: User = Depends(get_current_user)
):
    """
    Get Go-Live statistics for dashboard.
    """
    db = get_db()
    
    # Count by status
    pipeline = [
        {"$group": {"_id": "$status", "count": {"$sum": 1}}}
    ]
    
    results = await db.go_live_requests.aggregate(pipeline).to_list(10)
    
    stats = {
        "pending": 0,
        "approved": 0,
        "rejected": 0,
        "total": 0
    }
    
    for r in results:
        if r["_id"] in stats:
            stats[r["_id"]] = r["count"]
        stats["total"] += r["count"]
    
    # Employees needing go-live
    employees_pending = await db.employees.count_documents({
        "$or": [
            {"go_live_status": {"$exists": False}},
            {"go_live_status": None},
            {"go_live_status": "not_submitted"},
            {"go_live_status": "rejected"}
        ]
    })
    
    stats["employees_pending_go_live"] = employees_pending
    
    return stats


# ==================== AUDIT TRAIL ====================

@router.get("/audit/{employee_id}")
async def get_go_live_audit_trail(
    employee_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get audit trail for an employee's Go-Live process.
    """
    db = get_db()
    
    # Authorization
    hr_roles = get_role_group("HR_ROLES", fail_closed=True) or []
    hr_admin_roles = get_role_group("HR_ADMIN_ROLES", fail_closed=True) or []
    admin_roles = get_role_group("ADMIN_ROLES", fail_closed=False) or ["admin"]
    
    allowed_roles = list(set(hr_roles + hr_admin_roles + admin_roles))
    if not has_role(current_user.role, allowed_roles):
        raise HTTPException(status_code=403, detail="Access denied")
    
    logs = await db.go_live_audit_logs.find(
        {"employee_id": employee_id},
        {"_id": 0}
    ).sort("timestamp", -1).to_list(100)
    
    return logs
