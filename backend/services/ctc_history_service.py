"""
CTC History Service - Versioned CTC Tracking with Effective Dates

This service provides versioned CTC tracking, ensuring historical CTC data is preserved
and the current CTC is always calculated based on effective dates.

The ctc_structures collection is the single source of truth for CTC data.
The employees.salary field becomes a cached/calculated value.

Usage:
    from backend.services.ctc_history_service import (
        get_current_ctc, get_ctc_history, get_ctc_as_of_date
    )
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timezone, date
from dateutil.relativedelta import relativedelta


def parse_effective_date(effective_month: str) -> date:
    """
    Parse effective_month string (YYYY-MM) to a date object.
    
    Args:
        effective_month: Month string in YYYY-MM format
        
    Returns:
        First day of the effective month
    """
    try:
        year, month = effective_month.split("-")
        return date(int(year), int(month), 1)
    except:
        return date.today()


async def get_current_ctc(db, employee_id: str) -> Optional[Dict[str, Any]]:
    """
    Get the current effective CTC structure for an employee.
    
    The current CTC is the most recent approved structure with an effective_month
    that is on or before the current date.
    
    Args:
        db: Database connection
        employee_id: The employee ID
        
    Returns:
        Current CTC structure or None
    """
    today = date.today()
    current_month = today.strftime("%Y-%m")
    
    # Find the most recent approved CTC structure that is effective
    ctc_structure = await db.ctc_structures.find_one(
        {
            "employee_id": employee_id,
            "status": "approved",
            "effective_month": {"$lte": current_month}
        },
        {"_id": 0},
        sort=[("effective_month", -1), ("version", -1)]
    )
    
    return ctc_structure


async def get_ctc_as_of_date(db, employee_id: str, as_of_date: date) -> Optional[Dict[str, Any]]:
    """
    Get the CTC structure that was effective on a specific date.
    
    Useful for payroll calculations, historical reports, and audits.
    
    Args:
        db: Database connection
        employee_id: The employee ID
        as_of_date: The date to check
        
    Returns:
        CTC structure effective on that date or None
    """
    as_of_month = as_of_date.strftime("%Y-%m")
    
    ctc_structure = await db.ctc_structures.find_one(
        {
            "employee_id": employee_id,
            "status": "approved",
            "effective_month": {"$lte": as_of_month}
        },
        {"_id": 0},
        sort=[("effective_month", -1), ("version", -1)]
    )
    
    return ctc_structure


async def get_ctc_history(db, employee_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Get the full CTC revision history for an employee.
    
    Args:
        db: Database connection
        employee_id: The employee ID
        limit: Maximum number of records to return
        
    Returns:
        List of CTC structures ordered by effective date (newest first)
    """
    structures = await db.ctc_structures.find(
        {"employee_id": employee_id, "status": "approved"},
        {"_id": 0}
    ).sort([("effective_month", -1), ("version", -1)]).to_list(limit)
    
    # Add computed fields
    for i, structure in enumerate(structures):
        structure["is_current"] = (i == 0)
        
        # Calculate duration if not current
        if i < len(structures) - 1:
            current_eff = parse_effective_date(structure.get("effective_month", "2024-01"))
            next_eff = parse_effective_date(structures[i + 1].get("effective_month", "2024-01"))
            months_effective = (current_eff.year - next_eff.year) * 12 + (current_eff.month - next_eff.month)
            structure["months_in_effect"] = months_effective
    
    return structures


async def get_ctc_summary(db, employee_id: str) -> Dict[str, Any]:
    """
    Get a summary of CTC history with key metrics.
    
    Args:
        db: Database connection
        employee_id: The employee ID
        
    Returns:
        Summary with current CTC, history count, and growth metrics
    """
    history = await get_ctc_history(db, employee_id, limit=50)
    
    if not history:
        return {
            "employee_id": employee_id,
            "has_ctc": False,
            "current_ctc": None,
            "revision_count": 0
        }
    
    current = history[0]
    first = history[-1] if len(history) > 1 else current
    
    # Calculate growth
    current_amount = current.get("annual_ctc", 0)
    first_amount = first.get("annual_ctc", 0)
    
    if first_amount > 0:
        total_growth_percent = round(((current_amount - first_amount) / first_amount) * 100, 2)
    else:
        total_growth_percent = 0
    
    return {
        "employee_id": employee_id,
        "has_ctc": True,
        "current_ctc": {
            "annual": current_amount,
            "monthly": round(current_amount / 12, 2) if current_amount else 0,
            "effective_from": current.get("effective_month"),
            "structure_id": current.get("id")
        },
        "revision_count": len(history),
        "first_ctc": {
            "annual": first_amount,
            "effective_from": first.get("effective_month")
        },
        "total_growth_percent": total_growth_percent,
        "last_revision": {
            "date": history[0].get("created_at") if history else None,
            "previous_ctc": history[1].get("annual_ctc") if len(history) > 1 else None,
            "change_percent": round(
                ((current_amount - history[1].get("annual_ctc", 0)) / history[1].get("annual_ctc", 1)) * 100, 2
            ) if len(history) > 1 and history[1].get("annual_ctc") else 0
        }
    }


