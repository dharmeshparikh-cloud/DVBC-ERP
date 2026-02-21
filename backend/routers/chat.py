"""
Internal Chat System Router
- Direct Messages (DMs)
- Group Channels
- Actionable Buttons with ERP Record Sync
- @mentions, file sharing, read receipts
- Real-time WebSocket support
"""
from fastapi import APIRouter, HTTPException, Depends, Query, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from bson import ObjectId
import uuid
import json
import logging

from websocket_manager import get_manager, ConnectionManager

router = APIRouter(prefix="/chat", tags=["Chat"])
logger = logging.getLogger(__name__)

# Pydantic Models
class MessageCreate(BaseModel):
    content: str
    message_type: str = "text"  # text, file, erp_record, action
    erp_record: Optional[Dict[str, Any]] = None  # {type: "leave_request", id: "xxx", data: {...}}
    action_buttons: Optional[List[Dict[str, str]]] = None  # [{label: "Approve", action: "approve"}, ...]
    mentions: Optional[List[str]] = None  # list of user_ids
    file_url: Optional[str] = None
    file_name: Optional[str] = None

class MessageResponse(BaseModel):
    id: str
    conversation_id: str
    sender_id: str
    sender_name: str
    sender_avatar: Optional[str] = None
    content: str
    message_type: str
    erp_record: Optional[Dict[str, Any]] = None
    action_buttons: Optional[List[Dict[str, str]]] = None
    action_taken: Optional[Dict[str, Any]] = None
    mentions: Optional[List[str]] = None
    file_url: Optional[str] = None
    file_name: Optional[str] = None
    read_by: List[str] = []
    created_at: datetime
    is_pinned: bool = False

class ConversationCreate(BaseModel):
    name: Optional[str] = None  # Required for groups, optional for DMs
    type: str = "dm"  # dm or group
    participant_ids: List[str]
    description: Optional[str] = None

class ConversationResponse(BaseModel):
    id: str
    name: Optional[str] = None
    type: str
    participants: List[Dict[str, Any]]
    created_by: str
    created_at: datetime
    last_message: Optional[Dict[str, Any]] = None
    unread_count: int = 0

class ActionExecute(BaseModel):
    action: str  # approve, reject, comment, etc.
    comment: Optional[str] = None


def get_db():
    from server import db
    return db


# ==================== CONVERSATIONS ====================

@router.post("/conversations", response_model=dict)
async def create_conversation(data: ConversationCreate, db=Depends(get_db)):
    """Create a new DM or group conversation"""
    conversation_id = str(uuid.uuid4())
    
    # For DMs, check if conversation already exists between these two users
    if data.type == "dm" and len(data.participant_ids) == 2:
        existing = await db.chat_conversations.find_one({
            "type": "dm",
            "participant_ids": {"$all": data.participant_ids}
        })
        if existing:
            existing["id"] = str(existing["_id"])
            del existing["_id"]
            return existing
    
    # Get participant details
    participants = []
    for pid in data.participant_ids:
        user = await db.users.find_one({"id": pid})
        if user:
            participants.append({
                "id": pid,
                "name": user.get("full_name", "Unknown"),
                "email": user.get("email"),
                "avatar": user.get("avatar_url")
            })
    
    conversation = {
        "id": conversation_id,
        "name": data.name if data.type == "group" else None,
        "type": data.type,
        "participant_ids": data.participant_ids,
        "participants": participants,
        "description": data.description,
        "created_by": data.participant_ids[0],  # First participant is creator
        "created_at": datetime.now(timezone.utc),
        "last_message": None,
        "last_activity": datetime.now(timezone.utc)
    }
    
    await db.chat_conversations.insert_one(conversation)
    del conversation["_id"]
    return conversation


