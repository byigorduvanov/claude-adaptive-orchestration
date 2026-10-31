#!/usr/bin/env python3
"""Runs guard-bash.py as a subprocess, the way Claude Code does. Usage: python3 tests/test_guard.py"""
import json
import os
import subprocess
import sys
import tempfile

HOOK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "hooks", "guard-bash.py")
tmp = tempfile.mkdtemp()
shared = os.path.join(tmp, "shared", "repo")
other = os.path.join(tmp, "other")
os.makedirs(shared)
os.makedirs(other)
cfg = os.path.join(tmp, "cfg.json")
json.dump({"shared_checkouts": [os.path.join(tmp, "shared")], "blocked_hosts": ["203.0.113.7"]}, open(cfg, "w"))
ENV = dict(os.environ, GUARD_BASH_CONFIG=cfg)

CASES = [
    ("git push --force origin main", other, "deny"),
    ("git push -f", other, "deny"),
    ("cd x && git push --force-with-lease=main:abc origin main", other, "deny"),
    ("git push origin +main", other, "deny"),
    ("git -C /tmp/r push --force", other, "deny"),
    ("OWNER_APPROVED_FORCE_PUSH=1 git push --force origin main", other, None),
    ("cd x && OWNER_APPROVED_FORCE_PUSH=1 git push -f", other, None),
    ("git push origin main", other, None),
    ("git push -u origin feat", other, None),
    ("git commit -m 'never git push --force here' && git push origin main", other, None),
    ("echo 'git push --force'", other, None),
    ('git push "--force" origin main', other, "deny"),
    ("git push '-f' origin main", other, "deny"),
    ('git push origin "+main"', other, "deny"),
    ("git push -fu origin main", other, "deny"),
    ("git push -uf origin main", other, "deny"),
    ("git push --follow-tags origin main", other, None),
    ("git log --force", other, None),
    ("git fetch -f", other, None),
    ("git add -A", shared, "deny"),
    ("git add .", shared, "deny"),
    ("git add --all && git commit -m x", shared, "deny"),
    (f"git -C {shared} add -A", other, "deny"),
    ("git add --update", shared, "deny"),
    ("git add src/a.go go.mod", shared, None),
    (f'cd "{other}" && git add -A', shared, None),
    (f"cd {shared} && git add .", other, "deny"),
    (f'cd "{shared}" && git add -A', other, "deny"),
    ('R=/x; cd "$R" && git add -A', shared, None),
    ("cd sub; git add -A", shared, "deny"),
    (f"(cd {other}; git status) && git log", shared, None),
    ("git add -A", other, None),
    ("git add -p", shared, None),
    ("ssh root@203.0.113.7 ls", other, "deny"),
    ("scp a root@203.0.113.7:/x", shared, "deny"),
    ("ssh root@203.0.113.70 ls", other, None),
    ("ssh example-host ls", other, None),
    ("grep 203.0.113.7 notes.md", other, None),
    ("", other, None),
]

failures = 0
for cmd, cwd, want in CASES:
    r = subprocess.run([HOOK], input=json.dumps({"tool_input": {"command": cmd}, "cwd": cwd}), capture_output=True, text=True, env=ENV)
    got = json.loads(r.stdout)["hookSpecificOutput"]["permissionDecision"] if r.stdout.strip() else None
    if got != want or r.returncode != 0:
        failures += 1
        print(f"FAIL {cmd!r}: want {want}, got {got}, exit {r.returncode}: {r.stderr[:120]}")
for bad in ("not json", "{}", '{"tool_input":null}'):
    r = subprocess.run([HOOK], input=bad, capture_output=True, text=True, env=ENV)
    if r.returncode != 0 or r.stdout:
        failures += 1
        print(f"FAIL fail-open on {bad!r}: exit {r.returncode}, stdout {r.stdout!r}")
print(f"{len(CASES) + 3} cases, {failures} failures")
sys.exit(1 if failures else 0)
