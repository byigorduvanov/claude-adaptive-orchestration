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
   "Observer prompt went unanswered" / "Generator paused for transport" of the same session is a stall
   (laptop sleep), not auth.
3. The newest claude-mem log: an explicit auth verdict in the last hour with no STORED after it:
   "[PARSER] SDK authentication failed", "Generator paused for auth", "Observer stopped ... reason=auth", or a
   "Response received" whose body is "Failed to authenticate..." / "Not logged in..." (that response is the
   failure, not a success). An "API Error: <status>" other than 401 (Cloudflare 403) is transient and ignored.
   Lines dated in the future, and WARN / verdict lines dated well before a line already read, are quoted
   text (a pasted heredoc), not events.

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
API_ERR = re.compile(rb"API Error: (\d{3})")  # any status but 401 (e.g. Cloudflare 403) is transient, not a login failure
TRANSIENT_S = 10  # the PARSER / "Observer stopped" lines that follow a transient response are its aftermath
FUTURE_S = 5  # a "line" dated later than now is a quoted heredoc, not an event
BACK_S = 5  # so is one dated well before a line already read: the log is written in time order
# "[ts] [LEVEL] [TAG   ] [session-N] message": marks count only in the message of their own tag, so a logged command
# that quotes them (ENQUEUED ... tool=Bash(grep STORED ...), PostToolUse) is not mistaken for the event itself.
LINE = re.compile(rb"\[(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d)[.\d]*\] \[\w+ *\] \[(\w+) *\] (?:\[session-(\d+)\] )?")
DB_ID = re.compile(rb"sessionDbId=(\d+)")
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


def _ts(key):
    return dt.datetime.strptime(key.decode(), "%Y-%m-%d %H:%M:%S").timestamp()


def _transient(text):
    m = API_ERR.search(text)
    return m is not None and m.group(1) != b"401"


def _kind(tag, msg):
    if tag == b"OAUTH" and any(k in msg for k in FAIL_MARKS):
        return "warn"
    if tag == b"SDK" and b"Response received" in msg[:40]:
        body = msg[msg.find(b"} ") + 2:] if b"} " in msg else b""
        if body.startswith(AUTH_BODIES):
            return "transient" if _transient(body) else "verdict"
        return "ok"
    if tag == b"DB" and msg.startswith(b"STORED"):
        return "ok"
    if tag == b"PARSER" and msg.startswith(b"SDK authentication failed"):
        return "transient" if _transient(msg) else "verdict"
    if tag == b"SESSION" and (msg.startswith(b"Generator paused for auth")
                              or (msg.startswith(b"Observer stopped") and b"reason=auth" in msg)):
        return "verdict"
    if (tag == b"SDK" and msg.startswith(b"Observer prompt went unanswered")) or \
            (tag == b"SESSION" and msg.startswith(b"Generator paused for transport")):
        return "stall"
    if tag in (b"SESSION", b"SDK") and msg.startswith(GEN_MARKS):
        return "gen"
    return None


def scan(data, now):
    # Two failure shapes, each only when nothing was stored after it (file order decides "after"):
    # - an explicit auth verdict (not a transient API error such as a Cloudflare 403);
    # - a generator WARN older than the grace period that no transport stall of the same session explains.
    # The harmless pattern, a generator WARN followed by STORED seconds later, stays silent.
    future_key = dt.datetime.fromtimestamp(now + FUTURE_S).strftime("%Y-%m-%d %H:%M:%S").encode()
    ev = {"warn": [], "ok": [], "gen": [], "verdict": [], "transient": [], "stall": []}
    max_key = None
    for idx, line in enumerate(data.split(b"\n")):
        m = LINE.match(line)
        if not m:
            continue
        key = m.group(1)
        if key > future_key:
            continue
        behind = max_key is not None and key < max_key
        if not behind:
            max_key = key
        tag, sid, msg = m.group(2), m.group(3), line[m.end():]
        kind = _kind(tag, msg)
        if kind is None:
            continue
        # Only alarm-raising lines are dropped when out of order: a log can mix clocks (2026-11-11: hook lines
        # 12:39, worker lines 06:39), so dropping STORED there would raise the false alarm this guards against.
        if behind and kind in ("warn", "verdict"):
            try:
                if _ts(max_key) - _ts(key) > BACK_S:
                    continue
            except ValueError:
                continue
        try:
            ts = _ts(key)
        except ValueError:
            continue
        if now - ts > WINDOW_S + max(GEN_NEAR_S, TRANSIENT_S):
            continue
        if sid is None:
            d = DB_ID.search(msg)
            sid = d.group(1) if d else None
        ev[kind].append((ts, idx, sid))
    last_ok = max((i for t, i, _ in ev["ok"] if now - t <= WINDOW_S), default=-1)
    verdicts = [i for t, i, sid in ev["verdict"] if now - t <= WINDOW_S
                and not any(s == sid and 0 <= t - tt <= TRANSIENT_S and ii < i for tt, ii, s in ev["transient"])]
    if verdicts and max(verdicts) > last_ok:
        return "SDK authentication failed in the last hour, nothing stored after it"
    warns = []
    for t, i, _ in ev["warn"]:
        if not GRACE_S < now - t <= WINDOW_S:
            continue
        sids = {s for tt, _, s in ev["gen"] if abs(tt - t) <= GEN_NEAR_S}
        if not sids:
            continue
        if any(ii > i and s in sids and s is not None for _, ii, s in ev["stall"]):
            continue
        warns.append(i)
    if warns and max(warns) > last_ok:
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
