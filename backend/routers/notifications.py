"""
Notifications Router - User notifications, read status, and actions.
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Optional, List
from datetime import datetime, timezone
from .deps import get_db
from .models import User
from .auth import get_current_user

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("")
async def get_notifications(
    limit: int = 50,
    unread_only: bool = False,
    current_user: User = Depends(get_current_user)
):
    """Get user notifications"""
    db = get_db()
    
    query = {"user_id": current_user.id}
    if unread_only:
        query["read"] = False
    
    notifications = await db.notifications.find(
        query, {"_id": 0}
    ).sort("created_at", -1).to_list(limit)
    
    return notifications


@router.patch("/{notification_id}/read")
async def mark_notification_read(notification_id: str, current_user: User = Depends(get_current_user)):
    """Mark a notification as read"""
    db = get_db()
    
    result = await db.notifications.update_one(
        {"id": notification_id, "user_id": current_user.id},
        {
            "$set": {
                "read": True,
                "read_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    return {"message": "Notification marked as read"}


@router.get("/unread-count")
async def get_unread_count(current_user: User = Depends(get_current_user)):
    """Get count of unread notifications"""
    db = get_db()
    
    count = await db.notifications.count_documents({
        "user_id": current_user.id,
        "read": False
    })
    
    return {"unread_count": count}


@router.patch("/mark-all-read")
async def mark_all_read(current_user: User = Depends(get_current_user)):
    """Mark all notifications as read"""
    db = get_db()
    
    result = await db.notifications.update_many(
        {"user_id": current_user.id, "read": False},
        {
            "$set": {
                "read": True,
                "read_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    return {"message": f"Marked {result.modified_count} notifications as read"}


@router.patch("/{notification_id}/action")
async def notification_action(notification_id: str, data: dict, current_user: User = Depends(get_current_user)):
    """Record action taken on a notification"""
    db = get_db()
    
    action = data.get("action", "acknowledged")
    
    result = await db.notifications.update_one(
        {"id": notification_id, "user_id": current_user.id},
        {
            "$set": {
                "action_taken": action,
                "action_at": datetime.now(timezone.utc).isoformat(),
                "read": True,
                "read_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    return {"message": "Action recorded", "action": action}
