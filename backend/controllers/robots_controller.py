class RobotsController:
    def __init__(self, fleet_state):
        self._fleet_state = fleet_state

    def list_robots(self) -> list:
        return self._fleet_state.get_all()

    def get_robot(self, robot_id: str):
        return self._fleet_state.get_one(robot_id)
