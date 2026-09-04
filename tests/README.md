# Integration & Failure Tests

These are **integration tests**, not unit tests. Each one runs against the **live
stack** and checks behaviour through the real system (HTTP, WebSocket, MQTT), and
the later ones deliberately **break a service** and assert the system copes.

One scenario per file, ordered so non-destructive tests run first and the
service-killing ones run last.

| File | What it proves | Breaks anything? |
|------|----------------|------------------|
| `test_04_drop_rule_out_of_order.py` | **drop rule** rejects a late/older message (trickiest logic) | no |
| `test_06_rest_ws_consistency.py` | REST and WS agree on the same fleet | no |
| `test_07_robot_hard_kill_lwt.py` | SIGKILL a robot → `link: lost` (LWT) | kills a robot |
| `test_08_robot_clean_kill_stays_online.py` | SIGTERM a robot → stays `online`, goes `stale` | kills a robot |
| `test_09_backend_restart_recovers.py` | backend restart → fleet recovered | restarts backend |
| `test_10_broker_restart_persists.py` | broker restart → state survives (persistence) | restarts broker |

Each test logs its steps live (via `log_cli` in `pytest.ini`), so you can watch
what it does as it runs.

## Run

**1. Start the stack** (in one terminal, or detached):
```bash
cd robot-fleet
docker compose up
```

**2. Install test deps and run** (soon after starting — the kill tests need live robots):
```bash
pip install -r tests/requirements.txt
pytest tests/ -v
```

Run a single scenario:
```bash
pytest tests/test_04_drop_rule_out_of_order.py -v
```
