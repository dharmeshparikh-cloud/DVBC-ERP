"""
WebSocket Router for Real-Time Updates
=======================================

Endpoints:
- WS /ws/{user_id} - Main WebSocket connection
- GET /ws/stats - WebSocket manager statistics
"""

import asyncio
import json
import logging
from typing import Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Depends, Query
from services.websocket_manager import ws_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws", tags=["WebSocket"])


@router.websocket("/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    """
    WebSocket endpoint for real-time updates.
    
    Client should:
    1. Connect with user_id
    2. Optionally send subscription message to filter updates
    3. Listen for incoming messages
    
    Message types received:
    - connected: Connection established
    - ping: Keep-alive ping
    - data_update: Data change notification
    - notification: User notification
    
    Client can send:
    - {"type": "subscribe", "topics": ["employees", "leads"]}
    - {"type": "unsubscribe", "topics": ["employees"]}
    - {"type": "pong"} - Response to ping
    """
    connected = await ws_manager.connect(websocket, user_id)
    if not connected:
        return
    
    try:
        # Default subscriptions based on common needs
        await ws_manager.subscribe(user_id, ["dashboard", "notifications"])
        
        while True:
            try:
                # Wait for messages from client
                data = await websocket.receive_text()
                message = json.loads(data)
                
                msg_type = message.get("type")
                
                if msg_type == "subscribe":
                    topics = message.get("topics", [])
                    if topics:
                        await ws_manager.subscribe(user_id, topics)
                        await websocket.send_json({
                            "type": "subscribed",
                            "topics": topics
                        })
                
                elif msg_type == "unsubscribe":
                    topics = message.get("topics", [])
                    if topics:
                        await ws_manager.unsubscribe(user_id, topics)
                        await websocket.send_json({
                            "type": "unsubscribed",
                            "topics": topics
                        })
                
                elif msg_type == "pong":
                    # Client responded to ping - connection is alive
                    pass
                
                elif msg_type == "ping":
                    # Client is checking connection
                    await websocket.send_json({"type": "pong"})
                
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON from user {user_id}")
            except Exception as e:
                logger.error(f"Error processing message from {user_id}: {e}")
                break
                
    except WebSocketDisconnect:
        logger.info(f"User {user_id} disconnected normally")
    except Exception as e:
        logger.error(f"WebSocket error for user {user_id}: {e}")
    finally:
        ws_manager.disconnect(user_id)


@router.get("/stats")
async def get_websocket_stats():
    """Get WebSocket manager statistics."""
    return ws_manager.get_stats()


@router.get("/connections")
async def get_connected_users():
    """Get list of connected users."""
    return {
        "connected_users": ws_manager.get_connected_users(),
        "count": len(ws_manager.get_connected_users())
    }


@router.post("/broadcast")
async def broadcast_message(
    message: str = Query(..., description="Message to broadcast"),
    topic: Optional[str] = Query(None, description="Topic to broadcast to (optional)")
):
    """
    Broadcast a message to connected clients.
    Admin-only endpoint for testing or announcements.
    """
    msg = {
        "type": "announcement",
        "message": message
    }
    
    if topic:
        await ws_manager.broadcast_to_topic(topic, msg)
    else:
        await ws_manager.broadcast(msg)
    
    return {"success": True, "message": "Broadcast sent"}


# Background task for periodic pings
async def ping_task():
    """Send periodic pings to keep connections alive."""
    while True:
        await asyncio.sleep(30)  # Every 30 seconds
        try:
            await ws_manager.ping_all()
        except Exception as e:
            logger.error(f"Ping task error: {e}")


# Start ping task when module loads
_ping_task = None

def start_ping_task():
    """Start the background ping task."""
    global _ping_task
    if _ping_task is None:
        _ping_task = asyncio.create_task(ping_task())
        logger.info("WebSocket ping task started")
