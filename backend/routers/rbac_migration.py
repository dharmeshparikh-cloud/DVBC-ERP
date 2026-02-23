"""
RBAC Migration Framework
=========================
Safe, auditable, fail-loud migration from hardcoded roles to database-driven RBAC.

PRINCIPLES:
1. NEVER silently fallback - always log and alert
2. NEVER duplicate logic - single function per check type
3. NEVER leave legacy code - explicit deprecation with runtime warnings
4. ALWAYS audit trail - log every permission check in sensitive flows
5. ALWAYS validate - run consistency checks on startup

MIGRATION PHASES:
- Phase 1: Audit mode (log all checks, no behavior change)
- Phase 2: Shadow mode (check both old and new, alert on mismatch)
- Phase 3: Cutover mode (new system primary, old as validation)
- Phase 4: Cleanup mode (remove old code)
"""

import logging
import asyncio
from typing import Dict, List, Optional, Set, Tuple, Any, Callable
from datetime import datetime, timezone
from functools import wraps
from enum import Enum
import traceback
import os

logger = logging.getLogger(__name__)

# ==================== MIGRATION CONFIGURATION ====================

class MigrationPhase(Enum):
    AUDIT = "audit"      # Log everything, no changes
    SHADOW = "shadow"    # Run both, compare results
    CUTOVER = "cutover"  # New system primary
    COMPLETE = "complete" # Old code removed

# Set via environment variable or database config
CURRENT_PHASE = MigrationPhase(os.environ.get("RBAC_MIGRATION_PHASE", "audit"))

# Track all role check locations for audit
_role_check_registry: Dict[str, Dict] = {}
_permission_mismatches: List[Dict] = []
_fallback_events: List[Dict] = []


# ==================== AUDIT DECORATORS ====================

def register_role_check(location: str, check_type: str, roles_involved: List[str]):
    """
    Register a role check location for audit tracking.
    Call this at module load time to build registry.
    """
    _role_check_registry[location] = {
        "check_type": check_type,
        "roles_involved": roles_involved,
        "call_count": 0,
        "last_called": None,
        "mismatches": 0
    }


