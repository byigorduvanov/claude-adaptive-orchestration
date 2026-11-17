#!/usr/bin/env python3
"""PreToolUse on Agent: no worker agents before this session has written a plan file.

Owner 2026-11-17: when Claude starts agents, the work must live in a file the agents read and write
(`.plans/<date>-<slug>.md`, see CLAUDE.md Orchestration), not only in the conversation.
The session passes once any Write, Edit or Bash call in its transcript touched a path containing `/.plans/`.

Exempt: agents that only read or judge and must stay independent (reviewers, verifier, web-fetch, guides).
Exits 0 always; a block is a JSON `deny` with the reason, which Claude sees and acts on.
"""
import json
import sys

EXEMPT = {"money-reviewer", "critical-reviewer", "reviewer", "verifier", "web-fetch", "claude-code-guide", "statusline-setup"}
REASON = (
    "Plan file first (CLAUDE.md Orchestration): before starting worker agents, write `.plans/<YYYY-MM-DD>-<slug>.md` "
    "at the workspace top, outside any git repo (goal, what proves done, the owner's answers, steps todo/doing/done). "
    "Then give each agent that path and have it put long output in `.plans/<slug>/<agent>.md`, returning the path and <=25 lines. "
    "Then start the agent again."
)


def has_plan(path):
    try:
        f = open(path, encoding="utf-8", errors="ignore")
    except (OSError, TypeError):
        return True  # no transcript to read: never block on our own blind spot
    with f:
        for line in f:
            if "/.plans/" not in line or '"tool_use"' not in line:
                continue
            try:
                d = json.loads(line)
            except ValueError:
                continue
            for x in (d.get("message") or {}).get("content") or []:
                if isinstance(x, dict) and x.get("type") == "tool_use" and x.get("name") in ("Write", "Edit", "Bash", "MultiEdit"):
                    if "/.plans/" in json.dumps(x.get("input") or {}):
                        return True
    return False


def main():
    try:
        data = json.load(sys.stdin)
    except ValueError:
        return
    if data.get("tool_name") != "Agent":
        return
    kind = ((data.get("tool_input") or {}).get("subagent_type") or "general-purpose").split(":")[-1]
    if kind in EXEMPT or has_plan(data.get("transcript_path")):
        return
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": REASON}}))


if __name__ == "__main__":
    main()
