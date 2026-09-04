from fastapi import Request

from controllers.health_controller import HealthController
from controllers.robots_controller import RobotsController


def get_robots_controller(request: Request) -> RobotsController:
    return request.app.state.robots_controller


def get_health_controller(request: Request) -> HealthController:
    return request.app.state.health_controller
