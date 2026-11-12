#!/usr/bin/env python3
"""Measure what a Claude Code session loads before the first message.

Usage:
  measure.py <transcript.jsonl> [--compare <older.jsonl>]
  measure.py --find "<unique text from the probe prompt>" [--project DIR]

Reads the FIRST main-chain assistant `usage` (input + cache_creation + cache_read)
and the first `api-request-shape` / `api-request` / `api-request-blob` records, then
splits the request by component in characters. Token split per component is
proportional to characters (the total itself is exact).
"""
import argparse, glob, json, os, re, sys

SECTIONS = [
    ("claude-mem start block", r"^SessionStart hook additional context"),
    ("environment", r"^# Environment"),
    ("deferred tool names", r"^The following deferred tools"),
    ("agent types", r"^Available agent types"),
    ("MCP instructions", r"^# MCP Server Instructions"),
    ("skill listing", r"^The following skills are available"),
    ("bypass-mode note", r"^While bypass permissions mode"),
    ("UserPromptSubmit hook", r"^UserPromptSubmit hook"),
    ("CLAUDE.md (global)", r"^Contents of .*/\.claude/CLAUDE\.md"),
    ("memory index", r"^Contents of .*/memory/MEMORY\.md"),
    ("project CLAUDE.md", r"^Contents of (?!.*/\.claude/CLAUDE\.md)(?!.*MEMORY\.md).*CLAUDE\.md"),
]


def load(path):
    rows = []
    for line in open(path, errors="ignore"):
        try:
            rows.append(json.loads(line))
        except Exception:
            pass
    return rows


def first_request(rows):
    usage = next((r for r in rows if r.get("type") == "assistant" and not r.get("isSidechain")), None)
    shape = next((r["shape"] for r in rows if r.get("type") == "api-request-shape"), None)
    req = next((r for r in rows if r.get("type") == "api-request"), None)
    blobs = {r["hash"]: r["message"] for r in rows if r.get("type") == "api-request-blob"}
    if not (usage and shape and req):
        sys.exit("transcript has no usage/api-request-shape/api-request records (old CLI, or no request yet)")
    texts = []
    for h in req.get("tail", []):
        for c in blobs.get(h, {}).get("content", []):
            if isinstance(c, dict) and c.get("text"):
                texts.append(c["text"])
    return usage, shape, texts


def split_sections(texts):
    out = {}
    for t in texts:
        marks = sorted({m.start(): name for name, pat in SECTIONS for m in re.finditer(pat, t, re.M)}.items())
        starts = [0] + [p for p, _ in marks] + [len(t)]
        names = ["other"] + [n for _, n in marks]
        for name, a, b in zip(names, starts, starts[1:]):
            out[name] = out.get(name, 0) + (b - a)
    return out


def skill_entries(texts):
    for t in texts:
        i = t.find("The following skills are available")
        if i < 0:
            continue
        s = t[i:]
        for stop in ("\n\nWhile bypass", "\n\nUserPromptSubmit hook"):
            j = s.find(stop)
            if j > 0:
                s = s[:j]
        ents = {}
        for e in re.split(r"\n- ", s)[1:]:
            name = e.split(":", 2)
            name = ":".join(name[:2]) if e.startswith(("anthropic-skills:", "claude-mem:")) else name[0]
            ents[name.strip()] = len(e)
        return ents
    return {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("transcript", nargs="?")
    ap.add_argument("--find")
    ap.add_argument("--project", default=os.path.expanduser("~/.claude/projects/") + os.getcwd().replace("/", "-").replace(".", "-"),
                    help="transcript dir (default: the one for the current directory)")
    ap.add_argument("--compare")
    a = ap.parse_args()
    path = a.transcript
    if a.find:
        files = sorted(glob.glob(os.path.join(a.project, "*.jsonl")), key=os.path.getmtime, reverse=True)[:30]
        hits = [f for f in files if a.find in open(f, errors="ignore").read()]
        if not hits:
            sys.exit("no transcript contains that text")
        # the probe's own transcript is the newest hit that is NOT the parent's (parent also quotes it)
        hits.sort(key=lambda f: os.path.getsize(f))
        path = hits[0]
    usage, shape, texts = first_request(load(path))
    u = usage["message"]["usage"]
    total = u.get("input_tokens", 0) + u.get("cache_creation_input_tokens", 0) + u.get("cache_read_input_tokens", 0)
    L = lambda x: len(x if isinstance(x, str) else json.dumps(x, ensure_ascii=False))
    tools_c = sum(L(t) for t in shape["tools"])
    sys_c = sum(L(b.get("text", "")) for b in shape["system"])
    secs = split_sections(texts)
    all_c = tools_c + sys_c + sum(secs.values())
    tok = lambda c: total * c / all_c / 1000
    print(f"transcript {os.path.basename(path)}  version {usage.get('version')}  at {usage.get('timestamp')}")
    print(f"FIRST REQUEST {total:,} tokens  (input {u.get('input_tokens')} + cache_creation "
          f"{u.get('cache_creation_input_tokens'):,} + cache_read {u.get('cache_read_input_tokens'):,})")
    print(f"chars/token here {all_c / total:.2f}\n")
    rows = [(f"tool schemas ({len(shape['tools'])})", tools_c), ("system prompt", sys_c)] + sorted(secs.items(), key=lambda kv: -kv[1])
    for name, c in rows:
        print(f"  {tok(c):5.1f}k tok  {c:7,} ch  {name}")
    print("\n  largest tools:")
    for t in sorted(shape["tools"], key=L, reverse=True)[:8]:
        print(f"    {L(t):6,} ch  {t['name']}")
    ents = skill_entries(texts)
    if ents:
        print(f"\n  skills listed {len(ents)}, name-only {sum(v < 60 for v in ents.values())}, longest entry {max(ents.values())} ch")
    if a.compare:
        o_usage, o_shape, o_texts = first_request(load(a.compare))
        ou = o_usage["message"]["usage"]
        ot = ou.get("input_tokens", 0) + ou.get("cache_creation_input_tokens", 0) + ou.get("cache_read_input_tokens", 0)
        print(f"\nvs {os.path.basename(a.compare)}: {ot:,} -> {total:,} ({total - ot:+,})")
        on, nn = {t["name"] for t in o_shape["tools"]}, {t["name"] for t in shape["tools"]}
        print(f"  tools removed {sorted(on - nn)}  added {sorted(nn - on)}")
        oe = skill_entries(o_texts)
        moved = sorted(((ents.get(k, 0) - oe.get(k, 0), k) for k in set(oe) | set(ents)), key=lambda x: x[0])
        print("  skill entries that changed most:", [(k, d) for d, k in moved if abs(d) > 200][:12])


if __name__ == "__main__":
    main()
