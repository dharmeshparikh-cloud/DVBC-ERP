"""
Approvals Router - Generic approval workflow, scope approvals, and action handling.
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Optional, List
from datetime import datetime, timezone
import uuid
from pydantic import BaseModel
from .deps import get_db, MANAGER_ROLES
from .models import User
from .auth import get_current_user

router = APIRouter(prefix="/approvals", tags=["Approvals"])


class ApprovalAction(BaseModel):
    action: str  # approve, reject, request_changes
    comments: Optional[str] = ""


@router.get("/pending")
async def get_pending_approvals(current_user: User = Depends(get_current_user)):
    """Get pending approvals for current user"""
    db = get_db()
    
    approvals = await db.approvals.find(
        {
            "approver_id": current_user.id,
            "status": "pending"
        },
        {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    
    return approvals


@router.get("/all")
async def get_all_approvals(
    status: Optional[str] = None,
    type: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get all approvals (managers only)"""
    db = get_db()
    
    if current_user.role not in MANAGER_ROLES:
        raise HTTPException(status_code=403, detail="Only managers can view all approvals")
    
    query = {}
    if status:
        query["status"] = status
    if type:
        query["type"] = type
    
    approvals = await db.approvals.find(query, {"_id": 0}).sort("created_at", -1).to_list(500)
    return approvals


@router.get("/my-requests")
async def get_my_requests(current_user: User = Depends(get_current_user)):
    """Get approval requests submitted by current user"""
    db = get_db()
    
    approvals = await db.approvals.find(
        {"requester_id": current_user.id},
        {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    
    return approvals


@router.post("/{approval_id}/action")
async def take_approval_action(approval_id: str, data: ApprovalAction, current_user: User = Depends(get_current_user)):
    """Take action on an approval request"""
    db = get_db()
    
    approval = await db.approvals.find_one({"id": approval_id}, {"_id": 0})
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")
    
    if approval.get("approver_id") != current_user.id and current_user.role not in MANAGER_ROLES:
        raise HTTPException(status_code=403, detail="Not authorized to act on this approval")
    
    if approval.get("status") != "pending":
        raise HTTPException(status_code=400, detail="Approval is not pending")
    
    valid_actions = ["approve", "reject", "request_changes"]
    if data.action not in valid_actions:
        raise HTTPException(status_code=400, detail=f"Invalid action. Must be one of: {valid_actions}")
    
    new_status = "approved" if data.action == "approve" else ("rejected" if data.action == "reject" else "changes_requested")
    
    await db.approvals.update_one(
        {"id": approval_id},
        {
            "$set": {
                "status": new_status,
                "action_by": current_user.id,
                "action_at": datetime.now(timezone.utc).isoformat(),
                "action_comments": data.comments,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    return {"message": f"Approval {data.action}d", "status": new_status}


@router.get("/preview-chain")
async def preview_approval_chain(
    type: str,
    value: Optional[float] = None,
    current_user: User = Depends(get_current_user)
):
    """Preview the approval chain for a given type and value"""
    db = get_db()
    
    # Get approval configuration
    config = await db.approval_configs.find_one({"type": type}, {"_id": 0})
    
    if not config:
        return {
            "type": type,
            "chain": [{"level": 1, "role": "manager", "description": "Direct Manager"}],
            "message": "Default approval chain"
        }
    
    chain = config.get("chain", [])
    
    # Filter based on value thresholds if applicable
    if value and config.get("value_thresholds"):
        for threshold in config["value_thresholds"]:
            if value >= threshold["min_value"]:
                chain = threshold.get("chain", chain)
    
    return {
        "type": type,
        "value": value,
        "chain": chain
    }


# Scope Task Approvals
@router.post("/scope-task")
async def create_scope_task_approval(data: dict, current_user: User = Depends(get_current_user)):
    """Create a scope task approval request"""
    db = get_db()
    
    sow_id = data.get("sow_id")
    item_id = data.get("item_id")
    
    if not sow_id or not item_id:
        raise HTTPException(status_code=400, detail="sow_id and item_id are required")
    
    approval_id = str(uuid.uuid4())
    approval_doc = {
        "id": approval_id,
        "type": "scope_task",
        "sow_id": sow_id,
        "item_id": item_id,
        "description": data.get("description", ""),
        "status": "pending",
        "requester_id": current_user.id,
        "requester_name": current_user.full_name,
        "approver_id": data.get("approver_id"),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.scope_task_approvals.insert_one(approval_doc)
    approval_doc.pop("_id", None)
    return approval_doc


@router.get("/scope-task/sow/{sow_id}")
async def get_scope_approvals_by_sow(sow_id: str, current_user: User = Depends(get_current_user)):
    """Get all scope task approvals for a SOW"""
    db = get_db()
    
    approvals = await db.scope_task_approvals.find(
        {"sow_id": sow_id},
        {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    
    return approvals


@router.get("/scope-task/pending")
async def get_pending_scope_approvals(current_user: User = Depends(get_current_user)):
    """Get pending scope task approvals"""
    db = get_db()
    
    query = {"status": "pending"}
    
    if current_user.role not in MANAGER_ROLES:
        query["approver_id"] = current_user.id
    
    approvals = await db.scope_task_approvals.find(query, {"_id": 0}).to_list(100)
    return approvals


@router.post("/scope-task/{approval_id}/action")
async def scope_approval_action(approval_id: str, data: ApprovalAction, current_user: User = Depends(get_current_user)):
    """Take action on a scope task approval"""
    db = get_db()
    
    approval = await db.scope_task_approvals.find_one({"id": approval_id}, {"_id": 0})
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")
    
    if approval.get("status") != "pending":
        raise HTTPException(status_code=400, detail="Approval is not pending")
    
    new_status = "approved" if data.action == "approve" else "rejected"
    
    await db.scope_task_approvals.update_one(
        {"id": approval_id},
        {
            "$set": {
                "status": new_status,
                "action_by": current_user.id,
                "action_at": datetime.now(timezone.utc).isoformat(),
                "action_comments": data.comments,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    # Update SOW item status if approved
    if new_status == "approved":
        await db.sow.update_one(
            {"id": approval["sow_id"], "items.id": approval["item_id"]},
            {"$set": {"items.$.status": "approved"}}
        )
    
    return {"message": f"Scope task {data.action}d", "status": new_status}


@router.post("/scope-task/send-reminders")
async def send_scope_approval_reminders(data: dict, current_user: User = Depends(get_current_user)):
    """Send reminders for pending scope approvals"""
    db = get_db()
    
    if current_user.role not in MANAGER_ROLES:
        raise HTTPException(status_code=403, detail="Only managers can send reminders")
    
    pending = await db.scope_task_approvals.find({"status": "pending"}, {"_id": 0}).to_list(100)
    
    reminders_sent = 0
    for approval in pending:
        # Create reminder notification
        notification = {
            "id": str(uuid.uuid4()),
            "user_id": approval.get("approver_id"),
            "type": "approval_reminder",
            "title": "Pending Scope Approval",
            "message": f"You have a pending scope approval request",
            "reference_type": "scope_task_approval",
            "reference_id": approval["id"],
            "read": False,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.notifications.insert_one(notification)
        reminders_sent += 1
    
    return {"message": f"Sent {reminders_sent} reminders"}
