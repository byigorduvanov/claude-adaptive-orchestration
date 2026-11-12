#!/usr/bin/env python3
"""UserPromptSubmit: remind the model of the task contract on every owner prompt.

The owner should not have to write "done when" or reproduce-first into prompts:
the model derives them, and asks at once only for what it cannot find itself.
The hook also fires on background-agent reports and app events: those get nothing.

Past CONTEXT_LIMIT tokens of context it also tells the model to hand the work off to a new
session: every request re-reads the whole conversation, so long sessions are where the cost is.
"""
import json
import os
import re
import sys

CONTEXT_LIMIT = int(os.environ.get("TASK_CONTRACT_CONTEXT_LIMIT", "150000"))
USAGE = re.compile(r'"input_tokens":(\d+),"cache_creation_input_tokens":(\d+),"cache_read_input_tokens":(\d+)')

CONTRACT = """Task contract (ignore for a plain question or conversation):
1. Done when: derive the proof yourself and state it in your first line (a test that fails now and passes after, a command and its output, a log line, a trade id). Quote that proof in your final message; if you did not get it, say "not verified".
2. Bug or incident: reproduce or prove the cause with a log line or trade first, then a failing test, then the fix. Name the token, time and trade id you found.
3. Port from another exchange or service: read the sibling first, copy without new logic, list the differences.
4. Missing facts: first look in code, logs, memory and git. If the result still depends on something only the owner knows (expected behaviour, which account, money, irreversible steps), ask at once with one AskUserQuestion before doing the work. If nothing is missing, do not ask.
5. Money bug: keep the failing test in the repo. If the logic depends on price scale, use real numbers from the incident (price, tick, mark), not round ones.
6. Big or vague task: interview the owner with AskUserQuestion, write SPEC.md, and build it in a fresh session.
7. After two failed fixes in a row, stop and report what is known and a clean prompt for a new session instead of a third try."""

SYSTEM_PREFIXES = ("<task-notification", "<side-sessions-event", "<ci-monitor-event", "[Artifact comment", "<local-command-stdout")


def context_tokens(path):
    """Context size of the main session's latest request, read from the tail of its transcript."""
    try:
        with open(path, "rb") as f:
            f.seek(0, os.SEEK_END)
            f.seek(max(0, f.tell() - 600_000))
            tail = f.read().decode("utf-8", "ignore")
    except (OSError, TypeError):
        return 0
    for line in reversed(tail.splitlines()):
        if '"isSidechain":true' in line:
            continue
        m = USAGE.search(line)
        if m:
            return sum(int(x) for x in m.groups())
    return 0


def main():
    try:
        data = json.load(sys.stdin)
        prompt = data.get("prompt") or ""
    except (ValueError, AttributeError):
        return
    head = prompt.lstrip()
    if head.startswith(SYSTEM_PREFIXES) or "[SYSTEM NOTIFICATION" in head[:200]:
        return
    print(CONTRACT)
    used = context_tokens(data.get("transcript_path"))
    if used >= CONTEXT_LIMIT:
        print(
            f"\nContext is {used // 1000}k tokens, over the owner's {CONTEXT_LIMIT // 1000}k limit. Do what this message asks, "
            "then end your reply with a section that tells the owner to start a new session and gives a ready-to-paste "
            "prompt for it: the goal, what is done and proven, what is left, the files and commands, what proves done. "
            "Skip the section only if the owner already said to keep going here."
        )


if __name__ == "__main__":
    main()