@router.get("/conversations", response_model=List[dict])
async def get_conversations(
    user_id: str = Query(...),
    db=Depends(get_db)
):
    """Get all conversations for a user"""
    conversations = await db.chat_conversations.find({
        "participant_ids": user_id
    }).sort("last_activity", -1).to_list(100)
    
    result = []
    for conv in conversations:
        # Get unread count
        unread = await db.chat_messages.count_documents({
            "conversation_id": conv["id"],
            "sender_id": {"$ne": user_id},
            "read_by": {"$nin": [user_id]}
        })
        
        conv["unread_count"] = unread
        conv["id"] = conv.get("id", str(conv["_id"]))
        if "_id" in conv:
            del conv["_id"]
        result.append(conv)
    
    return result


@router.get("/conversations/{conversation_id}", response_model=dict)
async def get_conversation(conversation_id: str, db=Depends(get_db)):
    """Get a specific conversation"""
    conv = await db.chat_conversations.find_one({"id": conversation_id})
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    conv["id"] = conv.get("id", str(conv["_id"]))
    if "_id" in conv:
        del conv["_id"]
    return conv


# ==================== MESSAGES ====================

@router.post("/conversations/{conversation_id}/messages", response_model=dict)
async def send_message(
    conversation_id: str,
    data: MessageCreate,
    sender_id: str = Query(...),
    db=Depends(get_db)
):
    """Send a message in a conversation"""
    # Verify conversation exists
    conv = await db.chat_conversations.find_one({"id": conversation_id})
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Get sender info
    sender = await db.users.find_one({"id": sender_id})
    if not sender:
        raise HTTPException(status_code=404, detail="Sender not found")
    
    message_id = str(uuid.uuid4())
    message = {
        "id": message_id,
        "conversation_id": conversation_id,
        "sender_id": sender_id,
        "sender_name": sender.get("full_name", "Unknown"),
        "sender_avatar": sender.get("avatar_url"),
        "content": data.content,
        "message_type": data.message_type,
        "erp_record": data.erp_record,
        "action_buttons": data.action_buttons,
        "action_taken": None,
        "mentions": data.mentions or [],
        "file_url": data.file_url,
        "file_name": data.file_name,
        "read_by": [sender_id],
        "created_at": datetime.now(timezone.utc),
        "is_pinned": False
    }
    
    await db.chat_messages.insert_one(message)
    
    # Update conversation last activity
    await db.chat_conversations.update_one(
        {"id": conversation_id},
        {
            "$set": {
                "last_message": {
                    "content": data.content[:100],
                    "sender_name": sender.get("full_name"),
                    "created_at": message["created_at"]
                },
                "last_activity": message["created_at"]
            }
        }
    )
    
    # Create notifications for mentions
    if data.mentions:
        for mentioned_id in data.mentions:
            if mentioned_id != sender_id:
                notification = {
                    "id": str(uuid.uuid4()),
                    "user_id": mentioned_id,
                    "type": "chat_mention",
                    "title": f"{sender.get('full_name')} mentioned you",
                    "message": data.content[:100],
                    "link": f"/chat?conversation={conversation_id}",
                    "read": False,
                    "created_at": datetime.now(timezone.utc)
                }
                await db.notifications.insert_one(notification)
    
    del message["_id"]
    
    # Broadcast message via WebSocket to all conversation participants
    ws_manager = get_manager()
    ws_message = {
        "type": "new_message",
        "conversation_id": conversation_id,
        "message": {
            **message,
            "created_at": message["created_at"].isoformat() if isinstance(message["created_at"], datetime) else message["created_at"]
        }
    }
    await ws_manager.broadcast_to_users(ws_message, conv.get("participant_ids", []), exclude_user=sender_id)
    
    return message


@router.get("/conversations/{conversation_id}/messages", response_model=List[dict])
async def get_messages(
    conversation_id: str,
    limit: int = Query(50, le=100),
    before: Optional[str] = None,
    db=Depends(get_db)
):
    """Get messages in a conversation"""
    query = {"conversation_id": conversation_id}
    
    if before:
        # Get messages before a specific message
        ref_msg = await db.chat_messages.find_one({"id": before})
        if ref_msg:
            query["created_at"] = {"$lt": ref_msg["created_at"]}
    
    messages = await db.chat_messages.find(query).sort("created_at", -1).limit(limit).to_list(limit)
    
    result = []
    for msg in messages:
        msg["id"] = msg.get("id", str(msg["_id"]))
        if "_id" in msg:
            del msg["_id"]
        result.append(msg)
    
    return list(reversed(result))  # Return in chronological order


