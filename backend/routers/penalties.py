"""
Unified Penalties Router - All Policy Violation Penalties

Handles penalties from ALL business rule types:
- Attendance: Late arrivals, unauthorized absences
- Leave: Unauthorized leave, policy violations
- Travel: Policy violations, excess claims
- Expense: Policy violations, fraudulent claims
- General HR: Dress code, code of conduct, etc.

All penalties flow into the payroll engine via the employee_penalties collection.
"""

from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
import uuid

from .models import User
from .deps import get_db, get_role_group, has_role, get_current_user

router = APIRouter(prefix="/penalties", tags=["Penalties"])

# Policy type to penalty category mapping
PENALTY_CATEGORIES = {
    "attendance": {
        "code": "AT",
        "name": "Attendance Penalty",
        "violations": [
            {"code": "AT_LATE", "name": "Late Arrival", "default_amount": 100},
            {"code": "AT_ABSENT", "name": "Unauthorized Absence", "default_amount": 500},
            {"code": "AT_EARLY", "name": "Early Departure", "default_amount": 100},
            {"code": "AT_NO_CHECKIN", "name": "Missing Check-in", "default_amount": 200},
        ]
    },
    "leave": {
        "code": "LV",
        "name": "Leave Policy Penalty",
        "violations": [
            {"code": "LV_UNAUTH", "name": "Unauthorized Leave", "default_amount": 500},
            {"code": "LV_EXCESS", "name": "Excess Leave (Beyond Quota)", "default_amount": 0},  # LOP
            {"code": "LV_NO_NOTICE", "name": "Leave Without Notice", "default_amount": 250},
            {"code": "LV_SANDWICH", "name": "Sandwich Leave Violation", "default_amount": 0},  # LOP applied
        ]
    },
    "travel": {
        "code": "TR",
        "name": "Travel Policy Penalty",
        "violations": [
            {"code": "TR_EXCESS_CLAIM", "name": "Excess Travel Claim", "default_amount": 0},  # Recovery
            {"code": "TR_NO_RECEIPT", "name": "Missing Receipts", "default_amount": 0},  # Claim rejected
            {"code": "TR_POLICY_VIOL", "name": "Travel Policy Violation", "default_amount": 500},
            {"code": "TR_LATE_SETTLE", "name": "Late Settlement", "default_amount": 100},
        ]
    },
    "expense": {
        "code": "EX",
        "name": "Expense Policy Penalty",
        "violations": [
            {"code": "EX_EXCESS", "name": "Excess Expense Claim", "default_amount": 0},  # Recovery
            {"code": "EX_DUPLICATE", "name": "Duplicate Claim", "default_amount": 0},  # Recovery + penalty
            {"code": "EX_FRAUD", "name": "Fraudulent Claim", "default_amount": 1000},
            {"code": "EX_POLICY_VIOL", "name": "Expense Policy Violation", "default_amount": 250},
        ]
    },
    "general": {
        "code": "HR",
        "name": "HR Policy Penalty",
        "violations": [
            {"code": "HR_DRESS", "name": "Dress Code Violation", "default_amount": 100},
            {"code": "HR_CONDUCT", "name": "Code of Conduct Violation", "default_amount": 500},
            {"code": "HR_CONFIDENTIAL", "name": "Confidentiality Breach", "default_amount": 1000},
            {"code": "HR_PROPERTY", "name": "Company Property Misuse", "default_amount": 500},
            {"code": "HR_HARASSMENT", "name": "Workplace Harassment", "default_amount": 2000},
        ]
    }
}


@router.get("/categories")
async def get_penalty_categories(current_user: User = Depends(get_current_user)):
    """Get all penalty categories and violation types for dropdown selection."""
    hr_roles = get_role_group("HR_ROLES", fail_closed=True)
    if not hr_roles or not has_role(current_user.role, hr_roles):
        raise HTTPException(status_code=403, detail="Only HR can view penalty categories")
    
    return {
        "categories": PENALTY_CATEGORIES,
        "total_violation_types": sum(len(cat["violations"]) for cat in PENALTY_CATEGORIES.values())
    }


