"""
Leave Balance Calculation Service

PURPOSE: Provides a single source of truth for leave balance calculations.
Instead of storing leave balance in employees collection (which can become stale),
this service calculates balances on-read from leave_requests collection.

AUTHORITATIVE SOURCES:
- Entitled: leave_policies (scope-based: company, department, role, employee)
- Used: SUM(approved leave_requests for current year)

USAGE:
- Called by API endpoints that need leave balance
- Cached with short TTL for performance
- Replaces employees.leave_balance reads
"""

from typing import Dict, Optional, List
from datetime import datetime, timezone, timedelta
from dateutil.relativedelta import relativedelta
import logging

logger = logging.getLogger("leave_balance_service")

# Default leave entitlements (fallback if no policy exists)
DEFAULT_ENTITLEMENTS = {
    "casual_leave": 12,
    "sick_leave": 6,
    "earned_leave": 15
}

# Leave types
LEAVE_TYPES = ["casual_leave", "sick_leave", "earned_leave", "compensatory_off", "loss_of_pay"]


async def get_leave_entitlements(db, employee_id: str) -> Dict:
    """
    Get leave entitlements for an employee based on applicable policies.
    
    Policy priority (highest first):
    1. Employee-specific policy
    2. Role-based policy
    3. Department-based policy  
    4. Company-wide policy
    5. System default
    """
    try:
        # Get employee details for policy matching
        employee = await db.employees.find_one(
            {"id": employee_id},
            {"_id": 0, "department": 1, "designation": 1, "role": 1, "joining_date": 1}
        )
        
        if not employee:
            return DEFAULT_ENTITLEMENTS.copy()
        
        # Try to find matching policy in priority order
        
        # 1. Employee-specific policy
        policy = await db.leave_policies.find_one(
            {"scope": "employee", "target_id": employee_id, "is_active": True},
            {"_id": 0}
        )
        
        # 2. Role/Designation-based policy
        if not policy and employee.get("designation"):
            policy = await db.leave_policies.find_one(
                {"scope": "role", "target_id": employee.get("designation"), "is_active": True},
                {"_id": 0}
            )
        
        # 3. Department-based policy
        if not policy and employee.get("department"):
            policy = await db.leave_policies.find_one(
                {"scope": "department", "target_id": employee.get("department"), "is_active": True},
                {"_id": 0}
            )
        
        # 4. Company-wide policy
        if not policy:
            policy = await db.leave_policies.find_one(
                {"scope": "company", "is_active": True},
                {"_id": 0}
            )
        
        # 5. Fallback to settings-based policy
        if not policy:
            settings_policy = await db.settings.find_one(
                {"key": "leave_policy"},
                {"_id": 0, "value": 1}
            )
            if settings_policy and settings_policy.get("value"):
                policy = settings_policy.get("value")
        
        # Build entitlements from policy or use defaults
        entitlements = DEFAULT_ENTITLEMENTS.copy()
        
        if policy:
            # Extract entitlements from policy's leave_types array
            leave_types = policy.get("leave_types", [])
            for lt in leave_types:
                if lt.get("enabled", True):
                    leave_key = lt.get("type", "").lower().replace(" ", "_")
                    if not leave_key.endswith("_leave") and leave_key not in ["compensatory_off", "loss_of_pay"]:
                        leave_key = f"{leave_key}_leave"
                    entitlements[leave_key] = lt.get("quota", 0)
            
            # Also check direct fields (legacy format)
            for key in ["casual_leave", "sick_leave", "earned_leave"]:
                if key in policy:
                    entitlements[key] = policy[key]
        
        # Pro-rate for employees who joined mid-year
        joining_date = employee.get("joining_date")
        if joining_date:
            try:
                if isinstance(joining_date, str):
                    joining_date = datetime.fromisoformat(joining_date.replace("Z", "+00:00"))
                
                today = datetime.now(timezone.utc)
                year_start = datetime(today.year, 1, 1, tzinfo=timezone.utc)
                
                if joining_date > year_start:
                    # Calculate months remaining in year
                    months_remaining = 12 - joining_date.month + 1
                    prorate_factor = months_remaining / 12
                    
                    for key in ["casual_leave", "sick_leave", "earned_leave"]:
                        if key in entitlements:
                            entitlements[key] = round(entitlements[key] * prorate_factor, 1)
            except Exception as e:
                logger.warning(f"Failed to pro-rate for employee {employee_id}: {e}")
        
        return entitlements
        
    except Exception as e:
        logger.error(f"Error getting entitlements for {employee_id}: {e}")
        return DEFAULT_ENTITLEMENTS.copy()


