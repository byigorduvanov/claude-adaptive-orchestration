#!/usr/bin/env python3
"""Cost and time of one arm: wall time, tokens (deduped by message id), subagents.

Usage: AB=<workdir> [CONFIG_ROOT=<dir holding the arm config dirs, default $AB/arms>] python3 score.py <task> <arm> [<arm> ...]
Wall time is cut at the last write to REPORT.md when there is one. The end of the transcript is not the end of the
work: a session that keeps talking afterwards once turned a 26-minute run into an "81-minute" one.
Weighted tokens use input-equivalents: cache read x0.1, cache write x1.25, output x5.
"""
import glob, json, os, sys
from collections import Counter, defaultdict
from datetime import datetime

AB = os.environ["AB"]
ROOT = os.environ.get("CONFIG_ROOT", f"{AB}/arms")
ts = lambda s: datetime.fromisoformat(s.replace("Z", "+00:00"))


def scan(path, tok, seen, report_at=None):
    first = last = None
    for line in open(path, errors="ignore"):
        try:
            d = json.loads(line)
        except ValueError:
            continue
        t = d.get("timestamp")
        if t:
            first, last = first or t, t
        if d.get("type") != "assistant":
            continue
        m = d["message"]
        for b in m.get("content") or []:
            if report_at is not None and isinstance(b, dict) and b.get("type") == "tool_use" and b.get("name") in ("Write", "Edit") and "REPORT.md" in json.dumps(b.get("input", {})):
                report_at.append(t)
        if m.get("id") and m["id"] not in seen:
            seen.add(m["id"])
            for k, v in (m.get("usage") or {}).items():
                if isinstance(v, int):
                    tok[k] += v
    return first, last


task, arms = sys.argv[1], sys.argv[2:]
for arm in arms:
    sid = open(f"{AB}/{task}/{arm}/session-id").read().strip()
    hits = glob.glob(f"{ROOT}/{arm}/projects/*/{sid}.jsonl")
    if not hits:
        print(f"{task}/{arm}: no transcript for {sid}")
        continue
    main = hits[0]
    tok, seen, report = defaultdict(int), set(), []
    first, last = scan(main, tok, seen, report)
    agents = Counter()
    for sub in glob.glob(main[:-6] + "/subagents/*.jsonl"):
        f, l = scan(sub, tok, seen)
        meta = sub[:-6] + ".meta.json"
        agents[json.load(open(meta)).get("agentType", "?") if os.path.exists(meta) else "?"] += 1
        if not report and l and l > last:
            last = l
    end = report[-1] if report else last
    w = tok["cache_read_input_tokens"] * 0.1 + tok["cache_creation_input_tokens"] * 1.25 + tok["output_tokens"] * 5 + tok["input_tokens"]
    print(f"{task}/{arm}: wall {(ts(end) - ts(first)).total_seconds() / 60:.1f} min ({'to report' if report else 'to transcript end'}), transcript {(ts(last) - ts(first)).total_seconds() / 60:.1f} min, weighted {w / 1e6:.2f}M, agents {dict(agents)}")