@router.post("/apply")
async def apply_penalty(data: dict, current_user: User = Depends(get_current_user)):
    """
    Apply a penalty to an employee for any policy violation.
    
    Body: {
        "employee_id": "uuid",
        "month": "2026-03",
        "violation_code": "AT_LATE",  # From PENALTY_CATEGORIES
        "amount": 300,  # Override default if needed
        "description": "3 late arrivals beyond grace",
        "reference_id": "optional_reference",  # e.g., leave request ID, expense claim ID
        "apply_to_payroll": true  # If true, deduct from next payroll
    }
    """
    hr_admin_roles = get_role_group("HR_ADMIN_ROLES", fail_closed=True)
    if not hr_admin_roles or not has_role(current_user.role, hr_admin_roles):
        raise HTTPException(status_code=403, detail="Only HR Manager/Admin can apply penalties")
    
    db = get_db()
    
    employee_id = data.get("employee_id")
    month = data.get("month")
    violation_code = data.get("violation_code")
    custom_amount = data.get("amount")
    description = data.get("description", "")
    reference_id = data.get("reference_id")
    apply_to_payroll = data.get("apply_to_payroll", True)
    
    if not employee_id or not month or not violation_code:
        raise HTTPException(status_code=400, detail="employee_id, month, and violation_code required")
    
    # Validate employee
    employee = await db.employees.find_one(
        {"id": employee_id},
        {"_id": 0, "employee_id": 1, "first_name": 1, "last_name": 1, "department": 1}
    )
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Find violation type
    violation_info = None
    category_info = None
    for cat_key, cat_data in PENALTY_CATEGORIES.items():
        for viol in cat_data["violations"]:
            if viol["code"] == violation_code:
                violation_info = viol
                category_info = {"key": cat_key, **cat_data}
                break
        if violation_info:
            break
    
    if not violation_info:
        raise HTTPException(status_code=400, detail=f"Invalid violation_code: {violation_code}")
    
    # Determine penalty amount
    penalty_amount = custom_amount if custom_amount is not None else violation_info["default_amount"]
    
    now = datetime.now(timezone.utc).isoformat()
    
    # === ARREARS LOGIC: Check payroll status for the target month ===
    is_arrears = False
    original_month = month
    effective_month = month
    arrears_reason = None
    
    payroll_register = await db.payroll_register.find_one(
        {"month": month, "status": {"$in": ["locked", "pending_admin_approval"]}},
        {"_id": 0, "status": 1, "month": 1}
    )
    
    if payroll_register:
        is_arrears = True
        payroll_status = payroll_register.get("status", "unknown")
        arrears_reason = f"Payroll for {month} is {payroll_status}"
        
        # Find next unlocked month
        year, mon = map(int, month.split('-'))
        for offset in range(1, 13):  # Look up to 12 months ahead
            next_mon = mon + offset
            next_year = year + (next_mon - 1) // 12
            next_mon = ((next_mon - 1) % 12) + 1
            candidate = f"{next_year}-{next_mon:02d}"
            
            locked_register = await db.payroll_register.find_one(
                {"month": candidate, "status": {"$in": ["locked", "pending_admin_approval"]}},
                {"_id": 0}
            )
            if not locked_register:
                effective_month = candidate
                break
    
    # Check for existing penalty (idempotency)
    existing = await db.employee_penalties.find_one({
        "employee_id": employee_id,
        "month": month,
        "violation_code": violation_code,
        "reference_id": reference_id
    })
    
    if existing:
        # Update existing
        await db.employee_penalties.update_one(
            {"id": existing["id"]},
            {"$set": {
                "amount": penalty_amount,
                "description": description,
                "updated_at": now,
                "updated_by": current_user.id,
                "updated_by_name": current_user.full_name
            }}
        )
        return {
            "message": "Penalty updated",
            "penalty_id": existing["id"],
            "action": "updated"
        }
    
    # Create new penalty
    penalty_id = str(uuid.uuid4())
    penalty_record = {
        "id": penalty_id,
        "employee_id": employee_id,
        "employee_code": employee.get("employee_id"),
        "employee_name": f"{employee.get('first_name', '')} {employee.get('last_name', '')}".strip(),
        "department": employee.get("department"),
        "month": month,
        "original_month": original_month,
        "effective_month": effective_month,
        "is_arrears": is_arrears,
        "arrears_reason": arrears_reason,
        "category": category_info["key"],
        "category_name": category_info["name"],
        "violation_code": violation_code,
        "violation_name": violation_info["name"],
        "rule_id": violation_code,
        "name": violation_info["name"],
        "amount": penalty_amount,
        "reason": description,
        "description": description,
        "reference_id": reference_id,
        "apply_to_payroll": apply_to_payroll,
        "status": "active",
        "created_at": now,
        "created_by": current_user.id,
        "created_by_name": current_user.full_name
    }
    
    await db.employee_penalties.insert_one(penalty_record)
    
    # Audit log
    await db.audit_logs.insert_one({
        "id": str(uuid.uuid4()),
        "action": "penalty_applied",
        "entity_type": "employee_penalty",
        "entity_id": penalty_id,
        "user_id": current_user.id,
        "user_name": current_user.full_name,
        "details": {
            "employee_id": employee_id,
            "month": month,
            "violation": violation_info["name"],
            "amount": penalty_amount,
            "is_arrears": is_arrears,
            "effective_month": effective_month
        },
        "created_at": now
    })
    
    if is_arrears:
        return {
            "message": f"Penalty applied as ARREARS: {violation_info['name']} - INR {penalty_amount}. "
                       f"Payroll for {month} is already {payroll_register.get('status')}. "
                       f"Will be deducted in {effective_month} payroll.",
            "penalty_id": penalty_id,
            "action": "created_as_arrears",
            "is_arrears": True,
            "original_month": original_month,
            "effective_month": effective_month,
            "arrears_reason": arrears_reason
        }
    
    return {
        "message": f"Penalty applied: {violation_info['name']} - INR {penalty_amount}",
        "penalty_id": penalty_id,
        "action": "created",
        "is_arrears": False,
        "effective_month": month
    }