async def get_used_leave(db, employee_id: str, year: Optional[int] = None) -> Dict:
    """
    Calculate used leave from approved leave requests.
    
    This is the AUTHORITATIVE source for used leave - calculated on read,
    not stored as a denormalized field.
    """
    try:
        if year is None:
            year = datetime.now().year
        
        year_start = f"{year}-01-01"
        year_end = f"{year}-12-31"
        
        # Get employee's employee_id (code like DVC001)
        employee = await db.employees.find_one(
            {"id": employee_id},
            {"_id": 0, "employee_id": 1}
        )
        emp_code = employee.get("employee_id") if employee else None
        
        # Query approved leave requests for this year
        query = {
            "status": {"$in": ["approved", "rm_approved", "hr_approved"]},
            "start_date": {"$gte": year_start, "$lte": year_end}
        }
        
        # Match by either id or employee_id code
        if emp_code:
            query["$or"] = [
                {"employee_id": employee_id},
                {"employee_id": emp_code}
            ]
        else:
            query["employee_id"] = employee_id
        
        leave_requests = await db.leave_requests.find(query, {"_id": 0}).to_list(None)
        
        # Aggregate by leave type
        used = {
            "casual_leave": 0,
            "sick_leave": 0,
            "earned_leave": 0,
            "compensatory_off": 0,
            "loss_of_pay": 0
        }
        
        for req in leave_requests:
            leave_type = req.get("leave_type", "").lower().replace(" ", "_")
            
            # Normalize leave type names
            if leave_type in ["casual", "cl"]:
                leave_type = "casual_leave"
            elif leave_type in ["sick", "sl"]:
                leave_type = "sick_leave"
            elif leave_type in ["earned", "el", "privilege", "pl"]:
                leave_type = "earned_leave"
            elif leave_type in ["comp_off", "compensatory"]:
                leave_type = "compensatory_off"
            elif leave_type in ["lop", "lwp", "without_pay"]:
                leave_type = "loss_of_pay"
            
            # Calculate days
            days = req.get("total_days", req.get("days", 0))
            if not days:
                try:
                    start = datetime.fromisoformat(req.get("start_date", "").replace("Z", "+00:00"))
                    end = datetime.fromisoformat(req.get("end_date", "").replace("Z", "+00:00"))
                    days = (end - start).days + 1
                except Exception:
                    days = 1
            
            if leave_type in used:
                used[leave_type] += days
        
        return used
        
    except Exception as e:
        logger.error(f"Error calculating used leave for {employee_id}: {e}")
        return {lt: 0 for lt in LEAVE_TYPES}


async def calculate_leave_balance(db, employee_id: str, year: Optional[int] = None) -> Dict:
    """
    Calculate complete leave balance for an employee.
    
    This is the SINGLE SOURCE OF TRUTH for leave balance.
    
    Returns:
        {
            "casual_leave": { "entitled": 12, "used": 5, "available": 7 },
            "sick_leave": { "entitled": 6, "used": 2, "available": 4 },
            "earned_leave": { "entitled": 15, "used": 3, "available": 12 },
            "total": { "entitled": 33, "used": 10, "available": 23 }
        }
    """
    try:
        if year is None:
            year = datetime.now().year
        
        # Get entitlements and used counts
        entitlements = await get_leave_entitlements(db, employee_id)
        used = await get_used_leave(db, employee_id, year)
        
        # Calculate balances
        balance = {}
        total_entitled = 0
        total_used = 0
        total_available = 0
        
        for leave_type in ["casual_leave", "sick_leave", "earned_leave"]:
            entitled = entitlements.get(leave_type, 0)
            used_days = used.get(leave_type, 0)
            available = max(0, entitled - used_days)
            
            balance[leave_type] = {
                "entitled": entitled,
                "used": used_days,
                "available": available
            }
            
            total_entitled += entitled
            total_used += used_days
            total_available += available
        
        # Add other leave types
        for leave_type in ["compensatory_off", "loss_of_pay"]:
            used_days = used.get(leave_type, 0)
            balance[leave_type] = {
                "entitled": 0,  # These are not entitled, just tracked
                "used": used_days,
                "available": 0
            }
            total_used += used_days
        
        balance["total"] = {
            "entitled": total_entitled,
            "used": total_used,
            "available": total_available
        }
        
        balance["year"] = year
        balance["calculated_at"] = datetime.now(timezone.utc).isoformat()
        
        return balance
        
    except Exception as e:
        logger.error(f"Error calculating balance for {employee_id}: {e}")
        return {
            "error": str(e),
            "casual_leave": {"entitled": 12, "used": 0, "available": 12},
            "sick_leave": {"entitled": 6, "used": 0, "available": 6},
            "earned_leave": {"entitled": 15, "used": 0, "available": 15},
            "total": {"entitled": 33, "used": 0, "available": 33}
        }


async def get_leave_balance_simple(db, employee_id: str) -> Dict:
    """
    Get leave balance in simple format (compatible with old employees.leave_balance format).
    
    This provides backward compatibility for existing code that expects:
    {
        "casual_leave": 7,
        "sick_leave": 4,
        "earned_leave": 12,
        "used_casual": 5,
        "used_sick": 2,
        "used_earned": 3
    }
    """
    full_balance = await calculate_leave_balance(db, employee_id)
    
    simple = {
        "casual_leave": full_balance.get("casual_leave", {}).get("available", 0),
        "sick_leave": full_balance.get("sick_leave", {}).get("available", 0),
        "earned_leave": full_balance.get("earned_leave", {}).get("available", 0),
        "used_casual": full_balance.get("casual_leave", {}).get("used", 0),
        "used_sick": full_balance.get("sick_leave", {}).get("used", 0),
        "used_earned": full_balance.get("earned_leave", {}).get("used", 0),
        "total_available": full_balance.get("total", {}).get("available", 0),
        "total_used": full_balance.get("total", {}).get("used", 0)
    }
    
    return simple
