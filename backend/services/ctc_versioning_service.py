"""
CTC Versioning Service

PURPOSE: Provides version-controlled CTC/salary structure management.
Each CTC change creates a new versioned record with effective_date.
Current CTC is calculated by finding the latest active structure.

AUTHORITATIVE SOURCE: ctc_structures collection (with effective_date)
DERIVED: employees.current_ctc (should be calculated, not stored)

USAGE:
- Create CTC structure with effective_date
- Get current CTC via get_current_ctc(db, employee_id)
- Get CTC history via get_ctc_history(db, employee_id)
- Salary slip references structure_id, not raw values

BENEFITS:
- Full audit trail of CTC changes
- Historical accuracy for past months
- No stale data in employees collection
"""

from typing import Dict, Optional, List
from datetime import datetime, timezone
from uuid import uuid4
import logging

logger = logging.getLogger("ctc_versioning_service")


async def get_current_ctc(db, employee_id: str) -> Optional[Dict]:
    """
    Get the current (latest effective) CTC structure for an employee.
    
    This is the AUTHORITATIVE source for current CTC.
    
    Args:
        db: Database instance
        employee_id: The employee's UUID (id field)
    
    Returns:
        Dict with current CTC structure or None
    """
    try:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        
        # Find the latest structure where effective_date <= today
        # and either no end_date or end_date > today
        structure = await db.ctc_structures.find_one(
            {
                "employee_id": employee_id,
                "effective_date": {"$lte": today},
                "$or": [
                    {"end_date": None},
                    {"end_date": ""},
                    {"end_date": {"$gt": today}},
                    {"is_active": True}
                ]
            },
            {"_id": 0},
            sort=[("effective_date", -1), ("created_at", -1)]
        )
        
        if structure:
            return structure
        
        # Fallback: Get any active structure for this employee
        structure = await db.ctc_structures.find_one(
            {
                "employee_id": employee_id,
                "is_active": {"$ne": False}
            },
            {"_id": 0},
            sort=[("created_at", -1)]
        )
        
        return structure
        
    except Exception as e:
        logger.error(f"Error getting current CTC for {employee_id}: {e}")
        return None


async def get_ctc_for_date(db, employee_id: str, date: str) -> Optional[Dict]:
    """
    Get the CTC structure that was effective on a specific date.
    Useful for historical calculations (e.g., past salary slips).
    
    Args:
        db: Database instance
        employee_id: The employee's UUID
        date: Date string (YYYY-MM-DD)
    
    Returns:
        Dict with CTC structure effective on that date
    """
    try:
        structure = await db.ctc_structures.find_one(
            {
                "employee_id": employee_id,
                "effective_date": {"$lte": date},
                "$or": [
                    {"end_date": None},
                    {"end_date": ""},
                    {"end_date": {"$gt": date}}
                ]
            },
            {"_id": 0},
            sort=[("effective_date", -1)]
        )
        
        return structure
        
    except Exception as e:
        logger.error(f"Error getting CTC for date {date}, employee {employee_id}: {e}")
        return None


async def get_ctc_history(db, employee_id: str) -> List[Dict]:
    """
    Get complete CTC history for an employee.
    Returns all versions sorted by effective_date descending.
    """
    try:
        structures = await db.ctc_structures.find(
            {"employee_id": employee_id},
            {"_id": 0}
        ).sort([("effective_date", -1), ("created_at", -1)]).to_list(None)
        
        return structures
        
    except Exception as e:
        logger.error(f"Error getting CTC history for {employee_id}: {e}")
        return []