@router.post("/messages/{message_id}/read")
async def mark_as_read(
    message_id: str,
    user_id: str = Query(...),
    db=Depends(get_db)
):
    """Mark a message as read"""
    await db.chat_messages.update_one(
        {"id": message_id},
        {"$addToSet": {"read_by": user_id}}
    )
    return {"status": "ok"}


@router.post("/conversations/{conversation_id}/read-all")
async def mark_all_as_read(
    conversation_id: str,
    user_id: str = Query(...),
    db=Depends(get_db)
):
    """Mark all messages in a conversation as read"""
    await db.chat_messages.update_many(
        {"conversation_id": conversation_id},
        {"$addToSet": {"read_by": user_id}}
    )
    return {"status": "ok"}


@router.post("/messages/{message_id}/pin")
async def toggle_pin(message_id: str, db=Depends(get_db)):
    """Toggle pin status of a message"""
    msg = await db.chat_messages.find_one({"id": message_id})
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")
    
    new_status = not msg.get("is_pinned", False)
    await db.chat_messages.update_one(
        {"id": message_id},
        {"$set": {"is_pinned": new_status}}
    )
    return {"is_pinned": new_status}


# ==================== ERP RECORD ACTIONS ====================

@router.post("/messages/{message_id}/action")
async def execute_action(
    message_id: str,
    data: ActionExecute,
    user_id: str = Query(...),
    db=Depends(get_db)
):
    """Execute an action on an ERP record shared in chat"""
    msg = await db.chat_messages.find_one({"id": message_id})
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")
    
    if not msg.get("erp_record"):
        raise HTTPException(status_code=400, detail="Message has no ERP record")
    
    erp_record = msg["erp_record"]
    record_type = erp_record.get("type")
    record_id = erp_record.get("id")
    
    user = await db.users.find_one({"id": user_id})
    user_name = user.get("full_name", "Unknown") if user else "Unknown"
    
    action_result = {
        "action": data.action,
        "executed_by": user_id,
        "executed_by_name": user_name,
        "executed_at": datetime.now(timezone.utc),
        "comment": data.comment
    }
    
    # Execute action based on record type
    if record_type == "leave_request":
        if data.action == "approve":
            await db.leave_requests.update_one(
                {"id": record_id},
                {"$set": {"status": "approved", "approved_by": user_id, "approved_at": datetime.now(timezone.utc)}}
            )
            action_result["success"] = True
            action_result["message"] = "Leave request approved"
        elif data.action == "reject":
            await db.leave_requests.update_one(
                {"id": record_id},
                {"$set": {"status": "rejected", "rejected_by": user_id, "rejected_at": datetime.now(timezone.utc), "rejection_reason": data.comment}}
            )
            action_result["success"] = True
            action_result["message"] = "Leave request rejected"
    
    elif record_type == "expense":
        if data.action == "approve":
            await db.expenses.update_one(
                {"id": record_id},
                {"$set": {"status": "approved", "approved_by": user_id, "approved_at": datetime.now(timezone.utc)}}
            )
            action_result["success"] = True
            action_result["message"] = "Expense approved"
        elif data.action == "reject":
            await db.expenses.update_one(
                {"id": record_id},
                {"$set": {"status": "rejected", "rejected_by": user_id, "rejection_reason": data.comment}}
            )
            action_result["success"] = True
            action_result["message"] = "Expense rejected"
    
    elif record_type == "kickoff_request":
        if data.action == "approve":
            await db.kickoff_requests.update_one(
                {"id": record_id},
                {"$set": {"status": "approved", "approved_by": user_id, "approved_at": datetime.now(timezone.utc)}}
            )
            action_result["success"] = True
            action_result["message"] = "Kickoff approved"
    
    # Update message with action taken
    await db.chat_messages.update_one(
        {"id": message_id},
        {"$set": {"action_taken": action_result}}
    )
    
    # Send notification to original requester
    if erp_record.get("requester_id"):
        notification = {
            "id": str(uuid.uuid4()),
            "user_id": erp_record["requester_id"],
            "type": "action_taken",
            "title": f"Your {record_type.replace('_', ' ')} was {data.action}ed",
            "message": f"Action taken by {user_name}" + (f": {data.comment}" if data.comment else ""),
            "link": f"/chat?conversation={msg['conversation_id']}",
            "read": False,
            "created_at": datetime.now(timezone.utc)
        }
        await db.notifications.insert_one(notification)
    
    return action_result


