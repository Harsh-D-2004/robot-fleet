"""Business logic for the health endpoint.

Reports whether the broker connection is up and how long ago we last heard from
the quietest robot. The failure tests use this to wait for a ready backend.
"""


class HealthController:
    def __init__(self, fleet_state, mqtt_ingest):
        self._fleet_state = fleet_state
        self._mqtt_ingest = mqtt_ingest

    def get_health(self) -> dict:
        broker_connected = self._mqtt_ingest.is_connected()

        if broker_connected:
            overall_status = "ok"
        else:
            overall_status = "degraded"

        return {
            "status": overall_status,
            "broker_connected": broker_connected,
            "robot_count": self._fleet_state.count()
        }
