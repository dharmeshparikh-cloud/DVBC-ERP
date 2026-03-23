"""
Payroll Engine Router - Production-grade payroll APIs

APIs:
- POST /payroll/engine/run - Run payroll for month (creates draft)
- POST /payroll/engine/simulate - Simulate single employee (HR Test Mode)
- POST /payroll/engine/simulate-bulk - Bulk simulation with Excel
- GET /payroll/engine/register - Get payroll register
- GET /payroll/engine/breakdown/{employee_id} - Field-level breakdown
- POST /payroll/engine/approve - Approval workflow
- GET /payroll/engine/comparison - Before/After comparison
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from typing import Optional, List
from datetime import datetime, timezone
import uuid
import io
import pandas as pd

from .deps import get_db, HR_ADMIN_ROLES, HR_ROLES, get_current_user
from .models import User
from .audit_logging import log_audit
from services.payroll_engine import get_payroll_engine

router = APIRouter(prefix="/payroll/engine", tags=["Payroll Engine"])


# ==================== PAYROLL RUN ====================

@router.post("/run")
async def run_payroll(
    data: dict,
    current_user: User = Depends(get_current_user)
):
    """
    Run payroll calculation for a month.
    Creates payroll register in DRAFT status.
    
    Required: HR Manager role
    """
    if current_user.role not in HR_ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Only HR Manager can run payroll")
    
    db = get_db()
    month = data.get("month")
    if not month:
        raise HTTPException(status_code=400, detail="Month is required (format: YYYY-MM)")
    
    # Check if payroll already exists for this month - handle duplicate drafts
    existing_registers = await db.payroll_register.find(
        {"month": month, "status": {"$ne": "cancelled"}}
    ).to_list(100)
    
    for existing in existing_registers:
        if existing.get("status") == "locked":
            raise HTTPException(
                status_code=400, 
                detail=f"Payroll for {month} is already locked. Create adjustment entry instead."
            )
        # Delete ALL drafts if re-running (fixes duplicate draft bug)
        if existing.get("status") in ["draft", "pending_admin_approval"]:
            await db.payroll_register.delete_one({"_id": existing["_id"]})
    
    # Also clean up any old calculations for this month to prevent stale data
    await db.payroll_calculations.delete_many({"month": month, "status": {"$ne": "locked"}})
    
    engine = get_payroll_engine(db)
    
    # Get all active employees
    employees = await db.employees.find(
        {"is_active": True, "go_live_status": "active"},
        {"_id": 0}
    ).to_list(1000)
    
    if not employees:
        raise HTTPException(status_code=400, detail="No active employees found")
    
    # Get payroll inputs for all employees
    inputs = await db.payroll_inputs.find({"month": month}, {"_id": 0}).to_list(1000)
    inputs_map = {i["employee_id"]: i for i in inputs}
    
    # Process each employee
    calculations = []
    total_gross = 0
    total_net = 0
    total_deductions = 0
    errors = []
    department_summary = {}
    
    for emp in employees:
        emp_id = emp.get("id")
        
        # Get CTC structure
        ctc = await db.ctc_structures.find_one(
            {"employee_id": emp_id, "status": "active"},
            {"_id": 0}
        )
        
        # Get payroll input
        payroll_input = inputs_map.get(emp_id, {})
        
        # Calculate
        result = await engine.run_payroll_calculation(
            employee=emp,
            month=month,
            payroll_input=payroll_input,
            ctc_structure=ctc
        )
        
        if result.get("success"):
            calculations.append(result)
            total_gross += result.get("gross_monthly", 0)
            total_net += result.get("net_payable", 0)
            total_deductions += result.get("total_deductions", 0)
            
            # Department summary
            dept = result.get("department", "Unknown")
            if dept not in department_summary:
                department_summary[dept] = {"count": 0, "gross": 0, "net": 0}
            department_summary[dept]["count"] += 1
            department_summary[dept]["gross"] += result.get("gross_monthly", 0)
            department_summary[dept]["net"] += result.get("net_payable", 0)
            
            # Store individual calculation
            calc_doc = {
                "id": str(uuid.uuid4()),
                "employee_id": emp_id,
                "month": month,
                **result,
                "status": "calculated"
            }
            await db.payroll_calculations.update_one(
                {"employee_id": emp_id, "month": month},
                {"$set": calc_doc},
                upsert=True
            )
        else:
            errors.append({
                "employee_id": emp_id,
                "employee_name": f"{emp.get('first_name', '')} {emp.get('last_name', '')}".strip(),
                "error": result.get("error_message", "Unknown error")
            })
    
    # Create payroll register
    register_id = str(uuid.uuid4())
    register = {
        "id": register_id,
        "month": month,
        "status": "draft",
        "total_employees": len(calculations),
        "total_errors": len(errors),
        "total_gross_salary": round(total_gross, 2),
        "total_deductions": round(total_deductions, 2),
        "total_net_payable": round(total_net, 2),
        "department_summary": department_summary,
        "errors": errors,
        "created_by": current_user.id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "approval_history": []
    }
    
    await db.payroll_register.insert_one(register)
    
    # Audit log
    await log_audit(
        action="payroll.run",
        entity_type="payroll_register",
        entity_id=register_id,
        performed_by=current_user.id,
        after_state={
            "month": month,
            "total_employees": len(calculations),
            "total_net": round(total_net, 2)
        }
    )
    
    return {
        "success": True,
        "register_id": register_id,
        "month": month,
        "status": "draft",
        "total_employees": len(calculations),
        "total_errors": len(errors),
        "total_gross_salary": round(total_gross, 2),
        "total_net_payable": round(total_net, 2),
        "department_summary": department_summary,
        "errors": errors[:10],  # First 10 errors
        "message": f"Payroll calculated for {len(calculations)} employees. {len(errors)} errors."
    }


# ==================== SIMULATION (HR TEST MODE) ====================

@router.post("/simulate")
async def simulate_payroll(
    data: dict,
    current_user: User = Depends(get_current_user)
):
    """
    Simulate payroll for a single employee (HR Test Mode).
    Does NOT save to database.
    
    Supports all granular inputs:
    - Earnings: bonus, incentive, arrears, overtime_hours
    - Reimbursements: travel, medical, food, telephone, other
    - Deductions: penalty, advance_recovery, loan_emi, other_deduction
    - Metadata: reasons for arrears, penalty, advance, loan_type
    """
    if current_user.role not in HR_ROLES:
        raise HTTPException(status_code=403, detail="Only HR can simulate payroll")
    
    db = get_db()
    employee_id = data.get("employee_id")
    month = data.get("month")
    
    if not employee_id or not month:
        raise HTTPException(status_code=400, detail="employee_id and month required")
    
    engine = get_payroll_engine(db)
    
    # Build comprehensive simulation inputs with all granular fields
    simulation_inputs = {
        # LOP
        "lop_days": data.get("lop_days", 0),
        "working_days": data.get("working_days", 30),
        
        # Earnings
        "bonus": data.get("bonus", 0),
        "incentive": data.get("incentive", 0),
        "overtime_hours": data.get("overtime_hours", 0),
        "arrears": data.get("arrears", 0),
        "arrears_reason": data.get("arrears_reason", ""),
        
        # Reimbursements (non-taxable)
        "travel_reimbursement": data.get("travel_reimbursement", 0),
        "medical_reimbursement": data.get("medical_reimbursement", 0),
        "food_reimbursement": data.get("food_reimbursement", 0),
        "telephone_reimbursement": data.get("telephone_reimbursement", 0),
        "other_reimbursement": data.get("other_reimbursement", 0),
        
        # Deductions
        "penalty": data.get("penalty", 0),
        "penalty_reason": data.get("penalty_reason", ""),
        "advance_recovery": data.get("advance_recovery", 0),
        "advance_reason": data.get("advance_reason", ""),
        "loan_emi": data.get("loan_emi", 0),
        "loan_type": data.get("loan_type", ""),
        "other_deduction": data.get("other_deduction", 0),
        "other_deduction_name": data.get("other_deduction_name", "")
    }
    
    result = await engine.simulate_payroll(
        employee_id=employee_id,
        month=month,
        simulation_inputs=simulation_inputs
    )
    
    # Fetch previous month's actual saved data for comparison
    if result.get("success"):
        year, mon = map(int, month.split('-'))
        if mon == 1:
            prev_month = f"{year-1}-12"
        else:
            prev_month = f"{year}-{mon-1:02d}"
        
        previous_calc = await db.payroll_calculations.find_one(
            {"employee_id": employee_id, "month": prev_month},
            {"_id": 0}
        )
        
        if previous_calc:
            # Build comparison between simulation and previous actual
            changes = []
            
            # Compare key fields
            comparisons = [
                ("Net Payable", result.get("net_payable", 0), previous_calc.get("net_salary", 0)),
                ("Gross Salary", result.get("gross_monthly", 0), previous_calc.get("gross_salary", 0)),
                ("Total Deductions", result.get("total_deductions", 0), previous_calc.get("total_deductions", 0)),
                ("Total Earnings", result.get("total_earnings", 0), previous_calc.get("total_earnings", previous_calc.get("gross_salary", 0))),
            ]
            
            for field, current, previous in comparisons:
                if current != previous and previous > 0:
                    diff = current - previous
                    pct = round((diff / previous) * 100, 2) if previous else 0
                    changes.append({
                        "field": field,
                        "current": current,
                        "previous": previous,
                        "difference": diff,
                        "percentage_change": pct
                    })
            
            result["comparison"] = {
                "has_previous": True,
                "previous_month": prev_month,
                "previous_net": previous_calc.get("net_salary", 0),
                "previous_gross": previous_calc.get("gross_salary", 0),
                "previous_deductions": previous_calc.get("total_deductions", 0),
                "changes": changes
            }
        else:
            result["comparison"] = {
                "has_previous": False,
                "previous_month": prev_month,
                "message": f"No saved payroll data for {prev_month}"
            }
    
    return result


@router.post("/simulate-bulk")
async def simulate_bulk_payroll(
    data: dict,
    current_user: User = Depends(get_current_user)
):
    """
    Bulk payroll simulation from list of employees.
    
    Input:
    {
        "month": "2024-03",
        "employees": [
            {"employee_id": "xxx", "lop_days": 2},
            {"employee_id": "yyy", "lop_days": 0, "bonus": 5000}
        ]
    }
    """
    if current_user.role not in HR_ROLES:
        raise HTTPException(status_code=403, detail="Only HR can simulate payroll")
    
    db = get_db()
    month = data.get("month")
    employees_data = data.get("employees", [])
    
    if not month:
        raise HTTPException(status_code=400, detail="Month is required")
    
    engine = get_payroll_engine(db)
    result = await engine.run_bulk_simulation(month, employees_data)
    
    return result


@router.post("/simulate-bulk-excel")
async def simulate_bulk_from_excel(
    month: str,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """
    Upload Excel with employee_id, lop_days columns for bulk simulation.
    
    Expected columns: employee_id, lop_days, bonus (optional), incentive (optional)
    """
    if current_user.role not in HR_ROLES:
        raise HTTPException(status_code=403, detail="Only HR can simulate payroll")
    
    if not file.filename.endswith(('.xlsx', '.xls', '.csv')):
        raise HTTPException(status_code=400, detail="Only Excel/CSV files allowed")
    
    try:
        contents = await file.read()
        
        if file.filename.endswith('.csv'):
            df = pd.read_csv(io.BytesIO(contents))
        else:
            df = pd.read_excel(io.BytesIO(contents))
        
        # Validate required columns
        if 'employee_id' not in df.columns:
            raise HTTPException(status_code=400, detail="Column 'employee_id' is required")
        
        # Build employee inputs
        employees_data = []
        for _, row in df.iterrows():
            emp_input = {
                "employee_id": str(row.get("employee_id", "")),
                "lop_days": float(row.get("lop_days", 0) or 0),
                "bonus": float(row.get("bonus", 0) or 0),
                "incentive": float(row.get("incentive", 0) or 0),
                "penalty": float(row.get("penalty", 0) or 0)
            }
            if emp_input["employee_id"]:
                employees_data.append(emp_input)
        
        if not employees_data:
            raise HTTPException(status_code=400, detail="No valid employee data found in file")
        
        db = get_db()
        engine = get_payroll_engine(db)
        result = await engine.run_bulk_simulation(month, employees_data)
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error processing file: {str(e)}")


# ==================== PAYROLL REGISTER ====================

@router.get("/register")
async def get_payroll_register(
    month: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get payroll register for a month"""
    if current_user.role not in HR_ROLES:
        raise HTTPException(status_code=403, detail="Only HR can view payroll register")
    
    db = get_db()
    query = {}
    if month:
        query["month"] = month
    
    registers = await db.payroll_register.find(query, {"_id": 0}).sort("month", -1).to_list(50)
    return registers


