"""
Expanded Audit Logging System
Tracks all significant actions with before/after values
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from functools import wraps
import uuid

from .deps import get_db, ADMIN_ROLES, HR_ADMIN_ROLES
from .auth import get_current_user
from .models import User

router = APIRouter(prefix="/audit", tags=["Audit Logs"])


# ============== Audit Action Types ==============

class AuditAction:
    # User actions
    LOGIN = "user.login"
    LOGOUT = "user.logout"
    PASSWORD_CHANGE = "user.password_change"
    PROFILE_UPDATE = "user.profile_update"
    
    # Lead actions
    LEAD_CREATE = "lead.create"
    LEAD_UPDATE = "lead.update"
    LEAD_DELETE = "lead.delete"
    LEAD_REASSIGN = "lead.reassign"
    LEAD_STAGE_CHANGE = "lead.stage_change"
    
    # Agreement actions
    AGREEMENT_CREATE = "agreement.create"
    AGREEMENT_UPDATE = "agreement.update"
    AGREEMENT_SIGN = "agreement.sign"
    AGREEMENT_CONSENT = "agreement.consent"
    
    # Approval actions
    APPROVAL_REQUEST = "approval.request"
    APPROVAL_GRANT = "approval.grant"
    APPROVAL_REJECT = "approval.reject"
    
    # Permission actions
    PERMISSION_GRANT = "permission.grant"
    PERMISSION_REVOKE = "permission.revoke"
    PERMISSION_BULK_UPDATE = "permission.bulk_update"
    
    # HR actions
    EMPLOYEE_CREATE = "employee.create"
    EMPLOYEE_UPDATE = "employee.update"
    EMPLOYEE_TERMINATE = "employee.terminate"
    LEAVE_REQUEST = "leave.request"
    LEAVE_APPROVE = "leave.approve"
    LEAVE_REJECT = "leave.reject"
    SALARY_UPDATE = "salary.update"
    
    # Project actions
    PROJECT_CREATE = "project.create"
    PROJECT_UPDATE = "project.update"
    PROJECT_COMPLETE = "project.complete"
    PAYMENT_RECORD = "payment.record"
    
    # System actions
    CONFIG_CHANGE = "system.config_change"
    DATA_EXPORT = "system.data_export"
    BULK_IMPORT = "system.bulk_import"


# ============== Audit Log Model ==============

class AuditLogEntry(BaseModel):
    action: str
    entity_type: str
    entity_id: str
    changes: Optional[Dict[str, Any]] = None
    before_state: Optional[Dict[str, Any]] = None
    after_state: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


class AuditLogQuery(BaseModel):
    action: Optional[str] = None
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    performed_by: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    limit: int = 100


# ============== Audit Log Functions ==============

async def log_audit(
    action: str,
    entity_type: str,
    entity_id: str,
    performed_by: str,
    changes: Dict[str, Any] = None,
    before_state: Dict[str, Any] = None,
    after_state: Dict[str, Any] = None,
    request: Request = None,
    metadata: Dict[str, Any] = None
):
    """
    Create an audit log entry.
    Call this from any router to log significant actions.
    """
    db = get_db()
    
    # Build audit entry
    audit_entry = {
        "id": str(uuid.uuid4()),
        "action": action,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "performed_by": performed_by,
        "performed_at": datetime.now(timezone.utc).isoformat(),
        "changes": changes,
        "before_state": before_state,
        "after_state": after_state,
        "metadata": metadata or {}
    }
    
    # Add request info if available
    if request:
        audit_entry["metadata"]["ip_address"] = request.client.host if request.client else None
        audit_entry["metadata"]["user_agent"] = request.headers.get("user-agent")
        audit_entry["metadata"]["path"] = str(request.url.path)
        audit_entry["metadata"]["method"] = request.method
    
    await db.audit_logs.insert_one(audit_entry)
    return audit_entry["id"]


def compute_changes(before: Dict, after: Dict) -> Dict[str, Any]:
    """Compute the differences between two states"""
    changes = {}
    
    all_keys = set(before.keys()) | set(after.keys())
    
    for key in all_keys:
        before_val = before.get(key)
        after_val = after.get(key)
        
        if before_val != after_val:
            changes[key] = {
                "from": before_val,
                "to": after_val
            }
    
    return changes


# ============== API Endpoints ==============

@router.get("/logs")
async def get_audit_logs(
    action: Optional[str] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    performed_by: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 100,
    skip: int = 0,
    current_user: User = Depends(get_current_user)
):
    """Query audit logs with filters (Admin only)"""
    if current_user.role not in ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    db = get_db()
    
    # Build query
    query = {}
    
    if action:
        query["action"] = {"$regex": action, "$options": "i"}
    if entity_type:
        query["entity_type"] = entity_type
    if entity_id:
        query["entity_id"] = entity_id
    if performed_by:
        query["performed_by"] = performed_by
    if start_date:
        query["performed_at"] = {"$gte": start_date}
    if end_date:
        if "performed_at" in query:
            query["performed_at"]["$lte"] = end_date
        else:
            query["performed_at"] = {"$lte": end_date}
    
    # Execute query
    total = await db.audit_logs.count_documents(query)
    logs = await db.audit_logs.find(
        query,
        {"_id": 0}
    ).sort("performed_at", -1).skip(skip).limit(min(limit, 500)).to_list(500)
    
    return {
        "total": total,
        "limit": limit,
        "skip": skip,
        "logs": logs
    }


@router.get("/logs/entity/{entity_type}/{entity_id}")
async def get_entity_audit_trail(
    entity_type: str,
    entity_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get complete audit trail for a specific entity"""
    if current_user.role not in ADMIN_ROLES + HR_ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Admin or HR access required")
    
    db = get_db()
    
    logs = await db.audit_logs.find(
        {"entity_type": entity_type, "entity_id": entity_id},
        {"_id": 0}
    ).sort("performed_at", -1).to_list(200)
    
    return {
        "entity_type": entity_type,
        "entity_id": entity_id,
        "audit_trail": logs,
        "total_actions": len(logs)
    }


