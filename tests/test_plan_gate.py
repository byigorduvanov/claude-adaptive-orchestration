#!/usr/bin/env python3
"""plan-gate.py: worker agents are blocked until the session has written a .plans/ file."""
import json
import os
import subprocess
import sys
import tempfile

HOOK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "hooks", "plan-gate.py")
failures = 0


def run(tool, kind, transcript):
    inp = {"tool_name": tool, "tool_input": {"subagent_type": kind, "prompt": "x"}, "transcript_path": transcript}
    r = subprocess.run([sys.executable, HOOK], input=json.dumps(inp), capture_output=True, text=True)
    return r.returncode, r.stdout.strip()


def check(ok, what):
    global failures
    if not ok:
        failures += 1
        print("FAIL", what)


def transcript(*calls):
    fd, p = tempfile.mkstemp(suffix=".jsonl")
    with os.fdopen(fd, "w") as f:
        f.write(json.dumps({"type": "user", "message": {"content": "do the big task"}}) + "\n")
        for name, inp in calls:
            f.write(json.dumps({"type": "assistant", "message": {"content": [{"type": "tool_use", "id": "t", "name": name, "input": inp}]}}) + "\n")
    return p


empty = transcript(("Bash", {"command": "ls"}))
read_only = transcript(("Read", {"file_path": "/w/.plans/old.md"}))
written = transcript(("Write", {"file_path": "/w/.plans/2026-11-17-x.md", "content": "goal"}))
via_bash = transcript(("Bash", {"command": "cat > ~/w/.plans/2026-11-17-x.md <<'EOF'\ngoal\nEOF"}))

code, out = run("Agent", "general-purpose", empty)
check(code == 0 and '"deny"' in out and "Plan file first" in out, f"no plan file -> deny ({out[:80]})")
code, out = run("Agent", "general-purpose", read_only)
check('"deny"' in out, "reading an old plan file is not writing one")
code, out = run("Agent", "general-purpose", written)
check(out == "", f"plan file written -> allowed ({out[:80]})")
code, out = run("Agent", "Explore", via_bash)
check(out == "", "plan file written through Bash -> allowed")
for kind in ("money-reviewer", "reviewer", "verifier", "web-fetch"):
    code, out = run("Agent", kind, empty)
    check(out == "", f"{kind} is exempt")
code, out = run("Bash", "", empty)
check(out == "", "other tools are not touched")
code, out = run("Agent", "general-purpose", "/nonexistent/t.jsonl")
check(out == "", "missing transcript never blocks")
for p in (empty, read_only, written, via_bash):
    os.remove(p)
print(f"plan-gate: 11 checks, {failures} failed")
sys.exit(1 if failures else 0)
