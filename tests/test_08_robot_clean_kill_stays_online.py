"""A clean shutdown (SIGTERM) must NOT look like a death.

The robot catches SIGTERM and disconnects cleanly, so the broker does not fire
the LWT: link stays "online". Because it stopped publishing, the backend's own
freshness timer eventually marks it stale. Destructive: this robot stays down
until the stack is restarted.
"""
import time

import pytest

import support

ROBOT_ID = "r7"


def test_clean_kill_keeps_link_online_but_goes_stale():
    if not support.robot_process_running(ROBOT_ID):
        pytest.skip(ROBOT_ID + " is not running; start the stack fresh and re-run")

    support.log.info("confirming %s is online before the clean kill", ROBOT_ID)
    support.wait_until(
        lambda: support.get_robot(ROBOT_ID)["link"] == "online",
        message=ROBOT_ID + " online at the start",
    )

    support.log.info("SIGTERM %s (clean shutdown -> no LWT expected)", ROBOT_ID)
    support.exec_in_robots("pkill", "-f", "robot.py " + ROBOT_ID)

    support.log.info("sleeping 20s past the keepalive window")
    time.sleep(20)

    robot = support.get_robot(ROBOT_ID)
    support.log.info("%s after clean kill: link=%s stale=%s", ROBOT_ID, robot["link"], robot["stale"])

    assert robot["link"] == "online"   # clean disconnect -> no death certificate
    assert robot["stale"] is True      # but no telemetry -> freshness timer flips
