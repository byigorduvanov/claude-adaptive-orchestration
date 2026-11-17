#!/usr/bin/env python3
"""mem-health.py: one context line at session start when claude-mem's observer cannot authenticate."""
import datetime as dt
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

HOOK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "hooks", "mem-health.py")
failures = 0
checks = 0
WARN = "[WARN ] [OAUTH ] Refusing to inject expired CLAUDE_CODE_OAUTH_TOKEN: The Claude Code login in the credential store has expired. {expiresAt=1790554711012}"
STORED = "[INFO ] [DB    ] [session-1] STORED | sessionDbId=1 | obsCount=1 | obsIds=[1] | summaryId=none"


def check(ok, what):
    global failures, checks
    checks += 1
    if not ok:
        failures += 1
        print("FAIL", what)


def ms(minutes_ago):
    return int((time.time() - minutes_ago * 60) * 1000)


def stamp(minutes_ago):
    t = dt.datetime.now() - dt.timedelta(minutes=minutes_ago)
    return t.strftime("[%Y-%m-%d %H:%M:%S.") + f"{t.microsecond // 1000:03d}]"


def case(health=None, log=None, raw_health=None):
    d = tempfile.mkdtemp()
    hp = os.path.join(d, "observer-health.json")
    if raw_health is not None:
        open(hp, "w").write(raw_health)
    elif health is not None:
        json.dump(health, open(hp, "w"))
    logs = os.path.join(d, "logs")
    os.mkdir(logs)
    if log is not None:
        name = dt.datetime.now().strftime("claude-mem-%Y-%m-%d.log")
        with open(os.path.join(logs, name), "w") as f:
            for minutes_ago, text in log:
                f.write(f"{stamp(minutes_ago)} {text}\n")
    env = dict(os.environ, MEM_HEALTH_FILE=hp, MEM_LOG_DIR=logs)
    t0 = time.monotonic()
    r = subprocess.run([sys.executable, HOOK], input="{}", capture_output=True, text=True, env=env)
    took = time.monotonic() - t0
    shutil.rmtree(d)
    return r.returncode, r.stdout.strip(), took


def health(kind, err_min, ok_min):
    return {"consecutiveFailures": 0, "lastErrorAt": ms(err_min) if err_min is not None else None,
            "lastErrorMessage": "Claude Code could not authenticate the observer",
            "lastSuccessAt": ms(ok_min) if ok_min is not None else None, "lastErrorKind": kind}


code, out, took = case(health("auth_invalid", 60 * 24 * 4, 1), [(30, WARN), (30, STORED)])
check(code == 0 and out == "", f"healthy: old auth error, WARN followed by STORED (app-token wrapper) -> silent ({out[:80]})")
check(took < 0.2, f"runs under 200 ms ({took * 1000:.0f} ms)")
code, out, _ = case(health("auth_invalid", 5, 60))
check(code == 0 and out.startswith("claude-mem observer auth is broken (auth_invalid") and "run skill claude-mem-observer-auth-heal before other work" in out,
      f"auth_invalid newer than lastSuccessAt -> one line ({out[:100]})")
check(out.count("\n") == 0, "exactly one line")
code, out, _ = case(health("auth_invalid", 5, None))
check("auth is broken" in out, "auth error with no success ever -> line")
code, out, _ = case(health("quota_exhausted", 5, 60))
check(out == "", f"quota is not an auth failure -> silent ({out[:60]})")
code, out, _ = case(None, [(40, WARN), (20, WARN), (10, WARN)])
check("auth is broken" in out and "OAUTH" in out, f"OAUTH WARN in the last hour, nothing stored after it -> line ({out[:100]})")
code, out, _ = case(None, [(90, WARN), (80, WARN)])
check(out == "", "WARN older than an hour -> silent")
code, out, _ = case(None, [(0.2, WARN)])
check(out == "", "a WARN from seconds ago may still be followed by STORED -> silent")
code, out, _ = case(None, [(40, WARN), (39.9, "[INFO ] [SDK   ] [session-2] <- Response received (900 chars)")])
check(out == "", "a response after the WARN proves auth works -> silent")
code, out, _ = case(None, None)
check(code == 0 and out == "", "no files at all -> silent, exit 0")
code, out, _ = case(None, None, raw_health="{not json")
check(code == 0 and out == "", "corrupt health file -> silent, exit 0")
print(f"mem-health: {checks} checks, {failures} failed")
sys.exit(1 if failures else 0)
