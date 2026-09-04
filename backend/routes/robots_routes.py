from fastapi import APIRouter, Depends, HTTPException

from controllers.robots_controller import RobotsController
from helpers.dependencies import get_robots_controller

router = APIRouter()


@router.get("/robots")
def list_robots(controller: RobotsController = Depends(get_robots_controller)):
    return controller.list_robots()


@router.get("/robots/{robot_id}")
def get_robot(robot_id: str, controller: RobotsController = Depends(get_robots_controller)):
    robot = controller.get_robot(robot_id)
    if robot is None:
        raise HTTPException(status_code=404, detail="unknown robot: " + robot_id)
    return robot
