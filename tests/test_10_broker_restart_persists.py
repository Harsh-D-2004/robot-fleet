"""Broker restart keeps state, because persistence writes it to disk.

After the broker restarts, the backend auto-reconnects and the fleet the API
served before is still present (retained state was persisted to the volume).
"""
import support


def test_broker_restart_keeps_state():
    before_ids = {robot["robot_id"] for robot in support.get_all_robots()}
    support.log.info("fleet before broker restart: %d robots", len(before_ids))
    assert len(before_ids) >= 1

    support.log.info("restarting the broker")
    support.run_compose("restart", "mosquitto")

    support.wait_until(
        lambda: support.get_health()["broker_connected"] is True,
        timeout=30,
        message="backend reconnected to the broker",
    )

    after_ids = {robot["robot_id"] for robot in support.get_all_robots()}
    support.log.info("fleet after broker restart: %d robots", len(after_ids))
    assert before_ids.issubset(after_ids)
