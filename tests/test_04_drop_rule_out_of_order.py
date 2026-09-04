"""The trickiest logic: a late / out-of-order message must be dropped.

We publish a newer message (t=215) and then an older one (t=205) for the same
robot, straight through the real broker, and assert the backend kept the newer
state. Without the drop rule, the older message would overwrite it and the
battery would appear to change backwards.
"""
import time

import support

ROBOT_ID = "rTestDrop"


def test_out_of_order_message_is_dropped():
    support.log.info("step 1: publish the NEWER message (t=215)")
    support.publish_state(ROBOT_ID, t=215, battery=40.2, status="idle")
    support.wait_until(
        lambda: support.get_robot(ROBOT_ID)["t"] == 215,
        message="first (newer) message was applied",
    )

    support.log.info("step 2: publish the OLDER message (t=205) — should be dropped")
    support.publish_state(ROBOT_ID, t=205, battery=40.3, status="idle")
    time.sleep(1)  # give the backend a moment to (not) apply it

    robot = support.get_robot(ROBOT_ID)
    support.log.info("final state: t=%s battery=%s (expected t=215, battery=40.2)",
                     robot["t"], robot["battery"])

    assert robot["t"] == 215
    assert robot["battery"] == 40.2
