"""The backend recovers the fleet after a restart.

Because it reconnects with the same fixed client id and pulls the retained
snapshot, a restarted backend returns the full fleet again with no manual steps.
"""
import support


def test_backend_restart_recovers_fleet():
    before_ids = {robot["robot_id"] for robot in support.get_all_robots()}
    support.log.info("fleet before restart: %d robots", len(before_ids))
    assert len(before_ids) >= 1

    support.log.info("stopping then starting the backend")
    support.run_compose("stop", "backend")
    support.run_compose("start", "backend")

    support.wait_until(
        lambda: support.get_health()["broker_connected"] is True,
        timeout=30,
        message="backend reconnected after restart",
    )
    support.wait_until(
        lambda: len(support.get_all_robots()) >= len(before_ids),
        timeout=30,
        message="fleet recovered after backend restart",
    )
    support.log.info("fleet recovered after backend restart")
