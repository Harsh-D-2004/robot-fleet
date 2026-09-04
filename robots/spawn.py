
import json
import logging
import os
import signal
import subprocess
import sys
import time

LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s %(levelname)-5s [%(name)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("spawn")


def find_roster() -> str:
    if os.environ.get("ROBOTS_FILE"):
        return os.environ["ROBOTS_FILE"]
    here = os.path.dirname(os.path.abspath(__file__))
    candidate = os.path.join(here, "robots.json")
    if not os.path.exists(candidate):
        raise FileNotFoundError("robots.json not found next to spawn.py (or set ROBOTS_FILE)")
    return candidate


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    robot_py = os.path.join(here, "robot.py")

    roster_path = find_roster()
    roster = json.load(open(roster_path))
    ids = [r["robot_id"] for r in roster]
    log.info("roster: %d robots from %s → %s",
             len(ids), os.path.basename(roster_path), ", ".join(ids))

    procs: dict[str, subprocess.Popen] = {}
    for r in roster:
        rid = r["robot_id"]
        env = {**os.environ, "ROBOT_ID": rid}
        p = subprocess.Popen([sys.executable, robot_py, rid], env=env)
        procs[rid] = p
        log.info("launched %-4s (type=%s) as pid %d",
                 rid, r.get("robot_type", "?"), p.pid)

    def shutdown(signum, frame):
        log.info("received signal %s — terminating %d robot processes", signum, len(procs))
        for rid, p in procs.items():
            if p.poll() is None:
                p.terminate()  # SIGTERM → robot.py disconnects cleanly (no LWT)
        deadline = time.time() + 10
        for rid, p in procs.items():
            try:
                p.wait(timeout=max(0.0, deadline - time.time()))
            except subprocess.TimeoutExpired:
                log.warning("%s did not exit in time — killing", rid)
                p.kill()
        log.info("all robot processes stopped")
        sys.exit(0)

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    log.info("all %d robots launched; waiting for them to finish their windows", len(procs))
    while procs:
        for rid, p in list(procs.items()):
            rc = p.poll()
            if rc is not None:
                level = log.info if rc == 0 else log.warning
                level("robot %-4s (pid %d) exited with code %s", rid, p.pid, rc)
                del procs[rid]
        time.sleep(1)

    log.info("all robots have exited — spawn.py done")


if __name__ == "__main__":
    main()