async def create_ctc_structure(
    db,
    employee_id: str,
    annual_ctc: float,
    effective_date: str,
    components: Optional[Dict] = None,
    created_by: Optional[str] = None,
    notes: Optional[str] = None
) -> Dict:
    """
    Create a new CTC structure with versioning.
    
    This automatically:
    - Sets end_date on the previous active structure
    - Creates new structure with effective_date
    
    Args:
        db: Database instance
        employee_id: The employee's UUID
        annual_ctc: Total annual CTC
        effective_date: When this CTC becomes effective (YYYY-MM-DD)
        components: Breakdown of CTC (basic, hra, allowances, etc.)
        created_by: User who created this structure
        notes: Reason for change
    
    Returns:
        Dict with new structure or error
    """
    try:
        now = datetime.now(timezone.utc).isoformat()
        structure_id = str(uuid4())
        
        # End the previous active structure
        prev_structure = await db.ctc_structures.find_one(
            {
                "employee_id": employee_id,
                "is_active": True,
                "end_date": None
            },
            {"_id": 0, "id": 1}
        )
        
        if prev_structure:
            # Set end_date to day before new effective_date
            from datetime import timedelta
            eff_date = datetime.strptime(effective_date, "%Y-%m-%d")
            end_date = (eff_date - timedelta(days=1)).strftime("%Y-%m-%d")
            
            await db.ctc_structures.update_one(
                {"id": prev_structure["id"]},
                {
                    "$set": {
                        "end_date": end_date,
                        "is_active": False,
                        "superseded_by": structure_id,
                        "updated_at": now
                    }
                }
            )
        
        # Calculate monthly CTC
        monthly_ctc = annual_ctc / 12
        
        # Default components if not provided
        if not components:
            components = calculate_default_components(annual_ctc)
        
        # Create new structure
        structure = {
            "id": structure_id,
            "employee_id": employee_id,
            "annual_ctc": annual_ctc,
            "monthly_ctc": monthly_ctc,
            "effective_date": effective_date,
            "end_date": None,
            "components": components,
            "is_active": True,
            "version": await get_next_version(db, employee_id),
            "notes": notes,
            "created_by": created_by,
            "created_at": now,
            "updated_at": now
        }
        
        await db.ctc_structures.insert_one(structure)
        
        logger.info(f"Created CTC structure {structure_id} for employee {employee_id}, effective {effective_date}")
        
        return {"success": True, "structure_id": structure_id, "structure": structure}
        
    except Exception as e:
        logger.error(f"Error creating CTC structure: {e}")
        return {"error": str(e)}


async def get_next_version(db, employee_id: str) -> int:
    """Get the next version number for an employee's CTC structure."""
    try:
        latest = await db.ctc_structures.find_one(
            {"employee_id": employee_id},
            {"_id": 0, "version": 1},
            sort=[("version", -1)]
        )
        
        return (latest.get("version", 0) if latest else 0) + 1
        
    except Exception:
        return 1


def calculate_default_components(annual_ctc: float) -> Dict:
    """
    Calculate default CTC component breakdown.
    This follows Indian payroll standards.
    """
    # Standard breakdown (adjust based on company policy)
    basic = annual_ctc * 0.40  # 40% of CTC
    hra = basic * 0.50  # 50% of Basic (for metro cities)
    
    # Statutory components
    pf_employer = min(basic * 0.12, 21600)  # 12% of Basic, max 1800/month
    esi_employer = annual_ctc * 0.0325 if annual_ctc <= 252000 else 0
    gratuity = basic * 0.0481  # 4.81% of Basic
    
    # Allowances
    special_allowance = annual_ctc - basic - hra - pf_employer - esi_employer - gratuity
    if special_allowance < 0:
        special_allowance = 0
        # Recalculate with lower basic
        basic = annual_ctc * 0.35
        hra = basic * 0.40
        pf_employer = min(basic * 0.12, 21600)
        special_allowance = annual_ctc - basic - hra - pf_employer - esi_employer - gratuity
    
    return {
        "basic": round(basic, 2),
        "hra": round(hra, 2),
        "special_allowance": round(max(special_allowance, 0), 2),
        "pf_employer": round(pf_employer, 2),
        "esi_employer": round(esi_employer, 2),
        "gratuity": round(gratuity, 2),
        "medical_allowance": 0,
        "conveyance": 0,
        "lta": 0,
        "other_allowances": 0
    }


async def calculate_employee_current_ctc(db, employee_id: str) -> Optional[float]:
    """
    Get the current annual CTC for an employee.
    This replaces reading from employees.current_ctc.
    
    Returns:
        float: Current annual CTC or None
    """
    structure = await get_current_ctc(db, employee_id)
    return structure.get("annual_ctc") if structure else None


async def sync_ctc_to_employee(db, employee_id: str) -> bool:
    """
    Sync current CTC from ctc_structures to employees collection.
    For backward compatibility with code that reads employees.current_ctc.
    
    This should be called after creating a new CTC structure.
    Eventually, all code should use get_current_ctc() instead.
    """
    try:
        structure = await get_current_ctc(db, employee_id)
        
        if not structure:
            return False
        
        await db.employees.update_one(
            {"id": employee_id},
            {
                "$set": {
                    "current_ctc": structure.get("annual_ctc"),
                    "annual_ctc": structure.get("annual_ctc"),
                    "monthly_ctc": structure.get("monthly_ctc"),
                    "ctc_structure_id": structure.get("id"),
                    "ctc_effective_date": structure.get("effective_date"),
                    "ctc_synced_at": datetime.now(timezone.utc).isoformat()
                }
            }
        )
        
        return True
        
    except Exception as e:
        logger.error(f"Error syncing CTC to employee: {e}")
        return False
