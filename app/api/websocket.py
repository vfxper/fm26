"""
WebSocket Handler - Real-time match event streaming
"""

from typing import Dict, Set
from fastapi import WebSocket, WebSocketDisconnect
from redis.asyncio import Redis
import json
import logging

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Manages WebSocket connections for real-time match streaming
    """
    
    def __init__(self):
        # Active connections: match_id -> set of WebSocket connections
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        
    async def connect(self, websocket: WebSocket, match_id: str) -> None:
        """
        Accept new WebSocket connection and add to match room
        
        Args:
            websocket: WebSocket connection
            match_id: Match ID to subscribe to
        """
        await websocket.accept()
        
        if match_id not in self.active_connections:
            self.active_connections[match_id] = set()
            
        self.active_connections[match_id].add(websocket)
        logger.info(f"Client connected to match {match_id}. Total connections: {len(self.active_connections[match_id])}")
        
    def disconnect(self, websocket: WebSocket, match_id: str) -> None:
        """
        Remove WebSocket connection from match room
        
        Args:
            websocket: WebSocket connection
            match_id: Match ID to unsubscribe from
        """
        if match_id in self.active_connections:
            self.active_connections[match_id].discard(websocket)
            
            # Clean up empty rooms
            if not self.active_connections[match_id]:
                del self.active_connections[match_id]
                
        logger.info(f"Client disconnected from match {match_id}")
        
    async def broadcast_to_match(self, match_id: str, message: dict) -> None:
        """
        Broadcast message to all clients watching a specific match
        
        Args:
            match_id: Match ID
            message: Message data to broadcast
        """
        if match_id not in self.active_connections:
            return
            
        # Create list to track disconnected clients
        disconnected = []
        
        for connection in self.active_connections[match_id]:
            try:
                await connection.send_json(message)
            except WebSocketDisconnect:
                disconnected.append(connection)
            except Exception as e:
                logger.error(f"Error broadcasting to client: {e}")
                disconnected.append(connection)
                
        # Clean up disconnected clients
        for connection in disconnected:
            self.disconnect(connection, match_id)
            
    async def send_personal_message(self, websocket: WebSocket, message: dict) -> None:
        """
        Send message to specific WebSocket connection
        
        Args:
            websocket: WebSocket connection
            message: Message data to send
        """
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")


# Global connection manager instance
manager = ConnectionManager()


async def handle_match_websocket(
    websocket: WebSocket,
    match_id: str,
    redis: Redis
) -> None:
    """
    Handle WebSocket connection for match streaming
    
    Args:
        websocket: WebSocket connection
        match_id: Match ID to stream
        redis: Redis client for event buffering
    """
    await manager.connect(websocket, match_id)
    
    try:
        # Send initial connection confirmation
        await manager.send_personal_message(websocket, {
            "type": "connected",
            "match_id": match_id,
            "message": "Connected to match stream"
        })
        
        # Keep connection alive and handle incoming messages
        while True:
            # Receive messages from client (e.g., playback control)
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Handle client messages
            if message.get("type") == "ping":
                await manager.send_personal_message(websocket, {
                    "type": "pong",
                    "timestamp": message.get("timestamp")
                })
            elif message.get("type") == "playback_control":
                # Handle playback speed changes, pause, etc.
                logger.info(f"Playback control for match {match_id}: {message}")
                
    except WebSocketDisconnect:
        manager.disconnect(websocket, match_id)
        logger.info(f"Client disconnected from match {match_id}")
    except Exception as e:
        logger.error(f"WebSocket error for match {match_id}: {e}")
        manager.disconnect(websocket, match_id)
