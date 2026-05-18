"""
WebSocket Implementation (Task 30)
- Connection handler with authentication
- Match event streaming protocol
- Real-time event broadcasting
- Client reconnection handling
- Event buffering for disconnections
- Heartbeat/ping-pong mechanism

Protocol:
  Client -> Server:
    {"type": "auth", "token": "jwt_or_initdata"}
    {"type": "subscribe", "match_id": "123"}
    {"type": "unsubscribe", "match_id": "123"}
    {"type": "ping", "ts": 1234567890}
    {"type": "playback", "action": "pause|resume|speed", "value": 2}

  Server -> Client:
    {"type": "auth_ok", "user_id": 1}
    {"type": "auth_fail", "reason": "..."}
    {"type": "pong", "ts": 1234567890}
    {"type": "match_event", "match_id": "123", "event": {...}}
    {"type": "match_state", "match_id": "123", "state": {...}}
    {"type": "error", "message": "..."}
"""

import asyncio
import json
import time
import logging
from typing import Dict, Set, List, Optional, Any
from collections import defaultdict

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from starlette.websockets import WebSocketState

logger = logging.getLogger(__name__)

router = APIRouter()


class EventBuffer:
    """Buffers events for clients that temporarily disconnect."""
    
    def __init__(self, max_size: int = 200, ttl_seconds: int = 60):
        self.max_size = max_size
        self.ttl = ttl_seconds
        self._buffers: Dict[str, List[dict]] = defaultdict(list)  # user_id -> events
        self._timestamps: Dict[str, float] = {}
    
    def add(self, user_id: str, event: dict):
        """Buffer an event for a disconnected user."""
        self._buffers[user_id].append(event)
        if len(self._buffers[user_id]) > self.max_size:
            self._buffers[user_id] = self._buffers[user_id][-self.max_size:]
        self._timestamps[user_id] = time.time()
    
    def get_and_clear(self, user_id: str) -> List[dict]:
        """Get buffered events and clear buffer."""
        events = self._buffers.pop(user_id, [])
        self._timestamps.pop(user_id, None)
        return events
    
    def cleanup(self):
        """Remove expired buffers."""
        now = time.time()
        expired = [uid for uid, ts in self._timestamps.items() if now - ts > self.ttl]
        for uid in expired:
            self._buffers.pop(uid, None)
            self._timestamps.pop(uid, None)


class MatchStreamManager:
    """Manages WebSocket connections and match event streaming."""
    
    def __init__(self):
        # match_id -> set of (websocket, user_id)
        self.match_rooms: Dict[str, Set[tuple]] = defaultdict(set)
        # user_id -> websocket
        self.user_connections: Dict[str, WebSocket] = {}
        # user_id -> set of subscribed match_ids
        self.user_subscriptions: Dict[str, Set[str]] = defaultdict(set)
        # Event buffer for reconnections
        self.buffer = EventBuffer()
        # Match state cache (latest state for new subscribers)
        self.match_states: Dict[str, dict] = {}
        # Heartbeat tracking
        self.last_pong: Dict[str, float] = {}
    
    async def connect(self, ws: WebSocket, user_id: str):
        """Register a new connection."""
        await ws.accept()
        
        # If user already connected, close old connection
        if user_id in self.user_connections:
            old_ws = self.user_connections[user_id]
            try:
                await old_ws.close(code=4001, reason="New connection from same user")
            except Exception:
                pass
        
        self.user_connections[user_id] = ws
        self.last_pong[user_id] = time.time()
        
        # Send buffered events from disconnection period
        buffered = self.buffer.get_and_clear(user_id)
        if buffered:
            await self._send(ws, {
                "type": "buffered_events",
                "count": len(buffered),
                "events": buffered,
            })
        
        logger.info(f"WS connected: user={user_id}")
    
    def disconnect(self, user_id: str):
        """Handle disconnection."""
        self.user_connections.pop(user_id, None)
        
        # Remove from all match rooms
        for match_id in list(self.user_subscriptions.get(user_id, set())):
            self.match_rooms[match_id].discard((None, user_id))
            # Clean up room entries
            self.match_rooms[match_id] = {
                (ws, uid) for ws, uid in self.match_rooms[match_id] if uid != user_id
            }
        
        self.user_subscriptions.pop(user_id, None)
        self.last_pong.pop(user_id, None)
        logger.info(f"WS disconnected: user={user_id}")
    
    async def subscribe(self, user_id: str, match_id: str):
        """Subscribe user to a match stream."""
        ws = self.user_connections.get(user_id)
        if not ws:
            return
        
        self.match_rooms[match_id].add((ws, user_id))
        self.user_subscriptions[user_id].add(match_id)
        
        # Send current match state if available
        if match_id in self.match_states:
            await self._send(ws, {
                "type": "match_state",
                "match_id": match_id,
                "state": self.match_states[match_id],
            })
        
        await self._send(ws, {"type": "subscribed", "match_id": match_id})
    
    async def unsubscribe(self, user_id: str, match_id: str):
        """Unsubscribe user from a match stream."""
        ws = self.user_connections.get(user_id)
        self.match_rooms[match_id] = {
            (w, uid) for w, uid in self.match_rooms[match_id] if uid != user_id
        }
        self.user_subscriptions[user_id].discard(match_id)
        
        if ws:
            await self._send(ws, {"type": "unsubscribed", "match_id": match_id})
    
    async def broadcast_match_event(self, match_id: str, event: dict):
        """Broadcast event to all subscribers of a match."""
        if match_id not in self.match_rooms:
            return
        
        message = {"type": "match_event", "match_id": match_id, "event": event}
        disconnected = []
        
        for ws, user_id in list(self.match_rooms[match_id]):
            try:
                if ws and ws.client_state == WebSocketState.CONNECTED:
                    await ws.send_json(message)
                else:
                    disconnected.append(user_id)
                    # Buffer for reconnection
                    self.buffer.add(user_id, message)
            except Exception:
                disconnected.append(user_id)
                self.buffer.add(user_id, message)
        
        for uid in disconnected:
            self.disconnect(uid)
    
    async def update_match_state(self, match_id: str, state: dict):
        """Update cached match state (for new subscribers)."""
        self.match_states[match_id] = state
    
    async def _send(self, ws: WebSocket, data: dict):
        """Safe send."""
        try:
            if ws.client_state == WebSocketState.CONNECTED:
                await ws.send_json(data)
        except Exception as e:
            logger.debug(f"Send failed: {e}")


