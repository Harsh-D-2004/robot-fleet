# Robot Fleet — Backend (Assignment 2)

Eight mock robots publish their telemetry over MQTT; a broker sits in the middle;
a backend consumes everything, holds one live picture of the fleet, and exposes it
two ways — REST (poll) and WebSocket (push) — that always agree.

## Architecture

```
robots (8 processes)  ──MQTT──▶  mosquitto (broker)  ──▶  backend  ──▶  REST + WebSocket
  replay events.jsonl            retains + queues          FleetState (in memory)
```

Three containers: **robots**, **mosquitto**, **backend**. They talk only through the
broker, so producers and consumers are fully decoupled.

## Run

```bash
docker compose up --build
```
That's it — no manual steps. (`--build` whenever you change code; drop it otherwise.)

Put the two data files in `robots/`: `events.jsonl` and `robots.json`.

## See the feed

- **REST:** http://localhost:8000/robots  (also `/robots/{id}`, `/health`)
- **WebSocket:** `ws://localhost:8000/ws`  (snapshot on connect, then live updates)

```bash
curl -s localhost:8000/robots | jq        # whole fleet
websocat ws://localhost:8000/ws           # live stream
```

## Test

```bash
docker compose up -d --build              # stack must be running
pip install -r tests/requirements.txt
pytest -v                                 # integration + failure tests
```
See `tests/README.md` for what each test does.

## Design decisions (and why)

- **MQTT, not HTTP POST** — built for many small devices on flaky networks; gives us
  offline buffering, death detection, and a second consumer for free. HTTP POST would
  also work, but we'd hand-build all of that.
- **One topic per robot** (`fleet/{id}/state`, `fleet/{id}/status`) — retained messages
  are per-topic, so the backend cold-starts with the whole fleet's last state instantly.
- **Retained vs queue** — *retained* = latest per topic (cold start "what's true now");
  the persistent-session *queue* = the backlog missed while the backend was down.
- **Drop rule** — a message with an older `t` is ignored, so a late/reordered message
  can never overwrite newer state (keeps the data's "battery only rises while charging"
  invariant). This is the trickiest bit and the focus of the tests.
- **Two clocks** — the robot's `t` decides *ordering*; our `received_at` decides
  *freshness* (`stale`). Never mixed.
- **Three liveness signals, kept separate** — `status` (robot says what it's doing),
  `link` (broker's LWT: connection alive/dead), `stale` (backend's own timer: gone quiet).
  Each is owned by the only party that can know it.
- **Bounded queue (1000), not unlimited** — drops old overflow gracefully instead of
  OOM-ing the broker on a long outage. ~10 min tolerance at 8 robots.
- **State in memory, one object** — REST and WebSocket read the same `FleetState`, so
  they can never disagree (the graded consistency requirement). No second store to drift.
- **Fixed backend client id + persistent session** — a restarted backend resumes the
  same broker session and gets the backlog; the id is a stable string, not the container id.
- **Robots publish their own type** in the birth message — so the backend needs no roster
  file (the producer owns its metadata).
- **Single-pass replay** — robots play the recorded window once, then exit cleanly (no
  fake looped feed; that's Assignment 1's job).
- **Layered backend** (routes / controllers / services / helpers / models) — small files,
  each with one job, easy to read and test.

## Known limits

- **Single broker + single backend** — fine at 8 robots. At ~500, the broker's connection
  count and the queue window (10 min → 10 s) are the first things to break; the path is a
  clustered broker and a log with offsets (NATS JetStream / Kafka bridge).
- **No auth/TLS** on the broker (demo only).

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
  (retained cold-start, LWT on kill, drop rule, REST/WS consistency, restart recovery).
- **Tests** — wrote the integration/failure suite one scenario per file.

Everything was reviewed and understood, not pasted blindly — the design choices above are
ones I can defend line by line.
