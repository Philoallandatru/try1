"""
WebSocket endpoint for real-time analysis updates.

Provides streaming updates during:
- Deep analysis progress (evidence collection, LLM reasoning)
- Daily report generation (incremental sections)
"""

import asyncio
import json
from typing import Dict, Set
from fastapi import WebSocket, WebSocketDisconnect
from datetime import datetime, timezone


class AnalysisWebSocketManager:
    """Manages WebSocket connections for analysis updates."""

    def __init__(self):
        # Map analysis_id -> set of connected websockets
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, analysis_id: str):
        """Accept a new WebSocket connection for an analysis."""
        await websocket.accept()
        async with self._lock:
            if analysis_id not in self.active_connections:
                self.active_connections[analysis_id] = set()
            self.active_connections[analysis_id].add(websocket)

    async def disconnect(self, websocket: WebSocket, analysis_id: str):
        """Remove a WebSocket connection."""
        async with self._lock:
            if analysis_id in self.active_connections:
                self.active_connections[analysis_id].discard(websocket)
                if not self.active_connections[analysis_id]:
                    del self.active_connections[analysis_id]

    async def send_update(self, analysis_id: str, update: dict):
        """Send an update to all connected clients for an analysis."""
        if analysis_id not in self.active_connections:
            return

        message = json.dumps(update)
        disconnected = set()

        for websocket in self.active_connections[analysis_id]:
            try:
                await websocket.send_text(message)
            except Exception:
                disconnected.add(websocket)

        # Clean up disconnected clients
        if disconnected:
            async with self._lock:
                self.active_connections[analysis_id] -= disconnected
                if not self.active_connections[analysis_id]:
                    del self.active_connections[analysis_id]

    async def send_progress(self, analysis_id: str, stage: str, progress: float, message: str = ""):
        """Send a progress update."""
        await self.send_update(analysis_id, {
            "type": "progress",
            "stage": stage,
            "progress": progress,
            "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

    async def send_evidence(self, analysis_id: str, evidence: dict):
        """Send evidence collection update."""
        await self.send_update(analysis_id, {
            "type": "evidence",
            "evidence": evidence,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

    async def send_section(self, analysis_id: str, section_name: str, content: str):
        """Send a completed section (for daily reports)."""
        await self.send_update(analysis_id, {
            "type": "section",
            "section": section_name,
            "content": content,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

    async def send_complete(self, analysis_id: str, result: dict):
        """Send completion notification."""
        await self.send_update(analysis_id, {
            "type": "complete",
            "result": result,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

    async def send_error(self, analysis_id: str, error: str):
        """Send error notification."""
        await self.send_update(analysis_id, {
            "type": "error",
            "error": error,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })


# Global WebSocket manager instance
ws_manager = AnalysisWebSocketManager()


def create_websocket_router():
    """Create FastAPI router with WebSocket endpoints."""
    from fastapi import APIRouter

    router = APIRouter()

    @router.websocket("/ws/analysis/{analysis_id}")
    async def analysis_websocket(websocket: WebSocket, analysis_id: str):
        """
        WebSocket endpoint for real-time analysis updates.

        Clients connect to /ws/analysis/{analysis_id} to receive:
        - Progress updates during analysis
        - Evidence collection notifications
        - Incremental section updates (daily reports)
        - Completion/error notifications

        Message format:
        {
            "type": "progress" | "evidence" | "section" | "complete" | "error",
            "timestamp": "2026-01-15T10:30:00",
            ... type-specific fields
        }
        """
        await ws_manager.connect(websocket, analysis_id)
        try:
            # Keep connection alive and handle client messages
            while True:
                data = await websocket.receive_text()
                # Echo back for heartbeat/ping
                if data == "ping":
                    await websocket.send_text("pong")
        except WebSocketDisconnect:
            await ws_manager.disconnect(websocket, analysis_id)

    return router