# ==================== GROUP MANAGEMENT ====================

@router.post("/conversations/{conversation_id}/participants")
async def add_participants(
    conversation_id: str,
    participant_ids: List[str],
    db=Depends(get_db)
):
    """Add participants to a group conversation"""
    conv = await db.chat_conversations.find_one({"id": conversation_id})
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    if conv["type"] != "group":
        raise HTTPException(status_code=400, detail="Can only add participants to group conversations")
    
    # Get new participant details
    new_participants = []
    for pid in participant_ids:
        if pid not in conv["participant_ids"]:
            user = await db.users.find_one({"id": pid})
            if user:
                new_participants.append({
                    "id": pid,
                    "name": user.get("full_name", "Unknown"),
                    "email": user.get("email"),
                    "avatar": user.get("avatar_url")
                })
    
    await db.chat_conversations.update_one(
        {"id": conversation_id},
        {
            "$addToSet": {"participant_ids": {"$each": participant_ids}},
            "$push": {"participants": {"$each": new_participants}}
        }
    )
    
    return {"added": len(new_participants)}


@router.delete("/conversations/{conversation_id}/participants/{participant_id}")
async def remove_participant(
    conversation_id: str,
    participant_id: str,
    db=Depends(get_db)
):
    """Remove a participant from a group conversation"""
    conv = await db.chat_conversations.find_one({"id": conversation_id})
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    if conv["type"] != "group":
        raise HTTPException(status_code=400, detail="Can only remove participants from group conversations")
    
    await db.chat_conversations.update_one(
        {"id": conversation_id},
        {
            "$pull": {
                "participant_ids": participant_id,
                "participants": {"id": participant_id}
            }
        }
    )
    
    return {"status": "removed"}


# ==================== SEARCH ====================

@router.get("/search")
async def search_messages(
    q: str = Query(..., min_length=2),
    user_id: str = Query(...),
    db=Depends(get_db)
):
    """Search messages across all conversations the user is part of"""
    # Get user's conversations
    user_convs = await db.chat_conversations.find(
        {"participant_ids": user_id}
    ).to_list(100)
    conv_ids = [c["id"] for c in user_convs]
    
    # Search messages
    messages = await db.chat_messages.find({
        "conversation_id": {"$in": conv_ids},
        "content": {"$regex": q, "$options": "i"}
    }).sort("created_at", -1).limit(20).to_list(20)
    
    result = []
    for msg in messages:
        msg["id"] = msg.get("id", str(msg["_id"]))
        if "_id" in msg:
            del msg["_id"]
        result.append(msg)
    
    return result


# ==================== USERS LIST ====================

@router.get("/users")
async def get_chat_users(
    search: Optional[str] = None,
    db=Depends(get_db)
):
    """Get list of users available for chat"""
    query = {"is_active": {"$ne": False}}
    if search:
        query["$or"] = [
            {"full_name": {"$regex": search, "$options": "i"}},
            {"email": {"$regex": search, "$options": "i"}}
        ]
    
    users = await db.users.find(query, {"_id": 0, "id": 1, "full_name": 1, "email": 1, "role": 1, "department": 1, "avatar_url": 1}).limit(50).to_list(50)
    return users


# ==================== WEBSOCKET ====================

