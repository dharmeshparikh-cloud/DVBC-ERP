"""
Employee-User Sync Service

PURPOSE: Ensures user collection stays in sync with employee collection.
This service maintains data consistency between the two collections.

AUTHORITATIVE SOURCE: employees collection
DERIVED/SYNC TARGET: users collection (for authentication only)

SYNCED FIELDS:
- full_name (from first_name + last_name)
- role
- department / departments / primary_department
- designation
- level
- reporting_manager_id
- is_active

USAGE:
- Called automatically on employee update
- Can be called manually for bulk sync
"""

from typing import Optional, List, Dict
from datetime import datetime, timezone
import logging

logger = logging.getLogger("employee_user_sync")

# Fields that should be synced from employee to user
SYNC_FIELDS = [
    "role",
    "department",
    "departments", 
    "primary_department",
    "designation",
    "level",
    "reporting_manager_id",
    "is_active",
    "is_view_only"
]


async def sync_employee_to_user(db, employee_id: str, updated_fields: Optional[Dict] = None) -> bool:
    """
    Sync employee data to corresponding user record.
    
    Args:
        db: Database instance
        employee_id: The employee's UUID (id field)
        updated_fields: Optional dict of fields that were updated (for targeted sync)
    
    Returns:
        bool: True if sync was successful, False if no user found or error
    """
    try:
        # Get the employee
        employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
        if not employee:
            logger.warning(f"Sync: Employee {employee_id} not found")
            return False
        
        email = employee.get("email")
        if not email:
            logger.warning(f"Sync: Employee {employee_id} has no email")
            return False
        
        # Check if user exists
        user = await db.users.find_one({"email": email}, {"_id": 0, "id": 1})
        if not user:
            # No user record - employee may not have portal access yet
            logger.debug(f"Sync: No user found for employee {employee_id} ({email})")
            return False
        
        # Build update payload
        update_payload = {
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "synced_from_employee": True,
            "last_sync_at": datetime.now(timezone.utc).isoformat()
        }
        
        # Sync full_name from first_name + last_name
        first_name = employee.get("first_name", "")
        last_name = employee.get("last_name", "")
        if first_name or last_name:
            update_payload["full_name"] = f"{first_name} {last_name}".strip()
        
        # Determine which fields to sync
        fields_to_sync = SYNC_FIELDS
        if updated_fields:
            # Only sync fields that were actually updated
            fields_to_sync = [f for f in SYNC_FIELDS if f in updated_fields]
        
        # Copy sync fields from employee to user
        for field in fields_to_sync:
            if field in employee:
                update_payload[field] = employee[field]
        
        # Only update if there are changes
        if len(update_payload) > 3:  # More than just updated_at, synced_from_employee, last_sync_at
            await db.users.update_one(
                {"email": email},
                {"$set": update_payload}
            )
            logger.info(f"Sync: Updated user for employee {employee_id}, fields: {list(update_payload.keys())}")
            return True
        
        return False
        
    except Exception as e:
        logger.error(f"Sync error for employee {employee_id}: {str(e)}")
        return False


async def sync_all_employees_to_users(db, batch_size: int = 100) -> Dict:
    """
    Bulk sync all employees to their user records.
    Useful for initial sync or periodic reconciliation.
    
    Returns:
        Dict with sync statistics
    """
    stats = {
        "total_employees": 0,
        "synced": 0,
        "no_user": 0,
        "errors": 0
    }
    
    try:
        # Get all employees with portal access
        employees = await db.employees.find(
            {"has_portal_access": True},
            {"_id": 0, "id": 1, "email": 1}
        ).to_list(None)
        
        stats["total_employees"] = len(employees)
        
        for emp in employees:
            result = await sync_employee_to_user(db, emp["id"])
            if result:
                stats["synced"] += 1
            else:
                stats["no_user"] += 1
        
        logger.info(f"Bulk sync complete: {stats}")
        return stats
        
    except Exception as e:
        logger.error(f"Bulk sync error: {str(e)}")
        stats["errors"] += 1
        return stats


async def verify_sync_consistency(db, employee_id: str) -> Dict:
    """
    Check if employee and user data are in sync.
    Useful for debugging and monitoring.
    
    Returns:
        Dict with consistency report
    """
    report = {
        "employee_id": employee_id,
        "is_consistent": True,
        "mismatched_fields": []
    }
    
    try:
        employee = await db.employees.find_one({"id": employee_id}, {"_id": 0})
        if not employee:
            return {"error": "Employee not found"}
        
        email = employee.get("email")
        user = await db.users.find_one({"email": email}, {"_id": 0})
        if not user:
            return {"error": "No user record", "has_portal_access": employee.get("has_portal_access", False)}
        
        # Check each sync field
        for field in SYNC_FIELDS:
            emp_val = employee.get(field)
            user_val = user.get(field)
            
            if emp_val != user_val:
                report["is_consistent"] = False
                report["mismatched_fields"].append({
                    "field": field,
                    "employee_value": emp_val,
                    "user_value": user_val
                })
        
        # Check full_name
        expected_name = f"{employee.get('first_name', '')} {employee.get('last_name', '')}".strip()
        if user.get("full_name") != expected_name:
            report["is_consistent"] = False
            report["mismatched_fields"].append({
                "field": "full_name",
                "employee_value": expected_name,
                "user_value": user.get("full_name")
            })
        
        return report
        
    except Exception as e:
        return {"error": str(e)}



async def check_sync_status(db) -> Dict:
    """
    Check overall sync status between employees and users collections.
    Used for health checks.
    
    Returns:
        Dict with sync health status
    """
    try:
        total_employees = await db.employees.count_documents({})
        employees_with_access = await db.employees.count_documents({"has_portal_access": True})
        total_users = await db.users.count_documents({})
        
        # Sample check for consistency
        sample_employees = await db.employees.find(
            {"has_portal_access": True},
            {"_id": 0, "id": 1, "email": 1}
        ).limit(10).to_list(10)
        
        inconsistent_count = 0
        for emp in sample_employees:
            report = await verify_sync_consistency(db, emp["id"])
            if not report.get("is_consistent", True) or report.get("error"):
                inconsistent_count += 1
        
        return {
            "status": "ok" if inconsistent_count == 0 else "warning",
            "total_employees": total_employees,
            "employees_with_access": employees_with_access,
            "total_users": total_users,
            "sample_checked": len(sample_employees),
            "sample_inconsistent": inconsistent_count
        }
    
    except Exception as e:
        return {"status": "error", "error": str(e)}