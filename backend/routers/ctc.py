"""
CTC Router - CTC Structure Design and Approval Workflow
"""

from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone
from typing import Optional, List
import uuid

from .models import User, CTCStructureRequest
from .deps import get_db
from .auth import get_current_user

router = APIRouter(prefix="/ctc", tags=["CTC Structure"])


# Default CTC Components
DEFAULT_CTC_COMPONENTS = [
    {"key": "basic", "name": "Basic Salary", "calc_type": "percentage_of_ctc", "default_value": 40, "is_mandatory": True, "is_earning": True, "is_taxable": True, "enabled_by_default": True, "order": 1},
    {"key": "hra", "name": "House Rent Allowance", "calc_type": "percentage_of_basic", "default_value": 50, "is_mandatory": False, "is_earning": True, "is_taxable": True, "enabled_by_default": True, "order": 2},
    {"key": "da", "name": "Dearness Allowance", "calc_type": "percentage_of_basic", "default_value": 10, "is_mandatory": False, "is_earning": True, "is_taxable": True, "enabled_by_default": False, "order": 3},
    {"key": "conveyance", "name": "Conveyance Allowance", "calc_type": "fixed_monthly", "default_value": 1600, "is_mandatory": False, "is_earning": True, "is_taxable": False, "enabled_by_default": True, "order": 4},
    {"key": "medical", "name": "Medical Allowance", "calc_type": "fixed_monthly", "default_value": 1250, "is_mandatory": False, "is_earning": True, "is_taxable": False, "enabled_by_default": True, "order": 5},
    {"key": "special_allowance", "name": "Special Allowance", "calc_type": "balance", "default_value": 0, "is_mandatory": True, "is_earning": True, "is_taxable": True, "enabled_by_default": True, "order": 6, "is_balance": True},
    {"key": "pf_employer", "name": "PF (Employer Contribution)", "calc_type": "percentage_of_basic", "default_value": 12, "is_mandatory": False, "is_earning": False, "is_taxable": False, "is_deferred": True, "enabled_by_default": False, "order": 7},
    {"key": "pf_employee", "name": "PF (Employee Contribution)", "calc_type": "percentage_of_basic", "default_value": 12, "is_mandatory": False, "is_earning": False, "is_taxable": False, "is_deduction": True, "enabled_by_default": False, "order": 8},
    {"key": "esic_employer", "name": "ESIC (Employer)", "calc_type": "percentage_of_gross", "default_value": 3.25, "is_mandatory": False, "is_earning": False, "is_taxable": False, "is_deferred": True, "enabled_by_default": False, "order": 9},
    {"key": "esic_employee", "name": "ESIC (Employee)", "calc_type": "percentage_of_gross", "default_value": 0.75, "is_mandatory": False, "is_earning": False, "is_taxable": False, "is_deduction": True, "enabled_by_default": False, "order": 10},
    {"key": "gratuity", "name": "Gratuity", "calc_type": "percentage_of_basic", "default_value": 4.81, "is_mandatory": False, "is_earning": False, "is_taxable": False, "is_deferred": True, "enabled_by_default": False, "order": 11},
    {"key": "retention_bonus", "name": "Retention Bonus", "calc_type": "fixed_annual", "default_value": 0, "is_mandatory": False, "is_earning": True, "is_taxable": True, "is_optional": True, "enabled_by_default": False, "order": 12, "vesting_months": 12},
    {"key": "professional_tax", "name": "Professional Tax", "calc_type": "fixed_monthly", "default_value": 200, "is_mandatory": False, "is_earning": False, "is_taxable": False, "is_deduction": True, "enabled_by_default": False, "order": 13},
]


async def get_ctc_component_master():
    """Get CTC component master configuration from DB or return defaults."""
    db = get_db()
    config = await db.ctc_config.find_one({"type": "component_master"}, {"_id": 0})
    if config:
        return config.get("components", DEFAULT_CTC_COMPONENTS)
    return DEFAULT_CTC_COMPONENTS


