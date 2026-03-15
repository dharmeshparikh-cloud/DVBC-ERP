"""
Payroll Router - Salary components, payroll inputs, salary slips, reports
Extracted from server.py for better modularity and load performance.
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Optional, List
from datetime import datetime, timezone, timedelta
import uuid
import calendar
from .deps import get_db, HR_ADMIN_ROLES, HR_ROLES, DEFAULT_PAGE_SIZE, LARGE_QUERY_SIZE
from .models import User
from .deps import get_current_user

router = APIRouter(prefix="/payroll", tags=["Payroll"])


@router.get("/salary-components")
async def get_salary_components(current_user: User = Depends(get_current_user)):
    """Get salary component configuration. HR and Admin only."""
    # Role guard - sensitive payroll data
    if current_user.role not in HR_ADMIN_ROLES + HR_ROLES:
        raise HTTPException(
            status_code=403,
            detail="Access denied. HR or Admin role required."
        )
    
    db = get_db()
    config = await db.payroll_config.find_one({"type": "salary_components"}, {"_id": 0})
    if not config:
        default = {
            "type": "salary_components",
            "earnings": [
                {"name": "Basic Salary", "key": "basic", "percentage": 40, "is_default": True},
                {"name": "HRA", "key": "hra", "percentage": 20, "is_default": True},
                {"name": "Special Allowance", "key": "special_allowance", "percentage": 20, "is_default": True},
                {"name": "Conveyance Allowance", "key": "conveyance", "fixed": 1600, "is_default": True},
                {"name": "Medical Allowance", "key": "medical", "fixed": 1250, "is_default": True}
            ],
            "deductions": [
                {"name": "Provident Fund", "key": "pf", "percentage": 12, "is_default": True},
                {"name": "Professional Tax", "key": "pt", "fixed": 200, "is_default": True},
                {"name": "ESI", "key": "esi", "percentage": 0.75, "is_default": True}
            ]
        }
        await db.payroll_config.insert_one(default)
        return default
    return config


@router.post("/salary-components")
async def update_salary_components(data: dict, current_user: User = Depends(get_current_user)):
    """Update salary components (Admin/HR only)"""
    if current_user.role not in HR_ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Only Admin/HR Manager can update salary components")
    db = get_db()
    await db.payroll_config.update_one({"type": "salary_components"}, {"$set": data}, upsert=True)
    return {"message": "Salary components updated"}


@router.post("/salary-components/add")
async def add_salary_component(data: dict, current_user: User = Depends(get_current_user)):
    """Add a new salary component (Admin/HR only)"""
    if current_user.role not in HR_ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Only Admin/HR Manager can modify salary components")
    db = get_db()
    comp_type = data.get("type")
    if comp_type not in ["earnings", "deductions"]:
        raise HTTPException(status_code=400, detail="type must be 'earnings' or 'deductions'")
    name = data.get("name", "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Component name is required")
    key = data.get("key", name.lower().replace(" ", "_"))
    component = {"name": name, "key": key, "is_default": False}
    if data.get("percentage"):
        component["percentage"] = float(data["percentage"])
    elif data.get("fixed") is not None:
        component["fixed"] = float(data["fixed"])
    else:
        raise HTTPException(status_code=400, detail="Either percentage or fixed amount required")
    config = await db.payroll_config.find_one({"type": "salary_components"}, {"_id": 0})
    if not config:
        raise HTTPException(status_code=400, detail="Salary components not initialized")
    existing_keys = [c["key"] for c in config.get(comp_type, [])]
    if key in existing_keys:
        raise HTTPException(status_code=400, detail=f"Component with key '{key}' already exists")
    config[comp_type].append(component)
    await db.payroll_config.update_one({"type": "salary_components"}, {"$set": {comp_type: config[comp_type]}})
    return {"message": f"{name} added to {comp_type}"}


@router.delete("/salary-components/{comp_type}/{comp_key}")
async def remove_salary_component(comp_type: str, comp_key: str, current_user: User = Depends(get_current_user)):
    """Remove a salary component (Admin/HR only). Cannot remove default components."""
    if current_user.role not in HR_ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Only Admin/HR Manager can modify salary components")
    db = get_db()
    if comp_type not in ["earnings", "deductions"]:
        raise HTTPException(status_code=400, detail="type must be 'earnings' or 'deductions'")
    config = await db.payroll_config.find_one({"type": "salary_components"}, {"_id": 0})
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")
    updated = [c for c in config.get(comp_type, []) if c["key"] != comp_key]
    if len(updated) == len(config.get(comp_type, [])):
        raise HTTPException(status_code=404, detail="Component not found")
    await db.payroll_config.update_one({"type": "salary_components"}, {"$set": {comp_type: updated}})
    return {"message": f"Component removed from {comp_type}"}


@router.get("/inputs")
async def get_payroll_inputs(month: str, current_user: User = Depends(get_current_user)):
    """Get payroll input data for a month (Admin/HR only)"""
    if current_user.role not in HR_ROLES:
        raise HTTPException(status_code=403, detail="Only HR can access payroll inputs")
    db = get_db()
    inputs = await db.payroll_inputs.find({"month": month}, {"_id": 0}).to_list(LARGE_QUERY_SIZE)
    input_map = {i["employee_id"]: i for i in inputs}
    employees = await db.employees.find(
        {"$or": [{"is_active": True}, {"is_active": {"$exists": False}}]},
        {"_id": 0, "id": 1, "employee_id": 1, "first_name": 1, "last_name": 1, "department": 1, "salary": 1}
    ).to_list(500)
    result = []
    for emp in employees:
        existing = input_map.get(emp["id"], {})
        result.append({
            "employee_id": emp["id"],
            "emp_code": emp.get("employee_id", ""),
            "name": f"{emp['first_name']} {emp['last_name']}",
            "department": emp.get("department", ""),
            "salary": emp.get("salary", 0),
            "month": month,
            "present_days": existing.get("present_days", 0),
            "absent_days": existing.get("absent_days", 0),
            "public_holidays": existing.get("public_holidays", 0),
            "leaves": existing.get("leaves", 0),
            "working_days": existing.get("working_days", 30),
            "incentive": existing.get("incentive", 0),
            "incentive_reason": existing.get("incentive_reason", ""),
            "expense_reimbursement": existing.get("expense_reimbursement", 0),
            "expense_ids": existing.get("expense_ids", []),
            "advance": existing.get("advance", 0),
            "advance_reason": existing.get("advance_reason", ""),
            "penalty": existing.get("penalty", 0),
            "penalty_reason": existing.get("penalty_reason", ""),
            "overtime_hours": existing.get("overtime_hours", 0),
            "remarks": existing.get("remarks", ""),
        })
    return result


@router.post("/inputs")
async def save_payroll_input(data: dict, current_user: User = Depends(get_current_user)):
    """Save payroll input for a single employee for a month (Admin/HR only)."""
    if current_user.role not in HR_ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Only Admin/HR Manager can update payroll inputs")
    db = get_db()
    employee_id = data.get("employee_id")
    month = data.get("month")
    if not employee_id or not month:
        raise HTTPException(status_code=400, detail="employee_id and month required")
    required_fields = ["working_days", "present_days", "absent_days", "public_holidays", "leaves", "overtime_hours", "incentive", "advance", "penalty"]
    for f in required_fields:
        if data.get(f) is None or data.get(f) == '':
            raise HTTPException(status_code=400, detail=f"Field '{f.replace('_', ' ')}' is mandatory. Enter 0 if not applicable.")
    input_doc = {
        "employee_id": employee_id,
        "month": month,
        "present_days": data.get("present_days", 0),
        "absent_days": data.get("absent_days", 0),
        "public_holidays": data.get("public_holidays", 0),
        "leaves": data.get("leaves", 0),
        "working_days": data.get("working_days", 30),
        "incentive": data.get("incentive", 0),
        "incentive_reason": data.get("incentive_reason", ""),
        "advance": data.get("advance", 0),
        "advance_reason": data.get("advance_reason", ""),
        "penalty": data.get("penalty", 0),
        "penalty_reason": data.get("penalty_reason", ""),
        "overtime_hours": data.get("overtime_hours", 0),
        "remarks": data.get("remarks", ""),
        "updated_by": current_user.id,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    await db.payroll_inputs.update_one(
        {"employee_id": employee_id, "month": month},
        {"$set": input_doc},
        upsert=True
    )
    return {"message": "Payroll input saved"}


@router.post("/inputs/bulk")
async def save_payroll_inputs_bulk(data: dict, current_user: User = Depends(get_current_user)):
    """Save payroll inputs for multiple employees (Admin/HR only)"""
    if current_user.role not in HR_ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Only Admin/HR Manager can update payroll inputs")
    db = get_db()
    month = data.get("month")
    inputs = data.get("inputs", [])
    if not month or not inputs:
        raise HTTPException(status_code=400, detail="month and inputs required")
    saved = 0
    for inp in inputs:
        inp["month"] = month
        inp["updated_by"] = current_user.id
        inp["updated_at"] = datetime.now(timezone.utc).isoformat()
        await db.payroll_inputs.update_one(
            {"employee_id": inp["employee_id"], "month": month},
            {"$set": inp},
            upsert=True
        )
        saved += 1
    return {"message": f"Saved {saved} payroll inputs"}


@router.get("/salary-slips")
async def get_salary_slips(employee_id: Optional[str] = None, month: Optional[str] = None, current_user: User = Depends(get_current_user)):
    """Get generated salary slips"""
    db = get_db()
    query = {}
    if employee_id:
        query["employee_id"] = employee_id
    if month:
        query["month"] = month
    if current_user.role not in HR_ROLES:
        emp = await db.employees.find_one({"user_id": current_user.id}, {"_id": 0, "id": 1})
        if emp:
            query["employee_id"] = emp["id"]
        else:
            return []
    slips = await db.salary_slips.find(query, {"_id": 0}).sort("month", -1).to_list(500)
    return slips


@router.post("/generate-slip")
async def generate_salary_slip(data: dict, current_user: User = Depends(get_current_user)):
    """Generate salary slip for an employee. Admin/HR only."""
    if current_user.role not in HR_ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Only Admin/HR Manager can generate salary slips")
    db = get_db()
    employee_id = data.get("employee_id")
    month = data.get("month")
    if not employee_id or not month:
        raise HTTPException(status_code=400, detail="employee_id and month required")
    
    if current_user.role != "admin":
        own_emp = await db.employees.find_one({"user_id": current_user.id}, {"_id": 0, "id": 1})
        if own_emp and own_emp['id'] == employee_id:
            raise HTTPException(status_code=403, detail="You cannot generate your own salary slip.")
    
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    go_live_status = employee.get("go_live_status")
    if go_live_status != "active":
        emp_name = f"{employee.get('first_name', '')} {employee.get('last_name', '')}".strip()
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot generate salary slip for {emp_name}. Employee is not Go-Live Active. Current status: {go_live_status or 'Not Started'}"
        )
    
    gross_salary = employee.get("salary", 0) or 0
    if gross_salary <= 0:
        raise HTTPException(status_code=400, detail="Employee salary not configured")
    
    active_ctc = await db.ctc_structures.find_one({
        "employee_id": employee_id,
        "status": "active",
        "effective_month": {"$lte": month}
    }, {"_id": 0}, sort=[("effective_month", -1)])
    
    earnings = []
    total_earnings = 0
    deductions = []
    total_deductions = 0
    
    if active_ctc and active_ctc.get("components"):
        for key, comp in active_ctc["components"].items():
            if not comp.get("enabled", True):
                continue
            monthly_amount = comp.get("monthly", 0)
            if monthly_amount <= 0:
                continue
            
            if comp.get("is_earning", True) and not comp.get("is_deferred"):
                earnings.append({
                    "name": comp.get("name", key), 
                    "key": key, 
                    "amount": round(monthly_amount, 2)
                })
                total_earnings += monthly_amount
            elif comp.get("is_deduction"):
                deductions.append({
                    "name": comp.get("name", key), 
                    "key": key, 
                    "amount": round(monthly_amount, 2)
                })
                total_deductions += monthly_amount
        
        gross_salary = active_ctc.get("summary", {}).get("gross_monthly", gross_salary)
    else:
        config = await db.payroll_config.find_one({"type": "salary_components"}, {"_id": 0})
        if not config:
            raise HTTPException(status_code=400, detail="Salary components not configured")
        
        for comp in config.get("earnings", []):
            if comp.get("percentage"):
                amount = round(gross_salary * comp["percentage"] / 100, 2)
            else:
                amount = comp.get("fixed", 0)
            earnings.append({"name": comp["name"], "key": comp["key"], "amount": amount})
            total_earnings += amount
        
        for comp in config.get("deductions", []):
            if comp.get("percentage"):
                amount = round(gross_salary * comp["percentage"] / 100, 2)
            else:
                amount = comp.get("fixed", 0)
            deductions.append({"name": comp["name"], "key": comp["key"], "amount": amount})
            total_deductions += amount
    
    att_records = await db.attendance.find({"employee_id": employee_id, "date": {"$regex": f"^{month}"}}, {"_id": 0}).to_list(50)
    present_days = sum(1 for r in att_records if r.get("status") in ["present", "work_from_home"])
    absent_days = sum(1 for r in att_records if r.get("status") == "absent")
    half_days = sum(1 for r in att_records if r.get("status") == "half_day")
    
    leave_requests = await db.leave_requests.find({
        "employee_id": employee_id,
        "status": "approved",
        "$or": [
            {"start_date": {"$regex": f"^{month}"}},
            {"end_date": {"$regex": f"^{month}"}}
        ]
    }, {"_id": 0}).to_list(50)
    
    auto_leaves = 0
    auto_half_day_leaves = 0
    for lr in leave_requests:
        if lr.get("is_half_day"):
            auto_half_day_leaves += 0.5
        else:
            auto_leaves += lr.get("days", 0)
    
    payroll_input = await db.payroll_inputs.find_one({"employee_id": employee_id, "month": month}, {"_id": 0})
    if payroll_input:
        if payroll_input.get("present_days", 0) > 0:
            present_days = payroll_input["present_days"]
        if payroll_input.get("absent_days", 0) > 0:
            absent_days = payroll_input["absent_days"]
        incentive_amt = payroll_input.get("incentive", 0) or 0
        if incentive_amt > 0:
            reason = payroll_input.get("incentive_reason", "")
            earnings.append({"name": f"Incentive{(' - ' + reason) if reason else ''}", "key": "incentive", "amount": round(incentive_amt, 2)})
            total_earnings += incentive_amt
        ot_hours = payroll_input.get("overtime_hours", 0) or 0
        if ot_hours > 0:
            ot_rate = round(gross_salary / (30 * 8), 2)
            ot_amount = round(ot_hours * ot_rate * 1.5, 2)
            earnings.append({"name": f"Overtime ({ot_hours} hrs)", "key": "overtime", "amount": ot_amount})
            total_earnings += ot_amount
        advance_amt = payroll_input.get("advance", 0) or 0
        if advance_amt > 0:
            reason = payroll_input.get("advance_reason", "")
            deductions.append({"name": f"Salary Advance{(' - ' + reason) if reason else ''}", "key": "advance", "amount": round(advance_amt, 2)})
            total_deductions += advance_amt
        penalty_amt = payroll_input.get("penalty", 0) or 0
        if penalty_amt > 0:
            reason = payroll_input.get("penalty_reason", "")
            deductions.append({"name": f"Penalty{(' - ' + reason) if reason else ''}", "key": "penalty", "amount": round(penalty_amt, 2)})
            total_deductions += penalty_amt
    working_days = payroll_input.get("working_days", 30) if payroll_input else 30
    public_holidays = payroll_input.get("public_holidays", 0) if payroll_input else 0
    leaves_count = payroll_input.get("leaves", 0) if payroll_input else 0
    if leaves_count == 0:
        leaves_count = auto_leaves + auto_half_day_leaves
    
    half_day_leaves = auto_half_day_leaves
    
    lop_leave_requests = await db.leave_requests.find({
        "employee_id": employee_id,
        "status": "approved",
        "leave_type": {"$in": ["loss_of_pay", "lop", "unpaid", "leave_without_pay"]},
        "$or": [
            {"start_date": {"$regex": f"^{month}"}},
            {"end_date": {"$regex": f"^{month}"}}
        ]
    }, {"_id": 0}).to_list(50)
    
    lop_days = 0
    for lr in lop_leave_requests:
        lop_days += lr.get("days", 0)
    
    per_day_salary = round(gross_salary / working_days, 2) if working_days > 0 else 0
    lop_deduction = round(per_day_salary * lop_days, 2)
    
    if lop_deduction > 0:
        deductions.append({
            "name": f"Loss of Pay ({lop_days} days)", 
            "key": "lop_deduction", 
            "amount": lop_deduction,
            "lop_days": lop_days
        })
        total_deductions += lop_deduction
        
        for lr in lop_leave_requests:
            await db.leave_requests.update_one(
                {"id": lr["id"]},
                {"$set": {"payroll_deducted": True, "payroll_month": month, "lop_amount": round(per_day_salary * lr.get("days", 0), 2)}}
            )
    
    expense_reimb = 0
    expense_reimbursements_list = []
    
    payroll_reimb_records = await db.payroll_reimbursements.find({
        "employee_id": employee_id,
        "payroll_period": month,
        "status": "pending"
    }, {"_id": 0}).to_list(50)
    
    for pr in payroll_reimb_records:
        expense_reimb += pr.get("amount", 0)
        expense_reimbursements_list.append({
            "expense_id": pr.get("expense_id"),
            "amount": pr.get("amount", 0),
            "category": pr.get("category", "expense"),
            "description": pr.get("description", "")[:50]
        })
        await db.payroll_reimbursements.update_one(
            {"id": pr["id"]},
            {"$set": {"status": "processed", "processed_at": datetime.now(timezone.utc).isoformat()}}
        )
        if pr.get("expense_id"):
            await db.expenses.update_one(
                {"id": pr["expense_id"]},
                {"$set": {"status": "reimbursed", "reimbursed_at": datetime.now(timezone.utc).isoformat(), "reimbursed_in_month": month}}
            )
    
    # Query expenses - support both employee_id (code) and user_id (UUID)
    emp_code = employee.get("employee_id")  # Employee code like EMP003
    user_id = employee.get("user_id")  # User UUID
    
    expense_query = {
        "$or": [
            {"employee_id": emp_code},
            {"employee_id": employee_id},  # Some old records may use internal ID
        ],
        "status": "approved",
        "payroll_period": month
    }
    if user_id:
        expense_query["$or"].append({"user_id": user_id})
        expense_query["$or"].append({"created_by": user_id})
    
    direct_expenses = await db.expenses.find(expense_query, {"_id": 0}).to_list(100)
    for exp in direct_expenses:
        if exp.get("id") not in [r.get("expense_id") for r in payroll_reimb_records]:
            exp_amount = exp.get("total_amount", 0) or exp.get("amount", 0)
            expense_reimb += exp_amount
            expense_reimbursements_list.append({
                "expense_id": exp.get("id"),
                "amount": exp_amount,
                "category": exp.get("category", "expense"),
                "description": (exp.get("description") or exp.get("notes", ""))[:50]
            })
            await db.expenses.update_one(
                {"id": exp["id"]},
                {"$set": {"status": "reimbursed", "reimbursed_at": datetime.now(timezone.utc).isoformat(), "reimbursed_in_month": month}}
            )
    
    expense_reimb = round(expense_reimb, 2)
    if expense_reimb > 0:
        earnings.append({
            "name": f"Expense Reimbursement ({len(expense_reimbursements_list)} claims)", 
            "key": "expense_reimbursement", 
            "amount": expense_reimb,
            "details": expense_reimbursements_list
        })
        total_earnings += expense_reimb
    
    # Calculate effective present days for reference
    _ = present_days + (half_days * 0.5)  # Used for logging/reporting
    unexcused_absences = max(0, absent_days - leaves_count)
    if unexcused_absences > 0 and not payroll_input:
        absence_deduction = round(per_day_salary * unexcused_absences, 2)
        if absence_deduction > 0:
            deductions.append({
                "name": f"Absent Days Deduction ({unexcused_absences} days)", 
                "key": "absence_deduction", 
                "amount": absence_deduction
            })
            total_deductions += absence_deduction
    
    existing = await db.salary_slips.find_one({"employee_id": employee_id, "month": month}, {"_id": 0})
    slip = {
        "id": existing["id"] if existing else str(uuid.uuid4()),
        "employee_id": employee_id,
        "employee_name": f"{employee['first_name']} {employee['last_name']}",
        "employee_code": employee.get("employee_id", ""),
        "department": employee.get("department", ""),
        "designation": employee.get("designation", ""),
        "month": month,
        "gross_salary": gross_salary,
        "earnings": earnings,
        "total_earnings": round(total_earnings, 2),
        "deductions": deductions,
        "total_deductions": round(total_deductions, 2),
        "net_salary": round(total_earnings - total_deductions, 2),
        "present_days": present_days,
        "absent_days": absent_days,
        "half_days": half_days,
        "working_days": working_days,
        "public_holidays": public_holidays,
        "leaves": leaves_count,
        "half_day_leaves": half_day_leaves,
        "lop_days": lop_days,
        "lop_deduction": lop_deduction,
        "expense_reimbursements": expense_reimbursements_list if expense_reimb > 0 else [],
        "expense_reimbursement_total": expense_reimb,
        "attendance_linked": len(att_records) > 0,
        "leave_requests_linked": len(leave_requests) > 0,
        "payroll_reimbursements_linked": len(payroll_reimb_records) > 0,
        "bank_account_number": employee.get("bank_account_number") or (employee.get("bank_details", {}) or {}).get("account_number"),
        "bank_name": employee.get("bank_name") or (employee.get("bank_details", {}) or {}).get("bank_name"),
        "ifsc_code": employee.get("ifsc_code") or (employee.get("bank_details", {}) or {}).get("ifsc_code"),
        "generated_by": current_user.id,
        "generated_at": datetime.now(timezone.utc).isoformat()
    }
    if existing:
        await db.salary_slips.update_one({"id": existing["id"]}, {"$set": slip})
    else:
        await db.salary_slips.insert_one(slip)
    
    slip.pop("_id", None)
    return slip


@router.post("/generate-bulk")
async def generate_bulk_salary_slips(data: dict, current_user: User = Depends(get_current_user)):
    """Generate salary slips for all active employees for a month"""
    if current_user.role not in HR_ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Only Admin/HR Manager can generate salary slips")
    db = get_db()
    month = data.get("month")
    if not month:
        raise HTTPException(status_code=400, detail="month required (YYYY-MM)")
    employees = await db.employees.find({"is_active": True, "salary": {"$gt": 0}}, {"_id": 0}).to_list(500)
    generated = 0
    for emp in employees:
        try:
            await generate_salary_slip({"employee_id": emp["id"], "month": month}, current_user)
            generated += 1
        except Exception:
            pass
    return {"message": f"Generated {generated} salary slips for {month}", "count": generated}


@router.get("/linkage-summary")
async def get_payroll_linkage_summary(month: str, current_user: User = Depends(get_current_user)):
    """Get summary of all payroll linkages for a month - attendance, leaves, expenses"""
    if current_user.role not in HR_ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Only Admin/HR Manager can view payroll linkage summary")
    db = get_db()
    
    pending_reimbursements = await db.payroll_reimbursements.find({
        "payroll_period": month,
        "status": "pending"
    }, {"_id": 0}).to_list(500)
    
    lop_leaves = await db.leave_requests.find({
        "status": "approved",
        "leave_type": {"$in": ["loss_of_pay", "lop", "unpaid", "leave_without_pay"]},
        "$or": [
            {"start_date": {"$regex": f"^{month}"}},
            {"end_date": {"$regex": f"^{month}"}}
        ]
    }, {"_id": 0}).to_list(500)
    
    attendance_records = await db.attendance.find({
        "date": {"$regex": f"^{month}"}
    }, {"_id": 0}).to_list(2000)
    
    attendance_by_employee = {}
    for att in attendance_records:
        emp_id = att.get("employee_id")
        if emp_id not in attendance_by_employee:
            attendance_by_employee[emp_id] = {"present": 0, "absent": 0, "half_day": 0, "wfh": 0}
        status = att.get("status", "present")
        if status == "present":
            attendance_by_employee[emp_id]["present"] += 1
        elif status == "absent":
            attendance_by_employee[emp_id]["absent"] += 1
        elif status == "half_day":
            attendance_by_employee[emp_id]["half_day"] += 1
        elif status == "work_from_home":
            attendance_by_employee[emp_id]["wfh"] += 1
    
    generated_slips = await db.salary_slips.find({"month": month}, {"_id": 0, "employee_id": 1, "employee_name": 1, "net_salary": 1, "lop_days": 1, "expense_reimbursement_total": 1}).to_list(500)
    
    total_reimbursements = sum(r.get("amount", 0) for r in pending_reimbursements)
    total_lop_days = sum(leave.get("days", 0) for leave in lop_leaves)
    
    return {
        "month": month,
        "pending_reimbursements": {
            "count": len(pending_reimbursements),
            "total_amount": total_reimbursements,
            "items": pending_reimbursements[:20]
        },
        "lop_leaves": {
            "count": len(lop_leaves),
            "total_days": total_lop_days,
            "items": lop_leaves[:20]
        },
        "attendance_summary": {
            "employees_with_records": len(attendance_by_employee),
            "total_records": len(attendance_records)
        },
        "salary_slips": {
            "generated_count": len(generated_slips),
            "slips": generated_slips
        }
    }


@router.get("/pending-reimbursements")
async def get_pending_reimbursements(month: Optional[str] = None, current_user: User = Depends(get_current_user)):
    """Get all pending expense reimbursements for payroll processing"""
    if current_user.role not in HR_ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Only Admin/HR Manager can view pending reimbursements")
    db = get_db()
    
    query = {"status": "pending"}
    if month:
        query["payroll_period"] = month
    
    reimbursements = await db.payroll_reimbursements.find(query, {"_id": 0}).sort("created_at", -1).to_list(500)
    
    total = sum(r.get("amount", 0) for r in reimbursements)
    
    return {
        "reimbursements": reimbursements,
        "total_amount": total,
        "count": len(reimbursements)
    }


@router.get("/summary-report")
async def get_payroll_summary_report(month: str, current_user: User = Depends(get_current_user)):
    """Get payroll summary report for a month with department breakdown"""
    if current_user.role not in HR_ROLES:
        raise HTTPException(status_code=403, detail="Only HR can view payroll reports")
    db = get_db()
    
    salary_slips = await db.salary_slips.find({"month": month}, {"_id": 0}).to_list(500)
    
    if not salary_slips:
        return {
            "month": month,
            "total_employees": 0,
            "total_gross_salary": 0,
            "total_net_salary": 0,
            "total_deductions": 0,
            "total_reimbursements": 0,
            "total_lop_deductions": 0,
            "total_penalties": 0,
            "total_leave_days": 0,
            "avg_attendance_percent": 0,
            "department_breakdown": {},
            "employee_details": []
        }
    
    payroll_inputs = await db.payroll_inputs.find({"month": month}, {"_id": 0}).to_list(500)
    inputs_by_emp = {p.get("employee_id"): p for p in payroll_inputs}
    
    emp_ids = [s.get("employee_id") for s in salary_slips]
    employees = await db.employees.find({"id": {"$in": emp_ids}}, {"_id": 0}).to_list(500)
    emp_by_id = {e.get("id"): e for e in employees}
    
    total_gross = 0
    total_net = 0
    total_deductions = 0
    total_reimbursements = 0
    total_lop = 0
    total_penalties = 0
    total_leaves = 0
    total_present = 0
    total_working = 0
    
    department_breakdown = {}
    employee_details = []
    
    for slip in salary_slips:
        emp_id = slip.get("employee_id")
        emp = emp_by_id.get(emp_id, {})
        inputs = inputs_by_emp.get(emp_id, {})
        
        gross = slip.get("gross_salary") or slip.get("ctc_monthly", 0)
        net = slip.get("net_salary", 0)
        deduct = slip.get("total_deductions", 0)
        reimbursements = sum(r.get("amount", 0) for r in slip.get("reimbursements", []))
        lop = sum(d.get("amount", 0) for d in slip.get("loss_of_pay_deductions", []))
        penalty = inputs.get("penalty", 0)
        leaves = inputs.get("leaves", 0)
        present = inputs.get("present_days", 0)
        working = inputs.get("working_days", 30)
        
        total_gross += gross
        total_net += net
        total_deductions += deduct
        total_reimbursements += reimbursements
        total_lop += lop
        total_penalties += penalty
        total_leaves += leaves
        total_present += present
        total_working += working
        
        dept = emp.get("department") or "Unassigned"
        if dept not in department_breakdown:
            department_breakdown[dept] = {"employee_count": 0, "total_salary": 0}
        department_breakdown[dept]["employee_count"] += 1
        department_breakdown[dept]["total_salary"] += net
        
        employee_details.append({
            "employee_id": emp_id,
            "employee_code": emp.get("employee_id", ""),
            "name": f"{emp.get('first_name', '')} {emp.get('last_name', '')}".strip() or slip.get("employee_name", ""),
            "department": dept,
            "gross_salary": gross,
            "total_deductions": deduct,
            "reimbursements": reimbursements,
            "net_salary": net,
            "present_days": present,
            "leave_days": leaves,
            "lop_days": sum(d.get("days", 0) for d in slip.get("loss_of_pay_deductions", []))
        })
    
    avg_attendance = (total_present / total_working * 100) if total_working > 0 else 0
    
    return {
        "month": month,
        "total_employees": len(salary_slips),
        "total_gross_salary": total_gross,
        "total_net_salary": total_net,
        "total_deductions": total_deductions,
        "total_reimbursements": total_reimbursements,
        "total_lop_deductions": total_lop,
        "total_penalties": total_penalties,
        "total_leave_days": total_leaves,
        "avg_attendance_percent": round(avg_attendance, 1),
        "department_breakdown": department_breakdown,
        "employee_details": sorted(employee_details, key=lambda x: x["name"])
    }


@router.post("/generate-summary-report")
async def generate_summary_report(data: dict, current_user: User = Depends(get_current_user)):
    """Generate and save a payroll summary report"""
    if current_user.role not in HR_ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Only HR Manager/Admin can generate reports")
    db = get_db()
    
    month = data.get("month")
    if not month:
        raise HTTPException(status_code=400, detail="Month is required")
    
    summary = await get_payroll_summary_report(month, current_user)
    
    report = {
        "id": str(uuid.uuid4()),
        "month": month,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generated_by": current_user.id,
        "generated_by_name": current_user.full_name,
        "data": summary
    }
    
    await db.payroll_reports.update_one(
        {"month": month},
        {"$set": report},
        upsert=True
    )
    
    return {"message": f"Payroll summary report generated for {month}", "report_id": report["id"]}


@router.get("/generated-reports")
async def get_generated_reports(current_user: User = Depends(get_current_user)):
    """Get list of generated payroll reports"""
    if current_user.role not in HR_ROLES:
        raise HTTPException(status_code=403, detail="Only HR can view reports")
    db = get_db()
    
    reports = await db.payroll_reports.find({}, {"_id": 0, "id": 1, "month": 1, "generated_at": 1, "generated_by_name": 1}).sort("month", -1).to_list(50)
    return reports


# ==================== LEAVE ENCASHMENT INTEGRATION ====================

@router.get("/leave-encashments")
async def get_leave_encashments(
    month: Optional[int] = None,
    year: Optional[int] = None,
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get leave encashment requests for payroll processing"""
    if current_user.role not in HR_ROLES:
        raise HTTPException(status_code=403, detail="Only HR can view leave encashments")
    
    db = get_db()
    query = {}
    if month:
        query["month"] = month
    if year:
        query["year"] = year
    if status:
        query["status"] = status
    
    encashments = await db.leave_encashments.find(query, {"_id": 0}).sort("created_at", -1).to_list(200)
    
    # Enrich with employee data
    emp_ids = list(set(e.get("employee_id") for e in encashments))
    employees = await db.employees.find({"id": {"$in": emp_ids}}, {"_id": 0}).to_list(500)
    emp_map = {e["id"]: e for e in employees}
    
    for enc in encashments:
        emp = emp_map.get(enc.get("employee_id"), {})
        enc["employee_name"] = f"{emp.get('first_name', '')} {emp.get('last_name', '')}".strip()
        enc["department"] = emp.get("department", "")
        # Calculate amount based on employee salary
        ctc = emp.get("ctc", 0) or emp.get("salary", 0) * 12
        basic_per_day = (ctc * 0.4 / 12) / 30 if ctc else 0
        enc["estimated_amount"] = round(basic_per_day * enc.get("days", 0), 2)
    
    return encashments