@router.get("/register/{month}/details")
async def get_payroll_register_details(
    month: str,
    current_user: User = Depends(get_current_user)
):
    """Get detailed payroll register with all employee calculations"""
    if current_user.role not in HR_ROLES:
        raise HTTPException(status_code=403, detail="Only HR can view payroll details")
    
    db = get_db()
    
    # Get register summary
    register = await db.payroll_register.find_one({"month": month}, {"_id": 0})
    if not register:
        raise HTTPException(status_code=404, detail=f"No payroll register found for {month}")
    
    # Get all calculations
    calculations = await db.payroll_calculations.find(
        {"month": month},
        {"_id": 0}
    ).to_list(1000)
    
    return {
        "register": register,
        "calculations": calculations
    }


# ==================== CLEANUP & MAINTENANCE ====================

@router.post("/cleanup-duplicates")
async def cleanup_duplicate_registers(
    current_user: User = Depends(get_current_user)
):
    """
    Clean up duplicate draft records in payroll register.
    Keeps only the latest draft per month, removes older duplicates.
    Admin only.
    """
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only Admin can run cleanup")
    
    db = get_db()
    
    # Get all registers grouped by month
    all_registers = await db.payroll_register.find({}, {"_id": 1, "month": 1, "status": 1, "created_at": 1}).to_list(1000)
    
    # Group by month
    from collections import defaultdict
    by_month = defaultdict(list)
    for reg in all_registers:
        by_month[reg["month"]].append(reg)
    
    deleted_count = 0
    kept_count = 0
    cleanup_log = []
    
    for month, registers in by_month.items():
        if len(registers) <= 1:
            kept_count += 1
            continue
        
        # Separate locked and drafts
        locked = [r for r in registers if r.get("status") == "locked"]
        drafts = [r for r in registers if r.get("status") != "locked"]
        
        # Keep the locked one (if exists) and latest draft
        if drafts:
            # Sort drafts by created_at descending
            drafts.sort(key=lambda x: x.get("created_at", ""), reverse=True)
            latest_draft = drafts[0]
            duplicates_to_delete = drafts[1:]
            
            for dup in duplicates_to_delete:
                await db.payroll_register.delete_one({"_id": dup["_id"]})
                deleted_count += 1
                cleanup_log.append({
                    "month": month,
                    "deleted_id": str(dup["_id"]),
                    "status": dup.get("status"),
                    "created_at": dup.get("created_at")
                })
            
            kept_count += 1  # Latest draft kept
        
        if locked:
            kept_count += len(locked)
    
    return {
        "success": True,
        "deleted_count": deleted_count,
        "kept_count": kept_count,
        "cleanup_log": cleanup_log,
        "message": f"Cleaned up {deleted_count} duplicate records. {kept_count} registers retained."
    }