def calculate_ctc_breakdown_dynamic(annual_ctc: float, component_config: list, retention_bonus: float = 0, retention_vesting_months: int = 12) -> dict:
    """
    Calculate CTC breakdown dynamically based on enabled components.
    """
    components = {}
    basic_annual = 0
    gross_monthly = 0
    total_deferred = 0
    total_deductions = 0
    
    # First pass: Calculate Basic (required for other calculations)
    for comp in component_config:
        if not comp.get("enabled", True):
            continue
        if comp["key"] == "basic":
            pct = comp.get("value", 40)
            basic_annual = round(annual_ctc * pct / 100, 2)
            basic_monthly = round(basic_annual / 12, 2)
            components["basic"] = {
                "key": "basic", "name": comp.get("name", "Basic Salary"), 
                "calc_type": "percentage_of_ctc", "value": pct,
                "annual": basic_annual, "monthly": basic_monthly, 
                "is_taxable": True, "is_earning": True, "enabled": True
            }
            gross_monthly += basic_monthly
            break
    
    # If no basic defined, default to 40%
    if basic_annual == 0:
        basic_annual = round(annual_ctc * 40 / 100, 2)
        basic_monthly = round(basic_annual / 12, 2)
        components["basic"] = {
            "key": "basic", "name": "Basic Salary", "calc_type": "percentage_of_ctc",
            "value": 40, "annual": basic_annual, "monthly": basic_monthly,
            "is_taxable": True, "is_earning": True, "enabled": True
        }
        gross_monthly += basic_monthly
    
    # Calculate gross for ESIC calculation (before deferred components)
    temp_gross = basic_annual
    
    # Second pass: Calculate all other components except balance
    for comp in component_config:
        if not comp.get("enabled", True) or comp["key"] == "basic" or comp.get("is_balance"):
            continue
        
        key = comp["key"]
        name = comp.get("name", key.replace("_", " ").title())
        calc_type = comp.get("calc_type", "fixed_monthly")
        value = comp.get("value", comp.get("default_value", 0))
        is_earning = comp.get("is_earning", True)
        is_deferred = comp.get("is_deferred", False)
        is_deduction = comp.get("is_deduction", False)
        
        annual = 0
        monthly = 0
        
        if calc_type == "percentage_of_ctc":
            annual = round(annual_ctc * value / 100, 2)
            monthly = round(annual / 12, 2)
        elif calc_type == "percentage_of_basic":
            annual = round(basic_annual * value / 100, 2)
            monthly = round(annual / 12, 2)
        elif calc_type == "percentage_of_gross":
            annual = round(temp_gross * value / 100, 2)
            monthly = round(annual / 12, 2)
        elif calc_type == "fixed_monthly":
            monthly = round(value, 2)
            annual = round(monthly * 12, 2)
        elif calc_type == "fixed_annual":
            annual = round(value, 2)
            monthly = 0
        
        components[key] = {
            "key": key, "name": name, "calc_type": calc_type, "value": value,
            "annual": annual, "monthly": monthly,
            "is_taxable": comp.get("is_taxable", True),
            "is_earning": is_earning, "is_deferred": is_deferred,
            "is_deduction": is_deduction, "enabled": True
        }
        
        if comp.get("vesting_months"):
            components[key]["vesting_months"] = comp["vesting_months"]
            components[key]["is_optional"] = True
        
        if is_earning and not is_deferred:
            gross_monthly += monthly
            temp_gross += annual
        elif is_deferred:
            total_deferred += annual
        elif is_deduction:
            total_deductions += monthly
    
    # Handle retention bonus separately if provided
    if retention_bonus > 0 and "retention_bonus" not in components:
        components["retention_bonus"] = {
            "key": "retention_bonus", "name": "Retention Bonus", "calc_type": "fixed_annual",
            "value": retention_bonus, "annual": retention_bonus, "monthly": 0,
            "is_taxable": True, "is_earning": True, "is_optional": True,
            "vesting_months": retention_vesting_months, "enabled": True,
            "note": f"Payable after {retention_vesting_months} months of service"
        }
        total_deferred += retention_bonus
    
    # Calculate Special Allowance as balance (if enabled)
    balance_comp = next((c for c in component_config if c.get("is_balance") and c.get("enabled", True)), None)
    if balance_comp or any(c.get("key") == "special_allowance" and c.get("enabled", True) for c in component_config):
        allocated = sum(c["annual"] for c in components.values())
        special_allowance_annual = round(annual_ctc - allocated, 2)
        if special_allowance_annual < 0:
            special_allowance_annual = 0
        special_allowance_monthly = round(special_allowance_annual / 12, 2)
        
        components["special_allowance"] = {
            "key": "special_allowance", "name": "Special Allowance", "calc_type": "balance",
            "value": 0, "annual": special_allowance_annual, "monthly": special_allowance_monthly,
            "is_taxable": True, "is_earning": True, "is_balance": True, "enabled": True
        }
        gross_monthly += special_allowance_monthly
    
    # Recalculate total deferred
    total_deferred = sum(c["annual"] for c in components.values() if c.get("is_deferred") or c.get("is_optional"))
    
    return {
        "components": components,
        "summary": {
            "annual_ctc": annual_ctc,
            "gross_monthly": round(gross_monthly, 2),
            "basic_annual": basic_annual,
            "total_deferred_annual": round(total_deferred, 2),
            "total_deductions_monthly": round(total_deductions, 2),
            "in_hand_approx_monthly": round(gross_monthly - total_deductions, 2)
        }
    }


