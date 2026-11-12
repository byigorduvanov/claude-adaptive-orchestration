#!/usr/bin/env python3
"""Deterministic lint for a Claude Code auto-memory directory.

Finds candidates for stale memory; it does not judge meaning. A model (or a
person) reads the findings and decides. No network, no writes to the notes.

Usage:
  memory_lint.py <memory_dir> [--json out.json] [--today YYYY-MM-DD] [--max-lines N]

Reads two optional files from <memory_dir>:
  .memory-lint.json           project config (superseded identifiers, eras)
  .memory-lint-baseline.json  findings already reviewed and accepted

Exit code: 0 = no errors, 1 = errors found, 2 = bad usage.
"""
import argparse
import datetime as dt
import json
import os
import re
import sys

INDEX = "MEMORY.md"
INDEX_MAX_LINES = 200          # Claude Code loads the first 200 lines ...
INDEX_MAX_BYTES = 25_000       # ... or 25 KB of MEMORY.md
HISTORY_HEADING = re.compile(r"history|not current|superseded|pre-move|obsolete|archive", re.I)
INLINE_HISTORY = re.compile(r"superseded|pre-move|obsolete|retired|revoked|no longer|history|\bold\b|\bwas\b|never", re.I)
BANNER = re.compile(r"Context note \(added \d{4}-\d{2}-\d{2}\)")
REL_HARD = re.compile(r"\b(yesterday|tomorrow|next week|last week|next month|last month)\b|завтра|вчора|позавчора|вчера", re.I)
REL_SOFT = re.compile(r"\b(today|tonight|this week)\b|сьогодні|сегодня", re.I)
RECHECK = re.compile(r"(?:re-?check|revisit|re-?test|review again)\s+in\s+(\d+)(?:\s*[–-]\s*(\d+))?\s*(day|week|month)s?", re.I)
EXPIRES = re.compile(r"expir\w*\s+(?:on\s+|at\s+)?(\d{4}-\d{2}-\d{2})", re.I)
DATE = re.compile(r"(20\d{2})-(\d{2})-(\d{2})")
LINK = re.compile(r"\]\(([^)#]+\.md)\)")


def parse_date(s):
    m = DATE.search(s or "")
    if not m:
        return None
    try:
        return dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None


def split_frontmatter(text):
    if not text.startswith("---\n"):
        return None, text, 0
    end = text.find("\n---\n", 4)
    if end < 0:
        return None, text, 0
    fm = text[4:end]
    body = text[end + 5:]
    return fm, body, fm.count("\n") + 3


