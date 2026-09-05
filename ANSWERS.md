### 1. What holds the fleet's current state, and why that shape?

Each robot publishes to its own topics : fleet/{id}/state and fleet/{id}/status
(see `robots/robot.py`) and the broker keeps the latest message per topic
. This makes every robot's stored state independant because the last
state of r6 lives on r6's own topic, a client still gets r6's data even if r3
is down, and one robot (or one topic) going quiet never affects the others' stored
state. On the backend that same shape is mirrored by `FleetState` in
`backend/services/fleet_state.py`: one dict keyed by `robot_id → RobotState`, filled
by apply_telemetry as messages arrive. Both surfaces read this one dict —
polling (`GET /robots` → `RobotsController.list_robots` → `FleetState.get_all`) returns
the latest state of every robot, and the WebSocket snapshot + per-robot deltas
(`backend/routes/ws_routes.py`, `MqttIngest._notify` → `WsManager.broadcast`) come from
the same dict so storing state is decoupled per robot and the two views can never
disagree.

### 2. One real tradeoff: the transport (MQTT over WebSocket / HTTP / gRPC).

I chose MQTT with a broker in the middle. WebSocket, HTTP POST, and gRPC are all
point to point approaches: the robot would have to know the backend's address, and if the
backend is down the robot has nowhere to send its data. As error handling here i would have
to build some features of brokerage myself. A common message broker
with topics + a short-lived queue gives all of that for free: producers and consumers
never know each other (pub/sub), an offline consumer's messages are held in its session
queue and replayed on reconnect, and one publish can reach many consumers. The broker
also maintains liveness of both sides and keep alive pings plus Last Will (`will_set`
in `robots/robot.py`, handled by `FleetState.apply_link`) so a dead robot is detected
without polling. The broker becomes the critical middle man
if it's down, everything stops — and its queue is limited (max_queued_messages 1000
in `mosquitto/mosquitto.conf`, consumed by the persistent-session subscriber in
`backend/services/mqtt_ingest.py`), so once it fills the broker starts dropping events. That
caps how long the backend can be down before data is lost.

### 3. What I left out, and what I'd build next.

Given more time I'd first shrink the payloads: today every message is JSON
(`json.dumps` in `robots/robot.py`, `json.loads` in `MqttIngest._parse_json`), which is
verbose on a constrained link — moving to Protobuf or another compact binary format
would cut bandwidth and parsing cost with almost no code change. Second, I'd swap the
short-lived broker queue for a more robust, durable queue that holds data much
longer a disk-backed log such as kafka or something more optimal so the
backend can be down well beyond 10 minutes without losing history. Finally I'd experiment with newer transports like
Zenoh which i read on some blogs, which unifies pub/sub, query, and storage in one lightweight stack built for
iot communication, to see if it removes the "broker is a single critical point" weakness
while keeping the decoupling.