@router.get("/component-master")
async def get_ctc_component_master_api(current_user: User = Depends(get_current_user)):
    """Get CTC component master configuration."""
    if current_user.role not in ["admin", "hr_manager", "hr_executive"]:
        raise HTTPException(status_code=403, detail="Only HR can access CTC components")
    
    components = await get_ctc_component_master()
    return {"components": components}


@router.post("/component-master")
async def update_ctc_component_master(data: dict, current_user: User = Depends(get_current_user)):
    """Update CTC component master configuration (Admin only)."""
    db = get_db()
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only Admin can update CTC component master")
    
    components = data.get("components", [])
    if not components:
        raise HTTPException(status_code=400, detail="Components list is required")
    
    await db.ctc_config.update_one(
        {"type": "component_master"},
        {"$set": {"type": "component_master", "components": components, "updated_at": datetime.now(timezone.utc).isoformat(), "updated_by": current_user.id}},
        upsert=True
    )
    return {"message": "CTC component master updated"}


@router.post("/calculate-preview")
async def preview_ctc_breakdown(data: dict, current_user: User = Depends(get_current_user)):
    """Preview CTC breakdown with configurable components."""
    if current_user.role not in ["admin", "hr_manager", "hr_executive"]:
        raise HTTPException(status_code=403, detail="Only HR can access CTC calculations")
    
    annual_ctc = data.get("annual_ctc", 0)
    if annual_ctc <= 0:
        raise HTTPException(status_code=400, detail="Annual CTC must be greater than 0")
    
    retention_bonus = data.get("retention_bonus", 0)
    retention_vesting_months = data.get("retention_vesting_months", 12)
    
    component_config = data.get("component_config")
    if component_config:
        breakdown = calculate_ctc_breakdown_dynamic(annual_ctc, component_config, retention_bonus, retention_vesting_months)
    else:
        master_components = await get_ctc_component_master()
        for comp in master_components:
            if "enabled" not in comp:
                comp["enabled"] = comp.get("enabled_by_default", True)
        breakdown = calculate_ctc_breakdown_dynamic(annual_ctc, master_components, retention_bonus, retention_vesting_months)
    
    return breakdown


