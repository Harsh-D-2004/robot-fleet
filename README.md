## Architecture

```
robots (8 processes)  ──MQTT──▶  mosquitto (broker)  ──▶  backend  ──▶  REST + WebSocket
  replay events.jsonl            retains + queues          FleetState (in memory)
```

Three containers: **robots**, **mosquitto**, **backend**. They talk only through the
broker, so producers and consumers are fully decoupled.

## Run

Make sure to clone repo and run these commands from home directory and avoid mounted external drives while running
on linux

```bash
gh repo clone Harsh-D-2004/robot-fleet
```

```bash
docker compose up
```
That's it (`--build` whenever you change code; drop it otherwise.)

## See the feed

- **REST:** http://localhost:8000/robots  (also `/robots/{id}`, `/health`)
- **WebSocket:** `ws://localhost:8000/ws`  (snapshot on connect, then live updates)

```bash
curl -s localhost:8000/robots | jq        # whole fleet
websocat ws://localhost:8000/ws           # live stream
```

## Test

```bash
docker compose up -d     # stack must be running
pip install -r tests/requirements.txt
pytest -v                                 # integration + failure tests
```

## Design decisions (and why)

- **MQTT, not HTTP POST** — built for many small devices on flaky networks; gives us
  offline buffering, death detection, HTTP POST would also work, but we'd hand-build a lot of things such as queue to handle flakiness.
- **One topic per robot** (`fleet/{id}/state`, `fleet/{id}/status`) — retained messages
  are per-topic, so the backend cold-starts with the whole fleet's last state instantly.
- **Retained vs queue** — *retained* = latest per topic (cold start "what's true now");
  the persistent-session *queue* = the backlog missed while the backend was down.
- **Drop rule** — a message with an older `t` is ignored, so a late/reordered message
  can never overwrite newer state.
- **Two clocks** — the robot's `t` decides *ordering*; our `received_at` decides
  *freshness* (`stale`). Never mixed.
- **Three liveness signals, kept separate** — `status` (robot says what it's doing),
  `link` (broker's LWT: connection alive/dead), `stale` (backend's own timer: gone quiet).
  Each is owned by the only party that can know it.
- **Bounded queue (1000), not unlimited** — drops old overflow gracefully instead of
  OOM-ing the broker on a long outage. ~10 min tolerance at 8 robots.
- **State in memory, one object** — REST and WebSocket read the same `FleetState`, so
  they can never disagree.
- **Fixed backend client id + persistent session** — a restarted backend resumes the
  same broker session and gets the backlog; the id is a stable string, not the container id.

## AI delegation notes

Built with Claude Code (Opus), used as a pair-programmer throughout:

- **Design** — worked through the architecture, topic design, and the retained-vs-queue /
  two-clocks / drop-rule reasoning in discussion before writing code.
- **Code** — generated the robots, broker config, and the layered backend, iterating on
  structure (splitting into routes/controllers/services/helpers/models) and trimming to
  keep it lean.
- **Debugging** — caught and fixed real issues live: paho callback signatures, Mosquitto
  not supporting inline comments (corrupted the persistence path), and `pkill` missing
  from the slim image (added `procps`).
- **Verification** — ran the full stack in Docker and confirmed each behaviour end-to-end
- **Tests** — wrote the failure suite understanding in scenarios which it would fail.

Everything was reviewed and understood, not pasted blindly the design choices above are
ones I can defend line by line.
