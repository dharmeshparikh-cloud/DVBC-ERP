"""
Exit Settlement & Full and Final (F&F) Router

Handles:
- Exit initiation and clearance workflow
- Gratuity calculation
- Leave encashment
- Notice period recovery/payment
- Pending loan/advance recovery
- Final settlement calculation
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta

from .models import User, UserRole
from .deps import get_db, get_current_user
from services.payroll_engine import get_payroll_engine

router = APIRouter(prefix="/exit-settlement", tags=["Exit & F&F"])

HR_ROLES = ["admin", "hr", "hr_manager"]


@router.post("/initiate")
async def initiate_exit(
    data: dict,
    current_user: User = Depends(get_current_user)
):
    """
    Initiate employee exit process.
    
    Input:
    {
        "employee_id": "xxx",
        "exit_type": "resignation" | "termination" | "retirement" | "death",
        "last_working_date": "2026-03-31",
        "notice_period_days": 30,
        "days_served": 15,
        "reason": "Personal reasons"
    }
    """
    if current_user.role not in HR_ROLES:
        raise HTTPException(status_code=403, detail="Only HR can initiate exit")
    
    db = get_db()
    employee_id = data.get("employee_id")
    
    if not employee_id:
        raise HTTPException(status_code=400, detail="employee_id required")
    
    # Fetch employee
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Check if exit already initiated
    existing_exit = await db.exit_settlements.find_one({
        "employee_id": employee_id,
        "status": {"$nin": ["completed", "cancelled"]}
    })
    if existing_exit:
        raise HTTPException(status_code=400, detail="Exit already initiated for this employee")
    
    # Create exit record
    exit_record = {
        "id": f"EXIT-{datetime.now().strftime('%Y%m%d%H%M%S')}-{employee_id[-4:]}",
        "employee_id": employee_id,
        "employee_code": employee.get("employee_id"),
        "employee_name": f"{employee.get('first_name', '')} {employee.get('last_name', '')}",
        "department": employee.get("department"),
        "designation": employee.get("designation"),
        
        "exit_type": data.get("exit_type", "resignation"),
        "resignation_date": data.get("resignation_date", datetime.now().isoformat()),
        "last_working_date": data.get("last_working_date"),
        "notice_period_days": data.get("notice_period_days", 30),
        "days_served": data.get("days_served", 0),
        "reason": data.get("reason", ""),
        
        # Clearance status
        "clearance": {
            "hr": {"status": "pending", "remarks": "", "cleared_by": None, "cleared_at": None},
            "finance": {"status": "pending", "remarks": "", "cleared_by": None, "cleared_at": None},
            "it": {"status": "pending", "remarks": "", "cleared_by": None, "cleared_at": None},
            "admin": {"status": "pending", "remarks": "", "cleared_by": None, "cleared_at": None},
            "manager": {"status": "pending", "remarks": "", "cleared_by": None, "cleared_at": None}
        },
        
        "status": "initiated",
        "initiated_by": current_user.id,
        "initiated_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }
    
    await db.exit_settlements.insert_one(exit_record)
    
    # Remove _id from response
    exit_record.pop("_id", None)
    
    return {
        "success": True,
        "message": "Exit process initiated",
        "exit_record": exit_record
    }


@router.get("/list")
async def list_exits(
    status: Optional[str] = None,
    department: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """List all exit settlements with optional filters."""
    if current_user.role not in HR_ROLES:
        raise HTTPException(status_code=403, detail="Only HR can view exits")
    
    db = get_db()
    query = {}
    if status:
        query["status"] = status
    if department:
        query["department"] = department
    
    exits = await db.exit_settlements.find(query, {"_id": 0}).sort("initiated_at", -1).to_list(100)
    
    return exits


@router.get("/{exit_id}")
async def get_exit_details(
    exit_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get detailed exit settlement information."""
    if current_user.role not in HR_ROLES:
        raise HTTPException(status_code=403, detail="Only HR can view exit details")
    
    db = get_db()
    exit_record = await db.exit_settlements.find_one({"id": exit_id}, {"_id": 0})
    
    if not exit_record:
        raise HTTPException(status_code=404, detail="Exit record not found")
    
    return exit_record


