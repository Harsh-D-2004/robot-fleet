from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    ws_manager = websocket.app.state.ws_manager
    fleet_state = websocket.app.state.fleet_state

    await ws_manager.connect(websocket)

    snapshot = {"type": "snapshot", "robots": fleet_state.get_all()}
    await websocket.send_json(snapshot)

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket)
