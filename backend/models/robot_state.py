import time
from dataclasses import dataclass


@dataclass
class RobotState:
    robot_id: str
    robot_type: str
    x: float = 0.0
    y: float = 0.0
    battery: float = 0.0
    status: str = "unknown"
    t: int = -1
    received_at: float = 0.0
    link: str = "online"

    def is_stale(self, stale_after_seconds: float) -> bool:
        if self.received_at == 0.0:
            return True
        age_seconds = time.monotonic() - self.received_at
        return age_seconds > stale_after_seconds

    def to_dict(self, stale_after_seconds: float) -> dict:
        return {
            "robot_id": self.robot_id,
            "robot_type": self.robot_type,
            "x": self.x,
            "y": self.y,
            "battery": self.battery,
            "status": self.status,
            "t": self.t,
            "link": self.link,
            "stale": self.is_stale(stale_after_seconds),
        }