async def sync_employee_ctc_field(db, employee_id: str) -> Dict[str, Any]:
    """
    Sync the employees.salary field with the current effective CTC.
    
    This keeps the denormalized field in sync for backward compatibility
    while the ctc_structures collection remains the source of truth.
    
    Args:
        db: Database connection
        employee_id: The employee ID
        
    Returns:
        Sync result
    """
    current_ctc = await get_current_ctc(db, employee_id)
    
    if not current_ctc:
        return {
            "employee_id": employee_id,
            "synced": False,
            "reason": "No approved CTC structure found"
        }
    
    annual_ctc = current_ctc.get("annual_ctc", 0)
    
    result = await db.employees.update_one(
        {"id": employee_id},
        {
            "$set": {
                "salary": annual_ctc,
                "annual_ctc": annual_ctc,
                "current_ctc": annual_ctc,
                "ctc_structure_id": current_ctc.get("id"),
                "ctc_effective_month": current_ctc.get("effective_month"),
                "ctc_synced_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    return {
        "employee_id": employee_id,
        "synced": result.modified_count > 0,
        "current_ctc": annual_ctc,
        "effective_month": current_ctc.get("effective_month"),
        "structure_id": current_ctc.get("id")
    }


async def bulk_sync_all_employee_ctc(db) -> Dict[str, Any]:
    """
    Sync all employees' salary fields with their current CTC structures.
    
    Returns:
        Bulk sync results
    """
    # Get all employees with CTC structures
    employees_with_ctc = await db.ctc_structures.distinct("employee_id")
    
    synced = 0
    errors = []
    
    for employee_id in employees_with_ctc:
        try:
            result = await sync_employee_ctc_field(db, employee_id)
            if result.get("synced"):
                synced += 1
        except Exception as e:
            errors.append({"employee_id": employee_id, "error": str(e)})
    
    return {
        "total_employees": len(employees_with_ctc),
        "synced": synced,
        "errors": len(errors),
        "error_details": errors[:10]
    }


async def get_upcoming_ctc_revisions(db, days_ahead: int = 30) -> List[Dict[str, Any]]:
    """
    Get CTC structures with effective dates in the upcoming period.
    
    Useful for HR to prepare for upcoming salary changes.
    
    Args:
        db: Database connection
        days_ahead: Number of days to look ahead
        
    Returns:
        List of upcoming CTC revisions
    """
    today = date.today()
    future_date = today + relativedelta(days=days_ahead)
    current_month = today.strftime("%Y-%m")
    future_month = future_date.strftime("%Y-%m")
    
    upcoming = await db.ctc_structures.find(
        {
            "status": "approved",
            "effective_month": {
                "$gt": current_month,
                "$lte": future_month
            }
        },
        {"_id": 0}
    ).sort("effective_month", 1).to_list(100)
    
    # Enrich with employee details
    for ctc in upcoming:
        employee = await db.employees.find_one(
            {"id": ctc.get("employee_id")},
            {"_id": 0, "first_name": 1, "last_name": 1, "employee_id": 1, "department": 1}
        )
        if employee:
            ctc["employee"] = employee
    
    return upcoming


async def calculate_payroll_ctc(db, employee_id: str, payroll_month: str) -> Dict[str, Any]:
    """
    Get the CTC structure to use for payroll calculation.
    
    For a given payroll month (e.g., "2025-12"), finds the CTC structure
    that was effective at the start of that month.
    
    Args:
        db: Database connection
        employee_id: The employee ID
        payroll_month: The payroll month in YYYY-MM format
        
    Returns:
        CTC structure for payroll with breakdown
    """
    ctc = await db.ctc_structures.find_one(
        {
            "employee_id": employee_id,
            "status": "approved",
            "effective_month": {"$lte": payroll_month}
        },
        {"_id": 0},
        sort=[("effective_month", -1), ("version", -1)]
    )
    
    if not ctc:
        # Fallback to employee's salary field
        employee = await db.employees.find_one(
            {"id": employee_id},
            {"_id": 0, "salary": 1, "annual_ctc": 1}
        )
        
        if employee:
            annual = employee.get("salary") or employee.get("annual_ctc") or 0
            return {
                "source": "employee_record",
                "annual_ctc": annual,
                "monthly_gross": round(annual / 12, 2) if annual else 0,
                "components": {},
                "warning": "No approved CTC structure found, using legacy salary field"
            }
        
        return {
            "source": "none",
            "annual_ctc": 0,
            "monthly_gross": 0,
            "components": {},
            "error": "No CTC data found for employee"
        }
    
    return {
        "source": "ctc_structure",
        "structure_id": ctc.get("id"),
        "effective_month": ctc.get("effective_month"),
        "annual_ctc": ctc.get("annual_ctc"),
        "monthly_gross": ctc.get("summary", {}).get("monthly_gross", round(ctc.get("annual_ctc", 0) / 12, 2)),
        "components": ctc.get("components", {}),
        "summary": ctc.get("summary", {})
    }