@router.get("/register-detailed")
async def get_detailed_register(
    month: Optional[str] = None,
    employee_id: Optional[str] = None,
    department: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """
    Get detailed payroll register with component-wise breakdown.
    Supports filtering by month, employee, and department.
    
    Returns full breakdown: Basic, HRA, Allowances, LOP, PF, PT, TDS, etc.
    """
    if current_user.role not in HR_ROLES:
        raise HTTPException(status_code=403, detail="Only HR can view payroll register")
    
    db = get_db()
    
    # Build query for calculations
    query = {}
    if month:
        query["month"] = month
    if employee_id:
        query["employee_id"] = employee_id
    
    # Get all calculations matching filters
    calculations = await db.payroll_calculations.find(query, {"_id": 0}).to_list(1000)
    
    if not calculations:
        return {
            "success": True,
            "data": [],
            "summary": {
                "total_employees": 0,
                "total_gross": 0,
                "total_deductions": 0,
                "total_net": 0
            },
            "filters_applied": {
                "month": month,
                "employee_id": employee_id,
                "department": department
            }
        }
    
    # Enrich with employee data and build detailed breakdown
    detailed_data = []
    total_gross = 0
    total_deductions = 0
    total_net = 0
    
    # Component-wise totals
    component_totals = {
        "basic": 0,
        "hra": 0,
        "special_allowance": 0,
        "bonus": 0,
        "incentive": 0,
        "arrears": 0,
        "overtime": 0,
        "reimbursements": 0,
        "lop": 0,
        "pf_employee": 0,
        "pf_employer": 0,
        "pt": 0,
        "tds": 0,
        "esi": 0,
        "advance_recovery": 0,
        "loan_emi": 0,
        "other_deductions": 0
    }
    
    for calc in calculations:
        emp_id = calc.get("employee_id")
        
        # Fetch employee details
        employee = await db.employees.find_one({"id": emp_id}, {"_id": 0, "first_name": 1, "last_name": 1, "employee_id": 1, "department": 1})
        
        # Apply department filter
        if department and employee and employee.get("department") != department:
            continue
        
        # Parse earnings directly from calculation (not nested in breakdown)
        earnings = calc.get("earnings", [])
        deductions = calc.get("deductions", [])
        
        # Parse earnings - handle both dict and list formats
        basic = 0
        hra = 0
        special = 0
        bonus = 0
        incentive = 0
        arrears = 0
        overtime = 0
        reimbursements = calc.get("reimbursements", 0) or 0
        
        if isinstance(earnings, list):
            for e in earnings:
                key = e.get("key", "").lower()
                amt = abs(e.get("amount", 0))
                if key == "basic_salary" or key == "basic":
                    basic = amt
                elif key == "hra" or key == "house_rent_allowance":
                    hra = amt
                elif key == "special_allowance":
                    special = amt
                elif key == "bonus":
                    bonus = amt
                elif key == "incentive":
                    incentive = amt
                elif key == "arrears":
                    arrears = amt
                elif key == "overtime":
                    overtime = amt
        
        # Parse deductions
        lop = 0
        pf = 0
        pt = 0
        tds = 0
        esi = 0
        advance = 0
        loan = 0
        penalty = 0
        other_ded = 0
        
        if isinstance(deductions, list):
            for d in deductions:
                key = d.get("key", "").lower()
                amt = abs(d.get("amount", 0))
                if key == "lop" or key == "loss_of_pay":
                    lop = amt
                elif key == "pf" or key == "provident_fund":
                    pf = amt
                elif key == "pt" or key == "professional_tax":
                    pt = amt
                elif key == "tds" or key == "income_tax":
                    tds = amt
                elif key == "esi":
                    esi = amt
                elif key == "advance_recovery":
                    advance = amt
                elif key == "loan_emi":
                    loan = amt
                elif key == "penalty":
                    penalty = amt
                elif key == "other_deduction":
                    other_ded = amt
        
        # Get values directly from calculation
        gross = calc.get("gross_monthly", 0) or calc.get("total_earnings", 0) or 0
        total_ded = calc.get("total_deductions", 0) or 0
        net = calc.get("net_payable", 0) or calc.get("net_salary", 0) or 0
        
        # Get attendance data
        attendance_summary = calc.get("attendance_summary", {})
        working_days = calc.get("working_days", attendance_summary.get("working_days", 0))
        lop_days = calc.get("lop_days", attendance_summary.get("lop_days", 0))
        
        # Get TDS details
        tds_details = calc.get("tds_details", {})
        if tds == 0 and tds_details:
            tds = tds_details.get("monthly_tds", 0)
        
        # Get employer contributions
        employer_contribs = calc.get("employer_contributions", {})
        pf_employer = employer_contribs.get("pf", pf)  # Usually same as employee
        esi_employer = employer_contribs.get("esi", 0)
        
        detailed_data.append({
            "employee_id": emp_id,
            "employee_code": calc.get("employee_code") or (employee.get("employee_id") if employee else emp_id),
            "employee_name": calc.get("employee_name") or (f"{employee.get('first_name', '')} {employee.get('last_name', '')}".strip() if employee else "Unknown"),
            "department": calc.get("department") or (employee.get("department") if employee else "Unknown"),
            "month": calc.get("month"),
            "status": calc.get("status", "draft"),
            
            # Earnings Breakdown
            "earnings": {
                "basic": round(basic, 2),
                "hra": round(hra, 2),
                "special_allowance": round(special, 2),
                "bonus": round(bonus, 2),
                "incentive": round(incentive, 2),
                "arrears": round(arrears, 2),
                "overtime": round(overtime, 2),
                "reimbursements": round(reimbursements, 2),
                "gross_earnings": round(gross, 2)
            },
            
            # Deductions Breakdown
            "deductions": {
                "lop": round(lop, 2),
                "pf_employee": round(pf, 2),
                "professional_tax": round(pt, 2),
                "tds": round(tds, 2),
                "esi": round(esi, 2),
                "advance_recovery": round(advance, 2),
                "loan_emi": round(loan, 2),
                "penalty": round(penalty, 2),
                "other": round(other_ded, 2),
                "total_deductions": round(total_ded, 2)
            },
            
            # Net
            "net_payable": round(net, 2),
            
            # Employer Contributions
            "employer_contributions": {
                "pf": round(pf_employer, 2),
                "esi": round(esi_employer, 2)
            },
            
            # Attendance
            "attendance": {
                "working_days": working_days,
                "present_days": attendance_summary.get("present", 0),
                "lop_days": lop_days,
                "leaves_taken": attendance_summary.get("leaves", 0)
            },
            
            # TDS Details
            "tds_details": {
                "taxable_income": tds_details.get("taxable_income", 0),
                "annual_tax": tds_details.get("annual_tax", 0),
                "rebate_87a": tds_details.get("rebate_87a", 0),
                "regime": tds_details.get("regime", "new")
            }
        })
        
        # Update totals
        total_gross += gross
        total_deductions += total_ded
        total_net += net
        
        # Update component totals
        component_totals["basic"] += basic
        component_totals["hra"] += hra
        component_totals["special_allowance"] += special
        component_totals["bonus"] += bonus
        component_totals["incentive"] += incentive
        component_totals["arrears"] += arrears
        component_totals["overtime"] += overtime
        component_totals["reimbursements"] += reimbursements
        component_totals["lop"] += abs(lop)
        component_totals["pf_employee"] += abs(pf)
        component_totals["pt"] += abs(pt)
        component_totals["tds"] += abs(tds)
        component_totals["esi"] += abs(esi)
        component_totals["advance_recovery"] += abs(advance)
        component_totals["loan_emi"] += abs(loan)
        component_totals["other_deductions"] += abs(penalty) + abs(other_ded)
    
    # Get unique departments for filter options
    departments = list(set(d.get("department") for d in detailed_data if d.get("department")))
    
    # Get available months
    all_months = await db.payroll_calculations.distinct("month")
    
    return {
        "success": True,
        "data": detailed_data,
        "summary": {
            "total_employees": len(detailed_data),
            "total_gross": round(total_gross, 2),
            "total_deductions": round(total_deductions, 2),
            "total_net": round(total_net, 2),
            "component_totals": {k: round(v, 2) for k, v in component_totals.items()}
        },
        "filters_applied": {
            "month": month,
            "employee_id": employee_id,
            "department": department
        },
        "filter_options": {
            "months": sorted(all_months, reverse=True),
            "departments": sorted(departments)
        }
    }


# ==================== CALCULATION BREAKDOWN ====================

@router.get("/breakdown/{employee_id}/{month}")
async def get_calculation_breakdown(
    employee_id: str,
    month: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get field-level calculation breakdown for an employee.
    Shows input → formula → output for each component.
    """
    db = get_db()
    
    # Check access
    if current_user.role not in HR_ROLES:
        # Employee can only see their own
        emp = await db.employees.find_one({"user_id": current_user.id}, {"_id": 0, "id": 1})
        if not emp or emp["id"] != employee_id:
            raise HTTPException(status_code=403, detail="Access denied")
    
    # Get calculation
    calculation = await db.payroll_calculations.find_one(
        {"employee_id": employee_id, "month": month},
        {"_id": 0}
    )
    
    if not calculation:
        raise HTTPException(status_code=404, detail="Calculation not found")
    
    # Format breakdown table
    breakdown_table = []
    
    # Earnings
    for earning in calculation.get("earnings", []):
        calc = earning.get("calculation", {})
        breakdown_table.append({
            "component": earning.get("name"),
            "type": "Earning",
            "input_values": calc.get("input_values", {}),
            "formula": calc.get("formula_used", ""),
            "output": earning.get("amount"),
            "rule_id": calc.get("rule_id"),
            "version": calc.get("rule_version")
        })
    
    # Deductions
    for deduction in calculation.get("deductions", []):
        calc = deduction.get("calculation", {})
        breakdown_table.append({
            "component": deduction.get("name"),
            "type": "Deduction",
            "input_values": calc.get("input_values", {}),
            "formula": calc.get("formula_used", ""),
            "output": deduction.get("amount"),
            "rule_id": calc.get("rule_id"),
            "version": calc.get("rule_version")
        })
    
    return {
        "employee_id": employee_id,
        "employee_name": calculation.get("employee_name"),
        "month": month,
        "gross_monthly": calculation.get("gross_monthly"),
        "net_payable": calculation.get("net_payable"),
        "breakdown": breakdown_table,
        "full_calculation": calculation
    }


# ==================== APPROVAL WORKFLOW ====================

@router.post("/submit-for-approval")
async def submit_for_approval(
    data: dict,
    current_user: User = Depends(get_current_user)
):
    """
    Submit payroll for approval (HR Manager action).
    Changes status from draft → pending_admin_approval
    """
    if current_user.role not in ["hr_manager"]:
        raise HTTPException(status_code=403, detail="Only HR Manager can submit for approval")
    
    db = get_db()
    month = data.get("month")
    
    register = await db.payroll_register.find_one({"month": month, "status": "draft"})
    if not register:
        raise HTTPException(status_code=404, detail="Draft payroll not found for this month")
    
    # Update status
    await db.payroll_register.update_one(
        {"month": month},
        {
            "$set": {
                "status": "pending_admin_approval",
                "submitted_by": current_user.id,
                "submitted_at": datetime.now(timezone.utc).isoformat()
            },
            "$push": {
                "approval_history": {
                    "action": "submitted",
                    "by": current_user.id,
                    "by_name": current_user.full_name,
                    "at": datetime.now(timezone.utc).isoformat(),
                    "remarks": data.get("remarks", "")
                }
            }
        }
    )
    
    await log_audit(
        action="payroll.submitted",
        entity_type="payroll_register",
        entity_id=str(register.get("id")),
        performed_by=current_user.id,
        metadata={"month": month, "remarks": data.get("remarks", "")}
    )
    
    return {"success": True, "message": "Payroll submitted for admin approval"}


@router.post("/approve")
async def approve_payroll(
    data: dict,
    current_user: User = Depends(get_current_user)
):
    """
    Approve payroll (Admin action).
    Changes status from pending_admin_approval → locked
    """
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only Admin can approve payroll")
    
    db = get_db()
    month = data.get("month")
    
    register = await db.payroll_register.find_one({"month": month, "status": "pending_admin_approval"})
    if not register:
        raise HTTPException(status_code=404, detail="No pending payroll found for this month")
    
    # Lock payroll
    await db.payroll_register.update_one(
        {"month": month},
        {
            "$set": {
                "status": "locked",
                "approved_by": current_user.id,
                "approved_at": datetime.now(timezone.utc).isoformat()
            },
            "$push": {
                "approval_history": {
                    "action": "approved",
                    "by": current_user.id,
                    "by_name": current_user.full_name,
                    "at": datetime.now(timezone.utc).isoformat(),
                    "remarks": data.get("remarks", "")
                }
            }
        }
    )
    
    # Lock all calculations
    await db.payroll_calculations.update_many(
        {"month": month},
        {"$set": {"status": "locked"}}
    )
    
    await log_audit(
        action="payroll.approved",
        entity_type="payroll_register",
        entity_id=str(register.get("id")),
        performed_by=current_user.id,
        metadata={"month": month, "remarks": data.get("remarks", "")}
    )
    
    return {"success": True, "message": "Payroll approved and locked"}


@router.post("/reject")
async def reject_payroll(
    data: dict,
    current_user: User = Depends(get_current_user)
):
    """
    Reject payroll (Admin action).
    Moves back to draft for corrections.
    """
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only Admin can reject payroll")
    
    db = get_db()
    month = data.get("month")
    reason = data.get("reason", "")
    
    if not reason:
        raise HTTPException(status_code=400, detail="Rejection reason is required")
    
    register = await db.payroll_register.find_one({"month": month, "status": "pending_admin_approval"})
    if not register:
        raise HTTPException(status_code=404, detail="No pending payroll found")
    
    await db.payroll_register.update_one(
        {"month": month},
        {
            "$set": {"status": "draft"},
            "$push": {
                "approval_history": {
                    "action": "rejected",
                    "by": current_user.id,
                    "by_name": current_user.full_name,
                    "at": datetime.now(timezone.utc).isoformat(),
                    "reason": reason
                }
            }
        }
    )
    
    return {"success": True, "message": "Payroll rejected and sent back for corrections"}


# ==================== COMPARISON ====================

@router.get("/comparison/{employee_id}/{month}")
async def get_payroll_comparison(
    employee_id: str,
    month: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get before/after comparison for rule changes.
    Compares current month with previous month.
    """
    if current_user.role not in HR_ROLES:
        raise HTTPException(status_code=403, detail="Only HR can view comparison")
    
    db = get_db()
    
    # Get current month calculation
    current = await db.payroll_calculations.find_one(
        {"employee_id": employee_id, "month": month},
        {"_id": 0}
    )
    
    # Get previous month
    year, mon = map(int, month.split('-'))
    if mon == 1:
        prev_month = f"{year-1}-12"
    else:
        prev_month = f"{year}-{mon-1:02d}"
    
    previous = await db.payroll_calculations.find_one(
        {"employee_id": employee_id, "month": prev_month},
        {"_id": 0}
    )
    
    if not current:
        raise HTTPException(status_code=404, detail="Current month calculation not found")
    
    # Build comparison
    comparison = {
        "employee_id": employee_id,
        "employee_name": current.get("employee_name"),
        "current_month": month,
        "previous_month": prev_month,
        "has_previous": previous is not None,
        "changes": []
    }
    
    if previous:
        # Compare key fields
        fields_to_compare = [
            ("gross_monthly", "Gross Salary"),
            ("total_earnings", "Total Earnings"),
            ("total_deductions", "Total Deductions"),
            ("net_payable", "Net Payable")
        ]
        
        for field, label in fields_to_compare:
            curr_val = current.get(field, 0)
            prev_val = previous.get(field, 0)
            diff = curr_val - prev_val
            
            if diff != 0:
                comparison["changes"].append({
                    "field": label,
                    "previous": prev_val,
                    "current": curr_val,
                    "difference": diff,
                    "percentage_change": round((diff / prev_val * 100) if prev_val else 0, 2)
                })
        
        # Compare deductions
        curr_deductions = {d["key"]: d["amount"] for d in current.get("deductions", [])}
        prev_deductions = {d["key"]: d["amount"] for d in previous.get("deductions", [])}
        
        all_deduction_keys = set(curr_deductions.keys()) | set(prev_deductions.keys())
        for key in all_deduction_keys:
            curr_val = curr_deductions.get(key, 0)
            prev_val = prev_deductions.get(key, 0)
            diff = curr_val - prev_val
            
            if diff != 0:
                comparison["changes"].append({
                    "field": f"Deduction: {key}",
                    "previous": prev_val,
                    "current": curr_val,
                    "difference": diff,
                    "percentage_change": round((diff / prev_val * 100) if prev_val else 0, 2)
                })
    
    return comparison


# ==================== EXCEL EXPORT ====================

@router.get("/export/{month}")
async def export_payroll_excel(
    month: str,
    current_user: User = Depends(get_current_user)
):
    """
    Export payroll register as downloadable data.
    Frontend will convert to Excel.
    """
    if current_user.role not in HR_ROLES:
        raise HTTPException(status_code=403, detail="Only HR can export payroll")
    
    db = get_db()
    
    calculations = await db.payroll_calculations.find(
        {"month": month},
        {"_id": 0}
    ).to_list(1000)
    
    if not calculations:
        raise HTTPException(status_code=404, detail="No payroll data found for this month")
    
    # Format for Excel
    export_data = []
    for calc in calculations:
        row = {
            "Employee ID": calc.get("employee_code", ""),
            "Employee Name": calc.get("employee_name", ""),
            "Department": calc.get("department", ""),
            "Designation": calc.get("designation", ""),
            "Gross Salary": calc.get("gross_monthly", 0),
            "Working Days": calc.get("working_days", 0),
            "LOP Days": calc.get("lop_days", 0),
            "Basic Salary": calc.get("basic_monthly", 0),
            "Total Earnings": calc.get("total_earnings", 0),
        }
        
        # Add individual deductions
        for ded in calc.get("deductions", []):
            row[ded.get("name", "Deduction")] = ded.get("amount", 0)
        
        row["Total Deductions"] = calc.get("total_deductions", 0)
        row["Net Salary"] = calc.get("net_salary", 0)
        row["Reimbursements"] = calc.get("reimbursements", 0)
        row["Net Payable"] = calc.get("net_payable", 0)
        
        export_data.append(row)
    
    return {
        "month": month,
        "data": export_data,
        "columns": list(export_data[0].keys()) if export_data else []
    }



# ==================== TEMPLATE DOWNLOAD/UPLOAD ====================

@router.get("/template/download")
async def download_payroll_template(
    month: str,
    current_user: User = Depends(get_current_user)
):
    """
    Download payroll input template with employee data pre-filled.
    Template columns match exactly with upload format.
    """
    if current_user.role not in HR_ROLES:
        raise HTTPException(status_code=403, detail="Only HR can download template")
    
    db = get_db()
    
    # Get all active employees
    employees = await db.employees.find(
        {"is_active": True, "go_live_status": "active"},
        {"_id": 0}
    ).to_list(1000)
    
    # Get existing payroll inputs for this month
    existing_inputs = await db.payroll_inputs.find(
        {"month": month},
        {"_id": 0}
    ).to_list(1000)
    inputs_map = {i["employee_id"]: i for i in existing_inputs}
    
    # Build template data
    template_data = []
    for emp in employees:
        emp_id = emp.get("id")
        existing = inputs_map.get(emp_id, {})
        
        # Fetch attendance summary for the month
        engine = get_payroll_engine(db)
        attendance = await engine.fetch_attendance_summary(emp_id, month)
        
        template_data.append({
            "employee_id": emp.get("employee_id", ""),
            "employee_name": f"{emp.get('first_name', '')} {emp.get('last_name', '')}".strip(),
            "department": emp.get("department", ""),
            "gross_monthly": emp.get("salary", 0) or emp.get("gross_salary", 0),
            "days_in_month": attendance.get("days_in_month", 30),
            "working_days": attendance.get("working_days", 22),
            "present_days": attendance.get("present_days", 0),
            "leave_days": attendance.get("total_leave_days", 0),
            "lop_days": existing.get("lop_days", attendance.get("calculated_lop", 0)),
            "bonus": existing.get("bonus", 0),
            "incentive": existing.get("incentive", 0),
            "overtime_hours": existing.get("overtime_hours", 0),
            "penalty": existing.get("penalty", 0),
            "penalty_reason": existing.get("penalty_reason", ""),
            "advance_recovery": existing.get("advance", 0),
            "reimbursements": existing.get("expense_reimbursement", 0),
            "notes": existing.get("notes", "")
        })
    
    columns = [
        "employee_id", "employee_name", "department", "gross_monthly",
        "days_in_month", "working_days", "present_days", "leave_days",
        "lop_days", "bonus", "incentive", "overtime_hours",
        "penalty", "penalty_reason", "advance_recovery", "reimbursements", "notes"
    ]
    
    return {
        "month": month,
        "template": template_data,
        "columns": columns,
        "instructions": {
            "editable_fields": ["lop_days", "bonus", "incentive", "overtime_hours", "penalty", "penalty_reason", "advance_recovery", "reimbursements", "notes"],
            "readonly_fields": ["employee_id", "employee_name", "department", "gross_monthly", "days_in_month", "working_days", "present_days", "leave_days"],
            "notes": "Edit only the editable fields. Do not change employee_id column."
        }
    }


@router.post("/template/upload-preview")
async def upload_payroll_template_preview(
    month: str,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """
    Upload payroll template and preview changes before applying.
    Returns comparison of old vs new values.
    """
    if current_user.role not in HR_ROLES:
        raise HTTPException(status_code=403, detail="Only HR can upload payroll data")
    
    if not file.filename.endswith(('.xlsx', '.xls', '.csv')):
        raise HTTPException(status_code=400, detail="Only Excel/CSV files allowed")
    
    try:
        contents = await file.read()
        
        if file.filename.endswith('.csv'):
            df = pd.read_csv(io.BytesIO(contents))
        else:
            df = pd.read_excel(io.BytesIO(contents))
        
        # Validate required columns
        required_cols = ['employee_id']
        for col in required_cols:
            if col not in df.columns:
                raise HTTPException(status_code=400, detail=f"Column '{col}' is required")
        
        db = get_db()
        
        # Get existing inputs
        existing_inputs = await db.payroll_inputs.find(
            {"month": month},
            {"_id": 0}
        ).to_list(1000)
        
        # Map by employee_id code (EMP001, etc.)
        emp_code_to_id = {}
        employees = await db.employees.find({"is_active": True}, {"_id": 0, "id": 1, "employee_id": 1}).to_list(1000)
        for emp in employees:
            emp_code_to_id[emp.get("employee_id", "")] = emp.get("id")
        
        existing_map = {i.get("employee_id"): i for i in existing_inputs}
        
        # Build preview with changes
        preview_data = []
        for _, row in df.iterrows():
            emp_code = str(row.get("employee_id", ""))
            emp_id = emp_code_to_id.get(emp_code)
            
            if not emp_id:
                preview_data.append({
                    "employee_id": emp_code,
                    "status": "error",
                    "error": "Employee not found"
                })
                continue
            
            existing = existing_map.get(emp_id, {})
            
            # Build change comparison
            changes = []
            new_values = {}
            
            editable_fields = ["lop_days", "bonus", "incentive", "overtime_hours", "penalty", "penalty_reason", "advance_recovery", "reimbursements", "notes"]
            
            for field in editable_fields:
                if field in df.columns:
                    new_val = row.get(field, 0)
                    if pd.isna(new_val):
                        new_val = 0 if field not in ["penalty_reason", "notes"] else ""
                    
                    old_val = existing.get(field, 0)
                    if field in ["penalty_reason", "notes"]:
                        old_val = existing.get(field, "")
                    
                    if new_val != old_val:
                        changes.append({
                            "field": field,
                            "old_value": old_val,
                            "new_value": new_val
                        })
                    
                    new_values[field] = new_val
            
            preview_data.append({
                "employee_id": emp_code,
                "employee_name": row.get("employee_name", ""),
                "internal_id": emp_id,
                "status": "changed" if changes else "unchanged",
                "changes": changes,
                "new_values": new_values
            })
        
        changed_count = len([p for p in preview_data if p.get("status") == "changed"])
        error_count = len([p for p in preview_data if p.get("status") == "error"])
        
        return {
            "success": True,
            "month": month,
            "total_rows": len(preview_data),
            "changed_count": changed_count,
            "unchanged_count": len(preview_data) - changed_count - error_count,
            "error_count": error_count,
            "preview": preview_data
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error processing file: {str(e)}")


@router.post("/template/apply")
async def apply_payroll_template(
    data: dict,
    current_user: User = Depends(get_current_user)
):
    """
    Apply the uploaded payroll data after preview confirmation.
    Expects the preview data returned from upload-preview endpoint.
    """
    if current_user.role not in HR_ROLES:
        raise HTTPException(status_code=403, detail="Only HR can apply payroll data")
    
    db = get_db()
    month = data.get("month")
    preview_data = data.get("preview", [])
    
    if not month or not preview_data:
        raise HTTPException(status_code=400, detail="Month and preview data required")
    
    updated_count = 0
    errors = []
    
    for item in preview_data:
        if item.get("status") != "changed":
            continue
        
        emp_id = item.get("internal_id")
        new_values = item.get("new_values", {})
        
        if not emp_id:
            errors.append({"employee_id": item.get("employee_id"), "error": "Missing internal ID"})
            continue
        
        try:
            # Prepare payroll input document
            payroll_input = {
                "employee_id": emp_id,
                "month": month,
                "lop_days": float(new_values.get("lop_days", 0) or 0),
                "bonus": float(new_values.get("bonus", 0) or 0),
                "incentive": float(new_values.get("incentive", 0) or 0),
                "overtime_hours": float(new_values.get("overtime_hours", 0) or 0),
                "penalty": float(new_values.get("penalty", 0) or 0),
                "penalty_reason": str(new_values.get("penalty_reason", "") or ""),
                "advance": float(new_values.get("advance_recovery", 0) or 0),
                "expense_reimbursement": float(new_values.get("reimbursements", 0) or 0),
                "notes": str(new_values.get("notes", "") or ""),
                "updated_by": current_user.id,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            
            # Upsert
            await db.payroll_inputs.update_one(
                {"employee_id": emp_id, "month": month},
                {"$set": payroll_input},
                upsert=True
            )
            updated_count += 1
            
        except Exception as e:
            errors.append({"employee_id": item.get("employee_id"), "error": str(e)})
    
    # Audit log
    await log_audit(
        action="payroll.template_applied",
        entity_type="payroll_inputs",
        entity_id=month,
        performed_by=current_user.id,
        metadata={"month": month, "updated_count": updated_count, "errors": len(errors)}
    )
    
    return {
        "success": True,
        "message": f"Applied payroll data for {updated_count} employees",
        "updated_count": updated_count,
        "error_count": len(errors),
        "errors": errors[:10]  # First 10 errors
    }
