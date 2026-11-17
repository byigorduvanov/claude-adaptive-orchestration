#!/usr/bin/env python3
"""SessionStart: one context line when claude-mem's observer cannot authenticate; silent when healthy.

Signals (any one):
1. observer-health.json: lastErrorKind is an auth kind and lastErrorAt is newer than lastSuccessAt.
2. The newest claude-mem log: an OAUTH "Refusing to inject expired" / "Not logged in" line in the
   last hour that belongs to an observer generation ("Generator auto-starting" / "Starting SDK query"
   within GEN_NEAR_S of it) with no STORED or "Response received" after it. Under the app-token wrapper
   (skill claude-mem-observer-auth-heal, 4c) that WARN appears on every spawn while the observer
   works, so a WARN alone is not a failure; a generator WARN with nothing answered after it is.
   Worker / scheduled agent-run spawns log the same WARN with no generator and nothing to store
   ("Worker became ready while waiting on live PID"); they are ignored. A generator WARN followed by
   "Observer prompt went unanswered" / "Generator paused for transport" is a stall (laptop sleep), not auth.
3. The newest claude-mem log: an explicit auth verdict in the last hour with no STORED after it:
   "[PARSER] SDK authentication failed", "Generator paused for auth", or a "Response received" whose
   body is "Failed to authenticate..." / "Not logged in..." (that response is the failure, not a success).

Always exits 0. Paths: MEM_HEALTH_FILE, MEM_LOG_DIR (defaults under ~/.claude-mem).
"""
import datetime as dt
import glob
import json
import os
import re
import sys
import time

AUTH_KINDS = {"auth_invalid", "setup_required"}
WINDOW_S = 3600
GRACE_S = 120  # a spawn this recent may still be answered
TAIL_BYTES = 2 * 1024 * 1024
FAIL_MARKS = (b"Refusing to inject expired", b"Not logged in")
GEN_MARKS = (b"Generator auto-starting", b"Starting SDK query")
AUTH_BODIES = (b"Failed to authenticate", b"Not logged in")
FUTURE_S = 60  # a "line" dated later than now is a quoted heredoc, not an event
# "[ts] [LEVEL] [TAG   ] [session-N] message": marks count only in the message of their own tag, so a logged command
# that quotes them (ENQUEUED ... tool=Bash(grep STORED ...), PostToolUse) is not mistaken for the event itself.
LINE = re.compile(rb"\[(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d)[.\d]*\] \[\w+ *\] \[(\w+) *\] (?:\[session-\d+\] )?")
GEN_NEAR_S = 2  # the generator logs its start and the WARN within milliseconds of each other


def from_health(path):
    try:
        h = json.load(open(path))
    except Exception:
        return None
    kind = h.get("lastErrorKind")
    err = h.get("lastErrorAt") or 0
    ok = h.get("lastSuccessAt") or 0
    if kind in AUTH_KINDS and err > ok:
        return kind
    return None


def from_log(log_dir):
    logs = glob.glob(os.path.join(log_dir, "claude-mem-*.log"))
    if not logs:
        return None
    path = max(logs, key=os.path.getmtime)
    if time.time() - os.path.getmtime(path) > WINDOW_S:
        return None
    with open(path, "rb") as f:
        f.seek(0, 2)
        size = f.tell()
        f.seek(max(0, size - TAIL_BYTES))
        data = f.read()
    return scan(data, time.time())


def scan(data, now):
    # The harmless pattern is a generator WARN followed by STORED seconds later. A real failure is a generator WARN
    # older than the grace period with no STORED after it (and no transport stall explaining it), or an explicit
    # auth verdict with no STORED after it, even when STOREDs came earlier in the hour.
    fails, oks, gens, verdicts, stalls = [], [], [], [], []
    for line in data.split(b"\n"):
        m = LINE.match(line)
        if not m:
            continue
        tag, msg = m.group(2), line[m.end():]
        if tag == b"OAUTH" and any(k in msg for k in FAIL_MARKS):
            bucket = fails
        elif tag == b"SDK" and b"Response received" in msg[:40]:
            body = msg[msg.find(b"} ") + 2:] if b"} " in msg else b""
            bucket = verdicts if body.startswith(AUTH_BODIES) else oks
        elif tag == b"DB" and msg.startswith(b"STORED"):
            bucket = oks
        elif (tag == b"PARSER" and msg.startswith(b"SDK authentication failed")) or \
                (tag == b"SESSION" and msg.startswith(b"Generator paused for auth")):
            bucket = verdicts
        elif (tag == b"SDK" and msg.startswith(b"Observer prompt went unanswered")) or \
                (tag == b"SESSION" and msg.startswith(b"Generator paused for transport")):
            bucket = stalls
        elif tag in (b"SESSION", b"SDK") and msg.startswith(GEN_MARKS):
            bucket = gens
        else:
            continue
        try:
            ts = dt.datetime.strptime(m.group(1).decode(), "%Y-%m-%d %H:%M:%S").timestamp()
        except ValueError:
            continue
        if -FUTURE_S <= now - ts <= WINDOW_S + GEN_NEAR_S:
            bucket.append(ts)
    last_fail = max((t for t in fails if GRACE_S < now - t <= WINDOW_S
                     and any(abs(g - t) <= GEN_NEAR_S for g in gens)
                     and not any(s >= t for s in stalls)), default=None)
    last_verdict = max((t for t in verdicts if now - t <= WINDOW_S), default=None)
    last_ok = max((t for t in oks if now - t <= WINDOW_S), default=None)
    if last_verdict is not None and (last_ok is None or last_ok <= last_verdict):
        return "SDK authentication failed in the last hour, nothing stored after it"
    if last_fail is not None and (last_ok is None or last_ok < last_fail):
        return "OAUTH WARN in the last hour, nothing stored after it"
    return None


def main():
    home = os.path.expanduser("~/.claude-mem")
    hp = os.environ.get("MEM_HEALTH_FILE") or os.path.join(home, "observer-health.json")
    ld = os.environ.get("MEM_LOG_DIR") or os.path.join(home, "logs")
    reason = None
    try:
        reason = from_health(hp)
    except Exception:
        pass
    if not reason:
        try:
            reason = from_log(ld)
        except Exception:
            pass
    if reason:
        print(f"claude-mem observer auth is broken ({reason}): run skill claude-mem-observer-auth-heal before other work")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
