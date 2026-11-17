#!/usr/bin/env python3
"""SessionStart: one context line when claude-mem's observer cannot authenticate; silent when healthy.

Signals (either one):
1. observer-health.json: lastErrorKind is an auth kind and lastErrorAt is newer than lastSuccessAt.
2. The newest claude-mem log: an OAUTH "Refusing to inject expired" / "Not logged in" line in the
   last hour with no STORED or "Response received" after it. Under the app-token wrapper
   (skill claude-mem-observer-auth-heal, 4c) that WARN appears on every spawn while the observer
   works, so a WARN alone is not a failure; a WARN with nothing answered after it is.

Always exits 0. Paths: MEM_HEALTH_FILE, MEM_LOG_DIR (defaults under ~/.claude-mem).
"""
import datetime as dt
import glob
import json
import os
import sys
import time

AUTH_KINDS = {"auth_invalid", "setup_required"}
WINDOW_S = 3600
GRACE_S = 120  # a spawn this recent may still be answered
TAIL_BYTES = 2 * 1024 * 1024
FAIL_MARKS = (b"Refusing to inject expired", b"Not logged in")
OK_MARKS = (b"STORED", b"Response received")


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
    now = time.time()
    first_fail = None
    answered_after = False
    for line in data.split(b"\n"):
        is_fail = b"[OAUTH" in line and any(m in line for m in FAIL_MARKS)
        is_ok = not is_fail and any(m in line for m in OK_MARKS)
        if not (is_fail or is_ok) or not line.startswith(b"[20"):
            continue
        try:
            ts = dt.datetime.strptime(line[1:20].decode(), "%Y-%m-%d %H:%M:%S").timestamp()
        except ValueError:
            continue
        age = now - ts
        if age > WINDOW_S:
            continue
        if is_fail and first_fail is None and age > GRACE_S:
            first_fail = ts
        elif is_ok and first_fail is not None and ts >= first_fail:
            answered_after = True
    if first_fail is not None and not answered_after:
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