@router.post("/design")
async def design_ctc_structure(request: CTCStructureRequest, current_user: User = Depends(get_current_user)):
    """HR designs/saves CTC structure for an employee - No admin approval required."""
    db = get_db()
    if current_user.role not in ["admin", "hr_manager", "hr_executive"]:
        raise HTTPException(status_code=403, detail="Only Admin/HR can design CTC structures")
    
    employee = await db.employees.find_one({"id": request.employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    if request.component_config:
        breakdown = calculate_ctc_breakdown_dynamic(
            request.annual_ctc, 
            request.component_config,
            request.retention_bonus or 0, 
            request.retention_vesting_months or 12
        )
    else:
        master_components = await get_ctc_component_master()
        for comp in master_components:
            if "enabled" not in comp:
                comp["enabled"] = comp.get("enabled_by_default", True)
        breakdown = calculate_ctc_breakdown_dynamic(
            request.annual_ctc, 
            master_components,
            request.retention_bonus or 0, 
            request.retention_vesting_months or 12
        )
    
    existing_pending = await db.ctc_structures.find_one({
        "employee_id": request.employee_id,
        "status": "pending"
    })
    if existing_pending:
        raise HTTPException(status_code=400, detail="There is already a pending CTC request for this employee.")
    
    latest = await db.ctc_structures.find_one(
        {"employee_id": request.employee_id},
        sort=[("version", -1)]
    )
    version = (latest.get("version", 0) + 1) if latest else 1
    
    ctc_structure = {
        "id": str(uuid.uuid4()),
        "employee_id": request.employee_id,
        "employee_name": f"{employee.get('first_name', '')} {employee.get('last_name', '')}",
        "employee_code": employee.get("employee_id", ""),
        "department": employee.get("department", ""),
        "designation": employee.get("designation", ""),
        "annual_ctc": request.annual_ctc,
        "effective_month": request.effective_month,
        "components": breakdown["components"],
        "component_config": request.component_config,
        "summary": breakdown["summary"],
        "retention_bonus": request.retention_bonus or 0,
        "retention_vesting_months": request.retention_vesting_months or 12,
        "status": "approved",  # Auto-approved - no admin approval needed
        "created_by": current_user.id,
        "created_by_name": current_user.full_name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "approved_at": datetime.now(timezone.utc).isoformat(),
        "approved_by": current_user.id,
        "approved_by_name": current_user.full_name,
        "remarks": request.remarks,
        "version": version,
        "previous_ctc": employee.get("salary", 0)
    }
    
    await db.ctc_structures.insert_one(ctc_structure)
    
    admins = await db.users.find({"role": "admin"}, {"_id": 0, "id": 1, "full_name": 1}).to_list(50)
    for admin in admins:
        notification = {
            "id": str(uuid.uuid4()),
            "user_id": admin["id"],
            "type": "ctc_approval_request",
            "title": "CTC Structure Approval Required",
            "message": f"{current_user.full_name} has submitted CTC structure for {employee.get('first_name')} {employee.get('last_name')} (₹{request.annual_ctc:,.0f}/year).",
            "reference_type": "ctc_structure",
            "reference_id": ctc_structure["id"],
            "is_read": False,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.notifications.insert_one(notification)
    
    return {
        "message": "CTC structure submitted for admin approval",
        "ctc_structure_id": ctc_structure["id"],
        "status": "pending"
    }


@router.get("/pending-approvals")
async def get_pending_ctc_approvals(current_user: User = Depends(get_current_user)):
    """Get all pending CTC structure approvals (Admin/HR Manager)."""
    db = get_db()
    if current_user.role not in ["admin", "hr_manager"]:
        raise HTTPException(status_code=403, detail="Only Admin/HR Manager can view pending CTC approvals")
    
    pending = await db.ctc_structures.find(
        {"status": "pending"},
        {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    
    return pending


@router.get("/all")
async def get_all_ctc_structures(
    status: Optional[str] = None,
    employee_id: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get all CTC structures with optional filters (Admin/HR)."""
    db = get_db()
    if current_user.role not in ["admin", "hr_manager"]:
        raise HTTPException(status_code=403, detail="Only Admin/HR Manager can view CTC structures")
    
    query = {}
    if status:
        query["status"] = status
    if employee_id:
        query["employee_id"] = employee_id
    
    structures = await db.ctc_structures.find(query, {"_id": 0}).sort("created_at", -1).to_list(500)
    return structures


@router.get("/employee/{employee_id}")
async def get_employee_ctc(employee_id: str, current_user: User = Depends(get_current_user)):
    """Get active CTC structure for an employee."""
    db = get_db()
    if current_user.role not in ["admin", "hr_manager", "hr_executive"]:
        if current_user.id != employee_id:
            raise HTTPException(status_code=403, detail="Access denied")
    
    active_ctc = await db.ctc_structures.find_one(
        {"employee_id": employee_id, "status": "active"},
        {"_id": 0}
    )
    
    pending_ctc = await db.ctc_structures.find_one(
        {"employee_id": employee_id, "status": "pending"},
        {"_id": 0}
    )
    
    return {"active": active_ctc, "pending": pending_ctc}


@router.get("/employee/{employee_id}/history")
async def get_employee_ctc_history(employee_id: str, current_user: User = Depends(get_current_user)):
    """Get CTC change history for an employee."""
    db = get_db()
    if current_user.role not in ["admin", "hr_manager"]:
        raise HTTPException(status_code=403, detail="Only Admin/HR Manager can view CTC history")
    
    history = await db.ctc_structures.find(
        {"employee_id": employee_id},
        {"_id": 0}
    ).sort("version", -1).to_list(50)
    
    return history


@router.post("/{ctc_id}/approve")
async def approve_ctc_structure(ctc_id: str, data: dict, current_user: User = Depends(get_current_user)):
    """Admin approves CTC structure - makes it active from effective month."""
    db = get_db()
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only Admin can approve CTC structures")
    
    ctc_structure = await db.ctc_structures.find_one({"id": ctc_id}, {"_id": 0})
    if not ctc_structure:
        raise HTTPException(status_code=404, detail="CTC structure not found")
    
    if ctc_structure["status"] != "pending":
        raise HTTPException(status_code=400, detail=f"CTC structure is already {ctc_structure['status']}")
    
    await db.ctc_structures.update_many(
        {"employee_id": ctc_structure["employee_id"], "status": "active"},
        {"$set": {"status": "superseded", "superseded_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    await db.ctc_structures.update_one(
        {"id": ctc_id},
        {"$set": {
            "status": "active",
            "approved_by": current_user.id,
            "approved_by_name": current_user.full_name,
            "approved_at": datetime.now(timezone.utc).isoformat(),
            "admin_remarks": data.get("remarks", "")
        }}
    )
    
    gross_monthly = ctc_structure["summary"]["gross_monthly"]
    await db.employees.update_one(
        {"id": ctc_structure["employee_id"]},
        {"$set": {
            "salary": gross_monthly,
            "annual_ctc": ctc_structure["annual_ctc"],
            "ctc_effective_from": ctc_structure["effective_month"],
            "ctc_structure_id": ctc_id
        }}
    )
    
    notification = {
        "id": str(uuid.uuid4()),
        "user_id": ctc_structure["created_by"],
        "type": "ctc_approved",
        "title": "CTC Structure Approved",
        "message": f"CTC structure for {ctc_structure['employee_name']} has been approved.",
        "reference_type": "ctc_structure",
        "reference_id": ctc_id,
        "is_read": False,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.notifications.insert_one(notification)
    
    return {"message": "CTC structure approved and activated", "effective_from": ctc_structure["effective_month"]}


@router.post("/{ctc_id}/reject")
async def reject_ctc_structure(ctc_id: str, data: dict, current_user: User = Depends(get_current_user)):
    """Admin rejects CTC structure."""
    db = get_db()
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only Admin can reject CTC structures")
    
    ctc_structure = await db.ctc_structures.find_one({"id": ctc_id}, {"_id": 0})
    if not ctc_structure:
        raise HTTPException(status_code=404, detail="CTC structure not found")
    
    if ctc_structure["status"] != "pending":
        raise HTTPException(status_code=400, detail=f"CTC structure is already {ctc_structure['status']}")
    
    rejection_reason = data.get("reason", "")
    if not rejection_reason:
        raise HTTPException(status_code=400, detail="Rejection reason is required")
    
    await db.ctc_structures.update_one(
        {"id": ctc_id},
        {"$set": {
            "status": "rejected",
            "approved_by": current_user.id,
            "approved_by_name": current_user.full_name,
            "approved_at": datetime.now(timezone.utc).isoformat(),
            "rejection_reason": rejection_reason
        }}
    )
    
    notification = {
        "id": str(uuid.uuid4()),
        "user_id": ctc_structure["created_by"],
        "type": "ctc_rejected",
        "title": "CTC Structure Rejected",
        "message": f"CTC structure for {ctc_structure['employee_name']} has been rejected. Reason: {rejection_reason}",
        "reference_type": "ctc_structure",
        "reference_id": ctc_id,
        "is_read": False,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.notifications.insert_one(notification)
    
    return {"message": "CTC structure rejected", "reason": rejection_reason}


@router.delete("/{ctc_id}/cancel")
async def cancel_ctc_request(ctc_id: str, current_user: User = Depends(get_current_user)):
    """HR cancels their own pending CTC request."""
    db = get_db()
    if current_user.role not in ["admin", "hr_manager"]:
        raise HTTPException(status_code=403, detail="Only Admin/HR Manager can cancel CTC requests")
    
    ctc_structure = await db.ctc_structures.find_one({"id": ctc_id}, {"_id": 0})
    if not ctc_structure:
        raise HTTPException(status_code=404, detail="CTC structure not found")
    
    if ctc_structure["status"] != "pending":
        raise HTTPException(status_code=400, detail="Can only cancel pending requests")
    
    if current_user.role != "admin" and ctc_structure["created_by"] != current_user.id:
        raise HTTPException(status_code=403, detail="You can only cancel your own requests")
    
    await db.ctc_structures.update_one(
        {"id": ctc_id},
        {"$set": {
            "status": "cancelled",
            "cancelled_by": current_user.id,
            "cancelled_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    return {"message": "CTC request cancelled"}


@router.get("/stats")
async def get_ctc_stats(current_user: User = Depends(get_current_user)):
    """Get CTC approval statistics (Admin/HR Manager)."""
    db = get_db()
    if current_user.role not in ["admin", "hr_manager"]:
        raise HTTPException(status_code=403, detail="Only Admin/HR Manager can view CTC stats")
    
    pending_count = await db.ctc_structures.count_documents({"status": "pending"})
    approved_count = await db.ctc_structures.count_documents({"status": "approved"})
    rejected_count = await db.ctc_structures.count_documents({"status": "rejected"})
    active_count = await db.ctc_structures.count_documents({"status": "active"})
    
    return {
        "pending": pending_count,
        "approved": approved_count,
        "rejected": rejected_count,
        "active": active_count
    }
