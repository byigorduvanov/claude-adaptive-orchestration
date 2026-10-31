---
name: reviewer-evals
description: Turn a real incident or confirmed bug on critical code into a lasting check for `critical-reviewer` (a failure class in its memory plus an eval case), and run its eval set after changing its prompt or model. Use at the end of a postmortem or a critical bug fix, and for "check the reviewer", "add this incident to the evals". Not for general code review.
---

# critical-reviewer evals

Every incident becomes a check, as the Claude Code team does with its reviewer. Two places:

- `~/.claude/agent-memory/critical-reviewer/MEMORY.md`: failure classes the reviewer loads at startup. The first 200 lines load, so keep it short and merge a new case into an existing class.
- `~/.claude/evals/critical-reviewer/cases/<id>/case.json`: an incident the reviewer must catch.

## Add an incident

1. Understand it first: a trade id or log line, and the code that caused it. An unproven theory is not a case.
2. Add or merge one line in `MEMORY.md`: the class, then the one real case.
3. Add a case when the bug can be reproduced from code. Skip it when the code is not available.

```json
{"id": "short-name", "repo": "~/work/<repo>", "base": "<commit with the bug>", "patch": "optional.diff",
 "focus": "paths or the change to review, with no hint of the bug", "expect": "what a passing review must identify"}
```

The focus names only where to look. `patch` is applied on top of `base` when the bug came in as a change.

## Reconcile with what was fixed

claude-mem records fixes on its own, and the reviewer never reads them. To find missing classes, list the last 14 days:

```bash
sqlite3 -readonly ~/.claude-mem/claude-mem.db "select id, title, narrative from observations where project='<project>' and type='bugfix' and created_at_epoch>(strftime('%s','now')-14*86400)*1000 order by id;"
```

On 10-31, 21 of 95 records were about critical code and 11 of those had no class, so filter by hand: most are test, build, CI and backtest noise.

A `bugfix` record means the session talked about it, not that the fix landed. Benchmark arms produce records for code that was never merged. Check the symbol on the remote before calling anything fixed: `git log --remotes -S<symbol>`.

## Run

```bash
python3 ~/.claude/evals/critical-reviewer/run.py            # all cases
python3 ~/.claude/evals/critical-reviewer/run.py <id>       # one case
```

It runs on the terminal `claude` login, one Opus session per case, so never on the desktop app account. It reviews with the current prompt but **without** the memory file, since memory contains the answers, and a small judge grades each report against `expect`. Reports land in `runs/<date>/`.

Run it after changing the reviewer's prompt or model, and run each case more than once before trusting a difference: one result moves between runs.
