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
# Line shapes copied from ~/.claude-mem/logs/claude-mem-2026-11-17.log. A real observer generation logs
# ENQUEUED -> "Generator auto-starting" -> WARN -> "Starting SDK query" within milliseconds (22:59:47, 23:05:47).
ENQ = "[INFO ] [QUEUE ] [session-921] ENQUEUED | sessionDbId=921 | messageId=2392 | type=observation | tool=Bash(ls) | depth=1"
GEN_START = "[INFO ] [SESSION] [session-921] Generator auto-starting (observation) using Claude SDK {queueDepth=1, historyLength=0}"
SDK_QUERY = "[INFO ] [SDK   ] Starting SDK query {sessionDbId=921, contentSessionId=9b92d4cb-5d72-4e1a-9332-cbf68cff5570, hasRealMemorySessionId=false, shouldResume=false, resume_parameter=(none - fresh start), "
RESPONSE = "[INFO ] [SDK   ] [session-921] \u2190 Response received (2655 chars) {promptNumber=4} <observation>"
STORED_REAL = "[INFO ] [DB    ] [session-921] STORED | sessionDbId=921 | memorySessionId=3da7576f-73f6-4bda-a913-29ee76ad0b4d | obsCount=1 | obsIds=[33091] | summaryId=none"
# Worker / scheduled agent-run spawns (21:20:59, 21:21:19, 22:11:03): a WARN with no generator, nothing to store.
AGENT_RUN = "[INFO ] [WORKER] Agent run (scheduled) starting on claude-code"
PID_LIVE = "[INFO ] [SYSTEM] Worker PID file points to a live process, skipping duplicate spawn"
READY = "[INFO ] [SYSTEM] Worker became ready while waiting on live PID"


def gen_warn(minutes_ago):
    """One observer generation spawn with its OAUTH WARN, as the worker logs it."""
    return [(minutes_ago, ENQ), (minutes_ago, GEN_START), (minutes_ago, WARN), (minutes_ago, SDK_QUERY)]