@router.post("/{exit_id}/clearance")
async def update_clearance(
    exit_id: str,
    data: dict,
    current_user: User = Depends(get_current_user)
):
    """
    Update clearance status for a department.
    
    Input:
    {
        "department": "hr" | "finance" | "it" | "admin" | "manager",
        "status": "cleared" | "pending" | "blocked",
        "remarks": "All dues settled"
    }
    """
    db = get_db()
    exit_record = await db.exit_settlements.find_one({"id": exit_id})
    
    if not exit_record:
        raise HTTPException(status_code=404, detail="Exit record not found")
    
    dept = data.get("department")
    if dept not in ["hr", "finance", "it", "admin", "manager"]:
        raise HTTPException(status_code=400, detail="Invalid department")
    
    update_data = {
        f"clearance.{dept}.status": data.get("status", "cleared"),
        f"clearance.{dept}.remarks": data.get("remarks", ""),
        f"clearance.{dept}.cleared_by": current_user.id,
        f"clearance.{dept}.cleared_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }
    
    await db.exit_settlements.update_one({"id": exit_id}, {"$set": update_data})
    
    # Check if all cleared
    updated = await db.exit_settlements.find_one({"id": exit_id}, {"_id": 0})
    all_cleared = all(
        c.get("status") == "cleared" 
        for c in updated.get("clearance", {}).values()
    )
    
    if all_cleared and updated.get("status") == "initiated":
        await db.exit_settlements.update_one(
            {"id": exit_id},
            {"$set": {"status": "clearance_complete"}}
        )
    
    return {
        "success": True,
        "message": f"{dept.upper()} clearance updated",
        "all_cleared": all_cleared
    }


@router.post("/{exit_id}/calculate-settlement")
async def calculate_full_settlement(
    exit_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Calculate Full & Final settlement amount.
    
    Components:
    - Pending salary
    - Gratuity (if eligible)
    - Leave encashment
    - Notice period recovery/payment
    - Pending expense reimbursements
    - Pending loan/advance recovery
    - Any bonus/incentive dues
    """
    if current_user.role not in HR_ROLES:
        raise HTTPException(status_code=403, detail="Only HR can calculate settlement")
    
    db = get_db()
    exit_record = await db.exit_settlements.find_one({"id": exit_id}, {"_id": 0})
    
    if not exit_record:
        raise HTTPException(status_code=404, detail="Exit record not found")
    
    employee_id = exit_record.get("employee_id")
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    engine = get_payroll_engine(db)
    
    # Get employee details
    ctc = employee.get("ctc", 0)
    gross_monthly = ctc / 12
    basic_monthly = gross_monthly * 0.4  # Assuming 40% basic
    da_monthly = 0  # DA if applicable
    
    # Calculate tenure
    joining_date = employee.get("joining_date") or employee.get("date_of_joining")
    if joining_date:
        join_dt = datetime.fromisoformat(joining_date.replace("Z", "+00:00")) if isinstance(joining_date, str) else joining_date
        lwd = datetime.fromisoformat(exit_record.get("last_working_date", datetime.now().isoformat()))
        tenure_delta = lwd - join_dt
        tenure_years = tenure_delta.days / 365.25
        tenure_months = int((tenure_delta.days % 365.25) / 30)
    else:
        tenure_years = 0
        tenure_months = 0
    
    # 1. Gratuity
    gratuity = await engine.calculate_gratuity(
        basic_monthly=basic_monthly,
        da_monthly=da_monthly,
        tenure_years=tenure_years,
        tenure_months=tenure_months
    )
    
    # 2. Leave Encashment
    leave_balance = await db.leave_balances.find_one(
        {"employee_id": employee_id},
        {"_id": 0}
    ) or {"earned": 0, "casual": 0, "sick": 0}
    
    encashment_policy = {
        "encashable_leave_types": ["earned", "privilege", "el", "pl"],
        "max_encashable_days": 300
    }
    
    leave_encashment = await engine.calculate_leave_encashment(
        basic_monthly=basic_monthly,
        leave_balance=leave_balance,
        encashment_policy=encashment_policy
    )
    
    # 3. Notice Period
    notice_period = await engine.calculate_notice_period(
        gross_monthly=gross_monthly,
        notice_period_days=exit_record.get("notice_period_days", 30),
        days_served=exit_record.get("days_served", 0),
        is_employee_resignation=(exit_record.get("exit_type") == "resignation")
    )
    
    # 4. Pending Expenses
    last_month = datetime.now().strftime("%Y-%m")
    expenses = await engine.fetch_approved_expenses(employee_id, last_month)
    
    # 5. Pending Loans/Advances
    pending_loans = await db.employee_loans.find({
        "employee_id": employee_id,
        "status": "active"
    }, {"_id": 0}).to_list(10)
    
    total_loan_recovery = sum(
        loan.get("remaining_amount", 0) 
        for loan in pending_loans
    )
    
    # 6. Pending Salary (last month if not processed)
    pending_salary = 0  # To be calculated based on last payroll
    
    # Calculate totals
    total_payable = (
        gratuity.get("amount", 0) +
        leave_encashment.get("amount", 0) +
        expenses.get("total", 0) +
        pending_salary +
        (notice_period.get("amount", 0) if notice_period.get("type") == "payment" else 0)
    )
    
    total_recovery = (
        total_loan_recovery +
        (notice_period.get("amount", 0) if notice_period.get("type") == "recovery" else 0)
    )
    
    net_settlement = total_payable - total_recovery
    
    settlement_details = {
        "exit_id": exit_id,
        "employee_id": employee_id,
        "employee_name": exit_record.get("employee_name"),
        "employee_code": exit_record.get("employee_code"),
        "department": exit_record.get("department"),
        
        "tenure": {
            "years": round(tenure_years, 2),
            "months": tenure_months,
            "joining_date": str(joining_date) if joining_date else None,
            "last_working_date": exit_record.get("last_working_date")
        },
        
        "salary_details": {
            "ctc_annual": ctc,
            "gross_monthly": round(gross_monthly, 2),
            "basic_monthly": round(basic_monthly, 2)
        },
        
        "payable_components": {
            "gratuity": gratuity,
            "leave_encashment": leave_encashment,
            "expense_reimbursements": expenses,
            "pending_salary": pending_salary,
            "notice_period_payment": notice_period if notice_period.get("type") == "payment" else None
        },
        
        "recovery_components": {
            "notice_period_recovery": notice_period if notice_period.get("type") == "recovery" else None,
            "loan_recovery": {
                "total": total_loan_recovery,
                "loans": pending_loans
            }
        },
        
        "summary": {
            "total_payable": round(total_payable, 2),
            "total_recovery": round(total_recovery, 2),
            "net_settlement": round(net_settlement, 2)
        },
        
        "calculated_at": datetime.now().isoformat(),
        "calculated_by": current_user.id
    }
    
    # Save settlement calculation
    await db.exit_settlements.update_one(
        {"id": exit_id},
        {
            "$set": {
                "settlement_details": settlement_details,
                "status": "settlement_calculated",
                "updated_at": datetime.now().isoformat()
            }
        }
    )
    
    return {
        "success": True,
        "settlement": settlement_details
    }


@router.post("/{exit_id}/approve-settlement")
async def approve_settlement(
    exit_id: str,
    data: dict,
    current_user: User = Depends(get_current_user)
):
    """
    Approve final settlement (Admin only).
    
    Input:
    {
        "approved": true,
        "remarks": "Approved for processing"
    }
    """
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only Admin can approve settlement")
    
    db = get_db()
    exit_record = await db.exit_settlements.find_one({"id": exit_id})
    
    if not exit_record:
        raise HTTPException(status_code=404, detail="Exit record not found")
    
    if exit_record.get("status") != "settlement_calculated":
        raise HTTPException(status_code=400, detail="Settlement must be calculated first")
    
    if data.get("approved"):
        new_status = "approved"
        message = "Settlement approved for processing"
    else:
        new_status = "rejected"
        message = "Settlement rejected"
    
    await db.exit_settlements.update_one(
        {"id": exit_id},
        {
            "$set": {
                "status": new_status,
                "approval": {
                    "approved": data.get("approved", False),
                    "remarks": data.get("remarks", ""),
                    "approved_by": current_user.id,
                    "approved_at": datetime.now().isoformat()
                },
                "updated_at": datetime.now().isoformat()
            }
        }
    )
    
    return {
        "success": True,
        "message": message,
        "status": new_status
    }


@router.post("/{exit_id}/complete")
async def complete_settlement(
    exit_id: str,
    data: dict,
    current_user: User = Depends(get_current_user)
):
    """
    Mark settlement as complete (payment processed).
    
    Input:
    {
        "payment_reference": "NEFT123456",
        "payment_date": "2026-03-31"
    }
    """
    if current_user.role not in HR_ROLES:
        raise HTTPException(status_code=403, detail="Only HR can complete settlement")
    
    db = get_db()
    exit_record = await db.exit_settlements.find_one({"id": exit_id})
    
    if not exit_record:
        raise HTTPException(status_code=404, detail="Exit record not found")
    
    if exit_record.get("status") != "approved":
        raise HTTPException(status_code=400, detail="Settlement must be approved first")
    
    # Update employee status
    await db.employees.update_one(
        {"id": exit_record.get("employee_id")},
        {
            "$set": {
                "status": "inactive",
                "exit_date": exit_record.get("last_working_date"),
                "exit_type": exit_record.get("exit_type")
            }
        }
    )
    
    # Complete settlement
    await db.exit_settlements.update_one(
        {"id": exit_id},
        {
            "$set": {
                "status": "completed",
                "payment": {
                    "reference": data.get("payment_reference"),
                    "date": data.get("payment_date"),
                    "processed_by": current_user.id,
                    "processed_at": datetime.now().isoformat()
                },
                "completed_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
        }
    )
    
    return {
        "success": True,
        "message": "Settlement completed. Employee marked as inactive."
    }


# ==================== LOAN MANAGEMENT ====================

@router.post("/loan/create")
async def create_employee_loan(
    data: dict,
    current_user: User = Depends(get_current_user)
):
    """
    Create employee loan/advance for auto-deduction.
    
    Input:
    {
        "employee_id": "xxx",
        "loan_type": "salary_advance" | "personal_loan" | "emergency",
        "amount": 50000,
        "tenure_months": 3,  // 1-6 months
        "interest_rate": 0,  // 0 for interest-free
        "start_month": "2026-04"  // First deduction month
    }
    """
    if current_user.role not in HR_ROLES:
        raise HTTPException(status_code=403, detail="Only HR can create loans")
    
    db = get_db()
    employee_id = data.get("employee_id")
    tenure_months = data.get("tenure_months", 1)
    
    if tenure_months < 1 or tenure_months > 6:
        raise HTTPException(status_code=400, detail="Tenure must be between 1 and 6 months")
    
    # Fetch employee
    employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Calculate EMI schedule
    engine = get_payroll_engine(db)
    schedule = await engine.calculate_loan_emi_schedule(
        loan_amount=data.get("amount", 0),
        tenure_months=tenure_months,
        interest_rate=data.get("interest_rate", 0)
    )
    
    if schedule.get("error"):
        raise HTTPException(status_code=400, detail=schedule.get("message"))
    
    loan_record = {
        "id": f"LOAN-{datetime.now().strftime('%Y%m%d%H%M%S')}-{employee_id[-4:]}",
        "employee_id": employee_id,
        "employee_code": employee.get("employee_id"),
        "employee_name": f"{employee.get('first_name', '')} {employee.get('last_name', '')}",
        
        "loan_type": data.get("loan_type", "salary_advance"),
        "amount": data.get("amount", 0),
        "tenure_months": tenure_months,
        "interest_rate": data.get("interest_rate", 0),
        "monthly_emi": schedule.get("monthly_emi"),
        "total_payable": schedule.get("total_payable"),
        
        "start_month": data.get("start_month"),
        "emi_schedule": schedule.get("schedule"),
        
        "remaining_amount": data.get("amount", 0),
        "remaining_emis": tenure_months,
        "deductions": [],
        
        "status": "active",
        "created_by": current_user.id,
        "created_at": datetime.now().isoformat()
    }
    
    await db.employee_loans.insert_one(loan_record)
    loan_record.pop("_id", None)
    
    return {
        "success": True,
        "message": f"Loan created. EMI of ₹{schedule.get('monthly_emi'):,.2f} for {tenure_months} months",
        "loan": loan_record
    }


@router.get("/loan/pending/{employee_id}")
async def get_pending_loans(
    employee_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get all pending/active loans for an employee."""
    if current_user.role not in HR_ROLES and current_user.id != employee_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    db = get_db()
    loans = await db.employee_loans.find({
        "employee_id": employee_id,
        "status": "active"
    }, {"_id": 0}).to_list(20)
    
    total_pending = sum(loan.get("remaining_amount", 0) for loan in loans)
    total_monthly_emi = sum(loan.get("monthly_emi", 0) for loan in loans)
    
    return {
        "loans": loans,
        "total_pending": round(total_pending, 2),
        "total_monthly_emi": round(total_monthly_emi, 2)
    }
