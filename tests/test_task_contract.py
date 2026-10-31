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
print(f"{len(CASES)} cases, {failures} failures")
sys.exit(1 if failures else 0)