# Global instance
stream_manager = MatchStreamManager()


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: Optional[str] = Query(None),
):
    """
    Main WebSocket endpoint.
    Connect with: ws://host/ws?token=jwt_token
    Or authenticate after connection with auth message.
    """
    user_id = None
    
    try:
        # Authenticate
        if token:
            user_id = await _authenticate_token(token)
        
        if not user_id:
            # Accept and wait for auth message
            await websocket.accept()
            try:
                auth_data = await asyncio.wait_for(websocket.receive_json(), timeout=10.0)
                if auth_data.get("type") == "auth":
                    user_id = await _authenticate_token(auth_data.get("token", ""))
            except asyncio.TimeoutError:
                await websocket.send_json({"type": "auth_fail", "reason": "Auth timeout"})
                await websocket.close()
                return
            
            if not user_id:
                await websocket.send_json({"type": "auth_fail", "reason": "Invalid token"})
                await websocket.close()
                return
            
            await websocket.send_json({"type": "auth_ok", "user_id": user_id})
        else:
            await stream_manager.connect(websocket, str(user_id))
            await websocket.send_json({"type": "auth_ok", "user_id": user_id})
        
        # If we accepted manually above, register now
        if str(user_id) not in stream_manager.user_connections:
            stream_manager.user_connections[str(user_id)] = websocket
            stream_manager.last_pong[str(user_id)] = time.time()
        
        # Main message loop
        while True:
            data = await websocket.receive_json()
            await _handle_message(str(user_id), data)
    
    except WebSocketDisconnect:
        if user_id:
            stream_manager.disconnect(str(user_id))
    except Exception as e:
        logger.error(f"WS error: {e}")
        if user_id:
            stream_manager.disconnect(str(user_id))


async def _handle_message(user_id: str, data: dict):
    """Handle incoming WebSocket message."""
    msg_type = data.get("type")
    
    if msg_type == "ping":
        ws = stream_manager.user_connections.get(user_id)
        stream_manager.last_pong[user_id] = time.time()
        if ws:
            await stream_manager._send(ws, {"type": "pong", "ts": data.get("ts", 0)})
    
    elif msg_type == "subscribe":
        match_id = str(data.get("match_id", ""))
        if match_id:
            await stream_manager.subscribe(user_id, match_id)
    
    elif msg_type == "unsubscribe":
        match_id = str(data.get("match_id", ""))
        if match_id:
            await stream_manager.unsubscribe(user_id, match_id)
    
    elif msg_type == "playback":
        # Forward playback control to match simulation
        pass  # Handled by match simulation service


async def _authenticate_token(token: str) -> Optional[int]:
    """Authenticate WebSocket token. Returns user_id or None."""
    if not token:
        return None
    
    try:
        # Try JWT
        from app.services.auth_service import AuthService
        auth = AuthService()
        payload = auth.verify_token(token)
        if payload and "user_id" in payload:
            return payload["user_id"]
    except Exception:
        pass
    
    try:
        # Try Telegram initData
        from app.services.auth_service import AuthService
        auth = AuthService()
        user_data = auth.validate_telegram_init_data(token)
        if user_data:
            return user_data.get("id")
    except Exception:
        pass
    
    # For development: accept numeric string as user_id
    if token.isdigit():
        return int(token)
    
    return None


# === Public API for broadcasting from other services ===

async def broadcast_match_event(match_id: int, event: dict):
    """Call this from match simulation to stream events to clients."""
    await stream_manager.broadcast_match_event(str(match_id), event)


async def update_match_state(match_id: int, state: dict):
    """Update match state cache for new subscribers."""
    await stream_manager.update_match_state(str(match_id), state)
