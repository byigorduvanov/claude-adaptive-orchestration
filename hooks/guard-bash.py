#!/usr/bin/env python3
"""PreToolUse(Bash) guard for the few rules with no exceptions.

Blocks a force push until the command carries OWNER_APPROVED_FORCE_PUSH=1, staging
everything inside shared checkouts, and connecting to listed hosts. It uses "deny":
an "ask" decision did not stop the command under bypassPermissions when tested.
It guards against accidents, not a determined agent, and fails open on any error.

Config: guard-bash.json next to this file, or the path in GUARD_BASH_CONFIG:
  {"shared_checkouts": ["~/work/shared"], "blocked_hosts": ["203.0.113.7"]}
"""
import json
import os
import re
import sys

APPROVAL = "OWNER_APPROVED_FORCE_PUSH=1"


def load_config():
    path = os.environ.get("GUARD_BASH_CONFIG") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "guard-bash.json")
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


CD = re.compile(r"""(?:^|&&|\|\||;|\n)\s*cd\s+("[^"]*"|'[^']*'|[^\s;&|]+)""")


def next_cwd(cwd, target):
    """Where a cd leads. None when the target cannot be known from the text ($VAR, cd -)."""
    target = target.strip("\"'")
    if cwd is None or "$" in target or "`" in target or target == "-":
        return None
    return os.path.join(cwd, os.path.expanduser(target))


def decide(cmd, cwd, config):
    # Quoted text (commit messages, echoes) is not a command, but a quoted lone flag ("--force") still is.
    bare = re.sub(r"""(?<![^\s])["']([-+][^"'\s]*)["'](?![^\s])""", r"\1", cmd)
    bare = re.sub(r"'[^']*'|\"[^\"]*\"", "''", bare)
    shared = [os.path.realpath(os.path.expanduser(p)) for p in config.get("shared_checkouts", [])]
    cds = iter(CD.findall(cmd))
    for part in re.split(r"&&|\|\||;|\||\n", bare):
        words = part.split()
        if words[:1] == ["cd"]:
            cwd = next_cwd(cwd, next(cds, "$unknown"))
            continue
        if "git" not in words:
            continue
        before, rest = words[: words.index("git")], words[words.index("git") + 1 :]
        if "push" in rest:
            args = rest[rest.index("push") + 1 :]
            forced = any(a == "--force" or re.fullmatch(r"-[A-Za-z]*f[A-Za-z]*", a) or a.startswith("--force-with-lease") or (a.startswith("+") and len(a) > 1) for a in args)
            if forced and APPROVAL not in before:
                return "deny", f"Force push: ask the owner first and wait for a yes. After that yes, prefix the command with {APPROVAL}."
        if "add" in rest:
            args = rest[rest.index("add") + 1 :]
            where = next((rest[i + 1] for i, a in enumerate(rest[:-1]) if a == "-C"), cwd)
            inside = False
            if where is not None and (cwd is not None or os.path.isabs(os.path.expanduser(where))):
                where = os.path.realpath(os.path.join(cwd or "/", os.path.expanduser(where)))
                inside = any(where == p or where.startswith(p + os.sep) for p in shared)
            if inside and any(a in ("-A", "--all", ".", "-u", "--update") for a in args):
                return "deny", "Other sessions share this checkout: stage named paths only, never everything."
    for host in config.get("blocked_hosts", []):
        if re.search(r"\b(ssh|scp|sftp|rsync)\b.*(?<![\w.-])" + re.escape(host) + r"(?![\w.-])", bare):
            return "deny", f"{host} is on the blocked host list: never connect to it."
    return None, None


def main():
    data = json.load(sys.stdin)
    cmd = (data.get("tool_input") or {}).get("command", "")
    decision, reason = decide(cmd, data.get("cwd") or os.getcwd(), load_config())
    if decision:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": decision, "permissionDecisionReason": reason}}))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
