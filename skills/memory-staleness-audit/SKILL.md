---
name: memory-staleness-audit
description: "Audit auto-memory, the personal vault and claude-mem work state for stale facts (old hosts/accounts, relative dates, overdue rechecks, broken links, oversize index) and fix without deleting. Use for \"почисти пам'ять\", \"перевір vault\", \"перевір пам'ять на старе\", the weekly run."
---

# Memory staleness audit

Memory notes are point-in-time observations that get loaded as if they were true today. The damage comes from a note that reads as a current instruction while describing a state that ended: an old IP, an account that moved, a permission that was withdrawn. The agent acts on it with full confidence. This audit finds those notes and marks them, cheaply and on a schedule.

Two parts, in this order: a deterministic lint that finds candidates, then judgement on what the lint returned. The lint cannot tell history from instruction; that is your part.

## 1. Run the lint

```bash
python3 ~/.claude/skills/memory-staleness-audit/scripts/memory_lint.py "<memory_dir>" --json /tmp/memory-lint.json
```

`<memory_dir>` is `~/.claude/projects/<project-key>/memory`, where the key is the working directory with `/` replaced by `-` (`/Users/me/work/app` → `-Users-me-work-app`). Exit 0 means no errors, 1 means errors, 2 means the directory has no index.

The same script lints a markdown vault: pass the vault directory. The index is `MEMORY.md`, or `index.md` when there is no `MEMORY.md`, or the file `--index` names. Notes are read from subfolders too (hidden ones such as `.obsidian` are skipped), any `index-*.md` in any folder counts as a sub-index, links are resolved relative to the index that holds them, and `[[wikilinks]]` count as links.

It prints one line per finding and a summary line `notes=… errors=… info=…`; the full list is in the JSON. Checks:

| Check | Severity | Meaning |
|---|---|---|
| `superseded` | error | an identifier listed in the config as no longer current appears outside a history section |
| `relative-date` | error / info | "yesterday", "tomorrow", "next week" (error); "today" on a line with no date (info) |
| `recheck-due` | error | the note says "recheck in N weeks" and that date has passed |
| `expired` / `expires-soon` | error / info | a stated expiry date has passed, or falls within 30 days |
| `index-size` | error / info | `MEMORY.md` past 200 lines or 25 KB (the rest is not loaded), or over 80% of it |
| `broken-link`, `unindexed` | error | an index links to a missing note; a note no index links to is never recalled |
| `frontmatter` | error | no `name`, `description` or `type` |
| `era` | info | the note predates a cutover named in the config, mentions things from before it, and has no context marker |
| `undated` | info | no absolute date anywhere, so the note cannot be aged |
| `fact-provenance` | error | config `"fact_provenance": true`: a bullet in a note does not end in `(YYYY-MM-DD, source)` (checkbox lines are exempt) |
| `secret` | error | config `"forbid_secrets": true`: a line looks like a password, PIN, CVV or a card number (Luhn-valid) |

A line is exempt from `superseded` when it sits under a heading containing "history", "not current", "superseded", "pre-move", "obsolete" or "archive", when the file carries a `Context note (added YYYY-MM-DD)` banner, or when the line itself says so ("superseded", "retired", "was", "old").

## 2. Judge and fix

Work through every error, and up to 15 `info` findings per run (oldest notes first) so a backlog shrinks without one run reading the whole directory.

For each finding, read the note and decide which of three things it is:

- **A stale instruction** — it tells the reader how to reach, deploy or configure something, and that something changed. Fix it: put the current state at the top, move the old text under a `## History before <date> — NOT current` heading. Take the current facts from a source you can read now (ssh config, the newer note, the command itself), never from memory of what is probably true. Mark what you could not re-verify as "not re-verified since <date>".
- **Valid history with a misleading surface** — an incident write-up, a measurement, a decision. The content is still true as history, but hosts and steps in it read as current. Add one line directly under the frontmatter:
  `> **Context note (added YYYY-MM-DD):** this describes <what> BEFORE <date>. <What changed>. Current state: [[<note-name>]].`
- **Fine as it is** — the lint matched a word, nothing misleads. Record it in `.memory-lint-baseline.json` so it stops coming back:
  `{"accepted": {"<key from the JSON>": "<one-line reason, date>"}}`

Other fixes: replace a relative date with the absolute one (derive it from the note's date; say so if it is a guess); for `recheck-due`, either do the recheck or tell the owner it is due; for `index-size`, move entries into a topic index file linked from `MEMORY.md`.

Notes are never deleted in this audit: an old incident is evidence, and a wrong note corrected in place shows what was believed and when. Removing files stays the owner's call.

Back up each note before editing it (`cp -p` into a dated directory under the scratchpad), and re-run the lint afterwards: errors must be 0.

## 3. Work state

Call claude-mem `work_state_read`. An open item is stale when it has not moved for three weeks and its `blocked_by` names something that will not change by itself (revoked access, a retired box). Set it to `dropped` with a reason and the date; the `task` text must match the existing item exactly, or a new item is created. Leave items that wait on the owner, and list them in the report.

## 4. Keep the config current

`.memory-lint.json` in the memory directory is what makes the lint useful, and it is the only project-specific part:

```json
{
  "superseded": [
    {"pattern": "10\\.0\\.0\\.5|i-0abc123", "since": "2026-01-15", "now": "app box is i-0def456 / 10.0.1.9"}
  ],
  "eras": [
    {"name": "moved to the new account 2026-01-15", "before": "2026-01-15",
     "pattern": "old-box-name|old-account-id", "marker": "new-account|superseded"}
  ]
}
```

Whenever a host, IP, instance ID, account, key or permission changes — during this audit or any other task — add the old value to `superseded` with what replaced it. Add an `era` when access or infrastructure changes wholesale. Three more keys suit a personal vault: `"fact_provenance": true` and `"forbid_secrets": true` switch on the two checks above, and `"index_exempt": ["log/20*.md"]` lists globs of notes that need no index line (daily logs). A migration that is not recorded here is invisible to every later run.

## 5. Report

Keep it short: the lint summary line before and after, what was fixed (file → what changed), what was baselined and why, work-state items dropped, and what waits on the owner (rechecks due, keys expiring, anything that needed a fact you could not find). Say plainly what was not re-verified.