def note_date(name, fm, path):
    """Best guess of when the note's facts were true: name, frontmatter, mtime."""
    d = parse_date(name)
    if d:
        return d
    if fm:
        m = re.search(r"modified:\s*(\S+)", fm)
        if m and parse_date(m.group(1)):
            return parse_date(m.group(1))
    return dt.date.fromtimestamp(os.path.getmtime(path))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("memory_dir")
    ap.add_argument("--json")
    ap.add_argument("--today")
    ap.add_argument("--max-lines", type=int, default=40)
    a = ap.parse_args()
    root = a.memory_dir
    if not os.path.isfile(os.path.join(root, INDEX)):
        print(f"no {INDEX} in {root}", file=sys.stderr)
        return 2
    today = parse_date(a.today) if a.today else dt.date.today()

    def load(name, default):
        p = os.path.join(root, name)
        if not os.path.isfile(p):
            return default
        with open(p) as f:
            return json.load(f)

    cfg = load(".memory-lint.json", {})
    baseline = set(load(".memory-lint-baseline.json", {}).get("accepted", {}))
    findings = []

    def add(sev, check, file, line, msg, key=""):
        k = f"{check}|{file}|{key}"
        if k in baseline:
            return
        findings.append({"severity": sev, "check": check, "file": file, "line": line, "msg": msg, "key": k})

    files = sorted(f for f in os.listdir(root) if f.endswith(".md"))
    texts = {f: open(os.path.join(root, f), encoding="utf-8", errors="replace").read() for f in files}

    # 1. index: size, broken links, notes nothing links to
    idx = texts[INDEX]
    n_lines, n_bytes = idx.count("\n") + 1, len(idx.encode())
    if n_lines > INDEX_MAX_LINES or n_bytes > INDEX_MAX_BYTES:
        add("error", "index-size", INDEX, 0, f"{n_lines} lines / {n_bytes} B: past {INDEX_MAX_LINES} lines or {INDEX_MAX_BYTES} B the rest is not loaded")
    elif n_lines > 0.8 * INDEX_MAX_LINES or n_bytes > 0.8 * INDEX_MAX_BYTES:
        add("info", "index-size", INDEX, 0, f"{n_lines} lines / {n_bytes} B: over 80% of the load limit")
    indexes = [INDEX] + [f for f in files if f.startswith("index-")]
    linked = set()
    for ix in indexes:
        for i, line in enumerate(texts[ix].split("\n"), 1):
            for target in LINK.findall(line):
                linked.add(target)
                if target not in texts:
                    add("error", "broken-link", ix, i, f"links to missing {target}", target)
    for f in files:
        if f not in indexes and f not in linked:
            add("error", "unindexed", f, 0, "no index links to this note, so it is never recalled")

    superseded = [(re.compile(s["pattern"]), s) for s in cfg.get("superseded", [])]
    eras = cfg.get("eras", [])

    for f in files:
        text = texts[f]
        fm, body, offset = split_frontmatter(text)
        is_index = f in indexes
        path = os.path.join(root, f)

        # 2. frontmatter
        if not is_index:
            if fm is None:
                add("error", "frontmatter", f, 1, "no frontmatter block")
            else:
                for field in ("name:", "description:", "type:"):
                    if field not in fm:
                        add("error", "frontmatter", f, 1, f"frontmatter lacks {field}", field)

        has_banner = bool(BANNER.search(text))
        ndate = note_date(f, fm, path)
        in_history = False
        for i, line in enumerate(body.split("\n"), offset + 1):
            if line.startswith("#"):
                in_history = bool(HISTORY_HEADING.search(line))
            # 3. identifiers known to be superseded, stated outside a history section
            for rx, s in superseded:
                if not rx.search(line):
                    continue
                if in_history or has_banner or INLINE_HISTORY.search(line):
                    continue
                add("error", "superseded", f, i,
                    f"{s['pattern']!r} is superseded since {s.get('since', '?')}: {s.get('now', 'see config')}", s["pattern"])
            # 4. relative dates lose their meaning once the note is a day old
            if not is_index:
                m = REL_HARD.search(line)
                if m:
                    add("error", "relative-date", f, i, f"relative date {m.group(0)!r}: write the absolute date", m.group(0).lower())
                else:
                    m = REL_SOFT.search(line)
                    if m and not DATE.search(line):
                        add("info", "relative-date", f, i, f"{m.group(0)!r} on a line with no absolute date", m.group(0).lower())
            # 5. deadlines written into the note
            m = RECHECK.search(line)
            if m:
                n = int(m.group(1))
                days = n * {"day": 1, "week": 7, "month": 30}[m.group(3).lower()]
                base = parse_date(line) or ndate
                due = base + dt.timedelta(days=days)
                if due <= today:
                    add("error", "recheck-due", f, i, f"{m.group(0)!r} from {base} was due {due}", m.group(0).lower())
            for m in EXPIRES.finditer(line):
                d = parse_date(m.group(1))
                if d and d < today and not (in_history or INLINE_HISTORY.search(line)):
                    add("error", "expired", f, i, f"states an expiry of {d}, which has passed", m.group(1))
                elif d and (d - today).days <= 30 and d >= today:
                    add("info", "expires-soon", f, i, f"expires {d} ({(d - today).days} days)", m.group(1))

        if is_index:
            continue
        # 6. a note with no absolute date anywhere cannot be aged
        if not DATE.search(f) and not DATE.search(text):
            add("info", "undated", f, 0, "no absolute date in the name or the text")
        # 7. notes written in an earlier era that still read as current
        for era in eras:
            before = parse_date(era["before"])
            if not before or ndate >= before or has_banner:
                continue
            if not re.search(era["pattern"], body):
                continue
            if era.get("marker") and re.search(era["marker"], body, re.I):
                continue
            add("info", "era", f, 0, f"dated {ndate}, before {era['before']} ({era['name']}), and carries no context marker", era["name"])

    order = {"error": 0, "info": 1}
    findings.sort(key=lambda x: (order[x["severity"]], x["check"], x["file"], x["line"]))
    errors = sum(1 for x in findings if x["severity"] == "error")
    infos = len(findings) - errors
    for x in findings[: a.max_lines]:
        loc = f"{x['file']}:{x['line']}" if x["line"] else x["file"]
        print(f"{x['severity'].upper():5} {x['check']:13} {loc} — {x['msg']}")
    if len(findings) > a.max_lines:
        print(f"... {len(findings) - a.max_lines} more in the JSON report")
    print(f"notes={len(files)} errors={errors} info={infos} baseline={len(baseline)} today={today}")
    if a.json:
        with open(a.json, "w") as out:
            json.dump({"today": str(today), "notes": len(files), "errors": errors, "info": infos, "findings": findings}, out, indent=1, ensure_ascii=False)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
