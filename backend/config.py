import os


class Config:
    def __init__(self):
        self.mqtt_host = os.environ.get("MQTT_HOST", "localhost")
        self.mqtt_port = int(os.environ.get("MQTT_PORT", "1883"))
        self.keepalive = int(os.environ.get("KEEPALIVE", "10"))
        self.stale_after_seconds = float(os.environ.get("STALE_AFTER_S", "15"))
        self.log_level = os.environ.get("LOG_LEVEL", "INFO")
