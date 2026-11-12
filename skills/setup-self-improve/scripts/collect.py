#!/usr/bin/env python3
"""Deterministic input for the weekly setup-self-improve run. Reads only; writes into --out.

    python3 collect.py --days 7 --out /tmp/self-improve-2026-11-16

Writes:
  sessions.md         one line per owner session of the window (newest first) with its digest path
  digests/<id>.md     compact digest: owner prompts, AskUserQuestion Q/A, skills used, assistant's last text per turn
  batches.txt         digest paths grouped into reader batches (~BATCH_CHARS each)
  skill-usage.md      every installed skill with its last use (hook log + all transcripts), unused 30+ days flagged
  summary.json        counts, for the report

Session sources: ~/.claude/self-improve/sessions.jsonl (hook) plus every transcript under ~/.claude/projects
modified in the window (the hook log is new, transcripts are the history). Scratch and observer transcripts are skipped;
subagent transcripts count for skill usage only. Usage of a skill = a Skill tool call, a /<skill> command, or a tool
call that reads `skills/<name>/`. Last use is only as old as the oldest kept transcript (see summary.json).
"""
import argparse
import datetime as dt
import glob
import json
import os
import re

HOME = os.path.expanduser("~")
PROJECTS = os.path.join(HOME, ".claude", "projects")
STATE = os.path.join(HOME, ".claude", "self-improve")
SKIP_DIRS = ("-private-tmp", "-claude-mem", "observer-sessions")
SKILL_ROOTS = [os.path.join(HOME, ".claude", "skills")] + sorted(
    set(glob.glob(os.path.join(HOME, "work", "*", ".claude", "skills")) + glob.glob(os.path.join(HOME, "work", "*", "*", ".claude", "skills"))))
SYSTEM_PREFIXES = ("<task-notification", "<side-sessions-event", "<ci-monitor-event", "[Artifact comment", "<local-command",
                   "[SYSTEM NOTIFICATION", "Caveat:", "<command-message", "[Request interrupted")
TAG = re.compile(r"<(system-reminder|antml:[a-z_]+)>.*?</\1>", re.S)
BATCH_CHARS = 60000
PROMPT_MAX = 1500
REPLY_MAX = 500


