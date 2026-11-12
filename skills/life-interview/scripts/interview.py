#!/usr/bin/env python3
"""State of the life interview, kept in <vault>/log/interview-checklist.md.

  interview.py status <vault> [--day N]          next day, its file, open topics
  interview.py tick <vault> <topic-id> <file>    mark a topic covered today
        [--skipped]                              the owner declined it for good
        [--today YYYY-MM-DD]

Checklist lines:  ## Day 3 — Money → areas/money.md
                  - [ ] d3-accounts: which banks and accounts
`tick` refuses unless <file> (relative to the vault) holds a fact dated today.
Exit code: 0 ok, 1 refused, 2 bad usage.
"""
import argparse
import datetime as dt
import os
import re
import sys

DAY = re.compile(r"^## Day (\d+)\s*[—-]\s*(.+?)\s*→\s*(\S+)\s*$")
ITEM = re.compile(r"^- \[([ xX~])\] ([a-z0-9-]+): (.*)$")


def parse(path):
    days, cur = [], None
    for n, line in enumerate(open(path, encoding="utf-8").read().split("\n")):
        m = DAY.match(line)
        if m:
            cur = {"n": int(m.group(1)), "title": m.group(2), "file": m.group(3), "items": []}
            days.append(cur)
            continue
        m = ITEM.match(line)
        if m and cur:
            cur["items"].append({"line": n, "state": m.group(1), "id": m.group(2), "text": m.group(3)})
    return days


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["status", "tick"])
    ap.add_argument("vault")
    ap.add_argument("topic", nargs="?")
    ap.add_argument("file", nargs="?")
    ap.add_argument("--day", type=int)
    ap.add_argument("--skipped", action="store_true")
    ap.add_argument("--today")
    a = ap.parse_args()
    today = a.today or str(dt.date.today())
    path = os.path.join(a.vault, "log", "interview-checklist.md")
    if not os.path.isfile(path):
        print(f"no checklist at {path}: copy assets/checklist.md there", file=sys.stderr)
        return 2
    days = parse(path)
    total = sum(len(d["items"]) for d in days)
    left = sum(1 for d in days for i in d["items"] if i["state"] == " ")

    if a.cmd == "status":
        for d in days:
            n_open = sum(1 for i in d["items"] if i["state"] == " ")
            print(f"day {d['n']}: {d['title']} -> {d['file']}  open {n_open}/{len(d['items'])}")
        pick = next((d for d in days if d["n"] == a.day), None) if a.day else \
            next((d for d in days if any(i["state"] == " " for i in d["items"])), None)
        if a.day and not pick:
            print(f"no day {a.day} in the checklist", file=sys.stderr)
            return 2
        if not pick:
            print(f"covered {total}/{total}: the interview is complete")
            return 0
        print(f"\nNEXT day {pick['n']}: {pick['title']} -> write to {pick['file']}")
        for i in pick["items"]:
            if i["state"] == " ":
                print(f"  {i['id']}: {i['text']}")
        later = [f"day {d['n']} ({', '.join(i['id'] for i in d['items'] if i['state'] == ' ')})" for d in days
                 if d is not pick and any(i["state"] == " " for i in d["items"]) and any(i["state"] != " " for i in d["items"])]
        if later:
            print("LEFT OPEN on a day already started: " + "; ".join(later))
        print(f"covered {total - left}/{total}")
        return 0

    if not a.topic or (not a.file and not a.skipped):
        print("tick needs <topic-id> and <file> (or --skipped)", file=sys.stderr)
        return 2
    item = next((i for d in days for i in d["items"] if i["id"] == a.topic), None)
    if not item:
        print(f"no topic {a.topic} in the checklist", file=sys.stderr)
        return 2
    if item["state"] != " ":
        print(f"{a.topic} is already closed")
        return 0
    if a.skipped:
        mark, note = "~", f"({today}, declined by the owner)"
    else:
        target = os.path.join(a.vault, a.file)
        if not os.path.isfile(target):
            print(f"REFUSED: {a.file} does not exist in the vault", file=sys.stderr)
            return 1
        if not re.search(r"^\s*[-*] .*\(" + re.escape(today) + r",\s*[^)]+\)", open(target, encoding="utf-8").read(), re.M):
            print(f"REFUSED: {a.file} holds no fact dated {today}: write the answer first", file=sys.stderr)
            return 1
        mark, note = "x", f"({today}, → {a.file})"
    lines = open(path, encoding="utf-8").read().split("\n")
    lines[item["line"]] = f"- [{mark}] {item['id']}: {item['text']} {note}"
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"ticked {a.topic}; covered {total - left + 1}/{total}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
