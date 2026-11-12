#!/usr/bin/env python3
"""Cheap signals for the weekly `setup-self-improve` run. No model call, no network, exits 0 always.

Wired twice in ~/.claude/settings.json:
- PreToolUse, matcher "Skill": appends {date, skill, cwd, session_id} to skill-usage.jsonl
  (which skills are used; the weekly run flags ones unused for 30+ days).
- SessionEnd and Stop: appends {date, cwd, transcript_path, session_id, reason} to sessions.jsonl
  (the weekly run's reading list). Desktop-app sessions often never end, so Stop is wired too;
  a session already in the file's tail is not written again, so a session is one line.

The event comes from the hook input's `hook_event_name`. Output dir: $SELF_IMPROVE_DIR or ~/.claude/self-improve.
"""
import datetime
import json
import os
import sys


def out_dir():
    return os.environ.get("SELF_IMPROVE_DIR") or os.path.expanduser("~/.claude/self-improve")


def seen(path, session_id):
    """True when session_id is already in the last 64 KB of path."""
    if not session_id:
        return False
    try:
        with open(path, "rb") as f:
            f.seek(0, os.SEEK_END)
            f.seek(max(0, f.tell() - 65536))
            return ('"session_id": %s' % json.dumps(session_id)).encode() in f.read()
    except OSError:
        return False


def record(data):
    event = data.get("hook_event_name")
    now = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
    if event == "PreToolUse":
        if data.get("tool_name") != "Skill":
            return None
        tool_input = data.get("tool_input") or {}
        skill = tool_input.get("skill") or tool_input.get("command") or tool_input.get("name")
        if not isinstance(skill, str) or not skill:
            return None
        return "skill-usage.jsonl", {"date": now, "skill": skill.lstrip("/"), "cwd": data.get("cwd"), "session_id": data.get("session_id")}
    if event in ("SessionEnd", "Stop"):
        path = data.get("transcript_path")
        if not isinstance(path, str) or not path:
            return None
        return "sessions.jsonl", {"date": now, "cwd": data.get("cwd"), "transcript_path": path,
                                  "session_id": data.get("session_id"), "reason": data.get("reason") or event}
    return None


def main():
    try:
        data = json.load(sys.stdin)
        if not isinstance(data, dict):
            return
        rec = record(data)
        if not rec:
            return
        name, row = rec
        d = out_dir()
        os.makedirs(d, exist_ok=True)
        path = os.path.join(d, name)
        if name == "sessions.jsonl" and seen(path, row.get("session_id")):
            return
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    except Exception:
        pass


if __name__ == "__main__":
    main()
    sys.exit(0)
