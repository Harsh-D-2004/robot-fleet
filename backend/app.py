import asyncio
import logging

from fastapi import FastAPI

from config import Config
from controllers.health_controller import HealthController
from controllers.robots_controller import RobotsController
from helpers.logging_config import configure_logging
from routes import health_routes, robots_routes, ws_routes
from services.fleet_state import FleetState
from services.mqtt_ingest import MqttIngest
from services.ws_manager import WsManager

config = Config()
configure_logging(config.log_level)
log = logging.getLogger("app")

app = FastAPI(title="Robot Fleet Backend")

app.include_router(robots_routes.router)
app.include_router(health_routes.router)
app.include_router(ws_routes.router)


@app.on_event("startup")
async def on_startup():
    fleet_state = FleetState(stale_after_seconds=config.stale_after_seconds)
    ws_manager = WsManager()
    loop = asyncio.get_running_loop()
    mqtt_ingest = MqttIngest(
        host=config.mqtt_host,
        port=config.mqtt_port,
        keepalive=config.keepalive,
        fleet_state=fleet_state,
        ws_manager=ws_manager,
        loop=loop,
    )

    app.state.fleet_state = fleet_state
    app.state.ws_manager = ws_manager
    app.state.mqtt_ingest = mqtt_ingest
    app.state.robots_controller = RobotsController(fleet_state)
    app.state.health_controller = HealthController(fleet_state, mqtt_ingest)

    mqtt_ingest.start()
    log.info("backend started on port 8000")


@app.on_event("shutdown")
async def on_shutdown():
    app.state.mqtt_ingest.stop()
    log.info("backend stopped")
