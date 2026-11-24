from typing import Dict, Set
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()


class SessionWebSocketManager:
    def __init__(self):
        self.connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, session_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self.connections.setdefault(session_id, set()).add(websocket)

    def disconnect(self, session_id: str, websocket: WebSocket) -> None:
        if session_id in self.connections:
            self.connections[session_id].discard(websocket)

    async def broadcast(self, session_id: str, payload: dict) -> None:
        sockets = list(self.connections.get(session_id, set()))
        for ws in sockets:
            try:
                await ws.send_json(payload)
            except Exception:
                self.disconnect(session_id, ws)


ws_manager = SessionWebSocketManager()


@router.websocket("/ws/analysis/{session_id}")
async def analysis_ws(websocket: WebSocket, session_id: str):
    await ws_manager.connect(session_id, websocket)
    try:
        while True:
            msg = await websocket.receive_text()
            if msg == "PING":
                await websocket.send_json({"type": "PONG", "session_id": session_id})
    except WebSocketDisconnect:
        ws_manager.disconnect(session_id, websocket)
