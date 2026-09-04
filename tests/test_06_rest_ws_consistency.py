"""REST and WebSocket must reflect the same underlying state.

Both read the one in-memory FleetState, so the set of robots a WebSocket client
sees in its snapshot must match what a REST client sees.
"""
import asyncio
import json

import websockets

import support


def test_rest_and_websocket_agree_on_the_fleet():
    support.log.info("reading the fleet from the WebSocket snapshot")
    ws_robot_ids = asyncio.run(_snapshot_ids_from_websocket())

    support.log.info("reading the fleet from REST /robots")
    rest_robot_ids = {robot["robot_id"] for robot in support.get_all_robots()}

    support.log.info("ws=%d robots, rest=%d robots", len(ws_robot_ids), len(rest_robot_ids))
    assert ws_robot_ids == rest_robot_ids


async def _snapshot_ids_from_websocket():
    async with websockets.connect(support.WS_URL) as socket:
        snapshot = json.loads(await socket.recv())
        return {robot["robot_id"] for robot in snapshot["robots"]}