def idle_warn(minutes_ago):
    """A worker-side spawn: WARN, then only 'Worker became ready'."""
    return [(minutes_ago, AGENT_RUN), (minutes_ago, WARN), (minutes_ago, PID_LIVE), (minutes_ago, READY)]


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
                f.write(f"{text}\n" if minutes_ago is None else f"{stamp(minutes_ago)} {text}\n")
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
code, out, _ = case(None, gen_warn(40) + gen_warn(20) + gen_warn(10))
check("auth is broken" in out and "OAUTH" in out, f"OAUTH WARN in the last hour, nothing stored after it -> line ({out[:100]})")
code, out, _ = case(None, gen_warn(90) + gen_warn(80))
check(out == "", "WARN older than an hour -> silent")
code, out, _ = case(None, gen_warn(0.2))
check(out == "", "a WARN from seconds ago may still be followed by STORED -> silent")
code, out, _ = case(None, gen_warn(40) + [(39.9, "[INFO ] [SDK   ] [session-2] <- Response received (900 chars)")])
check(out == "", "a response after the WARN proves auth works -> silent")
code, out, _ = case(None, None)
check(code == 0 and out == "", "no files at all -> silent, exit 0")
code, out, _ = case(None, None, raw_health="{not json")
check(code == 0 and out == "", "corrupt health file -> silent, exit 0")
# Review 2026-11-17: a failure that starts after an earlier success in the same hour must still be caught
code, out, _ = case(None, gen_warn(50) + [(49, STORED)] + gen_warn(5))
check("auth is broken" in out, f"WARN, STORED, then WARN 5 min ago with nothing after -> line ({out[:60]})")
code, out, _ = case(None, [(49, STORED)] + gen_warn(20) + gen_warn(10))
check("auth is broken" in out, "STORED early, then only WARNs for 20 min -> line")
# Regression 2026-11-17 22:59: idle-worker WARNs (no generator, nothing queued) raised a false alarm.
code, out, _ = case(None, idle_warn(38) + idle_warn(37.7) + idle_warn(10))
check(code == 0 and out == "", f"idle-worker WARNs only (no generator) -> silent ({out[:60]})")
code, out, _ = case(None, [(55, STORED)] + idle_warn(38) + idle_warn(10))
check(out == "", f"STORED, then idle-worker WARNs only -> silent ({out[:60]})")
code, out, _ = case(None, idle_warn(40) + gen_warn(1) + [(0.85, RESPONSE), (0.85, STORED_REAL)])
check(out == "", f"idle WARNs, then generator WARN followed by STORED (22:59:47 shape) -> silent ({out[:60]})")
code, out, _ = case(None, idle_warn(40) + gen_warn(10))
check("auth is broken" in out, f"generator WARN with nothing after it -> line ({out[:60]})")
code, out, _ = case(None, gen_warn(10)[1:] )
check("auth is broken" in out, "generator WARN without ENQUEUED line still counts -> line")
code, out, _ = case(None, gen_warn(20) + [(19.8, STORED_REAL)] + idle_warn(5))
check(out == "", f"generator answered, later idle-worker WARN -> silent ({out[:60]})")
code, out, _ = case(None, [(10, WARN), (6, SDK_QUERY)])
check(out == "", "generator start minutes away from the WARN does not claim it -> silent")
# Logged commands quote the marks; only the tagged event counts (44 such lines in the 2026-11-17 log).
QUOTE_GEN = "[INFO ] [QUEUE ] [session-959] ENQUEUED | sessionDbId=959 | messageId=2399 | type=observation | tool=Bash(grep -E 'Generator auto-starting|Starting SDK query|[OAUTH ] Refusing to inject expired' x.log) | depth=1"
QUOTE_OK = "[INFO ] [HOOK  ] \u2192 PostToolUse: Bash(grep -E 'STORED \\||Response received' x.log)"
code, out, _ = case(None, idle_warn(10) + [(10, QUOTE_GEN)])
check(out == "", f"idle WARN next to a logged command quoting generator marks -> silent ({out[:60]})")
code, out, _ = case(None, gen_warn(10) + [(9, QUOTE_OK)])
check("auth is broken" in out, "generator WARN, then only a logged command quoting STORED -> line")
code, out, _ = case(None, [(10, QUOTE_GEN), (10, QUOTE_GEN)])
check(out == "", "a quoted OAUTH WARN is not a WARN -> silent")
# Review 2026-11-18, finding 1: the real failure is an explicit verdict, not only a silent WARN
# (claude-mem-2026-11-02.log 15:56:59, session-863, OAuth token revoked).
AUTH_RESP = "[INFO ] [SDK   ] [session-863] \u2190 Response received (95 chars) {promptNumber=11} Failed to authenticate: OAuth token revoked. Please log in again or contact your administrator."
AUTH_PARSER = "[ERROR] [PARSER] [session-863] SDK authentication failed; run /login to preserve queued batch {outputClass=prose, remediation=/login, preview=Failed to authenticate: OAuth token revoked. Please log in aga"
SPAWN_EXIT = "[WARN ] [SDK_SPAWN] [session-863] Claude process exited {code=1, signal=null, pid=5612}"
AUTH_PAUSE = "[WARN ] [SESSION] [session-863] Generator paused for auth; preserving buffered work {pendingCount=1}"
NOT_LOGGED = "[INFO ] [SDK   ] [session-863] \u2190 Response received (40 chars) {promptNumber=2} Not logged in \u00b7 Please run /login"
AUTH_FAIL = [AUTH_RESP, AUTH_PARSER, SPAWN_EXIT, AUTH_PAUSE]
code, out, _ = case(None, gen_warn(10) + [(10, t) for t in AUTH_FAIL])
check("auth is broken" in out, f"11-02 shape: generator WARN, Response 'Failed to authenticate', PARSER, paused for auth -> line ({out[:60]})")
code, out, _ = case(None, [(55, STORED)] + [(0.5, t) for t in AUTH_FAIL])
check("auth is broken" in out, "explicit auth failure 30 s ago, no WARN at all -> line at once (no grace)")
code, out, _ = case(None, [(0.5, AUTH_PAUSE)])
check("auth is broken" in out, "'Generator paused for auth' alone -> line")
code, out, _ = case(None, gen_warn(10) + [(10, NOT_LOGGED)])
check("auth is broken" in out, "Response body 'Not logged in' is a failure, not a success -> line")
code, out, _ = case(None, [(30, t) for t in AUTH_FAIL] + gen_warn(5) + [(4.9, STORED_REAL)])
check(out == "", f"auth failure, then a later generation stored -> silent (recovered) ({out[:60]})")
# Finding 2: laptop sleep (claude-mem-2026-11-16.log, 2026-11-17 02:35:29 WARN, 02:50:35 unanswered).
# Stall lines carry the same session as gen_warn (921); in the real 11-17 02:35 case both were session-906.
UNANSWERED = "[WARN ] [SDK   ] [session-921] Observer prompt went unanswered; preserving the claimed batch and stopping this generation {waitedMs=180000, claimed=1}"
TRANSPORT = "[WARN ] [SESSION] [session-921] Generator paused for transport; preserving buffered work {pendingCount=0, released=0}"
code, out, _ = case(None, gen_warn(16) + [(1, UNANSWERED), (1, TRANSPORT)])
check(out == "", f"generator WARN, then 'went unanswered' / 'paused for transport' -> silent, not auth ({out[:60]})")
code, out, _ = case(None, gen_warn(30) + [(25, UNANSWERED)] + gen_warn(10))
check("auth is broken" in out, "transport stall explains only earlier WARNs; a later unanswered generator WARN -> line")
code, out, _ = case(None, gen_warn(16) + [(1, UNANSWERED)] + [(0.5, t) for t in AUTH_FAIL])
check("auth is broken" in out, "transport stall does not hide an explicit auth failure -> line")
# Finding 4: each generator mark alone is enough; pool wait puts 'Generator auto-starting' >2 s before the WARN.
code, out, _ = case(None, [(10.4, GEN_START), (10, WARN), (10, SDK_QUERY)])
check("auth is broken" in out, "pool wait: Generator auto-starting 24 s earlier, Starting SDK query adjacent -> line")
code, out, _ = case(None, [(10, GEN_START), (10, WARN)])
check("auth is broken" in out, "only 'Generator auto-starting' next to the WARN -> line")
code, out, _ = case(None, [(10, WARN), (10, SDK_QUERY)])
check("auth is broken" in out, "only 'Starting SDK query' next to the WARN -> line")
code, out, _ = case(None, [(10, GEN_START), (10, QUOTE_GEN), (10, SDK_QUERY)])
check(out == "", f"real generator start, WARN text only quoted in an ENQUEUED line -> silent ({out[:60]})")
code, out, _ = case(None, gen_warn(10) + [(None, "[2099-01-01 00:00:00.000] [INFO ] [DB    ] [session-1] STORED | obsIds=[1]")])
check("auth is broken" in out, "a future-dated STORED (quoted heredoc line) does not count -> line")
# Review round 2 (2026-11-18).
# Transient: Cloudflare 403 reported as "Failed to authenticate" (claude-mem-2026-11-13.log 16:47:00, session-902);
# the next generation stored normally, so it is not a login failure.
CF = ["[INFO ] [SDK   ] [session-902] \u2190 Response received (71 chars) {promptNumber=3} Failed to authenticate. API Error: 403 Attention Required! | Cloudflare",
      "[ERROR] [PARSER] [session-902] SDK authentication failed; run /login to preserve queued batch {outputClass=prose, remediation=/login, preview=Failed to authenticate. API Error: 403 Attention Required! | Cloudflare}",
      "[WARN ] [SDK_SPAWN] [session-902] Claude process exited {code=1, signal=null, pid=77230}",
      "[WARN ] [SESSION] [session-902] Observer stopped; skipped pending inputs, awaiting fresh activity {reason=auth}"]