@router.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    """WebSocket endpoint for real-time chat updates"""
    ws_manager = get_manager()
    await ws_manager.connect(websocket, user_id)
    
    try:
        # Send initial connection success message
        await websocket.send_json({
            "type": "connected",
            "user_id": user_id,
            "message": "Connected to chat WebSocket"
        })
        
        while True:
            # Receive and process messages from client
            data = await websocket.receive_json()
            
            if data.get("type") == "subscribe":
                # Subscribe to a conversation
                conversation_id = data.get("conversation_id")
                if conversation_id:
                    ws_manager.subscribe_to_conversation(user_id, conversation_id)
                    await websocket.send_json({
                        "type": "subscribed",
                        "conversation_id": conversation_id
                    })
            
            elif data.get("type") == "unsubscribe":
                # Unsubscribe from a conversation
                conversation_id = data.get("conversation_id")
                if conversation_id:
                    ws_manager.unsubscribe_from_conversation(user_id, conversation_id)
                    await websocket.send_json({
                        "type": "unsubscribed",
                        "conversation_id": conversation_id
                    })
            
            elif data.get("type") == "ping":
                # Keep-alive ping
                await websocket.send_json({"type": "pong"})
            
            elif data.get("type") == "typing":
                # Broadcast typing indicator
                conversation_id = data.get("conversation_id")
                if conversation_id:
                    await ws_manager.broadcast_to_users(
                        {
                            "type": "typing",
                            "conversation_id": conversation_id,
                            "user_id": user_id,
                            "user_name": data.get("user_name", "Someone")
                        },
                        data.get("participant_ids", []),
                        exclude_user=user_id
                    )
            
            elif data.get("type") == "read":
                # Broadcast read receipt
                conversation_id = data.get("conversation_id")
                message_id = data.get("message_id")
                if conversation_id:
                    await ws_manager.broadcast_to_users(
                        {
                            "type": "read",
                            "conversation_id": conversation_id,
                            "message_id": message_id,
                            "user_id": user_id
                        },
                        data.get("participant_ids", []),
                        exclude_user=user_id
                    )
    
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, user_id)
        logger.info(f"WebSocket disconnected for user {user_id}")
    except Exception as e:
        logger.error(f"WebSocket error for user {user_id}: {e}")
        ws_manager.disconnect(websocket, user_id)


@router.get("/online-users")
async def get_online_users():
    """Get list of currently online users"""
    ws_manager = get_manager()
    return {"online_users": ws_manager.get_online_users()}


# ==================== ADMIN AUDIT & CONTROL ====================

@router.get("/admin/all-conversations")
async def admin_get_all_conversations(
    admin_id: str = Query(...),
    limit: int = Query(100, le=500),
    db=Depends(get_db)
):
    """Admin only: Get all conversations for audit purposes"""
    # Verify admin role
    admin = await db.users.find_one({"id": admin_id})
    if not admin or admin.get("role", "").lower() != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    conversations = await db.chat_conversations.find({}).sort("last_activity", -1).limit(limit).to_list(limit)
    
    result = []
    for conv in conversations:
        conv["id"] = conv.get("id", str(conv["_id"]))
        if "_id" in conv:
            del conv["_id"]
        
        # Get message count
        msg_count = await db.chat_messages.count_documents({"conversation_id": conv["id"]})
        conv["message_count"] = msg_count
        result.append(conv)
    
    return result


@router.get("/admin/conversation/{conversation_id}/messages")
async def admin_get_conversation_messages(
    conversation_id: str,
    admin_id: str = Query(...),
    limit: int = Query(100, le=500),
    db=Depends(get_db)
):
    """Admin only: View all messages in a conversation"""
    # Verify admin role
    admin = await db.users.find_one({"id": admin_id})
    if not admin or admin.get("role", "").lower() != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    messages = await db.chat_messages.find(
        {"conversation_id": conversation_id}
    ).sort("created_at", 1).limit(limit).to_list(limit)
    
    result = []
    for msg in messages:
        msg["id"] = msg.get("id", str(msg["_id"]))
        if "_id" in msg:
            del msg["_id"]
        result.append(msg)
    
    # Log audit action
    audit_log = {
        "id": str(uuid.uuid4()),
        "admin_id": admin_id,
        "action": "view_chat_messages",
        "conversation_id": conversation_id,
        "timestamp": datetime.now(timezone.utc)
    }
    await db.admin_audit_logs.insert_one(audit_log)
    
    return result