@router.post("/leave-encashments/{encashment_id}/approve")
async def approve_leave_encashment(
    encashment_id: str,
    current_user: User = Depends(get_current_user)
):
    """Approve a leave encashment request and link to payroll"""
    if current_user.role not in HR_ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Only HR Admin can approve encashments")
    
    db = get_db()
    
    encashment = await db.leave_encashments.find_one({"id": encashment_id}, {"_id": 0})
    if not encashment:
        raise HTTPException(status_code=404, detail="Encashment request not found")
    
    if encashment.get("status") != "pending":
        raise HTTPException(status_code=400, detail=f"Cannot approve. Current status: {encashment.get('status')}")
    
    # Get employee and calculate amount
    employee = await db.employees.find_one({"id": encashment["employee_id"]}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    ctc = employee.get("ctc", 0) or employee.get("salary", 0) * 12
    basic_per_day = (ctc * 0.4 / 12) / 30 if ctc else 0
    amount = round(basic_per_day * encashment.get("days", 0), 2)
    
    # Update encashment status
    await db.leave_encashments.update_one(
        {"id": encashment_id},
        {"$set": {
            "status": "approved",
            "approved_by": current_user.id,
            "approved_at": datetime.now(timezone.utc).isoformat(),
            "amount": amount,
            "payroll_month": f"{encashment.get('year')}-{encashment.get('month'):02d}"
        }}
    )
    
    # Update employee leave balance (deduct encashed days)
    leave_type = encashment.get("leave_type", "earned_leave")
    await db.employees.update_one(
        {"id": encashment["employee_id"]},
        {"$inc": {f"leave_balance.used_{leave_type.replace('_leave', '')}": encashment.get("days", 0)}}
    )
    
    return {"message": "Leave encashment approved", "amount": amount}


@router.post("/leave-encashments/{encashment_id}/reject")
async def reject_leave_encashment(
    encashment_id: str,
    data: dict,
    current_user: User = Depends(get_current_user)
):
    """Reject a leave encashment request"""
    if current_user.role not in HR_ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Only HR Admin can reject encashments")
    
    db = get_db()
    
    await db.leave_encashments.update_one(
        {"id": encashment_id},
        {"$set": {
            "status": "rejected",
            "rejected_by": current_user.id,
            "rejected_at": datetime.now(timezone.utc).isoformat(),
            "rejection_reason": data.get("reason", "")
        }}
    )
    
    return {"message": "Leave encashment rejected"}


@router.get("/leave-policy-adjustments/{employee_id}")
async def get_leave_policy_adjustments_for_payroll(
    employee_id: str,
    month: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get all leave-related payroll adjustments for an employee:
    - LOP deductions
    - Leave encashment amounts
    - Calculated based on effective leave policy
    """
    if current_user.role not in HR_ROLES:
        raise HTTPException(status_code=403, detail="Only HR can view payroll adjustments")
    
    db = get_db()
    
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Parse month
    year, mon = map(int, month.split('-'))
    
    # Get CTC/salary info
    ctc = employee.get("ctc", 0) or employee.get("salary", 0) * 12
    monthly_gross = ctc / 12 if ctc else employee.get("salary", 0)
    basic = monthly_gross * 0.4
    per_day_basic = basic / 30
    
    # Get LOP leaves
    month_start = f"{year}-{mon:02d}-01"
    next_month = mon + 1 if mon < 12 else 1
    next_year = year if mon < 12 else year + 1
    month_end = f"{next_year}-{next_month:02d}-01"
    
    lop_leaves = await db.leave_requests.find({
        "employee_id": employee_id,
        "status": "approved",
        "leave_type": {"$in": ["loss_of_pay", "lop", "unpaid", "leave_without_pay"]},
        "start_date": {"$gte": month_start, "$lt": month_end}
    }, {"_id": 0}).to_list(50)
    
    lop_days = sum(leave.get("days", 0) for leave in lop_leaves)
    lop_deduction = round(lop_days * per_day_basic, 2)
    
    # Get approved encashments
    encashments = await db.leave_encashments.find({
        "employee_id": employee_id,
        "status": "approved",
        "month": mon,
        "year": year
    }, {"_id": 0}).to_list(10)
    
    encash_days = sum(e.get("days", 0) for e in encashments)
    encash_amount = round(encash_days * per_day_basic, 2)
    
    return {
        "employee_id": employee_id,
        "employee_name": f"{employee.get('first_name', '')} {employee.get('last_name', '')}".strip(),
        "month": month,
        "salary_info": {
            "monthly_gross": round(monthly_gross, 2),
            "basic": round(basic, 2),
            "per_day_basic": round(per_day_basic, 2)
        },
        "lop": {
            "days": lop_days,
            "deduction": lop_deduction,
            "leaves": lop_leaves
        },
        "encashment": {
            "days": encash_days,
            "amount": encash_amount,
            "requests": encashments
        },
        "net_adjustment": round(encash_amount - lop_deduction, 2)
    }



# ==================== PAYROLL APPROVAL WORKFLOW ====================

PAYROLL_STATUSES = ["draft", "submitted", "hr_approved", "finance_approved", "disbursed", "rejected"]


@router.get("/payroll-run")
async def get_payroll_runs(
    month: Optional[str] = None,
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get payroll run records with approval status."""
    if current_user.role not in HR_ROLES:
        raise HTTPException(status_code=403, detail="Only HR can view payroll runs")
    
    db = get_db()
    query = {}
    if month:
        query["month"] = month
    if status:
        query["status"] = status
    
    runs = await db.payroll_runs.find(query, {"_id": 0}).sort("month", -1).to_list(100)
    return runs


@router.post("/payroll-run/create")
async def create_payroll_run(data: dict, current_user: User = Depends(get_current_user)):
    """Create a new payroll run for a month (initiates approval workflow)."""
    if current_user.role not in HR_ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Only HR Manager/Admin can create payroll runs")
    
    db = get_db()
    month = data.get("month")
    if not month:
        raise HTTPException(status_code=400, detail="Month is required (YYYY-MM)")
    
    # Check if payroll run already exists for this month
    existing = await db.payroll_runs.find_one({"month": month}, {"_id": 0})
    if existing:
        raise HTTPException(status_code=400, detail=f"Payroll run already exists for {month}. Status: {existing.get('status')}")
    
    # Get salary slips count for this month
    slips = await db.salary_slips.find({"month": month}, {"_id": 0}).to_list(1000)
    if not slips:
        raise HTTPException(status_code=400, detail=f"No salary slips generated for {month}. Generate slips first.")
    
    total_gross = sum(s.get("gross_salary", 0) for s in slips)
    total_deductions = sum(s.get("total_deductions", 0) for s in slips)
    total_net = sum(s.get("net_salary", 0) for s in slips)
    total_reimbursements = sum(s.get("expense_reimbursement_total", 0) for s in slips)
    
    payroll_run = {
        "id": str(uuid.uuid4()),
        "month": month,
        "status": "draft",
        "employee_count": len(slips),
        "total_gross": round(total_gross, 2),
        "total_deductions": round(total_deductions, 2),
        "total_net": round(total_net, 2),
        "total_reimbursements": round(total_reimbursements, 2),
        "created_by": current_user.id,
        "created_by_name": current_user.full_name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "approval_history": [{
            "action": "created",
            "status": "draft",
            "by": current_user.id,
            "by_name": current_user.full_name,
            "at": datetime.now(timezone.utc).isoformat()
        }],
        "is_locked": False
    }
    
    await db.payroll_runs.insert_one(payroll_run)
    payroll_run.pop("_id", None)
    
    return {"message": f"Payroll run created for {month}", "payroll_run": payroll_run}


@router.post("/payroll-run/{run_id}/submit")
async def submit_payroll_for_approval(run_id: str, current_user: User = Depends(get_current_user)):
    """Submit payroll run for HR approval."""
    if current_user.role not in HR_ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Only HR Manager/Admin can submit payroll")
    
    db = get_db()
    run = await db.payroll_runs.find_one({"id": run_id}, {"_id": 0})
    if not run:
        raise HTTPException(status_code=404, detail="Payroll run not found")
    
    if run.get("status") != "draft":
        raise HTTPException(status_code=400, detail=f"Cannot submit. Current status: {run.get('status')}")
    
    # Lock the payroll data
    now = datetime.now(timezone.utc).isoformat()
    await db.payroll_runs.update_one(
        {"id": run_id},
        {
            "$set": {
                "status": "submitted",
                "is_locked": True,
                "locked_at": now,
                "locked_by": current_user.id,
                "submitted_at": now,
                "submitted_by": current_user.id,
                "submitted_by_name": current_user.full_name
            },
            "$push": {
                "approval_history": {
                    "action": "submitted",
                    "status": "submitted",
                    "by": current_user.id,
                    "by_name": current_user.full_name,
                    "at": now
                }
            }
        }
    )
    
    # Lock all salary slips for this month
    await db.salary_slips.update_many(
        {"month": run["month"]},
        {"$set": {"is_locked": True, "locked_at": now, "payroll_run_id": run_id}}
    )
    
    return {"message": "Payroll submitted for approval and locked"}


@router.post("/payroll-run/{run_id}/approve")
async def approve_payroll(run_id: str, data: dict = None, current_user: User = Depends(get_current_user)):
    """Approve payroll run (HR Manager → Finance → Admin)."""
    db = get_db()
    run = await db.payroll_runs.find_one({"id": run_id}, {"_id": 0})
    if not run:
        raise HTTPException(status_code=404, detail="Payroll run not found")
    
    current_status = run.get("status")
    now = datetime.now(timezone.utc).isoformat()
    comments = (data or {}).get("comments", "")
    
    # Determine next status based on current status and role
    if current_status == "submitted":
        if current_user.role not in ["hr_manager", "admin"]:
            raise HTTPException(status_code=403, detail="Only HR Manager can approve submitted payroll")
        new_status = "hr_approved"
        action = "hr_approved"
    elif current_status == "hr_approved":
        if current_user.role not in ["admin", "finance_manager"]:
            raise HTTPException(status_code=403, detail="Only Finance/Admin can approve HR-approved payroll")
        new_status = "finance_approved"
        action = "finance_approved"
    elif current_status == "finance_approved":
        if current_user.role != "admin":
            raise HTTPException(status_code=403, detail="Only Admin can give final approval")
        new_status = "disbursed"
        action = "disbursed"
    else:
        raise HTTPException(status_code=400, detail=f"Cannot approve. Current status: {current_status}")
    
    await db.payroll_runs.update_one(
        {"id": run_id},
        {
            "$set": {
                "status": new_status,
                f"{action}_at": now,
                f"{action}_by": current_user.id,
                f"{action}_by_name": current_user.full_name
            },
            "$push": {
                "approval_history": {
                    "action": action,
                    "status": new_status,
                    "by": current_user.id,
                    "by_name": current_user.full_name,
                    "comments": comments,
                    "at": now
                }
            }
        }
    )
    
    # If disbursed, mark salary slips as disbursed
    if new_status == "disbursed":
        await db.salary_slips.update_many(
            {"month": run["month"]},
            {"$set": {"status": "disbursed", "disbursed_at": now}}
        )
    
    return {"message": f"Payroll {action}", "new_status": new_status}


@router.post("/payroll-run/{run_id}/reject")
async def reject_payroll(run_id: str, data: dict, current_user: User = Depends(get_current_user)):
    """Reject payroll run with reason (unlocks for corrections)."""
    if current_user.role not in ["hr_manager", "admin", "finance_manager"]:
        raise HTTPException(status_code=403, detail="Only HR Manager/Finance/Admin can reject payroll")
    
    db = get_db()
    run = await db.payroll_runs.find_one({"id": run_id}, {"_id": 0})
    if not run:
        raise HTTPException(status_code=404, detail="Payroll run not found")
    
    reason = data.get("reason", "")
    if not reason:
        raise HTTPException(status_code=400, detail="Rejection reason is required")
    
    current_status = run.get("status")
    if current_status in ["draft", "rejected", "disbursed"]:
        raise HTTPException(status_code=400, detail=f"Cannot reject. Current status: {current_status}")
    
    now = datetime.now(timezone.utc).isoformat()
    
    await db.payroll_runs.update_one(
        {"id": run_id},
        {
            "$set": {
                "status": "rejected",
                "is_locked": False,  # Unlock for corrections
                "rejected_at": now,
                "rejected_by": current_user.id,
                "rejected_by_name": current_user.full_name,
                "rejection_reason": reason
            },
            "$push": {
                "approval_history": {
                    "action": "rejected",
                    "status": "rejected",
                    "by": current_user.id,
                    "by_name": current_user.full_name,
                    "reason": reason,
                    "at": now
                }
            }
        }
    )
    
    # Unlock salary slips for corrections
    await db.salary_slips.update_many(
        {"month": run["month"]},
        {"$set": {"is_locked": False}}
    )
    
    return {"message": "Payroll rejected and unlocked for corrections"}


@router.post("/payroll-run/{run_id}/resubmit")
async def resubmit_payroll(run_id: str, current_user: User = Depends(get_current_user)):
    """Resubmit rejected payroll after corrections."""
    if current_user.role not in HR_ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Only HR Manager/Admin can resubmit payroll")
    
    db = get_db()
    run = await db.payroll_runs.find_one({"id": run_id}, {"_id": 0})
    if not run:
        raise HTTPException(status_code=404, detail="Payroll run not found")
    
    if run.get("status") != "rejected":
        raise HTTPException(status_code=400, detail="Can only resubmit rejected payroll")
    
    # Recalculate totals from updated slips
    slips = await db.salary_slips.find({"month": run["month"]}, {"_id": 0}).to_list(1000)
    total_gross = sum(s.get("gross_salary", 0) for s in slips)
    total_deductions = sum(s.get("total_deductions", 0) for s in slips)
    total_net = sum(s.get("net_salary", 0) for s in slips)
    total_reimbursements = sum(s.get("expense_reimbursement_total", 0) for s in slips)
    
    now = datetime.now(timezone.utc).isoformat()
    
    await db.payroll_runs.update_one(
        {"id": run_id},
        {
            "$set": {
                "status": "submitted",
                "is_locked": True,
                "locked_at": now,
                "total_gross": round(total_gross, 2),
                "total_deductions": round(total_deductions, 2),
                "total_net": round(total_net, 2),
                "total_reimbursements": round(total_reimbursements, 2),
                "resubmitted_at": now,
                "resubmitted_by": current_user.id
            },
            "$push": {
                "approval_history": {
                    "action": "resubmitted",
                    "status": "submitted",
                    "by": current_user.id,
                    "by_name": current_user.full_name,
                    "at": now
                }
            }
        }
    )
    
    # Re-lock salary slips
    await db.salary_slips.update_many(
        {"month": run["month"]},
        {"$set": {"is_locked": True, "locked_at": now}}
    )
    
    return {"message": "Payroll resubmitted for approval"}


# ==================== PAYROLL LOCKING ====================

@router.get("/lock-status/{month}")
async def get_payroll_lock_status(month: str, current_user: User = Depends(get_current_user)):
    """Check if payroll is locked for a month."""
    if current_user.role not in HR_ROLES:
        raise HTTPException(status_code=403, detail="Only HR can check lock status")
    
    db = get_db()
    run = await db.payroll_runs.find_one({"month": month}, {"_id": 0})
    
    if not run:
        return {
            "month": month,
            "is_locked": False,
            "status": None,
            "can_modify_attendance": True,
            "can_modify_leaves": True,
            "can_modify_expenses": True,
            "can_regenerate_slips": True
        }
    
    is_locked = run.get("is_locked", False)
    status = run.get("status")
    
    return {
        "month": month,
        "is_locked": is_locked,
        "status": status,
        "payroll_run_id": run.get("id"),
        "can_modify_attendance": not is_locked,
        "can_modify_leaves": not is_locked,
        "can_modify_expenses": not is_locked,
        "can_regenerate_slips": status in ["draft", "rejected"],
        "locked_at": run.get("locked_at"),
        "locked_by_name": run.get("submitted_by_name")
    }


@router.post("/unlock/{month}")
async def unlock_payroll_month(month: str, data: dict, current_user: User = Depends(get_current_user)):
    """Emergency unlock payroll for a month (Admin only with reason)."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only Admin can unlock payroll")
    
    db = get_db()
    reason = data.get("reason", "")
    if not reason:
        raise HTTPException(status_code=400, detail="Unlock reason is required")
    
    run = await db.payroll_runs.find_one({"month": month}, {"_id": 0})
    if not run:
        raise HTTPException(status_code=404, detail=f"No payroll run found for {month}")
    
    if run.get("status") == "disbursed":
        raise HTTPException(status_code=400, detail="Cannot unlock disbursed payroll")
    
    now = datetime.now(timezone.utc).isoformat()
    
    await db.payroll_runs.update_one(
        {"id": run["id"]},
        {
            "$set": {
                "is_locked": False,
                "status": "draft",
                "unlocked_at": now,
                "unlocked_by": current_user.id,
                "unlock_reason": reason
            },
            "$push": {
                "approval_history": {
                    "action": "emergency_unlock",
                    "status": "draft",
                    "by": current_user.id,
                    "by_name": current_user.full_name,
                    "reason": reason,
                    "at": now
                }
            }
        }
    )
    
    # Unlock salary slips
    await db.salary_slips.update_many(
        {"month": month},
        {"$set": {"is_locked": False}}
    )
    
    return {"message": f"Payroll for {month} unlocked. Reason: {reason}"}


# ==================== BANK DETAILS STANDARDIZATION ====================

@router.get("/employees-bank-status")
async def get_employees_bank_status(current_user: User = Depends(get_current_user)):
    """Get list of employees with incomplete bank details."""
    if current_user.role not in HR_ROLES:
        raise HTTPException(status_code=403, detail="Only HR can view bank status")
    
    db = get_db()
    employees = await db.employees.find(
        {"go_live_status": "active"},
        {"_id": 0, "id": 1, "employee_id": 1, "first_name": 1, "last_name": 1, 
         "bank_account_number": 1, "bank_name": 1, "ifsc_code": 1, "bank_details": 1}
    ).to_list(500)
    
    incomplete = []
    complete = []
    
    for emp in employees:
        # Check both old format and new format
        account = emp.get("bank_account_number") or (emp.get("bank_details", {}) or {}).get("account_number")
        bank = emp.get("bank_name") or (emp.get("bank_details", {}) or {}).get("bank_name")
        ifsc = emp.get("ifsc_code") or (emp.get("bank_details", {}) or {}).get("ifsc_code")
        
        emp_data = {
            "employee_id": emp.get("id"),
            "employee_code": emp.get("employee_id"),
            "name": f"{emp.get('first_name', '')} {emp.get('last_name', '')}".strip(),
            "has_account": bool(account),
            "has_bank_name": bool(bank),
            "has_ifsc": bool(ifsc)
        }
        
        if account and bank and ifsc:
            complete.append(emp_data)
        else:
            incomplete.append(emp_data)
    
    return {
        "total_active": len(employees),
        "complete_count": len(complete),
        "incomplete_count": len(incomplete),
        "incomplete_employees": incomplete
    }


@router.post("/standardize-bank-details/{employee_id}")
async def standardize_bank_details(employee_id: str, current_user: User = Depends(get_current_user)):
    """Migrate employee bank details to standardized format."""
    if current_user.role not in HR_ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Only HR Manager/Admin can update bank details")
    
    db = get_db()
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Consolidate bank details
    bank_details = {
        "account_number": employee.get("bank_account_number") or (employee.get("bank_details", {}) or {}).get("account_number"),
        "bank_name": employee.get("bank_name") or (employee.get("bank_details", {}) or {}).get("bank_name"),
        "ifsc_code": employee.get("ifsc_code") or (employee.get("bank_details", {}) or {}).get("ifsc_code"),
        "account_type": (employee.get("bank_details", {}) or {}).get("account_type", "savings"),
        "branch": (employee.get("bank_details", {}) or {}).get("branch", "")
    }
    
    await db.employees.update_one(
        {"id": employee_id},
        {
            "$set": {"bank_details": bank_details},
            "$unset": {"bank_account_number": "", "bank_name": "", "ifsc_code": ""}
        }
    )
    
    return {"message": "Bank details standardized", "bank_details": bank_details}


@router.post("/standardize-bank-details-bulk")
async def standardize_bank_details_bulk(current_user: User = Depends(get_current_user)):
    """
    Migrate ALL employees' bank details to standardized format.
    Consolidates flat fields (bank_account_number, bank_name, ifsc_code) 
    into nested bank_details object and removes old fields.
    
    Admin only.
    """
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only Admin can run bulk standardization")
    
    db = get_db()
    
    # Find all employees with old-style bank fields
    employees = await db.employees.find(
        {"$or": [
            {"bank_account_number": {"$exists": True}},
            {"bank_name": {"$exists": True}},
            {"ifsc_code": {"$exists": True}}
        ]},
        {"_id": 0, "id": 1, "employee_id": 1, "first_name": 1, "last_name": 1,
         "bank_account_number": 1, "bank_name": 1, "ifsc_code": 1, "bank_details": 1}
    ).to_list(1000)
    
    migrated = 0
    skipped = 0
    errors = []
    
    for emp in employees:
        try:
            # Consolidate bank details
            bank_details = {
                "account_number": emp.get("bank_account_number") or (emp.get("bank_details", {}) or {}).get("account_number"),
                "bank_name": emp.get("bank_name") or (emp.get("bank_details", {}) or {}).get("bank_name"),
                "ifsc_code": emp.get("ifsc_code") or (emp.get("bank_details", {}) or {}).get("ifsc_code"),
                "account_type": (emp.get("bank_details", {}) or {}).get("account_type", "savings"),
                "branch": (emp.get("bank_details", {}) or {}).get("branch", "")
            }
            
            # Only migrate if there's data to migrate
            if bank_details["account_number"] or bank_details["bank_name"] or bank_details["ifsc_code"]:
                await db.employees.update_one(
                    {"id": emp["id"]},
                    {
                        "$set": {"bank_details": bank_details},
                        "$unset": {"bank_account_number": "", "bank_name": "", "ifsc_code": ""}
                    }
                )
                migrated += 1
            else:
                skipped += 1
        except Exception as e:
            errors.append({
                "employee_id": emp.get("employee_id"),
                "error": str(e)
            })
    
    return {
        "message": f"Bulk standardization complete",
        "total_processed": len(employees),
        "migrated": migrated,
        "skipped": skipped,
        "errors": errors
    }


@router.get("/bank-schema-status")
async def get_bank_schema_status(current_user: User = Depends(get_current_user)):
    """
    Get status of bank details schema migration.
    Shows how many employees are using old vs new format.
    """
    if current_user.role not in HR_ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Only HR Manager/Admin can view schema status")
    
    db = get_db()
    
    # Count employees with old-style fields
    old_format_count = await db.employees.count_documents({
        "$or": [
            {"bank_account_number": {"$exists": True, "$ne": None, "$ne": ""}},
            {"bank_name": {"$exists": True, "$ne": None, "$ne": ""}},
            {"ifsc_code": {"$exists": True, "$ne": None, "$ne": ""}}
        ]
    })
    
    # Count employees with new-style nested bank_details
    new_format_count = await db.employees.count_documents({
        "bank_details.account_number": {"$exists": True, "$ne": None, "$ne": ""}
    })
    
    # Count total active employees
    total_active = await db.employees.count_documents({"go_live_status": "active"})
    
    # Get sample of employees still using old format
    old_format_samples = await db.employees.find(
        {"$or": [
            {"bank_account_number": {"$exists": True, "$ne": None, "$ne": ""}},
            {"bank_name": {"$exists": True, "$ne": None, "$ne": ""}},
            {"ifsc_code": {"$exists": True, "$ne": None, "$ne": ""}}
        ]},
        {"_id": 0, "id": 1, "employee_id": 1, "first_name": 1, "last_name": 1}
    ).limit(10).to_list(10)
    
    is_standardized = old_format_count == 0
    
    return {
        "is_standardized": is_standardized,
        "total_active_employees": total_active,
        "old_format_count": old_format_count,
        "new_format_count": new_format_count,
        "old_format_samples": old_format_samples,
        "recommendation": "Run bulk standardization" if old_format_count > 0 else "Schema is already standardized"
    }



# ==================== ATTENDANCE GAP DETECTION ====================

@router.get("/attendance-gaps/{month}")
async def get_attendance_gaps(month: str, current_user: User = Depends(get_current_user)):
    """
    Detect attendance gaps for a payroll month.
    Returns employees with missing attendance records for working days.
    """
    if current_user.role not in HR_ROLES:
        raise HTTPException(status_code=403, detail="Only HR can view attendance gaps")
    
    db = get_db()
    
    # Get all active (Go-Live) employees
    employees = await db.employees.find(
        {"go_live_status": "active", "is_active": {"$ne": False}},
        {"_id": 0, "id": 1, "employee_id": 1, "first_name": 1, "last_name": 1, "department": 1, "date_of_joining": 1}
    ).to_list(500)
    
    if not employees:
        return {"message": "No active employees found", "gaps": []}
    
    # Get holidays for the month
    holidays = await db.holidays.find({
        "date": {"$regex": f"^{month}"}
    }, {"_id": 0, "date": 1}).to_list(31)
    holiday_dates = set(h.get("date") for h in holidays)
    
    # Generate expected working days for the month
    year, month_num = int(month[:4]), int(month[5:7])
    _, days_in_month = calendar.monthrange(year, month_num)
    
    working_days = []
    for day in range(1, days_in_month + 1):
        date_str = f"{month}-{day:02d}"
        dt = datetime(year, month_num, day)
        # Skip weekends (Saturday=5, Sunday=6)
        if dt.weekday() < 5 and date_str not in holiday_dates:
            working_days.append(date_str)
    
    # Get attendance records for all employees for this month
    attendance_records = await db.attendance.find({
        "date": {"$regex": f"^{month}"},
        "approval_status": {"$in": ["approved", None, "pending_approval"]}
    }, {"_id": 0, "employee_id": 1, "date": 1, "status": 1}).to_list(10000)
    
    # Build attendance map
    attendance_map = {}
    for rec in attendance_records:
        emp_id = rec.get("employee_id")
        date = rec.get("date")
        if emp_id not in attendance_map:
            attendance_map[emp_id] = set()
        attendance_map[emp_id].add(date)
    
    # Get leave records
    leave_records = await db.leave_requests.find({
        "status": "approved",
        "$or": [
            {"start_date": {"$regex": f"^{month}"}},
            {"end_date": {"$regex": f"^{month}"}}
        ]
    }, {"_id": 0, "employee_id": 1, "start_date": 1, "end_date": 1}).to_list(1000)
    
    # Build leave map
    leave_map = {}
    for leave in leave_records:
        emp_id = leave.get("employee_id")
        if emp_id not in leave_map:
            leave_map[emp_id] = set()
        # Add all dates in leave range
        try:
            start = datetime.fromisoformat(leave["start_date"])
            end = datetime.fromisoformat(leave["end_date"])
            current = start
            while current <= end:
                leave_map[emp_id].add(current.strftime("%Y-%m-%d"))
                current += timedelta(days=1)
        except (ValueError, TypeError):
            pass
    
    # Detect gaps for each employee
    gaps = []
    for emp in employees:
        emp_id = emp.get("id")
        emp_attendance = attendance_map.get(emp_id, set())
        emp_leaves = leave_map.get(emp_id, set())
        
        # Check joining date - don't flag gaps before joining
        joining_date = emp.get("date_of_joining", "")
        
        missing_days = []
        for wd in working_days:
            # Skip if before joining date
            if joining_date and wd < joining_date:
                continue
            
            # Skip if today or in future
            if wd >= datetime.now().strftime("%Y-%m-%d"):
                continue
            
            # Check if has attendance or leave
            if wd not in emp_attendance and wd not in emp_leaves:
                missing_days.append(wd)
        
        if missing_days:
            gaps.append({
                "employee_id": emp_id,
                "employee_code": emp.get("employee_id"),
                "employee_name": f"{emp.get('first_name', '')} {emp.get('last_name', '')}".strip(),
                "department": emp.get("department"),
                "missing_days": missing_days,
                "missing_count": len(missing_days),
                "total_working_days": len(working_days),
                "attendance_percentage": round((len(working_days) - len(missing_days)) / len(working_days) * 100, 1) if working_days else 0
            })
    
    # Sort by missing count descending
    gaps.sort(key=lambda x: x["missing_count"], reverse=True)
    
    return {
        "month": month,
        "total_working_days": len(working_days),
        "holidays": len(holiday_dates),
        "employees_with_gaps": len(gaps),
        "total_employees": len(employees),
        "gaps": gaps
    }


@router.post("/fill-attendance-gaps")
async def fill_attendance_gaps(data: dict, current_user: User = Depends(get_current_user)):
    """
    Bulk fill attendance gaps with a specified status.
    Used to mark missing days as absent/leave.
    """
    if current_user.role not in HR_ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Only HR Manager/Admin can fill gaps")
    
    db = get_db()
    
    employee_id = data.get("employee_id")
    dates = data.get("dates", [])
    status = data.get("status", "absent")  # absent, on_leave, holiday
    notes = data.get("notes", "Filled via attendance gap detection")
    
    if not employee_id or not dates:
        raise HTTPException(status_code=400, detail="employee_id and dates are required")
    
    valid_statuses = ["absent", "on_leave", "holiday", "half_day"]
    if status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}")
    
    # Verify employee exists
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0, "id": 1, "employee_id": 1})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    created_count = 0
    skipped_count = 0
    
    for date in dates:
        # Check if record already exists
        existing = await db.attendance.find_one({
            "employee_id": employee_id,
            "date": date
        }, {"_id": 0, "id": 1})
        
        if existing:
            skipped_count += 1
            continue
        
        # Create attendance record
        record = {
            "id": str(uuid.uuid4()),
            "employee_id": employee_id,
            "employee_code": employee.get("employee_id"),
            "date": date,
            "status": status,
            "notes": notes,
            "approval_status": "approved",  # Auto-approve gap fills
            "source": "gap_fill",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "created_by": current_user.id
        }
        
        await db.attendance.insert_one(record)
        created_count += 1
    
    return {
        "message": f"Created {created_count} attendance records, skipped {skipped_count} existing",
        "created": created_count,
        "skipped": skipped_count
    }