@router.get("/logs/user/{user_id}")
async def get_user_actions(
    user_id: str,
    days: int = 30,
    current_user: User = Depends(get_current_user)
):
    """Get all actions performed by a specific user"""
    if current_user.role not in ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    db = get_db()
    
    start_date = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    
    logs = await db.audit_logs.find(
        {
            "performed_by": user_id,
            "performed_at": {"$gte": start_date}
        },
        {"_id": 0}
    ).sort("performed_at", -1).to_list(500)
    
    # Group by action type
    action_summary = {}
    for log in logs:
        action = log.get("action", "unknown")
        if action not in action_summary:
            action_summary[action] = 0
        action_summary[action] += 1
    
    return {
        "user_id": user_id,
        "period_days": days,
        "total_actions": len(logs),
        "action_summary": action_summary,
        "actions": logs
    }


@router.get("/summary")
async def get_audit_summary(
    days: int = 7,
    current_user: User = Depends(get_current_user)
):
    """Get audit log summary for dashboard"""
    if current_user.role not in ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    db = get_db()
    
    start_date = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    
    # Aggregate by action type
    pipeline = [
        {"$match": {"performed_at": {"$gte": start_date}}},
        {"$group": {
            "_id": "$action",
            "count": {"$sum": 1},
            "latest": {"$max": "$performed_at"}
        }},
        {"$sort": {"count": -1}}
    ]
    
    action_stats = await db.audit_logs.aggregate(pipeline).to_list(50)
    
    # Aggregate by entity type
    entity_pipeline = [
        {"$match": {"performed_at": {"$gte": start_date}}},
        {"$group": {
            "_id": "$entity_type",
            "count": {"$sum": 1}
        }},
        {"$sort": {"count": -1}}
    ]
    
    entity_stats = await db.audit_logs.aggregate(entity_pipeline).to_list(20)
    
    # Most active users
    user_pipeline = [
        {"$match": {"performed_at": {"$gte": start_date}}},
        {"$group": {
            "_id": "$performed_by",
            "count": {"$sum": 1}
        }},
        {"$sort": {"count": -1}},
        {"$limit": 10}
    ]
    
    user_stats = await db.audit_logs.aggregate(user_pipeline).to_list(10)
    
    # Total count
    total_logs = await db.audit_logs.count_documents({"performed_at": {"$gte": start_date}})
    
    return {
        "period_days": days,
        "total_logs": total_logs,
        "by_action": action_stats,
        "by_entity": entity_stats,
        "most_active_users": user_stats
    }


@router.post("/log")
async def create_audit_log(
    entry: AuditLogEntry,
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """Manually create an audit log entry"""
    audit_id = await log_audit(
        action=entry.action,
        entity_type=entry.entity_type,
        entity_id=entry.entity_id,
        performed_by=current_user.id,
        changes=entry.changes,
        before_state=entry.before_state,
        after_state=entry.after_state,
        request=request,
        metadata=entry.metadata
    )
    
    return {"status": "success", "audit_id": audit_id}


# ============== Security Audit Specific ==============

@router.get("/security")
async def get_security_audit(
    days: int = 7,
    current_user: User = Depends(get_current_user)
):
    """Get security-related audit events"""
    if current_user.role not in ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    db = get_db()
    
    start_date = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    
    # Security-related actions
    security_actions = [
        "user.login", "user.logout", "user.password_change",
        "permission.grant", "permission.revoke", "permission.bulk_update",
        "system.config_change", "system.data_export"
    ]
    
    logs = await db.audit_logs.find(
        {
            "action": {"$in": security_actions},
            "performed_at": {"$gte": start_date}
        },
        {"_id": 0}
    ).sort("performed_at", -1).to_list(500)
    
    # Failed login attempts
    failed_logins = await db.security_events.find(
        {
            "event_type": "failed_login",
            "timestamp": {"$gte": start_date}
        },
        {"_id": 0}
    ).to_list(100)
    
    return {
        "period_days": days,
        "security_events": logs,
        "failed_logins": failed_logins,
        "total_security_events": len(logs),
        "total_failed_logins": len(failed_logins)
    }
