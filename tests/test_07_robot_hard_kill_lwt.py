"""Hard-killing a robot fires its Last Will -> the API shows link: lost.

SIGKILL gives the robot no chance to say goodbye, so the broker declares it dead
after the keepalive window and publishes the retained LWT. Destructive: this
robot stays down until the stack is restarted.
"""
import pytest

import support

ROBOT_ID = "r6"


def test_hard_kill_sets_link_lost():
    if not support.robot_process_running(ROBOT_ID):
        pytest.skip(ROBOT_ID + " is not running; start the stack fresh and re-run")

    support.log.info("confirming %s is online before the kill", ROBOT_ID)
    support.wait_until(
        lambda: support.get_robot(ROBOT_ID)["link"] == "online",
        message=ROBOT_ID + " online at the start",
    )

    support.log.info("SIGKILL %s (abrupt death, no clean disconnect)", ROBOT_ID)
    support.exec_in_robots("pkill", "-9", "-f", "robot.py " + ROBOT_ID)

    support.log.info("waiting for the broker to fire the LWT (~1.5 x keepalive)")
    support.wait_until(
        lambda: support.get_robot(ROBOT_ID)["link"] == "lost",
        timeout=25,
        message=ROBOT_ID + " link became lost",
    )
    support.log.info("%s is now link=lost", ROBOT_ID)
