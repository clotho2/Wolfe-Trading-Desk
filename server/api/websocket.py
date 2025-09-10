# path: server/api/websocket.py
from __future__ import annotations

import asyncio
import json
from datetime import datetime
from typing import Dict, Set

from fastapi import WebSocket, WebSocketDisconnect
from fastapi.routing import APIRouter

from config.settings import settings
from core.executor.registry import get_adapter

router = APIRouter()

# Store active WebSocket connections
active_connections: Set[WebSocket] = set()


class ConnectionManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)
    
    async def broadcast(self, message: dict):
        """Send message to all connected clients."""
        disconnected = set()
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.add(connection)
        
        # Clean up disconnected clients
        for conn in disconnected:
            self.active_connections.discard(conn)
    
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        await websocket.send_json(message)


manager = ConnectionManager()


@router.websocket("/ws/trades")
async def websocket_trades(websocket: WebSocket):
    """WebSocket endpoint for real-time trade updates."""
    await manager.connect(websocket)
    
    try:
        # Send initial status
        adapter = get_adapter("mt5")
        if adapter and hasattr(adapter, 'get_status'):
            status = adapter.get_status()
            await manager.send_personal_message({
                "type": "status",
                "data": status
            }, websocket)
        
        # Keep connection alive and send periodic updates
        while True:
            try:
                # Wait for any message from client (ping/pong)
                message = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                
                # Handle client messages
                if message == "ping":
                    await manager.send_personal_message({"type": "pong"}, websocket)
                
            except asyncio.TimeoutError:
                # Send heartbeat
                await manager.send_personal_message({
                    "type": "heartbeat",
                    "timestamp": datetime.utcnow().isoformat()
                }, websocket)
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(websocket)


async def broadcast_trade_event(event_type: str, data: dict):
    """Broadcast trade events to all connected WebSocket clients."""
    await manager.broadcast({
        "type": "trade_event",
        "event": event_type,
        "data": data,
        "timestamp": datetime.utcnow().isoformat()
    })


async def broadcast_position_update(positions: list):
    """Broadcast position updates to all connected clients."""
    await manager.broadcast({
        "type": "position_update",
        "positions": positions,
        "timestamp": datetime.utcnow().isoformat()
    })