#!/usr/bin/env python3
"""Runs skills/setup-self-improve/scripts/collect.py on a fake HOME. Usage: python3 tests/test_collect.py"""
import json
import os
import subprocess
import sys
import tempfile
import time

SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "skills", "setup-self-improve", "scripts", "collect.py")
failures = 0


def check(ok, what):
    global failures
    if not ok:
        failures += 1
        print("FAIL", what)


home = tempfile.mkdtemp()
now = time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime())
proj = os.path.join(home, ".claude", "projects", "-Users-me-work-app")
os.makedirs(os.path.join(proj, "s1", "subagents"))
lines = [
    {"type": "user", "isSidechain": False, "timestamp": now, "cwd": "/Users/me/work/app",
     "message": {"role": "user", "content": "<system-reminder>ctx</system-reminder>ні, не так, я ж казав без gate"}},
    {"type": "assistant", "isSidechain": False, "timestamp": now, "message": {"content": [
        {"type": "tool_use", "id": "t1", "name": "Skill", "input": {"skill": "used-skill"}},
        {"type": "tool_use", "id": "t2", "name": "AskUserQuestion", "input": {"questions": [{"question": "Which account?"}]}},
        {"type": "text", "text": "Done, proof below."}]}},
    {"type": "user", "isSidechain": False, "timestamp": now, "message": {"content": [
        {"type": "tool_result", "tool_use_id": "t2", "content": "User answered: acc-2"}]}},
    {"type": "user", "isSidechain": False, "timestamp": now, "message": {"content": "<task-notification>x</task-notification>"}},
    {"type": "custom-title", "customTitle": "Fix the gate"},
    "not json at all",
]
with open(os.path.join(proj, "s1.jsonl"), "w") as f:
    for x in lines:
        f.write((json.dumps(x) if isinstance(x, dict) else x) + "\n")
with open(os.path.join(proj, "s1", "subagents", "a.jsonl"), "w") as f:
    f.write(json.dumps({"isSidechain": True, "timestamp": now, "message": {"content": [
        {"type": "tool_use", "name": "Bash", "input": {"command": "cat ~/.claude/skills/sub-skill/SKILL.md"}}]}}) + "\n")
# an observer transcript must be ignored
obs = os.path.join(home, ".claude", "projects", "-Users-me--claude-mem-observer-sessions")
os.makedirs(obs)
open(os.path.join(obs, "o.jsonl"), "w").write(json.dumps({"type": "user", "timestamp": now, "message": {"content": "observer prompt"}}) + "\n")
for name, age_days in (("used-skill", 90), ("sub-skill", 90), ("dead-skill", 90), ("new-skill", 0)):
    d = os.path.join(home, ".claude", "skills", name)
    os.makedirs(d)
    p = os.path.join(d, "SKILL.md")
    open(p, "w").write(f"---\nname: {name}\ndescription: x\n---\n")
    t = time.time() - age_days * 86400
    os.utime(p, (t, t))

out = os.path.join(home, "out")
r = subprocess.run([sys.executable, SCRIPT, "--days", "7", "--out", out], capture_output=True, text=True, env=dict(os.environ, HOME=home))
check(r.returncode == 0, f"exit {r.returncode} {r.stderr[-300:]}")
summary = json.load(open(os.path.join(out, "summary.json")))
check(summary["sessions"] == 1, f"sessions {summary['sessions']} (observer must be skipped)")
check(summary["unused"] == ["dead-skill"], f"unused {summary['unused']} (used, subagent-used and new skills are not unused)")
dig = open(os.path.join(out, "digests", "s1.md")).read()
check("я ж казав без gate" in dig and "system-reminder" not in dig, "owner prompt kept, reminder stripped")
check("task-notification" not in dig, "app events are not owner prompts")
check("Which account?" in dig and "acc-2" in dig, "AskUserQuestion Q/A in digest")
check("Skills used: used-skill" in dig and "Done, proof below." in dig, "skills and last reply in digest")
check(open(os.path.join(out, "batches.txt")).read().count("batch ") == 1, "one batch")
print(f"collect: 7 checks, {failures} failed")
sys.exit(1 if failures else 0)
