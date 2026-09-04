import asyncio
import json
import logging

import paho.mqtt.client as mqtt

from helpers.mqtt_topics import is_state_topic, is_status_topic, robot_id_from_topic

log = logging.getLogger("mqtt")

STATE_SUBSCRIPTION = "fleet/+/state"
STATUS_SUBSCRIPTION = "fleet/+/status"


class MqttIngest:
    def __init__(self, host, port, keepalive, fleet_state, ws_manager, loop):
        self._host = host
        self._port = port
        self._keepalive = keepalive
        self._fleet_state = fleet_state
        self._ws_manager = ws_manager
        self._loop = loop
        self._connected = False

        self._client = mqtt.Client(client_id="backend", clean_session=False)
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message = self._on_message
        self._client.reconnect_delay_set(min_delay=1, max_delay=30)

    def start(self):
        log.info("connecting to broker %s:%d ...", self._host, self._port)
        self._client.connect(self._host, self._port, keepalive=self._keepalive)
        self._client.loop_start()

    def stop(self):
        self._client.loop_stop()
        self._client.disconnect()

    def is_connected(self) -> bool:
        return self._connected

    def _on_connect(self, client, userdata, flags, rc):
        if rc != 0:
            log.error("broker connect failed rc=%s", rc)
            return
        self._connected = True
        client.subscribe(STATE_SUBSCRIPTION, qos=1)
        client.subscribe(STATUS_SUBSCRIPTION, qos=1)
        log.info("connected; subscribed to %s and %s", STATE_SUBSCRIPTION, STATUS_SUBSCRIPTION)

    def _on_disconnect(self, client, userdata, rc):
        self._connected = False
        log.warning("disconnected from broker rc=%s (auto-reconnecting)", rc)

    def _on_message(self, client, userdata, message):
        payload = self._parse_json(message)
        if payload is None:
            return

        if is_state_topic(message.topic):
            self._handle_state(payload)
        elif is_status_topic(message.topic):
            self._handle_status(message.topic, payload)

    def _parse_json(self, message):
        try:
            return json.loads(message.payload)
        except (ValueError, TypeError):
            log.warning("ignoring non-JSON message on %s", message.topic)
            return None

    def _handle_state(self, payload):
        changed = self._fleet_state.apply_telemetry(payload)
        if changed:
            self._notify(payload.get("robot_id"))

    def _handle_status(self, topic, payload):
        robot_id = payload.get("robot_id")
        if robot_id is None:
            robot_id = robot_id_from_topic(topic)
        link = payload.get("link", "online")
        robot_type = payload.get("robot_type")  # present in birth messages only
        changed = self._fleet_state.apply_link(robot_id, link, robot_type)
        if changed:
            self._notify(robot_id)

    def _notify(self, robot_id):
        if robot_id is None:
            return
        robot = self._fleet_state.get_one(robot_id)
        if robot is None:
            return
        update = {"type": "update", "robot": robot}
        # We are on paho's thread, so schedule the async send on the web loop.
        asyncio.run_coroutine_threadsafe(self._ws_manager.broadcast(update), self._loop)