code, out, _ = case(None, [(55, STORED)] + [(5, t) for t in CF])
check(out == "", f"11-13 Cloudflare 403 'Failed to authenticate' -> silent, transient ({out[:60]})")
code, out, _ = case(None, [(5, t.replace("403 Attention Required! | Cloudflare", "401 {\"type\":\"authentication_error\"}")) for t in CF])
check("auth is broken" in out, "same shape with API Error 401 -> line")
code, out, _ = case(None, [(5, CF[3])])
check("auth is broken" in out, "'Observer stopped ... {reason=auth}' alone -> line")
code, out, _ = case(None, [(5, t) for t in CF] + [(4, AUTH_PAUSE.replace("863", "902"))])
check("auth is broken" in out, "a later auth pause, past the transient's own aftermath -> line")
# Quoted heredoc lines dated in the past (a pasted log excerpt) are not events.
code, out, _ = case(None, [(20, STORED_REAL), (5, AGENT_RUN)] + [(None, f"{stamp(10)} {AUTH_PAUSE}"), (None, f"{stamp(8)} {WARN}"), (None, f"{stamp(8)} {SDK_QUERY}")])
check(out == "", f"past-dated quoted verdict / WARN after newer lines -> silent ({out[:60]})")
# A stall excuses only its own session's WARN.
OTHER_STALL = UNANSWERED.replace("session-921", "session-906")
code, out, _ = case(None, gen_warn(10) + [(2, OTHER_STALL)])
check("auth is broken" in out, "another session's 'went unanswered' does not excuse this WARN -> line")
# File order, not one-second timestamps, decides what came after.
code, out, _ = case(None, [(5, AUTH_PAUSE), (5, STORED_REAL)])
check(out == "", "verdict then STORED in the same second -> silent")
code, out, _ = case(None, [(5, STORED_REAL), (5, AUTH_PAUSE)])
check("auth is broken" in out, "STORED then verdict in the same second -> line")
# Mixed clocks (claude-mem-2026-11-11.log line 30: hook line 12:39, then worker lines 06:39): a STORED dated
# before an earlier line still counts, so the out-of-order guard never raises an alarm.
code, out, _ = case(None, gen_warn(20) + [(1, AGENT_RUN), (None, f"{stamp(15)} {STORED_REAL}")])
check(out == "", f"out-of-order STORED still clears an older generator WARN -> silent ({out[:60]})")
# Review round 3: only Cloudflare / 429 / 5xx are transient; a 403 permission_error is a real auth failure.
PERM = '[INFO ] [SDK   ] [session-902] \u2190 Response received (120 chars) {promptNumber=3} Failed to authenticate. API Error: 403 {"type":"error","error":{"type":"permission_error","message":"OAuth authentication is currently not allowed for this organization."}}'
code, out, _ = case(None, [(55, STORED), (5, PERM)])
check("auth is broken" in out, "403 permission_error (not Cloudflare) -> line")
code, out, _ = case(None, [(5, CF[0].replace("403 Attention Required! | Cloudflare", "529 Overloaded"))])
check(out == "", f"529 overloaded -> silent, transient ({out[:60]})")
code, out, _ = case(None, [(5, CF[0]), (4.92, CF[1].replace("403 Attention Required! | Cloudflare", "401 authentication_error"))])
check("auth is broken" in out, "transient 403, then a 401 PARSER line 5 s later -> line (not its aftermath)")
code, out, _ = case(None, [(5, CF[0]), (4.87, CF[3])])
check(out == "", f"'Observer stopped' 8 s after a transient 403 is its aftermath -> silent ({out[:60]})")
code, out, _ = case(None, [(5, CF[0]), (4.5, CF[3])])
check("auth is broken" in out, "'Observer stopped' 30 s after a transient 403 -> line")
# A line dated slightly ahead of now must not hide a real verdict read after it.
code, out, _ = case(None, [(None, f"{stamp(-0.05)} {AGENT_RUN}"), (5, AUTH_PAUSE)])
check("auth is broken" in out, "line dated 3 s ahead, then a real verdict -> line")
print(f"mem-health: {checks} checks, {failures} failed")
sys.exit(1 if failures else 0)
