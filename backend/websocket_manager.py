"""
WebSocket Manager for Real-time Chat & Notifications
Handles connections, broadcasting, and message delivery
"""
from fastapi import WebSocket
from typing import Dict, List, Set
import json
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections for real-time chat and notifications"""
    
    def __init__(self):
        # Map of user_id -> list of WebSocket connections (user can have multiple tabs)
        self.active_connections: Dict[str, List[WebSocket]] = {}
        # Map of conversation_id -> set of user_ids subscribed to it
        self.conversation_subscribers: Dict[str, Set[str]] = {}
    
    async def connect(self, websocket: WebSocket, user_id: str):
        """Accept a new WebSocket connection"""
        await websocket.accept()
        
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)
        
        logger.info(f"User {user_id} connected. Total connections: {len(self.active_connections[user_id])}")
    
    def disconnect(self, websocket: WebSocket, user_id: str):
        """Remove a WebSocket connection"""
        if user_id in self.active_connections:
            if websocket in self.active_connections[user_id]:
                self.active_connections[user_id].remove(websocket)
            
            # Clean up empty user entries
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        
        # Remove from all conversation subscriptions
        for conv_id in list(self.conversation_subscribers.keys()):
            if user_id in self.conversation_subscribers[conv_id]:
                self.conversation_subscribers[conv_id].discard(user_id)
                if not self.conversation_subscribers[conv_id]:
                    del self.conversation_subscribers[conv_id]
        
        logger.info(f"User {user_id} disconnected")
    
    def subscribe_to_conversation(self, user_id: str, conversation_id: str):
        """Subscribe a user to receive messages from a conversation"""
        if conversation_id not in self.conversation_subscribers:
            self.conversation_subscribers[conversation_id] = set()
        self.conversation_subscribers[conversation_id].add(user_id)
    
    def unsubscribe_from_conversation(self, user_id: str, conversation_id: str):
        """Unsubscribe a user from a conversation"""
        if conversation_id in self.conversation_subscribers:
            self.conversation_subscribers[conversation_id].discard(user_id)
    
    async def send_personal_message(self, message: dict, user_id: str):
        """Send a message to a specific user (all their connections)"""
        if user_id in self.active_connections:
            disconnected = []
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error(f"Error sending to user {user_id}: {e}")
                    disconnected.append(connection)
            
            # Clean up disconnected sockets
            for conn in disconnected:
                self.active_connections[user_id].remove(conn)
    
    async def broadcast_to_conversation(self, message: dict, conversation_id: str, exclude_user: str = None):
        """Broadcast a message to all users subscribed to a conversation"""
        if conversation_id in self.conversation_subscribers:
            for user_id in self.conversation_subscribers[conversation_id]:
                if user_id != exclude_user:
                    await self.send_personal_message(message, user_id)
    
    async def broadcast_to_users(self, message: dict, user_ids: List[str], exclude_user: str = None):
        """Broadcast a message to specific users"""
        for user_id in user_ids:
            if user_id != exclude_user:
                await self.send_personal_message(message, user_id)
    
    def is_user_online(self, user_id: str) -> bool:
        """Check if a user is currently online"""
        return user_id in self.active_connections and len(self.active_connections[user_id]) > 0
    
    def get_online_users(self) -> List[str]:
        """Get list of all online user IDs"""
        return list(self.active_connections.keys())


# Global connection manager instance
manager = ConnectionManager()


def get_manager() -> ConnectionManager:
    """Get the global connection manager"""
    return manager
