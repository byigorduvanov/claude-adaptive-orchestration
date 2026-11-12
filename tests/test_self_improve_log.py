#!/usr/bin/env python3
"""Runs self-improve-log.py as a subprocess, the way Claude Code does. Usage: python3 tests/test_self_improve_log.py"""
import json
import os
import subprocess
import sys
import tempfile
import time

HOOK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "hooks", "self-improve-log.py")
failures = 0


def run(stdin, out):
    env = dict(os.environ, SELF_IMPROVE_DIR=out)
    t = time.monotonic()
    r = subprocess.run([sys.executable, HOOK], input=stdin, capture_output=True, text=True, env=env)
    return r, (time.monotonic() - t) * 1000


def lines(out, name):
    p = os.path.join(out, name)
    return [json.loads(x) for x in open(p)] if os.path.exists(p) else []


skill = json.dumps({"hook_event_name": "PreToolUse", "tool_name": "Skill", "tool_input": {"skill": "memory-staleness-audit", "args": "x"},
                    "cwd": "/tmp/p", "session_id": "s1", "transcript_path": "/tmp/t.jsonl"})
end = json.dumps({"hook_event_name": "SessionEnd", "reason": "prompt_input_exit", "cwd": "/tmp/p", "session_id": "s1", "transcript_path": "/tmp/t.jsonl"})
CASES = [
    # stdin, expected (file, count) after the call
    (skill, ("skill-usage.jsonl", 1)),
    (end, ("sessions.jsonl", 1)),
    (json.dumps({"hook_event_name": "PreToolUse", "tool_name": "Bash", "tool_input": {"command": "ls"}}), None),
    (json.dumps({"hook_event_name": "PreToolUse", "tool_name": "Skill", "tool_input": {}}), None),
    (json.dumps({"hook_event_name": "PreToolUse", "tool_name": "Skill", "tool_input": "oops"}), None),
    (json.dumps({"hook_event_name": "SessionEnd"}), None),
    (json.dumps(["not", "a", "dict"]), None),
    ("broken {", None),
    ("", None),
]
slowest = 0.0
times = []
for stdin, expected in CASES:
    out = tempfile.mkdtemp()
    r, ms = run(stdin, out)
    slowest = max(slowest, ms)
    times.append(ms)
    got = [(n, len(lines(out, n))) for n in ("skill-usage.jsonl", "sessions.jsonl") if lines(out, n)]
    want = [expected] if expected else []
    if r.returncode != 0 or r.stdout or got != want:
        failures += 1
        print("FAIL", stdin[:60], "exit", r.returncode, got, repr(r.stdout[:40]))

# row content
out = tempfile.mkdtemp()
run(skill, out); run(skill, out); run(end, out)
s = lines(out, "skill-usage.jsonl")
e = lines(out, "sessions.jsonl")
if len(s) != 2 or s[0]["skill"] != "memory-staleness-audit" or s[0]["cwd"] != "/tmp/p" or "date" not in s[0]:
    failures += 1; print("FAIL skill row", s)
if len(e) != 1 or e[0]["transcript_path"] != "/tmp/t.jsonl" or e[0]["reason"] != "prompt_input_exit":
    failures += 1; print("FAIL session row", e)

# Stop fires every turn: one line per session; another session still gets its own line
out = tempfile.mkdtemp()
stop = json.dumps({"hook_event_name": "Stop", "cwd": "/tmp/p", "session_id": "s2", "transcript_path": "/tmp/t2.jsonl"})
other = json.dumps({"hook_event_name": "Stop", "cwd": "/tmp/p", "session_id": "s3", "transcript_path": "/tmp/t3.jsonl"})
run(stop, out); run(stop, out); run(other, out); run(end.replace('"s1"', '"s2"'), out)
e = lines(out, "sessions.jsonl")
if [x["session_id"] for x in e] != ["s2", "s3"]:
    failures += 1; print("FAIL dedupe", e)

# unwritable output dir: still exit 0, no output
r, _ = run(skill, "/dev/null/nope")
if r.returncode != 0 or r.stdout or r.stderr:
    failures += 1; print("FAIL unwritable dir", r.returncode, r.stderr[:80])

# budget: < 50 ms per call including python start (median, so one slow fork on a busy Mac does not flake)
median = sorted(times)[len(times) // 2]
if median > 50:
    failures += 1; print(f"FAIL slow: median {median:.0f} ms")

print(f"self-improve-log: {len(CASES) + 4} cases, {failures} failed, slowest {slowest:.0f} ms (incl. python start)")
sys.exit(1 if failures else 0)