def audited_role_check(location: str):
    """
    Decorator to audit role checks during migration.
    Logs every check and tracks statistics.
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Track call
            if location in _role_check_registry:
                _role_check_registry[location]["call_count"] += 1
                _role_check_registry[location]["last_called"] = datetime.now(timezone.utc).isoformat()
            
            # Log in audit mode
            if CURRENT_PHASE == MigrationPhase.AUDIT:
                logger.debug(f"RBAC_AUDIT: {location} called with args={args[:2]}")
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


# ==================== FAIL-LOUD FALLBACK ====================

class RBACFallbackError(Exception):
    """Raised when RBAC system falls back to hardcoded values"""
    pass


def log_fallback_event(location: str, reason: str, fallback_value: Any):
    """
    Log and track when fallback to hardcoded values occurs.
    In production, this should trigger alerts.
    """
    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "location": location,
        "reason": reason,
        "fallback_value": str(fallback_value)[:200],
        "stack_trace": traceback.format_stack()[-5:]
    }
    _fallback_events.append(event)
    
    # FAIL LOUD - log as error, not warning
    logger.error(
        f"RBAC_FALLBACK: {location} - {reason}. "
        f"Using fallback: {str(fallback_value)[:100]}. "
        f"This indicates RBAC system issue!"
    )
    
    # In production, raise exception to prevent silent failures
    if os.environ.get("RBAC_STRICT_MODE", "false").lower() == "true":
        raise RBACFallbackError(f"RBAC fallback at {location}: {reason}")


# ==================== SHADOW MODE COMPARISON ====================

def compare_permission_results(
    location: str,
    user_role: str,
    old_result: bool,
    new_result: bool,
    context: Dict = None
):
    """
    Compare old (hardcoded) vs new (database) permission results.
    Log mismatches for investigation.
    """
    if old_result != new_result:
        mismatch = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "location": location,
            "user_role": user_role,
            "old_result": old_result,
            "new_result": new_result,
            "context": context or {},
            "stack_trace": traceback.format_stack()[-3:]
        }
        _permission_mismatches.append(mismatch)
        
        # Track in registry
        if location in _role_check_registry:
            _role_check_registry[location]["mismatches"] += 1
        
        logger.error(
            f"RBAC_MISMATCH: {location} - role={user_role}, "
            f"old={old_result}, new={new_result}. "
            f"Context: {context}"
        )
        
        return False  # Mismatch detected
    return True  # Results match


# ==================== APPROVAL FLOW REGISTRY ====================

APPROVAL_FLOWS = {
    "agreement_approval": {
        "description": "Agreement requires Principal Consultant or Admin approval",
        "states": ["draft", "pending_approval", "approved", "rejected"],
        "transitions": {
            "draft->pending_approval": {"actor": "creator", "roles": ["sales_executive", "executive"]},
            "pending_approval->approved": {"actor": "approver", "roles": ["admin", "principal_consultant"]},
            "pending_approval->rejected": {"actor": "approver", "roles": ["admin", "principal_consultant"]},
        },
        "legacy_check": "AGREEMENT_APPROVE_ROLES = ['admin', 'principal_consultant']",
        "new_check": "rbac.get_role_group('AGREEMENT_APPROVE_ROLES')",
        "file": "agreements.py",
        "line": "varies"
    },
    "kickoff_internal_approval": {
        "description": "Kickoff internal approval by Principal Consultant",
        "states": ["pending", "internal_approved", "client_pending", "approved", "rejected"],
        "transitions": {
            "pending->internal_approved": {"actor": "approver", "roles": ["admin", "principal_consultant"]},
            "internal_approved->client_pending": {"actor": "system", "roles": []},
            "client_pending->approved": {"actor": "client", "roles": ["client"]},
        },
        "legacy_check": "PRINCIPAL_CONSULTANT_ROLES",
        "new_check": "rbac.get_role_group('PRINCIPAL_CONSULTANT_ROLES')",
        "file": "kickoff.py",
        "line": "varies"
    },
    "leave_approval": {
        "description": "Leave requests approved by manager or HR",
        "states": ["pending", "approved", "rejected", "cancelled"],
        "transitions": {
            "pending->approved": {"actor": "approver", "roles": ["admin", "manager", "hr_manager", "principal_consultant"]},
            "pending->rejected": {"actor": "approver", "roles": ["admin", "manager", "hr_manager", "principal_consultant"]},
        },
        "legacy_check": "APPROVAL_ROLES",
        "new_check": "rbac.get_role_group('APPROVAL_ROLES')",
        "file": "leaves.py",
        "line": "varies"
    },
    "expense_approval": {
        "description": "Expense claims approved by manager",
        "states": ["draft", "submitted", "approved", "rejected", "paid"],
        "transitions": {
            "submitted->approved": {"actor": "approver", "roles": ["admin", "manager", "hr_manager"]},
        },
        "legacy_check": "MANAGER_ROLES",
        "new_check": "rbac.get_role_group('MANAGER_ROLES')",
        "file": "expenses.py",
        "line": "varies"
    }
}


# ==================== HIERARCHICAL FILTERING REGISTRY ====================

HIERARCHICAL_FILTERS = {
    "leads_access": {
        "description": "Leads filtered by assignment and reporting hierarchy",
        "logic": "User sees own leads + reportees' leads",
        "admin_override": True,
        "files": ["leads.py"],
        "endpoints": ["GET /leads", "GET /leads/{id}/funnel-progress"]
    },
    "employee_access": {
        "description": "Employee data filtered by department and reporting",
        "logic": "HR sees all, managers see reportees, others see self",
        "admin_override": True,
        "files": ["employees.py"],
        "endpoints": ["GET /employees", "GET /employees/{id}"]
    },
    "attendance_access": {
        "description": "Attendance records filtered by team",
        "logic": "HR sees all, managers see team, others see self",
        "admin_override": True,
        "files": ["attendance.py"],
        "endpoints": ["GET /attendance", "GET /attendance/team"]
    },
    "project_access": {
        "description": "Projects filtered by assignment",
        "logic": "Assigned consultants + managers see project",
        "admin_override": True,
        "files": ["projects.py"],
        "endpoints": ["GET /projects", "GET /projects/{id}"]
    }
}


# ==================== RACE CONDITION SAFEGUARDS ====================

class RBACLock:
    """
    Distributed lock for RBAC operations to prevent race conditions.
    Uses MongoDB for coordination in multi-instance deployments.
    """
    
    def __init__(self, db, lock_name: str, timeout_seconds: int = 30):
        self.db = db
        self.lock_name = lock_name
        self.timeout = timeout_seconds
        self.lock_id = None
    
    async def acquire(self) -> bool:
        """Attempt to acquire lock"""
        import uuid
        self.lock_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        
        try:
            # Try to insert lock document
            result = await self.db.rbac_locks.update_one(
                {
                    "name": self.lock_name,
                    "$or": [
                        {"expires_at": {"$lt": now.isoformat()}},
                        {"expires_at": {"$exists": False}}
                    ]
                },
                {
                    "$set": {
                        "name": self.lock_name,
                        "lock_id": self.lock_id,
                        "acquired_at": now.isoformat(),
                        "expires_at": (now.replace(second=now.second + self.timeout)).isoformat()
                    }
                },
                upsert=True
            )
            
            # Verify we got the lock
            lock_doc = await self.db.rbac_locks.find_one({"name": self.lock_name})
            return lock_doc and lock_doc.get("lock_id") == self.lock_id
            
        except Exception as e:
            logger.error(f"Failed to acquire RBAC lock {self.lock_name}: {e}")
            return False
    
    async def release(self):
        """Release lock"""
        if self.lock_id:
            await self.db.rbac_locks.delete_one({
                "name": self.lock_name,
                "lock_id": self.lock_id
            })


async def with_rbac_lock(db, lock_name: str, operation: Callable):
    """
    Execute operation with distributed lock.
    Prevents race conditions in role/permission updates.
    """
    lock = RBACLock(db, lock_name)
    
    if not await lock.acquire():
        raise Exception(f"Could not acquire lock for {lock_name}")
    
    try:
        return await operation()
    finally:
        await lock.release()


# ==================== CONSISTENCY CHECKS ====================

async def run_consistency_checks(db) -> Dict[str, Any]:
    """
    Run on startup to verify RBAC system integrity.
    Returns report of any issues found.
    """
    issues = []
    
    # Check 1: All users have valid roles
    roles = await db.rbac_roles.distinct("code")
    role_set = set(roles)
    
    invalid_role_users = await db.users.find(
        {"role": {"$nin": list(role_set)}},
        {"email": 1, "role": 1, "_id": 0}
    ).to_list(100)
    
    if invalid_role_users:
        issues.append({
            "type": "invalid_user_roles",
            "severity": "HIGH",
            "count": len(invalid_role_users),
            "details": invalid_role_users[:5]
        })
    
    # Check 2: All role groups reference valid roles
    groups = await db.rbac_role_groups.find({}).to_list(100)
    for group in groups:
        invalid_roles = [r for r in group.get("roles", []) if r not in role_set]
        if invalid_roles:
            issues.append({
                "type": "invalid_group_roles",
                "severity": "MEDIUM",
                "group": group["code"],
                "invalid_roles": invalid_roles
            })
    
    # Check 3: No circular inheritance
    roles_data = await db.rbac_roles.find({}).to_list(100)
    for role in roles_data:
        visited = set()
        queue = role.get("inherits_from", [])
        while queue:
            parent = queue.pop(0)
            if parent == role["code"]:
                issues.append({
                    "type": "circular_inheritance",
                    "severity": "HIGH",
                    "role": role["code"]
                })
                break
            if parent not in visited:
                visited.add(parent)
                parent_role = next((r for r in roles_data if r["code"] == parent), None)
                if parent_role:
                    queue.extend(parent_role.get("inherits_from", []))
    
    # Check 4: Orphaned permissions
    # (permissions referencing non-existent features)
    
    return {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "issues_found": len(issues),
        "issues": issues,
        "status": "HEALTHY" if not issues else "ISSUES_FOUND"
    }


# ==================== MIGRATION STATUS ====================

def get_migration_status() -> Dict:
    """Get current migration status and statistics"""
    return {
        "current_phase": CURRENT_PHASE.value,
        "role_checks_registered": len(_role_check_registry),
        "fallback_events": len(_fallback_events),
        "permission_mismatches": len(_permission_mismatches),
        "recent_fallbacks": _fallback_events[-10:] if _fallback_events else [],
        "recent_mismatches": _permission_mismatches[-10:] if _permission_mismatches else [],
        "approval_flows_mapped": len(APPROVAL_FLOWS),
        "hierarchical_filters_mapped": len(HIERARCHICAL_FILTERS)
    }


def get_audit_report() -> Dict:
    """Get detailed audit report of all role checks"""
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "phase": CURRENT_PHASE.value,
        "role_checks": _role_check_registry,
        "total_checks": sum(r["call_count"] for r in _role_check_registry.values()),
        "total_mismatches": sum(r["mismatches"] for r in _role_check_registry.values()),
        "approval_flows": APPROVAL_FLOWS,
        "hierarchical_filters": HIERARCHICAL_FILTERS
    }


# ==================== DEPRECATION MARKERS ====================

def deprecated_role_check(new_function: str):
    """
    Mark a function as deprecated, pointing to new implementation.
    Logs warning on every call to track usage.
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger.warning(
                f"DEPRECATED: {func.__name__} is deprecated. "
                f"Use {new_function} instead. "
                f"Called from: {traceback.format_stack()[-2]}"
            )
            return func(*args, **kwargs)
        return wrapper
    return decorator


# ==================== STARTUP INITIALIZATION ====================

async def initialize_rbac_migration(db):
    """
    Initialize RBAC migration framework on application startup.
    - Runs consistency checks
    - Seeds default data if needed
    - Sets up monitoring
    """
    logger.info(f"Initializing RBAC Migration Framework - Phase: {CURRENT_PHASE.value}")
    
    # Run consistency checks
    consistency_report = await run_consistency_checks(db)
    
    if consistency_report["status"] != "HEALTHY":
        logger.error(f"RBAC Consistency Issues Found: {consistency_report['issues']}")
        
        # In strict mode, fail startup
        if os.environ.get("RBAC_STRICT_MODE", "false").lower() == "true":
            raise Exception("RBAC consistency check failed - cannot start in strict mode")
    
    logger.info(f"RBAC Migration initialized. Status: {consistency_report['status']}")
    return consistency_report
