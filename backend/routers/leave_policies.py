"""
Leave Policies Router - Comprehensive leave policy management with hierarchy
Supports: Company-wide, Department-wise, Role-wise, Employee-wise policies
Integrated with Payroll for LOP deductions and leave encashment
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Optional, List
from datetime import datetime, timezone, date
from dateutil.relativedelta import relativedelta
import uuid
from pydantic import BaseModel
from .deps import get_db, HR_ADMIN_ROLES, HR_ROLES, ADMIN_ROLES
from .models import User
from .auth import get_current_user

router = APIRouter(prefix="/leave-policies", tags=["Leave Policies"])


# ==================== MODELS ====================

class LeaveTypeConfig(BaseModel):
    """Configuration for a single leave type"""
    leave_type: str  # casual_leave, sick_leave, earned_leave, maternity_leave, paternity_leave, etc.
    annual_quota: float  # Total days per year
    accrual_type: str  # 'yearly' (credited at year start) or 'monthly' (accrued per month)
    accrual_rate: Optional[float] = None  # Days per month if monthly accrual
    carry_forward: bool = False  # Can unused leave be carried forward
    max_carry_forward: Optional[float] = None  # Max days that can be carried forward
    encashment_allowed: bool = False  # Can be encashed in payroll
    encashment_max_days: Optional[float] = None  # Max days that can be encashed
    min_service_months: int = 0  # Minimum months of service required
    pro_rata_for_new_joiners: bool = True  # Calculate proportionally for new joiners
    can_be_negative: bool = False  # Allow negative balance (converts to LOP)
    lop_deduction_per_day: Optional[float] = None  # Salary deduction per day if LOP
    requires_medical_certificate: bool = False  # For sick leave > X days
    medical_certificate_threshold: int = 2  # Days after which certificate required
    max_consecutive_days: Optional[int] = None  # Max consecutive days allowed
    advance_notice_days: int = 0  # Days notice required before applying
    description: str = ""


class LeavePolicyCreate(BaseModel):
    """Create/Update a leave policy"""
    name: str
    description: Optional[str] = ""
    scope: str  # 'company', 'department', 'role', 'employee'
    scope_value: Optional[str] = None  # Department ID, Role name, or Employee ID
    leave_types: List[dict]  # List of LeaveTypeConfig as dicts
    effective_from: date
    effective_to: Optional[date] = None
    is_active: bool = True
    payroll_integration: dict = {}  # Payroll linkage settings


# ==================== DEFAULT POLICY ====================

DEFAULT_LEAVE_POLICY = {
    "name": "Standard Leave Policy",
    "description": "Default company-wide leave policy",
    "scope": "company",
    "scope_value": None,
    "leave_types": [
        {
            "leave_type": "casual_leave",
            "annual_quota": 12,
            "accrual_type": "yearly",
            "carry_forward": False,
            "encashment_allowed": False,
            "min_service_months": 0,
            "pro_rata_for_new_joiners": True,
            "can_be_negative": False,
            "advance_notice_days": 1,
            "description": "For personal/urgent matters"
        },
        {
            "leave_type": "sick_leave",
            "annual_quota": 6,
            "accrual_type": "yearly",
            "carry_forward": False,
            "encashment_allowed": False,
            "min_service_months": 0,
            "pro_rata_for_new_joiners": False,
            "can_be_negative": True,
            "requires_medical_certificate": True,
            "medical_certificate_threshold": 2,
            "description": "For health-related absence"
        },
        {
            "leave_type": "earned_leave",
            "annual_quota": 15,
            "accrual_type": "monthly",
            "accrual_rate": 1.25,
            "carry_forward": True,
            "max_carry_forward": 30,
            "encashment_allowed": True,
            "encashment_max_days": 15,
            "min_service_months": 12,
            "pro_rata_for_new_joiners": True,
            "can_be_negative": False,
            "advance_notice_days": 7,
            "description": "Accrued based on service, can be encashed"
        },
        {
            "leave_type": "maternity_leave",
            "annual_quota": 182,
            "accrual_type": "yearly",
            "carry_forward": False,
            "encashment_allowed": False,
            "min_service_months": 0,
            "pro_rata_for_new_joiners": False,
            "can_be_negative": False,
            "description": "As per Maternity Benefit Act"
        },
        {
            "leave_type": "paternity_leave",
            "annual_quota": 15,
            "accrual_type": "yearly",
            "carry_forward": False,
            "encashment_allowed": False,
            "min_service_months": 0,
            "pro_rata_for_new_joiners": False,
            "can_be_negative": False,
            "description": "For new fathers"
        }
    ],
    "payroll_integration": {
        "lop_deduction_formula": "basic_per_day",  # basic_per_day, gross_per_day, fixed
        "lop_fixed_amount": None,
        "encashment_formula": "basic_per_day",
        "include_in_full_final": True,
        "auto_adjust_salary": True
    }
}


# ==================== POLICY CRUD ====================

@router.get("")
async def get_leave_policies(
    scope: Optional[str] = None,
    is_active: Optional[bool] = True,
    current_user: User = Depends(get_current_user)
):
    """Get all leave policies. HR/Admin only."""
    if current_user.role not in HR_ADMIN_ROLES + HR_ROLES:
        raise HTTPException(status_code=403, detail="Access denied. HR role required.")
    
    db = get_db()
    query = {}
    if scope:
        query["scope"] = scope
    if is_active is not None:
        query["is_active"] = is_active
    
    policies = await db.leave_policies.find(query, {"_id": 0}).sort("created_at", -1).to_list(100)
    
    # If no policies exist, create default
    if not policies:
        default = {**DEFAULT_LEAVE_POLICY}
        default["id"] = str(uuid.uuid4())
        default["created_at"] = datetime.now(timezone.utc).isoformat()
        default["created_by"] = current_user.id
        default["effective_from"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        default["is_active"] = True
        await db.leave_policies.insert_one(default)
        policies = [default]
    
    return policies


@router.get("/effective/{employee_id}")
async def get_effective_policy_for_employee(
    employee_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get the effective leave policy for a specific employee (cascaded)"""
    db = get_db()
    
    # Get employee details
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Policy precedence: Employee > Role > Department > Company
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    # 1. Check employee-specific policy
    emp_policy = await db.leave_policies.find_one({
        "scope": "employee",
        "scope_value": employee_id,
        "is_active": True,
        "effective_from": {"$lte": today}
    }, {"_id": 0})
    if emp_policy:
        return {"policy": emp_policy, "applied_level": "employee"}
    
    # 2. Check role-specific policy
    emp_role = employee.get("designation") or employee.get("role")
    if emp_role:
        role_policy = await db.leave_policies.find_one({
            "scope": "role",
            "scope_value": emp_role,
            "is_active": True,
            "effective_from": {"$lte": today}
        }, {"_id": 0})
        if role_policy:
            return {"policy": role_policy, "applied_level": "role"}
    
    # 3. Check department-specific policy
    emp_dept = employee.get("department")
    if emp_dept:
        dept_policy = await db.leave_policies.find_one({
            "scope": "department",
            "scope_value": emp_dept,
            "is_active": True,
            "effective_from": {"$lte": today}
        }, {"_id": 0})
        if dept_policy:
            return {"policy": dept_policy, "applied_level": "department"}
    
    # 4. Fall back to company-wide policy
    company_policy = await db.leave_policies.find_one({
        "scope": "company",
        "is_active": True,
        "effective_from": {"$lte": today}
    }, {"_id": 0})
    
    if company_policy:
        return {"policy": company_policy, "applied_level": "company"}
    
    # Return default if nothing exists
    return {"policy": DEFAULT_LEAVE_POLICY, "applied_level": "default"}


