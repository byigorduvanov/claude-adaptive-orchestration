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


empty = transcript(("Bash", {"command": "ls"}), ("Agent", {"subagent_type": "general-purpose"}))
first = transcript(("Bash", {"command": "ls"}))
bash_read = transcript(("Bash", {"command": "ls ~/w/.plans/ && cat ~/w/.plans/old.md"}), ("Agent", {"subagent_type": "general-purpose"}))
read_only = transcript(("Read", {"file_path": "/w/.plans/old.md"}), ("Agent", {"subagent_type": "general-purpose"}))
written = transcript(("Write", {"file_path": "/w/.plans/2026-11-17-x.md", "content": "goal"}), ("Agent", {"subagent_type": "general-purpose"}))
via_bash = transcript(("Bash", {"command": "cat > ~/w/.plans/2026-11-17-x.md <<'EOF'\ngoal\nEOF"}), ("Agent", {"subagent_type": "general-purpose"}))

code, out = run("Agent", "general-purpose", first)
check(out == "", f"the first agent of a session is free ({out[:60]})")
code, out = run("Agent", "general-purpose", bash_read)
check('"deny"' in out, "ls/cat of .plans through Bash is not writing a plan")
code, out = run("Agent", "Explore", empty)
check(out == "", "Explore (read-only search) is exempt")
code, out = run("Agent", "general-purpose", empty)
check(code == 0 and '"deny"' in out and "Plan file first" in out, f"no plan file -> deny ({out[:80]})")
code, out = run("Agent", "general-purpose", read_only)
check('"deny"' in out, "reading an old plan file is not writing one")
code, out = run("Agent", "general-purpose", written)
check(out == "", f"plan file written -> allowed ({out[:80]})")
code, out = run("Agent", "general-purpose", via_bash)
check(out == "", "plan file written through Bash -> allowed")
for kind in ("money-reviewer", "reviewer", "verifier", "web-fetch"):
    code, out = run("Agent", kind, empty)
    check(out == "", f"{kind} is exempt")
code, out = run("Bash", "", empty)
check(out == "", "other tools are not touched")
code, out = run("Agent", "general-purpose", "/nonexistent/t.jsonl")
check(out == "", "missing transcript never blocks")
# Review 2026-11-17
explore_then = transcript(("Agent", {"subagent_type": "Explore"}))
code, out = run("Agent", "general-purpose", explore_then)
check(out == "", "an earlier exempt agent (Explore) does not count: the first worker is still free")
for cmd in ("mkdir -p .plans && cat > .plans/2026-11-17-x.md <<'E'\ngoal\nE", "cp /tmp/p.md ~/work/hft/.plans/x.md",
            "python3 -c \"open('/w/.plans/x.md','w').write('g')\""):
    t = transcript(("Bash", {"command": cmd}), ("Agent", {"subagent_type": "general-purpose"}))
    code, out = run("Agent", "general-purpose", t)
    check(out == "", f"plan written via Bash counts: {cmd[:40]}")
    os.remove(t)
code, out = run("Agent", "Plan", empty)
check(out == "", "Plan (read-only designer) is exempt")
# the current call is already in the transcript; the hook gets its tool_use_id and must not count itself
fd, cur = tempfile.mkstemp(suffix=".jsonl")
with os.fdopen(fd, "w") as f:
    f.write(json.dumps({"type": "assistant", "message": {"content": [{"type": "tool_use", "id": "me", "name": "Agent", "input": {"subagent_type": "general-purpose"}}]}}) + "\n")
r = subprocess.run([sys.executable, HOOK], input=json.dumps({"tool_name": "Agent", "tool_use_id": "me", "tool_input": {"subagent_type": "general-purpose"}, "transcript_path": cur}), capture_output=True, text=True)
check(r.stdout.strip() == "", "a lone agent does not count itself")
os.remove(cur); os.remove(explore_then)
for p in (empty, first, bash_read, read_only, written, via_bash):
    os.remove(p)
print(f"plan-gate: 20 checks, {failures} failed")
sys.exit(1 if failures else 0)
