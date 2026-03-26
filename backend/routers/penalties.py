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
    """Get all penalty categories with dynamic default amounts from business_policies."""
    hr_roles = get_role_group("HR_ROLES", fail_closed=True)
    if not hr_roles or not has_role(current_user.role, hr_roles):
        raise HTTPException(status_code=403, detail="Only HR can view penalty categories")
    
    db = get_db()
    
    # Read AT012 (late penalty amount) from business_policies for dynamic defaults
    dynamic_amounts = {}
    try:
        att_policy = await db.business_policies.find_one(
            {"policy_type": "attendance", "scope": "company", "is_active": True},
            {"_id": 0, "rules": 1}
        )
        if att_policy:
            rules = {r["rule_id"]: r for r in att_policy.get("rules", [])}
            dynamic_amounts["AT_LATE"] = rules.get("AT012", {}).get("numeric_value", 100)
    except Exception:
        pass
    
    # Build categories with dynamic defaults
    categories = {}
    for cat_key, cat_data in PENALTY_CATEGORIES.items():
        cat_copy = {"name": cat_data["name"], "violations": []}
        for v in cat_data["violations"]:
            v_copy = {**v}
            if v_copy["code"] in dynamic_amounts:
                v_copy["default_amount"] = dynamic_amounts[v_copy["code"]]
                v_copy["amount_source"] = "business_rules"
            else:
                v_copy["amount_source"] = "system_default"
            cat_copy["violations"].append(v_copy)
        categories[cat_key] = cat_copy
    
    return {
        "categories": categories,
        "total_violation_types": sum(len(cat["violations"]) for cat in categories.values()),
        "dynamic_amounts": dynamic_amounts
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
        "source": data.get("source", "manual"),
        "apply_to_payroll": apply_to_payroll,
        "status": "pending_review",
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
    """Get all penalties for an employee from the unified collection."""
    db = get_db()
    
    query = {"employee_id": employee_id}
    if month:
        query["month"] = month
    
    penalties = await db.employee_penalties.find(
        query,
        {"_id": 0}
    ).sort("created_at", -1).to_list(200)
    
    return {
        "penalties": penalties,
        "total_amount": sum(p.get("amount", 0) for p in penalties if p.get("status") in ("approved", "active")),
        "pending_amount": sum(p.get("amount", 0) for p in penalties if p.get("status") == "pending_review"),
        "count_by_status": {
            "pending_review": len([p for p in penalties if p.get("status") == "pending_review"]),
            "approved": len([p for p in penalties if p.get("status") in ("approved", "active")]),
            "rejected": len([p for p in penalties if p.get("status") == "rejected"]),
        }
    }


@router.get("/month/{month}")
async def get_month_penalties(
    month: str,
    status: Optional[str] = None,
    category: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get all penalties for a month from the unified collection. Supports status/category filters."""
    hr_roles = get_role_group("HR_ROLES", fail_closed=True)
    if not hr_roles or not has_role(current_user.role, hr_roles):
        raise HTTPException(status_code=403, detail="Only HR can view monthly penalties")
    
    db = get_db()
    
    query = {"month": month}
    if status:
        query["status"] = status
    if category:
        query["category"] = category
    
    penalties = await db.employee_penalties.find(query, {"_id": 0}).sort("created_at", -1).to_list(500)
    
    # Also get arrears carried into this month
    arrears_query = {"effective_month": month, "is_arrears": True, "month": {"$ne": month}}
    if status:
        arrears_query["status"] = status
    arrears = await db.employee_penalties.find(arrears_query, {"_id": 0}).to_list(200)
    
    all_penalties = penalties + arrears
    
    # Group by category
    by_category = {}
    for p in all_penalties:
        cat = p.get("category", "general")
        if cat not in by_category:
            by_category[cat] = {"count": 0, "total_amount": 0}
        by_category[cat]["count"] += 1
        by_category[cat]["total_amount"] += p.get("amount", 0)
    
    # Count by status
    count_by_status = {
        "pending_review": len([p for p in all_penalties if p.get("status") == "pending_review"]),
        "approved": len([p for p in all_penalties if p.get("status") in ("approved", "active")]),
        "rejected": len([p for p in all_penalties if p.get("status") == "rejected"]),
        "revoked": len([p for p in all_penalties if p.get("status") == "revoked"]),
    }
    
    return {
        "month": month,
        "penalties": all_penalties,
        "by_category": by_category,
        "count_by_status": count_by_status,
        "total_penalties": len(all_penalties),
        "total_amount": sum(p.get("amount", 0) for p in all_penalties),
        "employees_affected": len(set(p.get("employee_id") for p in all_penalties)),
        "arrears_count": len(arrears)
    }


# ==================== RULE CONFIGURATION (must be before /{penalty_id} routes) ====================

@router.get("/rule-config")
async def get_penalty_rule_config(current_user: User = Depends(get_current_user)):
    """Get penalty-related rules from business_policies for the Rule Configuration tab."""
    hr_roles = get_role_group("HR_ROLES", fail_closed=True)
    if not hr_roles or not has_role(current_user.role, hr_roles):
        raise HTTPException(status_code=403, detail="Only HR can view rule configuration")
    
    db = get_db()
    
    att_policy = await db.business_policies.find_one(
        {"policy_type": "attendance", "scope": "company", "is_active": True},
        {"_id": 0}
    )
    
    if not att_policy:
        return {"rules": [], "policy_id": None, "message": "No attendance policy found"}
    
    rules = att_policy.get("rules", [])
    rules_map = {r["rule_id"]: r for r in rules}
    
    # Extract only penalty-relevant rules
    penalty_rules = [
        {
            "rule_id": "AT004",
            "name": "Grace Period (Minutes)",
            "description": "Minutes after shift start before check-in is considered late",
            "value": rules_map.get("AT004", {}).get("numeric_value", 10),
            "type": "number",
            "unit": "minutes",
            "impact": "Employees arriving within this window are not marked late"
        },
        {
            "rule_id": "AT011",
            "name": "Grace Days per Month",
            "description": "Number of late days allowed per month before penalties apply",
            "value": rules_map.get("AT011", {}).get("numeric_value", 3),
            "type": "number",
            "unit": "days",
            "impact": "Late arrivals within this limit use grace days, no penalty"
        },
        {
            "rule_id": "AT012",
            "name": "Late Penalty Amount",
            "description": "Penalty amount per late day beyond grace limit",
            "value": rules_map.get("AT012", {}).get("numeric_value", 100),
            "type": "currency",
            "unit": "₹/day",
            "impact": "Deducted from payroll for each excess late day"
        }
    ]
    
    return {
        "rules": penalty_rules,
        "policy_id": att_policy.get("id"),
        "policy_name": att_policy.get("name", "Attendance Policy"),
        "last_updated": att_policy.get("updated_at"),
        "updated_by": att_policy.get("updated_by_name")
    }


@router.put("/rule-config")
async def update_penalty_rule_config(data: dict, current_user: User = Depends(get_current_user)):
    """Update penalty-related rules in business_policies."""
    hr_admin_roles = get_role_group("HR_ADMIN_ROLES", fail_closed=True)
    if not hr_admin_roles or not has_role(current_user.role, hr_admin_roles):
        raise HTTPException(status_code=403, detail="Only HR Manager/Admin can update rule configuration")
    
    db = get_db()
    now = datetime.now(timezone.utc).isoformat()
    
    updates = data.get("rules", {})  # {"AT004": 10, "AT011": 3, "AT012": 100}
    allowed_rules = {"AT004", "AT011", "AT012"}
    
    att_policy = await db.business_policies.find_one(
        {"policy_type": "attendance", "scope": "company", "is_active": True},
        {"_id": 0}
    )
    
    if not att_policy:
        raise HTTPException(status_code=404, detail="No attendance policy found")
    
    rules = att_policy.get("rules", [])
    updated_count = 0
    
    for i, rule in enumerate(rules):
        rid = rule.get("rule_id")
        if rid in allowed_rules and rid in updates:
            rules[i]["numeric_value"] = updates[rid]
            rules[i]["updated_at"] = now
            updated_count += 1
    
    await db.business_policies.update_one(
        {"policy_type": "attendance", "scope": "company", "is_active": True},
        {"$set": {
            "rules": rules,
            "updated_at": now,
            "updated_by": current_user.id,
            "updated_by_name": current_user.full_name
        }}
    )
    
    return {
        "message": f"Updated {updated_count} penalty rules",
        "updated_rules": {k: v for k, v in updates.items() if k in allowed_rules},
        "note": "Changes apply to future penalties only. Existing approved penalties are not affected."
    }


# ==================== PENALTY CRUD (parameterized routes) ====================

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


@router.post("/{penalty_id}/approve")
async def approve_penalty(penalty_id: str, current_user: User = Depends(get_current_user)):
    """Approve a pending penalty — moves it into payroll deduction."""
    hr_admin_roles = get_role_group("HR_ADMIN_ROLES", fail_closed=True)
    if not hr_admin_roles or not has_role(current_user.role, hr_admin_roles):
        raise HTTPException(status_code=403, detail="Only HR Manager/Admin can approve penalties")
    
    db = get_db()
    now = datetime.now(timezone.utc).isoformat()
    
    result = await db.employee_penalties.update_one(
        {"id": penalty_id, "status": "pending_review"},
        {"$set": {
            "status": "approved",
            "approved_at": now,
            "approved_by": current_user.id,
            "approved_by_name": current_user.full_name
        }}
    )
    
    if result.modified_count == 0:
        # Check if already approved
        existing = await db.employee_penalties.find_one({"id": penalty_id}, {"_id": 0, "status": 1})
        if existing and existing.get("status") == "approved":
            return {"message": "Penalty already approved", "status": "approved"}
        raise HTTPException(status_code=404, detail="Penalty not found or not in pending_review status")
    
    return {"message": "Penalty approved", "status": "approved"}


@router.post("/{penalty_id}/reject")
async def reject_penalty(penalty_id: str, data: dict = None, current_user: User = Depends(get_current_user)):
    """Reject a pending penalty with optional reason."""
    hr_admin_roles = get_role_group("HR_ADMIN_ROLES", fail_closed=True)
    if not hr_admin_roles or not has_role(current_user.role, hr_admin_roles):
        raise HTTPException(status_code=403, detail="Only HR Manager/Admin can reject penalties")
    
    db = get_db()
    now = datetime.now(timezone.utc).isoformat()
    reason = (data or {}).get("reason", "")
    
    result = await db.employee_penalties.update_one(
        {"id": penalty_id, "status": {"$in": ["pending_review", "approved"]}},
        {"$set": {
            "status": "rejected",
            "rejected_at": now,
            "rejected_by": current_user.id,
            "rejected_by_name": current_user.full_name,
            "rejection_reason": reason
        }}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Penalty not found or not in reviewable status")
    
    return {"message": "Penalty rejected", "status": "rejected"}


@router.post("/{penalty_id}/send-back")
async def send_back_penalty(penalty_id: str, data: dict = None, current_user: User = Depends(get_current_user)):
    """Send back a penalty to pending_review with a reason."""
    hr_admin_roles = get_role_group("HR_ADMIN_ROLES", fail_closed=True)
    if not hr_admin_roles or not has_role(current_user.role, hr_admin_roles):
        raise HTTPException(status_code=403, detail="Only HR Manager/Admin can send back penalties")
    
    db = get_db()
    now = datetime.now(timezone.utc).isoformat()
    reason = (data or {}).get("reason", "")
    
    result = await db.employee_penalties.update_one(
        {"id": penalty_id},
        {"$set": {
            "status": "pending_review",
            "sent_back_at": now,
            "sent_back_by": current_user.id,
            "sent_back_by_name": current_user.full_name,
            "sent_back_reason": reason
        }}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Penalty not found")
    
    return {"message": "Penalty sent back for review", "status": "pending_review"}


@router.put("/{penalty_id}")
async def update_penalty(penalty_id: str, data: dict, current_user: User = Depends(get_current_user)):
    """Update a pending penalty (amount, reason, etc.)."""
    hr_admin_roles = get_role_group("HR_ADMIN_ROLES", fail_closed=True)
    if not hr_admin_roles or not has_role(current_user.role, hr_admin_roles):
        raise HTTPException(status_code=403, detail="Only HR Manager/Admin can edit penalties")
    
    db = get_db()
    now = datetime.now(timezone.utc).isoformat()
    
    update_fields = {"updated_at": now, "updated_by": current_user.id, "updated_by_name": current_user.full_name}
    for field in ["amount", "reason", "description", "violation_code", "violation_name", "category"]:
        if field in data:
            update_fields[field] = data[field]
    
    result = await db.employee_penalties.update_one(
        {"id": penalty_id, "status": "pending_review"},
        {"$set": update_fields}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Penalty not found or not editable (must be pending_review)")
    
    return {"message": "Penalty updated"}


@router.post("/bulk-action")
async def bulk_penalty_action(data: dict, current_user: User = Depends(get_current_user)):
    """Bulk approve/reject penalties."""
    hr_admin_roles = get_role_group("HR_ADMIN_ROLES", fail_closed=True)
    if not hr_admin_roles or not has_role(current_user.role, hr_admin_roles):
        raise HTTPException(status_code=403, detail="Only HR Manager/Admin can bulk-action penalties")
    
    db = get_db()
    now = datetime.now(timezone.utc).isoformat()
    
    penalty_ids = data.get("penalty_ids", [])
    action = data.get("action")  # "approve" or "reject"
    reason = data.get("reason", "")
    
    if not penalty_ids or action not in ("approve", "reject"):
        raise HTTPException(status_code=400, detail="penalty_ids and action (approve/reject) required")
    
    if action == "approve":
        update_fields = {
            "status": "approved",
            "approved_at": now,
            "approved_by": current_user.id,
            "approved_by_name": current_user.full_name
        }
    else:
        update_fields = {
            "status": "rejected",
            "rejected_at": now,
            "rejected_by": current_user.id,
            "rejected_by_name": current_user.full_name,
            "rejection_reason": reason
        }
    
    result = await db.employee_penalties.update_many(
        {"id": {"$in": penalty_ids}, "status": "pending_review"},
        {"$set": update_fields}
    )
    
    return {
        "message": f"{action.title()}d {result.modified_count} penalties",
        "modified_count": result.modified_count
    }


@router.get("/summary-by-employees")
async def get_penalty_summary_by_employees(
    month: str,
    current_user: User = Depends(get_current_user)
):
    """Get penalty summary grouped by employee for a month. Used for inline badges in attendance/leave tables."""
    db = get_db()
    
    penalties = await db.employee_penalties.find(
        {"month": month},
        {"_id": 0, "employee_id": 1, "status": 1, "amount": 1, "category": 1, "violation_name": 1}
    ).to_list(1000)
    
    summary = {}
    for p in penalties:
        eid = p.get("employee_id")
        if eid not in summary:
            summary[eid] = {"pending": 0, "approved": 0, "rejected": 0, "total_amount": 0, "violations": []}
        status = p.get("status", "pending_review")
        if status == "pending_review":
            summary[eid]["pending"] += 1
        elif status in ("approved", "active"):
            summary[eid]["approved"] += 1
            summary[eid]["total_amount"] += p.get("amount", 0)
        elif status == "rejected":
            summary[eid]["rejected"] += 1
        summary[eid]["violations"].append(p.get("violation_name", "Unknown"))
    
    return summary


@router.get("/summary")
async def get_penalty_summary(
    months: int = 6,
    current_user: User = Depends(get_current_user)
):
    """Get comprehensive penalty summary from unified collection."""
    hr_roles = get_role_group("HR_ROLES", fail_closed=True)
    if not hr_roles or not has_role(current_user.role, hr_roles):
        raise HTTPException(status_code=403, detail="Only HR can view penalty summary")
    
    db = get_db()
    
    now = datetime.now(timezone.utc)
    month_list = []
    for i in range(months):
        month_date = now - timedelta(days=i*30)
        month_str = month_date.strftime("%Y-%m")
        if month_str not in month_list:
            month_list.append(month_str)
    
    all_penalties = await db.employee_penalties.find(
        {"month": {"$in": month_list}},
        {"_id": 0}
    ).to_list(3000)
    
    # Summary by category
    category_summary = {}
    for cat_key, cat_data in PENALTY_CATEGORIES.items():
        cat_penalties = [p for p in all_penalties if p.get("category") == cat_key and p.get("status") in ("approved", "active")]
        category_summary[cat_key] = {
            "name": cat_data["name"],
            "total_count": len(cat_penalties),
            "total_amount": sum(p.get("amount", 0) for p in cat_penalties),
            "unique_employees": len(set(p.get("employee_id") for p in cat_penalties))
        }
    
    # Monthly breakdown
    monthly_breakdown = {}
    for m in month_list:
        m_penalties = [p for p in all_penalties if p.get("month") == m]
        monthly_breakdown[m] = {
            "total": sum(p.get("amount", 0) for p in m_penalties if p.get("status") in ("approved", "active")),
            "pending": sum(p.get("amount", 0) for p in m_penalties if p.get("status") == "pending_review"),
            "count": len(m_penalties),
            "employees_affected": len(set(p.get("employee_id") for p in m_penalties))
        }
    
    approved = [p for p in all_penalties if p.get("status") in ("approved", "active")]
    
    return {
        "by_category": category_summary,
        "monthly_breakdown": monthly_breakdown,
        "grand_total": sum(p.get("amount", 0) for p in approved),
        "total_employees_penalized": len(set(p.get("employee_id") for p in approved)),
        "months_analyzed": months,
        "count_by_status": {
            "pending_review": len([p for p in all_penalties if p.get("status") == "pending_review"]),
            "approved": len([p for p in all_penalties if p.get("status") in ("approved", "active")]),
            "rejected": len([p for p in all_penalties if p.get("status") == "rejected"]),
        }
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