@router.post("")
async def create_leave_policy(
    policy_data: LeavePolicyCreate,
    current_user: User = Depends(get_current_user)
):
    """Create a new leave policy. HR Admin only."""
    if current_user.role not in HR_ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Only HR Admin can create policies")
    
    db = get_db()
    
    policy = policy_data.dict()
    policy["id"] = str(uuid.uuid4())
    policy["created_at"] = datetime.now(timezone.utc).isoformat()
    policy["updated_at"] = datetime.now(timezone.utc).isoformat()
    policy["created_by"] = current_user.id
    policy["effective_from"] = policy["effective_from"].isoformat() if isinstance(policy["effective_from"], date) else policy["effective_from"]
    if policy.get("effective_to"):
        policy["effective_to"] = policy["effective_to"].isoformat() if isinstance(policy["effective_to"], date) else policy["effective_to"]
    
    await db.leave_policies.insert_one(policy)
    
    # Log audit
    await db.audit_logs.insert_one({
        "id": str(uuid.uuid4()),
        "action": "leave_policy_created",
        "entity_type": "leave_policy",
        "entity_id": policy["id"],
        "user_id": current_user.id,
        "details": {"name": policy["name"], "scope": policy["scope"]},
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    return {"message": "Leave policy created", "id": policy["id"]}


@router.put("/{policy_id}")
async def update_leave_policy(
    policy_id: str,
    policy_data: dict,
    current_user: User = Depends(get_current_user)
):
    """Update an existing leave policy"""
    if current_user.role not in HR_ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Only HR Admin can update policies")
    
    db = get_db()
    
    existing = await db.leave_policies.find_one({"id": policy_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Policy not found")
    
    policy_data["updated_at"] = datetime.now(timezone.utc).isoformat()
    policy_data["updated_by"] = current_user.id
    
    # Handle date conversion
    if "effective_from" in policy_data and policy_data["effective_from"]:
        if isinstance(policy_data["effective_from"], date):
            policy_data["effective_from"] = policy_data["effective_from"].isoformat()
    if "effective_to" in policy_data and policy_data["effective_to"]:
        if isinstance(policy_data["effective_to"], date):
            policy_data["effective_to"] = policy_data["effective_to"].isoformat()
    
    await db.leave_policies.update_one({"id": policy_id}, {"$set": policy_data})
    
    return {"message": "Leave policy updated"}


@router.delete("/{policy_id}")
async def delete_leave_policy(
    policy_id: str,
    current_user: User = Depends(get_current_user)
):
    """Soft delete a leave policy"""
    if current_user.role not in HR_ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Only HR Admin can delete policies")
    
    db = get_db()
    await db.leave_policies.update_one(
        {"id": policy_id},
        {"$set": {"is_active": False, "deleted_at": datetime.now(timezone.utc).isoformat()}}
    )
    return {"message": "Leave policy deleted"}


# ==================== LEAVE BALANCE CALCULATION ====================

@router.get("/calculate-balance/{employee_id}")
async def calculate_leave_balance(
    employee_id: str,
    as_of_date: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """
    Calculate comprehensive leave balance for an employee based on:
    - Applicable policy (cascaded)
    - Service tenure
    - Accrual rules
    - Used leaves
    - Carry forward from previous year
    """
    db = get_db()
    
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Get effective policy
    policy_result = await get_effective_policy_for_employee(employee_id, current_user)
    policy = policy_result["policy"]
    
    # Calculate service months
    join_date_str = employee.get("date_of_joining") or employee.get("joining_date")
    if join_date_str:
        try:
            join_date = datetime.strptime(join_date_str[:10], "%Y-%m-%d")
        except:
            join_date = datetime.now(timezone.utc) - relativedelta(months=12)
    else:
        join_date = datetime.now(timezone.utc) - relativedelta(months=12)
    
    calc_date = datetime.strptime(as_of_date, "%Y-%m-%d") if as_of_date else datetime.now(timezone.utc)
    service_months = relativedelta(calc_date, join_date).months + (relativedelta(calc_date, join_date).years * 12)
    
    # Current year
    current_year = calc_date.year
    year_start = datetime(current_year, 1, 1)
    months_in_year = calc_date.month
    
    # Get leave usage this year
    year_start_str = year_start.strftime("%Y-%m-%d")
    used_leaves = await db.leave_requests.find({
        "employee_id": employee_id,
        "status": "approved",
        "start_date": {"$gte": year_start_str}
    }, {"_id": 0}).to_list(500)
    
    # Calculate usage by type
    usage_by_type = {}
    for leave in used_leaves:
        lt = leave.get("leave_type", "casual_leave")
        usage_by_type[lt] = usage_by_type.get(lt, 0) + leave.get("days", 0)
    
    # Get carry forward from previous year
    prev_year_balance = await db.leave_balance_snapshots.find_one({
        "employee_id": employee_id,
        "year": current_year - 1
    }, {"_id": 0})
    
    # Calculate balance for each leave type
    balance = {}
    payroll_impact = {
        "lop_days": 0,
        "encashable_days": 0,
        "lop_deduction": 0,
        "encashment_amount": 0
    }
    
    for lt_config in policy.get("leave_types", []):
        lt = lt_config.get("leave_type")
        annual_quota = lt_config.get("annual_quota", 0)
        accrual_type = lt_config.get("accrual_type", "yearly")
        min_service = lt_config.get("min_service_months", 0)
        pro_rata = lt_config.get("pro_rata_for_new_joiners", True)
        carry_forward = lt_config.get("carry_forward", False)
        max_carry = lt_config.get("max_carry_forward", 0)
        can_be_negative = lt_config.get("can_be_negative", False)
        encashment_allowed = lt_config.get("encashment_allowed", False)
        encashment_max = lt_config.get("encashment_max_days", 0)
        
        # Check minimum service requirement
        if service_months < min_service:
            entitled = 0
        elif accrual_type == "monthly":
            accrual_rate = lt_config.get("accrual_rate", annual_quota / 12)
            if pro_rata and join_date.year == current_year:
                # Pro-rata for current year joiners
                months_worked = months_in_year - (join_date.month - 1) if join_date.month <= months_in_year else 0
                entitled = round(accrual_rate * months_worked, 2)
            else:
                entitled = round(accrual_rate * months_in_year, 2)
        else:
            # Yearly accrual
            if pro_rata and join_date.year == current_year:
                # Pro-rata for current year joiners
                remaining_months = 12 - join_date.month + 1
                entitled = round(annual_quota * remaining_months / 12, 2)
            else:
                entitled = annual_quota
        
        # Add carry forward
        carried = 0
        if carry_forward and prev_year_balance:
            prev_available = prev_year_balance.get("balances", {}).get(lt, {}).get("available", 0)
            carried = min(prev_available, max_carry) if max_carry else prev_available
        
        total_entitled = entitled + carried
        used = usage_by_type.get(lt, 0)
        available = total_entitled - used
        
        # Handle negative balance (LOP)
        lop_days = 0
        if available < 0:
            if can_be_negative:
                lop_days = abs(available)
                payroll_impact["lop_days"] += lop_days
            else:
                available = 0
        
        # Calculate encashable days
        encashable = 0
        if encashment_allowed and available > 0:
            encashable = min(available, encashment_max) if encashment_max else available
            payroll_impact["encashable_days"] += encashable
        
        balance[lt] = {
            "annual_quota": annual_quota,
            "entitled_ytd": entitled,
            "carried_forward": carried,
            "total_entitled": total_entitled,
            "used": used,
            "available": max(available, 0) if not can_be_negative else available,
            "lop_days": lop_days,
            "encashable": encashable,
            "min_service_required": min_service,
            "service_months": service_months,
            "eligible": service_months >= min_service
        }
    
    return {
        "employee_id": employee_id,
        "employee_name": f"{employee.get('first_name', '')} {employee.get('last_name', '')}".strip(),
        "policy_name": policy.get("name"),
        "policy_level": policy_result["applied_level"],
        "service_months": service_months,
        "join_date": join_date_str,
        "as_of_date": calc_date.strftime("%Y-%m-%d"),
        "balance": balance,
        "payroll_impact": payroll_impact
    }


# ==================== BULK OPERATIONS ====================

@router.post("/apply-to-department/{department}")
async def apply_policy_to_department(
    department: str,
    policy_id: str,
    current_user: User = Depends(get_current_user)
):
    """Apply a policy to all employees in a department"""
    if current_user.role not in HR_ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Only HR Admin can apply policies")
    
    db = get_db()
    
    policy = await db.leave_policies.find_one({"id": policy_id}, {"_id": 0})
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    
    # Create department-level policy
    dept_policy = {**policy}
    dept_policy["id"] = str(uuid.uuid4())
    dept_policy["scope"] = "department"
    dept_policy["scope_value"] = department
    dept_policy["created_at"] = datetime.now(timezone.utc).isoformat()
    dept_policy["created_by"] = current_user.id
    dept_policy["source_policy_id"] = policy_id
    
    await db.leave_policies.insert_one(dept_policy)
    
    return {"message": f"Policy applied to department: {department}", "new_policy_id": dept_policy["id"]}


@router.post("/apply-to-role/{role}")
async def apply_policy_to_role(
    role: str,
    policy_id: str,
    current_user: User = Depends(get_current_user)
):
    """Apply a policy to all employees with a specific role"""
    if current_user.role not in HR_ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Only HR Admin can apply policies")
    
    db = get_db()
    
    policy = await db.leave_policies.find_one({"id": policy_id}, {"_id": 0})
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    
    # Create role-level policy
    role_policy = {**policy}
    role_policy["id"] = str(uuid.uuid4())
    role_policy["scope"] = "role"
    role_policy["scope_value"] = role
    role_policy["created_at"] = datetime.now(timezone.utc).isoformat()
    role_policy["created_by"] = current_user.id
    role_policy["source_policy_id"] = policy_id
    
    await db.leave_policies.insert_one(role_policy)
    
    return {"message": f"Policy applied to role: {role}", "new_policy_id": role_policy["id"]}


@router.post("/apply-to-employee/{employee_id}")
async def apply_policy_to_employee(
    employee_id: str,
    policy_id: str,
    current_user: User = Depends(get_current_user)
):
    """Apply a custom policy to a specific employee"""
    if current_user.role not in HR_ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Only HR Admin can apply policies")
    
    db = get_db()
    
    policy = await db.leave_policies.find_one({"id": policy_id}, {"_id": 0})
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Create employee-level policy
    emp_policy = {**policy}
    emp_policy["id"] = str(uuid.uuid4())
    emp_policy["scope"] = "employee"
    emp_policy["scope_value"] = employee_id
    emp_policy["name"] = f"{policy['name']} - {employee.get('first_name', '')} {employee.get('last_name', '')}"
    emp_policy["created_at"] = datetime.now(timezone.utc).isoformat()
    emp_policy["created_by"] = current_user.id
    emp_policy["source_policy_id"] = policy_id
    
    await db.leave_policies.insert_one(emp_policy)
    
    return {"message": f"Policy applied to employee", "new_policy_id": emp_policy["id"]}


# ==================== PAYROLL INTEGRATION ====================

@router.get("/payroll-adjustments/{employee_id}/{month}/{year}")
async def get_payroll_adjustments(
    employee_id: str,
    month: int,
    year: int,
    current_user: User = Depends(get_current_user)
):
    """
    Get leave-related payroll adjustments for an employee's salary
    Returns LOP deductions and leave encashment amounts
    """
    if current_user.role not in HR_ADMIN_ROLES + HR_ROLES:
        raise HTTPException(status_code=403, detail="HR role required")
    
    db = get_db()
    
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Get CTC/salary info
    ctc = employee.get("ctc", 0)
    monthly_gross = ctc / 12 if ctc else employee.get("monthly_salary", 0)
    basic = monthly_gross * 0.4  # Assuming 40% basic
    per_day_basic = basic / 30
    per_day_gross = monthly_gross / 30
    
    # Get effective policy
    policy_result = await get_effective_policy_for_employee(employee_id, current_user)
    policy = policy_result["policy"]
    payroll_config = policy.get("payroll_integration", {})
    
    # Get LOP leaves for the month
    month_start = f"{year}-{month:02d}-01"
    if month == 12:
        month_end = f"{year + 1}-01-01"
    else:
        month_end = f"{year}-{month + 1:02d}-01"
    
    lop_leaves = await db.leave_requests.find({
        "employee_id": employee_id,
        "status": "approved",
        "leave_type": {"$in": ["loss_of_pay", "lop"]},
        "start_date": {"$gte": month_start, "$lt": month_end}
    }, {"_id": 0}).to_list(100)
    
    total_lop_days = sum(l.get("days", 0) for l in lop_leaves)
    
    # Calculate LOP deduction
    lop_formula = payroll_config.get("lop_deduction_formula", "basic_per_day")
    if lop_formula == "basic_per_day":
        lop_deduction = round(total_lop_days * per_day_basic, 2)
    elif lop_formula == "gross_per_day":
        lop_deduction = round(total_lop_days * per_day_gross, 2)
    else:
        lop_deduction = round(total_lop_days * payroll_config.get("lop_fixed_amount", per_day_basic), 2)
    
    # Get leave encashment requests for the month
    encashments = await db.leave_encashments.find({
        "employee_id": employee_id,
        "status": "approved",
        "month": month,
        "year": year
    }, {"_id": 0}).to_list(10)
    
    total_encash_days = sum(e.get("days", 0) for e in encashments)
    
    # Calculate encashment amount
    encash_formula = payroll_config.get("encashment_formula", "basic_per_day")
    if encash_formula == "basic_per_day":
        encashment_amount = round(total_encash_days * per_day_basic, 2)
    else:
        encashment_amount = round(total_encash_days * per_day_gross, 2)
    
    return {
        "employee_id": employee_id,
        "month": month,
        "year": year,
        "monthly_gross": monthly_gross,
        "per_day_basic": round(per_day_basic, 2),
        "per_day_gross": round(per_day_gross, 2),
        "lop_days": total_lop_days,
        "lop_deduction": lop_deduction,
        "encashment_days": total_encash_days,
        "encashment_amount": encashment_amount,
        "net_adjustment": encashment_amount - lop_deduction,
        "policy_applied": policy.get("name")
    }


@router.post("/encashment-request")
async def create_encashment_request(
    data: dict,
    current_user: User = Depends(get_current_user)
):
    """Create a leave encashment request"""
    db = get_db()
    
    employee = await db.employees.find_one(
        {"$or": [{"user_id": current_user.id}, {"official_email": current_user.email}]},
        {"_id": 0}
    )
    if not employee:
        raise HTTPException(status_code=400, detail="Employee record not found")
    
    # Validate encashable balance
    balance_result = await calculate_leave_balance(employee["id"], None, current_user)
    leave_type = data.get("leave_type", "earned_leave")
    balance_info = balance_result["balance"].get(leave_type, {})
    
    if not balance_info.get("encashable", 0):
        raise HTTPException(status_code=400, detail="No encashable leave available")
    
    days = data.get("days", 0)
    if days > balance_info["encashable"]:
        raise HTTPException(status_code=400, detail=f"Maximum encashable days: {balance_info['encashable']}")
    
    encashment = {
        "id": str(uuid.uuid4()),
        "employee_id": employee["id"],
        "user_id": current_user.id,
        "leave_type": leave_type,
        "days": days,
        "month": datetime.now(timezone.utc).month,
        "year": datetime.now(timezone.utc).year,
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.leave_encashments.insert_one(encashment)
    
    return {"message": "Leave encashment request submitted", "id": encashment["id"]}


# ==================== YEAR-END PROCESSING ====================

@router.post("/year-end-processing/{year}")
async def process_year_end(
    year: int,
    current_user: User = Depends(get_current_user)
):
    """
    Year-end leave balance processing:
    - Snapshot current balances
    - Calculate carry forward
    - Reset annual quotas
    - Trigger pending encashments
    """
    if current_user.role not in HR_ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Only HR Admin can run year-end processing")
    
    db = get_db()
    
    # Get all active employees
    employees = await db.employees.find({"status": {"$ne": "terminated"}}, {"_id": 0}).to_list(1000)
    
    processed = []
    for emp in employees:
        try:
            balance_result = await calculate_leave_balance(emp["id"], f"{year}-12-31", current_user)
            
            # Create snapshot
            snapshot = {
                "id": str(uuid.uuid4()),
                "employee_id": emp["id"],
                "year": year,
                "balances": balance_result["balance"],
                "payroll_impact": balance_result["payroll_impact"],
                "policy_applied": balance_result["policy_name"],
                "processed_at": datetime.now(timezone.utc).isoformat(),
                "processed_by": current_user.id
            }
            
            await db.leave_balance_snapshots.update_one(
                {"employee_id": emp["id"], "year": year},
                {"$set": snapshot},
                upsert=True
            )
            
            processed.append({
                "employee_id": emp["id"],
                "name": f"{emp.get('first_name', '')} {emp.get('last_name', '')}",
                "status": "success"
            })
        except Exception as e:
            processed.append({
                "employee_id": emp["id"],
                "status": "error",
                "error": str(e)
            })
    
    return {
        "message": f"Year-end processing completed for {year}",
        "total_employees": len(employees),
        "processed": len([p for p in processed if p["status"] == "success"]),
        "errors": len([p for p in processed if p["status"] == "error"]),
        "details": processed
    }
