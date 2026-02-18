"""
Security Router - Audit Logs and Security-related endpoints
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Optional

from .models import User
from .deps import get_db
from .auth import get_current_user

router = APIRouter(prefix="/security-audit-logs", tags=["Security"])


@router.get("")
async def get_security_audit_logs(
    event_type: Optional[str] = None,
    email: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user)
):
    """Get security audit logs (admin only)."""
    db = get_db()
    
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can view security audit logs")

    query = {}
    if event_type:
        query["event_type"] = event_type
    if email:
        query["email"] = {"$regex": email, "$options": "i"}
    if date_from:
        query.setdefault("timestamp", {})["$gte"] = date_from
    if date_to:
        query.setdefault("timestamp", {})["$lte"] = date_to

    total = await db.security_audit_logs.count_documents(query)
    logs = await db.security_audit_logs.find(query, {"_id": 0}).sort("timestamp", -1).skip(skip).limit(limit).to_list(limit)

    return {"logs": logs, "total": total}
