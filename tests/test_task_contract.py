#!/usr/bin/env python3
"""Runs task-contract.py as a subprocess, the way Claude Code does. Usage: python3 tests/test_task_contract.py"""
import os
import subprocess
import sys

HOOK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "hooks", "task-contract.py")
CASES = [
    ('{"prompt":"fix this"}', True),
    ('{"prompt":"<system-reminder>ctx</system-reminder>fix this"}', True),
    ('{"prompt":"<pasted_content id=\\"x\\">log</pasted_content>"}', True),
    ('{"prompt":"<task-notification>x"}', False),
    ('{"prompt":"<side-sessions-event>x"}', False),
    ('{"prompt":"<ci-monitor-event>x"}', False),
    ('{"prompt":"[Artifact comment sent to Claude]"}', False),
    ('{"prompt":"<local-command-stdout>x"}', False),
    ('{"prompt":"<system-reminder>\\n[SYSTEM NOTIFICATION - NOT USER INPUT]"}', False),
    ("broken", False),
]
failures = 0
for stdin, expected in CASES:
    r = subprocess.run([sys.executable, HOOK], input=stdin, capture_output=True, text=True)
    got = r.stdout.startswith("Task contract") and "\n7. " in r.stdout
    if r.returncode != 0 or got != expected or (not expected and r.stdout):
        failures += 1
        print("FAIL", stdin, "exit", r.returncode, repr(r.stdout[:40]))

# context-size reminder: fires only past the limit, never on app events
import json, tempfile
def transcript(tokens, sidechain_tokens=None):
    f = tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False)
    f.write(json.dumps({"type": "assistant", "message": {"usage": {"input_tokens": 2, "cache_creation_input_tokens": 1000, "cache_read_input_tokens": tokens - 1002}}}, separators=(",", ":")) + "\n")
    if sidechain_tokens:
        f.write(json.dumps({"isSidechain": True, "message": {"usage": {"input_tokens": 2, "cache_creation_input_tokens": 0, "cache_read_input_tokens": sidechain_tokens}}}, separators=(",", ":")) + "\n")
    f.close()
    return f.name
CTX = [
    ("fix this", transcript(237000), True),
    ("fix this", transcript(90000), False),
    ("fix this", transcript(90000, sidechain_tokens=400000), False),
    ("fix this", "/nonexistent.jsonl", False),
    ("<task-notification>x", transcript(237000), False),
]
for prompt, path, expected in CTX:
    r = subprocess.run([sys.executable, HOOK], input=json.dumps({"prompt": prompt, "transcript_path": path}), capture_output=True, text=True)
    got = "new session" in r.stdout and "Context is" in r.stdout
    if r.returncode != 0 or got != expected:
        failures += 1
        print("FAIL context", prompt, path, "exit", r.returncode, repr(r.stdout[-80:]))
# per-project contract: .claude/task-contract.md at or above cwd replaces the code contract
proj = tempfile.mkdtemp(); os.makedirs(os.path.join(proj, ".claude")); os.makedirs(os.path.join(proj, "sub"))
empty = tempfile.mkdtemp(); os.makedirs(os.path.join(empty, ".claude"))
open(os.path.join(proj, ".claude", "task-contract.md"), "w").write("Own contract\n1. rule\n")
open(os.path.join(empty, ".claude", "task-contract.md"), "w").write("")
OWN = [
    (os.path.join(proj, "sub"), "Own contract\n1. rule\n"),
    (empty, ""),
    (tempfile.mkdtemp(), None),
]
for cwd, expected in OWN:
    r = subprocess.run([sys.executable, HOOK], input=json.dumps({"prompt": "fix this", "cwd": cwd}), capture_output=True, text=True)
    ok = r.stdout.startswith("Task contract") if expected is None else r.stdout == expected
    if r.returncode != 0 or not ok:
        failures += 1
        print("FAIL project contract", cwd, "exit", r.returncode, repr(r.stdout[:60]))
print(f"{len(CASES) + len(CTX) + len(OWN)} cases, {failures} failures")
sys.exit(1 if failures else 0)
