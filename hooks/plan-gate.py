#!/usr/bin/env python3
"""PreToolUse on Agent: no worker agents before this session has written a plan file.

Owner 2026-11-17: when Claude starts agents, the work must live in a file the agents read and write
(`.plans/<date>-<slug>.md`, see CLAUDE.md Orchestration), not only in the conversation.
A lone agent is free: the gate starts with the second Agent call of a session (several started in one message count
together), because one quick search does not need a file and two or more workers is the "big task" signal.
The session passes once a Write/Edit/MultiEdit targeted a `/.plans/…` path, or a Bash call redirected or tee'd into one.
Reading (`ls`, `cat`, Read) does not count.

Exempt: agents that only read or judge (Explore, scout, reviewers, verifier, web-fetch, guides).
Exits 0 always; a block is a JSON `deny` with the reason, which Claude sees and acts on.
"""
import json
import re
import sys

EXEMPT = {"Explore", "Plan", "scout", "money-reviewer", "critical-reviewer", "reviewer", "verifier", "web-fetch", "claude-code-guide", "statusline-setup"}
# A Bash write into a plan path: redirect, tee, cp/mv/install/touch target, or python open(..., 'w'); relative paths too.
PLANS = r"""(?:^|[\s"'=/(])\.plans/"""
BASH_WRITE = re.compile(r"""(?:>>?|\btee(?:\s+-a)?)\s*["']?[^\s"'|;&]*""" + PLANS[:-8] + r"""\.plans/"""
                        r"""|\b(?:cp|mv|install|touch)\b[^|;&]*""" + PLANS
                        + r"""|open\([^)]*\.plans/[^)]*['"][wa]""")
REASON = (
    "Plan file first (CLAUDE.md Orchestration): before starting worker agents, write `.plans/<YYYY-MM-DD>-<slug>.md` "
    "at the workspace top, outside any git repo (goal, what proves done, the owner's answers, steps todo/doing/done). "
    "Then give each agent that path and have it put long output in `.plans/<slug>/<agent>.md`, returning the path and <=25 lines. "
    "Then start the agent again."
)


def scan(path, current_id):
    """(plan file written?, number of other Agent calls) from the session transcript."""
    plan, agents = False, 0
    try:
        f = open(path, encoding="utf-8", errors="ignore")
    except (OSError, TypeError):
        return True, 0  # no transcript to read: never block on our own blind spot
    with f:
        for line in f:
            if '"tool_use"' not in line or (".plans/" not in line and '"Agent"' not in line):
                continue
            try:
                d = json.loads(line)
            except ValueError:
                continue
            for x in (d.get("message") or {}).get("content") or []:
                if not (isinstance(x, dict) and x.get("type") == "tool_use"):
                    continue
                name, inp = x.get("name"), x.get("input") or {}
                if name == "Agent" and x.get("id") != current_id:
                    agents += (str(inp.get("subagent_type") or "general-purpose").split(":")[-1] not in EXEMPT)
                elif name in ("Write", "Edit", "MultiEdit") and ".plans/" in str(inp.get("file_path", "")):
                    plan = True
                elif name == "Bash" and BASH_WRITE.search(str(inp.get("command", ""))):
                    plan = True
    return plan, agents


def main():
    try:
        data = json.load(sys.stdin)
    except ValueError:
        return
    if data.get("tool_name") != "Agent":
        return
    kind = ((data.get("tool_input") or {}).get("subagent_type") or "general-purpose").split(":")[-1]
    if kind in EXEMPT:
        return
    plan, others = scan(data.get("transcript_path"), data.get("tool_use_id"))
    if plan or others == 0:
        return
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": REASON}}))


if __name__ == "__main__":
    main()