def text_of(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(x.get("text", "") for x in content if isinstance(x, dict) and x.get("type") == "text")
    return ""


def owner_prompt(d):
    """Text the owner typed, or None for tool results, meta lines and app events."""
    if d.get("type") != "user" or d.get("isSidechain") or d.get("isMeta"):
        return None
    content = (d.get("message") or {}).get("content")
    if isinstance(content, list) and any(isinstance(x, dict) and x.get("type") == "tool_result" for x in content):
        return None
    t = TAG.sub("", text_of(content)).strip()
    if not t or t.lstrip().startswith(SYSTEM_PREFIXES):
        return None
    return t


def skills_in(d):
    """Skill names a transcript line shows in use."""
    out = []
    content = (d.get("message") or {}).get("content")
    if isinstance(content, list):
        for x in content:
            if not isinstance(x, dict) or x.get("type") != "tool_use":
                continue
            inp = x.get("input") or {}
            if x.get("name") == "Skill" and isinstance(inp, dict) and isinstance(inp.get("skill"), str):
                out.append(inp["skill"].split(":")[-1].lstrip("/"))
            else:
                out += re.findall(r"skills/([a-z0-9][a-z0-9-]+)/", json.dumps(inp))
    t = text_of(content) if d.get("type") == "user" else ""
    out += re.findall(r"<command-name>/?([a-z0-9:-]+)</command-name>", t)
    return [s.split(":")[-1] for s in out]


def parse(path):
    """One pass over a transcript: digest pieces and skill uses with dates."""
    prompts, turns, asks, uses, title, cwd, first, last = [], [], [], [], None, None, None, None
    pending_ask = {}
    last_reply = None
    try:
        f = open(path, encoding="utf-8", errors="ignore")
    except OSError:
        return None
    with f:
        for line in f:
            try:
                d = json.loads(line)
            except ValueError:
                continue
            if not isinstance(d, dict):
                continue
            ts = d.get("timestamp")
            if d.get("isSidechain"):
                uses += [(s, (ts or "")[:10]) for s in skills_in(d)]
                continue
            if ts:
                first = first or ts
                last = ts
            cwd = cwd or d.get("cwd")
            if d.get("type") == "custom-title":
                title = d.get("customTitle")
            for s in skills_in(d):
                uses.append((s, (ts or "")[:10]))
            p = owner_prompt(d)
            if p is not None:
                if last_reply:
                    turns.append(last_reply)
                    last_reply = None
                prompts.append(p)
                continue
            msg = d.get("message") or {}
            content = msg.get("content")
            if d.get("type") == "assistant" and isinstance(content, list):
                for x in content:
                    if not isinstance(x, dict):
                        continue
                    if x.get("type") == "text" and x.get("text", "").strip():
                        last_reply = x["text"].strip()
                    if x.get("type") == "tool_use" and x.get("name") == "AskUserQuestion":
                        qs = (x.get("input") or {}).get("questions") or []
                        pending_ask[x.get("id")] = [q.get("question", "") for q in qs if isinstance(q, dict)]
            if d.get("type") == "user" and isinstance(content, list):
                for x in content:
                    if isinstance(x, dict) and x.get("type") == "tool_result" and x.get("tool_use_id") in pending_ask:
                        asks.append((pending_ask.pop(x["tool_use_id"]), TAG.sub("", text_of(x.get("content")))[:600]))
    if last_reply:
        turns.append(last_reply)
    return {"prompts": prompts, "turns": turns, "asks": asks, "uses": uses, "title": title, "cwd": cwd, "first": first, "last": last}


def cut(s, n):
    s = s.strip()
    return s if len(s) <= n else s[:n] + f" …[+{len(s) - n} chars]"


def digest(sid, path, p):
    lines = [f"# {p['title'] or sid}", f"cwd: {p['cwd']}  ·  {p['first']} → {p['last']}  ·  transcript: {path}", ""]
    used = sorted({s for s, _ in p["uses"]})
    if used:
        lines.append("Skills used: " + ", ".join(used))
    for qs, ans in p["asks"]:
        lines.append(f"AskUserQuestion: {' | '.join(qs)}\n  → {cut(ans, 600)}")
    lines.append("")
    for i, pr in enumerate(p["prompts"]):
        lines.append(f"## Owner {i + 1}\n{cut(pr, PROMPT_MAX)}")
        if i < len(p["turns"]):
            lines.append(f"### Claude's last text in that turn\n{cut(p['turns'][i], REPLY_MAX)}")
    return "\n".join(lines) + "\n"


def installed_skills():
    out = {}
    for root in SKILL_ROOTS:
        for md in glob.glob(os.path.join(root, "*", "SKILL.md")):
            name = os.path.basename(os.path.dirname(md))
            out.setdefault(name, []).append(md)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--out", required=True)
    ap.add_argument("--unused-days", type=int, default=30)
    a = ap.parse_args()
    now = dt.datetime.now()
    since = now - dt.timedelta(days=a.days)
    os.makedirs(os.path.join(a.out, "digests"), exist_ok=True)

    hook_paths = set()
    try:
        for line in open(os.path.join(STATE, "sessions.jsonl"), encoding="utf-8"):
            try:
                hook_paths.add(json.loads(line)["transcript_path"])
            except (ValueError, KeyError, TypeError):
                pass
    except OSError:
        pass

    all_paths = [p for p in glob.glob(os.path.join(PROJECTS, "*", "*.jsonl")) if not any(s in p.split(os.sep)[-2] for s in SKIP_DIRS)]
    sub_paths = glob.glob(os.path.join(PROJECTS, "*", "*", "subagents", "*.jsonl"))
    oldest = min((os.path.getmtime(p) for p in all_paths), default=now.timestamp())
    last_use = {}
    rows = []
    window = {p for p in all_paths if os.path.getmtime(p) >= since.timestamp()} | {p for p in hook_paths if os.path.exists(p) and os.path.getmtime(p) >= since.timestamp()}
    for path in all_paths:
        p = parse(path)
        if not p:
            continue
        for s, day in p["uses"]:
            day = day or dt.datetime.fromtimestamp(os.path.getmtime(path)).strftime("%Y-%m-%d")
            last_use[s] = max(last_use.get(s, ""), day)
        if path in window and p["prompts"] and (p["last"] or "9") >= since.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M"):
            sid = os.path.basename(path)[:-6]
            dpath = os.path.join(a.out, "digests", sid + ".md")
            body = digest(sid, path, p)
            open(dpath, "w", encoding="utf-8").write(body)
            rows.append((p["last"] or "", sid, p["cwd"], p["title"], len(p["prompts"]), len(body), dpath))
    for path in sub_paths:
        p = parse(path)
        for s, day in (p or {}).get("uses", []):
            day = day or dt.datetime.fromtimestamp(os.path.getmtime(path)).strftime("%Y-%m-%d")
            last_use[s] = max(last_use.get(s, ""), day)
    try:
        for line in open(os.path.join(STATE, "skill-usage.jsonl"), encoding="utf-8"):
            try:
                r = json.loads(line)
                s = r["skill"].split(":")[-1]
                last_use[s] = max(last_use.get(s, ""), r["date"][:10])
            except (ValueError, KeyError, TypeError, AttributeError):
                pass
    except OSError:
        pass

    rows.sort(reverse=True)
    with open(os.path.join(a.out, "sessions.md"), "w", encoding="utf-8") as f:
        f.write(f"# Owner sessions {since:%Y-%m-%d} → {now:%Y-%m-%d}: {len(rows)}\n\n")
        for last, sid, cwd, title, n, size, dpath in rows:
            f.write(f"- {last[:16]}  {cwd}  «{title or '-'}»  prompts={n}  {size // 1000}k  {dpath}\n")
    batches, cur, size = [], [], 0
    for r in sorted(rows, key=lambda r: (r[2] or "", r[0])):
        if cur and size + r[5] > BATCH_CHARS:
            batches.append(cur); cur, size = [], 0
        cur.append(r[6]); size += r[5]
    if cur:
        batches.append(cur)
    with open(os.path.join(a.out, "batches.txt"), "w") as f:
        for i, b in enumerate(batches, 1):
            f.write(f"batch {i}: " + " ".join(b) + "\n")

    skills = installed_skills()
    cutoff = (now - dt.timedelta(days=a.unused_days)).strftime("%Y-%m-%d")
    unused = []
    with open(os.path.join(a.out, "skill-usage.md"), "w", encoding="utf-8") as f:
        f.write(f"# Skill usage (history from {dt.datetime.fromtimestamp(oldest):%Y-%m-%d}; unused = no use since {cutoff})\n\n")
        for name in sorted(skills):
            created = min(dt.datetime.fromtimestamp(os.path.getmtime(m)) for m in skills[name]).strftime("%Y-%m-%d")
            lu = last_use.get(name, "")
            flag = ""
            if (not lu or lu < cutoff) and created < cutoff:
                flag = "  UNUSED"
                unused.append(name)
            f.write(f"- {name}: last use {lu or 'never seen'}; SKILL.md modified {created}; {', '.join(skills[name])}{flag}\n")
    summary = {"window_days": a.days, "sessions": len(rows), "batches": len(batches), "skills": len(skills), "unused": unused,
               "history_from": dt.datetime.fromtimestamp(oldest).strftime("%Y-%m-%d"), "hook_sessions_logged": len(hook_paths)}
    json.dump(summary, open(os.path.join(a.out, "summary.json"), "w"), indent=1)
    print(f"sessions={len(rows)} batches={len(batches)} skills={len(skills)} unused={len(unused)} history_from={summary['history_from']} -> {a.out}")


if __name__ == "__main__":
    main()
