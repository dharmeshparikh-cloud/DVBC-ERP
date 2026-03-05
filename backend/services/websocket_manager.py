"""
WebSocket Manager for Real-Time Notifications
==============================================

Provides real-time updates across the ERP system.
When data changes, connected clients are notified instantly.

Usage:
    # In any router after data change:
    await ws_manager.broadcast_update("employees", "update", {"id": "123"})
    
    # Client receives:
    {
        "type": "data_update",
        "entity": "employees",
        "action": "update",
        "data": {"id": "123"},
        "timestamp": "2025-12-05T10:30:00Z"
    }
"""

import asyncio
import json
import logging
from typing import Dict, Set, List, Any, Optional
from datetime import datetime, timezone
from fastapi import WebSocket, WebSocketDisconnect
from dataclasses import dataclass, field

logger = logging.getLogger("websocket_manager")


@dataclass
class ConnectionInfo:
    """Information about a WebSocket connection."""
    websocket: WebSocket
    user_id: str
    subscriptions: Set[str] = field(default_factory=set)
    connected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_ping: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class WebSocketManager:
    """
    Manages WebSocket connections for real-time updates.
    Supports:
    - User-specific connections
    - Topic subscriptions (e.g., "employees", "leads", "notifications")
    - Broadcast to all or specific users
    - Automatic cleanup of dead connections
    """
    
    def __init__(self):
        # user_id -> ConnectionInfo
        self._connections: Dict[str, ConnectionInfo] = {}
        # topic -> set of user_ids
        self._subscriptions: Dict[str, Set[str]] = {}
        self._stats = {
            "total_connections": 0,
            "total_messages": 0,
            "total_broadcasts": 0
        }
    
    async def connect(self, websocket: WebSocket, user_id: str) -> bool:
        """
        Accept a new WebSocket connection.
        """
        try:
            await websocket.accept()
            
            # Close existing connection for this user if any
            if user_id in self._connections:
                old_ws = self._connections[user_id].websocket
                try:
                    await old_ws.close(code=1000, reason="New connection established")
                except Exception:
                    pass
            
            self._connections[user_id] = ConnectionInfo(
                websocket=websocket,
                user_id=user_id
            )
            self._stats["total_connections"] += 1
            
            logger.info(f"User {user_id} connected via WebSocket. Total: {len(self._connections)}")
            
            # Send welcome message
            await self.send_to_user(user_id, {
                "type": "connected",
                "message": "WebSocket connection established",
                "user_id": user_id,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            
            return True
        except Exception as e:
            logger.error(f"WebSocket connect error for user {user_id}: {e}")
            return False
    
    def disconnect(self, user_id: str):
        """
        Remove a disconnected user.
        """
        if user_id in self._connections:
            conn = self._connections[user_id]
            
            # Remove from all subscriptions
            for topic in conn.subscriptions:
                if topic in self._subscriptions:
                    self._subscriptions[topic].discard(user_id)
            
            del self._connections[user_id]
            logger.info(f"User {user_id} disconnected. Total: {len(self._connections)}")
    
    async def subscribe(self, user_id: str, topics: List[str]):
        """
        Subscribe a user to specific topics for updates.
        """
        if user_id not in self._connections:
            return
        
        conn = self._connections[user_id]
        for topic in topics:
            conn.subscriptions.add(topic)
            if topic not in self._subscriptions:
                self._subscriptions[topic] = set()
            self._subscriptions[topic].add(user_id)
        
        logger.debug(f"User {user_id} subscribed to: {topics}")
    
    async def unsubscribe(self, user_id: str, topics: List[str]):
        """
        Unsubscribe a user from topics.
        """
        if user_id not in self._connections:
            return
        
        conn = self._connections[user_id]
        for topic in topics:
            conn.subscriptions.discard(topic)
            if topic in self._subscriptions:
                self._subscriptions[topic].discard(user_id)
    
    async def send_to_user(self, user_id: str, message: Dict) -> bool:
        """
        Send a message to a specific user.
        Returns True if sent successfully.
        """
        if user_id not in self._connections:
            return False
        
        conn = self._connections[user_id]
        try:
            await conn.websocket.send_json(message)
            self._stats["total_messages"] += 1
            return True
        except Exception as e:
            logger.warning(f"Failed to send to user {user_id}: {e}")
            self.disconnect(user_id)
            return False
    
    async def broadcast(self, message: Dict, exclude_user: str = None):
        """
        Broadcast a message to all connected users.
        """
        disconnected = []
        
        for user_id, conn in self._connections.items():
            if user_id == exclude_user:
                continue
            
            try:
                await conn.websocket.send_json(message)
            except Exception:
                disconnected.append(user_id)
        
        # Cleanup disconnected
        for user_id in disconnected:
            self.disconnect(user_id)
        
        self._stats["total_broadcasts"] += 1
    
    async def broadcast_to_topic(
        self, 
        topic: str, 
        message: Dict, 
        exclude_user: str = None
    ):
        """
        Broadcast a message to all users subscribed to a topic.
        """
        if topic not in self._subscriptions:
            return
        
        disconnected = []
        
        for user_id in self._subscriptions[topic]:
            if user_id == exclude_user:
                continue
            
            if user_id not in self._connections:
                disconnected.append(user_id)
                continue
            
            conn = self._connections[user_id]
            try:
                await conn.websocket.send_json(message)
            except Exception:
                disconnected.append(user_id)
        
        # Cleanup
        for user_id in disconnected:
            self._subscriptions[topic].discard(user_id)
            if user_id in self._connections:
                self.disconnect(user_id)
    
    async def broadcast_update(
        self,
        entity: str,
        action: str,
        data: Dict = None,
        exclude_user: str = None
    ):
        """
        Broadcast a data update event.
        This is the main method to call when data changes.
        
        Args:
            entity: Type of data (employees, leads, onboarding, etc.)
            action: What happened (create, update, delete, approve, etc.)
            data: Relevant data (e.g., {"id": "123"})
            exclude_user: User to exclude (usually the one who made the change)
        """
        message = {
            "type": "data_update",
            "entity": entity,
            "action": action,
            "data": data or {},
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # Broadcast to users subscribed to this entity
        await self.broadcast_to_topic(entity, message, exclude_user)
        
        # Also broadcast to "all" subscribers
        await self.broadcast_to_topic("all", message, exclude_user)
        
        logger.debug(f"Broadcast update: {entity}.{action}")
    
    async def send_notification(
        self,
        user_id: str,
        title: str,
        message: str,
        notification_type: str = "info",
        data: Dict = None
    ):
        """
        Send a notification to a specific user.
        """
        notification = {
            "type": "notification",
            "notification_type": notification_type,
            "title": title,
            "message": message,
            "data": data or {},
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        await self.send_to_user(user_id, notification)
    
    async def send_notification_batch(
        self,
        user_ids: List[str],
        title: str,
        message: str,
        notification_type: str = "info",
        data: Dict = None
    ):
        """
        Send a notification to multiple users.
        """
        for user_id in user_ids:
            await self.send_notification(user_id, title, message, notification_type, data)
    
    async def ping_all(self):
        """
        Send ping to all connections to keep them alive.
        Call this periodically (e.g., every 30 seconds).
        """
        disconnected = []
        
        for user_id, conn in self._connections.items():
            try:
                await conn.websocket.send_json({
                    "type": "ping",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
                conn.last_ping = datetime.now(timezone.utc)
            except Exception:
                disconnected.append(user_id)
        
        for user_id in disconnected:
            self.disconnect(user_id)
    
    def get_stats(self) -> Dict:
        """Get WebSocket manager statistics."""
        return {
            "active_connections": len(self._connections),
            "subscriptions": {
                topic: len(users) 
                for topic, users in self._subscriptions.items()
            },
            "stats": self._stats
        }
    
    def get_connected_users(self) -> List[str]:
        """Get list of connected user IDs."""
        return list(self._connections.keys())
    
    def is_connected(self, user_id: str) -> bool:
        """Check if a user is connected."""
        return user_id in self._connections


# Global WebSocket manager instance
ws_manager = WebSocketManager()


# ===========================================
# HELPER FUNCTIONS FOR ROUTERS
# ===========================================

async def notify_employee_update(employee_id: str, action: str = "update", exclude_user: str = None):
    """Notify clients about employee data change."""
    await ws_manager.broadcast_update(
        entity="employees",
        action=action,
        data={"employee_id": employee_id},
        exclude_user=exclude_user
    )

async def notify_lead_update(lead_id: str, action: str = "update", exclude_user: str = None):
    """Notify clients about lead data change."""
    await ws_manager.broadcast_update(
        entity="leads",
        action=action,
        data={"lead_id": lead_id},
        exclude_user=exclude_user
    )

async def notify_onboarding_update(submission_id: str, action: str = "update", exclude_user: str = None):
    """Notify clients about onboarding change."""
    await ws_manager.broadcast_update(
        entity="onboarding",
        action=action,
        data={"submission_id": submission_id},
        exclude_user=exclude_user
    )

async def notify_approval_update(approval_type: str, item_id: str, action: str, exclude_user: str = None):
    """Notify clients about approval action."""
    await ws_manager.broadcast_update(
        entity="approvals",
        action=action,
        data={"type": approval_type, "id": item_id},
        exclude_user=exclude_user
    )

async def notify_dashboard_refresh(exclude_user: str = None):
    """Notify clients to refresh dashboard stats."""
    await ws_manager.broadcast_update(
        entity="dashboard",
        action="refresh",
        data={},
        exclude_user=exclude_user
    )