@router.get("/employee/{employee_id}")
async def get_employee_penalties(
    employee_id: str,
    month: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get all penalties for an employee, optionally filtered by month."""
    db = get_db()
    
    query = {"employee_id": employee_id, "status": "active"}
    if month:
        query["month"] = month
    
    penalties = await db.employee_penalties.find(
        query,
        {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    
    # Also get attendance penalties
    att_query = {"employee_id": employee_id}
    if month:
        att_query["month"] = month
    
    att_penalties = await db.attendance_penalties.find(
        att_query,
        {"_id": 0}
    ).sort("created_at", -1).to_list(50)
    
    return {
        "policy_penalties": penalties,
        "attendance_penalties": att_penalties,
        "total_policy_amount": sum(p.get("amount", 0) for p in penalties),
        "total_attendance_amount": sum(p.get("penalty_amount", 0) for p in att_penalties),
        "grand_total": sum(p.get("amount", 0) for p in penalties) + sum(p.get("penalty_amount", 0) for p in att_penalties)
    }


@router.get("/month/{month}")
async def get_month_penalties(month: str, current_user: User = Depends(get_current_user)):
    """Get all penalties for a month (for HR review). Includes arrears carried into this month."""
    hr_roles = get_role_group("HR_ROLES", fail_closed=True)
    if not hr_roles or not has_role(current_user.role, hr_roles):
        raise HTTPException(status_code=403, detail="Only HR can view monthly penalties")
    
    db = get_db()
    
    # Direct penalties for this month
    policy_penalties = await db.employee_penalties.find(
        {"month": month, "status": "active"},
        {"_id": 0}
    ).to_list(500)
    
    # Arrears carried into this month (original_month != month but effective_month == month)
    arrears_penalties = await db.employee_penalties.find(
        {"effective_month": month, "is_arrears": True, "status": "active", "month": {"$ne": month}},
        {"_id": 0}
    ).to_list(200)
    
    # Attendance penalties
    att_penalties = await db.attendance_penalties.find(
        {"month": month},
        {"_id": 0}
    ).to_list(500)
    
    # Group by category
    by_category = {}
    all_policy = policy_penalties + arrears_penalties
    for p in all_policy:
        cat = p.get("category", "general")
        if cat not in by_category:
            by_category[cat] = {"count": 0, "total_amount": 0, "penalties": []}
        by_category[cat]["count"] += 1
        by_category[cat]["total_amount"] += p.get("amount", 0)
        by_category[cat]["penalties"].append(p)
    
    # Add attendance as separate category
    if att_penalties:
        by_category["attendance_late"] = {
            "count": len(att_penalties),
            "total_amount": sum(p.get("penalty_amount", 0) for p in att_penalties),
            "penalties": att_penalties
        }
    
    # Check payroll lock status for this month
    payroll_reg = await db.payroll_register.find_one(
        {"month": month, "status": {"$in": ["locked", "pending_admin_approval"]}},
        {"_id": 0, "status": 1}
    )
    
    return {
        "month": month,
        "by_category": by_category,
        "total_penalties": len(all_policy) + len(att_penalties),
        "total_amount": sum(p.get("amount", 0) for p in all_policy) + sum(p.get("penalty_amount", 0) for p in att_penalties),
        "employees_affected": len(set(p.get("employee_id") for p in all_policy + att_penalties)),
        "arrears_count": len(arrears_penalties),
        "arrears_amount": sum(p.get("amount", 0) for p in arrears_penalties),
        "payroll_status": payroll_reg.get("status") if payroll_reg else "open"
    }


@router.delete("/{penalty_id}")
async def revoke_penalty(penalty_id: str, current_user: User = Depends(get_current_user)):
    """Revoke/cancel a penalty."""
    hr_admin_roles = get_role_group("HR_ADMIN_ROLES", fail_closed=True)
    if not hr_admin_roles or not has_role(current_user.role, hr_admin_roles):
        raise HTTPException(status_code=403, detail="Only HR Manager/Admin can revoke penalties")
    
    db = get_db()
    
    result = await db.employee_penalties.update_one(
        {"id": penalty_id},
        {"$set": {
            "status": "revoked",
            "revoked_at": datetime.now(timezone.utc).isoformat(),
            "revoked_by": current_user.id,
            "revoked_by_name": current_user.full_name
        }}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Penalty not found")
    
    return {"message": "Penalty revoked successfully"}


@router.get("/summary")
async def get_penalty_summary(
    months: int = 6,
    current_user: User = Depends(get_current_user)
):
    """
    Get comprehensive penalty summary across all categories.
    Used by Penalty Dashboard in Payroll Engine.
    """
    hr_roles = get_role_group("HR_ROLES", fail_closed=True)
    if not hr_roles or not has_role(current_user.role, hr_roles):
        raise HTTPException(status_code=403, detail="Only HR can view penalty summary")
    
    db = get_db()
    
    # Calculate month list
    now = datetime.now(timezone.utc)
    month_list = []
    for i in range(months):
        month_date = now - timedelta(days=i*30)
        month_str = month_date.strftime("%Y-%m")
        if month_str not in month_list:
            month_list.append(month_str)
    
    # Get all penalties
    policy_penalties = await db.employee_penalties.find(
        {"month": {"$in": month_list}, "status": "active"},
        {"_id": 0}
    ).to_list(2000)
    
    att_penalties = await db.attendance_penalties.find(
        {"month": {"$in": month_list}},
        {"_id": 0}
    ).to_list(1000)
    
    # Summary by category
    category_summary = {}
    for cat_key, cat_data in PENALTY_CATEGORIES.items():
        cat_penalties = [p for p in policy_penalties if p.get("category") == cat_key]
        category_summary[cat_key] = {
            "name": cat_data["name"],
            "total_count": len(cat_penalties),
            "total_amount": sum(p.get("amount", 0) for p in cat_penalties),
            "unique_employees": len(set(p.get("employee_id") for p in cat_penalties))
        }
    
    # Add attendance late
    category_summary["attendance_late"] = {
        "name": "Late Arrival (Attendance)",
        "total_count": len(att_penalties),
        "total_amount": sum(p.get("penalty_amount", 0) for p in att_penalties),
        "unique_employees": len(set(p.get("employee_id") for p in att_penalties))
    }
    
    # Monthly breakdown
    monthly_breakdown = {}
    for m in month_list:
        m_policy = [p for p in policy_penalties if p.get("month") == m]
        m_att = [p for p in att_penalties if p.get("month") == m]
        monthly_breakdown[m] = {
            "policy_penalties": sum(p.get("amount", 0) for p in m_policy),
            "attendance_penalties": sum(p.get("penalty_amount", 0) for p in m_att),
            "total": sum(p.get("amount", 0) for p in m_policy) + sum(p.get("penalty_amount", 0) for p in m_att),
            "employees_affected": len(set(p.get("employee_id") for p in m_policy + m_att))
        }
    
    return {
        "by_category": category_summary,
        "monthly_breakdown": monthly_breakdown,
        "grand_total": sum(p.get("amount", 0) for p in policy_penalties) + sum(p.get("penalty_amount", 0) for p in att_penalties),
        "total_employees_penalized": len(set(
            p.get("employee_id") for p in policy_penalties + att_penalties
        )),
        "months_analyzed": months
    }


@router.post("/auto-detect/{month}")
async def auto_detect_violations(month: str, current_user: User = Depends(get_current_user)):
    """
    Auto-detect policy violations for a month that may require penalties.
    Returns a list of potential violations for HR to review and approve.
    
    Checks:
    - Leave policy violations (sandwich, excess)
    - Expense policy violations (over limit, duplicates)
    - Travel policy violations (excess claims)
    """
    hr_admin_roles = get_role_group("HR_ADMIN_ROLES", fail_closed=True)
    if not hr_admin_roles or not has_role(current_user.role, hr_admin_roles):
        raise HTTPException(status_code=403, detail="Only HR Manager/Admin can run auto-detection")
    
    db = get_db()
    detected_violations = []
    
    # === 1. Leave Violations ===
    # Get leave requests for the month that might have violations
    leave_requests = await db.leave_requests.find({
        "$or": [
            {"start_date": {"$regex": f"^{month}"}},
            {"end_date": {"$regex": f"^{month}"}}
        ],
        "status": "approved"
    }, {"_id": 0}).to_list(500)
    
    # Get leave policy
    leave_policy = await db.business_policies.find_one(
        {"policy_type": "leave", "is_active": True},
        {"_id": 0}
    )
    leave_rules = {r["rule_id"]: r for r in leave_policy.get("rules", [])} if leave_policy else {}
    
    # Check for sandwich leave violations
    sandwich_enabled = leave_rules.get("LV010", {}).get("is_enabled", True)
    if sandwich_enabled:
        for lr in leave_requests:
            # Simplified check - in production, would check actual calendar
            if lr.get("sandwich_detected"):
                detected_violations.append({
                    "employee_id": lr.get("employee_id"),
                    "violation_code": "LV_SANDWICH",
                    "description": f"Sandwich leave detected for {lr.get('start_date')} to {lr.get('end_date')}",
                    "reference_id": lr.get("id"),
                    "suggested_action": "Apply LOP for weekend days"
                })
    
    # === 2. Expense Violations ===
    expense_policy = await db.business_policies.find_one(
        {"policy_type": "expense", "is_active": True},
        {"_id": 0}
    )
    exp_rules = {r["rule_id"]: r for r in expense_policy.get("rules", [])} if expense_policy else {}
    
    max_single = exp_rules.get("EX004", {}).get("numeric_value", 10000)
    monthly_cap = exp_rules.get("EX005", {}).get("numeric_value", 50000)
    
    # Get expenses for month
    expenses = await db.expenses.find({
        "expense_date": {"$regex": f"^{month}"},
        "status": "approved"
    }, {"_id": 0}).to_list(1000)
    
    # Check single expense limit
    for exp in expenses:
        if exp.get("amount", 0) > max_single:
            detected_violations.append({
                "employee_id": exp.get("employee_id"),
                "violation_code": "EX_EXCESS",
                "description": f"Single expense ₹{exp.get('amount'):,.0f} exceeds limit ₹{max_single:,.0f}",
                "reference_id": exp.get("id"),
                "suggested_action": f"Recover excess amount: ₹{exp.get('amount', 0) - max_single:,.0f}"
            })
    
    # Check monthly cap per employee
    emp_totals = {}
    for exp in expenses:
        emp_id = exp.get("employee_id")
        emp_totals[emp_id] = emp_totals.get(emp_id, 0) + exp.get("amount", 0)
    
    for emp_id, total in emp_totals.items():
        if total > monthly_cap:
            detected_violations.append({
                "employee_id": emp_id,
                "violation_code": "EX_POLICY_VIOL",
                "description": f"Monthly expenses ₹{total:,.0f} exceed cap ₹{monthly_cap:,.0f}",
                "reference_id": None,
                "suggested_action": f"Review expenses, recover excess: ₹{total - monthly_cap:,.0f}"
            })
    
    # Get employee details for violations
    emp_ids = list(set(v["employee_id"] for v in detected_violations))
    employees = await db.employees.find(
        {"id": {"$in": emp_ids}},
        {"_id": 0, "id": 1, "employee_id": 1, "first_name": 1, "last_name": 1, "department": 1}
    ).to_list(100)
    emp_map = {e["id"]: e for e in employees}
    
    # Enrich violations with employee info
    for v in detected_violations:
        emp = emp_map.get(v["employee_id"], {})
        v["employee_code"] = emp.get("employee_id", "-")
        v["employee_name"] = f"{emp.get('first_name', '')} {emp.get('last_name', '')}".strip()
        v["department"] = emp.get("department", "-")
    
    return {
        "month": month,
        "detected_violations": detected_violations,
        "total_detected": len(detected_violations),
        "note": "Review violations and use POST /api/penalties/apply to confirm penalties"
    }
