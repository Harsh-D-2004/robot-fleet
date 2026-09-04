import threading
import time

from models.robot_state import RobotState


class FleetState:
    def __init__(self, stale_after_seconds: float):
        self._stale_after_seconds = stale_after_seconds
        self._lock = threading.Lock()
        self._robots = {}

    def _get_or_create(self, robot_id: str, robot_type: str = "unknown") -> RobotState:
        robot = self._robots.get(robot_id)
        if robot is None:
            robot = RobotState(robot_id=robot_id, robot_type=robot_type)
            self._robots[robot_id] = robot
        return robot

    def apply_telemetry(self, message: dict) -> bool:
        robot_id = message.get("robot_id")
        if robot_id is None:
            return False

        with self._lock:
            robot = self._get_or_create(robot_id)

            new_t = message.get("t", -1)
            if new_t <= robot.t:
                return False  # drop rule: not newer

            robot.x = message.get("x", robot.x)
            robot.y = message.get("y", robot.y)
            robot.battery = message.get("battery", robot.battery)
            robot.status = message.get("status", robot.status)
            robot.t = new_t
            robot.received_at = time.monotonic()
            robot.link = "online"
            return True

    def apply_link(self, robot_id: str, link: str, robot_type: str = None) -> bool:
        if robot_id is None:
            return False
        with self._lock:
            robot = self._get_or_create(robot_id)
            robot.link = link
            if robot_type is not None:
                robot.robot_type = robot_type
            return True

    def get_all(self) -> list:
        with self._lock:
            snapshot = []
            for robot in self._robots.values():
                snapshot.append(robot.to_dict(self._stale_after_seconds))
            return snapshot

    def get_one(self, robot_id: str):
        with self._lock:
            robot = self._robots.get(robot_id)
            if robot is None:
                return None
            return robot.to_dict(self._stale_after_seconds)

    def count(self) -> int:
        with self._lock:
            return len(self._robots)
