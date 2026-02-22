"""
Payroll Router - Salary components, payroll inputs, salary slips, reports
Extracted from server.py for better modularity and load performance.
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Optional, List
from datetime import datetime, timezone
import uuid
from .deps import get_db, HR_ADMIN_ROLES, HR_ROLES, DEFAULT_PAGE_SIZE, LARGE_QUERY_SIZE
from .models import User
from .auth import get_current_user

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
    
    expense_query = {"employee_id": employee_id, "status": "approved", "payroll_period": month}
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
