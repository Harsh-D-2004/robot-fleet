import asyncio
import json
import logging

from fastapi import WebSocket

log = logging.getLogger("ws")


class WsManager:
    def __init__(self):
        self._clients = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        async with self._lock:
            self._clients.add(websocket)
        log.info("websocket client connected (total=%d)", len(self._clients))

    async def disconnect(self, websocket: WebSocket):
        async with self._lock:
            self._clients.discard(websocket)
        log.info("websocket client disconnected (total=%d)", len(self._clients))

    async def broadcast(self, message: dict):
        text = json.dumps(message)

        async with self._lock:
            targets = list(self._clients)

        failed_clients = []
        for client in targets:
            try:
                await client.send_text(text)
            except Exception:
                failed_clients.append(client)

        if failed_clients:
            async with self._lock:
                for client in failed_clients:
                    self._clients.discard(client)
