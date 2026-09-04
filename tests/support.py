import json
import logging
import os
import subprocess
import time

import httpx
import paho.mqtt.client as mqtt

log = logging.getLogger("test")

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

BASE_URL = os.environ.get("BASE_URL", "http://localhost:8000")
WS_URL = os.environ.get("WS_URL", "ws://localhost:8000/ws")
MQTT_HOST = os.environ.get("TEST_MQTT_HOST", "localhost")
MQTT_PORT = int(os.environ.get("TEST_MQTT_PORT", "1883"))


# --- docker compose control -------------------------------------------------
def run_compose(*args, check=True):
    log.info("docker compose %s", " ".join(args))
    command = ["docker", "compose", *args]
    return subprocess.run(command, cwd=PROJECT_ROOT, check=check,
                          capture_output=True, text=True)


def exec_in_robots(*command, check=False):
    return run_compose("exec", "-T", "robots", *command, check=check)


def robot_process_running(robot_id):
    result = exec_in_robots("pgrep", "-f", "robot.py " + robot_id)
    return result.returncode == 0


# --- HTTP -------------------------------------------------------------------
def get_all_robots():
    response = httpx.get(BASE_URL + "/robots", timeout=5)
    response.raise_for_status()
    return response.json()


def get_robot(robot_id):
    response = httpx.get(BASE_URL + "/robots/" + robot_id, timeout=5)
    response.raise_for_status()
    return response.json()


def get_status_code(path):
    return httpx.get(BASE_URL + path, timeout=5).status_code


def get_health():
    response = httpx.get(BASE_URL + "/health", timeout=5)
    response.raise_for_status()
    return response.json()


# --- MQTT publish (stands in for a robot) -----------------------------------
def publish_state(robot_id, t, battery=50.0, status="idle", x=1.0, y=1.0):
    payload = {
        "robot_id": robot_id,
        "t": t,
        "x": x,
        "y": y,
        "battery": battery,
        "status": status,
    }
    log.info("publish %s state: t=%s battery=%s status=%s", robot_id, t, battery, status)
    _publish("fleet/" + robot_id + "/state", payload)


def _publish(topic, payload):
    client = mqtt.Client()
    client.connect(MQTT_HOST, MQTT_PORT, keepalive=10)
    client.loop_start()
    message = client.publish(topic, json.dumps(payload), qos=1, retain=False)
    message.wait_for_publish(timeout=5)
    client.loop_stop()
    client.disconnect()


# --- waiting ----------------------------------------------------------------
def wait_until(predicate, timeout=20.0, interval=0.5, message="condition not met"):
    """Poll `predicate` until it returns True or the timeout elapses."""
    log.info("waiting for: %s", message)
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            if predicate():
                log.info("ok: %s", message)
                return True
        except Exception:
            # Endpoint may be briefly unavailable (e.g. backend restarting).
            pass
        time.sleep(interval)
    raise AssertionError("timeout waiting: " + message)