@router.post("/admin/restrict-user")
async def admin_restrict_user(
    admin_id: str = Query(...),
    target_user_id: str = Query(...),
    restrict_chat: bool = Query(True),
    restrict_ai: bool = Query(True),
    reason: str = Query(...),
    db=Depends(get_db)
):
    """Admin only: Restrict a user from chat and/or AI features"""
    # Verify admin role
    admin = await db.users.find_one({"id": admin_id})
    if not admin or admin.get("role", "").lower() != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Update user restrictions
    update_data = {
        "chat_restricted": restrict_chat,
        "ai_restricted": restrict_ai,
        "restriction_reason": reason,
        "restricted_by": admin_id,
        "restricted_at": datetime.now(timezone.utc)
    }
    
    result = await db.users.update_one(
        {"id": target_user_id},
        {"$set": update_data}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Log audit action
    audit_log = {
        "id": str(uuid.uuid4()),
        "admin_id": admin_id,
        "action": "restrict_user",
        "target_user_id": target_user_id,
        "restrict_chat": restrict_chat,
        "restrict_ai": restrict_ai,
        "reason": reason,
        "timestamp": datetime.now(timezone.utc)
    }
    await db.admin_audit_logs.insert_one(audit_log)
    
    # Disconnect user from WebSocket if chat restricted
    if restrict_chat:
        ws_manager = get_manager()
        if target_user_id in ws_manager.active_connections:
            for conn in ws_manager.active_connections[target_user_id]:
                try:
                    await conn.send_json({
                        "type": "restricted",
                        "message": "Your chat access has been restricted by admin."
                    })
                    await conn.close()
                except:
                    pass
            ws_manager.disconnect(None, target_user_id)
    
    return {
        "status": "restricted",
        "user_id": target_user_id,
        "chat_restricted": restrict_chat,
        "ai_restricted": restrict_ai
    }


@router.post("/admin/unrestrict-user")
async def admin_unrestrict_user(
    admin_id: str = Query(...),
    target_user_id: str = Query(...),
    db=Depends(get_db)
):
    """Admin only: Remove restrictions from a user"""
    # Verify admin role
    admin = await db.users.find_one({"id": admin_id})
    if not admin or admin.get("role", "").lower() != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    result = await db.users.update_one(
        {"id": target_user_id},
        {"$set": {
            "chat_restricted": False,
            "ai_restricted": False,
            "restriction_reason": None,
            "unrestricted_by": admin_id,
            "unrestricted_at": datetime.now(timezone.utc)
        }}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Log audit action
    audit_log = {
        "id": str(uuid.uuid4()),
        "admin_id": admin_id,
        "action": "unrestrict_user",
        "target_user_id": target_user_id,
        "timestamp": datetime.now(timezone.utc)
    }
    await db.admin_audit_logs.insert_one(audit_log)
    
    return {"status": "unrestricted", "user_id": target_user_id}


@router.get("/admin/restricted-users")
async def admin_get_restricted_users(
    admin_id: str = Query(...),
    db=Depends(get_db)
):
    """Admin only: Get list of all restricted users"""
    # Verify admin role
    admin = await db.users.find_one({"id": admin_id})
    if not admin or admin.get("role", "").lower() != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    restricted = await db.users.find({
        "$or": [
            {"chat_restricted": True},
            {"ai_restricted": True}
        ]
    }, {"_id": 0, "password": 0, "hashed_password": 0}).to_list(100)
    
    return restricted


@router.get("/admin/audit-logs")
async def admin_get_audit_logs(
    admin_id: str = Query(...),
    limit: int = Query(100, le=500),
    db=Depends(get_db)
):
    """Admin only: Get admin audit logs"""
    # Verify admin role
    admin = await db.users.find_one({"id": admin_id})
    if not admin or admin.get("role", "").lower() != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    logs = await db.admin_audit_logs.find({}).sort("timestamp", -1).limit(limit).to_list(limit)
    
    result = []
    for log in logs:
        if "_id" in log:
            del log["_id"]
        result.append(log)
    
    return result


