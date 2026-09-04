
import json
import logging
import os
import signal
import sys
import threading
import time

import paho.mqtt.client as mqtt

# ---------------------------------------------------------------------------
# Config (all overridable via env)
# ---------------------------------------------------------------------------
ROBOT_ID = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("ROBOT_ID")
MQTT_HOST = os.environ.get("MQTT_HOST", "localhost")
MQTT_PORT = int(os.environ.get("MQTT_PORT", "1883"))
SPEEDUP = float(os.environ.get("SPEEDUP", "10"))
KEEPALIVE = int(os.environ.get("KEEPALIVE", "10"))
DATA_FILE = os.environ.get("DATA_FILE")
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")

if not ROBOT_ID:
    print("FATAL: robot id required (argv[1] or ROBOT_ID env)", file=sys.stderr)
    sys.exit(2)

logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s %(levelname)-5s [%(name)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(ROBOT_ID)

STATE_TOPIC = f"fleet/{ROBOT_ID}/state"
STATUS_TOPIC = f"fleet/{ROBOT_ID}/status"


def find_robot_type(robot_id: str) -> str:
    """Look up this robot's type from robots.json (shipped in this container).

    The robot publishes its own type in the birth message so the backend does
    not need to read any roster file.
    """
    here = os.path.dirname(os.path.abspath(__file__))
    path = os.environ.get("ROBOTS_FILE") or os.path.join(here, "robots.json")
    if not os.path.exists(path):
        return "unknown"
    roster = json.load(open(path, "r"))
    for entry in roster:
        if entry.get("robot_id") == robot_id:
            return entry.get("robot_type", "unknown")
    return "unknown"


ROBOT_TYPE = find_robot_type(ROBOT_ID)

connected = threading.Event()   # set by on_connect, cleared by on_disconnect
stop = threading.Event()        # set by SIGTERM/SIGINT for graceful shutdown


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------
def find_data_file() -> str:
    if DATA_FILE:
        return DATA_FILE
    here = os.path.dirname(os.path.abspath(__file__))
    for name in ("events.jsonl", "events.json"):
        candidate = os.path.join(here, name)
        if os.path.exists(candidate):
            return candidate
    raise FileNotFoundError(
        "no events.jsonl / events.json found next to robot.py (or set DATA_FILE)"
    )


def load_my_events() -> list[dict]:
    path = find_data_file()
    text = open(path, "r").read().strip()
    # Support both JSON-lines (events.jsonl) and a single JSON array (events.json).
    if text.startswith("["):
        rows = json.loads(text)
    else:
        rows = [json.loads(line) for line in text.splitlines() if line.strip()]
    mine = sorted((r for r in rows if r.get("robot_id") == ROBOT_ID),
                  key=lambda r: r["t"])
    log.info("loaded %d/%d events for %s from %s",
             len(mine), len(rows), ROBOT_ID, os.path.basename(path))
    if not mine:
        log.warning("no events matched robot_id=%s — nothing to publish", ROBOT_ID)
    return mine


# ---------------------------------------------------------------------------
# MQTT callbacks
# ---------------------------------------------------------------------------
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        log.info("CONNECTED to %s:%d (keepalive=%ds, clean_session=True)",
                 MQTT_HOST, MQTT_PORT, KEEPALIVE)
        # Birth: overwrite any retained "lost" left by a previous crash, and
        # carry this robot's type so the backend learns it without a roster file.
        client.publish(
            STATUS_TOPIC,
            json.dumps({"robot_id": ROBOT_ID, "link": "online", "robot_type": ROBOT_TYPE}),
            qos=1, retain=True,
        )
        log.info("BIRTH published → %s {link: online, robot_type: %s}", STATUS_TOPIC, ROBOT_TYPE)
        connected.set()
    else:
        log.error("connect failed rc=%s", rc)


def on_disconnect(client, userdata, rc):
    connected.clear()
    if rc == 0:
        log.info("clean disconnect (LWT will NOT fire)")
    else:
        log.warning("UNEXPECTED disconnect rc=%s — auto-reconnecting...", rc)


def on_publish(client, userdata, mid):
    log.debug("broker acked publish mid=%s", mid)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def handle_signal(signum, frame):
    log.info("received signal %s — shutting down cleanly", signum)
    stop.set()


def main():
    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    events = load_my_events()

    client = mqtt.Client(client_id=f"robot-{ROBOT_ID}", clean_session=True)
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_publish = on_publish

    # LWT: retained, so a backend that connects AFTER our death still sees it.
    client.will_set(
        STATUS_TOPIC,
        json.dumps({"robot_id": ROBOT_ID, "link": "lost"}),
        qos=1, retain=True,
    )
    client.reconnect_delay_set(min_delay=1, max_delay=30)
    log.info("LWT registered → %s {link: lost} (fires only on ABNORMAL drop)", STATUS_TOPIC)

    log.info("connecting to broker %s:%d ...", MQTT_HOST, MQTT_PORT)
    try:
        client.connect(MQTT_HOST, MQTT_PORT, keepalive=KEEPALIVE)
    except Exception as exc:
        log.error("initial connect failed: %s", exc)
        sys.exit(1)

    client.loop_start()   # background thread: pings + publish flush + reconnect

    if not connected.wait(timeout=30):
        log.error("not connected within 30s — exiting")
        client.loop_stop()
        sys.exit(1)

    log.info("REPLAY start: %d events, speedup=%sx (~%.0fs of playback)",
             len(events), SPEEDUP, (events[-1]["t"] / SPEEDUP) if events else 0)

    prev_t = None
    published = 0
    for e in events:
        if stop.is_set():
            break
        if prev_t is not None:
            delay = (e["t"] - prev_t) / SPEEDUP
            if delay > 0:
                # interruptible sleep: wakes immediately if a stop signal arrives
                if stop.wait(timeout=delay):
                    break

        client.publish(STATE_TOPIC, json.dumps(e), qos=1, retain=True)
        published += 1
        log.info("t=%-4s → pos=(%6.1f,%6.1f) batt=%5.1f%% status=%-11s",
                 e["t"], e.get("x", 0.0), e.get("y", 0.0),
                 e.get("battery", 0.0), e.get("status", "?"))
        if "task_event" in e:
            log.info("t=%-4s   task_event=%s (not graded, surfaced only)",
                     e["t"], e["task_event"])
        prev_t = e["t"]

    if stop.is_set():
        log.info("REPLAY interrupted after %d/%d events", published, len(events))
    else:
        log.info("REPLAY complete: %d/%d events published", published, len(events))

    client.disconnect()   # CLEAN goodbye → broker discards the will (no false "lost")
    client.loop_stop()
    log.info("robot %s exited", ROBOT_ID)


if __name__ == "__main__":
    main()
