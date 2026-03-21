"""
Notification Service - Create and manage in-app notifications

This module provides the create_notification function used across the application.
"""

import uuid
from datetime import datetime, timezone
from routers.deps import get_db


async def create_notification(data: dict) -> dict:
    """
    Create an in-app notification.
    
    Args:
        data: dict with keys:
            - user_id: Target user's ID
            - title: Notification title
            - message: Notification body
            - type: Notification type (e.g., 'kickoff_request', 'expense_approved')
            - entity_type: Related entity type (optional)
            - entity_id: Related entity ID (optional)
            - priority: 'low', 'medium', 'high' (optional)
            - link: URL to navigate to (optional)
    
    Returns:
        The created notification document
    """
    db = get_db()
    
    notification = {
        "id": str(uuid.uuid4()),
        "user_id": data.get("user_id"),
        "title": data.get("title", "Notification"),
        "message": data.get("message", ""),
        "type": data.get("type", "general"),
        "entity_type": data.get("entity_type"),
        "entity_id": data.get("entity_id"),
        "reference_type": data.get("entity_type"),  # Alias for compatibility
        "reference_id": data.get("entity_id"),  # Alias for compatibility
        "priority": data.get("priority", "medium"),
        "link": data.get("link"),
        "is_read": False,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.notifications.insert_one(notification)
    
    return notification


async def mark_notification_read(notification_id: str, user_id: str) -> bool:
    """Mark a notification as read."""
    db = get_db()
    
    result = await db.notifications.update_one(
        {"id": notification_id, "user_id": user_id},
        {"$set": {"is_read": True, "read_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    return result.modified_count > 0


async def get_user_notifications(user_id: str, unread_only: bool = False, limit: int = 50) -> list:
    """Get notifications for a user."""
    db = get_db()
    
    query = {"user_id": user_id}
    if unread_only:
        query["is_read"] = False
    
    notifications = await db.notifications.find(
        query,
        {"_id": 0}
    ).sort("created_at", -1).limit(limit).to_list(limit)
    
    return notifications
