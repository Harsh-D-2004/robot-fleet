import pytest

import support


@pytest.fixture(scope="session", autouse=True)
def stack_is_running():
    try:
        support.wait_until(
            lambda: support.get_health()["broker_connected"] is True,
            timeout=15,
            message="backend /health not ready",
        )
    except AssertionError:
        pytest.exit(
            "Stack is not running. Start it first:\n"
            "    docker compose up -d --build\n"
            "then run the tests soon after (the robot-kill tests need live robots).",
            returncode=1,
        )
