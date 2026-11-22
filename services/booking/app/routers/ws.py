from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.ws_manager import ShowWsManager

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/shows/{show_id}")
async def show_seat_updates(websocket: WebSocket, show_id: str) -> None:
    ws_manager: ShowWsManager = websocket.app.state.ws_manager
    await ws_manager.connect(show_id=show_id, websocket=websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await ws_manager.disconnect(show_id=show_id, websocket=websocket)